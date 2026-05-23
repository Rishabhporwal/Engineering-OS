---
name: accessibility
description: WCAG 2.2 AA as an ENFORCED CI gate, not an assertion, across Brain's web (Next.js) + mobile (RN/Expo) surfaces. axe-core / pa11y gate on every route; keyboard nav + focus management; screen-reader support including chart fallbacks for the CM Waterfall / cohort heatmap / RAG cards; RAG colour-contrast for colourblind operators (never colour-only — always pair with icon + label); prefers-reduced-motion; mobile a11y for the Morning Brief. Use whenever Ananya builds a web route, Karan builds a mobile screen, a new chart or KPI card lands, or a RAG status is rendered. Owner: Ananya + Karan.
---

# Accessibility — WCAG 2.2 AA, gated not asserted

Canon says "WCAG AA on every route" (TECH/07 §15) — but there is **no current gate** enforcing it, so today it is an aspiration. This skill makes it real: a11y is a CI blocker like RLS or `@paradigm`, not a manual QA hope. The colour-coded RAG dashboard is the highest-risk surface — a P&L that communicates Red/Amber/Green by colour alone is unreadable to ~8% of male operators (deuteranopia/protanopia), and that's a meaningful slice of Indian DTC founders.

> **The one rule:** *every interactive element is keyboard-reachable, every status carries a non-colour signal, and every chart has a screen-reader fallback — verified in CI, not in someone's head.*

**Canonical source:** TECH/07 §15 (web a11y), TECH/10 (mobile). Owned by **Ananya** (web) + **Karan** (mobile). Target standard is **WCAG 2.2 Level AA** (2.2 adds focus-appearance, target-size ≥24px, dragging alternatives, accessible authentication — all relevant to the thumb-first Morning Brief).

## The CI gate (the part that's missing today)

Web — `axe-core` via Playwright on every critical route + `pa11y-ci` on a route manifest:

```typescript
// apps/web/e2e/a11y.spec.ts — runs in CI on PR-to-main, blocks merge
import AxeBuilder from '@axe-core/playwright';
for (const route of ['/', '/waterfall', '/analytics/cohorts', '/calendar', '/alerts']) {
  test(`a11y: ${route}`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
      .analyze();
    expect(results.violations).toEqual([]);   // any violation fails the build
  });
}
```

```yaml
# .github/workflows/a11y.yml
- run: pnpm --filter web exec pa11y-ci --config .pa11yci.json   # WCAG2AA standard
```

Mobile — `@axe-core/react-native` assertions in Detox E2E + RNTL accessibility queries (`getByRole`, `getByLabelText`) in component tests. Linting: `eslint-plugin-jsx-a11y` (web) is advisory-fast; the **axe run is the blocker**. Suppressions live in one reviewed file with a reason + expiry, same discipline as `vulnerability-scanning`.

## RAG: never colour-only (the headline rule)

RAG status (canon goal-RAG: Green ≥95% / Amber 80–95% / Red <80% for higher-better) MUST carry a redundant non-colour channel. WCAG 1.4.1 (Use of Colour) is a hard fail otherwise.

```tsx
// packages/ui/data/RagBadge.tsx — icon + text label, not just a colour
const RAG = {
  green: { icon: CheckCircle, label: 'On track',   cls: 'bg-status-green-50  text-status-green-700' },
  amber: { icon: AlertTriangle, label: 'At risk',  cls: 'bg-status-amber-50  text-status-amber-700' },
  red:   { icon: XCircle,    label: 'Off track',   cls: 'bg-status-red-50    text-status-red-700' },
};
export function RagBadge({ status }: { status: 'green'|'amber'|'red' }) {
  const r = RAG[status];
  return (
    <span className={r.cls} role="status">
      <r.icon aria-hidden="true" /> <span>{r.label}</span>   {/* shape + word, colour is decoration */}
    </span>
  );
}
```

- **Calendar Report RagCell** (TECH/07 §8): the cell already tints `bg-status-*-50`; add an icon glyph + `aria-label="CM3 ₹4.8L of ₹5L goal — off track"` so a screen reader and a colourblind operator both get the verdict.
- **Contrast:** verify the chosen `status.*` tokens hit 4.5:1 for text (3:1 for the ≥24px badge as a graphical object). The default `#10B981/#F59E0B/#EF4444` swatches need a darker `-700` text shade on the `-50` fill — do not put `-500` text on `-50` fill.

## Charts must have a screen-reader fallback

Visx/Recharts render `<svg>` with no semantics. Each Brain chart provides an equivalent reachable in the DOM:

| Chart | Fallback |
|---|---|
| **CM Waterfall** (Visx) | A visually-hidden `<table>`: each step (Net Rev → −COGS → CM1 → −Marketing → CM2 → …) as a row with label + signed minor-units value formatted by `formatMoney`. The SVG gets `role="img"` + `aria-label` summarising "CM2 ₹X.X L, down ₹Y from last period". |
| **Cohort heatmap** (Visx, 864 cells) | A `<table>` with cohort-month row headers + period column headers; each cell `aria-label="Apr cohort, month 3 retention 41%"`. Desktop-only per TECH/07 §13 — mobile links out, so the table is the web a11y path. |
| **RAG KPI cards / Sparkline** | Card exposes the number + RAG label as text (decorative sparkline `aria-hidden`); never communicate the trend by line colour alone. |
| **Line/Bar (Recharts)** | `role="img"` + `aria-label` summary; underlying data also available via the drill-down drawer table. |

Pattern: `<VisuallyHidden><DataTable .../></VisuallyHidden>` next to every `<Chart aria-hidden="true">` so the SVG is decorative and the table is the truth — which matches Brain's "every number is auditable" obligation anyway.

## Keyboard + focus management

- Every interactive element reachable by Tab; logical order; visible focus ring (WCAG 2.2 **2.4.11 Focus Appearance**) — never `outline:none` without a replacement.
- **Modals/drawers** (DrillDownDrawer, GoalEditorModal, AI Side Panel) trap focus, restore focus to the trigger on close, close on `Esc`. shadcn/Radix primitives do this — don't hand-roll.
- **cmd+K search / cmd+I AI panel:** announce open state via `aria-expanded`; the AI chat stream uses `aria-live="polite"` so new assistant tokens are announced without stealing focus.
- **Target size (WCAG 2.2 2.5.8):** approve/reject/edit buttons ≥24×24px CSS (the Morning Brief's thumb targets are far larger by design — keep them).

## prefers-reduced-motion

Skeleton shimmer, chart entrance animations, the AI streaming cursor, and Morning Brief card transitions all gate on the media query:

```css
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
```
Mobile: read `AccessibilityInfo.isReduceMotionEnabled()` and skip victory-native chart animations.

## Mobile a11y — the Morning Brief (the product)

The Morning Brief is the highest-quality UI in Brain (`morning-brief-mobile`); it must also be the most accessible. Each of the three signal cards: `accessibilityRole="summary"`, an `accessibilityLabel` reading problem → evidence → impact, and approve/reject/edit as `accessibilityRole="button"` with explicit labels (not icon-only). Honour Dynamic Type / font scaling (don't pin font sizes); support VoiceOver/TalkBack swipe order matching visual order; RAG signals carry the same icon+label redundancy as web.

## Anti-patterns (code-review blockers)

- RAG / status communicated by **colour alone** — no icon, no label. The single most common Brain a11y bug.
- A new route or chart merged with **no axe assertion** — the gate is the point.
- `outline:none` with no visible focus replacement; a modal that doesn't trap or restore focus.
- A Visx/Recharts chart with **no table/`aria-label` fallback** — screen-reader users get an empty SVG.
- Icon-only button (sidebar toggle, approve/reject) with no `aria-label`/`accessibilityLabel`.
- Pinned font sizes that break OS text scaling on the Morning Brief.
- Status text using a `-500` colour token on a `-50` fill (fails 4.5:1) — use `-700` text.

## Verify

- `pnpm --filter web exec playwright test a11y` → 0 violations on the 5 gate routes.
- Tab through the Calendar Report + Waterfall with no mouse; every cell/step reachable, focus always visible.
- VoiceOver/TalkBack reads each Morning Brief card's verdict and the approve/reject actions.
- Greyscale the dashboard (devtools rendering emulation): RAG state still distinguishable by icon + label.

## References
- TECH/07 §15 (web a11y) + §16 (i18n) + §8 (Calendar RagCell) + §7 (charts) — canonical
- TECH/10 — mobile architecture (Morning Brief surface)
- [`frontend-web`](../frontend-web/SKILL.md) — Next.js patterns these gates run against
- [`frontend-mobile`](../frontend-mobile/SKILL.md) — RN/Expo a11y APIs
- [`kpi-dashboard-design`](../kpi-dashboard-design/SKILL.md) — RAG selection + the 3-min Founder scan
- [`design-review`](../design-review/SKILL.md) — where a11y verdicts are gated alongside visual review
- [`i18n-rtl`](../i18n-rtl/SKILL.md) — RTL + locale formatting share the same render layer
