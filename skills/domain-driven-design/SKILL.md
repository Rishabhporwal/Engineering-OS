---
name: domain-driven-design
description: Brain's mandatory service-internal organization — every backend service structured by bounded context, NEVER by controllers/services/models. DDD tactical patterns, CQRS, inward-pointing layering.
---

# Domain-Driven Design — Brain Service Internals

> The internal shape of every Brain backend service. Aryan owns the structure; **every builder** (Vikram, Maya) follows it.

The **service-internal** companion to `architecture-patterns` (which governs the 7-service topology). Architecture-patterns says *which* services exist; this says *how each one is organized inside*.

## The Iron Law

```
ORGANIZE BY BOUNDED CONTEXT, NEVER BY TECHNICAL LAYER
```

A service folder is named for a **business capability** (`recovery`, `audience`, `attribution`, `consent`) — never a technical role (`controllers/`, `services/`, `models/`). If a reviewer can't tell what the business does from the directory tree, the structure is wrong.

## The mandatory service-internal structure

Every backend service — TS (Fastify) and Python (FastAPI) — uses the same skeleton:

```
service/src/
  bootstrap/          # server, container (DI), startup, config, grpc, kafka, database
  domain/<bounded-context>/   # entities, services, repositories, value-objects, dto,
                              # validators, mappers, events, policies, exceptions, factories, aggregates
  application/        # commands, queries, workflows, orchestrators, handlers, use-cases   ← CQRS
  infrastructure/     # database, repositories, kafka, grpc, cache, telemetry, external, storage
  interfaces/         # rest, grpc, consumers, producers, websocket, jobs
  observability/      # OTel wiring, metrics, health (see `observability`)
  security/           # workspace_id guard, authz, tenant scoping (see `security-baseline`)
  testing/
  main                # entrypoint
```

