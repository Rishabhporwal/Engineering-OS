# Brain — Technical Context (Agent Primer)

**Read this before writing code, designing a service, or reviewing a PR.** Every agent loads this at the start of every task. Condensed, load-bearing extract from `Requirements/BRAIN_TECHNICAL.md` (4,557 lines). When in doubt, the original document wins.

---

## Stack snapshot

| Layer | Locked choice |
|-------|--------------|
| **Web frontend** | Next.js 14+ (App Router) + React 18 + TypeScript |
| **Mobile** | React Native + Expo (PWA fallback for Phase 0–1; native via EAS Build Phase 1+) |
| **Node services** | Node 20 + Fastify + tRPC + Prisma + grpc-js + KafkaJS + Zod |
| **Python services** | Python 3.12 + FastAPI + grpcio + asyncpg + clickhouse-driver + aiokafka + httpx + structlog + Anthropic SDK |
| **API style (internal)** | gRPC + Protobuf via **buf** (single source of truth for all internal contracts AND MCP tool schemas) |
| **API style (external)** | tRPC (web/mobile ↔ api-gateway) |
| **OLTP** | Supabase Postgres (managed RDS, AWS) |
| **OLAP** | ClickHouse Cloud (or self-hosted on EKS via Altinity Operator) |
| **Streaming** | AWS MSK (Kafka) + Glue Schema Registry + Avro |
| **Cache** | ElastiCache Redis (cluster mode) |
| **Object storage** | S3 (encryption, versioning, lifecycle policies, cross-region replication Phase 4) |
| **Container orchestration** | EKS + Karpenter (spot autoscaling) + ArgoCD (GitOps) |
| **IaC** | AWS CDK (**TypeScript**) — *NOT Terraform, NOT Pulumi* |
| **Monorepo** | Turborepo (TS) + uv workspaces (Python) |
| **Package manager** | pnpm (TS) + uv (Python) |
| **CI/CD** | GitHub Actions (lint → typecheck → test → build → ECR push) → ArgoCD sync |
| **LLMs** | Claude **Sonnet 4.6** (synthesis) + Claude **Haiku 4.5** (bounded NL) |
| **Mobile build** | EAS Build + EAS Submit + EAS Update (OTA for JS-only) |

> Stack is **LOCKED.** Use [`tech-stack-evaluation`](../plugin-skills/tech-stack-evaluation/SKILL.md) *only* when adding a new layer not in the stack (e.g., picking the AI calling vendor — Bolna vs Vapi vs native).

---

## The 7 microservices

| # | Service | Lang | Owns |
|---|---------|------|------|
| 1 | `api-gateway` | TS | BFF: tRPC (web/mobile) + MCP server. Auth + multi-tenancy + rate limit live here. Fan-out via gRPC to internal services. |
| 2 | `core-service` | TS | Workspaces, users, integrations, settings, goals, costs, campaigns, festivals. OLTP write path. |
| 3 | `ingestion-service` | Python | Connectors (Shopify, Meta, Google, Shiprocket, Klaviyo, Razorpay, WooCommerce, …). OAuth, sync, canonicalize, produce to Kafka. |
| 4 | `analytics-service` | Python | ClickHouse query gateway. Materialized views. KPI computation. |
| 5 | `intelligence-service` | Python | The 15 AICMO/AICOO/AICFO agents. Daily tick 06:55–07:15 IST. Claude API calls. Memory Layer (pgvector). |
| 6 | `notifications-service` | TS | Email, SMS, push, in-app. WhatsApp via partner BSP. Templates + delivery + receipts. |
| 7 | `lifecycle-service` | Python | RFM scoring, audience builder, channel routers, AI calling, compliance engine, multi-channel inbox (Phase 3). |

**Communication model:** gRPC for synchronous request/reply. Kafka for asynchronous state changes. Services **never** call each other via REST.

