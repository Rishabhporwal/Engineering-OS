---
name: accessibility
description: WCAG 2.2 AA as an ENFORCED CI gate (axe-core/pa11y) across web + RN/Expo — keyboard/focus, chart fallbacks, RAG never colour-only, reduced-motion, mobile a11y.
---

# Accessibility — WCAG 2.2 AA, gated not asserted

Canon says "WCAG AA on every route" (TECH/07 §15) — this skill makes it a CI blocker like RLS or `@paradigm`, not a manual hope. The colour-coded RAG dashboard is the highest-risk surface — a P&L that signals Red/Amber/Green by colour alone is unreadable to ~8% of male operators (deuteranopia/protanopia).

> **The one rule:** *every interactive element is keyboard-reachable, every status carries a non-colour signal, and every chart has a screen-reader fallback — verified in CI, not in someone's head.*

**Canon:** TECH/07 §15 (web), TECH/10 (mobile). Owners: Ananya (web) + Karan (mobile). Standard: **WCAG 2.2 Level AA** (2.2 adds focus-appearance, target-size ≥24px, dragging alternatives, accessible authentication — all relevant to the thumb-first Morning Brief).

## The CI gate (the part that's missing today)

Web — `axe-core` via Playwright on every critical route + `pa11y-ci` on a route manifest:

```typescript
// apps/web/e2e/a11y.spec.ts — runs on PR-to-main, blocks merge
import AxeBuilder from '@axe-core/playwright';
for (const route of ['/', '/waterfall', '/analytics/cohorts', '/calendar', '/alerts']) {
  test(`a11y: ${route}`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag22aa']).analyze();
    expect(results.violations).toEqual([]);   // any violation fails the build
  });
}
```

Mobile — `@axe-core/react-native` in Detox E2E + RNTL accessibility queries (`getByRole`, `getByLabelText`). `eslint-plugin-jsx-a11y` is advisory-fast; **the axe run is the blocker**. Suppressions live in one reviewed file with a reason + expiry.

## RAG: never colour-only (the headline rule)

RAG status (Green ≥95% / Amber 80–95% / Red <80% for higher-better) MUST carry a redundant non-colour channel — WCAG 1.4.1 is a hard fail otherwise.

```tsx
// packages/ui/data/RagBadge.tsx — icon + text label, not just colour
const RAG = {
  green: { icon: CheckCircle,   label: 'On track',  cls: 'bg-status-green-50 text-status-green-700' },
  amber: { icon: AlertTriangle, label: 'At risk',   cls: 'bg-status-amber-50 text-status-amber-700' },
  red:   { icon: XCircle,       label: 'Off track', cls: 'bg-status-red-50   text-status-red-700' },
};
export function RagBadge({ status }) {
  const r = RAG[status];
  return <span className={r.cls} role="status"><r.icon aria-hidden="true" /> <span>{r.label}</span></span>;
}
```

- **Calendar Report RagCell:** add an icon glyph + `aria-label="CM3 ₹4.8L of ₹5L goal — off track"` so screen reader + colourblind operator both get the verdict.
- **Contrast:** verify `status.*` tokens hit 4.5:1 for text (3:1 for the ≥24px badge as a graphical object). Use `-700` text on `-50` fill — never `-500` text on `-50` fill.

## Charts must have a screen-reader fallback

Visx/Recharts render `<svg>` with no semantics. Each chart provides a DOM equivalent:

| Chart | Fallback |
|---|---|
| **CM Waterfall** | visually-hidden `<table>`: each step (Net Rev → −COGS → CM1 → −Marketing → CM2 …) a row with label + `formatMoney` value; SVG gets `role="img"` + summary `aria-label`. |
| **Cohort heatmap** (864 cells) | `<table>` with cohort-month row headers + period column headers; each cell `aria-label="Apr cohort, month 3 retention 41%"`. Desktop-only — mobile links out. |
| **RAG KPI cards / Sparkline** | card exposes number + RAG label as text (decorative sparkline `aria-hidden`). |
| **Line/Bar (Recharts)** | `role="img"` + `aria-label` summary; data also in the drill-down drawer table. |

Pattern: `<VisuallyHidden><DataTable/></VisuallyHidden>` beside every `<Chart aria-hidden="true">` — the SVG is decorative, the table is the truth (matches Brain's "every number is auditable" obligation).

## Keyboard + focus management

- Every interactive element Tab-reachable; logical order; visible focus ring (WCAG 2.2 2.4.11) — never `outline:none` without a replacement.
- Modals/drawers (DrillDownDrawer, GoalEditorModal, AI Side Panel) trap focus, restore to trigger on close, close on `Esc` — use shadcn/Radix, don't hand-roll.
- cmd+K / cmd+I: announce open via `aria-expanded`; AI chat stream uses `aria-live="polite"`.
- Target size (2.5.8): approve/reject/edit ≥24×24px CSS (Morning Brief thumb targets are larger by design).

## prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
```
Mobile: read `AccessibilityInfo.isReduceMotionEnabled()` and skip victory-native chart animations.

## Mobile a11y — the Morning Brief

Each of the three signal cards: `accessibilityRole="summary"`, an `accessibilityLabel` reading problem → evidence → impact, approve/reject/edit as `accessibilityRole="button"` with explicit labels (not icon-only). Honour Dynamic Type / font scaling (don't pin font sizes); VoiceOver/TalkBack swipe order matches visual order; RAG carries the same icon+label redundancy as web.

## Anti-patterns (code-review blockers)

- RAG/status by **colour alone** (the most common Brain a11y bug); a route/chart merged with **no axe assertion**; `outline:none` with no focus replacement; a modal that doesn't trap/restore focus; a chart with **no table/`aria-label` fallback**; icon-only button with no label; pinned font sizes that break OS scaling; `-500` text on `-50` fill.

## Verify

- `playwright test a11y` → 0 violations on the 5 gate routes.
- Tab through Calendar Report + Waterfall with no mouse; every cell/step reachable, focus visible.
- VoiceOver/TalkBack reads each Morning Brief card's verdict + approve/reject.
- Greyscale the dashboard (devtools): RAG state still distinguishable by icon + label.

## References

- TECH/07 §15/§16/§8/§7 · TECH/10 — canonical
- [`frontend-web`] · [`mobile-surface`] · [`morning-brief-mobile`] · [`kpi-dashboard-design`] · [`region-and-locale`] (RTL/locale share the render layer)
