---
name: kpi-dashboard-design
description: Dashboard design discipline — visual hierarchy, KPI selection from the canonical metric registry (never reinvent), mobile-vs-desktop split, accessible/locale-correct rendering, charting patterns. Use when designing a dashboard page or chart. NOTE — the prior business's specific KPIs/rendering were reset; redefine domain KPIs from the new business canon + metric engine.
---

# KPI / Dashboard Design

The reusable discipline is intact; the **prior business's specific KPIs and locale rendering were reset** (business plan changed). Pull the actual metrics from the canonical metric registry (`metric-engine`) once it's redefined for the new business — never hard-code or reinvent metrics in the UI.

## Generic discipline (business-agnostic — keep)
- **Select KPIs from the metric registry**, don't invent them in the component (single source of truth; TS↔Python parity).
- **Visual hierarchy for a fast scan:** the most decision-relevant number first; progressive disclosure for detail.
- **Mobile vs desktop split:** dense analytical views are desktop-first; the mobile surface shows the few signals that matter.
- **Accessibility + locale:** WCAG AA contrast; render currency/numbers/dates in the product's locale (defined via `region-adapter` once re-fed).
- **Charting:** consistent, lightweight chart patterns; label clearly; avoid chartjunk.

## To re-fill (business-specific)
> _(to be defined from the new business canon + metric engine)_ — which KPIs matter, RAG thresholds, any domain overlays, the locale/currency rules.

*Prior business-specific content retained in git history.*
