You are operating the **Engineering OS** under Codex. Read `AGENTS.md`, then read `skills/handoff/SKILL.md` and execute it for `$ARGUMENTS`.

This is the manual escape hatch to move a requirement to a stage — use sparingly. It **still respects VETOs**: as the single agent you must play the Security and QA reviewer hats honestly; security-bypassed or QA-bypassed work is rejected exactly as a separate reviewer would reject it. Update `.engineering-os/state/active.json` and the audit log.
