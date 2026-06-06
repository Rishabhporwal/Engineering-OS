---
name: integration-connectors
description: External-integration / connector patterns — OAuth token handling, idempotent UPSERT, canonical events, raw archive, cursors/watermarks, late-data re-pull, freshness SLOs. Same code path live + backfill.
---

# Integration Connectors — Ingestion Patterns

The layer that turns an external source into canonical events: source → canonical events → the async backbone → downstream. Canon: the Product Canon's integrations section (`STACK.md`, HLD/LLD).

> The patterns below are vendor-agnostic. Where a specific vendor appears (a storefront, an ads platform, a logistics provider, a marketing tool), treat it as an *example* of the pattern, not a requirement — your product's sources live in the Canon.

## Universal connector flow
```
Scheduler (per tenant × integration)
  ▼ Acquire an OAuth token from the auth service (decrypted from the managed store; refresh if expired)
  ▼ Read source (webhook payload OR API pull with cursor)
  ▼ Idempotency check: cache SETNX 24h TTL  key: f"idempotency:{source}:{tenant_id}:{event_id}"
  ▼ [first time] Canonical transform: source row → canonical event (per the event schema)
  ▼ Fan out to all sinks (idempotent UPSERT everywhere):
     • raw object-store archive
     • columnar raw table
     • the async backbone (a versioned event topic)
     • a hot transactional mirror (fast joins + webhook reconciliation)
  ▼ Persist cursor/watermark to the watermarks table
```
**Same `Connector` interface for every source** (`authenticate / refresh_token / sync(window) / receive_webhook / canonicalize / health_check`); **backfill == live — only the window changes** (bounded vs unbounded). Sinks written idempotently so a replay never doubles a row.

## OAuth per source
The shape is the same across sources; the scopes differ:

| Source kind | Flow | Scope minimum (example) |
|---|---|---|
| Storefront | App OAuth, per-tenant install | read orders / products / customers / inventory |
| Ads platform | Marketing-API OAuth (sometimes + a developer token) | ads read / management |
| Marketing/CRM tool | OAuth or API key | events / profiles / campaigns read |
| Logistics / fulfilment | Token (or credential → JWT; refresh in-band) | as the provider allows |

Some sources are region-gated (available in one region, banned in another) — gate them on the tenant's region, never enable blindly.

**Tokens live in the auth service's encrypted store, envelope-encrypted with a managed KMS.** The ingestion service never persists plaintext; it asks the auth service per poll, refreshes if expired, and discards from memory.

## Idempotency keys per source
Derive a key from the source event's stable identity, not the client: e.g. `(tenant_id, order.id)`, `(tenant_id, customer.id, customer.updated_at)`, `(tenant_id, account_id, campaign_id, date)`, `(tenant_id, shipment_id, status)`, `(tenant_id, event_id)`. A cache `SETNX` 24h is the backstop; a `ReplacingMergeTree`-style columnar engine keyed on an ingest version handles late updates. See `idempotency-handling`.

## Event producer
```python
await producer.send_and_wait(
    topic=f"integrations.{entity}.v1",
    key=tenant_id.encode(),                           # partition by tenant
    value=await serializer.encode_record(topic=topic, record=payload),
    headers=[("event_id", event_id.encode()), ("schema_version", b"1"), ("trace_id", get_trace_id().encode())])
```
Compression on; retention per the Canon (tiered to object storage where supported). See `event-driven-kafka`.

## Backfill discipline
A multi-year window in a bounded time · chunk size per source (page/bucket per the API) · per-tenant parallelism cap (respect source rate limits) · resumable via a `backfill_resume_at` cursor · **same code path as live** (a `mode=backfill` toggle changes only the window).

## Rate limit + retry
```python
@retry(wait=wait_exponential_jitter(initial=1, max=30, jitter=2),
       stop=stop_after_attempt(5), retry=retry_if_exception_type(httpx.HTTPStatusError))
async def call_source(tenant_id, endpoint):
    token = await get_oauth_token(tenant_id, source="storefront")
    r = await httpx_client.get(endpoint, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 429:
        await asyncio.sleep(int(r.headers.get("Retry-After", 4)))
        raise httpx.HTTPStatusError("rate limited", request=r.request, response=r)
    r.raise_for_status(); return r.json()
```
Respect each source's own rate-limit signal (a call-limit header, a usage header, a `RESOURCE_EXHAUSTED` code, or plain exponential backoff).

## Late-data handling
Refunds, status updates, and attribution restatements arrive late; each connector defines a re-pull window (e.g. some insights aren't final for N days — each sync re-pulls the trailing N days for active records). Watermarks live in the watermarks table; a reconciliation step runs at window close; an `ingested_at` version in a `ReplacingMergeTree`-style table means latest wins.

## Connector quality levels + freshness SLO
| Level | Meaning | Examples (kind) |
|---|---|---|
| **Green** | clean stable API | first-party storefronts / ads platforms |
| **Yellow** | gated API — per-tenant onboarding | marketplaces requiring approval |
| **Red** | no real API → email/file ingest + extraction; brittle; **notify the tenant fast on breakage** + explicit UI label | sources with no seller API |

**Critical connectors alert when freshness exceeds the SLO.** `health_check` is "healthy" only when data is *fresh* — auth succeeding while data is stale is the canonical anti-pattern (a connector is NOT healthy just because the token is valid). Agents degrade gracefully and label stale data downstream (see `data-quality`).

## Canonical schema rules
The tenant key in the envelope (partition key + payload) · `occurred_at` (source time) in payload, `ingested_at` added at the producer · monetary in **integer minor units**, never float/decimal display types · schemas backward-compatible (additive only); a breaking change → a new version, registered with the schema registry before publish.

## Domain-specific lifecycles
A source's domain lifecycle (e.g. a fulfilment state machine with branch states, status/reason codes that drive retries or conversions, settlement-timing rules that decide when a value becomes realized) is product-specific — model it in the Canon and the connector's `canonicalize`. Keep the *raw* in the connector; compute derived metrics only via the metric registry, never in the connector.

## Columnar raw table + object-store archive
```sql
CREATE TABLE raw_source_orders_local ON CLUSTER cluster (
  tenant_id String, source_event_id String, occurred_at DateTime64(3),
  ingested_at DateTime64(3) DEFAULT now64(), raw_payload String,   -- JSON
  order_id String, customer_id String, total_minor Int64           -- projections
) ENGINE = ReplicatedReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(occurred_at) ORDER BY (tenant_id, occurred_at, source_event_id);
```
Archive raw payloads to object storage partitioned `<source>/<entity>/<tenant>/<YYYY>/<MM>/<event_id>.json.gz` (gzip; lifecycle to cheaper tiers over time).

## Common failure modes
Inventing metric formulas in a connector (connectors stay raw) · pipeline lag drift (alarm on consumer lag) · non-idempotent producer (cache SETNX before publish) · OAuth token leak (`grep -r "access_token" src/` for unredacted paths) · missing tenant key in the envelope · a breaking schema change (the registry rejects it) · backfill cost surprise (chunk + parallel cap + cost estimate first).

## References
Product Canon integrations section · `event-driven-kafka` · `clickhouse-olap` · `python-services` · `oauth-implementation` · `security-baseline` §oauth-tokens · `idempotency-handling` · `data-quality`.
