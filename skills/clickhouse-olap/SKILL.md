---
name: clickhouse-olap
description: Brain's ClickHouse OLAP patterns — MergeTree engine choice, primary-key ordering with workspace_id first, materialized view design, query gateway (pylibs/brain_clickhouse rejects un-scoped queries), partition strategy, late-data handling via ReplicatedReplacingMergeTree, sharding to 6 nodes at Phase 3. Auto-load whenever editing analytics-service, designing a new CH table or MV, or writing any ClickHouse query.
---

# ClickHouse OLAP — Brain Patterns

Brain's OLAP store. All dashboards read from ClickHouse; raw aggregates never run in API handlers. Owned operationally by Maya; Aryan reviews schema changes.

**Canonical doc:** `canon/technical-requirements.md`. This skill is operational.

## Invariants (NON-NEGOTIABLE)

1. **`workspace_id` is the FIRST column of primary key (`ORDER BY`)** on every workspace-scoped table
2. **Every query goes through `pylibs/brain_clickhouse.query()`** which rejects queries missing `workspace_id =` predicate at runtime
3. **`PARTITION BY toYYYYMM(occurred_at)`** for time-series tables; pruning is critical at scale
4. **`ReplicatedMergeTree` family** in all environments (HA + replay-safe)
5. **`ReplicatedReplacingMergeTree(ingested_at)`** when late-data updates matter (refunds, RTO state changes)
6. **No raw scans in API handlers** — pre-aggregated MVs or scheduled rollups only

## Engine choice

| Use case | Engine |
|---|---|
| Default fact table (orders, ads, shipments) | `ReplicatedMergeTree` |
| Late-data UPSERTs (refunds, RTO state, customer profile mirror) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Pre-aggregated rollups (daily_metrics, cohort_aggregates) | `ReplicatedReplacingMergeTree(computed_at)` |
| Append-only event archive (raw_*) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Materialized views | `MergeTree` (via `TO` target table — keep targets explicit) |

## Standard table template

```sql
CREATE TABLE orders_local ON CLUSTER brain_cluster (
  workspace_id            String,
  order_id                String,
  customer_id             String,
  occurred_at             DateTime64(3),                  -- order placed in Shopify
  ingested_at             DateTime64(3) DEFAULT now64(),  -- when we wrote it
  customer_order_number   UInt32,                          -- 1 = new customer
  total_minor             Int64,                           -- paisa
  discount_minor          Int64,
  tax_minor               Int64,                           -- GST
  shipping_minor          Int64,
  payment_method          LowCardinality(String),          -- 'cod' | 'prepaid'
  campaign_id             Nullable(String),                -- attribution
  pincode                 LowCardinality(String),
  status                  LowCardinality(String)
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (workspace_id, occurred_at, order_id)
SETTINGS index_granularity = 8192;
```

For sharded clusters, also create a `Distributed` engine table on top:

```sql
CREATE TABLE orders ON CLUSTER brain_cluster AS orders_local
ENGINE = Distributed(brain_cluster, default, orders_local, cityHash64(workspace_id));
```

Shard by `cityHash64(workspace_id)` so single-workspace queries hit one shard.

## Materialized view pattern (real-time aggregates from Kafka)

Pre-step: a Kafka engine table consumes from MSK; MV transforms into the target.

```sql
-- Source from Kafka
CREATE TABLE orders_queue (
  workspace_id            String,
  order_id                String,
  /* ... */
) ENGINE = Kafka()
SETTINGS
  kafka_broker_list = 'msk:9092',
  kafka_topic_list = 'integrations.orders.v1',
  kafka_group_name = 'analytics-orders-consumer',
  kafka_format = 'AvroConfluent',
  kafka_schema_registry_url = 'https://glue-schema-registry...',
  kafka_num_consumers = 4;

-- MV transform into the local table
CREATE MATERIALIZED VIEW orders_mv TO orders_local AS
SELECT
  workspace_id,
  order_id,
  customer_id,
  toDateTime64(occurred_at_ms / 1000, 3) AS occurred_at,
  /* ... */
FROM orders_queue;
```

For rollups (canon/technical-requirements.md):

```sql
CREATE MATERIALIZED VIEW daily_metrics_from_orders TO daily_metrics_local AS
SELECT
  workspace_id,
  toDate(occurred_at) AS date,
  'all'              AS customer_type,
  'all'              AS channel,
  sumState(total_minor)         AS revenue_net_minor,
  countState()                   AS orders_count,
  /* ... */
FROM orders_local
GROUP BY workspace_id, date;
```

Use `*State` aggregate functions in MVs; `*Merge` at read time for correct partial-aggregate merges across parts.

## Query gateway (the multi-tenant safety net)

```python
# pylibs/brain_clickhouse/query.py
import re

WORKSPACE_PREDICATE = re.compile(r"workspace_id\s*=", re.IGNORECASE)

class ClickHouseQueryError(Exception): pass

async def query(sql: str, params: dict):
    if not WORKSPACE_PREDICATE.search(sql):
        raise ClickHouseQueryError(
            f"CH query missing workspace_id predicate. SQL: {sql[:200]}..."
        )
    return await client.execute(sql, params)
```

**Every Python call to ClickHouse must go through `brain_clickhouse.query(...)`.** Bypass = security incident.

