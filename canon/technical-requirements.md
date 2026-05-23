# Brain Technical Requirements

> **Version:** Consolidated v2.1
> **Updated:** 2026-05-23
> **Audience:** AI builder agents, engineers, data engineers, design-system agents, QA agents, implementation reviewers
> **Product:** Brain — AI-native commerce operating system for DTC brands (India-first; UAE/GCC sequenced)
> **Status:** Source-of-truth technical requirements. Derived from `business-requirements.md` v1.1.
> **Companion docs:** `TECH/00_tech_stack_decision.md` (stack + phasing) and `TECH/01–17` (deep-dives). This document is the authoritative top-level spec; the TECH/ files expand each area. Where they ever disagree, **this document and TECH/00 win.**

---

## 0. Prime Directive

Brain is the AI-native commerce operating system that turns a DTC brand's fragmented stack into one place to **read, decide, and act** on revenue and profit. It is not a dashboard, a reporting tool, a chatbot, a helpdesk wrapper, or a single-channel marketing sender. It is the high-frequency operating surface an operator opens repeatedly because it shows live revenue movement, margin quality, leaks, recovery opportunities, customer risk, and **executable next actions**.

The technical system is built around four obligations:

1. **Truth** — every number is auditable, reproducible, and traceable to source events. LLMs never invent numbers.
2. **Memory** — every recommendation, action, response, and outcome compounds into the Decision Log and Brand Fingerprint.
3. **Execution** — Brain can recommend, queue, execute, and reverse commerce actions across marketing, lifecycle, support, logistics, inventory, and finance, with guardrails.
4. **Profit quality** — surfaces privilege CM2/CM3, recovered revenue, reduced RTO, reduced wasted spend, retained customers, and support-driven revenue protection over vanity metrics.

A feature ships only if it ties to revenue, profit, risk reduction, operator time saved, compliance, or decision memory.

This document is standalone: an AI builder agent should be able to implement Brain from this document plus the TECH/ deep-dives, with no external brief.

---

## 1. Product Boundary and Naming

- The product is **Brain**. All code, prompts, package names, routes, seed data, and UI copy use Brain-only language.
- Provider names (Shopify, Meta, Google, Shiprocket, Razorpay, WhatsApp, etc.) appear **only** as integration targets, never as positioning anchors.
- No legacy codenames, no "modeled after X" framing, no hardcoded vendor domains (use `{BRAIN_DOMAIN}` placeholders).

Every major module must answer at least one of: *What revenue was made/recovered/protected/lost? What happened to CM2/CM3/cash/CAC/MER/aMER/RTO/COD/refunds/support cost? What should the operator do next? Can Brain safely execute it? How did it perform at 7 and 30 days?*

---

## 2. Canonical Architecture Principles (non-negotiable)

1. **Workspace isolation everywhere.** Every row, event, object, cache key, vector, log, token, and export carries `workspace_id`. Enforced at four layers (JWT → service assertion → Postgres RLS → ClickHouse query gateway).
2. **Source events are immutable; derived data is rebuildable.** Raw payloads and canonical events are append-only.
3. **OLTP and OLAP are separate.** Postgres = product/workflow state. ClickHouse = analytical facts + aggregates.
4. **Events are the spine.** Cross-context state changes flow through Kafka (replayable, retained). No hidden cross-service DB reads.
5. **One primitive per concern.** Audience, Consent, Decision Log, Identity, Attribution, Integration Health, Notifications, Audit are each built **once** and consumed by every channel and agent. (The Single-Primitive Rule.)
6. **SQL ≫ ML ≫ small LLM ≫ frontier LLM.** Metrics are deterministic; ML predicts; LLMs classify/explain/synthesize/draft. The cost-routing gate is a build-pipeline check, not a preference. (See §19, `TECH/12`.)
7. **Region adapters, not regional forks.** One metric engine; region-specific behavior behind the `RegionAdapter` interface. India implemented first.
8. **Backfill and live sync share one connector code path.** Only the window changes.
9. **Decision Log is mandatory.** No recommendation, auto-execution, lifecycle send, support resolution, or reversal exists unless logged.
10. **Guardrails before autonomy.** Confidence thresholds, caps, consent/policy checks, kill switch, auto-revert, audit — on every agentic action.
11. **Observable by default.** Freshness, lag, agent runs, LLM cost, automation outcomes are first-class metrics with one correlation ID end-to-end.
12. **Money is integer minor units + `currency_code`.** Never float. (Canonical resolution R1.)
13. **Bill on realized/delivered GMV.** The metering base for pricing is revenue that survives RTO/refund/cancellation. (R5.)
14. **Multi-tenant from day one, India-first by sequencing.** Region-adapter exists from the first commit; UAE/GCC go live in Phase 4.

---

## 3. Tech Stack (summary)

The full decision + justification + phased adoption is in **`TECH/00_tech_stack_decision.md`**. Summary of the **mature target stack**:

| Layer | Choice |
|---|---|
| Monorepo | Turborepo + pnpm (TS) · uv (Python) · Buf (proto codegen) |
| Web | Next.js 16 App Router (React 19) · tRPC client · TanStack Query · nuqs · Redux Toolkit · shadcn/Tailwind · Recharts + Visx |
| Mobile | React Native + Expo · Expo Router · Tamagui · victory-native · expo-secure-store · Expo Push · EAS |
| Edge / API | Fastify + tRPC (BFF) · MCP server (in api-gateway) · Zod |
| Internal | gRPC over Protobuf (buf) · Pydantic (Python) |
| OLTP | Postgres (Supabase) + pgvector |
| OLAP | ClickHouse Cloud |
| Cache | Redis (ElastiCache) |
| Object store | S3 |
| Events | Amazon MSK (Kafka) + Glue Schema Registry (Avro) + Debezium CDC |
| Intelligence | **LiteLLM gateway** (OSS, self-host on EKS) → model-agnostic backends; **Claude default** (Sonnet 4.6 synthesis, Haiku 4.5 bounded NL), each task routed to the cheapest model passing its eval bar · Prophet/sklearn/PyMC-Marketing/lifelines/XGBoost/statsmodels |
| Infra | EKS + Karpenter (Fargate early) · AWS CDK · GitHub Actions → ECR → ArgoCD · ap-south-1 |
| Observability | OpenTelemetry → CloudWatch/X-Ray · Sentry · PostHog · OpenSearch (logs) |
| Secrets | AWS Secrets Manager + KMS |

**Phasing (see TECH/00 §3):** Phase 0–1 runs **3 deployables** (`edge` = Node api-gateway+core; `data` = Python ingestion+analytics+intelligence; + web + mobile) on **Fargate** with **MSK Serverless** and managed ClickHouse, single-region. Bounded contexts are logically separate (own gRPC contracts) and split into the **7-service** target at Phase 2–3 when triggers fire.

---

## 4. System Architecture

### 4.1 Conceptual layers

| Layer | Responsibility | Owner service(s) |
|---|---|---|
| Data | Pull + normalize commerce/ads/payments/logistics/returns/support/messaging data | `ingestion`, `analytics` |
| Metric | Deterministic revenue, CM, acquisition, lifecycle, product, logistics, finance metrics | `analytics` |
| Memory | Brand Fingerprint, Decision Log, condition-outcome pairs, segment/creative memory | `intelligence` (Postgres + pgvector) |
| Agent | AICMO/AICOO/AICFO + AI CX, daily tick, auto-execute | `intelligence` |
| Execution | WhatsApp/email/SMS/calls, ad/courier/refund/PO actions, inbox | `lifecycle`, `notifications`, connectors |
| Interface | Web workbench, mobile Morning Brief, inbox, reports, settings, MCP/API | `web`, `mobile`, `api-gateway` |

### 4.2 Services (7 backend + 2 clients)

| Service | Runtime | Responsibilities |
|---|---|---|
| `web` | Next.js / TS | Operator workbench: dashboards, P&L, waterfall, cohorts, lifecycle builder, inbox, settings, auto-execute log |
| `mobile` | React Native + Expo / TS | **Morning Brief (primary surface)**, dashboards, alerts, AI chat, approvals |
| `api-gateway` | Fastify / TS | Auth, RBAC, rate limiting, tRPC + SSE/WS, **MCP server**, BFF fan-out to internal gRPC |
| `core-service` | Node / TS | Organisations, workspaces, users, roles, settings, costs, goals, integrations registry, consent, audit, billing/metering |
| `ingestion-service` | Python | Connector framework, sync jobs, webhooks, canonicalization, raw archive, integration health |
| `analytics-service` | Python | ClickHouse materializations, metric engine, RFM, lifecycle states, LTV, attribution, regional math, Decision Log writes |
| `intelligence-service` | Python | Memory Layer, agents, anomaly, forecasts, LLM orchestration, internal MCP tools |
| `lifecycle-service` | Node (orchestration) + Python (RFM/LLM) | Audience builder, channel routers, AI calling, compliance engine, inbound inbox, recovered-revenue attribution |
| `notifications-service` | Node / TS | Alerts, Morning Brief assembly + delivery, digests, push, exports, outbound webhooks |

