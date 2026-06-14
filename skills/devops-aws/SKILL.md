---
name: devops-aws
description: Reference implementation — AWS infra patterns: CDK IaC, EKS+Karpenter+ArgoCD orchestration, MSK, managed OLAP, cache, object storage. Phased footprint, selective deploy, auto-rollback.
---

# DevOps + AWS — a Platform Reference Implementation

> **Reference implementation.** This skill documents one concrete binding of the infrastructure/orchestration seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind this seam to different technology (a different cloud, ECS/Cloud Run/Nomad instead of EKS, Terraform/Pulumi instead of CDK). The *patterns* here — IaC-from-day-one, phased footprint, selective deploy, deploy-pipeline-as-part-of-the-slice, auto-rollback, restore drills — are what transfer; AWS is the example.

The binding is **locked in the Canon** (`STACK.md`). This reference uses **AWS CDK (TypeScript)** for IaC (not Terraform) and graduates to **EKS + Karpenter + ArgoCD** for orchestration at scale (not ECS at the target). IaC is CDK from day one; the orchestration/event-bus/CDC layers are **phased**.

## Phased infra — build the contracts now, run the smallest footprint

The mature architecture below is the **destination**, not the day-one build. Run the smallest footprint for current scale and **graduate each heavy layer only when its trigger fires**.

| Layer | Early phase (small scale) | Later phase (graduate when…) |
|---|---|---|
| **Backend deployables** | A few merged deployables (e.g. an `edge` Node bundle + a `data` Python bundle + web + mobile). (Always N *logical* bounded contexts with contract definitions; splitting is mechanical.) | Split into the full set of services as load/teams demand |
| **Compute hosting** | **ECS Fargate** + managed web hosting + a mobile build service | **EKS + Karpenter** when Fargate cost crosses a threshold OR you need bin-packing across bursty pods |
| **Event bus** | **MSK Serverless** + transactional outbox | **Provisioned MSK** when sustained throughput beats serverless cost OR you need CDC + tiered-storage tuning |
| **CDC** | none — ingestion writes OLTP + OLAP **directly** | **Debezium on MSK Connect** when >1 consumer needs the recent mirror in the OLAP store |
| **OLAP** | a managed columnar store, single region | shard/rightsize per its graduation trigger |
| **Region** | single region | multi-region per a later phase, **driven by the Canon's residency requirement** (`COMPLIANCE.md`) |

Because contract definitions + the logical contexts exist from day one, the split is "flip in-process call → network call," not a rewrite. Everything below is the **mature target** — apply the phase table when deciding what to provision today.

### Managed → BYOC → self-host (a hosting ladder)

