---
name: api-discipline
description: Contract testing, versioning + traffic across Brain's tRPC/gRPC/MCP surfaces — buf breaking, Pact, deprecation/sunset, keyset pagination (OFFSET banned), token-bucket limits.
---

# API Discipline — Contracts, Versions, Traffic

Three surfaces, one discipline. **tRPC** (web/mobile BFF, Zod-inferred), **gRPC** (internal services via `buf` — see `grpc-buf`), **MCP** (agents + external partners — see `mcp-protocol`). Contract details are canonical in `canon/technical-requirements.md`; this is the operational playbook.

A breaking change in any surface propagates silently: a renamed `OrderEvent` field stops analytics materializing, the dashboard MER drops to zero, the Founder notices three days later. The three parts below are the structural alternative to "we'll review carefully."

---

# Part 1 — Contract testing

## gRPC — `buf breaking` is the gate
```bash
buf lint                                   # style/naming
buf breaking --against '.git#branch=main'  # CI gate on every protos/ PR
buf generate                               # TS + Python clients
```
CI fails if a PR removes a field, changes a type, or renumbers a tag. Intentional breaks → new `vN+1` package; v1 stays one minor release (see Part 2).

## tRPC — Zod inference + version gates
End-to-end typed inference is most of the protection — drift is a TS build error in CI. Remaining gap is cross-deploy shape change on the **same** procedure:
- New optional output fields are fine (`.optional()`). Outputs `.passthrough()`, inputs `.strict()`.
- Removing/renaming a field = breaking: add new, deploy both, wait one release, remove.

## MCP tool contracts
Versioned by name + schema version (`analytics.waterfall.compute.v2`). **Never edit a tool schema in place** — register `vN+1`, mark old `deprecated: true` (redirects internally with translation) for ≥1 release. Schemas generate from `protos/` so MCP↔gRPC cannot drift.

## Pact — consumer-driven, for cross-language semantic contracts
The `.proto` covers the wire format; Pact covers the *semantic* contract (e.g. "`CreateOrder` with `currency=INR` stores `gst_excluded = round(amount*100/118)`"). Use when Python ingestion calls Node core over gRPC.
```typescript
const provider = new PactV3({ consumer: 'core-service', provider: 'intelligence-service' });
// .given(state).uponReceiving(...).withRequest(...).willRespondWith({ body: MatchersV3.like({...}) })
// Provider side: new Verifier({ provider, pactBrokerUrl, publishVerificationResult: true, stateHandlers }).verifyProvider();
```
Use matchers (`like`, `eachLike`, `uuid`), validate structure not values, cover error paths (404/409/429/503). Hard-coded business values belong in integration tests, not contracts.

## OpenAPI / JSON Schema
Only the external read-only surface (Enterprise clients writing their own client) — generate from tRPC via `trpc-to-openapi`, gate on schema validation in middleware.

## CI gates
| PR touches | Gate |
|---|---|
| `protos/**` | `buf lint` + `buf breaking --against main` + clean `buf generate` |
| web/mobile tRPC clients | TypeScript build (Zod inference) |
| Service code | Pact verifier against published consumer contracts |
| MCP tool registry | schema diff; no in-place edits |

---

# Part 2 — Versioning & deprecation

## Safe vs breaking (cheat-sheet)
**Safe (no bump):** add optional input field · add output field · new endpoint/tool · new gRPC field with new tag · loosen validation.
**Breaking (new version):** remove/rename field · change type · remove enum value · add required input · tighten validation · change a field's *meaning* while keeping the name (silent break — worst kind).

## gRPC proto rules
Never renumber a tag · never change a field's type · never remove a field (mark `reserved`) · always add with new tag numbers. Breaking → new `package brain.<svc>.v2`; v1 stays ≥1 minor release.

## tRPC / MCP deprecation headers
```http
Deprecation: true
Sunset: Wed, 01 Jul 2026 00:00:00 GMT
Link: </api/trpc/orders.listV2>; rel="successor-version"
```
After sunset, return `410 Gone` with `{ error: "VERSION_SUNSET", migration_url }`.

## Deprecation timeline (canonical — min 6 months)
| Phase | Duration | Action |
|---|---|---|
| Deprecated | ≥3 mo | `Deprecation`+`Sunset` headers; MCP `deprecated:true`; email Enterprise consumers |
| Sunset announced | ≥2 mo (overlaps) | email all consumers + migration guide; UI nudge for internal callers still on v1 |
| Read-only | 1 mo | mutating calls → `410`; reads still work |
| Shutdown | — | all calls `410`; code removed next release |
Sooner only with all-Owner approval + Decision Log entries from every consuming workspace.

