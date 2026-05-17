---
name: devops-aws
description: Brain's AWS infrastructure — AWS CDK (TypeScript) for IaC; EKS + Karpenter + ArgoCD for orchestration; MSK + Glue Schema Registry; Supabase Postgres; ClickHouse Cloud; ElastiCache Redis; OpenSearch (logs + Phase 3 search); S3; CloudFront + Route 53; ECR; Secrets Manager; SES; EventBridge Scheduler. EAS Build for mobile pipelines. Auto-load whenever Jatin is touching infra, deployment, or cost. Brain uses CDK (NOT Terraform); EKS (NOT ECS).
---

# DevOps + AWS — Brain's Platform

**Stack is locked** (`docs/BRAIN_TECHNICAL_DOCUMENTATION.md` §4 + §11). Brain uses **AWS CDK (TypeScript)** for IaC and **EKS + Karpenter + ArgoCD** for orchestration. This is **different** from the prior plugin defaults of Terraform + ECS Fargate — don't revert.

## Reference architecture

```
Internet
   │
Route 53 + CloudFront (DNS + CDN + WAF)
   │
ALB (L7; HTTP/2 + gRPC passthrough)
   │
┌────────────────────────────────────────────────────────────────┐
│  EKS cluster (Karpenter-managed; mix of on-demand + spot)       │
│                                                                  │
│  api-gateway · core-service · ingestion-service · analytics-    │
│  service · intelligence-service · notifications-service ·       │
│  lifecycle-service                                              │
│                                                                  │
│  Reconciled by ArgoCD (GitOps from infra/k8s/<service>/<env>/)   │
└────────────────────────────────────────────────────────────────┘
   │                              │                          │
   ▼                              ▼                          ▼
Supabase Postgres           ClickHouse Cloud           ElastiCache Redis
(RDS-managed, AWS)          (workspace_id-sharded)     (cluster mode)
   │
   ▼
MSK Kafka (3 brokers, 3 AZs) + Glue Schema Registry
   │
   ├── MSK Connect (Debezium for Postgres → Kafka CDC)
   └── Tiered storage backend on S3 (infinite retention)
                              │
                              ▼
            S3 (raw archive, exports, recordings, mobile assets)
                              │
                              ▼
            OpenSearch (Fluent Bit log spine + Phase 3 search)
```

## CDK layout

```
infra/
├── bin/
│   └── brain.ts                 # CDK app entry
├── stacks/
│   ├── network.ts               # VPC, subnets, security groups, NAT
│   ├── compute.ts               # EKS cluster, node groups, Karpenter
│   ├── data.ts                  # Supabase peering, CH Cloud, ElastiCache
│   ├── kafka.ts                 # MSK cluster, topics, Glue Schema Registry, MSK Connect (Debezium)
│   ├── storage.ts               # S3 buckets, CloudFront distributions
│   ├── observability.ts         # OpenSearch, Fluent Bit, CloudWatch dashboards, X-Ray, Sentry
│   ├── security.ts              # IAM roles (per-pod IRSA on EKS), Secrets Manager, WAF
│   └── mobile.ts                # EAS Build webhook integration, AASA + assetlinks.json
└── lib/
    └── constructs/              # Reusable CDK constructs (eks-service, msk-topic, ch-shard)
```

## CDK standard construct

```typescript
// infra/lib/constructs/eks-service.ts
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

interface BrainServiceProps {
  serviceName: string;
  image: string;
  replicasMin: number;
  replicasMax: number;
  targetCpu: number;       // HPA target
  containerPort: number;
  envFromSecrets: string[]; // Secrets Manager ARNs
}

export class BrainService extends Construct {
  constructor(scope: Construct, id: string, props: BrainServiceProps) {
    super(scope, id);
    // Deployment + Service + HPA + PodDisruptionBudget + IRSA + ArgoCD app
  }
}
```

## EKS service config (per service)

| Setting | Default |
|---|---|
| `replicas.min` | per `docs/BRAIN_TECHNICAL_DOCUMENTATION.md` §3 (api-gateway 4, core 2, ingestion 4, analytics 3, intelligence 2, notifications 2, lifecycle 3) |
| `replicas.max` | 10× min (api-gateway up to 40 at peak) |
| HPA | Target 60% CPU + 70% memory |
| `PodDisruptionBudget.minAvailable` | 1 |
| `topologySpreadConstraints` | spread across 3 AZs |
| Resource requests | tuned per service; spot nodes for non-critical |

