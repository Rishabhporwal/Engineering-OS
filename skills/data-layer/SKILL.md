---
name: data-layer
description: Brain's Postgres OLTP — schema conventions, workspace_id-leading RLS, indexes/partitioning, transaction-vs-session pooling, query optimization. ClickHouse → clickhouse-olap.
---

# Data Layer — Postgres OLTP + Query Optimization

Brain's split: **Supabase Postgres** = OLTP (workspaces, members, integrations config, goals, classifications, marketing actions, consent_event, audience, outreach, call, ticket, rfm_score, `ai.decision_log`, `ai.brand_fingerprint`+pgvector, idempotency_keys); **ClickHouse Cloud** = OLAP (see `clickhouse-olap`). CDC Postgres→Kafka via Debezium on MSK Connect. **No service queries another service's DB** — cross-service data flows via Kafka events or gRPC.

This playbook owns Postgres + query-shape rules for both engines. Schema/migration canon: `canon/technical-requirements.md`. RLS depth → `security-baseline`; key TTL → `idempotency-handling`; CH → `clickhouse-olap`.

## Naming + standard columns
- Tables `snake_case` plural; PK `id` (UUID v7 preferred, `bigserial` for hot-write loops).
- Tenant column is always **`workspace_id`** (UUID NOT NULL, indexed) on every workspace-scoped table.
- `created_at`/`updated_at` timestamptz default `now()`; soft delete `deleted_at` nullable only when business needs it.
```sql
CREATE TABLE <entities> (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id),
  external_id  text,
  occurred_at  timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, external_id)
);
CREATE INDEX idx_<entities>_ws_occurred ON <entities> (workspace_id, occurred_at DESC);
```

## Indexing rules (non-negotiable)
- **`workspace_id` is the FIRST column** of every multi-tenant index — RLS predicates always include it; the planner uses the index only if it leads.
- Composite beats multi-single for a query filtering both columns. Every FK has its own index (audit/decision-log JOINs fall over without).
- "list-recent" → `(workspace_id, created_at DESC)` composite (avoids a Sort after Index Scan).
- Partial indexes for sparse hot paths (`WHERE flag = true`). Don't index every column — profile with `EXPLAIN ANALYZE`. `ANALYZE` after bulk insert/migration (stale stats pick wrong plans).
- `WHERE x LIKE '%term%'` is banned (kills B-tree) → use `pg_trgm` GIN.

## RLS — workspace_id-leading (Shreya VETO)
Mandatory on every workspace-scoped table, but a **safety net, not the primary boundary**.
```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_orders ON orders USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
```typescript
// preHandler hook, transaction-local, cleared at tx end
await db.query("SELECT set_config('app.workspace_id', $1, true)", [req.workspaceId]);
```
- `workspace_id` MUST come from `app_metadata.workspace_id` in the verified JWT — **never from the request body** (slice-3 caught a cross-tenant write CVE from that). See `auth-and-access`, `defense-in-depth-validation`.
- For the policy to be index-usable, the index leading column must be `workspace_id`. `EXPLAIN (ANALYZE, BUFFERS)` to confirm `Index Scan`, not `Seq Scan + Filter`.
- Bypass RLS only via `service_role` (cross-workspace backfill, metric engine); key lives in Secrets Manager. Never unset RLS.

## Connection pooling (CRITICAL)
| Pooler | Port | When |
|---|---|---|
| Transaction | 6543 | API request paths (short, stateless). No prepared statements / `LISTEN/NOTIFY` / session state. |
| Session | 5432 | Migrations, `$transaction([...])`, `LISTEN/NOTIFY`. |
Services use transaction pooler (Prisma `pgbouncer` mode) for tRPC+gRPC; migrations via session pooler. **`connection_limit=20` per pod**; each EKS pod owns its own pool — don't share across processes. ClickHouse: `@clickhouse/client` / `clickhouse-driver` with HTTP keep-alive, no pool needed.

## Migration discipline (Prisma)
One migration per PR, never bundle · idempotent (`IF NOT EXISTS`/`OR REPLACE`) · backwards-compatible: add column nullable → backfill → `NOT NULL` later (two-phase, never single `ADD COLUMN NOT NULL`) · `CREATE INDEX CONCURRENTLY` in prod (not inside a tx) · no locking DDL in business hours · huge tables use `pg_repack`/batched UPDATE · check the generated down migration.

## Data access rules
- **No `SELECT *` in API code** — project columns (heap fetch without a covering index).
- Cursor pagination, never OFFSET (see `api-discipline`).
- **Money = integer minor units** (`spend_minor`, `gross_revenue_minor`) — never `numeric`/float (slice-3 lesson; code-review blocker).
- `text` not `varchar(N)`; `citext` for case-insensitive (email). JSONB for flexible payloads but promote frequently-queried fields to a generated column + index.
- Batched DML (`INSERT ... ON CONFLICT DO UPDATE` via `UNNEST`, or `COPY` for bulk). N+1 ORM lazy-load → use JOIN/DataLoader.
- Concurrency: optimistic (`xmin`/`version`) on high-write paths; `FOR UPDATE NOWAIT` only when serialization is correctness-critical (consent transitions, call scheduling). `pg_try_advisory_lock` for one-at-a-time jobs.

## pg extensions Brain uses
`pg_cron` (idempotency-key TTL cleanup, daily rollups, NCPR refresh) · `pgvector` (Memory Layer: Brand Fingerprint, Segment Memory, Seasonal Codebook) · `pg_trgm` (fuzzy customer-name search).

## Time + timezone (multi-tenant gotcha)
`NOW()`/`CURRENT_DATE` return server/UTC time, never tenant-local. "Today's revenue" is meaningless without naming whose today (lived failure: a UTC `datetime('now')` showed empty "today" to an IST user at 9am). **Store each tenant's IANA timezone; scope every time-bucket query by it as a UTC range.** Store times as `timestamptz`, never text ISO. Brain default IST (`Asia/Kolkata`) but always read from the workspace RegionAdapter, never hardcoded.
```sql
-- "today" in tenant tz as a UTC range
WITH bounds AS (
  SELECT date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone AS start_utc,
         (date_trunc('day', NOW() AT TIME ZONE t.timezone) AT TIME ZONE t.timezone + INTERVAL '1 day') AS end_utc
  FROM workspaces t WHERE t.id = $1)
