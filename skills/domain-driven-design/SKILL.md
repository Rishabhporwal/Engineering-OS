---
name: domain-driven-design
description: Mandatory service-internal organization — every backend service structured by bounded context, NEVER by controllers/services/models. DDD tactical patterns, CQRS, inward-pointing layering.
---

# Domain-Driven Design — Service Internals

> The internal shape of every backend service. The Architect owns the structure; **every builder** follows it.

The **service-internal** companion to `architecture-patterns` (which governs the service topology). Architecture-patterns says *which* services exist; this says *how each one is organized inside*.

## The Iron Law

```
ORGANIZE BY BOUNDED CONTEXT, NEVER BY TECHNICAL LAYER
```

A service folder is named for a **business capability** (`recovery`, `audience`, `attribution`, `consent`) — never a technical role (`controllers/`, `services/`, `models/`). If a reviewer can't tell what the business does from the directory tree, the structure is wrong.

## The mandatory service-internal structure

Every backend service — whatever runtime the Canon binds (the examples below show one TS + one Python binding) — uses the same skeleton:

```
service/src/
  bootstrap/          # server, container (DI), startup, config, rpc, event-bus, database
  domain/<bounded-context>/   # entities, services, repositories, value-objects, dto,
                              # validators, mappers, events, policies, exceptions, factories, aggregates
  application/        # commands, queries, workflows, orchestrators, handlers, use-cases   ← CQRS
  infrastructure/     # database, repositories, event-bus, rpc, cache, telemetry, external, storage
  interfaces/         # rest, rpc, consumers, producers, websocket, jobs
  observability/      # OTel wiring, metrics, health (see `observability`)
  security/           # tenant guard, authz, tenant scoping (see `security-baseline`)
  testing/
  main                # entrypoint
```

