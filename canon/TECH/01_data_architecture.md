# TECH/01 — Data Architecture (Postgres + ClickHouse)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E3 (Backend/Data) + E4 (Analytics/ML) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md)

This document defines:
- The OLTP / OLAP split (Postgres vs ClickHouse)
- Postgres schemas (Supabase) — workspaces, settings, recent canonical data
- ClickHouse schemas — time-series, aggregates, customer history
- Event-driven sync via CDC (Debezium) + Kafka
- Multi-tenancy enforcement in both stores
- Migration & seeding strategy
- Sharding & scale plan for 100k req/min

---

## 1. The Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WRITE PATH                                   │
└─────────────────────────────────────────────────────────────────────┘

External APIs                     ┌──────────────────────────────┐
(Shopify/Meta/                ───►│  ingestion-service           │
 Google/Shiprocket)               │  (Python)                    │
                                  └────────────┬─────────────────┘
                                               │
                  ┌────────────────────────────┼────────────────────┐
                  │                            │                    │
                  ▼                            ▼                    ▼
       ┌───────────────────┐       ┌──────────────────────┐    ┌──────────┐
       │ ClickHouse        │       │ Kafka                │    │ S3       │
       │ raw_events.*      │       │ integrations.*       │    │ raw      │
       │ (insert-only)     │       │ (canonical events)   │    │ payload  │
       └───────────────────┘       └──────────────────────┘    │ archive  │
                                              │                 └──────────┘
                                              │
                            ┌─────────────────┼──────────────────┐
                            │                 │                  │
                            ▼                 ▼                  ▼
                ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐
                │ analytics-       │ │ intelligence-    │ │ notifications│
                │ service          │ │ service          │ │ -service     │
                │                  │ │                  │ │              │
                │ Writes to        │ │ Reads, writes    │ │ Reads        │
                │ ClickHouse       │ │ to Postgres ai.* │ │              │
                │ derived tables   │ │                  │ │              │
                └──────────────────┘ └──────────────────┘ └──────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                          OLTP WRITE PATH                             │
└─────────────────────────────────────────────────────────────────────┘

Frontend ──► api-gateway ──► core-service ──► Postgres (Supabase)
                                                    │
                                                    │ (logical replication)
                                                    ▼
                                              Debezium on MSK Connect
                                                    │
                                                    ▼
                                              Kafka operations.* topics
                                                    │
                                                    ▼
                                              analytics-service ingests
                                              and projects to ClickHouse
                                              (for joined queries)


┌─────────────────────────────────────────────────────────────────────┐
│                           READ PATH                                  │
└─────────────────────────────────────────────────────────────────────┘

Frontend
  │
  ▼
api-gateway ──► core-service (workspace/user/settings reads) ──► Postgres + Redis
  │
  ▼
api-gateway ──► analytics-service (dashboards) ──► ClickHouse + Redis (hot cache)
  │
  ▼
