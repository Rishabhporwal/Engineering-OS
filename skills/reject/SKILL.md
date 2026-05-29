---
name: reject
description: Founder rejection (Stage 7) — bounces back with a reason.
disable-model-invocation: true
---

**This is the Founder gate.** Only run when you are the Founder (Rishabh).

Rejection is not a deletion. The requirement bounces back to the CTO Advisor with your reason; CTOA decides where in the pipeline to re-route.

Steps:

1. Parse `$ARGUMENTS` into `req_id` and `reason`. If reason is empty, refuse — rejection without rationale is forbidden (Founder must always include a path forward).
2. Read `.engineering-os/state/active.json`. Find the req_id.
3. Write `12-founder-decision.json`:
   ```json
   { "decision": "rejected", "ts": "...", "actor": "rishabh", "reason": "<the reason from $ARGUMENTS>" }
   ```
4. Update `state/active.json`: status → `rejected`. Stage stays at 7 (terminal until CTOA reroutes).
5. Append a decision-log entry: type `decision`, decision `rejected`, reason.
6. Append `cto-advisor.journal.md`: "Founder rejected feat-X with reason: <reason>. Re-routing to stage Y because <CTOA's analysis>."
7. **Invoke the `cto-advisor` subagent** to decide re-route target stage.
8. Print: "Rejected. CTOA will re-route based on your reason."

Tone: constructive. The Founder is the source of truth on intent; rejection means "the engineering work is not what I want this to become." The team adapts; nobody is fired.
