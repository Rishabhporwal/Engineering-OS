---
name: kpi-dashboard-design
description: Dashboard design discipline for Brain — KPI selection from the canonical metric registry (never reinvent), visual hierarchy for the 3-min Founder scan, mobile-vs-desktop split, India-specific rendering (₹, GST inclusive, festival overlay), Visx + shadcn patterns. Use when Ananya designs a new dashboard page, when Karan designs a Morning Brief variant, when adding a chart, or when the Founder asks for "a way to see X at a glance".
---

# KPI Dashboard Design

Brain **is** a dashboard. The discipline of which KPI to show, where it lives in the visual hierarchy, and what NOT to render is the difference between an operator opening Brain daily versus quarterly.

## Why this matters for Brain

Brain's surface split (see canon/BRAIN_TECHNICAL.md):

| Surface | Time on task | Density | Owner |
|---|---|---|---|
| **Mobile Morning Brief** | 3 minutes / day, 06:55–09:00 IST | Three signals, thumb-first | Karan |
| **Mobile dashboards** | Quick checks during day | Sparse, glanceable | Karan |
| **Web dashboard** | 5–30 min, Monday review + on-demand depth | Dense, drillable | Ananya |

Same KPIs, different rendering. The web's CM Waterfall is a 12-cell drill-down view. Mobile's CM Waterfall is **a single number + a sparkline + "tap for detail"**.

## Brain's KPI registry is canonical — NEVER reinvent

Every metric Brain shows lives in `packages/lib-metrics` (TS) + `pylibs/brain_metrics` (Python). The formulas are versioned, parity-tested (`testing-tdd` mutation testing 90%+), and documented in canon/BRAIN_TECHNICAL.md. **You do not invent a new metric in a dashboard.** If a real new KPI is needed, propose it to Maya → Aryan → enter the registry → THEN render it.

### The Brain canon (from `memory/business-context.md`)

| Goal | KPI | Where it lives |
|---|---|---|
| **Profitability** | MER, aMER, paMER, iROAS (Phase 4) | `lib-metrics/mer.ts` |
| | CM1, CM2, CM3 | `lib-metrics/cm.ts` |
| **Acquisition** | New customers, conversion rate, CAC | `lib-metrics/acquisition.ts` |
| **Retention** | NAC (Net Active Customers), churn thresholds (P40/P80 data-derived) | `lib-metrics/nac.ts` |
| **Mix** | First Product Cascade, cohort by first-product × window | `lib-metrics/cascade.ts` |
| **India** | RTO per pincode × courier × AOV, COD %, NDR % | `lib-metrics/india.ts` |
| **Lifecycle (Phase 2+)** | RFM segment counts, recovered revenue | `lib-metrics/lifecycle.ts` |
| **Cost** | Per-brand LLM spend vs cap, paradigm distribution | `lib-metrics/cost.ts` |

Don't add "Burn Rate" or "MRR" or "DAU/MAU" from generic SaaS playbooks. Brain is a DTC commerce OS — the canon is different.

## Visual hierarchy (the Founder's 3-min scan)

Mobile Morning Brief (Karan):
- **Hero**: today's biggest signal (1 number + 1 sentence)
- **Two supporting signals**: 1 number each, no chart
- **Approve / Reject / Edit** on each
- That's it. No drill-down on mobile.

Desktop dashboard landing (Ananya):
```
┌────────────────────────────────────────────────────────────────┐
│  MER  ↑ 12%      aMER  ↑ 8%      CM2  ↓ 2%      NAC  ↑ 5%     │   ← 4 hero cards, 7d vs prior 7d
│  3.4x             2.8x            ₹1.2L          412            │
├──────────────────────────────────┬─────────────────────────────┤
│                                  │                             │
│   CM Waterfall (filterable)      │   First Product Cascade     │
│   Visx — 12 cells, drillable     │   Table — top 5 + drill    │
│                                  │                             │
├──────────────────────────────────┼─────────────────────────────┤
│                                  │                             │
│   Cohort Heatmap (24 × 36)       │   Pincode Reliability       │
│   Desktop only                   │   India map + table         │
│                                  │                             │
└──────────────────────────────────┴─────────────────────────────┘
```

Rule: **a dashboard page has ≤7 distinct things on it**. More than that and the Founder skips it.

## Comparison is mandatory

A number without a comparison is noise. Every Brain number ships with:
- **vs prior period** (7d vs prior 7d, MTD vs prior MTD, festival vs same-festival-last-year)
- **Trend sparkline** (last 14 days or last 12 weeks depending on cadence)
- **Threshold context** (is this number good/warning/bad — colored accordingly)

```tsx
// packages/ui — KPI card primitive used everywhere
<KpiCard
  label="MER"
  value={3.4}
  format="multiplier"               // → "3.4x"
  delta={{ value: 0.41, vs: '7d prior', direction: 'up', kind: 'good' }}
  sparkline={metric.last14d}
  onDrill={() => router.push('/mer')}
/>
```

## Color coding (Brain palette)

Use semantic intent, not arbitrary brand color, for numeric direction. Tailwind tokens from `packages/ui/tokens`:

```tsx
// MER up 12% → green
const goodColor = 'text-emerald-600 dark:text-emerald-400';   // healthy
const warnColor = 'text-amber-600 dark:text-amber-400';       // attention
const badColor  = 'text-rose-600 dark:text-rose-400';         // problem
```

**India-specific:** RTO over 25% is red; festival lift "below seasonal average" is red even if absolute is up.

## Chart selection (Brain canon)

| Data shape | Chart | Library |
|---|---|---|
| Trend over time | Line (sparkline for cards; full Visx for drill-down) | Visx |
| Composition (CM1 → CM2 → CM3) | **Waterfall** (the Brain hero chart) | Visx (custom build, canon/BRAIN_TECHNICAL.md) |
| Cohort retention | **Heatmap** 24×36 grid | Visx |
| Mix-by-segment | Stacked bar | Visx |
| Distribution (AOV, pincode reliability) | Histogram | Visx |
| Funnel (NDR → delivery → refund) | Funnel | Visx |
| Comparison across N items | Horizontal bar (sorted descending) | Visx |
| **NEVER** pie/donut | Banned. They lie about proportion. Use stacked bar. | — |

**No Recharts.** Brain uses Visx (locked stack). Pick one.

## India-native rendering rules

| Concern | Rendering rule |
|---|---|
| Currency | `₹` prefix; **lakh/crore** formatting (`₹1.2 Cr`, not `₹120,000,000`) for values > ₹1L; `Intl.NumberFormat('en-IN')` for grouping |
| Dates | `DD MMM` (e.g., "13 May") — never `MM/DD/YYYY` |
| Time | 24-hour for system events, 12-hour `am/pm` for user-facing (Morning Brief at "7:00 am IST") |
| GST | Every revenue/margin display is GST-net. If the brand wants gross, expose a toggle — default is net |
| Festivals | Festival overlay band on every time-series (canon/BRAIN_TECHNICAL.md); Diwali, Holi, Eid, Rakhi, Christmas |
| Pincode | Render with state + tier (e.g., "411014 · Pune · Tier-2"); reliability score color-coded |
| Phone numbers | Mask middle digits if Phase 3 inbox shows customer phone (PII discipline) |

## Drill-down pattern (web only — mobile escapes to web)

Every dashboard cell that represents an aggregate is drillable:

```
Cell shows "₹2.4L spend"
  → click opens drawer
    → drawer shows the campaigns/days/products that compose ₹2.4L
      → click row shows the underlying orders (Cypress test: 3 clicks max to raw data)
```

Mobile cells don't drill. They show "View on desktop →" if the user taps. Karan owns this UX call.

## Interactivity features Brain ships

- **Date range** selector (nuqs URL state — bookmarkable)
- **Filter by segment** (acquisition vs non-acq, COD vs prepaid, RFM segment)
- **Drill-down drawer** (web only)
- **Export to CSV** (Phase 2+ — heavy use by accountants)
- **Scheduled email** report (Phase 3 — Vikram's notifications-service)

## Common mistakes (avoid these)

- **Too many KPIs** — 7+ KPIs per dashboard means none of them get attention
- **No comparison** — "3.4x MER" tells me nothing; "3.4x, up 12% from last week" tells me everything
- **Stale data without disclosure** — if a number is from 06:55 IST and we're now at 14:00, show "as of 06:55 IST" or refresh
- **Generic SaaS KPIs** — MRR, DAU/MAU don't apply to DTC commerce; CM2 and NAC do
- **Pie charts**
- **Tiny sparklines** without numeric labels
- **Mobile dashboards that try to be desktop dashboards** — different jobs, different UX

## Best practices

- **≤7 KPIs per page**
- **Trends, not snapshots** — sparkline on every card
- **Consistent color coding** for direction (green/amber/red)
- **Comparison period** required on every number
- **Real-time or hourly** data refresh (most Brain metrics are hourly via ClickHouse MV)
- **Review dashboard relevance quarterly** with the Founder — drop what's not opened
- **Empty states matter** — a brand with no Shopify yet should see "Connect Shopify to see this" not "0.00"

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Web dashboard layout + drill-down | **Ananya** | canon/BRAIN_TECHNICAL.md (frontend) |
| Mobile Morning Brief + dashboard | **Karan** | canon/BRAIN_TECHNICAL.md, `morning-brief-mobile` |
| Canonical metric registry | **Maya** | canon/BRAIN_TECHNICAL.md, `lib-metrics` + `brain_metrics` |
| India-specific rendering | **Ananya** + **Maya** | canon/BRAIN_TECHNICAL.md (UI) |
| Empty/loading states | **Ananya** + **Karan** | canon/BRAIN_TECHNICAL.md (states) |
| Performance budget (LCP/INP) | **Ananya** | `web-performance` |

Related Brain skills: `frontend-web`, `frontend-mobile`, `morning-brief-mobile`, `web-performance`, `india-commerce-economics` (the rules behind India-native rendering), `engineering-discipline` (Simplicity First applies to dashboard design too).
