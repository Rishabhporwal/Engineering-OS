---
name: metric-engine
description: Brain's Metric Engine & Formula Book (canon/TECH/03) — the single source of truth for every KPI definition, computed identically in TS (`packages/lib-metrics`) and Python (`pylibs/brain_metrics`) with CI-enforced parity. The full revenue ladder (Gross→Net→Net-Net-Tax per-SKU→Net Revenue→Realized/Delivered), the CM waterfall (CM1/CM2/CM3 + True CM2), marketing metrics (MER/aMER/paMER/CAC/payback/LTV:CAC; ROAS display-only), COD/RTO metrics, Goal RAG. Money = integer minor units; deterministic SQL paradigm; LLMs NEVER produce a metric number. Use when adding/changing a metric, when a number disagrees across surfaces, or when wiring a KPI card.
---

# Metric Engine & Formula Book

Every number Brain shows comes from the **Formula Book** (canon/TECH/03 §0) — the canonical, versioned definition of each metric. The Iron Rule: **a metric is defined once and computed identically in TypeScript (`packages/lib-metrics`) and Python (`pylibs/brain_metrics`).** Divergence is a P0 trust bug — a founder seeing two different "CM2" numbers stops trusting Brain. This is the single most important service in the product (analytics-service).

**Canonical sources:** `canon/TECH/03_metrics_engine.md` (Formula Book §0 + registry §2) · `canon/technical-requirements.md` §11.

## The four invariants

1. **Single definition, single source of truth.** Each metric has one entry in the registry. Python is generated from the TS registry (`tools/generate-metrics-registry.sh`); never inline a formula at a call site.
2. **TS↔Python parity is CI-gated.** Same inputs → same output (to defined precision) in both languages. A parity failure is a Tanvi QA **VETO** ([`testing-tdd`](../testing-tdd/SKILL.md)).
3. **LLMs never produce metric numbers** — paradigm 1 (SQL/deterministic). The frontier LLM only enters at the Morning Brief synthesis boundary to *narrate* numbers it is given, never to compute them ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)).
4. **Money = integer minor units** (`Int64` paisa) + `currency_code`. Never `NUMERIC`/float for money (anti-pattern). Region/currency formatting via [`region-adapter`](../region-adapter/SKILL.md).

## The revenue ladder (each step is GST-aware)

| Term | Formula | Note |
|---|---|---|
| **Gross Sales** | Σ line-item prices (pre-tax, pre-discount, pre-refund) | marketing-only; not P&L |
| **Net Sales** | Gross − Discounts − Refunds | still includes GST |
| **Net Sales Net Tax** | Net Sales − GST, extracted **per SKU slab** (0/5/18/40) | via `adapter.extract_net_revenue` |
| **Net Revenue** | GST-exclusive revenue | first-class input to all CM math |
| **Realized / Delivered Revenue** | Net Revenue from `status = delivered` (excludes RTO + cancelled) | **the honest number AND the billing base** |

GST is **per line item by SKU slab** — a single blended rate is an anti-pattern (a 5% apparel + 40% luxury cart breaks a blend).

## The CM waterfall (canonical cost placement)

Non-marketing variable costs sit in CM1, marketing in CM2, fixed in CM3:

```
Gross Product Margin = Net Revenue − COGS                              (pre-variable view, not a CM step)
CM1 = Net Revenue − COGS − non-marketing variable costs
      (forward shipping, packaging, payment-gateway, COD handling,
       RTO provisions [modelled], returns provisions, per-order CS)
CM2 = CM1 − Marketing Spend (paid media + influencer + affiliate + lifecycle msg cost)   ← the honest number
CM3 = CM2 − allocated Fixed Costs (salaries, agency, rent, software, warehouse)
Operating Profit = CM3 − founder salary / financing / one-offs
True CM2 = CM2 − RTO provision − late-refund provision − payment-failure provision        (India-honest)
```

If **CM1 < 0**, no marketing can save it — flag. If **CM2 < 0**, scale makes it worse. **Tax to government is never a cost** (CGST/SGST/IGST flow through net revenue). Discounts apply at line-item level **before** GST.

## Marketing efficiency