> **Boundary resolution (R4):** `lifecycle-service` (revenue execution) is distinct from `notifications-service` (alerts/digests/push/exports). Lifecycle is a Phase-2 build. In Phase 0–1 the Python contexts co-deploy as one `data` service and the Node contexts as one `edge` service (TECH/00 §3).

### 4.3 Data stores & ownership

| Store | Purpose | Owned/written by |
|---|---|---|
| Postgres (Supabase) | Product/workflow state, settings, Decision Log, consent, tickets, audit, billing, 90-day hot mirror, pgvector memory | `core`, `analytics` (Decision Log), `intelligence` (`ai.*`), `lifecycle` (`lifecycle.*`) |
| ClickHouse Cloud | Raw + canonical facts, daily metrics, cohorts, pincode/RTO, support/lifecycle aggregates | `ingestion` (raw), `analytics` (canonical + derived) |
| Redis (ElastiCache) | Sessions, rate-limit, idempotency, hot metric cache, feature flags | all |
| S3 | Raw payload archive, exports, consented recordings, Kafka tiered storage, audit mirror | `ingestion`, `notifications`, `lifecycle` |
| MSK (Kafka) | Event spine, replay, decoupling | all |
| pgvector | Brand Fingerprint + condition-outcome vectors | `intelligence` |

### 4.4 Runtime flow

```text
Provider APIs + webhooks
  → ingestion-service: canonicalize → S3 raw archive + ClickHouse raw + Kafka integrations.*.v1 + Postgres 90-day mirror
  → analytics-service: materialize ClickHouse facts + daily_metrics; compute order_costs; write Decision Log; emit analytics.*.v1
  → intelligence-service: build Brand Fingerprint (07:00 IST), query memory, run agents (07:10), synthesize Morning Brief (07:15)
  → notifications-service: deliver Morning Brief / alerts (push, 07:00–09:00 IST) ; lifecycle-service: execute approved outreach
  → api-gateway → web/mobile: surface revenue/profit/actions/outcomes
  → Decision Log captures condition → recommendation → response → execution → 7d/30d outcome
```

---

## 5. Monorepo & Folder Structure

### 5.1 Top-level layout

```text
brain/
├── apps/
│   ├── web/                     # Next.js 16
│   ├── mobile/                  # React Native + Expo
│   ├── api-gateway/             # Fastify + tRPC + MCP (Node)
│   ├── core-service/            # Node
│   ├── ingestion-service/       # Python
│   ├── analytics-service/       # Python
│   ├── intelligence-service/    # Python
│   ├── lifecycle-service/       # Node + Python
│   └── notifications-service/   # Node
├── packages/                    # Shared TS
│   ├── ui/                      # shadcn-derived web components
│   ├── ui-mobile/               # Tamagui mobile primitives
│   ├── lib-formatters/          # currency/date formatters (web + mobile)
│   ├── lib-metrics/             # metric registry (TS side; parity with pylib)
│   ├── lib-grpc-clients/        # generated gRPC TS clients
│   ├── trpc-client/             # shared tRPC client + AppRouter types
│   ├── state/                   # shared Redux slices (web + mobile)
│   ├── lib-auth/ lib-observability/ lib-test-fixtures/
├── pylibs/                      # Shared Python
│   ├── brain_metrics/           # metric registry (Python side; parity with TS)
│   ├── brain_regional/          # RegionAdapter + India/UAE adapters
│   ├── brain_connectors/        # connector base + provider impls
│   ├── brain_clickhouse/        # ClickHouse query gateway (tenant-enforced)
│   ├── brain_kafka/             # producer/consumer + rate limiter
│   ├── brain_ml/ brain_llm/ brain_agents/ brain_mcp/ brain_grpc/ brain_logger/
│   └── brain_cost_router/       # @paradigm decorator + caps middleware
├── protos/                      # SINGLE SOURCE OF TRUTH for gRPC + MCP + events
│   ├── core/ analytics/ intelligence/ notifications/ lifecycle/ integrations/
│   └── events/                  # Avro schemas
├── infra/
│   ├── cdk/                     # AWS CDK (TS)
│   ├── k8s/                     # Helm/ArgoCD manifests (Phase 2+)
│   └── migrations/              # Postgres (Prisma) + ClickHouse SQL
├── docs/ tools/ tests/
```

### 5.2 Service-internal structure — DDD by bounded context (mandatory)

Every backend service is organized **by domain**, never by technical layers (`controllers/`, `models/`). The standard layering inside each service:

```text
<service>/src/
├── bootstrap/         # server wiring, DI, config, health probes
├── domain/            # entities, value-objects, aggregates, domain events, policies (pure)
├── application/       # use-cases / commands / queries (CQRS), orchestration
├── infrastructure/    # repositories, gRPC clients, Kafka producers/consumers, DB, external APIs
└── interfaces/        # gRPC handlers / tRPC routers / Kafka consumers / HTTP
```

**Node example — `core-service`:**
```text
apps/core-service/src/
├── bootstrap/            # fastify/grpc server, prisma client, env validation, /healthz /readyz
├── contexts/
│   ├── workspaces/       # domain/ application/ infrastructure/ interfaces/
│   ├── members-rbac/
│   ├── integrations/     # registry + OAuth state + encrypted-credential wrapper
│   ├── costs-goals/
│   ├── consent/
│   ├── billing-metering/ # realized-GMV metering, min fee, CM2 guardrail (TECH/15)
│   └── audit/
└── shared/
```

**Python example — `analytics-service`:**
```text
apps/analytics-service/src/
├── bootstrap/           # grpc server (grpcio), CH client, kafka consumers, probes
├── contexts/
│   ├── metric_engine/   # registry-driven computation; Path A (materialized) + Path B (live)
│   ├── materialization/ # MV + scheduled rollups; order_costs computation
│   ├── customer/        # NAC states, RFM inputs, churn thresholds, LTV
│   ├── attribution/     # placed/realized/incremental attribution primitive
│   ├── regional/        # pincode reliability, festival lift (via brain_regional)
│   └── decision_log/    # writer + 7d/30d outcome attribution jobs
├── consumers/           # integrations.*.v1, cdc.*, settings_changed
└── jobs/                # nightly/hourly/weekly scheduled rollups
```

**Python example — `intelligence-service`** (agent layout from `TECH/14`):
```text
apps/intelligence-service/
├── src/bootstrap/ memory/ forecast/ anomaly/ insights/ chat/ budget/ ltv/
├── agents/
│   ├── _base/           # agent.py (daily-tick + Decision Log + graduation tracker), memory_query.py, mcp_decorator.py
│   ├── aicmo/           # meta google tiktok snap cross_channel creative pricing festival
│   ├── aicoo/           # logistics returns inventory marketplace
│   └── aicfo/           # conversion cashflow pricing_margin
└── orchestration/       # daily_tick.py (06:55–07:15 IST) ; morning_brief.py (Sonnet synthesis 07:15)
```

**`lifecycle-service`** (from `TECH/11`):
```text
apps/lifecycle-service/
├── orchestration/ (Node)   # BuildAudience, TriggerOutreach, LaunchCampaign, GetTicketFeed
├── audience/ (Python)      # daily RFM scoring (SQL), 11 segments, materialization
├── routers/                # call_router, whatsapp_router, email_router, sms_router, ad_audience_router
├── compliance/             # compliance.py — calling hours, DLT, NCPR/DND, frequency caps, consent
├── inbox/                  # multi-channel inbound (Phase 3) + autonomous resolution
└── attribution/            # recovered-revenue 7d/30d → Decision Log
```

**`web`** (Next.js App Router, from `TECH/07`): route groups `(auth)`, `(onboarding)`, `(workspace)` (shell + analytics/regional/ai/plan/settings), `(admin)`; `packages/ui` for components; three-layer state (TanStack/nuqs/Redux).

