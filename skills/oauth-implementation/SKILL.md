---
name: oauth-implementation
description: Reference OAuth 2.0 for outbound vendor/connector integrations — server-side auth-code, KMS+secret-manager token storage, refresh, per-vendor quirks.
---

# OAuth Implementation — Reference Implementation

> **Reference implementation.** This skill documents one concrete binding of a seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (not the vendor) are what transfer.

End-user auth is a separate concern (`auth-and-access`). This skill is the other side — the product acting as the **OAuth Client** to third-party vendor APIs. Connectors typically start with OAuth, so this is the foundation of an ingestion pipeline.

- **Every vendor has different quirks.** One vendor wants per-account installs with HMAC-signed callbacks; another requires a "system user" flow for long-running tokens; another needs a developer token AND scope upgrades per account hop; some use rotating API keys or private keys instead of OAuth. Treat each as an example of a class, not a fixed list.
- **Token storage is a compliance + security surface.** Per-tenant vendor tokens are KMS-envelope-encrypted and stored in a **managed secret store** — the `integrations` row holds only an opaque `credential_secret_arn` (or equivalent reference), never the ciphertext. Reads go through a decryption wrapper, decrypting only at the moment of an API call. Plaintext NEVER in logs, env vars, the DB row, or memory beyond the active request.
- **Token failure breaks ingestion.** A refresh-token expiry unnoticed for 24h means a tenant's data silently freezes at the wrong number. Monitoring is part of `observability`.

## OAuth flows (reference)
| Flow | Used by | Note |
|---|---|---|
| Authorization Code | most server-side vendor installs | Standard server-side; the product holds the client_secret |
| Auth Code + PKCE | n/a when the product is never a public client | |
| Client Credentials | when a vendor exposes it | |
| Refresh Token | all of the above | Long-lived; rotate per vendor policy |
| API Key (NOT OAuth) | vendors without OAuth | Same encrypted storage; different rotation |

## Canonical pattern (Authorization Code, server-side)
```python
# ingestion-service — generic vendor OAuth callback
@app.get("/oauth/{vendor}/install")
async def install(vendor: str, account: str, tenant_id: str):
    state = sign_state({"tenant_id": tenant_id, "nonce": secrets.token_hex(16)})  # signed, verified on callback
    params = urllib.parse.urlencode({
        "client_id": settings.client_id_for(vendor), "scope": settings.scopes_for(vendor),
        "redirect_uri": f"{settings.PUBLIC_API_URL}/oauth/{vendor}/callback", "state": state })
    return RedirectResponse(f"{settings.authorize_url_for(vendor, account)}?{params}")

@app.get("/oauth/{vendor}/callback")
async def callback(vendor: str, request: Request):
    params = dict(request.query_params)
    if not verify_vendor_hmac(vendor, params, settings.client_secret_for(vendor)):  # HMAC first — defense in depth
        raise HTTPException(401, "HMAC verification failed")
    state = verify_state(params["state"])                              # raises on tampering
    tenant_id = state["tenant_id"]
    async with httpx.AsyncClient() as client:
        r = await client.post(settings.token_url_for(vendor, params),
            json={"client_id": settings.client_id_for(vendor), "client_secret": settings.client_secret_for(vendor),
                  "code": params["code"]})
    r.raise_for_status(); tokens = r.json()
    secret_arn = await secrets.put_credential(tenant_id, vendor, tokens)  # KMS→secret store; store only the reference
    await integrations_repo.upsert(tenant_id=tenant_id, integration_type=vendor,
        external_account_id=params.get("account"), credential_secret_arn=secret_arn,
        config={"scopes": tokens.get("scope")}, status="connected")
    return RedirectResponse(f"{settings.WEB_URL}/integrations/{vendor}/connected")
```

