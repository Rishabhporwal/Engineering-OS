# Section 3.4 — Escalation Rules

When a gate fails, when agents disagree, or when something unexpected happens, this document tells you **who to escalate to, with what evidence, and on what timeline**.

Escalation has three flavors:
1. **Bounce-back** — within the pipeline, normal flow. (Already defined in [quality-gates.md §Gate failure → bounce conventions](quality-gates.md#gate-failure--bounce-conventions).)
2. **Sideways escalation** — to a peer (e.g., dev → security for an open question that isn't a gate failure).
3. **Up-escalation** — to the Engineering Advisor or the Stakeholder when the matter exceeds the current agent's authority.

---

## Up-escalation triggers

### Escalate to the Engineering Advisor

Use when you need a **technical / process** decision that is above your authority bound.

| Trigger | From | Evidence | Advisor expected to … |
|---------|------|----------|--------------------|
| Architectural ambiguity | Any builder | What's ambiguous + 2 plausible interpretations | Decide or refer to the Architect with a directive |
| Cross-team conflict | Any agent | Both positions + their reasoning | Mediate; record the call in the audit log |
| Effort-tier dispute (cheapest-sufficient-effort) | AI/ML Engineer, Backend Engineer, Architect | Proposed effort tier + cheaper alternative considered | Decide the tier or escalate cost to the Stakeholder |
| Gate interpretation question | Any agent | The specific gate condition + the ambiguous evidence | Clarify the gate or update it |
| Persistent bounce loop (>3 cycles same gate) | QA, Security | Bounce history | Either accept tech debt with a waiver, or restructure the task |
| Plan vs. reality drift | Any builder | Where the plan diverges from what's possible | Either re-plan (Stage 2 bounce) or accept the divergence with note |
| Adding a recommended skill | Any agent | Why current skills are insufficient | Approve / defer / reject |

### Escalate to the Stakeholder

Use when you need a **strategic / scope / cost** decision that is above the Engineering Advisor's authority.

| Trigger | From | Evidence | Stakeholder expected to … |
|---------|------|----------|----------------------|
| Tech-stack change (new layer) | Architect (via Advisor) | `tech-stack-evaluation` artifact; ADR draft | Approve / reject / defer |
| Region / locale addition | Architect (via Advisor) | RegionAdapter plan; cost estimate | Approve / sequence later |
| External dependency / partner commitment (new) | Advisor, AI/ML Engineer | Brief; integration cost; switching cost | Approve / defer |
| Cost impact (any change that materially raises per-tenant cost) | Advisor | Cost delta + impact | Approve / re-scope / kill |
| Compliance scope change (new regime in `COMPLIANCE.md`) | Security Reviewer (via Advisor) | What changes; deadline; cost | Approve / defer / scope down |
| Cost cap breach (live) | Platform/SRE, AI/ML Engineer | Cost-usage chart + recent trend | Decide: raise cap, throttle harder, kill feature |
| Customer-visible incident | Platform/SRE (via Advisor) | Incident report; blast radius; status | Decide: comms, remediation, rollback strategy |
| Deploy gate (always) | Advisor | `final-review.md` | Approve or reject the entire requirement |

---

## Page (P0) — immediate human attention

These conditions **page** the on-call human within minutes. They are not "escalations" — they are **alerts**. (Concrete surfaces + thresholds come from the product's `TRIGGER-SURFACES.md`, `COMPLIANCE.md`, and `PLAYBOOK-incident.md`.)

| Condition | Detected by | Pager target |
|-----------|-------------|--------------|
| **Compliance-regime violation** in production (e.g. a channel/consent rule from `COMPLIANCE.md`) | Runtime compliance assertion | Stakeholder + Security |
| **Cross-tenant data leak** suspected | Audit-log anomaly; isolation integrity check | Stakeholder + Security |
| **Auth bypass** / tenant-isolation break | Production assertion (tenant-key mismatch) | Stakeholder + Security |
| **Irreversible action** with consequential impact and **no rollback** | Action guard | Stakeholder + AI/ML Engineer + Platform/SRE |
| **Model/LLM cost** spikes well past the daily budget | Cost alarm | Stakeholder + AI/ML Engineer + Platform/SRE |
| **System-of-record (audit-log) corruption** detected | Audit-log integrity check | Stakeholder + AI/ML Engineer |
| **Production error rate** > 1% for 5 min | Metrics alarm | Platform/SRE + Stakeholder |
| **Health check** failing 2 consecutive probes (production) | Orchestrator / deploy platform | Platform/SRE + Stakeholder |

---

## Anti-blind-agreement in escalation

When you escalate up:

1. **Don't dump and run.** Bring the structured challenge:
   - What I understood.
   - What I'm concerned about.
   - What risk that introduces.
   - What I recommend instead.
   - What decision I need.

2. **Don't escalate to skip the work.** Try the work first. Escalate when you've hit a true authority boundary.

3. **Don't ask the same question twice.** Read the decision log first — has this come up before?

4. **Don't accept "yes, do it" without checking.** Even when the Stakeholder says "yes, do it," if the request would push you past a hard gate (CRITICAL security, a compliance violation, a Single-Primitive violation), respectfully challenge once more with the specific gate referenced.

---

## When escalation goes the other way

The team can — and must — push back on the Stakeholder. Examples:

- Stakeholder asks for "a channel-specific audience builder" (a parallel copy of an existing primitive).
  → **The Advisor pushes back:** "That violates the Single-Primitive Rule. We have one shared builder; the new channel is a consumer of it. Building a parallel one means N× engineering cost as we add channels. Recommend: extend the shared builder with channel-specific filters (a 1-day change) instead of forking it (a 3-week change). Decision needed: confirm extend, or override and accept the tech-debt with a date for refactor."
- Stakeholder asks for a feature that requires a large model, when a small model would do.
  → **The AI/ML Engineer pushes back via the Advisor:** "This is ~10× the cost at expected load. The small model tested at <task> shows 92% agreement with the large one. Recommend: ship on the small model; flag a periodic A/B vs the large model for accuracy-regression detection. Decision needed: confirm the small model, or accept the cost."
- Stakeholder approves a plan that has a missing dashboard.
  → **Platform/SRE pushes back:** "Approving as-is means we won't see the new metric in monitoring. Recommend: 1-hour dashboard work before merge. Decision needed: confirm 1-hour delay, or ship blind with the dashboard as a fast-follow."

In every case: **constructive, evidence-based, with a path forward.** The Stakeholder is the source of truth on intent; the team is the source of truth on implementation reality.

---

## Logging escalations

Every up-escalation (and every Stakeholder-direction push-back) produces a journal entry **plus** an audit-log entry:

**Per-agent journal entry:** narrative.

**Audit-log entry (JSONL — one line):**
```json
{
  "ts": "2026-05-17T14:32:00Z",
  "actor": "cto-advisor",
  "type": "escalation",
  "to": "stakeholder",
  "req_id": "feat-example-slug",
  "topic": "effort-tier-change",
  "summary": "Asked the Stakeholder to confirm the small model over the large one; saves ~10x cost at expected load.",
  "decision": "pending",
  "decided_at": null
}
```

When the decision lands:

```json
{
  "ts": "2026-05-17T18:11:00Z",
  "actor": "stakeholder",
  "type": "decision",
  "req_id": "feat-example-slug",
  "topic": "effort-tier-change",
  "decision": "confirmed-small-model",
  "rationale": "Cost wins; agreed to schedule a small-vs-large A/B as a follow-up.",
  "follow_up": "schedule-ab-small-vs-large"
}
```

This makes every escalation **searchable** in the audit log. `/recall <topic>` finds prior similar decisions.

---

## Escalation SLAs (target, not hard)

| Type | Target response time |
|------|---------------------|
| Bounce-back (within pipeline) | <2 h working time |
| Sideways escalation | <4 h working time |
| Up-escalation to the Engineering Advisor | <8 h working time |
| Up-escalation to the Stakeholder (non-page) | <24 h working time |
| Page (P0) | <15 min, human acknowledged |

These are targets. Pipeline status (`/status`) shows time-in-stage so it's visible when escalations stall.

---

## Related

- [`engineering-os-blueprint/01-organization-structure.md`](../engineering-os-blueprint/01-organization-structure.md) — overall philosophy.
- [quality-gates.md](quality-gates.md) — gate definitions + bounce-note convention.
- [prompts/challenge-framework.md](../prompts/challenge-framework.md) — the canonical challenge structure.
- [prompts/anti-blind-agreement.md](../prompts/anti-blind-agreement.md) — the behavioral prompt every agent inherits.
