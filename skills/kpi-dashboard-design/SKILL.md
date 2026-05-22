---
name: kpi-dashboard-design
description: Brain's profit-quality dashboard design (business §6/§8/§10 + canon/TECH/03/07/08) — Home/Command Center, Store Analytics, P&L, CM waterfall (Visx), cohort heatmap, MER/aMER/CAC cards, RTO/COD/pincode, Goal RAG (green ≥95%/amber 80–95%/red <80%), drill-down to source rows, realized-vs-placed revenue, Decision ROI (recovered ÷ fee), integration-health. Privilege CM2/CM3 over vanity ROAS; KPIs come ONLY from the metric registry; every metric drills to source; LLMs never invent numbers; currency-aware (₹ lakh/crore vs locale). Use when Ananya designs a dashboard page, Karan designs a Morning Brief variant, or anyone adds a chart.
---

# KPI / Dashboard Design — profit-quality surfaces

Brain's web UI is the wedge against incumbent dashboards: **Notion-level polish, Linear-level speed.** But the design discipline is what matters — every surface privileges **profit quality (CM2/CM3, recovered/protected revenue, RTO/COD truth)** over vanity ROAS. The dashboard's job is to answer *"are we making high-quality money today, and what should I do before the day gets away?"* — not to dump charts.

**Canonical sources:** `canon/business-requirements.md` §6/§8/§10 · `canon/TECH/03_metrics_engine.md` (registry) · `canon/TECH/07_frontend_architecture.md` (web) · `canon/TECH/08_alerts_reporting.md` (RAG + digests).

## The five non-negotiable rules

1. **KPIs come ONLY from the metric registry** (`packages/lib-metrics`) — never invent or inline a metric in a component. The card renders `METRICS[name]`'s value, unit, and direction ([`metric-engine`](../metric-engine/SKILL.md)).
2. **LLMs never produce numbers** — every figure on screen is a deterministic SQL/ML result; the AI panel narrates, the registry computes.
3. **Every metric drills to source rows** — a number you can't trace is a number a founder won't trust. Click any cell → drawer of underlying orders/campaigns/shipments/refunds (`trpc.drillDown.byMetric`).
4. **Privilege CM2/CM3 over ROAS** — ROAS is display-only, never the headline. Lead with contribution margin and realized revenue.
5. **Currency-aware rendering** — `formatMoney(amount, currency, format)`: INR → `₹4,82,000` / `₹4.8 L` / `₹3.2 Cr` (Indian grouping + lakh/crore), other currencies via locale. Never hardcode ₹ ([`region-adapter`](../region-adapter/SKILL.md)).

## Visual hierarchy for the 3-minute scan

The most decision-relevant number first; progressive disclosure for depth. **Home / Command Center** strip (business §7): live revenue + profit, a revenue-quality panel (CM2%, RTO risk, COD share), **Top-3 actions**, queues, **Decision ROI**, integration health. Mobile shows the few signals that matter ([`morning-brief-mobile`](../morning-brief-mobile/SKILL.md)); dense analytical views are desktop-first.

## The profit-quality surfaces (what to build)

| Surface | What it shows | Chart |
|---|---|---|
| **Home / Command Center** | live revenue+profit, revenue-quality, Top-3 actions, Decision ROI, integration health | KPI cards + sparklines |
| **Store Analytics** | revenue/orders/AOV by customer-type/channel, WoW | Recharts line/bar |
| **P&L** | the CM waterfall as a statement | Visx |
| **CM Waterfall** | Net Revenue → CM1 → CM2 → CM3, each step a bar (green = revenue/profit, red = deduction) | **Visx** (custom) |
| **Cohort heatmap** | acquisition month × age, CM2 retention (864 cells, virtualized) | **Visx** — desktop only |
| **Acquisition** | MER/aMER/CAC/payback cards vs goal | KPI cards + RAG |
| **Regional (IN)** | RTO, COD economics, pincode reliability, NDR queue | tables + heatmap |
| **Calendar Report** | one row/day, all metrics vs goal, with marketing-action overlays | CSS-grid (2,250 cells) |
| **Customer Lifecycle (NAC)** | new/returning/at-risk/churned movement | stacked area |

