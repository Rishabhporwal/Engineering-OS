---
name: sql-query-optimization
description: Query optimization for Supabase Postgres (OLTP) and ClickHouse (OLAP) — EXPLAIN/EXPLAIN PIPELINE, index strategy, cursor pagination, materialized-view discipline. Use when a Brain endpoint exceeds the 100ms p95 budget, when EXPLAIN shows Seq Scan / Sort / Hash Aggregate on large tables, when CH queries miss the primary key prefix, or when adding a new metric to the metric engine.
---

# SQL Query Optimization

Brain's API queries MUST hit pre-aggregated tables in **<100ms p95** (canon/technical-requirements.md, engineering invariants). When a query is slow, the answer is almost always one of: missing/wrong index, sequential scan over the primary key, `OFFSET` pagination, or aggregating in the request path instead of materializing upstream. This skill covers both Postgres (OLTP — orders, members, integrations, consent, decision_log) and ClickHouse (OLAP — events, rollups, cohort, waterfall).

## Why this matters for Brain

| Surface | Budget | Owner |
|---|---|---|
| Dashboard tRPC reads (web) | 100ms p95 | Vikram + Maya |
| MCP tool queries (`memory.*`, `analytics.*`) | 200ms p95 | Vikram + Maya |
| Morning Brief synthesis inputs (intelligence) | <1s for all signal fetches combined | Maya |
| ClickHouse materialized-view refresh | configurable cadence; never >5s lag | Maya |
| ClickHouse drill-down queries | 500ms p95 | Maya |

---

## Postgres (Supabase) — quick start

### 1. Find the slow query

```sql
-- pg_stat_statements is enabled in Supabase by default
SELECT
  query,
  mean_exec_time,
  calls,
  max_exec_time,
  rows
FROM pg_stat_statements
WHERE userid = (SELECT oid FROM pg_roles WHERE rolname = current_user)
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 2. EXPLAIN with real metrics

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT id, gross_revenue, currency
FROM orders
WHERE workspace_id = 'xxxx-...'::uuid
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 100;
```

Look for:
- `Seq Scan on orders` over a large table → missing index on `(workspace_id, created_at)`.
- `Sort` after the scan → composite index in the wrong column order; `created_at DESC` should be in the index.
- `Bitmap Heap Scan` with high "Rows Removed by Filter" → predicate not selective; consider partial index.
- `Buffers: shared read=...` (high read count) → cold cache; in Brain prod, alert if `cache hit ratio < 99%`.

### 3. Create the index (NEVER block prod)

```sql
-- Always CONCURRENTLY in prod. Never inside a migration transaction.
CREATE INDEX CONCURRENTLY idx_orders_ws_created
  ON orders (workspace_id, created_at DESC);
```

For Brain tables, the **leading column is ALWAYS `workspace_id`**. RLS enforces it; the index must match.

---

## Brain-specific Postgres rules (non-negotiable)

| Rule | Why |
|---|---|
| `workspace_id` is the first column of every multi-tenant index | RLS predicates always include it; planner uses the index iff it leads |
| Every foreign key has its own index | JOINs in the audit / decision-log paths fall over without them |
| Every "list-recent" pattern uses `(workspace_id, created_at DESC)` composite | Avoids Sort step after Index Scan |
| **Cursor pagination, not OFFSET** | OFFSET 10000 scans 10000 rows it discards; cursor uses index seek |
| ANALYZE after any bulk insert / migration | Stale planner stats pick wrong plans, hard to debug |
| No `SELECT *` in API code paths | Bandwidth + Postgres has to fetch heap rows unnecessarily |
| `WHERE x LIKE '%term%'` → never. Use `pg_trgm` GIN | Leading wildcard kills B-tree |

### Cursor pagination (the only kind Brain ships)

```typescript
// tRPC procedure — orders list
const orders = await db.query(
  `SELECT id, gross_revenue, currency, created_at
   FROM orders
   WHERE workspace_id = current_setting('app.workspace_id')::uuid
     AND ($1::timestamptz IS NULL OR created_at < $1)
   ORDER BY created_at DESC
   LIMIT $2`,
  [input.cursor ?? null, Math.min(input.limit ?? 50, 200)],
);
const nextCursor = orders.rows.at(-1)?.created_at ?? null;
return { data: orders.rows, nextCursor };
```

OFFSET is banned in production code paths. Use it only for admin-tooling pages.

---

## ClickHouse — the OLAP rules

ClickHouse is fast when you let it. Slow when you make it scan everything.

### 1. Primary key prefix discipline

Every workspace-scoped table starts with `workspace_id` in `ORDER BY`. Query gateway (`pylibs/brain_clickhouse`) rejects queries missing a `workspace_id =` predicate.

