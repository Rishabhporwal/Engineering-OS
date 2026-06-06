---
name: qa-browser
description: Real-browser QA. Drives actual Chromium to walk critical user flows, capture console/network/JS errors and screenshots, and generate a Playwright regression spec from the walk. Use in the QA Engineer's Stage 5 for any web-touching change. Catches layout shifts, broken flows, auth issues, and runtime errors that mocks miss.
disable-model-invocation: true
---

Run real-browser QA against the app (QA Engineer, Stage 5, web changes). This verifies *rendered* behaviour, not mocks — it complements unit/contract tests, it does not replace them.

> Engine: `${CLAUDE_PLUGIN_ROOT}/tools/browse.py` (Playwright/Chromium — plugin-side dev tooling, NOT a product dependency). First run auto-installs Chromium (~150MB), once.

## Procedure

1. **Pick the target URL.** Local dev server (e.g. `http://localhost:3000`) if running, else the staging URL from the deployment context. Confirm it's reachable.

2. **Health-check the key pages** the change touches:
   ```sh
   uv run "${CLAUDE_PLUGIN_ROOT}/tools/browse.py" check "<url>" --screenshot "<run_folder>/qa/<page>.png"
   ```
   Inspect the JSON: `console_errors`, `page_errors`, `failed_requests`, `bad_responses`. **Any non-empty ⇒ a Stage-5 finding** (exit code 2). A clean page is `ok:true`.

3. **Walk the critical flow(s).** Write a scenario JSON (navigate / fill / click / wait / expect_text / expect_url / screenshot) for each user-visible flow the change affects, then:
   ```sh
   uv run "${CLAUDE_PLUGIN_ROOT}/tools/browse.py" run "<flow>.json" --artifacts "<run_folder>/qa/"
   ```
   A failing step stops the flow and saves a `FAIL-step-N.png`. Console/network errors during the walk are captured too.

4. **Generate a regression spec from the passing walk.** Translate the validated scenario into a **Playwright** spec (`@playwright/test`) under the app's `e2e/` (`*.spec.ts`), using `page.getByTestId(...)` + web-first assertions (`await expect(locator).toBeVisible()`). This is now **one unified engine** — the `/qa-browser` walk and the durable regression spec are both Playwright, the same engine `browse.py` already drives — which is *cleaner* for the Single-Primitive Rule (no second E2E system to maintain).

5. **Record** screenshots + the JSON reports under `<run_folder>/qa/`, and fold the verdict into `10-qa-review.md`. Capture the actual command output (no paraphrasing — verification-before-completion).

## Gate contribution (G5)
- [ ] Key pages `ok:true` (no console/page/network errors)
- [ ] Each critical flow scenario passes
- [ ] A Playwright regression spec exists for each newly-walked flow

## Notes
- This is for the **web** surface. A native mobile app isn't browser-renderable; use the framework's web preview if available, else fall back to the Mobile Engineer's device-level E2E (e.g. Detox/Maestro).
- Screenshots are viewport-sized (small) and committed as QA evidence; use git LFS for any >1MB.