| Metric | Formula |
|---|---|
| **MER** | Total Net Revenue ÷ Total Marketing Spend (blended) |
| **aMER** | New-Customer Net Revenue ÷ New-Customer Acquisition Spend |
| **paMER** | profit-adjusted variant (CM2 basis) |
| **CAC** | Marketing Spend ÷ **delivered** new customers (not placed) |
| **CAC payback** | months for cumulative cohort CM2 to cover CAC |
| **LTV:CAC** | cohort cumulative **CM2** ÷ cohort CAC (LTV via BG/NBD + Gamma-Gamma; retention via Kaplan-Meier) |
| **ROAS** (per channel) | channel attributed revenue ÷ channel spend — **DISPLAY-ONLY, never the P&L decision metric** |

## COD / RTO metrics (India)

`rto_rate`, `rto_cost_per_order` (forward + reverse + restock + write-down), `cod_conversion_rate`, `prepaid_conversion_rate`, COD/prepaid mix at SKU/channel/pincode/AOV, and the **break-even COD RTO rate `r* = M/(M+C)`** ([`india-commerce-economics`](../india-commerce-economics/SKILL.md)). RTO-adjusted CM2 is the default margin view.

## Goal RAG (each metric carries direction)

- Higher-is-better: Green **≥95%**, Amber **80–95%**, Red **<80%** of goal.
- Lower-is-better: Green **≤105%**, Amber **105–125%**, Red **>125%** of goal.
- Output always includes an explanation + recommended action — never a bare colour.

## The registry (`packages/lib-metrics` + `pylibs/brain_metrics`)

```typescript
export interface MetricDefinition {
  name: string; displayName: string;
  unit: 'currency_minor' | 'count' | 'ratio' | 'percentage' | 'days';
  direction: 'higher_is_better' | 'lower_is_better' | 'neutral';
  cadence: 'realtime' | 'minute' | 'hourly' | 'daily' | 'weekly';
  category: 'revenue' | 'margin' | 'marketing' | 'customer' | 'regional' | 'inventory';
  supportsBreakdowns: Array<'customer_type'|'channel'|'campaign_classification'|'region'>;
  formula: string; derivedFrom: string[]; isCurrency: boolean;
}
```

Two computation paths (canon/TECH/03 §3): **Path A** pre-materialized (ClickHouse MVs + scheduled rollups → `daily_metrics`, sub-100ms reads) for default views and standard breakdowns; **Path B** live ClickHouse query for arbitrary filters (e.g. "CM2 for pincode 110001 last month", p95 < 500ms). Every metric is per-`workspace_id`; **every metric drills down to its source rows** ([`kpi-dashboard-design`](../kpi-dashboard-design/SKILL.md)).

## Adding or changing a metric

1. Define/version it in the TS registry (the source of truth).
2. Regenerate the Python mirror (`tools/generate-metrics-registry.sh`); CI diffs and fails on mismatch.
3. Add a **parity test** with ≥3 representative rows including an **RTO/COD edge** and a **GST per-SKU edge**.
4. Wire it into the KPI surface via the registry — never reinvent the metric in the UI.
5. If it feeds the Morning Brief, confirm the daily-tick (Python) and any web display (TS) read the same definition.
6. Bump the metric version + update parity fixtures on any formula change.

## Anti-patterns (code-review blockers — canon §16)

- LLM-generated metric numbers.
- Inlining a formula in a React component or ad-hoc SQL instead of the registry → drift.
- A metric implemented in only one language → guaranteed parity failure.
- Margin without RTO/GST adjustment → systematically wrong for India.
- A single blended tax rate; `NUMERIC`/float money.
- Billing on placed (not realized/delivered) GMV; using ROAS as a P&L decision metric.

## Verify

- Parity test passes (TS output == Python output for shared fixtures).
- Spot-check one workspace + date: web KPI card == analytics-service value == Morning Brief value.
- Every dashboard metric drills to underlying orders/campaigns/shipments.

## References

- `canon/TECH/03_metrics_engine.md` — Formula Book §0, registry §2, materialization §4, Path A/B
- `canon/technical-requirements.md` §11 — metric registry + parity invariant
- [`india-commerce-economics`](../india-commerce-economics/SKILL.md) · [`region-adapter`](../region-adapter/SKILL.md) · [`clickhouse-olap`](../clickhouse-olap/SKILL.md) · [`kpi-dashboard-design`](../kpi-dashboard-design/SKILL.md)
