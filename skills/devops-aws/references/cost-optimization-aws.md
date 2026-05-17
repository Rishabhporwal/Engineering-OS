# AWS Cost Optimization — Deep Reference

## The Hierarchy (in order of cost lever size)

1. **Right-size compute** — biggest line item, biggest savings
2. **Commitment discounts** — Savings Plans / RIs
3. **Spot for interruptible workloads**
4. **Storage tiering** — S3 lifecycle, EBS gp3 over gp2
5. **NAT-vs-VPC-Endpoints** — counterintuitively large for high-traffic services
6. **CloudWatch volume** — easy to over-log
7. **Idle / forgotten resources** — orphaned EBS volumes, snapshots, ELBs

## Compute Right-Sizing

### Tools
- **Compute Optimizer** — AWS reads your CloudWatch metrics and recommends sizes. Free. Enable at org level.
- **CloudWatch Container Insights** — per-task CPU + memory utilization (need this for ECS recommendations)
- **AWS Trusted Advisor (Business / Enterprise tiers)** — flags low-utilization EC2/RDS

### ECS Fargate sizing rules
- Target average CPU: 50-70%. If <30%, downsize. If >80%, upsize.
- Memory: provision to peak + 20% buffer. Bursting causes OOM kills.
- ARM64 (Graviton): default for new services, 20% cheaper

### RDS sizing
- Production: Multi-AZ, t4g (Graviton burstable) for low-load, m7g for sustained
- Don't use db.t3 in prod for sustained load — credits run out
- **RDS Proxy** for high-connection-count services (each Lambda invocation can spawn a connection; Proxy multiplexes)

## Savings Plans + Reserved Instances

### Compute Savings Plans (recommended over EC2 RIs for most cases)
- Apply to EC2, Fargate, Lambda
- 1-year all-upfront: ~30% savings
- 3-year all-upfront: ~50% savings
- Commit to a $/hour spend, applied to any compute

Strategy:
- Cover **baseline** with 3-year SP (the always-on minimum capacity)
- Cover **growth** with 1-year SP every 6 months (rolling)
- Leave **bursty** capacity on-demand

Math example:
```
Baseline:  2 ECS tasks × $0.04/hr × 730hr = $58.40/mo on-demand
With 3yr Compute SP (50% off): $29.20/mo
Annual savings: $350/mo per service. At 10 services = $3.5k/yr.
```

### RDS Reserved Instances
- Production DBs are always-on → 1yr or 3yr RI is a lock
- Multi-AZ counts as 2× the instance for RI purposes
- ~30-60% savings vs on-demand

### ElastiCache Reserved Nodes
- Same model. Worth it for production. Skip for dev.

### Don't Reserve
- Workers that scale spiky → use Spot or on-demand
- Anything you might right-size in the next year — RIs lock you in
- New services in their first 6 months — usage is unpredictable

## Spot

### Where it works
- ECS Fargate Spot for **stateless, idempotent workers** (Kafka consumers, dbt jobs, batch ML)
- Up to 70% cheaper
- 2-min interruption warning via SIGTERM → app must drain

### Where it doesn't
- User-facing API tasks (interruption = customer impact)
- Stateful workloads (DBs, in-memory caches)
- Anything where the 2-min drain time isn't enough

### Capacity provider strategy (mixed)
```hcl
capacity_provider_strategy {
  capacity_provider = "FARGATE"
  weight            = 70
  base              = 2
}
capacity_provider_strategy {
  capacity_provider = "FARGATE_SPOT"
  weight            = 30
}
```
70/30 on-demand/spot is a safe mix for non-critical services. Pure Spot for batch.

## S3 Cost Optimization

### Storage class selection
| Class | Use case | Cost |
|---|---|---|
| Standard | Hot, < 30 days | $0.023/GB |
| Intelligent-Tiering | Mixed/unknown access | Standard + $0.0025/1000 obj |
| Standard-IA | Infrequent, > 30 days | $0.0125/GB + retrieval $0.01/GB |
| Glacier Instant | Quarterly access | $0.004/GB |
| Glacier Flexible | Yearly access | $0.0036/GB + retrieval delay |
| Glacier Deep Archive | Compliance only | $0.00099/GB + 12hr retrieval |

### Lifecycle policy template
```hcl
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "tier-aging-data"
    status = "Enabled"
    filter { prefix = "exports/" }
    transition { days = 30  storage_class = "STANDARD_IA" }
    transition { days = 90  storage_class = "GLACIER_IR" }
    transition { days = 365 storage_class = "DEEP_ARCHIVE" }
    expiration { days = 2555 }   # 7y for compliance
  }
  rule {
    id     = "expire-incomplete-mpu"
    status = "Enabled"
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}
```

