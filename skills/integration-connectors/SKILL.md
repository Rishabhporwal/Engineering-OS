---
name: integration-connectors
description: Brain's ingestion connectors (Shopify, Meta, Google, Shiprocket, Klaviyo, TikTok, Snap) — OAuth + idempotent UPSERT + Kafka + raw archive + cursors. Same code path live + backfill.
---

# Integration Connectors — Brain's Ingestion Patterns

The Maya-owned layer: source → canonical events → Kafka → downstream. Canon: `canon/TECH/02_integrations.md` (+ `canon/technical-requirements.md` §11).

## Universal connector flow
```
EventBridge cron (per workspace × integration)
  ▼ Acquire OAuth token from core-service (KMS-decrypted; refresh if expired)
  ▼ Read source (webhook payload OR API pull with cursor)
  ▼ Idempotency check: Redis SETNX 24h TTL  key: f"idempotency:{source}:{workspace_id}:{event_id}"
  ▼ [first time] Canonical transform: source row → canonical event (per protos/events/<topic>.avsc)
  ▼ Fan out to all sinks (idempotent UPSERT everywhere):
     • S3 raw archive (brain-raw-archive)
     • ClickHouse raw_<source>_<entity>_local
     • Kafka integrations.<entity>.v1 (Avro via Glue)
     • Postgres 90-day hot mirror (Phase 0–1; fast joins + webhook reconciliation)
  ▼ Persist cursor/watermark to Postgres integrations.watermarks
```
**Same `Connector` interface for every source** (`authenticate / refresh_token / sync(window) / receive_webhook / canonicalize / health_check`); **backfill == live — only the window changes** (bounded vs unbounded). Sinks written idempotently so a replay never doubles a row.

## OAuth per source
| Source | Flow | Scope minimum |
|---|---|---|
| Shopify | App OAuth, per-workspace install | `read_orders, read_products, read_customers, read_inventory` |
| Meta Ads | Marketing API OAuth | `ads_read, ads_management` |
| Google Ads | OAuth + Developer Token (apply Week 0) | `.../auth/adwords` |
| Shiprocket | Token (email+password → JWT; refresh in-band) | n/a |
| Klaviyo | OAuth or API key | `events:read, profiles:read, campaigns:read` |
| TikTok Ads | OAuth | `report.read, audience.read, ad.read` — **region-gated: UAE/GCC only (banned in India; never enable for `region=in`)** |
| Snapchat Ads | OAuth | `ads.basic, audience.read` — GCC-first (Phase 4) |

**Tokens in `core-service.integrations_oauth_tokens` (Postgres), envelope-encrypted with AWS KMS.** ingestion-service never persists plaintext; asks core-service per poll, refreshes if expired, discards from memory.

## Idempotency keys per source
Shopify orders `(workspace_id, order.id)` · Shopify customers `(workspace_id, customer.id, customer.updated_at)` · Meta `(workspace_id, ad_account_id, campaign_id, date)` · Google `(workspace_id, customer_id, campaign_id, date)` · Shiprocket `(workspace_id, awb_code, status)` · Klaviyo `(workspace_id, event_id)`. Redis SETNX 24h is the backstop; CH `ReplicatedReplacingMergeTree(ingested_at)` handles late updates. See `idempotency-handling`.

## Kafka producer
```python
await producer.send_and_wait(
    topic=f"integrations.{entity}.v1",
    key=workspace_id.encode(),                       # partition by workspace
    value=await avro_serializer.encode_record(topic=topic, record=payload),
    headers=[("event_id", event_id.encode()), ("schema_version", b"1"), ("trace_id", get_trace_id().encode())])
```
Compression zstd; retention infinite (MSK tiered storage to S3). See `event-driven-kafka`.

## Backfill discipline
2-year window in **< 2 hours** · chunk size per source (Shopify 250/page, Meta 90-day bucket/call, Google similar, Shiprocket by date) · per-workspace parallelism cap (respect source rate limits) · resumable via `connector_cursor.backfill_resume_at` · **same code path as live** (`mode=backfill` toggles the window).

