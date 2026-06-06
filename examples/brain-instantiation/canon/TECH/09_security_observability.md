# TECH/09 — Security & Observability

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E1 (Tech Lead) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md)

This document specifies:
- Authentication (Supabase Auth) and authorization
- AWS IAM, service-to-service trust
- Secret management (AWS Secrets Manager + KMS envelope encryption)
- Audit logging
- Data protection: encryption, PII, residency
- Vulnerability management
- Observability stack: CloudWatch + X-Ray + Sentry + PostHog
- Incident response and on-call
- SLOs at 100k req/min scale
- Compliance roadmap (SOC 2)

---

## 1. Authentication

### Provider: Supabase Auth

- Email + password
- Magic links
- Google OAuth
- Server-side JWT validation

### JWT Claims

```json
{
  "sub": "user_uuid",
  "email": "...",
  "app_metadata": {
    "active_workspace_id": "uuid",
    "workspaces": [
      {"id": "ws_1", "role": "owner"},
      {"id": "ws_2", "role": "analyst"}
    ],
    "is_admin": false
  },
  "iat": 1700000000,
  "exp": 1700003600
}
```

- Access token: 1 hour
- Refresh token: 30 days; rotated on use
- Cookies: HttpOnly, Secure, SameSite=Lax

### Workspace Switching

When user switches, Supabase issues a new JWT with new `active_workspace_id`. Old token expires naturally; api-gateway validates `active_workspace_id` matches requested workspace on every call.

### MFA (Phase 3)

Optional TOTP for owners/admins. Recovery codes hashed and stored. Mandatory for paying enterprise workspaces (Phase 4).

### Account Lockout

- 5 failed logins in 15 min → 15-min lock
- 10 in 1 hour → 1-hour lock
- Owner notification on repeated lockouts
- Brain admin can unlock manually (audited)

---

## 2. Authorization

### Roles (Per Workspace)

| Role | Permissions |
|------|-------------|
| **Owner** | Everything; billing; integrations; auto-execute enablement; delete workspace |
| **Operator** | Operational write; approve/reject; lifecycle campaigns; inbox; cannot change billing or delete brand |
| **Analyst** | Read all + comment; modify goals, marketing actions, alert rules; no approvals/execution |
| **Agency** | Scoped per-brand read/write as granted by Owner; every action tagged + audited |
| **Viewer** | Read-only; no PII; no exports; no actions |

### System-Level Roles

| Role | Permissions |
|------|-------------|
| **Brain Admin** | Cross-workspace read; impersonate (audited); manage system |
| **Brain Engineer** | DB read via audited Aurora replica role |

### Enforcement (Defense in Depth)

1. **api-gateway:** tRPC procedure tier (`workspaceProcedure`, `ownerProcedure`, ...)
2. **gRPC:** server-side interceptor validates `x-workspace-id` metadata + role from token
3. **Postgres:** RLS policies
4. **ClickHouse:** workspace_id ordering key + query gateway enforcement

### Cross-Workspace (Admin)

Brain Admins access `/admin/*` routes. Their queries hit Postgres via a separate `app_admin` Postgres role with `BYPASSRLS`. Every such query is logged to `audit_log`.

### Impersonation (Phase 2)

For customer support:

```sql
CREATE TABLE impersonation_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID NOT NULL REFERENCES auth.users(id),
  target_user_id UUID NOT NULL REFERENCES auth.users(id),
  target_workspace_id UUID NOT NULL,
  reason TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  actions_taken JSONB
);
```

Red banner in UI during impersonation: "Impersonating the pilot brand / Rishabh — End Impersonation".

---

## 3. AWS IAM & Service-to-Service Trust

### IRSA (IAM Roles for Service Accounts)

Every EKS pod has an IAM role via IRSA. No long-lived AWS access keys in pods.

```yaml
# k8s/api-gateway/service-account.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-gateway
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/brain-api-gateway
```

```hcl
# infra/cdk/lib/iam.ts (CDK)
const apiGatewayRole = new iam.Role(this, 'ApiGatewayRole', {
  assumedBy: new iam.OpenIdConnectPrincipal(oidcProvider, {
    StringEquals: {
      [`${oidcProvider.providerArn}:sub`]: 'system:serviceaccount:brain:api-gateway'
    }
  }),
  inlinePolicies: {
    KafkaAccess: kafkaAccessPolicy,
    SecretsAccess: secretsAccessPolicy,
    SesAccess: sesAccessPolicy,                  // for AWS SES
  },
});
```

### Service-to-Service AuthN

Two layers:

**Network:** VPC security groups + Kubernetes NetworkPolicies. Only api-gateway can reach core-service; only analytics-service can reach ClickHouse cluster; etc.

**Application (Phase 2+):** Service mesh (Istio or AWS App Mesh) provides mTLS, identity-based authn, and traffic policies. Each pod gets a SPIFFE-style identity certificate. Auto-rotated.

### Database Auth (RDS / Supabase)

Postgres connections use IAM authentication:

```typescript
// apps/core-service/src/db.ts
import { Signer } from "@aws-sdk/rds-signer";

const signer = new Signer({
  hostname: PG_HOST,
  port: 5432,
  username: 'core_service_role',
});

const token = await signer.getAuthToken();
const pool = new Pool({
  host: PG_HOST,
  user: 'core_service_role',
  password: token,
  ssl: { rejectUnauthorized: true },
});
```

Tokens valid 15 minutes; auto-refreshed. No static passwords in env vars.

For Supabase (managed): a dedicated database role per service (no shared `postgres` superuser). Password rotated via Secrets Manager every 90 days.

---

## 4. Secret Management

### AWS Secrets Manager

- All credentials (OAuth tokens, API keys, DB passwords) in Secrets Manager
- Per-environment (dev/staging/prod) namespacing
- Auto-rotation enabled where supported (RDS passwords)
- KMS encryption with per-environment keys
- IAM policy: each service's IRSA role grants `secretsmanager:GetSecretValue` only to its own secrets

