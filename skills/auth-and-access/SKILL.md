---
name: auth-and-access
description: Brain's identity + authorization layer — Supabase Auth (JWT + refresh token) session lifecycle (cookie config, mobile secure-store, token refresh, revocation/invalidate-all) AND role-based access control (5 level-ordered roles viewer<analyst<agency<operator<owner per workspace + agency multi-workspace) enforced structurally in JWT claims + Postgres RLS + MCP tool scopes, never in an in-process map. Use when wiring web cookie flows (Ananya), mobile token storage (Karan), token refresh, logout, adding a permission, designing an admin endpoint, wiring an MCP tool's scope, giving an agency user cross-brand access, or debugging JWT signature mismatch, refresh storms, cookie domain bugs, leaked tokens.
---

# Auth and Access

Brain uses **Supabase Auth** (JWT + refresh token) as the identity primitive. Authentication answers "who"; authorization answers "can they." Both are enforced **structurally** — JWT claims + Postgres RLS + MCP scopes — never as application-level if-statements. This skill covers the session lifecycle (Part 1) and RBAC (Part 2).

## Why this matters for Brain

| Surface | Concern |
|---|---|
| Web (Next.js BFF, Ananya) | Browser JS NEVER sees the access token — server reads it from an httpOnly cookie, adds `Authorization: Bearer` for the BFF → api-gateway hop |
| Mobile (RN + Expo, Karan) | Tokens live in **expo-secure-store** (Keychain/Keystore). NEVER AsyncStorage |
| api-gateway (Vikram) | Validates JWT on every request (incl. MCP); refresh is a dedicated rate-limited endpoint |
| MCP write tools | Each tool declares required scope + role; external partner keys are scoped (read-only by default) |
| Decision Log / Audit (Shreya) | Every session + role change is audit-logged with actor |
| Agency multi-workspace | One user → N workspaces with potentially-different roles in each |

## Don't reinvent — use Supabase Auth as the primitive

Supabase ships HS256 JWT + a Postgres-backed refresh-token table. Brain wires around it; we don't roll our own JWT library (slice-3 anti-pattern: don't install `jsonwebtoken`).

```typescript
// JWT verification (api-gateway preHandler hook) — jose, not a hand-rolled lib
import { createRemoteJWKSet, jwtVerify } from 'jose';
const JWKS = createRemoteJWKSet(new URL(`${process.env.SUPABASE_URL}/auth/v1/jwks`));

async function verifySupabaseJWT(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: `${process.env.SUPABASE_URL}/auth/v1`,
    audience: 'authenticated',
  });
  return payload; // { sub, email, app_metadata.workspace_id, app_metadata.role, ... }
}
```

**`workspace_id` AND `role` MUST come from `app_metadata` in the verified JWT** — never from the request body or query string. Slice-3 caught a cross-tenant write CVE because `brand_id` was read from `req.body.brandId` (see `defense-in-depth-validation`).

---

## Part 1 — Session lifecycle

### Cookie configuration (Web — Ananya, Next.js BFF)

```typescript
const COOKIE_OPTS = {
  httpOnly: true,                            // browser JS can't read
  secure:   process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,                  // 'strict' breaks OAuth redirects
  path:     '/',
  maxAge:   60 * 60,                         // 1 hour = access-token TTL
  // domain: '.brain.pipadacapital.com',     // only when serving multiple subdomains
};
const REFRESH_COOKIE_OPTS = { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 * 7 }; // 7 days
```

Server component reads the cookie via `next/headers` and adds it as a Bearer header to the api-gateway call. Browser JavaScript NEVER touches the token.

### Mobile token storage (Karan)

```typescript
import * as SecureStore from 'expo-secure-store';
const ACCESS = 'brain.access', REFRESH = 'brain.refresh';

export async function storeSession(s: { access: string; refresh: string }) {
  await SecureStore.setItemAsync(ACCESS, s.access, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY, // no iCloud Keychain sync
  });
  await SecureStore.setItemAsync(REFRESH, s.refresh);
}
export async function clearSession() {
  await Promise.all([SecureStore.deleteItemAsync(ACCESS), SecureStore.deleteItemAsync(REFRESH)]);
}
```

### Token refresh flow

```typescript
app.post('/auth/refresh', {
  config: { rateLimit: { max: 6, timeWindow: '1 minute' } },   // anti-storm
}, async (req, reply) => {
  const refreshCookie = req.cookies['brain.refresh'];
  if (!refreshCookie) return reply.code(401).send({ error: 'NO_REFRESH_TOKEN' });
  try {
    const s = await supabase.auth.refreshSession({ refresh_token: refreshCookie });
    if (!s.data.session) throw new Error('REFRESH_FAILED');
    reply.setCookie('brain.access',  s.data.session.access_token, COOKIE_OPTS)
         .setCookie('brain.refresh', s.data.session.refresh_token, REFRESH_COOKIE_OPTS)
         .send({ ok: true });
  } catch {
    reply.clearCookie('brain.access').clearCookie('brain.refresh').code(401).send({ error: 'REFRESH_FAILED' });
  }
});
```

