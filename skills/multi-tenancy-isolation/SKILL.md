---
name: multi-tenancy-isolation
description: Brain's tenant-isolation contract (canon §9) — tenant = workspace_id, enforced at FOUR layers (JWT claim → service-side assertion → Postgres RLS → Kafka envelope), the ClickHouse query gateway (no RLS), account models A/B/C/D, and agency cross-brand access + cross-brand portfolio/benchmark aggregation. Use on ANY endpoint, query, event, MCP tool, or cache key that touches tenant data. A single missed layer is a cross-brand data leak — P0.
---

# Multi-Tenancy & Data Isolation

**Tenant = `workspace_id`** (canon/BRAIN_TECHNICAL.md §9). Brain is multi-tenant at every layer; a cross-brand leak is the single worst thing the product can do. Isolation is **defense in depth — four layers, all required**:

| Layer | Enforcement | Owner |
|---|---|---|
| 1. **JWT claim** | `workspace_id` (+ role) in the Supabase Auth token | auth ([`auth-and-access`](../auth-and-access/SKILL.md)) |
| 2. **Service-side assertion** | every gRPC/tRPC handler asserts the caller's `workspace_id` matches the target | Vikram / Maya |
| 3. **Postgres RLS** | row-level security policy, `workspace_id`-leading, on every tenant table | [`database-design`](../database-design/SKILL.md) |
| 4. **Kafka envelope** | every event carries `workspace_id`; partition key IS `workspace_id` | [`event-driven-kafka`](../event-driven-kafka/SKILL.md) |

**ClickHouse has no RLS** (§9.3) — isolation is enforced by the **query gateway** (`pylibs/brain_clickhouse/query.py`): it rejects any query missing a `workspace_id` predicate. Never bypass it ([`clickhouse-olap`](../clickhouse-olap/SKILL.md)). Cache keys are also `workspace_id`-prefixed ([`caching-strategy`](../caching-strategy/SKILL.md)).

## Account models (§9.4)

| Model | Shape |
|---|---|
| **A** | One brand = one workspace (the default) |
| **B** | Agency / multi-brand — one operator, many workspaces, scoped cross-brand access |
| **C** | Enterprise with sub-brands |
| **D** | Enterprise variant with stricter isolation guarantees (§9.5) |

- **Agency cross-brand access** is an explicit, role-gated grant — never implicit. An agency user sees brand X only if granted; enforced at all 4 layers.
- **Cross-brand portfolio queries + benchmarks** (§9.6–9.7) run through a dedicated aggregation pipeline that anonymizes/aggregates — a benchmark must never expose another brand's raw row.

## Anti-patterns (each is a potential P0 leak)

- Trusting the JWT claim alone without the service-side assertion (layer 2 skipped).
- A Postgres query/table without an RLS policy.
- A ClickHouse query that bypasses the gateway or omits the `workspace_id` predicate.
- A Kafka event without `workspace_id` in the envelope.
- A cache key, log line, or metric without `workspace_id` scoping.
- A cross-brand benchmark that returns a competitor's raw values.

## Verify

- For a new tenant endpoint: write a test that a token for workspace A **cannot** read/write workspace B's data (must fail closed) — at the service layer AND via RLS.
- Grep new ClickHouse calls go through `brain_clickhouse.query`. Confirm new events include `workspace_id`. This is Shreya's VETO surface.