| Layer | Holds | May import |
|---|---|---|
| **domain/** | Pure business logic — no I/O, no framework | nothing outside domain |
| **application/** | Use-cases that orchestrate the domain (CQRS) | domain only |
| **infrastructure/** | Concrete adapters (Postgres, Kafka, gRPC, Redis, S3) | domain interfaces |
| **interfaces/** | Inbound edges (REST, gRPC, Kafka consumers, WS, jobs) | application |

**Dependency rule (the spine):** dependencies point INWARD. `interfaces → application → domain`; `infrastructure` implements `domain` interfaces (dependency inversion). Domain NEVER imports Fastify, FastAPI, asyncpg, KafkaJS, grpc-js, or any framework — that's how the moat logic (RTO/COD/GST math) stays testable in isolation.

## Bounded contexts per service (examples)

| Service | Bounded contexts (`domain/<context>/`) |
|---|---|
| core-service | `workspace`, `goals`, `integrations`, `consent`, `identity` |
| lifecycle-service | `rfm`, `audiences`, `recovery`, `compliance` |
| analytics-service | `metrics`, `attribution`, `decision-log`, `region-adapter` |
| intelligence-service | `agents`, `memory`, `recommendation`, `morning-brief` |

One context = one ubiquitous language. Brain's India-commerce vocabulary (RTO, COD, NDR, DLT, NCPR, calling-hours) lives inside the relevant context's entities + value-objects, not scattered as utility functions.

## Tactical patterns

| Pattern | Lives in | What it is |
|---|---|---|
| **Entity** | `domain/<ctx>/entities/` | Identity + lifecycle (`Audience`, `Outreach`, `Workspace`) |
| **Value Object** | `domain/<ctx>/value-objects/` | Immutable, equality-by-value (`Money` in paisa, `Pincode`, `CallingWindow`, `GstRate`) |
| **Aggregate** | `domain/<ctx>/aggregates/` | Consistency boundary; one root guards invariants; only the root is loaded/saved |
| **Repository** | `domain/<ctx>/repositories/` (interface) → `infrastructure/repositories/` (impl) | Persists aggregates; interface is domain, SQL is infrastructure |
| **Domain Event** | `domain/<ctx>/events/` | A fact the domain emits (`OutreachCompleted`) → mapped to Kafka in `interfaces/producers/` |
| **Factory** | `domain/<ctx>/factories/` | Constructs valid aggregates (invariants at birth) |
| **Policy** | `domain/<ctx>/policies/` | Encapsulated rule (`CallingHoursPolicy`, `FrequencyCapPolicy`, `RtoRiskPolicy`) |
| **Domain Service** | `domain/<ctx>/services/` | Logic that doesn't belong to one entity (cross-entity calc) |
| **Mapper** | `domain/<ctx>/mappers/` | Domain ↔ persistence row / DTO / proto |
| **Exception** | `domain/<ctx>/exceptions/` | Domain-specific failures (`OutOfCallingWindowError`) |

**Money is ALWAYS a `Money` value-object in paisa (Int64) — never a raw number.** GST, RTO cost, recovered-revenue all flow through value-objects so the India-commerce economics moat is enforced by the type system.

## CQRS — application layer

Commands mutate; queries read. They never mix.

```
application/
  commands/      # LaunchRecoveryCampaign, AdjustCampaignBudget  (write side; returns ack/id)
  queries/       # GetAudienceById, ListOutreach                  (read side; returns DTOs)
  use-cases/     # one handler per command/query
  handlers/      # wire use-cases to interfaces
  workflows/     # multi-step orchestration (saga over Kafka)
  orchestrators/ # in-process choreography across use-cases
```

A use-case loads an aggregate via a repository, calls domain methods, persists, and publishes domain events. It contains **no** business rules itself — those live in the domain. Reads can bypass the aggregate and hit a query-optimized projection (e.g. ClickHouse MV) directly.

## On Fastify (TypeScript)

```
interfaces/rest/audience.routes.ts → application/commands/launch-recovery-campaign.ts
  → domain/audience/aggregates/Audience.ts
  → domain/audience/repositories/AudienceRepository.ts (interface)
  ↑ implemented by infrastructure/repositories/PgAudienceRepository.ts
```

Fastify routes are THIN — parse/validate (Zod), call the use-case, map the result. The DI container in `bootstrap/container.ts` wires concrete repositories to domain interfaces. tRPC procedures and gRPC handlers are also `interfaces/` adapters over the same use-cases.

## On FastAPI (Python)

```
interfaces/rest/audience_router.py → application/commands/launch_recovery_campaign.py
domain/audience/aggregates/audience.py        (pure dataclasses / pydantic for VOs)
domain/audience/repositories/audience_repository.py   (Protocol / ABC)
infrastructure/repositories/pg_audience_repository.py (asyncpg impl)
```

FastAPI routers stay thin; `bootstrap/container.py` does wiring. Domain modules import **nothing** from `fastapi`, `asyncpg`, or `aiokafka`. aiokafka consumers live in `interfaces/consumers/` and translate Kafka envelopes into commands.

## The anti-pattern — STOP

The most common drift is the **technical-layer tree**:

```
✗  src/controllers/   src/services/   src/models/   src/routes/   src/utils/
```

This scatters one business capability (recovery) across five folders, makes domain logic untestable without the framework, and hides the bounded contexts. **Block at code review.**

## Red flags — STOP

- A new top-level folder named `controllers/`, `services/`, `models/`, `helpers/`, `utils/`, or `managers/`
- A domain file that imports `fastify`, `fastapi`, `asyncpg`, `kafkajs`, `grpc`, or `prisma`
- Business rules (calling-hours check, GST math, frequency cap) inside a route handler instead of a `policy` / domain method
- Raw `number` for money instead of a `Money` value-object
- A use-case that contains an `if`-ladder of business rules
- A repository returning ORM rows instead of reconstituted aggregates
- Two services sharing a `domain/` module (share via proto/events, not code)

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "controllers/services/models is the framework default" | Brain's default is bounded-context |
| "It's a small service, layers are overkill" | Small services drift into big ones; the skeleton costs nothing now |
| "The route already validates, I'll put the rule there" | Rules in routes can't be reused by the Kafka consumer or gRPC handler — Single-Primitive violation |
| "I'll use the ORM model as my entity" | ORM models couple domain to persistence; a schema change ripples into business logic |
| "Money as a number is simpler" | One missing paisa rounding = a wrong CM2 on the Founder's dashboard |
| "CQRS is enterprise bloat" | Brain already splits OLTP (write) from OLAP (read); CQRS is the in-service expression |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Service-internal structure standard | **Aryan** | this skill + `architecture-patterns` |
| TS (Fastify) service internals | **Vikram** | `backend-fastify-trpc-grpc` |
| Python (FastAPI) service internals | **Maya** | `python-services` |
| Bounded-context boundaries + ADR | Aryan | `memory/decisions/ADR-<NNN>-*.md` |
| Domain ↔ event / proto mapping | Vikram / Maya | `event-driven-kafka`, `grpc-buf` |

Related: `architecture-patterns`, `backend-fastify-trpc-grpc`, `python-services`, `grpc-buf`, `cost-routing-paradigms` (`@paradigm` gate on every use-case).
