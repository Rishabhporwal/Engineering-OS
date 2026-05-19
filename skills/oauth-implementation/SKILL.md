---
name: oauth-implementation
description: OAuth 2.0 flows for Brain's vendor connectors — Shopify partner OAuth, Meta Marketing API, Google Ads (long-lived refresh tokens + scope upgrades), Shiprocket, Klaviyo. Use when adding a new connector to ingestion-service, when a vendor's OAuth scope changes, when refresh tokens start failing, or when storing/rotating per-brand vendor credentials.
---

# OAuth Implementation

Brain's end-user auth is **Supabase Auth** (see `session-management`). This skill is the other side — Brain acting as the **OAuth Client** to vendor APIs (Shopify, Meta, Google, Shiprocket, Klaviyo). Every Maya-owned connector starts with OAuth, so getting this right is the foundation of the ingestion pipeline.

## Why this matters for Brain

- **Every vendor has different OAuth quirks.** Shopify wants per-shop installs with HMAC-signed callbacks. Meta requires the System User flow for long-running tokens. Google Ads needs a developer token AND OAuth scope upgrades for each manager-account hop. Shiprocket has rotating API keys (not OAuth proper). Klaviyo uses Private API keys, NOT OAuth (Phase 4 may add OAuth).
- **Token storage is a compliance + security surface.** Per-brand vendor tokens are encrypted at rest with AWS KMS envelope encryption, stored in `integrations.encrypted_credentials` (Postgres bytea), and decrypted only at the moment of an API call. Tokens NEVER live in logs, env vars, or memory beyond the active request.
- **Token failure breaks ingestion.** A Meta refresh-token expiry that goes unnoticed for 24h = a brand's MER chart silently freezes at the wrong number. Refresh-token monitoring is part of `observability`.

## OAuth flows in Brain

