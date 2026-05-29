---
name: devops-aws
description: Brain's AWS infra — CDK (not Terraform), EKS+Karpenter+ArgoCD (not ECS), MSK, Supabase, ClickHouse, ElastiCache, S3. Phased footprint, selective deploy, auto-rollback.
---

# DevOps + AWS — Brain's Platform

**Stack is locked** (`canon/technical-requirements.md`). Brain uses **AWS CDK (TypeScript)** for IaC (NOT Terraform) and graduates to **EKS + Karpenter + ArgoCD** for orchestration at scale (NOT ECS at the target). IaC is CDK from day one; the orchestration/event-bus/CDC layers are **phased**.

## Phased infra — build the contracts now, run the smallest footprint (canon TECH/00 §3.3)

The mature architecture below is the **destination**, not the day-one build. Run the smallest footprint for current scale and **graduate each heavy layer only when its trigger fires**.

| Layer | Phase 0–1 (≤~25 brands) | Phase 2+ (graduate when…) |
|---|---|---|
| **Backend deployables** | **3 deployables** — `edge` (Node: api-gateway + core) + `data` (Python: ingestion + analytics + intelligence) + web + mobile. (Always 7 *logical* bounded contexts with proto contracts; splitting is mechanical.) | Split into the full **7 services** + add `lifecycle-service` at Phase 2 |
| **Compute hosting** | **ECS Fargate** + Amplify/managed (web) + EAS (mobile) | **EKS + Karpenter** when Fargate cost crosses ~$1.5–2K/mo OR you need bin-packing across bursty pods |
| **Event bus** | **MSK Serverless** + transactional outbox | **Provisioned MSK** when sustained throughput beats serverless cost OR you need Debezium + tiered-storage tuning |
| **CDC** | none — ingestion writes Postgres + ClickHouse **directly** | **Debezium on MSK Connect** at Phase 2 when >1 consumer needs the 90-day mirror in ClickHouse |
| **ClickHouse** | managed **ClickHouse Cloud**, single region | shard/rightsize per Phase-3 trigger |
| **Region** | single region (**ap-south-1**) | multi-region per Phase 4 |

Because gRPC contracts + the 7 logical contexts exist from day one, the split is "flip in-process call → network call," not a rewrite. Everything below is the **mature target** — apply the phase table when deciding what to provision today.

### ClickHouse hosting ladder (managed → BYOC → self-host)

Stays **managed ClickHouse Cloud (ap-south-1) for Phase 0–3** — DPDP-clean Mumbai region, idle-to-zero fits the batch-spiky daily tick, ops ≈ 0. **First graduation = BYOC** when **sustained compute spend ≥ ~$6K/mo for 3 months**, OR an in-account-residency contract requires it, OR AWS committed-spend discounts beat CH's markup. **Self-host on EKS (Altinity-supported) only at Phase 4** (always-on ≥ ~$15–20K/mo + a named infra owner); loaded self-host TCO is a wash below ~$6–8K/mo, so **never graduate on bare infra cost alone**.

**BYOC = data plane in Brain's AWS account, control plane in CH's.** CH clusters run in Brain's VPC; CH operates them remotely. **CDK's job is the VPC + PrivateLink, not the CH cluster** — provision the dedicated subnets, security groups, the **PrivateLink/VPC endpoint** connecting CH's control plane to Brain's data-plane VPC, plus IAM for the BYOC role. CDK does **not** manage the CH cluster lifecycle. Keep prod **warm before the 06:55–07:20 IST tick**; idle-to-zero is dev/off-peak only. Lock-in is mitigated by the Kafka/MSK replay spine — migration is a replay from S3 tiered storage (see `clickhouse-olap`).

### LiteLLM gateway (self-hosted on EKS)

