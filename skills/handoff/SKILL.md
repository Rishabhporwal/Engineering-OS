---
name: handoff
description: Manually move a requirement to a stage (escape hatch).
disable-model-invocation: true
---

**Use sparingly.** This is the manual escape hatch. Normal flow uses the per-stage agent handoff signals (READY-FOR-SECURITY, etc.) and goes through the gate checks.

Manual handoff still respects VETOs — Shreya can reject security-bypassed work; Tanvi can reject QA-bypassed work.

Steps:

1. Parse `$ARGUMENTS` into `req_id` and `target_stage` (or status name).
2. Read `.engineering-os/state/active.json` and find the entry.
3. Read [`docs/quality-gates.md`](../../docs/quality-gates.md) — what gates would the normal path have checked? Surface any that would have been skipped.
4. **Require explicit confirmation from the operator** that they intend to skip those gates.
5. Update `state/active.json` (with `.bak.<ts>`).
6. Append a decision-log entry of type `manual-handoff` with rationale.
7. Append a journal entry under the new stage owner.
8. Print:
   - Old stage → new stage
   - Gates skipped (if any)
   - The new owner
   - Reminder: "VETO authority of subsequent agents still applies."

If the operator did not provide a rationale, ask for one before proceeding.
