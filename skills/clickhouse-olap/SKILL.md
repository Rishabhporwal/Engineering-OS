---
name: clickhouse-olap
description: Brain's ClickHouse OLAP — MergeTree engines, workspace_id-first ORDER BY, materialized views, query gateway, partitioning, late-data via ReplacingMergeTree, sharding plan.
---

# ClickHouse OLAP — Brain Patterns

Brain's OLAP store; all dashboards read from CH, raw aggregates never run in API handlers. Maya owns operationally; Aryan reviews schema. Canon: `canon/technical-requirements.md`.

## Invariants (NON-NEGOTIABLE)
1. **`workspace_id` is the FIRST `ORDER BY` column** on every workspace-scoped table.
2. **Every query goes through `pylibs/brain_clickhouse.query()`** — rejects queries missing a `workspace_id =` predicate at runtime.
3. **`PARTITION BY toYYYYMM(occurred_at)`** for time-series; pruning is critical at scale.
4. **`ReplicatedMergeTree` family** everywhere (HA + replay-safe).
5. **`ReplicatedReplacingMergeTree(ingested_at)`** when late-data updates matter (refunds, RTO).
6. **No raw scans in API handlers** — pre-aggregated MVs or scheduled rollups only.

## Engine choice
| Use case | Engine |
|---|---|
| Default fact table (orders, ads, shipments) | `ReplicatedMergeTree` |
| Late-data UPSERTs (refunds, RTO state, profile mirror) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Pre-aggregated rollups (daily_metrics, cohort) | `ReplicatedReplacingMergeTree(computed_at)` |
| Append-only archive (raw_*) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Materialized views | `MergeTree` via explicit `TO` target table |

## Standard table template
```sql
CREATE TABLE orders_local ON CLUSTER brain_cluster (
  workspace_id   String,
  order_id       String,
  occurred_at    DateTime64(3),                  -- placed in Shopify
  ingested_at    DateTime64(3) DEFAULT now64(),  -- when we wrote it
  total_minor    Int64,                          -- paisa
  tax_minor      Int64,                          -- GST
  payment_method LowCardinality(String),         -- 'cod' | 'prepaid'
  pincode        LowCardinality(String),
  status         LowCardinality(String)
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (workspace_id, occurred_at, order_id)
SETTINGS index_granularity = 8192;
```
Sharded clusters add a `Distributed` table on top, sharded `cityHash64(workspace_id)` so single-workspace queries hit one shard:
```sql
CREATE TABLE orders ON CLUSTER brain_cluster AS orders_local
ENGINE = Distributed(brain_cluster, default, orders_local, cityHash64(workspace_id));
```

## Materialized view pattern (real-time aggregates from Kafka)
A Kafka engine table consumes from MSK; an MV transforms into the target `_local`:
```sql
CREATE TABLE orders_queue (workspace_id String, order_id String /* ... */) ENGINE = Kafka()
SETTINGS kafka_broker_list='msk:9092', kafka_topic_list='integrations.orders.v1',
  kafka_group_name='analytics-orders-consumer', kafka_format='AvroConfluent',
  kafka_schema_registry_url='https://glue...', kafka_num_consumers=4;

CREATE MATERIALIZED VIEW orders_mv TO orders_local AS
SELECT workspace_id, order_id, toDateTime64(occurred_at_ms/1000, 3) AS occurred_at /* ... */ FROM orders_queue;

CREATE MATERIALIZED VIEW daily_metrics_from_orders TO daily_metrics_local AS
SELECT workspace_id, toDate(occurred_at) AS date,
  sumState(total_minor) AS revenue_net_minor, countState() AS orders_count
FROM orders_local GROUP BY workspace_id, date;
```
Use `*State` in MVs; `*Merge` at read time. **MVs always read from `_local`, never `Distributed`** (double-aggregates).

## Query gateway (multi-tenant safety net)
```python
# pylibs/brain_clickhouse/query.py
WORKSPACE_PREDICATE = re.compile(r"workspace_id\s*=", re.IGNORECASE)
async def query(sql, params):
    if not WORKSPACE_PREDICATE.search(sql):
        raise ClickHouseQueryError(f"CH query missing workspace_id predicate. SQL: {sql[:200]}...")
    return await client.execute(sql, params)
```
**Every Python CH call goes through `brain_clickhouse.query(...)`. Bypass = security incident.**

