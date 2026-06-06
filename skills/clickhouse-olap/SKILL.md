---
name: clickhouse-olap
description: A ClickHouse OLAP binding — MergeTree engines, tenant-first ORDER BY, materialized views, a query gateway, partitioning, late-data via ReplacingMergeTree, sharding plan.
---

# ClickHouse OLAP — Reference Patterns

> **Reference implementation.** This skill documents one concrete binding of the OLAP seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind analytics to a different store. The *patterns* here (tenant-first ORDER BY, a query gateway that enforces tenant scoping, MVs over raw scans, late-data via a versioned engine, integer minor-unit money) are what transfer, not ClickHouse itself.

In this binding ClickHouse is the OLAP store; all dashboards read from it, raw aggregates never run in API handlers. The AI/ML Engineer owns it operationally; the Architect reviews schema. Canon: `STACK.md` / LLD.

## Invariants (NON-NEGOTIABLE)
1. **The tenant key is the FIRST `ORDER BY` column** on every tenant-scoped table.
2. **Every query goes through the analytics query wrapper** — it rejects queries missing a tenant predicate at runtime.
3. **`PARTITION BY toYYYYMM(occurred_at)`** for time-series; pruning is critical at scale.
4. **`ReplicatedMergeTree` family** everywhere (HA + replay-safe).
5. **`ReplicatedReplacingMergeTree(ingested_at)`** when late-data updates matter (e.g. refunds, returns).
6. **No raw scans in API handlers** — pre-aggregated MVs or scheduled rollups only.

## Engine choice
| Use case | Engine |
|---|---|
| Default fact table (orders, events, shipments) | `ReplicatedMergeTree` |
| Late-data UPSERTs (refunds, state changes, profile mirror) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Pre-aggregated rollups (daily_metrics, cohort) | `ReplicatedReplacingMergeTree(computed_at)` |
| Append-only archive (raw_*) | `ReplicatedReplacingMergeTree(ingested_at)` |
| Materialized views | `MergeTree` via explicit `TO` target table |

## Standard table template
```sql
CREATE TABLE orders_local ON CLUSTER analytics_cluster (
  tenant_id      String,
  order_id       String,
  occurred_at    DateTime64(3),                  -- when it happened at the source
  ingested_at    DateTime64(3) DEFAULT now64(),  -- when we wrote it
  total_minor    Int64,                          -- integer minor units
  tax_minor      Int64,
  payment_method LowCardinality(String),
  region_code    LowCardinality(String),
  status         LowCardinality(String)
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (tenant_id, occurred_at, order_id)
SETTINGS index_granularity = 8192;
```
Sharded clusters add a `Distributed` table on top, sharded by `cityHash64(tenant_id)` so single-tenant queries hit one shard:
```sql
CREATE TABLE orders ON CLUSTER analytics_cluster AS orders_local
ENGINE = Distributed(analytics_cluster, default, orders_local, cityHash64(tenant_id));
```

## Materialized view pattern (real-time aggregates from Kafka)
A Kafka engine table consumes from the broker; an MV transforms into the target `_local`:
```sql
CREATE TABLE orders_queue (tenant_id String, order_id String /* ... */) ENGINE = Kafka()
SETTINGS kafka_broker_list='broker:9092', kafka_topic_list='integrations.orders.v1',
  kafka_group_name='analytics-orders-consumer', kafka_format='AvroConfluent',
  kafka_schema_registry_url='https://registry...', kafka_num_consumers=4;

CREATE MATERIALIZED VIEW orders_mv TO orders_local AS
SELECT tenant_id, order_id, toDateTime64(occurred_at_ms/1000, 3) AS occurred_at /* ... */ FROM orders_queue;

CREATE MATERIALIZED VIEW daily_metrics_from_orders TO daily_metrics_local AS
SELECT tenant_id, toDate(occurred_at) AS date,
  sumState(total_minor) AS revenue_net_minor, countState() AS orders_count
FROM orders_local GROUP BY tenant_id, date;
```
Use `*State` in MVs; `*Merge` at read time. **MVs always read from `_local`, never `Distributed`** (double-aggregates).

