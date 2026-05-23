---
name: lifecycle-revenue-layer
description: Brain's revenue engine (canon/TECH/11) — lifecycle-service is a REVENUE CENTRE, not a cost centre. The Single-Primitive Audience (built once, consumed by call/WhatsApp/email/SMS/ad-audience/referral) with per-customer routing (high-value→call, mid→WhatsApp, low→email); RFM scoring (SQL), response modelling (ML), personalization (Haiku); the CallProvider vendor abstraction; the hard-coded compliance engine (09:00–21:00 IST, two-layer DND brand+NCPR, consent re-verify, DLT, 48h cap); the offer-governance ladder; attribution placed/realized/incremental; recovered-revenue 7d/30d → Decision Log. Always CM2-gated. Auto-load on any lifecycle-service work.
---

# Lifecycle & Revenue Execution Layer

`lifecycle-service` (Node orchestration + Python RFM/LLM) is the **[MOAT]** service that makes Brain a **revenue centre, not a cost centre.** The brand's team approves strategy; Brain runs the operation. **Every feature is judged on incremental rupees recovered or retained — not tickets deflected or hours saved.**

**Canonical source:** `canon/TECH/11_lifecycle_revenue_layer.md` · `canon/business-requirements.md` §11.

## The Single-Primitive Rule (this is where it lives or dies)

> Every cross-cutting concern is built **once** and consumed by every channel, agent, and workflow.

The **Audience** is the primitive: built once (RFM segment + custom filters), then simultaneously pushed to the call queue, WhatsApp queue, email queue, SMS queue, ad-platform custom-audience sync, and referral engine — with **per-customer channel routing** applied (`high-value → call`, `mid → WhatsApp`, `low → email`). Adding a channel costs engineering **1×** (a new router), not **N×**. **This is why GMV-% pricing survives** — competitors with per-channel stacks pay N× and price per-channel.

**Code-review blocks** (anti-pattern detection): "the email version of the audience builder", "a call-specific consent flow", "the WhatsApp Decision Log", "per-channel customer profiles". There is **one** audience builder, **one** consent model (core-service), **one** Decision Log (analytics-service), **one** unified customer record.

## Cost-routing paradigms in the pipeline

| Step | Paradigm | Why |
|---|---|---|
| RFM scoring | **1 — SQL** | `NTILE(5)` over the brand's own base, daily 06:30 IST |
| Response-rate / revenue-recovery modelling | **2 — ML** | patterns exist, rules don't |
| Message personalization | **3 — Haiku** | bounded NL, the *only* LLM in the pipeline |

No Sonnet, no LLM, in audience building or scoring ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)).

## RFM-triggered audience builder

RFM is a structured query against Customer Segment Memory ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md)) — not a separate feature. Three 1–5 scores per customer per day, **against the brand's own base** (never industry benchmarks):

- **Recency** — days since last order vs the brand's median repurchase cycle.
- **Frequency** — order count, trailing 365d.
- **Monetary** — total **CM2 contribution** (not Gross Sales), trailing 365d.

```sql
-- lifecycle-service daily job, 06:30 IST → rfm_score
NTILE(5) OVER (PARTITION BY brand_id ORDER BY days_since_last_order DESC) AS r_score,
NTILE(5) OVER (PARTITION BY brand_id ORDER BY order_count_365d ASC)      AS f_score,
NTILE(5) OVER (PARTITION BY brand_id ORDER BY cm2_contribution_365d ASC) AS m_score
```

**11 canonical segments** (Champions 5-5-5 → Lost 1-1-X) with default routing (Champions/Can't-Lose → call; Loyal/New → WhatsApp; Lost → email, do-not-call). One-click trigger returns audience size, modelled response rate, modelled revenue recovery, and recommended channel mix; the RFM score is **frozen as a snapshot** on `audience_member` at trigger time.

## Channel routers + CallProvider abstraction

One router per channel (`whatsapp-router` → WhatsApp Cloud API — replies inside the **free service window** (24h customer-service reply; 72h ad-click entry-point) skip per-message template billing, `email-router` → SES, `sms-router` → Gupshup/Kaleyra DLT-registered, `ad-audience-router` → Meta Custom Audience / Google Customer Match). AI calling hides the vendor behind a stable contract so swapping is config, not a rewrite:

```python
class CallProvider(ABC):
    async def place_call(self, brand_id, customer_phone, script_template_id, context) -> CallTicket: ...
    async def get_outcome(self, call_id) -> CallOutcome: ...

class BolnaProvider(CallProvider): ...   # Path A (India partner)
class VapiProvider(CallProvider): ...    # Path B (global partner)
class NativeStackProvider(CallProvider): ...  # Path C (build)
```

Multiple providers can run concurrently (Bolna for Hindi, Vapi for English) — the call-router picks by the customer's language tag. The vendor decision is the one place to use [`tech-stack-evaluation`](../tech-stack-evaluation/SKILL.md).

## The compliance engine (hard-coded, NOT feature-flaggable)

Shipped as core infrastructure on **every** calling/sending path (`lifecycle-service/compliance.py`). This is a Shreya VETO surface ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)):

