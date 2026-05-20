# Live Monitoring Mode (`/monitor`)

> Watch the running app in a real browser, catch console/network/runtime errors **as they happen**, triage what's real, and get actionable bugs **fixed through the pipeline** — without shipping past the human gate. This is the client-side complement to server-side observability (CloudWatch/OpenSearch/Sentry); it's the gstack `/canary` idea, Brain-grounded.

## The loop

```
/monitor <app-url>
   │
   ▼  browse.py monitor — real Chromium, watches console/page/network errors live
   │     (streams each [monitor] … line to the terminal + .engineering-os/live.log)
   ▼  triage each distinct issue by severity (drop noise, de-dupe)
   ├─ LOW  → finding only (findings/monitor.md)
   └─ HIGH/MED → open a fix /requirement
                    │
                    ▼ top-level orchestrator runs the pipeline
                    builder fixes → QA RE-RUNS browse check on that page (error gone?)
                    → Founder gate → deploy
```

Monitoring drives autonomy **up to** the Founder gate, not past it: the team detects and fixes, but a fix still clears QA + the human approval before it ships.

## What it detects (via `tools/browse.py monitor`)
Per watched URL, in real time over a `--duration` window (optionally re-sweeping every `--interval`):
- **page-error** — uncaught JS exceptions (app crashes)
- **console.error / warning** — app-logged errors
- **request-failed** — network failures
- **http-error** — 4xx/5xx responses

Each issue streams live to stderr (`[monitor] …`) and the run returns a JSON summary (`issue_count`, full lists); exit is non-zero if anything was caught. **Verified**: captures both load-time and *delayed* (timer/websocket) errors during the watch window.

## Two ways to run
- **On demand:** `/monitor http://localhost:3000 /dashboard` while developing or right after a deploy.
- **Continuous canary:** schedule it (`/schedule`) every N minutes against staging/prod; each run triages and opens fix requirements for *new* issues.

## Boundaries
- **Web only.** The RN/Expo mobile app isn't browser-renderable — use Expo web preview or device logs for the mobile Morning Brief.
- **Plugin-side tooling.** Playwright/Chromium lives in the plugin's `tools/`, not Brain's product runtime.
- **De-dupe is mandatory** — never open a second requirement for an already-tracked issue (check `findings/monitor.md` + open requirements).
- The live stream is `.engineering-os/live.log` (`/watch`); findings are committed in `findings/monitor.md`; the fix's durable trail is its requirement run folder + decision-log.
