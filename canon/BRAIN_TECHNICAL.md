# BRAIN — Consolidated Technical Document

> **⚠️ BUSINESS CONTEXT RESET — read first.** This is now a **technical engineering team with no business context.** The product's business/domain was cleared (`BRAIN_BUSINESS.md` is blank). The **technical architecture, stack, and patterns in this document stand** — they're engineering decisions. But everything here that encodes the *old business/domain* — the daily-intelligence-loop narrative, the specific product-agent roster (the 15 AICMO/AICOO/AICFO agents), domain economics (RTO/COD/GST/festivals), pricing (GMV %), telecom/compliance specifics, "the moat", and the commerce-specific framing of the service map — is **stale/illustrative** and must be **re-derived from the new business canon** when re-fed. Do **not** treat any business/domain statement below as current. The condensed primer agents actually load is `docs/technical-context.md`.
>
> **Document version:** 1.0 (Consolidated) · **Companion:** `BRAIN_BUSINESS.md` (RESET — being re-fed)

---

## 0. About This Document & Conflict Resolution Log

This is the single source of truth for **Brain's technical realization** — architecture, services, data, formulas, integrations, build phases, infrastructure, security, observability, scale.

It is the consolidation of five prior technical source documents that contradicted each other on important points. Conflicts were resolved using these rules:

1. **Most recent date wins** for architecture decisions.
2. **Technical Document v2.0 (PDF/MD, 2026-05-13) is authoritative for system architecture** — microservices, AWS, Kafka, ClickHouse, EKS, gRPC, Python+TypeScript split.
3. **Brain-Technical-Brief (May 2026) is authoritative for product strategy** that the technical doc references — Memory Layer, Agent Layer, Lifecycle Layer, MCP, cost-routed compute, streamlining principles, agentic commerce 30-day commitment.
4. **brain-platform-complete-spec (March 2026) is authoritative for product formulas and feature specs** — MER/aMER/CM math, RFM segmentation, BG/NBD LTV, Plan Module, RTO/COD/Pincode/Festival mechanics.
5. **TECHNICAL_ARCHITECTURE.md + PROJECT_SCOPE.md (Looqus, 2026-05-04)** describe the **existing codebase** on `kushal-app` branch (Next.js 16 + Supabase + Prisma + Vercel-style serverless). This is the **v1 reality** that Phase 0 of the new architecture either evolves from or rebuilds. The existing codebase contains valuable working logic (COGS engine, P&L bucketing, AI engine with Claude integration, OAuth flows for Meta/Google/Shopify/Shiprocket/Klaviyo, customer-lifecycle module). That logic gets ported into the new microservices.
6. **Brand name is BRAIN.** Sugandh Lok / Kumkumadi Face Oil / Sandalwood Soap are *illustrative examples* of any onboarded brand.

### Conflicts resolved (technical summary)

| # | Topic | Conflict | Resolution |
|---|-------|----------|-----------|
| 1 | Architecture pattern | Next.js monolith (Looqus) vs Microservices on AWS (v2.0) | **Microservices on AWS.** Looqus codebase logic ports into the new services during Phase 0/1. |
| 2 | OLAP store | Postgres-only with materialized views vs Postgres + ClickHouse | **Postgres (OLTP) + ClickHouse (OLAP).** Dashboards read ClickHouse; OLTP stays Postgres. |
| 3 | Event streaming | None (direct DB writes) vs BullMQ vs Kafka | **Apache Kafka via Amazon MSK.** BullMQ explicitly rejected (no replay, no schema registry). |
| 4 | Hosting | Vercel vs Supabase-only-then-AWS vs AWS EKS | **AWS EKS (Karpenter for nodes).** Supabase Postgres is *only* the managed Postgres layer. |
| 5 | Service-to-service comms | REST/Next.js API routes vs gRPC | **gRPC internal, tRPC external** (frontend ↔ api-gateway). |
| 6 | Language stack | All TypeScript (Looqus) vs TS + Python split | **TypeScript** for api-gateway, core-service, notifications-service, frontend. **Python** for ingestion-service, analytics-service, intelligence-service. Boundary enforced. |
| 7 | LLM provider | Claude Sonnet 4 + Opus 4 vs Claude Sonnet 4.6 + Haiku 4.5 | **Claude Sonnet 4.6 + Haiku 4.5** with prompt caching. Haiku for narrow tasks; Sonnet for strategic synthesis. |
| 8 | Auth provider | Supabase Auth vs Cognito | **Supabase Auth** (co-located with Postgres RLS). |
| 9 | Frontend version | Next.js 16.1.6 (Looqus) vs Next.js 14+ (v2.0) | **Next.js 14+ (App Router).** The v2.0 doc was written before Next 16; we adopt latest stable at build time. |
| 10 | OAuth token storage | Plaintext (Looqus today) vs encrypted | **AES-256-GCM application-layer encryption** with per-brand key from AWS Secrets Manager. |
| 11 | Role enforcement | Inconsistent (Looqus today) vs `requireRole()` everywhere | **Standard `requireRole()` guard** at every gRPC handler. |
| 12 | Background jobs / cron | External cron + scripts (Looqus) vs EventBridge Scheduler | **EventBridge Scheduler.** |
| 13 | Order data store | Source-table queries (Looqus) vs pre-computed daily rollup | **ClickHouse materialized views** computed by analytics-service from Kafka events. |
| 14 | AI engine | Single Next.js module (Looqus) vs intelligence-service | **intelligence-service** (Python) — port AI engine logic from existing `module/ai-engine/`. |
| 15 | Notifications | In-app only (Looqus) vs multi-channel (email + push + WhatsApp + Slack) | **notifications-service** handles all channels; SES + Gupshup + APNs/FCM + Slack webhooks. |
| 16 | Build phases | 28-week roadmap vs Phase 0–4 weeks | **Phase 0 (W1–4 Foundation), Phase 1 (W5–12 Wedge), Phase 2 (W13–22), Phase 3 (W23–36), Phase 4 (W37+).** |
| 17 | Dead code modules | `module/ai/`, `lib/ai-calc/`, `lib/insights/`, `WorkspaceAiInsightsCache`, populated-but-unused `WorkspaceDailyMetrics` table | **Delete during Phase 0 migration.** Active equivalents move into `analytics-service` and `intelligence-service`. |
| 18 | Customer scope | Just small DTC (₹50L–₹50Cr) vs enterprise too (user clarification 2026-05-17) | **Full DTC spectrum from line 1.** Architecture supports Small (₹50L–₹3Cr/month), Mid-Market (₹3Cr–₹50Cr/month), and Enterprise (₹50Cr+/month or multi-brand holding co with 3+ brands) from launch. Enterprise Variant features (private data warehouse / BYO-VPC, custom model fine-tuning, EU/US data residency, custom SLA) are **available from launch via sales-led motion** — only the *managed* enterprise tier ramp is gated to Phase 3/4. Scale design (Section 35) is sized for global multi-tenant at 100k req/min with per-tenant capacity sized for enterprise volumes (50M+ orders, 10K+ products, 100+ ad accounts per Brand). |
| 19 | Geographic scope | India-only vs global | **Global product from line 1, sequenced India-first.** Every region-specific economic lives behind a `RegionAdapter` interface (India in Phase 0–1; GCC in Phase 1 parallel build; US/EU in Phase 4; LATAM/SEA/Africa Phase 5+). Adding a region = implementing the interface, not rewriting the engine. Multi-region deployment infrastructure (per-workspace `home_region`, cross-region replication via DMS / MirrorMaker 2 / S3 CRR) **designed from Phase 0; activated in Phase 4**. |
| 20 | Multi-brand support | Single-brand workspace vs multi-brand holding co vs agency | **Four account structures supported from line 1 (Models A/B/C + Enterprise Variant overlay D).** Hierarchy: Organisation → Brand (= Workspace) → Store(s) → Users. Pricing per Brand, never per User. Cross-brand portfolio rollups (Tier 3) computed at runtime from isolated per-Brand data stores — never via mixed queries. Agencies cannot see each other's clients. |

The full conflict trail is in this section so future engineers can audit every architectural decision back to its source.

---

## Table of Contents

1. Architectural Principles
2. Three-Layer Conceptual Architecture (Data / Memory / Agentic)
3. Five-Layer Operational Architecture
4. High-Level System Architecture
5. Service Map (Six Services)
6. Tech Stack & Rationale
7. Monorepo Structure
8. Communication Patterns (gRPC + Kafka)
9. Multi-Tenancy & Data Isolation
10. Data Architecture (Postgres OLTP)
11. Data Architecture (ClickHouse OLAP)
12. Data Architecture (S3 + Redis + Kafka tiered storage)
13. Integration Architecture
14. Metric Engine & Formula Book
15. India Regional Adapter
16. Customer Lifecycle Engine
17. RFM / RFMC Segmentation Engine
18. LTV Prediction Engine (BG/NBD + Gamma-Gamma)
19. Forecasting (The Plan Module)
20. Anomaly Detection
21. Lifecycle Layer (Audience Builder + Multi-Channel Execution)
22. AI Calling Architecture
23. Native Email Engine
24. Agentic Creative Intelligence
25. Agent Layer (AICMO / AICOO / AICFO)
26. 30-Day Agentic Commerce (Auto-Execute)
27. MCP Server Surface
28. API Contracts (gRPC Internal + tRPC/REST External)
29. Frontend Architecture
30. Cost-Routed Compute Paradigm
31. Streamlining Principles (Single Primitives)
32. Privacy & Compliance Implementation
33. Auth & Authorization
34. Observability & Monitoring
35. Scale Design (Path to 100k req/min)
36. Multi-Region Deployment
37. AWS Service Inventory & Cost Class
38. Local Development
39. Ownership Matrix
40. Build Phases & Roadmap
41. Migration Plan from Existing Codebase (Looqus)
42. Technical Debt Inventory
43. Glossary

---

## 1. Architectural Principles

These are non-negotiable. Every service must respect them.

1. **Multi-tenant from line 1.** Every record carries `workspace_id`. Every query filters by it. Postgres RLS for OLTP; ClickHouse uses `workspace_id` as first column of primary key + per-query enforcement.

2. **Source data is immutable. Derived data is rebuildable.** Raw events from sources land in Kafka topics with infinite retention (S3-backed). Every downstream materialization can be replayed from event streams.

3. **Events are the spine. Services are the muscles.** Services communicate state changes via Kafka events. Direct service-to-service calls are reserved for synchronous query paths.

4. **Each service owns its data.** A service may not query another service's database directly. Cross-service data flows via published events or gRPC APIs.

5. **OLTP and OLAP separated.** Postgres for transactions (workspaces, members, settings, recent canonical state). ClickHouse for analytics (time-series, aggregates, customer histories, all dashboard reads).

6. **Compute close to data, expose far from it.** Heavy aggregations run as ClickHouse materialized views or scheduled jobs — never in API request handlers. API queries hit pre-aggregated tables in <100ms.

7. **AI is a feature, not the foundation.** All metrics must be computable and explainable without LLMs. The LLM layer enriches and summarizes — it does not invent numbers.

8. **Regional adapters, not regional forks.** India-specific economics (RTO, COD, GST, pincode) live behind a `RegionAdapter` interface. Adding a region = implementing the interface, not rewriting the metric engine.

9. **Stateless services, horizontal scale.** Every backend pod can be killed at any time without state loss. State lives in Postgres, ClickHouse, Kafka, Redis, S3.

10. **Operators must be able to audit every number.** Every aggregate must be drillable to the underlying rows. Auditability is a hard constraint, not a Phase 2 feature.

11. **Backfill and live are the same code path.** No "historical loader" vs "live syncer" dichotomy. Same connector code; bounded vs unbounded window mode.

12. **Cost-aware scale.** Design for 100k req/min from day 1; ramp infra spend with revenue. Cluster sizing parameterized; no over-provisioning before traffic justifies.

13. **Memory is the moat.** Every architectural decision should preserve and extend the brand's decision-outcome history. Decision Log is the highest-protected store.

14. **Use the lightest tool that works.** SQL > ML > Small LLM > Frontier LLM, by cost and reliability. See Section 30.

15. **Streamlining: single primitives.** Audience, Decision Log, Consent, Notification, Attribution, Identity resolution — each built once, consumed everywhere. See Section 31.

---

## 2. Three-Layer Conceptual Architecture (Data / Memory / Agentic)

This is the strategic frame for understanding Brain. Maps cleanly to services in Section 5.

### Layer 1 — Data Layer (Live)
Normalized signals from connected platforms. The data layer is the **prerequisite, not the product.** Every commerce tool has one.
- **Owners:** ingestion-service, analytics-service
- **Stores:** Kafka raw event topics, ClickHouse raw event archive, S3 backup, Postgres canonical OLTP state
- **Phase 1 sources:** Shopify, Meta Ads, Google Ads, Shiprocket, Razorpay
- **Phase 2+ sources:** WooCommerce, Salla, Zid, Amazon SP-API, Flipkart, Myntra, Nykaa, Noon, Blinkit, Zepto, Klaviyo, TikTok, Snapchat, Unicommerce, GoKwik

### Layer 2 — Memory Layer (Building)
Multi-timescale embeddings of brand performance, customer cohorts, market patterns across the Brain network, and decision-outcome history. **This is where the moat lives.** Compounds over time and becomes harder to replicate the longer a brand stays on Brain.

Six memory domains:
1. **Brand Fingerprint** — multi-timescale vector capturing the brand's seasonal patterns, channel efficiency curves, customer cohort behaviour, CM2 trajectory
2. **Condition-Outcome Pairs** — historical conditions matched against historical outcomes
3. **Decision Log** — every Brain recommendation, user response (approve/reject/edit), 7-day and 30-day outcome. Immutable. The most-protected store.
4. **Cross-Brand Benchmarks** — aggregated, anonymized statistics from the Brain network
5. **Seasonal Codebook** — per-brand seasonal indices computed from 2+ years of data
6. **Customer Segment Memory** — RFM segments, lifecycle states, predicted LTV per customer

**Stores:** Postgres `memory` schema, ClickHouse `memory_*` tables, pgvector inside Postgres for similarity matching (cosine search over Brand Fingerprint).

### Layer 3 — Agentic Layer (Next)
Three executive agents — AICMO, AICOO, AICFO — each with sub-agents per platform/domain. They read the Context Vector and query Memory. Each agent produces one output: a priority score plus a recommended action. Agents run in parallel every morning. Human-in-the-loop in the founding cohort phase; graduating to auto-execute (Section 26).

- **Owners:** intelligence-service hosts agent execution; analytics-service provides metric queries via gRPC
- **Communication:** internal MCP between agents (Section 27)

---

## 3. Five-Layer Operational Architecture

Read bottom-up. This is the runtime view of Brain.

| Layer | Name | Function | Status |
|-------|------|----------|--------|
| **L5 (bottom)** | Data Layer | Live integrations + raw data normalised daily. | Live |
| **L4** | Memory Layer | Six memory domains (above). | Building |
| **L3** | Context Layer | Generates the **Business Moment Vector** each morning: 16 signals across time, performance, market, operations, customer state. Conditions, not histories. | Building |
| **L2** | Agent Layer | 7 specialist agents read the Context Vector and query Memory. Each produces a priority score + recommended action. Agents run in parallel every morning. | Next |
| **L1 (top)** | Interface Layer | Morning Brief (phone), web app, evening pulse (18:00 IST), month-end compound report. | Live (basic) |

### The Daily Intelligence Loop (End-to-End, One Calendar Day)

| Time (IST) | Step |
|------------|------|
| 06:55 | Data pull. All live integrations synced. Yesterday's actuals committed to OLTP + ClickHouse. |
| 07:00 | Vector generation. The 16-dimension Business Moment Vector is built for each brand. |
| 07:05 | Memory query. pgvector cosine similarity finds closest historical conditions for this brand and category. |
| 07:10 | Agent processing. All 7 agents run in parallel. Each returns priority score + recommended action. |
| 07:15 | Morning Brief assembly. Top 3 priority actions selected. Brief written and sent to phone. |
| Throughout day | Approve/reject flows back into Decision Log. Outcomes auto-logged at 7-day and 30-day windows. |
| 18:00 | Evening pulse. Day's actuals vs forecast, exceptions flagged. |
| 08:00 next morning | Daily email digest sent (longer form than phone Brief). |
| Month-end | Compound report. What worked, what didn't, what the system learned. |

---

## 4. High-Level System Architecture

```
                                         Internet
                                            │
                              ┌─────────────┴──────────────┐
                              │   Route 53 + CloudFront    │
                              │   (DNS + CDN + WAF)        │
                              └─────────────┬──────────────┘
                                            │
                              ┌─────────────┴──────────────┐
                              │   AWS Application LB       │
                              │   (with AWS WAF, Shield)   │
                              └─────────────┬──────────────┘
                                            │
                              ┌─────────────┴──────────────┐
                              │    api-gateway service     │
                              │   (Node, BFF for frontend) │
                              │   - Auth check (Supabase)  │
                              │   - Rate limit (Redis)     │
                              │   - tRPC + REST + SSE      │
                              │   - Aggregates downstream  │
                              └──┬──────────────────────┬──┘
                                 │ gRPC                 │ gRPC
                ┌────────────────┼──────────────┬──────┼─────────────────┐
                │                │              │      │                  │
        ┌───────▼──────┐ ┌──────▼───────┐ ┌────▼──────▼────┐ ┌──────────▼──────┐
        │ core-service │ │ analytics-   │ │ intelligence-  │ │ notifications-  │
        │   (Node)     │ │ service      │ │ service        │ │ service         │
        │              │ │ (Python)     │ │ (Python)       │ │ (Node)          │
        │ Workspaces,  │ │ Metrics      │ │ Forecasting,   │ │ Alerts, digests,│
        │ users,       │ │ engine,      │ │ anomaly,       │ │ exports, channel│
        │ settings,    │ │ ClickHouse   │ │ proactive AI,  │ │ orchestration   │
        │ goals,       │ │ queries      │ │ Claude orch.,  │ │                 │
        │ campaigns    │ │              │ │ agents         │ │                 │
        └───────┬──────┘ └──────┬───────┘ └────┬───────────┘ └──────┬──────────┘
                │               │              │                     │
        ┌───────▼───────────────▼──────────────▼─────────────────────▼──────────┐
        │                          KAFKA (Amazon MSK)                            │
        │  Topics:                                                                │
        │    integrations.orders.v1          analytics.metrics.daily.v1           │
        │    integrations.shipments.v1       analytics.customer_state.v1          │
        │    integrations.ads.v1             intelligence.insights.v1             │
        │    integrations.refunds.v1         intelligence.anomalies.v1            │
        │    integrations.customers.v1       intelligence.actions.executed.v1     │
        │    operations.workspace.changed.v1 notifications.alerts.fired.v1        │
        │    operations.settings.changed.v1  notifications.digest.sent.v1         │
        │    operations.goals.changed.v1     lifecycle.outreach.v1                │
        │                                    lifecycle.ticket.v1                  │
        └───────────────────────────┬─────────────────────────────────────────────┘
                                    │
                  ┌───────────────────────────┐
                  │ ingestion-service         │
                  │ (Python)                  │
                  │ Connectors:               │
                  │   Shopify, Meta Ads,      │
                  │   Google Ads, Shiprocket, │
                  │   Klaviyo, Razorpay (P1)  │
                  │   Amazon, Flipkart, etc.  │
                  │   (P2+)                   │
                  └───────────────────────────┘

  Data Stores:
  ┌──────────────────────────┐    ┌─────────────────────────┐    ┌───────────────────┐
  │  Supabase Postgres       │    │  ClickHouse Cloud (AWS) │    │  S3               │
  │  (RDS-managed, AWS)      │    │  or self-hosted on EKS  │    │  Raw event archive│
  │  • OLTP                  │    │  • OLAP                 │    │  Exports, uploads │
  │  • Auth + RLS            │    │  • Time-series          │    │  Kafka tiered     │
  │  • Workspaces, users     │    │  • daily_metrics        │    │    storage backend│
  │  • Integrations config   │    │  • Raw event store      │    └───────────────────┘
  │  • Goals, alert rules    │    │  • customer_states      │
  │  • Memory (pgvector)     │    │  • cohort_aggregates    │    ┌───────────────────┐
  │  • Decision Log          │    │  • pincode_reliability  │    │  ElastiCache Redis│
  │  • Recent orders mirror  │    │  • cross_brand_         │    │  • Rate limits    │
  │                          │    │    benchmarks           │    │  • Session cache  │
  └──────────────────────────┘    └─────────────────────────┘    │  • Hot metric     │
                                                                   │    cache          │
  External:                                                        │  • Idempotency    │
  ┌──────────────────────────┐    ┌─────────────────────────┐    └───────────────────┘
  │  Anthropic Claude API    │    │  AWS SES / Gupshup       │
  │  Sonnet 4.6 + Haiku 4.5  │    │  Email / WhatsApp        │
  │  Prompt caching          │    │                          │
  └──────────────────────────┘    └─────────────────────────┘
```

### Why Microservices + Monorepo

**Microservices because:**
- Independent scaling: ingestion can run 20 pods, analytics can run 5, intelligence can run 2
- Failure isolation: a hung Claude call doesn't block the dashboard
- Per-service language choice: Node for I/O-heavy, Python for analytics/ML
- Independent deploys: ship a metrics fix without redeploying the world

**Monorepo because:**
- Shared types (protobuf for cross-language contracts, TS packages for cross-TS contracts)
- Atomic refactors across services
- Single CI pipeline orchestrates
- Documentation, infra-as-code, migrations live alongside service code

### Why Two Languages (TypeScript + Python)

- **TypeScript:** api-gateway, core-service, notifications-service, frontend. Strong I/O ecosystem; type safety with frontend.
- **Python:** ingestion-service, analytics-service, intelligence-service. Best ecosystem for ETL (pandas, requests), data math (numpy, scipy, scikit-learn), forecasting (Prophet, statsmodels), and Anthropic SDK.

Boundary is enforced: **TS services never do heavy math; Python services never serve user-facing latency-critical paths.**

---

## 5. Service Map (Detailed)

Six backend services + frontend. Each service has:
- Its own deploy pipeline
- Its own ECR image
- Its own EKS namespace
- Its own Postgres schema (where applicable)
- Its own Kafka consumer group(s)
- Its own metrics namespace
- One designated engineer-owner

### 5.1 api-gateway (Node, TypeScript)

**Purpose:** the single entry point for the frontend. Aggregates and orchestrates downstream services.

**Responsibilities:**
- Auth verification (validates Supabase JWT)
- Multi-tenant context resolution (sets `workspace_id`)
- Rate limiting (Redis-backed sliding window)
- Request fan-out to downstream services (parallel gRPC calls)
- Response shaping for the frontend (BFF pattern)
- WebSocket/SSE for streaming (AI Chat, live metric refreshes)
- CORS, request validation, error normalization

**Scale:** stateless. 4–40 pods (HPA auto-scaled). Each Node pod handles ~500 RPS comfortably.

**Owns no data.** Only orchestrates.

### 5.2 core-service (Node, TypeScript)

**Purpose:** OLTP system of record. Workspaces, users, members, integrations, settings, configurations.

**Responsibilities:**
- Workspace CRUD
- User membership & roles (Owner / Operator / Analyst / Agency / Read-only)
- Integrations config (OAuth tokens, AES-256-GCM encrypted at write-time)
- Cost settings (COGS per SKU, variable costs, misc fixed expenses, founder salary)
- Campaign classifications (Acquisition / Non-Acquisition / Brand / Unclassified)
- Goals & alert rules
- Marketing actions log (operator-entered)
- Festival events
- Publishes `operations.*` Kafka events on every mutation

**Data:**
- Postgres (Supabase) `core` schema: primary OLTP store
- Publishes events to Kafka
- Uses Prisma as ORM

**Scale:** 2–10 pods. Workload mostly cached reads (Redis); writes rare and small.

### 5.3 ingestion-service (Python)

**Purpose:** all external data ingestion. One service, many connectors.

**Responsibilities:**
- Per-workspace, per-integration sync jobs (scheduled via EventBridge Scheduler)
- OAuth token refresh (with retry + alerting on failure)
- Idempotent fetch + UPSERT to raw event store
- Canonicalization: raw vendor payload → canonical event
- Publishes to Kafka: `integrations.orders.v1`, `integrations.shipments.v1`, `integrations.ads.v1`, `integrations.refunds.v1`, `integrations.customers.v1`
- Webhook receivers for Shopify (HMAC-validated), Shiprocket, Razorpay

**Connectors (Phase 1 commitment):**
- Shopify (OAuth 2.0 + GraphQL Admin API 2025-01 + Webhooks)
- Meta Ads (OAuth 2.0 + Graph API v22.0)
- Google Ads (OAuth 2.0 + PKCE + GAQL)
- Shiprocket (credential-based REST + webhook)
- Klaviyo (API key + REST v2023-10)
- Razorpay (API key + webhook)
- WooCommerce (REST API v3, consumer key/secret)

**Connectors (Phase 2+):**
- Amazon SP-API (India + AE), Flipkart Marketplace Seller API v3.0, Myntra (gated API + Gmail OAuth + LLM PDF fallback), Ajio (same), Nykaa (Gmail+PDF only), Meesho (gated), Noon (mature REST), Namshi/Ounass (Gmail+PDF), Blinkit/Zepto/Instamart (Gmail+PDF), BigBasket (gated API), Salla/Zid (native API for KSA), Unicommerce, Eshopbox, TikTok Ads, Snapchat Ads

**Data:**
- ClickHouse: raw event archive (forever)
- S3: backup of raw payloads (forever, tiered to Glacier after 90 days)
- Kafka: outbound canonical events

**Scale:** 4–30 pods. Workload is bursty around backfills.

**Why one service for all connectors:** shared retry, rate-limit, OAuth machinery. Splitting per-connector adds operational cost without proportional benefit at our stage.

**Integration quality gradient (engineering honesty):**
- **Green (clean API):** Shopify, WooCommerce, Salla, Zid, Amazon (India/AE), Flipkart, Noon, BigBasket (gated), Razorpay, Meta Ads, Google Ads. Build with confidence and test rigorously.
- **Yellow (gated API requiring per-brand onboarding):** Myntra, Ajio, Meesho, Namshi, Talabat. Build the connector, then onboard per-brand as access is granted.
- **Red (no API, workaround required):** Nykaa, Blinkit, Zepto, Instamart, Ounass. Workaround integrations using Gmail OAuth + LLM PDF parsing of seller portal exports. Brittle by definition. Monitor health continuously; notify brand within 1 hour of breakage; UI disclaimer for Red integrations.

### 5.4 analytics-service (Python)

**Purpose:** metric engine. Computes all dashboards.

**Responsibilities:**
- Listens to `integrations.*` topics; updates ClickHouse aggregates
- Materializes daily_metrics, cohort_aggregates, first_product_attribution, pincode_reliability
- Serves metric queries via gRPC to api-gateway
- Runs nightly compute jobs (customer states, churn thresholds via P40/P80, regional analytics, RFM scores)
- Publishes `analytics.*` events on materialization completion

**Data:**
- ClickHouse: primary read/write
- Postgres: read-only access to settings via gRPC to core-service
- Redis: hot metric cache (60s TTL, ~99% hit rate target)

**Scale:** 3–20 pods. Heavy compute, light per-request.

### 5.5 intelligence-service (Python)

**Purpose:** the Level 3 + Level 4 brain. Forecasting, anomaly detection, AI insights, AI Chat, agent orchestration.

**Responsibilities:**
- Plan Module forecasting (Prophet, isotonic regression)
- Anomaly detection (z-score, isolation forest, EWMA for creative)
- Daily proactive insight generation (Claude with prompt caching)
- AI Chat with tool use (queries analytics-service via gRPC)
- Budget allocation recommendations
- Agent execution (AICMO / AICOO / AICFO + sub-agents)
- LTV model training (BG/NBD + Gamma-Gamma via `lifetimes` library)
- Brand Fingerprint embedding generation
- pgvector similarity search for condition-outcome matching
- Internal MCP server endpoints for agent-to-agent communication

**Data:**
- ClickHouse (read-only): historical metrics
- Postgres (read-only via core-service): config
- Postgres (own schema `ai`): insights, chat history, forecasts, anomalies, agent recommendations, Decision Log entries
- Postgres (own schema `memory`): Brand Fingerprint embeddings, condition-outcome pairs, seasonal codebook
- Anthropic Claude API (external)

**Scale:** 2–10 pods. LLM-bound; throughput limited by Claude rate limits.

### 5.6 notifications-service (Node, TypeScript)

**Purpose:** all outbound communications. Alerts, digests, exports, lifecycle channel execution.

