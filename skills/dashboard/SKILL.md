---
name: dashboard
description: Generate a visual progress dashboard of all engineering work — a self-contained HTML pipeline board (requirements by stage, lanes, throughput, challenges, who's-working-on-what, recent activity) built from the git-committed .engineering-os memory. Open it in a browser; regenerate any time. The visual companion to /team-digest (text) and /status.
disable-model-invocation: true
---

Generate the engineering progress dashboard — a visual board of what the team is building, by stage.

## Run

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/tools/dashboard.py" $ARGUMENTS
```

- Writes a **self-contained** `.engineering-os/dashboard.html` (no server, no external deps — works offline).
- Pass `--open` to open it in the default browser automatically.
- Then tell the operator: `open .engineering-os/dashboard.html` (macOS) / `xdg-open` (Linux).

## What it shows
- **KPIs:** in-flight, shipped, challenges, engineers, lessons, decision events.
- **Pipeline board:** every in-flight requirement as a card in its stage column (1 Intake → 8 Deploy), colour-coded by lane (express / standard / high-stakes), with owner + engineer + status.
- **Lanes in flight**, **throughput** (shipped/day), **challenges & bounces** (per feature), **who's-working-on-what** (per engineer), **recently shipped**, and a **recent-activity feed** (last decision-log events).

## Notes
- It's a **snapshot** — regenerate with `/dashboard` to refresh (data comes from `.engineering-os/`, which updates as the pipeline runs). For the live per-step stream use `/watch`; for the text summary use `/team-digest`.
- `dashboard.html` is gitignored (derived/rebuildable, like the semantic index + live.log) — the durable record is the journals + decision-log.
- Reuses the `/team-digest` aggregation, so the numbers match.
