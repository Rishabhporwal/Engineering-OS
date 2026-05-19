---
name: india-commerce-economics
description: Brain's India-native economics — RTO, COD, GST, pincode reliability, NDR, festivals, multi-3PL, DLT, NCPR, DND, IST timezone discipline. THE MOAT. Auto-load whenever touching the India RegionAdapter, Shiprocket integration, RTO cost computation, GST extraction (Western tools overstate margin 18%), pincode reliability scoring, festival calendar, lifecycle-service compliance engine, or anything date/time-sensitive (IST window 09:00-21:00 calling hours; Morning Brief 06:55-09:00 IST).
---

# India Commerce Economics — Brain's Moat

Every Western DTC tool assumes prepaid orders, mail returns, no COD, consistent delivery, simple tax. **None are true in India.** Brain's India-native economics are the moat — anyone can rebuild dashboards, but reproducing this domain knowledge takes years.

**Canonical doc:** `canon/BRAIN_TECHNICAL.md`. This skill is operational.

## The seven India realities

| Reality | Brain's response |
|---|---|
| COD is 60–75% of orders | Revenue uncertain until delivery; landed CM2 is the metric |
| RTO (Return to Origin) is 15–40% | Biggest profitability killer; XGBoost RTO-risk-per-order; AICOO-Logistics |
| Pincode reliability varies 5%→45% | Pincode reliability scoring; auto-block / restrict-COD recommendations |
| GST inclusive in listed prices | All revenue + margin nets out GST. Western tools overstate margin 18%. |
| Festival seasonality is extreme | Festival overlay; AICMO-Festival agent; Prophet festival regressors |
| COD handling charges ₹25–50/order | Included in CM2 (Shiprocket charges) |
| NDR before RTO | NDR workflow; Gupshup WhatsApp template for outreach |

## GST extraction (NON-NEGOTIABLE)

```python
# RegionAdapter — apps/analytics-service/region_adapters/india.py
def extract_net_revenue(gross_minor: int, gst_rate: float = 0.18) -> int:
    """₹999 listed (gross_minor=99900) at 18% GST → ₹846.76 net (84676 paisa)"""
    return int(gross_minor / (1 + gst_rate))
```

Every revenue / margin formula on India workspaces applies this. Forgetting it = 18% inflated margin = trust-killing dashboard bug.

## RTO cost (canon/BRAIN_TECHNICAL.md)

```python
def rto_cost(order: Order, shipment: Shipment) -> int:
    if shipment.status != "rto":
        return 0
    return (
        shipment.forward_ship_cost_minor +
        shipment.return_ship_cost_minor +
        order.restock_cost_minor +
        (shipment.cod_handling_fee_minor if order.payment_method == "cod" else 0)
    )
```

RTO is **the** biggest margin killer in India. Average lost: ₹200–600 per RTO.

## Pincode reliability scoring

```sql
-- pincode_reliability_local — nightly job in analytics-service
CREATE TABLE pincode_reliability_local (
  workspace_id        String,
  pincode             LowCardinality(String),
  total_orders        UInt32,
  rto_count           UInt32,
  rto_rate            Float64,
  cod_count           UInt32,
  cod_rto_rate        Float64,
  recommendation      LowCardinality(String),  -- 'block' | 'restrict_cod' | 'monitor' | 'normal'
  computed_at         DateTime64(3) DEFAULT now64()
) ENGINE = ReplicatedReplacingMergeTree(computed_at)
ORDER BY (workspace_id, pincode);
```

Recommendation logic:
- `rto_rate > 0.45` AND `total_orders >= 10` → **block**
- `cod_rto_rate > 0.35` AND `total_orders >= 10` → **restrict_cod** (allow prepaid only)
- `rto_rate > 0.25` → **monitor**
- else → **normal**

Cross-workspace baseline (anonymised aggregate, k ≥ 5 brands) for sparse-history workspaces.

## Festival calendar

```sql
CREATE TABLE seasonal_events_in (
  date            DATE NOT NULL,
  event_name      TEXT NOT NULL,             -- 'Diwali', 'Navratri', 'Holi', ...
  category        TEXT NOT NULL,             -- 'festival' | 'sale' | 'wedding_season' | ...
  region          TEXT,                       -- NULL = all India; 'south' | 'north' | ...
  expected_lift   NUMERIC,                    -- baseline multiplier
  PRIMARY KEY (date, event_name)
);
```

