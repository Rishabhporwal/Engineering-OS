# Postmortem — {{INCIDENT_TITLE}}

> **Blameless** postmortem. Filled by Platform-SRE + the builder(s) per the `incident-response` skill, after any SEV-1/SEV-2 (and any compliance or auto-execute incident regardless of severity). Blameless = we fix systems, not people. Save to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/incidents/<date>-<slug>.md` and feed every action item into the lessons-learned registry.

| Field | Value |
|---|---|
| **Incident ID** | {{INC-YYYY-MM-DD-NN}} |
| **Severity** | {{SEV-1 / SEV-2 / SEV-3}} |
| **Status** | {{mitigated / resolved}} |
| **Detected** | {{TS}} ({{how: alarm / customer / agent / manual}}) |
| **Mitigated** | {{TS}} · **Resolved** | {{TS}} |
| **Duration** | {{time-to-detect / time-to-mitigate / time-to-resolve}} |
| **Incident Commander** | {{who}} |
| **Affected** | {{services / workspaces / customers — quantify}} |

## 1. Impact (in business terms, not just technical)
{{What broke for whom. Financial impact, audit-log writes lost, scheduled jobs missed, compliance exposure, data exposed? Quantify against the SLOs — e.g. "feature X unavailable for N tenants vs the stated SLO".}}

## 2. Timeline (UTC, factual)
- `{{TS}}` — {{event}}
- `{{TS}}` — {{detection}}
- `{{TS}}` — {{actions taken, by whom}}
- `{{TS}}` — {{mitigation}}
- `{{TS}}` — {{resolution}}

## 3. Root cause (use `systematic-debugging` — trace backward to the true cause, not the symptom)
{{The actual root cause. "5 whys" if useful. Distinguish trigger vs underlying cause. Was a gate/guardrail/SLO that should have caught this missing or mis-set?}}

## 4. What went well / what went wrong / where we got lucky
- **Well:** {{detection, rollback, comms that worked}}
- **Wrong:** {{gaps in detection, runbook, guardrail}}
- **Lucky:** {{things that could have been worse — these are P0 action items}}

## 5. Action items (each: owner + due date + tracked; the point of the postmortem)
| Action | Type (prevent / detect / mitigate) | Owner | Due | Tracking |
|---|---|---|---|---|
| {{e.g. add burn-rate alert at 2× error budget}} | detect | Platform-SRE | {{date}} | {{decision-log / tracker id}} |

## 6. Lessons → registry
- If this root cause has now appeared in ≥3 runs/incidents, propose a durable rule (`/propose-rule`) per the self-learning loop. Otherwise log the lesson in `lessons-learned.md`.
- **Did a guardrail/SLO/threshold need changing?** {{yes/no — if yes, the change + who approved}}