## v1↔v2 reconciliation (legacy single-tenant → multi-tenant migration)
Migration W14–16: W14 v2 in shadow (v1 canonical, data flows to both) · W15 Tanvi runs reconciliation daily · W16 cutover (v2 canonical, v1 read-only → 6-month timeline). **Any dashboard-metric divergence > 1% blocks cutover** (parity tests, Tanvi).

## Practices
Support N-1 minimum · ≥6-month window · monitor per-version usage (TanStack Query logs which version each request uses) · ship `docs/migrations/<from>-to-<to>.md` with code examples · migrate internal callers before announcing external sunset · Decision Log row when a sunset endpoint starts returning 410.

---

# Part 3 — Traffic: pagination + rate limiting

## Cursor (keyset) pagination — OFFSET is BANNED in prod paths
OFFSET scans rows it discards (page 50 = 50× page 1). Default for every list endpoint (orders, customers, decision_log, audiences). OFFSET only in bounded internal admin tooling.
```typescript
const listInput = z.object({ cursor: z.string().datetime().nullish(), limit: z.number().min(1).max(200).default(50) });
// WHERE workspace_id = current_setting('app.workspace_id')::uuid
//   AND ($1::timestamptz IS NULL OR created_at < $1)
// ORDER BY created_at DESC, id DESC LIMIT $2   -- fetch limit+1 to detect hasMore
// return { data, nextCursor: hasMore ? last.created_at.toISOString() : null }
```
- Cursor = last item's sort key. For ties use a **compound `(created_at, id)`** cursor (base64url-encode for high-write tables: decision_log, raw events).
- Sort column must be indexed with **`workspace_id` leading** (see `data-layer`).
- Max limit 200, default 50, never "unlimited." Don't `COUNT(*)` a multi-million-row table for a total.
- UI: "load more"/infinite scroll, never "page X of Y." BFF uses TanStack `useInfiniteQuery` consuming `nextCursor`.
- ClickHouse: cursor cheap when `ORDER BY` matches the primary key; for >5k-row drill-downs, server-side aggregate before paginating — never pull raw points to the client.
- MCP/canonical envelope: `{ "data": [...], "nextCursor": "...", "hasMore": true }` — external clients honor `nextCursor` like internal ones.

## Rate limiting — distributed token bucket / sliding window
Protect api-gateway, throttle per-brand by tier, prevent connector spikes from blowing vendor quotas.

| Algorithm | When |
|---|---|
| Token bucket | api-gateway per-brand — allows bursts (dashboard refreshes) |
| Sliding window log | high-precision (Decision Log writes, AI dispatch) where exact count matters |
| Fixed window | cheap per-IP defense at CloudFront; not per-brand |

**Distributed state via ElastiCache** — in-process buckets break under EKS auto-scaling.
```typescript
// Fastify preHandler, ElastiCache-backed sliding window (INCR + EXPIRE in a Lua script)
const TIER_LIMITS = { launch:{max:60}, growth:{max:120}, scale:{max:600}, enterprise:{max:6000} }; // per 60s
// emit X-RateLimit-Limit/Remaining/Reset; on over-limit → 429 + Retry-After (never 503/500)
```
Per-vendor **outbound** throttling (ingestion): ElastiCache as a global semaphore so replicas share the budget (Shopify 2 rps/shop, Meta ~200 calls/hr/app-user).

| Tier | GMV fee (of realized GMV) | Budget/brand |
|---|---|---|
| Launch | ~1.0% | 60 rpm |
| Growth | ~0.75% | 120 rpm |
| Scale | ~0.5% | 600 rpm |
| Enterprise | Custom | 6,000 rpm or custom |

Always emit `X-RateLimit-*` so clients back off · 429+`Retry-After`, never 503 · per-brand AND per-IP (CloudFront does IP) · never rate-limit `/health/*` · cost-cap-aware AI throttle: brand over 80% monthly LLM budget → Sonnet→Haiku (see `cost-routing-paradigms`).

---

## Anti-patterns
`OFFSET 5000 LIMIT 50` on decision_log · `SELECT COUNT(*)` for a total over millions of rows · page numbers in URLs · ordering by `id` only · `limit=10000` · in-place gRPC tag / MCP schema edits · deploying without Pact verification · breaking change without a new version.

## Wiring
tRPC versioning/lists/quotas → Vikram · gRPC `buf breaking`/packages → Aryan+Vikram · MCP versioning → Vikram+Maya · v1↔v2 reconciliation → Tanvi+Maya · CH drill-down pagination + outbound/AI throttling → Maya · migration guides → owner+Priya.

Related: `grpc-buf`, `mcp-protocol`, `data-layer` (index for cursors), `cost-routing-paradigms`, `integration-connectors`, `observability` (429 rate as SLO).
