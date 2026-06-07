You are operating the **Engineering OS** under Codex. Read `AGENTS.md` at the repo root (the cross-runtime operating contract), then read `skills/watch/SKILL.md` and execute it for `$ARGUMENTS`.

> Mirrors the `watch` command-skill. Show the live pipeline activity stream — what every agent is thinking, planning, implementing, deciding, and handing off in real time. Reads .engineering-os/live.log; optionally filter by req_id.

Single-agent discipline: you play every role + reviewer hat yourself, honor the Iron Laws (verify before done; cheapest sufficient effort; tenant key on everything; reversible + audited), and **block yourself at any VETO gate** (Security CRITICAL/HIGH, QA missing smoke/parity) you would fail — Codex has no separate enforcing subagent. Journal to `.engineering-os/` as the skill specifies; where it says `${CLAUDE_PROJECT_DIR}`, use this repo's root.
