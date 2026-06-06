---
name: design-review
description: Visual design audit. Screenshots a page (before/after a change) with real Chromium, then scores each design dimension 0-10 with "what would a 10 look like?" and proposes concrete fixes. Use in the Frontend/Web Engineer's self-review for any visible web UI change, to protect the product's UI quality bar.
disable-model-invocation: true
---

Run a visual design review of a web UI change (Frontend/Web Engineer). Looks at the *rendered pixels*, not the code — catches what a 10/10 designer would catch.

> Engine: `${CLAUDE_PLUGIN_ROOT}/tools/browse.py` (Playwright/Chromium). First run auto-installs Chromium, once.

The page/URL under review (and optional "before" reference) is:

> $ARGUMENTS

## Procedure

1. **Capture screenshots** with real Chromium:
   ```sh
   uv run "${CLAUDE_PLUGIN_ROOT}/tools/browse.py" screenshot "<url>" --out "<run_folder>/design/after.png" --full-page
   ```
   If reviewing a change, also capture a "before" (from the prior commit / staging) as `before.png`. Capture at desktop width by default; re-run for a mobile viewport if the change is responsive.

2. **Read the screenshots** (vision) and **score each dimension 0–10**, and for each, state *what a 10 looks like* and the specific gap:

   | Dimension | Score | What a 10 looks like | Gap → fix |
   |---|:--:|---|---|
   | Typography (scale, weight, line-height) | | | |
   | Spacing & rhythm (grid, padding consistency) | | | |
   | Color & contrast (WCAG AA, palette discipline) | | | |
   | Visual hierarchy (what the eye hits first) | | | |
   | Locale rendering (currency symbol/format, numbering, date/RTL per the region seam) | | | |
   | Responsiveness (no overflow/clipping at target widths) | | | |
   | Empty / loading / error states | | | |

3. **Apply the high-value fixes** (anything scoring <8 on a dimension that matters for this surface), re-screenshot `after-fixed.png`, and confirm the score moved.

4. **Write `15-design-review.md`** into the run folder: the scored table, the before/after screenshots, and the fixes made. Make it an **atomic commit** separate from the feature code.

## Where this matters most
- The product's **primary, most-used surface** must be the highest-quality UI — design-review it every time it changes.
- Dense data views (KPI cards, tables, charts) — verify the locale-correct numbering/currency, status colors, and that dense data stays scannable in a quick scan.

## Notes
- Vision review is judgment; pair it with `/qa-browser` for the functional + console-error side.
- Screenshots are committed as design evidence (git LFS for any >1MB).
