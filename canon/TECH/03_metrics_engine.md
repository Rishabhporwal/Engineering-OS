# TECH/03 — Metrics Engine (analytics-service)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 (Analytics/ML) | **Reviewers:** E1, E3
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/01_data_architecture.md](01_data_architecture.md), [TECH/02_integrations.md](02_integrations.md), [TECH/12_cost_routing_compute.md](12_cost_routing_compute.md)

## 0. Formula Book — Authoritative Definitions (Per Brief Section 3)

**Every layer of Brain must use these definitions.** If two parts of the system calculate the same metric differently, the system is broken. This section is the single source of truth.

### 0.1 Revenue

| Term | Formula | Notes |
|------|---------|-------|
| **Gross Sales** | Σ line-item prices (pre-tax, pre-discount, pre-refund) | Marketing-only number; not used in P&L |
| **Net Sales** | Gross Sales − Discounts − Refunds | Still includes GST collected |
| **Net Revenue** | Net Sales − GST collected | **GST-exclusive.** First-class input to CM math. |
| **Delivered Revenue** | Net Revenue from orders with `status = delivered` (excludes RTO + cancelled) | Honest revenue for Indian D2C |

### 0.2 Contribution Margin Waterfall

Three CMs. Brain calculates all three on every order and aggregates daily.

> **Convention (canonical, per `business-requirements.md` §6.2 + `technical-requirements.md` §11.2):** non-marketing variable costs sit in **CM1**, marketing in **CM2**, fixed costs in **CM3**.

**Gross Product Margin = Net Revenue − COGS** — e.g. ₹846 net revenue − ₹250 COGS = ₹596 (70%). Reported as the pre-variable view; not a CM step.

**CM1 = Net Revenue − COGS − non-marketing variable costs** (order delivery + collection):
- Forward shipping · Packaging (primary + secondary) · Payment gateway fees · COD handling fees
- **RTO provisions** (RTO rate × reverse-logistics cost) — modelled, not actuals
- **Returns provisions** — modelled
- Per-order customer-support allocation
- **If CM1 is negative, no marketing budget can save the business.** Brain flags immediately.

**CM2 = CM1 − Marketing Spend** (paid media + influencer + affiliate + lifecycle message cost):
- **CM2 is the honest number.** If CM2 < 0, scale makes the business worse.
- Most early-stage Indian D2C brands underestimate CM2 by 15–25 pp (RTO + returns systematically underestimated).
- First-order CM2 may be negative (it carries acquisition cost); acceptable **only if 90-day repeat behaviour pays it back**. Brain alerts if CM2 stays negative 90 days with no LTV recovery curve.

**CM3 = CM2 − allocated Fixed Costs** (salaries, agency, rent, software, warehouse overhead):
- Operating Profit = CM3 − founder salary / financing / one-offs (when enabled).

### 0.3 Marketing Efficiency

| Metric | Formula |
|--------|---------|
| **MER** (Marketing Efficiency Ratio) | Total Net Revenue ÷ Total Marketing Spend (blended; all channels) |
| **aMER** (Acquisition MER) | New Customer Net Revenue ÷ New Customer Acquisition Spend |
| **ROAS** (per channel) | Channel attributed revenue ÷ Channel spend |
| **CAC** | Total Marketing Spend ÷ New Customers Acquired (**delivered orders only**, not orders placed) |
| **Blended CAC** | All-customers version; reported separately |
| **aCAC** (all-in CAC) | CAC + allocated salaries; only when running it explicitly |

### 0.4 LTV & Cohort (Mathematical Methods, Non-Negotiable)

| Metric | Method | Why |
|--------|--------|-----|
| **LTV** | **BG/NBD + Gamma-Gamma** models | Per brief Section 3.4; naive averages are systematically wrong for repeat-skewed distributions |
| **LTV horizons** | 30d, 60d, 90d, 180d, 365d per acquisition cohort | All using **CM2 contribution per order, not Gross Sales** |
| **Cohort retention curves** | **Kaplan-Meier survival analysis** | Per brief Section 3.4 |
| **Repeat rate** | % of customers with ≥2 orders in LTV window | |
| **Repeat purchase rate** | Total repeat orders ÷ total orders | Distinct from repeat rate |

### 0.5 RTO & COD-Specific (India)

RTO is the second-largest cost line in Indian D2C after COGS. Brain treats it as a first-class P&L line and a feature in every model.

| Metric | Formula |
|--------|---------|
| **RTO Rate** | Orders Returned to Origin ÷ Orders Shipped |
| **RTO Cost per Order** | Forward shipping + Reverse logistics + Restocking labour + Inventory write-down provision |
| **COD Conversion Rate** | COD Orders Delivered ÷ COD Orders Placed |
| **Prepaid Conversion Rate** | Prepaid Orders Delivered ÷ Prepaid Orders Placed |
| **COD vs Prepaid Mix** | Tracked at SKU, channel, pincode, and AOV level |

