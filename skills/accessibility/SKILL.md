---
name: accessibility
description: WCAG 2.2 AA as an ENFORCED CI gate (axe-core/pa11y) across web + native — keyboard/focus, chart fallbacks, status never colour-only, reduced-motion, mobile a11y.
---

# Accessibility — WCAG 2.2 AA, gated not asserted

Where the Canon requires "WCAG AA on every route" (`INVARIANTS.md` / `COMPLIANCE.md`), this skill makes it a CI blocker like tenant-isolation or the cost gate, not a manual hope. A colour-coded status dashboard is the highest-risk surface — a metric that signals Red/Amber/Green by colour alone is unreadable to ~8% of male users (deuteranopia/protanopia).

> **The one rule:** *every interactive element is keyboard-reachable, every status carries a non-colour signal, and every chart has a screen-reader fallback — verified in CI, not in someone's head.*

**Canon:** `INVARIANTS.md` (web + mobile a11y bar). Owners: Frontend/Web Engineer (web) + Mobile Engineer (mobile). Standard: **WCAG 2.2 Level AA** (2.2 adds focus-appearance, target-size ≥24px, dragging alternatives, accessible authentication — all relevant to thumb-first mobile surfaces).

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

## Status: never colour-only (the headline rule)

A status indicator (Green ≥95% / Amber 80–95% / Red <80% for higher-better) MUST carry a redundant non-colour channel — WCAG 1.4.1 is a hard fail otherwise.

```tsx
// packages/ui/data/StatusBadge.tsx — icon + text label, not just colour
const STATUS = {
  green: { icon: CheckCircle,   label: 'On track',  cls: 'bg-status-green-50 text-status-green-700' },
  amber: { icon: AlertTriangle, label: 'At risk',   cls: 'bg-status-amber-50 text-status-amber-700' },
  red:   { icon: XCircle,       label: 'Off track', cls: 'bg-status-red-50   text-status-red-700' },
};
export function StatusBadge({ status }) {
  const r = STATUS[status];
  return <span className={r.cls} role="status"><r.icon aria-hidden="true" /> <span>{r.label}</span></span>;
}
```

- **Status cells in tables:** add an icon glyph + an `aria-label` carrying the full verdict (label + formatted value) so screen reader + colourblind user both get it.
- **Contrast:** verify `status.*` tokens hit 4.5:1 for text (3:1 for the ≥24px badge as a graphical object). Use `-700` text on `-50` fill — never `-500` text on `-50` fill.

## Charts must have a screen-reader fallback

SVG charting libraries render `<svg>` with no semantics. Each chart provides a DOM equivalent:

| Chart | Fallback |
|---|---|
| **Waterfall** | visually-hidden `<table>`: each step a row with label + formatted value; SVG gets `role="img"` + summary `aria-label`. |
| **Cohort heatmap** (many cells) | `<table>` with row + column headers; each cell `aria-label` carrying its full meaning. Desktop-only — mobile links out. |
| **KPI cards / Sparkline** | card exposes number + status label as text (decorative sparkline `aria-hidden`). |
| **Line/Bar** | `role="img"` + `aria-label` summary; data also in the drill-down drawer table. |

Pattern: `<VisuallyHidden><DataTable/></VisuallyHidden>` beside every `<Chart aria-hidden="true">` — the SVG is decorative, the table is the truth (matches the "every number is auditable" obligation where the Canon requires one).

## Keyboard + focus management

- Every interactive element Tab-reachable; logical order; visible focus ring (WCAG 2.2 2.4.11) — never `outline:none` without a replacement.
- Modals/drawers (drill-down drawers, editor modals, side panels) trap focus, restore to trigger on close, close on `Esc` — use an accessible primitive library (shadcn/Radix), don't hand-roll.
- Command/search palettes: announce open via `aria-expanded`; any chat stream uses `aria-live="polite"`.
- Target size (2.5.8): action buttons ≥24×24px CSS (primary thumb targets are larger by design).

## prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
```
Mobile: read `AccessibilityInfo.isReduceMotionEnabled()` and skip chart animations.

## Mobile a11y

Each primary card: `accessibilityRole="summary"`, an `accessibilityLabel` reading problem → evidence → impact, action buttons as `accessibilityRole="button"` with explicit labels (not icon-only). Honour Dynamic Type / font scaling (don't pin font sizes); VoiceOver/TalkBack swipe order matches visual order; status carries the same icon+label redundancy as web.

## Anti-patterns (code-review blockers)

- Status by **colour alone** (the most common a11y bug); a route/chart merged with **no axe assertion**; `outline:none` with no focus replacement; a modal that doesn't trap/restore focus; a chart with **no table/`aria-label` fallback**; icon-only button with no label; pinned font sizes that break OS scaling; `-500` text on `-50` fill.

## Verify

- `playwright test a11y` → 0 violations on the gate routes.
- Tab through the densest tables/charts with no mouse; every cell/step reachable, focus visible.
- VoiceOver/TalkBack reads each primary card's verdict + actions.
- Greyscale the dashboard (devtools): status state still distinguishable by icon + label.

## References

- `INVARIANTS.md` / `COMPLIANCE.md` — canonical a11y bar; `engineering-os-blueprint/05-engineering-standards.md`
- [`frontend-web`] · [`mobile-surface`] · [`kpi-dashboard-design`] · [`region-and-locale`] (RTL/locale share the render layer)
