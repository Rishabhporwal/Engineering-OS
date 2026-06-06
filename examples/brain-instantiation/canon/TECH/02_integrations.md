# TECH/02 — Integrations & ETL (Kafka-Driven)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E3 (Backend/Data) | **Reviewers:** E1, E4
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/01_data_architecture.md](01_data_architecture.md)

This document defines:
- The ingestion-service architecture
- Per-source connector specifications (Shopify, Meta, Google, Shiprocket, Klaviyo)
- Kafka event topology and event schemas
- Backfill vs incremental sync
- Error handling and observability
- Scale design: how ingestion handles 100k+ events/min

---

## 1. ingestion-service Architecture

One Python service. One container image. Multiple connector implementations.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ingestion-service                              │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Scheduler (EventBridge → SQS → service)                         │ │
│  │  Tasks: "Sync orders for workspace X via Shopify"               │ │
│  └────────────────────────────────┬───────────────────────────────┘ │
│                                   │                                   │
│  ┌────────────────────────────────▼───────────────────────────────┐ │
│  │ Connector Registry (Strategy Pattern)                           │ │
│  │ • ShopifyOrdersConnector                                        │ │
│  │ • MetaAdsConnector                                              │ │
│  │ • GoogleAdsConnector                                            │ │
│  │ • ShiprocketConnector                                           │ │
│  │ • KlaviyoConnector (Phase 2)                                    │ │
│  └────────────────────────────────┬───────────────────────────────┘ │
│                                   │                                   │
│         ┌─────────────────────────┼─────────────────────────┐        │
│         │                         │                         │        │
│         ▼                         ▼                         ▼        │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐ │
│  │ Token        │         │ Rate Limiter │         │ Retry        │ │
│  │ Manager      │         │ (per-source) │         │ Manager      │ │
│  │ (KMS-backed) │         │              │         │ (Redis)      │ │
│  └──────────────┘         └──────────────┘         └──────────────┘ │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Canonicalizer                                                   │ │
│  │  Raw API response → Canonical event (one per record)            │ │
│  └────────────────────────────────┬───────────────────────────────┘ │
│                                   │                                   │
│  ┌────────────────────────────────▼───────────────────────────────┐ │
│  │ Output Sinks                                                    │ │
│  │  • Kafka producer → integrations.* topics (canonical events)   │ │
│  │  • S3 archiver    → raw payload backup                          │ │
│  │  • ClickHouse     → raw_* tables (direct write)                 │ │
│  │  • Postgres       → *_recent tables (last 90d window)           │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Scaling

- Stateless. Each pod handles any (workspace, integration, resource) job.
- HPA scales 4–30 pods based on SQS queue depth + CPU.
- Karpenter spins up nodes on backfill bursts.
- Per-source rate limits enforced via Redis (sliding window).

### Job Trigger Sources

1. **EventBridge Scheduler:** cron-style scheduled syncs (e.g., "every 10 min, fan out Shopify sync for all workspaces"). Pushes job descriptors to SQS.
2. **Webhooks** (Phase 2): Shopify, Meta send change notifications. Trigger immediate targeted sync.
3. **User-triggered backfill:** UI → api-gateway → core-service publishes `operations.sync.requested.v1` event → ingestion-service consumes.

### Job Descriptor

A unit of work:

```json
{
  "job_id": "uuid",
  "workspace_id": "uuid",
  "integration_id": "uuid",
  "integration_type": "shopify",
  "resource": "orders",
  "window": {
    "start": "2026-05-13T00:00:00Z",
    "end":   "2026-05-13T23:59:59Z",
    "is_backfill": false
  },
  "cursor": null,
  "priority": "normal"
}
```

Stored briefly in SQS; processed once, idempotent.

---

## 2. Idempotency & Watermarks

### Watermark Storage

Each integration's watermarks live in `integrations.watermarks` (Postgres):

```json
{
  "orders": {
    "last_synced_at": "2026-05-13T14:30:00Z",
    "last_record_updated_at": "2026-05-13T14:28:14Z",
    "earliest_backfilled_at": "2024-10-15T00:00:00Z"
  },
  "customers": { "last_synced_at": "..." },
  "campaigns": { "last_synced_at": "..." }
}
```

Updated atomically after each successful sync.

### Late-Data Window

External sources update records after the fact. Each connector defines a rolling window:

