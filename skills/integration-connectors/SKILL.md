---
name: integration-connectors
description: Brain's connector patterns for Shopify, Meta Ads, Google Ads, Shiprocket, Klaviyo, TikTok, Snap. OAuth + idempotent UPSERT + Kafka producer to integrations.*.v1 + raw archive in ClickHouse + S3 backup + cursor persistence. Auto-load whenever wiring a new connector, modifying OAuth flow, handling rate limits, designing backfill, or debugging ingestion lag. Same code path for live + backfill (bounded vs unbounded window).
---

# Integration Connectors — Brain's Ingestion Patterns

The Maya-owned layer. Source → canonical events → Kafka → downstream.

**Canonical doc:** `canon/TECH/02_integrations.md` (+ `canon/technical-requirements.md` §11). This skill is operational.

## Universal connector flow

```
EventBridge cron (per workspace × integration)
   ▼
Acquire OAuth token from core-service (KMS-decrypted; refresh if expired)
   ▼
Read source (webhook payload OR API pull with cursor)
   ▼
Idempotency check: Redis SETNX with 24h TTL
   key: f"idempotency:{source}:{workspace_id}:{event_id}"
   ▼ [first time]
Canonical transform: source row → canonical event (per protos/events/<topic>.avsc)
   ▼
Fan out to all sinks (idempotent UPSERT everywhere):
   • S3 raw archive (brain-raw-archive)
   • ClickHouse raw_<source>_<entity>_local
   • Kafka integrations.<entity>.v1 (Avro via Glue Schema Registry)
   • Postgres 90-day hot mirror (Phase 0–1; fast joins + webhook reconciliation)
   ▼
Persist cursor/watermark to Postgres integrations.watermarks table
```

**Same `Connector` interface for every source** (`authenticate / refresh_token / sync(window) / receive_webhook / canonicalize / health_check`); **backfill == live — only the window changes** (bounded vs unbounded). The three-to-four sinks above are written idempotently so a replay never doubles a row.

## OAuth per source

| Source | OAuth flow | Scope minimum |
|---|---|---|
| Shopify | App OAuth via partner app; per-workspace install | `read_orders, read_products, read_customers, read_inventory` |
| Meta Ads | Marketing API OAuth | `ads_read, ads_management` |
| Google Ads | OAuth + Developer Token (gating; apply Week 0) | `https://www.googleapis.com/auth/adwords` |
| Shiprocket | Token-based (email + password → JWT; refresh in-band) | n/a |
| Klaviyo | OAuth or API key | `events:read, profiles:read, campaigns:read` |
| TikTok Ads | OAuth | `report.read, audience.read, ad.read` — **region-gated: UAE/GCC only (TikTok is banned in India; never enable for `region=in`)** |
| Snapchat Ads | OAuth | `ads.basic, audience.read` — GCC-first (AICMO-Snap, Phase 4) |

**Tokens written to `core-service.integrations_oauth_tokens` (Postgres), envelope-encrypted with AWS KMS.** The ingestion-service never persists plaintext tokens; it asks core-service per poll, refreshes if expired, discards from memory.

## Idempotency keys per source

| Source | Idempotency key |
|---|---|
| Shopify orders | `(workspace_id, order.id)` |
| Shopify customers | `(workspace_id, customer.id, customer.updated_at)` |
| Meta insights | `(workspace_id, ad_account_id, campaign_id, date)` |
| Google insights | `(workspace_id, customer_id, campaign_id, date)` |
| Shiprocket shipments | `(workspace_id, awb_code, status)` |
| Klaviyo events | `(workspace_id, event_id)` |

Redis SETNX with 24h TTL is the safety net. ClickHouse `ReplicatedReplacingMergeTree(ingested_at)` handles late updates.

## Kafka producer pattern

```python
from aiokafka import AIOKafkaProducer
from python_schema_registry_client.serializers import AvroSerializer

async def publish_canonical_event(topic: str, workspace_id: str, event_id: str, payload: dict):
    avro_value = await avro_serializer.encode_record(topic=topic, record=payload)
    await producer.send_and_wait(
        topic=f"integrations.{entity}.v1",
        key=workspace_id.encode(),   # partition by workspace
        value=avro_value,
        headers=[
            ("event_id", event_id.encode()),
            ("schema_version", b"1"),
            ("trace_id", get_trace_id().encode()),
        ],
    )
```

Compression: zstd. Retention: infinite (MSK tiered storage to S3).

## Backfill discipline (canon/technical-requirements.md)

- 2-year window in **< 2 hours**
- Chunk size tuned per source:
  - Shopify orders: 250/page
  - Meta insights: 90-day bucket per call
  - Google Ads insights: similar
  - Shiprocket: paginated by date
- Per-workspace parallelism cap (respect source rate limits)
- Resumable: `connector_cursor.backfill_resume_at` so crash restarts from last chunk
- **Same code path as live mode** — `mode=backfill` toggles bounded/unbounded window

## Rate limit + retry per source

```python
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type

@retry(
    wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
)
async def call_shopify(workspace_id, endpoint):
    token = await get_oauth_token(workspace_id, source="shopify")
    response = await httpx_client.get(endpoint, headers={"X-Shopify-Access-Token": token})
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 4))
        await asyncio.sleep(retry_after)
        raise httpx.HTTPStatusError("rate limited", request=response.request, response=response)
    response.raise_for_status()
    return response.json()
```

