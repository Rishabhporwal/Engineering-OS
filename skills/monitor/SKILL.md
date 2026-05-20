---
name: monitor
description: Live monitoring mode — keep a real browser on the running app, watch console/network/runtime errors as they happen, triage what's real, and auto-open a fix requirement (which flows through the pipeline) for actionable bugs. Use for post-deploy canary watching or while developing. Owned by Jatin (DevOps, post-deploy) + Tanvi (QA, browser-error triage).
disable-model-invocation: true
---

Live monitoring mode: watch the running app, catch issues in real time, and get them fixed through the pipeline.

The app URL(s) to monitor (default `http://localhost:3000` if a dev server is up, else the deploy/staging URL):

> $ARGUMENTS

> Engine: `${CLAUDE_PLUGIN_ROOT}/tools/browse.py monitor` (real Chromium). Plugin-side tooling, not a Brain runtime dep.

## Procedure

1. **Resolve targets.** The base URL + the key pages/flows to watch (e.g. `/`, `/dashboard`, `/p&l`, the Morning Brief web view). Confirm the app is reachable.

2. **Watch live.** Run (tee the live stream into the activity log so `/watch` shows it too):
   ```sh
   uv run "${CLAUDE_PLUGIN_ROOT}/tools/browse.py" monitor <url> [<url2> …] --duration 120 --interval 30 \
     2> >(tee -a "${CLAUDE_PROJECT_DIR}/.engineering-os/live.log" >&2)
   ```
   Each `[monitor] console.error / page-error / request-failed / http-error …` line is streamed as it happens. The JSON summary (stdout) lists every issue + `issue_count`; exit is non-zero if any issue was seen.

3. **Triage each distinct issue** (don't act on noise):
   | Signal | Severity | Action |
   |---|---|---|
   | `page-error` (uncaught JS), 5xx on a core flow | **HIGH** | open a fix requirement now |
   | `console.error` from app code, 4xx on our API | **MED** | open a fix requirement |
   | transient / third-party / known-flaky | LOW | finding only, no requirement |
   - De-dupe against `.engineering-os/findings/monitor.md` and already-open requirements — never open a duplicate.

4. **Record findings** → append each to `.engineering-os/findings/monitor.md` (ts, severity, url, error, recommended action) — committed evidence.

5. **Get it fixed (the team fixes it).** For each HIGH/MED actionable bug, open a fix requirement:
   `/requirement Fix: <error> on <url> — <one-line repro from the monitor capture>`
   The top-level orchestrator runs it through the pipeline → the right builder (Ananya/Karan/Vikram/Maya) fixes it → **QA re-runs `browse.py check`/`monitor` on that page to confirm the error is gone** → Founder gate → deploy. The fix never ships without the gates — monitoring drives autonomy *up to* the human gate, not past it.

6. **Surface a summary:** issues found, severity split, findings written, requirements opened (with req_ids).

## Continuous monitoring (canary)
Schedule it for always-on post-deploy watching (gstack-style canary):
```
/schedule create monitor --cron "*/15 * * * *" --args "https://app.staging.brain... /dashboard" --model haiku
```
Each run watches, triages, and opens fix requirements for new issues. (Adjust to your `/schedule` syntax.)

## Notes
- Mobile (RN/Expo) isn't browser-renderable — for the mobile Morning Brief use Expo web preview or device logs; this mode is for the Next.js web app.
- The live stream goes to `.engineering-os/live.log` (watch with `/watch`); findings go to `findings/monitor.md`; the durable fix trail is the requirement's run folder + decision-log.
