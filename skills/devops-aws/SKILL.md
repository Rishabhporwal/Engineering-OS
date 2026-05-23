---
name: devops-aws
description: Brain's AWS infrastructure — AWS CDK (TypeScript) for IaC; EKS + Karpenter + ArgoCD for orchestration; MSK + Glue Schema Registry; Supabase Postgres; ClickHouse Cloud; ElastiCache Redis; OpenSearch (logs + Phase 3 search); S3; CloudFront + Route 53; ECR; Secrets Manager; SES; EventBridge Scheduler. EAS Build for mobile pipelines. Auto-load whenever Jatin is touching infra, deployment, or cost. Brain uses CDK (NOT Terraform); EKS (NOT ECS).
---

# DevOps + AWS — Brain's Platform

**Stack is locked** (`canon/technical-requirements.md`). Brain uses **AWS CDK (TypeScript)** for IaC (NOT Terraform) and graduates to **EKS + Karpenter + ArgoCD** for orchestration at scale. IaC is CDK from day one; the orchestration/event-bus/CDC layers are **phased**.

## Phased infra — build the contracts now, run the smallest footprint (canon TECH/00 §3.3)

The mature architecture below is the **destination**, not the day-one build. Run the smallest footprint that serves current scale and **graduate each heavy layer only when its trigger fires**.

| Layer | Phase 0–1 (≤~25 brands) | Phase 2+ (graduate when…) |
|---|---|---|
| **Backend deployables** | **3 deployables** — `edge` (Node: api-gateway + core) + `data` (Python: ingestion + analytics + intelligence) + web + mobile. (Always 7 *logical* bounded contexts with proto contracts; splitting is mechanical.) | Split into the full **7 services** + add `lifecycle-service` at Phase 2 |
| **Compute hosting** | **ECS Fargate** + Amplify/managed (web) + EAS (mobile) | **EKS + Karpenter** when Fargate cost crosses ~$1.5–2K/mo OR you need bin-packing across bursty pods |
| **Event bus** | **MSK Serverless** + transactional outbox | **Provisioned MSK** when sustained throughput beats serverless cost OR you need Debezium + tiered-storage tuning |
| **CDC** | none — ingestion writes Postgres + ClickHouse **directly** | **Debezium on MSK Connect** at Phase 2 when >1 consumer needs the 90-day mirror in ClickHouse |
| **ClickHouse** | managed **ClickHouse Cloud**, single region | shard/rightsize per Phase-3 trigger |
| **Region** | single region (**ap-south-1**) | multi-region per Phase 4 |

Because gRPC contracts + the 7 logical contexts exist from day one, the split is "flip in-process call → network call," not a rewrite. Everything below this section is the **mature target** — apply the phase table when deciding what to actually provision today.

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

`infra/bin/brain.ts` (app entry); `infra/stacks/` one per concern — `network` (VPC/subnets/SG/NAT), `compute` (EKS + Karpenter), `data` (Supabase peering, CH Cloud, ElastiCache), `kafka` (MSK + Glue + MSK Connect), `storage` (S3 + CloudFront), `observability` (OpenSearch, Fluent Bit, CloudWatch, X-Ray, Sentry), `security` (per-pod IRSA, Secrets Manager, WAF), `mobile` (EAS Build webhook, AASA + assetlinks). Reusable constructs in `infra/lib/constructs/` (e.g. a `BrainService` construct that emits Deployment + Service + HPA + PodDisruptionBudget + IRSA + ArgoCD app from `{ serviceName, image, replicasMin/Max, targetCpu, containerPort, envFromSecrets }`).

**CDK manages cluster + AWS resources; ArgoCD manages app deployments.** Never put a `Deployment` in CDK or an IAM role in ArgoCD.

## EKS service config (per service — Phase 2+; on Fargate in Phase 0–1)

| Setting | Default |
|---|---|
| `replicas.min` | per canon/technical-requirements.md (api-gateway 4, core 2, ingestion 4, analytics 3, intelligence 2, notifications 2, lifecycle 3) |
| `replicas.max` | 10× min (api-gateway up to 40 at peak) |
| HPA | 60% CPU + 70% memory target |
| `PodDisruptionBudget.minAvailable` | 1 |
| `topologySpreadConstraints` | spread across 3 AZs |

