---
name: security-baseline
description: Brain's security baseline — OWASP Top 10; Supabase Auth + JWT; multi-tenant `workspace_id` enforcement on Postgres (RLS) + ClickHouse (query gateway) + Kafka envelopes + MCP tool tenant check; MCP auth scopes (TECH/13 §5); AWS IAM/VPC/WAF/Secrets Manager; threat modeling (STRIDE); mobile MASVS Level 1 + Level 2; cert pinning rotation discipline; India compliance gates (DLT, NCPR, DND, 48h frequency cap, calling hours, recording consent, GST). Shreya VETO on CRITICAL/HIGH and any India compliance violation.
---

# Security Baseline — Brain

## OWASP Top 10 (applied to Brain)

| # | OWASP | Brain enforcement |
|---|---|---|
| A01 | Broken Access Control | `workspaceProcedure` on every tRPC procedure; `requireTenant` on every MCP tool; gRPC server handler asserts `request.workspace_id === metadata.workspace_id`; Postgres RLS as safety net; ClickHouse query gateway rejects unscoped queries |
| A02 | Cryptographic Failures | TLS everywhere; RS256 JWT in prod via Supabase Auth; KMS envelope encryption for OAuth tokens in core-service `integrations_oauth_tokens` |
| A03 | Injection | Prisma parameterized queries; Zod validation on every input; asyncpg parameterized; ClickHouse query gateway |
| A04 | Insecure Design | Postgres RLS + ClickHouse query gateway = defense in depth; never rely on one layer |
| A05 | Security Misconfiguration | No debug in prod; Fastify-helmet security headers; MCP `scope` declared on every tool; `requireTenant` on every write |
| A06 | Vulnerable Components | `pnpm audit` + `pip-audit` in CI; Snyk on Docker images |
| A07 | Auth Failures | Supabase Auth defaults; refresh rotation on every use; magic link expiry 10 min |
| A08 | Software Integrity | Pinned Docker image SHA; SBOM in CI; EAS Build provenance for mobile |
| A09 | Logging Failures | Auth events logged to OpenSearch with correlation IDs; PII/secret redaction at logger + Fluent Bit Lua script; never log tokens |
| A10 | SSRF | Whitelist allowed URLs in ingestion-service (only Shopify/Meta/Google/Shiprocket endpoints); no arbitrary URL fetches |

## Multi-Tenant Isolation — defense in depth

The Brain invariant. Four layers, all mandatory.

### Layer 1 — JWT claim
Every authenticated request carries `active_workspace_id` in the JWT. api-gateway extracts on every request, propagates via gRPC metadata.

### Layer 2 — Service-side check
Every gRPC handler asserts `request.workspace_id === metadata.workspace_id` (or member-of for cross-workspace orgs). Reject mismatches.

### Layer 3 — Database enforcement

**Postgres** — RLS policies on every workspace-scoped table:
```sql
CREATE POLICY tenant_isolation ON <table>
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
Connection pool sets `app.workspace_id` on acquisition (Vikram's `pg.setRoleAndTenant()`; Python `asyncpg` pool's `setup=set_tenant_context`).

**ClickHouse** — primary key first column always `workspace_id`. Every query through `pylibs/brain_clickhouse.query()`:
```python
WORKSPACE_PREDICATE = re.compile(r"workspace_id\s*=", re.IGNORECASE)

async def query(sql: str, params: dict):
    if not WORKSPACE_PREDICATE.search(sql):
        raise ClickHouseQueryError("CH query missing workspace_id predicate")
    return await client.execute(sql, params)
```

### Layer 4 — Kafka envelope
Every event carries `workspace_id` in payload and is partitioned by `workspace_id`. Consumers extract and assert on join.

### Verification snippet (per security review)

```typescript
it('workspace A cannot read workspace B', async () => {
  const response = await request.post('/trpc/orders.list')
    .set('Authorization', `Bearer ${WORKSPACE_A_JWT}`)
    .send({ workspace_id: 'workspace-b' });
  expect(response.status).toBe(403);
});

it('CH query gateway rejects unscoped', async () => {
  await expect(query("SELECT * FROM orders_local", {}))
    .rejects.toThrow(/workspace_id/);
});
```

## Supabase Auth (TECH/09)

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

## MCP Auth Scopes (TECH/13 §5)

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

## OAuth Token Storage

Tokens go to `core-service.integrations_oauth_tokens` (Postgres). Envelope-encrypted with AWS KMS via:

```typescript
// apps/core-service/src/integrations/oauth.ts
import { KMSClient, EncryptCommand } from '@aws-sdk/client-kms';

async function encryptToken(plaintext: string): Promise<string> {
  const result = await kms.send(new EncryptCommand({
    KeyId: process.env.OAUTH_KMS_KEY_ID,
    Plaintext: Buffer.from(plaintext),
  }));
  return result.CiphertextBlob.toString('base64');
}
```

Sahil (ingestion) asks core-service for a fresh-decrypted token per poll, refreshes if expired, **discards from memory immediately**. Plaintext tokens never live long-lived in Python services.

## India Compliance (TECH/11 §6) — VETO authority

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

## Mobile MASVS (TECH/10 §11) — Shreya pairs with Karan

Brain targets MASVS Level 1 + key Level 2:

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

## AWS Security Baseline (TECH/09)

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

## References

- `docs/TECH/09_security_observability.md` — canonical IAM + audit + log spine
- `docs/TECH/13_mcp_protocol.md` §5 — MCP auth scopes
- `docs/TECH/11_lifecycle_revenue_layer.md` §6 — India compliance hard-codes
- `docs/TECH/10_mobile_architecture.md` §11 — MASVS + cert pinning
- `skills/india-commerce-economics/SKILL.md` §compliance — DLT + NCPR + DND patterns
- `blueprints/threat-model.md` — STRIDE template
