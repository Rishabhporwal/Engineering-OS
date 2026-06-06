# Requirement: {{TITLE}}

> Filled out by `/requirement <text>` automatically. The Stakeholder can edit afterward.
> Validates against [schemas/requirement.schema.json](../schemas/requirement.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Title** | {{TITLE}} |
| **Submitted by** | {{SUBMITTED_BY}} |
| **Submitted at** | {{SUBMITTED_AT}} |
| **Tier impact** | {{TIER_IMPACT}}  *(the product's packaging tier, if any — per the Product Canon)* |
| **Region impact** | {{REGION_IMPACT}}  *(the affected region/locale via the RegionAdapter seam — per the Product Canon)* |

---

## Lane *(set by the Engineering Advisor at Stage 1 — leave blank at intake)*

> The Engineering Advisor assigns the pipeline lane before persona count, per [docs/feature-tiering.md](../docs/feature-tiering.md). Trigger surfaces force `high-stakes` mechanically; `express` requires an empty `trigger_surfaces_touched`.

| Field | Value |
|-------|-------|
| **feature_class** | {{FEATURE_CLASS}}  *(express / standard / high-stakes)* |
| **feature_class_rationale** | {{FEATURE_CLASS_RATIONALE}}  *(one line: which classifier rule fired + any surfaces)* |
| **trigger_surfaces_touched** | {{TRIGGER_SURFACES_TOUCHED}}  *(the trigger surfaces declared in the Product Canon's TRIGGER-SURFACES.md — e.g. auth / multi-tenancy / mcp-tools / connectors / outbound-channels / pii / schema-proto / money / compliance — empty for express)* |

---

## Raw text (from the Stakeholder)

> {{RAW_TEXT}}

---

## Problem statement

*What is broken or missing? What is the user trying to do today that doesn't work?*

{{PROBLEM_STATEMENT}}

---

## Target user

*Which persona + tier? (e.g., the role of the end user and the packaging tier they fall under, per the Product Canon.)*

{{TARGET_USER}}

---

## Success metric

*How will we know it worked? Quantitative if possible (e.g., a measurable target on a business metric within a defined window post-launch).*

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

*Any extra context, screenshots, links, hypotheses the Stakeholder wants the team to consider.*

{{NOTES}}
