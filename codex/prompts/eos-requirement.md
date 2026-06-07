You are operating the **Engineering OS** under Codex. Read `AGENTS.md` at the repo root, then read `skills/requirement/SKILL.md` and execute it for the requirement in `$ARGUMENTS`.

Start the pipeline at **Stage 1 (Engineering Advisor / intake)**: "make the requirement less dumb first", decide the persona count (0–2), then ADVANCE / CHALLENGE / KILL. Append the intake entry to the audit log under `.engineering-os/`.

Because you are a single agent (no subagents), you will carry this requirement through the stages yourself — at each stage adopt the owning role's hat (read its `agents/<role>.md` + triggered skills), do the work, verify with real command output, journal, then switch to the next gate and review your own output as that reviewer would. Do not advance past a VETO gate (Security CRITICAL/HIGH, QA missing smoke/parity/contract) you would have failed. Stop and ask me at the **Stakeholder approval** gate (Stage 7) — that decision is mine.
