---
name: architecture-patterns
description: Brain's architecture patterns — Microservices + Monorepo + Event-Driven (Kafka primary) + BFF (api-gateway) + MCP server + DDD service internals. The Single-Primitive Rule (every cross-cutting concern built once, consumed N times). 7 services (api-gateway, core, ingestion, analytics, intelligence, notifications, lifecycle) + Next.js web + React Native + Expo mobile. Per-service DB ownership; the 15 strict rules; communication rules (frontend→api-gateway only). Auto-load when Aryan is reviewing service boundaries, DB ownership, or when a PR triggers a Single-Primitive / DDD concern (anti-pattern detection).
---

# Architecture Patterns — Brain

## Brain's locked pattern (TECH §1)

- **Microservices on monorepo** — 7 backend services + web + mobile (Turborepo only; never Nx)
- **DDD service internals** — every service organized by bounded context, never by technical layer (see `domain-driven-design`)
- **Event-driven (Kafka primary)** — MSK + Glue Schema Registry; `integrations.*.v1` with infinite retention
- **BFF at the edge** — api-gateway aggregates downstream via gRPC; serves tRPC to web + mobile
- **MCP server inside api-gateway** — same auth + multi-tenancy as tRPC (see canon/BRAIN_TECHNICAL.md)
- **Contract-first** — `proto/` is the single source of truth for all internal contracts + MCP tool schemas
- **OLTP / OLAP split** — Supabase Postgres + ClickHouse Cloud; analytics isolated in data-platform/
- **CDC** — Debezium on MSK Connect for Postgres → Kafka where downstream wants recent OLTP mirror
- **IaC** — AWS CDK + ArgoCD (NOT Terraform, NOT Helm); observability on CloudWatch/X-Ray/OpenSearch (NOT Prometheus/Grafana)

**Pattern is locked.** Don't re-evaluate; see canon/BRAIN_TECHNICAL.md and raise an explicit architecture decision if you're proposing a change.

## The 15 strict rules (architecture invariants)

**Never:**
1. Build a monolith — every capability is an independently deployable service
2. Share a database across services — no service touches another's DB (see ownership table below)
3. Put business logic in the frontend — the frontend renders; logic lives in services
4. Do AI orchestration in api-gateway — agents live in intelligence-service; the gateway is a BFF
5. Run analytics in frontend-facing services — OLAP is isolated (ClickHouse + data-platform/)

**Always:**
6. Apply DDD — organize each service by bounded context, never controllers/services/models (`domain-driven-design`)
7. Keep services independently deployable
8. Design for horizontal scale (stateless services; state in datastores)
9. Use circuit breakers on every cross-service call (`observability`)
10. Be contract-first — `proto/` is the source of truth; `buf breaking` gates changes
11. Be event-driven — state changes flow via Kafka; sync via gRPC
12. Separate infrastructure from domain — domain code imports no framework (`domain-driven-design`)
13. Be K8s-ready — health/liveness/readiness probes, graceful drain, PDB (`health-check-endpoints`)
14. Enforce multi-tenancy — `workspace_id` at 4 layers (Postgres RLS, CH query gateway, Kafka envelope, MCP tenant check)
15. Pass the cost-routing paradigm gate on every new path (`cost-routing-paradigms`)

## The Single-Primitive Rule (NON-NEGOTIABLE — see canon/BRAIN_TECHNICAL.md)

> Every cross-cutting concern is built **once** and consumed by every channel, every agent, every workflow.

Block at code review if you see:
- "The email version of the audience builder" — there's ONE audience builder
- "The call-specific consent flow" — there's ONE consent model
- "The WhatsApp Decision Log" — there's ONE Decision Log
- "A new notification service for SMS alerts" — there's ONE notification framework
- "Per-channel customer profiles" — there's ONE customer record

Single primitives + owners:

| Primitive | Owner service |
|---|---|
| Audience builder | lifecycle-service |
| Decision Log (`ai.decision_log`) | analytics-service |
| Consent model (`consent_event`) | core-service |
| Notification framework | notifications-service |
| Attribution | analytics-service |
| Identity resolution | core-service |

