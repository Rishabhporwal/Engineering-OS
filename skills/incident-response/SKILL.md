---
name: incident-response
description: Run-time incident discipline — severity ladder, Incident Commander, detect→mitigate→resolve, ≤60s kill switches, blameless postmortems → lessons-learned loop. Owner Jatin.
---

# Incident Response — when Brain breaks in production

`operational-readiness` is the gate that keeps a service from shipping broken; **this skill is what happens after it ships and breaks anyway.** Brain is an *acting* system — it sends WhatsApp/calls under telecom law, executes reversible commerce actions, and writes the moat (the Decision Log). So an incident can be a **compliance violation**, **financial damage from an auto-execute loop**, or **lost moat**.

**Canonical doc:** `canon/TECH/09_security_observability.md` + `canon/technical-requirements.md` §14. Owner: **Jatin** (on-call). Detection rides the observability spine (one correlation ID end-to-end — see `observability`).

## The severity ladder

| SEV | Definition (Brain-specific) | Examples | Response |
|---|---|---|---|
| **SEV-1** | Compliance violation · customer-data exposure · cross-brand leak · auto-execute financial damage · **Decision-Log write outage** | DND/out-of-window send fired · cross-brand data visible · auto-execute reversal rate past threshold burning money · `ai.decision_log` writes failing (99.99% SLO) | Page now · IC assigned · **Shreya looped on any compliance/data item** · Founder notified for financial/compliance/data · kill switch first, diagnose second |
| **SEV-2** | Core surface down, no compliance/data/financial harm | **Morning Brief missed 07:20 IST / 99.5% SLO** · P0 connector class outage (mass staleness) · api-gateway error spike | Page on-call · IC for multi-workspace impact · mitigate to restore (degrade gracefully) |
| **SEV-3** | Degraded / single-workspace / non-urgent | one connector stale for one brand · elevated p95 within SLO · a non-critical agent run failed + retried | Ticket + runbook · handle in hours · no page |

**Escalation, not certainty, is the trigger:** if it *might* be compliance, data exposure, or financial damage, treat as SEV-1 until proven otherwise and loop Shreya. Under-calling is the expensive mistake.

## Incident Commander (IC) + comms

