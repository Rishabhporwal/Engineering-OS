---
name: metric-engine
description: Brain's Metric Engine & Formula Book (canon/TECH/03) — single KPI source of truth, identical in TS + Python with CI parity. Revenue ladder, CM waterfall, MER/CAC, COD/RTO, Goal RAG.
---

# Metric Engine & Formula Book

Every number Brain shows comes from the **Formula Book** (canon/TECH/03 §0) — the canonical, versioned definition of each metric. Iron Rule: **a metric is defined once and computed identically in TypeScript (`packages/lib-metrics`) and Python (`pylibs/brain_metrics`).** Divergence is a P0 trust bug (a founder seeing two "CM2" numbers stops trusting Brain). This is the most important service in analytics-service.

**Canon:** `canon/TECH/03_metrics_engine.md` (Formula Book §0 + registry §2) · `canon/technical-requirements.md` §11.

## Four invariants
1. **Single definition.** One registry entry per metric; Python generated from the TS registry (`tools/generate-metrics-registry.sh`). Never inline a formula at a call site.
2. **TS↔Python parity is CI-gated.** Same inputs → same output to defined precision. A parity failure is a Tanvi QA **VETO** (`testing-tdd`).
3. **LLMs never produce metric numbers** — paradigm 1 (SQL/deterministic). The frontier LLM only enters at the Morning Brief synthesis boundary to *narrate* given numbers (`cost-routing-paradigms`).
4. **Money = integer minor units** (`Int64` paisa) + `currency_code`. Never `NUMERIC`/float for money. Region/currency formatting via `region-adapter`.

## The revenue ladder (each step GST-aware)
| Term | Formula | Note |
|---|---|---|
| Gross Sales | Σ line-item prices (pre-tax/discount/refund) | marketing-only; not P&L |
| Net Sales | Gross − Discounts − Refunds | still includes GST |
| Net Sales Net Tax | Net Sales − GST, extracted **per SKU slab** (0/5/18/40) | via `adapter.extract_net_revenue` |
| Net Revenue | GST-exclusive revenue | first-class input to all CM math |
| Realized / Delivered Revenue | Net Revenue from `status = delivered` (excl. RTO + cancelled) | **the honest number AND the billing base** |

GST is **per line item by SKU slab** — a blended rate is an anti-pattern (a 5% apparel + 40% luxury cart breaks a blend).

## The CM waterfall (canonical cost placement)
```
Gross Product Margin = Net Revenue − COGS                              (pre-variable view, not a CM step)
CM1 = Net Revenue − COGS − non-marketing variable costs
      (forward shipping, packaging, payment-gateway, COD handling, RTO/returns provisions, per-order CS)
CM2 = CM1 − Marketing Spend (paid media + influencer + affiliate + lifecycle msg cost)   ← the honest number
CM3 = CM2 − allocated Fixed Costs (salaries, agency, rent, software, warehouse)
Operating Profit = CM3 − founder salary / financing / one-offs
True CM2 = CM2 − RTO provision − late-refund provision − payment-failure provision        (India-honest)
```
If **CM1 < 0**, no marketing saves it — flag. If **CM2 < 0**, scale makes it worse. **Tax to government is never a cost.** Discounts apply at line-item level **before** GST.

## Marketing efficiency
| Metric | Formula |
|---|---|
| MER | Total Net Revenue ÷ Total Marketing Spend (blended) |
| aMER | New-Customer Net Revenue ÷ New-Customer Acquisition Spend |
| paMER | profit-adjusted (CM2 basis) |
| CAC | Marketing Spend ÷ **delivered** new customers (not placed) |
| CAC payback | months for cumulative cohort CM2 to cover CAC |
| LTV:CAC | cohort cumulative **CM2** ÷ cohort CAC (LTV via BG/NBD + Gamma-Gamma; retention via Kaplan-Meier) |
| ROAS (per channel) | channel revenue ÷ channel spend — **DISPLAY-ONLY, never the P&L decision metric** |

## COD / RTO metrics (India)
`rto_rate`, `rto_cost_per_order` (forward+reverse+restock+write-down), `cod_conversion_rate`, `prepaid_conversion_rate`, COD/prepaid mix at SKU/channel/pincode/AOV, and the **break-even COD RTO rate `r* = M/(M+C)`** (`india-commerce-economics`). RTO-adjusted CM2 is the default margin view.

## Goal RAG (each metric carries direction)
Higher-is-better: Green ≥95%, Amber 80–95%, Red <80% of goal. Lower-is-better: Green ≤105%, Amber 105–125%, Red >125%. Output always includes explanation + recommended action — never a bare colour.

## The registry
```typescript
export interface MetricDefinition {
  name: string; displayName: string;
  unit: 'currency_minor'|'count'|'ratio'|'percentage'|'days';
  direction: 'higher_is_better'|'lower_is_better'|'neutral';
  cadence: 'realtime'|'minute'|'hourly'|'daily'|'weekly';
  category: 'revenue'|'margin'|'marketing'|'customer'|'regional'|'inventory';
  supportsBreakdowns: Array<'customer_type'|'channel'|'campaign_classification'|'region'>;
  formula: string; derivedFrom: string[]; isCurrency: boolean;
}
```
Two paths (canon §3): **A** pre-materialized (CH MVs + rollups → `daily_metrics`, sub-100ms) for default views/standard breakdowns; **B** live CH query for arbitrary filters (p95 < 500ms). Every metric is per-`workspace_id`; **every metric drills to its source rows** (`kpi-dashboard-design`).

## Adding / changing a metric
1. Define/version in the TS registry (source of truth).
2. Regenerate the Python mirror; CI diffs and fails on mismatch.
3. Add a **parity test** with ≥3 rows including an **RTO/COD edge** and a **GST per-SKU edge**.
4. Wire into the KPI surface via the registry — never reinvent in the UI.
5. If it feeds the Morning Brief, confirm the daily-tick (Python) and web display (TS) read the same definition.
6. Bump the metric version + update parity fixtures on any formula change.

## Anti-patterns (code-review blockers)
LLM-generated metric numbers · inlining a formula in a component/ad-hoc SQL (drift) · a metric in only one language · margin without RTO/GST adjustment · blended tax rate · `NUMERIC`/float money · billing on placed (not realized) GMV · ROAS as a P&L decision metric.

## Verify
Parity test passes (TS == Python on shared fixtures) · spot-check one workspace+date: web KPI card == analytics value == Morning Brief value · every dashboard metric drills to underlying rows.

## References
`canon/TECH/03_metrics_engine.md` (Formula Book §0, registry §2, materialization §4) · `canon/technical-requirements.md` §11 · `india-commerce-economics` · `region-adapter` · `clickhouse-olap` · `kpi-dashboard-design`.