## Money
All monetary fields `Int64` paisa — never `Decimal`/`Float`. Display layer formats `₹X,XX,XXX`.

## Partitioning + retention
Partition `toYYYYMM(occurred_at)` (`toYYYYMMDD` for ultra-hot). TTL: hot in CH 24 months; older partitions → S3 via `BACKUP` + dropped (Phase 3+). Avoid mutations; if needed `ALTER TABLE … DELETE WHERE` and budget merge time.

## Sharding plan
Phase 0–2: 3 shards × 2 replicas · Phase 3: 6 shards × 2 replicas at 50K+ workspaces · shard key `cityHash64(workspace_id)`. Config under managed CH Cloud — no self-hosting needed. Cross-workspace (admin) queries explicitly route to all shards.

## Hosting ladder: managed → BYOC-first → self-host (canon TECH/00 §5)
Cost-best, not ops-maximalist — graduate only when a trigger fires.
- **Phase 0–3 = ClickHouse Cloud (managed, ap-south-1):** Mumbai is DPDP-clean; idle-to-zero fits the batch-spiky daily tick; ops ≈ 0. Phase-3 sharding stays (config).
- **First graduation = BYOC** (data plane in Brain's AWS, control plane in CH's) when sustained compute ≥ ~$6K/mo for 3 months, OR in-account-residency contract, OR AWS committed-spend beats CH markup. VPC/PrivateLink → `devops-aws`.
- **Self-host on EKS (Altinity) only at Phase 4** — large/predictable/always-on (≥ ~$15–20K/mo) + a named infra owner. Loaded TCO is a wash below ~$6–8K/mo — never graduate on bare infra cost alone.

**Cost lever:** idle-to-zero for dev/off-peak — but **keep prod CH warm before the 06:55–07:20 IST daily tick** (a cold start inside the window risks the Morning Brief SLO). **Lock-in mitigated** by the Kafka/MSK replay spine — every CH table is a downstream materialization of `integrations.*.v1`, so migration is a replay not an egress bill.

## Late-data handling
Refunds + RTO arrive late (weeks). `ingested_at` as version → latest wins on merge; `is_deleted UInt8` is the ReplacingMergeTree tombstone (second engine arg; filter `WHERE is_deleted = 0` on read). For FINAL-read perf set `do_not_merge_across_partitions_select_final = 1`. Reconciliation MV recomputes daily_metrics after the late-data window closes.
```sql
ENGINE = ReplicatedReplacingMergeTree(ingested_at, is_deleted)
PARTITION BY toYYYYMM(occurred_at) ORDER BY (workspace_id, shipment_id);
```

## Performance budgets
Dashboard read p95 < 100ms via MV / < 500ms on-demand · MV freshness < 30s for daily_metrics from `integrations.orders.v1` · cross-workspace admin best-effort.

## Data platform (isolated from transactional)
Heavy batch + ELT + transformation + forecasting live in the top-level **`data-platform/`**, NOT in any frontend-facing or OLTP service — a long batch job must never contend with a Founder dashboard read or a core-service mutation.
| Tool | Role |
|---|---|
| **dbt** | tested SQL transforms over CH (staging → marts); canonical ELT |
| **Airflow / Dagster** | orchestrate analytics DAGs (live ONLY here; no business sagas) |
| **Spark** | large batch/ELT beyond dbt-in-CH (heavy joins, big backfills) |
dbt models still respect `workspace_id`-first ordering. Forecasting batch refreshes scheduled here; per-request serving stays in intelligence-service (`forecasting-prophet`).

## Common failure modes
`workspace_id` not first in `ORDER BY` · analytics batch job in a transactional service (move to `data-platform/`) · API handler `SELECT … GROUP BY` on raw tables (should be MV) · forgetting `ON CLUSTER` · MV reading `Distributed` (double-aggregates) · `*State` misuse (unreadable blobs) · bypassing query gateway (`grep -r "client.execute" apps/analytics-service/`).

## References
`canon/technical-requirements.md` §clickhouse + §india · `event-driven-kafka` (Kafka engine tables) · `python-services` (`pylibs/brain_clickhouse`) · `data-layer` (Postgres↔CH split) · `forecasting-prophet`.