**Language split discipline:** TypeScript for I/O-heavy (gateway, core, notifications, web). Python for analytics/ML/agents (ingestion, analytics, intelligence, lifecycle).

---

## Data layer — `workspace_id` is law

### Supabase Postgres (OLTP)
Schemas: `auth` (Supabase-managed), `core`, `notifications`, `ai`, `memory` (pgvector).

**Rules:**
- `workspace_id` is the **first column** of the primary key on every workspace-scoped table.
- **Row-Level Security (RLS) on every table.** Set `app.workspace_id` via `SET LOCAL` per request.
- **Every mutation endpoint** calls `requireRole(ctx, workspaceId, minimumRole)`. Role checks on read are optional; on write they are **mandatory**.
- OAuth tokens stored **AES-256-GCM** with per-brand key from AWS Secrets Manager. Plaintext tokens never in logs.
- Migrations via Prisma Migrate (TS) or Alembic (Python). **2 reviewers required** for migrations, proto changes, infra, and LLM-cost-impacting changes.
- Pooling: PgBouncer transaction mode (10K client → 200 backend connections).

### ClickHouse (OLAP)
Schemas: `raw.*` (infinite retention), `agg.*` (materialized aggregations).

**Rules:**
- Primary key ordering: `(workspace_id, date/event_timestamp, entity_id)` for fast range scans.
- Timestamps: `DateTime64(3, 'UTC')` or `DateTime64(3, 'Asia/Kolkata')` — **never ambiguous timezone**.
- Partition by month: `PARTITION BY toYYYYMM(date)`.
- `LowCardinality` codec for high-cardinality categorical fields (platform, status, payment_method).
- **Query gateway (`pylibs/brain_clickhouse`) rejects any query missing a `workspace_id =` predicate.**
- `max_execution_time = 30s` for dashboard reads. Queries scanning >100M rows without LIMIT are rejected.
- Cluster: 3 shards × 1 replica (Phase 0–1) → 6 shards (Phase 3).

### Redis (ElastiCache)
- Hot metric cache (60s TTL, ~99% hit rate target).
- Session cache (30 min TTL).
- Rate limits (sliding window, 70s TTL).
- Idempotency keys (24 h TTL).
- Cluster: 3 shards initially → 12.

### S3 lifecycle
- Raw payloads: 90 d → Glacier → delete 7 y.
- Exports: 30 d.
- Kafka tiered storage backend.
- Call recordings: 1 y, per-brand KMS key.
- Logical backups: 90 d.

---

## Kafka — async backbone

- **Platform:** AWS MSK + AWS Glue Schema Registry + Avro.
- **Naming:** `<domain>.<entity>.<event_type>.v<version>` (e.g., `integrations.orders.v1`, `intelligence.decision.logged.v1`).
- **Partition key:** **always `workspace_id`** → guarantees per-workspace ordering.
- **Retention:**
  - `integrations.*` — infinite (S3 tiered storage). Every downstream materialization is replayable.
  - `operations.*`, `notifications.*` — 30 days.
  - `intelligence.decision.logged.v1` — **forever**. This is the Decision Log; the moat.
- **Exactly-once:** Idempotent producer (`enable.idempotence=true`) + transactional consumer groups with offset commits in the **same Postgres transaction** as the side-effect.
- **Schema evolution:** backward-compatible by default. Breaking changes require new `.v2` topic + dual-publish window.

---

## AI / LLM layer

- **Primary:** Claude **Sonnet 4.6** for strategic synthesis (Morning Brief Synthesizer, multi-step reasoning).
- **Secondary:** Claude **Haiku 4.5** for narrow tasks, classification, bounded NL understanding.
- **Prompt caching:** Anthropic prompt caching is the single biggest cost lever — **enable for Brand Fingerprint queries, decision log context, repeated context vectors. Aim for ~30× reduction.**

### Cost-routed paradigm (the engineering invariant)