### Encryption Pattern: KMS Envelope

For workspace-scoped credentials (OAuth tokens for Shopify/Meta/etc.):

```
1. Plaintext token
2. Generate Data Encryption Key (DEK) via KMS GenerateDataKey
3. Encrypt token with DEK (locally, AES-256-GCM)
4. KMS returns DEK + KMS-encrypted DEK
5. Store: ciphertext + KMS-encrypted DEK + secret_arn (in Secrets Manager)
6. To decrypt: KMS Decrypt the wrapped DEK → use to decrypt ciphertext
```

This gives us:
- Per-workspace cryptographic isolation
- Key rotation by re-wrapping DEKs (no re-encryption of large data)
- KMS audit logs for every key use

### Secret Rotation

- KMS keys (KEK): annual (via AWS Key Manager auto-rotation)
- RDS passwords: 90 days (Secrets Manager rotation Lambda)
- OAuth tokens: per-provider expiry; refreshed by ingestion-service
- API tokens issued to customers: customer-controlled

### Local Development

`.env.local` (gitignored) with development-only credentials. Loaded via `dotenv`. Never production secrets.

---

## 5. Data Protection

### Encryption At Rest

- **RDS / Supabase:** AES-256, KMS-managed
- **ClickHouse Cloud:** AES-256
- **S3:** SSE-S3 default; SSE-KMS for export buckets containing customer data
- **MSK:** encrypted at rest (per AWS standard)
- **EBS volumes (EKS):** KMS-encrypted

### Encryption In Transit

- All HTTPS (TLS 1.2+); HSTS header
- DB connections: TLS required; cert-pinned in production
- Internal gRPC: TLS via service mesh (Phase 2+)
- Kafka: TLS + SASL/AWS_MSK_IAM for client auth

### PII Inventory

| Field | Source | Sensitivity | Notes |
|-------|--------|-------------|-------|
| Customer email | Shopify | Medium | For matching across channels |
| Customer phone | Shopify | Medium | For Klaviyo/SMS attribution |
| Customer name | Shopify | Low | Stored |
| Customer address | Shopify | Medium | Default to **pincode/city-level** for analytics; full address only if a workflow requires it + approved (BR §19.3) |
| Order details | Shopify | Low | Stored |
| Brain user emails | Supabase Auth | Medium | For login |
| OAuth tokens | Various | **High** | KMS envelope-encrypted |
| Shiprocket credentials | Operator | **High** | KMS envelope-encrypted |

### Data Minimization

- We don't store customer payment card details (Shopify handles)
- We don't store customer passwords (Shopify customers, not Brain users)
- We sync only fields we use
- Address fields not needed for analytics aren't pulled

### Right to Deletion

Workspace owner request → within 30 days:
1. Soft-delete (`workspaces.deleted_at`)
2. Disable integrations, revoke tokens
3. Suspend sync jobs
4. After 90 days, hard-delete (purge raw, canonical, derived, AI tables; remove from ClickHouse via `ALTER TABLE ... DELETE WHERE workspace_id = ?`)
5. Retain only audit log (legally required)

Customer-level deletion (within a workspace): supported as a DPDP right-to-erasure workflow — see `16_compliance_engine.md` §4.4 (purge plaintext PII across Postgres + ClickHouse + S3 + audiences; consent set to withdrawn; audit entry retained). Phased per TECH/16 §7 (self-serve erasure in Phase 3).

### Multi-Region Residency (Phase 4)

EU workspaces' data never leaves eu-central-1. India workspaces' data stays in ap-south-1. Per-region Supabase project, per-region ClickHouse cluster, per-region MSK.

---

## 6. Audit Logging

```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  workspace_id UUID,
  actor_user_id UUID,
  actor_type TEXT NOT NULL,                       -- 'user', 'system', 'admin', 'api_token', 'service'
  action TEXT NOT NULL,                           -- 'goal.create', 'integration.disconnect', ...
  resource_type TEXT,
  resource_id TEXT,
  details JSONB,
  ip_address INET,
  user_agent TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_workspace ON audit_log(workspace_id, occurred_at DESC);
CREATE INDEX idx_audit_log_actor ON audit_log(actor_user_id, occurred_at DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, occurred_at DESC);
```

### What's Logged

- Workspace creation / deletion / region change
- Member invitations / removals / role changes
- Integration connect / disconnect
- Goal CRUD
- Cost settings changes
- Campaign classifications
- Impersonation start/end + every action during it
- Bulk operations (CSV imports)
- API token issuance / revocation
- Failed logins
- Admin queries via BYPASSRLS

### Streamed to S3

Audit log also written async to S3 via Kinesis Firehose (immutable archive, 7-year retention). Hard delete from Postgres after 1 year; S3 archive remains.

### Visibility

- Workspace owners can view their workspace's audit log
- Brain Admins can query across workspaces (also audited)

---

## 7. Vulnerability Management

### Dependency Scanning

- **GitHub Dependabot** for all repos; critical CVEs auto-PR within 24h
- Weekly review of open PRs
- **Renovate** for granular update control

### Static Analysis

- **ESLint** + `eslint-plugin-security`
- **TypeScript strict** mode
- **Ruff** + **Bandit** for Python
- **CodeQL** GitHub-native scanning on every PR
- **Semgrep** custom rules for Brain-specific anti-patterns (e.g., raw SQL without workspace_id filter)

### Container Image Scanning

- **Trivy** scans every Docker build (CI)
- Base images: `node:24-alpine`, `python:3.13-slim`, or distroless variants
- **AWS ECR image scanning** on push (enhanced scanning enabled)

### Penetration Testing

- Internal pen test before Phase 3 (10+ paying customers)
- External annual pen test from Phase 4 (e.g., Bishop Fox, Cobalt)

### Bug Bounty

- HackerOne-style program at Phase 4 (50+ workspaces)

---

## 8. Threat Model (Summary)

