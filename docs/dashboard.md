# Progress Dashboard (`/dashboard`)

> A **visual** view of everything the engineering team is building — a self-contained HTML pipeline board generated from the git-committed `.engineering-os/` memory. No server, no external deps, works offline on `file://`. The visual companion to `/team-digest` (text) and `/status`.

## Generate it

```
/dashboard            # writes .engineering-os/dashboard.html
/dashboard --open     # …and opens it in the browser
```

Then `open .engineering-os/dashboard.html` (macOS) / `xdg-open` (Linux). Regenerate any time to refresh — it's a snapshot of current state.

## What it shows
- **KPI tiles** — in-flight, shipped, challenges, engineers, lessons, decision events.
- **Pipeline board** — every in-flight requirement as a card in its stage column (1 Intake → 8 Deploy), colour-coded by lane (🟢 express · 🔵 standard · 🔴 high-stakes), with owner + engineer + status.
- **Lanes in flight**, **throughput** (shipped/day bars), **challenges & bounces** (per feature), **who's-working-on-what** (per engineer), **recently shipped**, and a **recent-activity feed** (last decision-log events).

## How it's built
- `tools/dashboard.py` reuses `team_digest.collect()` (so numbers match `/team-digest`), enriches with per-stage grouping + lane + throughput + a recent-events feed, and renders one self-contained HTML file (data rendered server-side; no client JS, no CDN).
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