## Rate limit + retry
```python
@retry(wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
       stop=stop_after_attempt(5), retry=retry_if_exception_type(httpx.HTTPStatusError))
async def call_shopify(workspace_id, endpoint):
    token = await get_oauth_token(workspace_id, source="shopify")
    r = await httpx_client.get(endpoint, headers={"X-Shopify-Access-Token": token})
    if r.status_code == 429:
        await asyncio.sleep(int(r.headers.get("Retry-After", 4)))
        raise httpx.HTTPStatusError("rate limited", request=r.request, response=r)
    r.raise_for_status(); return r.json()
```
Per-source: Shopify respects `X-Shopify-Shop-Api-Call-Limit` (leaky bucket) · Meta `X-Business-Use-Case-Usage` · Google `RESOURCE_EXHAUSTED` · Shiprocket exponential backoff.

## Late-data handling
Refunds, RTO updates, ad-attribution restatements arrive late; each connector defines a re-pull window: Shopify 60d · **Meta 28d** (insights not final for 28d — each sync re-pulls trailing 28d for active campaigns) · Google 7d · Razorpay 30d. Watermarks in `integrations.watermarks` (Postgres); reconciliation MV runs at window close; `ingested_at` as version in `ReplicatedReplacingMergeTree` (latest wins).

## Connector quality levels + freshness SLO
| Level | Meaning | Examples |
|---|---|---|
| **Green** | clean stable API | Shopify, Meta, Google, Razorpay, Amazon SP-API, Salla, Zid |
| **Yellow** | gated API — per-brand onboarding | Myntra, Ajio, Meesho, Namshi, Talabat |
| **Red** | no seller API → Gmail OAuth + PDF/CSV + LLM extraction; brittle; **notify brand within 1h of breakage** + explicit UI label | Nykaa, Blinkit, Zepto, Instamart, Ounass |

**P0 connectors alert when freshness > 60 min.** `health_check` is "healthy" only when data is *fresh* — auth succeeding while data is stale is the canonical anti-pattern (a connector is NOT healthy just because the token is valid). Agents degrade gracefully and label stale data downstream (see `data-quality`).

## Canonical schema rules
`workspace_id` in envelope (partition key + payload) · `occurred_at` (source time) in payload, `ingested_at` added at producer · monetary in **paisa** (`Int64`), never `Decimal`/`Float` · Avro backward-compatible (additive only); breaking → `.v2`; registered with Glue before publish.

## India-specific (per `india-commerce-economics`)
Shiprocket lifecycle: `pending → manifested → in_transit → out_for_delivery → delivered` (branch `→ ndr → rto_initiated → rto_in_transit → rto_delivered`). NDR codes: `customer_unavailable` (retry) · `address_incorrect` (capture-and-update) · `customer_refused` (likely RTO) · `payment_issue` COD (convert-to-prepaid opportunity). COD orders: `landed_revenue_minor` only after `delivered`; COD handling fee (`cod_handling_fee_minor`, ~₹25–50) surfaces in CM2.

## ClickHouse raw table + S3 archive
```sql
CREATE TABLE raw_shopify_orders_local ON CLUSTER brain_cluster (
  workspace_id String, source_event_id String, occurred_at DateTime64(3),
  ingested_at DateTime64(3) DEFAULT now64(), raw_payload String,   -- JSON
  order_id String, customer_id String, total_minor Int64           -- projections
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at) ORDER BY (workspace_id, occurred_at, source_event_id);
```
S3: `s3://brain-raw-archive/<source>/<entity>/<workspace>/<YYYY>/<MM>/<event_id>.json.gz` (gzip; Intelligent-Tiering after 30d, Glacier after 365d).

## Common failure modes
Inventing metric formulas in a connector (connectors stay raw) · pipeline lag drift (alarm on `kafka.consumer.lag`) · non-idempotent producer (Redis SETNX before publish) · OAuth token leak (`grep -r "access_token" src/` for unredacted paths) · missing `workspace_id` in envelope · Avro breaking change (Glue rejects) · backfill cost surprise (chunk + parallel cap + cost estimate first).

## References
`canon/TECH/02_integrations.md` · `canon/technical-requirements.md` §11 · `event-driven-kafka` · `clickhouse-olap` · `python-services` · `india-commerce-economics` §shiprocket · `security-baseline` §oauth-tokens · `idempotency-handling` · `data-quality`.
