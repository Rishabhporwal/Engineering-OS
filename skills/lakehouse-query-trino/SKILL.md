---
name: lakehouse-query-trino
description: Reference implementation — interactive + federated SQL over the Iceberg lakehouse with Trino (self-managed on EKS) and AWS Athena (serverless). The ad-hoc/exploration + cross-source-join tier — distinct from StarRocks sub-second serving and Spark heavy batch. Bytes-scanned is the cost; tenant-predicate + Lake Formation the isolation. Owner Data Engineer.
---

# Lakehouse Query — Trino + Athena (Reference Patterns)

> **Reference implementation.** One concrete binding of the **interactive-query / federation seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — `STACK.md` may bind it to Trino, Athena (serverless Presto-derived), Spark SQL, or DuckDB. The *patterns* — engine-on-the-lakehouse via the catalog, partition-pruned columnar reads, bytes-scanned cost discipline, tenant predicate + catalog FGAC, and CTAS-to-scratch (never write back into the served tables) — transfer; Trino + Athena is the example.

This is the **explore + federate** tier: analyst ad-hoc SQL, cross-source joins (Iceberg + Postgres + others), one-off backf-investigation, and the engine behind a notebook or BI tool. It is **not** the low-latency tenant-facing serving path (that's `starrocks-olap`) and **not** the scheduled heavy-ELT path (that's `batch-processing-spark` / `data-transformation-dbt`). **Owner:** Data Engineer; Platform/SRE runs the Trino cluster. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Pick the engine by workload, not habit.** **Athena** = serverless, **per-TB-scanned** pricing, zero ops → spiky/low-volume/exploratory queries and "I don't want to run a cluster." **Trino on EKS** = you pay for worker time → predictable cost at *sustained* concurrency, federation across many connectors, and big batch-y queries via **fault-tolerant execution**. **Neither is the sub-second serving path** — a high-QPS tenant dashboard belongs on StarRocks, not on per-query Athena scans.
2. **Cost is bytes scanned (Athena) / worker-time (Trino).** A full-table S3 scan is a money *and* latency bug. Always: columnar **Parquet + compression**, **partition pruning** (Iceberg hidden partitioning + predicates that hit them), **Athena partition projection** to skip Glue partition listing, and `SELECT` only the columns you need. Treat `bytes_scanned`/query-cost as a reviewable metric (`finops-cost`).
3. **Every query is tenant-scoped — predicate + a catalog backstop.** Analysts/services query with the `tenant_id` predicate (cross-tenant read = P0, `multi-tenancy-isolation`); tenants never get direct engine credentials — the Analytics API or a governed analyst seat only. **Know your engine's enforcement:** **Athena enforces AWS Lake Formation FGAC natively** (column/row/cell), so a per-tenant LF row filter is a real backstop. **OSS Trino does NOT enforce Lake Formation** (it does neither policy enforcement nor credential vending — confirmed open issue #28609) — on self-managed Trino enforce with **Apache Ranger**, or route governed access through **Athena/EMR/Starburst**. Don't assume "Trino + LF" works; it doesn't on OSS.
4. **Read the lakehouse; don't write back into it from ad-hoc queries.** CTAS/INSERT goes to a **scratch/sandbox namespace**, never into Bronze/Silver/Gold — preserve the one-way `Iceberg → dbt → serving` flow (`lakehouse-iceberg`, `starrocks-olap`). Promote a useful exploration into a real dbt model, don't leave it as a hand-written table.
5. **Small files kill both engines.** Query performance + S3 LIST/GET cost degrade on uncompacted Iceberg. Compaction/snapshot-expiry is the lakehouse's scheduled job (`lakehouse-iceberg` / `pipeline-orchestration`), not something you fix per query — but a slow Trino/Athena query is often the symptom.

## Trino — Iceberg over Glue (EKS)
```properties
# catalog/iceberg.properties
connector.name=iceberg
iceberg.catalog.type=glue
hive.metastore.glue.region=ap-south-1
fs.native-s3.enabled=true
s3.region=ap-south-1
iceberg.register-table-procedure.enabled=false   # don't let ad-hoc register tables into prod
```
- Run coordinator + autoscaled workers on EKS (Karpenter). Size worker memory + **enable spill** for big joins; use **fault-tolerant execution** (exchange to S3) for long batch-y queries so a lost worker doesn't fail the whole query.
- Federation: add a `postgresql` connector to join Iceberg facts against control-plane dims in one query — Trino's reason-to-exist over a single-store engine.

