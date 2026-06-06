---
name: decide
description: Stakeholder ruling that resolves a hard-gated requirement (e.g. a compliance lawful-basis gate) and resumes the pipeline. Fixes the gap where /resume couldn't satisfy a hard gate.
disable-model-invocation: true
---

You are recording a Stakeholder ruling that clears a hard gate and resumes a blocked requirement.

Invocation: `/decide <req-id> <ruling>`

A hard-gated requirement (e.g. a compliance lawful-basis gate declared in `COMPLIANCE.md`, a `blocked-on-dependency` state, a compliance-ambiguity escalation the Engineering Advisor raised) has no normal command — `/resume` does NOT satisfy a hard gate. This command makes the resolution explicit, logged, and resumable.

Steps:

1. **Read the gate.** Find `<req-id>` in `.engineering-os/state/active.json`. Confirm it is in a gated/blocked status (e.g. `blocked-on-dependency`, `awaiting-stakeholder`, a compliance hard-gate, or `build_gated_on` set). Read `.engineering-os/pending-stakeholder-attention.md` for the gate's question. If the requirement is NOT gated, say so and stop (use `/resume` for a normal interrupted run).

2. **Record the ruling.** Append an audit-log entry:
   ```json
   {"ts":"<UTC ISO>","actor":"stakeholder","type":"hard-gate-ruling","req_id":"<req>","gate":"<gate-name>","ruling":"<the Stakeholder's ruling text>"}
   ```
   Redact any secret/PII in the ruling text before writing.

3. **Clear the gate.** Update the requirement entry in `state/active.json` (write a `.bak` first): remove/clear the gating field (`build_gated_on`, `blocked-on-dependency`, `surface_to_stakeholder`), set `status`/`stage`/`current_owner` to where the pipeline resumes (the stage that was waiting on the gate). Remove the resolved item from `pending-stakeholder-attention.md`.

4. **Append the per-feature journal + the Engineering Advisor's journal** noting the ruling and that the gate is cleared, so the audit trail is complete.

5. **Resume.** Print: `Gate cleared for <req-id> by Stakeholder ruling. Resuming at Stage <N> (<owner>). Run /resume to continue, or the orchestrator will pick it up.` Then hand back to the orchestrator loop (`pipeline/orchestrator.md`) at the resumed stage.

A hard gate exists because something previously went wrong (a compliance basis must be recorded before processing PII, a dependency must ship first). This command does NOT bypass the gate's intent — it records the Stakeholder's authoritative resolution of it. If the ruling would itself violate a non-negotiable (e.g. "process PII with no lawful basis"), refuse and surface back to the Stakeholder via the Engineering Advisor.
