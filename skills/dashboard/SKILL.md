---
name: dashboard
description: Generate an interactive, PM-grade progress dashboard of all engineering work — a self-contained HTML app with tabs for Overview (pipeline board), Agent performance, Bugs, Features (sortable/filterable), Tokens & cost, and Activity, built from the git-committed .engineering-os memory. Open it in a browser; regenerate any time. The visual companion to /team-digest (text) and /status.
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

## What it shows (interactive tabs, vanilla JS — no CDN)
- **Overview:** KPIs (in-flight, shipped, open bugs, engineers, tokens, est. cost, lessons, events) + the **pipeline board** (cards by stage 1→8, lane-coloured) + lane & throughput charts.
- **Agents:** per-agent **performance table** (events, stages, VETOs, bounces, tokens, last-active) + charts (events-by-agent, tokens-by-agent). Click a column header to sort.
- **Bugs:** total/open/resolved + a **filterable table** — severity, type (gate bounce/VETO vs worker/monitor finding), feature, source, status. (Bugs = decision-log bounces/VETOs + `findings/*.md`.)
- **Features:** a **sortable, filterable table** of every requirement — lane, stage, status, owner, engineer(s), bug count, tokens, started/shipped dates.
- **Tokens:** total tokens + **est. cost**, with charts by agent / feature / stage / day (from `usage.jsonl`, logged per spawn by the orchestrator). Empty-state until runs accrue.
- **Activity:** recent decision-log feed.

## Notes
- It's a **snapshot** — regenerate with `/dashboard` to refresh. For the live per-step stream use `/watch`; for the text summary use `/team-digest`.
- **Token data** comes from `.engineering-os/usage.jsonl`, which the `/requirement` orchestrator + `/approve` append to after each agent spawn. Cost is a rough estimate (blended $/1M: opus 30 · sonnet 6 · haiku 1.5).
- `dashboard.html` is gitignored (derived/rebuildable). Reuses the `/team-digest` aggregation, so numbers match. Verified: all tabs render with **0 console errors** (checked via `browse.py`).
