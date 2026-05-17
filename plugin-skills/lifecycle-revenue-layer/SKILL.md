---
name: lifecycle-revenue-layer
description: Brain's revenue engine — RFM scoring (SQL paradigm 1), 11 canonical RFM segments + custom filters, the audience builder (THE single primitive), channel routers (call / WhatsApp / email / SMS / ad audience), AI calling vendor abstraction (Bolna / Vapi / native), compliance engine (calling hours, DLT, NCPR, DND, 48h frequency cap), inbound multi-channel inbox (Phase 3), recovered-revenue attribution. Auto-load on any lifecycle-service work. Every feature is judged on rupees recovered, not tickets deflected.
---

# Lifecycle / Revenue Layer

Brain's revenue centre. Pricing model (GMV %) survives because Lifecycle layer recovered-revenue ratio > 3x by month 3, > 5x by month 6. Below 3x = cost centre = failure.

**Canonical doc:** `docs/TECH/11_lifecycle_revenue_layer.md`. This skill is operational.

## The Single-Primitive Rule (THE foundation — TECH/11 §1)

> Every cross-cutting concern is built **once** and consumed by every channel, every agent, every workflow.

Block at code review if you see:
- "The email version of the audience builder"
- "The call-specific consent flow"
- "The WhatsApp Decision Log"
- "A new notification service for SMS alerts"
- "Per-channel customer profiles"

Single primitives:
- **Audience builder** (owned: lifecycle-service)
- **Decision Log** (owned: analytics-service — `ai.decision_log`)
- **Consent model** (owned: core-service — `consent_event`)
- **Notification framework** (owned: notifications-service)
- **Attribution** (owned: analytics-service)
- **Identity resolution** (owned: core-service)

## RFM scoring — SQL paradigm 1 (TECH/11 §4.5)

```sql
-- Daily RFM job at 06:30 IST in lifecycle-service Python side
INSERT INTO rfm_score (workspace_id, customer_id, date, r_score, f_score, m_score, segment)
WITH customer_rfm AS (
  SELECT
    workspace_id,
    customer_id,
    NTILE(5) OVER (PARTITION BY workspace_id ORDER BY days_since_last_order DESC) AS r_score,
    NTILE(5) OVER (PARTITION BY workspace_id ORDER BY order_count_365d ASC)       AS f_score,
    NTILE(5) OVER (PARTITION BY workspace_id ORDER BY cm2_contribution_365d ASC)  AS m_score
  FROM customer_lifetime_value
  WHERE workspace_id = $1 AND last_order_at IS NOT NULL
)
SELECT
  workspace_id, customer_id, CURRENT_DATE,
  r_score, f_score, m_score,
  classify_segment(r_score, f_score, m_score) AS segment
FROM customer_rfm
ON CONFLICT (workspace_id, customer_id, date) DO UPDATE SET
  r_score = EXCLUDED.r_score, /* ... */;
```

Per-brand bucketing (NTILE 1–5) — never industry benchmarks. **Monetary = CM2 contribution, not Gross Sales** (TECH/11 §4.1).

## 11 canonical segments (TECH/11 §4.2)

| Segment | RFM | Default routing |
|---|---|---|
| Champions | 5-5-5, 5-5-4 | VIP call / personalised WhatsApp |
| Loyal | 5-4-X, 4-4-X | WhatsApp |
| Potential Loyal | 5-3-X | WhatsApp + email |
| New Customers | 5-1-X | WhatsApp welcome series |
| Promising | 4-1-X | Email nurture |
| Need Attention | 3-3-X | WhatsApp re-engagement |
| About to Sleep | 3-2-X, 2-2-X | WhatsApp + email |
| At Risk | 2-4-X, 2-3-X | Call (high LTV) or WhatsApp |
| Can't Lose Them | 2-5-X, 1-5-X | Call mandatory |
| Hibernating | 1-2-X, 2-1-X | Email winback |
| Lost | 1-1-X | Email final-touch; do-not-call |

## Audience builder — the one-click flow (TECH/11 §4.3)

```
Brand operator (web):
   1. Pick a segment OR build custom (RFM + filter: SKU, channel, geography, AOV band, last product)
   2. Brain returns:
      - Audience size
      - Modelled response rate (per channel, per brand history — paradigm 2 ML)
      - Modelled revenue recovery (paradigm 2)
      - Recommended channel mix
   3. ONE CLICK trigger:
      → simultaneously pushed to: call queue, WhatsApp queue, email queue, ad-platform custom audience
      → channel routing per customer (high-value → call; mid → WhatsApp; low → email)
```

Audience is **frozen at trigger time** — `audience_member.rfm_score_snapshot` captures the score at that moment.

## Compliance engine (TECH/11 §6 — NON-NEGOTIABLE)

```python
class CallComplianceEngine:
    def can_call(self, workspace_id, customer_id, segment) -> ComplianceResult:
        customer = self.get_customer(workspace_id, customer_id)
        now = datetime.now(IST_TIMEZONE)

        # 1. Calling hours 09:00–21:00 IST
        if not (9 <= now.hour < 21):
            return ComplianceResult.deferred("outside_calling_hours")

        # 2. Consent
        if customer.consent_status in ("opted_out", "withdrawn"):
            return ComplianceResult.blocked("consent_revoked")

        # 3. DND (brand opt-out + TRAI NCPR)
        if customer.do_not_call or self.ncpr_cache.is_listed(customer.phone):
            return ComplianceResult.blocked("brand_dnd" if customer.do_not_call else "ncpr_listed")

        # 4. Frequency cap (48h across all channels)
        last_contact = self.get_last_contact(workspace_id, customer_id)
        if last_contact and (now - last_contact.at) < timedelta(hours=48):
            if segment != "champions" or not customer.vip_override_approved:
                return ComplianceResult.blocked("frequency_cap")

        # 5. DLT registration
        if not self.dlt_registered(workspace_id):
            return ComplianceResult.blocked("dlt_not_registered")

        return ComplianceResult.ok()
```

