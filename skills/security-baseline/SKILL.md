---
name: security-baseline
description: App-sec playbook — OWASP map, four-layer input validation, output encoding/XSS, RLS, KMS secrets, STRIDE, MASVS, the CI scanner suite. Shreya VETO gate.
---

# Security Baseline

Shreya's review gate + the app-sec playbook. Multi-tenant `workspace_id` isolation and the role model are gated here but OWNED elsewhere — RBAC + session lifecycle in `auth-and-access`; compliance/India regime in `compliance-engine`. Don't restate those; gate against them.

## OWASP Top 10:2025 → Brain enforcement

| # | Category | Enforcement |
|---|---|---|
| A01 | Broken Access Control (incl. SSRF) | `workspaceProcedure` on every tRPC proc; `requireTenant` on every MCP tool; gRPC handler asserts `request.workspace_id === metadata.workspace_id`; Postgres RLS safety net; ClickHouse query gateway rejects unscoped queries. SSRF: ingestion-service URL allowlist (only vendor endpoints) — no arbitrary fetches |
| A02 | Security Misconfiguration | No debug in prod; fastify-helmet headers; MCP `scope` on every tool; `requireTenant` on every write |
| A03 | Software Supply-Chain Failures | scanner suite below + SBOM + pinned Docker SHAs + EAS Build provenance |
| A04 | Cryptographic Failures | TLS everywhere; Supabase JWT via JWKS; KMS envelope encryption for OAuth tokens (ARN ref in `core.integrations`, never ciphertext-in-DB) |
| A05 | Injection | Prisma + asyncpg parameterized; Zod on every input; ClickHouse query gateway |
| A06 | Insecure Design | RLS + query gateway = defense in depth; never one layer |
| A07 | Auth Failures | Supabase defaults; refresh rotation on every use; magic-link expiry 10min |
| A08 | Data Integrity Failures | pinned SHA; SBOM; EAS provenance |
| A09 | Logging/Alerting Failures | auth events → OpenSearch w/ correlation IDs; PII/secret redaction at logger + Fluent Bit Lua; never log tokens |
| A10 | Mishandling Exceptional Conditions | fail-closed on compliance/auth errors (thrown check blocks, never falls through to allow); strip tokens from error paths; no stack traces to clients |

## Four-layer input validation (make the bug structurally impossible)

The slice-3 lesson: a single check is bypassed by new code paths, refactors, mocks, or an MCP tool wired up six months later. Validate at EVERY layer. The cross-tenant `brand_id`-from-body CVE was killed by four layers, not one.

**L1 — Entry (Zod `.strict()` / Pydantic).** Reject invalid input at the boundary; `.strict()` REJECTS extra fields (incl. `brand_id`/`brandId`). `workspace_id` is NEVER in the input — it comes from JWT.
```typescript
const adsSpendInput = z.object({
  campaign_id: z.string().uuid(),
  spend_minor: z.number().int().nonnegative(),  // integer minor units — no float
  currency: z.enum(['INR','USD']),
}).strict();   // .strict() on EVERY public-facing schema — drift fails loud
// ctx.workspaceId set from JWT by the auth hook, never from input
```
**L2 — Business logic.** Assert invariants; don't trust your own callers. `assert(isUUID(workspaceId))`; verify the campaign belongs to this workspace even though RLS will block.
**L3 — Environment guard (RLS / query gateway).** The structural bottom even if L1/L2 are bypassed by a migration script.
```sql
ALTER TABLE ad_spend ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_ad_spend ON ad_spend
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
ClickHouse has no native RLS — every query goes through `pylibs/brain_clickhouse`, which rejects any query lacking a `workspace_id =` predicate. gRPC: server cross-checks metadata `workspace_id` against the issuing JWT; mismatch blocked + audit-logged.
**L4 — Audit.** Every write → `ai.decision_log` `(workspace_id, actor, action, target, payload_hash, paradigm, model, request_id)`. The forensic floor when L1–3 fail in future.

The Stripe-grade test: **can you craft a curl that bypasses L1–L2 and writes a row in another workspace?** If the answer isn't immediately "no," you don't have defense in depth.

Per-surface matrix (L1/L2/L3/L4): tRPC mutation · MCP write tool · ClickHouse insert · every outbound message (channel validator → compliance engine → vendor rate limit → `lifecycle.outbound_log`) · auth refresh · web cookie auth. Each needs all four.

## Output safety (XSS prevention)

Brain renders untrusted content everywhere: campaign names (Meta/Google), brand notes, inbox/ticket text, AI-generated headlines (treat as untrusted — prompt-injection risk; see `agentic-safety`), Decision Log payloads, deep-link params, external logo URLs. React escapes text by default; the net is gone the moment you reach for `dangerouslySetInnerHTML` or build URLs from input.

| XSS type | Defense |
|---|---|
| Reflected | Server Components escape; `URL()` validation |
| Stored | React text escape; DOMPurify when rendered as HTML |
| DOM-based | avoid `innerHTML`/`document.write`/`eval`; use `textContent` |
| Mutation (mXSS) | DOMPurify; never roll your own sanitizer |

```typescript
// packages/ui/src/sanitize.ts — isomorphic-dompurify (the only sanitizer Brain uses)
const RICH = { ALLOWED_TAGS:['b','i','em','strong','a','p','br','ul','ol','li','h3','h4'],
               ALLOWED_ATTR:['href','title','target','rel'], ALLOW_DATA_ATTR:false };
