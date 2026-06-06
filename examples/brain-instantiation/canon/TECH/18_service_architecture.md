# TECH/18 — Service Architecture (per-service operational spec)

> **Authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. This deep-dive is the **per-service operational specification** — it consolidates *how each service is built, bounded, scaled, secured, and recovered*, and the *communication + data/event flows* that stitch them into Brain's end-to-end functionality.
> **Stay DRY:** the deep specifics live in their home files — DB schemas → `TECH/01`, integrations/connectors → `TECH/02`, metric engine → `TECH/03`, region adapters → `TECH/04`, intelligence/memory → `TECH/05`, API contracts → `TECH/06`, web → `TECH/07`, alerts → `TECH/08`, security/observability → `TECH/09`, mobile → `TECH/10`, lifecycle → `TECH/11`, cost-routing → `TECH/12`, MCP → `TECH/13`, agents → `TECH/14`, billing → `TECH/15`, compliance → `TECH/16`. This file cross-references them; it does not duplicate them.
> Updated 2026-05-23.

---

## 0. How to read this

The product is the 10-layer flow the founder defined (ingest → raw → canonical → analytics → prediction → memory → agentic → multi-tenant → RBAC → cloud-native). Those layers are **realized by 7 backend bounded contexts + 2 clients + the LiteLLM gateway**, never by per-layer microservices. This file specifies each service across nine dimensions: **responsibilities · boundary/ownership · internal modules · communication · data/event flow · scalability/deployment · security/tenancy · real-time · failure/retry.** Section 1 states the platform-wide decisions once; §3 is the per-service detail; §4–§5 are the connectivity matrix + the end-to-end flows; §6 is the deferred-until-trigger forward extensions; §7 is the service-readiness DoD.

---

## 1. Platform-wide architecture decisions

| Concern | Decision |
|---|---|
| **Topology / DDD** | Modular-monolith → microservices: **3 deployables Phase 0–1** (`edge`=api-gateway+core [Node]; `data`=ingestion+analytics+intelligence [Python]) + web + mobile → split to the **7 backend services** at Phase 2. Every context is DDD-structured (`bootstrap/domain/application/infrastructure/interfaces`); proto contracts exist day-one → the split is mechanical, not a rewrite. |
| **DB-per-service (polyglot persistence)** | No shared DB. core→Postgres `core/billing/audit/consent`; ingestion→ClickHouse `raw_*` + S3 (+ watermarks); analytics→ClickHouse canonical+derived + Postgres `ai.decision_log`; intelligence→Postgres `ai.*` + **pgvector(HNSW)**; lifecycle→Postgres `lifecycle.*`+`support.*`; notifications→Postgres delivery-state + S3. Shared **infra** (not schemas): Redis, MSK, S3. Cross-service data only via gRPC (sync) or Kafka (async). Full DDL: `TECH/01`. |
| **Message broker / event bus** | **Amazon MSK (Kafka)** + Glue Schema Registry (Avro). Topic `<domain>.<entity>.<event>.vN`; **partition key = `workspace_id`**; raw + Decision-Log topics retained **∞** (tiered→S3, replayable); transient 30–90d. Phase 0–1 MSK Serverless + **transactional outbox**; Phase 2 provisioned MSK + **Debezium CDC**. DLQ + replay per consumer. Topic catalog: `../technical-requirements.md` §8.3. |
| **API-gateway flow** | Clients → `api-gateway` (tRPC/HTTPS + SSE/WS) **only** → authN + tenancy + RBAC/ABAC + rate-limit → **gRPC fan-out** to services. No business logic at the edge. MCP server co-located (shares auth/tenancy/rate-limit). |
| **Sync vs async** | **gRPC (sync)** only at a request/response boundary where the caller blocks on the answer (dashboard read, metric lookup, AI-chat tool calls). **Kafka (async)** for state propagation, fan-out, eventual consistency (ingestion→analytics→intelligence). **Default async.** |
| **CQRS / Event Sourcing** | **CQRS yes** — writes → Postgres OLTP + emit events; reads → ClickHouse MVs + Redis (separate read model). **Event-sourcing pragmatic/partial** — the Kafka log + S3 raw archive is the event store for the analytical side (materializations rebuildable by replay); the Decision Log is an append-then-update ledger. OLTP product state is NOT event-sourced (Postgres is the system of record). |
| **Caching** | Redis cache-aside, **workspace-scoped keys**, mandatory TTL, invalidate-on-write (api-gateway consumes `analytics.metrics.daily_materialized.v1` to bust hot keys). Serves cached-dashboard p95<500ms + is a cost lever. Stampede protection. (`caching-strategy`.) |
| **Vector DB / Memory** | **pgvector(HNSW) inside Postgres — no separate vector DB.** Memory = Brand Fingerprint (16-dim) + condition→outcome pairs + Decision Log + seasonal codebook + segment memory. (`TECH/05`.) Knowledge graph = §6 forward item. |
| **Data lake / warehouse** | **Lakehouse-lite:** S3 raw = the lake (immutable, replayable source of truth); ClickHouse = the warehouse/OLAP; Postgres = OLTP + 90-day hot mirror. No Snowflake/BigQuery (per-query billing fights %-GMV). |
| **ML pipeline** | Modular in `intelligence-service`: monthly batch training (flag MAPE>40%), batch+real-time inference, features = ClickHouse aggregates + a feature table (lightweight store now), model registry/experiment-tracking = model versions in Postgres + the `llm-evals` per-tier gate, feedback loop = condition→outcome memory + 7d/30d attribution. Formal feature store / MLflow = §6 deferred. |
| **Workflow orchestration** | In-service: Kafka consumers + EventBridge Scheduler (daily tick, rollups) + state machines + transactional outbox. **No separate orchestrator yet**; durable workflow engine = §6 Phase-3 trigger. |
| **Observability** | OTel → CloudWatch/X-Ray (ADOT exporter) + Sentry + PostHog + OpenSearch. One correlation ID HTTP→gRPC→Kafka→LLM. SLO error-budget policy + burn-rate alerts. (`observability`, `TECH/09`.) |
| **Security / tenancy** | Supabase Auth (JWT). **RBAC + ABAC**: 5 roles (viewer<analyst<agency<operator<owner) + ABAC (per-action approval matrix, feature flags, agency per-brand scoping, action caps, auto-execute policies). Enforced at **4 layers** (JWT → service assertion → Postgres RLS + ClickHouse query-gateway → Kafka envelope) + MCP scopes. KMS envelope encryption. Compliance engine (`TECH/16`). |
| **Multi-region** | ap-south-1 only Phase 0–3 (DPDP in-region by default). Phase 4 multi-region for UAE/GCC/EU residency keyed off `workspace.home_region`; RegionAdapter abstracts behavior → infra change, not a fork. |
| **LLM access** | All LLM calls go through the **LiteLLM gateway** (self-host on EKS, ap-south-1): model-agnostic routed policy (cheapest model passing the tier eval; Claude frontier default, swappable), per-workspace virtual-key budgets, fallback, semantic cache. Backend (Bedrock vs native direct) deferred + reversible behind the gateway. (`llm-gateway`, `TECH/12`.) |
| **DevOps** | Turborepo; GitHub Actions → ECR → ArgoCD (services) + EAS (mobile); AWS CDK; Fargate → EKS+Karpenter at Phase 2; progressive delivery (flags + canary + per-brand graduation); `version-upgrade-policy` cadence. |

