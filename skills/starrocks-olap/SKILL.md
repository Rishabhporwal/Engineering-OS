---
name: starrocks-olap
description: Reference implementation — StarRocks as the sub-second analytics-serving engine over an Iceberg lakehouse: external Glue/Iceberg catalogs, the table-model decision (Primary Key for CDC/upsert), async materialized-view serving, dbt-on-StarRocks, medallion, and the Iceberg→dbt→StarRocks→API one-way rule. Owner Data Engineer.
---

# StarRocks OLAP — Sub-Second Serving over the Lakehouse (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **analytics-serving seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — `STACK.md` may bind serving to StarRocks, ClickHouse (`clickhouse-olap` — sibling), or Apache Doris. The *patterns* — a derived serving copy over an open lakehouse SSOT, tenant-first modeling, materialize-don't-federate for QPS, MV partition-alignment, API-sole-path isolation — are what transfer; StarRocks is the example. **Anchor version: StarRocks 4.0 (GA 2025-10) / 4.1.**

StarRocks is an MPP SQL engine (MySQL protocol, cost-based optimizer, fast distributed joins) that both **queries Iceberg in place** and **serves sub-second, high-concurrency dashboards** from native columnar tables. In this stack it is the **derived serving layer**; the Iceberg lakehouse (`lakehouse-iceberg`) is the source of truth. **Owner:** Data Engineer (modeling + serving); AI/ML Engineer pairs on the analytics math; Platform/SRE on the cluster. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Iceberg is the SSOT; StarRocks is a rebuildable serving copy. The flow is one-directional: `Iceberg → dbt → StarRocks → Analytics API` — never StarRocks → Iceberg.** StarRocks 4.0 *can* now write Iceberg natively, so this is a **chosen guardrail, not a limitation**: it keeps the lakehouse open to every engine (Spark/Trino/Athena), keeps lineage clean, and avoids read-modify-write split-brain on the tables StarRocks serves. (Phase-3 exception: Silver/Gold marts may *migrate into* Iceberg written by Spark/Trino/dbt, which StarRocks then *reads back* — still no loop on its own serving tables.)
2. **Tenants NEVER get direct StarRocks credentials — the Analytics API is the only path.** The API holds tenant context and injects the `tenant_id` predicate on every query; a backstop row-filter (Apache Ranger or catalog-centric Lake Formation) enforces it again so an API bug can't leak. There is **no Postgres-style native row-policy DDL** in StarRocks (as of 4.0/4.1) — do not design around one (`multi-tenancy-isolation`).
3. **Pick the table model deliberately** — the single most consequential modeling call:
   | Model | Use for |
   |---|---|
   | **Duplicate Key** (default) | append-only/immutable facts (events, logs, Bronze-style) |
   | **Aggregate Key** | fixed pre-rollups you only query aggregated (Gold cubes) |
   | **Primary Key** | **CDC / upsert / mutable served data** — delete+insert via a PK index, 3–10× faster than Unique under updates; set `enable_persistent_index=true` + **partition the table** |
   | ~~Unique Key~~ | legacy merge-on-read — avoid for new designs unless you truly can't afford the PK index |
4. **Don't serve a high-QPS tenant API straight off Iceberg federation.** Direct external-catalog reads pay S3 scan + metadata listing and won't hold sub-second under concurrency. **Materialize** the serving slice — an async MV or a dbt-built native table.
5. **Partition-align every MV to its base Iceberg table** so refresh stays **partition-incremental**, not full. Bound it (`partition_ttl_number`, `auto_refresh_partitions_limit`, `partition_refresh_number`). Misaligned partitioning silently forces full refreshes.

## External Iceberg catalog (Glue + S3)
```sql
CREATE EXTERNAL CATALOG iceberg_glue PROPERTIES (
  "type"="iceberg", "iceberg.catalog.type"="glue",
  "aws.glue.use_instance_profile"="true", "aws.glue.region"="ap-south-1",
  "aws.s3.use_instance_profile"="true",   "aws.s3.region"="ap-south-1");
-- three-part name; query Bronze in place:
SELECT * FROM iceberg_glue.bronze.events WHERE tenant_id=? AND dt='2026-06-14';
```
For AWS S3 Tables / Glue Iceberg REST use `iceberg.catalog.type=rest` + the Glue Iceberg REST URI + `aws.s3.enable_sigv4=true` and authorize via **Lake Formation**.

## Async materialized view = the sub-second-serving primitive
An MV on the Iceberg external catalog materializes a native serving copy and **transparently rewrites** queries (even against the base table) to hit it:
```sql
CREATE MATERIALIZED VIEW gold_daily_revenue
DISTRIBUTED BY HASH(tenant_id)
PARTITION BY datekey                                 -- aligned to the base Iceberg partition
REFRESH ASYNC EVERY (INTERVAL 5 MINUTE)
PROPERTIES ("partition_refresh_number"="1","partition_ttl_number"="90",
            "auto_refresh_partitions_limit"="7","query_rewrite_consistency"="checked")
AS SELECT tenant_id, datekey, sum(amount_minor) AS revenue_minor, count(*) n
   FROM iceberg_glue.silver.orders GROUP BY tenant_id, datekey;
```
Partition-incremental refresh works for Iceberg from v3.1.4+ (partition transforms v3.2.3+). Money stays integer **minor units** (`metric-engine`).

