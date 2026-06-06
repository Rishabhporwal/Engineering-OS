---
name: security-baseline
description: App-sec playbook — OWASP map, four-layer input validation, output encoding/XSS, row-level isolation, KMS-backed secrets, STRIDE, mobile MASVS, the CI scanner suite. Security Reviewer VETO gate.
---

# Security Baseline

> **Reference implementation.** This skill documents one concrete binding of the security seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind these controls to different technology. The *patterns* (defense-in-depth at every
> layer, structural isolation, secrets never in the DB/logs, a CI scanner gate) are what transfer; the
> named tools are examples.

The Security Reviewer's review gate + the app-sec playbook. Multi-tenant isolation (the tenant key) and the role model are gated here but OWNED elsewhere — RBAC + session lifecycle in `auth-and-access`; the product's regulatory regime in `compliance-engine`. Don't restate those; gate against them.

## OWASP Top 10:2025 → enforcement

| # | Category | Enforcement |
|---|---|---|
| A01 | Broken Access Control (incl. SSRF) | a tenant-scoped procedure on every endpoint; a `requireTenant` check on every write tool; RPC handler asserts the request's tenant key matches the authenticated identity; row-level security as a datastore safety net; the OLAP query gateway rejects unscoped queries. SSRF: outbound URL allowlist (only known vendor endpoints) — no arbitrary fetches |
| A02 | Security Misconfiguration | no debug in prod; security response headers; a `scope` on every tool; `requireTenant` on every write |
| A03 | Software Supply-Chain Failures | scanner suite below + SBOM + pinned image SHAs + build provenance |
| A04 | Cryptographic Failures | TLS everywhere; verify JWTs via JWKS; KMS envelope encryption for stored credentials (a key/secret reference in the row, never ciphertext-in-DB) |
| A05 | Injection | parameterized queries everywhere; schema validation on every input; the OLAP query gateway |
| A06 | Insecure Design | row-level security + query gateway = defense in depth; never one layer |
| A07 | Auth Failures | refresh-token rotation on every use; short magic-link / OTP expiry |
| A08 | Data Integrity Failures | pinned SHA; SBOM; build provenance |
| A09 | Logging/Alerting Failures | auth events → the log aggregator with correlation IDs; PII/secret redaction at the logger + shipping layer; never log tokens |
| A10 | Mishandling Exceptional Conditions | fail-closed on compliance/auth errors (a thrown check blocks, never falls through to allow); strip tokens from error paths; no stack traces to clients |

## Four-layer input validation (make the bug structurally impossible)

The lesson: a single check is bypassed by new code paths, refactors, mocks, or a write tool wired up six months later. Validate at EVERY layer. A cross-tenant "id-from-request-body" class of bug is killed by four layers, not one.

**L1 — Entry (strict schema validation).** Reject invalid input at the boundary; strict mode REJECTS extra fields (including an attacker-supplied tenant/account id). The tenant key is NEVER in the input — it comes from the authenticated identity.
```typescript
const spendInput = z.object({
  campaign_id: z.string().uuid(),
  amount_minor: z.number().int().nonnegative(),  // integer minor units — no float money
  currency_code: z.string().length(3),
}).strict();   // .strict() on EVERY public-facing schema — drift fails loud
// the tenant key is set from the authenticated identity by the auth hook, never from input
```
**L2 — Business logic.** Assert invariants; don't trust your own callers. `assert(isUUID(tenantId))`; verify the resource belongs to this tenant even though row-level security will block.
**L3 — Environment guard (row-level security / query gateway).** The structural bottom even if L1/L2 are bypassed by a migration script.
```sql
ALTER TABLE spend ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_spend ON spend
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```
Where the OLAP store has no native row-level security, every query goes through a query gateway that rejects any query lacking a tenant-key predicate. For RPC: the server cross-checks the metadata tenant key against the issuing identity; a mismatch is blocked + audit-logged.
**L4 — Audit.** Where the Canon requires a system-of-record, every write → the audit log `(tenant_key, actor, action, target, payload_hash, request_id)`. The forensic floor when L1–3 fail in future.

