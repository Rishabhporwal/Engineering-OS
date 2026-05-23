# TECH/04 — Regional Adapter Layer (India First, Global Ready)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 (Analytics/ML) + E3 (Backend) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/01_data_architecture.md](01_data_architecture.md), [TECH/03_metrics_engine.md](03_metrics_engine.md)

This document specifies:
- The `RegionAdapter` abstraction
- India regional implementation (RTO, COD, GST, pincode, NDR, festivals)
- US regional implementation skeleton (Phase 4)
- Pattern for adding new regions
- Multi-currency, multi-timezone, multi-tax-model handling

**Philosophy:** India is our first region. Every region-specific concept (RTO economics, COD handling, tax inclusivity, postal-code reliability, festival seasonality) is implemented behind the `RegionAdapter` interface. New regions = new implementations of the same interface — never forks of the metric engine.

This is what lets us serve the pilot brand in India today and a US brand at Phase 4 without rewriting the core.

---

## 1. The `RegionAdapter` Interface

```python
# pylibs/brain_regional/adapter.py

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

class RegionAdapter(ABC):
    """Region-specific economics and behavior contract.

    Each implementation handles one country's tax model, payment realities,
    logistics quirks, seasonal patterns, and postal-code semantics.
    """

    region_code: str                              # 'IN', 'US', 'GB', 'AE', etc.
    default_currency: str                         # 'INR', 'USD', 'GBP', 'AED'
    default_timezone: str                         # 'Asia/Kolkata', 'America/New_York'
    fiscal_year_start_month: int                  # 4 for India, 1 for most others

    # --- Pricing ---
    @abstractmethod
    def extract_net_revenue(self, order: dict) -> tuple[int, int]:
        """
        Returns (net_revenue_minor, tax_minor).
        Handles tax-inclusive vs tax-exclusive pricing.
        India: GST-inclusive by default.
        US: tax-exclusive (tax added on top).
        """
        ...

    # --- Payment ---
    @abstractmethod
    def classify_payment_method(self, order: dict) -> str:
        """Returns one of: 'card', 'wallet', 'upi', 'cod', 'bnpl', 'other'."""
        ...

    @abstractmethod
    def is_high_risk_payment(self, order: dict, region_data: dict) -> bool:
        """Region-aware risk flag. India: COD-on-high-RTO-pincode = high risk."""
        ...

    # --- Logistics ---
    @abstractmethod
    def map_shipment_status(self, source: str, source_status: str) -> str:
        """Map source-specific status to Brain canonical states.
        Canonical states include 'rto', 'rto_delivered' for return-to-origin (India-relevant);
        for regions without RTO concept, 'rto' is unused and 'lost'/'damaged' may dominate."""
        ...

    @abstractmethod
    def compute_logistics_cost(self, shipment: dict, settings: dict) -> dict[str, int]:
        """Returns dict of cost_type → amount_minor."""
        ...

    # --- Postal codes ---
    @abstractmethod
    def normalize_postal_code(self, raw: str) -> Optional[str]:
        """Canonicalize a postal code. India: 6-digit pincode. US: ZIP5 or ZIP+4."""
        ...

    @abstractmethod
    def postal_code_metadata(self, postal_code: str) -> dict:
        """Returns {'city', 'state', 'tier', 'serviceable_by': []}"""
        ...

    # --- Seasonality ---
    @abstractmethod
    def get_seasonal_events(self, year: int) -> list[dict]:
        """Returns list of seasonal events with shopping-lift periods."""
        ...

    # --- Tax reporting ---
    @abstractmethod
    def tax_reconciliation_report(self, workspace_id: str, period: date) -> dict:
        """Region-appropriate tax filing summary."""
        ...
```

### Registration

