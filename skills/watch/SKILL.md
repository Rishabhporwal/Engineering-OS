---
name: watch
description: Show the live pipeline activity stream — what every agent is thinking, planning, implementing, deciding, and handing off in real time. Reads .engineering-os/live.log; optionally filter by req_id.
disable-model-invocation: true
---

Show the live agent-activity stream. Every agent appends a one-line progress marker to `.engineering-os/live.log` as it works (thinking / plan / edit / run / verify / handoff), prefixed `[persona·S<stage>·<req_id>]`.

Optional filter (a `req_id`):

> $ARGUMENTS

## Show it

- **Recent activity (default):** `tail -n 60 "${CLAUDE_PROJECT_DIR}/.engineering-os/live.log"`
- **Filtered to one requirement** (if `$ARGUMENTS` is a req_id): `grep -F "$ARGUMENTS" "${CLAUDE_PROJECT_DIR}/.engineering-os/live.log" | tail -n 80`
- **Follow live in a second terminal** (tell the operator — a slash command can't stream continuously):
  ```sh
  tail -f .engineering-os/live.log                   # whole team
  tail -f .engineering-os/live.log | grep <req_id>   # one requirement
  ```

Present the lines grouped by agent/stage so it reads as a play-by-play. If `live.log` doesn't exist yet, say so — it's created the moment the first agent starts working.

## Notes

- `live.log` is the **watch** stream (verbose, ephemeral, gitignored). The durable record is the per-agent/feature **journals** + the **decision-log** — use `/recall <feat-slug>` or `/team-digest`.
- The main terminal also shows the orchestrator's live narration (stage spawns + per-agent summaries) while a `/requirement` runs; `/watch` is the deeper per-step stream.
