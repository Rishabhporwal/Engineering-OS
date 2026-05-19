---
name: session-management
description: Session lifecycle, token refresh, cookie configuration, and revocation patterns for Brain's Supabase Auth + JWT layer. Use when wiring web cookie flows (Ananya), mobile token storage (Karan), token refresh, logout / invalidate-all-sessions, or encountering JWT signature mismatch, refresh storms, cookie domain bugs, leaked tokens.
---

# Session Management

Brain uses **Supabase Auth** (JWT + refresh token) as the identity primitive. This skill covers the production-shaped wiring around it: cookie config for web (Ananya), secure token storage for mobile (Karan), refresh flows (Vikram), and revocation (Shreya).

## Why this matters for Brain

| Surface | Requirement |
|---|---|
| Web (Next.js BFF, Ananya) | Browser JS NEVER sees the access token. Server components read it from an httpOnly cookie and add it as `Authorization: Bearer` for the BFF → api-gateway hop. |
| Mobile (RN + Expo, Karan) | Tokens live in **expo-secure-store** (Keychain on iOS, Keystore on Android). NEVER AsyncStorage. |
| api-gateway (Vikram) | Validates JWT on every request, including MCP. Refresh is a dedicated endpoint with strict rate limit. |
| Decision Log / Audit (Shreya) | Session events (issued, refreshed, revoked, invalidated-all) are audit-logged. |

## Don't reinvent — use Supabase Auth as the primitive

Supabase ships HS256 JWT + a refresh-token table backed by Postgres. Brain wires around it; we don't roll our own JWT library (see `.engineering-os/lessons-learned.md` — slice-3 anti-pattern: don't install `jsonwebtoken`).

```typescript
// JWT verification (api-gateway preHandler hook)
import { createRemoteJWKSet, jwtVerify } from 'jose';

const JWKS = createRemoteJWKSet(new URL(`${process.env.SUPABASE_URL}/auth/v1/jwks`));

async function verifySupabaseJWT(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: `${process.env.SUPABASE_URL}/auth/v1`,
    audience: 'authenticated',
  });
  return payload; // { sub, email, app_metadata.workspace_id, role, ... }
}
```

**`workspace_id` MUST come from `app_metadata.workspace_id` in the JWT.** Never from the request body or query string. Lesson learned: slice-3 caught a cross-tenant write CVE because brand_id was being read from `req.body.brandId`.

## Cookie Configuration (Web — Ananya, Next.js BFF)

```typescript
// app/api/auth/login/route.ts
const COOKIE_OPTS = {
  httpOnly: true,                            // browser JS can't read
  secure:   process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,                  // 'strict' breaks OAuth redirects
  path:     '/',
  maxAge:   60 * 60,                         // 1 hour matches access-token TTL
  // domain: '.brain.pipadacapital.com',     // only set when serving multiple subdomains
};

const REFRESH_COOKIE_OPTS = { ...COOKIE_OPTS, maxAge: 60 * 60 * 24 * 7 }; // 7 days
```

The server component reads the cookie via `next/headers` and adds it as a Bearer header to the api-gateway call. Browser JavaScript NEVER touches the token.

## Mobile token storage (Karan)

```typescript
import * as SecureStore from 'expo-secure-store';

const ACCESS = 'brain.access';
const REFRESH = 'brain.refresh';

export async function storeSession(s: { access: string; refresh: string }) {
  await SecureStore.setItemAsync(ACCESS, s.access, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  await SecureStore.setItemAsync(REFRESH, s.refresh);
}

export async function clearSession() {
  await Promise.all([SecureStore.deleteItemAsync(ACCESS), SecureStore.deleteItemAsync(REFRESH)]);
}
```

iOS `WHEN_UNLOCKED_THIS_DEVICE_ONLY` ensures the token doesn't sync to iCloud or other devices via Keychain sync.

## Token Refresh Flow

```typescript
// api-gateway: /auth/refresh
app.post('/auth/refresh', {
  config: { rateLimit: { max: 6, timeWindow: '1 minute' } }, // anti-storm
}, async (req, reply) => {
  const refreshCookie = req.cookies['brain.refresh'];
  if (!refreshCookie) return reply.code(401).send({ error: 'NO_REFRESH_TOKEN' });

  try {
    const newSession = await supabase.auth.refreshSession({ refresh_token: refreshCookie });
    if (!newSession.data.session) throw new Error('REFRESH_FAILED');

    reply
      .setCookie('brain.access',  newSession.data.session.access_token, COOKIE_OPTS)
      .setCookie('brain.refresh', newSession.data.session.refresh_token, REFRESH_COOKIE_OPTS)
      .send({ ok: true });
  } catch (err) {
    reply.clearCookie('brain.access').clearCookie('brain.refresh');
    reply.code(401).send({ error: 'REFRESH_FAILED' });
  }
});
```

**Refresh storm protection:** rate-limit at 6/min per workspace. A web client that loops on refresh without backoff is a bug; let it 429 so it's visible.

## Revocation: invalidate-all-sessions (Shreya, GDPR + compromised-creds path)

```typescript
// Supabase: globally sign out all sessions for a user
await supabase.auth.admin.signOut(userId, 'global');

// Brain audit log
await db.query(
  `INSERT INTO ai.decision_log (workspace_id, action, actor, reason)
   VALUES ($1, 'session.invalidate_all', $2, $3)`,
  [workspaceId, callerUserId, 'compromised_credentials'],
);
```

After global signout, mobile clients receive 401 on next protected call, clear secure-store, and bounce to login.

## Security Requirements (non-negotiable)

- **HTTPS exclusively.** TLS terminates at CloudFront; the ALB → ECS link is also TLS.
- **httpOnly + sameSite + secure on every auth cookie.** Browser JS NEVER reads tokens.
- **Refresh token rotation.** Supabase rotates on every refresh; Brain stores the new pair atomically.
- **Strong, unique secrets per environment.** Supabase Project URL + anon key + service-role key live in AWS Secrets Manager, NOT env files.
- **Validate signatures on every request.** No request bypasses the JWKS check, including MCP.
- **Audit every state transition.** session.issued, session.refreshed, session.revoked, session.invalidate_all → Decision Log.

## Never Do

- Store tokens in localStorage / sessionStorage / AsyncStorage.
- Transmit tokens via URL query parameters (logs leak them).
- Use a single shared secret across environments.
- Skip JWKS verification because "we know it came from Supabase."
- Set `sameSite: 'none'` without `secure: true` — modern browsers reject it silently.
- Refresh on every request — clients refresh lazily on 401, never proactively.
- Roll your own JWT library. Use `jose` or Supabase SDK.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| api-gateway JWT verification + refresh endpoint | **Vikram** | canon/BRAIN_TECHNICAL.md (auth) |
| Next.js BFF cookie flow | **Ananya** | canon/BRAIN_TECHNICAL.md (BFF + auth) |
| Mobile secure-store + refresh | **Karan** | canon/BRAIN_TECHNICAL.md (token storage) |
| Revocation, audit, compliance | **Shreya** | canon/BRAIN_TECHNICAL.md (audit) |
| Composite session events feed | **Jatin** (incident response) | canon/BRAIN_TECHNICAL.md |

Related Brain skills: `security-baseline` (broader auth posture), `api-rate-limiting` (refresh-storm protection), `defense-in-depth-validation` (never trust client-supplied `workspace_id`).
