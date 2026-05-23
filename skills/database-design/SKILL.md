---
name: database-design
description: Brain's data layer — Supabase Postgres (OLTP) + ClickHouse Cloud (OLAP) split. Schema conventions, RLS policies (workspace_id-leading), multi-tenant discipline, indexes/partial indexes, partitioning, materialized views, Debezium CDC, transaction-vs-session pooling, idempotency-key TTL, pg_cron/pgvector. Auto-load whenever designing a new core-service table, adding an index, configuring connection pooling, reviewing a Supabase migration, or hitting a query performance issue. See clickhouse-olap for deep CH patterns and security-baseline for RLS detail.
---

# Database Design — Brain's OLTP + OLAP Split

Brain's data layer:

| Store | Purpose | Owner |
|---|---|---|
| **Supabase Postgres** | OLTP: workspaces, members, integrations config, goals, classifications, marketing actions, consent_event, audience, audience_member, outreach, call, ticket, message, rfm_score, ai.decision_log, ai.forecast_accuracy, ai.brand_fingerprint (+pgvector), mobile_push_tokens | core-service (Vikram); notifications/lifecycle Node (Vikram); intelligence-service Memory writes (Maya) |
| **ClickHouse Cloud** | OLAP: raw_<source>_<entity>_local, orders_local, ads_local, shipments_local, daily_metrics_local, cohort_aggregates_local, first_product_attribution_local, pincode_reliability_local, customer_states_local | analytics-service (Maya); ingestion-service raw writes (Maya) |
| **CDC** | Postgres → Kafka via Debezium on MSK Connect — for recent OLTP mirror in CH if needed | Jatin |

**No service queries another service's database directly.** Cross-service data flows via published Kafka events or gRPC APIs (see canon/technical-requirements.md).

## PostgreSQL (Supabase) — OLTP

### Naming Conventions
- Tables: `snake_case`, plural (`<entities>`, `<entity>_<relation>`)
- Primary keys: `id` (UUID v7 preferred, `bigserial` if hot-write loop)
- Tenant column: **`workspace_id`** (UUID, NOT NULL, indexed) — on every workspace-scoped business table. Brain's tenant = workspace = brand = billing unit; the `<tenant_id>` placeholder in the generic templates below is always `workspace_id` in Brain.
- Timestamps: `created_at`, `updated_at` (timestamptz), default `now()`
- Soft delete: `deleted_at` (timestamptz, nullable) when business needs it; otherwise hard delete

### Standard Columns (template — replace `<tenant_id>` with the project's actual name)
```sql
CREATE TABLE <entities> (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  <tenant_id>  uuid NOT NULL REFERENCES <tenants>(id),
  external_id  text,                                -- if mirroring an external source
  occurred_at  timestamptz NOT NULL,
  <domain_columns>,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (<tenant_id>, external_id)
);
CREATE INDEX idx_<entities>_<tenant>_occurred ON <entities> (<tenant_id>, occurred_at DESC);
```

### Indexing Rules
- **Always** index `<tenant_id>` first in any composite index used in WHERE clauses
- **Composite over multi-single**: `(<tenant_id>, occurred_at)` beats two single-column indexes for a query that filters both
- **Partial indexes** for sparse hot paths: `WHERE <flag> = true`
- **Don't index** every column — indexes cost on write. Profile first (`EXPLAIN ANALYZE`).

### Row-Level Security (safety net, not substitute)
```sql
ALTER TABLE <entities> ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <entities>
  USING (<tenant_id> = current_setting('app.<tenant_id>')::uuid);
```
Set `app.<tenant_id>` via Prisma middleware on every connection.

### Migration Discipline (Prisma)
- Never `ALTER TABLE` directly. Always migrations.
- **One migration per PR** — never bundle schema changes.
- **Idempotent**: `IF NOT EXISTS`, `IF EXISTS`, `OR REPLACE`.
- Backwards-compatible by default: add column nullable → backfill → make NOT NULL in a later migration (two-phase pattern; never a single `ADD COLUMN NOT NULL` lock).
- **No locking DDL during business hours** — schedule for the maintenance window.
- **Always `CREATE INDEX CONCURRENTLY`** in prod (cannot run inside a transaction).
- For huge tables: use `pg_repack` or batched UPDATE, not a single locking ALTER.
- **Roll-back script** for every migration (Prisma generates the down migration — check it).

## Supabase + Brain specifics (workspace_id as the tenant column)

Brain's OLTP system of record is **Supabase Postgres** (workspaces, members, integrations config, goals, marketing actions, consent model, Decision Log, idempotency keys, audit). For Brain, the `<tenant_id>` column above is concretely **`workspace_id`**. Companion skills: `sql-query-optimization` (query-shape), `security-baseline` (RLS + secret handling), `idempotency-handling` (key TTL + cleanup).

### Connection management — transaction vs session pooler (CRITICAL)

Supabase exposes two pooler endpoints:

| Pooler | Port | When |
|---|---|---|
| **Transaction** | 6543 | Default for API request paths (short, stateless). **Cannot use prepared statements**, `LISTEN/NOTIFY`, or session state. |
| **Session** | 5432 | Long-running connections needing session state — migrations, Prisma `$transaction([...])`, `LISTEN/NOTIFY`. |

