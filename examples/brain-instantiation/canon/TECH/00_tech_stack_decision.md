# TECH/00 — Tech Stack Decision & Phased Adoption

> **Status:** Authoritative architecture decision record (ADR-style).
> **Updated:** 2026-05-23
> **Companion:** `../technical-requirements.md` (the consolidated spec) + `../business-requirements.md` (source of truth).
> **Purpose:** Decide Brain's technology stack on the basis of the business (India-first DTC commerce OS, realized-GMV pricing, 25–35% RTO economics, daily intelligence loop, cost-routing margin discipline) **and** scalability — and define a **phased "start simple → scale into it" adoption path** so a small founding team does not pay Phase-4 operational cost on day one.

---

## 0. How to read this document

This document does three things:

1. **Locks the mature (target) stack** — what Brain runs at Phase 3–4 scale — with a one-line justification per layer tied to the business.
2. **Right-sizes the rollout** — what to actually build in Phase 0–1, with **explicit triggers** for when to graduate to the heavier option. The target architecture is correct; building all of it before there are 10 paying brands is the mistake this document prevents.
3. **Records the canonical resolutions** of inconsistencies found across the prior technical docs (money representation, role model, service boundaries, schema naming), so the consolidated spec and the TECH/ deep-dives agree.

The guiding principle (from `business-requirements.md` §0 and the cost-routing discipline): **every layer must earn its place against revenue, profit, risk, operator time, or compliance.** Infrastructure that only buys theoretical scale we do not yet have is deferred behind a trigger.

---

## 1. The business constraints that drive the stack

| Business reality (from `business-requirements.md` v1.1) | Technical consequence |
|---|---|
| Brain bills **% of realized/delivered GMV**, bundling all channels into one fee | Per-brand compute cost **must** stay far below the fee → the **cost-routing paradigm** (SQL ≫ ML ≫ Haiku ≫ Sonnet) is a structural requirement, not an optimization. |
| Honest CM2 over vanity ROAS; metrics must be auditable & reproducible | Deterministic **metric engine** with one definition per metric; **OLAP store** (ClickHouse) for billion-row aggregates; LLMs never produce numbers. |
| 25–35% COD RTO; pincode/courier/COD economics are the moat | First-class **time-series + analytical** workloads (RTO modelling, pincode reliability) → ClickHouse, not Postgres. |
| Decision Log is the compounding moat | Append-only event spine + immutable audit; **event-driven** architecture with replay. |
| Morning Brief is THE primary surface, delivered 06:55–09:00 IST | **Native mobile app** (push reliability, thumb-first); a tight daily batch loop with a hard SLO. |
| India-first, UAE/GCC sequenced; multi-region by architecture | **Region-adapter** pattern from day one; single AWS region (Mumbai) until Phase 4. |
| DPDP / PDPL / DLT / NCPR / 9am–9pm calling | **Compliance engine** + data residency in-region by default; PII minimization everywhere. |
| Small founding team, early-stage runway | **Polyglot monorepo** for code reuse; **managed services** over self-hosted; **consolidated deployment** early, split into microservices only when load/team size justifies. |

The single most important architectural invariant: **most decisions run at SQL/ML cost; LLMs enter only at the human-language boundary.** This is what makes %-of-GMV pricing survive. Every other choice serves it.

---

## 2. The locked target stack (Phase 3–4 mature state)

Each row is the **final** choice with its business justification. §3 then sequences the rollout.

### 2.1 Languages & repo

| Layer | Choice | Why |
|---|---|---|
| Monorepo | **Turborepo + pnpm** (TS) · **uv** workspace (Python) | One repo; shared types/contracts across web, mobile, Node, Python; cached incremental builds. |
| Edge/product language | **TypeScript (strict)** | End-to-end types web ↔ mobile ↔ api-gateway via tRPC; one language for all client + BFF code. |
| Data/ML/agent language | **Python 3.13+** | Ecosystem for analytics, Prophet/sklearn/PyMC-Marketing/statsmodels, ClickHouse + Kafka drivers, LLM-gateway client. |
| Contract codegen | **Buf** (protobuf → TS + Python) | Internal contracts are generated, never hand-written; cannot drift across the TS↔Python boundary. |