### S3 Intelligent-Tiering (when in doubt)
Set as default storage class on buckets where you don't know access patterns. AWS auto-tiers based on observed access. No retrieval fees within Frequent/Infrequent. ~$0.0025 per 1000 objects monitored.

### Common S3 cost leaks
- Versioning enabled + no expiration of old versions → infinite growth
- Incomplete multipart uploads not cleaned up → orphaned storage
- Cross-region replication for non-critical buckets → 2× storage + transfer
- Public S3 with no CloudFront → high request charges

## Data Transfer (the silent killer)

### Free
- Inbound to AWS: free
- Within same AZ: free
- VPC Endpoints (Gateway type — S3, DynamoDB): free

### Charged
- Inter-AZ: $0.01/GB each way
- Inter-region: $0.02/GB
- Egress to internet: $0.09/GB (first 10TB, decreasing tiers after)
- VPC Endpoints (Interface): $0.01/hr + $0.01/GB

### Strategies
- **Use VPC Endpoints** for S3 + DynamoDB (Gateway, free) and Secrets Manager + ECR + CloudWatch Logs (Interface, paid but cheaper than NAT for high traffic)
- **Co-locate services in same AZ** when possible (App Mesh `preferLocal` weighting)
- **CloudFront in front of API** for any public endpoint > 1TB egress/month
- **Compress** API responses (gzip / brotli) to reduce egress

### NAT Gateway: the most common surprise bill
- $0.045 per GB processed
- A service doing 1TB/mo of egress through NAT = $45/mo just for processing
- Move common destinations to VPC Interface Endpoints (~$10/mo per endpoint, but only $0.01/GB)
- Break-even: ~285GB/mo per service

## CloudWatch Cost Control

### Logs
- INFO + WARN + ERROR in prod. DEBUG only in staging.
- Sample high-volume INFO logs (e.g., access logs at 10%)
- Move beyond-retention to S3 + Athena for compliance retention

### Metrics
- Custom metrics: $0.30/metric/mo. With 100 services × 50 metrics each = $1500/mo. Discipline matters.
- High-cardinality dimensions explode cost. Don't include `tenantId` in every dimension; use AMP for that.
- EMF (Embedded Metric Format) emits metrics inside log lines — same cost as a metric, but no extra API call

### Container Insights
- "default" tier: $1.50 per task/mo
- "enhanced" tier: $2.55 per task/mo
- Enable enhanced only for services where you need GPU/storage metrics

## Lambda Cost Optimization

- Use ARM64 (Graviton2) — 34% cheaper, comparable perf
- Right-size memory: each Lambda has a sweet spot. AWS Lambda Power Tuning tool finds it.
- Lambda SnapStart for Java functions (cold start mitigation)
- Avoid Provisioned Concurrency unless you have predictable traffic and tight latency SLO

## Common Cost Anti-Patterns (from real audits)

- ❌ Forgotten dev environments running 24/7 (use auto-shutdown via Instance Scheduler)
- ❌ Orphaned EBS volumes after instance termination (set deleteOnTermination = true on creation)
- ❌ Snapshots accumulating with no lifecycle (DLM — Data Lifecycle Manager — automates)
- ❌ Public-facing ELBs that should be internal
- ❌ Multi-AZ on dev RDS instances (single-AZ is fine for dev)
- ❌ Reserved Instances on instance types you've outgrown
- ❌ S3 versioning + no version expiration = infinite cost growth
- ❌ CloudFront caching too short → high origin requests
- ❌ Logging full request bodies including base64 images

## Tooling

- **AWS Cost Explorer** — primary lens. Set up a "by-service" + "by-tag" view.
- **AWS Cost Anomaly Detection** — ML-based alerts on unusual spend
- **AWS Budgets** — hard alerts at 80% / 100% of monthly budget
- **AWS Compute Optimizer** — sizing recommendations
- **Tag policies (Org-level)** — enforce required tags (`env`, `service`, `cost_center`) for chargeback

## Tag Strategy (mandatory)

```
env:           production | staging | dev
service:       <service-name>
owner:         <agent or team>
cost_center:   <eng | ops | data | growth>
managed_by:    terraform | manual
data_class:    public | internal | sensitive | pii
```

Enforce via SCPs (Service Control Policies) at the Org level. Resources without tags get auto-blocked from creation.