api-gateway ──► intelligence-service (AI/forecasts) ──► Postgres ai.* + ClickHouse
```

### Why Split OLTP and OLAP

| Workload | Postgres | ClickHouse |
|----------|----------|------------|
| Workspace CRUD | ✓ | — |
| Cost setting writes | ✓ | — |
| Goal upserts | ✓ | — |
| Daily metric queries (1B+ rows) | ✗ (slow) | ✓ (sub-second) |
| Cohort heatmap | ✗ | ✓ |
| LTV curves | ✗ | ✓ |
| Customer state history | ✗ | ✓ |
| First Product Cascade | ✗ | ✓ |
| Calendar Report 90-day | ✗ | ✓ |
| Membership/auth lookups | ✓ | — |

Rule of thumb: **if you'd join, group, or aggregate large tables → ClickHouse. If you'd insert, update, or fetch a single row → Postgres.**

---

## 2. Postgres Layout (Supabase)

### Schema Namespaces

```
postgres (Supabase project: brain-prod)
├── public                            # Application primary
│   ├── workspaces                    # Tenant
│   ├── workspace_regions             # Regional adapter binding (TECH/04)
│   ├── users                         # (Supabase auth.users joined)
│   ├── workspace_members
│   ├── integrations
│   ├── campaigns                     # Recent campaign metadata (canonical)
│   ├── campaign_classifications
│   ├── cost_settings
│   ├── product_cogs
│   ├── products                      # Catalog (snapshot)
│   ├── customers_recent              # Last 90 days only; historical lives in ClickHouse
│   ├── orders_recent                 # Last 90 days only
│   ├── shipments_recent              # Last 90 days only
│   ├── metric_goals
│   ├── marketing_actions
│   ├── alert_rules
│   ├── in_app_notifications
│   ├── export_jobs
│   └── audit_log
│
├── ai                                # intelligence-service owns
│   ├── insights
│   ├── chat_conversations
│   ├── chat_messages
│   ├── embeddings (pgvector)
│   ├── forecasts
│   ├── forecast_accuracy
│   ├── anomalies
│   └── workspace_llm_budget
│
└── auth                              # Supabase-managed
    └── ...
```

### Why `*_recent` tables only

Historical data lives in ClickHouse. Postgres only mirrors the last ~90 days for:
- Fast lookup paths that need joins to settings (e.g., display "this customer's last 5 orders" with cost overlays)
- Webhook reconciliation
- New-data write target before async fan-out to ClickHouse

After 90 days, rows are moved to ClickHouse (via cleanup job) and deleted from Postgres. ClickHouse has them forever.

This keeps Postgres small (~50 GB at 50 brands) and fast.

### Core Tables

#### `workspaces`

```sql
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  brand_category TEXT,                          -- 'beauty', 'apparel', etc.

  -- Regional + currency (was India-hardcoded; now configurable)
  home_region TEXT NOT NULL DEFAULT 'IN',       -- ISO country code; 'IN', 'US', 'GB', 'AE'
  default_currency CHAR(3) NOT NULL DEFAULT 'INR',
  default_timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  fiscal_year_start_month SMALLINT DEFAULT 4,

  -- Reporting prefs
  founder_salary_monthly_minor BIGINT,

  -- Tier / plan
  tier TEXT NOT NULL DEFAULT 'starter',         -- 'starter', 'pro', 'enterprise'

  -- Multi-region
  aws_primary_region TEXT NOT NULL DEFAULT 'ap-south-1',

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_workspaces_slug ON workspaces(slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_workspaces_region ON workspaces(home_region) WHERE deleted_at IS NULL;
```

#### `workspace_members`

```sql
CREATE TABLE workspace_members (
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner','operator','analyst','agency','viewer')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);
```

#### `integrations`

```sql
CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  integration_type TEXT NOT NULL,               -- 'shopify','meta','google_ads','shiprocket','klaviyo'
  status TEXT NOT NULL DEFAULT 'connected',
  external_account_id TEXT,

  -- Tokens encrypted via AWS KMS envelope encryption
  -- We store an opaque key reference; actual key lives in Secrets Manager
  credential_secret_arn TEXT NOT NULL,

  config JSONB NOT NULL DEFAULT '{}',
  watermarks JSONB NOT NULL DEFAULT '{}',       -- per-resource sync watermarks

  last_sync_started_at TIMESTAMPTZ,
  last_sync_completed_at TIMESTAMPTZ,
  last_sync_error TEXT,
  backfill_completed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, integration_type, external_account_id)
);

