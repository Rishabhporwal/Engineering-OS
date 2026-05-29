---
name: architecture-patterns
description: Brain's locked architecture — microservices on a monorepo, event-driven (Kafka), BFF, MCP server, DDD internals, Single-Primitive Rule, 7 services, the 15 invariants.
---

# Architecture Patterns — Brain

## Brain's locked pattern (TECH §1)

- **Microservices on monorepo** — 7 backend services + web + mobile (Turborepo only; never Nx)
- **DDD service internals** — every service organized by bounded context, never technical layer (see `domain-driven-design`)
- **Event-driven (Kafka primary)** — MSK + Glue Schema Registry; `integrations.*.v1` with infinite retention
- **BFF at the edge** — api-gateway aggregates downstream via gRPC; serves tRPC to web + mobile
- **MCP server inside api-gateway** — same auth + multi-tenancy as tRPC
- **Contract-first** — `protos/` is the single source of truth for all internal contracts + MCP tool schemas
- **OLTP / OLAP split** — Supabase Postgres + ClickHouse Cloud; analytics isolated in data-platform/
- **CDC** — Debezium on MSK Connect for Postgres → Kafka where downstream wants recent OLTP mirror
- **IaC** — AWS CDK + ArgoCD (NOT Terraform, NOT Helm); observability on CloudWatch/X-Ray/OpenSearch (NOT Prometheus/Grafana)

**Pattern is locked.** Don't re-evaluate; raise an explicit architecture decision if proposing a change.

## The 15 strict rules (invariants)

**Never:** (1) build a monolith; (2) share a database across services; (3) put business logic in the frontend; (4) do AI orchestration in api-gateway (agents live in intelligence-service); (5) run analytics in frontend-facing services.

**Always:** (6) apply DDD (`domain-driven-design`); (7) keep services independently deployable; (8) design for horizontal scale (stateless; state in datastores); (9) circuit breakers on every cross-service call (`observability`); (10) be contract-first — `protos/` source of truth, `buf breaking` gates; (11) be event-driven — state changes via Kafka, sync via gRPC; (12) separate infrastructure from domain (domain imports no framework); (13) be K8s-ready — probes, graceful drain, PDB (`operational-readiness`); (14) enforce multi-tenancy — `workspace_id` at 4 layers (Postgres RLS, CH query gateway, Kafka envelope, MCP tenant check); (15) pass the cost-routing paradigm gate (`cost-routing-paradigms`).

## The Single-Primitive Rule (NON-NEGOTIABLE)

> Every cross-cutting concern is built **once** and consumed by every channel, every agent, every workflow.

