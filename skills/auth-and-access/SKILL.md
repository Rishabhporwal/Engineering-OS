---
name: auth-and-access
description: Auth-provider session lifecycle (cookies, secure-store, refresh, revoke) + level-ordered RBAC enforced in JWT claims, RLS, and MCP scopes, never in app code.
---

# Auth and Access

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the identity seam to a different provider. The *patterns* here (structural enforcement via JWT claims + RLS + scopes, never app-level if-statements; level-ordered roles; per-request GUCs; audit every transition) are what transfer, not the Supabase vendor.

This binding uses **Supabase Auth** (JWT + refresh token) as the identity primitive. Authentication answers "who"; authorization answers "can they." Both are enforced **structurally** — JWT claims + Postgres RLS + MCP scopes — never as application-level if-statements. Part 1 = session lifecycle; Part 2 = RBAC.

> **Self-hosted IdP binding (Authentik / Keycloak / Zitadel).** When `STACK.md` runs its own identity provider, the structural-enforcement patterns are unchanged — only the provider differs. **Authentik** specifics that matter: the auth pipeline is **flows + stages** (customize auth by editing flows, not code); OIDC endpoints derive from the app **slug** (`/application/o/<slug>/.well-known/...`, JWKS at `/jwks/`, RP-initiated logout at `/end-session/`); verify via **JWKS** (`jose`), `audience = client_id`; a **refresh token needs the `offline_access` scope** mapping assigned or it's silently absent; **groups → claims** via a scope mapping (`request.user.ak_groups`), then map groups→app roles. **MFA** = an Authenticator Validation stage (TOTP/WebAuthn); **SAML** only when the RP speaks only SAML 2.0; **forward-auth/proxy provider** (via an outpost) protects non-OIDC services. **Operational reality (2025–26):** Postgres is the *only* durable store (**Redis removed in 2025.10**), `AUTHENTIK_SECRET_KEY` is a crown jewel (back it up *separately* from the DB — a DB restore is useless without it), never skip a major version on upgrade, and **patch the forward-auth bypass (≥2025.10.4/2025.12.4, CVSS 8.6)**. **Honest decision boundary:** Authentik **brands are NOT hard multi-tenancy** (apps/providers/policies are global) — for per-tenant isolation pick **Zitadel/Keycloak**; for a managed service pick Zitadel Cloud / Auth0. Run the IdP itself prod-like locally (`local-dev-environment`).

| Surface | Concern |
|---|---|
| Web (Next.js BFF, Frontend/Web Engineer) | Browser JS NEVER sees the access token — server reads it from an httpOnly cookie, adds `Authorization: Bearer` for BFF → api-gateway |
| Mobile (RN + Expo, Mobile Engineer) | Tokens in **expo-secure-store** (Keychain/Keystore). NEVER AsyncStorage |
| api-gateway (Backend Engineer) | Validates JWT on every request (incl. MCP); refresh is a dedicated rate-limited endpoint |
| MCP write tools | Each declares required scope + role; external partner keys scoped (read-only by default) |
| Audit (Security Reviewer) | Every session + role change is audit-logged with actor |
| Multi-tenant agency | One user → N tenants with potentially-different roles in each |

## Use the auth provider as the primitive
A managed auth provider ships JWT + a refresh-token table with asymmetric signing keys (RS256/ES256) at a JWKS endpoint — verify via JWKS, not a shared secret. Don't roll your own JWT lib (anti-pattern: don't install `jsonwebtoken`).
```typescript
// JWT verification (api-gateway preHandler) — jose, not hand-rolled
import { createRemoteJWKSet, jwtVerify } from 'jose';
const JWKS = createRemoteJWKSet(new URL(`${process.env.AUTH_URL}/auth/v1/jwks`));
async function verifyJWT(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: `${process.env.AUTH_URL}/auth/v1`, audience: 'authenticated' });
  return payload; // { sub, email, app_metadata.tenant_id, app_metadata.role, ... }
}
```
**The tenant key AND `role` MUST come from `app_metadata` in the verified JWT** — never from request body/query. A real cross-tenant write CVE traced to reading the tenant id from `req.body` — see `security-baseline` four-layer validation.

