---
name: oauth-implementation
description: OAuth 2.0 for Brain's vendor connectors (Shopify/Meta/Google Ads/Shiprocket/Klaviyo) — server-side auth-code, KMS+Secrets-Manager token storage, refresh.
---

# OAuth Implementation

Brain's end-user auth is **Supabase Auth** (`auth-and-access`). This skill is the other side — Brain acting as the **OAuth Client** to vendor APIs. Every Maya-owned connector starts with OAuth, so this is the foundation of the ingestion pipeline.

- **Every vendor has different quirks.** Shopify wants per-shop installs with HMAC-signed callbacks. Meta requires the System User flow for long-running tokens. Google Ads needs a developer token AND scope upgrades per manager-account hop. Shiprocket uses rotating API keys (not OAuth). Klaviyo uses Private API keys (Phase 4 may add OAuth).
- **Token storage is a compliance + security surface.** Per-brand vendor tokens are KMS-envelope-encrypted and stored in **AWS Secrets Manager** — the `core.integrations` row holds only an opaque `credential_secret_arn`, never the ciphertext. Reads go through a core-service decryption wrapper, decrypting only at the moment of an API call. Plaintext NEVER in logs, env vars, the DB row, or memory beyond the active request.
- **Token failure breaks ingestion.** A Meta refresh-token expiry unnoticed for 24h = a brand's MER chart silently freezes at the wrong number. Monitoring is part of `observability`.