A managed OLAP service stays the default early — low ops, idle-to-zero fits batch-spiky workloads. **First graduation = BYOC** (data plane in your cloud account, control plane in the vendor's) when **sustained spend crosses a multi-month threshold**, OR an in-account-residency contract requires it, OR committed-spend discounts beat the vendor markup. **Self-host only at high, always-on scale** with a named infra owner; loaded self-host TCO is a wash below the BYOC threshold, so **never graduate on bare infra cost alone**.

**BYOC = clusters run in your VPC; the vendor operates them remotely.** **IaC's job is the VPC + PrivateLink, not the cluster** — provision dedicated subnets, security groups, the **PrivateLink/VPC endpoint** connecting the vendor's control plane to your data-plane VPC, plus the BYOC IAM role. IaC does **not** manage the cluster lifecycle. Keep prod **warm before any time-boxed batch window**; idle-to-zero is dev/off-peak only. Lock-in is mitigated by the event-bus replay spine — migration is a replay from tiered storage (see `clickhouse-olap`).

### Model gateway (self-hosted)

A self-hosted **model gateway** (model-agnostic routing for the small/large model tiers) runs as a deployable — **2+ stateless replicas behind the load balancer** (HA; it's on a latency-sensitive critical path). It fronts the model backends (cloud-managed vs direct vendor clients — deferred + reversible behind the gateway); per-tenant virtual-key budgets + routing/fallback/semantic-cache live here. Hard constraint where the Canon requires it: **in-region inference for PII-bearing calls** — do not route those to a cross-region inference endpoint. The cache layer backs its semantic cache + budget counters. See `llm-gateway`.

## Reference architecture (mature target)

```
DNS + CDN + WAF → load balancer (L7; HTTP/2 + gRPC passthrough)
  → EKS cluster (Karpenter-managed; on-demand + spot mix)
      the set of services, reconciled by ArgoCD (GitOps from infra/k8s/<service>/<env>/)
  → OLTP (managed Postgres) · OLAP (tenant-sharded columnar store) · cache (Redis)
  → MSK Kafka (3 brokers / 3 AZs) + a schema registry
      ├── MSK Connect (Debezium: OLTP → Kafka CDC)
      └── Tiered storage on object storage (long/infinite retention)
  → object storage (raw archive, exports, assets) → log store (log-shipper spine + search)
```

## CDK layout + constructs

`infra/bin/app.ts` (entry); `infra/stacks/` one per concern — `network`, `compute` (EKS + Karpenter), `data` (OLTP peering, OLAP, cache), `kafka` (MSK + schema registry + Connect), `storage` (object storage + CDN), `observability`, `security` (workload IAM, secrets, WAF), `mobile` (build webhook, app-link assets). Reusable constructs in `infra/lib/constructs/` (e.g. a `Service` construct emitting Deployment + Service + HPA + PodDisruptionBudget + workload-IAM + ArgoCD app).

**CDK manages cluster + cloud resources; ArgoCD manages app deployments.** Never put a `Deployment` in CDK or an IAM role in ArgoCD.

## EKS service config (per service)

| Setting | Default |
|---|---|
| `replicas.min` | per the Canon (HA-critical services higher) |
| `replicas.max` | ~10× min (the gateway higher at peak) |
| HPA | ~60% CPU + 70% memory target |
| `PodDisruptionBudget.minAvailable` | 1 |
| `topologySpreadConstraints` | spread across 3 AZs |

**Karpenter NodePool:** capacity-type `[spot, on-demand]`, `arch: arm64` (Graviton), `consolidationPolicy: WhenEmptyOrUnderutilized` (renamed in Karpenter v1.0 — old `WhenUnderutilized` breaks on upgrade), `expireAfter: 720h`. On-demand baseline for HA-critical; spot for bursty workers (ingestion, analytics).

## CI/CD per service

CI on push to the main branch, gated jobs: lint+typecheck → unit-tests → contract-tests (`buf breaking` + schema compile + metric-registry parity) → build-and-push (**OIDC short-lived credentials — never long-lived cloud keys**) → ArgoCD auto-sync to staging → real-network smoke → ArgoCD production (**manual approval via a protected `production` environment** → canary).

ArgoCD app structure is Kustomize: `infra/k8s/<service>/base/` + `overlays/{staging,production}/` + `argocd-app.yaml`. **Dockerfiles** multi-stage: a slim base, deps → builder → non-root runner copying only build output, with a `HEALTHCHECK`.

## Selective deployment — monorepo, but deploy ONLY what changed

**The monorepo organizes code; it is NOT the deployment unit.** Each service has its **own image + its own ArgoCD Application**. The 4-step mechanism:

1. **Affected detection = the build tool's dependency graph (NOT a bare path-filter).** A path-filter misses services that *import* a shared package/contract. Use the graph:
   ```bash
   turbo run build test lint --affected
   turbo run build --affected --dry-run=json | jq '[.tasks[].package]|unique'
   ```
   A change to a shared lib or a contract file **correctly fans out** to every consumer.
2. **CI builds + pushes ONLY the affected images** via a matrix; each tagged by git SHA / content hash. A **remote build cache** makes affected-but-unchanged tasks cache hits.
3. **Per-service ArgoCD App syncs only the changed one.** CI bumps the image tag in the GitOps manifest for only the affected services. Production-grade config: (a) each Application sets **`argocd.argoproj.io/manifest-generate-paths`** to its own `infra/k8s/<service>/` so ArgoCD skips reconciliation for untouched apps; (b) generate Apps with an **ApplicationSet** (git-directory generator); (c) drive syncs by **webhook, not polling**; (d) Kustomize overlays + external-secrets (never secrets in git), no branch-per-environment.
4. **Shared-package / contract change → fan-out is correct, not waste.** This is the **`deploy_class=library`** path — build + redeploy *exactly* the named consumers (never all services). `buf breaking` + metric-parity gates prevent shipping a half-updated set.

**Phasing nuance:** selective deploy is **per-deployable**; the count grows as you split. Early phase = a few deployables (a change to one redeploys its bundle while `turbo --affected` skips the rest); later = independently-deployable services with their own ArgoCD apps.

## Deploy pipeline FROM DAY ONE (non-negotiable)

**Every service ships with its CI/CD pipeline as part of its first vertical slice — never a later add-on.** The slice MUST include: the affected-aware CI workflow, Dockerfile, per-service **ArgoCD Application** (base + staging/production overlays), health probes, canary + auto-rollback, a `deployment-report` entry. A service is not "done" until it can deploy itself to staging→prod on its own image + own ArgoCD app.

## Auto-rollback

A composite alarm on (5xx rate > threshold AND p99 latency > threshold) → notification → ArgoCD rollback hook → previous revision. Triggered automatically post-deploy; verifies for a monitor window.

## Mobile pipeline

Path-filtered to the mobile app: lint+typecheck → unit → E2E → build (matrix: preview, production) → store submit (manual approval) → OTA update (JS-only patches). **OTA-vs-native rule:** a JS bugfix → OTA channel; a new SDK / native module / permission change / bundle id → native bump → store review. (See `app-store-deployment`.)

## MSK + log store (infra notes)

- **MSK:** early phase = MSK Serverless + transactional outbox; graduate to provisioned MSK — 3 brokers, 3 AZs, TLS in transit, tiered storage to object storage. Per-topic retention by domain class (retain-forever for source/audit classes; bounded for operational/notification classes). Partition key always the **tenant key**. A registered schema registry.
- **Log store:** multi-AZ; ISM lifecycle (hot → warm → cold to object storage); per-service indices; a log-shipper DaemonSet that **redacts PII** before the store (see `observability`).

## Cost discipline

Track infra spend by layer; set **per-layer cost triggers** the Platform/SRE role watches on a cadence (e.g. log-store > threshold → reduce retention; event bus > threshold → broker sizing; OLAP > threshold → shard/rightsize; egress > threshold → VPC endpoints; **model-gateway tier mix > the cost-routing target → high-priority incident**, coordinate with the AI/ML Engineer — see `cost-routing-paradigms`). The thresholds themselves live in the Canon.

## DR + chaos

- RTO/RPO targets per the Canon; scheduled backups (point-in-time + cross-region copies); object-storage versioning + replication for critical buckets; a mobile kill-switch endpoint for emergency cert-pin rotation.
- **Chaos experiments before any high-stakes release:** kill a fraction of gateway pods (ArgoCD heals, the LB drains); throttle a broker's network (consumers slow, no data loss); inject OLAP latency (dashboards degrade to the hot cache); block the model backend (model features → template fallback); drop OLTP connections (pooler + retries keep core green). Verdict RESILIENT or FRAGILE; FRAGILE loops to the builder.

## Disaster recovery — restore drills

**An untested backup is not a backup.** RTO/RPO targets are **proven by rehearsal**. Run a **periodic restore-from-backup drill** into an isolated account/namespace; record wall-clock restore time + data delta against targets.

1. **OLTP point-in-time restore** — restore to a recent point into a scratch instance; confirm recovery point within RPO and restore within RTO.
2. **OLAP `BACKUP`/`RESTORE`** — back up tables to object storage on schedule; in the drill restore the latest into a scratch cluster.
3. **Verify against the metric registry** — recompute canonical metrics on restored data; assert they match prod within tolerance. A restore that yields wrong numbers is a failed drill.
4. **Backup-integrity verification** — between drills, automate a checksum/row-count probe on each backup; alert on corrupt/missing, don't wait for the cycle.

**Cross-region failover runbook (where residency / availability requires it):** a written, rehearsed failover runbook (promote the cross-region replica, repoint DNS, restore OLAP from replicated object storage, replay Kafka from tiered storage) — same targets, proven by drill before relied on. Capture each drill's measured RTO/RPO + gaps in the runbook.

## Common failure modes

- **Manual prod deploy** — `kubectl apply` / direct cloud-CLI to prod. The bash guard blocks it. Fix the CI gap, don't override.
- **Workload IAM role too broad** — wildcard / admin on a CI role. Scope per environment, least privilege.
- **Cost surprise on spot** — interrupts long tasks. `consolidationPolicy: WhenEmptyOrUnderutilized` + tolerate eviction.
- **Log hot tier full** — ISM mis-sized; new logs drop. Monitor cluster disk + index size.
- **IaC drift vs ArgoCD** — a k8s `Deployment` in CDK or cloud IAM in ArgoCD. Detection: `cdk diff` shows k8s resources.
- **Bash-denied fallback** — sandbox denies Bash → write the IaC + pipeline configs, list the exact `cdk diff` / `gh workflow run` / build commands, emit `→ ORCHESTRATOR (Bash denied — verify on my behalf)`.

## References

- The Product Canon's `STACK.md` + deploy playbook — the concrete binding (cloud, IaC tool, orchestrator, log spine, IAM, MSK topology, build/cert pinning, cost-discipline thresholds)
- `engineering-os-blueprint/09-reference-architecture.md` — the seam this skill binds
- Related: `observability`, `event-driven-kafka`, `operational-readiness`, `app-store-deployment`, `clickhouse-olap`

## 2026 market update

- **IaC pluralism (the 2024–26 shift):** **OpenTofu** (Linux Foundation fork of Terraform; native **state encryption** + provider-defined functions) is the open alternative after HashiCorp's BSL relicense + IBM acquisition — a live de-risking decision (`version-upgrade-policy`). Pulumi / SST / Crossplane are peers. CDK stays this reference's binding.
- **EKS Auto Mode** (managed Karpenter + Bottlerocket + bundled add-ons) is AWS's new easy-default, alongside the explicit Karpenter + ArgoCD pattern.
- **Argo CD won GitOps** (~50% vs Flux ~11%); Istio **ambient mode** + **Cilium/eBPF** are ending the sidecar era. Wire signing/provenance per `supply-chain-security` and admission rules per `policy-as-code`.

### Terraform-on-AWS binding (when `STACK.md` picks Terraform over CDK)
The patterns above transfer; the Terraform/OpenTofu specifics that matter:
- **The GitOps boundary is a hard line: Terraform provisions the cluster + cloud infra; Argo CD deploys apps INTO it.** TF owns VPC/IAM/EKS control plane/node infra/IRSA-or-Pod-Identity + a **one-time Argo CD bootstrap** (install Argo CD + an app-of-apps root pointing at Git). **Do NOT manage day-2 Kubernetes app objects via the TF `kubernetes`/`helm` providers** — configuring them from `data` lookups of the cluster you're creating in the same run is the chicken-and-egg/dependency-cycle trap, plus destroy-ordering pain and drift. Bridge values TF produces (IRSA role ARNs) into the app-of-apps Helm values, not into TF-managed add-ons.
- **State:** remote S3 with **native S3 locking** (`use_lockfile=true`, TF/OpenTofu **1.10+**; `dynamodb_table` deprecated in 1.11); **separate state/backend per env**, not CLI workspaces, as the prod boundary; **one AWS account per env** reached via `assume_role` per account (the dev/staging/prod-separate-accounts topology). `encrypt=true` + a KMS CMK (Terraform has no native client-side state encryption — **OpenTofu 1.7+ does**, a real de-risking lever).
- **EKS:** the `terraform-aws-modules/eks/aws` module + its `karpenter` submodule. Run a **tiny On-Demand managed node group (~1/AZ) for system add-ons** (CoreDNS/kube-proxy/Karpenter controller) + **Karpenter for everything else** — without the static MNG you hit a Karpenter bootstrap deadlock. (v21 of the module made **EKS Pod Identity** the default, removing native IRSA — plan the v20→v21 bump.)
- **CI:** OIDC federation (`assume_role_with_web_identity`, repo/branch-scoped) — **never static keys**; plan-on-PR + human-approved apply (GitHub Environments / Atlantis); scan with **Checkov / Trivy** (tfsec folded into Trivy; Terrascan archived Nov 2025); scheduled `plan` for drift. **Argo Workflows** (`pipeline-orchestration`) runs the batch/CI job DAGs *on* the cluster — distinct from Argo CD.