Brain services use the **transaction pooler** for tRPC + gRPC request paths (Prisma in `pgbouncer` mode); migrations run via the session pooler.

```env
DATABASE_URL="postgres://...@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=20"
DIRECT_URL="postgres://...@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
```

**`connection_limit` per pod = 20** (Brain default). 10 replicas → 200 connections, within Supabase's budget. Each EKS pod owns its own; don't share across processes.

### RLS — workspace_id-leading (Shreya VETO territory)

RLS is mandatory on every workspace-scoped table — but it is a **safety net, not the primary boundary**. `workspace_id` is set per-request from the verified JWT:

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_orders ON orders
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
```typescript
// preHandler hook on every request — transaction-local, cleared at tx end
await db.query("SELECT set_config('app.workspace_id', $1, true)", [req.workspaceId]);
```

Brain rule: **`workspace_id` MUST come from `app_metadata.workspace_id` in the verified JWT** (see `auth-and-access`, `defense-in-depth-validation`). Never from the request body — slice-3 caught a CVE-class cross-tenant write from that exact anti-pattern.

**RLS performance:** for the policy predicate to be index-usable, the index leading column must be `workspace_id`. EXPLAIN the policy-augmented query to confirm `Index Scan`, not `Seq Scan + Filter`:
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE id = 'some-uuid';
```

**Bypass RLS only via `service_role`** (admin paths: cross-workspace backfill, the metric engine). NEVER unset RLS. The `service_role` key lives in AWS Secrets Manager — never in env files, never in client code.

### Concurrency

```sql
CREATE INDEX CONCURRENTLY idx_orders_ws_created ON orders (workspace_id, created_at DESC);
SELECT pg_try_advisory_lock(hashtext('daily_rollup_2026_05_13'));  -- one-at-a-time jobs
```
For high-write paths (ingestion, Decision Log) prefer **optimistic concurrency** (`xmin` / `version` column). Use `FOR UPDATE NOWAIT` only when serialization is correctness-critical (consent transitions, AI calling scheduling).

### Data access + schema reminders
- **No `SELECT *` in API code** — project columns; the heap fetch happens without a covering index.
- **Cursor pagination, never OFFSET** (banned in prod paths — see `api-traffic-patterns`).
- **Batched DML** — multi-row `INSERT ... ON CONFLICT ... DO UPDATE` via `UNNEST(...)`, or `COPY` for bulk loads.
- **Integer minor units** for money (`spend_minor`, `gross_revenue_minor`) — never `numeric(15,2)` floats (slice-3 lesson).
- **`text` not `varchar(N)`** (identical in PG, avoids truncation bugs); **`citext`** for case-insensitive (email).
- **JSONB for flexible payloads** (Decision Log, integration config), but promote frequently-queried fields to a generated column + index.

### Advanced features Brain uses
- **`pg_cron`** — idempotency-key cleanup (TTL), daily rollups, NCPR cache refresh.
- **`pgvector`** — the Memory Layer (Brand Fingerprint, Customer Segment Memory, Seasonal Codebook).
- **`pg_trgm`** — fuzzy customer-name search (replaces banned `LIKE '%term%'`).

### Monitoring (Jatin + Vikram)
- **`pg_stat_statements`** (default in Supabase): any query with `mean_exec_time > 500ms` and `calls > 100` over 1h → page Vikram (blowing the BFF latency budget).
- **Pool saturation** — CloudWatch PgBouncer active connections; alert at 80% capacity.
- **Cache hit ratio** — `sum(blks_hit)/sum(blks_hit+blks_read)` target > 99%; below 95% suggests memory pressure (talk to Supabase about instance size).

## Time + Timezones (multi-tenant gotcha)

`NOW()`, `CURRENT_DATE`, `datetime('now')`, `date_trunc('day', NOW())` — all return **server-local or UTC** time, never the tenant's local time. For a multi-tenant analytics product, "today's revenue" is meaningless without naming whose "today".

**Lived failure** (multi-tenant analytics build, slice 1): a `todayRevenue` query used `substr(datetime('now'), 1, 10) = substr(orders.ordered_at, 1, 10)`. SQLite's `datetime('now')` is UTC. A tenant reading the dashboard at 9:00 AM IST (= 03:30 UTC) sees an empty "today" because UTC is still on yesterday. The bug is silent — the API returns `{ orderCount: 0 }`, not an error.

### Rule: store every tenant's timezone, scope every time-bucket query by it.

```sql
ALTER TABLE <tenants> ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';  -- 'Asia/Kolkata', 'America/Los_Angeles', etc.
```

### PostgreSQL (canonical pattern)
```sql
-- "today" in the tenant's timezone, expressed as a UTC range
WITH bounds AS (
  SELECT
    (date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone)        AS start_utc,
    (date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone
       + INTERVAL '1 day')                                                            AS end_utc
  FROM <tenants> t WHERE t.id = $1
)
SELECT COALESCE(SUM(net_revenue), 0)
FROM orders, bounds
WHERE orders.<tenant_col> = $1
  AND orders.ordered_at >= bounds.start_utc
  AND orders.ordered_at <  bounds.end_utc;
