---
name: reject
description: Stakeholder rejection (Stage 7) — bounces the requirement back with a reason.
disable-model-invocation: true
---

**This is the Stakeholder gate.** Only run when you are the Stakeholder (the human who files requirements and holds the deploy gate).

Rejection is not a deletion. The requirement bounces back to the Engineering Advisor with your reason; the Advisor decides where in the pipeline to re-route.

Steps:

1. Parse `$ARGUMENTS` into `req_id` and `reason`. If reason is empty, refuse — rejection without rationale is forbidden (the Stakeholder must always include a path forward).
2. Read `.engineering-os/state/active.json`. Find the req_id.
3. Write `12-stakeholder-decision.json`:
   ```json
   { "decision": "rejected", "ts": "...", "actor": "<stakeholder>", "reason": "<the reason from $ARGUMENTS>" }
   ```
4. Update `state/active.json`: status → `rejected`. Stage stays at 7 (terminal until the Advisor reroutes).
5. Append a decision-log entry: type `decision`, decision `rejected`, reason.
6. Append `cto-advisor.journal.md`: "Stakeholder rejected feat-X with reason: <reason>. Re-routing to stage Y because <the Advisor's analysis>."
7. **Invoke the `cto-advisor` subagent** to decide the re-route target stage.
8. Print: "Rejected. The Engineering Advisor will re-route based on your reason."

Tone: constructive. The Stakeholder is the source of truth on intent; rejection means "the engineering work is not what I want this to become." The team adapts; nobody is fired.