| Rule | Implementation |
|---|---|
| **Calling hours 09:00–21:00 IST** | Blocked at **queue level** (not dialer). Pre-09:00 held in `pending_window`, flushed at 09:00; post-21:00 rescheduled next day. |
| **Two-layer DND** | Every number checked vs (a) brand's own opt-out list **and** (b) TRAI **NCPR** before dialing. NCPR cache refreshed weekly. |
| **Consent re-verify** | Excluded if `consent_status IN ('opted_out','withdrawn')` — checked **before every send**, not once. |
| **DLT templates** | Every post-call WhatsApp/SMS template registered under the **brand's** DLT entity — Brain never commingles brands' registrations. |
| **AI-voice disclosure + recording consent** | Every call opens with automated-caller disclosure; recording only if consented (else call proceeds, no audio retained). |
| **48h frequency cap** | No customer contacted more than once / 48h by any Brain flow. Override only for VIP + Owner approval logged in audit. |

`CallComplianceEngine.can_call()` returns `ok` / `deferred(reason)` / `blocked(reason)`. **Compliance SLO: 0 DND-blocked + 0 out-of-window dial attempts** — non-zero is a rule violation.

> **TRAI is sharpening rules on AI-driven / robocall telemarketing** (advance auto-dialer notification, call traceability) — Brain's AI-calling is in scope; keep the calling-hours / DLT / NCPR / DND / 48h-cap discipline above and verify the advance-notification + traceability path before any AI call fires ([`agentic-actions-auditor`](../agentic-actions-auditor/SKILL.md)).

## The offer-governance ladder (always CM2-gated)

Discount-led lifecycle destroys margin — so offers escalate only as needed (business-requirements §11.4):

1. **No discount** — service, urgency, education, reminder, social proof.
2. **Low-cost value-add** — bundle, sample, gift where margin permits.
3. **Limited discount** — **only when expected CM2 remains positive** after message + offer + RTO cost.
4. **Escalated retention offer** — high-value customer or high-risk save.
5. **Human review** — low confidence, high cost, sensitive customer.

Never discount where expected CM2 is negative. CM2 gating + the ladder is the canonical mitigation against margin destruction (business-requirements §22).

## Attribution → Decision Log (the moat)

Three views (business-requirements §11.5), and **every lifecycle surface shows realized revenue + CM2, not just placed**:

- **Placed** — customer clicked/replied and ordered within the window.
- **Realized** — order delivered/paid/settled after post-order leakage (the honest number).
- **Incremental** — campaign cohort vs holdout/baseline where testing exists.

Recovered revenue is attributed at **7d and 30d** and written back to `ai.decision_log` (`recovered_revenue_7d_minor`, `recovered_revenue_30d_minor`, `channel`). The North-Star metric is **Recovered Revenue ÷ Brain GMV Fee** (target > 3× by month 3, > 5× by month 6 — below 3× means the brand is paying for a cost centre).

## Anti-patterns

- A per-channel fork of the audience builder / consent / Decision Log / customer profile.
- A discount where expected CM2 is negative; skipping the offer ladder.
- A send/call that bypasses the compliance engine or doesn't re-verify consent.
- Vendor-specific calling code outside `CallProvider`.
- Reporting placed revenue without realized + CM2.
- A lifecycle send without 7d/30d attribution into the Decision Log (canon §16).

## Verify

- A pre-09:00 IST call is held in `pending_window` and flushed at 09:00; a NCPR-listed or opted-out number is blocked (test both DND layers).
- One audience triggers across N channels from a single primitive; routing matches RFM tier.
- A converted outreach writes recovered revenue to the Decision Log at 7d and 30d; the surface shows realized + CM2.

## References

- `canon/TECH/11_lifecycle_revenue_layer.md` — full service, segments, compliance engine, data model
- `canon/business-requirements.md` §11 — offer ladder + attribution requirements
- [`india-commerce-economics`](../india-commerce-economics/SKILL.md) · [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) · [`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md) · [`metric-engine`](../metric-engine/SKILL.md)