## Token storage (the rule)
```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id UUID NOT NULL,
  integration_type TEXT NOT NULL,                   -- one row per (tenant, vendor, account)
  external_account_id TEXT,
  credential_secret_arn TEXT NOT NULL,              -- opaque ref; KMS-enveloped ciphertext lives in the secret store
  config JSONB NOT NULL DEFAULT '{}', watermarks JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'connected',         -- connected|revoked|expired|error
  last_sync_error TEXT, UNIQUE (tenant_id, integration_type, external_account_id));
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_integrations ON integrations
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```
- DB row stores **only `credential_secret_arn`** — never ciphertext. KMS-enveloped token lives in the secret store; per-tenant DEK, KEK never exported. Decrypt is per-task IAM (the ingestion/core decryption wrapper only).
- **Tokens never in logs** — `observability` `redact` covers `*.access_token`, `*.refresh_token`, `*.api_key`.
- **NEVER expose `client_secret`** to browser/mobile — all OAuth lives in the server-side ingestion path.
- Connector dispatcher fetches creds at call time, decrypts in-memory, never stores in-process beyond the request.

## Refresh token handling
```python
async def get_valid_credentials(tenant_id: str, source: str) -> dict:
    record = await integrations_repo.get(tenant_id, source)
    creds = await secrets.get_credential(record.credential_secret_arn)   # fetch by ref, KMS-decrypt in-memory
    expires_at = creds.get("expires_at")
    if expires_at and expires_at < datetime.utcnow() + timedelta(minutes=10):
        creds = await refresh_token(source, creds)
        await secrets.put_credential(tenant_id, source, creds, arn=record.credential_secret_arn)  # re-encrypt, same ref
    return creds

async def refresh_token(source: str, creds: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(REFRESH_URLS[source], data={"grant_type": "refresh_token",
            "refresh_token": creds["refresh_token"], "client_id": settings.client_id_for(source),
            "client_secret": settings.client_secret_for(source)})
    r.raise_for_status()
    return {**creds, **r.json()}   # some vendors rotate refresh tokens — preserve the new refresh_token if present
```
**Refresh failures must page the on-call engineer + alert on the tenant dashboard.** A silently-broken integration means data stops flowing — a metric is stale for a week before anyone notices.

## Per-vendor specifics (examples of the classes you'll hit)
| Vendor class | Flow | Long-lived? | Quirk |
|---|---|---|---|
| Per-account install + HMAC callbacks | Auth Code + per-account HMAC | often permanent | per-account install; re-request scopes if changed |
| "System user" long-running token | Auth Code + system user | short access; system user ~indefinite w/ refresh | use the system-user grant for long-running access |
| Ads/marketing API | Auth Code | refresh never expires unless revoked; access ~1h | developer-token approval may be a launch blocker; scope upgrades need re-consent |
| Rotating API key (not OAuth) | API key | manual rotation | rate-limit per key |
| Private API key (may add OAuth later) | API key | permanent; rotate periodically | account-wide key, not per-resource |

## Security requirements (Security VETO)
HTTPS only (no HTTP redirect URIs) · `state` validation (signed + nonce + tenant_id; reject mismatch 401) · HMAC verification first (where the vendor signs callbacks) before parsing · PKCE n/a (server-side) · strict redirect_uri allow-list, never wildcard · token-rotation alert when `expires_at - now() < 24h` · per-task IAM for KMS decrypt · no tokens in logs (`redact` + `/review` check).

## Never Do
Store tokens in localStorage/sessionStorage/AsyncStorage · expose `client_secret` to browser/mobile · use implicit flow (deprecated) · skip `state` validation · use long-lived access tokens where refresh is available · log credentials even at DEBUG · cache decrypted tokens beyond the active request.

## Wiring
| Concern | Owner |
|---|---|
| Connector OAuth flows | AI/ML Engineer |
| Token storage (DB + KMS) | AI/ML Engineer + Backend Engineer |
| Per-task IAM (KMS decrypt) | Platform/SRE |
| Token failure alerting | AI/ML Engineer + Platform/SRE → `observability` |
| End-user auth (NOT this skill) | Backend Engineer + Security Reviewer → `auth-and-access` |

Related: `auth-and-access` (end-user auth + RBAC — distinct) · `integration-connectors` (per-vendor specifics) · `security-baseline` (broader posture + secrets handling) · `observability` (redaction).