**Polyglot, not monolingual:** the product is half web/app (TS) and half data/ML (Python). Forcing one language would cripple one half. The monorepo + codegen makes the boundary safe.

### 2.2 Frontend & mobile

| Layer | Choice | Why |
|---|---|---|
| Web | **Next.js 16+ App Router** | Server Components for data-heavy dashboards; streaming SSR; the analytics "workbench". |
| Web state | **TanStack Query (via tRPC)** + **nuqs** (URL state) + **Redux Toolkit** (client/app state) | Three layers, three best-fit tools (server cache / URL / ephemeral UI). |
| Web UI | **shadcn/ui + Tailwind**; **Recharts** (standard charts) + **Visx** (waterfall, cohort heatmap) | Polished, fast, composable; Visx for the bespoke profit visualizations. |
| Mobile | **React Native + Expo (managed)** | One TS codebase for iOS+Android; reuses tRPC/Redux/types; the **Morning Brief** primary surface; EAS cloud builds + OTA. |
| Mobile UI | **Tamagui** + **victory-native** (Skia) | Native-feel; design-token parity with web; charts that run on RN. |
| Mobile storage | **expo-secure-store** (tokens) + AsyncStorage | Keychain/Keystore for refresh tokens; access token in memory only. |
| Push | **Expo Push (APNS + FCM)** | Morning Brief + critical alerts; one pipeline both platforms. |

### 2.3 Edge / API

| Layer | Choice | Why |
|---|---|---|
| API gateway / BFF | **Fastify + tRPC** | Type-safe edge for web+mobile; BFF fan-out to internal services; one auth + rate-limit + tenancy choke point. |
| Internal service calls | **gRPC over Protobuf (buf)** | Binary, streaming, strongly typed across TS↔Python; protos are the single source of truth (also generate MCP tool schemas). |
| Agent / partner surface | **MCP server inside api-gateway** | Shares auth + tenancy + rate-limit; tools generated from the same protos (cannot drift); inter-agent + external tool use. |
| Public REST | Thin adapter over tRPC (Phase 4) | Programmatic partners; not needed early. |
| Validation | **Zod** (TS) · **Pydantic** (Python) | Schema validation at every boundary. |

### 2.4 Data stores

| Layer | Choice | Why |
|---|---|---|
| OLTP | **Postgres (Supabase)** — product state, settings, Decision Log, consent, tickets, audit, 90-day hot mirror | Relational integrity, RLS for tenancy, Supabase Auth + pgvector in one place. |
| OLAP | **ClickHouse Cloud** — orders/line-items/shipments/ads facts, daily metrics, cohorts, pincode/RTO | Sub-second aggregates over billions of rows; the analytics product **cannot** run on Postgres. |
| Vector memory | **pgvector** in Postgres — Brand Fingerprint + condition-outcome pairs | Memory Layer at SQL economics; no separate vector DB until full-text+vector is needed. |
| Cache / ephemeral | **Redis (ElastiCache)** — sessions, rate-limit counters, idempotency keys, hot metric cache | A cached metric is an LLM/ClickHouse call you didn't pay for (cost lever). |
| Object store | **S3** — raw payload archive, exports, consented call recordings, Kafka tiered storage | Cheap durable archive; replay source of truth. |
| Money representation | **Integer minor units** (BIGINT in PG, Int64 in CH) + `currency_code` | No float drift; superjson preserves `bigint`; display via `formatMoney`. **(Canonical — see §5.)** |

### 2.5 Event spine

| Layer | Choice | Why |
|---|---|---|
| Event bus | **Amazon MSK (Kafka)** — partitioned by `workspace_id`; tiered storage to S3 (infinite retention) | Durable, replayable spine; every downstream materialization rebuildable; Decision Log永 retained. |
| Schema registry | **AWS Glue Schema Registry + Avro** | Versioned event schemas; backward-compatible evolution; `.vN` topic bump for breaking changes. |
| CDC | **Debezium on MSK Connect** (Postgres → ClickHouse) | Keeps the 90-day Postgres mirror and ClickHouse authoritative store in sync. |

### 2.6 Intelligence

