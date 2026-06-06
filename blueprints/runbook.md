# Runbook — {{SERVICE_OR_SCENARIO}}

> Operational runbook. One per service + one per known failure scenario. Authored by the owning builder, reviewed by Platform-SRE (`operational-readiness` + `incident-response`). A runbook is for the person paged at 3am who didn't write the code — concrete commands, not prose. Save to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/runbooks/<slug>.md`.

| Field | Value |
|---|---|
| **Service / scenario** | {{e.g. a service / "scheduled job missed SLO" / "auto-action error-rate breach"}} |
| **Owner** | {{persona}} |
| **Related SLO** | {{e.g. a user-facing job within its latency target; audit-log write 99.99%; critical-data freshness < 1h}} |
| **Dashboards** | {{links}} · **Alarms** | {{which alarms point here}} |

## Quick reference
- **Healthcheck:** `{{cmd / URL}}` → expect {{...}}
- **Logs:** `{{the log store query / kubectl logs ...}}` (correlation ID = `request_id`+`trace_id`+`tenant_id`+`user_id`)
- **Kill switch / feature flag:** {{how to disable this surface — esp. auto-execute Owner kill switch within 60s}}
- **On-call escalation:** {{IC → secondary → Stakeholder for compliance/financial}}

## Symptoms → diagnosis → action
| Symptom (what the alarm/customer says) | Likely cause | Diagnose | Action (exact commands) |
|---|---|---|---|
| {{e.g. a scheduled job not delivered on time}} | {{scheduled job stalled / model timeout / push failure}} | {{check tick logs, LLM cap, freshness gate}} | {{rerun job / degrade to a cheaper path / page}} |
| {{e.g. connector freshness >1h}} | {{token expired / vendor outage / rate-limit}} | {{integration health table, last_sync, error}} | {{refresh token / backfill window / mark degraded + label stale data}} |
| {{e.g. auto-execute reversal rate >15%}} | {{model drift / bad threshold}} | {{audit log reversal query}} | {{auto-revert to recommend-only (already automatic at threshold) / Owner kill switch}} |

## Rollback
- **Code:** {{ArgoCD rollback to prev sync / `git revert <sha>` — per `finishing-a-development-branch`}}
- **Data:** {{is there state to unwind? migration down-script? audit log entries are append-only — never delete}}
- **Verify recovery:** {{the exact command + expected output that proves we're back}}

## Do NOT
- Don't `git push --force`, rewrite history, or delete audit log / audit rows. Don't disable a compliance gate to "unblock". Don't bypass RLS in the request path.