```python
# pylibs/brain_regional/__init__.py
from .india import IndiaAdapter
from .us import USAdapter           # Phase 4
from .uk import UKAdapter           # Phase 4
from .uae import UAEAdapter         # Phase 4

ADAPTERS = {
    'IN': IndiaAdapter(),
    'US': USAdapter(),
    'GB': UKAdapter(),
    'AE': UAEAdapter(),
}

def get_adapter(workspace_region: str) -> RegionAdapter:
    return ADAPTERS.get(workspace_region, IndiaAdapter())
```

### Usage in Services

ingestion-service, analytics-service, intelligence-service all use the adapter:

```python
async def process_order(workspace_id, raw_order):
    workspace = await get_workspace(workspace_id)
    adapter = get_adapter(workspace.home_region)

    net_revenue, tax = adapter.extract_net_revenue(raw_order)
    payment_method = adapter.classify_payment_method(raw_order)
    postal_code = adapter.normalize_postal_code(raw_order.get('shipping', {}).get('zip'))

    # Persist
    ...
```

Region-specific code never escapes the adapter implementation.

---

## 2. India Adapter — Implementation

This is the depth of our wedge. Everything below is what makes Brain irreplaceable for Indian DTC.

### 2.1 GST Extraction

Indian Shopify stores typically list prices **GST-inclusive**. Brain stores GST-exclusive Net Revenue.

```python
class IndiaAdapter(RegionAdapter):
    region_code = 'IN'
    default_currency = 'INR'
    default_timezone = 'Asia/Kolkata'
    fiscal_year_start_month = 4

    def extract_net_revenue(self, order: dict) -> tuple[int, int]:
        """Indian Shopify orders are typically GST-inclusive."""
        taxes_included = order.get('taxes_included', True)
        subtotal_minor = to_minor(order['subtotal_price'], 'INR')
        discount_minor = to_minor(order['total_discounts'], 'INR')
        tax_minor = to_minor(order['total_tax'], 'INR')

        if taxes_included:
            # GST already inside subtotal
            net_revenue = subtotal_minor - discount_minor - tax_minor
        else:
            net_revenue = subtotal_minor - discount_minor

        return net_revenue, tax_minor
```

Edge case: international Shopify markets within an Indian brand's store. The adapter handles both modes via the `taxes_included` flag.

**Critical:** Western analytics tools that don't extract GST overstate margin by 18-28%. Brain's CM1/CM2/CM3 calculations use `net_revenue_minor` (GST-exclusive) everywhere.

### 2.2 RTO Economics

RTO (Return to Origin) is India's biggest profitability killer. Brain models it fully.

**Definition:** An order is RTO when:
- A shipment was dispatched
- The customer did not accept delivery
- The package returned to the brand's pickup location

Distinct from customer return (post-delivery refund), NDR (failed delivery attempt, may retry), or Lost (mid-transit loss).

**State machine** (recap):

```
pickup_pending → pickup_done → in_transit → out_for_delivery
                                                  │
              ┌───────────────────────────────────┼──────────────────────┐
              ▼                                   ▼                      ▼
         delivered                       undelivered (NDR)        lost / damaged
                                                  │
                                  ┌───────────────┼───────────────┐
                                  ▼               ▼               ▼
                              delivered    rto_initiated    (re-attempt)
                                                  │
                                                  ▼
                                            rto_delivered
                                            (terminal)
```

### 2.3 RTO Cost Computation