| Layer | Choice | Why |
|---|---|---|
| LLM | **LiteLLM gateway** (OSS, self-hosted on EKS, ap-south-1) → model backends; **Claude is the default** (Sonnet 4.6 synthesis, Haiku 4.5 bounded NL) | Model-agnostic: each task routes to the **cheapest model that passes its eval bar** — not always Claude. Gateway = unified API + routing/fallback/semantic-cache/per-workspace budgets/cost-tracking; `@paradigm` tiers name a routed *policy*, the gateway resolves the model. Backend choice (AWS Bedrock vs native provider direct clients) is **deferred + reversible behind the gateway** — pick per cost. Prompt caching stays the biggest cost lever (on the frontier backend). |
| ML / stats | **Prophet, scikit-learn, PyMC-Marketing (BG/NBD+Gamma-Gamma LTV), lifelines (Kaplan-Meier), XGBoost, statsmodels** | Forecasts, LTV, cohort survival, RTO risk, anomaly — paradigm-2 economics. (`lifetimes` is archived → PyMC-Marketing.) |
| Agent pattern | 15 AICMO/AICOO/AICFO agents in `intelligence-service`; daily tick → Sonnet synthesis | Specialists at ML cost; one frontier-LLM synthesis step for the Morning Brief. |

### 2.7 Infrastructure

| Layer | Choice (target) | Why |
|---|---|---|
| Orchestration | **EKS + Karpenter** | Bin-packing autoscale across many services + bursty backfills/agent ticks at scale. |
| IaC | **AWS CDK (TypeScript)** | Same language as the team; typed infra. |
| CI/CD | **GitHub Actions → ECR → ArgoCD** (services); **EAS** (mobile) | GitOps deploys; managed mobile builds. |
| Region | **ap-south-1 (Mumbai)** primary; multi-region Phase 4 | India-first; DPDP residency by default. |
| Search/logs | **OpenSearch** (logs; Phase 3 search) | Centralized log store + later product search. |
| Observability | **OpenTelemetry → CloudWatch/X-Ray + Sentry + PostHog** | One correlation ID end-to-end; errors + product analytics. |
| Secrets | **AWS Secrets Manager + KMS** (envelope encryption of vendor tokens) | No plaintext credentials; per-workspace key reference. |

---

## 3. Phased adoption — start simple, scale into it

The mature stack above is the destination. **Do not build it all in Phase 0.** Below is what to actually run at each phase, what's deferred, and the **trigger** that graduates each deferred layer.

### 3.1 The principle: logical separation now, physical separation later

Brain has **7 backend bounded contexts**: `api-gateway`, `core`, `ingestion`, `analytics`, `intelligence`, `lifecycle`, `notifications` (+ `web`, `mobile`). These are **always logically separate** — each is its own DDD bounded context with its own gRPC contract (defined in `protos/` from day one). What changes by phase is **how many independent deployables** they run as.

> **Modular-monolith-to-microservices:** co-deploy bounded contexts in a few processes early; split into independent services when load, team size, or deploy-cadence conflicts justify it. Because the gRPC contracts exist from day one, splitting is mechanical (flip an in-process call to a network call), not a rewrite.

### 3.2 Phase-by-phase stack

| Concern | Phase 0–1 (MVP → operator wedge, ~1–25 brands) | Phase 2–3 (lifecycle + agentic, ~25–200 brands) | Phase 4 (scale + enterprise, 200+) |
|---|---|---|---|
| **Deployables** | **3 services**: `edge` (Node: api-gateway + core), `data` (Python: ingestion + analytics + intelligence), + `web` + `mobile` | Split into the full **7 backend services**; add `lifecycle-service` (new in Phase 2) and `notifications-service` | 7 services, independently scaled; hot-workspace isolation |
| **Compute hosting** | **ECS Fargate** (backend) + **Amplify/managed** (web) + **EAS** (mobile) | Migrate backend to **EKS + Karpenter**; web to EKS or stay managed | EKS multi-AZ; Karpenter; per-region clusters |
| **Event bus** | **MSK Serverless** (or Redpanda single-node in dev) + transactional **outbox** for the few cross-context events that exist | Provisioned **MSK** + Glue Schema Registry + Debezium CDC | MSK 6+ brokers; MirrorMaker for multi-region |
| **OLTP** | Supabase Postgres (single primary) | + 1 read replica (analytics/backfill reads) | + 2 replicas; PgBouncer; consider Aurora if Supabase ceilings hit |
| **OLAP** | **ClickHouse Cloud** (managed, small) — from day one | ClickHouse Cloud scaled; 3 shards × 2 replicas | 6–12 shards; projections; query-result cache |
| **Cache** | Redis (ElastiCache, single node) | ElastiCache cluster mode | Cluster + read replicas |
| **Internal calls** | In-process (co-deployed) **behind the gRPC contract**; gRPC activates as services split | gRPC over HTTP/2 across services | gRPC + service mesh (mTLS) |
| **LLM** | **LiteLLM gateway on EKS** + Claude (default) with prompt caching + per-workspace caps (gateway virtual-key budgets) from day one | + model-agnostic routing to cheaper backends as the cheap tier scales; cost-discipline dashboard | + add/optimize backends per cost (Bedrock / native direct clients; Provisioned Throughput where it pays) |
| **Region** | ap-south-1 only | ap-south-1 only | + secondary regions for UAE/GCC/EU residency |
| **Mobile** | Morning Brief + read-only dashboards (Phase 1) | Interaction layer (chat, approvals) | Widgets, watch, parity |

