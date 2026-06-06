---
name: data-layer
description: Reference implementation — Postgres OLTP conventions: tenant-leading RLS, indexes/partitioning, transaction-vs-session pooling, query optimization. OLAP → clickhouse-olap.
---

# Data Layer — Postgres OLTP + Query Optimization

> **Reference implementation.** This skill documents one concrete binding of the OLTP seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind this seam to different technology. The *patterns* here (tenant-leading indexes, RLS as defense-in-depth, pooling discipline, integer-minor-unit money, tenant-tz time bucketing) are what transfer; Postgres is the example.

A common split: **Postgres** = OLTP (tenants, members, config, classifications, actions, consent_event, audience, outreach, idempotency_keys, and the system-of-record audit log); a columnar store = OLAP (see `clickhouse-olap`). CDC Postgres→event-bus via a log-based connector (e.g. Debezium). **No service queries another service's DB** — cross-service data flows via events or RPC.

This playbook owns Postgres + query-shape rules. Schema/migration canon: the Product Canon's `STACK.md` + HLD/LLD. RLS depth → `security-baseline`; key TTL → `idempotency-handling`; OLAP → `clickhouse-olap`.

## Naming + standard columns
- Tables `snake_case` plural; PK `id` (UUID v7 preferred, `bigserial` for hot-write loops).
- The tenant column is always the **tenant-isolation key** (`tenant_id`, declared in the Canon; UUID NOT NULL, indexed) on every tenant-scoped table.
- `created_at`/`updated_at` timestamptz default `now()`; soft delete `deleted_at` nullable only when business needs it.
```sql
CREATE TABLE <entities> (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenants(id),
  external_id text,
  occurred_at timestamptz NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, external_id)
);
CREATE INDEX idx_<entities>_tenant_occurred ON <entities> (tenant_id, occurred_at DESC);
```

## Indexing rules (non-negotiable)
- **`tenant_id` is the FIRST column** of every multi-tenant index — RLS predicates always include it; the planner uses the index only if it leads.
- Composite beats multi-single for a query filtering both columns. Every FK has its own index (audit-log JOINs fall over without).
- "list-recent" → `(tenant_id, created_at DESC)` composite (avoids a Sort after Index Scan).
- Partial indexes for sparse hot paths (`WHERE flag = true`). Don't index every column — profile with `EXPLAIN ANALYZE`. `ANALYZE` after bulk insert/migration (stale stats pick wrong plans).
- `WHERE x LIKE '%term%'` is banned (kills B-tree) → use `pg_trgm` GIN.

## RLS — tenant-leading (Security Reviewer VETO)
Mandatory on every tenant-scoped table, but a **safety net, not the primary boundary**.
```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_orders ON orders USING (tenant_id = current_setting('app.tenant_id')::uuid);
```
```typescript
// preHandler hook, transaction-local, cleared at tx end
await db.query("SELECT set_config('app.tenant_id', $1, true)", [req.tenantId]);
```
- `tenant_id` MUST come from the verified JWT claim — **never from the request body** (a real lesson: a cross-tenant write CVE came from trusting the body). See `auth-and-access`, `security-baseline` (four-layer input validation).
- For the policy to be index-usable, the index leading column must be `tenant_id`. `EXPLAIN (ANALYZE, BUFFERS)` to confirm `Index Scan`, not `Seq Scan + Filter`.
- Bypass RLS only via a privileged service role (cross-tenant backfill, the metric engine); its key lives in a managed secret store. Never unset RLS.

## Connection pooling (CRITICAL)
| Pooler | Port | When |
|---|---|---|
| Transaction | 6543 | API request paths (short, stateless). No prepared statements / `LISTEN/NOTIFY` / session state. |
| Session | 5432 | Migrations, multi-statement transactions, `LISTEN/NOTIFY`. |
Services use the transaction pooler for RPC paths; migrations via the session pooler. **`connection_limit` per pod**; each pod owns its own pool — don't share across processes. The OLAP client uses HTTP keep-alive, no pool needed.

## Migration discipline
One migration per PR, never bundle · idempotent (`IF NOT EXISTS`/`OR REPLACE`) · backwards-compatible: add column nullable → backfill → `NOT NULL` later (two-phase, never single `ADD COLUMN NOT NULL`) · `CREATE INDEX CONCURRENTLY` in prod (not inside a tx) · no locking DDL in business hours · huge tables use `pg_repack`/batched UPDATE · check the generated down migration.