```python
def compute_logistics_cost(self, shipment: dict, settings: dict) -> dict[str, int]:
    """All cost components for a shipment. RTO costs only if shipment ended in RTO."""
    is_rto = shipment['status'] in ('rto', 'rto_delivered', 'lost')
    is_cod = shipment.get('is_cod', False)

    forward = shipment.get('forward_shipping_cost_minor') or \
              self._effective_setting(settings, 'shipping_forward', shipment['created_at'])

    costs = {
        'shipping_forward': forward,
        'packaging': self._packaging_cost(shipment, settings),
        'payment_gateway': self._payment_gateway_cost(shipment, is_cod, settings),
    }

    if is_cod:
        costs['cod_handling'] = shipment.get('cod_handling_fee_minor') or \
            self._effective_setting(settings, 'cod_handling_fee', shipment['created_at'])

    if is_rto:
        return_shipping = shipment.get('return_shipping_cost_minor') or \
            self._effective_setting(settings, 'shipping_return', shipment['created_at']) or \
            forward                                                  # default = same as forward

        restocking = self._effective_setting(settings, 'rto_restocking_cost', shipment['created_at'])

        # Damaged inventory: probabilistic — % of RTOs return damaged
        damage_rate = self._effective_setting(settings, 'rto_damage_rate', shipment['created_at']) or 0.10
        cogs = self._get_order_cogs(shipment.get('order_id'))
        damage_loss = int(cogs * damage_rate)

        costs['shipping_return'] = return_shipping
        costs['rto_restocking'] = restocking or 0
        costs['rto_damage'] = damage_loss
        # The full "rto_cost" rolled up
        costs['rto_cost'] = return_shipping + (restocking or 0) + damage_loss

    return costs
```

These costs flow into `order_costs_local` (ClickHouse) via analytics-service. The CM2 line of every margin calculation already subtracts them — operators see the true profit number.

### 2.4 Pincode Reliability

```python
def normalize_postal_code(self, raw: str) -> Optional[str]:
    """India pincode: 6-digit string."""
    if not raw:
        return None
    cleaned = raw.strip().replace(' ', '').replace('-', '')
    if len(cleaned) == 6 and cleaned.isdigit():
        return cleaned
    return None
```

**Reliability scoring** (nightly job in analytics-service):

```sql
INSERT INTO brain_analytics.pincode_reliability_local
SELECT
  workspace_id,
  delivery_pincode AS pincode,
  any(delivery_city) AS city,
  any(delivery_state) AS state,
  count(*) AS shipments_last_90d,
  countIf(status IN ('delivered')) AS delivered_last_90d,
  countIf(status IN ('rto', 'rto_delivered')) AS rto_last_90d,
  countIf(status IN ('rto', 'rto_delivered')) / count(*) AS rto_rate,
  countIf(is_cod) AS cod_shipments_last_90d,
  countIf(is_cod AND status IN ('rto', 'rto_delivered')) / nullIf(countIf(is_cod), 0) AS cod_rto_rate,
  countIf(NOT is_cod AND status IN ('rto', 'rto_delivered')) / nullIf(countIf(NOT is_cod), 0) AS prepaid_rto_rate
FROM brain_analytics.shipments FINAL
WHERE workspace_id = :ws
  AND created_at_source >= now64() - INTERVAL 90 DAY
  AND delivery_pincode IS NOT NULL
GROUP BY workspace_id, delivery_pincode
HAVING shipments_last_90d >= 5;
```

**Recommendation logic:**

```python
def classify_pincode_recommendation(stats):
    if stats.shipments_last_90d < 10:
        return 'monitor', f'Only {stats.shipments_last_90d} shipments — insufficient data'
    if stats.rto_rate >= 0.50:
        return 'block', f'{stats.rto_rate*100:.0f}% RTO — exclude from ads'
    if stats.cod_rto_rate and stats.cod_rto_rate >= 0.40:
        return 'restrict_cod', f'{stats.cod_rto_rate*100:.0f}% COD RTO — disable COD'
    if stats.rto_rate >= 0.25:
        return 'monitor', f'{stats.rto_rate*100:.0f}% RTO — watch closely'
    return 'normal', None
```

**Cross-workspace baseline** (Phase 3): a separate table `pincode_baseline` aggregates anonymized data across workspaces. New workspaces use the baseline until they have enough of their own data (Bayesian blending).

### 2.5 NDR Tracking

When a courier attempts delivery and fails, the shipment status becomes `undelivered`. Active NDR management reduces RTO by 30-50%.