```python
class ShopifyOrdersConnector(BaseConnector):
    LATE_DATA_WINDOW = timedelta(days=60)        # refunds can hit 60d later
    NEW_DATA_LAG = timedelta(minutes=5)          # clock skew safety
```

Sync window = `max(last_updated - LATE_DATA_WINDOW, now - LATE_DATA_WINDOW)` to `now - NEW_DATA_LAG`.

Re-fetched records UPSERT to no-op when payload hash unchanged. ClickHouse's `ReplacingMergeTree` dedups by `version`.

### Event Versioning

Every canonical event carries `version`:

```json
{
  "event_id": "uuid",
  "workspace_id": "uuid",
  "source_record_id": "shopify_order_id_123",
  "event_type": "order.created" | "order.updated" | "order.refunded" | "order.cancelled",
  "occurred_at": "2026-05-13T14:28:14Z",
  "version": 17329123128,                       -- monotonic; from source updated_at (ms epoch)
  "schema_version": "v1",
  "payload": { ...canonical fields... }
}
```

Higher `version` wins in ClickHouse `ReplacingMergeTree`.

---

## 3. Kafka Topology

### Topics for Ingestion Outputs

| Topic | Partitions | Retention | Producer | Consumers |
|-------|-----------|-----------|----------|-----------|
| `integrations.orders.v1` | 12 | Infinite (S3 tier) | ingestion-service | analytics-service, intelligence-service |
| `integrations.customers.v1` | 12 | Infinite | ingestion-service | analytics-service |
| `integrations.products.v1` | 6 | Infinite | ingestion-service | analytics-service |
| `integrations.line_items.v1` | 12 | Infinite | ingestion-service | analytics-service |
| `integrations.refunds.v1` | 6 | Infinite | ingestion-service | analytics-service |
| `integrations.campaigns.v1` | 6 | Infinite | ingestion-service | analytics-service |
| `integrations.ads_insights.v1` | 12 | Infinite | ingestion-service | analytics-service |
| `integrations.shipments.v1` | 12 | Infinite | ingestion-service | analytics-service |
| `integrations.shipment_events.v1` | 12 | Infinite | ingestion-service | analytics-service |
| `integrations.sync.completed.v1` | 3 | 30 days | ingestion-service | core-service (for UI updates) |
| `integrations.sync.failed.v1` | 3 | 30 days | ingestion-service | notifications-service |

### Partitioning

All event topics partition by `workspace_id` hash:

```python
producer.produce(
    topic='integrations.orders.v1',
    key=workspace_id.encode(),     # determines partition
    value=avro_serialize(event),
)
```

Guarantees: a single workspace's events are always ordered. Critical for `version`-based deduplication downstream.

### Event Schemas (Avro)

Stored in AWS Glue Schema Registry; schema files in `/protos/events/`.

```avro
// protos/events/order_event.avsc
{
  "type": "record",
  "name": "OrderEvent",
  "namespace": "brain.events.integrations.v1",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "workspace_id", "type": "string"},
    {"name": "source_integration", "type": {"type": "enum", "name": "Integration",
      "symbols": ["SHOPIFY", "WOOCOMMERCE", "BIGCOMMERCE"]}},
    {"name": "source_record_id", "type": "string"},
    {"name": "event_type", "type": {"type": "enum", "name": "OrderEventType",
      "symbols": ["CREATED", "UPDATED", "REFUNDED", "CANCELLED"]}},
    {"name": "occurred_at", "type": {"type": "long", "logicalType": "timestamp-millis"}},
    {"name": "version", "type": "long"},
    {"name": "schema_version", "type": "string", "default": "v1"},
    {"name": "payload", "type": "string"}                  // serialized canonical JSON
  ]
}
```

### Producing Events

```python
# apps/ingestion-service/src/sinks/kafka.py
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

class KafkaEventSink:
    def __init__(self):
        sr = SchemaRegistryClient({'url': GLUE_SCHEMA_REGISTRY_URL, 'auth': aws_iam_auth()})
        self.serializer = AvroSerializer(sr, schema_str_from_file('order_event.avsc'))
        self.producer = Producer({
            'bootstrap.servers': MSK_BOOTSTRAP,
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'AWS_MSK_IAM',
            'compression.type': 'zstd',
            'linger.ms': 50,
            'batch.size': 65536,
            'enable.idempotence': True,
            'acks': 'all'
        })

    def emit_order(self, event: OrderEvent):
        self.producer.produce(
            topic='integrations.orders.v1',
            key=event.workspace_id.encode(),
            value=self.serializer(event.to_dict(), SerializationContext(topic, MessageField.VALUE)),
            on_delivery=self._on_delivery_callback,
        )
```