---

## Part 1 — Session lifecycle

### Cookie config (Web — Frontend/Web Engineer, Next.js BFF)
```typescript
const COOKIE_OPTS = {
  httpOnly: true, secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,                  // 'strict' breaks OAuth redirects
  path: '/', maxAge: 60 * 60,                // 1h = access-token TTL
  // domain: '.example.com',                 // only for multiple subdomains
};
const REFRESH_COOKIE_OPTS = { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 * 7 }; // 7 days
```
Server component reads the cookie via `next/headers`, adds it as a Bearer header to the api-gateway call. Browser JS NEVER touches the token.

### Mobile token storage (Mobile Engineer)
```typescript
import * as SecureStore from 'expo-secure-store';
const ACCESS = 'app.access', REFRESH = 'app.refresh';
export async function storeSession(s: { access: string; refresh: string }) {
  await SecureStore.setItemAsync(ACCESS, s.access, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY }); // no cloud sync
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
  const refreshCookie = req.cookies['app.refresh'];
  if (!refreshCookie) return reply.code(401).send({ error: 'NO_REFRESH_TOKEN' });
  try {
    const s = await auth.refreshSession({ refresh_token: refreshCookie });
    if (!s.data.session) throw new Error('REFRESH_FAILED');
    reply.setCookie('app.access', s.data.session.access_token, COOKIE_OPTS)
         .setCookie('app.refresh', s.data.session.refresh_token, REFRESH_COOKIE_OPTS)
         .send({ ok: true });
  } catch {
    reply.clearCookie('app.access').clearCookie('app.refresh').code(401).send({ error: 'REFRESH_FAILED' });
  }
});
```
**Refresh-storm protection:** 6/min per tenant; a client looping without backoff should 429 so the bug is visible. Clients refresh **lazily on 401**, never proactively. The provider rotates the refresh token on every refresh; store the new pair atomically (`api-discipline` for the limiter).

### Revocation: invalidate-all-sessions (Security Reviewer — data-protection erasure + compromised creds)
```typescript
await auth.admin.signOut(userId, 'global');   // kill every session
await db.query(`INSERT INTO audit_log (tenant_id, action, actor, reason)
   VALUES ($1, 'session.invalidate_all', $2, $3)`, [tenantId, callerUserId, 'compromised_credentials']);
```
After global signout, mobile clients get 401 on the next protected call, clear secure-store, bounce to login.

### Non-negotiable
HTTPS exclusively (TLS at the edge; edge→service also TLS) · httpOnly + sameSite + secure on every auth cookie (`sameSite:'none'` without `secure:true` is silently rejected) · refresh token rotation, store new pair atomically · per-environment secrets in a secrets manager, never env files · validate signatures on every request incl. MCP · audit every transition (issued/refreshed/revoked/invalidate_all → audit log).

---

## Part 2 — Role-based access control

### Role model (level-ordered)
A small, level-ordered role set (this binding uses 5). **No generic `admin` role** — a coarse owner/admin/analyst/viewer model was explicitly rejected in favor of operational roles. `requireRole` enforces a **minimum level** on every mutation.

| Role | Level | Within a tenant |
|---|---|---|
| Viewer | 1 | Limited reports only. No PII, no exports, no actions. |
| Analyst | 2 | Read dashboards + comment. No approvals/settings writes/outbound. |
| Agency | 3 | Scoped per-tenant read/write as granted by Owner; every action tagged + audited. |
| Operator | 4 | Operational write, approve/reject, lifecycle, inbox. Cannot change billing or delete a tenant. |
| Owner | 5 | Full control — billing, integrations, users, costs, auto-execute enablement, consent transitions, agency invites, deletion. |
| Service Bot | — | Per-task service role; bypasses RLS for backfills + scheduled jobs only. Not user-assignable. |

**Agency context:** an agency user (level 3) has `tenant_members` rows per tenant, with potentially-different roles. The JWT carries the current tenant + role; switching re-issues the session. Every agency action is tagged + audited.

