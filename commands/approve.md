---
name: approve
description: Founder approval (Stage 7 → Stage 8).
arguments:
  - name: req_id
    description: The requirement to approve.
    required: true
  - name: note
    description: Optional approval note (caveats, strategic context).
    required: false
---

**This is the Founder gate.** Only run when you are the Founder (Rishabh).

Steps:

1. Read `.engineering-os/state/active.json`. Find `$1` (the req_id).
2. Verify status == `awaiting-founder`. If not, refuse: "Cannot approve — requirement is at stage X (status: Y). Either advance through the pipeline or use `/handoff` (with caveats)."
3. Read `11-final-review.md` in the run folder. Surface the CTO Advisor's recommendation. If REJECT, warn the Founder before letting them proceed.
4. Write `12-founder-decision.json`:
   ```json
   {
     "decision": "approved",
     "ts": "...",
     "actor": "rishabh",
     "note": "<optional note from $2>"
   }
   ```
5. Update `state/active.json`: status → `approved`, stage → 8, owner → `platform-devops`.
6. Append a decision-log entry of type `decision` with `actor: rishabh, decision: approved`.
7. Append journal under `platform.journal.md` ("Founder approval received").
8. **Invoke the `platform-devops` subagent** to run Stage 8.
9. Print: "Approved. Jatin is starting Stage 8."

If `$ARGUMENTS` was empty or req_id not found, print available `awaiting-founder` requirements.