**`mobile`** (Expo Router, from `TECH/10`): `(auth)` + `(workspace)` tab navigator (`index` Home, `morning-brief`, `insights`, `alerts`, `chat`, `settings`); `expo-secure-store` for tokens; the Morning Brief screen is the highest-quality UI in Brain.

> Full per-service trees and code patterns: `TECH/01–14`. The DDD layering is enforced at code review (a `controllers/`-style folder is a blocker).

---

## 6. Multi-Tenancy, Auth & RBAC

### 6.1 Account hierarchy

```text
Organisation → Brand/Workspace → Store/Channel/Integration → records
```
- **Workspace = tenant = brand = billing unit.** One org owns many brands (Model B). Agencies get scoped cross-brand access (Model C). Enterprise overlay = Model D. (Business doc §3.4.)
- Portfolio/benchmark views aggregate workspaces only via explicit permission + anonymized/scoped queries.

### 6.2 Roles (canonical — R2)

| Role | Level | Rights |
|---|---|---|
| Viewer (read-only) | 1 | Limited reports; no PII; no exports; no actions |
| Analyst | 2 | Read dashboards + comment; no approvals/settings writes |
| Agency | 3 | Scoped per-brand read/write as granted by Owner; every action tagged + audited |
| Operator | 4 | Operational write, approve/reject, lifecycle campaigns, inbox; cannot change billing or delete brand |
| Owner | 5 | Full control: billing, integrations, users, costs, auto-execute enablement, deletion |

Approval matrix per action class is in business doc §4.3; enforced in `application/` use-cases.

### 6.3 Enforcement (four layers)

1. **JWT** (Supabase) carries `user_id`, `active_workspace_id`, `role`, accessible-workspace list.
2. **api-gateway** validates JWT; propagates `workspace_id`/`user_id`/`request_id` via gRPC metadata; `requireRole(ctx, ws, minRole)` on every mutation.
3. **Postgres RLS** on every workspace-scoped table (`workspace_id = current_setting('app.workspace_id')`).
4. **ClickHouse query gateway** (`pylibs/brain_clickhouse`) rejects any query lacking a `workspace_id` predicate. Redis keys + S3 paths are workspace-scoped. Audit Log records every settings/integration/role/consent/action/reversal mutation.

### 6.4 Auth features
Email/password, magic link, Google OAuth, SSO/SAML + SCIM (enterprise), invite tokens (role+workspace scoped). Web: HttpOnly cookies. Mobile: refresh token in secure-store, access token in memory. Full detail: `TECH/09`.

---

## 7. Integration Architecture

### 7.1 Connector interface (one shape; backfill == live)

```python
class Connector(ABC):
    provider: str; category: str
    async def authenticate(self, credentials) -> AuthResult: ...
    async def refresh_token(self, integration) -> RefreshResult: ...
    async def sync(self, integration, window: SyncWindow) -> SyncResult: ...     # backfill vs live = window only
    async def receive_webhook(self, payload, signature, headers) -> WebhookResult: ...
    async def canonicalize(self, raw_event) -> list[CanonicalEvent]: ...
    async def health_check(self, integration) -> HealthStatus: ...
```

Each connector fans out to **3–4 sinks**: S3 raw archive, ClickHouse raw, Kafka canonical `integrations.*.v1`, and (Phase 0–1) the Postgres 90-day mirror. Idempotent: re-fetched records UPSERT to no-op on unchanged payload hash; ClickHouse `ReplacingMergeTree(version)` dedups (version = source `updated_at` ms). Watermarks + per-connector late-data window (Shopify 60d, Meta 28d, Google 7d, Razorpay 30d). Full spec: `TECH/02`.

### 7.2 Provider catalog (implementation targets — region-gated)

| Category | Providers |
|---|---|
| Storefront | Shopify, WooCommerce, Shopflo, Salla, Zid |
| OMS/warehouse | Unicommerce, EasyEcom, Eshopbox-style |
| Marketplaces | Amazon IN/AE/SA, Flipkart, Myntra, Ajio, Nykaa, Meesho, Noon, Namshi, Ounass (quality-graded; see §7.4) |
| Logistics | Shiprocket, Delhivery, Blue Dart, NimbusPost, iThink, ClickPost, Aramex, DHL, SMSA |
| Payments | Razorpay, GoKwik, Cashfree, PayU, PhonePe, Stripe, Checkout.com, Telr, **Tabby, Tamara (BNPL — UAE/GCC)** |
| Ads | Meta, Google, GA4, Snapchat, Amazon Ads; **TikTok (UAE/GCC only — banned in India, region-gated)** |
| Messaging | WhatsApp Cloud API, Gupshup, AiSensy, Wati, Interakt, Twilio, Karix, Kaleyra |
| Email/CRM | Klaviyo, Mailmodo, Netcore, WebEngage, MoEngage |
| Voice | Exotel, Plivo, Knowlarity, voice-AI vendors via abstraction (TECH/11 §5) |
| Support | Native Brain Inbox, Freshdesk, Zendesk, Intercom, Gorgias-style |

### 7.3 Token security
OAuth tokens/API keys encrypted via **KMS envelope encryption**; only a `credential_secret_arn` reference in `core.integrations`. Plaintext never logged; reads go through a core-service decryption wrapper; rotation supported.

### 7.4 Quality levels & health
Green (clean API), Yellow (gated/per-brand onboarding), Red (no API → Gmail/PDF/CSV workaround with LLM extraction + 1-hour breakage alert + explicit UI label). Every integration exposes connected/syncing/healthy/degraded/expired/failed/paused + last-success + freshness + records-24h + webhook status + error + affected reports + whether recommendations are blocked/degraded/safe. **P0 connectors alert at freshness > 60 min.** Agents degrade gracefully and label stale data. Full spec: `TECH/02`.

### 7.5 Onboarding & data-quality gate (BR §16)

Onboarding (Day 0 → 30, BR §16.1) is owned by `core-service` (workspace + region + currency + timezone + revenue-definition + cost setup) and `ingestion-service` (historical backfill + quality scan). Before metrics are presented as authoritative (vs "estimated"), a **data-quality gate** validates:

| Check | Pass condition |
|---|---|
| Order totals reconcile | ingested order totals ≈ storefront control total (within tolerance) |
| Ad spend reconciles | per-platform spend ≈ ad-account totals |
| Payment-method data present | COD/prepaid resolvable on orders |
| Refunds/returns mapped | refund + RTO/return events linked to orders |
| Logistics/RTO status available | shipment terminal states resolvable |
| **SKU costs cover ≥80% of revenue** | `product_cogs` populated for top-revenue SKUs |
| Customer identity joinable | email/phone hash joins across sources |
| Timezone/currency/tax correct | region adapter settings validated |
| Consent data present | consent state exists where lifecycle is enabled |

Reports are labelled **"estimated"** until the gate passes (esp. the SKU-cost-coverage check, since CM2 is meaningless without it). Activation (BR §18.5) requires ≥3 healthy integrations + 80% cost coverage + Morning Brief delivered + ≥5 logged recommendations + ≥1 attributed outcome. The gate result feeds the value-proof ledger and the first-value milestone (BR §16.4).

---

## 8. Event Architecture

### 8.1 Conventions
Topic: `<domain>.<entity>.<event>.v<n>`. **Partition key = `workspace_id`** (per-workspace ordering, required for version-based dedup). Avro schemas in `protos/events/`, registered with Glue Schema Registry.

### 8.2 Standard envelope
Every event: `event_id, event_type, workspace_id, occurred_at, produced_at, producer_service, trace_id, schema_version, idempotency_key, payload`.

### 8.3 Core topics

| Topic | Producer | Consumers |
|---|---|---|
| `integrations.orders.v1` / `.line_items.v1` / `.customers.v1` / `.products.v1` / `.refunds.v1` | ingestion | analytics, intelligence |
| `integrations.ads_insights.v1` / `.campaigns.v1` | ingestion | analytics, intelligence |
| `integrations.shipments.v1` / `.shipment_events.v1` | ingestion | analytics, intelligence, lifecycle |
| `integrations.payments.v1` | ingestion | analytics, intelligence, core (billing) |
| `analytics.metrics.daily_materialized.v1` | analytics | intelligence, notifications, api-gateway (cache invalidation) |
| `analytics.customer_state.changed.v1` | analytics | intelligence, lifecycle |
| `intelligence.insight.generated.v1` / `.anomaly.detected.v1` | intelligence | notifications |
| `intelligence.action.recommended.v1` / `.executed.v1` / `.decision.logged.v1` | intelligence/lifecycle | analytics, notifications, audit |
| `lifecycle.outreach.completed.v1` / `.recovered_revenue.attributed.v1` | lifecycle | analytics, intelligence |
| `support.ticket.created.v1` / `.resolved.v1` | lifecycle | analytics, intelligence |
| `notifications.digest.sent.v1` / `.alert.fired.v1` | notifications | audit |
| `integrations.sync.completed.v1` / `.failed.v1` / `integrations.dlq.v1` | ingestion | core, notifications |

