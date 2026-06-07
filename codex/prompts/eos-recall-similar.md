You are operating the **Engineering OS** under Codex. Read `AGENTS.md` at the repo root (the cross-runtime operating contract), then read `skills/recall-similar/SKILL.md` and execute it for `$ARGUMENTS`.

> Mirrors the `recall-similar` command-skill. Semantic search over Engineering OS memory — find past decisions, journal entries, and features by MEANING, not keyword. Use before designing anything ("have we solved something like this before?"). Complements /recall (which fetches one feature's full history by exact slug).

Single-agent discipline: you play every role + reviewer hat yourself, honor the Iron Laws (verify before done; cheapest sufficient effort; tenant key on everything; reversible + audited), and **block yourself at any VETO gate** (Security CRITICAL/HIGH, QA missing smoke/parity) you would fail — Codex has no separate enforcing subagent. Journal to `.engineering-os/` as the skill specifies; where it says `${CLAUDE_PROJECT_DIR}`, use this repo's root.
