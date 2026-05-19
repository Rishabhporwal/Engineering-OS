---
name: supabase-postgres-best-practices
description: Brain-tuned Postgres + Supabase patterns — workspace_id-leading indexes, RLS discipline, transaction vs session pooler, partial indexes, idempotency-key TTL, pg_cron jobs. Use when designing a new core-service table, when an RLS policy slows the query, when "tests pass locally, prod is slow", when configuring connection pooling, or when reviewing a Supabase migration.
---

# Supabase Postgres Best Practices

Brain's OLTP system of record is **Supabase Postgres**: workspaces, members, integrations config, goals, marketing actions, consent model, Decision Log, idempotency keys, audit. This skill is the Brain-specific shape of Supabase/Postgres performance + security rules.

**Companion skills:** `sql-query-optimization` (query-shape rules), `database-design` (schema decisions), `security-baseline` (RLS + multi-tenancy). This one focuses on the **Supabase + Brain combination**.

## Rule categories (priority order)

| Priority | Category | Impact | Owner |
|---|---|---|---|
| 1 | **Query performance** (indexes, EXPLAIN, prepared statements) | CRITICAL | Vikram |
| 2 | **Connection management** (transaction vs session pooler) | CRITICAL | Vikram + Jatin |
| 3 | **Security & RLS** (`workspace_id` leading; policy correctness) | CRITICAL | Shreya + Vikram |
| 4 | **Schema design** (UUIDs, timestamptz, native types) | HIGH | Aryan + Vikram |
| 5 | **Concurrency & locking** (`CREATE INDEX CONCURRENTLY`, advisory locks, FOR UPDATE NOWAIT) | MEDIUM-HIGH | Vikram |
| 6 | **Data access patterns** (cursor pagination, batched DML) | MEDIUM | Vikram |
| 7 | **Monitoring & diagnostics** (pg_stat_statements, slow query log) | LOW-MEDIUM | Jatin |
| 8 | **Advanced features** (pg_cron, pgvector, RLS bypass via service_role) | LOW | per use case |

## P1 — Query performance

See `sql-query-optimization` for the full set. Brain-specific reminders:

- **Every multi-tenant index starts with `workspace_id`** — RLS predicates always include it; without leading, the planner Seq-Scans.
- **Composite indexes match the query**: `(workspace_id, created_at DESC, id)` for paginated "list recent" patterns.
- **No `SELECT *` in API code.** Project the columns. Postgres still fetches the row from the heap if you don't have a covering index.
- **Cursor pagination, never OFFSET.** Banned in prod paths.

## P2 — Connection management (Supabase specifics)

Supabase exposes two pooler endpoints:

| Pooler | Port | When |
|---|---|---|
| **Transaction** | 6543 | Default for API requests. Short, stateless queries. **Cannot use prepared statements**, listen/notify, or session state. |
| **Session** | 5432 | Long-running connections that need session state — migrations, Prisma `$transaction([...])`, `LISTEN/NOTIFY`. |

Brain services use the **transaction pooler** for tRPC + gRPC request paths. Prisma is configured for `pgbouncer` mode. Migrations run via the session pooler.

```env
# .env (api-gateway, core-service)
DATABASE_URL="postgres://...@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=20"
DIRECT_URL="postgres://...@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
```

**`connection_limit` per pod = 20** (Brain default). Per replica, with 10 replicas, that's 200 connections — well within Supabase's pool budget. Don't share across processes; each EKS pod has its own.

## P3 — Security & RLS (Shreya VETO territory)

### RLS is mandatory on every workspace-scoped table

```sql
-- Every table gets this. No exceptions.
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY rls_orders ON orders
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

### `workspace_id` is set per-request from the JWT

```typescript
// preHandler hook on every tRPC request
await db.query("SELECT set_config('app.workspace_id', $1, true)", [req.workspaceId]);
// `true` = transaction-local; cleared at the end of the connection's tx
```

Brain rule: **`workspace_id` MUST come from `app_metadata.workspace_id` in the verified JWT** (see `session-management`, `defense-in-depth-validation`). Never from request body. Slice-3 caught a CVE-class cross-tenant write that came from this exact anti-pattern.

### RLS performance: leading column

For RLS predicates to be index-usable, the index leading column must be `workspace_id`. EXPLAIN ANALYZE the policy-augmented query to verify the planner picks the index.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE id = 'some-uuid';
-- Look for: Index Scan using idx_orders_workspace_id_id_pkey
-- NOT:      Seq Scan + Filter
```

### Bypass RLS only via service_role (admin paths)

Some background jobs (data backfill, the metric engine running across workspaces) need to bypass RLS. Use the **`service_role` key**, NEVER unset RLS.

```typescript
// Only in trusted server-side admin paths
const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
```

The `service_role` key lives in AWS Secrets Manager. Never in env files. Never in client code.

## P4 — Schema design (Brain canon)

