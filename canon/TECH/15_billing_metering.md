# TECH/15 — Billing & Metering (realized-GMV pricing)

> **Status:** New deep-dive (created with consolidated v2.0).
> **Owner:** core-service (`billing-metering` context) + Founder (commercial terms).
> **Companion:** `../technical-requirements.md` §17.2, `../business-requirements.md` §15, `12_cost_routing_compute.md`, `01_data_architecture.md`.
> **Why this exists:** Brain is priced as **% of realized/delivered GMV** with a minimum monthly fee and a CM2 affordability guardrail (business doc v1.1). No prior TECH file covered how GMV is metered, re-trued for RTO lag, fee-computed, capped, or invoiced. This is that spec.

---

## 1. Principles

1. **Bill on realized/delivered GMV**, never placed GMV. In a 25–35% COD-RTO market, billing on placed GMV would charge brands for revenue that physically returned. (Resolution R5.)
2. **Minimum monthly fee** per tier — a cost-to-serve floor; the GMV % applies above it.
3. **CM2 affordability guardrail** — the fee is capped so it never consumes a disproportionate share of contribution margin.
4. **No per-seat pricing** — adding teammates never raises the bill.
5. **Pass-through tracked, bundled below caps** — LLM, messaging, call minutes, email, storage are metered; bundled into the fee under per-brand caps; itemized for Enterprise.
6. **Metering is auditable** — every billed rupee traces to delivered orders in ClickHouse. Same truth discipline as the metric engine.
7. **Value-proof, always visible** — every paying brand sees recovered-revenue ÷ fee and CM2-recovered ÷ fee.

---

## 2. The GMV metering pipeline

```
ClickHouse delivered facts (orders FINAL, shipments FINAL, refunds)
        │  monthly aggregation, workspace-local calendar month
        ▼
billable_gmv = placed_gmv − cancelled − rto − refunds − failed_payments
        │  (RTO resolves up to ~30 days late → provisional then re-trued)
        ▼
billing.gmv_meter  (provisional at month close T+0; final at T+35)
        │
        ▼
fee = clamp( gmv_pct × billable_gmv ,  min_monthly_fee ,  cm2_cap_pct × CM2 )
        │
        ▼
billing.invoices  → payment provider (Razorpay/Stripe) → collection
```

### 2.1 Metered base

`billable_gmv_minor` is computed in the workspace's **reporting currency** and **local-time calendar month**:

```
placed_gmv          = Σ net_revenue_minor of orders created in month        (tax-exclusive, per §11 metric engine)
− cancelled         = orders cancelled before fulfilment
− rto               = orders whose shipment terminal state ∈ {rto, rto_delivered, lost}
− refunds           = refunded amount on delivered orders (full + partial)
− failed_payments   = prepaid-attempted-but-failed captures
= billable_gmv
```

GMV is metered on **net revenue (tax-exclusive)** so Brain never charges a % on GST/VAT the brand merely collected for the government. This is intentional and brand-favourable.

### 2.2 The RTO lag problem and re-truing

RTO resolves up to ~30 days after order. So month M's `billable_gmv` is **provisional** at month close and **final** ~35 days later.