CREATE INDEX idx_integrations_workspace ON integrations(workspace_id);
```

### Recent-Window Canonical Tables

These mirror ClickHouse's authoritative tables but only for the last 90 days.

```sql
CREATE TABLE orders_recent (
  id UUID PRIMARY KEY,                          -- same UUID across PG and CH
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  source_record_id TEXT NOT NULL,
  source_order_number TEXT,

  customer_id UUID,
  customer_orders_count INT,
  is_new_customer BOOLEAN,

  created_at TIMESTAMPTZ NOT NULL,

  -- Money in workspace currency, minor units (e.g., paise for INR, cents for USD)
  subtotal_minor BIGINT NOT NULL,
  discount_minor BIGINT NOT NULL DEFAULT 0,
  total_tax_minor BIGINT NOT NULL DEFAULT 0,
  total_shipping_minor BIGINT NOT NULL DEFAULT 0,
  total_minor BIGINT NOT NULL,
  net_revenue_minor BIGINT GENERATED ALWAYS AS (subtotal_minor - discount_minor - total_tax_minor) STORED,

  currency_code CHAR(3) NOT NULL,               -- multi-currency support
  fx_rate_to_workspace_currency NUMERIC(18,8) DEFAULT 1.0,

  -- Payment
  payment_method TEXT,
  is_cod BOOLEAN GENERATED ALWAYS AS (payment_method = 'cod') STORED,

  -- Status
  financial_status TEXT,
  fulfillment_status TEXT,
  is_rto BOOLEAN NOT NULL DEFAULT FALSE,

  -- Shipping (denormalized for fast filtering)
  ship_city TEXT,
  ship_state TEXT,
  ship_pincode TEXT,                            -- India; other regions store equivalent postal code here
  ship_country CHAR(2),

  -- Attribution
  referring_site TEXT,
  source_name TEXT,
  landing_site TEXT,

  -- For idempotent reprocessing
  raw_payload_hash BYTEA,

  created_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (workspace_id, source_record_id)
);

CREATE INDEX idx_orders_recent_workspace_created ON orders_recent(workspace_id, created_at DESC);
CREATE INDEX idx_orders_recent_workspace_customer ON orders_recent(workspace_id, customer_id);
CREATE INDEX idx_orders_recent_workspace_pincode ON orders_recent(workspace_id, ship_pincode);
```

`shipments_recent`, `customers_recent` follow the same pattern.

### Configuration Tables

`cost_settings`, `product_cogs`, `campaign_classifications`, `metric_goals`, `marketing_actions`, `alert_rules` — same as v1.0 schema (TECH/01 v1.0 §5). Now joined by the canonical fact tables that live primarily in ClickHouse.

### `ai.*` Schema

Same as v1.0 (TECH/01 v1.0 §7). `insights`, `chat_conversations`, `chat_messages`, `embeddings`, `forecasts`, `forecast_accuracy`, `anomalies`, `workspace_llm_budget`. Lives in Postgres because:
- Per-row updates (acknowledged_at, etc.) are frequent
- Reads are bounded (per workspace, recent N)
- pgvector for embeddings

---

## 3. ClickHouse Layout

ClickHouse Cloud (AWS region) or self-hosted via Altinity Operator on EKS. Either way, the schemas are identical.

### Cluster Topology

- **Database:** `brain_analytics`
- **Engine family:** `ReplicatedMergeTree` for replication; `Distributed` for sharding
- **Shards:** 3 initially (by `workspace_id` hash); scale to 6 at 50+ workspaces; 12 at 200+
- **Replicas:** 2 per shard (HA)
- **ZooKeeper:** ClickHouse Keeper (no external Zk)

### Raw Event Tables

Append-only mirror of incoming canonical events from Kafka.

```sql
CREATE TABLE brain_analytics.raw_orders_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  source_record_id String,
  source_integration String,                   -- 'shopify'
  event_type String,                           -- 'created', 'updated', 'cancelled', 'refunded'
  event_at DateTime64(3, 'UTC'),
  payload String CODEC(ZSTD(3)),               -- canonical JSON payload
  payload_hash FixedString(32),                -- SHA-256
  ingested_at DateTime64(3, 'UTC') DEFAULT now64()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/raw_orders', '{replica}')