```sql
CREATE TABLE events_raw
(
  workspace_id UUID,
  event_ts     DateTime64(3, 'Asia/Kolkata'),
  source       LowCardinality(String),
  payload      JSON,
  ...
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_ts)
ORDER BY (workspace_id, source, event_ts)  -- prefix MUST start with workspace_id
TTL event_ts + INTERVAL 90 DAY;
```

### 2. EXPLAIN PIPELINE for ClickHouse

```sql
EXPLAIN PIPELINE
SELECT count() FROM events_raw
WHERE workspace_id = 'xxxx-...'
  AND event_ts BETWEEN now() - INTERVAL 7 DAY AND now();
```

Look for:
- `FilterTransform → ExpressionTransform → ...` with full scan → primary key prefix not matching the predicate.
- High `ReadFromMergeTree` row count → partition pruning failed; check `PARTITION BY`.

### 3. Materialized views, not request-path aggregations

Never compute aggregates in API handlers. **Brain's golden rule (canon/technical-requirements.md — compute close to data):**

```sql
-- The materialized view does the work overnight (or every N minutes)
CREATE MATERIALIZED VIEW orders_daily_mv
ENGINE = SummingMergeTree()
ORDER BY (workspace_id, order_date, currency)
AS SELECT
  workspace_id,
  toDate(event_ts) AS order_date,
  currency,
  sum(gross_revenue) AS gross_revenue,
  sum(gst) AS gst,
  count() AS order_count
FROM orders_raw
GROUP BY workspace_id, order_date, currency;
```

API queries hit `orders_daily_mv` — sub-millisecond reads instead of multi-second scans.

### 4. ReplacingMergeTree for idempotent ingestion

Maya's ingestion-service inserts the same event on retry (see `idempotency-handling`). ClickHouse handles dedup at merge time:

```sql
CREATE TABLE orders_raw (...)
ENGINE = ReplacingMergeTree(updated_at)  -- newest wins
ORDER BY (workspace_id, order_id);
```

But: querying the table before merge sees both rows. Use `FINAL` for correctness, or — better — query through a `SELECT DISTINCT` materialized view.

---

## Top anti-patterns Brain has seen (or could ship if you're not careful)

| Anti-pattern | Symptom | Fix |
|---|---|---|
| Composite index with `workspace_id` *not* first | RLS forces a Seq Scan even though the index exists | Re-create with `(workspace_id, ...)` |
| OFFSET 5000 on the audit log | Page 50 of a tenant audit log times out | Cursor on `(created_at, id)` |
| Computing MER in the request handler | 8s response on a 30-day window | Materialize daily; query rolls up at request time |
| ClickHouse `SELECT * FROM events` for "row count" | Reads every column from every part | `SELECT count() FROM events WHERE ...` |
| Postgres `SELECT *` over `decision_log` JSONB | Pulls 500KB rows for a 1KB dashboard cell | Project specific columns; never `*` |
| ORM lazy-loading inside a loop (N+1) | 200 SQL calls per request | `INNER JOIN` or `DataLoader` |
| Forgetting `ANALYZE` after migrations | "It was fast yesterday, why is it slow today?" | `ANALYZE table_name;` after every bulk DML |

---

## Connection pooling

Brain Node services use `pg.Pool` with `max: 20` per replica. Don't share a pool across multiple processes; each EKS pod is its own pool. ClickHouse uses `clickhouse-driver` (Python) or `@clickhouse/client` (Node) with HTTP keep-alive; no pool needed at the same scale.

For Supabase, use the **transaction pooler** (port 6543) for short queries from API requests, **session pooler** (port 5432) for long-running migrations + Prisma operations that need session state.

---

## Production checklist (Vikram / Maya before any new endpoint)

- [ ] Index includes `workspace_id` first
- [ ] EXPLAIN ANALYZE result attached to PR (Postgres) OR EXPLAIN PIPELINE (ClickHouse)
- [ ] Cursor pagination if endpoint returns a list
- [ ] `LIMIT` set, max 200, default 50
- [ ] No `SELECT *` — explicit columns
- [ ] No `OFFSET` in prod paths
- [ ] p95 measured in staging at expected load (use k6 — see `testing-tdd`)
- [ ] If ClickHouse: query hits an MV, not raw table

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Postgres OLTP query review | **Vikram** + Aryan | canon/technical-requirements.md (OLTP design) |
| ClickHouse OLAP + MVs | **Maya** | canon/technical-requirements.md (OLAP design), `clickhouse-olap` skill |
| Metric engine query patterns | **Maya** | canon/technical-requirements.md (metric registry) |
| Connection pool config (EKS) | **Jatin** | canon/technical-requirements.md |

Related Brain skills: `clickhouse-olap` (OLAP-specific patterns), `database-design` (schema decisions), `api-traffic-patterns` (cursor pattern).
