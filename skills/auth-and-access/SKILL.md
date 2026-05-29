---
name: auth-and-access
description: Supabase Auth session lifecycle (cookies, secure-store, refresh, revoke) + 5-role RBAC enforced in JWT claims, RLS, and MCP scopes, never in app code.
---

# Auth and Access

Brain uses **Supabase Auth** (JWT + refresh token) as the identity primitive. Authentication answers "who"; authorization answers "can they." Both are enforced **structurally** — JWT claims + Postgres RLS + MCP scopes — never as application-level if-statements. Part 1 = session lifecycle; Part 2 = RBAC.

| Surface | Concern |
|---|---|
| Web (Next.js BFF, Ananya) | Browser JS NEVER sees the access token — server reads it from an httpOnly cookie, adds `Authorization: Bearer` for BFF → api-gateway |
| Mobile (RN + Expo, Karan) | Tokens in **expo-secure-store** (Keychain/Keystore). NEVER AsyncStorage |
| api-gateway (Vikram) | Validates JWT on every request (incl. MCP); refresh is a dedicated rate-limited endpoint |
| MCP write tools | Each declares required scope + role; external partner keys scoped (read-only by default) |
| Decision Log / Audit (Shreya) | Every session + role change is audit-logged with actor |
| Agency multi-workspace | One user → N workspaces with potentially-different roles in each |

## Use Supabase Auth as the primitive
Supabase ships JWT + a Postgres-backed refresh-token table with asymmetric signing keys (RS256/ES256) at a JWKS endpoint — verify via JWKS, not a shared secret. Don't roll your own JWT lib (slice-3 anti-pattern: don't install `jsonwebtoken`).
```typescript
// JWT verification (api-gateway preHandler) — jose, not hand-rolled
import { createRemoteJWKSet, jwtVerify } from 'jose';
const JWKS = createRemoteJWKSet(new URL(`${process.env.SUPABASE_URL}/auth/v1/jwks`));
async function verifySupabaseJWT(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: `${process.env.SUPABASE_URL}/auth/v1`, audience: 'authenticated' });
  return payload; // { sub, email, app_metadata.workspace_id, app_metadata.role, ... }
}
```
**`workspace_id` AND `role` MUST come from `app_metadata` in the verified JWT** — never from request body/query. Slice-3 caught a cross-tenant write CVE because `brand_id` was read from `req.body.brandId` (see `security-baseline` four-layer validation).

---

## Part 1 — Session lifecycle

### Cookie config (Web — Ananya, Next.js BFF)
```typescript
const COOKIE_OPTS = {
  httpOnly: true, secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,                  // 'strict' breaks OAuth redirects
  path: '/', maxAge: 60 * 60,                // 1h = access-token TTL
  // domain: '.brain.pipadacapital.com',     // only for multiple subdomains
};
const REFRESH_COOKIE_OPTS = { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 * 7 }; // 7 days
```
Server component reads the cookie via `next/headers`, adds it as a Bearer header to the api-gateway call. Browser JS NEVER touches the token.

### Mobile token storage (Karan)
```typescript
import * as SecureStore from 'expo-secure-store';
const ACCESS = 'brain.access', REFRESH = 'brain.refresh';
export async function storeSession(s: { access: string; refresh: string }) {
  await SecureStore.setItemAsync(ACCESS, s.access, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY }); // no iCloud sync
  await SecureStore.setItemAsync(REFRESH, s.refresh);
}
export async function clearSession() {
  await Promise.all([SecureStore.deleteItemAsync(ACCESS), SecureStore.deleteItemAsync(REFRESH)]);
}
```