| Threat | Mitigation |
|--------|-----------|
| **Cross-tenant data leak** | Four-layer enforcement: tRPC tier + gRPC interceptor + Postgres RLS + ClickHouse query gateway |
| **OAuth token theft** | KMS envelope encryption; per-workspace DEK; KEK in KMS (never exported) |
| **Phishing → account takeover** | MFA for owners/admins; short JWT; suspicious-login detection |
| **SQL injection** | Parameterized queries only; no string concatenation; CI lint rule blocks raw SQL |
| **XSS in user content** | React default escaping; no `dangerouslySetInnerHTML` for user content; CSP headers |
| **CSRF** | SameSite=Lax cookies; tRPC mutations check Origin |
| **Insider data exfiltration** | RLS bypass audited; quarterly access reviews; admin actions surface in workspace owner's audit log |
| **Supply chain attack** | Lockfile-only installs; renovate review; signed commits (Phase 3) |
| **DDoS** | CloudFront + AWS Shield Standard; rate limits |
| **Replay attacks** | JWT iat/exp validation; refresh token single-use; nonces on sensitive ops |
| **Shopify webhook spoofing** | HMAC signature verification |
| **Service-to-service spoofing** | mTLS via service mesh (Phase 2); IRSA-based IAM authn |
| **Kafka topic compromise** | MSK IAM authorization; per-service topic ACLs |
| **ClickHouse query escape** | Query gateway pattern; workspace_id literal enforcement |

---

## 8a. Mobile-Specific Security

The React Native mobile app (TECH/10) introduces an additional attack surface: lost/stolen devices, hostile networks, app tampering. Mobile security follows **OWASP MASVS Level 1 + key Level 2 controls.**

### Threat Surfaces Unique to Mobile