### 0.6 Cost Inclusion Rules (Non-Negotiable)

**Included in CM1 (and carried into CM2)** — order delivery + collection:
- COGS (landed cost: product + freight-in + customs + per-unit warehousing)
- Forward shipping · Packaging (primary + secondary) · Payment gateway fees · COD handling fees
- RTO provisions (modelled) · Returns provisions (modelled) · Per-order CS allocation

**Subtracted at CM2:** Marketing spend (paid media + influencer + affiliate + lifecycle message cost).

**Subtracted at CM3 (fixed / opex):** Salaries, tooling, rent, agency, warehouse overhead.

**Never a cost:** Tax to government (CGST/SGST/IGST flow through net revenue, not cost).

### 0.7 Discount / Refund / Tax Handling

| Concern | Rule |
|---------|------|
| **Discount** | Applied at line-item level **before** GST calculation. Brain never reports CM2 on pre-discount price. |
| **Refund** | Reduces Net Sales + removes contribution from original order's CM. Refund processing fees → opex. |
| **GST** | Stripped from Gross Sales at the first calculation step. Every downstream metric is GST-exclusive. |
| **Shipping charged to customer** | Treated as revenue, not cost offset. Shipping paid to logistics partner is the actual cost. |
| **Ad spend GST** | 18% input GST credit assumed **only** if brand has registered for it. Default: no credit. |

### 0.8 Statistical Methods Used Across Metrics (Per Cost-Routing Principle)

All paradigm-2 (ML). Listed here so the metrics engine is honest about what's a model vs an SQL aggregate.

| Concern | Method | Library |
|---------|--------|---------|
| Creative fatigue detection | **EWMA on CTR / CPM** | numpy |
| LTV prediction (purchase + monetary) | **BG/NBD + Gamma-Gamma** | `PyMC-Marketing` (`lifetimes` is archived — TECH/00 §2.6) |
| Cohort retention curves | **Kaplan-Meier survival** | `lifelines` |
| RTO risk per order | **XGBoost** on pincode × courier × AOV × COD × time-of-day | xgboost |
| RTO pincode clustering | **DBSCAN** on (pincode, RTO rate, volume) | scikit-learn |
| Demand forecasting | **Prophet** (multivariate with festival regressors) | prophet |
| Spend → aMER response curve | **Isotonic regression** | scikit-learn |
| Brand-state similarity | **pgvector cosine similarity** on Brand Fingerprint vector | pgvector |
| Anomaly detection on CM2 | EWMA + 3σ + DBSCAN outlier flagging | numpy + sklearn |

Every method above costs ~$0.001/inference or less. The frontier LLM (Claude Sonnet) only enters at the Morning Brief synthesis boundary where these results need to become human-readable narrative.

---

This document specifies:
- analytics-service architecture
- Metric registry (TS + Python mirrors)
- ClickHouse materialization strategies
- Per-metric computation specifications (MER/aMER, Waterfall, NAC, First Product Cascade)
- gRPC query API surface
- Caching layers
- Performance targets at 100k req/min

This is the single most important service in Brain.

---

## 1. analytics-service Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       analytics-service (Python)                     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ gRPC Server (FastAPI + grpcio)                                  ││
│  │  • GetDailyMetrics                                              ││
│  │  • GetCalendarReport                                            ││
│  │  • GetWaterfall                                                 ││
│  │  • GetFirstProductCascade                                       ││
│  │  • GetCohortHeatmap                                             ││
│  │  • GetLifecycleReport                                           ││
│  │  • DrillDown                                                    ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Query Layer                                                     ││
│  │  • Redis cache check (60s TTL)                                  ││
│  │  • ClickHouse query gateway (workspace_id enforced)             ││
│  │  • Result shaping                                               ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ ClickHouse Cluster (read replicas; analytics workload)          ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Materialization Workers (Kafka consumers)                       ││
│  │  • Orders consumer → updates orders + costs                     ││
│  │  • Shipments consumer → updates shipments + rto status          ││
│  │  • Ads consumer → updates campaign_insights                     ││
│  │  • CDC settings consumer → invalidates affected aggregates      ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Scheduled Jobs (EventBridge → SQS → service)                    ││
│  │  • Nightly: customer_states, churn_thresholds, first_product   ││
│  │  • Nightly: regional_metrics (pincode_reliability, etc.)        ││
│  │  • Hourly: daily_metrics rollup for today                       ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Scaling

- gRPC server pods: 3–20, HPA on RPS + CPU
- Consumer pods: scale with partition count
- Job worker pods: SQS-driven; up to 30 during nightly windows

---

## 2. Metric Registry