PARTITION BY toYYYYMM(event_at)
ORDER BY (workspace_id, event_at, source_record_id)
SETTINGS index_granularity = 8192;

CREATE TABLE brain_analytics.raw_orders ON CLUSTER brain_cluster
AS brain_analytics.raw_orders_local
ENGINE = Distributed('brain_cluster', 'brain_analytics', 'raw_orders_local', cityHash64(workspace_id));
```

Pattern repeats for: `raw_customers`, `raw_products`, `raw_shipments`, `raw_shipment_events`, `raw_refunds`, `raw_ads_insights`, `raw_campaigns`.

### Canonical Fact Tables (Authoritative)

```sql
CREATE TABLE brain_analytics.orders_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  order_id UUID,                                -- canonical UUID; same as PG orders_recent.id
  source_record_id String,
  customer_id Nullable(UUID),
  customer_orders_count UInt32,
  is_new_customer UInt8,

  created_at DateTime64(3, 'UTC'),
  local_date Date MATERIALIZED toDate(created_at, 'Asia/Kolkata'),  -- per-workspace TZ via Mat View instead

  subtotal_minor Int64,
  discount_minor Int64,
  total_tax_minor Int64,
  total_shipping_minor Int64,
  total_minor Int64,
  net_revenue_minor Int64 MATERIALIZED subtotal_minor - discount_minor - total_tax_minor,

  currency_code FixedString(3),
  fx_rate_to_usd Decimal(18, 8),                -- for cross-region reporting
  fx_rate_to_workspace_currency Decimal(18, 8),

  payment_method LowCardinality(String),
  is_cod UInt8,

  financial_status LowCardinality(String),
  fulfillment_status LowCardinality(String),
  is_rto UInt8,
  rto_resolved_at Nullable(DateTime64(3, 'UTC')),

  ship_city LowCardinality(String),
  ship_state LowCardinality(String),
  ship_pincode String,
  ship_country FixedString(2),

  referring_site Nullable(String),
  source_name LowCardinality(Nullable(String)),

  updated_at DateTime64(3, 'UTC'),
  version UInt64                                -- for ReplacingMergeTree dedup
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/orders', '{replica}', version)
PARTITION BY toYYYYMM(created_at)
ORDER BY (workspace_id, created_at, order_id)
SETTINGS index_granularity = 8192;

CREATE TABLE brain_analytics.orders ON CLUSTER brain_cluster
AS brain_analytics.orders_local
ENGINE = Distributed('brain_cluster', 'brain_analytics', 'orders_local', cityHash64(workspace_id));
```

Why `ReplacingMergeTree` with `version`: events arrive multiple times (raw fetched repeatedly due to late-data window). ClickHouse de-duplicates by ordering key, keeping the highest version. Reads use `FINAL` modifier or merging queries.

Same pattern for `customers`, `products`, `line_items`, `refunds`, `shipments`, `shipment_events`, `campaigns`, `campaign_insights_daily`.

### Derived Aggregate Tables

#### `daily_metrics_local` — The Master Aggregate

```sql
CREATE TABLE brain_analytics.daily_metrics_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  date Date,
  metric_name LowCardinality(String),
  customer_type LowCardinality(Nullable(String)),    -- 'new', 'returning', NULL = all
  channel LowCardinality(Nullable(String)),          -- 'meta', 'google_ads', etc.
  campaign_classification LowCardinality(Nullable(String)),
  value Float64,
  source_version UInt32,
  computed_at DateTime64(3, 'UTC') DEFAULT now64()
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/daily_metrics', '{replica}', computed_at)
PARTITION BY toYYYYMM(date)
ORDER BY (workspace_id, metric_name, date, customer_type, channel, campaign_classification)
SETTINGS index_granularity = 8192;
```

This table is the primary read path for dashboards. Sub-100ms queries achievable for any (workspace, metric, date-range) lookup.

#### Materialized View: Incremental Daily Metrics

```sql
-- Refresh CM1 daily metric from orders + costs on insert
CREATE MATERIALIZED VIEW brain_analytics.mv_daily_revenue_net
TO brain_analytics.daily_metrics_local
AS SELECT
  workspace_id,
  toDate(created_at) AS date,
  'revenue_net_minor' AS metric_name,
  CAST(NULL, 'Nullable(String)') AS customer_type,
  CAST(NULL, 'Nullable(String)') AS channel,
  CAST(NULL, 'Nullable(String)') AS campaign_classification,
  CAST(sum(net_revenue_minor) AS Float64) AS value,
  1 AS source_version,
  now64() AS computed_at