```

Store `ordered_at` as `timestamptz`. Never store `text` ISO strings for time-bucketed queries — you lose the index and you lose timezone math.

**Brain default: IST (`Asia/Kolkata`).** India-first by sequencing, but the timezone is always read from the workspace's region (RegionAdapter), never hardcoded — UAE/GCC workspaces resolve to their own zone. "Today's revenue" is always bucketed in the workspace's local day, expressed as a UTC range. (Brain's stack is Postgres + ClickHouse only — no SQLite; the patterns below are the two engines Brain runs.)

### ClickHouse
```sql
SELECT sum(net_revenue) FROM analytics.orders
WHERE <tenant_id> = {tid:String}
  AND toDate(ordered_at, {tz:String}) = toDate(now(), {tz:String});
```
ClickHouse's `toDate(datetime, 'Asia/Kolkata')` does the timezone math correctly. Always pass the tenant's IANA string, never bake it in.

### Anti-patterns this skill forbids
- ❌ `WHERE date(ordered_at) = date('now')` with no timezone arg
- ❌ Storing timestamps as `TEXT` for any time-bucketed query
- ❌ Hardcoding a single timezone ("we'll fix it when we expand to the US") — fix it at v1, the schema is the hard part
- ❌ Letting the frontend compute "today" from the browser clock and pass it as a date range — it disagrees with the backend on DST boundaries and travel

## ClickHouse — Analytics

### Engine Selection
| Engine | Use case |
|---|---|
| `MergeTree` | append-only fact tables (orders, ad insights) |
| `SummingMergeTree` | pre-aggregated rollups (`SUM(revenue)` by day) |
| `ReplacingMergeTree` | mutable rows where you want latest version (rare) |
| `AggregatingMergeTree` | materialized views with state functions |

### Schema Conventions
```sql
CREATE TABLE analytics.<entity> (
  <tenant_id>     String,
  external_id     UInt64,
  occurred_at     DateTime,
  <domain_columns>,
  <enum_column>   Enum8('A'=1, 'B'=2),
  <flag>          Bool,
  <low_card>      LowCardinality(String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (<tenant_id>, occurred_at);
```

Rules:
- `<tenant_id>` first in `ORDER BY` (always — partition pruning + tenant isolation)
- Partition by month (`toYYYYMM`) for time-series tables. Daily partitions for >100M rows/day.
- Use `LowCardinality(String)` for enum-like columns (status, country, channel)
- Use `Enum8` for fixed sets
- **Money = `Int64` minor units (paisa) + a `currency_code` column — NEVER `Float64`/`Decimal` for money** (Brain canonical fact; float money is a code-review blocker). Ratios (MER/aMER/AOV) may be `Float64`.

### Materialized Views (the analytics pattern)
```sql
CREATE MATERIALIZED VIEW analytics.daily_<entity>_summary
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(date)
ORDER BY (<tenant_id>, date)
AS SELECT
  <tenant_id>,
  toDate(occurred_at) AS date,
  sum(<measure>) AS total,
  count() AS events
FROM analytics.<entity>
GROUP BY <tenant_id>, date;
```

### Query Optimization
- `WHERE <tenant_id> = ?` first (matches partition + sort key)
- Avoid `SELECT *` on wide tables (column store)
- Use `PREWHERE` for very selective filters
- For top-N: `ORDER BY ... LIMIT N` is cheap because of sort key

## Cache Layer (Redis — ElastiCache)
- Cache key: `<entity>:{workspace_id}:{<key>}` — workspace-scoped; never user-id-keyed without tenant scope
- TTL: ~60s for hot metric cache, 5 min for dashboards, 1 hour for static lookups
- Invalidation: explicit, not TTL-only (invalidate on write; see `caching-strategy`)

## When You Hit a Wall
1. `EXPLAIN ANALYZE` the slow query
2. Check `pg_stat_user_indexes` for unused indexes (cost) and missing ones (your slow query is full-scanning)
3. For ClickHouse: `system.query_log` shows what's slow
4. For Redis: `--latency` flag, check key cardinality

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Schema + migrations for core-service | **Vikram** | canon/technical-requirements.md (OLTP design) |
| RLS policy review | **Shreya** + Aryan | canon/technical-requirements.md (multi-tenancy) |
| Connection pooler config | **Jatin** + Vikram | canon/technical-requirements.md (connection) |
| Slow query alerting | **Jatin** | `observability` |
| Memory Layer (pgvector) | **Maya** | canon/technical-requirements.md |
| pg_cron job inventory | **Jatin** | scheduled tasks doc |

Related Brain skills: `sql-query-optimization` (query-shape rules), `clickhouse-olap` (deep CH patterns), `security-baseline` (RLS + secret handling), `idempotency-handling` (key TTL + cleanup), `auth-and-access` (`workspace_id` from JWT into the `app.workspace_id` GUC), `api-traffic-patterns` (cursor pagination).
