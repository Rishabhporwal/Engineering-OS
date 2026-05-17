---
name: database-design
description: Brain's data layer — Supabase Postgres (OLTP) + ClickHouse Cloud (OLAP) split. Schema conventions, RLS policies, multi-tenant `workspace_id` discipline, indexes, partitioning, materialized views, Debezium CDC. Auto-load whenever designing a new table, adding an index, or hitting a query performance issue. See clickhouse-olap for deep CH patterns and security-baseline for RLS detail.
---

# Database Design — Brain's OLTP + OLAP Split

Brain's data layer:

| Store | Purpose | Owner |
|---|---|---|
| **Supabase Postgres** | OLTP: workspaces, members, integrations config, goals, classifications, marketing actions, consent_event, audience, audience_member, outreach, call, ticket, message, rfm_score, ai.decision_log, ai.forecast_accuracy, memory.brand_fingerprint (+pgvector), mobile_push_tokens | core-service (Vikram); lifecycle-service Node (Neel); intelligence-service Memory writes (Maya) |
| **ClickHouse Cloud** | OLAP: raw_<source>_<entity>_local, orders_local, ads_local, shipments_local, daily_metrics_local, cohort_aggregates_local, first_product_attribution_local, pincode_reliability_local, customer_states_local | analytics-service (Kabir); ingestion-service raw writes (Sahil) |
| **CDC** | Postgres → Kafka via Debezium on MSK Connect — for recent OLTP mirror in CH if needed | Jatin |

**No service queries another service's database directly.** Cross-service data flows via published Kafka events or gRPC APIs (TECH §1 §4).

## PostgreSQL (Supabase) — OLTP

### Naming Conventions
- Tables: `snake_case`, plural (`<entities>`, `<entity>_<relation>`)
- Primary keys: `id` (UUID v7 preferred, `bigserial` if hot-write loop)
- Tenant column: `<tenant_id>` (UUID, NOT NULL, indexed) — on every business table; column name set per-project in `memory/business-context.md` (e.g., `brand_id`, `org_id`, `account_id`)
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
- Backwards-compatible by default: add column nullable → backfill → make NOT NULL in a later migration
- For huge tables: use `pg_repack` or batched UPDATE, not a single locking ALTER

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

### SQLite (dev/Speed Mode)
```sql
SELECT COALESCE(SUM(net_revenue), 0)
FROM orders
WHERE <tenant_col> = ?
  AND ordered_at >= datetime('now', 'start of day', ?)        -- ?2 = e.g. '-5 hours -30 minutes' from tenants.timezone
  AND ordered_at <  datetime('now', 'start of day', ?, '+1 day');
```
Resolve the offset from the tenant's IANA timezone in application code (Luxon / date-fns-tz / `Intl.DateTimeFormat`) — SQLite has no timezone database.

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
- `Float64` for currency (yes, even though it's lossy — match upstream)

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

## Cache Layer (Redis Upstash)
- Cache key: `<entity>:{<tenantId>}:{<key>}` — never user-id-keyed without tenant scope
- TTL: 5 min for dashboards, 1 hour for static lookups
- Invalidation: explicit, not TTL-only (publish to Kafka `<app>.cache.invalidate.<entity>` topic)

## When You Hit a Wall
1. `EXPLAIN ANALYZE` the slow query
2. Check `pg_stat_user_indexes` for unused indexes (cost) and missing ones (your slow query is full-scanning)
3. For ClickHouse: `system.query_log` shows what's slow
4. For Redis: `--latency` flag, check key cardinality