## Query gateway (multi-tenant safety net)
```python
# pylibs/analytics_clickhouse/query.py
TENANT_PREDICATE = re.compile(r"tenant_id\s*=", re.IGNORECASE)
async def query(sql, params):
    if not TENANT_PREDICATE.search(sql):
        raise ClickHouseQueryError(f"CH query missing tenant_id predicate. SQL: {sql[:200]}...")
    return await client.execute(sql, params)
```
**Every analytics CH call goes through the query wrapper. Bypass = security incident.**

## Money
All monetary fields `Int64` integer **minor units** — never `Decimal`/`Float`. The display layer formats per locale + `currency_code`.

## Partitioning + retention
Partition `toYYYYMM(occurred_at)` (`toYYYYMMDD` for ultra-hot). TTL: keep hot in CH for the active window; older partitions → object storage via `BACKUP` + dropped (later phases). Avoid mutations; if needed `ALTER TABLE … DELETE WHERE` and budget merge time.

## Sharding plan
Start with a small shard×replica count; grow the shard count at scale; shard key `cityHash64(tenant_id)`. On a managed CH offering, config-only — no self-hosting needed early. Cross-tenant (admin) queries explicitly route to all shards.

## Hosting ladder: managed → BYOC-first → self-host
Cost-best, not ops-maximalist — graduate only when a trigger fires.
- **Early phases = managed ClickHouse Cloud (in the required region):** clean for residency, idle-to-zero fits batch-spiky workloads, ops ≈ 0. Sharding stays config.
- **First graduation = BYOC** (data plane in the product's own cloud account, control plane vendor-managed) when sustained compute is large for several months, OR an in-account-residency contract is required, OR committed cloud spend beats the markup. VPC/PrivateLink → `devops-aws`.
- **Self-host (e.g. on Kubernetes via Altinity) only at large scale** — large/predictable/always-on + a named infra owner. Loaded TCO is a wash below a meaningful threshold — never graduate on bare infra cost alone.

**Cost lever:** idle-to-zero for dev/off-peak — but **keep prod CH warm before a scheduled batch window** (a cold start inside the window risks the SLO). **Lock-in mitigated** by the Kafka replay spine — every CH table is a downstream materialization of `integrations.*.v1`, so migration is a replay not an egress bill.

## Late-data handling
Late updates (e.g. refunds, returns) arrive weeks later. `ingested_at` as version → latest wins on merge; `is_deleted UInt8` is the ReplacingMergeTree tombstone (second engine arg; filter `WHERE is_deleted = 0` on read). For FINAL-read perf set `do_not_merge_across_partitions_select_final = 1`. A reconciliation MV recomputes daily_metrics after the late-data window closes.
```sql
ENGINE = ReplicatedReplacingMergeTree(ingested_at, is_deleted)
PARTITION BY toYYYYMM(occurred_at) ORDER BY (tenant_id, shipment_id);
```

## Performance budgets
Dashboard read p95 < 100ms via MV / < 500ms on-demand · MV freshness < 30s for daily_metrics from `integrations.orders.v1` · cross-tenant admin best-effort.

## Data platform (isolated from transactional)
Heavy batch + ELT + transformation + forecasting live in the top-level **`data-platform/`**, NOT in any frontend-facing or OLTP service — a long batch job must never contend with a dashboard read or an OLTP mutation.
| Tool | Role |
|---|---|
| **dbt** | tested SQL transforms over CH (staging → marts); canonical ELT |
| **Airflow / Dagster** | orchestrate analytics DAGs (live ONLY here; no business sagas) |
| **Spark** | large batch/ELT beyond dbt-in-CH (heavy joins, big backfills) |
dbt models still respect tenant-first ordering. Forecasting batch refreshes scheduled here; per-request serving stays in the intelligence service.

## Common failure modes
Tenant key not first in `ORDER BY` · analytics batch job in a transactional service (move to `data-platform/`) · API handler `SELECT … GROUP BY` on raw tables (should be MV) · forgetting `ON CLUSTER` · MV reading `Distributed` (double-aggregates) · `*State` misuse (unreadable blobs) · bypassing the query gateway (`grep -r "client.execute" apps/analytics-service/`).

## References
`STACK.md` / LLD §analytics + §region · `event-driven-kafka` (Kafka engine tables) · `python-services` (the analytics query wrapper) · `data-layer` (OLTP↔OLAP split).