---

## 2. Service catalog

| # | Service | Runtime | One-line role | Owner |
|---|---|---|---|---|
| 1 | `api-gateway` | TS/Fastify | BFF + MCP; the only front door; auth/tenancy/rate-limit/gRPC-fan-out | Vikram |
| 2 | `core-service` | TS/Fastify | system of record: orgs/users/RBAC/costs/goals/integrations-registry/consent/audit/billing | Vikram |
| 3 | `ingestion-service` | Python | ingest + raw-preserve + canonicalize + integration health (connector framework) | Maya |
| 4 | `analytics-service` | Python | canonical facts + the deterministic metric engine + RFM/LTV/attribution + Decision-Log writer | Maya |
| 5 | `intelligence-service` | Python | Memory Layer + 15 agents + anomaly/forecasts + daily tick + LLM orchestration (via gateway) | Maya |
| 6 | `lifecycle-service` | Node+Python | execution arm: audience builder + channel routers + AI calling + compliance engine + inbox | Maya/Vikram |
| 7 | `notifications-service` | TS | delivery: Morning Brief assembly+push + alerts + digests + exports + outbound webhooks | Vikram |
| 8 | `web` | Next.js 16 | operator workbench (presentation only) | Ananya |
| 9 | `mobile` | Expo 56 | Morning Brief primary surface (presentation only) | Karan |
| — | LiteLLM gateway | infra (EKS) | model-agnostic LLM routing layer (runtime of paradigm 3/4) | Maya/Jatin |

---

## 3. Per-service deep-dive (the nine dimensions)

### 3.1 `api-gateway`
- **Responsibilities:** authN, `workspace_id` tenancy, RBAC/ABAC, rate-limit, tRPC termination, SSE/WS streaming, MCP server, gRPC fan-out.
- **Boundary/ownership:** owns the edge contract (tRPC AppRouter) + MCP tool surface; **no domain data**; the only client-reachable service.
- **Internal modules:** `auth` · `tenancy` · `rbac-abac` · `rate-limit` (Redis) · `trpc-routers` (thin) · `mcp-server` (proto-derived tools + Decision-Log middleware) · `grpc-clients` · `sse-ws` · `cache-invalidator`.
- **Communication:** ⬅ web/mobile (tRPC), agents/partners (MCP) · ➡ all services (gRPC). Subscribes `analytics.metrics.daily_materialized.v1`.
- **Data/event flow:** stateless relay; Redis for sessions/rate-limit/hot-cache; emits no domain events.
- **Scale/deploy:** stateless → horizontal autoscale behind ALB; busiest tier; `edge` Phase 0–1 → own service Phase 2.
- **Security/tenancy:** **the policy enforcement point** — JWT claims → gRPC metadata; rejects cross-tenant/unauthorized before any service is hit; MCP tools scoped (read-only default; write needs Owner/Operator).
- **Real-time:** SSE/WS for chat streaming + live dashboards; sub-second.
- **Failure/retry:** gRPC circuit breakers + timeouts; degrade to cached reads on downstream outage; WAF + rate-limit; idempotency on mutations.