| Threat | Mitigation |
|--------|-----------|
| **Stolen/unlocked phone — attacker opens Brain app** | Refresh token in Keychain/Keystore with `WhenUnlockedThisDeviceOnly`; biometric re-auth after backgrounding (Phase 2) |
| **MITM on hostile WiFi (café, airport)** | TLS certificate pinning against api-gateway cert + rotation cert |
| **Tampered Brain app (sideloaded modified APK)** | App attestation via Apple DeviceCheck + Play Integrity API (Phase 3); api-gateway gates critical mutations on attestation token |
| **Reverse-engineered API tokens from APK** | No long-lived API tokens in client; all auth via short-lived JWTs refreshed from Keychain |
| **Jailbreak/root with debug attached** | `expo-device.isRootedExperimentalAsync()` detection + Sentry alert (don't block — too aggressive; some power users root) |
| **Screenshot of sensitive financial data** | `FLAG_SECURE` on Android + iOS equivalent for screens showing revenue/margin (Phase 2) |
| **Deep link spoofing** | Validate scheme + host before navigation; only `brain://` + verified universal links accepted |
| **Push notification spoofing** | Verify notification payload signature; deep link target validated before opening |
| **Outdated app with known CVE** | `min_supported_version` table; api-gateway returns `426 Upgrade Required` on out-of-date clients |

### Secure Token Storage

```typescript
// Refresh tokens — Keychain (iOS) / Keystore (Android)
import * as SecureStore from 'expo-secure-store';

await SecureStore.setItemAsync('brain.refresh_token', token, {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
});
```

- iOS: tokens encrypted, hardware-backed via Secure Enclave when available, not synced to iCloud
- Android: tokens in EncryptedSharedPreferences backed by Keystore
- Access tokens: **in-memory only, never persisted** — lost on app kill, forcing refresh-token round-trip on cold start

### TLS Certificate Pinning

Production mobile builds pin api-gateway TLS certificate:

```typescript
// apps/mobile/lib/network/pinning.ts (managed via expo-ssl-pinning module)
const PINS = [
  'sha256/AAAA...current-cert-pin',
  'sha256/BBBB...rotation-cert-pin',
];
```

**Rotation procedure** (to avoid bricking the app on cert renewal):
1. Add new cert's SHA-256 to PINS array
2. OTA update with new pin (one week before cert rotation)
3. Rotate cert on api-gateway
4. Remove old pin in next OTA

**Kill switch:** if all pins fail, app calls a non-pinned health endpoint to fetch a fresh pin set, then retries. Prevents permanent connectivity loss from a botched rotation.

### App Attestation (Phase 3)

```typescript
// Mobile: generate attestation on critical operations
import * as DeviceCheck from 'expo-device-check';

const attestation = await DeviceCheck.generateAttestationToken();
headers['X-App-Attestation'] = attestation;
```

api-gateway validates against Apple DeviceCheck (iOS) or Play Integrity API (Android). Gated endpoints:
- Authentication / login
- Workspace creation
- Integration connection (OAuth callbacks)
- Goal mutations
- Any mutation that could be abused at scale

Failed attestation → 403; logged + investigated.

### Sensitive Screen Protection (Phase 2)

Financial summary screens (revenue, margins) mark themselves sensitive:

```typescript
// iOS: prevents screenshot + screen recording while on this screen
// Android: FLAG_SECURE
import { setScreenCaptureBlock } from 'react-native-prevent-screenshot';

useEffect(() => {
  setScreenCaptureBlock(true);
  return () => setScreenCaptureBlock(false);
}, []);
```

Applied to: P&L view, CM Waterfall (when added to mobile), Plan Module forecasts.

### Deep Link Validation

```typescript
// apps/mobile/lib/deeplink/handler.ts
const VALID_HOSTS = new Set(['alerts', 'insights', 'workspaces', 'auth']);

export function handleDeepLink(url: string) {
  const parsed = new URL(url);
  if (parsed.protocol !== 'brain:' && parsed.host !== '{BRAIN_DOMAIN}') {
    Sentry.captureMessage('Invalid deep link rejected', { extra: { url } });
    return;
  }
  if (parsed.protocol === 'brain:' && !VALID_HOSTS.has(parsed.host)) {
    return;
  }
  navigate(parsed.host, Object.fromEntries(parsed.searchParams));
}
```

### Out-of-Date Client Enforcement

```typescript
// api-gateway middleware
const minVersion = await coreClient.getMinSupportedAppVersion({ platform });
if (clientVersion < minVersion) {
  return new Response('Update required', { status: 426 });
}
```

Mobile app handles 426 by showing blocking "Update Brain to continue" screen. `min_supported_version` is a config table; bumped by E1 when a security-relevant fix ships and old versions must be retired.

### Audit Log for Mobile-Originated Actions

Every mutation from mobile is tagged with `actor_type='mobile_app'` + `device_id` in `audit_log`. Lets us investigate "every action this device ever took" if a device is reported stolen.

### Lost Device Workflow

User reports lost device → support team revokes:
1. Mark `mobile_push_tokens.active = false` for that device_id
2. Force-expire refresh tokens for that user (invalidate all sessions on all devices, since we don't track per-device refresh tokens)
3. User re-authenticates from trusted device

Phase 4: per-device refresh tokens + selective revocation.

### CI/CD Mobile-Specific Security

- **Code signing keys** (iOS distribution cert, Android upload keystore) in AWS Secrets Manager; EAS Build retrieves at build time
- **App Store Connect API key** rotated quarterly
- **No bundled secrets** — strict CI check that no `EXPO_PUBLIC_*` env var contains anything secret (PostHog public key + Sentry DSN are intentionally public; nothing else)
- **Source maps uploaded to Sentry** but not bundled in shipped builds

---

## 9. Compliance Roadmap

### Phase 1: Internal Hygiene

- Privacy Policy + Terms (lawyer-reviewed before public launch)
- Data Processing Agreement template
- Security FAQ for sales

### Phase 2: India DPDPA Compliance

- Data localization for Indian customer data (already done: ap-south-1)
- Consent collection guidelines documented
- DPO appointed (Phase 3 when revenue justifies)

### Phase 3-4: SOC 2 Type 1 → Type 2

- Engage auditor (Sprinto / Vanta / Drata)
- 12-month audit window
- Required for enterprise sales
- Estimated cost: $30-60K/year

### Phase 5: ISO 27001 / GDPR Specific (if EU customers)

---

## 10. Observability Stack

Five pillars; **centralized logging is the spine of incident debugging** at 100k req/min and microservices scale.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Logs (events) ← CENTRALIZED — primary incident-debugging surface     │
│  → Pod stdout → Fluent Bit DaemonSet → OpenSearch (hot, 14d)         │
│                                       → CloudWatch Logs (warm, 30d)  │
│                                       → S3 (cold archive, 1y)        │
│  → Common log schema; correlation IDs on every line                  │
│  → OpenSearch Dashboards (Kibana) for cross-service search           │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Metrics (numbers)                                                    │
│  → AWS CloudWatch Metrics (custom namespaces per service)            │
│  → CloudWatch Container Insights (EKS pod metrics)                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Traces (request flows)                                               │
│  → OpenTelemetry SDK → AWS X-Ray exporter                            │
│  → Trace IDs linked from log lines (click-through from OpenSearch)   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Errors (exceptions)                                                  │
│  → Sentry (front + back). Auto-grouping, source maps                  │
│  → Sentry event ID linked from log lines                              │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Product analytics                                                    │
│  → PostHog. Feature adoption, funnels, session replay.                │
└──────────────────────────────────────────────────────────────────────┘
```

### 10.1 Centralized Logging — Architecture

The system must answer questions like: *"User saw a 500 at 14:32 IST — show me every log line, every service hop, every Kafka event, and the X-Ray trace for that single request."*

```
                ┌───────────────────────────────────────────────────────┐
                │  EKS Cluster                                          │
                │                                                       │
                │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
                │  │api-      │ │core-     │ │analytics-│ │... all 7 │ │
                │  │gateway   │ │service   │ │service   │ │pods      │ │
                │  │  pod     │ │  pod     │ │  pod     │ │          │ │
                │  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘ │
                │        │ stdout    │ stdout    │ stdout    │ stdout │
                │        ▼            ▼            ▼            ▼      │
                │  ┌─────────────────────────────────────────────────┐ │
                │  │ Fluent Bit DaemonSet (one pod per node)         │ │
                │  │  • Tails /var/log/containers/*.log               │ │
                │  │  • Parses JSON; enriches with k8s metadata       │ │
                │  │  • Redacts secrets via pattern filters           │ │
                │  │  • Batches + ships                               │ │
                │  └────────────────────┬────────────────────────────┘ │
                └───────────────────────┼────────────────────────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                          ▼                           ▼
              ┌────────────────────┐      ┌───────────────────────┐
              │   OpenSearch       │      │   CloudWatch Logs     │
              │   (hot, 14d)       │      │   (warm, 30d)         │
              │                    │      │   Compliance, alarm   │
              │  • Indexed search  │      │   triggers, IAM-tied  │
              │  • Kibana          │      │   queries             │
              │  • Cross-service   │      └──────┬────────────────┘
              │    correlation     │             │
              └──────┬─────────────┘             ▼
                     │                  ┌────────────────────┐
                     │                  │  S3 (cold, 1y)     │
                     │                  │  Subscription      │
                     │                  │  Filter export     │
                     │                  └────────────────────┘
                     │
                     ▼
              Engineer's browser:
              kibana.{BRAIN_DOMAIN}
```

**Why both OpenSearch and CloudWatch:**
- **OpenSearch** is for engineers debugging. Kibana queries, dashboards, alerts on log patterns.
- **CloudWatch Logs** is for AWS-native integrations: CloudWatch Alarms on log patterns, Lambda subscription filters, IAM-controlled audit access. Cheap warm storage.
- **S3** for compliance retention and rare deep history queries.

Fluent Bit ships to both via parallel outputs.

### 10.2 Common Log Schema

Every log line, regardless of language or service, MUST emit this JSON:

```json
{
  "ts": "2026-05-13T14:32:18.421Z",
  "level": "info",
  "msg": "KPI request",
  "service": "api-gateway",
  "version": "v1.42.0",
  "env": "production",
  "region": "ap-south-1",
  "pod": "api-gateway-7f8c9-x2p4q",
  "request_id": "req_01H8X9Y0Z1A2B3C4D5E6F7G8H9",
  "trace_id": "1-5759e988-bd862e3fe1be46a994272793",
  "span_id": "53995c3f42cd8ad8",
  "workspace_id": "ws_01H7XYZ...",
  "user_id": "usr_01H7XYZ...",
  "route": "trpc/store.kpis",
  "duration_ms": 142,
  "status": 200
}
```

**Mandatory fields** (CI lint enforces; loggers emit by default):
- `ts`, `level`, `msg`, `service`, `version`, `env`, `region`, `pod`
- `request_id` — if request-scoped
- `trace_id`, `span_id` — if trace-scoped
- `workspace_id` — if tenant-scoped

**Why mandatory:** in incidents, you need to filter by any of these dimensions. Missing fields → blind spots.

### 10.3 Correlation IDs

A single user action generates many log lines across many services. Correlation IDs stitch them.

```
Browser request
    │  generates request_id = req_xxx
    ▼
api-gateway        ← logs all hops with request_id=req_xxx, trace_id=t_xxx
    │  attaches request_id + trace_id to gRPC metadata
    ▼
core-service       ← logs with request_id=req_xxx, trace_id=t_xxx
    │  attaches to Kafka event envelope
    ▼
Kafka topic
    │
    ▼
analytics-service  ← logs with request_id=req_xxx (from event payload), trace_id=t_xxx
    │  query ClickHouse with `SETTINGS log_comment='req_xxx'`
    ▼
ClickHouse query log ← also tagged with request_id
```

Result: a single OpenSearch query `request_id:"req_xxx"` returns every log line from every service for that single user request.

### 10.4 Propagation Implementation

**HTTP (browser → api-gateway):**
```typescript
// Generated by api-gateway on every incoming request
const requestId = req.headers['x-request-id'] ?? `req_${ulid()}`;
const traceId = req.headers['traceparent'] ?? generateTraceparent();
```

**gRPC metadata (service → service):**
```typescript
// packages/lib-grpc-clients/metadata.ts
md.set('x-request-id', ctx.requestId);
md.set('x-workspace-id', ctx.workspaceId);
md.set('x-user-id', ctx.userId);
md.set('traceparent', ctx.traceparent);
```

```python
# pylibs/brain_grpc/server.py — interceptor extracts and binds to logger context
class CorrelationInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        md = dict(handler_call_details.invocation_metadata)
        bind_contextvars(
            request_id=md.get('x-request-id'),
            workspace_id=md.get('x-workspace-id'),
            user_id=md.get('x-user-id'),
            trace_id=extract_trace_id(md.get('traceparent')),
        )
        return await continuation(handler_call_details)
```

**Kafka events:** request_id + trace_id live in the event envelope (see TECH/06 §4). Consumers extract on receive and bind to logger.

**ClickHouse:** every query from analytics-service includes `SETTINGS log_comment = '<request_id>'`. CH's `system.query_log` becomes searchable by request_id.

### 10.5 Structured Logging Implementation

**TypeScript (pino → stdout):**

```typescript
// packages/lib-logger/src/index.ts
import pino from "pino";
import { AsyncLocalStorage } from "node:async_hooks";

export const requestContext = new AsyncLocalStorage<LogContext>();

export const log = pino({
  formatters: {
    level: (label) => ({ level: label }),
    log: (obj) => {
      const ctx = requestContext.getStore();
      return {
        ...ctx,                              // request_id, trace_id, workspace_id, user_id
        service: process.env.SERVICE_NAME,
        version: process.env.SERVICE_VERSION,
        env: process.env.ENV,
        region: process.env.AWS_REGION,
        pod: process.env.POD_NAME,
        ...obj,
      };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

// Usage:
log.info({ route: "store.kpis", duration_ms: 142 }, "KPI request");
log.error({ err, route: "store.kpis" }, "KPI request failed");
```

**Python (structlog → stdout):**

```python
# pylibs/brain_logger/__init__.py
import structlog
import contextvars

request_id = contextvars.ContextVar("request_id", default=None)
trace_id = contextvars.ContextVar("trace_id", default=None)
workspace_id = contextvars.ContextVar("workspace_id", default=None)

def add_context(_, __, event_dict):
    event_dict["request_id"] = request_id.get()
    event_dict["trace_id"] = trace_id.get()
    event_dict["workspace_id"] = workspace_id.get()
    event_dict["service"] = os.environ["SERVICE_NAME"]
    event_dict["version"] = os.environ["SERVICE_VERSION"]
    event_dict["env"] = os.environ["ENV"]
    event_dict["region"] = os.environ["AWS_REGION"]
    event_dict["pod"] = os.environ["POD_NAME"]
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()

# Usage:
log.info("canonicalize.started", integration="shopify", duration_ms=142)
log.error("canonicalize.failed", error=str(e), exc_info=True)
```

Pods write JSON to stdout; Fluent Bit picks up.

### 10.6 Fluent Bit Configuration

Deployed as DaemonSet on EKS via Helm chart. Each node has one Fluent Bit pod tailing all container logs.

```yaml
# infra/k8s/fluent-bit/values.yaml (Helm values)
config:
  inputs: |
    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            cri
        Refresh_Interval  5
        Mem_Buf_Limit     50MB

  filters: |
    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Merge_Log           On
        Keep_Log            Off
        K8S-Logging.Parser  On
        K8S-Logging.Exclude On

    # Redact patterns: tokens, passwords, credit cards
    [FILTER]
        Name      modify
        Match     kube.*
        Condition Key_value_matches password ^[^$].*
        Set       password "[REDACTED]"

    [FILTER]
        Name    lua
        Match   kube.*
        Script  /fluent-bit/scripts/redact.lua
        Call    redact_sensitive

    # Drop noisy health-check logs
    [FILTER]
        Name      grep
        Match     kube.*
        Exclude   route ^/health$

  outputs: |
    # Hot store: OpenSearch
    [OUTPUT]
        Name             opensearch
        Match            kube.*
        Host             ${OPENSEARCH_ENDPOINT}
        Port             443
        TLS              On
        AWS_Auth         On
        AWS_Region       ${AWS_REGION}
        Index            brain-logs
        Logstash_Format  On
        Logstash_Prefix  brain-${ENV}
        Suppress_Type_Name On
        Replace_Dots     On
        Retry_Limit      5

    # Warm store: CloudWatch
    [OUTPUT]
        Name              cloudwatch_logs
        Match             kube.*
        region            ${AWS_REGION}
        log_group_name    /brain/${ENV}/services
        log_stream_prefix from-fluentbit-
        auto_create_group On

    # Cold archive: S3 (subscription-filter handled separately, not duplicating here)
```

**Resource tuning:** Fluent Bit per node: 100m CPU, 200Mi RAM baseline. At 100k req/min, peak load ~500k log lines/min cluster-wide; per-pod ~10K lines/min — well within capacity.

### 10.7 OpenSearch Cluster

**Phase 0 setup (~$400/month):**
- 3-node cluster, `t3.medium.search` instance type
- 1 master + 2 data, multi-AZ
- 14-day hot retention; daily index rollover (`brain-prod-YYYY.MM.DD`)
- Index State Management (ISM) policy auto-deletes after 14d

**Phase 3 scale (~$1.5K/month):**
- 5-node cluster, `m5.large.search`
- Dedicated master tier (3 small instances)
- 30-day hot retention
- Adds product/customer search indices on same cluster

**Index strategy:**

```json
{
  "brain-prod-2026.05.13": {
    "settings": {
      "number_of_shards": 3,
      "number_of_replicas": 1,
      "refresh_interval": "10s"
    },
    "mappings": {
      "properties": {
        "ts": {"type": "date"},
        "level": {"type": "keyword"},
        "service": {"type": "keyword"},
        "msg": {"type": "text"},
        "request_id": {"type": "keyword"},
        "trace_id": {"type": "keyword"},
        "workspace_id": {"type": "keyword"},
        "user_id": {"type": "keyword"},
        "route": {"type": "keyword"},
        "duration_ms": {"type": "long"},
        "status": {"type": "integer"},
        "err.message": {"type": "text"},
        "err.stack": {"type": "text", "index": false}
      }
    }
  }
}
```

Mapping enforced via index template — new fields rejected unless explicitly added (prevents mapping explosion).

### 10.8 Kibana Dashboards

Three standard dashboards available day-1:

1. **System Health** — error rates per service, p95/p99 latency, throughput, top error messages last 24h
2. **Per-Service Deep Dive** — service-filtered view: top routes, slow queries, recent errors, related Sentry events
3. **Per-Workspace Investigation** — workspace_id-filtered view; used during customer support: every request, every error, every integration sync

### 10.9 Log → Trace Correlation (Click-Through)

A log line in Kibana contains `trace_id`. A Kibana custom field formatter renders it as a clickable link to X-Ray:

```
https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#xray:traces/{trace_id}
```

From X-Ray, click any segment → linked back to OpenSearch with `trace_id` filter pre-applied. Round-trip debugging.

Similarly, `request_id` links to OpenSearch query (`request_id:"req_xxx"`); `sentry_event_id` (when present) links to Sentry.

### 10.10 Common Investigation Queries

Saved Kibana queries; on-call has them bookmarked.

```
# All errors in last 1h
level:error AND env:production

# All log lines for a customer-reported issue (they share request_id from headers)
request_id:"req_01H8X9Y0Z1A2B3C4D5E6F7G8H9"

# Slow analytics queries
service:analytics-service AND duration_ms:>500 AND env:production

# A specific workspace's recent activity (customer support)
workspace_id:"ws_01H7XYZ..." AND ts:[now-1h TO now]

# All Shopify sync failures in last 24h
service:ingestion-service AND msg:"sync.failed" AND payload.integration:shopify AND ts:[now-24h TO now]

# Kafka consumer lag spikes
service:analytics-service AND msg:*consumer_lag* AND value_ms:>30000

# All requests that hit Claude API
service:intelligence-service AND msg:"llm.call.completed"

# Find which workspace caused a global error spike
level:error AND env:production | stats count by workspace_id | sort by count desc
```

### 10.11 Retention Tiers

| Tier | Where | Retention | Use case | Cost/100k workspaces |
|------|-------|-----------|----------|---------------------|
| Hot | OpenSearch | 14d (Phase 0) → 30d (Phase 3) | Active incident debugging, support | $400–1.5K/mo |
| Warm | CloudWatch Logs | 30d | Alarm triggers, AWS-native integrations | $200/mo |
| Cold | S3 (gzipped JSON) | 1 year | Compliance, retrospective analysis | $50/mo |
| Audit | S3 Object Lock | 7 years | `audit_log` table mirror only | $20/mo |

Total at Phase 3 scale: ~$2K/month for logging infrastructure.

### 10.12 PII & Secret Redaction

**At source (preferred):** loggers never emit raw tokens or PII. Field names are filtered:

```typescript
// packages/lib-logger/src/redact.ts
const REDACT_FIELDS = ['password', 'token', 'access_token', 'refresh_token',
                        'authorization', 'cookie', 'api_key', 'credential'];
const REDACT_FIELDS_RE = /^(.*_)?(password|token|secret|api_?key|credential)(_.*)?$/i;

function redactObject(obj: any): any {
  // Recursively walk; replace matching keys with [REDACTED]
}
```

**At Fluent Bit (defense in depth):** Lua script applies pattern-based redaction on transit:

```lua
-- redact.lua
function redact_sensitive(tag, ts, record)
  for k, v in pairs(record) do
    if type(v) == "string" then
      v = v:gsub('(eyJ[%w%-_]+%.[%w%-_]+%.[%w%-_]+)', '[JWT_REDACTED]')
      v = v:gsub('(sk%-[%w]+)', '[ANTHROPIC_KEY_REDACTED]')
      v = v:gsub('(shppa_[%w]+)', '[SHOPIFY_TOKEN_REDACTED]')
      record[k] = v
    end
  end
  return 1, ts, record
end
```

PII fields (customer email, phone, full address) anonymized at logger level:
- Email: `anonymized_email(email)` → `r***@example.com`
- Phone: `last_4(phone)` → `*****1234`
- Address: only city/state/pincode logged, never street

### 10.13 Alerting on Log Patterns

OpenSearch monitors run scheduled queries; trigger PagerDuty/Slack on threshold breach:

```yaml
# infra/opensearch/monitors/error-rate-spike.yaml
monitor:
  name: "Error rate spike per service"
  query: |
    SELECT service, count(*) AS error_count
    FROM brain-prod-*
    WHERE level = 'error' AND ts >= now() - INTERVAL 5 MINUTE
    GROUP BY service
    HAVING error_count > 50
  schedule: "*/1 * * * *"  # every minute
  triggers:
    - severity: "P2"
      channels: ["slack:#brain-incidents", "pagerduty:on-call"]
```

Standard monitors:
- Error rate spike per service (>50/min)
- p99 latency > SLO target (per service per route)
- Auth failures > 100/min (potential attack)
- Specific error patterns (`CrossTenantAccessAttempt`, `RLSPolicyDenied`)

### 10.14 Production Incident Workflow Using Centralized Logs

**Scenario:** customer reports "I clicked Calendar Report at 2pm and got a 500."

1. **Get the request_id:** ask customer for the X-Request-Id from the failed response (Brain shows this in error toasts), or grep their support email for the timestamp.
2. **Open Kibana:** filter `request_id:"req_xxx"` — see every log line across every service for that request.
3. **Find the error:** OpenSearch returns ordered lines from api-gateway → analytics-service → ClickHouse query log.
4. **Click `trace_id` link:** jumps to X-Ray; see latency breakdown, where time was spent.
5. **Identify root cause:** maybe ClickHouse timeout, slow query, downstream unavailable.
6. **Check sister requests:** filter `workspace_id:"ws_xxx" AND status:>=500 AND ts:[now-1h TO now]` — is this an isolated request or a pattern?

End-to-end debugging time: 2–5 minutes vs ~30+ minutes with per-service log groups in CloudWatch alone.

### 10.15 CloudWatch Metric Namespaces

(Still useful — metrics live separately from logs.)

- `Brain/Gateway` — api-gateway
- `Brain/Core` — core-service
- `Brain/Ingestion` — ingestion-service
- `Brain/Analytics` — analytics-service
- `Brain/Intelligence` — intelligence-service
- `Brain/Notifications` — notifications-service
- `Brain/Kafka` — Kafka producer/consumer metrics
- `Brain/Business` — DAU, workspace count, etc.

### 10.16 Dashboards Locations

| Dashboard | Lives In | Source |
|-----------|----------|--------|
| System health (errors, latency, throughput) | CloudWatch | Metrics |
| Log search / cross-service investigation | OpenSearch (Kibana) | Logs |
| Distributed traces | AWS X-Ray Console | Traces |
| Error grouping / regression | Sentry | Errors |
| Product analytics (DAU, funnels) | PostHog | Events |
| ETL pipeline health | CloudWatch | Metrics |
| Per-workspace health (support tool) | OpenSearch + CloudWatch | Both |
| Cost dashboard | CloudWatch + AWS Cost Explorer | Billing |

### 10.17 Never Log

- Passwords, tokens, any encrypted-at-rest field (redaction enforced at source + transit)
- Full PII (use IDs, not emails — anonymize at logger if must)
- Full request bodies for non-error paths
- Verbose debug logs in production (use `info` minimum; `debug` only via feature flag)

### Tracing (X-Ray)

OpenTelemetry SDK in every service; X-Ray exporter for traces. 5% sampling on healthy paths, 100% on errors.

Trace context propagation:
- HTTP: W3C `traceparent` header
- gRPC: `x-traceparent` metadata
- Kafka: traceparent in event envelope

This gives us end-to-end visibility: frontend → api-gateway → analytics-service → ClickHouse → response, all in one trace. Trace IDs surface on every log line so engineers can pivot between logs and traces frictionlessly.

---

## 11. Sentry Setup

```typescript
// apps/web/sentry.client.config.ts
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.05,
  release: process.env.NEXT_PUBLIC_RELEASE,
  beforeSend(event) {
    if (event.user?.email) event.user.email = anonymizeEmail(event.user.email);
    return event;
  },
});
```

```python
# Python services
import sentry_sdk
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=0.05,
    release=GIT_SHA,
    before_send=lambda event, hint: strip_pii(event),
)
```

### Alert Rules

- New issue (first occurrence) of error level → Slack `#brain-errors`
- Issue frequency > 10/min → page on-call
- Performance regression (p95 2x baseline) → Slack notification