Single source of truth for every metric Brain knows about. Lives in `packages/lib-metrics/` (TS) and `pylibs/brain_metrics/` (Python). CI enforces parity.

### Schema

```typescript
// packages/lib-metrics/src/registry.ts
export type MetricUnit = 'currency_minor' | 'count' | 'ratio' | 'percentage' | 'days';
export type MetricDirection = 'higher_is_better' | 'lower_is_better' | 'neutral';
export type MetricCadence = 'realtime' | 'minute' | 'hourly' | 'daily' | 'weekly';

export interface MetricDefinition {
  name: string;
  displayName: string;
  unit: MetricUnit;
  direction: MetricDirection;
  cadence: MetricCadence;
  supportsBreakdowns: Array<'customer_type' | 'channel' | 'campaign_classification' | 'region'>;
  category: 'revenue' | 'margin' | 'marketing' | 'customer' | 'regional' | 'inventory';
  description: string;
  formula: string;
  derivedFrom: string[];
  // Multi-currency: this metric's value is always in the workspace's reporting currency
  isCurrency: boolean;
}

export const METRICS: Record<string, MetricDefinition> = {
  revenue_net_minor: { /* ... */ },
  mer: { /* ... */ },
  amer: { /* ... */ },
  // ...
};
```

### Cross-Language Sync

```bash
# tools/generate-metrics-registry.sh
# Generates Python from TS registry to ensure parity
node packages/lib-metrics/scripts/export-to-python.js > pylibs/brain_metrics/registry.py
```

CI check: diff TS → Python; fail PR on mismatch.

---

## 3. Two Computation Paths

**Path A — Pre-Materialized:**
ClickHouse materialized views + scheduled refreshes maintain `daily_metrics` in real-time. API just reads. Sub-100ms p95.

**Path B — Live Query:**
For user filters that can't be pre-aggregated (e.g., "CM2 for pincode 110001 last month"), analytics-service runs ClickHouse query on demand. Target p95 <500ms.

**Decision rule:**
- Default dashboard view (no filters)? Path A.
- Date-range only? Path A.
- Standard breakdowns (customer_type, channel, campaign_classification)? Path A — we pre-materialize these.
- Arbitrary dimension filters? Path B.

---

## 4. Materialization Strategy

### Real-Time via ClickHouse Materialized Views

For simple aggregates that don't require joins, MVs run on every INSERT:

```sql
-- Refresh on every insert into orders_local
CREATE MATERIALIZED VIEW brain_analytics.mv_daily_revenue_all
TO brain_analytics.daily_metrics_local
AS SELECT
  workspace_id,
  toDate(created_at) AS date,
  'revenue_net_minor' AS metric_name,
  CAST(NULL, 'Nullable(String)') AS customer_type,
  CAST(NULL, 'Nullable(String)') AS channel,
  CAST(NULL, 'Nullable(String)') AS campaign_classification,
  toFloat64(sum(net_revenue_minor)) AS value,
  1 AS source_version,
  now64() AS computed_at
FROM brain_analytics.orders_local
WHERE NOT is_rto                                 -- exclude RTO orders from revenue
GROUP BY workspace_id, date;
```

Similar MVs for `revenue_net_minor.customer_type=new`, `revenue_net_minor.customer_type=returning`, `orders_count`, `new_customers_count`, `ad_spend_minor`, etc.

Each MV is independent; failures in one don't affect others. The `daily_metrics_local` table uses `ReplacingMergeTree(computed_at)` so the latest value wins.

### Scheduled Rollups (for Complex Metrics)

Metrics that involve joins or external data (e.g., `mer`, `cm1_minor`, `cm2_minor`) run as scheduled Python jobs:

```python
# apps/analytics-service/src/jobs/daily_metrics_rollup.py

async def rollup_daily_metrics(workspace_id: str, date: datetime.date):
    """Computes derived metrics and UPSERTs to daily_metrics_local."""
    ch = ClickHouseClient()

    # 1. Read base aggregates already in daily_metrics from MVs
    revenue = await ch.query("""
        SELECT sum(value) FROM daily_metrics_local FINAL
        WHERE workspace_id = :ws AND date = :d AND metric_name = 'revenue_net_minor'
          AND customer_type IS NULL AND channel IS NULL AND campaign_classification IS NULL
    """, workspace_id=workspace_id, params={'ws': workspace_id, 'd': date})

    ad_spend = await ch.query("""
        SELECT sum(value) FROM daily_metrics_local FINAL
        WHERE workspace_id = :ws AND date = :d AND metric_name = 'ad_spend_minor'
          AND channel IS NULL AND campaign_classification IS NULL
    """, ...)

    # 2. Derive
    mer = revenue / ad_spend if ad_spend else 0

    # 3. UPSERT
    await ch.insert('daily_metrics_local', [{
        'workspace_id': workspace_id,
        'date': date,
        'metric_name': 'mer',
        'customer_type': None, 'channel': None, 'campaign_classification': None,
        'value': mer,
        'source_version': CURRENT_METRIC_VERSION,
        'computed_at': datetime.utcnow(),
    }])

    # ... and so on for cm1, cm2, cm3, cac, aov, etc.
```

