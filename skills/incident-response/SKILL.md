---
name: incident-response
description: Run-time incident discipline — severity ladder, Incident Commander, detect→mitigate→resolve, fast kill switches, blameless postmortems → lessons-learned loop. Owner Platform/SRE.
---

# Incident Response — when the product breaks in production

`operational-readiness` is the gate that keeps a service from shipping broken; **this skill is what happens after it ships and breaks anyway.** When the product is an *acting* system — one that takes real-world side effects (notifications, calls, financial or otherwise-irreversible actions) and writes a system-of-record audit log — an incident can be a **compliance violation**, **financial/irreversible damage from an automated loop**, or a **lost audit record**.

**Canonical doc:** the Product Canon's `PLAYBOOK-incident.md` + the SLO/observability section of the Canon (see `engineering-os-blueprint/07-operations-and-reliability.md`). Owner: **Platform/SRE** (on-call). Detection rides the observability spine (one correlation ID end-to-end — see `observability`).

## The severity ladder

| SEV | Definition | Examples | Response |
|---|---|---|---|
| **SEV-1** | Compliance violation · customer-data exposure · cross-tenant leak · automated action causing financial/irreversible damage · **audit-log write outage** | A send fired outside an allowed channel/window · cross-tenant data visible · an automated action's reversal/error rate past threshold causing harm · system-of-record writes failing past SLO | Page now · IC assigned · **Security Reviewer looped on any compliance/data item** · Stakeholder notified for financial/compliance/data · kill switch first, diagnose second |
| **SEV-2** | Core surface down, no compliance/data/financial harm | A defining product surface missed its SLO · a connector-class outage (mass staleness) · API error spike | Page on-call · IC for multi-tenant impact · mitigate to restore (degrade gracefully) |
| **SEV-3** | Degraded / single-tenant / non-urgent | One connector stale for one tenant · elevated p95 within SLO · a non-critical job failed + retried | Ticket + runbook · handle in hours · no page |

**Escalation, not certainty, is the trigger:** if it *might* be compliance, data exposure, or financial/irreversible damage, treat as SEV-1 until proven otherwise and loop the Security Reviewer. Under-calling is the expensive mistake.

## Incident Commander (IC) + comms

