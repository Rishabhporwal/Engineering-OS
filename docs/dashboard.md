# Progress Dashboard (`/dashboard`)

> A **visual** view of everything the engineering team is building — a self-contained HTML pipeline board generated from the git-committed `.engineering-os/` memory. No server, no external deps, works offline on `file://`. The visual companion to `/team-digest` (text) and `/status`.

## Generate it

```
/dashboard            # writes .engineering-os/dashboard.html
/dashboard --open     # …and opens it in the browser
```

Then `open .engineering-os/dashboard.html` (macOS) / `xdg-open` (Linux). Regenerate any time to refresh — it's a snapshot of current state.

## What it shows — interactive tabs (vanilla JS, no CDN)
- **Overview** — KPIs (in-flight · shipped · open bugs · engineers · tokens · est. cost · lessons · events) + the pipeline board (cards by stage 1→8, lane-coloured 🟢 express · 🔵 standard · 🔴 high-stakes) + lane & throughput charts.
- **Agents** — per-agent performance table (events · stages · VETOs · bounces · tokens · last-active), sortable, plus charts. The "who's pulling weight / where bounces originate" view.
- **Bugs** — total/open/resolved + a filterable table: severity · type (gate bounce/VETO vs worker/monitor finding) · feature · source · status. Bugs = decision-log bounces/VETOs + `findings/*.md`.
- **Features** — sortable, filterable table of every requirement: lane · stage · status · owner · engineer(s) · bug count · tokens · started/shipped.
- **Tokens** — total tokens + **est. cost**, charted by agent / feature / stage / day (from `usage.jsonl`).
- **Activity** — recent decision-log feed.

Tables sort on header-click and filter via the search box. Charts are hand-rolled inline SVG (no chart library, fully offline).

## Token usage & cost (where the data comes from)
The `/requirement` orchestrator and `/approve` append one line per agent spawn to `.engineering-os/usage.jsonl` (`{ts, req_id, agent, stage, total_tokens, model}`) — read from each Agent result's reported usage. The dashboard aggregates it into the Tokens tab. Cost is a **rough estimate** (blended $/1M tokens: opus 30 · sonnet 6 · haiku 1.5). Until runs accrue, the Tokens tab shows an empty state.

## How it's built
- `tools/dashboard.py` reuses `team_digest.collect()` (so numbers match `/team-digest`), enriches with per-stage grouping + lane + throughput + a recent-events feed, and renders one self-contained HTML file: the data is embedded as JSON and rendered by inline vanilla JS (no external deps, no CDN — fully offline on `file://`).
- **Verified**: generated from real Brain data and screenshot-rendered via `browse.py` — it draws correctly.

## The three views, when to use which
| View | Form | Use |
|---|---|---|
| `/dashboard` | visual HTML board | scan overall progress at a glance; share a snapshot |
| `/team-digest` | text summary | quick terminal read; cross-engineer awareness |
| `/watch` | live stream | follow a *running* pipeline step-by-step |

## Notes
- `dashboard.html` is **gitignored** (derived/rebuildable, like the semantic index + live.log). The durable record stays the journals + decision-log.
- It's a snapshot, not live — regenerate to refresh. (A `--watch`/auto-refresh mode could be added later if useful.)
- Web-page artifact only; nothing leaves your machine.