### Refresh Cadence

| Tier | Cadence | Driver | Examples |
|------|---------|--------|----------|
| Real-time-ish | On Kafka event | MVs + consumers | Today's revenue, orders, spend |
| Hourly | EventBridge cron | rollup job | Today's MER, aMER, CAC |
| Nightly 03:00 IST | EventBridge | nightly jobs | Yesterday's full daily_metrics, cohorts, LTV |
| Nightly 04:00 IST | EventBridge | nightly jobs | customer_states, first_product_attribution |
| Weekly Sun 03:30 IST | EventBridge | weekly jobs | Churn threshold P40/P80 recalc |

After every rollup, publish `analytics.metrics.daily_materialized.v1` event. Downstream (intelligence-service, notifications-service) react.

---

## 5. Path A Reads (Hot Path)

### Read Flow

```
api-gateway gRPC call
    │
    ▼
analytics-service: GetDailyMetrics(workspace, dateRange, metrics)
    │
    ▼
Redis cache check (key = SHA-256 of request)
    │
    │ cache miss
    ▼
ClickHouse query:
  SELECT date, metric_name, customer_type, channel, value
  FROM brain_analytics.daily_metrics FINAL
  WHERE workspace_id = ?
    AND metric_name IN (?, ?, ?)
    AND date BETWEEN ? AND ?
  ORDER BY date, metric_name
    │
    ▼
Cache result (TTL 60s) and return
```

### Query Helper

```python
# apps/analytics-service/src/queries/daily_metrics.py

async def get_daily_metrics(
    workspace_id: str,
    date_from: date,
    date_to: date,
    metric_names: list[str],
    customer_type: str | None = None,
    channel: str | None = None,
    campaign_classification: str | None = None,
) -> list[DailyMetric]:
    cache_key = _cache_key('dm', workspace_id, date_from, date_to, metric_names, customer_type, channel, campaign_classification)
    if cached := await redis.get(cache_key):
        return deserialize(cached)

    sql = """
    SELECT
      date,
      metric_name,
      customer_type,
      channel,
      campaign_classification,
      value
    FROM brain_analytics.daily_metrics FINAL
    WHERE workspace_id = :workspace_id
      AND metric_name IN :metric_names
      AND date BETWEEN :date_from AND :date_to
      AND (:customer_type IS NULL OR customer_type = :customer_type OR customer_type IS NULL)
      AND (:channel IS NULL OR channel = :channel OR channel IS NULL)
      AND (:campaign_classification IS NULL OR campaign_classification = :campaign_classification OR campaign_classification IS NULL)
    ORDER BY date, metric_name
    """
    rows = await ch.query(sql, workspace_id=workspace_id, params={...})
    results = [DailyMetric(**r) for r in rows]
    await redis.setex(cache_key, 60, serialize(results))
    return results
```

`FINAL` modifier ensures we always read the latest version after `ReplacingMergeTree` dedup.

---

## 6. MER / aMER

### Materialized

```python
# Hourly rollup
async def compute_mer(workspace_id: str, date: date):
    revenue = await get_metric(workspace_id, date, 'revenue_net_minor', customer_type=None)
    spend = await get_metric(workspace_id, date, 'ad_spend_minor', channel=None, campaign_classification=None)
    mer = revenue / spend if spend > 0 else 0
    await upsert_metric(workspace_id, date, 'mer', mer)

async def compute_amer(workspace_id: str, date: date):
    new_rev = await get_metric(workspace_id, date, 'revenue_net_minor', customer_type='new')
    acq_spend = await get_metric(workspace_id, date, 'ad_spend_minor', campaign_classification='acquisition')
    amer = new_rev / acq_spend if acq_spend > 0 else 0
    await upsert_metric(workspace_id, date, 'amer', amer)
```

### Unclassified Spend Disclosure

```python
async def get_amer_with_quality(workspace_id, date):
    amer = await get_metric(workspace_id, date, 'amer')
    total_spend = await get_metric(workspace_id, date, 'ad_spend_minor')
    unclass_spend = await get_metric(workspace_id, date, 'ad_spend_minor', campaign_classification='unclassified')
    return {
        'value': amer,
        'unclassified_spend_share': unclass_spend / total_spend if total_spend else 0,
    }
```

---

## 7. CM Waterfall (Path B — On-Demand)

Customer-type filter creates too many combinations to materialize. Run live.

