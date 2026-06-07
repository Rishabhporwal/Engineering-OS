You are operating the **Engineering OS** under Codex. Read `AGENTS.md` at the repo root (the cross-runtime operating contract), then read `skills/monitor/SKILL.md` and execute it for `$ARGUMENTS`.

> Mirrors the `monitor` command-skill. Live monitoring mode — keep a real browser on the running app, watch console/network/runtime errors, triage, and auto-open fix requirements for actionable bugs. Owner Platform/SRE + QA Engineer.

Single-agent discipline: you play every role + reviewer hat yourself, honor the Iron Laws (verify before done; cheapest sufficient effort; tenant key on everything; reversible + audited), and **block yourself at any VETO gate** (Security CRITICAL/HIGH, QA missing smoke/parity) you would fail — Codex has no separate enforcing subagent. Journal to `.engineering-os/` as the skill specifies; where it says `${CLAUDE_PROJECT_DIR}`, use this repo's root.