### Consuming Events

Consumers in analytics-service:

```python
# apps/analytics-service/src/consumers/orders_consumer.py
from confluent_kafka import Consumer, KafkaError
from brain_clickhouse import ClickHouseClient

class OrdersConsumer:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': MSK_BOOTSTRAP,
            'security.protocol': 'SASL_SSL',
            'sasl.mechanism': 'AWS_MSK_IAM',
            'group.id': 'analytics.orders.v1',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        })
        self.ch = ClickHouseClient()

    def run(self):
        self.consumer.subscribe(['integrations.orders.v1'])
        batch = []
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                self._flush_if_needed(batch)
                continue
            if msg.error():
                handle_error(msg.error())
                continue

            event = self.deserialize(msg)
            batch.append(self.to_ch_row(event))

            if len(batch) >= 1000:
                self._flush(batch)
                self.consumer.commit(asynchronous=False)

    def _flush(self, batch):
        self.ch.insert('orders_local', batch)
```

Consumer groups give us automatic partition assignment + scale-out (more consumer pods → more partitions consumed in parallel).

---

## 4. Shopify Connector

### API: Shopify Admin GraphQL API (2024-10 or newer)

GraphQL is mandatory now; REST is deprecated for new apps.

### Auth: OAuth 2.0

```
1. User clicks "Connect Shopify" in Brain
2. Brain redirects to:
   https://{shop}.myshopify.com/admin/oauth/authorize
     ?client_id=BRAIN_APP_ID
     &scope=read_orders,read_products,read_customers,read_inventory,read_fulfillments
     &redirect_uri=https://api.{BRAIN_DOMAIN}/integrations/shopify/callback
     &state={signed_csrf_token}
3. Callback handler exchanges code for access_token
4. Token encrypted via KMS envelope encryption; stored in AWS Secrets Manager
5. integrations row created with credential_secret_arn reference
6. Brain publishes operations.sync.requested.v1 for backfill
```

### Resources

| Resource | GraphQL root | Backfill range | Incremental key |
|----------|-------------|----------------|-----------------|
| Orders | `orders` | All-time (capped 3y) | `updated_at` |
| Customers | `customers` | All-time | `updated_at` |
| Products | `products` | All-time | `updated_at` |
| Line items | nested in `order.lineItems` | with parent | — |
| Refunds | nested in `order.refunds` | with parent | — |
| Inventory | `inventoryLevels` | daily snapshot | — |

### Pagination

```python
async def fetch_orders(self, integration, since: datetime):
    cursor = None
    while True:
        query = """
        query GetOrders($cursor: String, $query: String) {
          orders(first: 100, after: $cursor, query: $query, sortKey: UPDATED_AT) {
            pageInfo { hasNextPage, endCursor }
            edges {
              node {
                id, name, createdAt, updatedAt, displayFinancialStatus,
                totalPriceSet { shopMoney { amount, currencyCode } },
                customer { id, numberOfOrders },
                lineItems(first: 100) {
                  edges { node { id, title, quantity, variant { id, sku }, originalUnitPriceSet { shopMoney { amount } } } }
                },
                refunds { id, createdAt, totalRefundedSet { shopMoney { amount } } },
                shippingAddress { city, province, zip, country }
              }
            }
          }
        }
        """
        variables = {
            'cursor': cursor,
            'query': f'updated_at:>=\'{since.isoformat()}\'',
        }
        data = await self.http.execute_graphql(query, variables, integration)
        self._check_throttle(data)

        for edge in data['orders']['edges']:
            yield self.to_order_event(edge['node'])

        if not data['orders']['pageInfo']['hasNextPage']:
            break
        cursor = data['orders']['pageInfo']['endCursor']
```

### Rate Limit Handling

Shopify's leaky bucket signals via `extensions.cost.throttleStatus`:

```python
def _check_throttle(self, response):
    cost = response.get('extensions', {}).get('cost', {})
    available = cost.get('throttleStatus', {}).get('currentlyAvailable', 1000)
    restore = cost.get('throttleStatus', {}).get('restoreRate', 50)
    if available < 100:
        asyncio.sleep(max(0.5, 100 / restore))
```

On 429, raise `RateLimitError` and re-queue with backoff.

### Canonicalization

Raw → canonical OrderEvent:

```python
def to_order_event(self, raw: dict) -> OrderEvent:
    money = raw['totalPriceSet']['shopMoney']
    return OrderEvent(
        event_id=str(uuid4()),
        workspace_id=self.workspace_id,
        source_integration=Integration.SHOPIFY,
        source_record_id=raw['id'].split('/')[-1],
        event_type=OrderEventType.UPDATED,                # or CREATED, derived from createdAt vs first-seen
        occurred_at=parse_iso(raw['updatedAt']),
        version=int(parse_iso(raw['updatedAt']).timestamp() * 1000),
        schema_version='v1',
        payload=json.dumps({
            'source_order_number': raw['name'],
            'created_at': raw['createdAt'],
            'customer_id_external': raw.get('customer', {}).get('id'),
            'customer_orders_count': raw.get('customer', {}).get('numberOfOrders'),
            'subtotal_minor': to_minor(money['amount'], money['currencyCode']),
            'currency_code': money['currencyCode'],
            # ... etc.
        }),
    )
```

### Output Fan-Out

For each canonical event, write to **3 sinks**:

```python
async def process_order(self, raw_payload):
    event = self.to_order_event(raw_payload)

    # 1. Raw archive (S3 + ClickHouse raw table)
    await self.raw_sink.emit(event, raw_payload)

    # 2. Kafka canonical event
    await self.kafka_sink.emit_order(event)

    # 3. Postgres recent-window mirror (for fast 90d lookups)
    await self.pg_sink.upsert_order(event)
```

Failures in one sink don't block others (best-effort with circuit breakers).

---

## 5. Meta Ads Connector

### API: Meta Marketing API v18.0+

### Auth: OAuth 2.0 with long-lived tokens (60-day expiry; refresh every 30d)

Scopes: `ads_read`, `business_management`, `read_insights`.

### Resources

| Resource | Endpoint | Notes |
|----------|----------|-------|
| Campaigns | `/{ad_account_id}/campaigns` | List + diff |
| Ad Sets | `/{ad_account_id}/adsets` | Phase 2 |
| Ads | `/{ad_account_id}/ads` | Phase 2 |
| Insights | `/{campaign_id}/insights?time_increment=1` | Daily breakdown |

### Late-Data Window: 28 Days

Meta insights are not final for 28 days. Each incremental sync re-pulls the last 28 days for all active campaigns.

```python
class MetaInsightsConnector(BaseConnector):
    LATE_DATA_WINDOW = timedelta(days=28)
```

### Output

Two event types:

- `integrations.campaigns.v1` — when a campaign's metadata changes
- `integrations.ads_insights.v1` — for each (campaign, date) data point

### Campaign Auto-Classification

Runs as a downstream step in core-service (which owns `campaign_classifications`):

```python
# In core-service: consumes integrations.campaigns.v1
async def on_campaign_event(event):
    if not has_classification(event.workspace_id, event.campaign_id):
        classification, confidence = auto_classify_meta_campaign(event.payload)
        await save_classification(event.workspace_id, event.campaign_id, classification, confidence, auto=True)
```

Classification logic same as v1.0 (see TECH/02 v1.0 §4).

---

## 6. Google Ads Connector

### API: Google Ads API v15+ (gRPC)

### Auth: OAuth 2.0 + Developer Token + Manager Account (MCC)

Apply for Developer Token early — expect 2 weeks for approval.

### Late-Data Window: 7 Days

Google's attribution stabilizes faster than Meta's.

### Quirk: Cost in Micros

`metrics.cost_micros` in micro-currency-units. Convert in canonicalizer.

```python
def cost_to_minor(cost_micros: int, currency: str) -> int:
    # micros → currency unit → minor
    # 1,000,000 micros = 1 currency unit
    # 1 currency unit = 100 minor units (for most currencies)
    return cost_micros // 10_000
```

---

## 7. Shiprocket Connector

### API: Shiprocket REST API v1

### Auth: Email/password → JWT (10-day expiry; daily refresh job)