| Flow | Used by | Note |
|---|---|---|
| **Authorization Code** | Shopify (partner install), Meta (System User), Google Ads | Standard server-side flow; Brain holds the client_secret |
| **Authorization Code + PKCE** | n/a (Brain is never a "public client" — all OAuth happens server-side in ingestion-service) | |
| **Client Credentials** | n/a (vendors don't expose this) | |
| **Refresh Token** | All of the above | Long-lived; rotate per vendor's policy |
| **API Key** (NOT OAuth) | Shiprocket, Klaviyo current | Same encrypted storage; different rotation |

## Brain canonical pattern (Authorization Code, server-side)

```typescript
// ingestion-service (Python) — Shopify connector OAuth callback
import secrets, hmac, hashlib, urllib.parse, httpx
from cryptography.fernet import Fernet
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# Step 1: Install — redirect the brand admin to Shopify's authorize URL
@app.get("/oauth/shopify/install")
async def install(shop: str, workspace_id: str):
    # State carries workspace_id + nonce, signed so we can verify on callback
    state = sign_state({"workspace_id": workspace_id, "nonce": secrets.token_hex(16)})
    scopes = "read_orders,read_products,read_customers"
    params = urllib.parse.urlencode({
        "client_id":    settings.SHOPIFY_API_KEY,
        "scope":        scopes,
        "redirect_uri": f"{settings.PUBLIC_API_URL}/oauth/shopify/callback",
        "state":        state,
    })
    return RedirectResponse(f"https://{shop}/admin/oauth/authorize?{params}")

# Step 2: Callback — verify HMAC + state, exchange code for token
@app.get("/oauth/shopify/callback")
async def callback(request: Request):
    params = dict(request.query_params)
    # Verify Shopify's HMAC signature first — defense in depth
    if not verify_shopify_hmac(params, settings.SHOPIFY_API_SECRET):
        raise HTTPException(401, "HMAC verification failed")
    state = verify_state(params["state"])  # raises on tampering
    workspace_id = state["workspace_id"]

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://{params['shop']}/admin/oauth/access_token",
            json={
                "client_id":     settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code":          params["code"],
            },
        )
    r.raise_for_status()
    tokens = r.json()

    await integrations_repo.upsert(
        workspace_id=workspace_id,
        source="shopify",
        shop_domain=params["shop"],
        encrypted_credentials=kms.encrypt(tokens),    # KMS envelope
        scopes=tokens.get("scope"),
        installed_at=datetime.utcnow(),
    )
    return RedirectResponse(f"{settings.WEB_URL}/integrations/shopify/connected")
```

## Token storage (the Brain rule)

```sql
CREATE TABLE integrations (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id         UUID NOT NULL,
  source               TEXT NOT NULL,                 -- shopify | meta | google | shiprocket | klaviyo
  account_identifier   TEXT NOT NULL,                 -- shop domain, ad account id, etc.
  encrypted_credentials BYTEA NOT NULL,               -- KMS-encrypted JSON
  scopes               TEXT[],
  installed_at         TIMESTAMPTZ NOT NULL,
  refreshed_at         TIMESTAMPTZ,
  expires_at           TIMESTAMPTZ,                   -- NULL for non-expiring tokens
  status               TEXT NOT NULL DEFAULT 'active', -- active | revoked | expired | error
  last_error           TEXT,
  UNIQUE (workspace_id, source, account_identifier)
);

ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_integrations ON integrations
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

**Brain rules:**
- `encrypted_credentials` is **BYTEA**, KMS-envelope-encrypted. Decryption key access is per-task IAM role (the ingestion-service role only).
- **Tokens never appear in logs.** `logging-best-practices` `redact` config covers `*.access_token`, `*.refresh_token`, `*.api_key`.
- **NEVER expose `client_secret` to the browser or mobile** — all OAuth happens in `ingestion-service`.
- Connector dispatcher fetches credentials at call time, decrypts in-memory, never stores in-process beyond the request.

## Refresh token handling

```python
# Brain pattern: refresh on 401, save the new token atomically
async def get_valid_credentials(workspace_id: str, source: str) -> dict:
    record = await integrations_repo.get(workspace_id, source)
    creds = kms.decrypt(record.encrypted_credentials)

    if record.expires_at and record.expires_at < datetime.utcnow() + timedelta(minutes=10):
        creds = await refresh_token(source, creds)
        await integrations_repo.update_credentials(
            workspace_id, source,
            encrypted_credentials=kms.encrypt(creds),
            expires_at=datetime.utcnow() + timedelta(seconds=creds["expires_in"]),
            refreshed_at=datetime.utcnow(),
        )

    return creds

async def refresh_token(source: str, creds: dict) -> dict:
    refresh_url = REFRESH_URLS[source]
    async with httpx.AsyncClient() as client:
        r = await client.post(refresh_url, data={
            "grant_type":    "refresh_token",
            "refresh_token": creds["refresh_token"],
            "client_id":     settings.client_id_for(source),
            "client_secret": settings.client_secret_for(source),
        })
    r.raise_for_status()
    new = r.json()
    # Vendors that rotate refresh tokens (Google Ads, Meta) — preserve new refresh_token if present
    return {**creds, **new}
```

**Refresh failures must page Maya + alert on the workspace dashboard.** A silently-broken integration means the data simply stops flowing — operators don't notice until they check, by which point CM2 is stale for a week.

## Per-vendor specifics (Brain)

| Vendor | Flow | Long-lived token? | Quirk |
|---|---|---|---|
| **Shopify** | Auth Code + per-shop HMAC | Permanent access tokens (no expiry) | Per-shop install; scopes must be re-requested if you change them |
| **Meta Marketing** | Auth Code + System User | 60d access token; System User tokens last ~indefinitely with refresh | Permissions review required for `ads_read`; use System User for long-running |
| **Google Ads** | Auth Code | Refresh token never expires (unless revoked); access token 1h | Developer token approval is a W0 blocker; scope upgrades require user re-consent |
| **Shiprocket** | API key (not OAuth) | API key + secret; manually rotated | Rate-limit is per-key; respect 60 req/min on tracking endpoints |
| **Klaviyo** | Private API key (Phase 4 may add OAuth) | Permanent; rotate quarterly | Per-list scoping not granular — key is account-wide |

## Security requirements (Shreya VETO territory)

- **HTTPS everywhere** — no HTTP redirect URIs allowed
- **`state` parameter validation** — signed + nonce + workspace_id; reject mismatches with 401
- **HMAC verification first** (Shopify, Meta webhook handlers) — defense in depth before parsing
- **PKCE not applicable** (we're server-side; Brain holds the secret)
- **Strict redirect_uri allow-list** in each vendor's app config; never wildcard
- **Token rotation alert** — surface in observability dashboard when `expires_at - now() < 24h`
- **Per-task IAM for KMS** — ingestion-service role can decrypt; others cannot
- **No tokens in logs** — `redact` config + reviewer check in `/review`

## Never Do

- Store tokens in localStorage / sessionStorage / AsyncStorage
- Expose `client_secret` to the browser or mobile
- Use implicit flow (deprecated by OAuth 2.0 BCP)
- Skip `state` validation
- Use long-lived access tokens where refresh is available
- Log credentials, even at DEBUG
- Cache decrypted tokens beyond the active request

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Connector OAuth flows | **Maya** | canon/BRAIN_TECHNICAL.md (OAuth + per-source auth) |
| Token storage (Postgres + KMS) | **Maya** + **Vikram** | canon/BRAIN_TECHNICAL.md |
| Per-task IAM (KMS decrypt) | **Jatin** | canon/BRAIN_TECHNICAL.md (secrets) |
| Token failure alerting | **Maya** + **Jatin** | `observability` |
| End-user auth (NOT this skill) | **Vikram** + **Shreya** | `session-management` |

Related Brain skills: `session-management` (Supabase end-user auth — distinct), `integration-connectors` (per-vendor specifics), `security-baseline` (broader posture), `defense-in-depth-validation` (HMAC + state verification), `logging-best-practices` (redaction).