**Karpenter NodePool:** capacity-type `[spot, on-demand]` mix, `arch: arm64` (Graviton, cheaper), `consolidationPolicy: WhenEmptyOrUnderutilized` (renamed in Karpenter v1.0 — the old `WhenUnderutilized` breaks on upgrade), `expireAfter: 720h`. On-demand baseline for HA-critical services; spot for ingestion + analytics workers.

## CI/CD per service

GitHub Actions, path-filtered to `apps/<service>/**` on push to `main`, with gated jobs: lint+typecheck → unit-tests → contract-tests (`buf breaking` + proto compile) → build-and-push (**OIDC `id-token: write` — never long-lived AWS keys**) → ArgoCD auto-sync to staging → real-network smoke-tests → ArgoCD production (**manual approval gate via `environment: production`**).

ArgoCD app structure is Kustomize: `infra/k8s/<service>/base/` (deployment, service, hpa, pdb, serviceaccount/IRSA) + `overlays/{staging,production}/` + `argocd-app.yaml`.

**Dockerfiles:** multi-stage — Node uses `node:24-alpine` (deps → builder `pnpm build` → non-root runner copying `dist/` + `node_modules`, with a `HEALTHCHECK` curling `/health`); Python uses `python:3.13-slim` + `uv sync --frozen`.

## Auto-rollback

CloudWatch composite alarm on (5xx rate > 2% AND p99 latency > 2s) → SNS → ArgoCD rollback hook → previous revision. Triggered automatically post-deploy; verifies for 10 minutes.

## Mobile pipeline (canon/technical-requirements.md)

Path-filtered to `apps/mobile/**`: lint+typecheck → unit (Vitest + RNTL) → Detox E2E (macOS iOS sim + Linux Android emu) → `eas-build` (matrix: preview, production) → `eas-submit` (manual approval; App Store + Play Store) → `eas-update-ota` (JS-only patches).

**OTA-vs-native rule (canon/technical-requirements.md):** JS bugfix → `eas update --channel production`; new Expo SDK / native module / permission change / bundle id → native bump → store review.

## MSK + OpenSearch (infra notes)

- **MSK:** **Phase 0–1 = MSK Serverless** + transactional outbox; graduate to **provisioned MSK** at Phase 2 (the broker topology below). Provisioned: 3 brokers (`kafka.m7g.large`), 3 AZs, TLS in transit, `storageMode: TIERED` to S3. Per-topic retention: `-1` for `integrations.*.v1` (tiered to S3), 30d for `operations.*`/`notifications.*`. Partition key always `workspace_id` (canon/technical-requirements.md). Glue Schema Registry `brain-schemas`.
- **OpenSearch:** 3-node `t3.medium.search` (Phase 0) → `r6g.large.search` (Phase 3), multi-AZ; ISM hot 7d → warm 7d → cold-S3 after 14d; indices `brain-logs-<service>-<date>`; Fluent Bit DaemonSet dual-outputs to OpenSearch + CloudWatch with Lua PII redaction. Correlation IDs propagate via headers / gRPC metadata / Kafka envelope (see `observability`).

## Cost (Phase summary — canon/technical-requirements.md)

| Item | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|
| EKS + Karpenter | $1.5K | $2K | $3K | $5K | $10K |
| MSK | $0.5K | $0.8K | $1.2K | $2K | $5K |
| ClickHouse Cloud | $0.5K | $1K | $1.5K | $3K | $8K |
| Supabase | $0.3K | $0.5K | $0.8K | $1.5K | $3K |
| OpenSearch | $0.3K | $0.4K | $0.6K | $1K | $3K |
| S3 + CloudFront + R53 | $0.2K | $0.3K | $0.5K | $1K | $3K |
| Anthropic Claude | $0.1K | $0.3K | $0.5K | $1K | $5K |
| **Total estimate** | **~$1.7K** | **~$3K** | **~$6K** | **~$13K** | **~$35K** |

### Cost triggers (Jatin watches weekly)

- CloudWatch Logs > $400/mo → reduce retention; rotate to S3 sooner
- MSK > $2K/mo before Phase 3 → broker sizing / dev-topic RF down
- Anthropic > $500/mo before Phase 3 → verify prompt-caching hit rate; downgrade to Haiku where applicable
- ClickHouse Cloud > $2K/mo before Phase 3 → shard utilization / rightsize replicas
- NAT Gateway transfer > $500/mo → investigate egress; consider VPC endpoints
- **Cost-routing dashboard** (canon/technical-requirements.md): Frontier-LLM rate > 1% of total calls → tier-1 incident; coordinate with Maya on prompt audit