### Token refresh flow
```typescript
app.post('/auth/refresh', { config: { rateLimit: { max: 6, timeWindow: '1 minute' } } }, // anti-storm
  async (req, reply) => {
  const refreshCookie = req.cookies['brain.refresh'];
  if (!refreshCookie) return reply.code(401).send({ error: 'NO_REFRESH_TOKEN' });
  try {
    const s = await supabase.auth.refreshSession({ refresh_token: refreshCookie });
    if (!s.data.session) throw new Error('REFRESH_FAILED');
    reply.setCookie('brain.access', s.data.session.access_token, COOKIE_OPTS)
         .setCookie('brain.refresh', s.data.session.refresh_token, REFRESH_COOKIE_OPTS)
         .send({ ok: true });
  } catch {
    reply.clearCookie('brain.access').clearCookie('brain.refresh').code(401).send({ error: 'REFRESH_FAILED' });
  }
});
```
**Refresh-storm protection:** 6/min per workspace; a client looping without backoff should 429 so the bug is visible. Clients refresh **lazily on 401**, never proactively. Supabase rotates the refresh token on every refresh; store the new pair atomically (`api-traffic-patterns` for the limiter).

### Revocation: invalidate-all-sessions (Shreya — GDPR + compromised creds)
```typescript
await supabase.auth.admin.signOut(userId, 'global');   // kill every session
await db.query(`INSERT INTO ai.decision_log (workspace_id, action, actor, reason)
   VALUES ($1, 'session.invalidate_all', $2, $3)`, [workspaceId, callerUserId, 'compromised_credentials']);
```
After global signout, mobile clients get 401 on the next protected call, clear secure-store, bounce to login.

### Non-negotiable
HTTPS exclusively (TLS at CloudFront; ALB→service also TLS) · httpOnly + sameSite + secure on every auth cookie (`sameSite:'none'` without `secure:true` is silently rejected) · refresh token rotation, store new pair atomically · per-environment secrets in Secrets Manager, never env files · validate signatures on every request incl. MCP · audit every transition (issued/refreshed/revoked/invalidate_all → Decision Log).

---

## Part 2 — Role-based access control

### Brain role model (R2: 5 roles, level-ordered)
Exactly 5 roles, level-ordered. **No `admin` role** — the 4-role owner/admin/analyst/viewer model was explicitly rejected (R2). `requireRole` enforces a **minimum level** on every mutation.

| Role | Level | Within a workspace |
|---|---|---|
| Viewer | 1 | Limited reports only. No PII, no exports, no actions. |
| Analyst | 2 | Read dashboards + comment. No approvals/settings writes/outbound. |
| Agency | 3 | Scoped per-brand read/write as granted by Owner; every action tagged + audited. |
| Operator | 4 | Operational write, approve/reject, lifecycle, inbox. Cannot change billing or delete brand. |
| Owner | 5 | Full control — billing, integrations, users, costs, auto-execute enablement, consent transitions, agency invites, deletion. |
| Service Bot | — | Per-task Supabase service role; bypasses RLS for backfills + scheduled jobs only. Not user-assignable. |

**Agency context:** an agency user (level 3) has `workspace_members` rows per brand, with potentially-different roles. The JWT carries the current workspace_id + role; switching re-issues the session. Every agency action is tagged + audited.

### Enforce in JWT + RLS — NOT in app code
```sql
CREATE TABLE workspace_members (
  workspace_id UUID NOT NULL, user_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('viewer','analyst','agency','operator','owner')),
  invited_by UUID, joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id));
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_members ON workspace_members
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
A Supabase trigger writes `app_metadata.workspace_id` + `app_metadata.role` into the JWT on sign-in/switch. The api-gateway preHandler verifies the JWT and sets both as Postgres GUCs:
```typescript
await db.query("SELECT set_config('app.workspace_id', $1, true), set_config('app.role', $2, true)",
  [req.workspaceId, req.role]);