### Enforce in JWT + RLS — NOT in app code
```sql
CREATE TABLE tenant_members (
  tenant_id UUID NOT NULL, user_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('viewer','analyst','agency','operator','owner')),
  invited_by UUID, joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tenant_id, user_id));
ALTER TABLE tenant_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_members ON tenant_members
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```
An auth-provider trigger writes `app_metadata.tenant_id` + `app_metadata.role` into the JWT on sign-in/switch. The api-gateway preHandler verifies the JWT and sets both as Postgres GUCs:
```typescript
await db.query("SELECT set_config('app.tenant_id', $1, true), set_config('app.role', $2, true)",
  [req.tenantId, req.role]);
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
**`requireRole` on every mutation** is non-negotiable (Canon Definition of Done). If a future bug skips the middleware, RLS + the audit log still catch it.

### MCP tool scopes
Each MCP write tool declares its required role; external partner keys carry scopes (read-only by default; write scopes need Owner approval). The MCP server middleware rejects calls failing **either** check.
```typescript
mcp.registerTool({ name: 'analytics.waterfall.compute.v2', inputSchema: WaterfallV2Input,
  requiredScope: 'analytics:read', requiredRole: 'analyst', handler: async (i, ctx) => {/*…*/} });
mcp.registerTool({ name: 'ads.spend.adjust',
  requiredScope: 'ads:write', requiredRole: 'operator', handler: async (i, ctx) => {/*…*/} });
```
Canonical scope catalog (namespaced per product): `<product>:analytics:read`, `<product>:memory:read`, `<product>:lifecycle:read|write`, `<product>:integrations:read|write`, `<product>:agent:invoke`, `<product>:admin` (rare, audited). Default new external key: read-only scopes; higher scopes need Owner approval (audit-logged). Verify: a `*:read` key returns 403 on a `*:write` tool call.

### Multi-tenant agency switching
Switching tenant hits `/api/auth/switch-tenant?id=…` which (1) verifies a `tenant_members` row exists, (2) re-issues the JWT with the new `app_metadata.tenant_id` + `role`, (3) re-sets cookies. The provider admin API + this endpoint are the ONLY places that mutate session tenant.

### Audit every change
```sql
INSERT INTO audit_log (tenant_id, actor, action, target, payload, paradigm)
VALUES ($1, $2, 'tenant.member.role_change', $3,
        jsonb_build_object('from_role', $4, 'to_role', $5), 'sql');
```
This is also what makes the system reviewable for SOC 2 (see `compliance-attestation`).

---

## Never Do
- Store tokens in localStorage/sessionStorage/AsyncStorage; transmit them in URL query params (logs leak them).
- Single shared secret across environments; skip JWKS verification; `sameSite:'none'` without `secure:true`; refresh proactively every request.
- Roll your own JWT library; hardcode permission checks deep in business logic (belong in tRPC middleware + RLS).
- Broad wildcards (`['*']`) — only Owner is wildcard; trust the client about role/tenant; skip audit logging for role changes.

## Best practices
Least privilege (start at Viewer, escalate on need; review grants quarterly) · level-ordered hierarchies (one `requireRole(minRole)` check replaces N membership arrays; cache per-request in `ctx`, never across requests) · separate authN from authZ.

## Wiring
| Concern | Role |
|---|---|
| api-gateway JWT verification + refresh | Backend Engineer |
| Next.js BFF cookie flow + agency switch | Frontend/Web Engineer |
| Mobile secure-store + refresh | Mobile Engineer |
| Role taxonomy + middleware; RLS review | Backend Engineer + Security Reviewer / Architect |
| MCP tool scope catalogue | Backend Engineer + AI/ML Engineer |
| Revocation, audit, SOC 2 prep | Security Reviewer + Platform/SRE |

Related: `security-baseline` (broader posture + four-layer validation) · `oauth-implementation` (vendor-side OAuth, distinct) · `api-discipline` (refresh-storm limiting) · `mcp-protocol` · `data-layer` (RLS + GUC) · `compliance-attestation` (SOC 2 evidence).
