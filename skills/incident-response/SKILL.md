---
name: incident-response
description: Brain's run-time incident discipline — what to do when production breaks. The severity ladder (SEV-1 = compliance violation / data exposure / auto-execute financial damage / Decision-Log write outage; SEV-2 = Morning-Brief SLO miss / connector-wide outage; SEV-3 = degraded), the Incident Commander role + comms, the detect→mitigate→resolve flow, the kill switches (Owner auto-execute pause within 60s, per-action, feature flags), blameless postmortems via `blueprints/postmortem.md`, runbooks via `blueprints/runbook.md`, and feeding action items into the lessons-learned registry / `/propose-rule`. Brain-specific incidents: a DND/out-of-window send, auto-execute reversal-rate breach, a missed Morning Brief, a Decision-Log write failure, connector mass-staleness. Owner Jatin. Use when an alarm fires, a customer reports breakage, or you write a runbook/postmortem.
---

# Incident Response — when Brain breaks in production

[`operational-readiness`](../operational-readiness/SKILL.md) is the gate that keeps a service from shipping broken; **this skill is what happens after it ships and breaks anyway.** Brain is an *acting* system — it sends WhatsApp/calls under telecom law, executes reversible commerce actions, and writes the moat (the Decision Log). So an incident here isn't just "the dashboard is down" — it can be a **compliance violation**, **financial damage from an auto-execute loop**, or **lost moat**. The discipline below maps each of those to a severity, an owner, and a kill switch.

**Canonical doc:** `canon/TECH/09_security_observability.md` (SLOs, alarms, kill switches) + `canon/technical-requirements.md` §14. Owner: **Jatin** (DevOps / on-call). Detection rides the observability spine — one correlation ID (`request_id`+`trace_id`+`workspace_id`+`user_id`) end-to-end ([`observability`](../observability/SKILL.md)).

## The severity ladder

| SEV | Definition (Brain-specific) | Examples | Response |
|---|---|---|---|
| **SEV-1** | Compliance violation · customer-data exposure · cross-brand leak · auto-execute financial damage · **Decision-Log write outage** (the moat is going un-written) | DND/out-of-window send fired · cross-brand data visible to another workspace · auto-execute reversal/error rate past threshold burning real money · `ai.decision_log` writes failing (99.99% SLO breached) | Page immediately · IC assigned · **Shreya looped on any compliance/data item** · Founder notified for financial/compliance/data exposure · kill switch first, diagnose second |
| **SEV-2** | Core surface down but no compliance/data/financial harm | **Morning Brief missed the 07:20 IST / 99.5% SLO** for many workspaces · a P0 connector class outage (mass staleness, all brands) · api-gateway error spike | Page on-call · IC for multi-workspace impact · mitigate to restore the surface (degrade gracefully) |
| **SEV-3** | Degraded / single-workspace / non-urgent | one connector stale for one brand · elevated p95 within SLO · a non-critical agent run failed and retried | Ticket + runbook · handle in hours · no page |

**Escalation, not certainty, is the trigger:** if it *might* be compliance, data exposure, or financial damage, treat it as SEV-1 until proven otherwise and loop Shreya. Under-calling these is the expensive mistake.

## Incident Commander (IC) + comms

