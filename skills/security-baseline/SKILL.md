---
name: security-baseline
description: Brain's security baseline — OWASP Top 10; Supabase Auth + JWT; multi-tenant `workspace_id` enforcement on Postgres (RLS) + ClickHouse (query gateway) + Kafka envelopes + MCP tool tenant check; MCP auth scopes (canon/technical-requirements.md); AWS IAM/VPC/WAF/Secrets Manager; threat modeling (STRIDE); mobile MASVS Level 1 + Level 2; cert pinning rotation discipline; India compliance gates (DLT, NCPR, DND, 48h frequency cap, calling hours, recording consent, GST). Shreya VETO on CRITICAL/HIGH and any India compliance violation.
---

# Security Baseline — Brain

This skill is the **security index + Shreya's review gate**. It owns the OWASP map, the Brain-specific security controls (Supabase Auth, OAuth token storage, India compliance VETO, MASVS, AWS baseline, STRIDE) and the verdict format. The two deep dives it links to:

- **`auth-and-access`** — OWASP A01 (Broken Access Control) in depth: the 5 level-ordered roles (viewer 1 < analyst 2 < agency 3 < operator 4 < owner 5), JWT-claim + RLS enforcement, `requireRole` on every mutation, MCP tool roles, agency multi-workspace — plus the Supabase session lifecycle (cookies, refresh, revocation).
- **`defense-in-depth-validation`** — multi-tenant `workspace_id` isolation as the four-layer (entry → business → environment/RLS → audit) pattern, and the structural "make the bug impossible" approach.

Don't duplicate those here — gate against them.

## OWASP Top 10:2025 (applied to Brain)

Mapped to **OWASP Top 10:2025** (finalized Jan 2026). Key shifts vs the older 2021 list: **A03 Software Supply-Chain Failures** is NEW (broadened from "Vulnerable & Outdated Components"), **A02** is now **Security Misconfiguration**, **Insecure Design** moves to **A06**, **SSRF is folded into Broken Access Control** (no longer a standalone A10), and **A10 Mishandling of Exceptional Conditions** is NEW. Brain ALREADY does most of A03 (Snyk/Trivy/SBOM/pinned image SHAs/EAS Build provenance) — so this is largely a **re-label that strengthens our supply-chain story**, not new work.

| # | OWASP 2025 | Brain enforcement |
|---|---|---|
| A01 | Broken Access Control (incl. **SSRF**) | `workspaceProcedure` on every tRPC procedure; `requireTenant` on every MCP tool; gRPC server handler asserts `request.workspace_id === metadata.workspace_id`; Postgres RLS as safety net; ClickHouse query gateway rejects unscoped queries. **SSRF (folded in):** whitelist allowed URLs in ingestion-service (only Shopify/Meta/Google/Shiprocket endpoints); no arbitrary URL fetches |
| A02 | Security Misconfiguration | No debug in prod; Fastify-helmet security headers; MCP `scope` declared on every tool; `requireTenant` on every write |
| A03 | Software Supply-Chain Failures (**NEW**) | `pnpm audit` + `pip-audit` + Snyk (TS/Py) in CI; Trivy on ECR images + filesystem; **SBOM in CI**; **pinned Docker image SHAs**; **EAS Build provenance** for mobile. (Brain already does most of this — see `vulnerability-scanning`.) |
| A04 | Cryptographic Failures | TLS everywhere; Supabase Auth JWT verified via JWKS; KMS envelope encryption for OAuth tokens — ciphertext in **AWS Secrets Manager**, only a `credential_secret_arn` ref in `core.integrations` |
| A05 | Injection | Prisma parameterized queries; Zod validation on every input; asyncpg parameterized; ClickHouse query gateway |
| A06 | Insecure Design (was A04) | Postgres RLS + ClickHouse query gateway = defense in depth; never rely on one layer |
| A07 | Auth Failures | Supabase Auth defaults; refresh rotation on every use; magic link expiry 10 min |
| A08 | Software / Data Integrity Failures | Pinned Docker image SHA; SBOM in CI; EAS Build provenance for mobile |
| A09 | Logging & Alerting Failures | Auth events logged to OpenSearch with correlation IDs; PII/secret redaction at logger + Fluent Bit Lua script; never log tokens |
| A10 | Mishandling of Exceptional Conditions (**NEW**) | Fail-closed on compliance/auth errors (a thrown check blocks the action, never falls through to "allow"); structured error paths that strip tokens; no stack traces to clients |

