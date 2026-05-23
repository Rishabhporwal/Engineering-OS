# CTO Advisor Review — {{STAGE_LABEL}}

> Filled by the CTO Advisor agent in Stage 1 (intake) or Stage 6 (final review).
> Validates against [schemas/cto-advisor-review.schema.json](../schemas/cto-advisor-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Stage** | {{STAGE}}  *(1 = intake, 6 = final review)* |
| **Timestamp** | {{TS}} |
| **Decision** | **{{DECISION}}**  *(ADVANCE / CHALLENGE-BACK / KILL / PASS / FAIL / BOUNCE)* |

---

## Made requirements less dumb first

*The "delete / simplify / defer" pass before anything else.*

**Could delete:**
- {{COULD_DELETE_1}}

**Could simplify:**
- {{COULD_SIMPLIFY_1}}

**Could defer:**
- {{COULD_DEFER_1}}

---

## Personas spawned *(Stage 1 only — 0, 1, or 2 by complexity; cap 2)*

1. **{{PERSONA_1}}** — see [`03-persona-{{PERSONA_1}}.md`](.)
2. **{{PERSONA_2}}** — see [`04-persona-{{PERSONA_2}}.md`](.)

**Synthesis:**

{{PERSONA_SYNTHESIS}}

---

## Paradigm recommendation

**Recommended paradigm:** `{{PARADIGM}}`  *(sql / ml / small_llm / frontier_llm)*

**Why:** {{PARADIGM_WHY}}

> Architect (Aryan) may refine in Stage 2 — this is a first-pass read.

---

## India context check

| Lens | Impact |
|------|--------|
| **RTO** | {{RTO_IMPACT}} |
| **COD** | {{COD_IMPACT}} |
| **GST** | {{GST_IMPACT}} |
| **Festival seasonality** | {{FESTIVAL_IMPACT}} |
| **Pincode reliability** | {{PINCODE_IMPACT}} |
| **Telecom compliance (DLT / NCPR / DND / calling hours)** | {{TELECOM_IMPACT}} |

---

## Challenge *(present only if decision = CHALLENGE-BACK)*

> Tone is constructive. Always end with a path forward.

| Field | Content |
|-------|---------|
| **What I understood** | {{UNDERSTOOD}} |
| **What concern I have** | {{CONCERN}} |
| **What risk this carries** | {{RISK}} |
| **What I recommend instead** | {{ALTERNATIVE}} |
| **What decision I need from you** | {{DECISION_NEEDED}} |

---

## Final review *(Stage 6 only)*

| Sub-review | Verdict |
|------------|---------|
| Requirement alignment | {{REQ_ALIGN}} |
| Paradigm audit (`@paradigm` decorators match plan) | {{PARADIGM_AUDIT}} |
| Architecture quality (Single-Primitive Rule held) | {{ARCH_QUALITY}} |
| Code quality (sampled 3–5 files) | {{CODE_QUALITY}} |
| Security review pass-through | {{SEC_PASS}} |
| QA review pass-through | {{QA_PASS}} |
| Observability complete | {{OBS_COMPLETE}} |
| Cost estimate held within ±20% of plan | {{COST_HELD}} |

**Risks remaining:**
- {{RISK_REMAINING_1}}

**Production-readiness assessment:** {{PROD_READY_ASSESSMENT}}

**Recommendation to Founder:** **{{RECOMMENDATION}}**  *(APPROVE / APPROVE-WITH-CAVEATS / REJECT)*

**Caveats (if any):**
- {{CAVEAT_1}}

---

## Bounce details *(if decision = BOUNCE or FAIL)*

| Field | Value |
|-------|-------|
| **Target stage** | {{BOUNCE_TARGET}} |
| **Target persona** | {{BOUNCE_PERSONA}} |
| **Rationale** | {{BOUNCE_RATIONALE}} |

---

## Decision log entry (mirrored)

```json
{
  "ts": "{{TS}}",
  "actor": "cto-advisor",
  "type": "{{LOG_TYPE}}",
  "req_id": "{{REQ_ID}}",
  "stage": {{STAGE}},
  "decision": "{{DECISION}}",
  "rationale": "{{RATIONALE_ONE_LINE}}"
}
```