Onboarding UX: user pastes Shiprocket credentials. Encrypted via KMS envelope encryption.

### Resources

| Resource | Pattern |
|----------|---------|
| Orders/Shipments | Paginated, filter by `updated_at` |
| Tracking events | Per shipment on status change |
| Pincode serviceability | Cached aggressively; refresh weekly |

### Output Events

- `integrations.shipments.v1` — shipment lifecycle events
- `integrations.shipment_events.v1` — granular tracking events (used for NDR analysis)

### Order Matching

Shiprocket shipments need to match Shopify orders for unified analytics. Matching key options:

1. `channel_order_id` (if Shopify-Shiprocket sync configured)
2. Order number string match
3. Fuzzy match on email + total + date

Unmatched shipments stored with `order_id = NULL`; surfaced in admin view.

### Status Mapping

Shiprocket → Brain canonical statuses (see TECH/04 §1 for full state machine).

---

## 7a. Marketplace Connectors (Phase 2-3) — Multi-Channel Commerce

Per the brief, Brain's data layer must cover every major commerce surface a D2C brand operates on in India and the Middle East. Brain ships marketplace connectors with an explicit **quality gradient** — engineering honesty about which integrations are robust vs brittle.

### 7a.1 Integration Quality Gradient

| Tier | Quality | Marketplaces |
|------|---------|--------------|
| **Green** (clean API) | Build with confidence; test rigorously | Amazon India/AE (SP-API), Flipkart, Noon, BigBasket (gated but stable), Salla, Zid |
| **Yellow** (gated API; per-brand onboarding required) | Build the connector, onboard per-brand as access granted | Myntra, Ajio, Meesho, Namshi, Talabat |
| **Red** (no seller API; workaround required) | Brittle by definition; monitor continuously; notify brand within 1 hour of breakage | Nykaa, Blinkit, Zepto, Instamart, Ounass |

### 7a.2 India Marketplaces

| Marketplace | Tier | Connector Type | Phase |
|-------------|------|---------------|-------|
| **Amazon India (SP-API)** | Green | OAuth + Selling Partner API; reports + orders + inventory | Phase 2 W14 |
| **Flipkart Seller API** | Green | OAuth + REST; orders + listings + returns + payments | Phase 2 W15 |
| **Myntra Partner API** | Yellow | Gated; per-brand application; OAuth | Phase 2 W18 |
| **Ajio Partner API** | Yellow | Gated; per-brand application | Phase 2 W19 |
| **Meesho Seller API** | Yellow | Gated; brand-tier specific | Phase 2 W19 |
| **BigBasket Seller** | Green (gated) | Per-brand onboarding; stable once provisioned | Phase 3 W23 |
| **Nykaa** | Red | **Workaround:** Gmail OAuth + LLM PDF parsing of seller portal exports | Phase 3 W25 |

### 7a.3 Middle East Marketplaces

| Marketplace | Tier | Connector Type | Phase |
|-------------|------|---------------|-------|
| **Amazon AE (SP-API)** | Green | Same Selling Partner API as India, different marketplace ID | Phase 3 W23 |
| **Noon Seller API** | Green | Clean REST; orders + listings + payments | Phase 3 W24 |
| **Namshi Partner** | Yellow | Gated; per-brand application | Phase 3 W26 |
| **Talabat Partner** | Yellow | Gated; F&B-focused | Phase 3 W27 |
| **Ounass** | Red | **Workaround:** Gmail OAuth + LLM PDF parsing | Phase 3 W28 |

### 7a.4 Quick Commerce (India) — The Hardest Category

**No quick-commerce platform in India offers a clean seller API.** Phase 2 commitment is workaround integrations producing reliable data; graduate to native API when platforms open up.

| Platform | Tier | Workaround |
|----------|------|------------|
| **Blinkit** | Red | Gmail OAuth → parse seller portal daily-report PDFs → LLM extract orders/SKUs/inventory |
| **Zepto** | Red | Gmail OAuth → parse seller portal exports |
| **Instamart** | Red | Gmail OAuth + SFTP if brand has it; LLM parse of report attachments |

**Engineering pattern for Red workarounds:**

