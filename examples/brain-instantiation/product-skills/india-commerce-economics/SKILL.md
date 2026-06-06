---
name: india-commerce-economics
description: India economic moat in IndiaAdapter — COD/RTO economics, break-even r*=M/(M+C), NDR, pincode scoring, GST 2.0 per-SKU slabs, festival lift, True CM2.
---

# India Commerce Economics — the economic moat

This is the domain knowledge that makes Brain irreplaceable for Indian DTC. Western analytics tools **overstate margin by ~18–28%** because they ignore GST extraction and RTO. Brain models them as first-class P&L lines. All of it lives behind `IndiaAdapter` (`pylibs/brain_regional/india.py`, canon/TECH/04) — never hardcode any of this in the metric engine ([`region-adapter`](../region-adapter/SKILL.md)).

**Canonical sources:** `canon/TECH/04_regional_adapters.md` §2 · `canon/business-requirements.md` §5.2/§6.4/§17.2 · `canon/TECH/03_metrics_engine.md` §0.5.

## When to use

- Computing RTO cost or break-even, COD vs prepaid economics, pincode reliability, NDR resolution, GST extraction, festival lift, settlement/cash-delay, True CM2.
- Reviewing Shiprocket / Razorpay ingestion, the `order_costs` materializer, or any India-specific alert.

## 1. COD vs prepaid — the central tension

COD is the default in Indian DTC and the **single largest controllable margin leak**. The asymmetry:

| | COD | Prepaid |
|---|---|---|
| RTO rate (typical) | **20–35%** | **2–8%** |
| AOV | lower | higher |
| Cash | delayed (settlement after delivery) | upfront |
| Extra cost | COD handling fee (~1.5%) | gateway fee (~2%) |

Every COD order that RTOs costs forward shipping + reverse shipping + restocking + damage write-down **and** earns zero revenue. Pushing COD→prepaid (or restricting COD on bad pincodes) is often the highest-CM2 lever Brain can surface.

## 2. RTO cost model

RTO ≠ customer return ≠ NDR ≠ lost. RTO = dispatched, refused/undelivered, returned to origin. **RTO cost per failed order** =

```
RTO_cost = forward_shipping + reverse_shipping + restocking_labour + inventory_damage_writedown + lost_contribution
```

`IndiaAdapter.compute_logistics_cost(shipment, settings)` rolls this up (canon/TECH/04 §2.3); damage is probabilistic (`rto_damage = cogs × rto_damage_rate`, default 10%). These flow into `order_costs_local` (ClickHouse) and the **CM1** line — operators see the true number, not a platform fantasy.

### Break-even COD RTO rate (the decision threshold)

```
r* = M / (M + C)
  M = contribution margin on a DELIVERED order
  C = RTO cost per FAILED order
```

If the actual COD RTO rate exceeds `r*`, COD on that segment/pincode/SKU is **net-negative** — stop or restrict it. A naive `M / C` ratio understates the true break-even; always use `M / (M+C)` (business-requirements §6.4). This is paradigm-1 SQL — `LLMs never produce this number` ([`metric-engine`](../metric-engine/SKILL.md)).

## 3. NDR — the leading indicator

When a courier attempt fails, status becomes `undelivered` (NDR) *before* it becomes RTO. Active NDR management cuts RTO **30–50%**. Track `shipments.ndr_count` and `ndr_resolved_at`:

```python
ndr_resolution_rate = COUNT(ndr_resolved_at IS NOT NULL) / COUNT(ndr_count > 0)
```

NDR is a queue Brain surfaces (AICOO-Logistics) with per-row actions: WhatsApp the customer (template), update address (Phase 3 Shiprocket writeback), or give up → flip to RTO. Falling NDR resolution is an India default alert (threshold 0.40 / 30d).

## 4. Pincode + city-tier reliability scoring

Nightly job over the last **90 days**, only pincodes with **≥5 shipments** (statistical floor), in `pincode_reliability_local`:

```sql
SELECT workspace_id, delivery_pincode AS pincode,
  count(*) AS shipments_last_90d,
  countIf(status IN ('rto','rto_delivered')) / count(*) AS rto_rate,
  countIf(is_cod AND status IN ('rto','rto_delivered')) / nullIf(countIf(is_cod),0) AS cod_rto_rate
FROM brain_analytics.shipments FINAL
WHERE workspace_id = :ws AND created_at_source >= now64() - INTERVAL 90 DAY
  AND delivery_pincode IS NOT NULL
GROUP BY workspace_id, delivery_pincode
HAVING shipments_last_90d >= 5;
```

Recommendation ladder (`classify_pincode_recommendation`, canon/TECH/04 §2.4):