### 8.4 Retention, evolution, idempotency
Raw integration + Decision Log topics: **infinite** (MSK tiered storage → S3). Transient (sync/digest): 30–90 days. Backward-compatible changes only within `.vN` (new fields have defaults); breaking changes → `.v(n+1)` with dual-write migration. Every consumer is idempotent (envelope `idempotency_key` + ClickHouse version dedup). DLQ + replay tool for poison events. **Phase 0–1:** MSK Serverless + a transactional outbox; Debezium CDC and provisioned MSK graduate per TECH/00 triggers.

---

## 9. Postgres Data Model (OLTP)

Bounded-context schemas (R3): `core`, `ai`, `lifecycle`, `support`, `billing`, `audit` (+ Supabase `auth`). Every workspace-scoped table has `workspace_id` + RLS. **Money = BIGINT minor units + `currency_code`.** Historical facts live in ClickHouse; Postgres keeps a **90-day hot mirror** (`*_recent`) for fast joined lookups + webhook reconciliation. Full DDL: `TECH/01`.

### 9.1 Core
```sql
core.organisations(id, name, billing_currency, created_at)
core.workspaces(id, organisation_id, slug, name, brand_category,
  home_region DEFAULT 'IN', default_currency DEFAULT 'INR', default_timezone DEFAULT 'Asia/Kolkata',
  fiscal_year_start_month DEFAULT 4, tier DEFAULT 'launch', aws_primary_region DEFAULT 'ap-south-1',
  features JSONB, created_at, updated_at, deleted_at)
core.workspace_members(workspace_id, user_id, role CHECK (role IN ('owner','operator','analyst','agency','viewer')), invited_by, created_at, PK(workspace_id,user_id))
core.integrations(id, workspace_id, integration_type, status, external_account_id,
  credential_secret_arn, config JSONB, watermarks JSONB, last_sync_*, backfill_completed_at,
  health JSONB, UNIQUE(workspace_id, integration_type, external_account_id))
core.oauth_states(token PK, workspace_id, provider, verifier, redirect_after, created_at, used_at)
```

### 9.2 Cost & goals
```sql
core.product_cogs(workspace_id, product_id, variant_id, sku, cogs_per_unit_minor BIGINT, currency_code, effective_from, effective_to, PK(workspace_id,product_id,effective_from))
core.cost_settings(workspace_id PK, fallback_cogs_pct, payment_gateway_fee_pct, cod_handling_fee_minor,
  packaging_cost_minor, rto_return_shipping_minor, rto_restocking_minor, rto_damage_rate,
  fixed_costs_monthly_minor, founder_salary_monthly_minor, updated_at)   -- tax handled per-SKU by RegionAdapter, not a single default rate
core.goals(id, workspace_id, metric_key, period, goal_type, value_minor_or_ratio, starts_on, ends_on, created_by)
```

### 9.3 Decision Log (`ai.decision_log`) — the moat
```sql
ai.decision_log(
  id, workspace_id, agent_group, agent_name,
  decision_type, action_type, status,            -- proposed/approved/rejected/edited/queued/auto_executed/blocked/executed/reversed/failed/observed
  priority_score, confidence, risk_level, reversibility,
  channel,                                        -- call/whatsapp/email/sms/ad_audience/no_action
  title, explanation, input_snapshot JSONB, evidence_refs JSONB,
  proposed_action JSONB, expected_impact JSONB, user_response JSONB, executed_action JSONB, reversal JSONB,
  outcome_7d JSONB, outcome_30d JSONB,
  attributed_revenue_minor BIGINT, attributed_cm2_minor BIGINT,
  recovered_revenue_7d_minor BIGINT, recovered_revenue_30d_minor BIGINT,
  learning_note TEXT, created_by DEFAULT 'brain', created_at, updated_at)
-- indexes: (workspace_id, created_at DESC), (workspace_id, agent_name, status), (workspace_id, action_type)
```
Rules: every recommendation creates a row before display; approvals/edits/executions/reversals update it; nightly 7d/30d jobs backfill outcomes; a workflow that cannot write here is not a Brain action.

### 9.4 Memory (`ai.*`, pgvector)
`ai.brand_fingerprint(workspace_id, date, vector vector(16), components JSONB, PK(workspace_id,date))`; `ai.condition_outcome(... brand_fingerprint_at_decision vector(16), decision_log_id, outcome_7d/30d, recovered_revenue_*_minor)`; `ai.cross_brand_pattern(... brand_count CHECK (>=5))` (k-anonymity); `ai.insights`, `ai.forecasts`, `ai.forecast_accuracy`, `ai.anomalies`, `ai.workspace_llm_budget`. HNSW cosine indexes on vectors (write-heavy, daily-growing tables — HNSW gives 95%+ recall out-of-box and absorbs inserts without a rebuild; keep ivfflat only as the >50M-vector/memory-constrained escape hatch). (TECH/05.)

### 9.5 Auto-execute (`ai.*`)
`ai.auto_execute_policies(workspace_id, action_type, enabled DEFAULT false, min_confidence, daily_count_cap, daily_value_cap_minor, requires_owner_for_irreversible DEFAULT true, PK(workspace_id,action_type))`; `ai.auto_execute_log(... decision_log_id FK, action_payload, provider_response, executed_at, reversed_at, reversal_payload)`.

### 9.6 Lifecycle (`lifecycle.*`)
`audience`, `audience_member` (frozen `rfm_score_snapshot` + `assigned_channel` at trigger), `outreach` (status, blocked_reason, outcome_label, recovered_revenue_minor), `call` (vendor, duration, transcript/recording only if consented), `rfm_score(workspace_id, customer_id, date, r/f/m, segment, PK(..))`, `consent_event` (append-only), `customer_consent_current(PK workspace_id,customer_id,channel)`. Customer record carries `do_not_call/email/whatsapp`, `last_rfm_score`, `last_segment`. (TECH/11.)

### 9.7 Support (`support.*`)
`support.tickets(id, workspace_id, decision_log_id, customer_id, channel, status, priority, ticket_type, tags[], assigned_to, resolution_type, confidence, csat_score, first_response_at, resolved_at)`; `support.messages(id, workspace_id, ticket_id, role, channel, content, provider_message_id)`.

### 9.8 Billing (`billing.*` — new, see TECH/15)
`billing.gmv_meter(workspace_id, period_month, placed_gmv_minor, realized_gmv_minor, rto_refund_adjustment_minor, billable_gmv_minor, currency_code)`; `billing.invoices(...)`; `billing.usage_passthrough(workspace_id, period, llm_cost_minor, messaging_cost_minor, call_minutes_cost_minor, ...)`; `billing.plan(workspace_id, tier, gmv_pct, min_monthly_fee_minor, cm2_cap_pct)`.

### 9.9 Audit (`audit.audit_log`)
Append-only: login/user/role changes, integration connect/disconnect, token-refresh failures, cost/goal changes, lifecycle approvals, support resolutions, refund/replacement actions, auto-execute enable/disable, kill-switch events, export/deletion events. 7-year retention.

---

## 10. ClickHouse Data Model (OLAP)

`ReplicatedMergeTree` family; `Distributed` over `cityHash64(workspace_id)`. Ordering key **leads with `workspace_id`**. `ReplacingMergeTree(version)` for late-data dedup (read with `FINAL`). `LowCardinality(String)` for repeated values. Money = `Int64` minor units. Full DDL + CDC + sharding: `TECH/01`.

- **Raw:** `raw_orders`, `raw_customers`, `raw_products`, `raw_shipments`, `raw_shipment_events`, `raw_refunds`, `raw_ads_insights`, `raw_campaigns` (append-only mirror of canonical events; ZSTD payload + SHA-256 hash).
- **Canonical facts:** `orders`, `line_items`, `customers`, `products`, `refunds`, `shipments`, `shipment_events`, `campaigns`, `campaign_insights_daily`, `order_costs` (per-order cost components computed from effective `cost_settings`).
- **Derived aggregates:** `daily_metrics` (master; `(workspace_id, metric_name, date, customer_type, channel, campaign_classification)`), `customer_states`, `cohort_aggregates`, `first_product_attribution`, `customer_lifetime_value`, `pincode_reliability`, `festival_lift_factors`, `support_daily`, `lifecycle_outreach_daily`.
- **Materialization:** ClickHouse MVs for simple aggregates (run on INSERT); scheduled Python rollups for join-heavy metrics (MER/aMER/CM2). CDC (Postgres→CH) via Debezium for the dual-store tables (Phase 2+).

