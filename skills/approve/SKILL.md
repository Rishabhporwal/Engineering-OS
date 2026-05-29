---
name: approve
description: Founder approval (Stage 7 → Stage 8).
disable-model-invocation: true
---

**This is the Founder gate.** Only run when you are the Founder (Rishabh).

Steps:

1. Read `.engineering-os/state/active.json`. Find `$1` (the req_id).
2. Verify status == `awaiting-founder`. If not, refuse: "Cannot approve — requirement is at stage X (status: Y). Either advance through the pipeline or use `/handoff` (with caveats)."
3. Read `11-final-review.md` in the run folder. Surface the CTO Advisor's recommendation. If REJECT, warn the Founder before letting them proceed.
4. Write `12-founder-decision.json`:
   ```json
   { "decision": "approved", "ts": "...", "actor": "rishabh", "note": "<optional note from $2>" }
   ```
5. Update `state/active.json`: status → `approved`, stage → 8, owner → `platform-devops`.
6. Append a decision-log entry of type `decision` with `actor: rishabh, decision: approved`.
7. Append journal under `platform.journal.md` ("Founder approval received").
8. **Drive Stage 8 (you are top-level — you have the Agent tool).** Spawn the `platform-devops` subagent for Stage 8, passing the absolute `${CLAUDE_PLUGIN_ROOT}` + `${CLAUDE_PROJECT_DIR}` and the note "you have no Agent tool — do Stage 8, persist artifacts/state/journals, return a HANDOFF block." Read its returned HANDOFF + state:
   - `shipped` / `monitoring` → done; print the deployment summary.
   - `rolled-back` (BOUNCE) → the rollback re-enters Stage 4: spawn `security-reviewer`, then continue the orchestration loop (per `pipeline/orchestrator.md`).
   After the spawn returns, append a token-usage line to `.engineering-os/usage.jsonl` (full-breakdown format per `pipeline/orchestrator.md`: `{ts,req_id,agent:"platform-devops",stage:8,total_tokens,input_tokens,output_tokens,cache_read_tokens,cache_creation_tokens,model:"sonnet"}` — pull the split from the Agent result's `usage` object; omit any field the harness doesn't surface, never fabricate).
9. Print: "Approved. Jatin ran Stage 8 → <final status>."

If `$ARGUMENTS` was empty or req_id not found, print available `awaiting-founder` requirements.