## OAuth flows in Brain
| Flow | Used by | Note |
|---|---|---|
| Authorization Code | Shopify (partner install), Meta (System User), Google Ads | Standard server-side; Brain holds the client_secret |
| Auth Code + PKCE | n/a (Brain is never a public client) | |
| Client Credentials | n/a (vendors don't expose) | |
| Refresh Token | all of the above | Long-lived; rotate per vendor policy |
| API Key (NOT OAuth) | Shiprocket, Klaviyo current | Same encrypted storage; different rotation |

## Canonical pattern (Authorization Code, server-side)
```python
# ingestion-service — Shopify connector OAuth callback
@app.get("/oauth/shopify/install")
async def install(shop: str, workspace_id: str):
    state = sign_state({"workspace_id": workspace_id, "nonce": secrets.token_hex(16)})  # signed, verified on callback
    params = urllib.parse.urlencode({
        "client_id": settings.SHOPIFY_API_KEY, "scope": "read_orders,read_products,read_customers",
        "redirect_uri": f"{settings.PUBLIC_API_URL}/oauth/shopify/callback", "state": state })
    return RedirectResponse(f"https://{shop}/admin/oauth/authorize?{params}")

@app.get("/oauth/shopify/callback")
async def callback(request: Request):
    params = dict(request.query_params)
    if not verify_shopify_hmac(params, settings.SHOPIFY_API_SECRET):   # HMAC first — defense in depth
        raise HTTPException(401, "HMAC verification failed")
    state = verify_state(params["state"])                              # raises on tampering
    workspace_id = state["workspace_id"]
    async with httpx.AsyncClient() as client:
        r = await client.post(f"https://{params['shop']}/admin/oauth/access_token",
            json={"client_id": settings.SHOPIFY_API_KEY, "client_secret": settings.SHOPIFY_API_SECRET,
                  "code": params["code"]})
    r.raise_for_status(); tokens = r.json()
    secret_arn = await secrets.put_credential(workspace_id, "shopify", tokens)  # KMS→Secrets Manager; store only ARN
    await integrations_repo.upsert(workspace_id=workspace_id, integration_type="shopify",
        external_account_id=params["shop"], credential_secret_arn=secret_arn,
        config={"scopes": tokens.get("scope")}, status="connected")
    return RedirectResponse(f"{settings.WEB_URL}/integrations/shopify/connected")
```

## Token storage (the Brain rule)
```sql
CREATE TABLE integrations (                         -- core.integrations (canon TECH/01)
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id UUID NOT NULL,
  integration_type TEXT NOT NULL,                   -- shopify|meta|google_ads|shiprocket|klaviyo
  external_account_id TEXT,
  credential_secret_arn TEXT NOT NULL,              -- opaque ref; KMS-enveloped ciphertext lives in Secrets Manager
  config JSONB NOT NULL DEFAULT '{}', watermarks JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'connected',         -- connected|revoked|expired|error
  last_sync_error TEXT, UNIQUE (workspace_id, integration_type, external_account_id));
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_integrations ON integrations
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```
- DB row stores **only `credential_secret_arn`** — never ciphertext. KMS-enveloped token lives in Secrets Manager; per-workspace DEK, KEK never exported. Decrypt is per-task IAM (ingestion/core-service wrapper only).
- **Tokens never in logs** — `observability` `redact` covers `*.access_token`, `*.refresh_token`, `*.api_key`.
- **NEVER expose `client_secret`** to browser/mobile — all OAuth in `ingestion-service`.
- Connector dispatcher fetches creds at call time, decrypts in-memory, never stores in-process beyond the request.

## Refresh token handling
```python
async def get_valid_credentials(workspace_id: str, source: str) -> dict:
    record = await integrations_repo.get(workspace_id, source)
    creds = await secrets.get_credential(record.credential_secret_arn)   # fetch by ARN, KMS-decrypt in-memory
    expires_at = creds.get("expires_at")
    if expires_at and expires_at < datetime.utcnow() + timedelta(minutes=10):
        creds = await refresh_token(source, creds)
        await secrets.put_credential(workspace_id, source, creds, arn=record.credential_secret_arn)  # re-encrypt, same ARN
    return creds

async def refresh_token(source: str, creds: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(REFRESH_URLS[source], data={"grant_type": "refresh_token",
            "refresh_token": creds["refresh_token"], "client_id": settings.client_id_for(source),
            "client_secret": settings.client_secret_for(source)})
    r.raise_for_status()
    return {**creds, **r.json()}   # Google/Meta rotate refresh tokens — preserve new refresh_token if present
```
**Refresh failures must page Maya + alert on the workspace dashboard.** A silently-broken integration means data stops flowing — CM2 is stale for a week before anyone notices.

## Per-vendor specifics
| Vendor | Flow | Long-lived? | Quirk |
|---|---|---|---|
| Shopify | Auth Code + per-shop HMAC | permanent (no expiry) | per-shop install; re-request scopes if changed |
| Meta Marketing | Auth Code + System User | 60d access; System User ~indefinite w/ refresh | `ads_read` permissions review; use System User for long-running |
| Google Ads | Auth Code | refresh never expires unless revoked; access 1h | developer-token approval is a W0 blocker; scope upgrades need re-consent |
| Shiprocket | API key (not OAuth) | manual rotation | rate-limit per-key; 60 req/min on tracking |
| Klaviyo | Private API key (Phase 4 may add OAuth) | permanent; rotate quarterly | account-wide key, not per-list |

## Security requirements (Shreya VETO)
HTTPS only (no HTTP redirect URIs) · `state` validation (signed + nonce + workspace_id; reject mismatch 401) · HMAC verification first (Shopify/Meta) before parsing · PKCE n/a (server-side) · strict redirect_uri allow-list, never wildcard · token-rotation alert when `expires_at - now() < 24h` · per-task IAM for KMS decrypt · no tokens in logs (`redact` + `/review` check).

## Never Do
Store tokens in localStorage/sessionStorage/AsyncStorage · expose `client_secret` to browser/mobile · use implicit flow (deprecated) · skip `state` validation · use long-lived access tokens where refresh is available · log credentials even at DEBUG · cache decrypted tokens beyond the active request.

## Brain wiring
| Concern | Owner |
|---|---|
| Connector OAuth flows | Maya |
| Token storage (Postgres + KMS) | Maya + Vikram |
| Per-task IAM (KMS decrypt) | Jatin |
| Token failure alerting | Maya + Jatin → `observability` |
| End-user auth (NOT this skill) | Vikram + Shreya → `auth-and-access` |

Related: `auth-and-access` (Supabase end-user auth + RBAC — distinct) · `integration-connectors` (per-vendor specifics) · `security-baseline` (broader posture + secrets handling) · `observability` (redaction).