FROM brain_analytics.orders_local
GROUP BY workspace_id, date;
```

Materialized views run on INSERT into the source table. They keep `daily_metrics_local` fresh in real-time for simple aggregates.

For complex metrics (MER, aMER, CM2 with multi-table joins), we use scheduled refresh jobs in analytics-service (see TECH/03).

#### `customer_states_local`

```sql
CREATE TABLE brain_analytics.customer_states_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  customer_id UUID,
  date Date,
  state LowCardinality(String),                 -- 'new','returning','reactivated','at_risk','churned'
  days_since_last_order Int32,
  lifetime_orders UInt32,
  lifetime_revenue_minor Int64
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/customer_states', '{replica}')
PARTITION BY toYYYYMM(date)
ORDER BY (workspace_id, customer_id, date);
```

Stored sparse: only on state change + monthly snapshots. Reconstruction query uses `argMax(state, date)` over previous rows.

#### `cohort_aggregates_local`, `first_product_attribution_local`, `customer_lifetime_value_local`, `pincode_reliability_local`

Same shape as v1.0 schemas, ported to `ReplicatedMergeTree` with `(workspace_id, ...)` ordering keys.

### LowCardinality Pattern

Note the heavy use of `LowCardinality(String)`. ClickHouse stores these as dictionary-encoded integers internally — 10–100x smaller and faster than plain `String` for repeated values like `metric_name`, `customer_type`, `channel`.

---

## 4. CDC (Change Data Capture): Postgres → ClickHouse

For tables that live in both stores (e.g., `orders_recent` ↔ `orders`), we use CDC.

### Architecture

```
Postgres (with logical replication slot)
    │
    │ WAL stream
    ▼
Debezium PostgresConnector (runs on MSK Connect)
    │
    │ Avro events
    ▼
Kafka topic: cdc.public.orders_recent.v1
    │
    ▼
ClickHouse Kafka engine consumer
    │
    │ Insert into orders_local (with version)
    ▼
ReplacingMergeTree dedups via version
```

### Debezium Connector Config

```json
{
  "name": "postgres-cdc-orders",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "supabase-host",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "${secrets:debezium-password}",
    "database.dbname": "postgres",
    "database.server.name": "brain-prod",
    "schema.include.list": "public",
    "table.include.list": "public.orders_recent,public.customers_recent,public.shipments_recent",
    "plugin.name": "pgoutput",
    "publication.name": "brain_cdc_pub",
    "slot.name": "brain_cdc_slot",
    "key.converter": "io.confluent.connect.avro.AvroConverter",
    "value.converter": "io.confluent.connect.avro.AvroConverter",
    "value.converter.schema.registry.url": "${glue-schema-registry-url}",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite"
  }
}
```

### ClickHouse Kafka Consumer

```sql
CREATE TABLE brain_analytics.cdc_orders_queue
(
  before String,
  after String,
  source String,
  op String,
  ts_ms UInt64
)
ENGINE = Kafka
SETTINGS
  kafka_broker_list = '${MSK_BOOTSTRAP_SERVERS}',
  kafka_topic_list = 'cdc.public.orders_recent.v1',
  kafka_group_name = 'clickhouse-cdc-orders',
  kafka_format = 'JSONEachRow',
  kafka_num_consumers = 4;

