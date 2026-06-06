# Durable Rule — {{RULE_ID}}

> An ADOPTED operating rule for the team. Lives at `.engineering-os/durable-rules/<ISO-adopted-ts>__<slug>.md` in the consuming product repo.
> Read by every agent at session start (Engineering Advisor step 3b in `agents/cto-advisor.md`; other agents via system prompt instruction).
> Mutation rule: append-only by date — a new rule can supersede an old one, but old rules are NEVER edited or deleted. Audit trail is permanent.

| Field | Value |
|---|---|
| **rule_id** | `{{RULE_ID}}` *(kebab-case slug)* |
| **adopted_at** | {{ADOPTED_AT}} |
| **adopted_by** | {{ADOPTED_BY}} *(the Stakeholder)* |
| **sourced_from_proposal** | {{PROPOSAL_PATH}} *(path to the rule-proposal that became this rule)* |
| **scope** | {{SCOPE}} *(e.g., "all-agents", "stage-3-developer", "stage-7-stakeholder-gate")* |
| **status** | active *(transitions to "superseded-by-<rule-id>" if a later rule replaces this one)* |

---

## Rule text

> The literal text agents are bound by. Quoted verbatim in agent prompts and docs that enforce it.

{{RULE_TEXT}}

---

## How agents must apply this

> Concrete bullets — what to check, what to bias toward, what to bounce on. Each bullet should be mechanically verifiable where possible.

- {{HOW_1}}
- {{HOW_2}}

---

## Exceptions (if any)

> Codified exceptions to the rule. Each exception must be mechanically check-able. No "judgment-based" exceptions — those rot.

- {{EXCEPTION_1}} *(condition + verifier)*

---

## Supersession history

> If this rule replaces a prior rule, name it. If a later rule replaces this one, that later rule's adoption marks this one's `status` as `superseded-by-<new-rule-id>`.

- {{SUPERSESSION_NOTE}}

---

## Rule decay check

> Heuristic for the team to know whether this rule is still load-bearing.

| Check | When |
|---|---|
| Has this rule fired (bounced something) in the last N children? | Reviewed at every Engineering Advisor Stage 1 dependency check |
| Has the rule become redundant with a newer rule or with codified workflow? | Surfaced if same lesson appears in N consecutive retros |
| Has the rule's evidence (the product's stack / Canon / compliance regime) materially changed? | Surfaced when an agent or the Stakeholder reviews durable-rules against the current Canon; file a `/engineering-os:propose-rule` supersession if it has |

Rules that fail decay checks should be PROPOSED for supersession via the rule-proposal mechanism, not silently ignored.