The acid test: **can you craft a request that bypasses L1–L2 and writes a row for another tenant?** If the answer isn't immediately "no," you don't have defense in depth.

Per-surface matrix (L1/L2/L3/L4): a mutation endpoint · a write tool · an OLAP insert · every outbound message (channel validator → compliance check → vendor rate limit → outbound log) · auth refresh · web cookie auth. Each needs all four.

## Output safety (XSS prevention)

Any product that renders untrusted content — vendor-supplied names, user notes, inbox/ticket text, model-generated text (treat as untrusted — prompt-injection risk; see `agentic-safety`), audit payloads, deep-link params, external logo URLs. React/most frameworks escape text by default; the net is gone the moment you reach for raw-HTML injection or build URLs from input.

| XSS type | Defense |
|---|---|
| Reflected | server rendering escapes; `URL()` validation |
| Stored | framework text escape; a vetted sanitizer when rendered as HTML |
| DOM-based | avoid `innerHTML`/`document.write`/`eval`; use `textContent` |
| Mutation (mXSS) | a vetted sanitizer; never roll your own |

```typescript
// one shared sanitize module — use a single vetted sanitizer, never a bespoke one
const RICH = { ALLOWED_TAGS:['b','i','em','strong','a','p','br','ul','ol','li','h3','h4'],
               ALLOWED_ATTR:['href','title','target','rel'], ALLOW_DATA_ATTR:false };
export const sanitizeRichText = (d:string) =>
  sanitize(d, RICH).replace(/<a /g,'<a rel="noopener noreferrer" target="_blank" ');
export const sanitizeInline = (d:string) =>            // model-generated: inline emphasis only
  sanitize(d, { ALLOWED_TAGS:['b','em','strong'], ALLOWED_ATTR:[] });

const SAFE = new Set(['http:','https:','mailto:','tel:']);   // blocks javascript:/data:/vbscript:
export function safeURL(input?:string|null, fb='#'){ if(!input) return fb;
  try{ const u=new URL(input); return SAFE.has(u.protocol)?u.toString():fb; }catch{ return fb; } }
```
Sanitize at the **render boundary**, not storage (store raw → rules can change without backfill). Always allowlist. CSP: strict, per-request nonce, **no `unsafe-inline` on `script-src`** (`'self' 'nonce-…' 'strict-dynamic'`), `frame-ancestors 'none'`, plus `X-Content-Type-Options: nosniff` + `Referrer-Policy`. Mobile: `WebView` JS off unless needed + strict `originWhitelist`; `safeURL()` before opening a link; validate push payloads before deep-link routing.

PR output-safety check: any new raw-HTML injection is sanitized; any data-driven `<a href>`/`<img src>` uses `safeURL()`/host allowlist; CSP changes Security-approved; a browser test renders `<script>alert(1)</script>` + `<img src=x onerror=alert(1)>` and asserts they appear literally escaped.

## Secrets handling (KMS envelope)

Vendor credentials / tokens are KMS-envelope-encrypted into a managed secrets store; the DB row holds only a `credential_secret_ref`. Per-tenant data encryption key (DEK); key-encryption key (KEK) in KMS, never exported. A service asks for a fresh-decrypted token per use, refreshes if expired, and discards it from memory immediately. Plaintext never in a DB row, in logs, or long-lived in process memory. Full flow: `oauth-implementation`.

Rotation: per-tenant DEK ~90d (re-wrap, lazy re-encrypt); KEK ~365d (KMS auto); vendor token per-vendor TTL + forced re-auth ~180d; JWT signing key ~90d (dual-key JWKS overlap ≥ max token TTL); DB creds ~90d (managed rotation). Services read by reference each time — rotation propagates without redeploy. **Break-glass:** a time-boxed role (auto-expires), every use logged + alerts the Security Reviewer / Platform-SRE; no standing human read on prod secrets. **Secret-sprawl:** a secret scanner (pre-commit + CI) + the host's push-protection; a hit blocks merge + triggers rotation.

## Scanner suite (CI gate + incident response)

