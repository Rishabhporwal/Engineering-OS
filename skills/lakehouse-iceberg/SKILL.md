---
name: lakehouse-iceberg
description: Reference implementation — an open lakehouse on object storage + Apache Iceberg: ACID table format, hidden partitioning, schema/partition evolution, time-travel snapshots, MERGE upserts, compaction. The replayable system-of-record for raw + historical events and ML datasets.
---

# Lakehouse — S3 + Apache Iceberg (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **lakehouse / historical-store seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to a different table format (Delta Lake, Apache Hudi) or object store. The *patterns* here — an open ACID table format over cheap object storage, hidden partitioning, schema + partition evolution without rewrites, snapshot isolation + time-travel, and a single table queried by many engines — are what transfer; S3 + Iceberg is the example.

The lakehouse is the **replayable source of truth** for raw + historical events, the immutable Decision Log archive, and ML training datasets. Flink (`stream-processing-flink`) and Spark (`batch-processing-spark`) write it; Spark, Trino, and ClickHouse read it. **Owner:** Data Engineer; Architect reviews table layout. Canon: `STACK.md`.

## Why a table format (not just files)
Raw Parquet on object storage gives you cheap storage but no atomicity, no consistent reads under concurrent writes, no schema evolution, and full-rewrite partition changes. Iceberg adds **ACID commits, snapshot isolation, hidden partitioning, and metadata-pruned reads** on top of the same cheap files. That's the whole point.

## Invariants (NON-NEGOTIABLE)
1. **Tenant + time in the partition spec.** Partition by `tenant_id` (or region) and a time transform (`days(occurred_at)`). Reads prune to a tenant's partitions; a full-table scan to answer one tenant's query is a design bug.
2. **Hidden partitioning — never expose partition columns to queries.** Iceberg derives partitions from the transform; queries filter on the real column (`occurred_at`) and Iceberg prunes. No manual `dt=` string columns leaking into application SQL.
3. **Append/MERGE, never in-place file mutation.** Updates go through `MERGE INTO` (copy-on-write or merge-on-read); the old snapshot stays valid until expired. This is what makes reads consistent and time-travel possible.
4. **Snapshots are retained per the retention/compliance policy.** Time-travel + rollback need history; `COMPLIANCE.md` (retention + residency) sets how long and in which region. Snapshot expiry is a scheduled, audited job — not ad hoc.
5. **Region-pinned storage.** Each region's lakehouse lives in that region's bucket (`region-and-locale` residency seam). A cross-region read of raw events is a residency violation unless the Canon explicitly allows it.

## Schema & partition evolution (the headline feature)
```sql
ALTER TABLE analytics.events ADD COLUMN channel string;        -- no rewrite
ALTER TABLE analytics.events ALTER COLUMN amount_minor TYPE bigint;
ALTER TABLE analytics.events ADD PARTITION FIELD bucket(16, customer_id);  -- evolves; old data stays
```
- Add nullable columns freely; Iceberg tracks field IDs so renames/adds don't break old data (mirrors Avro BACKWARD compat in `event-driven-kafka`).
- **Partition evolution** changes layout for *new* data without rewriting old — no more "repartition the whole table" outages.

## MERGE upsert (late data, corrections)
```sql
MERGE INTO analytics.events t
USING staged s ON t.tenant_id = s.tenant_id AND t.event_id = s.event_id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```
Stable `event_id = (tenant_id, source, source_event_id)` makes corrections + late re-pulls idempotent (same key discipline as `event-driven-kafka` / `integration-connectors`).

## Time-travel & reproducibility
```sql
SELECT * FROM analytics.events VERSION AS OF 8273...;        -- by snapshot id
SELECT * FROM analytics.events FOR TIMESTAMP AS OF '2026-06-01 00:00:00';
```
- Training jobs (`ml-lifecycle`) pin the **snapshot ID** so a model is reproducible from the exact dataset state — no "the data changed under me."
- `ROLLBACK` to a prior snapshot recovers from a bad write without a restore.

## Maintenance (or it rots)
- **Compaction** (`rewrite_data_files`) merges the small files that streaming writes produce — skip it and read performance collapses. Schedule it.
- **Snapshot expiry** + **orphan-file cleanup** bound storage cost and enforce retention.
- **Manifest rewrite** keeps metadata-planning fast as the table grows.
These are scheduled jobs (the orchestration layer / `workflow-engine-temporal`), monitored like any other.

## Effort-tier & cost note (`cost-routing-paradigms`)
Object storage + an open format is the **cheapest durable tier** — keep raw/historical here, not in the OLTP or OLAP store. Query it directly with a batch/SQL engine; only materialize the hot, frequently-served slice into ClickHouse (`clickhouse-olap`). Storing replayable raw events here is what lets every downstream materialization be rebuilt for free.

## Anti-patterns
Raw Parquet with no table format (no ACID, no evolution) · exposing `dt=` partition columns to app queries · in-place file edits · never compacting (small-files death) · unbounded snapshot retention (cost + compliance breach) · cross-region reads of residency-pinned data · training off a moving table instead of a pinned snapshot.