Adding a new channel costs **1x** engineering (a router adapter), not Nx. That's the structural reason Brain's GMV % pricing math works.

## 7-service topology

```
                            CloudFront + Route 53
                                    │
                                   ALB
                                    │
                            ┌───────┴─────────┐
                            │   api-gateway   │  (Node/Fastify; tRPC + MCP + WS/SSE; BFF)
                            └───────┬─────────┘
                                    │ gRPC
        ┌───────────────────────────┼──────────────────────────────────────┐
        │                           │                                       │
┌───────▼────────┐  ┌───────────────▼──────┐  ┌────────────────┐  ┌────────▼────────┐
│ core-service   │  │ analytics-service    │  │ intelligence-  │  │ notifications-  │
│ (Node)         │  │ (Python)             │  │ service        │  │ service         │
│                │  │                      │  │ (Python)       │  │ (Node)          │
│ OLTP system    │  │ Metric engine,       │  │ 15 agents,     │  │ Email, Slack,   │
│ of record:     │  │ ClickHouse MVs,      │  │ Memory Layer,  │  │ WhatsApp tx,    │
│ workspace,     │  │ Decision Log,        │  │ Prophet,       │  │ push, in-app,   │
│ goals,         │  │ India RegionAdapter  │  │ Claude,        │  │ exports         │
│ integrations,  │  │                      │  │ MCP tools,     │  │                 │
│ consent        │  │                      │  │ Morning Brief  │  │                 │
└────────────────┘  └──────────────────────┘  │ Synthesizer    │  └─────────────────┘
                                              └────────────────┘
                                                       │
                       ┌───────────────────────────────┴─────────────────────┐
                       │                                                      │
              ┌────────▼─────────┐                              ┌────────────▼─────────┐
              │ ingestion-       │                              │ lifecycle-service    │
              │ service          │                              │ (Node + Python)       │
              │ (Python)         │                              │                       │
              │ Shopify, Meta,   │                              │ RFM + audience builder│
              │ Google, Shiprocket│                              │ + channel routers     │
              │ Klaviyo          │                              │ + AI calling          │
              │ → Kafka          │                              │ + compliance engine   │
              └──────────────────┘                              │ + inbound inbox       │
                                                                │ (Phase 3)             │
                                                                └───────────────────────┘

Plus 2 frontends:
  Next.js web (workbench — Ananya)
  React Native + Expo mobile (Morning Brief — Karan; PRIMARY surface)
```

**Realtime, background jobs, cron, and long-running workflows are handled INSIDE these 7 services — never as separate dedicated services:**
- **Realtime push (WS/SSE)** — served at the edge by api-gateway (or by notifications-service for delivery fan-out).
- **Background jobs / async execution** — Kafka consumers inside the owning service handle retries, DLQ, and idempotency keys (`event-driven-kafka`).
- **Scheduled / recurring / delayed** — EventBridge Scheduler triggers an in-service handler; the intelligence-service daily tick (06:55–07:15 IST) is the canonical example.
- **Long-running multi-step workflows** — modeled as in-service application/use-cases (saga over Kafka with compensation) within the owning bounded context.

Each service:
- Is organized internally by **bounded context, never technical layer** (`domain-driven-design`)
- Has its own deploy pipeline (GitHub Actions → ECR → ArgoCD via AWS CDK)
- Has its own ECR image + EKS deployment + Kafka consumer group(s)
- **Owns its own datastore — no shared DBs** (table below)
- Has its own designated engineer-owner (see canon/BRAIN_TECHNICAL.md ownership matrix)

## Per-service DB ownership (NON-NEGOTIABLE — no shared DBs)

No service reads or writes another service's datastore. Cross-service data flows via gRPC (sync) or Kafka events (async) — NEVER a direct DB read.

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

Beyond `apps/<service>/`, the monorepo has these top-level dirs:

| Dir | Purpose | Maps to |
|---|---|---|
| `proto/` | **Contract-first source of truth** — gRPC + MCP tool schemas | `grpc-buf` (buf codegen → TS + Python) |
| `schemas/` | Avro event schemas | Glue Schema Registry (`event-driven-kafka`) |
| `kafka/` | Topic + consumer-group conventions | `event-driven-kafka` |
| `ai/` | Versioned/testable/evaluated prompts, guardrails, evaluations, RAG, embeddings, orchestration | `agentic-design` |
| `data-platform/` | dbt + Airflow/Dagster + Spark — analytics DAGs, isolated from OLTP | `clickhouse-olap` |
| `monitoring/` | CloudWatch + X-Ray dashboards + OpenSearch monitors (NOT Grafana/Loki/Tempo) | `observability` |
| `security/` | Threat models, IAM policy templates, India compliance gates | `security-baseline` |
| `deployments/` | ArgoCD apps + Kustomize overlays (GitOps) | `devops-aws` |
| `tests/` | Cross-service / E2E / load (k6) suites | `testing-tdd` |

Plus `infra/` — **AWS CDK** stacks (NOT Terraform; NOT Helm). `monitoring/` maps to CloudWatch/X-Ray dashboards, NOT Prometheus/Grafana.

## Communication rules (NON-NEGOTIABLE)

| From → To | Mechanism |
|---|---|
| frontend (web/mobile) → backend | **ONLY** api-gateway (tRPC/MCP request-response; WS/SSE push served at the gateway). Nothing else. |
| api-gateway → services | gRPC (BFF fan-out) |
| service → service | Kafka events (async state changes) — never a direct DB read |
| long-running multi-step | in-service application/use-cases (saga over Kafka with compensation) in the owning bounded context |
| scheduled / recurring | EventBridge Scheduler → in-service handler (e.g. intelligence-service daily tick) |

The frontend never touches core/analytics/intelligence/notifications/lifecycle directly — that's what the single edge (api-gateway) is for.

## Why microservices + monorepo (TECH §2)

**Microservices** because:
- Independent scaling: ingestion runs 20 pods, intelligence runs 2
- Failure isolation: hung Claude call doesn't block the dashboard
- Per-service language fit: Node for I/O-heavy edge work; Python for ETL + math + ML
- Independent deploys: ship a metrics fix without redeploying intelligence

**Monorepo** because:
- Shared types (protobuf for cross-language contracts; TS packages for cross-TS contracts)
- Atomic refactors across services
- Single CI pipeline orchestrates
- IaC + docs + migrations live alongside service code

## Why two languages (TECH §2)

- **TypeScript:** api-gateway, core-service, notifications-service, lifecycle-service Node side, web, mobile. Strong I/O ecosystem; type safety with frontend.
- **Python:** ingestion-service, analytics-service, intelligence-service, lifecycle-service Python side. Best ecosystem for ETL (httpx, aiokafka), data math (numpy, pandas), forecasting (Prophet, statsmodels), and Claude SDK.

Boundary enforced: **TS services don't do heavy math; Python services don't serve user-facing latency-critical paths.**

## Communication patterns

### Synchronous — gRPC internal + tRPC edge

```
Web/Mobile → tRPC → api-gateway → gRPC → backend service
```

`buf generate` produces TS + Python clients from `protos/*.proto`. See `skills/grpc-buf/SKILL.md`.

### Asynchronous — Kafka (MSK + Glue + Avro)

```
ingestion-service → Kafka producer → integrations.*.v1
                                          ↓
                              analytics-service consumer
                                          ↓
                              ClickHouse materialized view
                                          ↓
                              analytics emits → analytics.metrics.daily_materialized.v1
                                          ↓
                              intelligence-service + notifications-service consume
```

Every Kafka envelope carries `workspace_id`; partition key IS `workspace_id`. See `skills/event-driven-kafka/SKILL.md`.

### Agent surface — MCP