| Tool class | Where | Catches |
|---|---|---|
| package-manager audit (`--audit-level=high`) | every package ecosystem | advisory CVEs |
| an SCA scanner (CLI + host app) | all deps | CVEs, licenses, fix PRs |
| a container/filesystem scanner | built images + repo `fs` | OS/app CVEs, secrets, bad container files |
| a language linter for security | source | hardcoded secrets, weak crypto, `assert` in prod |
| dependency-advisory audit | language deps | advisory CVEs |
| an infra-as-code policy linter | `infra/` | cloud well-architected violations |
| host dependency/secret scanning | all repos | always-on |

CI runs the suite on every PR + nightly. Image scan runs after build-and-push to the default branch; CRITICAL/HIGH fails the deploy trigger. Ignore unfixable advisories (block what you can act on). Emit an SBOM per image — evidence for the compliance regime (see `compliance-attestation`).

**Severity policy:** CRITICAL → block merge, patch ≤24h, else a compensating control (WAF rule / flag off the path). HIGH → block, patch ≤7d or a Security-approved deferred exception + an audit-log entry. MEDIUM → backlog. LOW → note. A copyleft license in a linking context → block.

**Suppressions** live in one versioned policy file, each with a reason + an `expires` date; CI re-flags on expiry for quarterly re-review. No permanent ignores.

**Incident response (CI fires HIGH/CRITICAL):** Platform/SRE acks (P2/P3, → P0/P1 if actively exploited) → the Security Reviewer assesses path usage + fix availability → patch PR or compensating control → postmortem in `memory/incidents/<date>-cve-<slug>.md`.

## Mobile MASVS v2.1.0 (Level 1 + key Level 2)

Tokens in the OS keystore (Keychain/Keystore) via secure storage; same redaction as backend; TLS cert pinning in prod only (pin the API host + identity host, BOTH current + rotation cert); anti-tamper banner (don't block); release minification; biometric / screen-capture protection where the threat model needs it; app attestation where warranted; reject unknown deep-link hosts. Track MASVS-PRIVACY alongside `compliance-engine`.

**Cert-pin rotation (bricks app if mishandled):** (1) add new pin to `PINS`; (2) ship the new set ONE WEEK BEFORE server cert rotation; (3) rotate server cert; (4) remove old pin next release. Keep a kill-switch endpoint (no pinning) for emergency pin fetch.

## STRIDE (mandatory for any auth/payment/PII change)

Save to `memory/security/<slug>-threat-model.md`. Per component: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege.

## Cloud baseline

Private subnets (load balancer only public); no wildcard IAM in prod, per-workload identity; encryption at rest (DB, object store, cache, KMS for tokens); a managed secrets store via injected references; a WAF on the edge + load balancer (rate + geo rules); threat detection on all regions; a posture/compliance baseline (CIS + the cloud's best-practice set).

## Verdict format (Security Reviewer)

```
[SECURITY] Review: <feature>
Vulnerabilities: CRITICAL/HIGH/MEDIUM/LOW: <issue> → Fix: <verification snippet>
Controls Verified: tenant-scoped procedure / requireTenant / row-level security on new tables / PII redaction / MASVS (mobile)
Verdict: APPROVED | NEEDS FIXES   Accepted by: <Security Reviewer> on <YYYY-MM-DD>
```
The product's regulatory-regime gates → see `compliance-engine` (a separate VETO surface).

## Anti-patterns
- Findings without verification snippets (HIGH/CRITICAL needs a request + expected response or a test assertion).
- Forgetting one of the four tenant-isolation layers; a write tool without a scope; a token logged in an error message.
- httpOnly cookie missed on web; cert-pin rotation skipped the one-week pre-rotation; soft-warning scanners that get ignored.

## See also
`auth-and-access` (A01: RBAC + JWT / row-level security + session) · `compliance-engine` (the product's regulatory regime — a separate VETO) · `agentic-safety` (untrusted-text + agent actions) · `compliance-attestation` (SBOM / audit evidence) · `oauth-implementation` (token storage flow) · Product Canon: `COMPLIANCE.md`, `INVARIANTS.md`.