### 3.3 Scale triggers (graduate a layer only when its trigger fires)

| Deferred capability | Default until | **Trigger to adopt** |
|---|---|---|
| Split `edge`/`data` into 7 services | Phase 2 | Independent deploy cadence needed, OR a context's scaling profile diverges (e.g., ingestion backfills starving the API), OR team grows past ~4 engineers. |
| **EKS + Karpenter** (from Fargate) | Phase 2–3 | Fargate cost crosses ~$1.5–2K/mo, OR you need bin-packing across many bursty pods (agent ticks, backfills), OR fine-grained scheduling. |
| **Provisioned MSK** (from MSK Serverless) | Phase 2 | Sustained throughput makes serverless more expensive than provisioned, OR you need Debezium CDC + tiered storage tuning. |
| **Debezium CDC** | Phase 2 | More than one consumer needs the 90-day Postgres mirror in ClickHouse, OR webhook reconciliation needs streaming. (Phase 0–1: ingestion writes both stores directly.) |
| **Postgres read replica** | Phase 2 | Analytics/backfill reads contend with OLTP writes (replica lag acceptable for those reads). |
| **ClickHouse sharding** | Phase 3 | Single-shard query p95 misses target, OR data volume per node crosses comfort. |
| **Service mesh (mTLS)** | Phase 2–3 | More than ~5 services; need automatic mutual TLS + traffic policy. |
| **Multi-region** | Phase 4 | First UAE/GCC/EU customers with residency requirements. |
| **Per-workspace ClickHouse DB / dedicated shard** | Phase 4 | Enterprise hard-isolation contract, OR a top-1% workspace dominates a shard. |
| **Public REST API + outbound webhooks** | Phase 4 | A partner/enterprise integration requires programmatic access. |

### 3.4 What is non-negotiable from day one (do not defer)

These are foundational to the product thesis and cheap to do right early; retrofitting them is expensive:

1. **`workspace_id` on every row/event/cache key/log** + Postgres RLS + ClickHouse query-gateway. (Tenancy can't be bolted on.)
2. **Integer minor-units money** + `currency_code` everywhere. (Migrating money representation later is brutal.)
3. **Decision Log** append-only schema. (The moat.)
4. **Region-adapter interface** (even with only India implemented). (Prevents India hardcoding.)
5. **Metric registry** with TS↔Python parity. (One definition per metric.)
6. **Cost-routing `@paradigm` discipline** + per-workspace LLM caps. (Pricing survival.)
7. **OLTP/OLAP split** (Postgres + ClickHouse). (The analytics product needs OLAP from the first dashboard.)
8. **Proto-defined gRPC contracts** for every bounded context. (Makes the later service split mechanical.)
9. **Idempotency** on every connector write + mutating endpoint. (Webhooks retry; double-orders are unacceptable.)
10. **Mobile Morning Brief** as the primary surface (Phase 1). (It is the product.)
11. **Per-service CI/CD from day one** — every service ships with its own pipeline (Turborepo `--affected` build → its own ECR image → its own ArgoCD Application → canary + auto-rollback) as part of its first vertical slice. The monorepo is code-organization, not a deploy unit; **deploy only the changed service + its transitive dependents.** Retrofitting CI/CD (or shipping a deploy-all pipeline) later is the trap this prevents. (See `devops-aws` §Selective deployment.)

---

## 4. Alternatives considered (and why rejected)

| Decision | Chosen | Rejected alternative | Why |
|---|---|---|---|
| Architecture | Modular-monolith → microservices | Full microservices from day one | Premature ops cost for a small team; service boundaries are real but deployment can be consolidated early. |
| Architecture | Modular-monolith → microservices | Permanent monolith | Ingestion (Python/ML) and the edge (TS) have genuinely different runtimes, scaling, and deploy cadences; they must split eventually. |
| OLAP | ClickHouse | Postgres-only (TimescaleDB) | Billion-row cohort/RTO/pincode aggregates need columnar OLAP; Timescale doesn't reach ClickHouse's scan economics. |
| OLAP | ClickHouse | BigQuery/Snowflake | Per-query cost model fights %-GMV unit economics; ClickHouse gives predictable, owned cost. |
| Mobile | React Native + Expo | Native Swift+Kotlin | 2× effort, 2 skill sets, for a small team. |
| Mobile | React Native + Expo | Flutter | Adds Dart; loses shared TS types with backend. |
| Mobile | React Native + Expo | PWA | iOS push unreliable; no real home-screen/Face ID/store presence — fatal for the Morning Brief. |
| Edge | tRPC | GraphQL | Single first-party frontend doesn't need GraphQL's flexibility; tRPC gives free end-to-end types. |
| Internal | gRPC | REST/JSON | Binary efficiency + streaming + strong typing across TS↔Python. |
| Event bus | Kafka (MSK) | RabbitMQ/SQS-only | Need replay + infinite retention + multi-consumer fan-out (rebuildable materializations). |
| LLM | Anthropic Claude | OpenAI/open-source | Quality + prompt caching; cost-routing keeps LLM a thin layer regardless. |
| Vector | pgvector | Pinecone/Weaviate | Low volume; one fewer system; SQL economics for the Memory Layer. |
| Infra | EKS (at scale) / Fargate (early) | Always-EKS | EKS is over-engineered for the first 25 brands; Fargate ships faster and cheaper early. |
| IaC | AWS CDK | Terraform | TypeScript parity with the team; typed constructs. |

---

## 5. Canonical resolutions (cross-document consistency)

The prior docs disagreed in places. These are the **binding** resolutions; the consolidated `technical-requirements.md` and all TECH/ files follow them.

| # | Topic | Conflict | **Canonical resolution** |
|---|---|---|---|
| R1 | **Money representation** | Top-level spec used `NUMERIC(18,4)`; deep-dives used integer minor units | **Integer minor units** (BIGINT/Int64) + `currency_code`. Migrate any NUMERIC money to minor units. |
| R2 | **Role model** | 5 roles (Read-only/Analyst/Agency/Operator/Owner) vs 4 (owner/admin/analyst/viewer) | **5 roles per business doc: Owner, Operator, Analyst, Agency, Viewer (read-only).** Encoded in JWT claim + RLS + MCP scopes. |
| R3 | **Postgres schema layout** | `core/ai/...` named schemas vs `public + ai` | **Bounded-context schemas**: `core`, `ai`, `lifecycle`, `support`, `billing`, `audit` (+ Supabase `auth`). Each service owns its schema. |
| R4 | **Lifecycle service boundary** | Top-level folded lifecycle into `notifications-service`; deep-dive defined a separate `lifecycle-service` | **Separate `lifecycle-service`** (RFM, audience, channel routers, AI calling, compliance, inbox). `notifications-service` handles alerts/digests/push/exports/Morning Brief delivery. Lifecycle is a Phase-2 build, so no early cost. |
| R5 | **GMV billing base** | Undefined | **Realized/delivered GMV** (net of cancellation/RTO/refund). See `TECH/15_billing_metering.md`. |
| R6 | **India GST** | 5/12/18/28 slabs | **GST 2.0: 0/5/18/40**, extracted **per line item** by SKU slab. |
| R7 | **GCC VAT** | Treated as uniform 5% | **Per-country: KSA 15%, UAE 5%, Bahrain 10%, Oman 5%; Qatar/Kuwait none.** |
| R8 | **Geographic rollout** | "first-class day one" vs phased | **India-first; region-adapter from day one; UAE/GCC live in Phase 4.** |
| R9 | **Compliance** | Scattered/generic | Consolidated in `TECH/16_compliance_engine.md`: DPDP, UAE/KSA PDPL, TCCCPR/DLT, NCPR/DND, 9am–9pm; India in-region residency by default. |
| R10 | **External-canon leakage** | Deep-dives referenced an external companion doc, an example brand, a competitor name, and a hardcoded vendor domain | Removed. Brain-docs is the single source of truth; domains shown as `{BRAIN_DOMAIN}` placeholders. |
| R11 | **Service count headline** | "7 services" counted inconsistently | **7 backend services** (`api-gateway`, `core`, `ingestion`, `analytics`, `intelligence`, `lifecycle`, `notifications`) + `web` + `mobile`. |

---

## 6. Cost posture (why this stack fits %-of-GMV pricing)

The unit-economic invariant: **per-brand monthly infra + LLM + messaging cost must be a small fraction of the brand's Brain fee** (which is a small % of their realized GMV).

- **Compute:** Fargate/EKS bin-packed; most work is batch (daily tick, nightly rollups) on spot-friendly nodes.
- **OLAP:** ClickHouse owned-cost, not per-query — predictable as brands scale.
- **LLM:** cost-routing keeps ~85% of calls at SQL economics; prompt caching + per-workspace caps bound the rest. Target paradigm mix: **85% SQL · 12% ML · 2.5% Haiku · 0.5% Sonnet** by call count.
- **Messaging/telephony:** pass-through with per-brand caps; bundled into the fee below the cap.
- **Cache:** Redis turns repeat ClickHouse/LLM reads into ~free reads.

If the paradigm mix ever flips toward frontier-LLM, the pricing model breaks — that is why the `@paradigm` gate is a build-pipeline check, not a preference. See `TECH/12_cost_routing_compute.md`.

---

## 7. Open decisions (owner + trigger)

| # | Decision | Resolution path |
|---|---|---|
| 1 | AI calling vendor (Path A India partner / B global / C native) | Partner (A/B) months 1–6 to validate; parallel-build native if volume >~5K calls/day. See `TECH/11`. |
| 2 | MSK Serverless vs provisioned at Phase 2 cutover | Driven by sustained throughput cost-crossover; benchmark at end of Phase 1. |
| 3 | Web hosting: managed (Amplify) vs EKS | Managed until build-minutes/customization warrant EKS (Phase 3). |
| 4 | ClickHouse Cloud vs BYOC vs self-hosted | **ClickHouse Cloud (managed, ap-south-1) for Phase 0–3** — Mumbai is a standard auto-scaling region (DPDP-clean) and idle-to-zero fits the batch-spiky daily tick, so ops≈0 for a small team. **First graduation = BYOC** (data plane in Brain's own AWS account) when sustained **compute** spend ≥ ~$6K/mo for 3 months, OR an in-account-residency contract, OR AWS committed-spend discounts beat CH's markup. **Self-host on EKS (Altinity-supported) only at Phase 4** (large/predictable/always-on ≥~$15–20K/mo + a named infra owner). Loaded self-host TCO (infra + 4–8 hrs/wk eng + on-call) is a wash below ~$6–8K/mo — never graduate on bare infra cost alone. Keep the prod service warm before the 06:55–07:20 IST tick (idle-to-zero is for dev/off-peak). |
| 5 | LLM gateway + backend choice | **Decided: LiteLLM gateway (OSS, self-host on EKS, ap-south-1)** as the model-agnostic routing layer (gives routing/fallback/caching/per-workspace budgets/cost-tracking). **Backend choice deferred + reversible behind the gateway** — AWS Bedrock vs native-provider direct clients, picked per cost/need later. Hard constraint on any backend: India-resident inference for PII-bearing calls (DPDP — do NOT use Bedrock global cross-region inference for those) + prompt-caching for the frontier tier. |

---

**The one-line summary:** Build the *contracts and invariants* of the mature architecture from day one (tenancy, minor-units, Decision Log, region-adapter, metric registry, cost-routing, proto contracts, OLTP/OLAP split), but run the *infrastructure* at the smallest footprint that serves current scale (3 deployables on Fargate, MSK Serverless, single-region, managed ClickHouse) and graduate each heavy layer only when its trigger fires.