`shipments.ndr_count` tracks attempts; `shipments.ndr_resolved_at` set when delivery eventually succeeds.

**NDR Workflow UI** (Phase 2):

```
┌─────────────────────────────────────────────────────────────────────┐
│  ACTIVE NDRS — 23 shipments awaiting resolution                      │
├──────────┬──────────────┬────────┬─────────────┬───────────────────┤
│ AWB      │ Customer     │ AOV    │ Days in NDR │ Reason            │
├──────────┼──────────────┼────────┼─────────────┼───────────────────┤
│ 1234...  │ Priya M.     │ ₹1,840 │ 2 days      │ Customer not home │
│ 5678...  │ Rohan K.     │ ₹990   │ 4 days      │ Phone unreachable │
└──────────┴──────────────┴────────┴─────────────┴───────────────────┘
```

Per-row actions:
- "Call customer" (opens WhatsApp via Gupshup with pre-filled template)
- "Update address" (Phase 3 — writes back to Shiprocket)
- "Cancel & RTO" (gives up; flips to RTO immediately)

**NDR resolution rate** as a daily metric:

```python
daily_metric: ndr_resolution_rate
  = COUNT(shipments WHERE ndr_resolved_at IS NOT NULL)
    / COUNT(shipments WHERE ndr_count > 0)
```

### 2.6 COD vs Prepaid Economics

A dedicated dashboard (Phase 2):

```
            │  COD          │  Prepaid       │  Difference
────────────┼───────────────┼────────────────┼──────────
Orders      │  340          │  186           │  +154
AOV         │  ₹1,180       │  ₹1,420        │  -₹240
RTO rate    │  28%          │  6%            │  +22pp
CM2 / order │  ₹98 (8.3%)   │  ₹342 (24.1%)  │  -₹244 / -15.8pp
```

**Materialized metrics:**
- `cod_orders_count`, `cod_share`
- `cod_revenue_minor`, `prepaid_revenue_minor`
- `cod_rto_rate`, `prepaid_rto_rate` (30-day lag for RTO resolution)
- `cod_aov_minor`, `prepaid_aov_minor`
- `cod_cm2_per_order_minor`, `prepaid_cm2_per_order_minor`

**Insight surfaced (Phase 3 AI):**

> "Your COD orders are losing ₹98 per order on average over the last 30 days. Restricting COD to pincodes with <15% RTO rate would improve CM2 by ~₹X/month while costing ~Y% in lost orders."

### 2.7 Festival Calendar

Stored in a regional reference table:

```sql
CREATE TABLE public.seasonal_events_in (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,                           -- 'Diwali 2026'
  event_type TEXT NOT NULL,                     -- 'diwali', 'navratri', 'holi', 'republic_day', ...
  date_start DATE NOT NULL,
  date_end DATE NOT NULL,
  shopping_lift_start DATE,                     -- when demand begins
  shopping_lift_end DATE,                       -- when demand ends
  region_scope TEXT NOT NULL DEFAULT 'all_india',
  notes TEXT
);

INSERT INTO public.seasonal_events_in (name, event_type, date_start, date_end, shopping_lift_start, shopping_lift_end) VALUES
  ('Diwali 2026', 'diwali', '2026-11-08', '2026-11-12', '2026-10-15', '2026-11-15'),
  ('Navratri 2026', 'navratri', '2026-09-22', '2026-09-30', '2026-09-15', '2026-10-05'),
  ('Holi 2027', 'holi', '2027-03-13', '2027-03-13', '2027-03-05', '2027-03-15'),
  -- ... 5 years pre-seeded
;
```

Per-workspace lift factors (learned over time):