## Indian numbers (minor units — paisa)

All monetary fields are `Int64` in paisa. Never use `Decimal` or `Float`. Display layer (formatters) converts to `₹X,XX,XXX`.

## Partitioning + retention

- Partition by `toYYYYMM(occurred_at)` for most tables; `toYYYYMMDD(occurred_at)` for ultra-hot ones
- TTL policy: hot in CH for 24 months; older partitions moved to S3 via `BACKUP` + dropped from CH (Phase 3+)
- Mutations (UPDATE/DELETE): avoid; if needed, use `ALTER TABLE ... DELETE WHERE` and budget for merge time

## Sharding plan (canon/technical-requirements.md)

- Phase 0–2: 3 shards × 2 replicas
- Phase 3: scale to 6 shards × 2 replicas at 50K+ workspaces
- Shard key: `cityHash64(workspace_id)` — single-workspace queries hit one shard
- Cross-workspace queries (admin-only) explicitly route to all shards

## Late-data handling (canon/technical-requirements.md)

Refunds and RTO state changes arrive late (sometimes weeks). Pattern:

```sql
CREATE TABLE shipments_local (
  workspace_id      String,
  shipment_id       String,
  status            LowCardinality(String),
  occurred_at       DateTime64(3),
  ingested_at       DateTime64(3) DEFAULT now64(),
  is_deleted        UInt8 DEFAULT 0                 -- soft-delete tombstone for ReplacingMergeTree
) ENGINE = ReplicatedReplacingMergeTree(ingested_at, is_deleted)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (workspace_id, shipment_id);
```

`ingested_at` as version → latest update wins on merge. The **`is_deleted UInt8` column** is the ReplacingMergeTree tombstone — passed as the second engine arg so a later row with `is_deleted=1` removes the record on merge / under `FINAL` (filter `WHERE is_deleted = 0` on read). For FINAL-read performance set **`do_not_merge_across_partitions_select_final = 1`** so `FINAL` merges within each partition only (cheaper, valid because the partition key is part of the dedup scope here). Reconciliation MV recomputes daily_metrics after late-data window closes (canon/technical-requirements.md).

## Performance budgets

- Dashboard read: p95 < 100ms via MV; p95 < 500ms via on-demand query
- Cross-workspace admin query: best-effort
- Materialized view freshness: < 30 seconds for daily_metrics from `integrations.orders.v1`

## Data platform (isolated from transactional)

Heavy batch + ELT + transformation + forecasting work lives in the top-level **`data-platform/`** dir — NOT inside any frontend-facing or OLTP service. Analytics workloads MUST stay isolated from the transactional path so a long batch job can never contend with a Founder-facing dashboard read or a core-service mutation.

| Tool | Role |
|---|---|
| **dbt** | SQL transformations + tested models over ClickHouse (staging → marts); the canonical ELT layer |
| **Airflow / Dagster** | Orchestrate analytics DAGs (scheduled batch transforms, aggregations, forecasting refreshes) |
| **Spark** | Large batch/ELT where dbt-in-CH isn't enough (heavy cross-source joins, big backfills) |

Rules:
- **Isolation is the invariant:** data-platform jobs read raw/replica data and write back aggregates/marts — they never run in api-gateway, core-service, or any user-latency-critical path.
- **Airflow/Dagster live ONLY here** (analytics DAGs); analytics pipelines stay isolated from the transactional services. Do not put business sagas in Dagster.
- dbt models still respect `workspace_id`-first ordering + the multi-tenant invariants above.
- Forecasting (Prophet/sklearn/statsmodels) batch refreshes are scheduled here; the per-request serving stays in intelligence-service (see `forecasting-prophet`).

## Common failure modes

- **`workspace_id` not first in `ORDER BY`** — defeats sharding + scoping. Detection: DDL review.
- **Analytics batch job in a transactional service** — a long DAG/transform running inside core/api-gateway contends with user latency. Detection: heavy aggregation in a frontend-facing service. Move it to `data-platform/`.
- **API handler does `SELECT ... GROUP BY` on raw tables** — should be MV. Detection: code review on grpc handler.
- **Forgetting `ON CLUSTER` clauses** — table only exists on one node. Detection: subsequent inserts from MV fail.
- **MV reads from `Distributed` table** — double-aggregates. MVs always read from `_local`.
- **`*State` aggregate misuse** — using `sumState` where `sum` was intended produces unreadable blobs. Detection: query returns binary strings.
- **Bypassing query gateway** — direct `clickhouse_driver.Client.execute(sql)` skips workspace_id check. Detection: `grep -r "client.execute" apps/analytics-service/`.

## References

- `canon/technical-requirements.md` §clickhouse — canonical
- `canon/technical-requirements.md` — what MVs Brain runs
- `canon/technical-requirements.md` §india — GST-net-of, RTO-cost columns
- `skills/event-driven-kafka/SKILL.md` — Kafka engine table patterns
- `skills/python-services/SKILL.md` §clickhouse — `pylibs/brain_clickhouse` usage
- `skills/database-design/SKILL.md` — Postgres ↔ CH split principles
- `skills/forecasting-prophet/SKILL.md` — forecasting batch refreshes scheduled in data-platform/
