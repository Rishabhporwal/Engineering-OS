# ESCALATION RUBRIC (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/ESCALATION-RUBRIC.md`. When a role must escalate to the
> Stakeholder. The OS supplies the **categories**; you supply the **thresholds**. Escalation is
> Advisor-gated and last-resort, not democratic and not a status ping. See
> `engineering-os-blueprint/01-organization-structure.md §5`.

An escalation **may** be warranted when a change would:

| Category (OS-fixed) | This product's threshold (you fill) |
|---|---|
| Irreversible / high-blast-radius decision | `<e.g. a data migration; a public API contract; a tenancy/security boundary>` |
| Compliance / regulatory ambiguity the Canon doesn't resolve | `<e.g. a new jurisdiction; an unclear control>` |
| Threatens a cost / performance / reliability budget | `<e.g. >X% cost increase; SLO at risk>` |
| Cross-team pattern/contract conflict the Architect can't reconcile | `<…>` |
| Changes an invariant or the moat | `<reference INVARIANTS.md / THE-MOAT.md>` |

**Flow:** any role → Engineering Advisor → Advisor decides (answers from the Canon + lessons-learned
whenever possible; escalates only as a last resort). The Delivery Coordinator mirrors any pending
escalation into `pending-stakeholder-attention`.