---

## 11. Metric Engine & Formula Book

The **single source of truth** for every metric. One definition, computed identically in TS (`packages/lib-metrics`) and Python (`pylibs/brain_metrics`); CI enforces parity. **No metric is defined twice; LLMs never produce metric numbers.** Full spec: `TECH/03`.

### 11.1 Revenue (GST/VAT handled per-SKU — R6)
| Term | Definition |
|---|---|
| Gross Sales | Σ line-item price (pre-tax, pre-discount, pre-refund) — display only |
| Net Sales | Gross Sales − Discounts − Refunds |
| **Net Revenue (tax-exclusive)** | Net Sales − tax, where **tax is extracted per line item** by the SKU's slab via `RegionAdapter.extract_net_revenue()`. India GST 2.0 slabs: **0/5/18/40** (never a single blended rate). First-class input to CM math. |
| **Realized / Delivered Revenue** | Net Revenue from delivered+settled orders, excluding cancelled/RTO/failed-payment. The honest number; also the **billing base** (§17, TECH/15). |

### 11.2 Contribution-margin waterfall (computed per order, aggregated)
```
Net Revenue (tax-exclusive)
  − COGS (landed)
  − Forward shipping − Packaging − Payment gateway fee − COD handling
  − RTO provision (RTO_rate × reverse-logistics+restocking+damage)   ← modelled
  − Returns provision − Support allocation
= CM1 (if CM1<0, no marketing fixes it — flag immediately)
  − Marketing spend (Meta/Google/Snap/[TikTok GCC]/influencer/affiliate/lifecycle msg cost)
= CM2  (the honest number; if CM2<0, scale makes it worse)
  − Allocated fixed costs (salaries/agency/rent/software/warehouse)
= CM3
  − Founder salary / financing / one-offs (when enabled)
= Operating Profit
```
**True CM2** subtracts realized-order-only costs + (RTO_rate × return/restock/unrecoverable-COGS) + refund/payment-failure provisions. (Western tools that skip GST extraction overstate margin ~18%+.)

### 11.3 Marketing
MER = Net Revenue ÷ Total Marketing Spend · aMER = New-Customer Net Revenue ÷ Acquisition Spend · paMER = Paid Revenue ÷ Paid Spend · CAC = Spend ÷ **delivered** new customers · nCAC = Acquisition Spend ÷ new customers · CAC Payback = CAC ÷ monthly CM2/new-customer cohort · LTV:CAC = cohort cumulative CM2 ÷ cohort CAC · Incremental ROAS (holdout) · Creative Fatigue (EWMA on CTR/CPM/CVR). ROAS is display-only, never the P&L decision metric. Unclassified-spend share surfaced with aMER.

### 11.4 COD / RTO
RTO Rate = RTO ÷ Shipped · RTO Cost = forward + reverse + restocking + write-down · COD/Prepaid Realization = delivered ÷ shipped · COD/Prepaid Effective Revenue = value×(1−RTO_rate) − fees − RTO cost · Prepaid Incentive ROI · **Break-even COD RTO Rate = M/(M+C)** (M = delivered-order CM, C = RTO cost per failed order). (Corrected formula per business doc v1.1.)

### 11.5 Lifecycle & support
Recovered Cart/Winback Revenue + CM2 (after offer + message/call + attributable marketing cost) · Reorder Capture Rate · VIP Retention · Campaign Incrementality (vs holdout) · Recovered Revenue ÷ Brain Fee. Support: FRT, Resolution Time, Autonomous Resolution Rate, Refund Save Rate, **Support-Protected CM2** (cancellation prevention, COD→prepaid, replace-vs-refund, delivery rescue), Escalation Rate, CSAT/NPS.

### 11.6 Goal RAG
Higher-is-better: Green ≥95% goal, Amber 80–95%, Red <80%. Lower-is-better: Green ≤105%, Amber 105–125%, Red >125%. RAG output includes explanation + recommended action.

---

## 12. Regional Adapters

`RegionAdapter` interface (TECH/04): `extract_net_revenue` (per-SKU tax), `classify_payment_method`, `is_high_risk_payment`, `map_shipment_status`, `compute_logistics_cost`, `normalize_postal_code`, `postal_code_metadata`, `get_seasonal_events`, `tax_reconciliation_report`, currency/timezone. Registered in `pylibs/brain_regional`; `get_adapter(region)`.

- **India (`IN`) — implemented first:** GST 2.0 (0/5/18/40) per-SKU extraction; INR lakh/crore; COD/prepaid fees; RTO cost model + state machine; pincode reliability (90-day, ≥5 shipments) + recommendations (block/restrict_cod/monitor); NDR tracking; festival calendar (Diwali/Navratri/Dussehra/Dhanteras/Holi/Eid/Onam/Rakhi/Republic Day/Independence Day/wedding/year-end) + per-brand learned lift; channel-specific compliance (DLT/NCPR/9am–9pm/WhatsApp opt-in). GST tax-reconciliation breakdown uses **0/5/18/40** (not legacy 5/12/18/28).
- **UAE/GCC (`AE/SA/BH/OM`) — Phase 4:** **per-country VAT (KSA 15%, UAE 5%, Bahrain 10%, Oman 5%; Qatar/Kuwait none)**; AED/SAR; emirate/region geo; Ramadan/Eid/White-Friday calendar; Arabic/RTL; BNPL (Tabby/Tamara); cross-border duties; UAE/KSA PDPL compliance.
- Adding a region = new adapter + seasonal seed + default alerts/costs + tests. The metric engine, frontend, intelligence, and notifications need **zero** changes.

---

## 13. Customer Lifecycle, RFM & LTV

States: New / Returning / Reactivated / At-Risk / Churned. **Brand-specific P40/P80** churn thresholds from actual order gaps (fallback flagged in UI). **RFMC** scored by percentile within the brand: R=recency, F=frequency, M=**CM2 contribution** (not gross), C=COD behavior (India). 11 canonical segments (Champions … Lost) + custom filters. LTV via **BG/NBD + Gamma-Gamma** (monetary = CM2/order); cohort survival via **Kaplan-Meier**; min 6 months + 500 repeat customers; monthly train; flag if MAPE>40%. (TECH/03, TECH/05.)

---

## 14. Lifecycle & Revenue Execution (`lifecycle-service`)

Makes Brain a **revenue centre**. Single-Primitive Rule: the **Audience** is built once and consumed by call/WhatsApp/email/SMS/ad-audience/referral. (TECH/11.)

- **Audience builder:** pick segment or custom filters → Brain returns size + modelled response + modelled recovery + recommended channel mix → one-click triggers all channels with per-customer routing (high-value→call, mid→WhatsApp, low→email). RFM = SQL (paradigm 1); response modelling = ML (paradigm 2); message personalization = Haiku (paradigm 3).
- **Channel routers** behind stable contracts; **AI calling vendor abstraction** (`CallProvider`: Bolna/Vapi/native — decision in TECH/11 §5; partner first, native if volume justifies).
- **Compliance engine (hard-coded, non-negotiable):** calling hours 09:00–21:00 IST (queue-level gating), two-layer DND (brand list + NCPR), consent re-verify before every send, AI-call disclosure + recording consent, DLT-registered templates per brand, 48h frequency cap. (Detail: TECH/16.)
- **Offer governance ladder** (business doc §11.4): no-discount → low-cost value-add → limited discount (CM2-positive only) → escalated retention → human review. Lifecycle is always **CM2-gated**.
- **Inbound inbox (Phase 3):** WhatsApp/IG-DM/email/web-chat unified; autonomous resolution for top-10 ticket types; human escalation.
- **Attribution:** placed / realized / incremental; recovered revenue attributed at 7d/30d into Decision Log; all surfaces show **realized** revenue + CM2, not just placed.

---

## 15. AI Ticket Management