```
1. Brand grants Gmail OAuth (read-only, filtered to seller-portal email addresses)
2. Daily job pulls latest emails matching seller-portal patterns
3. Detects PDF/CSV attachments + extracts via:
   - PDF: pdfplumber → if structured table extraction succeeds, paradigm 1 (SQL).
          If unstructured → paradigm 3 (Claude Haiku) extracts to JSON schema.
   - CSV: direct parse, paradigm 1.
4. Output → canonical OrderEvent + InventorySnapshot → Kafka → ClickHouse
5. Health check: if 24h passes without a new export landing, alert brand + on-call
6. Schema-drift detection: if extraction confidence < 95%, page on-call (platform changed format)
```

UI explicitly labels Red integrations: *"Workaround integration — Brain reads your seller-portal exports via Gmail. Reliability depends on platform stability. Notifications within 1 hour of breakage."*

### 7a.5 The Strategic Cost of This Integration Matrix

Marketplaces are not optional. A brand at ₹3Cr/month with 40% of GMV on Amazon + Myntra + Nykaa is invisible to a Shopify-only analytics tool. Brain's wedge depends on seeing all of it. The Red workarounds are brittle by design — engineering accepts this cost because the alternative (telling the brand "we don't see Nykaa") is product-suicide in this market.

### 7a.6 Razorpay (Payments) — Required, Green

Already listed in §2 but elevated: **Razorpay is a green integration**, required Phase 2. Brain consumes Razorpay for:

- Payment + settlement timing (per-order)
- GoKwik Cashflow data (when brand has it enabled) — input to AICFO-Cashflow
- COD-vs-prepaid economics
- Refund processing fees

```python
class RazorpayConnector(BaseConnector):
    integration_type = "razorpay"
    LATE_DATA_WINDOW = timedelta(days=30)  # settlements can update for 30d post-order
```

---

## 8. Klaviyo Connector (Phase 2)

### API: Klaviyo REST v2024-02-15+

### Auth: Private API Key (user-generated, pasted in)

### Resources

| Resource | Pattern |
|----------|---------|
| Campaigns | Incremental |
| Campaign metrics | Per campaign per day |
| Flows | List + per-message metrics |
| Events (`Placed Order`) | For email-attributed revenue |

### Email-Attributed Revenue

Klaviyo events tie an order to the campaign that drove it. We use this directly:

```python
# Email-attributed revenue: sum of order totals where event.metric.name = 'Placed Order' AND event.attribution.send_id IS NOT NULL
```

Stored as `daily_metrics.email_revenue_minor`.

---

## 9. Backfill UX

When a user connects an integration:

```
┌──────────────────────────────────────────────────┐
│  Shopify connected ✓                              │
│  Backfilling 3 years of orders...                 │
│  ▰▰▰▰▰▰▰░░░ 68% (17,240 / 25,000 orders)         │
│  Estimated time remaining: 12 minutes             │
└──────────────────────────────────────────────────┘
```

Implementation:

- `integrations.watermarks.backfill_progress` JSONB updated per page
- core-service exposes `integrations.syncProgress` query that aggregates progress
- Frontend polls every 5s during active backfill

Backfill priority: separate Kafka topic `integrations.sync.backfill.v1` with throttled consumers (1 per workspace) to avoid hammering external APIs.

---

## 10. Rate Limit Architecture

Per-source rate limits enforced in Redis (cluster-mode for high throughput):

```python
# pylibs/brain_kafka/rate_limiter.py
import asyncio
from redis.asyncio import Redis

class SlidingWindowRateLimiter:
    def __init__(self, redis: Redis, scope: str, max_per_second: int):
        self.redis = redis
        self.scope = scope
        self.max = max_per_second

    async def acquire(self):
        key = f"rl:{self.scope}"
        now = time.time() * 1000
        await self.redis.zremrangebyscore(key, 0, now - 1000)
        count = await self.redis.zcard(key)
        if count >= self.max:
            sleep_for = await self._compute_wait(key, now)
            await asyncio.sleep(sleep_for)
            return await self.acquire()
        await self.redis.zadd(key, {str(uuid4()): now})
        await self.redis.expire(key, 60)
```

Used per (workspace, integration):

```python
limiter = SlidingWindowRateLimiter(redis, scope=f"shopify:{workspace_id}", max_per_second=40)
async with limiter:
    response = await shopify_client.execute_graphql(...)
```

Global per-source limiter ensures we don't exceed our app-wide quota (e.g., Google Ads developer token).

