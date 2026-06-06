---
name: architecture-patterns
description: A reference microservices-on-monorepo architecture — event-driven (Kafka), BFF, MCP server, DDD internals, the Single-Primitive Rule, per-service DB ownership, locked-pattern discipline.
---

# Architecture Patterns

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md` and `engineering-os-blueprint/04-architecture-and-decisions.md`). The OS is stack-agnostic — your product's `STACK.md` / HLD bind these seams to whatever the product needs. The *patterns* here (microservices-on-monorepo, event-driven, BFF, DDD internals, Single-Primitive Rule, per-service DB ownership, locked-pattern discipline) are what transfer, not the specific service map below.

## The locked pattern (this reference binding; see `STACK.md` / HLD for the product's)

- **Microservices on monorepo** — backend services + web + mobile (one monorepo runner; pick one and stick to it)
- **DDD service internals** — every service organized by bounded context, never technical layer (see `domain-driven-design`)
- **Event-driven (Kafka primary)** — managed Kafka + a schema registry; `<domain>.*.v1` topics with long/infinite retention
- **BFF at the edge** — an api-gateway aggregates downstream via gRPC; serves tRPC to web + mobile
- **MCP server inside api-gateway** — same auth + multi-tenancy as tRPC
- **Contract-first** — `protos/` is the single source of truth for all internal contracts + MCP tool schemas
- **OLTP / OLAP split** — a transactional store (Postgres) + an analytical store (ClickHouse); analytics isolated in `data-platform/`
- **CDC** — change-data-capture (Debezium) onto Kafka where a downstream wants a recent OLTP mirror
- **IaC + GitOps** — infrastructure as code + a GitOps deploy controller; observability on a chosen spine

**The pattern, once chosen, is locked.** Don't re-evaluate ad hoc; raise an explicit architecture decision (ADR) if proposing a change.

## The strict rules (invariants — the product's binding live in `INVARIANTS.md`)

**Never:** (1) build a monolith; (2) share a database across services; (3) put business logic in the frontend; (4) do model/agent orchestration in the api-gateway (agents live in the intelligence service); (5) run analytics in frontend-facing services.

**Always:** (6) apply DDD (`domain-driven-design`); (7) keep services independently deployable; (8) design for horizontal scale (stateless; state in datastores); (9) circuit breakers on every cross-service call (`observability`); (10) be contract-first — `protos/` source of truth, `buf breaking` gates; (11) be event-driven — state changes via Kafka, sync via gRPC; (12) separate infrastructure from domain (domain imports no framework); (13) be deploy-target-ready — health probes, graceful drain, disruption budgets (`operational-readiness`); (14) enforce multi-tenancy — the tenant key at every layer (data-store RLS, OLAP query gateway, event envelope, MCP tenant check); (15) pass the cost-routing paradigm gate (`cost-routing-paradigms`).

## The Single-Primitive Rule (NON-NEGOTIABLE)

> Every cross-cutting concern is built **once** and consumed by every channel, every agent, every workflow.

Block at code review: "the email version of the audience builder" (there's ONE), "the call-specific consent flow" (ONE consent model), "the per-channel audit log" (ONE audit log), "a new notification service for SMS alerts" (ONE notification framework), "per-channel customer profiles" (ONE customer record).

| Primitive | Owner service (example) |
|---|---|
| Audience builder | lifecycle-service |
| Audit log (system-of-record, where the Canon requires one) | analytics-service |
| Consent model (`consent_event`) | core-service |
| Notification framework | notifications-service |
| Attribution | analytics-service |
| Identity resolution | core-service |

Adding a new channel costs **1x** engineering (a router adapter), not Nx — the structural reason a usage-based pricing model can work.

## Service topology (this reference binding)

```
                            CDN + DNS → load balancer
                            ┌───────┴─────────┐
                            │   api-gateway   │  (Node/Fastify; tRPC + MCP + WS/SSE; BFF)
                            └───────┬─────────┘ gRPC
   ┌────────────────┬──────────────┼──────────────────┬─────────────────┐
