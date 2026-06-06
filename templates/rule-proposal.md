# Rule Proposal — {{PROPOSAL_ID}}

> A proposed change to the team's operating rules. Lives at `.engineering-os/rule-proposals/<ISO-ts>__<slug>.md` in the consuming product repo.
> Proposed by an agent or operator; ADOPTED only when the Stakeholder runs `/engineering-os:adopt-rule <proposal-path>`.
> Agents CANNOT self-promote a proposal to a durable rule.

| Field | Value |
|---|---|
| **proposal_id** | `{{PROPOSAL_ID}}` *(kebab-case slug)* |
| **proposed_by** | `{{PROPOSED_BY}}` *(role name, or the Stakeholder / operator handle)* |
| **proposed_at** | {{PROPOSED_AT}} |
| **target_scope** | {{TARGET_SCOPE}} *(e.g., "stage-3-developer", "all-agents", "platform-devops-only", "stage-7-stakeholder-gate")* |
| **status** | proposed *(transitions to "adopted" or "rejected" on Stakeholder action)* |

---

## Proposed text

> The literal rule text the team would follow if adopted. Should be unambiguous, mechanically checkable where possible, and quoted in the agent prompts that need to enforce it.

{{PROPOSED_TEXT}}

---

## Rationale

> Why does this rule need to exist? What problem does it solve? What was observed that motivated this proposal?

{{RATIONALE}}

---

## Evidence

> Cite the concrete observation(s) that motivated this proposal. Reference run-folder artifacts, journal entries, decision-log events, or external incidents. Be specific.

- {{EVIDENCE_1}}
- {{EVIDENCE_2}}

---

## Alternatives considered

> What other rules or approaches could solve the same problem? Why is this proposal preferred?

| Alternative | Why rejected |
|---|---|
| {{ALT_1}} | {{ALT_1_WHY}} |
| {{ALT_2}} | {{ALT_2_WHY}} |

---

## Cost of adoption

| Dimension | Impact |
|---|---|
| **Agent prompt changes needed** | {{PROMPT_CHANGES}} *(which agent files, approx line count)* |
| **Doc updates needed** | {{DOC_CHANGES}} |
| **Schema / template changes** | {{SCHEMA_CHANGES}} |
| **Throughput impact** | {{THROUGHPUT_IMPACT}} *(faster / same / slower; estimate %)* |
| **Token cost impact** | {{TOKEN_COST_IMPACT}} *(% over baseline)* |

---

## Cost of NOT adopting

> What continues to go wrong if the Stakeholder rejects this proposal?

{{COST_OF_NOT_ADOPTING}}

---

## Decision

| Field | Value |
|---|---|
| **decided_at** | {{DECIDED_AT}} *(filled by /engineering-os:adopt-rule or /reject-rule)* |
| **decided_by** | {{DECIDED_BY}} *(the Stakeholder; agents cannot decide their own rules)* |
| **decision** | {{DECISION}} *(adopted / rejected / deferred)* |
| **rationale** | {{DECISION_RATIONALE}} |
| **durable_rule_path** | {{DURABLE_RULE_PATH}} *(if adopted, path to the new file in .engineering-os/durable-rules/)* |