---

## 11. Failure Handling

### Error Categories

| Error | Action | Operator-Visible |
|-------|--------|------------------|
| Transient (network, 5xx) | DLQ + retry with backoff (max 3) | No (unless persists) |
| Rate limit | Per-source backoff; re-queue | No |
| Auth expired | Refresh token; if fails → mark `expired` | Yes — banner |
| Auth revoked (4xx) | Mark `disconnected`; revoke webhooks | Yes — banner + email |
| Schema drift | Sentry alert; skip record; continue | Internal |
| Quota exceeded | Mark `rate_limited`; resume next day | Yes — banner |
| Canonicalization bug | DLQ; Sentry; re-process after fix | No |

### Dead Letter Queue

Failed events go to `integrations.dlq.v1`:

```json
{
  "original_topic": "integrations.orders.v1",
  "original_event": { ... },
  "error_class": "CanonicalizationError",
  "error_message": "Missing required field 'totalPriceSet'",
  "attempts": 3,
  "first_failed_at": "...",
  "last_failed_at": "..."
}
```

Manual replay tool: `tools/replay_dlq.py --topic integrations.orders.v1 --since 2026-05-13`.

---

## 12. Observability

Metrics per (workspace, integration, resource):

- `etl_sync_runs_total` — counter
- `etl_records_fetched_total` — counter
- `etl_records_published_total{topic}` — counter (Kafka emissions)
- `etl_sync_duration_seconds` — histogram
- `etl_errors_total{integration, error_class}` — counter
- `etl_sync_lag_seconds` — gauge (seconds since `last_record_updated_at`)
- `kafka_publish_latency_seconds` — histogram
- `kafka_publish_errors_total` — counter

Alerts (CloudWatch alarms):
- `etl_sync_lag_seconds > 3600` for `shopify_orders` → P2
- `kafka_publish_errors_total` rate > 1/min → P3
- Any integration `status = error` for >24h → email workspace owners

---

## 13. Scale Design

### Target: 100k events/min ingested

At Phase 4 with 500 workspaces averaging 200 orders/day + 100 ad insights + 200 shipment events:
- 500 × 500 = 250k events/day in canonical form
- Burst: backfills can push 10k events/min for a single workspace

### Capacity

| Layer | Throughput target | Notes |
|-------|------------------|-------|
| Connector fetch (per worker, per integration) | 50 events/sec | Limited by external API rate limits |
| Kafka publish (per producer) | 10K events/sec | With batching + zstd |
| Kafka cluster ingest | 200K events/sec | 6 brokers × 3 AZs |
| ClickHouse insert | 100K rows/sec | Batched 1K-row inserts |
| Postgres recent-mirror UPSERT | 5K rows/sec | Bottleneck; batched + retried |

### Scaling Knobs

- **More pods:** linear gain up to consumer-group partition count
- **More partitions:** increase from 12 → 24 → 48 as workspace count grows
- **Backfill throttling:** dedicated `etl:backfill` consumer group with limited pods; doesn't starve live sync
- **Read replicas:** ingestion reads (for token refresh, watermark lookups) hit Postgres replica

---

## 14. Local Development

```bash
# docker-compose.yml provides MSK-equivalent (single-broker Kafka), MinIO, ClickHouse, Postgres

# Run a mock Shopify connector against synthetic data
uv run brain-ingest --connector shopify --workspace sandbox --mock
```

`MockShopifyConnector` generates synthetic Indian beauty brand data (5k orders, 18 months history, COD 65%, RTO 22%, Diwali spike).

---

## 15. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Webhook-driven sync vs polling? | E3 | Phase 2. Webhooks for Shopify orders (instant); polling for everything else. |
| Multi-store Shopify (e.g., .com + .in)? | E3 | Multiple integrations rows per workspace. Aggregate at query time. |
| Should we sync Shopify Discount Codes? | E3 | Phase 2 — enables discount-code cohort segmentation. |
| CSV/manual import for non-Shopify brands? | E1 | Phase 4 if 3+ prospects request. |
| iceberg/parquet S3 archive instead of raw JSON? | E4 | Phase 4. JSON is fine until S3 cost crosses $500/mo. |
| Per-region MSK clusters? | E1 | Phase 4. One MSK per AWS region; MirrorMaker for cross-region replication. |
