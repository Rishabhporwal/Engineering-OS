---
name: adopt-rule
description: Founder-only — adopt a proposed rule from .engineering-os/rule-proposals/ as a durable operating rule for the team. Promotes the proposal to .engineering-os/durable-rules/.
disable-model-invocation: true
---

Adopt a previously-proposed rule (from `/brain-engineering-os:propose-rule`) as a durable operating rule.

**This skill is Founder-only.** Verify the operator is Founder (Rishabh) before proceeding. If invoked by an agent (not Founder), refuse with "Only Founder can adopt rules. The proposal stays in `proposed` status until Rishabh runs this skill personally."

`$ARGUMENTS` is the `proposal_id` (the filename slug under `.engineering-os/rule-proposals/`).

## Steps

1. **Validate arguments + actor.** If `$ARGUMENTS` is empty, list pending proposals: `ls ${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals/`. Ask which to adopt. Confirm the actor is Founder.

2. **Locate the proposal.** Read `${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals/<proposal_id>.md`. If not found, list available proposals and ask the operator to pick.

3. **Surface the proposal for review.** Print the entire proposal content to the operator BEFORE adopting. Wait for explicit confirmation: "Confirm adopt by typing 'yes adopt'". This is a deliberate friction step — durable rules shape future agent behavior.

4. **On confirmation: generate the durable rule.**
   - `rule_id` = same slug as proposal (e.g., `qa-must-rerun-skipped-gates`).
   - `adopted_at` = `date -u +%Y-%m-%dT%H:%M:%SZ`.
   - Path = `${CLAUDE_PROJECT_DIR}/.engineering-os/durable-rules/<adopted-ts-no-colons>__<rule_id>.md`.
   - Template = `${CLAUDE_PLUGIN_ROOT}/templates/durable-rule.md`.
   - Copy rule text + scope + how-to-apply + exceptions verbatim from the proposal.

5. **Update the proposal** to record the decision. APPEND a "Decision" block to the proposal's `## Decision` section:
   ```
   | decided_at | <ts> |
   | decided_by | rishabh |
   | decision | adopted |
   | durable_rule_path | .engineering-os/durable-rules/<filename> |
   ```
   Do NOT delete or modify other content. The proposal stays in `.engineering-os/rule-proposals/` as audit-trail.

6. **Append decision-log events.**
   - `type: rule-adopted` with proposal_id, rule_id, scope.
   - `type: founder-decision` with `decision: adopted`, `target: rule-proposal`.

7. **Remove from pending-founder-attention.** Strike through the line in `pending-founder-attention.md` that was added by `propose-rule`.

8. **Notify the team.** Append to `${CLAUDE_PROJECT_DIR}/.engineering-os/durable-rules/INDEX.md` (create if missing):
   ```
   ## Active durable rules
   - `<rule_id>` — adopted <ts> — scope: <scope> — see `<filename>`
   ```

9. **Print to operator:**
   - Adopted rule path.
   - Effective immediately for all subagents invoked from now on.
   - To enforce the rule in this session, run `/reload-plugins`.

## Don't

- Don't adopt a proposal that contradicts an existing active durable rule without explicit supersession. If a proposal conflicts with an active rule, refuse and ask the operator to either (a) reject the proposal, or (b) re-propose it as an explicit supersession of the prior rule.
- Don't allow non-Founder operators (or agents) to invoke this skill. Refuse and surface the requirement to Founder via `pending-founder-attention.md`.
- Don't fabricate proposal content. Read the literal file; copy its fields.