| Condition | Action |
|---|---|
| `< 10` shipments | `monitor` (insufficient data) |
| `rto_rate ≥ 0.50` | **`block`** — exclude from ads |
| `cod_rto_rate ≥ 0.40` | **`restrict_cod`** — disable COD, keep prepaid |
| `rto_rate ≥ 0.25` | `monitor` — watch closely |
| else | `normal` |

New workspaces blend against a **k-anonymized cross-workspace pincode baseline** (Bayesian) until they have enough of their own data (Phase 3).

## 5. GST 2.0 — per-SKU slab extraction (NOT a blended rate)

Indian Shopify stores list prices **GST-inclusive**. Brain stores GST-**exclusive** Net Revenue, extracted **per line item by SKU slab** — slabs **0 / 5 / 18 / 40** (12% & 28% abolished, eff. 22 Sep 2025). `IndiaAdapter.extract_net_revenue(order) -> (net_revenue_minor, tax_minor)`:

```python
if order.get('taxes_included', True):
    net_revenue = subtotal_minor - discount_minor - tax_minor   # GST inside subtotal
else:
    net_revenue = subtotal_minor - discount_minor
```

A **single blended GST rate is an anti-pattern** (canon §16) — luxury SKUs at 40% vs apparel at 5% in one cart make a blended rate systematically wrong. `tax_reconciliation_report` breaks down by `{0,5,18,40}` slab and (Phase 2) CGST/SGST/IGST by state.

## 6. COD realization, settlement & cash delay

COD cash is collected by the courier and **settled to the brand days-to-weeks later** — and only on delivered orders. Brain tracks:

- **COD Conversion (realization) Rate** = COD Orders Delivered ÷ COD Orders Placed.
- **Realized/Delivered Revenue** = the honest number that survives cancellation/RTO/refund/payment-failure/settlement leakage — and the **billing base** (never bill on placed GMV — see [`billing-metering`](../billing-metering/SKILL.md)).
- **COD cash delay** — a cashflow input (AICFO-Cashflow), distinct from margin.

## 7. Festival calendar + learned lift

Festivals (Diwali, Navratri, Holi, …) are pre-seeded 5 years in `seasonal_events_in` with `shopping_lift_start/end`. Per-workspace **learned lift multipliers** in `festival_lift_factors_local` (computed after each festival: mean of during/baseline ratios + a variance-based confidence). Surfaced in the Calendar Report (shaded), goal-setting, forecasting regressors (Prophet — [`forecasting-prophet`](../forecasting-prophet/SKILL.md)), and anomaly baselines. Adding a region = new seasonal seed, not new code.

## 8. True CM2 — the India-honest margin

```
True CM2 = CM2 − RTO provision − late-refund provision − payment-failure provision
```

Standard CM2 = CM1 − marketing. **True CM2** subtracts the India delivery realities (business-requirements §def). Early Indian brands underestimate CM2 by 15–25 pp because RTO + returns are systematically under-modelled. If True CM2 < 0, scale makes the business worse — Brain flags immediately.

## IST discipline

Calling hours **09:00–21:00 IST** (telecom), Morning Brief window **06:55–09:00 IST**, daily aggregates use workspace-local time. Never reason in UTC for these windows ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md), [`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md)).

## Anti-patterns

- A single blended GST/VAT rate instead of per-SKU slab → margin wrong.
- Margin without RTO adjustment → ~18% overstated (the Western-tool bug Brain exists to fix).
- `M/C` instead of `M/(M+C)` for break-even → COD looks profitable when it isn't.
- Pincode scoring on < 5 shipments → noise treated as signal.
- Billing/CM on placed (not realized/delivered) GMV.
- Hardcoding ₹, GST %, 09:00–21:00, or RTO logic outside `IndiaAdapter` (region leak).

## Verify

- A mixed-slab cart (5% apparel + 40% luxury) extracts the correct per-SKU tax, not a blend.
- A COD order that RTOs writes forward + reverse + restock + damage into `order_costs_local`; CM1 reflects it.
- `r*` matches `M/(M+C)`; a pincode at 52% RTO classifies `block`; a 42% COD-RTO pincode classifies `restrict_cod`.

## References

- `canon/TECH/04_regional_adapters.md` §2 — India adapter (RTO, GST, pincode, NDR, festivals)
- `canon/TECH/03_metrics_engine.md` §0.5 — RTO/COD formula book
- `canon/business-requirements.md` §5.2/§6.4/§17.2 — economic requirements + break-even
- [`region-adapter`](../region-adapter/SKILL.md) · [`metric-engine`](../metric-engine/SKILL.md) · [`clickhouse-olap`](../clickhouse-olap/SKILL.md)
</content>
