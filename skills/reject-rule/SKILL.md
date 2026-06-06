---
name: reject-rule
description: Founder-only — reject a proposed rule. Marks the proposal as rejected with a written reason; does NOT delete the proposal (audit trail).
disable-model-invocation: true
---

Reject a previously-proposed rule.

**Founder-only.** Same actor check as `/engineering-os:adopt-rule`.

`$ARGUMENTS` is `<proposal_id> <reason>` (the reason is required — silent rejection is forbidden).

## Steps

1. **Validate arguments.** If `$ARGUMENTS` is empty or missing the reason, refuse: "Rejection requires a reason. Run: `/engineering-os:reject-rule <proposal_id> <one-sentence reason>`."

2. **Locate the proposal.** Read `${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals/<proposal_id>.md`.

3. **Update the proposal** to record the rejection. APPEND to the `## Decision` section:
   ```
   | decided_at | <ts> |
   | decided_by | rishabh |
   | decision | rejected |
   | rationale | <reason> |
   ```

4. **Append decision-log events.** `type: rule-rejected` with proposal_id + reason.

5. **Remove from pending-founder-attention.** Strike through the line.

6. **Print to operator:** Proposal stays in `.engineering-os/rule-proposals/` as audit trail of what was considered and why it was rejected. If the operator wants to re-propose with revisions, they create a NEW proposal (new proposal_id); they don't edit the rejected one.

## Don't

- Don't delete the rejected proposal. Audit trail must persist.
- Don't reject without a reason. Future audits ask "why did this rule fail to land?" and need the answer.