---

## 12. SLOs at Scale

### Phase 1 SLOs

| Objective | Target |
|-----------|--------|
| API availability | 99.5% |
| API p95 latency | <500ms |
| Dashboard TTI | <3s |
| Daily digest delivery | 99% by 06:30 IST |
| ETL freshness (Shopify orders) | <30 min lag p95 |

### Phase 3 SLOs

| Objective | Target |
|-----------|--------|
| API availability | 99.9% |
| API p95 latency | <300ms |
| API p99 latency | <1.5s |
| Dashboard TTI | <2s |
| ETL freshness | <15 min lag p95 |
| Forecast accuracy (30-day MAPE) | <25% |

### Phase 4 SLOs at 100k req/min

| Objective | Target |
|-----------|--------|
| API availability | 99.95% |
| API p95 latency | <300ms (steady state) |
| API p99 latency | <1.5s |
| API p99.9 latency | <5s (under burst) |
| ETL freshness | <5 min lag p95 |
| Forecast accuracy | <15% MAPE |

SLO violations trigger Sev3 review; sustained violations trigger Sev2 incident.

---

## 13. Incident Response

### Severity Levels

| Sev | Definition | Response Time |
|-----|-----------|---------------|
| **SEV1** | Total outage / data integrity / security breach | <15 min ack |
| **SEV2** | Major feature broken for many users | <1 hour ack |
| **SEV3** | Single workspace impact / slow performance | <4 hours ack |
| **SEV4** | Cosmetic / non-urgent | <1 business day |