```sql
CREATE TABLE festival_lift_factors_local ON CLUSTER brain_cluster
(
  workspace_id UUID,
  event_type LowCardinality(String),
  metric_name LowCardinality(String),
  lift_multiplier Float64,
  sample_size UInt32,
  confidence Float32,
  computed_at DateTime64(3, 'UTC')
)
ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/festival_lift', '{replica}', computed_at)
ORDER BY (workspace_id, event_type, metric_name);
```

Computed annually after a festival completes:

```python
def compute_festival_lift_factors(workspace_id: str, event_type: str):
    past_events = get_past_events(event_type, workspace_id, min_data_days=90)
    lifts = []
    for event in past_events:
        during = mean_metric(workspace_id, 'revenue_net_minor', event.shopping_lift_start, event.shopping_lift_end)
        baseline = mean_metric(workspace_id, 'revenue_net_minor',
                               event.shopping_lift_start - timedelta(days=30),
                               event.shopping_lift_start - timedelta(days=7))
        if baseline > 0:
            lifts.append(during / baseline)

    if lifts:
        mean_lift = np.mean(lifts)
        confidence = 1 / (1 + np.var(lifts)) if len(lifts) > 1 else 0.5
        save_lift_factor(workspace_id, event_type, 'revenue_net_minor', mean_lift, len(lifts), confidence)
```

**Surfaced in:**
- Calendar Report: festival periods shaded; tooltip shows expected lift
- Goal-setting UI: "Diwali typically lifts revenue 3.2x — consider goal of ₹X for October"
- Forecasting: lift factors applied during forecast windows
- Anomaly detection: festival days have adjusted baselines

### 2.8 Order Risk Score (Phase 3)

Predictive at order placement. Surfaced via Shopify webhook.

**Features:**
- Pincode RTO rate (workspace + baseline)
- COD vs prepaid
- Time of day (late-night COD orders RTO higher)
- Order value
- Customer history (existing customer with no prior RTO = low risk)

**Model:** Logistic regression initially → gradient boosted trees (Phase 4)

**Output:** P(rto) score per order; flagged for proactive action if >40%.

### 2.9 India Default Alerts

Seeded on workspace creation when `home_region = 'IN'`:

```python
INDIA_DEFAULT_ALERTS = [
    {'name': 'RTO rate spike', 'metric_name': 'rto_rate', 'condition': 'above', 'threshold': 0.30, 'comparison_window': '7d', 'severity': 'warning'},
    {'name': 'COD RTO rate critical', 'metric_name': 'cod_rto_rate', 'condition': 'above', 'threshold': 0.40, 'comparison_window': '7d', 'severity': 'critical'},
    {'name': 'High-RTO pincode count', 'metric_name': 'pincodes_recommended_block', 'condition': 'above', 'threshold': 5, 'severity': 'warning'},
    {'name': 'NDR resolution rate dropping', 'metric_name': 'ndr_resolution_rate', 'condition': 'below', 'threshold': 0.40, 'comparison_window': '30d', 'severity': 'warning'},
]
```

Workspaces in other regions get different defaults (see Section 3).

---

## 3. US Adapter (Phase 4 Skeleton)

