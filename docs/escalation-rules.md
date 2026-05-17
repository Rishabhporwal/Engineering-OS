# Section 3.4 — Escalation Rules

When a gate fails, when agents disagree, or when something unexpected happens, this document tells you **who to escalate to, with what evidence, and on what timeline**.

Escalation has three flavors:
1. **Bounce-back** — within the pipeline, normal flow. (Already defined in [quality-gates.md §Gate failure → bounce conventions](quality-gates.md#gate-failure--bounce-conventions).)
2. **Sideways escalation** — to a peer (e.g., dev → security for an open question that isn't a gate failure).
3. **Up-escalation** — to CTO Advisor or Founder when the matter exceeds the current agent's authority.

---

## Up-escalation triggers

### Escalate to CTO Advisor

Use when you need a **technical / process** decision that is above your authority bound.

| Trigger | From | Evidence | CTOA expected to … |
|---------|------|----------|--------------------|
| Architectural ambiguity | Any builder | What's ambiguous + 2 plausible interpretations | Decide or refer to Aryan with a directive |
| Cross-team conflict | Any agent | Both positions + their reasoning | Mediate; record the call in the decision log |
| Cost paradigm dispute | Maya, Vikram, Aryan | Proposed paradigm + cheaper alternative considered | Decide paradigm or escalate cost to Founder |
| Gate interpretation question | Any agent | The specific gate condition + the ambiguous evidence | Clarify the gate or update it |
| Persistent bounce loop (>3 cycles same gate) | QA, Security | Bounce history | Either accept tech debt with a waiver, or restructure the task |
| Plan vs. reality drift | Any builder | Where the plan diverges from what's possible | Either re-plan (Stage 2 bounce) or accept the divergence with note |
| Adding a recommended skill | Any agent | Why current skills are insufficient | Approve / defer / reject |

### Escalate to Founder (Rishabh)

Use when you need a **strategic / business / scope** decision that is above CTO Advisor's authority.

| Trigger | From | Evidence | Founder expected to … |
|---------|------|----------|----------------------|
| Tech-stack change (new layer) | Aryan (via CTOA) | `tech-stack-evaluation` artifact; ADR-001 draft | Approve / reject / defer |
| Region addition | Aryan (via CTOA) | RegionAdapter plan; cost estimate | Approve / sequence later |
| Partner commitment (new) | CTOA, Maya | Partner brief; integration cost; switching cost | Approve / defer |
| Pricing impact (any change that affects per-brand cost > 5%) | CTOA | Cost delta + revenue impact | Approve / re-price / kill |
| Compliance scope change (new regime) | Shreya (via CTOA) | What changes; deadline; cost | Approve / defer / scope down |
| Cost cap breach (live) | Jatin, Maya | Token usage chart + last 30d trend | Decide: raise cap, throttle harder, kill feature |
| Customer-visible incident | Jatin (via CTOA) | Incident report; blast radius; status | Decide: customer comms, refund, rollback strategy |
| Stage 7 gate (always) | CTOA | `final-review.md` | Approve or reject the entire requirement |

---

## Page (P0) — immediate human attention

These conditions **page** the on-call human (in MVP: Rishabh + Jatin) within minutes. They are not "escalations" — they are **alerts**.

| Condition | Detected by | Pager target |
|-----------|-------------|--------------|
| **DND violation** in production calling | Lifecycle compliance engine assertion | Rishabh + Shreya (immediate) |
| **Cross-brand data leak** suspected | Audit log anomaly; cross-brand benchmark integrity check | Rishabh + Shreya |
| **Auth bypass** / multi-tenancy break | Production assertion (`workspace_id` mismatch) | Rishabh + Shreya |
| **Auto-execute** action with financial impact and **no rollback** | Auto-execute engine guard | Rishabh + Maya + Jatin |
| **LLM cost** > 1.5× monthly cap / 30 in a single day | CloudWatch alarm | Rishabh + Maya + Jatin |
| **Memory layer corruption** detected | Decision Log integrity check; Brand Fingerprint sanity check | Rishabh + Maya |
| **Production error rate** > 1% for 5 min | CloudWatch alarm | Jatin + Rishabh |
| **Health check** failing 2 consecutive probes (production) | EKS / ArgoCD | Jatin + Rishabh |

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

4. **Don't accept "yes, do it" without checking.** Even when the Founder says "yes, do it," if the request would push you past a hard gate (CRITICAL security, India compliance, Single-Primitive violation), respectfully challenge once more with the specific gate referenced.

---

## When escalation goes the other way

The team can — and must — push back on the Founder. Examples:

- Founder asks for "a WhatsApp-specific audience builder."
  → **CTOA pushes back:** "That violates the Single-Primitive Rule. We have one Audience Builder; WhatsApp is a channel that consumes it. Building a parallel one means N× engineering cost as we add channels. Recommend: extend Audience Builder with WhatsApp-specific filters (a 1-day change) instead of forking it (a 3-week change). Decision needed: confirm extend, or override and accept the tech-debt with a date for refactor."
- Founder asks for a feature that requires Sonnet, when Haiku would do.
  → **Maya pushes back via CTOA:** "This is ~10× the cost at expected load. Haiku tested at <task> shows 92% agreement with Sonnet. Recommend: ship with Haiku; flag a periodic A/B vs Sonnet for accuracy regression detection. Decision needed: confirm Haiku, or accept the cost."
- Founder approves a plan that has a missing dashboard.
  → **Jatin pushes back:** "Approving as-is means we won't see the new metric in CloudWatch. Recommend: 1-hour dashboard work before merge. Decision needed: confirm 1-hour delay, or ship blind with dashboard as fast-follow."

In every case: **constructive, evidence-based, with a path forward.** The Founder is the source of truth on intent; the team is the source of truth on implementation reality.

---

## Logging escalations

Every up-escalation (and every Founder-direction push-back) produces a journal entry **plus** a decision log entry:

**Per-agent journal entry:** narrative.

**Decision log entry (JSONL — one line):**
```json
{
  "ts": "2026-05-17T14:32:00Z",
  "actor": "cto-advisor",
  "type": "escalation",
  "to": "founder",
  "req_id": "feat-abandoned-cart-recovery-gcc",
  "topic": "paradigm-change",
  "summary": "Asked Founder to confirm Haiku over Sonnet; saves ~10x cost at expected load.",
  "decision": "pending",
  "decided_at": null
}
```

When the decision lands:

```json
{
  "ts": "2026-05-17T18:11:00Z",
  "actor": "rishabh",
  "type": "decision",
  "req_id": "feat-abandoned-cart-recovery-gcc",
  "topic": "paradigm-change",
  "decision": "confirmed-haiku",
  "rationale": "Cost wins; agreed to schedule Haiku-vs-Sonnet A/B in Phase 2.",
  "follow_up": "schedule-ab-haiku-vs-sonnet"
}
```

This makes every escalation **searchable** in the decision log. `/recall <topic>` (V2) finds prior similar decisions.

---

## Escalation SLAs (target, not hard)

| Type | Target response time |
|------|---------------------|
| Bounce-back (within pipeline) | <2 h working time |
| Sideways escalation | <4 h working time |
| Up-escalation to CTOA | <8 h working time |
| Up-escalation to Founder (non-page) | <24 h working time |
| Page (P0) | <15 min, human acknowledged |

These are targets. Pipeline status (`/status`) shows time-in-stage so it's visible when escalations stall.

---

## Related

- [operating-system.md](operating-system.md) — overall philosophy.
- [quality-gates.md](quality-gates.md) — gate definitions + bounce-note convention.
- [prompts/challenge-framework.md](../prompts/challenge-framework.md) — the canonical challenge structure.
- [prompts/anti-blind-agreement.md](../prompts/anti-blind-agreement.md) — the behavioral prompt every agent inherits.
