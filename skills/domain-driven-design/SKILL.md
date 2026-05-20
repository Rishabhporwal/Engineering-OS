---
name: domain-driven-design
description: Brain's mandatory service-internal organization — every backend service (TS Fastify + Python FastAPI) is structured by bounded context, NEVER by controllers/services/models technical layers. Covers DDD tactical patterns (entities, aggregates, value-objects, repositories, domain events, factories, policies), CQRS (commands/queries/use-cases), and the bootstrap/domain/application/infrastructure/interfaces layering. Auto-load whenever scaffolding a new service, adding a bounded context, reviewing a PR that adds a directory, or refactoring a service that drifted into technical-layer folders.
---

# Domain-Driven Design — Brain Service Internals

> The internal shape of every Brain backend service. Aryan owns the structure; **every builder** (Vikram, Maya) follows it on every service.

This is the **service-internal** companion to `architecture-patterns` (which governs the 7-service topology). Architecture-patterns says *which* services exist; this skill says *how each one is organized inside*.

## The Iron Law

```
ORGANIZE BY BOUNDED CONTEXT, NEVER BY TECHNICAL LAYER
```

A service folder is named for a **business capability** (`recovery`, `audience`, `attribution`, `consent`) — never for a technical role (`controllers/`, `services/`, `models/`). If a reviewer can't tell what the business does from the directory tree, the structure is wrong.

## The mandatory service-internal structure

Every backend service — TS (Fastify) and Python (FastAPI) — uses the same skeleton:

```
service/src/
  bootstrap/          # server, container (DI), startup, config, grpc, kafka, database
  domain/<bounded-context>/
                      # entities, services, repositories, value-objects, dto,
                      # validators, mappers, events, policies, exceptions,
                      # factories, aggregates
  application/        # commands, queries, workflows, orchestrators, handlers, use-cases   ← CQRS
  infrastructure/     # database, repositories, kafka, grpc, cache, telemetry, external, storage
  interfaces/         # rest, grpc, consumers, producers, websocket, jobs
  observability/      # OTel wiring, metrics, health (see `observability` skill)
  security/           # workspace_id guard, authz, tenant scoping (see `security-baseline`)
  testing/
  main                # entrypoint
```

The four core layers and what may depend on what:

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

## Tactical patterns (the building blocks)

| Pattern | Lives in | What it is |
|---|---|---|
| **Entity** | `domain/<ctx>/entities/` | Identity + lifecycle (`Audience`, `Outreach`, `Workspace`) |
| **Value Object** | `domain/<ctx>/value-objects/` | Immutable, equality-by-value (`Money` in paisa, `Pincode`, `CallingWindow`, `GstRate`) |
| **Aggregate** | `domain/<ctx>/aggregates/` | Consistency boundary; one root entity guards invariants; only the root is loaded/saved |
| **Repository** | `domain/<ctx>/repositories/` (interface) → `infrastructure/repositories/` (impl) | Persists aggregates; the interface is domain, the SQL is infrastructure |
| **Domain Event** | `domain/<ctx>/events/` | A fact the domain emits (`OutreachCompleted`) → mapped to a Kafka event in `interfaces/producers/` |
| **Factory** | `domain/<ctx>/factories/` | Constructs valid aggregates (enforces invariants at birth) |
| **Policy** | `domain/<ctx>/policies/` | Encapsulated business rule (`CallingHoursPolicy`, `FrequencyCapPolicy`, `RtoRiskPolicy`) |
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
  workflows/     # multi-step orchestration (in-service use-cases / saga over Kafka)
  orchestrators/ # in-process choreography across use-cases
```

A use-case loads an aggregate via a repository, calls domain methods, persists, and publishes domain events. It contains **no** business rules itself — those live in the domain. Reads can bypass the aggregate and hit a query-optimized projection (e.g. ClickHouse MV) directly.

## On Fastify (TypeScript)

```
interfaces/rest/audience.routes.ts   →  application/commands/launch-recovery-campaign.ts
                                          ↓ calls
                                        domain/audience/aggregates/Audience.ts
                                          ↓ persisted via
                                        domain/audience/repositories/AudienceRepository.ts (interface)
                                          ↑ implemented by
                                        infrastructure/repositories/PgAudienceRepository.ts
