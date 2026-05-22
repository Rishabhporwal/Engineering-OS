# TECH/11 — Lifecycle & Revenue Execution Layer (lifecycle-service)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 + E1 (architecture) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/05_intelligence_layer.md](05_intelligence_layer.md), [TECH/12_cost_routing_compute.md](12_cost_routing_compute.md)

**Positioning:** This layer makes Brain a **revenue centre, not a cost centre.** The brand's team approves strategy; Brain runs the operation. Every feature here is judged on incremental rupees recovered or retained, not on tickets-deflected or hours-saved.

**Truncation note:** the source brief was cut off mid-Section 9.9. Sections 9.10+ and Section 14 (Channel Expansion) were not in source. Marked `TBD per brief` where relevant.

---

## 1. The Single-Primitive Rule (Strategic Foundation)

This service is where the **Single-Primitive Rule** of Brain's architecture lives or dies. The rule:

> Every cross-cutting concern is built **once** and consumed by every channel, every agent, every workflow.

The single primitives owned in or consumed by lifecycle-service:

| Primitive | Owner Service | Consumed By |
|-----------|--------------|-------------|
| **Audience builder** (RFM-triggered) | lifecycle-service | call queue, WhatsApp queue, email queue, SMS queue, ad-platform custom audience sync, referral engine |
| **Decision Log** | analytics-service | All agents; lifecycle outcomes attribute back here |
| **Consent model** | core-service | All outbound channels gate on it |
| **Notification framework** | notifications-service | In-app + email + push + WhatsApp transactional |
| **Attribution** | analytics-service | Lifecycle outcomes feed in |
| **Identity resolution** | core-service | One customer record per brand across all channels |

### Anti-Pattern Detection

If any of the following appear in a PR, **block at code review:**

- "The email version of the audience builder" → consume the existing one
- "The call-specific consent flow" → extend the consent model, do not fork
- "The WhatsApp Decision Log" → there is only one Decision Log
- "A new notification service for SMS alerts" → extend the existing notification framework
- "Per-channel customer profiles" → use the unified customer record

### Why This Matters

Adding a new channel must cost engineering **1x** (the channel adapter), not **Nx**. Brain's GMV % pricing depends on it: competitors with per-channel stacks pay Nx engineering cost for N channels and either price per-channel or run at lower margin. Brain pays 1x and bundles all channels at the same fee.

The **quarterly streamlining audit** (in TECH/12 §6) catches drift before it compounds.

---