| Paradigm | Relative cost | When to use |
|----------|--------------|-------------|
| 1. **SQL** | 1 | Any deterministic computation over structured data. |
| 2. **ML (sklearn, Prophet, pgvector)** | ~100 | When patterns exist but rules don't. |
| 3. **Haiku** | ~1,000 | Bounded natural-language understanding (intent classification, summarization of one document). |
| 4. **Sonnet** | ~10,000 | Multi-step reasoning, planning, synthesis across many documents. |

**Enforcement:**
- Every code path declares `@paradigm("sql"|"ml"|"haiku"|"sonnet")` decorator.
- CI rejects PRs missing the decorator or with a wrong-paradigm declaration.
- Every PR passes the Q1–Q4 cost-routing audit (see [`cost-routing-paradigms`](../plugin-skills/cost-routing-paradigms/SKILL.md)).
- Per-brand token cap: **soft throttle at 70%** (lower-priority features pause), **hard throttle at 100%** (only critical-path LLM features). System never breaks; it gets quieter.

### Agentic design

15 specialist agents inside `intelligence-service`:

- **AICMO** sub-agents: Meta, Google, TikTok, Snap, Cross-Channel, Creative, Pricing, Festival.
- **AICOO** sub-agents: Logistics, Returns, Inventory, Marketplace.
- **AICFO** sub-agents: Conversion, Cashflow, Pricing-Margin.

**Daily tick:** 06:55–07:15 IST agent fan-out → 07:15 IST Sonnet synthesis → push delivered 07:00–09:00 IST.

**Auto-execute (Phase 3):** 8 reversible actions with kill switch + per-action spend caps + immutable Auto-Execute Log + 7d/30d outcome tracking.

---

## Security baseline (Shreya has VETO)

### Auth
- **Provider:** Supabase Auth (email/password + Google OAuth + Apple OAuth). SSO/SAML Phase 3.
- **Token storage:** HttpOnly cookies (XSS-immune). Refresh tokens server-side only.
- **JWT claims:** `sub`, `email`, `active_workspace_id`, `active_role`, `available_workspaces`, `exp`.
- **OAuth state:** 10-min TTL, single-use.

### Authorization
- **Roles (numeric hierarchy):** `readonly`(1) → `analyst`(2) → `agency`(3) → `operator`(4) → `owner`(5).
- **Standard guards** on every mutation endpoint: `requireWorkspaceMember()`, `requireRole()`, `requireFeature()`.

### Multi-tenancy enforced at 4 layers
1. JWT claim validation (`active_workspace_id`).
2. Service-side assertion (`request.workspace_id == metadata.workspace_id`).
3. Database RLS (Postgres) + query gateway (ClickHouse).
4. Kafka consumer asserts `workspace_id` from event payload.

### Input validation
- **Zod schemas** on every API input (tRPC + gRPC).
- Date range bounds: client-side reject > 2 y; server-side reject > 5 y.

### Encryption
- **At rest:** AES-256 (Postgres, ClickHouse, S3 with KMS-managed keys).
- **In transit:** TLS 1.2+ at ALB; **mTLS between services Phase 3** via App Mesh.
- **Sensitive payloads:** OAuth tokens AES-256-GCM with per-brand KMS key. Call recordings per-brand KMS key.

### Compliance gates
- **DPDP Act 2023:** Brain = Data Processor.
- **GDPR:** SCCs + sub-processor list. EU residency (`eu-central-1`) on Enterprise tier Phase 4.
- **CCPA:** Same as GDPR for CA residents.
- **SOC 2 Type II:** Phase 1 kickoff, 9–12 month timeline.
- **ISO 27001:** post-SOC 2.

### India compliance (P0 — any violation pages immediately)
- Calling hours 09:00–21:00 IST, **hard-coded at queue level**.
- Two-layer DND block: brand opt-out + TRAI NCPR.
- Disclosure ("this is an automated assistant") on every AI call.
- Recording consent offered; declined → call proceeds, no audio retained.
- DLT registration per brand per template.
- Max 1 Brain-driven call / customer / 48 h (Owner override for VIP only).