```python
async def get_waterfall(workspace_id, date_from, date_to, customer_filter='all'):
    sql = """
    WITH
      orders_filtered AS (
        SELECT *
        FROM brain_analytics.orders FINAL
        WHERE workspace_id = :ws
          AND created_at BETWEEN :from AND :to
          AND ({customer_pred})
      ),
      order_costs AS (
        SELECT *
        FROM brain_analytics.order_costs
        WHERE workspace_id = :ws
          AND order_id IN (SELECT order_id FROM orders_filtered)
      )
    SELECT
      sum(o.subtotal_minor) AS gross_sales,
      sum(o.discount_minor) AS discounts,
      sum(o.total_tax_minor) AS gst,
      sum(o.total_shipping_minor) AS customer_paid_shipping,
      -- refunds joined separately
      sumIf(c.amount_minor, c.cost_type = 'cogs') AS cogs,
      sumIf(c.amount_minor, c.cost_type = 'shipping_forward') AS shipping_outbound,
      sumIf(c.amount_minor, c.cost_type = 'packaging') AS packaging,
      sumIf(c.amount_minor, c.cost_type = 'payment_gateway') AS payment_gateway,
      sumIf(c.amount_minor, c.cost_type = 'cod_handling') AS cod_handling,
      sumIf(c.amount_minor, c.cost_type = 'rto_cost') AS rto_cost
    FROM orders_filtered o
    LEFT JOIN order_costs c ON c.order_id = o.order_id
    """

    customer_pred = {
        'all': 'TRUE',
        'new': 'o.is_new_customer = 1',
        'returning': 'o.is_new_customer = 0',
    }[customer_filter]
    sql = sql.replace('{customer_pred}', customer_pred)

    base = await ch.query(sql, ws=workspace_id, from_=date_from, to=date_to)

    # Refunds + ad spend + fixed costs joined separately
    # ... build the full waterfall
    return Waterfall(steps=[...], summary={...})
```

### `order_costs` Table

A second canonical CH table:

```sql
CREATE TABLE brain_analytics.order_costs_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  order_id UUID,
  cost_type LowCardinality(String),     -- 'cogs', 'shipping_forward', 'packaging', etc.
  amount_minor Int64,
  computed_at DateTime64(3, 'UTC')
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/order_costs', '{replica}', computed_at)
ORDER BY (workspace_id, order_id, cost_type);
```

Populated by analytics-service consumer of `integrations.orders.v1` — for each order, compute every cost component using effective `cost_settings` at order time and write to `order_costs_local`.

---

## 8. Net Active Customer Lifecycle

### Threshold Recalculation (Weekly)

```python
async def recalculate_churn_thresholds(workspace_id: str):
    gaps = await ch.query("""
        SELECT
          (toUnixTimestamp(created_at) - toUnixTimestamp(prev_created_at)) / 86400 AS gap_days
        FROM (
          SELECT
            customer_id, created_at,
            lagInFrame(created_at) OVER (PARTITION BY customer_id ORDER BY created_at) AS prev_created_at
          FROM brain_analytics.orders FINAL
          WHERE workspace_id = :ws AND NOT is_rto
        )
        WHERE prev_created_at IS NOT NULL
    """, ws=workspace_id)

    if len(gaps) < 50:
        p40, p80 = 60, 180   # defaults
    else:
        p40 = int(np.percentile([g['gap_days'] for g in gaps], 40))
        p80 = int(np.percentile([g['gap_days'] for g in gaps], 80))

    await ch.insert('churn_thresholds_local', [{
        'workspace_id': workspace_id,
        'at_risk_threshold_days': p40,
        'churned_threshold_days': p80,
        'sample_size': len(gaps),
        'computed_at': datetime.utcnow(),
    }])
```

### Daily State Assignment

```python
async def assign_customer_states(workspace_id: str, as_of: date):
    thresholds = await get_churn_thresholds(workspace_id)
    p40, p80 = thresholds.at_risk, thresholds.churned

    # Compute state for every customer this workspace has
    # ClickHouse handles the heavy lifting
    sql = """
    INSERT INTO brain_analytics.customer_states_local
    SELECT
      :ws AS workspace_id,
      customer_id,
      :as_of AS date,
      CASE
        WHEN toDate(last_order_at) = :as_of AND lifetime_orders = 1 THEN 'new'
        WHEN toDate(last_order_at) = :as_of AND prev_state = 'churned' THEN 'reactivated'
        WHEN toDate(last_order_at) = :as_of THEN 'returning'
        WHEN dateDiff('day', last_order_at, :as_of) <= :p40 THEN 'returning'
        WHEN dateDiff('day', last_order_at, :as_of) <= :p80 THEN 'at_risk'
        ELSE 'churned'
      END AS state,
      dateDiff('day', last_order_at, :as_of) AS days_since_last_order,
      lifetime_orders,
      lifetime_revenue_minor
    FROM (
      SELECT
        customer_id,
        max(created_at) AS last_order_at,
        count(*) AS lifetime_orders,
        sum(net_revenue_minor) AS lifetime_revenue_minor,
        -- prev state
        argMax(state, date) AS prev_state
      FROM brain_analytics.orders FINAL
      LEFT JOIN brain_analytics.customer_states_local USING (workspace_id, customer_id)
      WHERE workspace_id = :ws AND NOT is_rto
      GROUP BY customer_id
    )
    """
    await ch.execute(sql, ws=workspace_id, as_of=as_of, p40=p40, p80=p80)
```