**Responsibilities:**
- Consumes `intelligence.anomalies.v1`, `intelligence.insights.v1`, `analytics.metrics.daily.v1`, `lifecycle.outreach.v1` topics
- Threshold evaluation against alert rules
- Daily/weekly/monthly digest composition
- Multi-channel dispatch: SES (email), Slack (webhook), Gupshup (WhatsApp), APNs/FCM (push), in-app
- **Audience Builder execution:** push audiences to channels (call queue, WhatsApp queue, email queue, ad-platform custom audience sync)
- Lifecycle Layer outbound: COD confirmation calls, abandoned cart recovery, winback, VIP retention, replenishment
- Inbound multi-channel inbox (Phase 2)
- Export jobs (CSV, XLSX, PDF) via S3 + signed URLs
- PDF generation via headless Chromium
- Referral Engine: trackable link generation, advocate outreach, fraud detection

**Data:**
- Postgres `notifications` schema: `in_app_notifications`, `alert_events`, `export_jobs`, `audiences`, `audience_members`, `outreach`, `calls`, `tickets`, `messages`, `consent_events`, `email_sends`, `email_templates`, `email_flows`
- S3: rendered exports, call recordings (with consent)
- Kafka: consumes events; publishes delivery status

**Scale:** 2–8 pods (Phase 1); scales independently with Lifecycle Layer volume.

### 5.7 frontend (Next.js)

**Purpose:** the operator UI. Server Components for initial paint; Client Components for interactivity.

**Responsibilities:**
- Routes (App Router): `/auth/*`, `/onboarding`, `/w/[slug]/*` (workspace-scoped pages)
- Calls api-gateway via tRPC (typed end-to-end)
- Static assets via CloudFront (immutable; 1-year cache)
- ISR for marketing pages (Phase 4)
- Streaming AI responses via SSE

**Scale:** stateless Next.js on AWS App Runner or EKS. CloudFront edge caches static.

---

## 6. Tech Stack & Rationale

### 6.1 Recommended Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Frontend** | Next.js 14+ (App Router), TypeScript, React 18+ | Server Components for heavy dashboards; tRPC client co-located |
| **UI** | shadcn/ui + Tailwind v4 | Owned primitives, no library lock-in. Container queries (`@container/main`) for responsive analytics layouts |
| **Charts** | Recharts (primary) + Visx (waterfall, heatmap, India map choropleth) | Recharts for 90% of needs; Visx for advanced viz |
| **Icons** | Tabler Icons (primary), Lucide React (legacy/secondary) | |
| **State (client)** | TanStack Query v5 (via tRPC) + Zustand 5 + nuqs | Server cache + UI/app state + URL state |
| **Form state** | react-hook-form 7 + Zod v4 | All forms validated at schema boundary |
| **External API** | tRPC (from api-gateway) | Type-safe client/server; one server, one client codebase |
| **Internal API** | gRPC (Protocol Buffers) | Strongly-typed cross-service; binary protocol (5–10× lower latency than JSON); HTTP/2 multiplexing; deadlines; streaming for live metric refresh |
| **API Gateway** | Node 20 + Fastify + tRPC + grpc-js | Lightweight, low-latency; handles 5K+ RPS per pod |
| **Backend services (Node)** | Node 20, Fastify, grpc-js, **Prisma** | Standard; predictable |
| **Backend services (Python)** | Python 3.12, FastAPI, grpcio, asyncpg, clickhouse-driver | Async-first |
| **Event streaming** | Apache Kafka via **Amazon MSK** | Managed Kafka; persistent infinite-retention topics for replay; schema evolution via Glue Schema Registry |
| **Schema registry** | AWS Glue Schema Registry | Schema evolution for Kafka events; Avro |
| **OLTP database** | **Supabase Postgres** (managed on AWS) | Postgres + RLS + Auth + Realtime in one product. Escape hatch: Aurora Postgres if tier ceiling hits |
| **Vector storage** | **pgvector** inside Supabase Postgres | Cosine similarity for Brand Fingerprint / condition-outcome matching. Avoids separate vector DB |
| **OLAP database** | **ClickHouse Cloud** (AWS region) or self-hosted ClickHouse on EKS via Altinity Operator | Best-in-class columnar OLAP; ~10–100× faster than Postgres on aggregations |
| **CDC (Postgres → ClickHouse)** | **Debezium on MSK Connect** | Streams Postgres WAL changes to Kafka; ClickHouse consumes |
| **Cache / sessions / rate limits** | **ElastiCache Redis** (cluster mode) | Horizontal scale via sharding; AWS-managed |
| **Search (Phase 3)** | OpenSearch (AWS managed) | Customer search, product search; replaces ad-hoc Postgres `ILIKE` |
| **Object storage** | **S3** | Exports, uploads, Kafka tiered storage backend, call recordings |
| **CDN + DNS** | **CloudFront** + **Route 53** | Edge caching for static, signed URLs for exports |
| **Container orchestration** | **EKS** (Elastic Kubernetes Service) | Standard; HPA + Karpenter for cost-optimal node provisioning |
| **Container registry** | **ECR** | AWS-native |
| **Service mesh (Phase 3)** | Istio or AWS App Mesh | mTLS, traffic shifting, observability when service count grows |
| **Load balancer** | **ALB** (Application Load Balancer) | L7 routing; WAF integration; gRPC pass-through |
| **Secrets** | **AWS Secrets Manager** + per-environment IAM | Auto-rotation, encryption, audit-logged |
| **CI/CD** | GitHub Actions → ECR → ArgoCD | GitOps; ArgoCD reconciles k8s state from Git |
| **IaC** | **AWS CDK** (TypeScript) | Type-safe infra; lives in monorepo |
| **Email** | **AWS SES** | Cost-efficient; native; configurable IP warming. Deliverability backbone for native email engine: optionally Postmark / Mailgun / SendGrid as alternatives during Phase 2 |
| **WhatsApp** | Gupshup or AiSensy (external) | India-first; pre-approved templates. Direct WhatsApp Business Cloud API in Phase 2 |
| **SMS** | TrustSignal (primary), Gupshup / Karix / Kaleyra (fallback) | DLT-compliant |
| **AI calling** | Path A (Bolna/Smallest.ai), Path B (Vapi/Retell), or Path C (native build) — see Section 22 | Decision per Section 22 |
| **LLM** | Anthropic Claude Sonnet 4.6 + Haiku 4.5 via Anthropic SDK | Best at structured reasoning; prompt caching reduces cost ~30× |
| **Image generation** | Stable Diffusion XL with brand-trained LoRA, or DALL-E 3 with brand kit, or Midjourney | For agentic creative |
| **Video generation** | Runway, Sora, Pika (as model landscape matures) | For short-form variant generation only |
| **Observability** | **CloudWatch Logs/Metrics** + **X-Ray** (tracing) + **Sentry** (errors) + **PostHog** (product analytics) | Standard AWS stack; Sentry/PostHog where AWS-native is weaker |
| **Scheduling** | **EventBridge Scheduler** | AWS-native cron replacement |
| **MCP** | Custom MCP server implementation per Anthropic MCP spec | Internal agent-to-agent + external client surface |

### 6.2 Why Not Other Choices

| Considered | Rejected because |
|-----------|------------------|
| **BullMQ** | User requested Kafka. Kafka also gives replay, schema registry, persistence — BullMQ doesn't |
| **Aurora Postgres** instead of Supabase | Supabase offers Auth + RLS + Realtime in one package. Aurora is fine but adds 3 services of build work. Revisit if Supabase tier ceiling hits |
| **Cognito** for Auth | Supabase Auth has better DX, integrated with Postgres RLS, runs on AWS |
| **DynamoDB** for OLTP | We need joins, aggregates, RLS. NoSQL is wrong tool |
| **Vercel + Render** (Looqus stack) | User wants AWS-native. Vercel/Render shifted to EKS |
| **TimescaleDB extension** | ClickHouse outperforms 10–100× on our workload. Keep Postgres pure-OLTP |
| **Snowflake / BigQuery / Redshift** | Cost prohibitive at our stage. ClickHouse cheaper and faster for our access patterns |
| **GraphQL** for public API | Phase 5+ if customer demand. tRPC sufficient for one frontend + small partner API |
| **gRPC for frontend** | Browsers can't speak gRPC natively (would need grpc-web). tRPC at edge, gRPC behind it |
| **Spark / Airflow** | Overkill. Kafka Streams + Python workers cover us through ₹100Cr/month brand scale |
| **OpenAI as primary LLM** | Claude better at structured analytical reasoning; Anthropic prompt caching reduces cost ~30× |
| **AWS Bedrock** | Worth revisiting if AWS-only mandate hardens; direct Anthropic API gives faster access to new models |
| **Separate vector DB (Pinecone, Weaviate)** | pgvector inside Postgres avoids one more service to operate; sufficient at our scale |
| **Lambda for backend services** | Long-running workers (ingestion sync, agent execution) don't fit serverless cold-start model |

---

## 7. Monorepo Structure

```
brain/                              # Turborepo + pnpm workspaces (TS) · uv workspace (Python). NO Nx.
│
├── apps/                           # 7 backend services + 2 presentation apps (the locked topology)
│   ├── frontend-web/               # Next.js 14 web (Ananya) — presentation only; talks to api-gateway only
│   ├── mobile/                     # React Native + Expo (Karan) — the Morning Brief surface
│   ├── api-gateway/                # Node/Fastify BFF + MCP server (Vikram) — auth, authz, aggregation, WS/SSE edge
│   ├── core-service/               # Node/Fastify OLTP (Vikram) — users, workspaces, campaigns, permissions, settings, tenancy
│   ├── ingestion-service/          # Python/FastAPI ETL (Maya) — Shopify/Meta/Google/Shiprocket/Klaviyo, webhooks, normalize
│   ├── analytics-service/          # Python/FastAPI metrics (Maya) — KPI/forecasting/attribution/anomaly on ClickHouse
│   ├── intelligence-service/       # Python/FastAPI AI (Maya) — 15 AICMO/COO/CFO agents, daily tick, RAG, Memory Layer
│   ├── notifications-service/      # Node/Fastify (Vikram) — email/WhatsApp/SMS/alerts/digests/exports
│   └── lifecycle-service/          # Python/FastAPI (Maya) — [MOAT] RFM, audience builder, AI calling, compliance engine, inbox
│
│   # Realtime (WS/SSE), background jobs, cron, and long-running workflows are handled INSIDE these 7 services —
│   # Kafka consumers, the intelligence-service daily tick, EventBridge Scheduler, in-service application/use-cases —
│   # NOT as separate realtime/worker/scheduler/workflow-orchestrator services.
│
│   # Every backend service is DDD-structured (skills/domain-driven-design):
│   #   src/{bootstrap, domain/<bounded-context>/{entities,services,repositories,value-objects,dto,validators,
│   #   mappers,events,policies,exceptions,factories,aggregates}, application/{commands,queries,workflows,
│   #   orchestrators,handlers,use-cases}, infrastructure, interfaces/{rest,grpc,consumers,producers,websocket,jobs},
│   #   observability, security, testing}.  NEVER controllers/services/models technical layers.
│
├── packages/                       # Shared TS libraries (Single-Primitive Rule)
│   ├── shared-types/ shared-auth/ shared-events/ shared-kafka/ shared-clients/ shared-config/ shared-errors/
│   ├── shared-observability/ shared-security/ shared-cache/ shared-storage/ shared-feature-flags/ shared-testing/ shared-utils/
│   ├── shared-ai/                  # cost-routed @paradigm Claude client wrappers
│   ├── lib-metrics/                # type-safe metric registry (TS↔Python parity)   [MOAT]
│   ├── lib-regional/               # RegionAdapter + INR/GST/currency utils          [MOAT]
│   ├── protobuf-generated/         # buf-generated gRPC clients (TS)
│   └── ui-system/                  # shadcn-derived component library
│
├── pylibs/                         # Shared Python libs (mirror shared-* + moat): brain_metrics, brain_regional,
│   │                               #   brain_kafka, brain_clickhouse, brain_db, brain_grpc, brain_mcp, brain_ml, brain_llm
│
├── proto/                          # CONTRACT-FIRST source of truth (buf) — versioned, no duplicate contracts
│   ├── common/ core/ ingestion/ analytics/ intelligence/ notifications/ lifecycle/
│   └── buf.yaml                    # → packages/protobuf-generated (TS) + pylibs/brain_grpc (Py)
│
├── kafka/                          # Event backbone (MSK + Glue Schema Registry + Avro)
│   └── topics/ schemas/ producers/ consumers/ retry-policies/ dead-letter/ stream-processors/ connectors/
│       # versioned topics (campaigns.created.v1) · workspace_id = partition key · schema-validation + retries + DLQ
│
├── schemas/                        # Data + API contracts: api/ events/ analytics/ ai/ validation/ exports/ database/ data-contracts/
│
├── ai/                             # AI infra (skills/agentic-design) — custom agents + pgvector
│   └── prompts(versioned)/ agents/ workflows/ orchestration/ memory/ embeddings/ vector-search/
│       evaluations/ benchmark/ guardrails/ policies/ datasets/ fine-tuning/
│
├── data-platform/                  # Analytics — ISOLATED from transactional (skills/clickhouse-olap)
│   └── clickhouse/ warehouse/ transformations/ aggregations/ pipelines/ forecasting/ benchmarks/ dbt/ airflow/ spark/
│       # dbt/airflow/spark = analytics DAGs ONLY here; keep analytics pipelines isolated from the OLTP services
│
├── infra/                          # AWS CDK (TypeScript) — NOT Terraform, NOT Helm
│   └── stacks/ (network·compute[EKS+Karpenter]·data·kafka·storage·observability·security)  k8s/ (ArgoCD manifests)  bin/
│
├── monitoring/                     # Observability config — AWS-native (skills/observability)
│   └── dashboards/ alerts/ slo/ tracing/ incident-response/
│       # CloudWatch · OpenSearch · X-Ray · Sentry · PostHog. OTel = in-code instrumentation exporting to these.
│       # NOT Prometheus/Grafana/Loki/Tempo.
│
├── security/                       # policies/ audits/ compliance/ pii/ pentest/ governance/ risk-assessments/ threat-models/
│                                   #   India gates (DLT/NCPR/DND/calling-hours/consent/GST) live here + lifecycle-service
├── deployments/                    # local/ staging/ production/ canary/ blue-green/ rollback/  (ArgoCD-driven)
├── tests/                          # integration/ e2e/ contracts/ load/ performance/ chaos/ security/ mocks/ fixtures/
│
├── tools/  docs/  scripts/  .github/workflows/
├── turbo.json  pnpm-workspace.yaml  pyproject.toml  docker-compose.yml  Makefile  .env.example  package.json  README.md
└── .engineering-os/                # plugin-delivered shared memory (journals/decision-log/state/runs).
                                    #   The team is INSTALLED, not vendored — there is NO engineering-os/ SOURCE tree in Brain.
```

### 7.1 Build & Deploy Tooling

- **Turborepo** for TS apps/packages — fast incremental builds + remote caching
- **uv** (or Poetry workspaces) for Python apps/pylibs
- **Buf** for proto management and codegen
- **Docker BuildKit** with multi-stage builds; one Dockerfile per app
- **ArgoCD** in EKS reconciles each service's manifests from `infra/k8s/*`
- **GitHub Actions:** lint → typecheck → test → build → push to ECR → ArgoCD sync

### 7.2 Code Generation

```bash
# Regenerate gRPC + Kafka event types from /protos
buf generate
# Outputs:
#   packages/lib-grpc-clients/   (TS)
#   pylibs/brain_grpc/           (Python)
#   packages/events/             (TS event schemas)
#   pylibs/brain_events/         (Python event schemas)
```


---

## 8. Communication Patterns (gRPC + Kafka)

### 8.1 Synchronous: gRPC (Internal)

Service-to-service calls use gRPC. Proto files in `/protos/*` are the source of truth.

Example:

```proto
// protos/analytics/metrics.proto
syntax = "proto3";
package brain.analytics.v1;
import "google/protobuf/timestamp.proto";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc GetWaterfall(WaterfallRequest) returns (WaterfallResponse);
  rpc GetFirstProductCascade(CascadeRequest) returns (CascadeResponse);
  rpc StreamLiveMetrics(StreamLiveMetricsRequest) returns (stream LiveMetricEvent);
}

message GetDailyMetricsRequest {
  string workspace_id = 1;
  google.protobuf.Timestamp from = 2;
  google.protobuf.Timestamp to = 3;
  repeated string metric_names = 4;
  optional CustomerType customer_type = 5;
  optional string channel = 6;
  optional Granularity granularity = 7;  // DAY | WEEK | MONTH | QUARTER
}

enum CustomerType {
  CUSTOMER_TYPE_UNSPECIFIED = 0;
  ALL = 1;
  NEW = 2;
  RETURNING = 3;
}
```

**Why gRPC, not HTTP/JSON:**
- Strong typing (compile-time check)
- Binary protocol (5–10× lower latency than JSON)
- HTTP/2 multiplexing (multiple concurrent RPCs over one connection)
- Deadlines built in (request timeouts propagate)
- Streaming support (used for live metric refresh, Morning Brief assembly)

**Code generation:**
- TS: `buf generate` → `packages/lib-grpc-clients/`
- Python: `buf generate` → `pylibs/brain_grpc/`

### 8.2 Asynchronous: Kafka

All cross-service state-change communication goes through Kafka topics.

**Topic naming convention:** `<domain>.<entity>.<event_type>.v<version>` (Avro-encoded with Glue Schema Registry).

### 8.3 Key Topics

| Topic | Producer | Consumers | Purpose |
|-------|----------|-----------|---------|
| `integrations.orders.v1` | ingestion-service | analytics-service, intelligence-service | New/updated order events |
| `integrations.shipments.v1` | ingestion-service | analytics-service | Shipment lifecycle events (RTO, NDR, delivered, in_transit) |
| `integrations.ads.v1` | ingestion-service | analytics-service | Ad insights events (campaign/adset/ad level + creative metrics) |
| `integrations.refunds.v1` | ingestion-service | analytics-service | Refund events |
| `integrations.customers.v1` | ingestion-service | analytics-service | Customer events |
| `integrations.payments.v1` | ingestion-service | analytics-service | Razorpay payment + settlement events |
| `operations.workspace.changed.v1` | core-service | all | Workspace metadata updates (region, currency, etc.) |
| `operations.settings.changed.v1` | core-service | analytics-service, intelligence-service | Cost/goal/classification changes |
| `operations.goals.changed.v1` | core-service | analytics-service, notifications-service | Goal value updates |
| `analytics.metrics.daily.materialized.v1` | analytics-service | intelligence-service, notifications-service | "Day N metrics are ready" |
| `analytics.customer_state.changed.v1` | analytics-service | intelligence-service, notifications-service | Lifecycle transitions (New → Returning → At-Risk → Churned) |
| `analytics.cohort_aggregates.refreshed.v1` | analytics-service | intelligence-service | Cohort materialized view refreshed |
| `intelligence.anomaly.detected.v1` | intelligence-service | notifications-service | New anomaly |
| `intelligence.insight.generated.v1` | intelligence-service | notifications-service | New insight |
| `intelligence.action.recommended.v1` | intelligence-service | notifications-service, (audit) | Agent recommendation produced |
| `intelligence.action.executed.v1` | intelligence-service | notifications-service, (audit) | Auto-execute action ran |
| `intelligence.decision.logged.v1` | intelligence-service | (audit, memory layer) | Decision Log entry created |
| `lifecycle.audience.built.v1` | notifications-service | (audit) | Audience materialized |
| `lifecycle.outreach.sent.v1` | notifications-service | analytics-service (attribution), (audit) | Outreach attempt completed |
| `lifecycle.ticket.created.v1` | notifications-service | intelligence-service | Inbound ticket created |
| `notifications.alert.fired.v1` | notifications-service | (audit) | Alert sent to channel |
| `notifications.digest.sent.v1` | notifications-service | (audit) | Daily/weekly/monthly digest delivered |

**Retention:**
- **Infinite** for `integrations.*` (S3 tiered storage via MSK — enables full replay)
- **30 days** for `operations.*` and `notifications.*`
- **Forever** for `intelligence.decision.logged.v1` (Decision Log is the moat)

**Partitioning:** by `workspace_id`. Single workspace's events always land in the same partition → ordering guaranteed per workspace.

### 8.4 Event Schema Evolution

Schema registry (AWS Glue) enforces:
- **Backward compatible by default** (consumers older than producers still work)
- **Schema version in topic name** (`.v1`, `.v2` for breaking changes)
- **All schemas in `/protos/events/`** reviewed via PR

### 8.5 Exactly-Once Semantics

- Producers use Kafka idempotent producer config (`enable.idempotence=true`)
- Consumers use transactional consumer groups with offset commits inside the same Postgres transaction as the side-effect write
- Idempotency keys stored in Redis (24-hour TTL) for HTTP-triggered writes

---

## 9. Multi-Tenancy & Data Isolation

### 9.1 Tenant = Workspace

A workspace is a single brand. Sugandh Lok = one workspace. Agency clients managing 10 brands have 10 workspaces (with optional parent Organisation grouping).

**Hierarchy:**
```
Organisation
└── Brand (= Workspace)            ← unit of pricing, billing, isolation
    └── Store (Shopify, Amazon, Flipkart, Blinkit listing, etc.)
        └── (data tables tagged with workspace_id, store_id)
```

### 9.2 Enforcement Layers (Defense in Depth)

**Layer 1 — JWT Claim**
- Every authenticated request carries `active_workspace_id` in the JWT
- api-gateway extracts and propagates via gRPC metadata (`x-workspace-id` header)

**Layer 2 — Service-side check**
- Every gRPC handler asserts `request.workspace_id == metadata.workspace_id` (or `member-of` for cross-workspace orgs)
- Reject mismatches with `PERMISSION_DENIED`
- Standard helper: `requireWorkspaceAccess(ctx, request.workspace_id)` — wraps the check
- Standard helper: `requireRole(member, minimumRole)` — for mutation endpoints

**Layer 3 — Database enforcement**
- **Postgres:** RLS policies — every workspace-scoped table has a policy like:
  ```sql
  CREATE POLICY workspace_isolation ON orders
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
  ```
- App sets the session variable at connection acquire: `SET LOCAL app.workspace_id = '...'`
- **ClickHouse:** `workspace_id` is **always the first column of primary key** on every workspace-scoped table. All queries go through `pylibs/brain_clickhouse/query.py` which **rejects any query missing a `workspace_id =` predicate** at compile time.

**Layer 4 — Kafka**
- Consumers extract `workspace_id` from event payload and assert against joined data
- Cross-tenant joins via the same `workspace_id` only

### 9.3 Why ClickHouse Doesn't Use RLS

ClickHouse has no Postgres-style RLS. We enforce via:
1. **Primary key ordering:** `ORDER BY (workspace_id, ...)` makes workspace-filtered queries O(log n)
2. **Query gateway:** all queries go through `pylibs/brain_clickhouse/query.py`, which raises a compile-time error if `WHERE workspace_id =` is missing
3. **Per-workspace databases (Phase 3 if needed):** `clickhouse_workspace_<uuid>` databases with per-workspace user privileges for hard isolation. Premature now.

### 9.4 Account Structures (Models A / B / C + Enterprise Variant D)

**Model A — Single-Brand Account.** One Organisation, one Brand. Founder is Owner. Most common at small-tier / founding cohort.

**Model B — Multi-Brand Holding Co.** One Organisation, N Brands **fully isolated** from each other in storage and queries. Each Brand has its own dashboards, integrations, team, roles, and pricing tier (each Brand falls into its tier based on its individual GMV). Cross-brand visibility is granted only by **explicit role assignment** — never implicit data sharing.
- *Storage:* every row in OLTP + OLAP carries `workspace_id` (where workspace = Brand) and `organisation_id`. Cross-brand portfolio queries filter by `organisation_id` AND require explicit `cross_brand_read` privilege.
- *Portfolio rollup features* (Tier 3 / Enterprise): cross-brand P&L, blended MER across the portfolio, brand-level RAG indicators, cross-brand benchmarks within the same Org. Computed at runtime from the isolated per-Brand stores — **never via mixed-tenant queries**.
- *Billing:* one invoice per Organisation rolls up all Brands; each Brand priced at its own tier rate.

**Model C — Agency Account.** Agency Organisation with read/write across **Client Brands belonging to different end-customer Organisations.** Agency users authenticate against the agency Org → get scoped roles per Client Brand. Client Brand retains Owner control + can revoke agency access in one click. Cross-brand benchmarks in agency view expose only aggregated/anonymized statistics. **Agencies cannot see each other's clients.** Agency Org pays a separate platform fee for agency tooling + multi-client dashboards (tier based on Client Brand count managed).

**Model D — Enterprise Variant (overlay on Models A or B).** Available at any time via sales-led motion, not gated to Phase 4. Engineering implications:
- *Private data warehouse / BYO-VPC:* Brand's Postgres + ClickHouse deployed in the Brand's own cloud account; Brain control plane in Brain's account orchestrates via VPC peering / PrivateLink. Same code, different deployment topology.
- *Custom model fine-tuning:* Brand's historical data used to fine-tune a per-Brand model (Claude fine-tune API or AWS Bedrock custom model). Strict opt-in. Fine-tuned model serves that Brand only; never leaks back to shared model.
- *Per-region data residency:* Brand's home region pinned (e.g., `eu-central-1` for EU brands); cross-region replication disabled for that Brand.
- *Custom SLA + 24/7 priority support:* PagerDuty escalation routes for enterprise Brands flagged separately from shared-tier alerts.
- *Custom integrations:* per-Brand connectors for proprietary ERP / data lake / internal tools. Lives as an additional connector in `ingestion-service` namespaced to that Brand.
- *White-label option:* per-Org brand kit override (logo, colors, custom domain `analytics.{brand}.com`) for agencies and consulting firms.

### 9.5 Enterprise-Specific Data Isolation Guarantees