```python
class USAdapter(RegionAdapter):
    region_code = 'US'
    default_currency = 'USD'
    default_timezone = 'America/New_York'
    fiscal_year_start_month = 1

    def extract_net_revenue(self, order: dict) -> tuple[int, int]:
        """US: sales tax is exclusive (added on top of listed price)."""
        subtotal = to_minor(order['subtotal_price'], 'USD')
        discount = to_minor(order['total_discounts'], 'USD')
        tax = to_minor(order['total_tax'], 'USD')

        # Tax is added on top in US; subtotal is already net
        net_revenue = subtotal - discount
        return net_revenue, tax

    def classify_payment_method(self, order: dict) -> str:
        gateway = order.get('payment_gateway_names', [''])[0].lower()
        if 'paypal' in gateway: return 'wallet'
        if 'klarna' in gateway or 'afterpay' in gateway: return 'bnpl'
        if 'shop_pay' in gateway: return 'wallet'
        return 'card'

    def is_high_risk_payment(self, order: dict, region_data: dict) -> bool:
        # US: no COD; high-risk = chargeback risk based on dispute history
        # Phase 4: integrate with Stripe Radar / Shopify Risk Analysis
        return False

    def normalize_postal_code(self, raw: str) -> Optional[str]:
        """US: ZIP5 (or ZIP+4 → take first 5)."""
        if not raw:
            return None
        cleaned = raw.strip().replace(' ', '').split('-')[0]
        if len(cleaned) == 5 and cleaned.isdigit():
            return cleaned
        return None

    def map_shipment_status(self, source: str, source_status: str) -> str:
        """US: no RTO concept. Map to canonical with 'rto' unused."""
        ...

    def compute_logistics_cost(self, shipment: dict, settings: dict) -> dict[str, int]:
        """US: no COD handling, no RTO; standard forward shipping."""
        return {
            'shipping_forward': shipment.get('forward_shipping_cost_minor') or 0,
            'packaging': self._packaging_cost(shipment, settings),
            'payment_gateway': self._payment_gateway_cost(shipment, settings),
        }

    def get_seasonal_events(self, year: int) -> list[dict]:
        return [
            {'name': f'Black Friday {year}', 'event_type': 'bf',
             'date_start': f'{year}-11-29', 'date_end': f'{year}-11-29',
             'shopping_lift_start': f'{year}-11-22', 'shopping_lift_end': f'{year}-11-30'},
            {'name': f'Cyber Monday {year}', 'event_type': 'cm',
             'date_start': f'{year}-12-02', 'date_end': f'{year}-12-02',
             'shopping_lift_start': f'{year}-12-01', 'shopping_lift_end': f'{year}-12-03'},
            {'name': f'Christmas {year}', 'event_type': 'xmas',
             'date_start': f'{year}-12-25', 'date_end': f'{year}-12-25',
             'shopping_lift_start': f'{year}-12-10', 'shopping_lift_end': f'{year}-12-26'},
            {'name': f'Prime Day {year}', 'event_type': 'prime_day',
             'date_start': f'{year}-07-15', 'date_end': f'{year}-07-16',
             'shopping_lift_start': f'{year}-07-10', 'shopping_lift_end': f'{year}-07-20'},
            # ...
        ]

    def tax_reconciliation_report(self, workspace_id: str, period: date) -> dict:
        """US: per-state sales tax breakdown."""
        ...
```

### US Default Alerts

```python
US_DEFAULT_ALERTS = [
    {'name': 'Chargeback rate spike', 'metric_name': 'chargeback_rate', 'condition': 'above', 'threshold': 0.01, 'comparison_window': '7d', 'severity': 'critical'},
    {'name': 'BNPL share dropping', 'metric_name': 'bnpl_share', 'condition': 'below', 'threshold': 0.10, 'severity': 'info'},
    # No RTO / COD alerts; not applicable
]
```

---

## 4. Adding a New Region — Checklist

To add the UK (`GB`):

1. **Create adapter:** `pylibs/brain_regional/uk.py` implementing `RegionAdapter`
2. **Seed seasonal events:** `tools/seed_seasonal_events_uk.py` → `public.seasonal_events_gb`
3. **Default alerts:** define `UK_DEFAULT_ALERTS`
4. **Default cost settings template:** typical UK shipping/payment-gateway rates
5. **Translation strings** (if UI is localized): English (en-GB)
6. **Test data generator:** `tools/seed-demo.py --region GB`
7. **CI test:** snapshot test that walks an example order through the adapter

The metric engine, frontend, intelligence layer, and notifications service require **zero changes** to support a new region.

---

## 5. Currency Handling

### Storage

- Order-level: `currency_code` (the transaction currency) + `total_minor` etc. (in that currency)
- Workspace-level: `default_currency` (reporting currency)
- All money is BIGINT in minor units (paise/cents/pence)