export const sanitizeRichText = (d:string) =>
  DOMPurify.sanitize(d, RICH).replace(/<a /g,'<a rel="noopener noreferrer" target="_blank" ');
export const sanitizeHeadline = (d:string) =>            // AI-generated: inline emphasis only
  DOMPurify.sanitize(d, { ALLOWED_TAGS:['b','em','strong'], ALLOWED_ATTR:[] });

const SAFE = new Set(['http:','https:','mailto:','tel:']);   // blocks javascript:/data:/vbscript:
export function safeURL(input?:string|null, fb='#'){ if(!input) return fb;
  try{ const u=new URL(input); return SAFE.has(u.protocol)?u.toString():fb; }catch{ return fb; } }
```
Sanitize at the **render boundary**, not storage (store raw → rules can change without backfill). Always allowlist. CSP: strict, per-request nonce, **no `unsafe-inline` on `script-src`** (`'self' 'nonce-…' 'strict-dynamic'`), `frame-ancestors 'none'`, plus `X-Content-Type-Options: nosniff` + `Referrer-Policy`. Mobile: `WebView` JS off unless needed + strict `originWhitelist`; `safeURL()` before `Linking.openURL`; Zod-validate push payloads before deep-link routing.

PR output-safety check: any new `dangerouslySetInnerHTML` is sanitized; any data-driven `<a href>`/`<img src>` uses `safeURL()`/host allowlist; CSP changes Shreya-approved; Playwright renders `<script>alert(1)</script>` + `<img src=x onerror=alert(1)>` and asserts they appear literally escaped.

## Secrets handling (KMS envelope)

Vendor OAuth tokens are KMS-envelope-encrypted into **AWS Secrets Manager**; `core.integrations` holds only `credential_secret_arn`. Per-workspace DEK; KEK in KMS, never exported. ingestion-service asks core-service for a fresh-decrypted token per poll, refreshes if expired, discards from memory immediately. Plaintext never in DB row, logs, or long-lived in Python. Full flow: `oauth-implementation`.

Rotation: per-workspace DEK 90d (re-wrap, lazy re-encrypt); KEK 365d (KMS auto); OAuth per-vendor TTL + forced re-auth 180d; JWT signing key 90d (dual-key JWKS overlap ≥ max token TTL); DB creds 90d (Secrets Manager rotation Lambda, 4-step). Pods read by ARN each pull — rotation propagates without redeploy. **Break-glass:** time-boxed IAM role (auto-expires), every use logged + alerts Shreya/Jatin; no standing human read on prod secrets. **Secret-sprawl:** gitleaks (pre-commit + CI) + GitHub secret scanning push-protection; a hit blocks merge + triggers rotation.

## Scanner suite (CI gate + incident response)

| Tool | Where | Catches |
|---|---|---|
| `pnpm audit` (`--audit-level=high`) | Node + web + mobile | npm advisory CVEs |
| Snyk (CLI + GitHub App) | Node + Python | CVEs, licenses, fix PRs |
| Trivy | ECR images + `fs` (vuln,secret,misconfig) | OS/app CVEs, secrets, bad Dockerfiles |
| Bandit | Python | hardcoded secrets, weak crypto, `assert` in prod |
| `pip-audit` + `safety` | Python deps | PyPA advisory CVEs |
| OWASP Dependency-Check | n/a (no JVM) — skip unless that changes | |
| cdk-nag | `infra/` | AWS Well-Architected violations |
| Dependabot + GitHub Secret Scanning | all repos | always-on |

CI workflow runs on every PR + nightly (`cron 0 18 * * *` = 23:30 IST). Image scan runs after build-and-push to `main`; CRITICAL/HIGH fails the ArgoCD trigger. Use `ignore-unfixed: true` (block what you can act on). SBOM (CycloneDX via Trivy) per image — SOC 2 evidence (see `compliance-attestation`).

**Severity policy:** CRITICAL → block merge, patch ≤24h, else compensating control (WAF rule / flag off path). HIGH → block, patch ≤7d or Shreya-approved deferred exception + Decision Log entry. MEDIUM → backlog. LOW → note. Copyleft license in link context → block.

**Suppressions** live in one versioned file (`.snyk` / `safety-policy.yml`), each with a reason + `expires` date; CI re-flags on expiry for quarterly re-review. No permanent ignores.

**Incident response (CI fires HIGH/CRITICAL):** Jatin acks (P2/P3, → P0/P1 if actively exploited) → Shreya assesses path usage + fix availability → patch PR or compensating control → postmortem in `memory/incidents/<date>-cve-<slug>.md`.

## Mobile MASVS v2.1.0 (Level 1 + key Level 2)

Tokens in Keychain/Keystore via `expo-secure-store`; same redaction as backend; TLS cert pinning prod-only (pin api-gateway + Supabase, BOTH current + rotation cert); anti-tamper banner (don't block); Hermes minification; biometric/`FLAG_SECURE` Phase 2; app attestation Phase 3; reject unknown deep-link hosts. Tracks MASVS-PRIVACY alongside `compliance-engine`.

**Cert-pin rotation (bricks app if mishandled):** (1) add new pin to `PINS`; (2) OTA the new set ONE WEEK BEFORE server cert rotation; (3) rotate server cert; (4) remove old pin next OTA. Kill-switch endpoint (HTTP, no pinning) for emergency pin fetch.

## STRIDE (mandatory for any auth/payment/PII change)

Save to `memory/security/<slug>-threat-model.md` via `blueprints/threat-model.md`. Per component: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.

## AWS baseline

Private subnets (ALB only public); no wildcard IAM in prod, per-pod IRSA; encryption at rest (RDS AES-256, S3 SSE, ElastiCache TLS+rest, KMS for tokens); Secrets Manager (KMS) via env-from-secret; WAF on CloudFront+ALB (2000 req/5min/IP, geo rules); GuardDuty all regions; Security Hub (CIS + AWS FBP).

## Verdict format (Shreya)

```
[SECURITY — SHREYA] Review: <feature>
Vulnerabilities: CRITICAL/HIGH/MEDIUM/LOW: <issue> → Fix: <verification snippet>
Controls Verified: workspaceProcedure / requireTenant / RLS on new tables / PII redaction / MASVS (mobile)
Verdict: APPROVED | NEEDS FIXES   Accepted by: <Shreya> on <YYYY-MM-DD>
```
Compliance/India gates → see `compliance-engine` (separate VETO surface).

## Anti-patterns
- Findings without verification snippets (HIGH/CRITICAL needs curl + expected response or test assertion).
- Forgetting one of the four tenant layers; MCP tool without scope; token logged in an error message.
- httpOnly cookie missed on web; cert-pin rotation skipped the one-week pre-rotation; soft-warning scanners that get ignored.

## See also
`auth-and-access` (A01: RBAC + JWT/RLS + session) · `compliance-engine` (DPDP/DLT/NCPR regime — separate VETO) · `agentic-safety` (untrusted-text + agent actions) · `compliance-attestation` (SBOM/SOC2 evidence) · `oauth-implementation` (token storage flow) · `canon/TECH/16_compliance_engine.md` · `canon/technical-requirements.md` · `blueprints/threat-model.md`