Every SEV-1/SEV-2 gets **one IC** (default Jatin/on-call) who **coordinates — does not solo-fix**. IC declares severity, owns the timeline, decides mitigations (kill switch / rollback / degrade), pulls in domain owners (Maya for agents/LLM, Shreya for compliance/security, Aryan for architecture, the surface's builder), runs comms. Cadence: an incident channel, a status line at declaration + each state change, and Founder notification for any compliance/data/financial SEV-1. **Affected workspaces are quantified** ("N workspaces vs the 07:20 SLO", not "some users").

## detect → mitigate → resolve

```
DETECT   alarm (CloudWatch/Sentry) · customer report · failed agent run · compliance counter > 0
   ▼     IC declares severity; opens incident channel; starts the timeline
MITIGATE stop the bleeding FIRST — kill switch / feature flag / ArgoCD rollback / degrade-gracefully
   ▼     restore the surface or halt the harm before chasing root cause
RESOLVE  root-cause via systematic-debugging (trace backward); ship the real fix;
   ▼     verify recovery with the exact runbook command (don't claim "back" — prove it)
POST     blameless postmortem (SEV-1/SEV-2 + any compliance/auto-execute incident) → action items → registry
```

**Mitigate before you understand.** A DND send or money-losing auto-execute loop is stopped *now* (kill switch); root cause is found *after*. Use `systematic-debugging` for root cause — never patch the symptom.

## The kill switches (first-line mitigation)

- **Owner auto-execute kill switch — pauses ALL auto-execute in ≤ 60s** (canon SLO). Global flag for fleet-wide. After a breach, autonomy **auto-reverts to recommend-only** when reversal/error rate crosses threshold (alert at 15%, SLO < 8%).
- **Per-action kill switch** — disable a single action class (e.g. just `courier_switch`).
- **Feature flags** — disable a surface (connector, AI Chat, new agent) without a deploy. Wired at ship time (`operational-readiness`).
- **Compliance engine fail-closed** — refuses to send outside 09:00–21:00 IST, on DND/NCPR hits, or without consent. A *send that escaped it* is the SEV-1; mitigation is to halt outbound (flag) and preserve evidence.

Reversals must themselves be logged: an auto-execute reversal updates the same `ai.decision_log` row with a `reversal` payload — an un-audited undo is its own finding.

## The Brain-specific incident playbook (each gets a runbook)

| Incident | SEV | First move (mitigate) | Then |
|---|---|---|---|
| **DND / out-of-window send fired** | SEV-1 | Halt outbound (flag); loop Shreya + Founder | Trace which consent/window check was bypassed; preserve evidence; reportable compliance event |
| **Auto-execute reversal-rate breach** | SEV-1 | Owner/global kill switch (≤60s); auto-revert trips at threshold | Decision-Log reversal query → action class / model drift; re-baseline before re-enabling |
| **Morning Brief missed (07:20 IST)** | SEV-2 | Rerun the daily tick or degrade to SQL+ML template brief; ensure push still goes | Check tick stall / Sonnet timeout / LLM cap / freshness gate; protect tomorrow's run |
| **Decision-Log write failure** (99.99% SLO) | SEV-1 | Retry via transactional outbox; never silently swallow | Each dropped write is lost moat — backfill from the Kafka topic (retained forever) |
| **Connector mass-staleness** (P0 freshness >1h) | SEV-2 | Mark connector degraded; **agents label stale data, not act on it** | Token refresh / vendor outage / rate-limit; backfill window (backfill == live) |
| **Cross-brand data leak** | SEV-1 | Disable the leaking surface; loop Shreya + Founder | Which of the 4 `workspace_id` layers failed (JWT/RLS/CH gateway/MCP); P0 — zero tolerance |

## Runbooks — `blueprints/runbook.md`

Every service + known failure scenario has a runbook by the owning builder, reviewed by Jatin. **For the person paged at 3am who didn't write the code:** healthcheck command, log query (with correlation ID), exact kill-switch/flag steps, symptom→diagnosis→action table, and a rollback recipe whose recovery is *verified by a concrete command*. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/runbooks/<slug>.md`.

## Blameless postmortem — `blueprints/postmortem.md`

Mandatory after every **SEV-1 / SEV-2**, and after **any compliance or auto-execute incident regardless of severity**. Blameless = fix systems, not people. Quantifies impact in business terms (revenue/CM2, Decision-Log writes lost, Briefs missed vs SLO), a factual UTC timeline, true root cause (via `systematic-debugging`, trigger vs underlying cause), what went well/wrong/lucky ("lucky" items are P0 prevention work), and **owned, dated, tracked action items**. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/incidents/<date>-<slug>.md`.

## Feed the loop — lessons-learned + `/propose-rule`

Action items don't die in the doc — each prevent/detect/mitigate item is tracked to closure. When the same root cause surfaced in **≥3 runs/incidents**, propose a durable rule via `/propose-rule` so the Engineering OS itself learns; otherwise log in `lessons-learned.md`. The fix often lands at Stage 8 (see `finishing-a-development-branch`).

## Anti-patterns

- **Diagnosing before mitigating** a SEV-1 — stop the bleeding first.
- **Under-calling severity** — default to SEV-1 + Shreya on a maybe-compliance/data/financial event.
- **No IC** — everyone fixes, no one coordinates.
- **Skipping the postmortem** because "we already fixed it" — the system doesn't learn.
- **Action items with no owner/date/tracking** — theatre.
- **Silently swallowing a dropped Decision-Log write** — lost moat; retry + backfill from the topic.
- **Disabling a compliance gate to "unblock"** — never; converts a SEV-2 into a SEV-1.

## References

- `canon/TECH/09_security_observability.md` — SLOs, alarms, kill switches, compliance counters
- `canon/technical-requirements.md` §14 — SLO table (07:20 Morning Brief, 99.99% Decision-Log write, <8% reversal)
- `blueprints/runbook.md` · `blueprints/postmortem.md`
- Related: `operational-readiness`, `observability`, `finishing-a-development-branch`, `decision-log`, `systematic-debugging`, `security-baseline`, `lifecycle-revenue-layer`