## Karpenter NodePool defaults

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: [spot, on-demand]      # mix
        - key: kubernetes.io/arch
          operator: In
          values: [arm64]                 # Graviton preferred (cheaper)
      taints: []
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 720h
```

On-demand baseline for HA-critical services; spot for ingestion + analytics workers.

## CI/CD per service

```yaml
# .github/workflows/<service>-deploy.yml
on:
  push:
    branches: [main]
    paths: ['apps/<service>/**']

jobs:
  lint-and-typecheck:
  unit-tests:
  contract-tests:                  # buf breaking + proto compile
  build-and-push:
    permissions: { id-token: write }   # OIDC; never long-lived AWS keys
  argocd-staging:                  # ArgoCD auto-syncs from main
  smoke-tests:                     # real-network curl against staging
  argocd-production:
    environment: production         # manual approval gate
```

## Mobile pipeline (TECH/10)

```yaml
# .github/workflows/mobile-deploy.yml
on: { push: { branches: [main], paths: ['apps/mobile/**'] } }
jobs:
  lint-and-typecheck:
  unit-tests:                      # Vitest + RNTL
  e2e-detox:                       # macOS iOS sim + Linux Android emu
  eas-build:
    strategy:
      matrix: { profile: [preview, production] }
  eas-submit:
    needs: eas-build
    environment: production         # manual approval (App Store + Play Store)
  eas-update-ota:                  # JS-only patches; no native bump
```

OTA-vs-native rule (TECH/10 §9):
- JS bugfix → `eas update --channel production`
- New Expo SDK / new native module / permission change / bundle id → native bump → App Store + Play Store review

## Dockerfile standard (Node)

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:20-alpine AS runner
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 svc
USER svc
WORKDIR /app
COPY --from=builder --chown=svc:nodejs /app/dist ./dist
COPY --from=builder --chown=svc:nodejs /app/node_modules ./node_modules
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:3000/health || exit 1
CMD ["node", "dist/main.js"]
```

Python services use `python:3.12-slim` + `uv sync --frozen` in builder.

## MSK + Glue Schema Registry

```typescript
// infra/stacks/kafka.ts
const msk = new msk.CfnCluster(this, 'BrainMsk', {
  clusterName: 'brain-msk',
  kafkaVersion: '3.6.0',
  numberOfBrokerNodes: 3,
  brokerNodeGroupInfo: {
    instanceType: 'kafka.m7g.large',
    clientSubnets: privateSubnetIds,
    securityGroups: [mskSg.securityGroupId],
    storageInfo: { ebsStorageInfo: { volumeSize: 1000 } },
  },
  encryptionInfo: { encryptionInTransit: { clientBroker: 'TLS' } },
  // Tiered storage to S3 — infinite retention
  storageMode: 'TIERED',
});

const glueRegistry = new glue.CfnRegistry(this, 'BrainSchemaRegistry', {
  name: 'brain-schemas',
});
```

Per-topic config: `retention.ms = -1` for `integrations.*.v1` (tiered to S3); 30 days for `operations.*` and `notifications.*`. Partition key always `workspace_id` (TECH/02).

## OpenSearch (centralized logs — TECH/09)

```
Cluster: 3-node t3.medium.search (Phase 0); scale to r6g.large.search (Phase 3)
Multi-AZ: yes
ISM policy: hot 7d → warm 7d → cold-S3-archive after 14d
Indices: brain-logs-<service>-<YYYY.MM.DD>
Fluent Bit DaemonSet: dual-output to OpenSearch + CloudWatch Logs; Lua redaction script for PII
Kibana dashboards: System Health, Per-Service Deep Dive, Per-Workspace Investigation
Monitors → PagerDuty/Slack: error-rate-spike, p99-latency, auth-failure-spike, paradigm-bypass-spike
```

Correlation IDs (`request_id + trace_id + workspace_id + user_id`) propagate end-to-end via HTTP headers, gRPC metadata, Kafka envelope. AsyncLocalStorage (TS) / contextvars (Python) wire it through.

## ArgoCD app structure

```
infra/k8s/<service>/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── serviceaccount.yaml      # IRSA role
│   └── kustomization.yaml
├── overlays/
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── replica-count.yaml
│   └── production/
│       ├── kustomization.yaml
│       └── replica-count.yaml
└── argocd-app.yaml              # ArgoCD Application CR
```

## Auto-rollback

CloudWatch composite alarm on (5xx rate > 2% AND p99 latency > 2s) → SNS → ArgoCD rollback hook → previous revision. Triggered automatically post-deploy; verifies for 10 minutes.

## Cost (Phase summary — TECH/12 §AWS-inventory)