Seeded with 5 years of festivals. Used by:
- AICMO-Festival agent
- Prophet festival regressors (forecasting)
- Festival overlay on time-series charts (Ananya's web)
- Goal suggestion ("Diwali typically lifts revenue 3.2x")

## Indian numbering format

`₹4,82,000` not `₹482,000`. Lakh / crore convention.

```typescript
import { formatINR } from '@brain/formatters';
formatINR(482000n)      // "₹4,82,000"
formatINR(48200000n)    // "₹4,82,00,000"
```

Shared between web (Ananya) and mobile (Karan) via `packages/lib-formatters`.

## IST timezone discipline

All Brain operations operating in India time:
- Calling hours: **09:00–21:00 IST** (hard-coded; never feature-flagged)
- Morning Brief window: **06:55–07:15 IST agent fan-out → 07:15 synthesis → 07:00–09:00 push**
- RFM scoring: **06:30 IST daily**
- Daily reconciliation: **23:30 IST**

```python
import pytz
IST = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(IST)
```

Never store UTC + display IST in a way that breaks DST boundaries (India doesn't observe DST, so this is simpler than US — but always store TZ-aware datetimes).

## Compliance hard-codes (canon/BRAIN_TECHNICAL.md — NON-NEGOTIABLE)

| Rule | Enforcement |
|---|---|
| Calling hours 09:00–21:00 IST | Queue-level gate. Pre-09:00 → `pending_window`; post-21:00 → next-day reschedule. |
| DND | Two-layer: brand opt-out (`customer.do_not_call`) + TRAI NCPR cache (refreshed weekly) |
| Customer consent | `consent_event` audit trail. Required before any outbound. |
| AI call disclosure | Every AI call opens with disclosure. |
| Recording consent | Asked at call start. Declined → call proceeds, no audio retained. |
| DLT registration | Per-brand entity. Brain NEVER commingles brands' DLT registrations. |
| Frequency cap | 48h per customer across ALL channels. Champions override only with Owner audit-logged approval. |
| GST inclusive | Every revenue / margin formula nets it out. |

Shreya VETOs any violation.

## DLT (Distributed Ledger Technology) — TRAI requirement

For Indian SMS / WhatsApp transactional messages:
- Each brand has its own DLT entity ID
- Templates pre-registered under that entity
- Brain's lifecycle-service stores `dlt_template_id` per brand per template
- Send rejected if template not registered
- Brain coordinates via Gupshup BSP

## NCPR (National Customer Preference Register)

TRAI's DND list. Phone numbers registered here can't be called for marketing.
- Cache refreshed weekly via Gupshup
- Two-layer check: brand opt-out OR NCPR-listed → blocked

## Shiprocket integration shape

Order lifecycle states Brain tracks:
```
pending → manifested → in_transit → out_for_delivery → delivered
                                  ↘ ndr (Non-Delivery Report)
                                       ↘ rto_initiated → rto_in_transit → rto_delivered
```

NDR codes worth knowing:
- `customer_unavailable` — retry recommended
- `address_incorrect` — capture-and-update flow
- `customer_refused` — likely RTO
- `payment_issue` (COD) — convert-to-prepaid opportunity

## Multi-3PL strategy (Phase 4)

Beyond Shiprocket — Delhivery, Bluedart direct. RegionAdapter abstracts:

```python
class ShippingProvider(ABC):
    @abstractmethod
    async def create_label(self, order, address): ...

    @abstractmethod
    async def track(self, awb): ...

    @abstractmethod
    def extract_ndr_code(self, raw_status): ...   # provider-specific mapping
```

## RegionAdapter interface (canon/BRAIN_TECHNICAL.md)

```python
class RegionAdapter(ABC):
    code: str           # "IN"
    currency: str       # "INR"
    timezone: str       # "Asia/Kolkata"

    @abstractmethod
    def gst_inclusive(self) -> bool: ...
    @abstractmethod
    def extract_net_revenue(self, gross_minor: int, gst_rate: float) -> int: ...
    @abstractmethod
    def rto_cost(self, order, shipment) -> int: ...
    @abstractmethod
    def pincode_reliability(self, pincode: str) -> PincodeReliability: ...
    @abstractmethod
    def festival_lift(self, date: date) -> float: ...
    @abstractmethod
    def calling_hours_window(self) -> tuple[int, int]: return (9, 21)
```

Adding US / EU = implementing this interface. No change to metric engine.

## Common failure modes

- **GST not extracted** — Western-tool-style margin inflation. Detection: any formula using `total_minor` without `extract_net_revenue` on India workspaces.
- **RTO cost forgotten** — CM2 looks healthy but doesn't reflect actual landed cost. Detection: shipment status='rto' but `rto_cost_minor` not in cm2 formula.
- **Indian numbering format** — `₹482,000` wrong; `₹4,82,000` correct. Use the formatter.
- **Calling hours off by timezone** — calling at 22:00 IST = compliance violation. Always TZ-aware.
- **DLT not registered** — template send returns error. Shreya checks at onboarding.
- **Pincode reliability without k ≥ 5** — cross-workspace baseline leaks brand-specific data. Detection: pincode aggregate query without `HAVING COUNT(DISTINCT workspace_id) >= 5`.
- **Festival not in regressor** — Prophet forecasts crash during Diwali. Detection: forecast MAPE > 30% in festival weeks.

## References

- `canon/BRAIN_TECHNICAL.md` — canonical RegionAdapter interface + India implementation
- `canon/BRAIN_TECHNICAL.md` §6 — compliance engine
- `canon/BRAIN_TECHNICAL.md` §shiprocket — NDR / RTO flow
- `canon/BRAIN_BUSINESS.md` §1.7 (current India support) + §market-realities
- `skills/integration-connectors/SKILL.md` §shiprocket — NDR codes, RTO state machine
- `skills/lifecycle-revenue-layer/SKILL.md` — DLT + NCPR + DND
- `skills/clickhouse-olap/SKILL.md` §india-tables — pincode_reliability_local schema
- `skills/forecasting-prophet/SKILL.md` — festival regressors