**Refresh-storm protection:** rate-limit 6/min per workspace; a client that loops without backoff should 429 so the bug is visible. Clients refresh **lazily on 401**, never proactively on every request. Supabase rotates the refresh token on every refresh; store the new pair atomically (see `api-traffic-patterns` for the limiter).

### Revocation: invalidate-all-sessions (Shreya — GDPR + compromised-creds)

```typescript
await supabase.auth.admin.signOut(userId, 'global');   // kill every session for the user
await db.query(
  `INSERT INTO ai.decision_log (workspace_id, action, actor, reason)
   VALUES ($1, 'session.invalidate_all', $2, $3)`,
  [workspaceId, callerUserId, 'compromised_credentials']);
```

After global signout, mobile clients get 401 on the next protected call, clear secure-store, and bounce to login.

### Security requirements (non-negotiable)

- **HTTPS exclusively** — TLS terminates at CloudFront; ALB → service link is also TLS.
- **httpOnly + sameSite + secure on every auth cookie** — `sameSite: 'none'` without `secure: true` is silently rejected.
- **Refresh token rotation** — store the new pair atomically.
- **Strong, unique secrets per environment** — Supabase URL + anon + service-role keys live in AWS Secrets Manager, never env files.
- **Validate signatures on every request** — nothing bypasses JWKS verification, including MCP.
- **Audit every transition** — session.issued / refreshed / revoked / invalidate_all → Decision Log.

---

## Part 2 — Role-based access control

### Brain role model (canonical — R2: 5 roles, ordered by level)

Brain has **exactly 5 roles**, level-ordered. There is **no `admin` role** — the 4-role owner/admin/analyst/viewer model was explicitly rejected (R2). `requireRole` enforces a **minimum level** on every mutation.

