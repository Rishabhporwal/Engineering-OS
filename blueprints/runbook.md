# Runbook — {{SERVICE_OR_SCENARIO}}

> Operational runbook. One per service + one per known failure scenario. Authored by the owning builder, reviewed by Jatin (`operational-readiness` + `incident-response`). A runbook is for the person paged at 3am who didn't write the code — concrete commands, not prose. Save to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/runbooks/<slug>.md`.

| Field | Value |
|---|---|
| **Service / scenario** | {{e.g. analytics-service / "Morning Brief missed SLO" / "auto-execute reversal-rate breach"}} |
| **Owner** | {{persona}} |
| **Related SLO** | {{e.g. Morning Brief 07:20 IST >99.5%; Decision-Log write 99.99%; P0 freshness <1h}} |
| **Dashboards** | {{links}} · **Alarms** | {{which alarms point here}} |

## Quick reference
- **Healthcheck:** `{{cmd / URL}}` → expect {{...}}
- **Logs:** `{{OpenSearch query / kubectl logs ...}}` (correlation ID = `request_id`+`trace_id`+`workspace_id`+`user_id`)
- **Kill switch / feature flag:** {{how to disable this surface — esp. auto-execute Owner kill switch within 60s}}
- **On-call escalation:** {{IC → secondary → Founder for compliance/financial}}

## Symptoms → diagnosis → action
| Symptom (what the alarm/customer says) | Likely cause | Diagnose | Action (exact commands) |
|---|---|---|---|
| {{e.g. Morning Brief not delivered by 07:20}} | {{daily-tick stalled / Sonnet timeout / push failure}} | {{check tick logs, LLM cap, freshness gate}} | {{rerun tick / degrade to SQL+ML brief / page}} |
| {{e.g. connector freshness >1h}} | {{token expired / vendor outage / rate-limit}} | {{integration health table, last_sync, error}} | {{refresh token / backfill window / mark degraded + label stale data}} |
| {{e.g. auto-execute reversal rate >15%}} | {{model drift / bad threshold}} | {{Decision-Log reversal query}} | {{auto-revert to recommend-only (already automatic at threshold) / Owner kill switch}} |

## Rollback
- **Code:** {{ArgoCD rollback to prev sync / `git revert <sha>` — per `finishing-a-development-branch`}}
- **Data:** {{is there state to unwind? migration down-script? Decision-Log entries are append-only — never delete}}
- **Verify recovery:** {{the exact command + expected output that proves we're back}}

## Do NOT
- Don't `git push --force`, rewrite history, or delete Decision-Log / audit rows. Don't disable a compliance gate to "unblock". Don't bypass RLS in the request path.
