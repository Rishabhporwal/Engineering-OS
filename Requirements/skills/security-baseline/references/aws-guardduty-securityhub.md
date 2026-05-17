# AWS Security Services — GuardDuty, Security Hub, Config, Inspector

The AWS-native security stack. Enable all four at the org level for any
production workload. Used by Shreya during reviews and Aarav during incidents.

## GuardDuty (threat detection)

ML-based threat detection across:
- VPC Flow Logs (anomalous outbound, port scanning, crypto mining patterns)
- CloudTrail (suspicious API calls, leaked-credential usage)
- DNS logs (queries to known-malicious domains)
- S3 Data Events (anomalous access patterns)
- EKS audit logs (pod escape, privilege escalation)

### Enable org-wide
```hcl
resource "aws_guardduty_organization_admin_account" "main" {
  admin_account_id = var.security_account_id
}

resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  
  datasources {
    s3_logs                  { enable = true }
    kubernetes               { audit_logs { enable = true } }
    malware_protection       { scan_ec2_instance_with_findings { ebs_volumes { enable = true } } }
  }
}
```

### Cost
- VPC Flow Log analysis: ~$1 per million events
- CloudTrail analysis: ~$4 per million events
- Typical mid-sized prod: ~$200-400/mo

### Findings → Alerts
GuardDuty findings → EventBridge rule → SNS topic → Slack #security + PagerDuty.

```hcl
resource "aws_cloudwatch_event_rule" "guardduty_high" {
  name        = "guardduty-high-findings"
  description = "Route HIGH/CRITICAL GuardDuty findings to security oncall"
  event_pattern = jsonencode({
    source        = ["aws.guardduty"]
    detail-type   = ["GuardDuty Finding"]
    detail = {
      severity = [{ "numeric": [">=", 7] }]    # HIGH (7-8.9) and CRITICAL (9+)
    }
  })
}

resource "aws_cloudwatch_event_target" "to_pagerduty" {
  rule = aws_cloudwatch_event_rule.guardduty_high.name
  arn  = aws_sns_topic.security_oncall.arn
}
```

### Common findings (and what they mean)

| Finding | Likely cause | Action |
|---|---|---|
| `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration` | Credentials leaked, in use outside VPC | Revoke role, rotate, investigate path |
| `Recon:EC2/PortProbeUnprotectedPort` | SG opens unintended port | Tighten SG immediately |
| `Trojan:EC2/DropPoint` | EC2 calling C2 server | Isolate instance, snapshot for forensics |
| `CryptoCurrency:EC2/BitcoinTool.B` | Compromised instance mining | Same as above |
| `PenTest:IAMUser/KaliLinux` | Pen-test tool detected | Confirm authorized; if yes, suppress; if no, investigate |

## AWS Config (compliance + drift)

Records every AWS resource configuration change. Pairs with rules that flag non-compliance.

### Standard rules to enable

```hcl
locals {
  required_rules = [
    "encrypted-volumes",                   # all EBS encrypted
    "rds-storage-encrypted",
    "rds-snapshot-encrypted",
    "s3-bucket-public-read-prohibited",
    "s3-bucket-public-write-prohibited",
    "s3-bucket-server-side-encryption-enabled",
    "s3-bucket-ssl-requests-only",
    "iam-password-policy",
    "iam-user-mfa-enabled",
    "root-account-mfa-enabled",
    "root-account-hardware-mfa-enabled",
    "vpc-flow-logs-enabled",
    "cloud-trail-enabled",
    "cloud-trail-encryption-enabled",
    "cloud-trail-log-file-validation-enabled",
    "ec2-imdsv2-check",                    # only IMDSv2, not v1
    "alb-http-to-https-redirection-check",
    "elb-tls-https-listeners-only",
    "incoming-ssh-disabled",
    "restricted-ssh",
    "ecs-task-definition-non-root-user",
    "ecs-no-environment-secrets",          # secrets in env vars (not Secrets Manager) flagged
  ]
}
```

### Conformance Packs
Pre-built rule bundles for compliance frameworks:
- `Operational-Best-Practices-for-PCI-DSS`
- `Operational-Best-Practices-for-HIPAA-Security`
- `Operational-Best-Practices-for-SOC-2`
- `CIS-AWS-Foundations-Benchmark`

Apply per environment via Terraform.

### Cost
- $0.003 per configuration item recorded
- $0.001 per rule evaluation
- Typical: $50-200/mo per account

## Security Hub (aggregator)

Central dashboard for findings from GuardDuty, Inspector, Macie, Config, IAM Access Analyzer, etc.

### Enable + standards
```hcl
resource "aws_securityhub_account" "main" {}

resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:::ruleset/finding-format/aws-foundational-security-best-practices/v/1.0.0"
  depends_on    = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.4.0"
  depends_on    = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "pci" {
  standards_arn = "arn:aws:securityhub:::ruleset/pci-dss/v/3.2.1"
  depends_on    = [aws_securityhub_account.main]
}
```