| Role | Level | Within a workspace, can… |
|---|---|---|
| **Viewer** | 1 | Limited reports only. **No PII**, no exports, no actions. (Read-only stakeholder access.) |
| **Analyst** | 2 | Read dashboards + comment. No approvals, no settings writes, no outbound. |
| **Agency** | 3 | **Scoped** per-brand read/write as granted by the Owner; **every action tagged + audited**. (Cross-brand agency user.) |
| **Operator** | 4 | Operational write, approve/reject, lifecycle campaigns, inbox. **Cannot** change billing or delete the brand. |
| **Owner** | 5 | Full control — billing, integrations, users, costs, **auto-execute enablement**, consent transitions, agency invites, deletion. (Usually the brand's founder.) |
| **Service Bot** (internal) | — | Per-task Supabase service role; bypasses RLS for backfills + scheduled jobs only. Not a user-assignable role. |

**Agency context:** an agency user (level 3) has rows in `workspace_members` for each brand they manage, with potentially-different roles. The JWT carries the **current** workspace_id + role for the active session; switching workspaces re-issues the session. Every agency action is tagged with the acting agency + audited.

### Enforce in JWT + RLS — NOT in application code

```sql
CREATE TABLE workspace_members (
  workspace_id UUID NOT NULL,
  user_id      UUID NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('viewer','analyst','agency','operator','owner')),
  invited_by   UUID,
  joined_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_members ON workspace_members
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

A Supabase trigger writes `app_metadata.workspace_id` + `app_metadata.role` into the JWT on sign-in / workspace-switch. The api-gateway preHandler verifies the JWT and sets both as Postgres session GUCs:

```typescript
await db.query("SELECT set_config('app.workspace_id', $1, true), set_config('app.role', $2, true)",
  [req.workspaceId, req.role]);
```

### Permission checks at the tRPC layer

Application code does NOT compute "can the user do this?" — it asserts the role and lets RLS / service logic enforce.

```typescript
// Roles are LEVEL-ORDERED (R2). requireRole enforces a MINIMUM level — never array membership.
const ROLE_LEVEL = { viewer: 1, analyst: 2, agency: 3, operator: 4, owner: 5 } as const;
type Role = keyof typeof ROLE_LEVEL;

function requireRole(minRole: Role) {
  return t.middleware(({ ctx, next }) => {
    if (ROLE_LEVEL[ctx.role as Role] < ROLE_LEVEL[minRole])
      throw new TRPCError({ code: 'FORBIDDEN', message: `Required role ≥ ${minRole}` });
    return next();
  });
}
export const viewerProcedure   = t.procedure.use(requireRole('viewer'));   // level ≥ 1
export const analystProcedure  = t.procedure.use(requireRole('analyst'));  // level ≥ 2
export const agencyProcedure   = t.procedure.use(requireRole('agency'));   // level ≥ 3 (scoped + tagged)
export const operatorProcedure = t.procedure.use(requireRole('operator')); // level ≥ 4
export const ownerProcedure    = t.procedure.use(requireRole('owner'));    // level 5

// Usage — procedure declares the MINIMUM role; RLS is the structural bottom
export const adsRouter = router({
  spend: router({
    list:   analystProcedure.query(/* analyst+ reads */),
    adjust: operatorProcedure.input(adjustInput).mutation(/* operator+ writes */),
  }),
  consent: router({ grant: ownerProcedure.input(consentInput).mutation(/* owner-only */) }),
});
```

**`requireRole` on every mutation** is non-negotiable (canon §15 Definition of Done).

If a future bug skips the middleware, RLS + the Decision Log audit still catch it (`defense-in-depth-validation`).

### MCP tool scopes

Each MCP write tool declares the role it requires; external partner keys carry scopes (read-only by default; write scopes require Owner approval). The MCP server middleware rejects calls that don't satisfy **both** checks.

```typescript
mcp.registerTool({ name: 'analytics.waterfall.compute.v2', inputSchema: WaterfallV2Input,
  requiredScope: 'analytics:read', requiredRole: 'analyst', handler: async (i, ctx) => { /* ... */ } });
mcp.registerTool({ name: 'ads.spend.adjust',
  requiredScope: 'ads:write', requiredRole: 'operator', handler: async (i, ctx) => { /* ... */ } });
```

### Agency multi-workspace pattern

An agency user is just a user with rows in multiple workspaces. Switching workspace hits `/api/auth/switch-workspace?id=...` which (1) verifies the user has a `workspace_members` row for that workspace, (2) re-issues the JWT with the new `app_metadata.workspace_id` + `role`, (3) re-sets the auth cookies. The Supabase admin API + this endpoint are the **only** places that mutate session workspace.

### Audit every change (Decision Log)

```sql
INSERT INTO ai.decision_log (workspace_id, actor, action, target, payload, paradigm)
VALUES ($1, $2, 'workspace.member.role_change', $3,
        jsonb_build_object('from_role', $4, 'to_role', $5), 'sql');
```

This is also what makes the system reviewable for SOC 2 T1 (Phase 4).

---

## Never Do

- Store tokens in localStorage / sessionStorage / AsyncStorage; transmit them in URL query params (logs leak them).
- Use a single shared secret across environments; skip JWKS verification "because we know it came from Supabase."
- Set `sameSite: 'none'` without `secure: true`; refresh proactively on every request.
- Roll your own JWT library — use `jose` or the Supabase SDK.
- Hardcode permission checks deep in business logic — they belong in tRPC middleware + RLS, not inside `adsRepository.adjust()`.
- Use broad wildcards (`permissions: ['*']`) — only Owner is wildcard; everyone else needs an explicit grant.
- Trust the client about role or workspace — always re-derive from the verified JWT server-side.
- Skip audit logging for role changes — auditors fail you on SOC 2 if it's missing.

## Best practices

- **Least privilege** — start every new role at Viewer, escalate only on need; review role grants quarterly.
- **Role hierarchies are level-ordered** (`owner` 5 ⊃ `operator` 4 ⊃ `agency` 3 ⊃ `analyst` 2 ⊃ `viewer` 1) — a single `requireRole(minRole)` level check replaces N membership arrays; cache role-check decisions per request (in `ctx`), never across requests.
- **Separate authN from authZ** — Supabase Auth answers "who"; RBAC answers "can they."

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| api-gateway JWT verification + refresh endpoint | **Vikram** | canon/technical-requirements.md (auth) |
| Next.js BFF cookie flow + agency switch | **Ananya** | canon/technical-requirements.md (BFF + auth) |
| Mobile secure-store + refresh | **Karan** | canon/technical-requirements.md (token storage) |
| Role taxonomy + middleware | **Vikram** + **Shreya** | canon/technical-requirements.md (auth) |
| Postgres RLS policy review | **Shreya** + Aryan | canon/technical-requirements.md (multi-tenancy) |
| MCP tool scope catalogue | **Vikram** + **Maya** | canon/technical-requirements.md (scopes) |
| Revocation, audit, SOC 2 prep | **Shreya** + Jatin | canon/technical-requirements.md (audit) |

Related Brain skills: `security-baseline` (broader posture; this is its OWASP A01 deep dive), `defense-in-depth-validation` (the four-layer `workspace_id` pattern backstopping every check), `api-traffic-patterns` (refresh-storm rate limiting), `mcp-protocol` (tool scopes), `database-design` (RLS + `app.workspace_id` GUC).