State changes published to Kafka:

```python
# Detect state changes and emit events
async def emit_state_changes(workspace_id, as_of):
    changes = await ch.query("""
        SELECT customer_id, prev_state, new_state
        FROM (...)
    """)
    for change in changes:
        await kafka_producer.emit('analytics.customer_state.changed.v1', {
            'workspace_id': workspace_id,
            'customer_id': change.customer_id,
            'previous_state': change.prev_state,
            'new_state': change.new_state,
            'changed_at': as_of.isoformat(),
        })
```

### Report Query

```python
async def get_lifecycle_report(workspace_id, date_from, date_to, granularity='month'):
    # ClickHouse handles state distribution efficiently
    sql = """
    SELECT
      toStartOfMonth(date) AS period,
      countIf(state = 'new') AS new,
      countIf(state = 'returning') AS returning,
      countIf(state = 'reactivated') AS reactivated,
      countIf(state = 'at_risk') AS at_risk,
      countIf(state = 'churned') AS churned
    FROM brain_analytics.customer_states FINAL
    WHERE workspace_id = :ws
      AND date BETWEEN :from AND :to
    GROUP BY period
    ORDER BY period
    """
    return await ch.query(sql, ws=workspace_id, from_=date_from, to=date_to)
```

---

## 9. First Product → Repeat Purchase Cascade

### Attribution Materialization (Nightly)

```sql
INSERT INTO brain_analytics.first_product_attribution_local
SELECT
  workspace_id,
  customer_id,
  argMin(order_id, created_at) AS first_order_id,
  min(created_at) AS first_order_at,
  argMin(first_product_id, created_at) AS first_product_id,
  argMin(first_product_title, created_at) AS first_product_title
FROM (
  SELECT
    o.workspace_id,
    o.customer_id,
    o.order_id,
    o.created_at,
    -- First line item per order
    argMin(li.product_id, li.line_item_id) AS first_product_id,
    argMin(li.title, li.line_item_id) AS first_product_title
  FROM brain_analytics.orders o FINAL
  JOIN brain_analytics.line_items li FINAL USING (workspace_id, order_id)
  WHERE o.workspace_id = :ws AND NOT o.is_rto
  GROUP BY o.workspace_id, o.customer_id, o.order_id, o.created_at
)
GROUP BY workspace_id, customer_id;
```

### Cascade Query

```sql
SELECT
  fpa.first_product_id,
  fpa.first_product_title,
  count(DISTINCT fpa.customer_id) AS first_order_customers,
  countDistinctIf(fpa.customer_id, lifetime_orders >= 2) AS customers_2nd,
  countDistinctIf(fpa.customer_id, lifetime_orders >= 3) AS customers_3rd,
  countDistinctIf(fpa.customer_id, lifetime_orders >= 4) AS customers_4th_plus,
  round(100.0 * countDistinctIf(fpa.customer_id, lifetime_orders >= 2) / count(DISTINCT fpa.customer_id), 1) AS second_order_pct,
  -- etc.
  round(sum(lifetime_revenue_minor) / count(DISTINCT fpa.customer_id), 0) AS avg_ltv_minor
FROM brain_analytics.first_product_attribution fpa FINAL
JOIN (
  SELECT
    workspace_id, customer_id,
    count(*) AS lifetime_orders,
    sum(net_revenue_minor) AS lifetime_revenue_minor
  FROM brain_analytics.orders FINAL
  WHERE workspace_id = :ws AND NOT is_rto
  GROUP BY workspace_id, customer_id
) customer_stats USING (workspace_id, customer_id)
WHERE fpa.workspace_id = :ws
  AND fpa.first_order_at BETWEEN :from AND :to
GROUP BY fpa.first_product_id, fpa.first_product_title
HAVING first_order_customers >= 10
ORDER BY first_order_customers DESC;
```

ClickHouse handles this with ease — typical query <500ms even with millions of orders.

---

## 10. Cohort Heatmap