### API security
- **CSRF:** tRPC default. Explicit CSRF token for non-tRPC routes.
- **Rate limits:** user 1K rpm, workspace 5K rpm, AI Chat 50 msg/min. Redis sliding window.
- **Webhook validation:** HMAC (Shopify, Klaviyo), token (Shiprocket), signature (Razorpay, WooCommerce).

> **Shreya VETO** on any CRITICAL/HIGH security finding or India compliance violation.

---

## Observability

| Pillar | Tool | Notes |
|--------|------|-------|
| **Logs** | Fluent Bit → OpenSearch | Structured JSON. `request_id` + `workspace_id` + `trace_id` + `user_id` on every line. PII redaction at logger + Fluent Bit Lua script. 30 d in OpenSearch; S3 archive for longer. |
| **Metrics** | CloudWatch + custom | Request rate/latency p50/p95/p99, error rate per endpoint, Kafka consumer lag, Postgres query duration, ClickHouse query duration + bytes scanned, LLM token usage per workspace, auto-execute counts. |
| **Traces** | AWS X-Ray | Propagated via gRPC metadata + Kafka headers. 100% sample on errors, 5% on success in production. |
| **Errors** | Sentry | Error grouping, source map upload, release tracking. |
| **Product analytics** | PostHog | Feature usage, funnels, RUM Core Web Vitals. |

**Single correlation ID:** `request_id` + `trace_id` + `workspace_id` + `user_id` propagated end-to-end through HTTP headers, gRPC metadata, and Kafka envelope.

### Health checks
- `GET /health` — process responsive.
- `GET /health/ready` — checks Postgres, ClickHouse, Kafka.

### SLOs
- API p95 latency (dashboard reads) < **100 ms**.
- ClickHouse p95 query < **500 ms**.
- Service availability > **99.9%** monthly.
- Data freshness (integration lag) < **1 hour**.
- Morning Brief delivery < **20 min** from data pull.
- LLM error rate < **0.5%**.
- Auto-execute accuracy > **80%**.

### Alarms (CloudWatch → SNS → PagerDuty/Slack)
- Error rate >1% for 5 min → page.
- p95 latency >2 s for 5 min → page.
- Kafka consumer lag >10K msg for 10 min → page.
- Postgres connection pool exhaustion → page.
- ClickHouse query timeout >0.1% → page.
- LLM cost >1.5× monthly cap / 30 per day → page.
- Integration stale >1 h → page per workspace.
- **DND violation in calling → P0 page.**

---

## Testing strategy

- **Coverage mandate:** >70% on new features.
- **Layers:**
  - Unit: SQL, ML, metrics functions.
  - Integration: connector end-to-end (with synthetic + live credentials).
  - Contract: gRPC messages (`buf breaking`), tRPC schemas, MCP tool schemas (Pact).
  - E2E: Cypress (web), Detox (mobile).
  - Load: k6 (Phase 3+ at 5K RPS target).
- **Real-network smoke tests** — mandatory for PASS. In-memory tests mask real-network bugs.
- **Metric registry parity:** TS↔Python parity for the lowest-level metric definitions stored in `packages/lib-metrics/` + `pylibs/brain_metrics/`. If two parts of the system calculate the same metric differently, the system is broken.
- **Model validation:** LTV/forecasting models flag unreliable on MAPE >40% on held-out month.
- **Mutation testing:** Stryker (TS, Vitest runner) + mutmut (Python, pytest) for high-stakes paths (metric registry, India compliance engine, Decision Log).

---

## Reliability patterns

