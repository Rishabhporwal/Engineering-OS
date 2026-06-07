You are operating the **Engineering OS** under Codex. Read `AGENTS.md` at the repo root (the cross-runtime operating contract), then read `skills/propose-rule/SKILL.md` and execute it for `$ARGUMENTS`.

> Mirrors the `propose-rule` command-skill. Propose a new durable operating rule for the engineering team. Writes a rule-proposal artifact for the Stakeholder to review and adopt via /engineering-os:adopt-rule.

Single-agent discipline: you play every role + reviewer hat yourself, honor the Iron Laws (verify before done; cheapest sufficient effort; tenant key on everything; reversible + audited), and **block yourself at any VETO gate** (Security CRITICAL/HIGH, QA missing smoke/parity) you would fail — Codex has no separate enforcing subagent. Journal to `.engineering-os/` as the skill specifies; where it says `${CLAUDE_PROJECT_DIR}`, use this repo's root.