Every SEV-1/SEV-2 gets **one IC** (default Jatin, or whoever is on-call) who **coordinates — does not solo-fix**. The IC: declares severity, owns the timeline, decides mitigations (kill switch / rollback / degrade), pulls in domain owners (Maya for agents/LLM, Shreya for compliance/security, Aryan for architecture, the surface's builder), and runs comms. Comms cadence: an incident channel, a status line at declaration + each state change, and — for any compliance/data/financial SEV-1 — Founder notification. **Affected workspaces are quantified** (the postmortem needs "N workspaces vs the 07:20 SLO," not "some users").

## detect → mitigate → resolve

```
DETECT   alarm (CloudWatch/Sentry) · customer report · failed agent run · compliance counter > 0
   ▼     IC declares severity; opens incident channel; starts the timeline
MITIGATE stop the bleeding FIRST — kill switch / feature flag / ArgoCD rollback / degrade-gracefully
   ▼     restore the surface or halt the harm before chasing root cause
RESOLVE  root-cause via `systematic-debugging` (trace backward, don't guess); ship the real fix;
   ▼     verify recovery with the exact command in the runbook (don't claim "back" — prove it)
POST     blameless postmortem (SEV-1/SEV-2 + any compliance/auto-execute incident) → action items → registry
```

**Mitigate before you understand.** A DND send firing or an auto-execute loop losing money is stopped *now* (kill switch); the root cause is found *after* the bleeding stops. Use [`systematic-debugging`](../systematic-debugging/SKILL.md) for root cause — never patch the symptom.

## The kill switches (Brain's first-line mitigation)

These exist precisely so an SEV-1 can be contained in seconds:

- **Owner auto-execute kill switch — pauses ALL auto-execute in ≤ 60s** (canon SLO). The IC can direct an Owner to hit it; for a fleet-wide auto-execute incident, the global flag halts auto-execute across workspaces. After a breach, autonomy **auto-reverts to recommend-only** when the reversal/error rate crosses threshold (alert at 15%, SLO < 8%).
- **Per-action kill switch** — disable a single action class (e.g. just `courier_switch`) without killing the rest.
- **Feature flags** — disable a surface (a connector, AI Chat, a new agent) without a deploy. Wired at ship time per [`operational-readiness`](../operational-readiness/SKILL.md); flipping one is the fastest SEV-2 mitigation.
- **Compliance engine fail-closed** — the lifecycle compliance engine refuses to send outside 09:00–21:00 IST, on DND/NCPR hits, or without consent. A *send that escaped it* is the SEV-1; the mitigation is to halt outbound (flag) and preserve evidence ([`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md), [`security-baseline`](../security-baseline/SKILL.md)).

Reversals must themselves be logged: an auto-execute reversal updates the same `ai.decision_log` row with a `reversal` payload — an un-audited undo is its own finding.

## The Brain-specific incident playbook (each gets a runbook)

| Incident | SEV | First move (mitigate) | Then |
|---|---|---|---|
| **DND / out-of-window send fired** | SEV-1 | Halt outbound (flag); loop Shreya + Founder | Trace which consent/window check was bypassed; preserve evidence; this is a reportable compliance event |
| **Auto-execute reversal-rate breach** | SEV-1 | Owner/global auto-execute kill switch (≤60s); auto-revert already trips at threshold | Decision-Log reversal query → which action class / model drift; re-baseline before re-enabling |
| **Morning Brief missed (07:20 IST)** | SEV-2 | Rerun the daily tick or degrade to a SQL+ML template brief; ensure push still goes | Check tick stall / Sonnet timeout / LLM cap / freshness gate; protect tomorrow's run |
| **Decision-Log write failure** (99.99% SLO) | SEV-1 | Retry via the transactional outbox; never silently swallow a dropped write | Each dropped write is lost moat — backfill from the Kafka topic (retained forever); find why the write path failed |
| **Connector mass-staleness** (P0 freshness >1h, all brands) | SEV-2 | Mark connector degraded; **agents must label stale data, not act on it** | Token refresh / vendor outage / rate-limit; backfill window (backfill == live) ([`integration-connectors`](../integration-connectors/SKILL.md)) |
| **Cross-brand data leak** | SEV-1 | Disable the leaking surface; loop Shreya + Founder | Which of the 4 `workspace_id` layers failed (JWT/RLS/CH gateway/MCP); P0 — zero tolerance |

## Runbooks — `blueprints/runbook.md`

Every service and every known failure scenario above has a runbook authored by the owning builder, reviewed by Jatin. A runbook is **for the person paged at 3am who didn't write the code**: healthcheck command, log query (with the correlation ID), the exact kill-switch/flag steps, symptom→diagnosis→action table, and a rollback recipe whose recovery is *verified by a concrete command*, not assumed. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/runbooks/<slug>.md`.

## Blameless postmortem — `blueprints/postmortem.md`

Mandatory after every **SEV-1 / SEV-2**, and after **any compliance or auto-execute incident regardless of severity**. Blameless = we fix systems, not people. It quantifies impact in business terms (revenue/CM2, Decision-Log writes lost, Briefs missed vs SLO, compliance exposure), a factual UTC timeline, the true root cause (via [`systematic-debugging`](../systematic-debugging/SKILL.md), trigger vs underlying cause), what went well/wrong/lucky (the "lucky" items are P0 prevention work), and **owned, dated, tracked action items** — the point of the exercise. Saved to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/incidents/<date>-<slug>.md`.

## Feed the loop — lessons-learned + `/propose-rule`

Action items don't die in the doc. Each prevent/detect/mitigate item is tracked to closure (often a Decision-Log or tracker entry). When the same root cause has surfaced in **≥3 runs/incidents**, propose a durable rule via `/propose-rule` so the Engineering OS itself learns; otherwise log it in `lessons-learned.md`. A guardrail/SLO/threshold change made in response is recorded with who approved it. The fix often lands at Stage 8 commit discipline — see [`finishing-a-development-branch`](../finishing-a-development-branch/SKILL.md) (explicit-path staging, never delete Decision-Log/audit rows, push-success gate).

## Anti-patterns

- **Diagnosing before mitigating** a SEV-1 — a DND send or money-losing auto-execute loop is *stopped first*.
- **Under-calling severity** — "probably fine" on a maybe-compliance/data/financial event; default to SEV-1 + Shreya.
- **No IC** — everyone fixes, no one coordinates or communicates.
- **Skipping the postmortem** because "we already fixed it" — the system doesn't learn.
- **Action items with no owner/date/tracking** — the postmortem becomes theatre.
- **Silently swallowing a dropped Decision-Log write** — that's lost moat; retry + backfill from the topic.
- **Disabling a compliance gate to "unblock"** — never; that converts a SEV-2 into a SEV-1.

## References

- `canon/TECH/09_security_observability.md` — SLOs, alarms, kill switches, compliance counters
- `canon/technical-requirements.md` §14 — SLO table (07:20 Morning Brief, 99.99% Decision-Log write, <8% reversal)
- `blueprints/runbook.md` · `blueprints/postmortem.md`
- [`operational-readiness`](../operational-readiness/SKILL.md) · [`observability`](../observability/SKILL.md) · [`finishing-a-development-branch`](../finishing-a-development-branch/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`systematic-debugging`](../systematic-debugging/SKILL.md) · [`security-baseline`](../security-baseline/SKILL.md) · [`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md)