The **LiteLLM gateway** (OSS, model-agnostic routing for paradigms 3/4) is a **self-hosted deployable on EKS, ap-south-1** — **2+ stateless replicas behind the ALB** (HA; it's on the Morning Brief critical path), via the `BrainService` construct. It fronts the model backends (Bedrock vs native direct clients — deferred + reversible behind the gateway); per-workspace virtual-key budgets + routing/fallback/semantic-cache live here. Hard constraint: **India-resident inference for PII-bearing calls** (DPDP) — do not route those to Bedrock global cross-region inference. ElastiCache backs its semantic cache + budget counters.

## Reference architecture (mature target — Phase 2+)

```
Route 53 + CloudFront (DNS + CDN + WAF) → ALB (L7; HTTP/2 + gRPC passthrough)
  → EKS cluster (Karpenter-managed; on-demand + spot mix)
      api-gateway · core-service · ingestion · analytics · intelligence · notifications · lifecycle
      reconciled by ArgoCD (GitOps from infra/k8s/<service>/<env>/)
  → Supabase Postgres (RDS-managed) · ClickHouse Cloud (workspace_id-sharded) · ElastiCache Redis
  → MSK Kafka (3 brokers / 3 AZs) + Glue Schema Registry
      ├── MSK Connect (Debezium: Postgres → Kafka CDC)
      └── Tiered storage on S3 (infinite retention)
  → S3 (raw archive, exports, recordings, mobile assets) → OpenSearch (Fluent Bit log spine + Phase 3 search)
```

## CDK layout + constructs

`infra/bin/brain.ts` (entry); `infra/stacks/` one per concern — `network`, `compute` (EKS + Karpenter), `data` (Supabase peering, CH Cloud, ElastiCache), `kafka` (MSK + Glue + MSK Connect), `storage` (S3 + CloudFront), `observability`, `security` (IRSA, Secrets Manager, WAF), `mobile` (EAS Build webhook, AASA + assetlinks). Reusable constructs in `infra/lib/constructs/` (e.g. a `BrainService` emitting Deployment + Service + HPA + PodDisruptionBudget + IRSA + ArgoCD app).

**CDK manages cluster + AWS resources; ArgoCD manages app deployments.** Never put a `Deployment` in CDK or an IAM role in ArgoCD.

## EKS service config (per service — Phase 2+; on Fargate in Phase 0–1)

| Setting | Default |
|---|---|
| `replicas.min` | per canon (api-gateway 4, core 2, ingestion 4, analytics 3, intelligence 2, notifications 2, lifecycle 3) |
| `replicas.max` | 10× min (api-gateway up to 40 at peak) |
| HPA | 60% CPU + 70% memory target |
| `PodDisruptionBudget.minAvailable` | 1 |
| `topologySpreadConstraints` | spread across 3 AZs |

**Karpenter NodePool:** capacity-type `[spot, on-demand]`, `arch: arm64` (Graviton), `consolidationPolicy: WhenEmptyOrUnderutilized` (renamed in Karpenter v1.0 — old `WhenUnderutilized` breaks on upgrade), `expireAfter: 720h`. On-demand baseline for HA-critical; spot for ingestion + analytics workers.

## CI/CD per service

GitHub Actions on push to `main`, gated jobs: lint+typecheck → unit-tests → contract-tests (`buf breaking` + proto compile + metric-registry parity) → build-and-push (**OIDC `id-token: write` — never long-lived AWS keys**) → ArgoCD auto-sync to staging → real-network smoke → ArgoCD production (**manual approval via `environment: production`** → canary).

ArgoCD app structure is Kustomize: `infra/k8s/<service>/base/` + `overlays/{staging,production}/` + `argocd-app.yaml`. **Dockerfiles** multi-stage: Node `node:24-alpine` (deps → builder `pnpm build` → non-root runner copying `dist/`+`node_modules` with a `HEALTHCHECK`); Python `python:3.13-slim` + `uv sync --frozen`.

## Selective deployment — monorepo, but deploy ONLY what changed

**The monorepo organizes code; it is NOT the deployment unit.** Each service has its **own ECR image + its own ArgoCD Application**. The 4-step mechanism:

1. **Affected detection = Turborepo's dependency graph (NOT a bare path-filter).** A path-filter misses services that *import* a shared package/proto. Use the graph:
   ```bash
   turbo run build test lint --affected
   turbo run build --affected --dry-run=json | jq '[.tasks[].package]|unique'
   ```
   A change to `packages/lib-metrics`, `pylibs/brain_metrics`, or a `protos/` file **correctly fans out** to every consumer.
2. **CI builds + pushes ONLY the affected images** via a matrix; each tagged by git SHA / content hash. Turborepo **remote cache (S3)** makes affected-but-unchanged tasks cache hits.
3. **Per-service ArgoCD App syncs only the changed one.** CI bumps the image tag in the GitOps manifest for only the affected services. Production-grade config: (a) each Application sets **`argocd.argoproj.io/manifest-generate-paths`** to its own `infra/k8s/<service>/` so ArgoCD skips reconciliation for untouched apps; (b) generate Apps with an **ApplicationSet** (git-directory generator); (c) drive syncs by **webhook, not polling**; (d) Kustomize overlays + external-secrets (never secrets in git), no branch-per-environment.
4. **Shared-package / proto change → fan-out is correct, not waste.** This is the **`deploy_class=library`** path — build + redeploy *exactly* the consumers, named in `consuming_services` (never all 7). `buf breaking` + metric-parity gates prevent shipping a half-updated set.

**Phasing nuance:** selective deploy is **per-deployable**; the count grows. Phase 0–1 = 3 deployables (a `core` change redeploys `edge`, while `turbo --affected` still skips `data`/`web`/`mobile`); Phase 2+ = 7 independently-deployable services with their own ArgoCD apps.

## Deploy pipeline FROM DAY ONE (non-negotiable)

**Every service ships with its CI/CD pipeline as part of its first vertical slice — never a later add-on.** The slice MUST include: the affected-aware GitHub Actions workflow, Dockerfile, per-service **ArgoCD Application** (base + staging/production overlays), health probes, canary + auto-rollback, a `deployment-report` entry. A service is not "done" until it can deploy itself to staging→prod on its own image + own ArgoCD app.

## Auto-rollback

CloudWatch composite alarm on (5xx rate > 2% AND p99 latency > 2s) → SNS → ArgoCD rollback hook → previous revision. Triggered automatically post-deploy; verifies for 10 minutes.

## Mobile pipeline

Path-filtered to `apps/mobile/**`: lint+typecheck → unit (Vitest + RNTL) → Detox E2E → `eas-build` (matrix: preview, production) → `eas-submit` (manual approval; App Store + Play Store) → `eas-update-ota` (JS-only patches). **OTA-vs-native rule:** JS bugfix → `eas update --channel production`; new Expo SDK / native module / permission change / bundle id → native bump → store review. (See `app-store-deployment`.)

## MSK + OpenSearch (infra notes)

- **MSK:** Phase 0–1 = MSK Serverless + transactional outbox; graduate to provisioned MSK at Phase 2 — 3 brokers (`kafka.m7g.large`), 3 AZs, TLS in transit, `storageMode: TIERED` to S3. Per-topic retention: `-1` for `integrations.*.v1`, 30d for `operations.*`/`notifications.*`. Partition key always `workspace_id`. Glue Schema Registry `brain-schemas`.
- **OpenSearch:** 3-node `t3.medium.search` (P0) → `r6g.large.search` (P3), multi-AZ; ISM hot 7d → warm 7d → cold-S3 after 14d; indices `brain-logs-<service>-<date>`; Fluent Bit DaemonSet dual-outputs with Lua PII redaction (see `observability`).

## Cost (Phase summary)

| Item | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| EKS + Karpenter | $1.5K | $2K | $3K | $5K | $10K |
| MSK | $0.5K | $0.8K | $1.2K | $2K | $5K |
| ClickHouse Cloud | $0.5K | $1K | $1.5K | $3K | $8K |
| Supabase | $0.3K | $0.5K | $0.8K | $1.5K | $3K |
| OpenSearch | $0.3K | $0.4K | $0.6K | $1K | $3K |
| S3+CloudFront+R53 | $0.2K | $0.3K | $0.5K | $1K | $3K |
| Anthropic Claude | $0.1K | $0.3K | $0.5K | $1K | $5K |
| **Total** | **~$1.7K** | **~$3K** | **~$6K** | **~$13K** | **~$35K** |

### Cost triggers (Jatin watches weekly)

- CloudWatch Logs > $400/mo → reduce retention; rotate to S3 sooner
- MSK > $2K/mo before P3 → broker sizing / dev-topic RF down
- Anthropic > $500/mo before P3 → verify prompt-caching hit rate; downgrade to Haiku where applicable
- ClickHouse Cloud > $2K/mo before P3 → shard utilization / rightsize replicas
- NAT Gateway transfer > $500/mo → investigate egress; consider VPC endpoints
- **Cost-routing dashboard:** Frontier-LLM rate > 1% of total calls → tier-1 incident; coordinate with Maya

## DR + chaos

- RTO 1h; RPO 15 min (Supabase PITR); daily 7d + cross-region weekly backups; S3 versioning + CRR for critical buckets; mobile kill-switch endpoint for emergency cert pin rotation.
- **AWS FIS chaos (Scale Mode), before any Scale release:** kill 1/3 api-gateway pods (ArgoCD heals, ALB drains); throttle MSK broker network (consumers slow, no data loss); inject ClickHouse latency (dashboard degrades to Redis hot cache); block Anthropic (AI Chat → template responses); drop Supabase connections (PgBouncer + retries keep core green). Verdict RESILIENT or FRAGILE; FRAGILE loops to the builder.

## Disaster recovery — restore drills

**An untested backup is not a backup.** RTO 1h / RPO 15m are **proven by rehearsal**. Run a **quarterly restore-from-backup drill** into an isolated account/namespace; record wall-clock restore time + data delta against targets.

1. **Postgres PITR** — restore Supabase to ~10 min ago into a scratch instance; confirm recovery point within RPO 15m and restore within RTO 1h.
2. **ClickHouse `BACKUP`/`RESTORE`** — `BACKUP TABLE <db>.<table> TO S3(...)` on schedule; in the drill `RESTORE` the latest from S3 into a scratch cluster.
3. **Verify against the metric registry** — recompute canonical metrics (daily_metrics, CM2, billable_gmv) on restored data; assert they match prod within tolerance. A restore that yields wrong numbers is a failed drill.
4. **Backup-integrity verification** — between drills, automate a checksum/row-count probe on each backup; alert on corrupt/missing, don't wait for the quarter.

**Cross-region failover runbook (Phase 4):** single region today; Phase-4 multi-region gets a written, rehearsed failover runbook (promote cross-region Postgres replica, repoint Route 53, restore CH from CRR'd S3, replay Kafka from S3 tiered storage) — same targets, proven by drill before relied on. Capture each drill's measured RTO/RPO + gaps in `blueprints/runbook.md`.

## Common failure modes

- **Manual prod deploy** (encoded 2026-05-12) — `kubectl apply` / `aws eks` direct to prod. `guard-bash.sh` blocks it. Fix the CI gap, don't override.
- **OIDC role too broad** (2026-05-12) — `*:*` / `eks:*` / `AdministratorAccess` on a CI role. Scope per environment, least privilege.
- **Cost surprise on Karpenter spot** — interrupts long ingestion tasks. `consolidationPolicy: WhenEmptyOrUnderutilized` + tolerate eviction.
- **OpenSearch hot tier full** — ISM mis-sized; new logs drop. Monitor cluster disk + index size weekly.
- **CDK app drift vs ArgoCD** — k8s `Deployment` in CDK or AWS IAM in ArgoCD. Detection: `cdk diff` shows k8s resources.
- **Bash-denied fallback** — sandbox denies Bash → write CDK + pipeline configs, list the exact `cdk diff` / `gh workflow run` / `eas build --profile production` commands, emit `→ ORCHESTRATOR (Bash denied — verify on my behalf)`.

## References

- `canon/technical-requirements.md` — log spine, IAM, MSK topology, EAS Build + cert pinning, cost-discipline dashboard
- Related: `observability`, `event-driven-kafka`, `operational-readiness`, `app-store-deployment`, `clickhouse-olap`