```
External MCP clients (Claude, partners) ──┐
                                          ▼
Brain agents (intelligence-service)  →  api-gateway MCP server  →  gRPC to backend services
   (acting as MCP clients to call                                       ↓
    memory.*, analytics.*, etc.)                                Decision Log auto-write on every write tool
```

See `skills/mcp-protocol/SKILL.md`.

## Quarterly streamlining audit (see canon/BRAIN_TECHNICAL.md)

Every quarter:
- Review codebase for anti-pattern drift
- Flag duplication of cross-cutting concerns
- Document any paradigm-bypass (LLM where ML would have worked — see `cost-routing-paradigms` skill)
- **Refactoring time allocated explicitly** in next quarter — not optional

## When you're tempted to break the pattern

- "Just one more service" — but only with an ADR + a clear bounded context + per-service owner assigned
- "Let's add a queue / pub-sub library alongside Kafka" — Kafka is primary for async; background jobs are Kafka consumers inside the owning service. Don't introduce a new broker.
- "Let's refactor api-gateway out so frontend talks to services directly" — no. The frontend has exactly one edge: api-gateway. BFF is intentional: rate limiting, fan-out aggregation, MCP surface, and live WS/SSE push all live there.
- "Let's organize this service by controllers/services/models" — no. Every service is organized by bounded context (`domain-driven-design`).

## Brainstorm personas (Aryan invokes these in design)

When Aryan designs, he invokes peers as personas:

- **Vikram (Node backend):** "Does this stay under 100ms p95? Can tRPC fan-out hit all downstreams without serial waits?"
- **Maya (ingestion / analytics / intelligence / lifecycle):** "Where does this enter Kafka? What's the idempotency key? Replay-safe? Metric registry entry, `workspace_id`-first MV, freshness SLA? Which paradigm, token budget, fallback when budget breaks? Audience, channel router, compliance gate, 48h frequency cap?"
- **Ananya (web):** "Drill-down path? Empty / loading / error states? Mobile responsive — or desktop-only territory?"
- **Karan (mobile):** "Morning Brief impact? Push notification? Deep link? Tamagui token coverage?"
- **Jatin (platform):** "Pod sizing? MSK partition count? Cost delta? Auto-rollback alarm? New ArgoCD app?"
- **Shreya (security):** "Multi-tenant — `workspace_id` at every layer? MCP scope? Secrets Manager? India compliance gate?"

## Common failure modes

- **Re-evaluating a locked pattern** — Aryan opens a "should we use microservices?" debate. The stack is locked (see canon/BRAIN_TECHNICAL.md); don't re-litigate without an explicit architecture decision.
- **Per-channel forks (Single-Primitive violation)** — block at code review.
- **Sync-via-Kafka antipattern** — using Kafka for request/response. Use gRPC for synchronous, Kafka for state changes.
- **Cross-service DB reads** — service A queries service B's database directly. Always go through gRPC or published events.
- **Forgetting workspace_id in event envelope** — downstream can't partition or scope.
- **New service without bounded context** — splitting a service "because it's getting big" without a clear domain boundary creates ops overhead without engineering benefit. ADR required.

## References

- `canon/BRAIN_TECHNICAL.md` — service map + scale design, Single-Primitive Rule, quarterly streamlining audit, MCP topology
- `skills/domain-driven-design/SKILL.md` — mandatory service-internal structure (bounded contexts, CQRS, tactical patterns)
- `skills/grpc-buf/SKILL.md` — gRPC + proto patterns (proto/ is contract-first source of truth)
- `skills/event-driven-kafka/SKILL.md` — Kafka topology
- `skills/mcp-protocol/SKILL.md` — MCP server design
- `skills/devops-aws/SKILL.md` — AWS CDK + ArgoCD (infra/ + deployments/)
- `skills/observability/SKILL.md` — CloudWatch/X-Ray dashboards (monitoring/) + circuit breakers
- `skills/cost-routing-paradigms/SKILL.md` — paradigm gate
