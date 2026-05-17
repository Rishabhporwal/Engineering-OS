# IAM + VPC — Deep Reference

## IAM: least privilege, always

### Per-service task roles
Every ECS service gets its own IAM role. Never share. Never use a wildcard role.

```hcl
data "aws_iam_policy_document" "service_task" {
  # Read its OWN secrets — no others
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:${var.service}/*"
    ]
  }
  # Decrypt with its OWN KMS key
  statement {
    actions = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [aws_kms_key.service.arn]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.region}.amazonaws.com"]
    }
  }
  # Read its OWN S3 bucket prefix
  statement {
    actions = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.service.arn}/${var.service}/*"]
  }
  # Publish to its OWN SNS topics / Kafka topics
  statement {
    actions = ["kafka-cluster:WriteData", "kafka-cluster:ReadData"]
    resources = ["arn:aws:kafka:${var.region}:${var.account_id}:topic/${var.cluster}/*/${var.service}.*"]
  }
}
```

Anti-pattern: a single "app-role" with `secretsmanager:*` — one compromise reads every secret.

### Conditions — narrow even further
- `aws:RequestedRegion` — limit to your primary region
- `aws:SourceVpc` — limit to your VPC (prevents exfil if creds leak)
- `aws:CurrentTime` — limit to business hours for sensitive ops
- `aws:MultiFactorAuthPresent` — required for human admin roles

### IAM Identity Center (formerly SSO)
Humans don't have IAM users. Period.
- Connect IdP (Okta, Google Workspace, Entra)
- Permission sets with read-only / power-user / admin scopes per AWS account
- Multi-account: Org → OU → accounts (separate accounts for sandbox / staging / prod)

### IAM Access Analyzer
Enable at the org level. Catches:
- Roles trusted by external accounts you didn't intend
- Resources accessible publicly (S3 buckets, KMS keys)
- Unused IAM access (helps with least-privilege right-sizing)

### CloudTrail
Org-wide trail to a dedicated logging account. Never deletable from member accounts.
- Management events: always
- Data events: enable for sensitive S3 buckets and Lambda functions
- Insights: detects anomalous API patterns

## VPC: the network spine

### Standard layout (per environment)

```
VPC: 10.0.0.0/16

Public subnets (1 per AZ × 3 AZs):
  10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24
  Resources: ALB, NAT Gateway, Bastion (if any)

Private app subnets (1 per AZ × 3 AZs):
  10.0.10.0/24, 10.0.11.0/24, 10.0.12.0/24
  Resources: ECS tasks, ECS Exec endpoints

Private data subnets (1 per AZ × 3 AZs):
  10.0.20.0/24, 10.0.21.0/24, 10.0.22.0/24
  Resources: RDS, ElastiCache, MSK
```

Why three subnet tiers: separates blast radius. App subnets can talk to data subnets, but data subnets can't initiate to public.

### Security Groups (stateful, allow-list)

```
ALB-SG:
  Ingress: 443 from 0.0.0.0/0 (or restricted CIDR if internal)
  Egress:  443 to ECS-SG

ECS-SG:
  Ingress: 3000 from ALB-SG (only)
  Egress:  443 to 0.0.0.0/0 (for AWS APIs and external deps via NAT)
           5432 to RDS-SG
           6379 to Redis-SG
           9092 to MSK-SG

RDS-SG:
  Ingress: 5432 from ECS-SG (only)
  Egress:  none (RDS doesn't need to call out)

Redis-SG:
  Ingress: 6379 from ECS-SG (only)
  Egress:  none

MSK-SG:
  Ingress: 9092/9094 from ECS-SG (only)
  Egress:  none
```

Iron rule: **never** use `0.0.0.0/0` ingress on an SG except ALB-SG-443. If you find one, file a P0 security ticket.

### NACLs (stateless, secondary)
SGs handle the "normal" case. NACLs are a safety net for:
- Blocking specific bad IPs at the subnet level
- Air-gapping a subnet during incident response (deny all)
- Preventing return traffic from a compromised resource

Default: leave NACLs at "allow all" and use SGs. Only modify NACLs during incidents.

### VPC Endpoints (PrivateLink) — for major AWS services

Without endpoints, traffic from ECS to S3/Secrets Manager/etc. goes via NAT Gateway (cost: $0.045/GB processed). With endpoints, it stays in the VPC (cost: $0.01/hr per endpoint, $0.01/GB processed).

Required endpoints for production:
- `com.amazonaws.<region>.s3` (Gateway type — free)
- `com.amazonaws.<region>.dynamodb` (Gateway type — free)
- `com.amazonaws.<region>.secretsmanager` (Interface — paid but cheaper than NAT for high volume)
- `com.amazonaws.<region>.ecr.api` + `com.amazonaws.<region>.ecr.dkr` (Interface — pulls images without NAT)
- `com.amazonaws.<region>.logs` (Interface — CloudWatch Logs ingestion)
- `com.amazonaws.<region>.kms` (Interface)
- `com.amazonaws.<region>.ssm` + `com.amazonaws.<region>.ssmmessages` (Interface — for ECS Exec)
- `com.amazonaws.<region>.execute-api` (Interface — for API Gateway calls)

Cost: ~$50-80/mo per environment for typical interface endpoints. Pays back at ~1-2TB of NAT traffic/month.

### NAT Gateway

One per AZ for HA (~$32/mo each + data charges). Use NAT Instances only for very low traffic dev environments (operationally fragile, single point of failure).

### Transit Gateway (multi-VPC)

Use when:
- Multiple VPCs need to talk (e.g., staging-vpc ↔ prod-vpc for shared services)
- Hybrid (on-prem connectivity via Direct Connect / VPN)
- Multi-account org

Cost: $36/mo + data + attachment charges. Plan capacity.

### Network ACLs vs Security Groups (the canonical rule)

| Concern | Use |
|---|---|
| Per-resource allow rules | Security Group (stateful) |
| Subnet-level deny | NACL (stateless, can deny) |
| Default | SG only; NACL = "allow all" |
| Incident response | NACL deny rule for specific IP/port |

## VPC Peering

Use **only** for low-volume, fixed-set, two-VPC connections. Otherwise prefer Transit Gateway. Peering doesn't transit — A↔B↔C requires both A↔B and A↔C peerings.

## Multi-AZ vs Multi-Region

| Failure | Multi-AZ helps? | Multi-region helps? |
|---|---|---|
| Single AZ outage | ✅ | ✅ |
| Whole AWS region outage | ❌ | ✅ (if active-active or warm DR) |
| Bad code deploy | ❌ | ❌ (rollback or canary helps) |
| Account compromise | ❌ | ❌ (separate accounts help) |

Default: multi-AZ in primary region. Add multi-region only when revenue / compliance / SLO justifies the operational tax (~30-50% more infra work + data replication complexity).

## VPC Flow Logs

Enable at VPC level → S3 bucket. Cost: $0.0025 per million log records. Use for:
- Forensics during security incidents
- Capacity planning
- Detecting anomalous traffic patterns (egress to unknown IPs)

Send to S3 (cheap, queryable via Athena), not CloudWatch (more expensive).