Beyond the four defense-in-depth layers in 9.2, Enterprise Variant adds:
- **Per-Brand encryption keys** for OAuth tokens + at-rest data (already standard, but enterprise gets dedicated KMS key with rotation cadence per the Brand's compliance schedule)
- **Per-Brand audit log export** to the Brand's own SIEM (Splunk, Datadog, etc.) via CloudWatch subscription filter or direct webhook
- **Per-Brand IP allowlist** for API access (enforced at api-gateway)
- **Disabled cross-brand benchmark contribution** if the Brand opts out (their data never feeds the network benchmark even in aggregated form)
- **Customer-managed encryption keys (CMEK)** for sensitive integrations — Brand controls the KMS key in their AWS account; Brain's services use cross-account IAM to read

### 9.6 Cross-Brand Portfolio Queries (Model B / Enterprise)

For multi-brand holding cos, the platform supports portfolio-level rollup views. Implementation:
- A user with `cross_brand_read` privilege on the Organisation (granted explicitly by Owner) gets an additional gRPC method `GetPortfolioRollup(organisation_id, metric, from, to)` on analytics-service
- The method **iterates each Brand in the Org**, calls the standard per-Brand `GetDailyMetrics`, and aggregates in-memory in the BFF
- **No SQL/ClickHouse query ever joins across `workspace_id`.** Per-Brand isolation is preserved; rollup happens above the data layer.
- Performance: portfolio of 50 Brands → 50 parallel ClickHouse queries (each <500ms) → in-memory aggregation → ~600ms total p95
- Cache: portfolio rollups cached in Redis with 5-min TTL per (organisation_id, metric, from, to) key

### 9.7 Cross-Brand Benchmarks (Aggregation Pipeline)

- Computed in a **separate analytics pipeline** (scheduled nightly job in analytics-service)
- Input: per-workspace metrics
- Output: anonymized percentile distributions per category (e.g., "Indian beauty brands at ₹X–Y AOV"), stored in ClickHouse `benchmarks` schema
- **Minimum sample size: 10 qualifying workspaces** per category before publishing — prevents reverse-identification
- Raw rows never leave the brand's data partition

---

## 10. Data Architecture (Postgres OLTP)

### 10.1 Postgres Layout

| Schema | Purpose | Owner Service |
|--------|---------|---------------|
| `auth` | Supabase Auth | Supabase managed |
| `core` | Workspaces, users, members, integrations, settings, goals, costs, campaigns, marketing actions, festivals, invitations | core-service |
| `notifications` | In-app notifications, alert events, export jobs, audiences, audience_members, outreach, calls, tickets, messages, consent_events, email_sends, email_templates, email_flows, referrals | notifications-service |
| `ai` | AI insights, chat history, forecasts, anomalies, agent recommendations, auto_execute_log, decision_log | intelligence-service |
| `memory` | Brand fingerprint embeddings (pgvector), condition_outcome_pairs, seasonal_codebook, customer_segment_snapshots | intelligence-service |

### 10.2 Key Tables

#### `core.workspaces`
```sql
CREATE TABLE core.workspaces (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organisation_id UUID NOT NULL,
  slug            TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  plan            TEXT NOT NULL,     -- 'founding', 'standard_early', 'standard_growth', 'enterprise'
  gmv_rate_pct    NUMERIC(5,4) NOT NULL,  -- 0.0050 for 0.5%, 0.0100 for 1.0%
  platform        TEXT NOT NULL DEFAULT 'SHOPIFY',  -- legacy: SHOPIFY/WOOCOMMERCE; multi-platform via stores table
  timezone        TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  currency        TEXT NOT NULL DEFAULT 'INR',
  home_region     TEXT NOT NULL DEFAULT 'ap-south-1',  -- multi-region routing
  features        JSONB,             -- per-workspace feature flags
  cogs_settings   JSONB,             -- { overrideAllCogsPercent, fallbackCogsPercent, markupPercent }
  order_filter_settings JSONB,       -- { skippedTags: [...], skipZeroSales: bool }
  founder_salary_monthly NUMERIC(18,2),
  revenue_definition TEXT NOT NULL DEFAULT 'net_sales_net_tax',
  default_gst_rate NUMERIC(5,4) NOT NULL DEFAULT 0.18,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON core.workspaces (organisation_id);
```

#### `core.workspace_members`
```sql
CREATE TABLE core.workspace_members (
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL,
  role         TEXT NOT NULL,  -- 'owner','operator','analyst','agency','readonly'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, user_id)
);
```

#### `core.integrations`
```sql
CREATE TABLE core.integrations (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id        UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  provider            TEXT NOT NULL,  -- 'shopify','meta','google','shiprocket','klaviyo','razorpay',...
  account_identifier  TEXT NOT NULL,  -- shop domain, ad account ID, etc.
  encrypted_credentials BYTEA NOT NULL,  -- AES-256-GCM ciphertext
  encryption_key_id   TEXT NOT NULL,    -- references AWS Secrets Manager key
  status              TEXT NOT NULL,    -- 'connected','disconnected','token_expired','error'
  token_expires_at    TIMESTAMPTZ,
  last_sync_at        TIMESTAMPTZ,
  last_sync_status    TEXT,
  metadata            JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON core.integrations (workspace_id, provider);
```

#### `core.workspace_costs`
```sql
CREATE TABLE core.workspace_costs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  cost_type    TEXT NOT NULL,       -- 'shipping','packaging','website','custom'
  name         TEXT NOT NULL,
  amount       NUMERIC(18,4) NOT NULL,
  unit         TEXT NOT NULL,       -- 'per_order','per_unit','flat_monthly','pct_revenue'
  effective_from DATE NOT NULL,
  effective_to   DATE,              -- null = current
  display_order INT NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON core.workspace_costs (workspace_id, effective_from, effective_to);
```

#### `core.metric_goals`
```sql
CREATE TABLE core.metric_goals (
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  metric_name  TEXT NOT NULL,         -- 'mer','amer','cac','revenue','cm3_pct','rto_rate', etc.
  period_type  TEXT NOT NULL,         -- 'daily','weekly','monthly'
  period_start DATE NOT NULL,
  goal_value   NUMERIC(18,4) NOT NULL,
  goal_type    TEXT NOT NULL,         -- 'minimum','maximum','target'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, metric_name, period_type, period_start)
);
```

#### `core.marketing_actions`
```sql
CREATE TABLE core.marketing_actions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  action_date  DATE NOT NULL,
  start_at     TIMESTAMPTZ,           -- for sale events
  end_at       TIMESTAMPTZ,           -- for sale events; triggers hourly mode
  action_type  TEXT NOT NULL,         -- 'email','sms','promotion','launch','influencer','creative','external','sale_event'
  action_name  TEXT NOT NULL,
  notes        TEXT,
  created_by   UUID,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON core.marketing_actions (workspace_id, action_date);
```

#### `core.workspace_festivals`
```sql
CREATE TABLE core.workspace_festivals (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id         UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  festival_name        TEXT NOT NULL,         -- 'diwali','navratri','holi','eid', etc.
  start_date           DATE NOT NULL,
  end_date             DATE NOT NULL,
  expected_multiplier  NUMERIC(5,2) NOT NULL,  -- 4.0 for Diwali, etc.
  pre_period_multiplier NUMERIC(5,2),
  post_period_multiplier NUMERIC(5,2),
  notes                TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `core.campaign_classifications`
```sql
CREATE TABLE core.campaign_classifications (
  workspace_id UUID NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  platform     TEXT NOT NULL,         -- 'meta','google','tiktok','snap'
  campaign_id  TEXT NOT NULL,
  campaign_type TEXT NOT NULL,         -- 'acquisition','non_acquisition','brand','unclassified'
  auto_classified BOOLEAN NOT NULL DEFAULT FALSE,
  confidence   NUMERIC(5,4),
  classified_by UUID,
  classified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, platform, campaign_id)
);
```

#### `core.workspace_thresholds`
```sql
CREATE TABLE core.workspace_thresholds (
  workspace_id UUID PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
  at_risk_days INT NOT NULL DEFAULT 45,
  churned_days INT NOT NULL DEFAULT 90,
  threshold_auto_calculated BOOLEAN NOT NULL DEFAULT TRUE,
  threshold_last_calculated TIMESTAMPTZ,
  rto_return_shipping_cost NUMERIC(10,2),
  rto_restocking_cost NUMERIC(10,2),
  rto_damage_rate NUMERIC(5,4) NOT NULL DEFAULT 0.05,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `ai.decision_log` (the moat)
```sql
CREATE TABLE ai.decision_log (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id          UUID NOT NULL,
  agent                 TEXT NOT NULL,             -- 'aicmo_meta','aicoo_logistics','aicfo_conversion', etc.
  action_type           TEXT NOT NULL,             -- 'pause_ad','reduce_budget','reorder_inventory', etc.
  parameters            JSONB NOT NULL,            -- structured action params
  confidence            NUMERIC(5,4) NOT NULL,     -- 0.0–1.0
  recommended_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_response         TEXT,                      -- 'approved','rejected','edited','auto_executed'
  user_response_at      TIMESTAMPTZ,
  user_response_by      UUID,
  executed_at           TIMESTAMPTZ,
  execution_result      JSONB,
  channel               TEXT,                      -- 'call','whatsapp','email','ad_audience','no_action'
  outcome_7d            JSONB,                     -- auto-attributed at +7 days
  outcome_30d           JSONB,                     -- auto-attributed at +30 days
  recovered_revenue_7d  NUMERIC(18,2),
  recovered_revenue_30d NUMERIC(18,2),
  reversal_status       TEXT,
  reversed_at           TIMESTAMPTZ,
  metadata              JSONB
);
CREATE INDEX ON ai.decision_log (workspace_id, recommended_at DESC);
CREATE INDEX ON ai.decision_log (workspace_id, agent, recommended_at DESC);
-- This table is APPEND-ONLY. Never UPDATE or DELETE rows; mutations write new rows.
```

#### `ai.auto_execute_log`
```sql
CREATE TABLE ai.auto_execute_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      UUID NOT NULL,
  decision_log_id   UUID NOT NULL REFERENCES ai.decision_log(id),
  agent             TEXT NOT NULL,
  action_type       TEXT NOT NULL,
  parameters        JSONB NOT NULL,
  confidence        NUMERIC(5,4) NOT NULL,
  executed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  execution_status  TEXT NOT NULL,    -- 'success','failed','reversed'
  execution_result  JSONB,
  outcome_7d        JSONB,
  outcome_30d       JSONB,
  reversal_status   TEXT,
  reversed_at       TIMESTAMPTZ,
  reversed_by       UUID
);
-- Immutable storage.
```

#### `ai.insights`
```sql
CREATE TABLE ai.insights (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL,
  page          TEXT NOT NULL,
  filters_hash  TEXT NOT NULL,        -- SHA256 of (workspace_id+page+date_from+date_to+filters)
  content       JSONB NOT NULL,       -- InsightItem[]
  status        TEXT NOT NULL,        -- 'done','failed','pending','processing'
  provider      TEXT NOT NULL,        -- 'claude'
  model         TEXT NOT NULL,        -- 'claude-sonnet-4-6','claude-haiku-4-5'
  tokens_used   INT,
  latency_ms    INT,
  metadata      JSONB,
  expires_at    TIMESTAMPTZ NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, filters_hash)
);
```

#### `memory.brand_fingerprint` (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE memory.brand_fingerprint (
  workspace_id UUID NOT NULL,
  snapshot_date DATE NOT NULL,
  embedding    vector(384) NOT NULL,  -- 384-dim embedding
  metadata     JSONB,                 -- dimensions captured: seasonality, channel efficiency curves, cohort patterns, CM2 trajectory
  PRIMARY KEY (workspace_id, snapshot_date)
);
CREATE INDEX ON memory.brand_fingerprint USING ivfflat (embedding vector_cosine_ops);
```

#### `memory.condition_outcome_pairs`
```sql
CREATE TABLE memory.condition_outcome_pairs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL,
  condition_at  TIMESTAMPTZ NOT NULL,
  condition_vec vector(384) NOT NULL,  -- Business Moment Vector
  action_taken  TEXT,                  -- nullable: 'no_action' if observed only
  outcome_7d    JSONB,
  outcome_30d   JSONB,
  metadata      JSONB
);
CREATE INDEX ON memory.condition_outcome_pairs USING ivfflat (condition_vec vector_cosine_ops);
```

#### `notifications.audiences`
```sql
CREATE TABLE notifications.audiences (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id     UUID NOT NULL,
  name             TEXT NOT NULL,
  rfm_filter       JSONB,                -- {champions: true, recency_score: [4,5], ...}
  custom_filter    JSONB,                -- {sku: [...], channel: [...], geography: [...], aov_band: [...]}
  computed_size    INT NOT NULL,
  modeled_response_rate NUMERIC(5,4),
  modeled_recovery NUMERIC(18,2),
  channel_mix      JSONB NOT NULL,       -- {call: ['top_decile'], whatsapp: ['mid'], email: ['rest']}
  status           TEXT NOT NULL,        -- 'draft','built','triggered','completed'
  built_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  triggered_at     TIMESTAMPTZ,
  created_by       UUID
);
```

#### `notifications.audience_members`
```sql
CREATE TABLE notifications.audience_members (
  audience_id  UUID NOT NULL REFERENCES notifications.audiences(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL,
  customer_id  UUID NOT NULL,
  channel_eligible JSONB NOT NULL,       -- {call: true, whatsapp: true, email: false}
  routed_channel TEXT,                   -- final channel for this member
  PRIMARY KEY (audience_id, customer_id)
);
```

#### `notifications.outreach`
```sql
CREATE TABLE notifications.outreach (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  audience_id     UUID REFERENCES notifications.audiences(id),
  customer_id     UUID NOT NULL,
  channel         TEXT NOT NULL,           -- 'call','whatsapp','email','sms','rcs'
  status          TEXT NOT NULL,           -- 'queued','sent','delivered','opened','clicked','responded','failed'
  template_id     TEXT,
  scheduled_at    TIMESTAMPTZ,
  attempted_at    TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  outcome         TEXT,                    -- channel-specific
  recovered_revenue NUMERIC(18,2),
  metadata        JSONB
);
CREATE INDEX ON notifications.outreach (workspace_id, customer_id, attempted_at DESC);
```

#### `notifications.calls`
```sql
CREATE TABLE notifications.calls (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  outreach_id     UUID REFERENCES notifications.outreach(id),
  customer_id     UUID NOT NULL,
  vendor          TEXT NOT NULL,           -- 'bolna','smallest','vapi','retell','native'
  vendor_call_id  TEXT NOT NULL,
  call_type       TEXT NOT NULL,           -- 'cod_confirmation','winback','vip_retention', etc.
  duration_seconds INT,
  outcome_label   TEXT,                    -- 'confirmed','converted_to_prepaid','no_answer','declined','do_not_call'
  transcript_id   TEXT,
  recording_url   TEXT,                    -- only if recording_consent=true
  recording_consent BOOLEAN NOT NULL DEFAULT FALSE,
  placed_at       TIMESTAMPTZ NOT NULL,
  metadata        JSONB
);
```

#### `notifications.tickets` & `notifications.messages`
```sql
CREATE TABLE notifications.tickets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  channel         TEXT NOT NULL,    -- 'whatsapp','instagram_dm','email','web_chat'
  customer_id     UUID,
  status          TEXT NOT NULL,    -- 'open','in_progress','resolved','escalated'
  assigned_to     TEXT,             -- 'ai' or user UUID
  resolution_type TEXT,             -- 'autonomous','human','customer_resolved'
  ticket_type     TEXT,             -- 'order_status','return_initiation','address_change', ...
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at     TIMESTAMPTZ,
  metadata        JSONB
);

CREATE TABLE notifications.messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  ticket_id       UUID REFERENCES notifications.tickets(id) ON DELETE CASCADE,
  outreach_id     UUID REFERENCES notifications.outreach(id),
  role            TEXT NOT NULL,    -- 'customer','ai','human'
  channel         TEXT NOT NULL,
  content         TEXT NOT NULL,
  timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata        JSONB
);
```

#### `notifications.consent_events`
```sql
CREATE TABLE notifications.consent_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  customer_id     UUID NOT NULL,
  channel         TEXT NOT NULL,    -- 'email','sms','whatsapp','call','all'
  old_state       TEXT,
  new_state       TEXT NOT NULL,    -- 'opted_in','opted_out','withdrawn','unknown'
  source          TEXT NOT NULL,    -- 'storefront','ticket','call','brand_bulk_update'
  changed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata        JSONB
);
```

#### `notifications.rfm_scores`
```sql
CREATE TABLE notifications.rfm_scores (
  workspace_id     UUID NOT NULL,
  customer_id      UUID NOT NULL,
  snapshot_date    DATE NOT NULL,
  recency_score    INT NOT NULL,    -- 1..5
  frequency_score  INT NOT NULL,    -- 1..5
  monetary_score   INT NOT NULL,    -- 1..5
  cod_score        INT NOT NULL,    -- 1..3 (India-specific 4th dimension)
  segment          TEXT NOT NULL,   -- 'champions','loyal','potential_loyalists',...
  PRIMARY KEY (workspace_id, customer_id, snapshot_date)
);
CREATE INDEX ON notifications.rfm_scores (workspace_id, snapshot_date, segment);
```

### 10.3 Migrations

- **Tool:** Prisma Migrate (TS services) + Alembic (Python services own their schemas)
- **Convention:** every migration in `infra/migrations/<service>/<timestamp>__<name>.sql`
- **Review rule:** all migrations require 2 reviewers
- **Phase 0:** `prisma db push` for dev iteration; `prisma migrate dev` for production
- **Production migrations** run via ArgoCD post-deploy hook

### 10.4 Connection Pooling

- **PgBouncer in transaction mode** in front of Postgres
- 10,000 client connections → 200 backend connections
- Connection pool per service (see Connection Budget in Section 35)

### 10.5 What Lives in Postgres vs ClickHouse

**Postgres (OLTP):**
- Recent canonical state, settings, configuration, user/membership data, integration tokens (encrypted), goals, marketing actions, campaign classifications, festivals
- All AI insight / chat history / decision log / agent state
- All notification / lifecycle / consent / RFM-snapshot / outreach / call / ticket / message state
- Brand fingerprint embeddings (pgvector)

**ClickHouse (OLAP):**
- Raw event archive (forever): every order, line item, shipment, ad insight, refund, customer event
- Materialized aggregates: daily_metrics, cohort_aggregates, first_product_attribution, pincode_reliability, customer_states
- Cross-brand benchmarks (anonymized)

---

## 11. Data Architecture (ClickHouse OLAP)

### 11.1 Why ClickHouse

- ~10–100× faster than Postgres on aggregations of millions of rows
- Native materialized views refresh on insert
- Columnar storage minimizes I/O for analytical queries
- ReplicatedMergeTree for HA
- Cluster scales horizontally

### 11.2 Cluster Topology

- **Phase 0–1:** ClickHouse Cloud (AWS), 3 nodes (3 shards × 1 replica) for dev cost
- **Phase 2:** 3 shards × 2 replicas (HA)
- **Phase 3:** Scale to 6 shards at 50k+ workspaces
- All workspace-scoped tables: `Distributed(<cluster>, default, <table>_local, rand())` with primary key starting `(workspace_id, ...)`

### 11.3 Schema Conventions

- Every workspace-scoped table: `ENGINE = ReplicatedMergeTree(...) ORDER BY (workspace_id, ...)`
- Date dimensions partitioned by month: `PARTITION BY toYYYYMM(event_date)`
- `Nullable()` only when truly nullable; prefer sentinel values for hot paths
- Timestamps stored as `DateTime64(3, 'Asia/Kolkata')` for India; local date columns derived

### 11.4 Key Tables

#### `raw.orders_local`
```sql
CREATE TABLE raw.orders_local ON CLUSTER brain_ch (
  workspace_id      UUID,
  source_id         String,            -- e.g., shopify_order_id
  source            LowCardinality(String),  -- 'shopify','woocommerce','amazon_in', ...
  store_id          UUID,
  order_name        String,
  email_hash        FixedString(64),
  phone_hash        FixedString(64),
  total_price       Decimal(18,4),
  total_tax         Decimal(18,4),
  total_discounts   Decimal(18,4),
  shipping_revenue  Decimal(18,4),
  financial_status  LowCardinality(String),
  fulfillment_status LowCardinality(String),
  payment_method    LowCardinality(String),  -- 'COD','Prepaid'
  payment_gateway   LowCardinality(String),
  shipping_pincode  String,
  shipping_city     String,
  shipping_state    String,
  customer_id       UUID,
  is_new_customer   UInt8,
  customer_order_sequence UInt32,
  tags              Array(String),
  utm_source        String,
  utm_medium        String,
  utm_campaign      String,
  meta_campaign_id  String,
  google_campaign_id String,
  processed_at      DateTime64(3, 'UTC'),
  created_at_local  Date,
  synced_at         DateTime64(3, 'UTC')
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/raw/orders', '{replica}')
ORDER BY (workspace_id, processed_at, source_id)
PARTITION BY toYYYYMM(created_at_local)
SETTINGS index_granularity = 8192;
```

#### `raw.line_items_local`
```sql
CREATE TABLE raw.line_items_local ON CLUSTER brain_ch (
  workspace_id    UUID,
  order_source_id String,
  source_id       String,
  source          LowCardinality(String),
  product_id      String,
  variant_id      String,
  product_title   String,
  sku             String,
  quantity        UInt32,
  price           Decimal(18,4),
  total_discount  Decimal(18,4),
  cogs_per_unit   Nullable(Decimal(18,4)),
  processed_at    DateTime64(3, 'UTC')
)
ENGINE = ReplicatedMergeTree(...)
ORDER BY (workspace_id, processed_at, order_source_id, source_id)
PARTITION BY toYYYYMM(toDate(processed_at));
```

#### `raw.shipments_local`
```sql
CREATE TABLE raw.shipments_local ON CLUSTER brain_ch (
  workspace_id        UUID,
  source              LowCardinality(String),   -- 'shiprocket','delhivery','bluedart'
  source_id           String,
  order_source_id     String,
  awb_code            String,
  courier_name        LowCardinality(String),
  pickup_pincode      String,
  delivery_pincode    String,
  payment_method      LowCardinality(String),
  status              LowCardinality(String),   -- 'delivered','rto_initiated','rto_delivered','in_transit','ndr','lost'
  ndr_reason          LowCardinality(String),
  forward_shipping_cost Decimal(18,4),
  return_shipping_cost  Decimal(18,4),
  cod_charges          Decimal(18,4),
  charge_amount        Decimal(18,4),
  is_rto              UInt8,
  is_cod              UInt8,
  pickup_attempted_at DateTime64(3, 'UTC'),
  delivered_at        Nullable(DateTime64(3, 'UTC')),
  rto_at              Nullable(DateTime64(3, 'UTC')),
  delivery_attempts   UInt8,
  created_at          DateTime64(3, 'UTC')
)
ENGINE = ReplicatedMergeTree(...)
ORDER BY (workspace_id, created_at, source_id)
PARTITION BY toYYYYMM(toDate(created_at));
```

#### `raw.ad_spend_local`
```sql
CREATE TABLE raw.ad_spend_local ON CLUSTER brain_ch (
  workspace_id       UUID,
  date               Date,
  platform           LowCardinality(String),   -- 'meta','google','tiktok','snap'
  account_id         String,
  campaign_id        String,
  campaign_name      String,
  adset_id           String,
  adset_name         String,
  ad_id              String,
  ad_name            String,
  campaign_type      LowCardinality(String),   -- 'acquisition','non_acquisition','brand','unclassified'
  spend              Decimal(18,4),
  impressions        UInt64,
  clicks             UInt64,
  conversions        UInt32,
  conversion_value   Decimal(18,4),
  add_to_cart        UInt32,
  checkout_initiated UInt32,
  purchases          UInt32,
  purchase_value     Decimal(18,4),
  video_views_3s     Nullable(UInt64),
  video_thruplay     Nullable(UInt64),
  video_p25_views    Nullable(UInt64),
  video_p50_views    Nullable(UInt64),
  video_p75_views    Nullable(UInt64),
  video_p95_views    Nullable(UInt64),
  video_avg_watch_time_seconds Nullable(Decimal(10,2)),
  creative_id        String,
  creative_type      LowCardinality(String),   -- 'video','image','carousel','collection'
  ingested_at        DateTime64(3, 'UTC')
)
ENGINE = ReplicatedMergeTree(...)
ORDER BY (workspace_id, date, platform, campaign_id, adset_id, ad_id)
PARTITION BY toYYYYMM(date);
```

#### `agg.daily_metrics_local` (materialized view target)
```sql
CREATE TABLE agg.daily_metrics_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  date             Date,
  gross_sales      Decimal(18,4),
  discounts        Decimal(18,4),
  refunds          Decimal(18,4),
  tax              Decimal(18,4),
  net_revenue      Decimal(18,4),                  -- gross - discounts - refunds
  net_revenue_ex_tax Decimal(18,4),                -- net - tax
  orders           UInt32,
  new_customer_orders UInt32,
  returning_customer_orders UInt32,
  unique_customers UInt32,
  cogs             Decimal(18,4),
  variable_costs   Decimal(18,4),
  meta_ad_spend    Decimal(18,4),
  google_ad_spend  Decimal(18,4),
  total_ad_spend   Decimal(18,4),
  acquisition_ad_spend Decimal(18,4),
  cm1              Decimal(18,4),
  cm2              Decimal(18,4),
  cm3              Decimal(18,4),
  rto_count        UInt32,
  rto_value        Decimal(18,4),
  rto_cost         Decimal(18,4),
  cod_orders       UInt32,
  prepaid_orders   UInt32,
  acos             Float64,
  mer              Float64,
  amer             Float64,
  blended_roas     Float64,
  cac              Decimal(18,4),
  aov              Decimal(18,4)
)
ENGINE = ReplicatedReplacingMergeTree(...)
ORDER BY (workspace_id, date)
PARTITION BY toYYYYMM(date);
```

#### `agg.cohort_aggregates_local`
```sql
CREATE TABLE agg.cohort_aggregates_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  cohort_month     Date,                          -- first day of acquisition month
  months_since_acquisition UInt16,
  new_customers    Nullable(UInt32),              -- populated only for months_since_acquisition=0
  customers_with_order UInt32,
  total_revenue    Decimal(18,4),
  total_cm2        Decimal(18,4),
  repeat_rate      Float64,
  cumulative_repeat_rate Float64,
  avg_revenue_per_original_customer Decimal(18,4)
)
ENGINE = ReplicatedReplacingMergeTree(...)
ORDER BY (workspace_id, cohort_month, months_since_acquisition)
PARTITION BY toYYYYMM(cohort_month);
```

#### `agg.pincode_reliability_local`
```sql
CREATE TABLE agg.pincode_reliability_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  pincode          String,
  city             String,
  state            String,
  tier             UInt8,
  trailing_90d_orders UInt32,
  trailing_90d_revenue Decimal(18,4),
  trailing_90d_rto_count UInt32,
  trailing_90d_rto_rate Float64,
  trailing_90d_cod_rate Float64,
  trailing_90d_repeat_rate Float64,
  trailing_90d_aov Decimal(18,4),
  profitability_score Float64,                    -- 0–100
  recommended_action LowCardinality(String),      -- 'disable_cod','allow_cod','watch','target_geo_ads'
  last_updated DateTime
)
ENGINE = ReplicatedReplacingMergeTree(...)
ORDER BY (workspace_id, pincode);
```

#### `agg.first_product_attribution_local`
```sql
CREATE TABLE agg.first_product_attribution_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  product_id       String,
  product_title    String,
  first_order_customers UInt32,
  customers_with_2nd_order UInt32,
  customers_with_3rd_order UInt32,
  customers_with_4th_plus_order UInt32,
  additional_order_rate Float64,
  avg_ltv          Decimal(18,4),
  avg_time_to_second_order_days Float64,
  computed_at DateTime
)
ENGINE = ReplicatedReplacingMergeTree(...)
ORDER BY (workspace_id, product_id);
```

#### `agg.customer_states_local`
```sql
CREATE TABLE agg.customer_states_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  customer_id      UUID,
  email_hash       FixedString(64),
  phone_hash       FixedString(64),
  state            LowCardinality(String),        -- 'new','returning','reactivated','at_risk','churned'
  state_since      DateTime,
  total_orders     UInt32,
  total_revenue    Decimal(18,4),
  total_cm2        Decimal(18,4),
  first_order_date Date,
  last_order_date  Date,
  first_product_id String,
  first_acquisition_channel LowCardinality(String),
  first_order_had_discount UInt8,
  first_discount_code String,
  first_payment_method LowCardinality(String),
  first_city       String,
  first_city_tier  UInt8,
  predicted_ltv_30d  Decimal(18,4),
  predicted_ltv_90d  Decimal(18,4),
  predicted_ltv_180d Decimal(18,4),
  predicted_active_probability Float64,
  ltv_calculated_at DateTime
)
ENGINE = ReplicatedReplacingMergeTree(ltv_calculated_at)
ORDER BY (workspace_id, customer_id);
```

### 11.5 Materialized Views

```sql
-- Refresh-on-insert: every order event updates daily_metrics
CREATE MATERIALIZED VIEW agg.mv_daily_metrics_from_orders ON CLUSTER brain_ch
TO agg.daily_metrics_local AS
SELECT
  workspace_id,
  toDate(processed_at) AS date,
  sumIf(total_price, financial_status != 'refunded') AS gross_sales,
  sum(total_discounts) AS discounts,
  sumIf(total_price, financial_status = 'refunded') AS refunds,
  sum(total_tax) AS tax,
  (gross_sales - discounts - refunds) AS net_revenue,
  (net_revenue - tax) AS net_revenue_ex_tax,
  count() AS orders,
  countIf(is_new_customer = 1) AS new_customer_orders,
  countIf(is_new_customer = 0) AS returning_customer_orders,
  uniqExact(customer_id) AS unique_customers,
  countIf(payment_method = 'COD') AS cod_orders,
  countIf(payment_method = 'Prepaid') AS prepaid_orders
