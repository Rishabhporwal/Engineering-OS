# Retro — {{REQ_ID}}

> Filled by CTO Advisor at the close of Stage 6 (final review). Append-only — never edited after write.
> Validates against [schemas/retro.schema.json](../schemas/retro.schema.json).
> Feeds the lessons-learned registry at `.engineering-os/lessons-learned.md`.

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Parent req_id** | `{{PARENT_REQ_ID}}` *(or "—" if standalone)* |
| **Shipped at** | {{SHIPPED_AT}} |
| **Author** | cto-advisor *(typically Rohan, on Founder's behalf under delegation)* |

---

## What worked (concrete patterns to replicate)

> Be specific. Cite artifacts. "X worked" with no rationale is noise.

- {{WHAT_WORKED_1}}
- {{WHAT_WORKED_2}}
- {{WHAT_WORKED_3}}

---

## What didn't work (concrete patterns to avoid)

> Even on a successful child, name what nearly broke or wasted time. Honest > flattering.

- {{WHAT_DIDNT_WORK_1}}
- {{WHAT_DIDNT_WORK_2}}

---

## What surprised us

> Emergent learning the planning didn't anticipate. Bugs caught at test time. Persona concerns that turned out load-bearing. Constraints that mattered more (or less) than expected. Tooling that helped (or got in the way).

- {{SURPRISE_1}}
- {{SURPRISE_2}}

---

## Lessons to file in the registry

> Each lesson becomes one entry in `.engineering-os/lessons-learned.md`. Use this format:

| # | Lesson (one-line) | Applies to | Evidence |
|---|---|---|---|
| 1 | {{LESSON_1}} | {{APPLIES_TO_1}} | {{EVIDENCE_1}} |
| 2 | {{LESSON_2}} | {{APPLIES_TO_2}} | {{EVIDENCE_2}} |

**Applies-to tags** (pick all that apply): `process`, `code`, `security`, `india-compliance`, `numeric-parity`, `cost-routing`, `single-primitive`, `migration`, `agent-discipline`, `pipeline-mechanics`, `infra`.

---

## Action items for next child

> Concrete things the NEXT CTOA intake should do differently. Each item becomes a check the next intake's "Read lessons registry" step looks for.

- [ ] {{ACTION_1}}
- [ ] {{ACTION_2}}

---

## Cost + paradigm reality vs plan

| Metric | Planned | Actual | Variance |
|---|---|---|---|
| Monthly $ cost | {{PLAN_COST}} | {{ACTUAL_COST}} | {{COST_VARIANCE}} |
| LLM tokens / day | {{PLAN_TOKENS}} | {{ACTUAL_TOKENS}} | {{TOKEN_VARIANCE}} |
| Wall-clock duration | {{PLAN_DURATION}} | {{ACTUAL_DURATION}} | {{DURATION_VARIANCE}} |
| Paradigm declared | {{PLAN_PARADIGM}} | {{ACTUAL_PARADIGM}} | {{PARADIGM_MATCH}} |
| Persona count | {{PLAN_PERSONAS}} | {{ACTUAL_PERSONAS}} | {{PERSONA_MATCH}} |

**Calibration note for next time:** {{CALIBRATION_NOTE}}
