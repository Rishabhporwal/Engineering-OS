---
name: monitor
description: Live monitoring mode — keep a real browser on the running app, watch console/network/runtime errors, triage, and auto-open fix requirements for actionable bugs. Owner Platform/SRE + QA Engineer.
disable-model-invocation: true
---

Live monitoring mode: watch the running app, catch issues in real time, and get them fixed through the pipeline.

The app URL(s) to monitor (default `http://localhost:3000` if a dev server is up, else the deploy/staging URL):

> $ARGUMENTS

> Engine: `${CLAUDE_PLUGIN_ROOT}/tools/browse.py monitor` (real Chromium). Plugin-side tooling, not a product runtime dep.

## Procedure

1. **Resolve targets.** Base URL + key pages/flows to watch (e.g. `/`, `/dashboard`, the product's primary surfaces). Confirm the app is reachable.
2. **Watch live.** Run (tee the stream into the activity log so `/watch` shows it too):
   ```sh
   uv run "${CLAUDE_PLUGIN_ROOT}/tools/browse.py" monitor <url> [<url2> …] --duration 120 --interval 30 \
     2> >(tee -a "${CLAUDE_PROJECT_DIR}/.engineering-os/live.log" >&2)
   ```
   Each `[monitor] console.error / page-error / request-failed / http-error …` line streams as it happens. The JSON summary (stdout) lists every issue + `issue_count`; non-zero exit if any issue seen.
3. **Triage each distinct issue** (don't act on noise):
   | Signal | Severity | Action |
   |---|---|---|
   | `page-error` (uncaught JS), 5xx on a core flow | **HIGH** | open a fix requirement now |
   | `console.error` from app code, 4xx on our API | **MED** | open a fix requirement |
   | transient / third-party / known-flaky | LOW | finding only, no requirement |
   De-dupe against `.engineering-os/findings/monitor.md` and already-open requirements.
4. **Record findings** → append each to `.engineering-os/findings/monitor.md` (ts, severity, url, error, recommended action).
5. **Get it fixed (the team fixes it).** For each HIGH/MED actionable bug:
   `/requirement Fix: <error> on <url> — <one-line repro from the monitor capture>`
   The orchestrator runs it through the pipeline → the right builder fixes it → **QA re-runs `browse.py check`/`monitor` on that page to confirm the error is gone** → Stakeholder gate → deploy. Monitoring drives autonomy *up to* the human gate, not past it.
6. **Surface a summary:** issues found, severity split, findings written, requirements opened (with req_ids).

## Continuous monitoring (canary)

```
/schedule create monitor --cron "*/15 * * * *" --args "https://app.staging.example.com /dashboard" --model haiku
```

## Notes

- A native mobile surface isn't browser-renderable — use the framework's web preview or device logs; this mode is for the web app.
- Live stream → `.engineering-os/live.log` (watch with `/watch`); findings → `findings/monitor.md`; durable fix trail → the requirement's run folder + the OS audit trail.