FROM raw.orders_local
GROUP BY workspace_id, date;
```

Additional MVs apply COGS resolution from line_items and join shipments for RTO data — full SQL in `TECH/03_metrics_engine.md`.

### 11.6 Query Gateway (`pylibs/brain_clickhouse/query.py`)

Every ClickHouse query in Python services must go through this helper. It:
1. Enforces `workspace_id =` is present in the WHERE clause (raises `MissingTenantPredicate` if not)
2. Adds query timeout (`max_execution_time = 30` for dashboard reads)
3. Adds memory cap (`max_memory_usage`)
4. Logs query + duration + bytes scanned to CloudWatch
5. Rejects queries scanning > 100M rows without `LIMIT`

### 11.7 Read Replicas & Routing

- **Phase 2:** analytics-service reads from a dedicated set of ClickHouse replicas; writes (materialization) go to primary
- **Phase 4 multi-region:** read replicas in secondary regions for sub-100ms dashboards outside India

---

## 12. Data Architecture (S3, Redis, Kafka tiered storage)

### 12.1 S3 Buckets

| Bucket | Purpose | Lifecycle |
|--------|---------|-----------|
| `brain-raw-payloads-{env}` | Backup of every raw integration payload | Glacier transition after 90d, delete after 7y |
| `brain-exports-{env}` | User-generated CSV/XLSX/PDF exports | 30-day expiry |
| `brain-kafka-tiered-{env}` | MSK tiered storage backend (long-tail Kafka data) | MSK-managed |
| `brain-call-recordings-{env}` | AI call recordings (consent only) | Encrypt with per-brand KMS key; 1-year retention |
| `brain-creative-assets-{env}` | Brand creative assets (images, videos generated/uploaded) | No expiry |
| `brain-backups-{env}` | Postgres/ClickHouse logical backups | 90-day retention |

All buckets:
- Server-side encryption with AWS KMS
- Block all public access
- Versioning enabled
- Object lock on `brain-call-recordings-{env}` and Decision Log exports

### 12.2 Redis (ElastiCache)

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `rl:user:{user_id}:{minute}` | 70s | User rate limit (sliding window) |
| `rl:workspace:{workspace_id}:{minute}` | 70s | Workspace rate limit |
| `rl:ai_chat:{user_id}` | 60s | AI Chat per-user rate limit |
| `session:{session_id}` | 30 min | Session cache |
| `metric:{workspace_id}:{metric}:{from}:{to}` | 60s | Hot metric cache |
| `workspace:{slug}` | 5 min | Workspace metadata cache |
| `workspace_member:{workspace_id}:{user_id}` | 5 min | Member lookup cache |
| `idempotency:{key}` | 24 hours | Idempotency keys for mutations |
| `feature_flag:{workspace_id}` | 5 min | Feature flag cache |

**Cluster mode:** 3 shards initially, scale to 12 at Phase 3. ~10 GB working set.

### 12.3 Kafka Tiered Storage

- MSK tiered storage backed by S3
- Hot tier (broker disks): last 24 hours
- Warm tier (S3): older data, transparently accessible
- Enables `integrations.*` topics to have effective infinite retention without paying for broker disk

---

## 13. Integration Architecture

### 13.1 Standard Connector Pattern

Every connector in `ingestion-service` implements:
```python
class Connector(ABC):
    provider: str

    async def authenticate(self, credentials: dict) -> AuthResult: ...
    async def refresh_token(self, integration: Integration) -> RefreshResult: ...
    async def list_resources(self, integration: Integration) -> list[Resource]: ...  # e.g., ad accounts, channels
    async def sync(self, integration: Integration, window: SyncWindow) -> SyncResult: ...
    async def receive_webhook(self, payload: bytes, signature: str) -> WebhookResult: ...
    async def canonicalize(self, raw_event: dict) -> list[CanonicalEvent]: ...
    async def health_check(self, integration: Integration) -> HealthStatus: ...
```

**Backfill = sync with bounded window. Live = sync with unbounded window (cursor-based).** Same code path.

### 13.2 OAuth Token Security

- All OAuth tokens (Meta access + refresh, Google refresh, Shopify access, etc.) stored as **AES-256-GCM ciphertext** in `core.integrations.encrypted_credentials`
- Per-brand encryption key, identified by `encryption_key_id`, stored in AWS Secrets Manager
- Wrapper API on `core-service`: `encryptIntegrationCredentials(workspaceId, plaintext)` / `decryptIntegrationCredentials(workspaceId, ciphertext)` — every read/write goes through the wrapper
- Adds ~1ms per token operation; acceptable
- Plaintext tokens never logged
- Key rotation: monthly via AWS Secrets Manager rotation; old keys retained for read-back during transition

### 13.3 Shopify Integration

**OAuth:**
- `GET /api/shopify/connect?shop={shop}` → validate domain → redirect to `https://{shop}/admin/oauth/authorize` with scopes `read_orders,read_products,read_customers,read_analytics,read_inventory`
- `GET /api/shopify/callback?code=...&hmac=...&shop=...` → HMAC validate → POST `/admin/oauth/access_token` → encrypt + UPSERT `core.integrations`

**Sync:**
- GraphQL Admin API 2025-01
- Paginated (50 records/page, cursor-based)
- Bulk Operations API for >10K orders (returns JSONL file URL)
- Webhook topics: `orders/create`, `orders/updated`, `orders/paid`, `refunds/create`
- HMAC validated via `X-Shopify-Hmac-Sha256` against `SHOPIFY_CLIENT_SECRET`

### 13.4 Meta Ads Integration

**OAuth:**
- Generate state token (10-min TTL, stored in `core.oauth_states`)
- Redirect to `https://www.facebook.com/v22.0/dialog/oauth` with scope `ads_read,ads_management,business_management`
- Callback: validate state → exchange code for long-lived token (60-day) → fetch ad accounts via Graph API → encrypt + UPSERT

**Sync:**
- Incremental: last 7 days
- Backfill: 30-day chunks up to 730 days
- Multi-account: iterate `selected_ad_account_ids`
- Insights endpoint: `/act_{id}/insights` at `level=ad`
- Fields:
  - Spend, impressions, clicks, CTR, CPM, CPC
  - `actions` (filter: `offsite_conversion.fb_pixel_purchase`, `offsite_conversion.fb_pixel_add_to_cart`, `offsite_conversion.fb_pixel_initiate_checkout`)
  - `action_values` (filter: `offsite_conversion.fb_pixel_purchase`)
  - `video_p25_watched_actions`, `video_p50_watched_actions`, `video_p75_watched_actions`, `video_p95_watched_actions`
  - `video_thruplay_watched_actions`, `video_avg_time_watched_actions`
- Rate limit: ~200 req/hour standard; request increase via developer portal
- **Server-side CAPI integration:** required for Meta Business Partner status

### 13.5 Google Ads Integration

**OAuth with PKCE:**
- Generate `code_verifier` (PKCE); store in `core.oauth_states`
- Redirect to `accounts.google.com/o/oauth2/v2/auth` with scope `https://www.googleapis.com/auth/adwords` and `code_challenge_method=S256`
- Callback: exchange `code + verifier` for access + refresh tokens

**Sync:**
- GAQL queries via `GoogleAdsService.SearchStream`
- Campaign-level + keyword-level + shopping funnel
- Multi-customer: iterate `selected_customer_ids`
- For shopping funnel (ATC/CI/Purchase): GA4 integration via Google Analytics Data API (Phase 2)

### 13.6 Shiprocket Integration

**Credential-based:**
- `POST /api/integrations/shiprocket/connect` with `{email, password}`
- POST to `https://apiv2.shiprocket.in/v1/external/auth/login` → JWT token (24h refresh)
- Encrypt + store credentials

**Sync:**
- `GET /v1/external/orders?page=N&per_page=100` — paginated
- `GET /v1/external/shipments/details-by-awbs` — granular status timeline
- `GET /v1/external/orders/ndr` — orders in NDR with reason codes
- Webhook: register `https://brain.pipadacapital.com/api/webhooks/shiprocket` for `shipment.delivered`, `shipment.rto`, `shipment.ndr`
- Token refresh: 24-hour cycle

### 13.7 Klaviyo Integration

**API Key:**
- `POST /api/integrations/klaviyo/connect` with `{api_key}`
- Validate via test API call → encrypt + store

**Sync:**
- `GET /campaigns/` (REST v2023-10)
- `GET /campaigns/{id}/campaign-recipient-estimations/`
- `GET /events/?filter=metric_id:placed_order_metric_id` → revenue attribution per campaign
- `GET /flows/` → automated flow performance
- Webhook: subscribe to Placed Order events for real-time attribution
- Attribution: 5-day click window (configurable)

### 13.8 Razorpay Integration

**API Key:**
- `POST /api/integrations/razorpay/connect` with `{key_id, key_secret}`
- Validate via test API call → encrypt + store

**Sync:**
- Payments API: list payments, settlements
- Webhooks: `payment.captured`, `payment.failed`, `settlement.processed`

### 13.9 WooCommerce Integration

- REST API v3 with consumer key + secret
- `POST /api/integrations/woocommerce/connect` with `{site_url, consumer_key, consumer_secret}`
- Endpoints: `/wp-json/wc/v3/orders`, `/products`, `/customers`
- Webhook signature validation (Phase 2 — currently a noted gap in the existing codebase)

### 13.10 Phase 2+ Connectors (Quality Gradient)

**Green (clean API):**
- Salla (Saudi GCC), Zid (GCC) — native API + Partner Program
- Amazon SP-API (India + AE) — mature REST + Data Kiosk GraphQL
- Flipkart Marketplace Seller API v3.0 — OAuth, Partner Dashboard
- Noon — mature REST seller API
- BigBasket — limited seller API (gated; pursue direct access)

**Yellow (gated API requiring per-brand onboarding):**
- Myntra, Ajio, Meesho, Namshi, Talabat

**Red (no API, workaround):**
- Nykaa, Blinkit, Zepto, Instamart, Ounass, Sharaf DG, Tata Cliq
- **Workaround pattern:** Gmail OAuth → ingestion-service receives email notifications of new seller reports → LLM (Haiku) extracts structured data from PDF/Excel attachments → publishes to canonical events topic
- Health monitoring: pattern-match seller email subject lines daily; alert brand within 1 hour if no expected email received for 24 hours

### 13.11 Sync Scheduling

- **EventBridge Scheduler** triggers sync jobs per (workspace, integration) at configurable intervals
- Default cadence:
  - Shopify orders: every 15 minutes (real-time webhook + safety polling)
  - Meta/Google ads insights: every 6 hours during the day, full day at midnight IST
  - Shiprocket: every 30 minutes
  - Klaviyo: every 2 hours
  - Razorpay: webhook-driven, daily safety sweep at 2 AM IST

### 13.12 Rate Limiting on Sync Endpoints

- **Per workspace:** max 1 manual sync trigger per 15 minutes per integration
- Background scheduled syncs not rate-limited (but throttled per partner API limits)
- Backfill jobs go to a separate priority-low queue with concurrency cap

---

## 14. Metric Engine & Formula Book

This is the single source of truth for all ecommerce metrics inside Brain. Every layer must use these definitions. If two parts of the system calculate the same metric differently, the system is broken.

### 14.1 Metric Registry

A versioned, typed registry in `packages/lib-metrics/` (TS) and `pylibs/brain_metrics/` (Python). Every metric has:
- `name` (canonical key)
- `display_name`
- `unit` (currency, percent, ratio, count, duration)
- `formula` (referenced from this section)
- `aggregation` (sum, avg, first, last, custom)
- `customer_type_filter` (optional: all/new/returning)
- `requires` (list of input metrics/columns)
- `goal_direction` (higher_is_better, lower_is_better)
- `rag_band` (per goal_direction)

### 14.2 Revenue Definitions

| Metric | Formula | Notes |
|--------|---------|-------|
| **Gross Sales** | Sum of order `total_price` (including tax, discounts) | Vanity metric. Never use for decisions. |
| **Net Revenue** | Gross Sales − Tax | Real revenue figure (₹999 at 18% GST → ₹846.61). |
| **Net Sales** | Net Revenue − Refunds − Discounts | Used for cohort analysis. |
| **Net Sales Net Tax** | Gross Sales − Tax − Refunds − Discounts | **Recommended default for Indian DTC.** |
| **Net Revenue (alt)** | Net Sales − Shipping Revenue | When excluding customer-paid shipping. |
| **Total Sales** | Gross Sales − Returns | Discounts embedded in price (no separate tracking). |
| **Recognised Revenue** | Net Sales for delivered orders only (COD counted after delivery confirmation) | Used for P&L. |

**Workspace setting `revenue_definition`** chooses which definition all reports use platform-wide.

### 14.3 Contribution Margin Waterfall

```
Gross Sales
  − Tax (GST stripped at first step)
  − Refunds
  − Discounts
= Net Revenue (ex tax)
  − COGS
= CM1 (Gross Margin)
  − Forward Shipping
  − Packaging
  − Payment Gateway Fees (2% prepaid)
  − COD Handling Fees (₹25–50 per COD order)
  − RTO Cost (RTO rate × (return shipping + restocking + COGS damage))
  − Returns Provisions (modelled)
  − Per-order CS allocation
= CM2 (Post-Fulfilment Margin)
  − Meta Ad Spend
  − Google Ad Spend
  − Other Ad Spend
= CM3 (Post-Marketing Margin)
  − Fixed Costs (misc expenses, prorated)
= Operating Profit
  − Founder Salary
= Net Profit
```

**Customer filter:** the same chain can be computed for All / New Customers / Returning Customers (filter `is_new_customer`).

### 14.4 True CM2 (RTO-Adjusted)

```
True CM2 = (Revenue × Realization Rate) − COGS − Forward Shipping
          − (RTO Rate × Return Shipping Cost)
          − (RTO Rate × Restocking Cost)
          − Payment Fees (only on realized orders)
          − Packaging
          − (RTO Rate × COGS portion unrecoverable)
          − Ad Spend

where:
  Realization Rate = 1 − RTO Rate
  RTO Rate = RTO Orders / Total Shipped Orders
```

A typical Indian D2C brand reporting "CM1 68%" actually has CM1 closer to **39%** once RTO-adjusted on a 25% RTO rate (see worked example in business doc).

### 14.5 COGS Resolution (3-Tier)

For each line item, resolve COGS in this order:
1. **Workspace `cogsSettings.overrideAllCogsPercent`** if set → `line_item.price * pct`
2. **Per-product COQ** (in `core.product_cogs`) → use directly per unit × quantity
3. **Workspace `cogsSettings.fallbackCogsPercent`** → `line_item.price * pct`

Implemented in `pylibs/brain_metrics/cogs.py` (port of `lib/cogs/resolve.ts` from existing Looqus codebase).

### 14.6 Marketing Efficiency Ratios

| Metric | Formula | Notes |
|--------|---------|-------|
| **ROAS** | Platform-reported revenue ÷ platform-reported spend | Vanity / inflated. Never used as P&L decision input. |
| **MER** | Total Net Revenue ÷ Total Marketing Spend (all channels) | Cannot be gamed. The honest blended number. |
| **aMER** | New Customer Revenue ÷ Acquisition Ad Spend | Surgical metric. *Is my acquisition engine working?* |
| **paMER** | Total Revenue ÷ Total Paid Media Spend | Excludes organic/direct/email revenue if trackable |
| **iROAS** | (Revenue with ads − Estimated revenue without ads) ÷ Ad Spend | Phase 4+. Requires geo holdout testing. |
| **New-Customer MER (all-in)** | New-customer Net Revenue ÷ Total Marketing Spend | Strips repeat halo. |
| **All-in aMER** | New Customer Revenue ÷ (Ad Spend + Creative + Tools + Salaries allocated) | Honest blended with full marketing cost. |

Where:
- **New Customer Revenue** = revenue from orders where `is_new_customer = TRUE`
- **Acquisition Ad Spend** = spend from campaigns where `campaign_type = 'acquisition'`

### 14.7 CAC

| Metric | Formula | Notes |
|--------|---------|-------|
| **CAC** | Total Marketing Spend ÷ New Customers Acquired (delivered orders only) | Excludes salaries by default. |
| **Blended CAC** | Total Ad Spend ÷ New Customer Count (all-in, not delivered-only) | Reported separately. |
| **nCAC** | Acquisition Ad Spend ÷ New Customer Count | Acquisition-channel-specific |
| **aCAC** (all-in) | (Marketing Spend + Salaries) ÷ New Customer Count | When running all-in CAC view |

Marketing Spend includes: ad platform spend, creative production, influencer fees, tooling allocated.

### 14.8 LTV & Cohort Metrics

- **LTV calculated using BG/NBD + Gamma-Gamma**, not naive averages (Section 18)
- LTV reported at 30, 60, 90, 180, 365 days per acquisition cohort
- LTV uses **CM2 contribution per order**, not Gross Sales
- Cohort retention curves use **Kaplan-Meier survival analysis**
- **Repeat Rate** = % of customers with at least 2 orders in the LTV window
- **Repeat Purchase Rate** = total repeat orders ÷ total orders
- **LTV:CAC** = Cumulative CM2 per customer (at N months) ÷ CAC
- **CAC Payback Period (months)** = CAC ÷ (Monthly CM2 per Active Customer)

### 14.9 RTO / COD Metrics (India)

| Metric | Formula |
|--------|---------|
| **RTO Rate** | RTO Orders ÷ Orders Shipped |
| **RTO Cost per Order** | Forward shipping + Reverse logistics + Restocking labour + Inventory write-down provision |
| **COD Conversion Rate** | COD Orders Delivered ÷ COD Orders Placed |
| **Prepaid Conversion Rate** | Prepaid Orders Delivered ÷ Prepaid Orders Placed |
| **COD Realization Rate** | Successfully Delivered COD Orders ÷ Total COD Shipped Orders |
| **Effective Revenue (COD)** | Order Value × (1 − RTO Rate) − COD Handling Fee − (RTO Rate × (Return Shipping + Restocking)) |
| **Effective Revenue (Prepaid)** | Order Value × (1 − Prepaid RTO Rate) − Payment Gateway Fee − (Prepaid RTO Rate × (Return Shipping + Restocking)) |
| **Break-even COD RTO Rate** | `[V×P + (COD_fee − PG_fee) + P×(S+RS)] / (V + S + RS)` where V=order value, P=prepaid RTO rate, S=return shipping, RS=restocking |
| **Prepaid Incentive ROI** | (Prepaid Effective Revenue − COD Effective Revenue − Incentive Cost) ÷ Incentive Cost |

### 14.10 Shopping Funnel Metrics (Paid Media)

| Metric | Formula |
|--------|---------|
| **CTR** | Clicks ÷ Impressions × 100 |
| **ATC Rate** | Add-to-Cart Events ÷ Clicks × 100 |
| **CI/ATC Rate** | Checkout Initiated ÷ Add-to-Cart Events × 100 |
| **Purchase/CI Rate** | Purchases ÷ Checkout Initiated × 100 |
| **Overall CVR** | Purchases ÷ Clicks × 100 |
| **Cost per ATC** | Ad Spend ÷ Add-to-Cart Events |
| **Cost per CI** | Ad Spend ÷ Checkout Initiated |
| **Cost per Purchase (CPP)** | Ad Spend ÷ Purchases |

Color-coded RAG:
- ATC Rate: <5% Red, 5–15% Amber, >15% Green
- CI/ATC: <50% R, 50–70% A, >70% G
- Purchase/CI: <25% R, 25–45% A, >45% G

### 14.11 Video Ad Creative Metrics

| Metric | Formula | Benchmark |
|--------|---------|-----------|
| **Hook Rate (3-Second View Rate)** | 3-Second Views ÷ Impressions × 100 | >30% strong, 15–30% avg, <15% weak |
| **Hold Rate (ThruPlay Rate)** | ThruPlay Views ÷ 3-Second Views × 100 | >25% strong, 10–25% avg, <10% weak |
| **Video 25/50/75/95% Completion** | Views at N% ÷ Impressions × 100 | — |
| **Average Watch Time** | Total seconds watched ÷ Total impressions | — |

**Diagnostic logic in `pylibs/brain_metrics/creative.py`:**
- Low Hook (<15%) + Good Hold (>25%) → "Creative has weak opening; first 3 seconds not stopping scroll."
- Good Hook (>30%) + Low Hold (<10%) → "Strong opening but fails to hold attention."
- Good Hook + Good Hold + Low CTR (<0.8%) → "Watched but not clicked; CTA/offer issue."
- Good Hook + Good Hold + Good CTR + Low ATC (<5%) → "Ads working; landing page conversion issue."

### 14.12 Statistical Anomaly Detection

```python
def detect_anomaly(metric_name, current_value, historical_values,
                   threshold_sd=2.0, direction="both"):
    if len(historical_values) < 7:
        return False, 0, "insufficient_data"
    mean = np.mean(historical_values)
    std = np.std(historical_values)
    if std == 0:
        return False, 0, "no_variance"
    z_score = (current_value - mean) / std
    is_anomaly = (
        (direction == "up" and z_score > threshold_sd) or
        (direction == "down" and z_score < -threshold_sd) or
        (direction == "both" and abs(z_score) > threshold_sd)
    )
    severity = "critical" if abs(z_score) >= 3.0 else ("high" if abs(z_score) >= 2.0 else "medium")
    return is_anomaly, z_score, severity
```

Full configuration in Section 20.

### 14.13 Goal RAG Logic

```
Higher-is-better (MER, aMER, CM3%, Revenue, New Customers, Repeat Rate):
  Green: Actual ≥ Goal × 0.95
  Amber: Goal × 0.80 ≤ Actual < Goal × 0.95
  Red:   Actual < Goal × 0.80

Lower-is-better (CAC, ACOS, RTO Rate):
  Green: Actual ≤ Goal × 1.05
  Amber: Goal × 1.05 < Actual ≤ Goal × 1.20
  Red:   Actual > Goal × 1.20
```

### 14.14 Discount, Refund, Tax Handling

- **Discount:** always applied at line-item level **before** GST calculation. Brain never reports CM2 on pre-discount price.
- **Refund:** reduces Net Sales and removes the contribution from the original order's CM. Refund processing fees → opex.
- **GST:** always stripped from Gross Sales at the **first calculation step.** Every downstream metric is GST-exclusive.
- **Shipping charged to customer:** treated as revenue, not cost offset. Shipping cost paid to logistics partner is the actual cost.
- **Ad spend GST:** 18% input GST credit assumed **only** if the brand has registered for it. Default: assume no credit.

### 14.15 Cost Inclusion Rules (Non-Negotiable)

**Always included in CM2:**
- COGS (landed cost: product + freight in + customs + warehousing per unit)
- Forward shipping
- Packaging (primary + secondary)
- Payment gateway fees
- COD handling fees
- RTO provisions (modelled, not actuals)
- Returns provisions
- Per-order CS allocation

**Excluded from CM2 (live in CM3 or opex):**
- Marketing spend → CM3
- Salaries → opex
- Tooling → opex
- Rent → opex
- Tax payments to government (CGST/SGST/IGST flow through Net Revenue, not cost)


---

## 15. India Regional Adapter

### 15.1 The Pattern

All India-specific economics live behind a `RegionAdapter` interface (`pylibs/brain_regional/`). Adding a region = implementing the interface, not rewriting the metric engine.

```python
class RegionAdapter(ABC):
    region_code: str   # 'IN', 'AE', 'SA', 'US', 'EU'

    @abstractmethod
    def strip_tax(self, gross_price: Decimal, product_id: str) -> Decimal: ...

    @abstractmethod
    def calculate_payment_fee(self, order: Order) -> Decimal: ...

    @abstractmethod
    def calculate_rto_cost(self, order: Order, shipment: Shipment) -> Decimal: ...

    @abstractmethod
    def classify_pincode_tier(self, pincode: str) -> int: ...   # 1, 2, or 3

    @abstractmethod
    def festival_multiplier(self, date: date, category: str) -> Decimal: ...

    @abstractmethod
    def currency_code(self) -> str: ...                          # 'INR', 'AED', 'SAR', 'USD'

    @abstractmethod
    def currency_format(self, amount: Decimal) -> str: ...       # ₹1,23,456 vs $123,456
```

### 15.2 India Adapter Specifics

#### GST Stripping
```python
def strip_tax(gross_price: Decimal, product_id: str) -> Decimal:
    rate = product_gst_rate(product_id) or workspace.default_gst_rate  # 0.18 default
    return gross_price / (1 + rate)
```

GST slab defaults (pre-loaded; product-level override):

| Category | Rate |
|----------|------|
| Beauty premium (cosmetics, skincare, perfumes) | 18% |
| Beauty essential (hair care, basic toiletries) | 12% |
| Ayurvedic | 12% |
| Packaged food | 5% |
| Processed/branded food | 12% |
| Health supplements | 18% |
| Apparel ≤ ₹1000 MRP | 5% |
| Apparel > ₹1000 MRP | 12% |
| Footwear ≤ ₹500 | 5% |
| Footwear > ₹500 | 18% |
| Home essentials | 12% |
| Luxury home | 18% |

#### Payment Fees
- COD orders: ₹35 default handling fee (₹25–50 range, configurable per workspace)
- Prepaid orders: 2% gateway fee (Razorpay/PhonePe/PayU)
- ₹999 prepaid order: ₹20 gateway fee
- ₹999 COD order: ₹35 handling fee + COD risk

#### RTO Cost
```python
def calculate_rto_cost(order, shipment) -> Decimal:
    if not shipment.is_rto:
        return Decimal(0)
    return (
        workspace.rto_return_shipping_cost
        + workspace.rto_restocking_cost
        + (order.cogs_total * workspace.rto_damage_rate)  # 5% default
    )
```

#### Pincode Tier Classification
- Pre-loaded India pincode database (~29,000 pincodes) → city, district, state
- City tier: hardcoded list of Tier 1 cities (Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad), Tier 2 (Jaipur, Lucknow, Surat, Kanpur, Nagpur, Indore, Bhopal, Patna, Vadodara, Ludhiana, …), Tier 3 = everything else

#### Festival Multipliers
Pre-loaded calendar (refreshed annually for lunar-calendar shifts):

| Festival | Period | Default Multiplier | Categories |
|----------|--------|--------------------|------------|
| Navratri | Late Sep / Early Oct (9 days) | 1.8× | fashion, beauty, jewelry, footwear (esp. Gujarat, Rajasthan, Maharashtra) |
| Dussehra | 1 day end of Navratri | 2.0× | all |
| Karwa Chauth | 1 day ~October | 1.5× | beauty, jewelry, fashion |
| Dhanteras | 2 days before Diwali | 3.0× | gold, electronics, home, kitchenware |
| Diwali | 5 days (Dhanteras → Bhai Dooj) | 4.0× (peak day 6.0×) | all — gifting, beauty, fashion, home; pre-period 2.0× (2 wks before); post-period 0.5× (hangover) |
| Christmas/NY | Dec 20 – Jan 5 | 1.4× | all — stronger in metro / premium |
| Republic Day Sale | Jan 24–26 | 1.6× | all |
| Valentine | Feb 7–14 | 1.5× | beauty, gifting, fashion, chocolates |
| Holi | 2–3 days March | 1.8× | beauty, skincare, fashion, colors |
| Ugadi / Gudi Padwa | 1 day March–April (regional) | 1.4× | home, fashion (south India) |
| Eid | 3–5 days (dates vary) | 2.0× | fashion, beauty, food, gifting (UP, Maharashtra, WB, Kerala) |
| Independence Day Sale | Aug 13–15 | 1.5× | all |
| Onam | 10 days Aug–Sep | 2.2× | all (Kerala-specific, enormous for Kerala brands) |
| Wedding Season 1 | Nov–Feb | 1.6× | fashion, beauty, jewelry, gifting |
| Wedding Season 2 | Apr–May | 1.4× | fashion, beauty, jewelry |

Brain-specific seasonal index (per brand, from 2+ years of data) overrides defaults once available.

### 15.3 GCC Adapter (Phase 1 Parallel Build)

Same interface, different specifics:
- VAT 5% (UAE/KSA) instead of GST
- Aramex, DHL, SMSA logistics
- Tabby, Tamara, Telr, Checkout.com, Stripe payments
- Ramadan/Eid/National Day festival calendar
- Pincode = postal code where applicable; otherwise emirate/region tier
- Currency: AED (UAE), SAR (KSA)

### 15.4 US/EU Adapter (Phase 4)

- US sales tax (per state)
- EU VAT (per country)
- USPS/UPS/FedEx + DHL logistics
- Stripe + ACH payments
- Black Friday / Cyber Monday calendar
- Currency: USD, EUR

---

## 16. Customer Lifecycle Engine

### 16.1 The Five States

Every customer is in exactly one state at any given time:
1. **New** — just placed first order (within current period)
2. **Returning** — has 2+ orders, most recent within At-Risk threshold
3. **Reactivated** — previously Churned, placed a new order
4. **At-Risk** — has not ordered in longer than P40 threshold
5. **Churned** — has not ordered in longer than P80 threshold

### 16.2 Data-Driven Churn Thresholds (P40 / P80)

Brain derives thresholds from each brand's actual order data — never arbitrary 90-day windows.

```python
def calculate_churn_thresholds(workspace_id):
    """Run monthly on the 1st using past 12 months of orders."""
    gaps = []
    for customer_id, orders in get_orders_by_customer(workspace_id, months=12):
        sorted_orders = sorted(orders, key=lambda o: o.processed_at)
        for i in range(1, len(sorted_orders)):
            gap_days = (sorted_orders[i].processed_at - sorted_orders[i-1].processed_at).days
            gaps.append(gap_days)
    return {
        'at_risk_days': int(np.percentile(gaps, 40)),
        'churned_days': int(np.percentile(gaps, 80)),
    }
```

Stored in `core.workspace_thresholds`. Recalculation: monthly cron, written to a versioned row so historical state assignments don't drift.

**Why P40 and P80:**
- P40: 40% of repeat purchases happen before this many days. Customer with gap > P40 ordering slower than 60% of repeat purchases → worth watching.
- P80: 80% of repeat purchases happen before this many days. Customer with gap > P80 ordering slower than 95%+ of repeat purchases → almost certainly churned.

### 16.3 State Assignment Algorithm

Implemented in `analytics-service` as a nightly job:

```python
def assign_customer_state(customer_id, last_order_date, order_count,
                          at_risk_threshold, churned_threshold,
                          calculation_date, previous_state):
    days_since_last = (calculation_date - last_order_date).days
    ordered_this_period = (last_order_date == calculation_date)

    if ordered_this_period:
        if order_count == 1: return "new"
        elif previous_state == "churned": return "reactivated"
        else: return "returning"
    elif days_since_last <= at_risk_threshold:
        return "returning"
    elif days_since_last <= churned_threshold:
        return "at_risk"
    else:
        return "churned"
```

