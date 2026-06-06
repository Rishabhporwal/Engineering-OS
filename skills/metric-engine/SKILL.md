---
name: metric-engine
description: The single-source metric registry — one definition per metric, computed identically across every runtime with CI parity checked against an independent oracle. Money = minor units + currency_code.
---

# Metric Engine — the single-source metric registry

Every number the product shows comes from the **metric registry** (`METRICS.md` in the Product Canon) — the canonical, versioned definition of each metric. Iron Rule: **a metric is defined once and computed identically across every runtime/language** that needs it. Divergence is a P0 trust bug (a stakeholder seeing two different values for the "same" metric stops trusting the product).

**Canonical doc:** the Product Canon's `METRICS.md` (the registry) + `engineering-os-blueprint/05-engineering-standards.md §6` (data) and `06-quality-gates-and-metrics.md §3` (independent-oracle / verification validity).

## Four invariants
1. **Single definition.** One registry entry per metric; secondary-runtime mirrors are *generated* from the source-of-truth registry. **Never inline a formula at a call site.**
2. **Cross-runtime parity is CI-gated.** Same inputs → same output to a defined precision, across every runtime. **Parity is checked against an independent oracle** (a separately-derived reference, never the implementation comparing to itself — no tautological assertion). A parity failure is a QA **VETO** (`testing-tdd`).
3. **Models never produce metric numbers** — metrics are deterministic computation. A model may only enter at a narration boundary to *describe* given numbers, never to compute them (`cost-routing-paradigms`, `llm-evals` faithfulness gate).
4. **Money = integer minor units** + a `currency_code`. Never a floating-point or arbitrary-precision-decimal money type carried as a display value. Locale/currency formatting via the region adapter (`region-and-locale`).

## A metric ladder (a worked example — define yours in `METRICS.md`)
A derived-metric ladder makes each step a registry entry that depends only on lower steps. A revenue/margin example:

| Term | Formula | Note |
|---|---|---|
| Gross | Σ line-item amounts (pre-tax/discount/refund) | top-of-ladder input |
| Net | Gross − Discounts − Refunds | still tax-inclusive |
| Net of tax | Net − tax, extracted **per line-item tax class** | a blended tax rate is an anti-pattern |
| Realized | the net-of-tax amount for *fulfilled/settled* records only | **the honest number AND any billing base** |

Tax is **per line item by its tax class** — a blended rate breaks a mixed-class basket. The exact ladder, cost placement, and any margin steps are product-specific and live in `METRICS.md`; the *discipline* (one entry per step, depends only on lower steps, fulfilled-only for the honest number) is what transfers.

## Goal status (each metric carries a direction)
Each goal-bearing metric carries a direction and renders a status with an explanation + recommended action — never a bare colour (`accessibility`):

| Direction | Green | Amber | Red |
|---|---|---|---|
| higher-is-better | ≥95% of goal | 80–95% | <80% |
| lower-is-better | ≤105% of goal | 105–125% | >125% |

## The registry
```typescript
export interface MetricDefinition {
  name: string; displayName: string;
  unit: 'currency_minor'|'count'|'ratio'|'percentage'|'days';
  direction: 'higher_is_better'|'lower_is_better'|'neutral';
  cadence: 'realtime'|'minute'|'hourly'|'daily'|'weekly';
  category: string;                                  // product taxonomy
  supportsBreakdowns: string[];                      // e.g. 'channel','region','segment'
  formula: string; derivedFrom: string[]; isCurrency: boolean;
}
```
Two serving paths: **A** pre-materialized (rollups → a metrics table, sub-100ms) for default views/standard breakdowns; **B** a live query for arbitrary filters (p95 < 500ms). Every metric is per-tenant; **every metric drills to its source rows** (`kpi-dashboard-design`).

## Adding / changing a metric
1. Define/version it in the source-of-truth registry.
2. Regenerate the secondary-runtime mirror(s); CI diffs and fails on mismatch.
3. Add a **parity test** with ≥3 rows including the **edge cases** that historically break a blend (a mixed tax-class basket, a partially-fulfilled record, a refund) — asserted against an **independent oracle**.
4. Wire it into the surface via the registry — never reinvent in the UI.
5. If it feeds a defining surface, confirm every consumer reads the same definition.
6. Bump the metric version + update parity fixtures on any formula change.

## Anti-patterns (code-review blockers)
Model-generated metric numbers · inlining a formula in a component/ad-hoc query (drift) · a metric defined in only one runtime · a margin/net number without its tax/return adjustment · a blended tax rate over mixed classes · floating-point money · billing on a placed (not realized/fulfilled) basis · a display-only vanity ratio used as a decision metric · parity asserted against the implementation itself instead of an independent oracle.

## Verify
Parity test passes (every runtime agrees on shared fixtures, against the independent oracle) · spot-check one tenant+date: the web KPI card == the service value == any other consumer's value · every dashboard metric drills to underlying rows.

## References
Product Canon `METRICS.md` (the registry) · `engineering-os-blueprint/05-engineering-standards.md §6` · `engineering-os-blueprint/06-quality-gates-and-metrics.md §3` · `region-and-locale` · `kpi-dashboard-design` · `cost-routing-paradigms` · `llm-evals`.