## Multi-Tenant Isolation (the Brain invariant) — gate, don't re-explain

`workspace_id` isolation is enforced as a four-layer defense-in-depth pattern (JWT claim → service-side gRPC check → Postgres RLS + ClickHouse query gateway → Kafka envelope + Decision Log audit). The full layer-by-layer walkthrough, the `brain_clickhouse` predicate guard, and the cross-workspace-403 verification snippets live in **`defense-in-depth-validation`** — Shreya's review confirms all four layers are present, citing that skill. Role-level access (who within a workspace can do what) is in **`auth-and-access`**.

Shreya's tenant-isolation gate (every review): cross-workspace read returns `403`; the ClickHouse gateway rejects any unscoped query; every new workspace-scoped table has an RLS policy; every MCP write tool declares a scope.

## Supabase Auth (canon/technical-requirements.md)

- Access token: short-lived JWT (~1h)
- Refresh token (web): httpOnly + secure + sameSite=lax cookie — **never** in JS
- Refresh token (mobile): `expo-secure-store` (Keychain `WHEN_UNLOCKED_THIS_DEVICE_ONLY` / Android Keystore-encrypted prefs) — **never** in AsyncStorage
- Refresh rotation: on every use
- Magic link expiry: 10 min
- Google OAuth scopes: `email + profile` only

### Fastify JWT verification

```typescript
// apps/api-gateway/src/auth.ts
import { createRemoteJWKSet, jwtVerify } from 'jose';

const JWKS = createRemoteJWKSet(new URL(`${SUPABASE_URL}/auth/v1/.well-known/jwks.json`));

export async function verifyToken(token: string) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: SUPABASE_URL,
    audience: 'authenticated',
  });
  return {
    userId: payload.sub as string,
    workspaceId: payload.app_metadata?.active_workspace_id as string,
  };
}
```

## MCP Auth Scopes (canon/technical-requirements.md)

Every MCP tool declares a required scope:

```
brain:analytics:read         — read-only metric queries
brain:memory:read            — Memory Layer read
brain:lifecycle:read         — outreach + ticket read
brain:lifecycle:write        — trigger audiences + outreach
brain:integrations:read      — connected platforms read
brain:integrations:write     — write back to platforms
brain:agent:invoke           — call Brain agents
brain:admin                  — superuser; rare; audited
```

Default new external API key: `brain:analytics:read + brain:memory:read`. Higher scopes need Owner approval (audit-logged).

Verification: a `*:read` scoped key returns 403 on `*:write` tool calls.

This is the canonical scope **catalog**. How each MCP tool *declares* its `requiredScope` + `requiredRole`, and how the server middleware enforces both, is in **`auth-and-access`** (MCP tool scopes section).

## OAuth Token Storage (canon: ARN ref, not ciphertext-in-DB)

Vendor tokens are **KMS-envelope-encrypted into AWS Secrets Manager**; the `core.integrations` row holds only an opaque `credential_secret_arn` reference — never the ciphertext. Per-workspace DEK; KEK in KMS, never exported. core-service owns a decryption wrapper:

```typescript
// apps/core-service/src/integrations/oauth.ts
import { SecretsManagerClient, PutSecretValueCommand } from '@aws-sdk/client-secrets-manager';

// Encrypt → store in Secrets Manager (KMS CMK on the secret); return the ARN for the DB row
async function putCredential(workspaceId: string, source: string, tokens: object): Promise<string> {
  const res = await sm.send(new PutSecretValueCommand({
    SecretId: `brain/integrations/${workspaceId}/${source}`,   // KMS-encrypted at rest
    SecretString: JSON.stringify(tokens),
  }));
  return res.ARN!;   // store ONLY this in core.integrations.credential_secret_arn
}
```