Block at code review: "the email version of the audience builder" (there's ONE), "the call-specific consent flow" (ONE consent model), "the WhatsApp Decision Log" (ONE Decision Log), "a new notification service for SMS alerts" (ONE notification framework), "per-channel customer profiles" (ONE customer record).

| Primitive | Owner service |
|---|---|
| Audience builder | lifecycle-service |
| Decision Log (`ai.decision_log`) | analytics-service |
| Consent model (`consent_event`) | core-service |
| Notification framework | notifications-service |
| Attribution | analytics-service |
| Identity resolution | core-service |

Adding a new channel costs **1x** engineering (a router adapter), not Nx — the structural reason Brain's GMV % pricing math works.

## 7-service topology

```
                            CloudFront + Route 53 → ALB
                            ┌───────┴─────────┐
                            │   api-gateway   │  (Node/Fastify; tRPC + MCP + WS/SSE; BFF)
                            └───────┬─────────┘ gRPC
   ┌────────────────┬──────────────┼──────────────────┬─────────────────┐
┌──▼─────────┐ ┌────▼───────────┐ ┌▼──────────────┐ ┌─▼───────────────┐
│ core (Node)│ │ analytics (Py) │ │ intelligence  │ │ notifications   │
│ OLTP SoR:  │ │ Metric engine, │ │ (Py)          │ │ (Node)          │
│ workspace, │ │ ClickHouse MVs,│ │ 15 agents,    │ │ Email, Slack,   │
│ goals,     │ │ Decision Log,  │ │ Memory Layer, │ │ WhatsApp tx,    │
│ integrations│ │ India Region- │ │ Prophet,Claude│ │ push, in-app,   │
│ consent    │ │ Adapter        │ │ MCP tools,    │ │ exports         │
└────────────┘ └────────────────┘ │ Morning Brief │ └─────────────────┘
                                   └───────────────┘
        ┌──────────────────┐              ┌──────────────────────┐
        │ ingestion (Py)   │              │ lifecycle (Node + Py) │
        │ Shopify, Meta,   │              │ RFM + audience builder│
        │ Google, Shiprocket│              │ + channel routers     │
        │ Klaviyo → Kafka  │              │ + AI calling          │
        └──────────────────┘              │ + compliance engine   │
                                          │ + inbound inbox (P3)  │
Plus 2 frontends: Next.js web (Ananya)    └──────────────────────┘
                  React Native + Expo mobile (Karan; PRIMARY surface)
```

**Realtime, background jobs, cron, and long-running workflows live INSIDE these 7 services — never as separate services:** realtime push (WS/SSE) at the edge (api-gateway / notifications fan-out); background jobs as Kafka consumers in the owning service (`event-driven-kafka`); scheduled via EventBridge Scheduler → in-service handler (the intelligence daily tick 06:55–07:15 IST is canonical); long-running multi-step as in-service use-cases (saga over Kafka with compensation).

Each service: organized by **bounded context** (`domain-driven-design`); own deploy pipeline (GitHub Actions → ECR → ArgoCD via CDK); own ECR image + EKS deployment + Kafka consumer groups; **owns its own datastore**; has a designated engineer-owner.

## Per-service DB ownership (NON-NEGOTIABLE — no shared DBs)

No service reads or writes another's datastore. Cross-service data flows via gRPC (sync) or Kafka (async) — NEVER a direct DB read.

| Service | Datastore |
|---|---|
| core-service | PostgreSQL |
| ingestion-service | PostgreSQL + S3 |
| analytics-service | ClickHouse |
| intelligence-service | PostgreSQL + **pgvector** (Memory Layer) |
| notifications-service | PostgreSQL |
| lifecycle-service | PostgreSQL |

api-gateway is stateless (BFF). A cross-service read through another service's DB is a hard violation — block at review.

## Monorepo top-level layout (Turborepo only — never Nx)

| Dir | Purpose | Maps to |
|---|---|---|
| `protos/` | Contract-first source of truth (gRPC + MCP schemas) | `grpc-buf` |
| `schemas/` | Avro event schemas | `event-driven-kafka` |
| `kafka/` | Topic + consumer-group conventions | `event-driven-kafka` |
| `ai/` | Versioned prompts, guardrails, evals, RAG, embeddings, orchestration | `agentic-design` |
| `data-platform/` | dbt + Airflow/Dagster + Spark, isolated from OLTP | `clickhouse-olap` |
| `monitoring/` | CloudWatch + X-Ray dashboards + OpenSearch monitors (NOT Grafana/Loki/Tempo) | `observability` |
| `security/` | Threat models, IAM templates, India compliance gates | `security-baseline` |
| `deployments/` | ArgoCD apps + Kustomize overlays (GitOps) | `devops-aws` |
| `tests/` | Cross-service / E2E / load (k6) | `testing-tdd` |

Plus `infra/` — **AWS CDK** stacks (NOT Terraform; NOT Helm).

## Communication rules (NON-NEGOTIABLE)

| From → To | Mechanism |
|---|---|
| frontend (web/mobile) → backend | **ONLY** api-gateway (tRPC/MCP; WS/SSE push at the gateway). Nothing else. |
| api-gateway → services | gRPC (BFF fan-out) |
| service → service | Kafka events (async state changes) — never a direct DB read |
| long-running multi-step | in-service use-cases (saga over Kafka with compensation) |
| scheduled / recurring | EventBridge Scheduler → in-service handler |

The frontend never touches core/analytics/intelligence/notifications/lifecycle directly.

## Why microservices + monorepo, and two languages (TECH §2)

**Microservices:** independent scaling (ingestion 20 pods, intelligence 2); failure isolation (a hung Claude call doesn't block the dashboard); per-service language fit; independent deploys. **Monorepo:** shared types (protobuf + TS packages); atomic refactors; single CI; IaC + docs + migrations alongside code.

**TypeScript:** api-gateway, core, notifications, lifecycle Node side, web, mobile. **Python:** ingestion, analytics, intelligence, lifecycle Python side (ETL, data math, forecasting, Claude SDK). Boundary enforced: **TS services don't do heavy math; Python services don't serve latency-critical user paths.**

## Communication patterns

- **Synchronous:** `Web/Mobile → tRPC → api-gateway → gRPC → backend`. `buf generate` produces TS + Python clients (`grpc-buf`).
- **Asynchronous:** `ingestion → Kafka producer → integrations.*.v1 → analytics consumer → ClickHouse MV → analytics emits analytics.metrics.daily_materialized.v1 → intelligence + notifications consume`. Every envelope carries `workspace_id`; partition key IS `workspace_id` (`event-driven-kafka`).
- **Agent surface (MCP):** external MCP clients + Brain agents → api-gateway MCP server → gRPC to backend; Decision Log auto-write on every write tool (`mcp-protocol`).

## Quarterly streamlining audit

Each quarter: review for anti-pattern drift; flag duplication of cross-cutting concerns; document any paradigm-bypass (LLM where ML would have worked — `cost-routing-paradigms`); **refactoring time allocated explicitly** next quarter — not optional.

## When tempted to break the pattern

- "Just one more service" — only with an ADR + a clear bounded context + per-service owner.
- "Add a queue/pub-sub alongside Kafka" — no; background jobs are Kafka consumers inside the owning service.
- "Refactor api-gateway out so frontend talks to services directly" — no; the frontend has exactly one edge (rate limiting, fan-out, MCP, WS/SSE all live there).
- "Organize this service by controllers/services/models" — no; bounded context (`domain-driven-design`).

## Brainstorm personas (Aryan in design)

- **Vikram (Node):** "Under 100ms p95? Can tRPC fan-out hit all downstreams without serial waits?"
- **Maya (data plane):** "Where does this enter Kafka? Idempotency key? Replay-safe? Metric registry entry, workspace_id-first MV, freshness SLA? Which paradigm, token budget, fallback? Audience, channel router, compliance gate, 48h cap?"
- **Ananya (web):** "Drill-down path? Empty/loading/error states? Mobile responsive or desktop-only?"
- **Karan (mobile):** "Morning Brief impact? Push? Deep link? Tamagui token coverage?"
- **Jatin (platform):** "Pod sizing? MSK partition count? Cost delta? Auto-rollback alarm? New ArgoCD app?"
- **Shreya (security):** "workspace_id at every layer? MCP scope? Secrets Manager? India compliance gate?"

## Common failure modes

- **Re-evaluating a locked pattern** — the stack is locked; don't re-litigate without an explicit decision.
- **Per-channel forks (Single-Primitive violation)** — block at review.
- **Sync-via-Kafka antipattern** — Kafka for state changes, gRPC for request/response.
- **Cross-service DB reads** — always go through gRPC or published events.
- **Forgetting workspace_id in the event envelope** — downstream can't partition or scope.
- **New service without bounded context** — ADR required.

## References

- `canon/technical-requirements.md` — service map + scale design, Single-Primitive Rule, quarterly audit, MCP topology
- `canon/TECH/18_service_architecture.md` — per-service operational spec (boundaries, modules, comms, data flow, scale, failure)
- Related: `domain-driven-design`, `grpc-buf`, `event-driven-kafka`, `mcp-protocol`, `devops-aws`, `observability`, `cost-routing-paradigms`