| Item | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|---|
| EKS + Karpenter | $1.5K | $2K | $3K | $5K | $10K |
| MSK | $0.5K | $0.8K | $1.2K | $2K | $5K |
| ClickHouse Cloud | $0.5K | $1K | $1.5K | $3K | $8K |
| Supabase | $0.3K | $0.5K | $0.8K | $1.5K | $3K |
| OpenSearch | $0.3K | $0.4K | $0.6K | $1K | $3K |
| S3 + CloudFront + R53 | $0.2K | $0.3K | $0.5K | $1K | $3K |
| Anthropic Claude | $0.1K | $0.3K | $0.5K | $1K | $5K |
| EAS Build | $0.1K | $0.1K | $0.1K | $0.1K | $0.1K |
| **Total estimate** | **~$1.7K** | **~$3K** | **~$6K** | **~$13K** | **~$35K** |

## Cost triggers (Jatin watches weekly)

- CloudWatch Logs > $400/mo → reduce retention; rotate to S3 sooner
- MSK > $2K/mo before Phase 3 → broker sizing / dev-topic RF down
- Anthropic > $500/mo before Phase 3 → verify prompt caching hit rate; downgrade to Haiku where applicable
- ClickHouse Cloud > $2K/mo before Phase 3 → shard utilization check; rightsize replicas
- NAT Gateway data transfer > $500/mo → investigate egress patterns; consider VPC endpoints
- **Cost-routing dashboard** (TECH/12 §5): Frontier-LLM rate > 1% of total calls → tier-1 incident; coordinate with Maya on prompt audit

## DR defaults

- RTO: 1 hour
- RPO: 15 min (Supabase PITR)
- Backups: daily 7d + cross-region weekly; S3 versioning + CRR for critical buckets
- AWS FIS chaos in staging before any Scale Mode release
- Mobile: kill-switch endpoint for emergency cert pin rotation

## AWS FIS chaos experiments (Scale Mode)

Standard list:
- Kill 1/3 of api-gateway pods → verify ArgoCD heals + ALB drains gracefully
- Throttle MSK broker network → consumers slow, but no data loss
- Inject ClickHouse query latency → dashboard degrades gracefully (Redis hot cache)
- Block Anthropic API → AI Chat degrades to template-based responses
- Drop Supabase Postgres connections → PgBouncer + retries keep core ops green

Verdict: RESILIENT or FRAGILE. FRAGILE loops back to builder.

## Common failure modes

- **Manual prod deploy** (encoded 2026-05-12) — `kubectl apply` to production, `aws eks ...` direct. `guard-bash.sh` blocks. Fix the CI gap, don't override. Detection: about to type `kubectl ... -n production`.
- **OIDC role too broad** (encoded 2026-05-12) — `*:*` or `eks:*` on CI roles is a blast-radius problem. Scope per environment + least privilege. Detection: CDK attaches `AdministratorAccess` to a CI role.
- **Cost surprise on Karpenter spot** — interrupts long-running ingestion tasks. Set `consolidationPolicy: WhenUnderutilized` + tolerate eviction. Detection: ingestion job restarts spike.
- **OpenSearch hot tier full** — ISM mis-sized at launch; new logs drop. Detection: Fluent Bit error rate > 0 in CloudWatch. Mitigation: monitor cluster disk + index size weekly.
- **CDK app drift** (vs ArgoCD) — CDK manages cluster + AWS resources; ArgoCD manages app deployments. Don't put `Deployment` resources in CDK or `IAM role` in ArgoCD. Detection: `cdk diff` shows changes to k8s resources or ArgoCD app shows AWS-managed resources.
- **Bash-denied fallback** — sandbox denies Bash → write CDK + pipeline configs, list exact `cdk diff` / `gh workflow run` / `eas build --profile production` commands, emit `→ ORCHESTRATOR (Bash denied — verify on my behalf)`. See CLAUDE.md.

## References

- `docs/TECH/09_security_observability.md` — log spine + X-Ray + Sentry + IAM
- `docs/TECH/02_integrations.md` — MSK topology
- `docs/TECH/10_mobile_architecture.md` §9-11 — EAS Build + distribution + cert pinning
- `docs/TECH/12_cost_routing_compute.md` — cost-discipline dashboard
- `skills/observability/SKILL.md` — Fluent Bit + OpenSearch + X-Ray wiring
- `skills/event-driven-kafka/SKILL.md` — MSK topic + Glue schema patterns
- `skills/operational-readiness/SKILL.md` — service pre-handoff checklist