Per-source overrides:
- Shopify: respects `X-Shopify-Shop-Api-Call-Limit` header; uses leaky bucket
- Meta: respects `X-Business-Use-Case-Usage` header
- Google: gracefully handles `RESOURCE_EXHAUSTED`
- Shiprocket: simple exponential backoff

## Late-data handling (canon/TECH/02_integrations.md)

Refunds, RTO updates, and ad-attribution restatements arrive late. Each connector defines its own re-pull window:

- **Per-connector late-data windows:** Shopify 60d · **Meta 28d** (insights aren't final for 28 days — each incremental sync re-pulls the trailing 28d for active campaigns) · Google 7d · Razorpay 30d
- Watermarks live in `integrations.watermarks` (Postgres); reconciliation MV runs at window close
- `ingested_at` as version in `ReplicatedReplacingMergeTree` — latest wins (idempotent UPSERT)

## Connector quality levels + freshness SLO (canon/TECH/02_integrations.md §quality)

Every connector carries a quality grade that the UI surfaces:

| Level | Meaning | Examples |
|---|---|---|
| **Green** | Clean, stable API | Shopify, Meta, Google, Razorpay, Amazon SP-API, Salla, Zid |
| **Yellow** | Gated API — per-brand onboarding as access is granted | Myntra, Ajio, Meesho, Namshi, Talabat |
| **Red** | No seller API → Gmail OAuth + PDF/CSV + LLM extraction; brittle by design; **notify brand within 1 hour of breakage** + explicit UI label | Nykaa, Blinkit, Zepto, Instamart, Ounass |

**P0 connectors alert when freshness > 60 min.** `health_check` is "healthy" only when data is *fresh* — auth succeeding while data is stale is the canonical anti-pattern (a connector is NOT healthy just because the token is valid). Agents degrade gracefully and label stale data downstream.

## Canonical schema rules

- Every canonical event has `workspace_id` in envelope (partition key + payload field)
- `occurred_at` in payload (source time); `ingested_at` added at producer
- Monetary fields in **paisa** (`Int64`), never `Decimal` / `Float`
- Avro schemas are backward-compatible by default (additive fields only); breaking changes → new topic version (`.v2`)
- Schema registered with AWS Glue Schema Registry before producer publishes

## India-specific notes (per `india-commerce-economics` skill)

### Shiprocket lifecycle states
```
pending → manifested → in_transit → out_for_delivery → delivered
                                  ↘ ndr → rto_initiated → rto_in_transit → rto_delivered
```

NDR codes worth knowing:
- `customer_unavailable` — retry recommended
- `address_incorrect` — capture-and-update flow
- `customer_refused` — likely RTO
- `payment_issue` (COD) — convert-to-prepaid opportunity

### COD orders
- Revenue stays uncertain until delivered (`landed_revenue_minor` only after `delivered`)
- COD handling fee (`cod_handling_fee_minor`, typically ₹25–50) charged by Shiprocket; surfaces in CM2

## ClickHouse raw table (per source × entity)

```sql
CREATE TABLE raw_shopify_orders_local ON CLUSTER brain_cluster (
  workspace_id      String,
  source_event_id   String,
  occurred_at       DateTime64(3),
  ingested_at       DateTime64(3) DEFAULT now64(),
  raw_payload       String,                          -- JSON
  order_id          String,                          -- projection
  customer_id       String,                          -- projection
  total_minor       Int64                            -- projection
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (workspace_id, occurred_at, source_event_id);
```

## S3 archive layout

```
s3://brain-raw-archive/<source>/<entity>/<workspace>/<YYYY>/<MM>/<event_id>.json.gz
```

Gzipped JSON. Lifecycle policy: Intelligent-Tiering after 30 days; Glacier after 365 days.

## Common failure modes

- **Inventing metric formulas in connector** — connectors stay raw. Detection: canonical event field named `mer`, `cac`, etc.
- **Pipeline lag drift** — consumer behind by hours; dashboards stale. Mitigation: alarm on `kafka.consumer.lag > threshold` per consumer group. Detection: today's dashboard = yesterday's numbers.
- **Non-idempotent producer** — retry double-publishes. Mitigation: Redis SETNX before Kafka publish.
- **OAuth token leak** — logged or returned in error message. Detection: `grep -r "access_token" src/` returns code paths that don't redact.
- **Missing `workspace_id` in Kafka envelope** — downstream can't partition or scope. Detection: producer call without `key=workspace_id` or payload field.
- **Avro schema-breaking change** — Glue rejects. Mitigation: additive evolution with defaults.
- **Backfill cost surprise** — uncapped parallelism + per-row API call. Mitigation: chunk + parallel cap + cost estimate before run.

## References

- `canon/TECH/02_integrations.md` — canonical (Connector interface, sinks, quality levels, late-data windows, marketplace roster)
- `canon/technical-requirements.md` §11 — integrations summary + raw event store
- `skills/event-driven-kafka/SKILL.md` — MSK + Glue + Avro
- `skills/clickhouse-olap/SKILL.md` — raw_* table patterns
- `skills/python-services/SKILL.md` — asyncio + httpx + aiokafka
- `skills/india-commerce-economics/SKILL.md` §shiprocket — NDR + RTO + COD lifecycle
- `skills/security-baseline/SKILL.md` §oauth-tokens — KMS envelope encryption