┌──▼─────────┐ ┌────▼───────────┐ ┌▼──────────────┐ ┌─▼───────────────┐
│ core (Node)│ │ analytics (Py) │ │ intelligence  │ │ notifications   │
│ OLTP SoR:  │ │ Metric engine, │ │ (Py)          │ │ (Node)          │
│ tenants,   │ │ OLAP MVs,      │ │ agents,       │ │ Email, Slack,   │
│ goals,     │ │ audit log,     │ │ memory store, │ │ messaging,      │
│ integrations│ │ RegionAdapter  │ │ forecasting,  │ │ push, in-app,   │
│ consent    │ │                │ │ model SDK,    │ │ exports         │
└────────────┘ └────────────────┘ │ MCP tools     │ └─────────────────┘
                                   └───────────────┘
        ┌──────────────────┐              ┌──────────────────────┐
        │ ingestion (Py)   │              │ lifecycle (Node + Py) │
        │ source connectors│              │ segmentation + audience│
        │ → Kafka          │              │ builder + channel      │
        │                  │              │ routers + compliance   │
        └──────────────────┘              │ engine + inbound inbox │
                                          └──────────────────────┘
Plus 2 frontends: web (Frontend/Web Engineer)
                  mobile (Mobile Engineer; primary surface where the product is mobile-first)