CREATE MATERIALIZED VIEW brain_analytics.mv_cdc_orders
TO brain_analytics.orders_local
AS SELECT
  JSONExtractString(after, 'workspace_id')::UUID AS workspace_id,
  JSONExtractString(after, 'id')::UUID AS order_id,
  JSONExtractString(after, 'source_record_id') AS source_record_id,
  -- ... extract all columns
  ts_ms AS version
FROM brain_analytics.cdc_orders_queue
WHERE op IN ('c', 'u');
```

### When NOT to CDC

For tables that originate entirely in ingestion-service (raw_*, campaign_insights_daily), the service writes **directly** to both Kafka and ClickHouse. No CDC loop. Postgres has no copy of these.

---

## 5. Multi-Tenancy Enforcement

### Postgres: Three Layers (Recap)

1. Application middleware (`workspaceProcedure`)
2. Prisma extension auto-injecting `workspace_id`
3. RLS policies on every workspace-scoped table

```sql
ALTER TABLE orders_recent ENABLE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON orders_recent
  USING (workspace_id = current_setting('app.workspace_id', true)::uuid)
  WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::uuid);
```

Service sets `SET LOCAL app.workspace_id = ?` at transaction start.

### ClickHouse: Two Layers

ClickHouse doesn't have Postgres-style RLS. We enforce via:

**Layer 1 — Ordering key:**
`ORDER BY (workspace_id, ...)` on every workspace-scoped table makes workspace-filtered queries O(log n).

**Layer 2 — Query gateway:**
All ClickHouse access goes through `pylibs/brain_clickhouse/`:

```python
# pylibs/brain_clickhouse/client.py

class ClickHouseClient:
    def query(self, sql: str, workspace_id: str, params: dict = None) -> list:
        if not self._has_workspace_filter(sql, workspace_id):
            raise QueryWithoutTenantFilter(f"Query missing workspace_id={workspace_id} filter")
        return self._raw_client.execute(sql, params or {})

    def _has_workspace_filter(self, sql: str, workspace_id: str) -> bool:
        # Either contains `workspace_id = '${workspace_id}'` literal,
        # or `:workspace_id` named param with matching value.
        # Conservative: reject queries that don't pattern-match.
        ...
```

The gateway is the **only** way to talk to ClickHouse. Direct `clickhouse_driver` use is forbidden via lint rule.

**Layer 3 (Phase 3, if needed) — Per-workspace databases:**
For enterprise tier with hard isolation requirements:

```sql
CREATE DATABASE brain_workspace_<uuid>;
CREATE USER ws_user_<uuid> IDENTIFIED ... ;
GRANT SELECT ON brain_workspace_<uuid>.* TO ws_user_<uuid>;
```

Each workspace's analytics-service pod uses a workspace-scoped CH user. Premature now; revisit at Phase 4.

---

## 6. Currency & Multi-Region

### Money Storage

All money is **minor units (integer)** in the order's transaction currency.

- ₹1.00 = 100 paise = `100`
- $1.00 = 100 cents = `100`
- £1.00 = 100 pence = `100`
- AED 1.00 = 100 fils = `100`

Plus `currency_code CHAR(3)` (`INR`, `USD`, `GBP`, `AED`, ...).

### FX Rates

```sql
CREATE TABLE fx_rates (
  from_currency CHAR(3) NOT NULL,
  to_currency CHAR(3) NOT NULL,
  rate_date DATE NOT NULL,
  rate NUMERIC(18, 8) NOT NULL,
  source TEXT NOT NULL,                         -- 'ecb', 'rbi', 'openexchangerates'
  PRIMARY KEY (from_currency, to_currency, rate_date)
);
```

Daily fetch from public FX API. For each order, we store:
- `currency_code` — the transaction currency
- `fx_rate_to_workspace_currency` — snapshot at order time (for stable reporting)
- `fx_rate_to_usd` — for cross-region benchmarking

Aggregates report in `workspace.default_currency`. Cross-workspace benchmarks normalize to USD.

### Workspace `home_region`

Stored as ISO country code: `IN`, `US`, `GB`, `AE`, ...

A region binds to:
- Default currency (e.g., `IN` → `INR`)
- Default timezone
- Region-adapter implementation (TECH/04)
- AWS region preference for data residency (Phase 4)

### Display Formatting

Frontend has currency-aware formatters:

```typescript
formatMoney(100000, 'INR') // → "₹1,000"  with Indian grouping
formatMoney(100000, 'USD') // → "$1,000.00"
formatMoney(1000000000, 'INR', 'compact') // → "₹100 Cr"
formatMoney(1000000000, 'USD', 'compact') // → "$10M"
```

Indian operators see lakh/crore; US operators see thousand/million. Lives in `packages/ui/lib/currency.ts`.

---

## 7. Time Zones

Every workspace has `default_timezone`. Daily aggregates are computed in workspace-local time.

```sql
-- ClickHouse query for "today" in workspace local time
SELECT sum(net_revenue_minor)
FROM orders
WHERE workspace_id = ?
  AND toDate(created_at, 'Asia/Kolkata') = today();
