---
name: ml-lifecycle
description: Reference implementation — the model lifecycle: MLflow registry (versioning, stages, lineage) + BentoML/FastAPI serving, reproducible training, gated promotion via the eval harness, drift monitoring + retrain triggers, rollback. A model is only shipped when it beats baseline.
---

# ML Lifecycle — MLflow + BentoML (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **model-lifecycle seam** — training reproducibility, registry, serving, and monitoring (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to SageMaker, Vertex AI, Kubeflow, Seldon, or KServe. The *patterns* here — reproducible training, a versioned registry with lineage, gated promotion through the eval harness, parity-preserving serving, and drift→retrain→rollback — are what transfer; MLflow + BentoML is the example.

This skill governs **trained models** (classification, ranking, forecasting, anomaly detection, embeddings). For prompt/agent/LLM-app changes the ship-gate is `llm-evals`; for the routing in front of providers it's `llm-gateway`. **Owner:** ML Platform Engineer (registry + serving platform) with AI/ML Engineer (training + per-model promotion). Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Every model is reproducible.** Log the training run with its code version, hyperparameters, metrics, **and the exact dataset snapshot** (Iceberg snapshot ID — `lakehouse-iceberg`) + feature-set version (`feature-store-feast`). "We can't reproduce that model" means it should never have shipped.
2. **The registry is the single source of model truth.** Versions + stages (Staging → Production → Archived) live in the registry; serving pulls by registry reference, never a loose artifact in a bucket. Lineage (data → features → run → version → deployment) is queryable.
3. **Promotion is gated by the eval harness — ship only if ≥ baseline.** A new version reaches Production only after passing the offline eval gate (`llm-evals` discipline applied to ML: holdout metrics, slice metrics, fairness/guardrail checks) AND meeting the latency/cost budget. No "looks better," no eyeballing.
4. **Serving preserves training/serving parity.** The features at inference come from the **same** feature definitions used in training (`feature-store-feast`); preprocessing is shared code, not re-implemented in the serving layer. Skew here silently degrades production accuracy.
5. **Tenant + trace + tier on every prediction.** Inference is tenant-scoped, trace-propagated, and declared at its effort tier (`cost-routing-paradigms`) — a model is a tier above ML/deterministic; use it only where the cheaper tier can't clear the bar, and cache where inputs repeat.

## Training → registry
```python
with mlflow.start_run() as run:
    mlflow.log_params(hp)
    mlflow.log_metric("auc", auc); mlflow.log_metric("recall@k", r)
    mlflow.set_tag("dataset_snapshot", iceberg_snapshot_id)     # reproducibility
    mlflow.set_tag("feature_set", feast_feature_service_version)
    mlflow.sklearn.log_model(model, "model",
        registered_model_name="churn_ranker")                   # → registry, versioned
```
Point-in-time-correct training data (no future leakage — `batch-processing-spark`). Tag the run with everything needed to rebuild it.

## Gated promotion
```
Staging version → run eval harness (holdout + per-slice + guardrail metrics + latency/cost)
   PASS and ≥ baseline on every guardrail → promote to Production (registry stage transition, logged)
   FAIL or regression on any guardrail     → stays in Staging; bounce with the metric diff
```
Promotion is an audited transition (who/what/when/why) — the model analogue of a deploy approval.

## Serving (BentoML / FastAPI)
```python
@bentoml.service(resources={"cpu": "2"}, traffic={"timeout": 10})
class Ranker:
    model = bentoml.models.get("churn_ranker:production")       # pull by registry ref
    @bentoml.api
    def rank(self, req: RankRequest) -> RankResponse:           # tenant-scoped, traced
        feats = feature_store.get_online_features(req.entity)   # SAME defs as training
        return self.model.predict(feats)
```
- Serve behind the platform's standard surface (operational-readiness: health probes, port, env validation). Batch/offline scoring uses the registry ref too.
- **Shadow / canary** a new version against the current one before full promotion (mirrors `progressive-delivery`); compare live metrics, then graduate or roll back to the prior registry stage.

## Monitoring → retrain → rollback
- Monitor **input drift, prediction drift, and live quality** (`data-quality`, `observability`). Drift crossing a threshold triggers a retrain workflow (`workflow-engine-temporal`), not a 2 a.m. page.
- **Rollback is a registry stage transition** back to the last-good version — fast, audited, no rebuild. Wire it like any kill switch (`incident-response`).
- Every production prediction path has a dashboard (volume, latency, drift, business metric) and an alarm, or it doesn't ship.

## Effort-tier & cost note (`cost-routing-paradigms`)
A trained model is cheaper than a frontier LLM and often the right tier for ranking/forecasting/anomaly/classification — prefer it over an LLM for structured prediction. Within serving, cache repeated inputs and batch where latency allows. The registry + eval gate is also a **cost control**: it stops a worse-and-pricier model from reaching production.

## Anti-patterns
An unreproducible model (no dataset/feature/version lineage) · serving a loose artifact instead of a registry reference · promoting on "looks better" instead of the eval gate · re-implementing preprocessing in serving (training/serving skew) · no drift monitoring · rollback that requires a rebuild · using an LLM for structured prediction a trained model handles cheaper · an inference path with no dashboard/alarm.
