---
name: approve
description: Founder approval (Stage 7 → Stage 8).
disable-model-invocation: true
---

**This is the Founder gate.** Only run when you are the Founder (Rishabh).

Steps:

1. Read `.engineering-os/state/active.json`. Find `$1` (the req_id).
2. Verify status == `awaiting-founder`. If not, refuse: "Cannot approve — requirement is at stage X (status: Y). Either advance through the pipeline or use `/handoff` (with caveats)."
3. **Render the DECISION CARD before asking for the call** (this is the one moment a human is required, and it triggers a production deploy — it must be the *best*-informed moment, not the thinnest). Read `11-final-review.md` for the CTO recommendation + risk, and assemble from data already on disk:
   ```
   ── Decision card · <req_id> ──────────────────────────────
   Lane:            <feature_class> · trigger surfaces: <list>
   CTO recommendation: <APPROVE/REJECT + one-line risk>
   Cost (this run): ~$<est> · <total_tokens> tokens   (from usage.jsonl: sum by req_id)
   Bounces:         <n>  (<delta>/<full>)              (from decision-log / usage review_scope)
   Diff:            <files changed>, <+adds/-dels>, services: <list>   (git diff --stat of staged paths)
   Verification:    real-network smoke <pass?> · metric parity <pass?> · negative-control <present?>
   Remaining risk:  <from final-review "risks remaining">
   ──────────────────────────────────────────────────────────
   ```
   Pull cost/tokens via `grep <req_id> usage.jsonl` (sum `total_tokens`); diff via `git diff --cached --stat` (or the dev-report's staged paths); the rest from `11-final-review.md` + `security-review`/`qa-review`. If the CTO recommendation is REJECT, lead with that and require an explicit override. Then ask for the approve/reject decision.
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