```

For multi-region performance, we store a `local_date` materialized column per workspace timezone — but only if we have ≥10 workspaces in that TZ; otherwise compute on the fly (still fast on ClickHouse).

---

## 8. Indexes & Performance

### Postgres

- Every workspace-scoped table: index leading with `workspace_id`
- Common patterns: `(workspace_id, created_at)`, `(workspace_id, customer_id)`, `(workspace_id, ship_pincode)`
- Partial indexes for status filters: `WHERE is_rto = true`

### ClickHouse

- Primary key (ordering key) `(workspace_id, date, ...)` — automatic
- Skip indices for high-cardinality filters:
  ```sql
  ALTER TABLE orders_local ADD INDEX idx_customer_id customer_id TYPE bloom_filter(0.01) GRANULARITY 4;
  ```
- Projections (Phase 3) for alternate sort orders without duplicating data:
  ```sql
  ALTER TABLE orders_local ADD PROJECTION by_pincode
  (SELECT * ORDER BY workspace_id, ship_pincode, created_at);
  ```

---

## 9. Backup & DR

### Postgres (Supabase)

- Automated daily snapshots, 30-day retention
- PITR with 7-day window
- Cross-region replication (Phase 4)

### ClickHouse Cloud

- Automated daily backups, 7-day retention default
- Point-in-time restore supported

### Kafka (MSK)

- Tiered storage to S3 — events retained forever
- Topic configs allow rewinding any consumer to any offset
- Replication factor 3 across 3 AZs

### S3

- Versioning enabled on critical buckets
- Lifecycle: move to S3 IA after 90 days; Glacier after 365 days for raw archives

### Recovery Procedure

1. Restore Postgres from Supabase snapshot (or PITR)
2. Restore ClickHouse from CH Cloud snapshot
3. Replay Kafka topics from S3 tier into ClickHouse for any gap

RTO: 4 hours. RPO: 1 hour (Phase 1); RPO: 5 minutes at Phase 4 with synchronous replication.

---

## 10. Migrations

### Postgres

- **Tool:** Prisma Migrate
- **Naming:** `YYYYMMDDHHMM__short_description.sql`
- **CI:** runs migrations against staging on every PR; production migrations gated by manual approval
- **Pattern:** expand → migrate → contract

### ClickHouse

- **Tool:** `clickhouse-migrations` (or homegrown via SQL files)
- **Pattern:** ON CLUSTER for replicated tables; idempotent via `IF NOT EXISTS`
- **Schema versioning:** every `daily_metrics` row has `source_version`. When metric computation changes, bump version; regenerate over the relevant date range.

```sql
-- Migration example
ALTER TABLE brain_analytics.orders_local ON CLUSTER brain_cluster
ADD COLUMN IF NOT EXISTS fx_rate_to_usd Decimal(18, 8) AFTER fx_rate_to_workspace_currency;
```

---

## 11. Data Retention

| Data | Retention | Storage |
|------|-----------|---------|
| `raw_*` (ClickHouse) | 5 years | ClickHouse + S3 archive |
| `*_recent` (Postgres) | 90 days | Postgres |
| Canonical (`orders`, `shipments`, ...) (ClickHouse) | Forever | ClickHouse |
| `daily_metrics` | Forever | ClickHouse |
| `customer_states` | Forever (sparse) | ClickHouse |
| `ai.chat_messages` | 1 year, then archive | Postgres → S3 |
| `ai.insights` | 2 years | Postgres |
| `audit_log` | 7 years | Postgres (cold partition after 1 year) |
| Soft-deleted workspaces | Hard-delete after 90 days | All stores |

---

## 12. Seed Data for Development

```bash
# tools/seed-demo.py
python tools/seed-demo.py \
  --workspace-name "Sandbox Beauty" \
  --region IN \
  --currency INR \
  --orders 5000 \
  --customers 3000 \
  --products 50 \
  --history-days 540 \
  --cod-share 0.65 \
  --rto-rate 0.22 \
  --festival-spikes diwali,navratri,holi