SELECT COALESCE(SUM(net_revenue),0) FROM orders, bounds
WHERE orders.workspace_id = $1 AND orders.ordered_at >= bounds.start_utc AND orders.ordered_at < bounds.end_utc;
```
ClickHouse: `toDate(ordered_at, {tz:String})` does the math; always pass the IANA string, never bake it in.

## Query optimization — Postgres
1. Find it: `pg_stat_statements` ordered by `mean_exec_time` (enabled in Supabase).
2. `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)`. Look for: `Seq Scan` on a large table → missing `(workspace_id, …)` index · `Sort` after scan → wrong column order (put `created_at DESC` in the index) · high "Rows Removed by Filter" → consider partial index · high `shared read` → cold cache (alert if cache hit ratio < 99%).
3. `CREATE INDEX CONCURRENTLY` — leading column always `workspace_id`.

## Query optimization — ClickHouse (deep patterns → clickhouse-olap)
- `workspace_id` first in `ORDER BY`; query gateway (`pylibs/brain_clickhouse`) rejects un-scoped queries.
- `EXPLAIN PIPELINE` — full scan means the PK prefix doesn't match the predicate; high `ReadFromMergeTree` rows = partition pruning failed.
- **Never aggregate in API handlers** — materialized views / scheduled rollups do the work; API reads the MV (sub-ms vs multi-second). `*State` in MVs, `*Merge` at read.
- `ReplacingMergeTree(version)` for idempotent ingestion; query via `FINAL` or a dedup MV (raw reads see both rows pre-merge).
- `PREWHERE` for very selective filters; never `SELECT *` on wide column-store tables.

## Monitoring
`pg_stat_statements`: `mean_exec_time > 500ms` & `calls > 100`/1h → page Vikram · PgBouncer active connections alert at 80% · cache hit ratio target > 99% (< 95% = memory pressure). `pg_stat_user_indexes` for unused/missing indexes. CH: `system.query_log`.

## Pre-endpoint checklist (Vikram / Maya)
- [ ] Index leads with `workspace_id` · [ ] EXPLAIN ANALYZE (PG) / EXPLAIN PIPELINE (CH) attached to PR · [ ] cursor pagination if list · [ ] `LIMIT` set (max 200, default 50) · [ ] no `SELECT *` · [ ] no OFFSET in prod · [ ] p95 measured in staging (k6) · [ ] CH query hits an MV, not raw.

## Wiring
core-service schema+migrations → Vikram · RLS review → Shreya+Aryan · pooler config + slow-query alerting → Jatin · Memory Layer pgvector + CH MVs → Maya · pg_cron inventory → Jatin.

Related: `clickhouse-olap`, `security-baseline`, `idempotency-handling`, `auth-and-access`, `api-discipline` (cursor pagination), `data-quality`.
