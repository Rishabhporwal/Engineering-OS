# PLAYBOOK — incident (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/PLAYBOOK-incident.md`. The severity ladder, paging, and
> kill switches for this product. Owner: Platform/SRE. See
> `engineering-os-blueprint/07-operations-and-reliability.md §4`.

## Severity ladder
| Sev | Definition | Response | Who's paged | Comms cadence |
|---|---|---|---|---|
| SEV1 | `<broad outage / data risk>` | immediate | `<…>` | `<…>` |
| SEV2 | `<major degradation>` | `<…>` | `<…>` | `<…>` |
| SEV3 | `<minor degradation>` | `<…>` | `<…>` | `<…>` |
| SEV4 | `<no user impact>` | `<…>` | `<…>` | `<…>` |

## Roles
- **Incident Commander:** `<owns the response; single point of authority>`
- **Responders / Comms / Scribe:** `<…>`

## Kill switches (mitigate first)
| Surface | Switch | Latency | How to trigger |
|---|---|---|---|
| `<highest-risk surface>` | `<flag / route / feature off>` | `<seconds>` | `<command>` |

## Flow
detect (alerting on SLO breach / error-budget burn) → **mitigate first** (kill switch / rollback /
failover / shed load) → resolve → blameless postmortem within `<window>` → action items → lessons-learned.