```

### Permission checks at the tRPC layer
App code does NOT compute "can the user do this?" — it asserts the role; RLS / service logic enforces.
```typescript
const ROLE_LEVEL = { viewer:1, analyst:2, agency:3, operator:4, owner:5 } as const;
type Role = keyof typeof ROLE_LEVEL;
function requireRole(minRole: Role) {
  return t.middleware(({ ctx, next }) => {
    if (ROLE_LEVEL[ctx.role as Role] < ROLE_LEVEL[minRole])
      throw new TRPCError({ code: 'FORBIDDEN', message: `Required role ≥ ${minRole}` });
    return next(); });
}
export const viewerProcedure   = t.procedure.use(requireRole('viewer'));
export const analystProcedure  = t.procedure.use(requireRole('analyst'));
export const agencyProcedure   = t.procedure.use(requireRole('agency'));   // scoped + tagged
export const operatorProcedure = t.procedure.use(requireRole('operator'));
export const ownerProcedure    = t.procedure.use(requireRole('owner'));
// Procedure declares the MINIMUM role; RLS is the structural bottom
export const adsRouter = router({
  spend: router({ list: analystProcedure.query(/*…*/), adjust: operatorProcedure.input(adjustInput).mutation(/*…*/) }),
  consent: router({ grant: ownerProcedure.input(consentInput).mutation(/*…*/) }) });
```
**`requireRole` on every mutation** is non-negotiable (canon §15 Definition of Done). If a future bug skips the middleware, RLS + the Decision Log audit still catch it.

### MCP tool scopes
Each MCP write tool declares its required role; external partner keys carry scopes (read-only by default; write scopes need Owner approval). The MCP server middleware rejects calls failing **either** check.
```typescript
mcp.registerTool({ name: 'analytics.waterfall.compute.v2', inputSchema: WaterfallV2Input,
  requiredScope: 'analytics:read', requiredRole: 'analyst', handler: async (i, ctx) => {/*…*/} });
mcp.registerTool({ name: 'ads.spend.adjust',
  requiredScope: 'ads:write', requiredRole: 'operator', handler: async (i, ctx) => {/*…*/} });
```
Canonical scope catalog: `brain:analytics:read`, `brain:memory:read`, `brain:lifecycle:read|write`, `brain:integrations:read|write`, `brain:agent:invoke`, `brain:admin` (rare, audited). Default new external key: `brain:analytics:read + brain:memory:read`; higher scopes need Owner approval (audit-logged). Verify: a `*:read` key returns 403 on a `*:write` tool call.

### Agency multi-workspace
Switching workspace hits `/api/auth/switch-workspace?id=…` which (1) verifies a `workspace_members` row exists, (2) re-issues the JWT with the new `app_metadata.workspace_id` + `role`, (3) re-sets cookies. The Supabase admin API + this endpoint are the ONLY places that mutate session workspace.

### Audit every change (Decision Log)
```sql
INSERT INTO ai.decision_log (workspace_id, actor, action, target, payload, paradigm)
VALUES ($1, $2, 'workspace.member.role_change', $3,
        jsonb_build_object('from_role', $4, 'to_role', $5), 'sql');
```
This is also what makes the system reviewable for SOC 2 (Phase 4 — `compliance-attestation`).

---

## Never Do
- Store tokens in localStorage/sessionStorage/AsyncStorage; transmit them in URL query params (logs leak them).
- Single shared secret across environments; skip JWKS verification; `sameSite:'none'` without `secure:true`; refresh proactively every request.
- Roll your own JWT library; hardcode permission checks deep in business logic (belong in tRPC middleware + RLS).
- Broad wildcards (`['*']`) — only Owner is wildcard; trust the client about role/workspace; skip audit logging for role changes.

## Best practices
Least privilege (start at Viewer, escalate on need; review grants quarterly) · level-ordered hierarchies (one `requireRole(minRole)` check replaces N membership arrays; cache per-request in `ctx`, never across requests) · separate authN from authZ.

## Brain wiring
| Concern | Owner |
|---|---|
| api-gateway JWT verification + refresh | Vikram |
| Next.js BFF cookie flow + agency switch | Ananya |
| Mobile secure-store + refresh | Karan |
| Role taxonomy + middleware; RLS review | Vikram + Shreya / Aryan |
| MCP tool scope catalogue | Vikram + Maya |
| Revocation, audit, SOC 2 prep | Shreya + Jatin |

Related: `security-baseline` (broader posture + four-layer validation) · `oauth-implementation` (vendor-side OAuth, distinct) · `api-traffic-patterns` (refresh-storm limiting) · `mcp-protocol` · `database-design` (RLS + GUC) · `compliance-attestation` (SOC 2 evidence).