- **Idempotency:** Redis idempotency key cache (24 h TTL), lookup before processing mutations.
- **Rate limiting:** user 1K rpm / workspace 5K rpm / AI Chat 50 msg/min. Redis sliding window.
- **Pagination:** **Cursor only.** Offset is banned in prod paths. Date ranges > 90 d aggregated weekly server-side.
- **API versioning:** proto names + `.v1`; breaking changes → `.v2` (same file). Kafka topics include `.v1`/`.v2`. REST (if any, Phase 4) uses `/v1/workspace/{slug}/…`.
- **Graceful degradation:** LLM cap hit → SQL + ML paths continue; LLM-dependent features (Morning Brief, AI Chat, insights) queue or degrade.

---

## Infrastructure

**AWS-only.** All IaC via **AWS CDK (TypeScript)**. Stacks:
- `network-stack` (VPC, subnets, NAT, peering).
- `eks-stack` (EKS, Karpenter, ArgoCD bootstrap).
- `data-stack` (RDS/Supabase peering, ClickHouse, ElastiCache, S3).
- `streaming-stack` (MSK, Glue Schema Registry).
- `observability-stack` (CloudWatch, X-Ray, OpenSearch, Sentry IAM).
- `security-stack` (Secrets Manager, KMS keys per brand, WAF, Shield).

**Multi-region (Phase 4):** primary `ap-south-1` (India), secondary `us-east-1` (US/EU). Cross-region via DMS (Postgres async), ClickHouse native replication, MirrorMaker 2 (Kafka), S3 CRR.

**Environments:** `dev` (docker-compose local) → `staging` (EKS) → `production` (EKS).

**Mobile pipeline:** EAS Build → TestFlight + Play Internal → manual approval → EAS Submit. OTA via EAS Update for JS-only changes.

---

## Integrations

**Phase 1 commit (every connector follows the standard pattern):**

| Vendor | Auth | API | Webhooks |
|--------|------|-----|----------|
| **Shopify** | OAuth 2.0 (Partner app) | GraphQL Admin API 2025-01 | Yes |
| **Meta Ads** | OAuth 2.0 | Graph API v22.0 | No (poll) |
| **Google Ads** | OAuth 2.0 + PKCE + long-lived refresh | GAQL | No (poll) |
| **Shiprocket** | Credential-based | REST | Yes (token-validated) |
| **Klaviyo** | API key | REST v2023-10 | No (poll) |
| **Razorpay** | API key | REST | Yes (signature-validated) |
| **WooCommerce** | Consumer key/secret | REST v3 | Yes (HMAC-validated) |

**Standard connector pattern:**
1. `authenticate()` / `refresh_token()`
2. `list_resources()`
3. `sync(window)` — same code path for live (unbounded window) AND backfill (bounded window).
4. `receive_webhook()` with vendor-specific signature validation.
5. `canonicalize()` — normalize to Brain's internal schema.
6. `produce_to_kafka()` — emit to `integrations.<entity>.v1` partitioned by `workspace_id`.
7. `health_check()` — feeds the 1h-stale alert.

**Sync scheduling (EventBridge Scheduler):** Shopify 15m, Meta/Google 6h, Shiprocket 30m, Razorpay daily.

**Phase 2+ quality gradient:**
- **Green** (clean API): Salla, Zid, Amazon SP-API, Flipkart v3, Noon, BigBasket.
- **Yellow** (gated): Myntra, Ajio, Meesho, Namshi, Talabat.
- **Red** (no API): Nykaa, Blinkit, Zepto, Instamart, Ounass — Gmail OAuth + LLM PDF extraction workaround. UI disclaimer for Red.

---

## Definition of Done (composite — Tanvi and CTO Advisor both gate on this)

A change is **Done** only when **all** of these are true:

### Code
- [ ] All new code declares `@paradigm` decorator (TS) / `@paradigm(...)` (Python).
- [ ] Per-feature LLM token budget set (soft 80%, hard fail 100%).
- [ ] Idempotency keys cached for all write operations.
- [ ] Zod schema on every API input; server-side re-validation.
- [ ] All timestamps explicit (UTC or `Asia/Kolkata`); no ambiguity.
- [ ] `workspace_id` assertion in every gRPC handler.
- [ ] `requireRole(...)` on every mutation endpoint.
- [ ] Rate limit enforcement (endpoint-level or inherited from api-gateway).
- [ ] CloudWatch custom metrics + Sentry instrumentation present.

### Tests
- [ ] >70% coverage on the new code.
- [ ] Real-network smoke test passes.
- [ ] Contract tests (`buf breaking` for proto; Pact for service-to-service; Zod schema diff for tRPC; MCP tool schema diff).
- [ ] Mutation tests pass for high-stakes paths.

### Integrations (if applicable)
- [ ] Standard connector pattern followed.
- [ ] Tested with mock + live credentials (Red integrations: 1 h staleness alert).
- [ ] OAuth tokens AES-256-GCM with per-brand KMS key.
- [ ] Webhook signatures validated.

### Security (Shreya)
- [ ] No CRITICAL/HIGH findings in vulnerability scan.
- [ ] No India compliance violation (DLT, NCPR, DND, hours, GST).
- [ ] PII not in logs.
- [ ] Standard auth guards present and tested.

### Ops (Jatin)
- [ ] Health endpoints respond.
- [ ] Pre-handoff checklist (see [`operational-readiness`](../plugin-skills/operational-readiness/SKILL.md)) all green.
- [ ] Dashboard added/updated if a new metric is emitted.
- [ ] Alarm registered if a new SLO is implied.

### Process
- [ ] Decision Log entry written.
- [ ] Per-feature journal updated in `.engineering-os/memory/features/`.
- [ ] CTO Advisor final review attached.
- [ ] Founder approval recorded.

---

## Load-bearing conventions (forbidden anti-patterns)

These are *explicitly* called out in `BRAIN_TECHNICAL.md` and are caught at design review:

- ❌ "The email version of the audience builder" → build once; have email consume the single audience builder.
- ❌ "The call-specific consent flow" → extend the unified consent model.
- ❌ "A new notification service for SMS alerts" → extend the existing notification framework.
- ❌ "Per-channel customer profiles" → use the unified customer record with per-channel engagement scores.
- ❌ "Sequential DB queries in page layout" → use `Promise.all()` for parallel fetching.
- ❌ "OAuth token plaintext storage" → AES-256-GCM + per-brand key in Secrets Manager.
- ❌ "Role checks only on reads" → role checks must be on **every mutation endpoint**.
- ❌ "Hard-coded India economics in the metric engine" → use `RegionAdapter`; new region = implement the interface.
- ❌ Offset pagination in production paths → cursor only.
- ❌ Direct service-to-service REST → gRPC for sync, Kafka for async.

> **Quarterly audit:** the codebase is reviewed for anti-pattern drift. Refactoring time is allocated explicitly each quarter; it is **not optional**.

---

## Verification before completion (Iron Law #5)

Every "done"/"ready"/"tests pass"/"should work" claim runs a verification command and captures real output. See [`verification-before-completion`](../plugin-skills/verification-before-completion/SKILL.md).

A run is **not complete** until the agent posts:
1. The exact command(s) executed.
2. The actual output.
3. A line confirming the output matches the expected success criterion.

---

## When in doubt

1. **Re-read this primer.**
2. **Open `Requirements/BRAIN_TECHNICAL.md`** — source of truth; this is the curated summary.
3. **Open the relevant curated skill** (see [skill-mapping-matrix.md](skill-mapping-matrix.md)).
4. **Escalate to Aryan (Architect)** if it's an architectural call.
5. **Escalate to Shreya** for a security call.
6. **Escalate to CTO Advisor** if priorities conflict.
7. **Escalate to Founder/Rishabh** if the tech stack itself is being changed (ADR-001 update required).