### 3.2 `core-service`
- **Responsibilities:** tenant identity + settings + money config + governance (orgs/workspaces/users/roles, cost setup, goals, integrations registry, consent primitive, audit log, billing/metering).
- **Boundary/ownership:** owns `core/billing/audit/consent` + encrypted credential ARNs; authority on "who/what/how-much."
- **Internal modules:** `workspaces` · `members-rbac` · `integrations` (registry + OAuth state + KMS credential wrapper) · `costs-goals` · `consent` · `billing-metering` (realized-GMV meter, invoices, CM2 guardrail — `TECH/15`) · `audit`.
- **Communication:** ⬅ api-gateway (gRPC); ingestion reads credential ARNs · consumes `integrations.payments.v1` (billing) · emits `settings_changed` + audit events.
- **Data/event flow:** OLTP writes; `settings_changed` → analytics recompute; audit on every mutation (WORM — `audit-log-immutability`).
- **Scale/deploy:** low-throughput/high-integrity; `edge`; modest scaling.
- **Security/tenancy:** holds the most sensitive data (credentials→KMS, ARN-only; consent; billing); RLS everywhere; secrets rotation (`security-baseline`).
- **Real-time:** request/response; consent/settings changes propagate via Kafka.
- **Failure/retry:** transactional writes + outbox (no dual-write loss); credential reads fail-closed.