## DR + chaos

- RTO 1h; RPO 15 min (Supabase PITR); daily 7d + cross-region weekly backups; S3 versioning + CRR for critical buckets; mobile kill-switch endpoint for emergency cert pin rotation. Full restore-drill discipline in **Disaster recovery — restore drills** below.
- **AWS FIS chaos (Scale Mode), before any Scale release:** kill 1/3 api-gateway pods (ArgoCD heals, ALB drains); throttle MSK broker network (consumers slow, no data loss); inject ClickHouse latency (dashboard degrades to Redis hot cache); block Anthropic (AI Chat → template responses); drop Supabase connections (PgBouncer + retries keep core green). Verdict RESILIENT or FRAGILE; FRAGILE loops back to the builder.

## Disaster recovery — restore drills

**An untested backup is not a backup.** The RTO 1h / RPO 15m targets are **proven by rehearsal, not assumed**. Run a **quarterly restore-from-backup drill** into an isolated account/namespace and record the wall-clock restore time + data delta against the targets.

**The drill (each quarter):**
1. **Postgres PITR** — restore Supabase to a timestamp ~10 min ago into a scratch instance; confirm the recovery point lands within RPO 15m and the restore completes within RTO 1h.
2. **ClickHouse `BACKUP`/`RESTORE`** — `BACKUP TABLE <db>.<table> TO S3(...)` on schedule; in the drill, `RESTORE` the latest backup from S3 into a scratch cluster.
3. **Verify against the metric registry** — recompute a sample of canonical metrics (daily_metrics, CM2, billable_gmv) on the restored data and assert they match production within tolerance. A backup that restores but yields wrong numbers is a failed drill.
4. **Backup-integrity verification** — between drills, automate a checksum/row-count probe on each backup (Postgres snapshot + ClickHouse S3 backup manifest); alert on a corrupt or missing backup, don't wait for the quarter.

**Cross-region failover runbook (Phase 4):** single region (ap-south-1) today; the Phase-4 multi-region step gets a written, rehearsed failover runbook — promote the cross-region Postgres replica, repoint Route 53, restore CH from CRR'd S3 backups, replay Kafka from S3 tiered storage — same RTO 1h / RPO 15m targets, proven by drill before it's relied on.

Capture each drill's measured RTO/RPO + any gap in `blueprints/runbook.md`; a missed target routes to incident follow-up (`observability` error-budget review + the auto-rollback path above).

## Common failure modes

- **Manual prod deploy** (encoded 2026-05-12) — `kubectl apply` / `aws eks ...` direct to production. `guard-bash.sh` blocks it. Fix the CI gap, don't override.
- **OIDC role too broad** (encoded 2026-05-12) — `*:*` / `eks:*` / `AdministratorAccess` on a CI role is a blast-radius problem. Scope per environment, least privilege.
- **Cost surprise on Karpenter spot** — interrupts long ingestion tasks. `consolidationPolicy: WhenEmptyOrUnderutilized` + tolerate eviction.
- **OpenSearch hot tier full** — ISM mis-sized; new logs drop. Monitor cluster disk + index size weekly.
- **CDK app drift vs ArgoCD** — k8s `Deployment` in CDK or AWS IAM in ArgoCD. Detection: `cdk diff` shows k8s resources, or the ArgoCD app shows AWS-managed resources.
- **Bash-denied fallback** — sandbox denies Bash → write CDK + pipeline configs, list the exact `cdk diff` / `gh workflow run` / `eas build --profile production` commands, emit `→ ORCHESTRATOR (Bash denied — verify on my behalf)`. See prompts/system-prompt.md.

## References

- `canon/technical-requirements.md` — log spine + X-Ray + Sentry + IAM, MSK topology, EAS Build + distribution + cert pinning, cost-discipline dashboard
- `skills/observability/SKILL.md` — Fluent Bit + OpenSearch + X-Ray wiring
- `skills/event-driven-kafka/SKILL.md` — MSK topic + Glue schema patterns
- `skills/operational-readiness/SKILL.md` — service pre-handoff checklist
