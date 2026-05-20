---
name: metric-engine
description: Brain's Metric Engine & Formula Book (canon §14) — the single source of truth for every KPI definition (CM, aMER, RTO-adjusted CM, LTV, RFM, etc.), GST-inclusive + RTO-adjusted by default, and the TS↔Python parity discipline that Tanvi gates on. Use when adding/changing a metric, when a number disagrees between web and the daily tick, or when a metric must render in a KPI card. A metric is defined ONCE; both languages compute it identically.
---

# Metric Engine & Formula Book

Every number Brain shows a Founder comes from the **Formula Book** (canon/BRAIN_TECHNICAL.md §14) — the canonical, versioned definition of each metric. The Iron Rule: **a metric is defined once and computed identically in TypeScript (web/BFF) and Python (analytics/intelligence).** Divergence is a P0 trust bug — a Founder seeing two different "Net Margin" numbers stops trusting Brain.

## The discipline

1. **Single definition.** Each metric has one canonical formula in the registry (the source of truth both languages generate from / test against). Never inline a formula at a call site.
2. **TS↔Python parity is gated.** Tanvi's [`testing-tdd`](../testing-tdd/SKILL.md) runs **metric-registry parity** — the same inputs must yield the same output in both languages (to defined precision). A parity failure is a QA VETO.
3. **India-correct by default.** Margins are **RTO-adjusted** and **GST-inclusive** — Western tooling overstates margin ~18% by ignoring these ([`india-commerce-economics`](../india-commerce-economics/SKILL.md)). A metric that ignores RTO/GST is wrong, not approximate.
4. **Workspace-scoped + currency-aware.** Every metric is per-`workspace_id`; rendering uses the region's currency/format ([`region-adapter`](../region-adapter/SKILL.md), Indian numbering for ₹).

## Adding or changing a metric

1. Define/version it in the Formula Book registry (the canonical source).
2. Implement in BOTH languages from that definition (or codegen if available).
3. Add a **parity test** with at least 3 representative input rows (incl. an RTO/COD edge and a GST edge).
4. Wire it into the KPI surface via [`kpi-dashboard-design`](../kpi-dashboard-design/SKILL.md) — never reinvent the metric in the UI; consume the registry value.
5. If it feeds the Morning Brief, confirm the daily-tick (Python) and any web display (TS) read the same definition.

## Anti-patterns

- Inlining a formula in a React component or a SQL query instead of the registry → drift.
- A metric implemented in only one language → guaranteed parity failure later.
- Margin without RTO/GST adjustment → systematically wrong for India.
- Changing a formula without bumping its version + updating the parity fixtures.

## Verify

- Parity test passes (TS output == Python output for the shared fixtures).
- A spot-check: pick one workspace + date; the web KPI card value equals the analytics-service value equals the Morning Brief value.
