---
name: kpi-dashboard-design
description: Dashboard design driven by the metric registry — visual hierarchy, drill-to-source, goal/RAG status, realized-vs-placed honesty, locale-aware money; KPIs ONLY from the registry, numbers never from a model.
---

# KPI / Dashboard Design — surfaces driven by the metric registry

A good dashboard answers a decision question — *"is the thing we care about on track today, and what should I do about it?"* — not "here are all the charts we could draw." Every surface privileges the **decision-relevant truth** over vanity metrics, and every number is a deterministic registry value.

**Canon:** the Product Canon's `METRICS.md` (the registry) + `TRIGGER-SURFACES.md` (which surfaces matter) + the web design section of `STACK.md`. See `engineering-os-blueprint/06-quality-gates-and-metrics.md`.

## The five non-negotiable rules

1. **KPIs come ONLY from the metric registry** — never invent/inline a metric in a component. The card renders the registry entry's value, unit, and direction ([`metric-engine`]).
2. **Models never produce numbers** — every figure is a deterministic computation; a narration panel may describe the numbers, the registry computes them.
3. **Every metric drills to source rows** — click any cell → a drawer of the underlying records (orders/events/shipments/etc.).
4. **Privilege the honest metric over the vanity one** — a flattering ratio is display-only, never the headline. Lead with the decision-relevant truth.
5. **Locale-aware rendering** — `formatMoney(amount_minor, currency_code, locale)`; never hardcode a currency symbol or grouping ([`region-and-locale`]).

## Visual hierarchy for the quick scan

Most decision-relevant number first; progressive disclosure for depth. A **home / command surface** typically carries: the headline status, a small set of **top ranked actions**, work queues, an ROI/impact signal, and integration/data health. A mobile surface shows the few signals that matter ([`mobile-surface`]); dense analytical views are desktop-first.

## Common dashboard surfaces (patterns that transfer)

| Surface | Shows | Chart |
|---|---|---|
| **Home / command** | headline status, top actions, impact, data health | KPI cards + sparklines |
| **Trend analytics** | a metric by dimension over time, WoW | line/bar (Recharts) |
| **A statement / ladder** | a derived-metric ladder as a step-down | waterfall (Visx) |
| **Cohort / retention** | acquisition period × age, a retention metric (virtualized) | heatmap (Visx) — desktop only |
| **Efficiency** | a ratio metric vs goal | KPI cards + RAG |
| **A dense grid** | one row per period, all metrics vs goal, action overlays | CSS-grid / virtualized table |
| **Movement** | state transitions over time | stacked area |

Charts: **Recharts** for line/bar/area/sparkline; **Visx** for waterfall/heatmap/funnel; a virtualized table component for large sortable grids. (Mobile uses a mobile-native chart lib.)

## Goal / RAG status (the at-a-glance signal)

Every goal-bearing metric carries a direction + renders a RAG status with an explanation + recommended action:

| Direction | Green | Amber | Red |
|---|---|---|---|
| higher-is-better | **≥95%** of goal | 80–95% | **<80%** |
| lower-is-better | **≤105%** of goal | 105–125% | **>125%** |

```typescript
function RagCell({ value, goal, currency }) {
  const status = ragStatus(value, goal.value, goal.type, goal.direction);
  return (
    <td className={cn(status==='green'&&'bg-status-green-50', status==='amber'&&'bg-status-amber-50', status==='red'&&'bg-status-red-50')}
        onClick={() => openDrillDown(date, metricName)}>
      {formatMoney(value, currency)} <span className="text-fg-muted">/ {formatMoney(goal.value, currency)}</span>
    </td>
  );
}
```
A bare colour is never enough — pair it with the why + the next action (a11y: never colour-only, [`accessibility`]).

## Realized vs placed + impact

- Always surface the **realized/settled value alongside the placed/exposed one** — the honest number is the headline, the optimistic one is context. Settlement lag means the placed number flatters reality.
- An **impact / ROI** card ties an action's effect to its cost — measured incrementally where possible ([`experimentation-holdouts`]), never from raw attributed volume.
- **Data/integration health** is part of the surface — a connector is "unhealthy" if data is stale even when auth works. Label stale/estimated explicitly; never render a confident number over stale inputs ([`data-quality`]).

## Locale-aware rendering

Currency grouping, symbol, and large-number abbreviation come from the locale via the region adapter; tax-inclusive corrections are done upstream (per line-item class, not in the chart layer); region-specific dimensions only render when the tenant's region calls for them ([`region-and-locale`]).

## Accessibility + performance

WCAG AA contrast (RAG verified at 4.5:1); chart `<table>` fallback + ARIA on icon-only buttons; virtualize large grids (`content-visibility: auto`); skeletons matching each chart's layout; memoize chart transforms. Perf budget LCP<2s, INP<200ms ([`web-performance`], [`accessibility`]).

## Anti-patterns

- Inventing/inlining a metric instead of reading the registry; a vanity ratio as headline / hiding the realized number behind the placed one; a metric that doesn't drill to source; hardcoding a currency symbol/grouping in the chart layer (use `formatMoney` + the adapter); a confident number over stale data with no freshness/estimated label; a bare RAG colour with no explanation/action; a desktop chart lib on mobile.

## Verify

- Each KPI card's value/unit/direction matches its registry entry; every consumer of the metric agrees.
- Clicking any numeric cell opens a drill-down drawer with the underlying rows.
- Money renders per the tenant's locale.
- RAG thresholds match green ≥95% / amber 80–95% / red <80% (higher-better).

## References

- Product Canon `METRICS.md` (the registry) · `TRIGGER-SURFACES.md` · the web design section of `STACK.md`
- [`metric-engine`] · [`frontend-web`] · [`mobile-surface`] · [`region-and-locale`] · [`accessibility`] · [`web-performance`] · [`experimentation-holdouts`] · [`data-quality`]
