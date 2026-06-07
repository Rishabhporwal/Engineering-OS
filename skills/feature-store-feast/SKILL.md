---
name: feature-store-feast
description: Reference implementation — an ML feature store on Feast: one feature definition serving training (offline) and inference (online) from the same transformation, point-in-time-correct joins, online/offline parity, tenant-scoped entities. Kills training/serving skew.
---

# Feature Store — Feast (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **feature-store seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to a different store (Tecton, Hopsworks, SageMaker Feature Store, Vertex, or a hand-rolled offline-table + online-cache pair). The *patterns* here — a single feature definition serving both training and inference, point-in-time-correct retrieval, online/offline parity, and feature reuse across models — are what transfer; Feast is the example.

A feature store is the contract between data engineering and ML: features are defined **once** and served two ways — **offline** (historical, point-in-time, for training) and **online** (low-latency, for inference). **Owner:** ML Platform Engineer (the platform + definitions); Data Engineer builds the upstream pipelines; AI/ML Engineer consumes for training/serving. Canon: `STACK.md`.

## Why it exists: kill training/serving skew
The cardinal ML-data sin is computing a feature one way for training and another way for inference. A feature store makes the **definition single-source** so both paths use identical logic (the ML analogue of the single-source `metric-engine`). If a feature can drift between offline and online, the model's production behaviour diverges from its evaluation — silently.

## Invariants (NON-NEGOTIABLE)
1. **One definition, two stores.** A feature is defined once; the offline store (lakehouse/warehouse) and online store (low-latency cache) are materialized from that one definition. Never hand-write the online version separately.
2. **Point-in-time correctness — no future leakage.** Training retrieval joins features **as they were at the label's timestamp**, using an event-timestamp + TTL. A feature value that "leaked" from after the prediction time inflates offline metrics and collapses in production.
3. **Tenant-scoped entities.** The entity key includes/[is namespaced by] `tenant_id`. Online lookups and offline joins are tenant-scoped; a feature vector assembled across tenants is a P0 (`multi-tenancy-isolation`).
4. **Online/offline parity is tested.** A parity check materializes a sample online and compares to the offline computation (QA gate, akin to cross-runtime metric parity in `metric-engine`).
5. **Freshness is an SLO.** Each feature view declares a freshness target; a stale online feature is a `data-quality` alarm, not a silent degradation.

## Definitions
```python
customer = Entity(name="customer", join_keys=["tenant_id", "customer_id"])

orders_30d = FeatureView(
    name="orders_30d",
    entities=[customer],
    ttl=timedelta(days=2),                       # online value valid window
    schema=[Field(name="order_count_30d", dtype=Int64),
            Field(name="gmv_minor_30d",   dtype=Int64)],   # money = integer minor units
    online=True,
    source=iceberg_source,                       # offline source = the lakehouse
)
```
- The **same** upstream transformation (Spark/Flink — `batch-processing-spark`, `stream-processing-flink`) that lands the offline table feeds the online materialization. Real-time features come from the stream path; daily features from batch.

## Retrieval
```python
# TRAINING — point-in-time correct: features as of each label's event_timestamp
training_df = store.get_historical_features(entity_df=labels_with_ts, features=[...]).to_df()

# INFERENCE — online, low-latency, same feature names
vector = store.get_online_features(features=[...],
            entity_rows=[{"tenant_id": t, "customer_id": c}]).to_dict()
```
The training and serving code reference the **same feature names** — that identity is the whole guarantee.

## Operability
- **Materialization** jobs (incremental) keep the online store current; schedule + monitor them (orchestration / `workflow-engine-temporal`).
- Track feature **freshness, null-rate, and distribution drift** (`data-quality`) — drift in an input feature is an early warning before model metrics move.
- Register the feature set version alongside the model in the registry (`ml-lifecycle`) so a model's exact feature contract is reproducible.

## Effort-tier note (`cost-routing-paradigms`)
The feature store serves **deterministic/statistical features cheaply** so models don't recompute them per request (a cache + reuse lever — features shared across models are computed once). Compute features in the cheapest tier (SQL/Spark/Flink); reserve the model call for the prediction itself.

## Anti-patterns
Separately hand-coding the online feature (skew) · training retrieval that leaks post-prediction data · entity keys without the tenant · no online/offline parity test · unmonitored freshness · recomputing a shared feature per model instead of reusing it · putting the feature transformation logic inside the model service instead of the store.

## 2026 market update

- **Embeddings are increasingly first-class features** — store + serve vectors as features alongside scalars (ties to `vector-search-pgvector`).
- **Alternatives (bind in `STACK.md`):** Tecton (managed, now Databricks-integrated) · Hopsworks · lakehouse-native stores (Databricks / Vertex / SageMaker Feature Store). Feast remains the OSS baseline; the online/offline-parity law is what matters, not the vendor.