## Data access rules
- **No `SELECT *` in API code** — project columns (heap fetch without a covering index).
- Cursor pagination, never OFFSET (see `api-discipline`).
- **Money = integer minor units** (`spend_minor`, `gross_revenue_minor`) + a `currency_code` — never `numeric`/float (a real lesson; code-review blocker).
- `text` not `varchar(N)`; `citext` for case-insensitive (email). JSONB for flexible payloads but promote frequently-queried fields to a generated column + index.
- Batched DML (`INSERT ... ON CONFLICT DO UPDATE` via `UNNEST`, or `COPY` for bulk). N+1 ORM lazy-load → use JOIN/DataLoader.
- Concurrency: optimistic (`xmin`/`version`) on high-write paths; `FOR UPDATE NOWAIT` only when serialization is correctness-critical (e.g. consent transitions, scheduling). `pg_try_advisory_lock` for one-at-a-time jobs.

## Useful pg extensions
`pg_cron` (idempotency-key TTL cleanup, daily rollups, suppression-list refresh) · `pgvector` (where the product needs similarity/embedding search) · `pg_trgm` (fuzzy text search).

## Time + timezone (multi-tenant gotcha)
`NOW()`/`CURRENT_DATE` return server/UTC time, never tenant-local. "Today's total" is meaningless without naming whose today (a lived failure: a UTC `datetime('now')` showed an empty "today" to a user whose local day had already started). **Store each tenant's IANA timezone; scope every time-bucket query by it as a UTC range.** Store times as `timestamptz`, never text ISO. Read the tenant's timezone from the region/locale seam (`region-and-locale`), never hardcoded.
```sql
-- "today" in tenant tz as a UTC range
WITH bounds AS (
  SELECT date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone AS start_utc,
         (date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone + INTERVAL '1 day') AS end_utc
  FROM tenants t WHERE t.id = $1)
SELECT COALESCE(SUM(net_revenue),0) FROM orders, bounds
WHERE orders.tenant_id = $1 AND orders.ordered_at >= bounds.start_utc AND orders.ordered_at < bounds.end_utc;
```
The OLAP store has its own tz-aware date functions; always pass the IANA string, never bake it in.

## Query optimization — Postgres
1. Find it: `pg_stat_statements` ordered by `mean_exec_time`.
2. `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)`. Look for: `Seq Scan` on a large table → missing `(tenant_id, …)` index · `Sort` after scan → wrong column order (put `created_at DESC` in the index) · high "Rows Removed by Filter" → consider partial index · high `shared read` → cold cache (alert if cache hit ratio < 99%).
3. `CREATE INDEX CONCURRENTLY` — leading column always `tenant_id`.

## Query optimization — OLAP (deep patterns → clickhouse-olap)
- `tenant_id` first in `ORDER BY`; the query gateway rejects un-scoped queries.
- `EXPLAIN PIPELINE` — full scan means the PK prefix doesn't match the predicate; high read-rows = partition pruning failed.
- **Never aggregate in API handlers** — materialized views / scheduled rollups do the work; API reads the MV (sub-ms vs multi-second). `*State` in MVs, `*Merge` at read.
- `ReplacingMergeTree(version)` for idempotent ingestion; query via `FINAL` or a dedup MV (raw reads see both rows pre-merge).
- `PREWHERE` for very selective filters; never `SELECT *` on wide column-store tables.

## Monitoring
`pg_stat_statements`: `mean_exec_time > 500ms` & `calls > 100`/1h → page the Backend Engineer · pooler active-connections alert at 80% · cache hit ratio target > 99% (< 95% = memory pressure). `pg_stat_user_indexes` for unused/missing indexes. OLAP: `system.query_log`.

## Pre-endpoint checklist
- [ ] Index leads with `tenant_id` · [ ] EXPLAIN ANALYZE (PG) / EXPLAIN PIPELINE (OLAP) attached to PR · [ ] cursor pagination if list · [ ] `LIMIT` set (max 200, default 50) · [ ] no `SELECT *` · [ ] no OFFSET in prod · [ ] p95 measured in staging · [ ] OLAP query hits an MV, not raw.

## Wiring
Schema+migrations → Backend Engineer · RLS review → Security Reviewer + Architect · pooler config + slow-query alerting → Platform/SRE · OLAP MVs / vector indexes → AI/ML Engineer · pg_cron inventory → Platform/SRE.

Related: `clickhouse-olap`, `security-baseline`, `idempotency-handling`, `auth-and-access`, `api-discipline` (cursor pagination), `data-quality`.