### 3.3 `ingestion-service`
- **Responsibilities:** real-time + batch ingest, raw preservation, canonicalization, integration health (the founder's layers 1–2). Backfill==live (window only). Independently extensible (new connector ≠ touch others). (`TECH/02`, `integration-connectors`.)
- **Boundary/ownership:** owns the connector code path + ClickHouse `raw_*` + S3 raw + sync watermarks.
- **Internal modules:** `connector-base` (ABC) + per-provider impls · `auth` (OAuth/refresh) · `scheduler` (EventBridge) · `webhook-receiver` (signature-validated) · `canonicalizer` · `raw-archiver` (S3+CH) · `health` · `dlq-replay`.
- **Communication:** ⬅ provider APIs/webhooks; credential ARNs from core · ➡ emits `integrations.*.v1` (orders/line_items/customers/products/refunds/ads_insights/campaigns/shipments/shipment_events/payments) + `integrations.sync.completed/failed/dlq.v1`.
- **Data/event flow:** each record → **3–4 sinks** (S3 raw + CH raw + Kafka canonical + Phase-0–1 Postgres 90-day mirror); idempotent UPSERT on payload hash; per-connector late-data window.
- **Scale/deploy:** most independently scalable + bursty (backfills/webhook storms) — diverging scaling profile is a reason it splits at Phase 2; per-connector concurrency caps.
- **Security/tenancy:** `workspace_id` on every raw row+event; tokens never logged; webhook signatures validated.
- **Real-time:** webhooks near-real-time (orders 5–15 min); polling per type; streaming where supported.
- **Failure/retry:** backoff + per-vendor rate-limit respect; **DLQ + replay** for poison payloads; watermark resume (no loss on restart); health→degraded + alert on staleness (P0 >60 min).

### 3.4 `analytics-service`
- **Responsibilities:** normalization→canonical + analytics/metrics (layers 3–4) — ClickHouse materializations, the deterministic metric engine (registry, TS↔Python parity, per-SKU GST), RFM, customer states, LTV, attribution, regional math; **the Decision-Log writer**. (`TECH/03`, `metric-engine`.)
- **Boundary/ownership:** owns ClickHouse canonical+derived + `ai.decision_log`; the single source of every number.
- **Internal modules:** `metric_engine` (Path A materialized + Path B live) · `materialization` (MVs + scheduled rollups; `order_costs`) · `customer` (NAC/RFM/churn/LTV) · `attribution` (placed/realized/incremental) · `regional` · `decision_log` (writer + 7d/30d outcome jobs).
- **Communication:** ⬅ consumes `integrations.*.v1`, `settings_changed`; serves metric reads (gRPC) · ➡ emits `analytics.metrics.daily_materialized.v1`, `analytics.customer_state.changed.v1`.
- **Data/event flow:** CQRS read-model builder — events → materialize → emit "materialized" → triggers cache-bust + the intelligence tick.
- **Scale/deploy:** compute-heavy (billion-row scans); scales with data volume; `data` Phase 0–1.
- **Security/tenancy:** all queries through the **ClickHouse query gateway** (rejects unscoped); LLMs never write here.
- **Real-time:** hybrid — MVs on INSERT (near-real-time) + scheduled rollups (join-heavy) + hourly Path-A for Sale/Event Mode.
- **Failure/retry:** idempotent consumers (envelope key + ReplacingMergeTree dedup); rebuildable by replay; metric-parity CI gate; Decision-Log write availability >99.99%; data-quality gate before "authoritative" (`data-quality`).

### 3.5 `intelligence-service`
- **Responsibilities:** prediction + memory + agentic (layers 5–7) — Memory Layer, 15 agents, anomaly, forecasts, the daily tick, LLM orchestration via the gateway, internal MCP tools. (`TECH/05`, `TECH/14`, `agentic-design`.)
- **Boundary/ownership:** owns `ai.*` + pgvector; decides what to do; never invents metric numbers (reads them from analytics).
- **Internal modules:** `memory` (Brand Fingerprint, condition→outcome, cross-brand k≥5, seasonal codebook, segment memory) · `agents` (`_base` + aicmo/aicoo/aicfo + AI-CX) · `forecast` (Prophet/PyMC-Marketing/isotonic/Kaplan-Meier) · `anomaly` (z-score + Isolation Forest) · `chat` (tool-use) · `orchestration` (`daily_tick`, `morning_brief`) · `mcp-tools` · `llm-client` (→ gateway).
- **Communication:** ⬅ consumes `analytics.metrics.daily_materialized.v1`, `customer_state.changed.v1`; queries analytics (gRPC); calls the **LiteLLM gateway** · ➡ emits `intelligence.insight.generated/anomaly.detected/action.recommended/decision.logged.v1`.
- **Data/event flow:** the daily tick (§5 Flow B); a Decision-Log row per recommendation; condition→outcome updated by 7d/30d jobs (feedback loop).
- **Scale/deploy:** bursty agent fan-out → Karpenter bin-packing; `data` Phase 0–1; heaviest LLM/ML consumer; per-workspace LLM budgets via gateway.
- **Security/tenancy:** PII redaction before the gateway; memory workspace-scoped (no cross-brand leak; benchmarks k≥5); prompt-injection defense on agent inputs (`prompt-injection-defense`).
- **Real-time:** batch daily tick is the heartbeat; real-time inference for chat + anomaly; Sale/Event Mode higher cadence.
- **Failure/retry:** the **07:20 IST Morning Brief SLO** is sacred — gateway fallback chain + degrade to SQL+ML brief if frontier stalls; agents recommendation-only until graduated; model swaps eval-gated (`llm-evals`).

### 3.6 `lifecycle-service`
- **Responsibilities:** the execution arm (revenue + future autonomous actions) — Audience Builder (the single primitive), channel routers, AI calling, compliance engine, inbound inbox (Phase 3), recovered-revenue attribution. (`TECH/11`, `lifecycle-revenue-layer`.)
- **Boundary/ownership:** owns `lifecycle.*`+`support.*`; the only service that **acts on customers**.
- **Internal modules:** `orchestration` (Node: BuildAudience/TriggerOutreach/LaunchCampaign) · `audience` (Python: daily RFM, 11 segments) · `routers` (call/whatsapp/email/sms/ad-audience) · `compliance` (calling hours, DLT, NCPR/DND, consent re-check, frequency caps — hard-coded, pre-send) · `inbox` · `attribution` (7d/30d → Decision Log).
- **Communication:** ⬅ consumes `customer_state.changed.v1`, `integrations.shipments.v1`; calls gateway (personalization) + external channel providers · ➡ emits `lifecycle.outreach.completed/recovered_revenue.attributed/support.ticket.*`.
- **Data/event flow:** approved Decision-Log action → audience (frozen at trigger) → compliance gate → route → execute → attribute back into the same Decision-Log row.
- **Scale/deploy:** **Phase-2 build**; spiky (campaign sends); per-channel/vendor rate-limited; workers scale independently.
- **Security/tenancy:** highest-risk (money-affecting + customer-facing) — auto-execute caps, Owner kill switch (60s), consent per send, `agentic-actions-auditor` + `prompt-injection-defense`.
- **Real-time:** trigger journeys near-real-time; calling-hours gated at the **queue** level (can't fire outside 9am–9pm).
- **Failure/retry:** every action idempotent + Decision-Log'd; partial-reversibility (stop future sends); auto-revert to recommend-only on reversal/error breach; provider failure → retry/fallback channel.

### 3.7 `notifications-service`
- **Responsibilities:** the delivery layer — Morning Brief assembly + push (07:00–09:00 IST), alerts, Evening Pulse, weekly/monthly digests, exports, outbound webhooks. (`TECH/08`.) Informs the **operator** (vs lifecycle → the customer).
- **Boundary/ownership:** owns delivery state + push tokens; S3 for exports.
- **Internal modules:** `brief-assembler` · `alert-engine` · `digest-scheduler` · `push` (Expo APNS/FCM) · `exports` · `webhooks-outbound`.
- **Communication:** ⬅ consumes `intelligence.insight.generated/anomaly.detected.v1`, `analytics.metrics.daily_materialized.v1` · ➡ Expo Push; emits `notifications.digest.sent/alert.fired.v1`.
- **Data/event flow:** event-triggered (insight/anomaly → alert/push) + scheduled (digests).
- **Scale/deploy:** moderate; spikes in the 07:00–09:00 IST push window; `edge` early.
- **Security/tenancy:** per-workspace delivery; **no PII in push payloads** (deep-link, fetch-on-open); consent-respecting.
- **Real-time:** the push window is SLO-critical; alerts near-real-time.
- **Failure/retry:** Expo receipt handling + retry; idempotent sends (no duplicate pushes); dead-token cleanup.

### 3.8 `web` & 3.9 `mobile` (clients)
- **Responsibilities:** presentation only; web = operator workbench (shadcn+Visx; Magic UI scoped to marketing/onboarding/delight), mobile = Morning Brief primary + chat/approvals.
- **Boundary:** no business logic; talk to api-gateway via tRPC only.
- **Comms/real-time:** tRPC + SSE/WS (live dashboards, chat streaming); mobile push.
- **Scale/deploy:** CDN/edge (web, Amplify→EKS); EAS (mobile, OTA vs store-review).
- **Security:** HttpOnly cookies (web), secure-store + cert pinning + MASVS (mobile).
- **Failure/retry:** offline-first on mobile (cached reads → optimistic queue); request-ID on error UI.

### 3.10 LiteLLM gateway (infra)
Model-agnostic routing layer; 2+ stateless replicas behind ALB on EKS (ap-south-1); per-workspace virtual-key budgets; routed policy tiers (small/frontier) → cheapest model passing the eval; fallback chain; semantic cache (Redis). Failure → fallback model → degrade. (`llm-gateway`.)

---

## 4. Cross-service communication matrix

| From → To | Mechanism | What / topic |
|---|---|---|
| web/mobile → api-gateway | tRPC (+SSE/WS) | all client traffic |
| agents/partners → api-gateway | MCP | read tools + action tools (write tools auto-write Decision Log) |
| api-gateway → any service | gRPC | request/response (reads, mutations) |
| ingestion → analytics/intelligence/lifecycle/core | Kafka | `integrations.*.v1` |
| analytics → intelligence/notifications/api-gateway | Kafka | `analytics.metrics.daily_materialized.v1`, `customer_state.changed.v1` |
| intelligence → notifications/analytics/audit | Kafka | `intelligence.insight.generated/anomaly.detected/action.recommended/decision.logged.v1` |
| lifecycle → analytics/intelligence | Kafka | `lifecycle.outreach.completed/recovered_revenue.attributed`, `support.ticket.*` |
| core → analytics/billing | Kafka | `settings_changed`; consumes `integrations.payments.v1` |
| ingestion → core/notifications | Kafka | `integrations.sync.completed/failed/dlq.v1` |
| intelligence/lifecycle → LiteLLM gateway | HTTPS (in-cluster) | all LLM calls |
| any service → Redis / S3 / MSK | client SDK | cache / archive / events (shared infra, not shared schemas) |

---

## 5. End-to-end flows

- **A — Onboarding & ingestion:** core registers integration + KMS-encrypts credentials → ingestion authenticates, backfills + subscribes webhooks → canonicalizes → fans to S3+CH+Kafka(+90-day mirror) → analytics materializes canonical facts + `order_costs` → "estimated until ≥80% SKU-cost coverage" (data-quality gate) → ingestion health; notifications alerts on staleness.
- **B — Daily heartbeat → Morning Brief (SLO-critical):** 06:55 freshness → 07:00 Brand Fingerprint (SQL+numpy→pgvector) → 07:05 memory HNSW k-NN → 07:10 15 agents parallel (Decision-Log row each, written by analytics) → 07:15 frontier synthesis via gateway → `insight.generated.v1` → notifications assembles + pushes by **07:20 IST (>99.5%)**.
- **C — Approve → execute → attribute (the moat loop):** operator Approve (mobile→tRPC→gateway) → Decision-Log row `approved` → lifecycle: build audience (once) → compliance gate (consent+DLT+9–9+caps, pre-send) → route per customer → personalize via gateway → execute → `outreach.completed.v1` → analytics/lifecycle attribute placed→realized→recovered at 7d/30d back into the same row + condition→outcome memory → next recommendation improves.
- **D — NL query / AI chat (read path):** question (mobile/web→tRPC/WS→gateway→gRPC `IntelligenceService.Chat`) → intelligence uses Claude tool-use over deterministic metric tools (≤5 calls) — LLM orchestrates, **numbers come from analytics, never invented** → streamed back with formulas + next action.
- **E — Auto-execute (Phase 3, guardrailed):** enabled action class + confidence ≥ threshold + caps/consent/policy/freshness pass → lifecycle executes → Decision Log + `ai.auto_execute_log` → notifications shows it with Reverse → reversal/error breach → auto-revert to recommend-only; Owner kill switch pauses all in 60s.

> The **Decision Log is the spine of every flow** (condition→recommendation→response→execution→reversal→7d/30d outcome, ∞-retained); `workspace_id` rides every hop; Kafka's ∞ retention makes every materialization rebuildable (also the migration/DR story).

---

## 6. Forward extensions (deferred until trigger — build the seam now, the heavy system later)

| Extension | Today (in canon) | Adopt when (trigger) |
|---|---|---|
| **Knowledge graph / entity relationships** | pgvector + relational (condition→outcome, FKs) + identity-resolution in analytics | Multi-hop relationship queries prove out (e.g. creative→cohort→RTO chains). Add Neptune/Neo4j only then; keep entity IDs+relationships in Postgres now. Phase 3+. |
| **Feature store + formal MLOps (Feast/MLflow)** | ClickHouse aggregates as features + model versions in Postgres + `llm-evals` gate | Model count / training cadence justify the platform ops. Phase 3. Don't pay MLOps cost for ~6 models. |
| **Durable workflow engine (Temporal / Step Functions)** | Event-driven + outbox + state machines + EventBridge | Long-running sagas (multi-step auto-execute, complex onboarding, reversals) get hard to reason about as raw event chains. Phase 3 trigger. |

Same discipline as `version-upgrade-policy` + TECH/00: build the invariant/seam day-one, graduate the heavy layer only when its trigger fires.

---

## 7. Service-readiness DoD (every service, before it's "production")

A service is ready only when it: is DDD-structured by bounded context (no `controllers/`); owns its own schema (no cross-service DB reads); enforces `workspace_id` at every layer it touches; declares `@paradigm` on any compute path; uses minor-units money; emits/consumes events idempotently (envelope key + dedup) with a DLQ; exposes the 4 health probes (liveness/readiness/startup/deep); is trace-instrumented end-to-end (correlation ID); has a runbook (`blueprints/runbook.md`) + an SLO with an error budget; degrades gracefully on a dependency outage; has a reversibility/rollback path; passes its contract tests (`buf breaking` / Pact / Zod / MCP-schema); and **ships with its own CI/CD pipeline from day one** — a `turbo --affected`-aware GitHub Actions workflow + Dockerfile + its **own ECR image** + its **own ArgoCD Application** (base + staging/production overlays) + canary + auto-rollback, so the service deploys *itself* (only-the-changed-service) and is never part of a deploy-all monorepo pipeline. (Composes the global DoD in `../technical-requirements.md` §25; mechanism in `devops-aws` §Selective deployment.)

---

## Appendix A — Per-service data ownership & key tables

Every store has exactly one **writer** service. No service reads another's schema — cross-service data is gRPC (sync) or Kafka (async). **Full DDL lives in `TECH/01`** (Postgres + ClickHouse); this is the ownership map + the load-bearing tables.

| Service | Store(s) it WRITES | Key tables / objects |
|---|---|---|
| `core-service` | Postgres `core`, `billing`, `audit`, `consent` | `core.organisations`, `core.workspaces`, `core.workspace_members`, `core.integrations` (credential_secret_arn only), `core.oauth_states`, `core.product_cogs`, `core.cost_settings`, `core.goals` · `billing.gmv_meter`, `billing.invoices`, `billing.usage_passthrough`, `billing.plan` · `audit.audit_log` (WORM, 7y) · `consent` primitive |
| `ingestion-service` | ClickHouse `raw_*` · S3 raw archive · (Phase 0–1) Postgres 90-day mirror · watermarks | `raw_orders/customers/products/shipments/shipment_events/refunds/ads_insights/campaigns` (ZSTD + SHA-256 hash); S3 `raw/{workspace_id}/{provider}/{date}/…`; `integration.watermarks` (JSONB on `core.integrations`, written via core) |
| `analytics-service` | ClickHouse canonical + derived · Postgres `ai.decision_log` | canonical: `orders`, `line_items`, `customers`, `products`, `refunds`, `shipments`, `shipment_events`, `campaigns`, `campaign_insights_daily`, `order_costs` · derived: `daily_metrics` (master), `customer_states`, `cohort_aggregates`, `first_product_attribution`, `customer_lifetime_value`, `pincode_reliability`, `festival_lift_factors`, `support_daily`, `lifecycle_outreach_daily` · **`ai.decision_log`** (the moat — analytics is its writer) |
| `intelligence-service` | Postgres `ai.*` + **pgvector** | `ai.brand_fingerprint` (vector(16), HNSW), `ai.condition_outcome` (HNSW), `ai.cross_brand_pattern` (k≥5), `ai.insights`, `ai.forecasts`, `ai.forecast_accuracy`, `ai.anomalies`, `ai.workspace_llm_budget`, `ai.auto_execute_policies`, `ai.auto_execute_log` |
| `lifecycle-service` | Postgres `lifecycle.*`, `support.*` | `lifecycle.audience`, `lifecycle.audience_member` (frozen rfm_score_snapshot + assigned_channel), `lifecycle.outreach`, `lifecycle.call`, `lifecycle.rfm_score`, `lifecycle.consent_event` (append-only), `lifecycle.customer_consent_current` · `support.tickets`, `support.messages` |
| `notifications-service` | Postgres (delivery state) · S3 (exports) | `notifications.deliveries`, `notifications.push_tokens` (`mobile_push_tokens`), `notifications.digests`; S3 `exports/{workspace_id}/…` |
| `api-gateway` | — (stateless) | Redis only: sessions, rate-limit counters, idempotency keys, hot-metric cache (all `workspace_id`-prefixed) |
| shared infra | Redis · S3 · MSK | not a schema — every key/path/event carries `workspace_id` |

**Cross-store sync (Phase 2):** Debezium CDC mirrors the dual-store tables Postgres→ClickHouse. **Replay:** any ClickHouse materialization is rebuildable from the ∞-retained Kafka raw topics + S3 archive.

---

## Appendix B — Kafka topic catalog with payload contracts

**Standard envelope (every event):** `event_id` (uuid) · `event_type` · `workspace_id` (**partition key**) · `occurred_at` · `produced_at` · `producer_service` · `trace_id` (correlation) · `schema_version` · `idempotency_key` · `payload`. Avro in `protos/events/`, registered with Glue Schema Registry. Consumers dedup on `idempotency_key` + ClickHouse `version`.

| Topic | Producer | Consumers | Retention | Payload contract (key fields) |
|---|---|---|---|---|
| `integrations.orders.v1` | ingestion | analytics, intelligence | ∞ | order_id, customer_ref, placed_at, status, payment_method (cod/prepaid), currency_code, total_minor, discount_minor, line_item_refs[], channel, region |
| `integrations.line_items.v1` | ingestion | analytics | ∞ | order_id, sku, product_id, variant_id, qty, unit_price_minor, tax_slab, discount_minor |
| `integrations.customers.v1` | ingestion | analytics, intelligence | ∞ | customer_id, email_hash, phone_hash, first_seen_at, region, pincode, consent_refs[] |
| `integrations.products.v1` | ingestion | analytics | ∞ | product_id, variant_id, sku, category, tax_slab, price_minor, inventory_qty |
| `integrations.refunds.v1` | ingestion | analytics, intelligence | ∞ | refund_id, order_id, amount_minor, reason, refunded_at |
| `integrations.ads_insights.v1` | ingestion | analytics, intelligence | ∞ | platform, campaign_id, adset_id, ad_id, date, spend_minor, impressions, clicks, conversions, attributed_revenue_minor |
| `integrations.campaigns.v1` | ingestion | analytics, intelligence | ∞ | platform, campaign_id, name, objective, classification (acquisition/retention/brand/…), status |
| `integrations.shipments.v1` | ingestion | analytics, intelligence, lifecycle | ∞ | shipment_id, order_id, courier, status, pincode, cod_flag, shipped_at |
| `integrations.shipment_events.v1` | ingestion | analytics, intelligence, lifecycle | ∞ | shipment_id, event_type (ndr/rto/delivered/…), occurred_at, attempt_no, reason |
| `integrations.payments.v1` | ingestion | analytics, intelligence, core(billing) | ∞ | payment_id, order_id, method, status, amount_minor, fee_minor, settled_at |
| `integrations.sync.completed.v1` / `.failed.v1` | ingestion | core, notifications | 30–90d | integration_id, provider, window, records, lag_seconds, error? |
| `integrations.dlq.v1` | ingestion | core, notifications | 30–90d | source_topic, raw_payload_ref(S3), error, attempts |
| `core.settings_changed.v1` | core | analytics | 30–90d | what (cost_settings/goals/region/…), changed_by, effective_from |
| `analytics.metrics.daily_materialized.v1` | analytics | intelligence, notifications, api-gateway(cache) | 30–90d | date, metric_keys[], dimensions, freshness_at |
| `analytics.customer_state.changed.v1` | analytics | intelligence, lifecycle | 30–90d | customer_id, old_state, new_state (new/returning/reactivated/at-risk/churned), rfm_segment |
| `intelligence.insight.generated.v1` | intelligence | notifications | 30–90d | insight_id, decision_log_id, title, priority_score, expected_cm2_minor, confidence |
| `intelligence.anomaly.detected.v1` | intelligence | notifications | 30–90d | anomaly_id, metric, magnitude, baseline, severity, root_cause? |
| `intelligence.action.recommended.v1` | intelligence | analytics, notifications, audit | ∞ | decision_log_id, agent_name, action_type, proposed_action, confidence, risk_level, reversibility |
| `intelligence.action.executed.v1` | intelligence/lifecycle | analytics, notifications, audit | ∞ | decision_log_id, executed_action, channel, provider_ref, executed_at, auto_executed? |
| `intelligence.decision.logged.v1` | intelligence/lifecycle | analytics, notifications, audit | **∞ (the moat)** | the full Decision-Log row delta (status transition + fields) |
| `lifecycle.outreach.completed.v1` | lifecycle | analytics, intelligence | ∞ | outreach_id, decision_log_id, audience_id, channel, sent/delivered/replied counts, cost_minor |
| `lifecycle.recovered_revenue.attributed.v1` | lifecycle | analytics, intelligence | ∞ | decision_log_id, window (7d/30d), recovered_revenue_minor, recovered_cm2_minor |
| `support.ticket.created.v1` / `.resolved.v1` | lifecycle | analytics, intelligence | ∞ | ticket_id, decision_log_id, channel, ticket_type, resolution_type?, csat?, support_protected_cm2_minor? |
| `notifications.digest.sent.v1` / `.alert.fired.v1` | notifications | audit | 30–90d | digest_id/alert_id, kind, channel, delivered_at, recipient_role |

> Convention recap: topic = `<domain>.<entity>.<event>.vN`; breaking change → `.v(n+1)` + dual-write window; backward-compatible additions stay in-version (new fields have defaults). `cdc.*` topics (Debezium) appear at Phase 2.

---

## Appendix C — Sequence diagrams (the two critical flows)

**Flow B — Daily tick → Morning Brief (SLO-critical: delivered by 07:20 IST, >99.5%)**
```
EventBridge   intelligence        analytics        LiteLLM-gw     notifications      mobile
    │ 06:55 tick   │                   │                │              │               │
    ├─────────────▶│ freshness check   │                │              │               │
    │              ├──gRPC GetMetrics──▶│ (today/MTD)    │              │               │
    │              │◀──daily_metrics────┤                │              │               │
    │ 07:00        ├─ build Brand Fingerprint → PG ai.brand_fingerprint (HNSW upsert)  │
    │ 07:05        ├─ memory query: HNSW k-NN on ai.condition_outcome                  │
    │ 07:10        ├─ 15 agents in parallel; each:                                     │
    │              │    • gRPC metric reads ─▶ analytics                               │
    │              │    • WRITE Decision-Log row (status=proposed) ─▶ analytics(ai.decision_log)
    │              │    • emit intelligence.action.recommended.v1 (Kafka)              │
    │ 07:15        ├─ assemble Top-3 → frontier synthesis ──▶│ (Claude default, cached)│
    │              │◀──────────── synthesized brief ─────────┤              │           │
    │              ├─ emit intelligence.insight.generated.v1 ──────────────▶│ (consume) │
    │ 07:00–09:00  │                   │                │     assemble brief├──push────▶│ open
    │              │                   │                │              │      (Expo)   │ (3-min)
  Fallback: if LiteLLM-gw stalls → fallback model in-chain; if still down → degrade to
  a SQL+ML brief (no frontier) so the 07:20 SLO still holds.
```

**Flow C — Approve → execute → attribute (the moat loop)**
```
mobile/web   api-gateway    analytics(DecisionLog)   lifecycle        provider      analytics/intel
   │ Approve     │                  │                    │               │              │
   ├──tRPC──────▶│ authZ+tenancy    │                    │               │              │
   │             ├──gRPC UpdateDecision(status=approved)─▶│ ai.decision_log row→approved│
   │             ├──emit intelligence.action.recommended? no → triggers lifecycle:      │
   │             │                  │   (consume customer_state / approved action)      │
   │             │                  │                    ├─ BuildAudience (once) → lifecycle.audience(_member frozen)
   │             │                  │                    ├─ COMPLIANCE ENGINE (pre-send):│
   │             │                  │                    │   consent re-check · DLT · NCPR/DND · 9am–9pm · freq-cap
   │             │                  │                    ├─ route per customer (call/WA/email)
   │             │                  │                    ├─ personalize via LiteLLM-gw   │
   │             │                  │                    ├──────────── send ────────────▶│ (channel)
   │             │                  │                    ├─ emit lifecycle.outreach.completed.v1
   │             │                  │  Decision-Log row→executed (executed_action)       │
   │  …7d/30d nightly (23:55)…       │                    ├─ attribute placed→realized→recovered
   │             │                  │                    ├─ emit lifecycle.recovered_revenue.attributed.v1
   │             │                  │◀── update SAME Decision-Log row: outcome_7d/30d, recovered_*_minor
   │             │                  │   intelligence: write ai.condition_outcome (feedback → next rec improves)
  Guardrails: every step idempotent + Decision-Log'd; partial-reversibility (stop future sends);
  Owner kill switch pauses all in 60s; reversal/error breach → auto-revert to recommend-only.
```