```sql
-- Cohort revenue by acquisition month × age in months
SELECT
  toStartOfMonth(first_order_at) AS cohort_month,
  dateDiff('month', toStartOfMonth(first_order_at), toStartOfMonth(order_created_at)) AS age_months,
  count(DISTINCT customer_id) AS active_customers,
  sum(net_revenue_minor) AS revenue,
  sum(net_revenue_minor) / count(DISTINCT customer_id) AS avg_revenue_per_customer
FROM (
  SELECT
    o.workspace_id,
    o.customer_id,
    o.created_at AS order_created_at,
    o.net_revenue_minor,
    -- first order for this customer
    minIf(o2.created_at, TRUE) OVER (PARTITION BY o.customer_id) AS first_order_at
  FROM brain_analytics.orders o FINAL
  WHERE o.workspace_id = :ws AND NOT o.is_rto
)
WHERE first_order_at >= :cohort_start
GROUP BY cohort_month, age_months
ORDER BY cohort_month, age_months;
```

For very large workspaces, we materialize `cohort_aggregates_local` nightly with this query frozen, so reads are <100ms.

---

## 11. Calendar Report

```sql
-- One row per day with all metrics + marketing actions
SELECT
  d AS date,
  -- Pivot daily_metrics
  maxIf(value, metric_name = 'cm3_minor' AND customer_type IS NULL) AS cm3,
  maxIf(value, metric_name = 'revenue_net_minor' AND customer_type IS NULL) AS revenue,
  maxIf(value, metric_name = 'mer') AS mer,
  maxIf(value, metric_name = 'amer') AS amer,
  maxIf(value, metric_name = 'cac_blended_minor') AS cac,
  maxIf(value, metric_name = 'new_customers_count') AS new_customers,
  maxIf(value, metric_name = 'ad_spend_minor' AND channel = 'meta' AND campaign_classification IS NULL) AS meta_spend,
  maxIf(value, metric_name = 'ad_spend_minor' AND channel = 'google_ads' AND campaign_classification IS NULL) AS google_spend
FROM (
  SELECT arrayJoin(arrayMap(x -> toDate(toUnixTimestamp(:from) + x * 86400), range(toUInt32(dateDiff('day', :from, :to) + 1)))) AS d
)
LEFT JOIN brain_analytics.daily_metrics FINAL
  ON workspace_id = :ws AND date = d
GROUP BY d
ORDER BY d DESC
```

Marketing actions joined from Postgres (small table; sub-ms):

```python
async def get_calendar_report(workspace_id, date_from, date_to):
    # 1. ClickHouse for metrics
    metrics = await ch.query(calendar_metrics_sql, ws=workspace_id, from_=date_from, to=date_to)
    # 2. Postgres for actions
    actions = await pg.query(
        "SELECT action_date, action_type, action_name FROM marketing_actions "
        "WHERE workspace_id = $1 AND action_date BETWEEN $2 AND $3",
        workspace_id, date_from, date_to
    )
    # 3. Postgres for goals
    goals = await pg.query(
        "SELECT metric_name, period_type, period_start, goal_value, goal_type FROM metric_goals "
        "WHERE workspace_id = $1 AND period_start BETWEEN $2 AND $3",
        workspace_id, date_from, date_to
    )
    return assemble_calendar(metrics, actions, goals)
```

---

## 12. Drill-Down

Every metric on every dashboard is drillable to the underlying rows.

```python
async def drill_down(workspace_id, metric_name, date_range, breakdown_filters, page=1):
    """For a metric on a given date, return the underlying rows."""
    if metric_name in ('revenue_net_minor', 'orders_count', 'aov_minor', 'cm1_minor'):
        return await drill_orders(workspace_id, date_range, breakdown_filters, page)
    elif metric_name in ('ad_spend_minor', 'mer', 'amer'):
        return await drill_campaigns(workspace_id, date_range, breakdown_filters, page)
    elif metric_name in ('rto_count', 'rto_cost_minor'):
        return await drill_shipments(workspace_id, date_range, breakdown_filters, page)
    # ... etc.
```

Each drill query returns sample rows + a count for pagination.

---

## 13. gRPC API Surface

