---
name: batch-processing-spark
description: Reference implementation — large-scale batch on Apache Spark: idempotent partition-overwrite jobs, model-training/reconciliation/backfill, broadcast joins + skew handling, the same logic as the stream path. Tenant-partitioned, replayable, cost-bounded.
---

# Batch Processing — Apache Spark (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **batch-compute seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind batch to a different engine (Spark on EMR/Glue/Databricks, Trino, Snowflake, plain SQL+dbt, Ray). The *patterns* here — idempotent re-runnable jobs, tenant-leading partitioning, broadcast/skew discipline, reconciliation against the live system, and parity with the streaming logic — are what transfer; Spark is the example.

Spark does the heavy, latency-tolerant work the stream path can't: **model-training feature builds, nightly reconciliation, historical rebuilds, backfills, large aggregations** over the lakehouse (`lakehouse-iceberg`). **Owner:** Data Engineer; ML feature/training jobs co-owned with the ML Platform Engineer. Canon: `STACK.md`.

> **Right-size the engine (2026) — Spark is no longer the automatic default.** Single-node engines now handle small-to-medium (and even hundreds-of-GB) workloads faster and cheaper: **Polars** (Rust dataframes), **DuckDB** (in-process, over Parquet/Iceberg/Delta — see `embedded-analytics-duckdb` if bound), and **Daft** (distributed Rust). Reach for Spark when the data is genuinely large or a Spark platform already exists; otherwise prefer the lighter engine. **Apache Arrow** is the shared memory layer; **Ray** for distributed Python/ML. The hybrid (Polars/DuckDB for light, Spark/Daft for heavy) is the emerging norm — the *patterns* in this skill (idempotent partition-overwrite, tenant-leading partitioning, reconciliation-as-oracle, point-in-time training data) transfer to whichever engine `STACK.md` binds.

## Invariants (NON-NEGOTIABLE)
1. **Every job is idempotent and re-runnable.** A re-run for the same logical date produces the same output. Use **dynamic partition overwrite** (`INSERT OVERWRITE` of `dt=YYYY-MM-DD` partitions) or an Iceberg `MERGE`/snapshot — never blind `append` (which double-counts on retry). A failed job is just re-run; no manual cleanup.
2. **Tenant-leading partitioning.** Output partitioned by `tenant_id`/region first, then date. Reads prune by tenant. (Mirrors `data-layer` / `clickhouse-olap` ORDER BY.)
3. **Reconciliation is a first-class job.** A scheduled job recomputes metrics from the lakehouse and diffs them against the serving store; a mismatch beyond tolerance raises a `data-quality` alarm. This is how the system proves the stream path is correct.
4. **Stream/batch parity.** Where a metric exists in both the Flink path and a Spark rebuild, both must compute it from the **single-source definition** (`metric-engine`) and agree within tolerance. The Spark rebuild is the oracle.
5. **Cost-bounded.** Every job declares expected input size + cluster shape; a job whose cost grows super-linearly with a tenant's data is a design bug, not an autoscaling problem.

## Idempotent write pattern
```python
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
(df.write
   .partitionBy("tenant_id", "dt")
   .mode("overwrite")          # overwrites ONLY the partitions present in df
   .format("iceberg")
   .save("warehouse.analytics.daily_metrics"))
```
For row-level upserts use Iceberg `MERGE INTO ... WHEN MATCHED UPDATE WHEN NOT MATCHED INSERT` (see `lakehouse-iceberg`).

## Performance discipline
- **Broadcast the small side** of a join (`broadcast(dim)`) when it fits; a shuffle join on a small dimension is wasted I/O.
- **Skew:** a hot tenant/key skews a shuffle → salt the key or use AQE skew-join (`spark.sql.adaptive.skewJoin.enabled=true`). Enable Adaptive Query Execution by default.
- **Partition sizing:** target ~128–256 MB per output file; `repartition`/`coalesce` to avoid the small-files problem (which then degrades every downstream read).
- **Predicate + partition pushdown:** read only the tenant/date partitions the job needs; never `select *` a full history when a window is enough.
- Cache only a DataFrame reused ≥2× and that fits; uncache when done.

## Training & feature builds (with ML Platform Engineer)
- Offline feature builds write to the **feature store** offline tables (`feature-store-feast`) with the SAME transformation the online/stream path uses — **online/offline skew is the cardinal ML-data sin**.
- Training reads a point-in-time-correct snapshot (Iceberg time-travel) so a model never trains on data that leaked from the future.
- Emit the dataset version + Iceberg snapshot ID into the model registry (`ml-lifecycle`) for reproducibility.

## Orchestration & operability
- Jobs are triggered by the workflow/orchestration layer (a scheduler or `workflow-engine-temporal` for dependency DAGs), not cron-on-a-box.
- Idempotent + partition-scoped ⇒ a late-arriving day is just a re-run of that date's partition (same code path as the original — mirrors `integration-connectors` late-data re-pull).
- Metrics: input rows, output rows, shuffle read/write, task failures, wall-clock vs budget. Alarm on a job exceeding its declared cost envelope.

## Effort-tier note (`cost-routing-paradigms`)
Batch aggregation/reconciliation is **deterministic compute** — the cheapest tier and the correctness oracle for everything above it. Don't push reconciliation or large aggregations into a model. Compute is cheap; an undetected metric drift is expensive.

## Anti-patterns
Blind `append` (double-counts on retry) · processing-then-overwriting the whole table to update one day · a backfill codebase separate from the regular job · ignoring skew until the job OOMs · small-files explosion · training on non-point-in-time data (future leakage) · online/offline feature skew.