## Athena — serverless Iceberg
```sql
-- Athena has native Iceberg support over the Glue catalog; time-travel + partition pruning work.
SELECT tenant_id, sum(amount_minor) AS revenue_minor
FROM iceberg_db.gold_orders
WHERE tenant_id = ? AND occurred_at >= date '2026-06-01'   -- prune partitions
GROUP BY tenant_id;
-- FOR TIMESTAMP AS OF / FOR VERSION AS OF for time-travel; CTAS to a SCRATCH db only.
```
Cost discipline: partition projection (avoid Glue partition-listing), Parquet+zstd, workgroup **per-query bytes-scanned limits** + a `bytes_scanned_cutoff` guardrail, and result reuse. Govern with Lake Formation on the Glue tables.

## When Trino/Athena vs StarRocks vs DuckDB vs Spark
| Need | Engine |
|---|---|
| Sub-second, high-QPS tenant dashboard | **StarRocks** (materialized serving) |
| Ad-hoc analyst SQL, exploration, cross-source federation | **Trino / Athena** (this skill) |
| Spiky/low-volume, zero-ops, pay-per-query | **Athena** |
| Sustained concurrency / multi-source / big fault-tolerant queries | **Trino on EKS** |
| Embedded/in-process, single-node, light local analytics | **DuckDB** |
| Scheduled heavy ELT / model training feature builds | **Spark / dbt** |

## Effort-tier & cost note (`cost-routing-paradigms`, `finops-cost`)
Interactive SQL is deterministic compute; never put an LLM on the query path (the model narrates pre-computed numbers — `metric-engine`). The dominant cost lever is **scan reduction** (partitions + columns + compaction), then engine choice (Athena per-TB vs Trino worker-time) by concurrency shape. A recurring exploratory query that becomes load-bearing should be **promoted to a dbt model + StarRocks mart**, not left on per-query Athena cost.

## Anti-patterns
Putting a tenant-facing low-latency dashboard on per-query Athena scans (use StarRocks) · full-table scans (no partition/column pruning) · missing Athena partition projection (slow Glue listing) · a query without the tenant predicate or with no Lake-Formation backstop · CTAS/INSERT writing back into Bronze/Silver/Gold (breaks the one-way flow — use a scratch namespace) · ignoring small-files (slow queries + S3 LIST cost) · handing a tenant direct engine credentials · running a permanent ETL on ad-hoc Trino instead of scheduled Spark/dbt · no per-query bytes-scanned guardrail (runaway Athena bill).

## Ops gotchas (verified)
- **Athena DML is always merge-on-read** — `write.*.mode=copy-on-write` is silently ignored; plan for delete-file accumulation + schedule `OPTIMIZE`. Athena creates Iceberg **v2** tables. Time-travel syntax is `FOR TIMESTAMP/VERSION AS OF` (engine v3; the old `SYSTEM_TIME`/`SYSTEM_VERSION` is deprecated). Athena engine **v3 is Trino-based** but not full Trino (no arbitrary connectors, no fault-tolerant execution).
- **Trino config migration:** native S3 became default in **Trino 458 (Sep 2024)**, legacy `hive.s3.*` deprecated **470 (Feb 2025)** and may be **removed on current 481** — use `fs.native-s3.enabled=true` + `s3.*` (as above). Iceberg default file format flipped **ORC→Parquet in release 422**. Re-validate memory config on every upgrade (post-upgrade OOM regressions are common) and **run Iceberg writes on On-Demand, not Spot** (Spot-worker write-corruption reports).
- **Stats aren't auto-refreshed** — `ANALYZE` after big loads or the CBO plans blind. Trino time-travel reads through the **current** schema, not the snapshot's.

## 2026 market update
- **AWS S3 Tables (GA Dec 2024, matured 2025–26)** = fully-managed Iceberg on S3 with **automatic compaction / snapshot-expiry / orphan-removal**, auto-registered in Glue, queryable by Athena/Trino/EMR/Redshift/Spark. Same $5/TB Athena scan cost — the difference is *who runs maintenance*. (Some workloads report it pricier — verify against your access pattern.)
- **Iceberg v3 spec** (2024, adoption 2025–26): binary **deletion vectors** (kills write-amplification on GDPR-style deletes), **row lineage** (auditability), VARIANT/geo/nanosecond types. Athena still creates v2.
- **DuckLake** (GA, v1.0 ~2026) puts all table metadata in a SQL catalog DB (Postgres) → millisecond planning + no small-files problem; the catalog DB becomes a new SPOF.
- **StarRocks 4.0** matured into a serious lakehouse engine (native Iceberg writes, async MVs) — sharpening the split: **StarRocks serves, Trino/Athena federate + explore** (`starrocks-olap`).

## References
`lakehouse-iceberg` (the tables + compaction/maintenance) · `starrocks-olap` (the serving sibling — when to materialize instead) · `batch-processing-spark` / `data-transformation-dbt` (the heavy-ELT siblings) · `multi-tenancy-isolation` (tenant predicate; Athena-LF vs Trino-Ranger) · `finops-cost` (bytes-scanned/worker-cost) · `devops-aws` (Trino on EKS) · `pipeline-orchestration` (compaction jobs).