### Insights (saved queries)
- "Failed password attempts in last 24h"
- "Public S3 buckets across all accounts"
- "IAM users without MFA"
- "EC2s with public IPs and open security groups"

### Findings → JIRA / Linear / ClickUp
EventBridge → Lambda → ticket in your task tracker. CRITICAL findings auto-create P0 tickets assigned to Shreya.

## Inspector (vulnerability scanning)

Scans:
- ECR images for CVEs (continuous on push)
- EC2 instances for OS-level CVEs
- Lambda functions for vulnerable dependencies

### ECR integration
```hcl
resource "aws_inspector2_enabler" "main" {
  account_ids    = [data.aws_caller_identity.current.account_id]
  resource_types = ["ECR", "EC2", "LAMBDA"]
}
```

When a builder pushes an image to ECR, Inspector scans within ~5 min. Findings:
- CRITICAL CVE in production image → Shreya tagged, deployment blocked
- HIGH CVE → ticket, fix in next sprint
- MEDIUM/LOW → bulk-triage monthly

### CI gate
Block CI if image has unsuppressed CRITICAL findings:
```bash
aws inspector2 list-findings \
  --filter-criteria '{"awsEcrContainerImageDetails": {"imageTags": [{"comparison": "EQUALS", "value": "'$GIT_SHA'"}]}, "severity": [{"comparison": "EQUALS", "value": "CRITICAL"}]}' \
  --query 'findings | length(@)'
# Exit 1 if > 0
```

## Macie (S3 PII detection)

Scans S3 buckets for PII, PHI, credentials accidentally committed.

Enable for buckets with `data_class: sensitive` tag. Findings → Security Hub.

## IAM Access Analyzer

- **External access**: flags resources accessible by accounts outside your org
- **Unused access**: roles/permissions/keys not used in last 90 days
- **Custom policy validation**: lints IAM policies in Terraform PRs

Enable at org level. Free.

## CloudTrail (audit log foundation)

Mandatory. Org-wide trail to dedicated logging account. Cannot be disabled by member accounts.

```hcl
resource "aws_cloudtrail" "org" {
  name                          = "<org>-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  is_organization_trail         = true
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true              # tamper detection
  kms_key_id                    = aws_kms_key.cloudtrail.arn
  
  insight_selector {
    insight_type = "ApiCallRateInsight"             # detects anomalous bursts
  }
  insight_selector {
    insight_type = "ApiErrorRateInsight"            # detects scanning attempts
  }
}
```

S3 bucket lifecycle:
- Standard for 90 days (Athena queries fast)
- Glacier IR for 1 year
- Deep Archive for compliance retention (often 7 years)

### Athena queries (CloudTrail forensics)
```sql
SELECT eventTime, userIdentity.arn, eventName, sourceIPAddress, errorCode
FROM cloudtrail_logs
WHERE eventTime > '2026-05-01T00:00:00Z'
  AND errorCode IS NOT NULL
  AND userIdentity.arn LIKE '%suspicious-role%'
ORDER BY eventTime DESC
LIMIT 100;
```

## SCPs (Service Control Policies) — org-level guardrails

Set at the AWS Organizations level. Apply to entire OUs (e.g., all production accounts).

### Examples (mandatory in production OU)
```json
{
  "Sid": "DenyDisableSecurity",
  "Effect": "Deny",
  "Action": [
    "guardduty:DeleteDetector", "guardduty:DisableOrganizationAdminAccount",
    "config:DeleteConfigurationRecorder", "config:StopConfigurationRecorder",
    "cloudtrail:DeleteTrail", "cloudtrail:StopLogging",
    "securityhub:DisableSecurityHub"
  ],
  "Resource": "*"
}
```

```json
{
  "Sid": "DenyRegionsExceptApproved",
  "Effect": "Deny",
  "NotAction": ["iam:*", "organizations:*", "support:*", "route53:*", "cloudfront:*"],
  "Resource": "*",
  "Condition": {
    "StringNotEquals": { "aws:RequestedRegion": ["ap-south-1", "us-east-1"] }
  }
}
```

```json
{
  "Sid": "RequireImdsv2",
  "Effect": "Deny",
  "Action": "ec2:RunInstances",
  "Resource": "arn:aws:ec2:*:*:instance/*",
  "Condition": {
    "StringNotEquals": { "ec2:MetadataHttpTokens": "required" }
  }
}
```

Even if a developer/role has IAM permission, the SCP overrides. Use sparingly — they're hard to debug ("why won't this work?").

## Daily Security Posture (for Shreya)

Morning checklist:
1. Security Hub: any new CRITICAL or HIGH findings?
2. GuardDuty: any HIGH severity findings overnight?
3. Inspector: any new CRITICAL CVEs in production images?
4. IAM Access Analyzer: any new external access findings?
5. Cost Anomaly Detection: any unusual spend (might indicate compromise)?

Codify as a CloudWatch dashboard + Slack daily summary via Lambda.