Channels: WhatsApp, Instagram DM, email, web chat, custom webhook, marketplace messages (where APIs allow). Every ticket enriched with identity+consent, RFM/state, LTV, latest orders, shipment/payment/return status, prior tickets/CSAT, policy eligibility, suggested resolution + CM2 impact. 15 ticket types (business doc §12.2). Resolution flow: classify → pull commerce truth (deterministic lookup) → policy/permission check → estimate revenue/profit impact → autonomous if high-confidence + low-risk, else draft for human, else escalate → log outcome + CM2 + Decision Log. **Safety:** never invent delivery status; never promise refund/replacement outside policy; never reveal margin/scores; stop automation on human request; consent-gated; no irreversible financial action above cap. Support signals feed product/logistics/ads/lifecycle. (TECH/11 inbox + business doc §12.)

---

## 16. Intelligence Layer, Memory & Agents

### 16.1 Memory Layer (the moat — TECH/05)
Five subsystems: **Brand Fingerprint** (16-dim daily vector), **Condition-Outcome pairs** (pgvector — "find similar past conditions" on every tick), **Cross-Brand Benchmarks** (k≥5 anonymized), **Seasonal Codebook** (per-brand festival uplift), **Customer Segment Memory** (daily RFM). Almost all operations are paradigm-1/2 (SQL+ML) — compounding learning at SQL economics.

### 16.2 Daily Intelligence Loop (the heartbeat — SLO-critical)
| IST | Step |
|---|---|
| 06:55 | Data pull / freshness check |
| 07:00 | Brand Fingerprint built (SQL + numpy) |
| 07:05 | Memory query (pgvector top-K + cross-brand baseline) |
| 07:10 | Agents run in parallel; each returns priority score + recommended action; write Decision Log |
| 07:15 | Top-3 assembled; **Morning Brief synthesized by Sonnet** (the only frontier-LLM step); pushed 07:00–09:00 |
| 18:00 | Evening Pulse (actuals vs forecast) |
| 23:55 | 7d/30d outcome attribution backfills `condition_outcome` |
**SLO: Morning Brief delivered by 07:20 IST on >99.5% of days.**

### 16.3 Forecasting / anomaly / chat
Plan Module: aMER response curve (isotonic) + returning-revenue model × festival multiplier (Phase 1 simple → Phase 3 Prophet with festival regressors); target 15% MAPE @30d. Anomaly: z-score (festival-aware baseline) + Isolation Forest multivariate. AI Chat: Claude tool-use over deterministic metric tools (max 5 tool calls; 20-turn history; per-workspace budget). Predictive LTV: cohort-calibrated → BG/NBD+Gamma-Gamma. (TECH/05.)