## 2. Service Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                       lifecycle-service                                │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ gRPC Server (Node — orchestration; Python — RFM scoring + LLM)   ││
│  │  • BuildAudience           • TriggerOutreach                     ││
│  │  • LaunchCampaign          • GetTicketFeed                       ││
│  │  • UpdateConsent           • GetRecoveredRevenue                 ││
│  └──────────────────────────────┬──────────────────────────────────┘│
│                                  │                                     │
│  ┌──────────────────────────────▼──────────────────────────────────┐│
│  │ Audience Engine                                                  ││
│  │  • Daily RFM scoring (SQL — paradigm 1)                          ││
│  │  • 11 canonical segments + custom filters                        ││
│  │  • Audience materialization (frozen snapshot at trigger)         ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Channel Routers (one per channel; consumed by audience)          ││
│  │  • call-router       → AI calling vendor / native (see §5)       ││
│  │  • whatsapp-router   → WhatsApp Cloud API                        ││
│  │  • email-router      → SES                                       ││
│  │  • sms-router        → Gupshup / Kaleyra (DLT-registered)        ││
│  │  • ad-audience-router → Meta Custom Audience, Google Customer Match│
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Inbound Inbox (Phase v1b)                                        ││
│  │  • WhatsApp + Instagram DM + email + web chat unified            ││
│  │  • Autonomous resolution for top 10 ticket types                 ││
│  │  • Human escalation path                                          ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ Compliance Engine                                                ││
│  │  • DLT entity registration tracking                               ││
│  │  • NCPR + DND list checks                                        ││
│  │  • Calling-hour gating (09-21 IST)                               ││
│  │  • Frequency caps (per customer, per channel, per brand)         ││
│  │  • Consent re-verification before every send                     ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                        │
│  Data:                                                                 │
│   • Postgres: audience, audience_member, outreach, call, ticket,       │
│     message, rfm_score, consent_event                                  │
│   • ClickHouse: read-only on customer/order history (RFM input)        │
│   • Kafka: consumes analytics.customer_state.changed.v1                │
│              publishes lifecycle.outreach.completed.v1                 │
│                         lifecycle.recovered_revenue.attributed.v1      │
└───────────────────────────────────────────────────────────────────────┘
```

### Scaling

- **Outbound bursty:** concentrated in 09:00–21:00 IST calling window
- 3–15 pods Node (orchestration); 2–8 pods Python (RFM + LLM)
- Per-brand monthly cost cap (telephony + LLM combined) — soft warn at 70%, hard throttle at 100%

---

## 3. Scope (v1 Build Sequence)

**Sequence:** outbound first, then inbound. Outbound is where attributable revenue lives.

### v1a — Outbound (Phase 2 W14+)

| Use Case | Trigger | Channel Routing | Expected Lift |
|----------|---------|-----------------|---------------|
| **Abandoned cart recovery** | Cart abandoned > 30 min | Call (high-value), WhatsApp (mid), email (low) — RFM-driven | ~15-25% cart recovery |
| **COD confirmation** | Every COD order, within 15 min | Call → upsell to prepaid | ~3-5 pt CM2 lift per order |
| **Post-delivery follow-up** | 3-day + 7-day after delivery | WhatsApp → email fallback | NPS capture + review request |
| **Winback campaigns** | 60+ day dormant (per brand's median repurchase cycle) | RFM-routed | ~8% response within 14 days |
| **VIP retention** | Top decile LTV | Call or personalised WhatsApp | High-touch, low frequency |
| **Replenishment** | Modelled depletion (consumables) | WhatsApp → email fallback | Direct repeat-order lift |
| **WhatsApp marketing campaigns** | RFM-segmented broadcasts | WhatsApp (with conversational follow-up) | Per-segment performance tracked |

### v1b — Inbound (Phase 3 W23+)

| Capability | Detail |
|------------|--------|
| **Multi-channel inbox** | WhatsApp + Instagram DM + email + web chat unified |
| **Autonomous resolution** | Top 10 ticket types: order status, return initiation, address change, refund status, product info, COD-to-prepaid conversion, cancellation, replacement, missing item, delivery delay |
| **Human escalation** | Below confidence threshold or on customer request |
| **Decision Log feedback** | Every ticket logs back to customer profile; feeds RFM and segment memory |

---

## 4. RFM-Triggered Audience Builder

This is the architectural primitive that ties the Lifecycle Layer to the Memory Layer.

### 4.1 RFM Inside Memory

RFM is **not** a separate feature. It is a structured query against Customer Segment Memory ([TECH/05](05_intelligence_layer.md)).

Three scores computed per customer per day. Scored 1–5 against the brand's own customer base (never industry benchmarks):

- **Recency:** days since last order, bucketed against the brand's median repurchase cycle
- **Frequency:** order count in trailing 365 days
- **Monetary:** total **CM2 contribution** (not Gross Sales) in trailing 365 days

Each customer carries a 3-digit RFM score (e.g. `5-4-5` = recent, frequent, high-value = VIP).

### 4.2 The 11 Canonical Segments

Brain emits 11 canonical RFM segments by default. Brands can define custom segments using any RFM combination + additional filters.

| Segment | RFM Pattern | Default Routing |
|---------|-------------|-----------------|
| **Champions** | 5-5-5, 5-5-4 | VIP call / personalised WhatsApp |
| **Loyal** | 5-4-X, 4-4-X | WhatsApp |
| **Potential Loyal** | 5-3-X | WhatsApp + email |
| **New Customers** | 5-1-X | WhatsApp welcome series |
| **Promising** | 4-1-X | Email nurture |
| **Need Attention** | 3-3-X | WhatsApp re-engagement |
| **About to Sleep** | 3-2-X, 2-2-X | WhatsApp + email |
| **At Risk** | 2-4-X, 2-3-X | Call (high LTV) or WhatsApp |
| **Can't Lose Them** | 2-5-X, 1-5-X | Call mandatory |
| **Hibernating** | 1-2-X, 2-1-X | Email winback |
| **Lost** | 1-1-X | Email final-touch; do-not-call |

### 4.3 The One-Click Audience Flow

```
Brand operator on web app:
   1. Pick a segment OR build custom with filters
      (SKU, channel, geography, AOV band, last product, etc.)
   2. Brain returns:
      • Audience size
      • Modelled response rate (per channel, per brand history)
      • Modelled revenue recovery
      • Recommended channel mix
   3. ONE CLICK: trigger
      → simultaneously pushed to: call queue, WhatsApp queue,
        email queue, ad-platform custom audience sync
      → channel routing applied per customer (high-value → call;
        mid → WhatsApp; low → email)