Charts: **Recharts** for line/bar/area/sparkline; **Visx** for waterfall/cohort heatmap/funnel; TanStack Table for sortable/virtualized tables. (On mobile it's `victory-native` — Recharts/Visx don't run on RN.)

## Goal RAG (the at-a-glance status)

Every goal-bearing metric carries a direction and renders a RAG cell with an explanation + recommended action (business §6, canon/TECH/08):

| Direction | Green | Amber | Red |
|---|---|---|---|
| higher-is-better | **≥95%** of goal | 80–95% | **<80%** |
| lower-is-better | **≤105%** of goal | 105–125% | **>125%** |

```typescript
function RagCell({ value, goal, currency }) {
  const status = ragStatus(value, goal.value, goal.type, goal.direction);
  return (
    <td className={cn(status === 'green' && 'bg-status-green-50',
                      status === 'amber' && 'bg-status-amber-50',
                      status === 'red'   && 'bg-status-red-50')}
        onClick={() => openDrillDown(date, metricName)}>
      {formatMoney(value, currency)} <span className="text-fg-muted">/ {formatMoney(goal.value, currency)}</span>
    </td>
  );
}
```

A bare colour is never enough — pair it with the why + the next action.

## Realized vs placed + Decision ROI

- Always surface **realized/delivered revenue alongside placed** — the honest number is the headline, placed is context (business §8 / §11.5). RTO/COD lag means placed flatters reality.
- **Decision ROI** card = recovered revenue ÷ Brain fee (the value-proof metric; target > 3× by month 3). CM2 recovered ÷ fee and operator-time-saved are companions.
- **Integration health** is part of the surface — a connector is "unhealthy" if data is stale even when auth works (P0 freshness < 1h). Label stale/estimated data explicitly; never render a confident number over stale inputs.

## India-specific rendering

₹ Indian grouping + lakh/crore compaction; GST-inclusive correction already done upstream (per-SKU); festival periods shaded on the Calendar Report with learned-lift tooltips; the Regional sidebar group (Pincodes/RTO/NDR/COD) only renders for `home_region = IN` ([`india-commerce-economics`](../india-commerce-economics/SKILL.md)).

## Accessibility + performance

WCAG AA contrast (RAG colours verified at 4.5:1); chart `<table>` fallback + ARIA on icon-only buttons; virtualize large grids (`content-visibility: auto`); skeletons matching each chart's layout; memoize chart transforms. Perf budget LCP < 2s, INP < 200ms ([`web-performance`](../web-performance/SKILL.md)).

## Anti-patterns

- Inventing/inlining a metric in a component instead of reading the registry.
- ROAS as the headline; hiding realized revenue behind placed.
- A metric that doesn't drill to source rows.
- Hardcoding ₹ / GST / Indian grouping in the chart layer (use `formatMoney` + the adapter).
- A confident number rendered over stale data with no freshness/estimated label.
- A bare RAG colour with no explanation or recommended action.
- Recharts/Visx on the mobile surface.

## Verify

- Each KPI card's value/unit/direction matches its registry entry; web == analytics-service == Morning Brief.
- Clicking any numeric cell opens a drill-down drawer with the underlying rows.
- INR renders Indian grouping + lakh/crore; a non-INR workspace renders its locale.
- RAG thresholds match green ≥95% / amber 80–95% / red <80% (higher-better).

## References

- `canon/business-requirements.md` §6/§8/§10 — metrics that matter, surfaces, RAG
- `canon/TECH/07_frontend_architecture.md` — web routes, charts, formatMoney, drill-down, Calendar Report
- `canon/TECH/08_alerts_reporting.md` — RAG cells, digests, integration health
- [`metric-engine`](../metric-engine/SKILL.md) · [`frontend-web`](../frontend-web/SKILL.md) · [`morning-brief-mobile`](../morning-brief-mobile/SKILL.md) · [`region-adapter`](../region-adapter/SKILL.md)
