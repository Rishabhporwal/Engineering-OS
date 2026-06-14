---
name: data-transformation-dbt
description: Reference implementation — the SQL transformation layer (dbt / SQLMesh): modular models, staging→marts, tests + freshness assertions, column-level lineage, incremental + idempotent builds, the semantic layer. The governed "T" between raw and serving. Owner Data Engineer.
---

# Data Transformation — dbt / SQLMesh (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **transformation seam** — the "T" of ELT (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to dbt, **SQLMesh**, Dataform, or plain orchestrated SQL. The *patterns* — modular SQL models, a staging→marts layering, tests + freshness as gates, column-level lineage, incremental idempotent builds, and a single semantic definition of metrics — transfer; dbt is the example.

This is the governed layer between raw ingested data (`event-driven-kafka`, `integration-connectors`, `lakehouse-iceberg`) and the serving stores (`clickhouse-olap`, marts). It was the biggest missing seam in the stack: we ingest, land, and serve, but nothing owned the **transform-with-tests-and-lineage** step. **Owner:** Data Engineer; the AI/ML Engineer consumes the marts. Canon: `STACK.md`. SQLMesh is the credible alternative (Python-native, column-level lineage, virtual data environments, real unit tests) — earns its place at ~200+ models or when warehouse cost/quality is the pain.

## Invariants (NON-NEGOTIABLE)
1. **Layered, modular models.** `staging` (1:1 cleaned source, renamed/typed) → `intermediate` (joins/business logic) → `marts` (consumable, dimensional). No monolithic 500-line query; no marts reading raw directly.
2. **Tested — schema + data tests are gates.** Every model has tests (not-null, unique, accepted-values, relationships) + **freshness** assertions; CI runs them and **blocks on failure** (ties to `data-quality`). An untested transformation is an untrusted number.
3. **Idempotent, incremental builds.** Incremental models are re-runnable for a window without double-counting (merge/insert-overwrite on a stable key) — the same idempotency law as `batch-processing-spark`. A failed run is just re-run.
4. **Column-level lineage is queryable.** Every mart column traces to its sources. "Where does this KPI come from?" is answerable from the DAG, not tribal knowledge — and a source change's blast radius is visible before it ships.
5. **Metrics defined once (semantic layer).** A metric's definition lives in the semantic layer, computed identically wherever queried — the warehouse-side counterpart of `metric-engine`. Money stays integer minor units + currency.

## Project shape
```
models/
  staging/      stg_<source>__<entity>.sql     -- cleaned, typed, renamed; 1:1 with source
  intermediate/ int_<area>.sql                 -- joins + business logic
  marts/        <domain>/fct_*.sql, dim_*.sql  -- consumable facts + dimensions
  metrics/      (semantic layer definitions)
tests/ + schema.yml (tests, freshness, descriptions)   sources.yml (raw + freshness SLAs)
```
```sql
-- incremental, idempotent, tenant-partitioned
{{ config(materialized='incremental', unique_key=['tenant_id','order_id'],
          incremental_strategy='merge') }}
select tenant_id, order_id, amount_minor, currency_code, occurred_at
from {{ ref('stg_orders') }}
{% if is_incremental() %} where occurred_at > (select max(occurred_at) from {{ this }}) {% endif %}
```

## Tests + freshness (the gate)
```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id   { tests: [unique, not_null] }
      - name: tenant_id  { tests: [not_null] }
      - name: amount_minor { tests: [{dbt_utils.accepted_range: {min_value: 0}}] }
sources:
  - name: raw
    freshness: { warn_after: {count: 6, period: hour}, error_after: {count: 12, period: hour} }
```
Run `dbt build` (run + test) in CI on PRs against changed models (`--select state:modified+`); block on test/freshness failure. SQLMesh adds **virtual environments** so a PR's models are validated against prod data without touching prod.

## Operability
- Orchestrate via the data orchestrator (Dagster/Airflow) or `workflow-engine-temporal`; schedule + monitor `dbt build` + freshness like any job.
- Tenant-partition marts; residency-pin per `region-and-locale`; document every model (descriptions become the data catalog → `platform-engineering-idp`).
- Hand the tested, lineage-tracked marts to `clickhouse-olap`/dashboards; `metric-engine` parity reads from the semantic layer.

## Anti-patterns
Marts reading raw directly · a monolithic untested query · non-idempotent incremental (double-counts) · no freshness SLA · metrics redefined per dashboard (drift vs the semantic layer) · no column lineage (KPIs are tribal) · running full refreshes nightly when an incremental window suffices · transformation logic hidden in BI tools instead of the governed layer.

## dbt-on-StarRocks + the medallion (a lakehouse binding)
When the warehouse is **StarRocks over an Iceberg lakehouse** (`starrocks-olap`, `lakehouse-iceberg`), dbt is the governed **T** between Bronze and the serving marts, and the layering is the **medallion**:
```
S3+Iceberg(Glue) BRONZE (raw, immutable)
   └─ dbt sources = iceberg_glue.bronze.* ─► SILVER (cleaned/conformed) ─► GOLD (marts) = StarRocks-native
                                                                              └─► Analytics API (tenant predicate)
```
- **`source()` on the external Iceberg catalog reads Bronze; models materialize Silver/Gold as StarRocks-native tables** (Phase 1) — sub-second serving. Phase 3 may migrate Silver/Gold *into* Iceberg (Spark/Trino/dbt-written) for open, multi-engine marts.
- **Directional rule: `Iceberg → dbt → StarRocks → API`, never StarRocks → Iceberg** — the lakehouse stays the rebuildable SSOT; the warehouse stays a derived, disposable serving copy.
- **`dbt-starrocks` has NO `MERGE`:** upserts = `materialized='incremental'` + `table_type='PRIMARY'` + `keys=[...]` (the PK index does delete+insert); idempotent rebuilds = `incremental_strategy='dynamic_overwrite'` (partition replace), never blind append. Pin adapter + server versions (less battle-hardened than tier-1 adapters).
- Same idempotency law as `batch-processing-spark`; freshness + tests are the gate (`data-quality`).