Maya (ingestion) asks core-service for a fresh-decrypted token per poll (fetched from Secrets Manager by ARN), refreshes if expired, **discards from memory immediately**. Plaintext tokens never live in the DB row, in logs, or long-lived in Python services. See `oauth-implementation` for the full flow.

## India Compliance (canon/technical-requirements.md) — VETO authority

Hard-coded into every calling / messaging path. Never feature-flagged.

| Rule | Verification snippet |
|---|---|
| Calling hours 09:00–21:00 IST | `place_call(...)` outside window → `deferred("outside_calling_hours")`; `call.dialed_at` never outside window in DB |
| DND (brand + NCPR) | Customer with `do_not_call=true` OR NCPR-listed → `blocked("brand_dnd"|"ncpr_listed")` |
| Consent | `consent_status IN ('opted_out','withdrawn')` → `blocked("consent_revoked")` |
| 48h frequency cap | Second call within 48h → `blocked("frequency_cap")` (unless segment=champions + vip_override) |
| DLT registration | Unregistered brand → `blocked("dlt_not_registered")` |
| Recording consent | Decline → call proceeds with no audio retained; `call.recording_url IS NULL` |
| GST inclusive pricing | Every revenue / margin calc nets out GST via RegionAdapter `extract_net_revenue` |

Test matrix mandatory for any lifecycle-service touch (see `testing-tdd` skill).

## Mobile MASVS v2.1.0 (canon/technical-requirements.md) — Shreya pairs with Karan

Pinned to **OWASP MASVS v2.1.0**. Brain targets MASVS Level 1 + key Level 2, and tracks the **MASVS-PRIVACY** control group (data minimization, transparency, user control over PII on-device) alongside `data-privacy-dpdp`:

| Control | Implementation |
|---|---|
| Sensitive data in secure storage | Refresh tokens in Keychain/Keystore via `expo-secure-store` |
| No PII / secrets in logs | Same redaction rules as backend |
| TLS cert pinning | Production builds only; pin api-gateway + Supabase; pin BOTH current + rotation cert |
| Anti-tampering | `expo-device.isRootedExperimentalAsync()` + warning banner (don't block — too aggressive) |
| Code obfuscation | Hermes minification (default) |
| Biometric for sensitive views | Phase 2 — `expo-local-authentication` |
| App attestation | Phase 3 — Apple DeviceCheck + Google Play Integrity |
| Screen recording prevention | Phase 2 — `FLAG_SECURE` on financial summary screens |
| Deep link validation | Reject unknown hosts |

### Cert pinning rotation sequence (CRITICAL — bricks app if mishandled)

1. Add new cert pin to `PINS` array in mobile code
2. **OTA-update the new pin set ONE WEEK BEFORE server cert rotation** via EAS Update
3. Rotate cert on server
4. Remove old pin in next OTA

Kill-switch endpoint (HTTP, NO pinning) for emergency pin fetch on cert errors.

## AWS Security Baseline (canon/technical-requirements.md)

```
VPC:    All services in private subnets; ALB only in public
IAM:    No wildcard `*` in production; per-pod IRSA roles on EKS; per-task ECR pull only
Encryption: Supabase RDS at-rest (AES-256), S3 SSE-S3, ElastiCache TLS + at-rest, KMS for OAuth tokens
Secrets: AWS Secrets Manager (KMS-encrypted), injected via EKS env-from-secret
WAF:    AWS WAF on CloudFront + ALB, 2000 req/5min/IP rate limit, geo rules
GuardDuty: enabled all regions
Security Hub: CIS + AWS Foundational Best Practices
```

## Threat modeling (STRIDE) — mandatory for any auth/payment/PII change

Save threat models to `memory/security/<slug>-threat-model.md` using `blueprints/threat-model.md`.

For each component touched:
- **S**poofing — can someone impersonate?
- **T**ampering — can data be modified in transit / at rest?
- **R**epudiation — can an action be denied?
- **I**nformation disclosure — what PII / secrets could leak?
- **D**enial of service — what can rate-limit be exhausted on?
- **E**levation of privilege — what scope escalation is possible?

## Verdict format (Shreya)

```
[SECURITY — SHREYA]
Review: <feature>

Vulnerabilities Found:
  CRITICAL: <issue>      → Fix: <verification snippet>
  HIGH:     <issue>      → Fix: <verification snippet>
  MEDIUM:   <issue>      → Recommendation: <suggestion>
  LOW:      <issue>      → Note

Security Controls Verified:
  - workspaceProcedure on tRPC: <list>
  - requireTenant on MCP tools: <list>
  - RLS policies on new tables: <list>
  - PII redaction at logger + Fluent Bit: verified
  - India compliance gates: <list of can_call / can_message paths tested>
  - MASVS controls (if mobile): <list>

Verdict: APPROVED | NEEDS FIXES

Accepted by: <Founder / Shreya> on <YYYY-MM-DD>
```

## Common failure modes

- **Findings without verification snippets** (encoded 2026-05-12 slice-3) — paragraphs feed design phase; builders need curl + expected response or test assertion. Detection: HIGH/CRITICAL with no snippet.
- **Forgetting one of the four tenant layers** — JWT alone, or RLS alone. All four mandatory.
- **MCP tool without scope** — Shreya blocks. Detection: `mcpTool({...})` missing `scope` field.
- **Token logged in error message** — when an OAuth refresh fails, the full request often contains the token. Mitigation: structured error path that strips tokens before logging.
- **httpOnly cookie missed** on web — XSS exfiltrates. Always `httpOnly + sameSite=lax + secure`.
- **Cert pinning rotation skipped one-week pre-rotation** — bricks app. Use kill-switch + coordinate with Jatin.
- **India compliance toggle** — never feature-flag calling hours / DLT / 48h cap.

## Secrets rotation lifecycle

KMS envelope encryption (above) protects secrets at rest; rotation bounds the blast radius if one leaks. Every secret class has a **cadence** and an **owner**:

| Secret | Rotation cadence | Mechanism |
|---|---|---|
| Per-workspace **DEK** | 90d | re-wrap under same KEK; lazy re-encrypt on next write |
| **KEK** (KMS CMK) | 365d | AWS KMS automatic key rotation (transparent; old key versions retained for decrypt) |
| Vendor **OAuth tokens** | per-vendor TTL (refresh on expiry) + forced re-auth 180d | core-service refresh wrapper; ARN-referenced in `core.integrations` |
| **JWT signing key** (Supabase) | 90d | dual-key overlap (below) |
| **DB creds** (Supabase/CH/Redis) | 90d | Secrets Manager rotation Lambda |

**Automated rotation:** DB + service creds rotate via **AWS Secrets Manager rotation Lambdas** (4-step `createSecret → setSecret → testSecret → finishSecret`); pods read the secret by ARN each pull (never bake into the image), so a rotation propagates without redeploy.

**Zero-downtime rotation (dual-key overlap):** never hard-swap a key in-flight. For JWT signing-key rollover, publish **both** old + new keys in the JWKS for one overlap window (≥ max token TTL ~1h) so in-flight tokens still verify; retire the old key only after the window. Mirrors the **cert-pin rotation** sequence (current + rotation pin live together one week before server cert rotation).

**Break-glass:** emergency human access to a raw secret is a separate, **time-boxed IAM role** (auto-expires), every use **logged to OpenSearch + audit** with `request_id`, and **alerts** Shreya + Jatin in real time. No standing human read on production secrets.

**Secret-sprawl scanning:** **gitleaks** in pre-commit + CI + **GitHub secret scanning** (push protection) catch a secret committed to the repo; a hit blocks the merge and triggers immediate rotation of the exposed credential.

## See also (the security trio + canon)

- `skills/auth-and-access/SKILL.md` — OWASP A01: role model + JWT/RLS + MCP tool roles + agency multi-workspace + session lifecycle
- `skills/defense-in-depth-validation/SKILL.md` — multi-tenant `workspace_id` four-layer isolation pattern
- `skills/india-commerce-economics/SKILL.md` — DLT + NCPR + DND compliance patterns
- `canon/technical-requirements.md` — canonical IAM + audit + log spine, MCP auth scopes, India compliance hard-codes, MASVS + cert pinning
- `blueprints/threat-model.md` — STRIDE template