```

Generates synthetic Shopify/Meta/Google/Shiprocket data, populates Postgres + ClickHouse via the ingestion pipeline (not direct inserts — exercises the real code path).

---

## 13. Sharding Strategy (Path to Scale)

### ClickHouse Sharding

- Phase 0–2: 3 shards × 2 replicas (single workspace's data in single shard via `cityHash64(workspace_id)`)
- Phase 3: scale to 6 shards as data grows
- Phase 4 (100k req/min): 12 shards; consider hot-workspace dedicated shards for top 1% of customers

Adding a shard:
1. Add new shard to cluster
2. Rebalance via background move job (workspace-by-workspace; no downtime)
3. Update `Distributed` table routing

### Postgres Read Replicas

- Phase 1: 1 primary
- Phase 2: 1 primary + 1 read replica (analytics-service reads from replica)
- Phase 3: 1 primary + 2 replicas; ingestion-service uses dedicated replica for backfill reads

### Kafka Partition Strategy

- Most topics: 12 partitions, partitioned by `workspace_id` hash
- Workspace's events always in same partition → ordering guaranteed
- Add partitions when consumer lag exceeds 60s (rebalance is online)

### Connection Pooling

PgBouncer in transaction mode:
- Per-service connection pools (5–20 conns)
- PgBouncer sees ~880 client conns max; maintains ~200 backend conns to Postgres
- Connection pinning for transactions that need session state (rare)

---

## 14. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Supabase ceiling at 100k RPM? | E1 + E3 | Likely fine with Pro/Team tier + read replicas. Migrate to Aurora if Supabase becomes a bottleneck. |
| ClickHouse Cloud vs self-hosted? | E1 | Start with ClickHouse Cloud (operational simplicity); self-host if cost exceeds $5K/mo. |
| pgvector vs OpenSearch for embeddings? | E4 | pgvector for now (low volume, simple). OpenSearch when we need full-text + vector search combined. |
| `currency_code` storage — CHAR(3) or LowCardinality? | E3 | CHAR(3) in PG; LowCardinality(FixedString(3)) in CH. |
| When to introduce per-workspace ClickHouse DBs? | E4 | Phase 4, only for enterprise-tier customers needing hard isolation. |
| Cross-region read replicas — eager or lazy? | E1 | Phase 4. Lazy initially (5-min replication lag acceptable). |
| Real-time CDC vs micro-batch (1 min)? | E3 | Real-time (Debezium streaming). Latency p95 <2s. |