### 16.4 Agent roster (TECH/14)
**AICMO (8):** Meta, Google, TikTok(GCC), Snap(GCC), Cross-Channel, Creative, Pricing, Festival. **AICOO (4):** Logistics, Returns, Inventory, Marketplace. **AICFO (3):** Conversion, Cashflow, Pricing-Margin. **AI CX:** triage/reply/resolution/escalation. Each agent: daily-tick + memory query + paradigm-appropriate model + Decision Log write + `@paradigm`/`@mcp_tool` decorators + graduation tracker. Cross-agent choreography via MCP; Morning Brief Synthesizer arbitrates conflicts (cashflow priority on material disagreement). Agents are recommendation-only until graduated. *(Reconciliation with BR §13.2: the business doc's 10 functional "specialist agents" — Morning Brief, Anomaly, Budget, Creative, Lifecycle, Support, RTO/Courier, Inventory, Plan, Pricing — are realized as this 15-agent domain roster (per-channel + per-function) plus the daily-tick/Morning-Brief orchestration and anomaly engine of §16.2–16.3. Same capabilities, finer decomposition — not a different set. Distinct, too, from the 11 **build-team** agents that construct Brain, see §29.)*

### 16.5 Sale / Event Mode — high-frequency monitoring (BR §8.6)

For sale events, launches, and festivals, Brain switches a workspace into **Event Mode** — a higher-frequency monitoring loop (the daily tick alone is too coarse). Owned by `intelligence-service` (pace models + anomaly) + `notifications-service` (alerts) + `web`/`mobile` (live surface).

- **Setup:** event goal, start/end window, channel plan, and an **expected revenue+CM2 forecast curve** (Plan Module + festival-lift factors, §12, TECH/04 §2.7).
- **During the event:** hourly (or sub-hourly) rollups of revenue + CM2 **pace** vs the expected curve; ad-spend pace; inventory pressure; COD/RTO risk by region; support/ticket spike.
- **Alerts:** fire if **hourly revenue drops materially vs pace**, OR **CM2 falls below the event threshold even if revenue rises** (the margin trap), OR inventory/COD risk crosses a bound.
- **Decision Log overlay:** every action taken during the event is tagged to the event for post-event compounding (what worked at this festival → seasonal codebook).
- **Implementation:** reuses the metric engine (Path A hourly rollup, §11), anomaly detection (§16.3), and the alert/push pipeline (TECH/08) — no new primitives; Event Mode is a higher-cadence configuration of existing ones (cost-routing respected: pace = SQL, anomaly = ML, narrative = Sonnet only at digest).

---

## 17. Cost-Routed Compute & Billing/Metering

### 17.1 Four paradigms (TECH/12) — the engineering invariant behind %-GMV pricing
SQL (paradigm 1, ~$0) ≫ ML (2, <$0.001) ≫ small LLM (3, ~$0.0005–0.005) ≫ frontier LLM (4, ~$0.05–0.50). **Cost ratio ≈ 1 : 100 : 1,000 : 10,000.** **Paradigms 3/4 are model-agnostic and implemented at runtime by the LiteLLM gateway:** the `@paradigm("small_llm"|"frontier_llm")` decorator names a routed *policy tier*, and the gateway routes to the **cheapest model that passes that tier's eval bar** (small tier → e.g. Nova/Gemini-Flash-Lite/Haiku; frontier → Claude Sonnet default, eval-gated + swappable). Every endpoint/agent declares `@paradigm`; PR is **blocked** if a cheaper paradigm would suffice. Three enforcement layers: default routing (gateway), per-feature token budget (soft 80% / hard 100% → degrade), per-workspace monthly cap as **gateway virtual-key budgets** (soft 70% throttle non-critical / hard 100% critical-path only: Morning Brief, NL query, ticket resolution). Target mix: **85% SQL · 12% ML · 2.5% small-LLM · 0.5% frontier-LLM**.

### 17.2 Billing & metering (new — TECH/15, business doc §15)
- **Base = realized/delivered GMV** (R5): `billable_gmv = placed_gmv − cancelled − RTO − refunds`. Computed monthly in `billing.gmv_meter` from ClickHouse delivered facts (RTO has up to ~30-day resolution lag → re-trued at month close).
- **Fee** = max(`gmv_pct × billable_gmv`, `min_monthly_fee`), then **capped** by the **CM2 affordability guardrail**: `fee ≤ cm2_cap_pct × CM2`. Tier %s: Launch ~1.0% / Growth ~0.75% / Scale ~0.5% (Enterprise custom).
- **Pass-through tracked** (LLM, messaging, call minutes, email, storage) in `billing.usage_passthrough`, bundled below per-brand caps; surfaced in a value-proof view (recovered revenue ÷ fee, CM2 recovered ÷ fee, operator time saved).
- **Activation period** before first invoice (aligned to Day 0–14 onboarding).

---

## 18. Auto-Execute & Guardrails

Auto-execute is **off by default**; Owner enables per action class. Initial actions + default confidence (business doc §14.2): pause ad 0.90 · reduce budget ≤X% 0.85 · abandoned-cart discount 0.80 · approved lifecycle send 0.85 · courier switch (high-RTO pincode) 0.85 · replacement-under-policy 0.90 · refund-under-cap 0.95 (irreversible → Owner) · draft PO 0.90. Guardrails: per-action enable, confidence threshold, daily count + value caps, consent + policy + data-freshness checks, irreversible-stricter, **global + per-action kill switch** (Owner pauses all within 60s; pausing doesn't stop recommendations), **auto-revert to recommend-only** if reversal/error rate crosses threshold, Decision Log + audit entry for every action. **Graduation** is per-tool, per-brand on outcome-accuracy + approval-rate + sample-size + reverse-rate thresholds with magnitude caps (TECH/14 §6).

---

## 19. API Contracts (TECH/06)

Three edge surfaces + internal:
- **tRPC** (web + mobile) over HTTPS; Supabase JWT; end-to-end types; SSE/WebSocket for AI chat + live dashboards. Mobile uses the **same** router (only additive: `registerPushToken`, `app.minVersion`, `featureFlags`). Procedure tiers: `public` → `authed` → `workspace` → `owner`. Cursor pagination (OFFSET banned in prod). Money fields are `bigint` minor units + `currency_code` (superjson).
- **gRPC** (internal, Protobuf via buf) — `WorkspaceService`, `MetricsService` (incl. `StreamMetricUpdates`), `IntelligenceService` (incl. bidi `Chat`), `NotificationsService`, `IntegrationsService`, `LifecycleService`. Metadata: `x-workspace-id`, `x-user-id`, `x-request-id`, `x-traceparent`; `TenancyInterceptor` rejects missing workspace.
- **MCP** (agent + partner) inside api-gateway, sharing auth/tenancy/rate-limit; tool schemas generated from the **same protos** (cannot drift); read tools (`brand_fingerprint`, `decision_log`, `rfm_segments`, `recovered_revenue_ledger`, `integration_health`, …) + action tools (`query_memory`, `propose_action`, `trigger_audience`, `log_external_decision`); every write tool auto-writes Decision Log via middleware; default scope read-only, write needs Owner/Operator consent. (TECH/13.)
- **Public REST** (Phase 4) = thin adapter over tRPC; hashed API tokens with scopes; HMAC-signed outbound webhooks.

Rate limits per user/workspace/tier in Redis + WAF. Errors: stable codes mapped gRPC→tRPC. Versioning: tRPC lockstep (no version); gRPC field-number evolution; Kafka `.vN`; REST `/v1` ≥12-month deprecation.

---

## 20. Frontend & Mobile

### 20.1 Web (TECH/07)
Next.js 16 App Router; Server Components default, Client Components for interactive charts/filters/chat; `createCaller()` server-side tRPC over the same path as the browser. State: TanStack Query (server) + nuqs (URL filters/date) + Redux Toolkit (UI/chat/drilldown). Design: shadcn + Tailwind tokens; Recharts + Visx (waterfall, cohort heatmap); currency-aware `formatMoney` (₹ lakh/crore vs locale). **Magic UI** (copy-paste, Tailwind + Motion — same shadcn ecosystem, zero runtime dep) is used **scoped to marketing / onboarding / login / empty-state / delight surfaces only — NOT the dense operator workbench** (dashboards stay shadcn + Visx/Recharts under the perf budget), and always respects `prefers-reduced-motion` + WCAG AA. Region-aware routing/sidebar. Hosting: managed (Amplify) Phase 0–2 → EKS Phase 3. Perf budget: LCP<2s, INP<200ms, CLS<0.1, route JS<100KB. WCAG AA. ~57-component library.

### 20.2 Mobile (TECH/10) — Morning Brief is the product
React Native + Expo; Expo Router tab nav; **Morning Brief screen is the highest-quality UI in Brain** — three signals, approve/reject/edit, three-minute thumb-first 06:55–09:00 IST flow. Phase 1 read-only (Home/Acquisition/Calendar/Insights/Alerts) + push; Phase 2 chat + approvals + biometric; Phase 3 plan/pincode + rich notifications; Phase 4 widgets/watch. Auth: refresh token in `expo-secure-store`, access token in memory, magic-link deep links; **cert pinning** (current + rotation pin); **MASVS L1 + key L2**; push via Expo (APNS+FCM) → `mobile_push_tokens`; offline = online-only Phase 1 → cached reads Phase 2 → optimistic queue Phase 3. EAS Build + OTA (JS-only) vs store review (native bump). Desktop-only views (cohort heatmap, waterfall filters, COGS bulk editor) link out gracefully.

---

## 21. Security, Privacy & Compliance (TECH/09, TECH/16)

### 21.1 Data Brain never stores
Card numbers, CVV, full UPI IDs, full bank accounts, plaintext passwords, national IDs (Aadhaar), sensitive special-category data, full customer addresses unless explicitly required+approved (default pincode/city-level), PII in logs.

### 21.2 PII handling
Hash email/phone by default; plaintext only where outreach is enabled + consent/legal basis exists. PII redaction at logger + Fluent Bit. Per-workspace KMS encryption for credentials/sensitive exports. Recordings only with consent. **India data stored in-region (ap-south-1) by default** (R8/R9; DPDP + KSA/UAE transfer restrictions); enterprise residency configurable.

### 21.3 Applicable regimes (consolidated — TECH/16)
- **India DPDP Act 2023 + Rules 2025** (phased to ~May 2027): consent-based processing, data minimization, retention limits, right to erasure, breach notification; Consent-Manager-compatible (registration ~Nov 2026).
- **India TCCCPR 2018 (amended 12 Feb 2025):** DLT registration for A2P SMS/voice, NCPR/DND scrubbing, **9am–9pm** promotional window.
- **UAE PDPL (45/2021) & KSA PDPL (enforced Sep 2024):** explicit revocable opt-in marketing, erasure, cross-border transfer restrictions.
- **Channel-specific outbound:** WhatsApp = Meta opt-in + approved templates + free service window (24h customer-service reply; 72h ad-click entry-point); SMS/voice = DLT + NCPR/DND + calling hours; AI voice = disclosure + human handoff.

### 21.4 Consent & audit
Consent primitive: per customer/channel/purpose/source/timestamp/region/withdrawal; append-only events; opt-out/withdrawn override all marketing. Cross-brand benchmarks: aggregate-only, k≥5, opt-in to contribute. Full audit log (§9.9). Compliance SLO: **0** DND/out-of-window violations, **0** cross-brand leaks.

---

## 22. Observability & SLOs (TECH/09)

One correlation ID (`request_id` + `trace_id` + `workspace_id` + `user_id`) propagates via HTTP headers → gRPC metadata → Kafka envelope. Stack: OTel → CloudWatch/X-Ray, Sentry (errors), PostHog (product), OpenSearch (logs, PII-redacted). Track: API p50/95/99, error rate, Kafka lag, connector freshness/duration, backfill progress, CH query duration/bytes, Redis hit rate, LLM tokens/cost by workspace+feature, agent run success, Decision Log write success, auto-execute count/failures/reversals, WhatsApp delivery/reply/conversion, ticket FRT/resolution/CSAT, DND/compliance violations.

| SLO | Target |
|---|---|
| P0 integration freshness | < 1 hour |
| Cached dashboard p95 | < 500ms |
| API p95 | < 2s |
| Morning Brief delivered | by 07:20 IST, >99.5% days |
| Decision Log write availability | > 99.99% |
| Agent daily run success | > 99% |
| Cross-brand leaks / compliance violations | 0 |
| Auto-execute reversal rate | < 8% (alert 15%) |

---

## 23. Roadmap (aligned to business doc §21)

| Phase | Ships | Exit |
|---|---|---|
| **0 Foundation** | 3-deployable footprint; auth + workspaces + RBAC; Shopify/Meta/Google/logistics/payments connectors; Postgres+ClickHouse+Redis+(MSK Serverless); integration health; daily metrics + CM waterfall; Decision Log schema; India adapter foundations; basic Morning Brief; audit log | One workspace: 7 days fresh data, every metric drills to source, Decision Log writes work |
| **1 Operator Wedge** | High-frequency Home; MER/aMER + acquisition classification; RTO/COD/pincode intelligence; RFMC; First-Product Cascade; customer states; Morning Brief (mobile primary); goals+RAG; freshness warnings | Brain is the daily surface; ≥1 recovery workflow live + measured |
| **2 Lifecycle & AI CX** | Split into 7 services; `lifecycle-service` (audience builder, WhatsApp + COD-confirm + abandoned-cart + winback + replenishment); compliance engine; unified inbox + AI triage/suggested replies + low-risk autonomous resolution; attribution ledger; provisioned MSK + Debezium CDC; EKS | Recovered revenue + support-protected CM2 visible; outcomes feed Decision Log |
| **3 Agentic Execution** | AICMO/AICOO/AICFO agents (alert→graduated); auto-execute policies + kill switch + reversal + outcome-accuracy dashboard; Plan/Prophet; creative intelligence; ClickHouse sharding | Outcome accuracy >80% auto-execute cohort; reversal <8%; no compliance incidents |
| **4 Scale & Enterprise / UAE-GCC** | UAE/GCC adapters + Salla/Zid/Noon/Namshi + Tabby/Tamara + Arabic/RTL; portfolio rollups; multi-region residency; SSO/SAML + SCIM; public API + webhooks; advanced benchmarking; native AI-calling decision; retail-aware extensions (POS / store-level) where demanded (BR §17.4) | First UAE/GCC brands onboarded region-correct; enterprise governance passes review; data isolation intact |

---

## 24. Business-Requirement → Technical-Fulfillment Map

| Business requirement (BR §) | Fulfilled by |
|---|---|
| Honest profit analytics, CM waterfall (§5.1, §6.2) | Metric engine §11 + ClickHouse §10 + TECH/03 |
| Regional commerce intelligence — RTO/COD/GST/pincode (§5.2, §17) | RegionAdapter §12 + TECH/04 |
| Decision memory / Decision Log / Brand Fingerprint (§5.3, §7) | `ai.decision_log` §9.3 + Memory Layer §16.1 + TECH/05 |
| Lifecycle as revenue engine, shared audience (§5.4, §11) | `lifecycle-service` §14 + TECH/11 |
| AI ticket management (§5.5, §12) | §15 + lifecycle inbox + TECH/11 |
| Safe agentic execution (§5.6, §14) | Auto-execute §18 + guardrails + Decision Log + TECH/14 |
| Metric/formula definitions (§6) | Metric registry §11 (TS↔Python parity) + TECH/03 |
| Goal RAG (§6.7) | §11.6 + goals table §9.2 |
| Product surfaces — Home/Morning Brief/Weekly/Month-end/NL query (§8) | Web §20.1 + Mobile §20.2 + intelligence §16 + notifications-service |
| Sale/Event Mode — high-frequency monitoring (§8.6) | §16.5 + metric engine §11 + alerts (TECH/08) |
| Integrations + health + freshness (§9) | §7 + TECH/02 |
| Analytics/reporting modules (§10) | analytics-service §4.2 + metric engine §11 |
| Lifecycle/WhatsApp + offer governance (§11) | §14 + compliance §21.3 + TECH/16 |
| Agent workflows / output contract / ranking (§13) | §16.4 + Decision Log + TECH/14 |
| Auto-execute + kill switch + audit (§14) | §18 |
| **Pricing — %-GMV, realized base, min fee, CM2 guardrail, no per-seat (§15)** | Billing/metering §17.2 + `billing.*` §9.8 + TECH/15 |
| Onboarding + cost setup + data-quality (§16) | **Onboarding & data-quality gate §7.5** + core-service + `core.cost_settings` + activation period §17.2 |
| Regional adapters (§17) | §12 + TECH/04 |
| GTM/CS/activation metrics (§18) | PostHog §22 + value-proof view §17.2 |
| Compliance/privacy/consent/audit (§19) | §21 + TECH/16 + `audit.audit_log` §9.9 |
| KPIs/success metrics (§20) | metric engine §11 + observability §22 |
| Risks & mitigations (§22) | freshness gates §7.4, cost-routing §17.1, guardrails §18, tenancy §6, CM2-gating §14 |

---

## 25. Definition of Done

A task is done only when it: uses Brain-only language; carries `workspace_id` isolation (4 layers); reuses shared primitives (no per-channel forks); writes to Decision Log if it's a recommendation/action/lifecycle send/support resolution/outcome; has RBAC checks; declares its `@paradigm`; uses minor-units money; handles regional behavior via adapter; has tests for success + permission-failure + stale-data + provider-failure + idempotency; emits structured logs + metrics with the correlation ID; degrades gracefully on missing/stale data; has reversal/rollback where possible; and is documented for the next builder.

---

## 26. Anti-Patterns to Reject (code-review blockers)

A per-channel audience/consent/attribution/profile fork · agent recommendations without Decision Log · lifecycle sends without attribution · LLM-generated metric numbers · region-specific forks of metric code · NUMERIC/float money · single blended tax rate (must be per-SKU slab) · billing on placed (not realized) GMV · integration "healthy" because auth works but data is stale · auto-execute without kill switch · frontier-LLM where SQL/ML suffices (paradigm bypass) · `controllers/`-style technical-layer folders · OFFSET pagination in prod · cross-brand data visible to another brand.

---

## 27. Glossary

AICMO/AICOO/AICFO — marketing/operations/finance agent groups · aMER — new-customer revenue ÷ acquisition spend · Brand Fingerprint — 16-dim daily brand-state vector · CM1/CM2/CM3 — contribution margins · Decision Log — append-only recommendation/action/outcome memory · GMV (billable) — realized/delivered GMV net of RTO/refunds (billing base) · GST 2.0 — India 0/5/18/40 slabs · MER — net revenue ÷ marketing spend · NDR — non-delivery report before RTO · paradigm — SQL/ML/small-LLM/frontier-LLM cost tier · PDPL/DPDP/TCCCPR/DLT/NCPR — privacy + telecom compliance regimes · RFMC — recency/frequency/monetary(CM2)/COD-behavior · RTO — return to origin · Single-Primitive Rule — every cross-cutting concern built once · True CM2 — CM2 adjusted for delivery/RTO/refund/payment leakage · Workspace — one brand tenant.

---

## 28. TECH/ Deep-Dive Index

`00` tech-stack decision & phasing · `01` data architecture (Postgres+ClickHouse) · `02` integrations & Kafka ETL · `03` metrics engine · `04` regional adapters · `05` intelligence layer & memory · `06` API contracts · `07` web frontend · `08` alerts/reporting/notifications · `09` security & observability · `10` mobile architecture · `11` lifecycle & revenue layer · `12` cost-routed compute · `13` MCP protocol · `14` agent roster · `15` billing & metering (new) · `16` compliance engine (new) · `17` engineering operating model — the AI team that builds Brain (new) · `18` service architecture — per-service operational spec (responsibilities/boundary/modules/comms/data-flow/scale/security/real-time/failure across all 7 services + the cross-service comms matrix + E2E flows + forward extensions) (new).

---

## 29. Engineering Operating Model (how Brain is built)

Brain is built by an **AI engineering team** delivered as a Claude Code plugin — the **Engineering OS** (full spec: `TECH/17`). This is the meta-layer that executes this document; it is **not** the product's agent roster (§16.4 / `TECH/14`), which runs *inside* Brain for customers.

- **Two phases.** *Phase 0 (one-time):* the founder hands over the BRD + TRD; Rohan (CTO Advisor) + Aryan (Architect) synthesize the `knowledge-base/`; the founder runs `/approve-foundation`, which writes the gate sentinel. *Recurring pipeline (per requirement):* an 8-stage flow — **1** intake+brainstorm (Rohan) → **2** binding plan (Aryan, `06-architecture-plan.md`) → **3** build (devs) → **4** security review (VETO) → **5** QA (VETO) → **6** final review (Rohan, VETO) → **7** deploy gate (founder `/approve`) → **8** deploy + 48h monitor + auto-rollback (platform-devops).
- **11 agents.** Rohan + Aryan (pre-named, opus) co-lead; security-reviewer (opus); backend / frontend-web / mobile / intelligence developers, qa-agent, platform-devops, product-manager (sonnet, named by Phase 0's `team-roster.md`); dynamic-persona-generator (sonnet). Model pins per `TECH/00`.
- **Plan-binding.** Stages 3–8 execute the Stage-2 binding plan; deviations go through Aryan's plan-amendment loop — never freelancing. PLAN-phase web research is allowed in Phase 0 + Stages 1–2 only.
- **Founder touchpoints — the entire surface area:** files BRD+TRD · `/approve-foundation` · files each requirement · responds to rare rubric-gated `/escalate` with `/decide` · runs the Stage-6 commit command · `/approve` or `/reject` at Stage 7. Nothing else.
- **Memory is the moat.** Shared state lives at `${CLAUDE_PROJECT_DIR}/.engineering-os/`, committed to git. Brain's approved foundation **is** these Brain-docs (`business-requirements.md` = BRD; this doc + `TECH/` = the knowledge-base — full mapping in `TECH/17` §9).
- **Traceability** (OS VETO surface) = Brain's observability spine (§22 + `TECH/09`); **compliance** regime = `TECH/16`; **cost** discipline = `TECH/12`.

## 30. Final Builder Instruction

Build Brain as the operator's profit command system: tell the brand what changed, why it matters, what to do, whether Brain can safely do it, and what happened after. The product compounds only if the Decision Log compounds. Build the **invariants** (tenancy, minor-units, Decision Log, region-adapter, metric registry, cost-routing, proto contracts, OLTP/OLAP split) from day one; run the **infrastructure** at the smallest footprint that serves current scale and graduate each heavy layer only when its trigger fires (TECH/00). If a local shortcut conflicts with this document or TECH/00, this document wins.