- **T+0 (month close):** issue a *provisional* invoice using a conservative RTO provision (the brand's trailing-90-day RTO rate applied to not-yet-resolved shipments).
- **T+35 (final true-up):** recompute `billable_gmv` with actual RTO outcomes; the **delta** is applied as a credit/debit line on the *next* month's invoice. Never re-issue a closed invoice; always reconcile forward.

```sql
-- billing.gmv_meter (Postgres; computed by core-service from ClickHouse)
billing.gmv_meter(
  workspace_id, period_month DATE,            -- first day of workspace-local month
  placed_gmv_minor BIGINT,
  cancelled_minor BIGINT, rto_minor BIGINT, refunds_minor BIGINT, failed_payment_minor BIGINT,
  billable_gmv_minor BIGINT,
  cm2_minor BIGINT,                            -- for the affordability guardrail
  status TEXT,                                 -- 'provisional' | 'final'
  rto_provision_rate NUMERIC(5,4),            -- used when provisional
  currency_code CHAR(3),
  computed_at TIMESTAMPTZ, finalized_at TIMESTAMPTZ,
  PRIMARY KEY (workspace_id, period_month)
)
```

### 2.3 Fee computation

```python
def compute_monthly_fee(meter, plan) -> int:
    raw = int(plan.gmv_pct * meter.billable_gmv_minor)        # tier %-of-GMV
    floored = max(raw, plan.min_monthly_fee_minor)             # cost-to-serve floor
    cm2_cap = int(plan.cm2_cap_pct * meter.cm2_minor)          # affordability guardrail
    # Guardrail only caps; it never raises the fee. If CM2 is tiny, the cap can bind below the floor —
    # in that case the brand is flagged for a commercial conversation, not silently over-charged.
    return min(floored, cm2_cap) if cm2_cap > 0 else floored
```

The guardrail makes the fee the **lower** of (`%-GMV` or `cm2_cap_pct × CM2`), but never below the minimum without a flagged exception. A brand should never feel Brain's fee is why it became unprofitable.

### 2.4 Plan table

```sql
billing.plan(
  workspace_id PK,
  tier TEXT,                       -- 'launch' | 'growth' | 'scale' | 'enterprise'
  gmv_pct NUMERIC(6,5),            -- 0.01000 = 1.0%
  min_monthly_fee_minor BIGINT,
  cm2_cap_pct NUMERIC(5,4),        -- e.g. 0.15 = fee ≤ 15% of CM2
  llm_monthly_cap_minor BIGINT,    -- cost-routing per-brand cap (TECH/12 §4 Layer 3)
  passthrough_mode TEXT,           -- 'bundled' (Launch/Growth/Scale) | 'itemized' (Enterprise)
  activation_until DATE,           -- no GMV invoice before this date
  effective_from DATE, effective_to DATE
)
```

Indicative tiers (commercial; tune with telemetry — business doc §15.2):

| Tier | gmv_pct | min fee | cm2_cap_pct | passthrough |
|---|---|---|---|---|
| Launch | ~1.00% | floor set per region/onboarding cost | ~15% | bundled |
| Growth | ~0.75% | higher floor | ~15% | bundled |
| Scale | ~0.50% | higher floor | ~12% | bundled |
| Enterprise | custom / fixed annual | negotiated | negotiated | itemized |

> Exact numbers are commercial decisions; the **architecture** must support floor + %, the CM2 cap, and per-brand caps. Defaults seeded per region at onboarding.

---

## 3. Pass-through metering

```sql
billing.usage_passthrough(
  workspace_id, period_month,
  llm_cost_minor BIGINT,           -- from intelligence-service cost router (TECH/12)
  messaging_cost_minor BIGINT,     -- WhatsApp per-message + SMS per-template
  call_minutes_cost_minor BIGINT,  -- AI calling vendor / SIP termination
  email_cost_minor BIGINT,
  storage_overage_minor BIGINT,
  connector_premium_minor BIGINT,
  PRIMARY KEY (workspace_id, period_month)
)
```

- **Bundled tiers:** Brain absorbs pass-through below the per-brand cap; above cap → soft throttle (lower-priority outreach/LLM pause) then a tier-upgrade conversation. Caps enforced by `pylibs/brain_cost_router` (LLM) and `lifecycle-service` compliance/cost layer (telephony/messaging).
- **Enterprise (itemized):** pass-through is a separate invoice line (call volumes 10–50× standard).

Cost sources are the same counters the cost-discipline dashboard reads (TECH/12 §5), so billing and cost-control never disagree.

---

## 4. Value proof (always-on)

Every workspace exposes a value-proof view (web Home + monthly report + mobile):

| Metric | Source |
|---|---|
| Brain-attributed placed revenue | Decision Log `attributed_revenue_minor` |
| Brain-attributed realized revenue | Decision Log 7d/30d realized attribution |
| Recovered / protected CM2 | Decision Log `attributed_cm2_minor` + lifecycle attribution |
| Brain fee (this month) | `billing.invoices` |
| **Recovered revenue ÷ fee** | target >3× by month 3, >5× by month 6 |
| **CM2 recovered ÷ fee** | positive + expanding |
| Operator time saved | actions automated + queues compressed |

This is non-negotiable: Brain is sold as a revenue/profit centre, so the ledger that proves it is a first-class surface.

---

## 5. Invoicing & collection

```sql
billing.invoices(
  id, workspace_id, period_month, status,       -- 'provisional'|'final'|'paid'|'failed'|'void'
  gmv_fee_minor BIGINT, passthrough_minor BIGINT, true_up_delta_minor BIGINT,
  total_minor BIGINT, currency_code,
  provider TEXT,                                  -- 'razorpay' (INR) | 'stripe' (intl)
  provider_invoice_id TEXT, issued_at, due_at, paid_at,
  line_items JSONB
)
```

- **Provider routing by currency:** INR via Razorpay; AED/SAR/USD via Stripe (Phase 4). Each line item carries the metered evidence reference.
- **Idempotency:** invoice generation is keyed `(workspace_id, period_month, status)`; re-runs are no-ops. (See `idempotency-handling`.)
- **Tax on Brain's own fee:** Brain charges GST on its SaaS fee to Indian brands (output GST on the platform fee) — separate from the brand's commerce GST. Handled in the invoice, not the GMV meter.
- **Multi-currency:** invoice in the workspace reporting currency; FX snapshot stored.
- **Dunning:** failed payment → retry schedule → soft feature degradation (analytics stay; outbound execution pauses) → Owner escalation. Analytics are never cut off for billing reasons mid-cycle (trust).

---

## 6. Activation period

New brands get a time-boxed activation window (aligned with Day 0–14 onboarding) before the first GMV invoice, so cost setup + data quality reach the accuracy bar first. `billing.plan.activation_until` gates invoice generation. During activation, the value-proof ledger still runs (to demonstrate worth before the first bill).

---

## 7. Cost-routing audit (this feature)

| Operation | Paradigm |
|---|---|
| Monthly GMV aggregation from ClickHouse | **1 — SQL** |
| RTO provision rate (trailing-90d) | **1 — SQL** |
| Fee computation + guardrail clamp | **1 — SQL/CPU** |
| Value-proof ledger | **1 — SQL** |

No ML, no LLM in billing. Billing must be deterministic and auditable.

---

## 8. Open questions

| # | Question | Resolution path |
|---|---|---|
| 1 | Exact min-fee floors per region/tier | Commercial; set from onboarding cost-to-serve telemetry after Phase 1 |
| 2 | CM2 cap when CM2 is provisional (RTO lag) | Use trailing-90d CM2 for the guardrail; re-true at T+35 with the GMV true-up |
| 3 | Provisional-vs-final billing cadence | Provisional at month close; final true-up as a next-month line at T+35 |
| 4 | Brand-visible cost-discipline dashboard? | Internal by default; Enterprise gets visibility (TECH/12 §8) |
| 5 | Annual prepay discounts | Phase 4 commercial; architecture supports via `billing.plan` effective windows |
