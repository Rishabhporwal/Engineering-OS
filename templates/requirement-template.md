# Requirement: {{TITLE}}

> Filled out by `/requirement <text>` automatically. Founder can edit afterward.
> Validates against [schemas/requirement.schema.json](../schemas/requirement.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Title** | {{TITLE}} |
| **Submitted by** | {{SUBMITTED_BY}} |
| **Submitted at** | {{SUBMITTED_AT}} |
| **Tier impact** | {{TIER_IMPACT}}  *(launch / growth / scale / enterprise — BRD §15.2 packaging tiers)* |
| **Region impact** | {{REGION_IMPACT}}  *(in / ae / sa / us / eu / lat / sea / afr)* |

---

## Lane *(set by Rohan at Stage 1 — leave blank at intake)*

> Rohan assigns the pipeline lane before persona count, per [docs/feature-tiering.md](../docs/feature-tiering.md). Trigger surfaces force `high-stakes` mechanically; `express` requires an empty `trigger_surfaces_touched`.

| Field | Value |
|-------|-------|
| **feature_class** | {{FEATURE_CLASS}}  *(express / standard / high-stakes)* |
| **feature_class_rationale** | {{FEATURE_CLASS_RATIONALE}}  *(one line: which classifier rule fired + any surfaces)* |
| **trigger_surfaces_touched** | {{TRIGGER_SURFACES_TOUCHED}}  *(auth / multi-tenancy / mcp-tools / connectors / outbound-channels / pii / schema-proto / money / india-compliance — empty for express)* |

---

## Raw text (from Founder)

> {{RAW_TEXT}}

---

## Problem statement

*What is broken or missing? What is the user trying to do today that doesn't work?*

{{PROBLEM_STATEMENT}}

---

## Target user

*Which persona + tier? (e.g., "Founder of a growth-tier beauty brand", "CFO of an enterprise multi-brand holding co".)*

{{TARGET_USER}}

---

## Success metric

*How will we know it worked? Quantitative if possible (e.g., "Recovered Revenue / Fee > 3× for COD orders in GCC by month 2 post-launch").*

{{SUCCESS_METRIC}}

---

## Constraints

*Cost, time, regulatory, technical. List them.*

- {{CONSTRAINT_1}}
- {{CONSTRAINT_2}}
- {{CONSTRAINT_3}}

---

## Non-goals

*Explicitly out of scope. What we're NOT doing here.*

- {{NON_GOAL_1}}
- {{NON_GOAL_2}}

---

## Linked prior runs

*If this requirement has prior runs (a re-attempt, an extension, a follow-up), list the run folders here.*

- {{LINKED_RUN_1}}

---

## Notes

*Any extra context, screenshots, links, hypotheses Rishabh wants the team to consider.*

{{NOTES}}