### On-Call Rotation

- **Phase 1:** E1 (tech lead) always on call
- **Phase 2:** rotation E1/E3/E4 (E2 frontend-only doesn't page off-hours)
- **Phase 3+:** dedicated on-call rotation; weekly handoffs Mon 10:00 IST

**Paging:** PagerDuty (free tier: 5 users → upgrade Phase 3).

### Workflow

1. **Detect** — Sentry alert, CloudWatch alarm, customer report
2. **Triage** — assign severity in #brain-incidents Slack
3. **Mitigate** — restore service first; root-cause after
4. **Document** — every Sev1/Sev2 gets a postmortem within 5 business days
5. **Communicate** — Sev1/Sev2 affecting customers triggers status page + email

### Status Page

Phase 2+: `status.{BRAIN_DOMAIN}`. Statuspage.io or Better Stack. Auto-updates via CloudWatch alarms (Phase 3).

### Postmortems

Blameless. Stored in `docs/postmortems/<YYYY-MM-DD>-<title>.md`. Format:
- Timeline (UTC)
- Root cause
- Mitigation
- What worked / what didn't
- Action items (owner + deadline)

---

## 14. Backup & DR

### Backup Strategy

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| Postgres (Supabase) | Daily snapshot + PITR | 30d snapshots, 7d PITR | Supabase-managed |
| ClickHouse | Daily snapshot | 7 days | ClickHouse Cloud automated |
| Kafka (MSK) | Tiered storage to S3 | Forever (raw archive) | MSK feature |
| S3 buckets | Versioning + replication | 30d versions | Cross-region replication (Phase 4) |
| Configuration | Git history | Forever | All in `infra/` repo |

### Restore Procedure

1. **Postgres:** Supabase snapshot or PITR restore
2. **ClickHouse:** CH Cloud snapshot restore
3. **Kafka:** rewind consumer offsets to replay from S3 tier
4. **Replay any gap** in ClickHouse from canonical Kafka topics

### RTO / RPO

- **Phase 1-2:** RTO 4h, RPO 1h
- **Phase 4 with multi-region:** RTO 2h, RPO 5 min

### DR Drills

- **Monthly automated:** restore latest snapshot to staging; verify schema + sample query passes; alert if fail
- **Quarterly full drill:** restore production-equivalent to alternate region; run smoke tests; switch traffic briefly

---

## 15. Production Access Control

### Who Can Access What

| Resource | Engineers with Access |
|----------|----------------------|
| Production DB read (read-only role) | E1, E3 (audited) |
| Production DB write (break-glass) | E1 only |
| Production env vars / Secrets Manager | E1 only |
| Production deploys (via PR + CI) | All |
| Customer impersonation | E1, E3 (audited, requires reason) |
| Sentry / CloudWatch | All |
| Anthropic / SES / Gupshup admin | E1, E4 |
| EKS kubectl (read) | All |
| EKS kubectl (write) | E1 only (use ArgoCD for app deploys) |

### Break-Glass

For SEV1 needing direct DB write:
1. Announce in `#brain-ops`: "Break-glass DB write for SEV1 #incident-id"
2. Use `app_admin` role with verbose audit logging
3. All queries logged to `audit_log` with incident link
4. Post-incident review of all break-glass actions

Never break-glass for non-emergencies. Schema changes go through migrations.

### Quarterly Access Reviews

E1 audits IAM roles, service accounts, and DB roles quarterly. Inactive roles disabled.

---

## 16. Security Quick-Reference Checklist

**Every PR:**
- [ ] Workspace data access uses `workspaceProcedure` or service interceptor
- [ ] No string-interpolated SQL with user input
- [ ] No `dangerouslySetInnerHTML` for user content
- [ ] No logged tokens, passwords, or raw bodies
- [ ] No bypass of RLS or query gateway (if yes, audited?)

**Every new table:**
- [ ] Has `workspace_id` column + index
- [ ] (Postgres) Has RLS policy enabled
- [ ] (ClickHouse) `workspace_id` in primary key ordering
- [ ] Verified test workspace cannot read other workspaces

**Every new integration:**
- [ ] Tokens KMS envelope-encrypted
- [ ] Token refresh logic implemented
- [ ] Audit log entry on connect/disconnect
- [ ] Sync errors surface to operator

**Every release:**
- [ ] Migrations tested in staging
- [ ] Dependency updates triaged
- [ ] Sentry shows no new unhandled errors in canary
- [ ] Performance dashboards show no regressions

**Every quarter:**
- [ ] IAM roles reviewed
- [ ] Secrets rotated where due
- [ ] DR drill completed
- [ ] Postmortems reviewed for recurring patterns

---

## 17. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Service mesh (Istio vs App Mesh)? | E1 | Phase 2. App Mesh if AWS-native mandate hardens; Istio for richer features. |
| AWS WAF managed rules tier? | E1 | Bot Control + IP Reputation. Phase 1. |
| Audit log to immutable S3 (Object Lock)? | E1 | Phase 3 for compliance. |
| Per-workspace data residency UI? | E1 | Phase 4. Owner can select region at workspace creation. |
| SOC 2 vendor (Vanta vs Drata vs Sprinto)? | E1 | Sprinto (India-friendly pricing); revisit Phase 4. |
| MFA mandatory or optional? | E1 | Optional Phase 3; mandatory for owners Phase 4. |
| Self-hosted Sentry for data residency? | E1 | Defer. SaaS Sentry adequate. Re-evaluate Phase 5. |
| Centralized SBOM for supply chain? | E1 | Phase 3. Syft + Grype, results to S3. |
