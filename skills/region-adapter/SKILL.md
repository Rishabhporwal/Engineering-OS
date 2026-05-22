---
name: region-adapter
description: Brain's multi-region abstraction (canon/TECH/04) — "multi-region from day one, India-first by sequencing." Every region-varying concern (per-SKU tax extraction, payment classification, shipment-status mapping, logistics cost, postal-code normalization + metadata, seasonal events, tax reconciliation, currency, timezone) goes behind the `RegionAdapter` interface, even when only India (`IN`) is implemented today. `get_adapter(region)` lives in `pylibs/brain_regional`. Adding a region = new adapter + seasonal seed + tests; the metric engine, frontend, intelligence, and notifications need ZERO changes. Use when building ANY primitive that could differ by market.
---

# Region Adapter — multi-region from day one, India-first by sequencing

Brain is India-first by go-to-market but **multi-region by architecture** (technical-context principle; canon/TECH/04). The rule: **every region-varying concern is accessed through the `RegionAdapter` interface, even when only the India implementation exists.** This is what lets us serve the India pilot today and a UAE/GCC brand at Phase 4 without rewriting the core. Region-specific code **never escapes** the adapter implementation.

**Canonical source:** `canon/TECH/04_regional_adapters.md`.

## The interface (`pylibs/brain_regional/adapter.py`)

`RegionAdapter` is an ABC with these region attributes + methods:

```python
class RegionAdapter(ABC):
    region_code: str                 # 'IN', 'AE', 'SA', 'US', ...
    default_currency: str            # 'INR', 'AED', 'SAR'
    default_timezone: str            # 'Asia/Kolkata', 'Asia/Dubai'
    fiscal_year_start_month: int     # 4 for India, 1 for most others

    def extract_net_revenue(self, order) -> tuple[int, int]   # (net_revenue_minor, tax_minor) — per-SKU tax
    def classify_payment_method(self, order) -> str           # card|wallet|upi|cod|bnpl|other
    def is_high_risk_payment(self, order, region_data) -> bool # IN: COD on high-RTO pincode
    def map_shipment_status(self, source, status) -> str      # → Brain canonical states (incl. rto)
    def compute_logistics_cost(self, shipment, settings) -> dict[str, int]  # cost_type → minor units
    def normalize_postal_code(self, raw) -> Optional[str]      # IN: 6-digit pincode
    def postal_code_metadata(self, code) -> dict              # {city, state, tier, serviceable_by}
    def get_seasonal_events(self, year) -> list[dict]         # festival/sale lift windows
    def tax_reconciliation_report(self, ws, period) -> dict   # region-appropriate filing summary
```

## Registration + resolution

```python
# pylibs/brain_regional/__init__.py
ADAPTERS = {'IN': IndiaAdapter(), 'US': USAdapter(), 'GB': UKAdapter(), 'AE': UAEAdapter()}

def get_adapter(workspace_region: str) -> RegionAdapter:
    return ADAPTERS.get(workspace_region, IndiaAdapter())
```

**Resolve the adapter per `workspace_id`** (a workspace has a `home_region`). `home_region` is read-only after creation (no migration complexity — create a new workspace if it must change).

## Usage — ingestion / analytics / intelligence all go through it

```python
async def process_order(workspace_id, raw_order):
    workspace = await get_workspace(workspace_id)
    adapter   = get_adapter(workspace.home_region)        # never assume IN
    net_revenue, tax = adapter.extract_net_revenue(raw_order)
    payment_method   = adapter.classify_payment_method(raw_order)
    pincode          = adapter.normalize_postal_code(raw_order["shipping"]["zip"])
```

## What India implements first (the deep wedge)

`IndiaAdapter` is the full implementation (see [`india-commerce-economics`](../india-commerce-economics/SKILL.md) for the economics):
GST 2.0 **per-SKU** slabs 0/5/18/40 (GST-inclusive default); INR with lakh/crore numbering; COD/prepaid + COD handling fee; the full **RTO cost model + state machine**; **pincode reliability** (≥5 shipments / 90d → block/restrict_cod/monitor); **NDR** tracking; **festival calendar + learned lift**; India default alerts (RTO spike, COD-RTO critical, etc.); `Asia/Kolkata`, fiscal year starting **month 4**. Telecom/privacy compliance for `IN` (DLT/NCPR/9am–9pm/WhatsApp opt-in, DPDP) is its compliance surface ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)).

## Currency + timezone (region-aware, never hardcoded)

- Money is `BIGINT` minor units + `currency_code`; each order stores its FX rate at order time (stable history). `to_workspace_currency()` converts to the reporting currency.
- Display via `packages/ui/lib/currency.ts formatMoney(...)`: INR gets **₹X,XX,XXX** Indian grouping and crore/lakh compaction; other currencies use `Intl.NumberFormat` with their locale. Crore/lakh appear **only** for INR.
- Daily aggregates use workspace-local time via `default_timezone` (ClickHouse `local_date` materialized column via a `workspace_tz` dictionary).

## UAE/GCC (Phase 4)

`UAEAdapter` etc.: per-country VAT (KSA 15 / UAE 5 / Bahrain 10 / Oman 5; Qatar/Kuwait none — tax-exclusive), AED/SAR, Ramadan/Eid seasonal events, Arabic/RTL, Tabby/Tamara BNPL, cross-border duties, PDPL, **no RTO concept** (`rto` state unused; `lost`/`damaged` dominate), Salla/Zid/Noon connectors. Built when the first GCC customer goes live — not before.

## Adding a new region — checklist (canon/TECH/04 §4)

1. Create the adapter: `pylibs/brain_regional/<cc>.py` implementing every `RegionAdapter` method.
2. Seed seasonal events → `public.seasonal_events_<cc>`.
3. Define `<CC>_DEFAULT_ALERTS` + region cost-settings template in `pylibs/brain_regional/defaults.py`.
4. Translation strings (if localized) + test-data generator (`--region <CC>`).
5. CI snapshot test: walk an example order through the adapter.

**The metric engine, frontend, intelligence layer, and notifications service require zero changes.** If adding a region forces a change outside the adapter, the region path leaked into shared code — that's the bug this pattern exists to prevent.

## Anti-patterns

- `if region == 'IN'` branches scattered through business logic — the exact thing the adapter prevents.
- Hardcoding ₹, a GST/VAT %, IST calling hours, or RTO logic outside an adapter.
- A region-specific **fork** of a primitive (audience builder, channel router, metric) instead of a new adapter (violates the Single-Primitive Rule).
- A single blended tax rate instead of per-SKU/per-country extraction.
- Assuming a new region "just works" without implementing its tax + payment + logistics + compliance methods.

## Verify

- Grep shared code for `'IN'` / `₹` / `GST` / `09:00`–`21:00` outside `pylibs/brain_regional/india.py` — none in shared primitives.
- A second (even stub) adapter registers and an example order flows through it without touching any primitive's code.

## References

- `canon/TECH/04_regional_adapters.md` — the canonical interface + India/US adapters + add-a-region checklist
- [`india-commerce-economics`](../india-commerce-economics/SKILL.md) — the `IN` economics behind the adapter
- [`metric-engine`](../metric-engine/SKILL.md) — region-agnostic formulas that consume the adapter
- [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) — region compliance is an adapter concern