### 16.4 Net Active Customers Formula

```
Net Active Customers = New + Returning + Reactivated − (New Churns this period)
Total Active Customers = New + Returning + Reactivated + At-Risk
```

**Key insight:** if Net Active Customers is declining over time, the business is slowly dying regardless of revenue. Revenue can look flat while customer base erodes if AOV is rising.

### 16.5 Storage

- Current state per customer in `agg.customer_states_local` (ClickHouse)
- Append-only history in `agg.customer_lifecycle_events_local`:

```sql
CREATE TABLE agg.customer_lifecycle_events_local ON CLUSTER brain_ch (
  workspace_id     UUID,
  customer_id      UUID,
  event_date       Date,
  previous_state   LowCardinality(String),
  new_state        LowCardinality(String),
  trigger_type     LowCardinality(String),    -- 'new_order','time_elapsed','at_risk_threshold','churn_threshold'
  trigger_order_id String,                    -- nullable
  created_at       DateTime
)
ENGINE = ReplicatedMergeTree(...)
ORDER BY (workspace_id, event_date, customer_id);
-- Never UPDATE; always APPEND.
```

---

## 17. RFM / RFMC Segmentation Engine

### 17.1 Score Definitions (Per Customer, Daily)

**R (Recency):** percentile-binned by days since last order, against the brand's own customer base (not industry).
- Score 5: most recent 20%
- Score 4: 20–40%
- Score 3: 40–60%
- Score 2: 60–80%
- Score 1: oldest 20%

**F (Frequency):** percentile-binned by order count in trailing 365 days.
- Score 5: top 20% by order count
- … Score 1: bottom 20%

**M (Monetary):** percentile-binned by **total CM2 contribution** (not Gross Sales) in trailing 365 days.
- Score 5: top 20%
- … Score 1: bottom 20%

**C (COD behaviour, India-specific):**
- Score 3: always prepaid
- Score 2: mix of COD and prepaid
- Score 1: always COD

### 17.2 The 11 Canonical Segments

```python
def assign_rfm_segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4: return "champions"
    elif r >= 3 and f >= 4: return "loyal_customers"
    elif r >= 4 and 2 <= f <= 3: return "potential_loyalists"
    elif r >= 4 and f == 1: return "new_customers"
    elif r >= 3 and f == 1: return "promising"
    elif r >= 3 and f >= 2 and m >= 2: return "need_attention"
    elif r == 2 and f <= 2: return "about_to_sleep"
    elif r == 2 and f >= 3: return "at_risk"
    elif r == 1 and f >= 4 and m >= 4: return "cannot_lose_them"
    elif r <= 2 and f >= 2: return "hibernating"
    else: return "lost"
```

Brands can define custom segments with any RFM combination + filters (SKU, channel, geography, AOV band, last product, etc.).

### 17.3 Segment Actions (Default Playbook)

| Segment | Recommended Action | Channel | Goal |
|---------|---------------------|---------|------|
| Champions (R4+, F4+, M4+) | Exclusive loyalty program, early access | WhatsApp, email | Maintain + upsell |
| Loyal | Loyalty rewards, review requests | Email | Upgrade to Champions |
| Potential Loyalists (R4+, F2–3) | 2nd-purchase incentive, subscription offer | SMS, email | Lock in 2nd/3rd purchase habit |
| At Risk (R2, F3+) | Win-back, "we miss you" offer | Email + WhatsApp | Reactivate before Lost |
| Cannot Lose Them (R1, F4+, M4+) | Personal outreach, 15–20% off | WhatsApp (personal tone) | Emergency reactivation |
| Lost (R1, F1–2, M1–2) | Suppress, or extremely compelling offer | Low-cost (email only) | Reactivate cheaply or accept churn |

### 17.4 Export to Marketing Platforms

Each segment exportable as:
- **Meta Custom Audience** via Marketing API with hashed email/phone
- **Google Customer Match** same
- **Klaviyo Segment** via Klaviyo API (tags each customer)
- **CSV** download for manual upload

### 17.5 Storage

- Snapshot per day in `notifications.rfm_scores` (Postgres) for fast lookup
- Historical trend in `agg.rfm_scores_local` (ClickHouse) for trend analysis

### 17.6 Recalculation Cadence

- **Daily** at 00:45 IST (after lifecycle state assignment)
- Use of CM2 (requires fresh daily_metrics) means RFM depends on `analytics.metrics.daily.materialized.v1` event

---

## 18. LTV Prediction Engine (BG/NBD + Gamma-Gamma)

### 18.1 Model Choice

**BG/NBD (Beta Geometric / Negative Binomial Distribution)** predicts how many more purchases a customer will make. Two assumptions:
1. While active, customer makes purchases at a customer-specific rate (gamma distribution)
2. After each purchase, probability of "death" (becoming inactive) drawn from a beta distribution

**Gamma-Gamma** predicts average transaction value.

Combined: predicted **CM2-based LTV** per customer over future window.

### 18.2 Required Inputs Per Customer

```python
class CustomerForLTV:
    customer_id: str
    recency: int     # Days from first order to most recent order
    frequency: int   # Number of REPEAT purchases (total orders − 1)
    T: int           # Days from first order to today (age of customer relationship)
    monetary: float  # Average CM2 per order (NOT revenue)
```

**Use CM2, not revenue, as monetary value.** Predicting profitable LTV, not revenue LTV.

### 18.3 Implementation

```python
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data

def train_ltv_model(workspace_id):
    transactions = get_all_transactions_with_cm2(workspace_id)
    rfm_data = summary_data_from_transaction_data(
        transactions, customer_id_col='customer_id',
        datetime_col='order_date', monetary_value_col='cm2',
        observation_period_end=datetime.today()
    )
    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(rfm_data['frequency'], rfm_data['recency'], rfm_data['T'])

    returning = rfm_data[rfm_data['frequency'] > 0]
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(returning['frequency'], returning['monetary_value'])

    return bgf, ggf, rfm_data

def predict_customer_ltv(bgf, ggf, rfm_data, months_ahead=6, discount_rate=0.01):
    rfm_data['predicted_purchases'] = bgf.conditional_expected_number_of_purchases_up_to_time(
        months_ahead * 30, rfm_data['frequency'], rfm_data['recency'], rfm_data['T']
    )
    rfm_data['predicted_clv'] = ggf.customer_lifetime_value(
        bgf, rfm_data['frequency'], rfm_data['recency'], rfm_data['T'],
        rfm_data['monetary_value'], time=months_ahead, discount_rate=discount_rate
    )
    return rfm_data[['customer_id', 'predicted_purchases', 'predicted_clv']]
```

### 18.4 Training & Serving

- **Training cadence:** monthly, 1st of each month, on all available history
- **Minimum data:** 6 months and 500+ customers with ≥2 purchases; below this, surface "Insufficient data for LTV predictions. Available after 6 months and 500+ repeat customers."
- **Serving:** pre-compute predictions for all customers monthly → write to `agg.customer_states_local.predicted_ltv_*`. Do NOT run model inference on demand.
- **Validation:** after each training, train on data up to month N−1, predict month N, calculate **MAPE (Mean Absolute Percentage Error).** If MAPE > 40%, flag model as unreliable + alert engineering.

### 18.5 LTV Drivers Report

Join `predicted_clv` back to customer attributes to find which attributes correlate with high LTV:

```python
def generate_ltv_drivers_report(workspace_id):
    customers = get_customers_with_predicted_ltv(workspace_id)
    customers = customers.merge(get_first_order_attributes(workspace_id), on='customer_id')
    # attributes: first_product, first_acquisition_channel, first_order_had_discount,
    #             first_discount_code, first_payment_method, first_city_tier, first_aov
    results = {}
    for attr in ['first_product', 'first_acquisition_channel', 'first_city_tier',
                 'first_order_had_discount', 'first_payment_method']:
        seg = customers.groupby(attr)['predicted_clv'].agg(['mean', 'count'])
        seg['vs_average'] = seg['mean'] / customers['predicted_clv'].mean() - 1
        results[attr] = seg.sort_values('mean', ascending=False)
    return results
```

### 18.6 Max CAC Recommendation

```python
def calculate_max_cac(predicted_90d_ltv_cm2, target_ltv_cac_ratio=2.0, payback_months=3):
    max_cac_by_ratio = predicted_90d_ltv_cm2 / target_ltv_cac_ratio
    monthly_cm2 = predicted_90d_ltv_cm2 / payback_months
    max_cac_by_payback = monthly_cm2 * payback_months
    return min(max_cac_by_ratio, max_cac_by_payback)
```

---

## 19. Forecasting (The Plan Module)

### 19.1 Architecture

Forward P&L for the next 1–3 months using **three combined models**:

1. **aMER Model** — predicts new-customer revenue from acquisition spend
2. **Retention Model** — predicts returning revenue from past cohorts
3. **Seasonality Adjustment** — brand-specific seasonal index + festival multipliers

### 19.2 Phase 1 Implementation (Simple but Robust)

**aMER scenarios:** use P25/P50/P75 of last 90 days of daily aMER.
```
Conservative: Planned Spend × P25 historical aMER
Base:         Planned Spend × P50 historical aMER
Optimistic:   Planned Spend × P75 historical aMER
```

**Retention multiplier:** average of `(Month N+1 returning revenue / Month N new-customer revenue)` across all available cohorts.

**Seasonality index:** `avg revenue in week N (across all years) / annual avg weekly revenue`.

### 19.3 Phase 2 Upgrade

#### aMER Response Curve (Isotonic Regression)
```python
from sklearn.isotonic import IsotonicRegression

def build_amer_response_curve(historical_data):
    data_sorted = sorted(historical_data, key=lambda x: x[0])  # (spend, amer) tuples
    spends = [d[0] for d in data_sorted]
    amers = [d[1] for d in data_sorted]
    ir = IsotonicRegression(increasing=False)  # monotone decreasing — aMER decreases with spend
    ir.fit(spends, amers)
    return ir
```

#### Retention Revenue Model
```python
def project_retention_revenue(cohort_data, repeat_rate_by_month, forecast_period):
    total = 0
    for cohort_month, cohort_info in cohort_data.items():
        months_since = months_between(cohort_month, forecast_period)
        if months_since < 1: continue
        typical_revenue_month_N = repeat_rate_by_month.get(months_since, 0)
        total += cohort_info['new_customers'] * typical_revenue_month_N
    return total
```

#### Seasonality (Prophet — Phase 2)
```python
from prophet import Prophet

def train_prophet_model(workspace_id):
    daily_revenue = get_daily_revenue(workspace_id, years=2)
    df = pd.DataFrame({'ds': daily_revenue['date'], 'y': daily_revenue['net_revenue']})
    model = Prophet(seasonality_mode='multiplicative',
                    weekly_seasonality=True, yearly_seasonality=True)
    model.add_country_holidays(country_name='IN')
    # Add custom festival regressors
    diwali_dates = pd.DataFrame({
        'holiday': 'diwali',
        'ds': pd.to_datetime(['2024-11-01', '2025-10-20', '2026-11-08']),
        'lower_window': -14, 'upper_window': 5,
    })
    model.add_holidays(diwali_dates)
    model.fit(df)
    return model
```

### 19.4 The Plan Module UI Contract

Operator inputs:
- Planning Period (month or quarter)
- Planned Meta + Google + other spend per week
- Expected aMER (AI-suggested with trend commentary)
- COGS %, Variable Costs %, Fixed Costs per month
- Events this period (e.g., "Navratri Sale April 2–5 — 2.5× lift")

Projected output (Conservative / Base / Optimistic):
- Acquisition Revenue, Retention Revenue, Total Revenue
- Total Ad Spend, MER, CM3, CM3 %
- New Customers, CAC
- Weekly breakdown with festival/event adjustments visible
- Confidence intervals on charts (P25–P75 shaded area)

### 19.5 Validation

Backtest by hiding last month's data, predicting it, comparing. Target: **within 15% variance** for base case (Phase 3 exit criterion). Initial Phase 1 target: within 25%.

### 19.6 Budget Allocation Optimizer

```python
from scipy.optimize import minimize, curve_fit
import numpy as np

def estimate_spend_response_curve(channel, workspace_id):
    """Fit a power law: revenue = a * spend^b (0 < b < 1)"""
    weekly = get_weekly_channel_data(workspace_id, channel)
    spends = [d['acquisition_spend'] for d in weekly]
    revenues = [d['new_customer_revenue'] for d in weekly]
    def power_law(s, a, b): return a * np.power(s, b)
    popt, _ = curve_fit(power_law, spends, revenues, p0=[2.0, 0.8], bounds=([0,0],[100,1]))
    return popt

def optimize_budget_allocation(workspace_id, total_budget, channels):
    curves = {ch: estimate_spend_response_curve(ch, workspace_id) for ch in channels}
    def total_revenue(allocation):
        return -sum(curves[ch][0] * (allocation[i] ** curves[ch][1])
                    for i, ch in enumerate(channels))
    constraint = {'type': 'eq', 'fun': lambda x: sum(x) - total_budget}
    bounds = [(total_budget * 0.1, total_budget * 0.6) for _ in channels]
    x0 = [total_budget / len(channels)] * len(channels)
    result = minimize(total_revenue, x0, method='SLSQP', constraints=constraint, bounds=bounds)
    return dict(zip(channels, result.x))
```

Returns optimal split. UI shows current vs optimal allocation, projected impact (MER, CAC, new-customer revenue), confidence level based on data volume.

### 19.7 What-If Scenario Builder

Run forecast pipeline with overridden inputs (e.g., increase Meta budget +₹2L, Diwali only 2× lift). Returns full P&L diff vs base case.

---

## 20. Anomaly Detection

### 20.1 Monitored Metrics

```python
MONITORED_METRICS = [
    # Revenue
    {"metric": "daily_revenue",   "window": 14, "threshold_sd": 2.0, "direction": "both"},
    {"metric": "daily_orders",    "window": 14, "threshold_sd": 2.0, "direction": "both"},
    {"metric": "aov",             "window": 14, "threshold_sd": 1.5, "direction": "both"},
    # Marketing
    {"metric": "daily_cac",       "window": 14, "threshold_sd": 1.5, "direction": "up"},
    {"metric": "daily_mer",       "window": 14, "threshold_sd": 1.5, "direction": "down"},
    {"metric": "daily_amer",      "window": 7,  "threshold_sd": 1.5, "direction": "down"},
    {"metric": "meta_cpc",        "window": 7,  "threshold_sd": 2.0, "direction": "up"},
    {"metric": "meta_ctr",        "window": 7,  "threshold_sd": 2.0, "direction": "down"},
    # Customer
    {"metric": "new_customers",   "window": 14, "threshold_sd": 1.5, "direction": "down"},
    {"metric": "rto_rate",        "window": 14, "threshold_sd": 2.0, "direction": "up"},
    # Product
    {"metric": "product_refund_rate", "window": 30, "threshold_sd": 2.0, "direction": "up"},
    # Inventory
    {"metric": "days_of_stock_critical", "threshold_days": 14, "direction": "below"},
]
```

### 20.2 Daily Scan Job

Runs at 00:30 IST in `intelligence-service`:

```python
def run_daily_anomaly_scan(workspace_id):
    alerts = []
    for cfg in MONITORED_METRICS:
        current = get_metric_today(workspace_id, cfg['metric'])
        history = get_metric_history(workspace_id, cfg['metric'], days=cfg['window'])
        is_anom, z, severity = detect_anomaly(cfg['metric'], current, history,
                                              cfg['threshold_sd'], cfg['direction'])
        if is_anom:
            alerts.append(generate_alert(workspace_id, cfg['metric'], current, history, z, severity))
    alerts = prioritize_alerts(alerts)
    publish_to_kafka("intelligence.anomalies.v1", alerts)
    return alerts
```

### 20.3 Root Cause Attribution

When revenue drops anomalously, attempt to identify root cause:

```python
def diagnose_revenue_drop(workspace_id, drop_date):
    causes = []
    # 1. Ad spend reduced?
    spend_today = get_ad_spend(workspace_id, drop_date)
    spend_baseline = get_avg_ad_spend(workspace_id, days=14, before=drop_date)
    if spend_today < spend_baseline * 0.7:
        causes.append({"cause": "Ad spend reduced", "evidence": ..., "probability": 0.8})
    # 2. Conversion rate drop?
    # 3. Stockout?
    stockouts = get_stockouts(workspace_id, drop_date)
    if stockouts:
        pct = get_product_revenue_pct(workspace_id, stockouts, days=14)
        if pct > 0.1:
            causes.append({"cause": f"Stockout: {stockouts}", "evidence": ..., "probability": 0.9})
    # 4. Festival / external event (check festival calendar)
    # 5. AOV drop while orders normal → discount / product mix shift
    return sorted(causes, key=lambda x: x['probability'], reverse=True)
```

### 20.4 Severity-Based Routing

| Severity | Channels |
|----------|----------|
| **CRITICAL** (>3 SD) | Push notification (immediate) + WhatsApp + Email (immediate) |
| **HIGH** (>2 SD) | Push notification + Email (daily digest) |
| **MEDIUM** (>1.5 SD) | Email digest + in-app notification badge |
| **ROUTINE** (always) | Daily digest, optional WhatsApp |

### 20.5 Phase 3 ML Upgrade

When 12+ months of data per workspace, add Isolation Forest and LSTM autoencoder for multivariate anomaly detection. Statistical methods remain primary; ML augments.

---

## 21. Lifecycle Layer (Audience Builder + Multi-Channel Execution)

### 21.1 Architectural Position

The Lifecycle Layer turns Brain from cost centre into revenue centre. **All channels share the single Audience primitive** (Section 31).

Owners: notifications-service (channel execution); intelligence-service (audience scoring, RFM segmentation, channel routing decisions).

### 21.2 Audience Builder (The Primitive)

```python
class Audience:
    workspace_id: str
    rfm_filter: dict          # e.g., {'segments': ['champions', 'loyal']}
    custom_filter: dict       # {sku, channel, geography, aov_band, last_product, ...}
    computed_size: int
    modeled_response_rate: float
    modeled_recovery: Decimal
    channel_mix: dict         # {'call': ['top_decile'], 'whatsapp': ['mid'], 'email': ['rest']}
```

**Build flow:**
1. Operator picks RFM segment or custom filter
2. analytics-service returns audience size + modeled response rate (from historical performance) + projected revenue recovery (from average CM2 per member × response rate)
3. Operator clicks Trigger
4. notifications-service materializes `notifications.audiences` + `notifications.audience_members`
5. Per-customer channel routing applied (high-value → call, mid → WhatsApp, low → email)
6. Channel-specific queues populated; outreach attempts begin
7. Events flow back into `notifications.outreach` + Decision Log

### 21.3 Channel Routing Rules (Default)

- **Top 10% by predicted LTV:** call (if consent + within calling hours)
- **Next 30%:** WhatsApp
- **Next 50%:** email
- **Bottom 10%:** suppress (or low-cost email only)

Editable per brand.

### 21.4 Outbound Workflows (v1a)

| Workflow | Trigger | Channel Logic |
|----------|---------|---------------|
| **Abandoned Cart Recovery** | Cart abandoned >30 min | RFM-segmented: call high-value, WhatsApp mid, email low |
| **COD Confirmation** | Every COD order placed | Call within 15 min; offer prepaid conversion incentive |
| **Post-Delivery Follow-Up** | 3 days and 7 days after delivery | WhatsApp NPS + review request; replenishment cue at 7d |
| **Winback** | Customer crosses At-Risk threshold | RFM-routed: WhatsApp + email |
| **VIP Retention** | Customer in Champions segment, defined cadence | Call or personalised WhatsApp |
| **Replenishment** | Consumable depletion model | WhatsApp first, email fallback |
| **WhatsApp Marketing Broadcasts** | Operator-scheduled | RFM-segmented broadcast with two-way follow-up |

### 21.5 Inbound (v1b)

#### Multi-Channel Inbox
- Channels: WhatsApp, Instagram DM, email, web chat — unified UI
- Each conversation = a `notifications.tickets` row; each message = `notifications.messages`

#### Autonomous Resolution (Top 10 Ticket Types)
1. Order status
2. Return initiation
3. Address change
4. Refund status
5. Product info
6. COD-to-prepaid conversion
7. Cancellation
8. Replacement
9. Missing item
10. Delivery delay

Pattern:
- Ticket arrives → intelligence-service classifier (Haiku) determines ticket_type
- If confidence > 0.85 and ticket_type in auto-resolvable set → autonomous response composed (Sonnet) → sent
- Below threshold or customer requests human → escalate (assigned_to = human user ID)
- Every ticket logs to customer profile + Decision Log

### 21.6 Referral Engine

#### Architecture
Sits inside Lifecycle Layer; consumes RFM segment memory.

#### Tables
```sql
CREATE TABLE notifications.referral_advocates (
  workspace_id   UUID,
  customer_id    UUID,
  referral_code  TEXT UNIQUE,
  referral_link  TEXT,
  enrolled_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  enabled        BOOLEAN NOT NULL DEFAULT TRUE,
  tier           TEXT NOT NULL DEFAULT 'base',  -- 'base','boosted','premium'
  PRIMARY KEY (workspace_id, customer_id)
);

CREATE TABLE notifications.referral_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  advocate_id     UUID NOT NULL,
  referred_customer_id UUID,
  event_type      TEXT NOT NULL,    -- 'click','signup','first_order','payout_processed','blocked'
  amount          NUMERIC(18,2),
  metadata        JSONB,
  device_fingerprint TEXT,
  ip_family       TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Flow
1. Champions/Loyal auto-enrolled (Owner-disableable per brand)
2. Brain sends advocate personalized message (WhatsApp first, email fallback) with code + assets
3. Click on referral link sets first-party cookie + server-side attribution record
4. Referred customer's first order triggers both incentives
5. Multi-touch: first advocate wins by default (configurable)
6. Payout: store credit, discount code, UPI cashback, or physical product

#### Fraud Detection
- Self-referral: same device fingerprint / IP family / phone / email / address → block at attribution time
- Circular ring: A→B→C→A within short window → flag for review
- Velocity caps: max N successful referrals per advocate per month (configurable)
- Cohort quality: if advocate's referred customers show abnormally high RTO/refund rates, incentive held in escrow
- Manual review queue: high-value payouts above brand threshold → Owner approval

#### Tier Mechanics
- First 3 successful referrals: base rate
- 4–10: boosted rate
- 10+: premium rate

---

## 22. AI Calling Architecture

### 22.1 Three Paths (Decision Open; Engineering Owns)

#### Path A — Partner Indian Voice AI Vendor (Bolna, Smallest.ai)
- Pros: 4–6 wk time-to-market, better Hindi/Hinglish/regional accent coverage, vendor handles TRAI DLT, DND, calling-hour compliance
- Cons: vendor stability dependency, less voice-quality control, per-minute margin squeeze (~₹0.30–0.60/min with bundled SIP)
- **Integration:** Brain pushes audience + call script template → vendor places call → outcome webhook returns (transcript, duration, outcome label, optional recording URL)

#### Path B — Partner Global Voice AI Vendor (Vapi, Retell, ElevenLabs Conversational, Bland)
- Pros: best-in-class voice quality + latency, mature SDKs, faster iteration on call flows
- Cons: pricier (~$0.05–0.15/min), Indian termination requires SIP trunk via Plivo/Exotel/Knowlarity, more compliance plumbing
- **Integration:** same as Path A + Indian SIP trunk layer

#### Path C — Build Native
- Stack: Deepgram or Whisper (ASR) + GPT-4o-mini or Claude Haiku (conversation) + ElevenLabs or Cartesia (TTS) + Plivo or Exotel SIP (Indian termination)
- Estimated build: 4–6 months for production-grade with interruption/silence/transfer/hold handling
- Pros: full voice/latency/pricing control; long-term margin protection
- Cons: 4–6 month build, voice-agent engineer hire needed, ongoing maintenance burden
- **Strategically attractive** if calling volume crosses ~10K calls/day across customer base (~50 brands × ~200 calls/day each)

### 22.2 Recommended Heuristic (Not a Decision)

- **Months 1–6:** partner (Path A or B) to validate unit economics, response rates, call flows on real brands
- **Months 6–12:** parallel-build (Path C) if calling crosses ~5K/day and per-minute economics dominate cost
- **Months 12+:** migrate primary traffic to native stack, keep partner as overflow + hedge

### 22.3 Compliance Rules (India — Non-Negotiable, Hard-Coded)

- **Calling hours:** 09:00–21:00 IST. Outside-window calls blocked at queue level (not dialer).
- **DND check:** every number against brand's opt-out list AND TRAI's NCPR. Two-layer block.
- **Consent:** customer must have opted-in for transactional or marketing calls. State in `notifications.consent_events`.
- **Disclosure:** every AI call opens with disclosure that caller is an automated assistant.
- **Recording consent:** asked at call start; declined → call proceeds, no audio retained.
- **DLT registration:** every template message that follows a call (WhatsApp, SMS) registered on the brand's DLT under their entity ID. Brain never commingles brands' DLT registrations.
- **Frequency cap:** no customer called >1× per 48 hours by any Brain-driven flow. Override only for VIP segments with Owner approval.

### 22.4 Storage

- Every call: `notifications.calls` row (vendor_call_id, duration, outcome_label, transcript_id, recording_url if consented)
- Outreach attempt: `notifications.outreach` (channel='call', status, attempted_at, completed_at, outcome)
- Recordings: S3 `brain-call-recordings-{env}` with per-brand KMS key, 1-year retention

### 22.5 Cost Model

- Telephony pass-through (vendor per-minute) bundled in GMV % fee at Standard/Growth tiers, up to per-brand monthly cap
- Above cap: communicate with brand; discuss tier upgrade or volume reduction
- Enterprise tier handles telephony as separate line item

---

## 23. Native Email Engine

### 23.1 Build Path Decision (Phase 2)

**Recommended: Path A — Partner backbone, native experience.**
- Deliverability backbone: Postmark / Mailgun / SendGrid / AWS SES with India + EU/UAE POP coverage. Owned IPs warmed per brand.
- Brain builds: segmentation engine (over Memory Layer), flow builder UI, template editor, A/B testing, predictive send-time, deliverability dashboard, suppression list management
- Differentiation: every email decision informed by same Memory Layer that powers AICMO + Lifecycle. Brain knows which customer responds to which subject line because the same customer's call outcome + WhatsApp open rate + email engagement live in one record.
- Estimated build: 3–4 months to v1 launch with 2–3 engineer email-focused squad

**Rejected:**
- Path B (white-label Klaviyo) — strategic dependency on competitor roadmap
- Path C (full SMTP infrastructure) — 12–18 months, 8–12 engineers, deliverability war from day one

### 23.2 India + Middle East Differentiation

- **Languages:** Hindi, Tamil, Telugu, Marathi, Bengali, Kannada, Malayalam, Gujarati, Punjabi, Arabic. Right-to-left for Arabic. Templates that don't break on Devanagari ligatures.
- **Currency rendering:** INR/AED with correct separator conventions (lakh/crore for India, regional Arabic numerals option for GCC)
- **Festival calendar** integrated into send-time optimization — model knows Diwali email on Dhanteras converts differently from same email on day of Diwali
- **Mailbox provider tuning:** not just Gmail/Outlook/Yahoo, but also Rediffmail + Zoho Mail + regional GCC ISPs. Deliverability monitoring per provider.
- **WhatsApp-aware:** suppress email for customers who engaged on WhatsApp in last X days for the same campaign
- **GST/VAT-correct transactional emails** (order confirmation, shipping confirmation)

### 23.3 v1 Feature Parity Checklist

- Segmentation engine over Memory Layer (RFM, cohort, behaviour, channel preference, custom)
- Flow builder: visual editor for triggered sequences (welcome, browse abandon, cart abandon, post-purchase, winback, replenishment, VIP, sunset)
- Template editor: drag-and-drop with template library; brand kit (colours, fonts, logos) pre-loaded
- Predictive send-time per customer
- Subject line A/B testing with auto-graduation
- Suppression list per-channel granularity
- Deliverability dashboard: inbox placement, complaint rate, bounce rate, unsubscribe rate per ISP
- Attribution: email-influenced revenue with 7-day click + 1-day open attribution windows
- API + webhook surface for brand developers

### 23.4 Tables

```sql
CREATE TABLE notifications.email_templates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL,
  name          TEXT NOT NULL,
  subject       TEXT NOT NULL,
  body_html     TEXT NOT NULL,
  body_text     TEXT NOT NULL,
  language      TEXT NOT NULL DEFAULT 'en',
  version       INT NOT NULL DEFAULT 1,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications.email_flows (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  UUID NOT NULL,
  name          TEXT NOT NULL,
  trigger_type  TEXT NOT NULL,    -- 'welcome','cart_abandon','post_purchase','winback', ...
  steps         JSONB NOT NULL,   -- ordered array of {wait_hours, template_id, condition}
  exit_criteria JSONB,
  enabled       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications.email_sends (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  template_id     UUID NOT NULL REFERENCES notifications.email_templates(id),
  audience_id     UUID REFERENCES notifications.audiences(id),
  flow_id         UUID REFERENCES notifications.email_flows(id),
  customer_id     UUID NOT NULL,
  outreach_id     UUID REFERENCES notifications.outreach(id),
  send_time       TIMESTAMPTZ NOT NULL,
  delivery_status TEXT,
  opened_at       TIMESTAMPTZ,
  clicked_at      TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  bounced_at      TIMESTAMPTZ,
  spam_at         TIMESTAMPTZ,
  attributed_order_id TEXT,
  attributed_revenue NUMERIC(18,2),
  metadata        JSONB
);
CREATE INDEX ON notifications.email_sends (workspace_id, send_time DESC);
CREATE INDEX ON notifications.email_sends (workspace_id, customer_id);
```

---

## 24. Agentic Creative Intelligence

### 24.1 Architecture: Confidence-Routed Decision Tree (Not a Generator)

Three loops:

**Loop 1 — Data Review and Pattern Extraction**
- Daily ingest of all live creative performance: Meta ad-level CPM, CTR, CPA, ROAS, hook performance, video retention curves
- EWMA-based creative decay detection per ad
- Pattern extraction: hooks, formats, lengths, palettes, claim styles, offer mechanics that correlate with brand's strongest performance over trailing 90 days
- Stored as brand-specific **Creative Fingerprint** in Memory Layer
- Cross-brand learning: anonymized aggregated patterns from network feed industry baseline

**Loop 2 — Creative Generation and Variant Production**
- When high-performing pattern identified, system proposes 3–5 variants applying the pattern to brand's existing assets
- Pipeline: structured brief (audience + pattern + product + offer) → Claude (copy variants) → Stable Diffusion XL with brand-trained LoRA / DALL-E 3 with brand kit / Midjourney (image variants) → Runway / Sora / Pika (short-form video as models mature)
- Every variant tagged with source pattern + confidence score

**Loop 3 — Confidence-Routed Decision Tree**

| Confidence Band | Decision | Output |
|----------------|----------|--------|
| **High (>0.85)** | Auto-generate and ship | Variant generated, auto-published to ad platform as test against current control. Founder notified, no approval required. |
| **Medium (0.55–0.85)** | Generate, route for approval | Variant generated, surfaced in Morning Brief or Creative Queue. Founder/marketing lead reviews/approves/edits. |
| **Low (0.30–0.55)** | Brief the human designer | Brain generates structured brief; delivered to designer's queue (Slack, Asana, email). |
| **Very low (<0.30)** | Escalate to founder | Pattern unclear, conflicting, or brand too new. Surfaced as strategic question: "We're seeing X — what's your read?" |

### 24.2 Creative Fatigue Detection (EWMA)

```python
def detect_creative_fatigue(creative_id, workspace_id, lookback_days=21):
    daily = get_creative_daily_metrics(creative_id, workspace_id, lookback_days)
    week1 = daily[:7];  week2 = daily[7:14];  week3 = daily[14:21]
    ctr_trend = [np.mean([d['ctr'] for d in w]) for w in [week1, week2, week3]]
    freq_trend = [np.mean([d['frequency'] for d in w]) for w in [week1, week2, week3]]
    is_fatiguing = ctr_trend[2] < ctr_trend[0] * 0.75 and freq_trend[2] > freq_trend[0] * 1.3
    days_live = (datetime.today() - get_creative_launch_date(creative_id)).days
    return {"is_fatiguing": is_fatiguing, "days_live": days_live, "ctr_trend": ctr_trend,
            "recommendation": "Replace creative" if is_fatiguing else "Monitor"}
```

### 24.3 Designer Brief Format (Typed Schema)

```python
class CreativeBrief:
    audience: AudienceSegment       # who this creative will target
    why_brief_exists: str           # data signal that triggered it
    pattern_to_apply: str           # high-performing pattern Brain detected
    product_to_feature: Product     # SKU, image refs, current PDP copy
    constraints: Constraints        # brand palette, font, logo, claim boundaries
    reference_images: list[str]     # 3–5 examples from brand's past winners + anonymized cross-brand exemplars
    deadline_priority: Priority     # urgency derived from ad fatigue / campaign date
    expected_output: OutputSpec     # format (static/video/carousel), aspect ratio, variants
```

### 24.4 Designer Workflow Inside Brain

1. Designer accepts brief from queue
2. Designer uploads resulting creative back to Brain (or auto-sync from Figma/Adobe Express/Canva)
3. Brain auto-tags creative with brief metadata (audience, pattern, product, brief-id)
4. Creative goes live on ad platform with appropriate test setup
5. Performance feeds back into Creative Fingerprint, refining future confidence scores
6. Designer's hit rate becomes a measurable signal

### 24.5 Tables

```sql
CREATE TABLE memory.creative_fingerprint (
  workspace_id   UUID NOT NULL,
  pattern_id     UUID NOT NULL,
  pattern_type   TEXT NOT NULL,    -- 'hook','format','length','palette','claim','offer_mechanic'
  pattern_value  JSONB NOT NULL,
  audience_segment TEXT,
  performance_score NUMERIC(5,4),
  sample_size    INT NOT NULL,
  decay_curve    JSONB,
  last_updated   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, pattern_id)
);