```

### 4.4 Why This Is the Unlock

- **One primitive, N channels.** Engineering builds the audience object once.
- **Compounding learning.** Every outreach attempt logs back: which segment × which channel × which message produced what outcome at 7d + 30d. System gets better at making money from existing customers every month.
- **Aligned pricing defence.** Recovered revenue is attributable. GMV % fee is structurally defensible when Brain can point to specific recovered rupees per month.

### 4.5 Implementation: SQL → ML Path (Per Cost-Routing Principle)

Per [TECH/12](12_cost_routing_compute.md), RFM scoring is **SQL** (paradigm 1). Response-rate modelling is **ML** (paradigm 2). No LLM in the audience pipeline — LLM only enters at the **message personalisation** boundary (paradigm 3, Claude Haiku).

```sql
-- Daily RFM job: lifecycle-service runs this at 06:30 IST
INSERT INTO rfm_score (brand_id, customer_id, date, r_score, f_score, m_score, segment)
WITH customer_rfm AS (
  SELECT
    brand_id,
    customer_id,
    NTILE(5) OVER (PARTITION BY brand_id ORDER BY days_since_last_order DESC) AS r_score,
    NTILE(5) OVER (PARTITION BY brand_id ORDER BY order_count_365d ASC) AS f_score,
    NTILE(5) OVER (PARTITION BY brand_id ORDER BY cm2_contribution_365d ASC) AS m_score
  FROM customer_lifetime_value
  WHERE brand_id = $1 AND last_order_at IS NOT NULL
)
SELECT
  brand_id,
  customer_id,
  CURRENT_DATE AS date,
  r_score,
  f_score,
  m_score,
  classify_segment(r_score, f_score, m_score) AS segment
FROM customer_rfm
ON CONFLICT (brand_id, customer_id, date) DO UPDATE SET
  r_score = EXCLUDED.r_score,
  f_score = EXCLUDED.f_score,
  m_score = EXCLUDED.m_score,
  segment = EXCLUDED.segment;
```

---

## 5. AI Calling Architecture (Decision Point)

The architecture decision is **open** as of the brief. Three paths documented. Engineering team owns the selection.

### Path A — Partner with Indian Voice AI Vendor

**Candidates:** Bolna, Smallest.ai, smaller domestic players.

**Strengths:**
- Stronger Hindi, Hinglish, regional accents
- STD-trunking economics: ~₹0.30-0.60/min outbound
- Vendor handles TRAI DLT, DND, calling-hour compliance

**Weaknesses:**
- Vendor dependency
- Less control over voice quality + latency
- Harder to differentiate on call experience
- Per-minute economics squeezed at scale

**Time to market:** 4-6 weeks

### Path B — Partner with Global Voice AI Vendor

**Candidates:** Vapi, Retell, ElevenLabs Conversational, Bland.

**Strengths:**
- Best-in-class English voice quality + conversational latency
- Mature SDKs; faster iteration on call flows

**Weaknesses:**
- Higher per-minute cost (~$0.05-0.15/min)
- Telephony termination to India requires SIP trunk via Plivo / Exotel / Knowlarity
- More compliance plumbing for Indian regulations

**Time to market:** 4-6 weeks + SIP trunk integration

### Path C — Build Native

**Stack:**
- ASR: Deepgram or Whisper
- Conversation: GPT-4o-mini or Claude Haiku
- TTS: ElevenLabs or Cartesia
- SIP: Plivo or Exotel (India termination)

**Strengths:**
- Full control over voice, latency, prompts, fallback logic, pricing economics
- Long-term margin protection: calling becomes infrastructure Brain owns, not vendor passthrough

**Weaknesses:**
- 4-6 month build
- ML engineer / voice-agent engineer needed (gap on team today)
- Ongoing maintenance burden

**Strategic threshold:** justified if calling volume crosses ~10K calls/day across customer base (~50 brands at ~200 calls/day).

### Recommendation Heuristic (Not a Decision)

- **Months 1-6:** Partner (Path A or B) to validate unit economics, response rates, call flows on real brands
- **Months 6-12:** Parallel-build (Path C) if calling volume crosses ~5K calls/day and per-minute economics dominate cost line
- **Months 12+:** Migrate primary traffic to native stack; keep partner as overflow + hedge against regional language gaps

Same playbook as Brain uses for LLM layer: managed model until economics or differentiation force a move.

### Vendor Abstraction Pattern

Regardless of choice, the **call-router** in lifecycle-service hides vendor specifics behind a stable internal contract:

```python
# lifecycle-service/call_router.py
class CallProvider(ABC):
    @abstractmethod
    async def place_call(
        self, brand_id: UUID, customer_phone: str,
        script_template_id: str, context: dict
    ) -> CallTicket: ...

    @abstractmethod
    async def get_outcome(self, call_id: str) -> CallOutcome: ...