```

**Realtime, background jobs, cron, and long-running workflows live INSIDE these services — never as separate services:** realtime push (WS/SSE) at the edge (api-gateway / notifications fan-out); background jobs as Kafka consumers in the owning service (`event-driven-kafka`); scheduled via a scheduler → in-service handler; long-running multi-step as in-service use-cases (saga over Kafka with compensation).

Each service: organized by **bounded context** (`domain-driven-design`); own deploy pipeline (CI → image registry → GitOps controller); own image + deployment + Kafka consumer groups; **owns its own datastore**; has a designated engineer-owner.

## Per-service DB ownership (NON-NEGOTIABLE — no shared DBs)

No service reads or writes another's datastore. Cross-service data flows via gRPC (sync) or Kafka (async) — NEVER a direct DB read.

| Service | Datastore (example) |
|---|---|
| core-service | PostgreSQL |
| ingestion-service | PostgreSQL + object storage |
| analytics-service | ClickHouse |
| intelligence-service | PostgreSQL + a vector index (memory store) |
| notifications-service | PostgreSQL |
| lifecycle-service | PostgreSQL |

api-gateway is stateless (BFF). A cross-service read through another service's DB is a hard violation — block at review.

## Monorepo top-level layout (one runner — never mix two)

| Dir | Purpose | Maps to |
|---|---|---|
| `protos/` | Contract-first source of truth (gRPC + MCP schemas) | `grpc-buf` |
| `schemas/` | Event schemas | `event-driven-kafka` |
| `kafka/` | Topic + consumer-group conventions | `event-driven-kafka` |
| `ai/` | Versioned prompts, guardrails, evals, RAG, embeddings, orchestration | `examples/brain-instantiation/` |
| `data-platform/` | dbt + orchestration + batch, isolated from OLTP | `clickhouse-olap` |
| `monitoring/` | Dashboards + monitors (one observability spine, not a mix) | `observability` |
| `security/` | Threat models, IAM templates, compliance gates | `security-baseline` |
| `deployments/` | GitOps apps + overlays | `devops-aws` |
| `tests/` | Cross-service / E2E / load | `testing-tdd` |

Plus `infra/` — infrastructure-as-code stacks.

## Communication rules (NON-NEGOTIABLE)

| From → To | Mechanism |
|---|---|
| frontend (web/mobile) → backend | **ONLY** api-gateway (tRPC/MCP; WS/SSE push at the gateway). Nothing else. |
| api-gateway → services | gRPC (BFF fan-out) |
| service → service | Kafka events (async state changes) — never a direct DB read |
| long-running multi-step | in-service use-cases (saga over Kafka with compensation) |
| scheduled / recurring | scheduler → in-service handler |

The frontend never touches backend services directly.

## Why microservices + monorepo, and two languages

**Microservices:** independent scaling (ingestion many pods, intelligence few); failure isolation (a hung model call doesn't block the dashboard); per-service language fit; independent deploys. **Monorepo:** shared types (protobuf + TS packages); atomic refactors; single CI; IaC + docs + migrations alongside code.

**TypeScript** for latency-critical user-facing services (api-gateway, core, notifications, lifecycle Node side, web, mobile); **Python** for data-heavy services (ingestion, analytics, intelligence, lifecycle Python side — ETL, data math, forecasting, model SDK). Boundary enforced: **TS services don't do heavy math; Python services don't serve latency-critical user paths.**

## Communication patterns

- **Synchronous:** `Web/Mobile → tRPC → api-gateway → gRPC → backend`. `buf generate` produces TS + Python clients (`grpc-buf`).
- **Asynchronous:** `ingestion → Kafka producer → <domain>.*.v1 → analytics consumer → OLAP MV → analytics emits a materialized-metrics event → intelligence + notifications consume`. Every envelope carries the tenant key; the partition key IS the tenant key (`event-driven-kafka`).
- **Agent surface (MCP):** external MCP clients + the product's agents → api-gateway MCP server → gRPC to backend; an audit-log write on every write tool, where the Canon requires one (`mcp-protocol`).

## Quarterly streamlining audit

Each quarter: review for anti-pattern drift; flag duplication of cross-cutting concerns; document any paradigm-bypass (a large model where a cheaper method would have worked — `cost-routing-paradigms`); **refactoring time allocated explicitly** next quarter — not optional.

## When tempted to break the pattern

- "Just one more service" — only with an ADR + a clear bounded context + per-service owner.
- "Add a queue/pub-sub alongside Kafka" — no; background jobs are Kafka consumers inside the owning service.
- "Refactor api-gateway out so frontend talks to services directly" — no; the frontend has exactly one edge (rate limiting, fan-out, MCP, WS/SSE all live there).
- "Organize this service by controllers/services/models" — no; bounded context (`domain-driven-design`).

## Brainstorm lenses (the Architect in design)

- **Backend (Node):** "Under 100ms p95? Can the tRPC fan-out hit all downstreams without serial waits?"
- **Data plane:** "Where does this enter Kafka? Idempotency key? Replay-safe? Metric-registry entry, tenant-first MV, freshness SLA? Which paradigm, token budget, fallback? Audience, channel router, compliance gate?"
- **Web:** "Drill-down path? Empty/loading/error states? Mobile responsive or desktop-only?"
- **Mobile:** "Primary-surface impact? Push? Deep link? Design-token coverage?"
- **Platform:** "Pod sizing? Partition count? Cost delta? Auto-rollback alarm? New GitOps app?"
- **Security:** "Tenant key at every layer? MCP scope? Secrets manager? Compliance gate?"

## Common failure modes

- **Re-evaluating a locked pattern** — don't re-litigate without an explicit decision (ADR).
- **Per-channel forks (Single-Primitive violation)** — block at review.
- **Sync-via-Kafka antipattern** — Kafka for state changes, gRPC for request/response.
- **Cross-service DB reads** — always go through gRPC or published events.
- **Forgetting the tenant key in the event envelope** — downstream can't partition or scope.
- **New service without bounded context** — ADR required.

## References

- `engineering-os-blueprint/04-architecture-and-decisions.md` + `engineering-os-blueprint/09-reference-architecture.md` — patterns + the reference binding
- Product Canon: `STACK.md` / HLD / LLD (the product's own service map + scale design), `INVARIANTS.md`
- Related: `domain-driven-design`, `grpc-buf`, `event-driven-kafka`, `mcp-protocol`, `devops-aws`, `observability`, `cost-routing-paradigms`