CREATE TABLE notifications.creative_assets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  source          TEXT NOT NULL,    -- 'ai_generated','designer_uploaded','founder_uploaded'
  brief_id        UUID,
  pattern_id      UUID,
  asset_type      TEXT NOT NULL,    -- 'static','video','carousel'
  asset_url       TEXT NOT NULL,
  metadata        JSONB,
  live_on_platforms JSONB,
  performance_ledger JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications.creative_briefs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id    UUID NOT NULL,
  brief_payload   JSONB NOT NULL,
  status          TEXT NOT NULL,    -- 'drafted','accepted','in_progress','delivered','live','retired'
  assigned_designer TEXT,
  deadline_at     TIMESTAMPTZ,
  delivered_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 25. Agent Layer (AICMO / AICOO / AICFO)

### 25.1 Service Ownership

All agents run inside **intelligence-service**. Each agent is a Python class implementing:

```python
class Agent(ABC):
    name: str
    domain: str   # 'marketing','operations','finance'

    @abstractmethod
    async def build_context(self, workspace_id: str) -> AgentContext: ...

    @abstractmethod
    async def evaluate(self, ctx: AgentContext) -> AgentRecommendation: ...
        # Returns priority score + recommended action + confidence + explanation

    @abstractmethod
    async def execute(self, action: Action, workspace_id: str) -> ExecutionResult: ...
        # Only called for auto-execute actions; otherwise human-in-the-loop
```

Every agent communicates via internal MCP (Section 27). New agents plug in by defining MCP surface and registering.

### 25.2 Initial Agent Roster

#### AICMO (Marketing Intelligence)

| Agent | Responsibility |
|-------|----------------|
| **AICMO-Meta** | Meta Ads creative performance, budget pacing, ad-set optimization, audience expansion, CM2-aligned scaling |
| **AICMO-Google** | Google Ads search + shopping optimization, keyword bid management, negative keyword discovery, audience expansion, shopping feed health |
| **AICMO-TikTok** | TikTok Ads creative performance, Spark Ads vs in-feed routing, audience expansion (India + GCC active) |
| **AICMO-Snap** | Snapchat Ads creative + audience expansion (GCC priority) |
| **AICMO-Cross-Channel** | Media-mix allocation across Meta/Google/TikTok/Snap based on CM2 contribution per channel |
| **AICMO-Creative** | Creative performance benchmarking + brief generator (platform-agnostic; consumed by all AICMO agents above) |
| **AICMO-Pricing** | SKU-level price elasticity from cross-brand patterns |
| **AICMO-Festival** | Demand calibration around festivals (Diwali, Ramadan, Eid, regional events) |

#### AICOO (Operations Intelligence)

| Agent | Responsibility |
|-------|----------------|
| **AICOO-Logistics** | Courier scoring, RTO mitigation, regional courier reallocation |
| **AICOO-Returns** | Return reason clustering, refund-vs-replace routing |
| **AICOO-Inventory** | Demand forecasting per SKU per channel, transfer recommendations, reorder triggers |
| **AICOO-Marketplace** | Marketplace-specific intelligence (BSR tracking on Amazon, listing health, A+ content optimization, ratings recovery) |

#### AICFO (Financial Intelligence)

| Agent | Responsibility |
|-------|----------------|
| **AICFO-Conversion** | COD vs Prepaid conversion patterns, payment-method reallocation |
| **AICFO-Cashflow** | 30-day cashflow projection using GMV trajectory + CM2-correct P&L (complements GoKwik Cashflow data) |
| **AICFO-Pricing-Margin** | Margin protection: alerts when discount stacking, COD overheads, or RTO surges threaten CM2 |

### 25.3 Daily Agent Run

| Time (IST) | Step |
|------------|------|
| 06:55 | Data pull complete (ingestion-service has synced yesterday) |
| 07:00 | Vector generation — analytics-service publishes Business Moment Vector per workspace |
| 07:05 | Memory query — intelligence-service uses pgvector cosine search to find closest historical conditions |
| 07:10 | All 7 agents run in parallel. Each writes recommendation to `ai.decision_log` (status=`recommended`). Each publishes `intelligence.action.recommended.v1` |
| 07:15 | notifications-service consumes recommendations, selects top 3 by priority, assembles Morning Brief, sends via APNs/FCM |

Throughout day: approve/reject flows update `ai.decision_log.user_response`. 7-day and 30-day cron jobs auto-attribute outcomes.

### 25.4 Internal MCP Between Agents

- Each agent exposes a small MCP server inside the intelligence-service pod
- AICMO-Cross-Channel can call `propose_action` on AICMO-Meta + AICMO-Google to evaluate hypothetical reallocations before recommending
- All inter-agent calls log to `ai.decision_log` so the system has one trace of all decisions

---

## 26. 30-Day Agentic Commerce (Auto-Execute)

### 26.1 What It Builds

A **graduation, not a new system.** Existing agents already produce recommendations in human-in-the-loop mode. The 30-day work moves a defined subset from recommend-then-approve to **auto-execute-with-kill-switch**.

### 26.2 Initial Auto-Execute Action Set (8 Actions)

| Action | Agent | Confidence Threshold | Reversibility |
|--------|-------|---------------------|---------------|
| Pause underperforming ad | AICMO | >0.90 | Fully reversible (unpause) |
| Reduce daily budget on fatiguing campaign by 20% | AICMO | >0.85 | Fully reversible |
| Issue full refund on verified return | AICOO | >0.95 | Irreversible (cash leaves bank) |
| Replace defective item under warranty | AICOO | >0.90 | Partially reversible (inventory) |
| Reorder inventory via automated PO to vendor | AICOO | >0.90 | Partially reversible (cancel PO) |
| Transfer inventory between warehouses | AICOO | >0.85 | Reversible (reverse transfer) |
| Apply discount code to abandoned-cart customer | AICMO | >0.80 | Reversible (revoke code) |
| Switch courier for region with elevated RTO | AICOO | >0.85 | Partially reversible |

### 26.3 Guardrail Architecture

#### Confidence Gating
- Per-action minimum threshold (above)
- Below threshold → fall back to human-in-the-loop
- Per-brand tunable upward, never below default

#### Per-Action Spend Caps
- Daily action budget per agent (e.g., AICMO ≤10 ads auto-paused/day; AICOO ≤₹50,000 aggregate refunds/day)
- Beyond cap, actions queue for Owner approval
- Per-brand override at onboarding

#### The Kill Switch
- Single button in Brain UI: **"Pause all auto-execute."** Reverts all agents to recommend-only within 60s
- **Auto-trigger:** if any agent's outcome accuracy drops below threshold over trailing 7 days, that agent auto-reverts to recommend-only. Owner notified.
- Per-action kill switch: Owner can disable specific action types while leaving others active

#### Audit & Reversal
- Every auto-executed action logs to immutable `ai.auto_execute_log` with: agent, action, parameters, confidence score, time, 7-day/30-day outcome, reversal status
- Owner can reverse any reversible action in one click. Reversal logged.
- Daily 18:00 IST digest: "Today Brain auto-executed N actions. M succeeded. K were reversed."

#### Compliance Boundaries (Hard-Coded)
- No action that issues cash from brand's bank account beyond daily refund cap
- No new financial liability (PO above brand-set threshold, new vendor contract, new ad platform commitment)
- No action touching customer PII the brand hasn't pre-authorised
- No action against EU/California customer conflicting with stored consent state

### 26.4 30-Day Build Plan

#### Week 1: Foundation
- `ai.auto_execute_log` table + immutable storage (CDC-replicated to S3 for tamper evidence)
- Confidence scoring framework for each of 8 action types
- Spend cap + kill switch infrastructure
- Owner consent flow during onboarding (explicit opt-in per action type)

#### Week 2: First Three Actions Live
- Pause ad, reduce budget, apply discount to abandoned cart (lowest-risk, fully reversible)
- Live on 2 founding-cohort brands with full Owner consent + daily review

#### Week 3: Next Three Actions
- Transfer inventory, switch courier, replace defective item
- Expanded to 4 brands

#### Week 4: Final Two + Hardening
- Issue refund (highest-risk, irreversible) + automated PO reorder
- Cross-brand outcome accuracy review
- Stress-test kill switch
- Ship documentation, Owner training, escalation runbook

### 26.5 Success Metrics

- **Auto-execute actions/day:** >50 per active brand by end of week 4
- **Outcome accuracy:** >80% (7-day or 30-day outcome matches predicted direction)
- **Reversal rate:** <8%; alarm at 15% (thresholds mis-calibrated)
- **Time saved per brand per week:** >5 hours of founder time freed
- **Recovered revenue from auto-execute:** net incremental CM2 vs counterfactual baseline

### 26.6 Out of Scope (30-Day)

- Customer-facing agentic commerce (Razorpay Agent Studio, external MCP for ChatGPT/Perplexity)
- Multi-agent action chains ("detect stockout → reorder → adjust ad spend → notify CS") — Phase 2 of agentic
- Auto-execute on competitor/external systems
- Voice/text user commands triggering auto-execute ("hey Brain, pause Meta") — auto-execute is system-initiated only


---

## 27. MCP Server Surface

### 27.1 Strategic Position

Every platform (Meta, Shopify, Razorpay, Stripe, Salesforce, Google) is shipping its own MCP server. **None of them have the decision log.** Brain's MCP is the **decision-log-and-context layer above every other MCP** — the layer that makes other MCPs intelligent for any AI agent that connects to multiple.

### 27.2 Implementation

