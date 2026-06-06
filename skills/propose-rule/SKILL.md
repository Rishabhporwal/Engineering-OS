---
name: propose-rule
description: Propose a new durable operating rule for the engineering team. Writes a rule-proposal artifact for the Stakeholder to review and adopt via /engineering-os:adopt-rule.
disable-model-invocation: true
---

Propose a new operating rule for the engineering team.

Any agent or operator may invoke this skill to propose a rule. **Agents cannot adopt their own proposals** — only the Stakeholder can run `/engineering-os:adopt-rule` to promote a proposal to a durable rule.

`$ARGUMENTS` is a short kebab-case slug describing the rule (e.g., `no-auto-commit-of-code`, `qa-must-rerun-skipped-gates`, `persona-count-capped-at-2`).

## Steps

1. **Validate arguments.** If `$ARGUMENTS` is empty, ask the operator: "What rule are you proposing? Give me a kebab-case slug describing it (e.g., `qa-must-rerun-skipped-gates`)." Then ask for the rule text + rationale.

2. **Generate proposal_id.** Format: `<ISO-UTC-no-colons>__<slug>` from `date -u +%Y-%m-%dT%H-%M-%SZ` + `$ARGUMENTS` slug. Example: `2026-05-19T14-30-00Z__qa-must-rerun-skipped-gates`.

3. **Detect the project root.** Use `${CLAUDE_PROJECT_DIR}`. If `.engineering-os/` does not exist, refuse with "This skill requires a project initialized with `/engineering-os:eos-init`."

4. **Ensure the rule-proposals directory exists.**
   ```bash
   mkdir -p ${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals
   ```

5. **Write the proposal artifact** to `${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals/<proposal_id>.md` using `${CLAUDE_PLUGIN_ROOT}/templates/rule-proposal.md`. Fill in every field with the operator's input + your own analysis. Specifically:
   - `proposal_id`: from step 2
   - `proposed_by`: the current agent's role OR `stakeholder` if invoked by the Stakeholder directly
   - `proposed_at`: from `date -u`
   - `target_scope`: which agents / stages this applies to
   - `proposed_text`: the literal rule text
   - `rationale`: why this rule needs to exist
   - `evidence`: concrete observations that motivated it
   - `alternatives_considered`: at least 2 alternatives + why rejected
   - `cost_of_adoption`: prompt changes + doc changes + throughput + token cost
   - `cost_of_not_adopting`: what continues to go wrong
   - `decision` block: leave blank — only the Stakeholder fills this via `/adopt-rule` or `/reject-rule`

6. **Append a decision-log event.**
   ```bash
   ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   echo "{\"ts\":\"$ts\",\"actor\":\"<proposer>\",\"type\":\"rule-proposed\",\"proposal_id\":\"$proposal_id\",\"slug\":\"$slug\",\"target_scope\":\"<scope>\"}" >> ${CLAUDE_PROJECT_DIR}/.engineering-os/decision-log/$(date -u +%Y/%m)/$(date -u +%Y-%m-%d).jsonl
   ```

7. **Surface to the Stakeholder.** Append a line to `${CLAUDE_PROJECT_DIR}/.engineering-os/pending-stakeholder-attention.md` (create if missing):
   ```
   - rule-proposal `<proposal_id>` — review at `.engineering-os/rule-proposals/<proposal_id>.md`. Adopt with `/engineering-os:adopt-rule <proposal_id>` or `/engineering-os:reject-rule <proposal_id> <reason>`.
   ```

8. **Print to operator:**
   - Proposal path.
   - One-line summary.
   - "Awaiting the Stakeholder. Run `/engineering-os:adopt-rule <proposal_id>` to adopt, or `/reject-rule <proposal_id> <reason>` to reject."

## Don't

- Don't adopt the proposal yourself. Only the Stakeholder adopts.
- Don't fabricate evidence. If the evidence is "I have a feeling this is needed," say so honestly; that's a weaker proposal than one with cited artifacts.
- Don't write rule text that requires judgment to apply ("when reasonable", "as appropriate"). Mechanical rules survive longer.
- Don't propose rules that overlap or contradict an existing durable rule without explicitly proposing supersession.