class BolnaProvider(CallProvider): ...
class VapiProvider(CallProvider): ...
class NativeStackProvider(CallProvider): ...
```

Swapping providers = config change, not code rewrite. Production can run multiple providers concurrently (e.g. Bolna for Hindi, Vapi for English) — call-router picks by language tag on the customer record.

---

## 6. Call Compliance Rules (India) — Non-Negotiable

Hard-coded into every calling path **regardless of build vs partner.** Engineering ships these as core infrastructure, not feature-flag-able policy.

| Rule | Implementation |
|------|----------------|
| **Calling hours: 09:00–21:00 IST** | Blocked at queue level, not dialer level. Pre-09:00 calls held in `pending_window` state; flushed at 09:00. Post-21:00 calls re-scheduled for next day. |
| **DND check** | Every number checked against (a) brand's own opt-out list AND (b) TRAI NCPR before dialing. Two-layer block. NCPR cache refreshed weekly. |
| **Consent** | Customer must have opted-in to transactional/marketing calls in brand's storefront. Consent state on customer record. Excluded if `consent_status IN ('opted_out', 'withdrawn')`. |
| **Disclosure** | Every AI call opens with clear disclosure that caller is automated. Rule applies regardless of whether regulation currently requires it. |
| **Recording consent** | Customer asked for recording consent at call start. If declined, call proceeds but no audio retained. |
| **DLT registration** | Every template message that follows a call (WhatsApp, SMS) registered on **brand's** DLT under their entity ID. Brain does not commingle brands' DLT registrations. |
| **Frequency cap** | No customer called more than once per 48 hours by any Brain-driven flow. Override only for VIP segments + only with Owner approval logged in audit log. |

### Compliance Engine

```python
# lifecycle-service/compliance.py
class CallComplianceEngine:
    def can_call(self, brand_id: UUID, customer_id: UUID, segment: str) -> ComplianceResult:
        customer = self.get_customer(brand_id, customer_id)
        now = datetime.now(IST_TIMEZONE)

        # 1. Calling hours
        if not (9 <= now.hour < 21):
            return ComplianceResult.deferred("outside_calling_hours")

        # 2. Consent
        if customer.consent_status in ('opted_out', 'withdrawn'):
            return ComplianceResult.blocked("consent_revoked")

        # 3. DND (brand + NCPR)
        if customer.do_not_call:
            return ComplianceResult.blocked("brand_dnd")
        if self.ncpr_cache.is_listed(customer.phone):
            return ComplianceResult.blocked("ncpr_listed")

        # 4. Frequency cap
        last_call = self.get_last_call(brand_id, customer_id)
        if last_call and (now - last_call.placed_at) < timedelta(hours=48):
            if segment != 'champions' or not customer.vip_override_approved:
                return ComplianceResult.blocked("frequency_cap")

        # 5. DLT entity check (verified during onboarding; cached)
        if not self.dlt_registered(brand_id):
            return ComplianceResult.blocked("dlt_not_registered")

        return ComplianceResult.ok()
```

---

## 7. Data Model

### New Tables

```sql
CREATE TABLE audience (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  filter_definition JSONB NOT NULL,          -- RFM segment + custom filters
  computed_size INT,
  projected_response_rate NUMERIC(5,4),
  projected_revenue_recovery_minor BIGINT,
  channel_mix JSONB,                          -- {'call': 0.2, 'whatsapp': 0.5, 'email': 0.3}
  built_by_user_id UUID,
  built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  triggered_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft'        -- draft / triggered / completed
);

CREATE TABLE audience_member (
  audience_id UUID NOT NULL REFERENCES audience(id) ON DELETE CASCADE,
  brand_id UUID NOT NULL,
  customer_id UUID NOT NULL,
  rfm_score_snapshot CHAR(5),                 -- '5-4-5' at trigger time, frozen
  assigned_channel TEXT NOT NULL,             -- 'call' / 'whatsapp' / 'email' / 'sms' / 'ad_audience'
  PRIMARY KEY (audience_id, customer_id)
);