### Conversion

```python
# pylibs/brain_regional/currency.py

async def to_workspace_currency(amount_minor: int, source_currency: str, workspace_currency: str, on_date: date) -> int:
    """Convert money from source currency to workspace's reporting currency, using FX rate on the given date."""
    if source_currency == workspace_currency:
        return amount_minor
    rate = await get_fx_rate(source_currency, workspace_currency, on_date)
    return int(amount_minor * rate)
```

Each order stores the FX rate at order time so historical reports are stable.

### Display

```typescript
// packages/ui/lib/currency.ts

export function formatMoney(
  amountMinor: number | bigint,
  currency: string,
  format: 'full' | 'compact' | 'lakh_crore' = 'full'
): string {
  const amount = Number(amountMinor) / 100;

  // India: lakh/crore formatting if explicitly requested or if currency is INR and format is compact
  if (currency === 'INR' && format === 'lakh_crore') {
    if (amount >= 10_000_000) return `₹${(amount / 10_000_000).toFixed(2)} Cr`;
    if (amount >= 100_000) return `₹${(amount / 100_000).toFixed(2)} L`;
    return `₹${new Intl.NumberFormat('en-IN').format(Math.round(amount))}`;
  }

  // Other regions: standard locale formatting
  return new Intl.NumberFormat(currencyToLocale(currency), {
    style: 'currency',
    currency: currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

function currencyToLocale(currency: string): string {
  return ({
    'INR': 'en-IN', 'USD': 'en-US', 'GBP': 'en-GB',
    'EUR': 'de-DE', 'AED': 'ar-AE', 'AUD': 'en-AU'
  })[currency] || 'en-US';
}
```

Indian operators see ₹4,82,000 (Indian grouping); US operators see $482,000.00 (US grouping). Crore/lakh appear only for INR.

---

## 6. Timezone Handling

Every workspace has `default_timezone`. Daily aggregates use workspace-local time:

```sql
-- ClickHouse: pre-materialize local_date per workspace
ALTER TABLE brain_analytics.orders_local ON CLUSTER brain_cluster
ADD COLUMN local_date Date MATERIALIZED toDate(created_at, dictGet('workspace_tz', 'timezone', workspace_id));
```

For top-N timezone workspaces (>10 brands), pre-materialize via dictionary lookup. For rare timezones, compute on the fly (still fast).

---

## 7. Region-Aware Default Configurations

When a workspace is created with `home_region`, ingestion-service seeds:

```python
async def seed_workspace_for_region(workspace_id, region):
    adapter = get_adapter(region)
    settings = REGION_DEFAULTS[region]

    # Default cost settings (shipping, packaging rates)
    await seed_cost_settings(workspace_id, settings.cost_settings)

    # Default alert rules
    await seed_alert_rules(workspace_id, settings.default_alerts)

    # Seasonal events visibility
    await link_seasonal_events(workspace_id, region)
```

```python
# pylibs/brain_regional/defaults.py

REGION_DEFAULTS = {
    'IN': RegionDefaults(
        cost_settings=[
            {'cost_type': 'shipping_forward', 'amount_minor': 6000, 'notes': 'Typical ₹60 forward shipping via Shiprocket'},
            {'cost_type': 'cod_handling_fee', 'percentage': 0.015, 'notes': '1.5% COD handling fee'},
            {'cost_type': 'payment_gateway_prepaid_pct', 'percentage': 0.020, 'notes': '2% prepaid gateway fee (Razorpay)'},
            {'cost_type': 'rto_damage_rate', 'percentage': 0.10, 'notes': '10% damaged on RTO return'},
        ],
        default_alerts=INDIA_DEFAULT_ALERTS,
        currency='INR',
        tax_rate_default=0.18,                # GST 2.0: tax is per-SKU slab (0/5/18/40); 0.18 is a FALLBACK only
        tax_inclusive_default=True,
    ),
    'US': RegionDefaults(
        cost_settings=[
            {'cost_type': 'shipping_forward', 'amount_minor': 800, 'notes': '$8 forward shipping via Shippo'},
            {'cost_type': 'payment_gateway_prepaid_pct', 'percentage': 0.029, 'notes': '2.9% Stripe'},
            {'cost_type': 'payment_gateway_prepaid_flat', 'amount_minor': 30, 'notes': '$0.30 Stripe'},
        ],
        default_alerts=US_DEFAULT_ALERTS,
        currency='USD',
        tax_rate_default=None,                # State-dependent
        tax_inclusive_default=False,
    ),
    # ...
}
```