```

Fastify routes are THIN — they parse/validate (Zod), call the use-case, map the result. The DI container in `bootstrap/container.ts` wires concrete repositories to domain interfaces. tRPC procedures and gRPC handlers are also `interfaces/` adapters over the same use-cases.

## On FastAPI (Python)

```
interfaces/rest/audience_router.py   →  application/commands/launch_recovery_campaign.py
domain/audience/aggregates/audience.py        (pure dataclasses / pydantic for VOs)
domain/audience/repositories/audience_repository.py   (Protocol / ABC)
infrastructure/repositories/pg_audience_repository.py (asyncpg impl)
```

FastAPI routers stay thin; `bootstrap/container.py` does dependency wiring. Domain modules import **nothing** from `fastapi`, `asyncpg`, or `aiokafka`. aiokafka consumers live in `interfaces/consumers/` and translate Kafka envelopes into commands.

## The anti-pattern — STOP

The single most common drift is the **technical-layer tree**:

```
✗  src/controllers/   src/services/   src/models/   src/routes/   src/utils/
```

This scatters one business capability (recovery) across five folders, makes the domain logic untestable without the framework, and hides the bounded contexts. **Block at code review.** The correct tree groups by capability and isolates the domain.

## Red flags — STOP

- A new folder named `controllers/`, `services/` (at the top level), `models/`, `helpers/`, `utils/`, or `managers/`
- A domain file that imports `fastify`, `fastapi`, `asyncpg`, `kafkajs`, `grpc`, or `prisma`
- Business rules (calling-hours check, GST math, frequency cap) inside a route handler instead of a `policy` / domain method
- Raw `number` for money instead of a `Money` value-object
- A use-case that contains an `if`-ladder of business rules (rules belong in the domain)
- A repository returning ORM rows instead of reconstituted aggregates
- Two services sharing a `domain/` module (each service owns its bounded contexts; share via proto/events, not code)

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "controllers/services/models is the framework default" | Brain's default is bounded-context. Frameworks don't dictate domain organization. |
| "It's a small service, layers are overkill" | Small services drift into big ones; the skeleton costs nothing now and saves a refactor later |
| "The route already validates, I'll just put the rule there" | Rules in routes can't be reused by the Kafka consumer or the gRPC handler — Single-Primitive violation |
| "I'll use the ORM model as my entity" | ORM models couple domain to persistence; a schema change then ripples into business logic |
| "Money as a number is simpler" | One missing paisa rounding = a wrong CM2 on the Founder's dashboard. Value-objects enforce the moat. |
| "CQRS is enterprise bloat" | Brain already splits OLTP (write) from OLAP (read); CQRS is the in-service expression of the same split |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Service-internal structure standard | **Aryan** | this skill + `architecture-patterns` |
| TS (Fastify) service internals | **Vikram** | `backend-fastify-trpc-grpc` |
| Python (FastAPI) service internals | **Maya** | `python-services` |
| Bounded-context boundaries + ADR | Aryan | `memory/decisions/ADR-<NNN>-*.md` |
| Domain ↔ event mapping | Vikram / Maya | `event-driven-kafka` |
| Domain ↔ proto mapping | Vikram / Maya | `grpc-buf` |

## Related

- `skills/architecture-patterns/SKILL.md` — the 7-service topology + Single-Primitive Rule + DB ownership
- `skills/backend-fastify-trpc-grpc/SKILL.md` — Fastify/tRPC/gRPC adapter patterns
- `skills/python-services/SKILL.md` — FastAPI/asyncpg/aiokafka patterns
- `skills/grpc-buf/SKILL.md` — proto as the contract-first source of truth
- `skills/cost-routing-paradigms/SKILL.md` — `@paradigm` gate on every use-case
