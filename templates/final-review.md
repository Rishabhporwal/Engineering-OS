# Final Review — {{REQ_ID}}

> Filled by the CTO Advisor in Stage 6. **VETO authority** — can bounce to any earlier stage.
> Validates against [schemas/final-review.schema.json](../schemas/final-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | cto-advisor |
| **Timestamp** | {{TS}} |
| **Verdict** | **{{VERDICT}}**  *(PASS / BOUNCE)* |

---

## Sub-reviews

| Sub-review | Verdict | Notes |
|------------|:------:|-------|
| **Requirement alignment** | {{REQ_ALIGN}} | Does the shipped change still solve the original requirement? |
| **Paradigm audit** | {{PARADIGM_AUDIT}} | Every `@paradigm` decorator matches the declared plan? No `frontier_llm` call snuck in where `small_llm` (or SQL/ML) was promised? Gateway routed each LLM tier to a model that passed its eval bar? |
| **Architecture quality** | {{ARCH_QUALITY}} | Single-Primitive Rule held? No anti-pattern drift? |
| **Code quality** | {{CODE_QUALITY}} | Sampled 3–5 files. No obvious smells. Comments only where *why* is non-obvious. |
| **Security review pass-through** | {{SEC_PASS}} | Shreya passed. |
| **QA review pass-through** | {{QA_PASS}} | Tanvi passed. |
| **Observability complete** | {{OBS_COMPLETE}} | Metrics, logs, traces, alarms, dashboards in place. |
| **Cost estimate held** | {{COST_HELD}} | Actual tokens/day within ±20% of plan. |

---

## Code-quality spot-checks

> Sample 3–5 files and note any concerns.

| File | Concern (or "clean") |
|------|---------------------|
| {{FILE_1}} | {{F1_NOTE}} |
| {{FILE_2}} | {{F2_NOTE}} |
| {{FILE_3}} | {{F3_NOTE}} |

---

## Cost audit

| Field | Value |
|-------|-------|
| **Planned tokens/day** | {{PLANNED_TOKENS}} |
| **Simulated daily-tick tokens** | {{SIMULATED_TOKENS}} |
| **Variance** | {{VARIANCE_PCT}}% |
| **Within ±20% tolerance?** | {{COST_TOLERANCE_OK}} |

---

## Risks remaining

- {{RISK_REMAINING_1}}
- {{RISK_REMAINING_2}}

---

## Production-readiness assessment

> Would Jatin's pre-deploy gates pass right now?

{{PROD_READY_ASSESSMENT}}

---

## Recommendation to Founder

**{{RECOMMENDATION}}**  *(APPROVE / APPROVE-WITH-CAVEATS / REJECT)*

### Caveats (if APPROVE-WITH-CAVEATS)
- {{CAVEAT_1}}
- {{CAVEAT_2}}

### Founder briefing (one paragraph)

> *What the Founder needs to know in 60 seconds before approving.*

{{FOUNDER_BRIEFING}}

---

## Bounce details *(if VERDICT = BOUNCE)*

| Field | Value |
|-------|-------|
| **Target stage** | {{BOUNCE_TARGET}} |
| **Target persona** | @{{BOUNCE_PERSONA}} |
| **Rationale** | {{BOUNCE_RATIONALE}} |

---

## Decision log entry (mirrored)

```json
{
  "ts": "{{TS}}",
  "actor": "cto-advisor",
  "type": "final-review",
  "req_id": "{{REQ_ID}}",
  "verdict": "{{VERDICT}}",
  "recommendation": "{{RECOMMENDATION}}"
}
```