- **UUIDs** for every primary key (`uuid_generate_v4()` or app-side `ulid()`). Sequential ids leak rate-of-creation info between tenants.
- **`timestamptz`** for every timestamp. Never `timestamp without tz`. The slice-1 lesson is in `.engineering-os/lessons-learned.md` — timezone bugs eat a quarter of debug time.
- **Integer minor units** for money (`spend_minor`, `gross_revenue_minor`) — no `numeric(15,2)` floats; matches the lesson on `spend_minor` from slice-3.
- **JSONB for flexible payloads** (Decision Log payload, integration config), but **promote frequently-queried JSON fields to columns** with a generated column + index.
- **`text` not `varchar(N)`** — Postgres treats them identically and `text` avoids accidental truncation bugs.
- **`citext`** for case-insensitive (email, username).

## P5 — Concurrency

### Indexing without blocking writes

```sql
-- ALWAYS in prod. Never inside a migration transaction.
CREATE INDEX CONCURRENTLY idx_orders_ws_created
  ON orders (workspace_id, created_at DESC);
```

### Optimistic vs pessimistic

For Brain's high-write paths (ingestion, Decision Log), prefer **optimistic concurrency** with `xmin` or a `version` column. Use `FOR UPDATE NOWAIT` only when serialization is correctness-critical (consent transitions, AI calling scheduling — Maya + Shreya territory).

### Advisory locks (for once-at-a-time jobs)

```sql
-- Make sure only one process runs the daily rollup
SELECT pg_try_advisory_lock(hashtext('daily_rollup_2026_05_13'));
```

Used by Brain's scheduled jobs (EventBridge → service → advisory lock → run).

## P6 — Data access patterns

- **Cursor pagination** for every list endpoint (see `api-pagination`)
- **Batched DML** — `INSERT ... ON CONFLICT ... DO UPDATE` with multi-row VALUES, or `COPY` for bulk loads
- **`returning *` discipline** — only when needed; otherwise return nothing

```sql
-- Bulk upsert for Maya's ingestion
INSERT INTO orders (workspace_id, order_id, gross_revenue_minor, ...)
SELECT * FROM UNNEST($1::uuid[], $2::text[], $3::bigint[], ...)
ON CONFLICT (workspace_id, order_id) DO UPDATE
  SET gross_revenue_minor = EXCLUDED.gross_revenue_minor,
      updated_at          = NOW();
```

## P7 — Monitoring (Jatin + Vikram)

### pg_stat_statements (enabled by default in Supabase)

```sql
SELECT query, mean_exec_time, calls, max_exec_time
FROM pg_stat_statements
WHERE userid = (SELECT oid FROM pg_roles WHERE rolname = current_user)
ORDER BY mean_exec_time DESC
LIMIT 20;
```

Brain alerts: any query with `mean_exec_time > 500ms` and `calls > 100` over 1h → page Vikram (it's blowing the BFF latency budget).

### Connection pool saturation

CloudWatch metric: PgBouncer active connections. Alert at 80% pool capacity.

### Cache hit ratio

```sql
SELECT
  sum(blks_hit)::float / NULLIF(sum(blks_hit + blks_read), 0) AS cache_hit_ratio
FROM pg_stat_database;
```

Target: > 99%. Below 95% suggests memory pressure — talk to Supabase about instance size.

## P8 — Advanced features Brain uses

- **`pg_cron`** for idempotency-key cleanup, daily rollups, NCPR cache refresh
- **`pgvector`** for the Memory Layer (Brand Fingerprint, Customer Segment Memory, Seasonal Codebook — see canon/BRAIN_TECHNICAL.md)
- **`pg_trgm`** for fuzzy customer-name search (replaces banned `LIKE '%term%'`)
- **`citext`** for case-insensitive lookups

## Migration discipline

- **One migration per PR** — never bundle schema changes
- **Idempotent**: `IF NOT EXISTS`, `IF EXISTS`, `OR REPLACE`
- **No locking DDL during business hours** — schedule `ALTER TABLE ... ADD COLUMN NOT NULL` for the maintenance window OR use the two-phase pattern (nullable column → backfill → SET NOT NULL CONCURRENT)
- **Always `CREATE INDEX CONCURRENTLY`** in prod (cannot be inside a transaction)
- **Roll-back script** for every migration (Prisma generates these; check the down migration)

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Schema + migrations for core-service | **Vikram** | canon/BRAIN_TECHNICAL.md (OLTP design) |
| RLS policy review | **Shreya** + Aryan | canon/BRAIN_TECHNICAL.md (multi-tenancy) |
| Connection pooler config | **Jatin** + Vikram | canon/BRAIN_TECHNICAL.md (connection) |
| Slow query alerting | **Jatin** | `observability` |
| Memory Layer (pgvector) | **Maya** | canon/BRAIN_TECHNICAL.md |
| pg_cron job inventory | **Jatin** | scheduled tasks doc |

Related Brain skills: `sql-query-optimization` (query-shape rules), `database-design` (schema decisions), `security-baseline` (RLS + secret handling), `idempotency-handling` (key TTL + cleanup), `session-management` (`workspace_id` from JWT into `app.workspace_id` GUC).
