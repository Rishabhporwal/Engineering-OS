# AWS KMS + Secrets Manager — Deep Reference

## KMS (Key Management Service)

### Customer Managed Keys (CMKs) — use these, not AWS-managed
| Aspect | AWS-managed (default) | Customer-managed (recommended) |
|---|---|---|
| Key policy | AWS controls | You control |
| Rotation | Yearly (auto) | Yearly auto OR custom rotation |
| Cross-account use | Limited | Full control |
| Audit trail | Limited | CloudTrail data events available |
| Cost | Free | $1/mo per CMK + $0.03/10k requests |

For production: one CMK per blast-radius (per service is overkill; per data classification is right).

### Standard CMK setup per environment

```hcl
resource "aws_kms_key" "data" {
  description              = "Encrypt sensitive data — PII / payments / auth"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"
  deletion_window_in_days  = 30                  # window to abort accidental deletion
  enable_key_rotation      = true                # auto annual rotation
  multi_region             = false               # set true only for multi-region projects
  policy                   = data.aws_iam_policy_document.kms_data.json
}

resource "aws_kms_alias" "data" {
  name          = "alias/<env>-data"
  target_key_id = aws_kms_key.data.id
}

data "aws_iam_policy_document" "kms_data" {
  # Root account always has full access (don't lock yourself out)
  statement {
    sid     = "RootFullAccess"
    actions = ["kms:*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.account_id}:root"]
    }
    resources = ["*"]
  }
  # Specific roles can encrypt/decrypt via specific services
  statement {
    sid     = "ServiceUseViaSecretsManager"
    actions = ["kms:Decrypt", "kms:GenerateDataKey"]
    principals {
      type        = "AWS"
      identifiers = local.service_task_role_arns
    }
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.region}.amazonaws.com"]
    }
  }
  # Force CloudTrail logging of all key uses
  statement {
    sid     = "DenyWithoutSourceVpc"
    effect  = "Deny"
    actions = ["kms:*"]
    principals { type = "AWS" identifiers = ["*"] }
    resources = ["*"]
    condition {
      test     = "StringNotEqualsIfExists"
      variable = "aws:SourceVpc"
      values   = [var.vpc_id]
    }
  }
}
```

### Envelope encryption (the right pattern for app-level data)
- KMS encrypts **data keys**, not your data directly
- Each large blob gets a fresh data key (DEK)
- KMS encrypts the DEK; you store DEK alongside the ciphertext
- Reads: GenerateDataKey (or LoadDecrypted) → KMS Decrypt the DEK → AES-decrypt the blob

In practice: AWS SDKs do this automatically (RDS at-rest encryption, S3 SSE-KMS, etc.). Only worry about it for application-level encryption (e.g., field-level PII in Postgres).

### Multi-region keys (when needed)
- Active-active multi-region apps need replicas of the CMK in each region
- Replicas share the same key material — same ciphertext can be decrypted in any region
- Enable only when the app is genuinely multi-region; doubles cost

### KMS Grants (fine-grained, time-bound)
For temporary access: a Lambda needs to decrypt a customer's data once.

```bash
aws kms create-grant \
  --key-id alias/data \
  --grantee-principal arn:aws:iam::...:role/customer-export-lambda \
  --operations Decrypt \
  --constraints EncryptionContextSubset={tenant_id=tenant_123}
```

Auto-expires. More secure than adding the role to the key policy permanently.

### Audit
CloudTrail data events for KMS:
```hcl
resource "aws_cloudtrail" "kms_data_events" {
  ...
  event_selector {
    read_write_type = "All"
    data_resource {
      type   = "AWS::KMS::Key"
      values = [aws_kms_key.data.arn]
    }
  }
}
```

This is mandatory for auditable compliance regimes (HIPAA, PCI). It's noisy — consider sampling for low-sensitivity environments.

## Secrets Manager

### Per-secret structure
```hcl
resource "aws_secretsmanager_secret" "service_db_url" {
  name                    = "${var.service}/database_url"
  description             = "Postgres connection string for ${var.service}"
  kms_key_id              = aws_kms_key.data.id
  recovery_window_in_days = 30
  replica { region = "us-east-1" }     # cross-region replication for DR
}

resource "aws_secretsmanager_secret_version" "service_db_url" {
  secret_id     = aws_secretsmanager_secret.service_db_url.id
  secret_string = jsonencode({
    username = "..."
    password = "..."        # never commit; populate via separate channel
    engine   = "postgres"
    host     = "..."
    port     = 5432
    dbname   = "..."
  })
}
```

Naming convention: `<env>/<service>/<key>` so policies like `arn:aws:secretsmanager:...:secret:<env>/<service>/*` work.

### ECS task injection
```json
"secrets": [
  { "name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:...:secret:<env>/<service>/database_url" }
]
```
ECS pulls at task start, sets as env var. Never logged. Never written to disk.

### Rotation
RDS secrets rotate via Lambda automatically:
```hcl
resource "aws_secretsmanager_secret_rotation" "db" {
  secret_id           = aws_secretsmanager_secret.service_db_url.id
  rotation_lambda_arn = aws_lambda_function.rotate_db.arn
  rotation_rules { automatically_after_days = 30 }
}
```

For non-RDS secrets (third-party API keys), write a custom rotation Lambda or rotate manually quarterly with calendar reminders.

### Cost
- $0.40 per secret per month
- $0.05 per 10,000 API calls
- Cache locally — don't call `GetSecretValue` on every request. Inject at task start; refresh on rotation event via SNS.

### Anti-Patterns
- ❌ One mega-secret with all keys → blast radius too large
- ❌ Secrets in CloudFormation/Terraform plain text outputs
- ❌ Secrets in ECS env vars (not the `secrets` block) → readable in task definition
- ❌ Long-lived database passwords with no rotation
- ❌ Sharing secrets across services (each service owns its credentials)

## SSM Parameter Store (alternative)

Use Parameter Store (not Secrets Manager) for:
- Non-sensitive config (feature flags, log levels) — Standard tier is FREE
- Sensitive but low-cost (SecureString, KMS-encrypted) — also free for Standard

Use Secrets Manager (not Parameter Store) for:
- Anything needing automatic rotation
- Anything needing cross-region replication
- Anything where Secrets Manager's audit trail is required

Hybrid: feature flags in Parameter Store, credentials in Secrets Manager.

## Cross-Account Secrets Sharing (rare)

If a sandbox account needs read-only access to a staging secret:

1. Resource policy on the secret allows the sandbox's role
2. KMS key policy on the encryption key allows decrypt from sandbox account
3. Sandbox role has `secretsmanager:GetSecretValue` permission

This is a footgun. Avoid unless absolutely necessary; prefer copying a sanitized version.

## What NOT to put in secrets
- Public information (API endpoints, region names) — env vars are fine
- Source code or large config files — use S3 with KMS
- Per-tenant secrets at high cardinality (>1000 tenants) — design a separate vault (HashiCorp Vault, or per-tenant KMS grant patterns)