| Layer | Holds | May import |
|---|---|---|
| **domain/** | Pure business logic — no I/O, no framework | nothing outside domain |
| **application/** | Use-cases that orchestrate the domain (CQRS) | domain only |
| **infrastructure/** | Concrete adapters (DB, event-bus, RPC, cache, object storage) | domain interfaces |
| **interfaces/** | Inbound edges (REST, RPC, event consumers, WS, jobs) | application |

**Dependency rule (the spine):** dependencies point INWARD. `interfaces → application → domain`; `infrastructure` implements `domain` interfaces (dependency inversion). Domain NEVER imports a web framework, a DB driver, or an event-bus client — that's how the business logic stays testable in isolation.

## Bounded contexts per service (examples)

| Service | Bounded contexts (`domain/<context>/`) |
|---|---|
| core-service | `tenant`, `goals`, `integrations`, `consent`, `identity` |
| lifecycle-service | `segmentation`, `audiences`, `recovery`, `compliance` |
| analytics-service | `metrics`, `attribution`, `audit-log`, `region-adapter` |
| intelligence-service | `agents`, `memory`, `recommendation`, `brief` |

One context = one ubiquitous language. The product's domain vocabulary lives inside the relevant context's entities + value-objects, not scattered as utility functions.

## Tactical patterns

| Pattern | Lives in | What it is |
|---|---|---|
| **Entity** | `domain/<ctx>/entities/` | Identity + lifecycle (`Audience`, `Outreach`, `Tenant`) |
| **Value Object** | `domain/<ctx>/value-objects/` | Immutable, equality-by-value (`Money` in minor units, `Window`, `Rate`) |
| **Aggregate** | `domain/<ctx>/aggregates/` | Consistency boundary; one root guards invariants; only the root is loaded/saved |
| **Repository** | `domain/<ctx>/repositories/` (interface) → `infrastructure/repositories/` (impl) | Persists aggregates; interface is domain, the query layer is infrastructure |
| **Domain Event** | `domain/<ctx>/events/` | A fact the domain emits (`OutreachCompleted`) → mapped to the event bus in `interfaces/producers/` |
| **Factory** | `domain/<ctx>/factories/` | Constructs valid aggregates (invariants at birth) |
| **Policy** | `domain/<ctx>/policies/` | Encapsulated rule (`WindowPolicy`, `FrequencyCapPolicy`, `RiskPolicy`) |
| **Domain Service** | `domain/<ctx>/services/` | Logic that doesn't belong to one entity (cross-entity calc) |
| **Mapper** | `domain/<ctx>/mappers/` | Domain ↔ persistence row / DTO / contract message |
| **Exception** | `domain/<ctx>/exceptions/` | Domain-specific failures (`OutOfWindowError`) |

**Money is ALWAYS a `Money` value-object in integer minor units + a currency — never a raw number.** Every monetary rule flows through value-objects so the financial logic is enforced by the type system.

## CQRS — application layer

Commands mutate; queries read. They never mix.

```
application/
  commands/      # LaunchRecovery, AdjustBudget  (write side; returns ack/id)
  queries/       # GetAudienceById, ListOutreach  (read side; returns DTOs)
  use-cases/     # one handler per command/query
  handlers/      # wire use-cases to interfaces
  workflows/     # multi-step orchestration (saga over the event bus)
  orchestrators/ # in-process choreography across use-cases
```

A use-case loads an aggregate via a repository, calls domain methods, persists, and publishes domain events. It contains **no** business rules itself — those live in the domain. Reads can bypass the aggregate and hit a query-optimized projection (e.g. an OLAP materialized view) directly.

## On a TypeScript binding

```
interfaces/rest/audience.routes.ts → application/commands/launch-recovery.ts
  → domain/audience/aggregates/Audience.ts
  → domain/audience/repositories/AudienceRepository.ts (interface)
  ↑ implemented by infrastructure/repositories/PgAudienceRepository.ts
```

Routes are THIN — parse/validate, call the use-case, map the result. The DI container in `bootstrap/container.ts` wires concrete repositories to domain interfaces. RPC handlers are also `interfaces/` adapters over the same use-cases.

## On a Python binding

```
interfaces/rest/audience_router.py → application/commands/launch_recovery.py
domain/audience/aggregates/audience.py        (pure dataclasses / value objects)
domain/audience/repositories/audience_repository.py   (Protocol / ABC)
infrastructure/repositories/pg_audience_repository.py (driver impl)
```

Routers stay thin; `bootstrap/container.py` does wiring. Domain modules import **nothing** from the web framework, the DB driver, or the event-bus client. Event consumers live in `interfaces/consumers/` and translate event envelopes into commands.

## The anti-pattern — STOP

The most common drift is the **technical-layer tree**:

```
✗  src/controllers/   src/services/   src/models/   src/routes/   src/utils/
```

This scatters one business capability across five folders, makes domain logic untestable without the framework, and hides the bounded contexts. **Block at code review.**

## Red flags — STOP

- A new top-level folder named `controllers/`, `services/`, `models/`, `helpers/`, `utils/`, or `managers/`
- A domain file that imports the web framework, a DB driver, the event-bus client, or an ORM
- Business rules (a window check, a financial calc, a frequency cap) inside a route handler instead of a `policy` / domain method
- Raw `number` for money instead of a `Money` value-object
- A use-case that contains an `if`-ladder of business rules
- A repository returning ORM rows instead of reconstituted aggregates
- Two services sharing a `domain/` module (share via contracts/events, not code)

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "controllers/services/models is the framework default" | The default here is bounded-context |
| "It's a small service, layers are overkill" | Small services drift into big ones; the skeleton costs nothing now |
| "The route already validates, I'll put the rule there" | Rules in routes can't be reused by the event consumer or RPC handler — Single-Primitive violation |
| "I'll use the ORM model as my entity" | ORM models couple domain to persistence; a schema change ripples into business logic |
| "Money as a number is simpler" | One missing rounding = a wrong financial number on a stakeholder's dashboard |
| "CQRS is enterprise bloat" | Splitting OLTP (write) from OLAP (read) is already common; CQRS is the in-service expression |

## Wiring

| Concern | Owner | Reference |
|---|---|---|
| Service-internal structure standard | **Architect** | this skill + `architecture-patterns` |
| TS service internals | **Backend Engineer** | `backend-fastify-trpc-grpc` |
| Python service internals | **AI/ML Engineer** | `python-services` |
| Bounded-context boundaries + ADR | Architect | `memory/decisions/ADR-<NNN>-*.md` |
| Domain ↔ event / contract mapping | Backend / AI-ML Engineer | `event-driven-kafka`, `grpc-buf` |

Related: `architecture-patterns`, `backend-fastify-trpc-grpc`, `python-services`, `grpc-buf`, `cost-routing-paradigms` (the effort-tier gate on every use-case).
