---
name: pipeline-orchestration
description: Reference implementation — Kubernetes-native job/DAG orchestration on Argo Workflows (the data/batch seam, distinct from Argo CD app-deploy and Temporal durable workflows): DAG vs steps, artifacts, retries, CronWorkflows, suspend gates, Argo Events, pod-GC discipline. Owner Data Engineer + Platform/SRE.
---

# Pipeline Orchestration — Argo Workflows (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **data/job-orchestration seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — `STACK.md` may bind it to Argo Workflows, Airflow, Dagster, or Prefect. The *patterns* — a DAG of idempotent containerized steps, big data via an artifact store (never inline), bounded concurrency, GC discipline, event-triggered runs — are what transfer; Argo Workflows is the example. **Anchor: Argo Workflows v3.6 (CNCF Graduated).**

Argo Workflows is a **Kubernetes-native engine for batch/ML/data DAGs and CI jobs** — each step is a container/pod. In this stack it runs the dbt/Spark/batch jobs on EKS. **Owner:** Data Engineer (the DAGs) + Platform/SRE (the controller + cluster). Canon: `STACK.md`.

## It orchestrates JOBS — three things it is NOT (don't conflate)
- **≠ Argo CD** (GitOps *app deploy*). The canonical compose: **Workflows = CI** (build/test/scan, then **write the new image tag/manifest back to Git**); **Argo CD = CD** (syncs that Git change to the cluster). Workflows never deploys directly — it hands off via Git, preserving the GitOps invariant. **Don't let Argo CD manage *live* `Workflow` instances** (its prune/self-heal fights the controller's status writes) — Argo CD owns the *templates + cron*; the controller/Argo Events create the ephemeral instances.
- **≠ Temporal** (`workflow-engine-temporal`) — durable *business* workflows as code (sagas, multi-day approvals). Argo is a batch-DAG/compute engine; don't run a durable app process on it.
- **≠ Dagster/Airflow** for *asset lineage*. If "a data asset with freshness + lineage" is the point → Dagster; if the broadest connector ecosystem + a mature data-ops UI → Airflow. **Argo wins when the platform is already K8s and you want one runtime for batch + ML + CI with container-per-step isolation** (e.g. Spark/dbt as pods, S3-event-triggered, Karpenter-scaled).

## Invariants (NON-NEGOTIABLE)
1. **GC your pods or drown the control plane.** Completed pods are **not** deleted by default — pod sprawl is the #1 way Argo melts apiserver/etcd. Set `spec.podGC.strategy` (≥ `OnWorkflowSuccess`) + `ttlStrategy` on every workflow, and `archiveLogs: true` + an artifact repo **before** aggressive GC (or logs vanish with the pods).
2. **Keep a Workflow object under etcd's ~1.5 MB limit.** Status lives in etcd. Big fan-outs, inline params, and accumulated retry history bloat it until `etcdserver: request is too large` and it can't be updated. **Pass big data via the artifact repository (S3), never inline; keep params tiny; enable the Workflow Archive (Postgres) + TTL** so history doesn't live in etcd.
3. **Bound concurrency at every level.** Controller (`--parallelism`), per-namespace (`--namespace-parallelism`), per-workflow (`spec.parallelism`), + semaphores/mutex for shared external systems. Unbounded fan-out DDoSes your own cluster + etcd.
4. **Least-privilege ServiceAccount per workflow — never `default`.** `workflow.spec.serviceAccountName` governs every pod; namespace-per-tenant + per-namespace caps + SSO/RBAC for multi-tenancy.
5. **Steps are idempotent + re-runnable** (same tenant/job law as `batch-processing-spark` / `data-transformation-dbt`); a failed step is just retried — set a real `retryPolicy`, not just a `limit`.

## Core shape
```yaml
spec:
  serviceAccountName: data-runner          # least-privilege, NOT default
  podGC: { strategy: OnWorkflowSuccess, deleteDelayDuration: "30s" }
  ttlStrategy: { secondsAfterCompletion: 3600 }
  templates:
    - name: medallion
      dag:                                  # DAG for any non-linear graph; `steps` for linear/fan-out
        tasks:
          - { name: bronze-ingest, template: run, arguments: {...} }
          - { name: dbt-silver, template: run, dependencies: [bronze-ingest] }
          - { name: dbt-gold,   template: run, dependencies: [dbt-silver] }
    - name: run
      retryStrategy: { limit: "3", retryPolicy: OnTransientError,
                       backoff: { duration: "10s", factor: "2", maxDuration: "5m" } }
      container: { image: ..., resources: { requests: {...}, limits: {...} } }   # requests REQUIRED
      outputs: { artifacts: [ { name: out, path: /tmp/out, s3: { key: "runs/{{workflow.name}}/out" } } ] }
```
- **`retryPolicy` matters:** default `OnFailure` won't retry controller/infra blips — use `OnTransientError`.
- **`WorkflowTemplate`/`ClusterWorkflowTemplate`** for reusable logic (a platform team owns the library; app teams `templateRef` it) — never copy-paste a template into every workflow.
- **`CronWorkflow`** for schedules (v3.6: multiple `schedules`, `timezone`, `concurrencyPolicy: Replace`, `startingDeadlineSeconds`).
- **`suspend: {}`** = the human-approval gate (resume via UI/CLI/API) — the manual-intervention primitive.
- **`onExit`** for cleanup/notify regardless of outcome; **`memoize`** to cache a deterministic step (label the cache ConfigMap; prune it — no built-in GC).

## Event-driven (Argo Events)
`EventSource` (S3/cron/Kafka/webhook → CloudEvents) → `EventBus` (NATS/JetStream) → `Sensor` (matches, fires → usually *create a Workflow*). Canonical: **an S3 object lands → a Workflow runs.** Platform owns EventSources+EventBus; app teams own Sensors.

## Operability
- The **workflow-controller** exposes Prometheus metrics at `:9090/metrics` (v3.6 moved to OpenTelemetry-based metrics — **metric names changed across versions; confirm for yours**). Watch per-phase counts, queue depth, op/pod durations. Run the controller HA + shard at high volume.
- **Artifact GC** (`artifactGC.strategy`, v3.4+) deletes temp artifacts but keeps the final output. Resource requests in a `steps` template **sum** on the co-scheduled pod — split heavy parallelism into DAG tasks.

## Effort-tier & cost note (`cost-routing-paradigms`, `finops-cost`)
Orchestration is deterministic plumbing — cheap. The cost is the pods it launches: set requests/limits, run batch on spot via Karpenter, GC aggressively, and bound parallelism so a runaway DAG can't autoscale into a surprise bill.

## Anti-patterns
No `podGC` (pod sprawl freezes the control plane) · inline big data → etcd 1.5 MB overflow · Argo CD managing live Workflow instances (fights the controller) · running a durable business process on Argo (use Temporal) · `default` ServiceAccount · only a retry `limit` with no `retryPolicy` (infra blips not retried) · `archiveLogs` off before aggressive GC (logs gone) · unbounded fan-out/parallelism · memoize cache that never gets pruned · resource requests omitted (unschedulable / noisy-neighbour).

## References
`batch-processing-spark` · `data-transformation-dbt` (the jobs it runs) · `devops-aws` (EKS + the Argo CD GitOps boundary) · `workflow-engine-temporal` (the durable-workflow sibling — different seam) · `event-driven-kafka` (Kafka-triggered runs) · `platform-engineering-idp`.