- Custom MCP server per Anthropic MCP spec
- Hosted as endpoints in api-gateway (external surface) and inside intelligence-service (internal agent-to-agent)
- Authentication: per-brand MCP tokens (scoped to user's role + workspace_id)
- Rate-limited via Redis sliding window (same caps as in-app API; covers all consumption regardless of surface)

### 27.3 Read Surface (External + Internal)

| Endpoint | Returns |
|----------|---------|
| `brand_fingerprint` | Multi-timescale embedding of brand performance — seasonality, channel efficiency, cohort behaviour, CM2 trajectory |
| `decision_log` | Every recommendation, response, 7d/30d outcome. Filterable by agent, action_type, outcome, time range. **Unique to Brain — no platform MCP has it.** |
| `condition_outcome_pairs` | Historical conditions matched against outcomes |
| `rfm_segments` | Live RFM segmentation of brand's customer base |
| `recovered_revenue_ledger` | Attribution of incremental revenue to Brain-driven actions |
| `creative_fingerprint` | Brand's high-performing creative patterns + decay curves |
| `cross_brand_benchmarks` | Aggregated, anonymized statistics from Brain network |

### 27.4 Action Surface

| Endpoint | Action |
|----------|--------|
| `trigger_audience` | Build audience by RFM filter or custom criteria; push to channels |
| `propose_action` | Ask Brain's agents to evaluate hypothetical action; returns confidence score + projected outcome before executing |
| `query_memory` | Free-form NL query against brand data; returns prose + underlying numbers |
| `log_external_decision` | Write into Decision Log from external context (decision brand's team made outside Brain) |

### 27.5 Build Sequence

| Phase | Months | Deliverable |
|-------|--------|-------------|
| Phase 1 (early) | 1–3 | **Internal MCP first.** Audience Builder, agents, Lifecycle execution speak MCP to each other. Establishes schema + tooling without external compliance burden. |
| Phase 1 (later) | 3–6 | **External read-only MCP.** `brand_fingerprint`, `decision_log`, `rfm_segments`, `cross_brand_benchmarks` queryable from brands' AI tools. |
| Phase 2 | 6–9 | **External action MCP.** `trigger_audience` + `propose_action` callable with explicit per-action consent at token issue. |
| Phase 2 (later) | 9–12 | **Bidirectional with platform MCPs** (Shopify, Meta, Razorpay). Brain orchestrates calls to other MCPs on behalf of brands' AI agents, combining cross-platform context with Brain's decision log. |

### 27.6 Security Model

- MCP tokens authenticate per brand. User authenticates → gets MCP token scoped to role + workspace
- Same RBAC as web app (Owner / Operator / Analyst / Agency / Read-only)
- External AI surfaces (Claude, ChatGPT, etc.) connect using user's MCP token; treated as authenticated clients with user's permissions
- Every MCP query + action logged with originating client (which AI surface, which user, what query)
- Rate limiting + cost caps apply to MCP traffic same as in-app traffic — monthly LLM cap covers all consumption regardless of surface
- **Write actions** (`trigger_audience`, `log_external_decision`) require explicit per-action consent at MCP token issue time. Default scope: read-only.

---

## 28. API Contracts

### 28.1 External API (Frontend ↔ api-gateway): tRPC

- Type-safe end-to-end (TS frontend + TS api-gateway)
- One server, one client codebase
- Co-located router definitions in `apps/api-gateway/src/routers/`
- Streaming responses via SSE for AI Chat + live metric refresh

Example router:
```typescript
// apps/api-gateway/src/routers/analytics.ts
export const analyticsRouter = router({
  getDailyMetrics: protectedProcedure
    .input(z.object({
      workspaceSlug: z.string(),
      from: z.string(),
      to: z.string(),
      metrics: z.array(z.string()),
      customerType: z.enum(['all', 'new', 'returning']).optional(),
    }))
    .query(async ({ input, ctx }) => {
      const workspace = await ctx.coreClient.resolveWorkspace(input.workspaceSlug);
      await ctx.requireRole(workspace.id, 'analyst');
      return await ctx.analyticsClient.getDailyMetrics({
        workspaceId: workspace.id,
        from: input.from,
        to: input.to,
        metricNames: input.metrics,
        customerType: input.customerType,
      });
    }),
});
```

### 28.2 Internal API (Service-to-Service): gRPC

Source of truth: `/protos/`. Code generated via `buf generate`.

Example service definitions:

```proto
// protos/core/workspace.proto
service WorkspaceService {
  rpc ResolveWorkspace(ResolveWorkspaceRequest) returns (Workspace);
  rpc GetMember(GetMemberRequest) returns (WorkspaceMember);
  rpc ListIntegrations(ListIntegrationsRequest) returns (ListIntegrationsResponse);
  rpc GetCogsSettings(GetCogsSettingsRequest) returns (CogsSettings);
  rpc ListGoals(ListGoalsRequest) returns (ListGoalsResponse);
}
```

```proto
// protos/intelligence/forecast.proto
service ForecastService {
  rpc GeneratePlanForecast(PlanForecastRequest) returns (PlanForecastResponse);
  rpc OptimizeBudget(OptimizeBudgetRequest) returns (OptimizeBudgetResponse);
  rpc EvaluateAction(EvaluateActionRequest) returns (EvaluateActionResponse);
}
```

```proto
// protos/notifications/lifecycle.proto
service LifecycleService {
  rpc BuildAudience(BuildAudienceRequest) returns (Audience);
  rpc TriggerAudience(TriggerAudienceRequest) returns (TriggerAudienceResponse);
  rpc QueueOutreach(QueueOutreachRequest) returns (QueueOutreachResponse);
}
```

### 28.3 Streaming (SSE / WebSocket)

- AI Chat responses: `text/event-stream` via SSE; tokens stream as Claude generates
- Live metric refresh: WebSocket on dashboard for selected metrics (opt-in per page)
- AI Insight generation: SSE — insight cards render progressively as JSON tokens accumulate

### 28.4 Public REST API (Phase 4)

- Pre-auth: API key issued by Owner from Settings → API Keys
- Read-only endpoints initially: `GET /v1/workspace/{slug}/metrics/daily?from=...&to=...&metrics=...`
- Tiered rate limits by plan
- OAuth (for third-party app builders): Phase 5+
- GraphQL: Phase 5+ if customer demand

### 28.5 Webhook Receivers

- `/api/webhooks/shopify` (HMAC validated)
- `/api/webhooks/shiprocket` (token-validated)
- `/api/webhooks/razorpay` (signature validated)
- `/api/webhooks/klaviyo` (HMAC validated)
- All webhook receivers in api-gateway → forward to ingestion-service via Kafka

### 28.6 Error Handling Standard

- All APIs return `{ error: string, code: string, details?: object }` with appropriate HTTP/gRPC status
- Error codes namespaced: `auth.unauthorized`, `workspace.not_found`, `feature.disabled`, `rate.exceeded`, `data.insufficient`, `integration.token_expired`, etc.
- AI engine returns structured error states (`insufficient_data`, `no_connection`) instead of throwing
- OAuth errors return redirect with `?error=` query param

---

## 29. Frontend Architecture

### 29.1 Stack

- **Next.js 14+** App Router with Server Components for initial paint + Client Components for interactivity
- **TypeScript** strict mode
- **Tailwind CSS v4** with container queries (`@container/main`)
- **shadcn/ui** primitives (Button, Dialog, Sheet, Select, Tabs, Card, Badge, Input, Table, Popover, Tooltip, Command, DatePicker)
- **@base-ui/react** for lower-level accessible primitives
- **Tabler Icons** primary; **Lucide React** legacy
- **Recharts** for 90% of charts; **Visx** for waterfall, heatmap, India map choropleth

### 29.2 Routing

```
app/
├── (auth)/
│   ├── auth/login/
│   ├── auth/signup/
│   ├── auth/forgot-password/
│   └── auth/reset-password/
├── (protected)/
│   ├── onboarding/
│   └── w/[slug]/
│       ├── dashboard/
│       ├── analytics/
│       ├── pnl/
│       ├── waterfall/
│       ├── acquisition/
│       ├── cohorts/
│       ├── lifetime-value/
│       ├── timings/
│       ├── distributions/
│       ├── customer-lifecycle/
│       ├── first-product-cascade/
│       ├── meta-ads/
│       ├── google-ads/
│       ├── products/
│       ├── inventory/
│       ├── logistics/
│       ├── rto-analytics/
│       ├── pincode-intelligence/
│       ├── cod-prepaid/
│       ├── calendar/                  # Calendar Report
│       ├── email-sms/
│       ├── store/                     # Store Explorer
│       ├── plan/                      # The Plan Module
│       ├── creative/                  # Creative Intelligence + Queue
│       ├── lifecycle/                 # Audience Builder + Outreach
│       ├── inbox/                     # Multi-channel inbox (Phase 2)
│       ├── auto-execute/              # Agentic Commerce log
│       └── settings/
│           ├── goals/
│           ├── costs/
│           ├── integrations/
│           ├── team/
│           ├── thresholds/            # Customer Lifecycle (P40/P80)
│           ├── api-keys/              # Phase 4
│           └── general/
└── invite/[token]/                    # Public invite acceptance
```

### 29.3 Component Hierarchy

```
app/layout.tsx                        (Root — QueryProvider, TooltipProvider, Toaster)
└── (protected)/layout.tsx            (Auth gate)
    └── w/[slug]/layout.tsx           (WorkspaceProvider, SidebarProvider)
        ├── AppSidebar                (Left nav)
        │   ├── WorkspaceSwitcher
        │   ├── NavMain
        │   ├── NavSecondary          (Settings, integrations)
        │   └── NavDocuments          (Utility pages)
        ├── SiteHeader                (Top bar — breadcrumbs, notifications, user menu)
        └── {page}/page.tsx           (RSC initial paint)
            ├── ChartAreaInteractive  (Recharts)
            ├── SectionCards          (KPI grid)
            ├── DataTable             (TanStack Table wrapper)
            ├── InsightPanel          (AI insight cards)
            ├── ChatSidebar           (AI Chat on every page)
            └── feature-components/...
```

### 29.4 State Management

| Layer | Tool | Scope |
|-------|------|-------|
| Server state | TanStack Query v5 (via tRPC) | All API data; 5-min stale time on analytics |
| Global UI state | Zustand 5 | Sidebar open, modals, global loading |
| Workspace context | React Context (`WorkspaceProvider`) | Current workspace, slug, role, features, plan, all workspaces |
| Form state | react-hook-form 7 + Zod v4 | All forms validated at schema boundary |
| URL state | `useSearchParams` + `useRouter` (via nuqs helper) | Date range, active tab, filters |
| Request-scoped cache | `React.cache()` | Deduplicates Supabase/Prisma calls within one render cycle |

**TanStack Query patterns:**
- `queryKey: ['workspace', slug, 'feature', { from, to, ...filters }]`
- Stale time: 5 min for analytics
- Background refetch on window focus disabled for analytics
- Mutations: `useMutation` → `queryClient.invalidateQueries()`

### 29.5 Data Fetching Architecture

**Server Components (RSC) — initial data only:**
- Workspace metadata, user role, feature flags
- Called via direct Prisma/Supabase calls (no fetch)
- Passed as props to Client Components

**Client Components — interactive data:**
- All analytics fetched via tRPC `useQuery` → api-gateway → gRPC to analytics-service
- Date range changes trigger new query key → automatic refetch

**AI Insights — streaming:**
- tRPC subscription or SSE: `text/event-stream`
- ReadableStream consumed chunk-by-chunk
- Insight cards render progressively

### 29.6 Forms

All forms: `react-hook-form` + `zod v4` at the schema boundary. Error messages rendered via `<FormMessage />`.

Forms present at v1:
- Login / Signup / Reset Password
- Create Workspace
- Invite Member
- COGS Settings
- Variable Costs (drag-and-drop reorderable via `@dnd-kit`)
- Misc Fixed Expenses
- Founder Salary (OWNER-only)
- Goal Creation
- Festival Event Creation
- Marketing Action Log
- Product Lead Time
- Campaign Classification
- Integration connect forms (Shiprocket credentials, Klaviyo API key, WooCommerce REST key, etc.)
- Workspace Settings
- Audience Builder
- Auto-execute consent flow (per action type)

### 29.7 Hosting

- Next.js on AWS App Runner or EKS (engineering choice during Phase 0)
- Static assets via CloudFront (immutable; 1-year cache)
- Per-region edge: Phase 4 multi-region deploy

### 29.8 Mobile (Phone Morning Brief)

- Responsive web is enough for v1 (no native iOS/Android app until Phase 5+)
- Web app installable as PWA
- Push notifications via Web Push API + APNs/FCM for native-like delivery on iOS/Android
- Morning Brief is a dedicated mobile route: `/m/brief?date=...` — optimized for one-thumb scroll + Approve/Reject taps

### 29.9 Live Sale Event Mode

When a Marketing Action is tagged as a Sale Event in `core.marketing_actions`, the dashboard automatically switches to hourly granularity for that date range with WebSocket-driven live refresh.

---

## 30. Cost-Routed Compute Paradigm

### 30.1 The Four Paradigms (Ranked by Cost)

| Paradigm | Cost / call | Reliability | Used for | Share |
|----------|-------------|-------------|----------|-------|
| **SQL / CRON** | ≈ ₹0 (server only) | Deterministic | Metric calculation, threshold alerts, scheduled aggregations, deterministic routing, day-of-week baselines | ~50% |
| **ML / Pattern Recognition** | ≈ ₹0.01–0.10 | High, bounded | Forecasting (Prophet), LTV (BG/NBD+Gamma-Gamma), cohort survival (Kaplan-Meier), creative decay (EWMA), RTO clustering (DBSCAN+XGBoost), condition matching (pgvector cosine) | ~35% |
| **Small LLM (Haiku, GPT-4o-mini)** | ≈ ₹0.50–₹2.00 | High for narrow tasks | Brief drafting, ticket triage, simple classification, NL-to-SQL on bounded schemas, ticket type classification | ~10% |
| **Frontier LLM (Sonnet, GPT-4o)** | ≈ ₹5–₹40 | Variable, needs eval | Strategic synthesis, multi-step reasoning, ambiguous NL, creative generation requiring brand voice | ~5% |

### 30.2 The Routing Decision (Required Gate)

Every feature ticket must answer four questions **in order**, escalating only when the previous paradigm cannot solve the problem:

1. **Can SQL solve this?** If deterministic, threshold-based, aggregation → SQL via CRON / stored procedure. Cost ≈ 0.
2. **Can ML solve this?** If pattern recognition, prediction, similarity matching, anomaly detection over historical data → ML using `pylibs/brain_ml/` (Prophet, BG/NBD, XGBoost, pgvector). Cost = one-time training + minimal inference.
3. **Can a small LLM solve this?** If NL understanding on a bounded domain → Haiku / GPT-4o-mini. Cost 10–50× higher than ML but acceptable when language understanding is genuinely required.
4. **Does this require a frontier LLM?** Only if multi-step synthesis, brand-voice generation, or ambiguous reasoning that smaller models fail at → Sonnet. Cost 5–20× small LLM. Reserved for highest-value, lowest-frequency operations.

**The questions and answers are documented in the ticket. No feature ships without this audit trail.**

### 30.3 What "Agentic Commerce" Means

Critical clarification: a substantial portion of what the industry calls "agentic AI" is **not AI at all.** It is ML and pattern recognition with an LLM wrapper at the NL interface boundary only.

| What it looks like | What it actually is |
|---------------------|---------------------|
| Detecting an ad is fatiguing | EWMA on CTR — **not LLM** |
| Predicting which customer will repeat | BG/NBD — **not LLM** |
| Scoring RTO risk on a pincode | XGBoost on historical data — **not LLM** |
| Finding closest historical condition to today | pgvector cosine similarity — **not LLM** |
| Recommending budget reallocation | Linear optimization over forecast vectors — **not LLM** |
| Writing the Morning Brief that explains all of the above in plain English | Yes — this is genuinely an LLM task |

**Result:** Brain executes most of its intelligence at SQL-and-ML cost economics; uses LLMs only at the human-language interface boundary. This is what makes GMV-linked pricing defensible.

### 30.4 Token Economics Enforcement (Three Hard-Coded Layers)

**Layer 1 — Default Routing**
- Every API endpoint and agent action declares its paradigm in code (`@paradigm("sql")` / `@paradigm("ml")` / `@paradigm("small_llm")` / `@paradigm("frontier_llm")`)
- Defaults to cheapest paradigm that can solve the problem
- Upgrading the paradigm requires documented justification in code comments + PR description
- Build pipeline check: if a feature declares LLM but reviewer judges SQL/ML would suffice → PR blocked

**Layer 2 — Per-Feature Token Budgets**
- Every LLM-using feature has token budget per call
- Soft warning at 80% of budget, hard fail at 100%
- Failed calls fall back to degraded SQL/ML path where possible, or graceful error otherwise
- Token budget overruns log to cost-discipline dashboard. Repeated overruns trigger prompt audit.

**Layer 3 — Per-Brand Monthly Caps**
- Every brand has monthly LLM cap denominated in INR/USD, set per tier
- Soft throttle at 70% (lower-priority LLM features pause)
- Hard throttle at 100% (only critical-path LLM features continue: Morning Brief, NL query, ticket resolution)
- Owner notified at 70% with breakdown of where tokens went + recommended actions
- Above cap: Brain continues to function on SQL + ML paths; only LLM-dependent features degrade. **The system never breaks; it gets quieter.**

### 30.5 LLM Client Wrapper (`pylibs/brain_llm/`)

```python
class CostRoutedClient:
    def __init__(self, workspace_id, feature_name, paradigm):
        self.workspace_id = workspace_id
        self.feature_name = feature_name
        self.paradigm = paradigm  # 'small_llm' or 'frontier_llm'

    async def call(self, prompt, max_tokens=1000, **kwargs):
        # Check per-brand cap
        if self._brand_cap_exceeded():
            return self._degraded_fallback(prompt)
        # Check per-feature budget
        if self._feature_budget_exceeded(max_tokens):
            raise FeatureBudgetExceeded(...)
        model = 'claude-haiku-4-5' if self.paradigm == 'small_llm' else 'claude-sonnet-4-6'
        # Use Anthropic prompt caching where possible
        response = await self.anthropic.messages.create(
            model=model, max_tokens=max_tokens,
            messages=prompt, extra_headers={'anthropic-beta': 'prompt-caching-2024-07-31'},
            **kwargs
        )
        self._track_usage(response.usage.input_tokens, response.usage.output_tokens)
        return response
```

---

## 31. Streamlining Principles (Single Primitives)

### 31.1 Single-Primitive Rule

Every cross-cutting concern is built once and consumed by every channel, agent, workflow:

| Primitive | Built In | Consumed By |
|-----------|----------|-------------|
| **Audience** | `notifications.audiences` + Audience Builder service | Call, WhatsApp, email, SMS, RCS, ad-platform sync, referral engine, MCP `trigger_audience` |
| **Decision Log** | `ai.decision_log` (immutable, append-only) | Every agent writes; every outcome attributes back; MCP exposes; audit views read |
| **Consent** | `notifications.consent_events` + consent_status field on customer | Call, WhatsApp, email, SMS, ads, MCP write actions |
| **Notification framework** | `notifications.in_app_notifications` + dispatcher | In-app, email, push, WhatsApp, Slack |
| **Attribution** | Unified attribution model in analytics-service | Email, SMS, WhatsApp, call, ad-platform, referral — all resolve to one revenue number per touch |
| **Identity resolution** | `customer_id` per brand joining touches across email/phone/device/account | Every channel; every agent; every report |

### 31.2 Anti-Patterns (Refactor Before Shipping)

- "The email version of the audience builder" — build once; have email consume it
- "The call-specific consent flow" — extend the consent model; do not fork
- "The WhatsApp Decision Log" — there is only one Decision Log
- "A new notification service for SMS alerts" — extend the existing notification framework
- "Per-channel customer profiles" — use the unified customer record with channel-engagement scores

### 31.3 Quarterly Audit

- Engineering team reviews codebase for anti-pattern drift quarterly
- Any duplication of cross-cutting concerns flagged + scheduled for refactor
- Refactoring time allocated explicitly each quarter — not optional, not deferred

### 31.4 Why This Matters Strategically

The single-primitive architecture lets Brain charge a flat GMV % and bundle every channel. A competitor with channel-specific stacks pays N× engineering cost for N channels and either prices per-channel or runs at lower margin. Brain pays 1× engineering cost; offers N channels at the same fee.

---

## 32. Privacy & Compliance Implementation

### 32.1 What Brain Stores

| Data Type | Storage | Retention |
|-----------|---------|-----------|
| Order data | ClickHouse `raw.orders_local` + Postgres recent mirror | Active brand life + 90 days |
| Customer identifiers | Hashed email/phone in `agg.customer_states_local`; plain only if brand explicitly enables | Active brand life + 90 days |
| Ad platform data | ClickHouse `raw.ad_spend_local` | Active brand life + 90 days |
| Logistics data | ClickHouse `raw.shipments_local` (no customer address) | Active brand life + 90 days |
| Payment data | Razorpay payment + settlement records (no card/UPI/bank) | Active brand life + 90 days |
| **Decision history** | Postgres `ai.decision_log` (immutable, append-only) | **Active brand life — no auto-delete (the moat)** |

### 32.2 What Brain Never Stores

- Card numbers, CVVs, full UPI IDs, full bank account numbers
- Full customer addresses — only ship-to pincode retained
- Customer national IDs (PAN, Aadhaar, SSN, passport) — even if Shopify exposes in customer notes (filtered at ingest)
- Plain-text passwords (Supabase Auth with hashed credentials)
- Health data, biometric data, or any other special-category data

### 32.3 Consent Implementation

- Every customer record carries `consent_status`: `opted_in`, `opted_out`, `unknown`, `withdrawn`
- Change history in `notifications.consent_events` (append-only)
- Customers with `opted_out` or `withdrawn` excluded from any agent-driven outreach
- They remain in cohort analytics in aggregated, anonymized form only
- Brand Owners can mass-import consent state from existing CRM or Shopify tags during onboarding

### 32.4 Right to Deletion (DSR)

- Owner triggers via UI or `POST /api/dsr/delete` with `{customer_id}`
- analytics-service queues hard-delete job:
  1. Find all rows for this customer across `raw.*`, `agg.customer_states_local`, `notifications.*` (audience_members, outreach, calls, tickets, messages)
  2. Hard-delete identifying fields (hashed email, hashed phone, ship-to pincode if linkable)
  3. Aggregated metrics derived from this customer retained (cannot be re-linked)
  4. Deletion logged in audit log with timestamp + Owner + customer_id

Target SLA: completed within 30 days.

### 32.5 Brand-Level Export & Closure

- Export: Owner requests via Settings → Account → Export Data. Job written to `notifications.export_jobs`; rendered ZIP delivered to S3 + signed URL emailed to Owner within 7 days
- Closure: 30-day grace → 90-day archival (data retained but workspace inaccessible) → permanent deletion
- Owner can fast-track to immediate deletion on request

### 32.6 Encryption

- **In transit:** TLS 1.2+ on every endpoint (ALB enforces); mTLS between services via App Mesh in Phase 3
- **At rest:** AES-256 — Postgres encrypted at rest by Supabase; ClickHouse encrypted by ClickHouse Cloud / EBS-encrypted volumes; S3 with KMS-managed keys per bucket
- **OAuth tokens:** AES-256-GCM application-layer encryption with **per-brand key** in AWS Secrets Manager
- Call recordings: per-brand KMS key

### 32.7 Logging

- PII never in logs
- All log lines pass through a redactor in `lib-auth` / `brain_db` that hashes email/phone patterns
- Audit log (every approve/reject, settings change, integration change, auto-execute action) in Postgres + S3 mirror for tamper evidence

### 32.8 Cross-Brand Benchmarks (Privacy Guarantee)

- Computed in separate analytics pipeline emitting only aggregated, anonymized statistics
- Raw rows never leave the brand's data partition
- **Minimum 10 qualifying workspaces per category** before benchmark publishes (prevents reverse-identification)
- Brain does not train its models on any single brand's data without explicit written opt-in

### 32.9 Regulatory Posture

- **DPDP Act 2023 (India):** Brain operates as Data Processor on behalf of brands. DPA available to all paying customers.
- **GDPR (EU):** SCCs + sub-processor list. Data residency option (EU region) on enterprise tier.
- **CCPA (California):** Same as GDPR for California-resident customers.
- **SOC 2 Type II:** kicked off Phase 1; certification 9–12 months from kick-off.
- **ISO 27001:** pursued after SOC 2.
- **Meta Tech Provider Designation:** required for handling Meta's customer data.
- **Shopify Built for Shopify badge:** target Phase 2.

---

## 33. Auth & Authorization

### 33.1 Auth Provider: Supabase

- Supabase Auth (`@supabase/ssr`) handles email/password, magic link, social OAuth (Google, Apple — Phase 1), SSO/SAML (Phase 3 for enterprise)
- JWT issued on login; stored in HttpOnly cookie (immune to XSS)
- Auto token refresh in middleware
- User row upserted in `core.users` on every login (via `lib/ensure-user.ts` pattern from existing codebase)

### 33.1.1 Signup, Login, and Per-Brand Dashboard Flow

Every DTC brand on Brain has its own signup → onboarding → dashboard:

1. **Signup:** founder visits `brain.pipadacapital.com/auth/signup` (Phase 4: per-region domains like `brain.com/auth/signup`). Email + password (or Google/Apple OAuth). One user, one global Brain account.
2. **Onboarding:** new user creates an Organisation (auto-default = their company name) → creates first Brand (= Workspace). They're auto-assigned Owner role on the Brand.
3. **Integration connect:** OAuth connect flow for Shopify, Meta, Google, Shiprocket, Razorpay. Each integration scoped to that Brand only.
4. **Team invite:** Owner invites teammates by email. Each invitee gets Owner / Operator / Analyst / Agency / Read-only role on the Brand. Same email can be invited to many Brands with different roles in each.
5. **Brand switcher:** if a user has access to multiple Brands (Model B holding-co, or multi-Brand membership), the UI shows a Brand switcher in the header. Session rebinds to the selected Brand; URL changes to `/w/{slug}/...`.
6. **Per-Brand dashboard:** every Brand's data + dashboards + alerts + integrations are fully isolated. Switching to a different Brand loads that Brand's data only — no leak.

**For Model B (multi-brand holding co):**
- A founder/CEO of the Org can be Owner across multiple Brands they own
- A group CFO can be granted **portfolio rollup access** (`cross_brand_read` privilege on the Org) — gets an additional "Portfolio" view across all Brands in the Org
- Per-Brand Operators / Analysts / Marketers stay scoped to their own Brand

**For Model C (agency):**
- Agency user signs up under the Agency Organisation
- Each Client Brand (belonging to a different end-customer Org) grants the agency user a scoped role
- Agency UI shows all Client Brands the user has access to in one switcher; never shows another agency's clients

**For Enterprise (Model D):**
- All of the above + SSO/SAML integration (Phase 3) so enterprise users authenticate via their corporate IdP (Okta, Azure AD, Google Workspace)
- SCIM provisioning (Phase 4) so enterprise IT can mass-provision/deprovision users
- IP allowlist enforcement at api-gateway per Org (Enterprise Variant feature)

### 33.2 JWT Claims

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "active_workspace_id": "workspace-uuid",
  "active_role": "owner",
  "available_workspaces": [
    { "workspace_id": "...", "role": "owner" },
    { "workspace_id": "...", "role": "operator" }
  ],
  "exp": 1234567890
}
```

### 33.3 Middleware

`middleware.ts` (Next.js Edge runtime in frontend) AND `apps/api-gateway/src/middleware/auth.ts`:
1. Validate JWT via Supabase
2. If unauthenticated:
   - Public path (`/auth/*`, `/invite/*`, webhooks) → pass through
   - Else → redirect to `/auth/login`
3. If authenticated:
   - Refresh token if expired
   - Set request context: `{user_id, active_workspace_id, active_role}`
   - Pass through

### 33.4 Authorization

**Role hierarchy** (numeric levels for comparison):

| Role | Level | Permissions |
|------|-------|-------------|
| readonly | 1 | Read defined subset; no PII, no raw data |
| analyst | 2 | Read all dashboards + comment; cannot approve/reject; cannot change settings |
| agency | 3 | Scoped read/write per Owner; always logged |
| operator | 4 | Full read/write on operational data; approve/reject; cannot change billing or delete brand |
| owner | 5 | Full access including billing, integrations, delete brand, founder salary |

**Standard guards** in `packages/lib-auth/`:
- `requireWorkspaceMember(ctx, workspaceId)` — checks membership exists
- `requireRole(ctx, workspaceId, minimumRole)` — checks role >= minimum
- `requireFeature(workspace, featureKey)` — checks `workspace.features[key] !== false`

Every mutation endpoint must call `requireRole`. Reviewers enforce in PRs.

### 33.5 Feature Flags

- Per-workspace JSON in `core.workspaces.features`: `{pnl: true, meta_ads: false, ...}`
- Default: all features ON unless explicitly `false`
- Used for plan gating + gradual rollout
- Cached in Redis with 5-min TTL

### 33.6 Session Storage

- HttpOnly cookies (Supabase SSR pattern) — immune to XSS
- Refresh tokens stored server-side; only access token in cookie
- No tokens in localStorage / sessionStorage anywhere

### 33.7 OAuth State Tokens

- `core.oauth_states` table — UUID token + workspace_id + provider + verifier (PKCE) + created_at
- 10-min TTL enforced at lookup
- Single-use: deleted after callback

---

## 34. Observability & Monitoring

### 34.1 Logs (CloudWatch Logs)

- Every service writes structured JSON logs to CloudWatch
- Standard fields: `timestamp`, `service`, `level`, `workspace_id`, `user_id`, `trace_id`, `span_id`, `message`, `metadata`
- PII redaction at log adapter level
- 30-day retention in CloudWatch; longer-term archive to S3 via subscription filter
- Sentry for errors (richer stack traces + grouping)

### 34.2 Metrics (CloudWatch Metrics)

Per-service custom metrics:
- Request rate, latency p50/p95/p99, error rate per endpoint
- Kafka consumer lag per topic per consumer group
- Postgres query duration per query class
- ClickHouse query duration + bytes scanned per query
- LLM token usage per workspace per feature
- Auto-execute action counts + outcomes per agent

### 34.3 Tracing (AWS X-Ray)

- Request flow: api-gateway → gRPC → service → Postgres/ClickHouse → response
- Distributed trace IDs propagated via gRPC metadata + Kafka headers
- Sample rate: 100% for errors, 5% for successes in production

### 34.4 Alarms

CloudWatch Alarms publish to SNS → PagerDuty (production) / Slack (staging):
- Error rate > 1% sustained for 5 min → page
- p95 latency > 2s sustained for 5 min → page
- Kafka consumer lag > 10K messages sustained for 10 min → page
- Postgres connection pool exhaustion → page
- ClickHouse query timeout rate > 0.1% → page
- LLM cost per brand per day exceeds 1.5× monthly cap / 30 → page
- Any integration with `last_sync_at` > 1 hour stale → page (per workspace, dedup)
- Any DND violation in calling → P0 page

### 34.5 Product Analytics (PostHog)

- Page views, feature engagement, retention, conversion funnels
- Per-workspace dashboards aggregated to cross-brand product metrics
- Strict PII handling — only hashed user IDs

### 34.6 SLOs

| SLO | Target |
|-----|--------|
| API p95 latency (dashboard reads) | <100ms |
| ClickHouse p95 query | <500ms |
| Service availability per service | >99.9% (3 nines monthly) |
| Data freshness (max integration lag) | <1 hour |
| Morning Brief delivery latency | <20 min from data pull |
| LLM error rate (Claude API) | <0.5% |
| Auto-execute action accuracy | >80% (7d or 30d outcome match) |

### 34.7 Health Check Endpoints

- `GET /health` on every service: returns `{status: "ok", version, uptime}` if process responsive
- `GET /health/ready` on every service: checks downstream deps (Postgres, ClickHouse, Kafka)
- ALB target group health checks against `/health`
- ArgoCD readiness probes against `/health/ready`

### 34.8 Audit Log

- Every mutation (settings change, integration connect/disconnect, invite, role change, auto-execute reverse) logged to `core.audit_log`:
  ```sql
  CREATE TABLE core.audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    user_id     UUID,
    action      TEXT NOT NULL,
    resource    TEXT NOT NULL,
    old_value   JSONB,
    new_value   JSONB,
    ip_address  INET,
    user_agent  TEXT,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```
- Owner can export via Settings → Audit Log

---

## 35. Scale Design (Path to 100k req/min — Global Multi-Tenant)

### 35.0 The Two Scale Vectors

Brain scales on two independent vectors:
1. **Cross-tenant scale:** number of Brands × requests per Brand. Target: **100k req/min sustained, 5K RPS peak** at 200+ Brands globally (Phase 4 exit). Each shared-tier Brand has its own rate-limit ceiling (Section 35.11).
2. **Per-tenant scale (enterprise):** a single Brand at enterprise scale generates 50M+ orders/year, 10K+ products, 100+ ad accounts, hundreds of pincodes/regions per day. Per-tenant capacity is sized so any one Brand can stress the ingestion + analytics stack without degrading other Brands.

Both vectors are addressed in this section. Per-tenant scale is not just "shared-tenant divided by N" — enterprise Brands get sized shards, dedicated workers (Phase 3+), or BYO-VPC deployment (Enterprise Variant D) as required.

100k req/min = ~1,666 RPS sustained, ~5,000 RPS peak. Per-layer plan:

### 35.1 Edge: CloudFront
- Caches static assets (immutable; 1-year)
- Caches `GET /api/health` and similar (5s)
- WAF: rate limits, geographic rules
- Capacity: effectively unlimited

### 35.2 Load Balancer: ALB
- Auto-scales itself
- HTTP/2 + gRPC pass-through
- Path-based routing to api-gateway target group

### 35.3 api-gateway
- HPA: 4–40 pods on EKS
- Each Node pod handles ~500 RPS comfortably (Fastify + tRPC)
- Karpenter scales nodes based on pod pressure
- Capacity: 40 pods × 500 RPS = 20K RPS → 1.2M RPM (above target)

### 35.4 core-service
- Mostly cached reads (Redis layer for workspace metadata, members, settings)
- Cache hit rate target: 95%+
- Writes rare, small. Single-digit RPS even at full scale.
- Pods: 2–10

### 35.5 analytics-service
- Heaviest read path (powers dashboards)
- ClickHouse handles heavy lifting; service is query routing + Redis caching
- Hot metric cache (Redis): 60s TTL on `daily_metrics`, ~99% hit rate
- Pods: 3–20

### 35.6 ClickHouse
- Cluster: 3 shards × 2 replicas start. Scale to 6 shards at 50K+ workspaces.
- ReplicatedMergeTree for HA
- Per-query budget: <500ms p95 for dashboard queries
- Materialized views for ultra-hot aggregations

### 35.7 Postgres (Supabase)
- Single primary + 2 read replicas (Phase 2)
- PgBouncer in transaction mode (10K client → 200 backend connections)
- Connection pool per service
- At 100k req/min, Postgres sees ~5K QPS (most reads cached). Comfortable on Supabase's higher tiers.
- Escape hatch: Aurora Postgres if Supabase tier ceiling hits us

### 35.8 Redis (ElastiCache)
- Cluster mode: 3 shards initially, scale to 12
- ~10 GB working set; scale via shard count
- Throughput: easily 1M ops/sec at our cluster sizes

### 35.9 Kafka (MSK)
- 6 brokers across 3 AZs initially
- Replication factor 3 for important topics
- Each broker handles ~50K msg/sec ingress
- At 100K req/min, even 1:1 event-to-API-call ratio well under capacity

### 35.10 Connection Budget (Postgres)

| Service | Pods (peak) | Conns/pod | Total |
|---------|-------------|-----------|-------|
| api-gateway | 40 | 5 | 200 |
| core-service | 10 | 20 | 200 |
| ingestion-service | 30 | 5 (long-lived per workspace) | 150 |
| analytics-service | 20 | 10 (mostly ClickHouse, light Postgres) | 200 |
| intelligence-service | 10 | 5 | 50 |
| notifications-service | 8 | 10 | 80 |
| **Total** | | | **~880** |

All behind PgBouncer transaction-pooled → ~200 backend connections on Postgres. Comfortable.

### 35.11 Per-Workspace Rate Limits

- Frontend → api-gateway: 1,000 req/min per user, 5,000 req/min per workspace
- Public API (Phase 4+): tiered (Starter/Pro/Enterprise)
- AI Chat: 50 messages/min per user; daily token budget per workspace
- MCP traffic: counts against same per-workspace caps as in-app
- Enforced in Redis sliding window

### 35.12 Capacity Levers (When We Need More)

In order of cost:
1. Increase Redis cluster shard count → improves cache hit rate at scale
2. Scale up analytics-service pods + ClickHouse query routing
3. Add ClickHouse shards (1 day rebalance)
4. Add Postgres read replicas
5. Increase Kafka broker count
6. Migrate Postgres to Aurora if Supabase ceiling
7. Add second region (Phase 4)

### 35.13 Enterprise Per-Tenant Scale (When a Single Brand Is Very Large)

Enterprise Brands (₹50Cr+/month or multi-warehouse multi-region operations) may individually exceed shared-tier per-Brand budgets. Levers in order:
1. **Dedicated ClickHouse shard:** route the enterprise Brand's queries to a reserved shard so noisy-neighbor effects are eliminated. Enabled per-Brand via `core.workspaces.dedicated_clickhouse_shard`.
2. **Dedicated ingestion-service worker pool:** the enterprise Brand's per-integration sync jobs scheduled to a dedicated Karpenter node pool with reserved capacity.
3. **Dedicated Kafka topic partition reserved:** for enterprise Brands generating millions of events/day, reserve dedicated partitions on `integrations.*` topics so consumer lag doesn't bleed across Brands.
4. **Per-Brand LLM cap uplift:** enterprise Brands get higher monthly cap or pass-through token billing.
5. **BYO-VPC deployment (Enterprise Variant D, Phase 3+):** entire Brand's stack (Postgres + ClickHouse + Kafka) deployed in the Brand's own AWS account. Brain control plane orchestrates via VPC peering / PrivateLink. Same code, different deployment topology.

### 35.14 Global Cross-Region Capacity (Phase 4)

When a Brand's `home_region` is not the primary (ap-south-1):
- Writes still go to home region (e.g., us-east-1 for US Brand)
- Per-region capacity sized independently — secondary region starts at 30% of primary capacity, scales with regional Brand count
- Cross-region replication (DMS for Postgres, MirrorMaker 2 for Kafka, ClickHouse native for OLAP) sized for the data velocity of the Brands homed there

---

## 36. Multi-Region Deployment (Phase 4)

### 36.1 Architecture

- **Primary region:** ap-south-1 (Mumbai) — India primary market
- **Secondary region:** us-east-1 (N. Virginia) — US/EU expansion
- **Read-only edges:** read replicas of Postgres + ClickHouse in secondary regions for sub-100ms dashboards

### 36.2 Per-Workspace Region

- `core.workspaces.home_region` (default `ap-south-1`)
- All writes for that workspace go to home region
- Reads from any region serve from local replica

### 36.3 Cross-Region Sync

- **Postgres:** AWS DMS or logical replication (async)
- **ClickHouse:** ClickHouse-native replication (ReplicatedMergeTree across regions; eventual consistency)
- **Kafka:** MirrorMaker 2 between MSK clusters (one-way; secondary is read-only)
- **S3:** cross-region replication for exports

### 36.4 Compliance Future (Phase 5+)

- Per-region data residency
- EU workspaces' data never leaves eu-central-1
- Brand-controlled cloud deployment for enterprise tier (BYO-VPC)

---

## 37. AWS Service Inventory & Cost Class

| AWS Service | Purpose | Monthly Cost @ Phase 3 |
|-------------|---------|------------------------|
| EKS | Container orchestration | $1.5K–3K (cluster + nodes) |
| EC2 (via Karpenter) | Worker nodes | $2K–6K (spot mix) |
| MSK | Kafka | $1K–2K (3 brokers, tiered storage) |
| RDS (or Supabase) | Postgres | $500–1.5K (Supabase Pro/Team tier) |
| ClickHouse Cloud | OLAP | $1K–3K (3 nodes) |
| ElastiCache | Redis | $400–1K (cluster mode) |
| ALB | Load balancer | $200 |
| CloudFront | CDN | $300 (volume-based) |
| Route 53 | DNS | $50 |
| S3 | Object storage | $200 |
| SES | Email | $50 (volume-based) |
| Secrets Manager | Secrets | $50 |
| CloudWatch | Logs + metrics + alarms | $400 |
| X-Ray | Tracing | $100 |
| EventBridge | Scheduler + cron | $20 |
| ECR | Container registry | $50 |
| WAF / Shield Standard | DDoS, app firewall | $30 + per-rule |
| VPC / NAT / etc. | Networking | $300 |
| Data transfer | Cross-AZ + egress | $500 |
| **Total estimate** | | **$8K–18K/month at Phase 3** |

**Plus external:**
- Anthropic Claude: $50–500/month with caching
- Sentry: $80
- PostHog: $0–200
- Gupshup WhatsApp: variable, ~$200–500

**Cost trajectory:**
- Phase 0 (1 brand): ~$1.5K/month
- Phase 1 (5 brands): ~$3K/month
- Phase 2 (15 brands): ~$5K/month
- Phase 3 (50 brands): ~$10K–15K/month
- Phase 4 (200+ brands, 100K req/min): $25K–50K/month

---

## 38. Local Development

### 38.1 Stack

Each developer runs:
- Docker Compose with Postgres, ClickHouse, Kafka (single-broker), Redis, MinIO (S3 stand-in)
- All 6 services run locally via `pnpm dev` (TS) + `uv run dev` (Python)
- Frontend connects to local api-gateway
- LocalStack for AWS service mocks (S3, SES)
- MSK has no local — use single-broker Kafka via Confluent's `cp-kafka` image
- Synthetic example brand data seeded on first `pnpm db:seed`

### 38.2 Commands

```bash
# One-time setup
pnpm install
uv sync
docker compose up -d
pnpm db:migrate
pnpm db:seed   # seeds demo workspace with synthetic Sugandh Lok-style data

# Daily
pnpm dev                          # all services
pnpm dev --filter api-gateway     # one service

# Regen code from protos
buf generate

# Run tests
pnpm test
uv run pytest

# Format
pnpm format
uv run ruff format .
```

### 38.3 Demo Data

`tools/seed-demo.py` generates synthetic data for a beauty brand (modeled after Sugandh Lok pattern but configurable):
- 12 months of synthetic orders (~10K)
- 5K customers with realistic repeat distribution
- 20 SKUs across 4 product categories
- Synthetic Meta + Google campaigns with realistic CTR/CPM/ROAS
- Shiprocket shipment data with realistic 22% RTO rate, NDR distribution
- 18% prepaid / 82% COD payment split
- Indian pincode distribution matching real geographic spread

This ensures every developer has a representative dataset to develop against without needing a real brand connected.

---

## 39. Ownership Matrix (4 Engineers)

| Engineer | Primary Owns | Secondary Owns |
|----------|--------------|----------------|
| **E1 (Tech Lead / Platform)** | api-gateway, infra (CDK), security, AWS-native ops, deployment, multi-tenancy, Kafka platform, MCP framework | core-service primary review |
| **E2 (Frontend-Heavy)** | frontend, design system, all dashboards, charts, mobile Morning Brief, Creative Queue UI | api-gateway tRPC surface, BFF aggregations |
| **E3 (Backend / Data)** | core-service, ingestion-service, Postgres + Kafka schemas, ETL, integration connectors | analytics-service primary review |
| **E4 (Data / ML)** | analytics-service, intelligence-service (agents, forecasting, anomaly), ClickHouse, regional adapters, LTV/RFM engines | notifications-service primary review |

**Cross-cutting:**
- Migrations require 2 reviewers
- Proto changes require E1 approval (cross-cutting contracts)
- Infra changes require E1 approval
- LLM cost-impacting changes require E4 approval

**Backstop:** when only 2 engineers, E1 + E3 cover backend; E2 covers frontend; E4 hire is second priority after Phase 1.


---

## 40. Build Phases & Roadmap

### 40.1 Master Timeline

| Phase | Weeks | Goal | Exit Criterion |
|-------|-------|------|----------------|
| **Phase 0** | 1–4 | Foundation. Brain runs end-to-end with all infra and 1 brand. | Example brand's data flows end-to-end for 7 consecutive days, including Shiprocket |
| **Phase 1** | 5–12 | The Wedge. Ship the three features that justify Brain to a new operator. | Operator opens Brain daily; 3+ more brands signed up |
| **Phase 2** | 13–22 | Customer Intelligence + Regional Depth + Lifecycle Layer (outbound) + Multi-Brand Holding Co (Model B) GA | 10+ paying brands incl. at least 1 multi-brand Org; ClickHouse handling 95% of dashboard reads |
| **Phase 3** | 23–36 | Full Intelligence Layer + Agentic Commerce 30-day + Native Email Engine + Scale + **Enterprise Variant (Model D) GA** | 30-day forecasts within 15% variance; sustained 5K+ RPS; first enterprise customer on Enterprise Variant (BYO-VPC or custom model) |
| **Phase 4** | 37+ | Global Expansion. US/EU regional adapters, multi-region, public REST API, SOC 2 Type II | First non-Indian customer; 100K req/min sustained |

### 40.1.1 Enterprise & Multi-Brand Availability by Phase

Enterprise and multi-brand features are not a single Phase 4 unlock — they ramp through the phases:

| Capability | Available From | Notes |
|-----------|----------------|-------|
| **Model A — Single-Brand** | Phase 0 | Default for founding cohort |
| **Model C — Agency Account** (scoped read/write across multiple client Brands) | Phase 1 | First agency customer in founding cohort |
| **Model B — Multi-Brand Holding Co** (one Org, N Brands, portfolio rollups) | Phase 2 | GA-ready by W22 |
| **Model D — Enterprise Variant — managed** (custom SLA, dedicated CSM, custom integrations) | Phase 2 | Sales-led from W13 onwards |
| **Model D — Enterprise Variant — BYO-VPC** (private deployment in customer's AWS account) | Phase 3 | Requires hardened CDK templates + customer onboarding runbook |
| **Model D — Enterprise Variant — custom model fine-tuning** | Phase 3 | Requires opt-in training pipeline + per-Brand model serving |
| **Model D — EU/US data residency** | Phase 4 | Requires multi-region infrastructure |
| **Public REST API + partner ecosystem** | Phase 4 | Tiered rate limits per plan |
| **Per-region per-Brand data residency (eu-central-1, etc.)** | Phase 5+ | Compliance-driven |

### 40.2 Phase 0 — Foundation (W1–4)

**Infrastructure:**
- AWS CDK infra: VPC, EKS, MSK, RDS/Supabase, ClickHouse, ElastiCache, S3, ECR, CloudFront, ALB
- Repo + CI/CD pipeline (GitHub Actions → ECR → ArgoCD)
- Postgres schemas + Supabase Auth + RLS
- ClickHouse schemas (raw + agg)
- Kafka topics + Glue Schema Registry
- Observability baseline: CloudWatch dashboards, Sentry, X-Ray

**Services:**
- 6 services scaffolded with health endpoints
- api-gateway with auth + rate limit
- core-service with workspace CRUD + invitations
- ingestion-service with Shopify + Shiprocket connectors (end-to-end)
- analytics-service computes basic daily_metrics
- intelligence-service stub
- notifications-service in-app + email scaffold

**Frontend:**
- Auth (signup/login/reset)
- Workspace creation + onboarding flow
- Team invites
- Basic dashboard (yesterday + 7-day metrics)

**Migration (if porting from existing Looqus codebase):**
- Export schema + data; load into new Postgres + ClickHouse
- Map OAuth credentials (re-encrypt with new per-brand keys)
- Decommission Looqus instance after parallel run

### 40.3 Phase 1 — The Wedge (W5–12)

Ship the **three features that justify Brain to a new operator:**

1. **First Product → Repeat Purchase Cascade**
2. **RTO-aware Contribution Margin Waterfall** (uses real Shiprocket data)
3. **MER + aMER + Acquisition vs Non-Acquisition** (with classification UI + auto-classifier)

Plus:
- Goal-setting infrastructure (Section 14.13)
- Calendar Report v1
- Meta Ads + Google Ads integrations (full incremental sync + creative metrics + funnel)
- Razorpay integration
- AI Chat embedded on every page (Phase 1 version — Sonnet with workspace context)
- Daily email digest at 08:00 IST

### 40.4 Phase 2 — Customer Intelligence + Regional Depth + Lifecycle (W13–22)

**Customer:**
- Net Active Customer report with P40/P80 thresholds
- Cohort segmentation by channel, first product, discount code
- RFM/RFMC segmentation engine (with daily snapshots + segment exports)

**India regional:**
- Pincode reliability + RTO prediction
- COD-vs-prepaid economics view
- Festival calendar overlay on all time-series
- Pincode Intelligence with India map heatmap
- AI pincode-blacklist recommender

**Inventory:**
- Predicted stockout date, reorder quantity calculator, safety stock

**Reporting:**
- Calendar Report v2 (all columns)

**Lifecycle Layer v1a (Outbound):**
- Audience Builder primitive
- Abandoned cart recovery, COD confirmation calls, post-delivery follow-up, winback, VIP retention, replenishment
- WhatsApp marketing campaigns via Gupshup
- Referral Engine v1

**Native Email Engine v1:**
- Klaviyo integration (read-only initially)
- Segmentation engine over Memory Layer
- Template editor + flow builder
- Deliverability backbone via AWS SES with IP warming

**Scale:**
- PgBouncer in front of Postgres
- Read replica routing for analytics-service

### 40.5 Phase 3 — Intelligence + Agentic + Scale (W23–36)

**Plan Module v1:**
- aMER curve (isotonic regression) + retention model + festival multipliers
- Conservative/Base/Optimistic scenarios
- What-if scenario builder
- AI aMER target suggestion

**Anomaly Detection (Section 20):**
- Z-score on 14 metrics
- Root cause attribution
- Multi-channel alert routing (CRITICAL/HIGH/MEDIUM/ROUTINE)

**Proactive AI:**
- Daily insight generation post-anomaly scan
- AI Chat upgrade with Claude tool use (queries analytics-service via gRPC)
- Brand Fingerprint embedding generation (pgvector)
- Condition-outcome matching via cosine search

**Budget Allocation Optimizer:**
- Spend-response curve estimation per channel (power-law fit)
- Marginal aMER optimization
- Per-channel allocation recommendation with confidence

**Predictive LTV Engine:**
- BG/NBD + Gamma-Gamma model training (monthly cron)
- Per-customer predicted_ltv_30d/90d/180d
- LTV Drivers report
- Max CAC recommendations

**Agentic Commerce (30-day commitment):**
- 8 initial auto-execute actions (Section 26)
- Confidence gating + spend caps + kill switch + immutable Auto-Execute Log
- Owner consent flow + per-brand consent matrix

**Lifecycle Layer v1b (Inbound):**
- Multi-channel inbox (WhatsApp + Instagram DM + email + web chat)
- Autonomous resolution of top 10 ticket types
- Human escalation path

**Creative Intelligence:**
- AIDA scoring per creative
- Creative fatigue detection (EWMA)
- Agentic creative variant generation with three-loop confidence routing
- Designer brief format + workflow

**Market Basket Analysis:**
- Apriori algorithm via `mlxtend`
- Bundle recommendations + cross-sell triggers

**Native Email Engine v2:**
- Predictive send-time per customer
- A/B testing with auto-graduation
- Deliverability dashboard
- WhatsApp-aware send suppression

**Channel Expansion (Phase 2 of Brain-Technical-Brief):**
- SMS via TrustSignal (DLT-compliant)
- RCS Business Messaging

**Scale:**
- ClickHouse cluster scaling (3 → 6 nodes)
- MSK auto-scaling + Kafka tiered storage to S3
- OpenSearch for product/customer search
- WebSocket live dashboard refresh

**MCP:**
- Internal MCP between agents
- External read-only MCP for brands' AI tools

### 40.6 Phase 4 — Global Expansion + Scale (W37+)

**Geographic:**
- GCC (UAE + KSA) integrations: Salla, Zid, Noon, Tabby, Tamara, Telr, Aramex, DHL, SMSA
- US/EU regional adapters: multi-currency, multi-timezone, regional tax models
- Multi-region deploy: primary ap-south-1, secondary us-east-1
- Read replicas in target regions for sub-100ms dashboards outside India

**Integrations expansion:**
- Klaviyo full migration option
- TikTok Ads, Snapchat Ads
- Multi-3PL (Delhivery, Bluedart direct)
- Amazon SP-API (India + AE), Flipkart, Myntra, Nykaa (PDF), Blinkit (PDF)

**Public API:**
- Read-only REST endpoints
- API key issuance
- Tiered rate limits

**Advanced features:**
- iROAS via geo holdouts
- WhatsApp Commerce attribution
- Demand forecasting integrated with Plan Module + inventory

**Compliance:**
- SOC 2 Type 1 → Type II
- ISO 27001 kickoff
- EU data residency (Phase 5)

**MCP:**
- External action MCP (trigger_audience, propose_action)
- Bidirectional with platform MCPs (Shopify, Meta, Razorpay)

### 40.7 Phase 5+ (Future Bets)

- Retail OS (POS + ERP + CRM/loyalty as data sources) — UAE pilot first
- Capital products (inventory-backed lending, revenue-based financing) on Brain's CM2-correct P&L data
- Customer-facing agentic commerce (MCP for ChatGPT/Perplexity exposing brand catalog)
- Native mobile apps (iOS + Android)
- Voice cloning of brand founder for AI calls (with explicit consent + disclosure)
- Enterprise tier: private data warehouse deployment in brand's own cloud

---

## 41. Migration Plan from Existing Codebase (Looqus)

### 41.1 What Exists Today

The Looqus codebase (audited 2026-05-04) is a Next.js 16 monolith on Supabase + Prisma + Vercel-style deployment. It contains substantial working logic:

- **COGS engine** (`lib/cogs/resolve.ts`) — 3-tier resolution
- **P&L bucketing** (`lib/pnl/buckets.ts`)
- **Customer lifecycle** (`lib/metrics/customer-lifecycle.ts`)
- **Cohorts** (`lib/cohorts/`)
- **LTV** (`lib/ltv/`)
- **Acquisition** (`lib/acquisition/`)
- **AI engine** (`module/ai-engine/`) — Claude integration, page-specific context adapters, caching
- **OAuth flows** for Shopify, Meta, Google, Shiprocket, Klaviyo
- **WooCommerce integration**
- **Festival calendar data**
- **5-level role hierarchy** (OWNER/ADMIN/MANAGER/ANALYST/VIEWER)
- **Workspace + multi-tenancy patterns**

### 41.2 What Gets Ported (Phase 0)

| Looqus Module | New Home | Notes |
|---------------|----------|-------|
| `lib/cogs/resolve.ts` | `pylibs/brain_metrics/cogs.py` (port to Python) | Re-implement with tests; keep TS version in lib-metrics for frontend display only |
| `lib/pnl/buckets.ts` | `pylibs/brain_metrics/pnl.py` | Port |
| `lib/cohorts/` | `pylibs/brain_metrics/cohorts.py` + ClickHouse materialized views | Port + rewrite for ClickHouse |
| `lib/ltv/` | `pylibs/brain_ml/ltv.py` (BG/NBD) | Replace empirical churn with BG/NBD model |
| `lib/acquisition/` | `pylibs/brain_metrics/acquisition.py` | Port |
| `lib/metrics/customer-lifecycle.ts` | `pylibs/brain_metrics/lifecycle.py` + state machine | Port + add P40/P80 thresholds |
| `lib/metrics/customer-first-order.ts` | `pylibs/brain_metrics/first_product.py` | Port + extend to First Product Cascade |
| `lib/festivals/` | `pylibs/brain_regional/festivals_india.py` | Port — fits into RegionAdapter |
| `lib/shopify/sync.ts` | `apps/ingestion-service/connectors/shopify.py` | Port logic; preserve UPSERT idempotency + cursor pagination |
| `lib/integrations/meta-sync.ts` | `apps/ingestion-service/connectors/meta.py` | Same |
| `lib/integrations/google-sync.ts` | `apps/ingestion-service/connectors/google.py` | Same; preserve PKCE |
| `lib/integrations/shiprocket-sync.ts` | `apps/ingestion-service/connectors/shiprocket.py` | Same; add webhook |
| `lib/integrations/klaviyo-sync.ts` | `apps/ingestion-service/connectors/klaviyo.py` | Same |
| `lib/integrations/woocommerce-sync.ts` | `apps/ingestion-service/connectors/woocommerce.py` | Add webhook signature validation (a gap in current code) |
| `module/ai-engine/pipeline/page-insight.ts` | `apps/intelligence-service/pipeline/page_insight.py` | Port; refactor with cost-routed paradigm |
| `module/ai-engine/context-adapters/*` | `apps/intelligence-service/context_adapters/*.py` | Port one adapter per page |
| `module/ai-engine/analysis/comparator.ts, anomaly.ts, trend.ts` | `pylibs/brain_ml/analysis/*.py` | Port |
| `lib/notifications/create.ts` | `apps/notifications-service/src/notifications.ts` | Port (stay TS) |
| Component library (`components/`) | `apps/frontend/components/` + `packages/ui/` | Move into new monorepo |
| All page routes (`app/`) | `apps/frontend/app/` | Move + adapt to tRPC calls |

### 41.3 What Gets Deleted

| Path | Reason |
|------|--------|
| `module/ai/` | Dead code (Looqus tech debt #1) |
| `lib/ai-calc/` | Dead code |
| `lib/insights/` | Dead code |
| `WorkspaceAiInsightsCache` (DB model) | Legacy, superseded by new `ai.insights` |
| `WorkspaceDailyMetrics` (table) | Populated by script but never queried; new architecture uses ClickHouse materialized views |
| `OLLAMA_INSIGHTS_MODEL` env var | Legacy Ollama fallback no longer in active code |

### 41.4 Data Migration

1. **Schema migration:** translate Prisma schema to new Postgres + ClickHouse split
2. **Export:** Looqus Postgres → CSV / Parquet
3. **Transform:** apply schema migrations + tenant-scope filtering
4. **Load:**
   - OLTP data → new Supabase Postgres (`core`, `notifications`, `ai`, `memory` schemas)
   - Time-series data → ClickHouse `raw.*` and `agg.*` tables
5. **OAuth re-encryption:** decrypt existing plaintext tokens, re-encrypt with new per-brand AES-256 keys, store in `core.integrations.encrypted_credentials`
6. **Verify:** parallel run for 1 week — both Looqus + Brain compute same metrics; diff alarm threshold
7. **Cutover:** redirect frontend traffic; decommission Looqus

### 41.5 Role Migration

| Looqus Role | New Role | Notes |
|-------------|----------|-------|
| OWNER | owner | Direct map |
| ADMIN | operator | Direct map |
| MANAGER | (deprecated) | Per-brand decision: upgrade to operator or downgrade to analyst |
| ANALYST | analyst | Direct map |
| VIEWER | readonly | Direct map |
| (new) | agency | New role for external agency staff |

### 41.6 Risk Mitigations

- Parallel run with both systems live for 1 week; metric diff alarm < 0.1%
- Read-only mode on Looqus during cutover (24 hours)
- Rollback plan: re-point frontend to Looqus DNS if Brain shows P0 issues in first 48 hours
- All Looqus data preserved in cold storage for 1 year post-cutover

---

## 42. Technical Debt Inventory (Inherited from Looqus + Net-New)

### 42.1 High-Severity (Fix in Phase 0/1)

| Issue | Source | Fix |
|-------|--------|-----|
| OAuth token plaintext storage | Looqus | AES-256-GCM wrapper with per-brand key in AWS Secrets Manager — Phase 0 |
| Inconsistent role enforcement (some routes check only `member != null`) | Looqus | `requireRole(ctx, workspaceId, 'operator')` guard applied to every mutation endpoint — Phase 0 |
| Dead code modules (`module/ai/`, `lib/ai-calc/`, `lib/insights/`) | Looqus | Delete during migration — Phase 0 |
| No rate limiting on sync endpoints | Looqus | Per-workspace rate limit (1 sync/15 min/integration); background scheduled syncs go to priority-low queue — Phase 0 |
| No CSRF protection on API mutations | Looqus | tRPC by default validates origin; add explicit CSRF token for non-tRPC routes — Phase 0 |
| No webhook signature validation for WooCommerce | Looqus | Add HMAC validation — Phase 1 |
| Long-lived Meta tokens (60 days) without rotation alerting | Looqus | Daily check of `token_expires_at < 7d`; auto-trigger refresh; alert workspace if refresh fails — Phase 1 |

### 42.2 Medium-Severity (Fix in Phase 1/2)

| Issue | Source | Fix |
|-------|--------|-----|
| Sequential DB queries in workspace layout (`workspace + member + all-memberships`) | Looqus | `Promise.all([...])` in new BFF — Phase 0 |
| No structured logging | Looqus | CloudWatch JSON + redaction at log adapter — Phase 0 |
| No CI/CD with tests | Looqus | GitHub Actions: lint → typecheck → test → build → push → ArgoCD — Phase 0 |
| Only one test file in entire Looqus codebase | Looqus | Mandate >70% test coverage per new feature; Phase 0 backfills tests on ported modules |
| No pagination on large analytics payloads (`Last 12 months` returns 365+ rows) | Looqus | Server-side bucketing in analytics-service for ranges > 90 days (weekly aggregation) — Phase 1 |
| Bundle size: recharts (~150KB), @dnd-kit (~35KB) loaded on every page | Looqus | Dynamic imports via `next/dynamic` — Phase 1 |
| Date range bounds not validated on API | Looqus | Zod schema rejects ranges > 2 years client-side; gRPC handler rejects > 5 years server-side — Phase 0 |

### 42.3 Net-New Debt to Watch

| Item | Mitigation |
|------|-----------|
| Red-tier integrations (Nykaa, Blinkit Gmail+PDF) are brittle by definition | Continuous health monitoring; per-brand alerting within 1 hour; UI disclaimer; graceful degradation in dashboards |
| pgvector cosine search may not scale past 10M embeddings | Phase 4 evaluation: migrate to Pinecone/Weaviate if benchmarks fail |
| MCP server is a new attack surface | Per-action consent at token issue; same rate limits as in-app; comprehensive audit log |
| Auto-execute reversal accuracy depends on partner APIs supporting reversal | For each auto-execute action: document partner API reversal capability; if irreversible, raise confidence threshold to >0.95 |
| Multi-region (Phase 4) introduces eventual consistency challenges | Per-workspace single home region; reads from any region; cross-region replication delay monitored |

### 42.4 Refactoring Opportunities

| Opportunity | Benefit |
|-------------|---------|
| Extract `validateWorkspaceMember(request, slug)` helper | Replaces copy-paste auth block in 25+ Looqus route files; standard in new architecture |
| Aggregate daily data server-side for 90-day+ ranges | Reduce JSON payload from 365 rows to 52 (weekly) |
| Convert workspace metrics rollup from script to event-driven job | Eliminates the unused `WorkspaceDailyMetrics` table; ClickHouse materialized views replace it |
| Add `Promise.all` in workspace layout parallel DB queries | Save ~100ms per navigation |

---

## 43. Decision Log

| Date | Decision | Why | Alternatives Considered |
|------|----------|-----|------------------------|
| 2026-05-13 | Microservices (6 services + FE) on monorepo | Independent scaling/deploys; per-service language fit; team can parallelize | Modular monolith (rejected: doesn't scale to 100k RPM in single process); 15+ microservices (rejected: ops overhead too high for 4 engineers) |
| 2026-05-13 | TypeScript + Python split | Best language per task; clean boundary at I/O vs compute | All-TS (rejected: weak ML libs); all-Python (rejected: weaker frontend integration) |
| 2026-05-13 | Postgres (Supabase) + ClickHouse | OLTP+OLAP separation; ClickHouse 10–100× faster on analytics; Supabase saves auth/RLS build | Postgres only (rejected: doesn't scale OLAP); Snowflake/BQ (rejected: cost); single-tenant DB per workspace (rejected: ops nightmare) |
| 2026-05-13 | Kafka via MSK | Replay, schema evolution, persistence, scale | BullMQ (rejected: user req); SQS (rejected: no ordering guarantees, weaker replay) |
| 2026-05-13 | gRPC internal, tRPC external | Type-safe; gRPC faster between services; tRPC for FE DX | REST internal (rejected: too much boilerplate); GraphQL (rejected: complexity) |
| 2026-05-13 | EKS over ECS | Industry standard; HPA + Karpenter; portability | ECS (acceptable but less ecosystem); Lambda (rejected: long-running workers don't fit) |
| 2026-05-13 | Claude (Sonnet 4.6 + Haiku 4.5) for LLM | Best analytical reasoning; prompt caching reduces cost ~30× | OpenAI (acceptable); Bedrock (revisit if AWS-native mandate hardens) |
| 2026-05-13 | RegionAdapter pattern; India first | Allow global expansion without rewriting metric engine | India-hardcoded (rejected: blocks Phase 4) |
| 2026-05-13 | CDC via Debezium for Postgres → ClickHouse | Industry-standard; runs on MSK Connect; minimal app code | Dual-write (rejected: consistency risk); periodic batch (rejected: latency too high) |
| 2026-05-13 | Supabase for Auth | Co-located with Postgres RLS; saves significant build | Cognito (rejected: weaker DX); Auth0 (rejected: cost) |
| 2026-05-17 | pgvector inside Postgres for Brand Fingerprint | Avoids separate vector DB; sufficient at our scale | Pinecone/Weaviate (rejected: operational overhead at current data volume) |
| 2026-05-17 | Per-brand AES-256-GCM encryption for OAuth tokens | Eliminates plaintext storage risk inherited from Looqus | DB-level encryption only (rejected: insufficient — DB dump still exposes tokens) |
| 2026-05-17 | Append-only Decision Log (`ai.decision_log`) | Memory is the moat; append-only preserves integrity | Mutable table (rejected: prevents reliable outcome attribution) |
| 2026-05-17 | Auto-execute kill switch + per-action consent + immutable audit | Brand-facing agentic commerce without operational risk | All-auto (rejected: outcome risk); all-manual (rejected: defeats the purpose) |
| 2026-05-17 | Cost-routed compute paradigm enforced via decorators + budgets + caps | Defends GMV-linked pricing economics | Pay-as-you-go LLM (rejected: cost runaway) |
| 2026-05-17 | Single-primitive architecture (Audience, Decision Log, Consent, Notification, Attribution, Identity) | Enables flat GMV % pricing across N channels | Per-channel stacks (rejected: N× engineering cost) |
| 2026-05-17 | Internal MCP between agents (Phase 1 month 1–3) | Standardizes agent-to-agent + external surface schema | Bespoke RPC per agent pair (rejected: doesn't compose) |
| 2026-05-17 | GoKwik treated as partner, not competitor | GoKwik has 5+ years of pincode RTO data we cannot economically rebuild | Build competing RTO product (rejected: 5-year head start to overcome) |
| 2026-05-17 | Brain is a global product from line 1, sequenced India-first | User clarification: target = all DTC brands globally; India is the focus, not the limit | India-only (rejected: blocks long-term TAM); US-first (rejected: crowded competitive landscape, no defensible moat as 12th US analytics tool) |
| 2026-05-17 | Full DTC spectrum supported from launch: Small + Mid + Enterprise | User clarification: build for small AND enterprise, not just SMB | SMB-only (rejected: TAM ceiling); enterprise-only (rejected: too few logos to validate Memory Layer + cross-brand benchmarks moat) |
| 2026-05-17 | Multi-brand holding co (Model B) is GA in Phase 2, not gated to enterprise | User clarification: 1 company may have multiple DTC brands; portfolio rollups + per-Brand isolation are first-class | Build B later (rejected: blocks Pipada Capital-style holding-co customers from day 1 — and that's the founders' own situation) |
| 2026-05-17 | Enterprise Variant (Model D) features ship across Phase 2/3/4, not all-at-Phase-4 | User clarification: enterprise customers should not have to wait for the full Phase 4 build | Phase 4 lock (rejected: blocks early enterprise revenue + reference logos); Phase 0 ship (rejected: features like BYO-VPC require hardened CDK + customer runbooks that aren't ready) |
| 2026-05-17 | Per-Brand signup → onboarding → dashboard isolation; same email can hold different roles in different Brands | Standard SaaS multi-tenancy pattern with Org → Brand → User hierarchy | Single global dashboard (rejected: violates data isolation); per-User pricing (rejected: penalizes team additions) |

---

## 44. Glossary

| Term | Meaning |
|------|---------|
| **AICMO / AICOO / AICFO** | Marketing / Operations / Finance executive agent groups |
| **aMER** | Acquisition Marketing Efficiency Ratio = New Customer Revenue / Acquisition Ad Spend |
| **BFF** | Backend for Frontend — service that aggregates other services for one UI (api-gateway is the BFF) |
| **BG/NBD** | Beta Geometric / Negative Binomial Distribution — LTV probabilistic model |
| **CDC** | Change Data Capture — streaming DB changes as events (Debezium on MSK Connect for Postgres → ClickHouse) |
| **CM1 / CM2 / CM3** | Contribution Margin 1/2/3 — see Section 14.3 |
| **EKS** | Elastic Kubernetes Service |
| **ECR** | Elastic Container Registry |
| **EWMA** | Exponentially Weighted Moving Average — used for creative fatigue detection |
| **HPA** | Horizontal Pod Autoscaler (Kubernetes) |
| **Karpenter** | Kubernetes node autoscaler (AWS open-source) |
| **MCP** | Model Context Protocol — Anthropic's open standard for AI agent access to systems |
| **MER** | Marketing Efficiency Ratio = Net Revenue / Marketing Spend (all channels) |
| **Materialized view** | ClickHouse aggregate refreshed on insert |
| **MSK** | Managed Streaming for Kafka (AWS) |
| **OLAP** | Online Analytical Processing — ClickHouse workload |
| **OLTP** | Online Transaction Processing — Postgres workload |
| **P40 / P80** | Percentile-based At-Risk / Churned thresholds derived from brand's order gaps |
| **pgvector** | Postgres extension for vector similarity (cosine) used in Memory Layer |
| **PgBouncer** | Postgres connection pooler (transaction mode for scale) |
| **RegionAdapter** | Pluggable region-specific economics (RTO/GST/COD/Pincode/Festival) |
| **RFM / RFMC** | Recency-Frequency-Monetary segmentation; RFMC adds COD-behaviour dimension (India-specific) |
| **RLS** | Row-Level Security (Postgres feature) |
| **SES** | Simple Email Service (AWS) |
| **tRPC** | Type-safe RPC framework for TS frontend ↔ TS backend |
| **Topic** | Kafka stream of events; partitioned by workspace_id |
| **Workspace** | A single brand's tenancy in Brain — unit of pricing, billing, isolation |

---

*End of BRAIN_TECHNICAL.md*
*Sources reconciled: PROJECT_SCOPE.md (Looqus audit, 2026-05-04), TECHNICAL_ARCHITECTURE.md (Looqus audit, 2026-05-04), brain-platform-complete-spec.md (March 2026), Brain-Technical-Brief.docx (May 2026), Technical Document.pdf (2026-05-13), Technical Document.md (2026-05-13).*
*Companion: BRAIN_BUSINESS.md*

