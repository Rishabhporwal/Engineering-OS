# Real-Browser & Visual QA (gstack-inspired)

> [gstack](https://github.com/garrytan/gstack)'s strongest edge over this OS was **real-browser QA + visual review** — opening actual Chromium to walk flows and screenshot UI, instead of trusting mocks. This adds that capability, mapped onto Tanvi (QA) and Ananya (web), while keeping everything git-native and Brain-grounded.

It closes the OS's biggest tooling gap: previously "QA" meant unit/contract/real-network smoke — nothing rendered a page or *looked* at it. Now it does.

---

## What it is (and isn't)

- **Engine:** [`tools/browse.py`](../tools/browse.py) — Playwright driving real Chromium.
- **Plugin-side dev tooling, NOT a Brain product dependency.** It lives in the plugin's `tools/` (alongside `memory_index.py`, `paradigm_check.py`) and runs via `uv`. It does **not** touch Brain's locked product stack — so no Brain ADR is needed. (The plugin's own tooling stack — uv, fastembed, sqlite-vec, playwright — is separate from Brain's product stack.)
- **Complements, doesn't replace** unit/contract/real-network tests and Playwright/Detox E2E.

---

## The engine — `browse.py`

All subcommands print JSON to stdout (agent-consumable) and exit non-zero when the page/flow isn't clean (CI/agent gate).

| Subcommand | Purpose |
|---|---|
| `check <url>` | Load a page; capture **console errors/warnings, page (JS) errors, failed requests, HTTP ≥400**, title; optional screenshot. The "is this page actually healthy" smoke. |
| `screenshot <url> --out f.png [--full-page]` | Capture pixels (for before/after design review). |
| `extract <url> --selector CSS [--attr]` | Pull text/attributes from elements. |
| `run <scenario.json> --artifacts DIR` | Walk a multi-step flow in one session (navigate/fill/click/wait/expect_text/expect_url/screenshot) with console+network capture and per-step + on-failure screenshots. |

First run auto-installs the Chromium binary (~150 MB), once. `EOS_NO_BROWSER_INSTALL=1` disables.

**Verified:** a healthy page returns `ok:true clean:true` + a real PNG; a broken page captured 2 console errors + 1 page error + 1 failed request (exit 2); a fill→click→assert→screenshot flow passed (exit 0).

---

## The two skills

### `/qa-browser` — Tanvi, Stage 5 (functional)
Health-checks the key pages, walks the critical flows in real Chromium, and **generates a Playwright regression spec** from each passing walk. Any console/page/network error is a Stage-5 finding. Both the exploratory browser walk and the durable regression spec are a Playwright spec — the same engine `browse.py` drives — so there's **one unified E2E engine, no parallel spec system** (Single-Primitive Rule).

### `/design-review` — Ananya, self-review (visual)
Screenshots before/after a UI change, then **scores each design dimension 0–10** ("what would a 10 look like?") via vision — typography, spacing, contrast, hierarchy, Indian rendering (₹/GST/festival), responsiveness, empty/loading/error states — and applies the high-value fixes as an atomic commit. Highest bar on the **Morning Brief** and the KPI/P&L/waterfall surfaces.

---

## Where it plugs into the pipeline

- **Stage 3 (Ananya):** `/design-review` in her self-review before handoff — catches visual issues early.
- **Stage 5 (Tanvi):** `/qa-browser` in her suite for any web-touching change — functional + console-error gate, plus regression-test generation.

Mobile (RN/Expo) isn't browser-renderable: use Expo web preview where available, else Karan's Detox E2E.

---

## Artifacts

Screenshots + JSON reports land in the feature's run folder (`.engineering-os/runs/<…>/qa/` and `/design/`) and are committed as QA/design **evidence**. Viewport screenshots are small (~10–50 KB); use git LFS for any >1 MB.

---

## Why this fits the OS's values

- **Git-native:** evidence in run folders, no external service.
- **Single-Primitive:** both the exploratory browser walk and the durable regression spec are Playwright — one engine (the same one `browse.py` drives), not two spec systems to maintain.
- **Verify-before-completion:** "QA passed" now includes *the page actually rendered without errors and looked right* — captured output, not a claim.