```proto
// protos/analytics/metrics.proto
syntax = "proto3";

package brain.analytics.v1;
import "google/protobuf/timestamp.proto";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc GetCalendarReport(GetCalendarReportRequest) returns (CalendarReportResponse);
  rpc GetWaterfall(WaterfallRequest) returns (WaterfallResponse);
  rpc GetFirstProductCascade(FirstProductCascadeRequest) returns (FirstProductCascadeResponse);
  rpc GetCohortHeatmap(CohortHeatmapRequest) returns (CohortHeatmapResponse);
  rpc GetLifecycleReport(LifecycleReportRequest) returns (LifecycleReportResponse);
  rpc GetProductsTable(ProductsTableRequest) returns (ProductsTableResponse);
  rpc GetLTVCurves(LTVRequest) returns (LTVResponse);
  rpc DrillDown(DrillDownRequest) returns (DrillDownResponse);
}

message GetDailyMetricsRequest {
  string workspace_id = 1;
  google.protobuf.Timestamp date_from = 2;
  google.protobuf.Timestamp date_to = 3;
  repeated string metric_names = 4;
  optional string customer_type = 5;
  optional string channel = 6;
  optional string campaign_classification = 7;
}

message DailyMetric {
  google.protobuf.Timestamp date = 1;
  string metric_name = 2;
  double value = 3;
  optional string customer_type = 4;
  optional string channel = 5;
  optional string campaign_classification = 6;
}

message DailyMetricsResponse {
  repeated DailyMetric metrics = 1;
}
```

All RPCs require `workspace_id`. Server-side middleware rejects requests where the gRPC metadata `workspace_id` doesn't match the request `workspace_id`.

---

## 14. Caching Strategy

### Three Layers

**L1 — In-Process LRU (per pod):**
Tiny TTL (5s). For hottest queries (e.g., "today's revenue"). Avoids the Redis hop.

**L2 — Redis (cluster):**
60s TTL on standard metric queries. ~99% hit rate at steady state.

**L3 — ClickHouse Query Result Cache:**
ClickHouse-native query cache for identical queries. Set `use_query_cache=true` per session.

### Cache Invalidation

Materialization workers publish `analytics.metrics.daily_materialized.v1` events:

```python
async def on_metrics_materialized(event):
    workspace_id = event['workspace_id']
    date = event['date']
    # Invalidate L2 cache for that workspace's recent queries
    await redis.delete_pattern(f'dm:{workspace_id}:*')
```

L1 expires naturally via short TTL.

### Cache Stampede Prevention

Redis lock + single-flight pattern:

```python
async def get_metric_cached(key, compute_fn):
    if cached := await redis.get(key):
        return cached

    lock_key = f"{key}:lock"
    if await redis.set(lock_key, "1", nx=True, ex=10):
        try:
            value = await compute_fn()
            await redis.setex(key, 60, value)
            return value
        finally:
            await redis.delete(lock_key)
    else:
        # Another pod is computing; wait briefly then retry
        await asyncio.sleep(0.05)
        return await get_metric_cached(key, compute_fn)
```

---

## 15. Performance Targets at 100k req/min

| Operation | Target p50 | Target p95 | Target p99 |
|-----------|-----------|-----------|-----------|
| Daily metrics, cached | 5ms | 20ms | 50ms |
| Daily metrics, cache miss | 50ms | 150ms | 400ms |
| Calendar report (90d) | 80ms | 250ms | 600ms |
| CM Waterfall (30d) | 200ms | 500ms | 1.5s |
| First Product Cascade | 150ms | 400ms | 1s |
| LTV curves (24m × 36m) | 300ms | 800ms | 2s |
| Drill-down (50 orders) | 100ms | 300ms | 800ms |

Benchmark monthly. Add indexes / optimize ClickHouse ordering keys when targets miss.

---

## 16. Capacity Planning

### Workload Estimates at 100k req/min

Assume:
- 80% dashboard reads (mostly cached)
- 15% live queries (Path B)
- 5% drill-downs

Per minute:
- 80k cached reads × Redis ≈ 1.3K RPS to Redis (trivial)
- 15k live queries × ClickHouse ≈ 250 RPS to ClickHouse
- 5k drill-downs × ClickHouse ≈ 80 RPS

ClickHouse cluster (3 shards × 2 replicas) easily handles 1K+ RPS of well-indexed queries.

### Pod Sizing

```yaml
# k8s/analytics-service.yaml
resources:
  requests:
    cpu: 1
    memory: 2Gi
  limits:
    cpu: 4
    memory: 4Gi
```

Each pod: ~500 RPS at 60ms avg. 20 pods = 10K RPS capacity = 600K RPM. Headroom for spikes.

---

## 17. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Materialize CM Waterfall? | E4 | No — too many filter combos. On-demand stays. |
| ClickHouse projections vs materialized views? | E4 | MVs for now. Projections in Phase 3 for alternate sort keys. |
| When to introduce ClickHouse dictionaries for `cost_settings` lookups? | E4 | Phase 2. Speeds up `order_costs` computation. |
| Real-time WebSocket dashboard refresh? | E1 | Phase 3. Subscribe to `analytics.metrics.daily_materialized.v1`. |
| First product attribution — first line item vs highest COGS? | E4 | First line item default; per-workspace configurable Phase 2. |
| Cross-workspace benchmarking queries — same cluster or separate? | E4 | Same cluster, but read-only `bench_user` with restricted access. Phase 3. |