Mirror `can_message(...)` for WhatsApp / SMS — DLT + opt-out + frequency apply.

**Out-of-window dial attempts = tier-1 incident. Hard zero target.**

## Vendor abstraction (TECH/11 §5)

```python
class CallProvider(ABC):
    @abstractmethod
    async def place_call(self, workspace_id, customer_phone, script_template_id, context) -> CallTicket: ...
    @abstractmethod
    async def get_outcome(self, call_id) -> CallOutcome: ...

class BolnaProvider(CallProvider): ...
class VapiProvider(CallProvider): ...
class NativeStackProvider(CallProvider): ...   # Deepgram + Haiku + ElevenLabs + Plivo
```

Swapping = config, not rewrite. Production can run multiple concurrently (Bolna for Hindi, Vapi for English) — pick by language tag on customer record.

**Migration heuristic:** Months 1–6 partner (A or B); months 6–12 parallel-build C if volume crosses ~5K calls/day; months 12+ migrate primary to C, keep partner as overflow + regional-language hedge.

## Data model (TECH/11 §7)

```
audience            -- the primitive (filter_definition JSONB)
audience_member     -- frozen snapshot at trigger; rfm_score_snapshot CHAR(5)
outreach            -- the unit of action; status + blocked_reason + outcome_label + recovered_revenue_*_minor
call                -- vendor-agnostic call record (transcript + recording per consent)
ticket              -- inbound: status + assigned_agent + resolution_label + resolution_confidence
message             -- ticket OR outreach scoped; role + channel + content
rfm_score           -- daily; PRIMARY KEY (workspace_id, customer_id, date)
consent_event       -- consent state transitions; immutable audit trail
mobile_push_tokens  -- shared with notifications-service
```

Plus columns on `customer`: `last_rfm_score`, `last_segment`, `last_outreach_at`, `do_not_call`, `do_not_email`, `do_not_whatsapp`.
Plus columns on `decision_log`: `channel`, `recovered_revenue_7d_minor`, `recovered_revenue_30d_minor`.

## Cost discipline (TECH/11 §8)

- **Bundled in GMV %** — no per-call or per-resolution fee
- **Per-brand monthly call cap** (set at onboarding by tier)
- **Soft throttle 70%** — lower-priority outreach pauses
- **Hard throttle 100%** — only critical-path (COD confirmation, ticket resolution)
- **Audience quality bar:** pickup < 25% on last 100 calls → auto-pause segment + alert Owner

System never breaks; it gets quieter.

## Success metrics (TECH/11 §9 — North Stars)

| Metric | Target |
|---|---|
| Recovered revenue / Brain GMV fee | > 3x by month 3; > 5x by month 6 |
| COD-to-prepaid conversion lift | > 15% over baseline |
| Winback response rate | > 8% within 14 days |
| Call answer rate | > 35% (industry baseline ~25%) |
| Ticket autonomous resolution | > 60% by month 6; > 75% by month 12 |
| First-response time (inbound) | < 60s WhatsApp; < 2 min email |
| DND-blocked dials | **0** — rule violation if non-zero |
| Out-of-window dials | **0** — rule violation if non-zero |

## Phase mapping (TECH/11 §10)

| Phase | Weeks | Capability |
|---|---|---|
| 2 | W14–16 | RFM scoring + audience builder UI + materialization |
| 2 | W17–18 | WhatsApp router + first outbound (abandoned cart) + Decision Log feedback |
| 2 | W19–20 | Email router + COD confirmation via AI calling |
| 2 | W21–22 | Compliance engine hardened; first call live |
| 3 | W23–26 | Winback + VIP retention + replenishment + WhatsApp marketing |
| 3 | W27–30 | Inbound inbox + top-5 ticket autonomous resolution |
| 3 | W31–34 | Remaining 5 ticket types + escalation polish |
| 4 | — | Native AI calling build decision; ad-platform sync; referral engine |

## Common failure modes

- **Per-channel fork** (Single-Primitive violation) — block at design.
- **Compliance toggle** — never feature-flag calling hours / DLT / DND / 48h cap.
- **Out-of-window dial** — tier-1 incident even on a single occurrence.
- **NCPR cache stale > 8 days** — false dial. Refresh weekly via Gupshup.
- **DLT entity mismatch** — Brain commingling two brands → vendor block. Per-brand entity strictly.
- **Frequency cap per-channel** — cap is 48h across ALL channels combined.
- **Forgetting outcome attribution** — outreach fires but `recovered_revenue_30d_minor` stays NULL → can't prove GMV-fee ratio.
- **RFM going LLM** — RFM is SQL paradigm 1. LLM in the RFM pipeline = cost-routing violation.

## References

- `docs/TECH/11_lifecycle_revenue_layer.md` — canonical
- `docs/TECH/12_cost_routing_compute.md` — RFM is SQL; response model is ML; personalisation is Haiku
- `docs/TECH/13_mcp_protocol.md` §lifecycle-tools — `lifecycle.audience.build` + `lifecycle.outreach.trigger` + `lifecycle.call.place` + `lifecycle.ticket.resolve`
- `docs/TECH/05_intelligence_layer.md` §Customer-Segment-Memory — Memory Layer feeding RFM
- `skills/india-commerce-economics/SKILL.md` — DLT + NCPR + DND + calling hours
- `skills/agentic-design/SKILL.md` §inter-agent — AICMO ↔ Lifecycle interaction
- `skills/mcp-protocol/SKILL.md` — lifecycle.* MCP tool definitions