CREATE TABLE outreach (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audience_id UUID REFERENCES audience(id),
  brand_id UUID NOT NULL,
  customer_id UUID NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,                       -- queued / in_flight / completed / failed / blocked
  blocked_reason TEXT,                        -- if status='blocked' (compliance)
  initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  outcome_label TEXT,                         -- 'converted' / 'no_pickup' / 'declined' / 'bounced' etc.
  recovered_revenue_minor BIGINT              -- attributed at 7d + 30d in Decision Log
);

CREATE TABLE call (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outreach_id UUID NOT NULL REFERENCES outreach(id) ON DELETE CASCADE,
  vendor TEXT NOT NULL,                       -- 'bolna' / 'vapi' / 'native'
  vendor_call_id TEXT,
  duration_seconds INT,
  transcript_id UUID,                         -- pointer to transcript blob in S3 (only if consented)
  recording_url TEXT,                         -- signed S3 URL, only if consented
  outcome_label TEXT,
  ended_at TIMESTAMPTZ
);

CREATE TABLE ticket (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL,
  customer_id UUID NOT NULL,
  channel TEXT NOT NULL,                      -- 'whatsapp' / 'instagram_dm' / 'email' / 'web_chat'
  status TEXT NOT NULL,                       -- 'open' / 'resolved_auto' / 'resolved_human' / 'escalated'
  assigned_agent TEXT,                        -- 'ai' / user_id
  resolution_label TEXT,                      -- one of top-10 categories
  resolution_confidence NUMERIC(4,3),
  opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE TABLE message (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id UUID REFERENCES ticket(id),
  outreach_id UUID REFERENCES outreach(id),
  brand_id UUID NOT NULL,
  role TEXT NOT NULL,                         -- 'customer' / 'ai_agent' / 'human_agent'
  channel TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE rfm_score (
  brand_id UUID NOT NULL,
  customer_id UUID NOT NULL,
  date DATE NOT NULL,
  r_score SMALLINT NOT NULL CHECK (r_score BETWEEN 1 AND 5),
  f_score SMALLINT NOT NULL CHECK (f_score BETWEEN 1 AND 5),
  m_score SMALLINT NOT NULL CHECK (m_score BETWEEN 1 AND 5),
  segment TEXT NOT NULL,
  PRIMARY KEY (brand_id, customer_id, date)
);

CREATE TABLE consent_event (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL,
  customer_id UUID NOT NULL,
  channel TEXT NOT NULL,                      -- 'call' / 'whatsapp' / 'email' / 'sms'
  old_status TEXT,
  new_status TEXT NOT NULL,
  source TEXT NOT NULL,                       -- 'storefront' / 'ticket' / 'call' / 'brand_bulk_update'
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Columns Added to Existing Tables

```sql
ALTER TABLE customer
  ADD COLUMN last_rfm_score CHAR(5),
  ADD COLUMN last_segment TEXT,
  ADD COLUMN last_outreach_at TIMESTAMPTZ,
  ADD COLUMN do_not_call BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN do_not_email BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN do_not_whatsapp BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE decision_log
  ADD COLUMN channel TEXT,                    -- 'call' / 'whatsapp' / 'email' / 'ad_audience' / 'no_action'
  ADD COLUMN recovered_revenue_7d_minor BIGINT,
  ADD COLUMN recovered_revenue_30d_minor BIGINT;
```

---

## 8. Pricing & Cost Discipline

### Bundled in GMV %

Per Owner decision in the brief: Lifecycle Layer is **included** in existing GMV % pricing. No per-call or per-resolution fee. No performance fee. Operator-grade simplicity > feature-itemised SaaS.

### Cost Pass-Through

Telephony pass-through (vendor per-minute charge OR native SIP termination) bundled into GMV % at Launch / Growth / Scale tiers, capped per brand (Enterprise = itemized). See `15_billing_metering.md`.

**Per-brand monthly call cost cap** (set at onboarding based on tier + expected volume):

- Below cap: Brain absorbs variable cost
- Above cap: calling continues but Brain talks to brand about tier upgrade or temporary call-volume reduction
- Cap exists to prevent abnormally high-volume brands from creating cost asymmetry vs other brands in same tier

**Enterprise tier:** telephony pass-through is a separate line item (enterprise call volumes 10-50x standard).

### Internal Margin Discipline

Three-layer enforcement (mirroring TECH/12 §4):

| Layer | Trigger | Action |
|-------|---------|--------|
| **Per-feature budget** | Single audience trigger > expected cost | Soft warn at 80% projected; hard fail at 100% |
| **Per-brand monthly cap** | Combined calling + messaging + LLM | Soft throttle at 70% (lower-priority outreach pauses); hard throttle at 100% (only critical-path: COD confirmation, ticket resolution) |
| **Audience quality bar** | If pickup-rate < 25% on last 100 calls in segment | Auto-pause that segment + alert owner |

Above caps, lifecycle features degrade gracefully. The system never breaks; it gets quieter.

---

## 9. Success Metrics

### Revenue-Aligned (North Stars)

| Metric | Target |
|--------|--------|
| **Recovered revenue per brand per month** | Total CM2 contribution attributable to Lifecycle outreach in trailing 30d |
| **Recovered revenue / Brain GMV fee** | > 3x by month 3; > 5x by month 6. Below 3x = brand is paying for cost centre, not revenue centre |
| **COD-to-prepaid conversion rate** | > 15% lift over brand baseline |
| **Winback response rate** | > 8% within 14 days of outreach |

### Operational

| Metric | Target |
|--------|--------|
| Call answer rate | > 35% (industry baseline ~25%) |
| Call-to-conversion rate (answered → intended outcome) | Tracked per call type |
| Ticket resolution rate (autonomous) | > 60% by month 6, > 75% by month 12 |
| First-response time (inbound) | < 60s WhatsApp, < 2 min email |

### Compliance

| Metric | Target |
|--------|--------|
| DND-blocked dial attempts | 0 (rule violation if non-zero) |
| Out-of-window dial attempts | 0 (rule violation if non-zero) |
| DLT-registered template % | 100% of WhatsApp + SMS sends |
| Recording-consent capture rate | Tracked; recording suppressed where declined |

---

## 10. Build Sequence (Phase Mapping)

| Phase | Capability |
|-------|-----------|
| **Phase 2 W14-16** | RFM scoring job + audience builder UI (web) + audience materialization |
| **Phase 2 W17-18** | WhatsApp router + first outbound campaign (abandoned cart) + Decision Log feedback |
| **Phase 2 W19-20** | Email router + COD confirmation (via partner Path A or B AI calling) |
| **Phase 2 W21-22** | Compliance engine (calling hours, DLT, DND, frequency) hardened; first call goes live |
| **Phase 3 W23-26** | Winback + VIP retention + replenishment + WhatsApp marketing campaigns |
| **Phase 3 W27-30** | Inbound multi-channel inbox + top-5 ticket-type autonomous resolution |
| **Phase 3 W31-34** | Remaining 5 ticket types + human escalation flow polish |
| **Phase 4** | AI calling native build decision point; ad-platform custom audience sync; referral engine |

---

## 11. Open Questions

| # | Question | Owner | Resolution |
|---|----------|-------|-----------|
| 1 | AI calling: Path A (India partner), Path B (global partner), or Path C (native build)? | E1 + E4 + Founder | Brief flags as decision point; default heuristic: Path A/B for months 1-6, parallel-build C if volume justifies |
| 2 | Which India calling vendor — Bolna vs Smallest.ai? | E4 | Pilot both on 2 brands in W17; pick on outcome + voice quality + economics |
| 3 | DLT entity sign-up workflow for new brands at onboarding | E1 + E5 (Mobile) + Founder | TBD — likely a self-serve onboarding step that triggers Gupshup DLT registration |
| 4 | Inbound: WhatsApp Cloud API vs Wati-style BSP fallback | E4 | Direct Cloud API. Wati only if Cloud API rate limits hurt at scale. |
| 5 | Ticket auto-resolution confidence threshold | E4 | Start at 0.85; tune per ticket type based on observed customer satisfaction after auto-resolve |
| 6 | Per-channel frequency caps — global default vs per-brand configurable? | E1 + Founder | Global default per brief; per-brand override at Enterprise tier |
| 7 | Recovered revenue attribution window — 7d vs 30d as canonical? | E4 + Founder | Both reported; 30d is the headline number for "GMV fee ratio" metric |
| 8 | Section 9.10+ from source brief (truncated) | E1 + Founder | TBD when full brief available |