Every SEV-1/SEV-2 gets **one IC** (default Platform/SRE on-call) who **coordinates — does not solo-fix**. IC declares severity, owns the timeline, decides mitigations (kill switch / rollback / degrade), pulls in domain owners (AI/ML Engineer for model/agent issues, Security Reviewer for compliance/security, Architect for architecture, the surface's builder), runs comms. Cadence: an incident channel, a status line at declaration + each state change, and Stakeholder notification for any compliance/data/financial SEV-1. **Affected tenants are quantified** ("N tenants vs the SLO", not "some users").

## detect → mitigate → resolve

```
DETECT   alarm (metrics/error tracking) · customer report · failed job · compliance counter > 0
   ▼     IC declares severity; opens incident channel; starts the timeline
MITIGATE stop the bleeding FIRST — kill switch / feature flag / deploy rollback / degrade-gracefully
   ▼     restore the surface or halt the harm before chasing root cause
RESOLVE  root-cause via systematic-debugging (trace backward); ship the real fix;
   ▼     verify recovery with the exact runbook command (don't claim "back" — prove it)
POST     blameless postmortem (SEV-1/SEV-2 + any compliance/automated-action incident) → action items → registry
```

**Mitigate before you understand.** A compliance breach or money-losing automated loop is stopped *now* (kill switch); root cause is found *after*. Use `systematic-debugging` for root cause — never patch the symptom.

## The kill switches (first-line mitigation)

- **Automated-action kill switch — pauses ALL automated execution fast** (per the Canon's kill-switch SLO). A global flag for fleet-wide halt. After a breach, autonomy **auto-reverts to recommend-only** when reversal/error rate crosses a threshold (alert below the SLO, hard-trip at the SLO ceiling).
- **Per-action kill switch** — disable a single action class without disabling the rest.
- **Feature flags** — disable a surface (a connector, a feature, a new component) without a deploy. Wired at ship time (`operational-readiness`, `progressive-delivery`).
- **Compliance fail-closed** — the enforcement machinery refuses to take an action that violates the regime (channel/window/consent rules in `COMPLIANCE.md`). An action *that escaped it* is the SEV-1; mitigation is to halt the outbound path (flag) and preserve evidence.

Reversals must themselves be logged: an automated reversal updates the same system-of-record audit row with a `reversal` payload — an un-audited undo is its own finding (see `decision-log`).

## A generic incident playbook (each gets a runbook)

| Incident | SEV | First move (mitigate) | Then |
|---|---|---|---|
| **Out-of-policy action fired** (wrong channel/window/consent) | SEV-1 | Halt outbound (flag); loop Security Reviewer + Stakeholder | Trace which consent/policy check was bypassed; preserve evidence; reportable compliance event |
| **Automated-action reversal-rate breach** | SEV-1 | Global/per-action kill switch (fast); auto-revert trips at threshold | Audit-log reversal query → action class / model drift; re-baseline before re-enabling |
| **Defining surface missed its SLO** | SEV-2 | Rerun the job or degrade to a deterministic fallback; ensure the surface still ships | Check job stall / model timeout / cost cap / freshness gate; protect the next run |
| **Audit-log write failure** (system-of-record SLO) | SEV-1 | Retry via transactional outbox; never silently swallow | Each dropped write is a lost record — backfill from the durable event log |
| **Connector mass-staleness** (freshness past SLO) | SEV-2 | Mark connector degraded; **agents label stale data, not act on it** | Token refresh / vendor outage / rate-limit; backfill window (backfill == live) |
| **Cross-tenant data leak** | SEV-1 | Disable the leaking surface; loop Security Reviewer + Stakeholder | Which isolation layer failed (identity/RLS/query-gateway/tool); zero tolerance |

## Runbooks

Every service + known failure scenario has a runbook by the owning builder, reviewed by Platform/SRE. **For the person paged at 3am who didn't write the code:** healthcheck command, log query (with correlation ID), exact kill-switch/flag steps, symptom→diagnosis→action table, and a rollback recipe whose recovery is *verified by a concrete command*. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/runbooks/<slug>.md`.

## Blameless postmortem

Mandatory after every **SEV-1 / SEV-2**, and after **any compliance or automated-action incident regardless of severity**. Blameless = fix systems, not people. Quantifies impact in business terms (financial, audit records lost, SLO breaches), a factual UTC timeline, true root cause (via `systematic-debugging`, trigger vs underlying cause), what went well/wrong/lucky ("lucky" items are prevention work), and **owned, dated, tracked action items**. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/incidents/<date>-<slug>.md`.

## Feed the loop — lessons-learned + `/propose-rule`

Action items don't die in the doc — each prevent/detect/mitigate item is tracked to closure. When the same root cause surfaced in **≥3 runs/incidents**, propose a durable rule via `/propose-rule` so the Engineering OS itself learns; otherwise log in `lessons-learned.md`. The fix often lands at Stage 8 (see `finishing-a-development-branch`).

## Anti-patterns

- **Diagnosing before mitigating** a SEV-1 — stop the bleeding first.
- **Under-calling severity** — default to SEV-1 + Security Reviewer on a maybe-compliance/data/financial event.
- **No IC** — everyone fixes, no one coordinates.
- **Skipping the postmortem** because "we already fixed it" — the system doesn't learn.
- **Action items with no owner/date/tracking** — theatre.
- **Silently swallowing a dropped audit-log write** — a lost record; retry + backfill from the event log.
- **Disabling a compliance gate to "unblock"** — never; converts a SEV-2 into a SEV-1.

## References

- The Product Canon's `PLAYBOOK-incident.md` — SLOs, alarms, kill switches, compliance counters
- `engineering-os-blueprint/07-operations-and-reliability.md` — reliability, SLOs, recovery
- Related: `operational-readiness`, `observability`, `progressive-delivery`, `finishing-a-development-branch`, `decision-log`, `systematic-debugging`, `security-baseline`