## dbt-on-StarRocks (the medallion build)
`dbt-starrocks` (StarRocks ≥3.4 recommended) reads **Bronze-Iceberg via `source()` on the external catalog** and writes **Silver/Gold as StarRocks-native tables**:
```jinja
{{ config(materialized='incremental', table_type='PRIMARY', keys=['tenant_id','order_id'],
          partition_by=['order_date'], order_by=['order_date'],
          incremental_strategy='dynamic_overwrite',           -- idempotent partition replace
          properties={"enable_persistent_index":"true"}) }}
```
**Critical gotcha: the adapter has NO `MERGE`.** Upserts come from targeting a **Primary Key table** (the `INSERT` delts+inserts via the PK index); idempotent rebuilds come from **`dynamic_overwrite`** (partition replace), not append. Don't expect dbt's `merge` strategy. Pin the adapter+server versions (less battle-hardened than tier-1 adapters). Tests/lineage are standard dbt (`data-quality` is the gate).

```
S3+Iceberg(Glue)  BRONZE = raw immutable Iceberg
      └─ dbt-on-StarRocks (sources=iceberg_glue.bronze.*) ─┐
   SILVER = cleaned/conformed → StarRocks-native (PK for mutable)   Phase 1
   GOLD   = marts/rollups     → StarRocks-native (Agg / async MV)
      └─ Analytics API (tenant predicate) ── sole path for tenants
   Phase 3: Silver/Gold migrate INTO Iceberg + Athena/Trino + Spark; StarRocks reads them back
```

## Deployment: shared-nothing vs shared-data
**Shared-nothing** (FE+BE, local disk) for fixed, latency-critical footprints. **Shared-data** (FE+CN, data on S3, local disk = cache; v3.0+) for cloud-elastic, large, or multi-tenant-isolated workloads — scales compute independently and enables **multi-warehouse** CN isolation per workload/tenant tier. Cache-hit query perf ≈ shared-nothing; size the CN cache and lean on 4.0 file-bundling + metadata caching + compaction (≈90% fewer S3 API calls).

## Governance (catalog-centric is the 2026 convergence)
- **Apache Ranger** — row filters + column masking + ACLs, per external catalog (quirk: masking errors on table aliases).
- **StarRocks 4.0 catalog-centric access control** — the engine grants only catalog *usage*; fine-grained authz is delegated to the catalog backend (Iceberg-REST rules / **Lake Formation**), so **one policy set holds across StarRocks, Spark, and Trino** on the same Iceberg tables.
- Govern Bronze (+ Phase-3 Iceberg Gold) at the catalog with **Lake Formation FGAC**; govern StarRocks-native serving with Ranger/native RBAC **+ the API predicate**. Defense in depth.

## Effort-tier & cost note (`cost-routing-paradigms`, `finops-cost`)
Serving is **deterministic SQL** — the cheapest tier; never put an LLM on the serving path (the model only narrates pre-computed numbers — `metric-engine`). Cost levers: materialize the hot slice (don't federate per query), persistent PK index (RAM→disk), shared-data cache sizing, MV TTL, and bounded partition counts.

## Anti-patterns / pitfalls
Tablet/partition explosion → FE OOM (keep partitions ≲100k, ~1GB/tablet, TTL them) · a big high-churn **Primary Key table left non-partitioned or on the in-memory index** (set `enable_persistent_index=true`) · Unique-Key for a new upsert design (use PK) · **federating Iceberg as the QPS serving path** (materialize) · an MV not partition-aligned to its base (forces full refresh) · expecting dbt `merge` (use PK + `dynamic_overwrite`) · designing around a native row-policy DDL that doesn't exist (use API predicate + Ranger/LF) · a **read-modify-write loop** back into StarRocks' own served Iceberg tables · colocation joins with mismatched bucket key/count (silent shuffle) · shared-data with an undersized CN cache (cold S3 latency) · a tenant handed direct StarRocks access.

## 2026 market update
- **StarRocks 4.0 (Oct 2025)** added native **Iceberg writes** (INSERT INTO, hidden partitions, compaction API, metadata caching) + **catalog-centric access control** — making "never StarRocks→Iceberg" a deliberate guardrail and enabling one cross-engine policy set on Iceberg.
- **Pick StarRocks over ClickHouse** for **JOIN-heavy / sub-second-on-lakehouse / real-time-upsert (CDC) serving / high-concurrency multi-tenant dashboards** (CBO + colocated joins + PK model + native Iceberg). Pick **ClickHouse** for single-table scan-heavy log/metric analytics. **Apache Doris** is the close sibling (shared lineage, no-ZK, strong updates). Cross-vendor benchmark multipliers are vendor-run — treat as directional. Cross-link: `clickhouse-olap`, `lakehouse-iceberg`, `data-transformation-dbt`.