---

## 8. Tax Reconciliation (Region-Specific)

Each adapter produces a region-appropriate tax filing summary.

### India: GST Summary

```python
def tax_reconciliation_report(self, workspace_id, period):
    return {
        'period': period.isoformat(),
        'total_gst_collected': sum_metric(workspace_id, period, 'total_tax_minor'),
        'gst_on_refunds': sum_metric(workspace_id, period, 'refund_tax_minor'),
        'breakdown_by_rate': {        # GST 2.0 slabs (eff. 22 Sep 2025): 12% & 28% abolished
            '0_pct': ...,
            '5_pct': ...,
            '18_pct': ...,
            '40_pct': ...,            # luxury/sin goods
        },
        'net_gst_liability': ...,
        'breakdown_by_state': [...],  # for IGST vs CGST/SGST classification
    }
```

### US: Sales Tax by State

```python
def tax_reconciliation_report(self, workspace_id, period):
    return {
        'period': period.isoformat(),
        'total_sales_tax_collected': ...,
        'breakdown_by_state': [
            {'state': 'CA', 'tax_collected': ..., 'taxable_orders': ...},
            {'state': 'NY', 'tax_collected': ..., 'taxable_orders': ...},
            # ...
        ],
        'nexus_warnings': [...],   # if any state crossed economic nexus threshold
    }
```

---

## 9. Multi-Region Deployment (Phase 4)

### Architecture

- **Primary region:** ap-south-1 (Mumbai) — serves Indian workspaces
- **Secondary region:** us-east-1 — serves US/EU expansion
- **Eu region** (later): eu-central-1 (Frankfurt) for GDPR-strict workspaces

### Data Residency

Each workspace's `aws_primary_region` determines:
- Where its OLTP data lives (Supabase project per region)
- Which MSK cluster receives its events
- Which ClickHouse cluster stores its analytics

### Cross-Region

- Kafka mirroring via MirrorMaker 2 (one-way to secondary regions for read-only replication)
- ClickHouse: `ReplicatedMergeTree` across regions (eventual consistency)
- Postgres: AWS DMS or logical replication

EU customers' data never leaves eu-central-1. India customers' data never leaves ap-south-1.

---

## 10. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Damage rate calibration from data? | E4 | Phase 3. Requires inventory reconciliation worker. Until then, operator-set with 10% default. |
| Per-state GST rates within India? | E3 | Phase 2 — when CGST/SGST/IGST split matters for filings. |
| Pincode tier mapping — manual or derived? | E4 | Derived from cross-workspace baseline (k-anonymized). |
| Pincode-block writeback to Shopify? | E1 | Phase 4 via Shopify app extension. |
| Region migration — can a workspace switch `home_region`? | E1 | Read-only after creation; create new workspace if needed. Avoid migration complexity. |
| Country detection from Shopify store domain? | E3 | Yes — `.in` → IN, `.com` with shop owner address → infer. Operator override always available. |
| Multi-region Stripe / Razorpay support? | E3 | Phase 4. Each region's payment gateway integration is region-adapter scoped. |
| WhatsApp NDR via Gupshup template — pre-approved? | E4 | Templates submitted before launch. India-only Phase 2. |
