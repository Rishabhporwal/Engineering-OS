---
name: dashboard
description: Generate a self-contained interactive HTML progress dashboard (pipeline board, agents, bugs, features, tokens/cost, activity) from .engineering-os memory. Visual companion to /team-digest.
disable-model-invocation: true
---

Generate the engineering progress dashboard — a visual board of what the team is building, by stage.

## Run

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/tools/dashboard.py" $ARGUMENTS
```

- Writes a **self-contained** `.engineering-os/dashboard.html` (no server, no external deps — works offline).
- Pass `--open` to open it automatically.
- Then tell the operator: `open .engineering-os/dashboard.html` (macOS) / `xdg-open` (Linux).

## What it shows (interactive tabs, vanilla JS — no CDN)

- **Overview:** KPIs (in-flight, shipped, open bugs, engineers, tokens, est. cost, lessons, events) + the **pipeline board** (cards by stage 1→8, lane-coloured) + lane & throughput charts.
- **Agents:** per-agent performance table (events, stages, VETOs, bounces, tokens, last-active) + charts. Click a header to sort.
- **Bugs:** total/open/resolved + filterable table (severity, type, feature, source, status). Bugs = decision-log bounces/VETOs + `findings/*.md`.
- **Features:** sortable, filterable table of every requirement — lane, stage, status, owner, engineer(s), bug count, tokens, started/shipped dates.
- **Tokens:** total tokens + est. cost, charts by agent / feature / stage / day (from `usage.jsonl`, logged per spawn by the orchestrator).
- **Activity:** recent decision-log feed.

## Notes

- It's a **snapshot** — regenerate to refresh. For the live per-step stream use `/watch`; for the text summary use `/team-digest`.
- **Token data** comes from `.engineering-os/usage.jsonl` (the orchestrator + `/approve` append per spawn). Cost is a rough estimate (blended $/1M: opus 30 · sonnet 6 · haiku 1.5).
- `dashboard.html` is gitignored (rebuildable). Reuses the `/team-digest` aggregation, so numbers match.
