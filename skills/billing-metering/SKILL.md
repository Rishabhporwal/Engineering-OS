---
name: billing-metering
description: Realized-GMV pricing — fee=clamp(gmv_pct×billable_gmv, min_fee, cm2_cap×CM2). Monthly gmv_meter from CH facts, ~30d RTO re-truing, no per-seat, value-proof. SQL-only.
---

# Billing & Metering — Brain's Realized-GMV Pricing

Brain is priced as a **percentage of realized/delivered GMV** under management, with a per-tier **minimum monthly fee** and a **CM2 affordability guardrail** cap. **No per-seat pricing** — adding teammates never raises the bill. The whole engine lives in the `billing-metering` bounded context inside **core-service** (canon TECH/15, business §15, technical-requirements §17.2). Money is always **integer minor units + `currency_code`**, never float.

## Why this matters for Brain

| Principle | Why |
|---|---|
| **Bill on realized/delivered GMV, not placed** | In a 25–35% COD-RTO market, billing on placed GMV charges brands for revenue that physically came back. Billing on placed GMV is a **code-review blocker** (R5). Realized-GMV definition lives in [`india-commerce-economics`](../india-commerce-economics/SKILL.md) + [`metric-engine`](../metric-engine/SKILL.md). |
| **Minimum monthly fee per tier** | A cost-to-serve floor; the GMV % applies above it. |
| **CM2 affordability guardrail** | The fee is capped so it never consumes a disproportionate share of contribution margin. |
| **No per-seat** | Pricing aligns with commerce scale, not headcount. Per-seat is **out of scope** — reject it in design. |
| **Auditable to delivered orders** | Every billed rupee traces back to delivered facts in ClickHouse. |
| **Value-proof always visible** | Every paying brand sees recovered-revenue ÷ fee and CM2-recovered ÷ fee. |

## The metered base — `billable_gmv` (R5)

```
billable_gmv = placed_gmv − cancelled − RTO − refunds − failed_payments
```

Computed monthly in `billing.gmv_meter` from **ClickHouse delivered facts** (`orders FINAL`, `shipments FINAL`, `refunds`), in the workspace's **reporting currency** and **local-time calendar month**:

```
placed_gmv        = Σ net_revenue_minor of orders created in month   (tax-EXCLUSIVE, per §11 metric engine)
− cancelled       = orders cancelled before fulfilment
− rto             = shipment terminal state ∈ {rto, rto_delivered, lost}
− refunds         = refunded amount on delivered orders (full + partial)
− failed_payments = prepaid-attempted-but-failed captures
= billable_gmv
```

GMV is metered on **net revenue (tax-exclusive)** — Brain never charges a % on GST/VAT the brand merely collected for the government. (Per-SKU slab extraction is in the RegionAdapter — see [`india-commerce-economics`](../india-commerce-economics/SKILL.md).)

## The RTO lag problem — provisional then re-trued

RTO resolves up to **~30 days** after an order, so month M's `billable_gmv` is **provisional** at month close and **final** ~35 days later.

- **T+0 (month close):** issue a *provisional* invoice using a conservative RTO provision = the brand's trailing-90-day RTO rate applied to not-yet-resolved shipments.
- **T+35 (final true-up):** recompute `billable_gmv` with actual RTO outcomes; apply the **delta** as a credit/debit line on the **next** month's invoice. **Never re-issue a closed invoice — always reconcile forward.**

## The fee — clamp, never just multiply

```python
@paradigm("sql")  # billing is deterministic + auditable: SQL/CPU only — no ML, no LLM
def compute_monthly_fee(meter, plan) -> int:               # returns minor units
    raw     = int(plan.gmv_pct * meter.billable_gmv_minor)  # tier %-of-GMV
    floored = max(raw, plan.min_monthly_fee_minor)          # cost-to-serve floor
    cm2_cap = int(plan.cm2_cap_pct * meter.cm2_minor)       # affordability guardrail
    # Guardrail only CAPS; never raises the fee. If CM2 is tiny the cap may bind below the
    # floor — flag for a commercial conversation, never silently over-charge.
    return min(floored, cm2_cap) if cm2_cap > 0 else floored
```

The guardrail makes the fee the **lower of** (`gmv_pct × billable_gmv`) or (`cm2_cap_pct × CM2`), but never below the minimum without a flagged exception. When CM2 is still provisional (RTO lag), use trailing-90-day CM2 for the guardrail and re-true at T+35 with the GMV true-up.

## Tiers (indicative — commercial; architecture must support the boundaries)

| Tier | gmv_pct | min fee | cm2_cap_pct | passthrough |
|---|---|---|---|---|
| **Launch** | ~1.00% | floor per region/onboarding cost | ~15% | bundled |
| **Growth** | ~0.75% | higher floor | ~15% | bundled |
| **Scale** | ~0.50% | higher floor | ~12% | bundled |
| **Enterprise** | custom / fixed annual | negotiated | negotiated | **itemized** |

Exact numbers are commercial; the **code** must support floor + % + the CM2 cap + per-brand caps. Defaults seeded per region at onboarding.

## Activation period — no bill before the data is trustworthy

New brands get a time-boxed activation window aligned with the **Day 0–14 onboarding** sequence before the first GMV invoice, so cost setup + data quality reach the accuracy bar first (≥80% SKU-cost coverage etc. — CM2 is meaningless without it). `billing.plan.activation_until` gates invoice generation. The value-proof ledger still runs during activation — prove worth before the first bill.

## Pass-through metering — tracked, bundled below caps

```sql
billing.usage_passthrough(
  workspace_id, period_month,
  llm_cost_minor BIGINT,           -- from intelligence-service cost router (TECH/12)
  messaging_cost_minor BIGINT,     -- WhatsApp per-delivered-template + SMS per DLT template
  call_minutes_cost_minor BIGINT,  -- AI calling vendor / SIP termination
  email_cost_minor BIGINT,
  storage_overage_minor BIGINT,
  connector_premium_minor BIGINT,
  PRIMARY KEY (workspace_id, period_month)
)
```

- **Bundled tiers (Launch/Growth/Scale):** Brain absorbs pass-through **below the per-brand cap**; above cap → soft throttle then a tier-upgrade conversation. LLM caps enforced in the gateway ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md), [`llm-gateway`](../llm-gateway/SKILL.md)); telephony/messaging by the lifecycle cost layer.
- **Enterprise (itemized):** pass-through is a separate invoice line.
- Cost sources are the **same counters** the cost-discipline dashboard reads (TECH/12 §5), so billing and cost-control never disagree.

## `billing.*` schema (Postgres, owned by core-service)

```sql
billing.gmv_meter(
  workspace_id, period_month DATE,            -- first day of workspace-local month
  placed_gmv_minor BIGINT,
  cancelled_minor BIGINT, rto_minor BIGINT, refunds_minor BIGINT, failed_payment_minor BIGINT,
  billable_gmv_minor BIGINT,
  cm2_minor BIGINT,                            -- for the affordability guardrail
  status TEXT,                                 -- 'provisional' | 'final'
  rto_provision_rate NUMERIC(5,4),             -- used while provisional
  currency_code CHAR(3),
  computed_at TIMESTAMPTZ, finalized_at TIMESTAMPTZ,
  PRIMARY KEY (workspace_id, period_month)
);

billing.plan(
  workspace_id PK, tier TEXT,                  -- 'launch'|'growth'|'scale'|'enterprise'
  gmv_pct NUMERIC(6,5),                        -- 0.01000 = 1.0%
  min_monthly_fee_minor BIGINT,
  cm2_cap_pct NUMERIC(5,4),                    -- 0.15 = fee ≤ 15% of CM2
  llm_monthly_cap_minor BIGINT,                -- cost-routing per-brand cap (TECH/12 §4 Layer 3)
  passthrough_mode TEXT,                       -- 'bundled' | 'itemized'
  activation_until DATE,                       -- no GMV invoice before this date
  effective_from DATE, effective_to DATE
);

billing.invoices(
  id, workspace_id, period_month, status,      -- 'provisional'|'final'|'paid'|'failed'|'void'
  gmv_fee_minor BIGINT, passthrough_minor BIGINT, true_up_delta_minor BIGINT,
  total_minor BIGINT, currency_code,
  provider TEXT,                               -- 'razorpay' (INR) | 'stripe' (intl, Phase 4)
  provider_invoice_id TEXT, issued_at, due_at, paid_at, line_items JSONB
);
-- + billing.usage_passthrough (above)
```

Every workspace-scoped `billing.*` table carries `workspace_id` + RLS (4-layer tenancy — [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)). Money columns are **BIGINT minor units** — never NUMERIC/float for money.

## Invoicing & collection notes

- **Provider routing by currency:** INR via Razorpay; AED/SAR/USD via Stripe (Phase 4); each line item carries its metered-evidence reference. **Idempotency:** invoice generation keyed `(workspace_id, period_month, status)` — re-runs are no-ops ([`idempotency-handling`](../idempotency-handling/SKILL.md)).
- **Tax on Brain's own fee:** Brain charges output GST on its SaaS fee to Indian brands — separate from the brand's commerce GST, never in the GMV meter.
- **Dunning:** failed payment → retry → soft degradation (**analytics stay; outbound execution pauses**) → Owner escalation. Analytics are never cut off mid-cycle for billing reasons (trust).

## Value proof (always-on — non-negotiable)

Every workspace exposes a value-proof view (web Home + monthly report + mobile): Brain-attributed placed/realized revenue (Decision Log `attributed_revenue_minor` + 7d/30d realized attribution); recovered/protected CM2 (`attributed_cm2_minor` + lifecycle attribution); the Brain fee (`billing.invoices`); **recovered revenue ÷ fee** (target >3× by month 3, >5× by month 6); **CM2 recovered ÷ fee** (positive + expanding); operator time saved. Incremental numbers come from holdout measurement ([`experimentation-holdouts`](../experimentation-holdouts/SKILL.md)). Brain is sold as a profit centre, so the ledger that proves it is first-class.

## Cost-routing audit (this feature)

| Operation | Paradigm |
|---|---|
| Monthly GMV aggregation from ClickHouse | **1 — SQL** |
| RTO provision rate (trailing-90d) | **1 — SQL** |
| Fee computation + guardrail clamp | **1 — SQL/CPU** |
| Value-proof ledger | **1 — SQL** |

**No ML, no LLM anywhere in billing.** Billing must be deterministic and auditable.

## FinOps: per-workspace cost-to-serve

The `min_monthly_fee` floor is a *blunt* cost-to-serve guard. The sharper check — the engineering defence of **%-of-GMV pricing at the brand level** — is attributing **infra cost per workspace** and comparing it to that workspace's **realized-GMV fee**. `cost-routing-paradigms` governs LLM cost; this adds the **infra** side.

**Cost-to-serve inputs (all already metered per `workspace_id`):**

| Driver | Source counter |
|---|---|
| ClickHouse query **bytes scanned** | `ClickHouseQueryDuration`/bytes by workspace (observability) |
| Kafka **throughput** (events × partition = `workspace_id`) | MSK per-key metrics |
| EKS **compute** | pod CPU/mem × workspace request share (agent-tick attribution) |
| **LLM tokens** | `billing.usage_passthrough.llm_cost_minor` (cost router) |
| Messaging / call minutes | `usage_passthrough.{messaging,call_minutes}_cost_minor` |

```
cost_to_serve(ws, month) = ch_bytes_cost + kafka_cost + eks_compute_share + llm_cost + messaging_cost
gross_margin(ws)         = realized_gmv_fee(ws) − cost_to_serve(ws)
```

**Margin alert:** when `cost_to_serve / realized_gmv_fee` crosses a threshold (e.g. >40%), the workspace is a unit-economics risk — flag for a tier/cap conversation **before** it goes negative. This is reporting/FinOps, not the fee path — the fee stays **SQL-only and deterministic** (above).

## Anti-patterns (reject in review)

- **Billing on placed GMV** — code-review **blocker**. The base is realized/delivered GMV, re-trued for RTO lag.
- **Per-seat pricing** — **out of scope**.
- **Float/NUMERIC for money** — money is integer minor units + `currency_code`.
- **Charging a % on GST/VAT** — the meter is on net (tax-exclusive) revenue.
- **Re-issuing a closed invoice** for the RTO true-up — always reconcile forward as a next-month delta line.
- **A fee that exceeds `cm2_cap_pct × CM2`** silently — the guardrail caps it; if it binds below the floor, flag a commercial exception.
- **Billing during the activation window** — `activation_until` gates the first GMV invoice.
- **Any ML/LLM in the fee path** — billing is SQL-only and deterministic.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| `billing.*` schema + GMV meter + fee computation | **Vikram** (core-service) | canon/TECH/15 + technical-requirements §17.2 |
| ClickHouse delivered-facts aggregation | **Maya** (analytics-service) | `clickhouse-olap`, `metric-engine` |
| CM2 input for the guardrail | **Maya** | `metric-engine` (CM2 = CM1 − marketing) |
| Pass-through counters | **Maya** + **Jatin** | TECH/12 cost router; lifecycle cost layer |
| Invoice provider integration (Razorpay/Stripe) | **Vikram** | `idempotency-handling` |
| Value-proof view (web + mobile) | **Ananya** + **Karan** | `frontend-web`, `frontend-mobile`, `kpi-dashboard-design` |
| Commercial terms (tiers, floors, caps) | **Founder** | business §15.2 |

## References

- `canon/TECH/15_billing_metering.md` — the full billing spec (pipeline, re-truing, schema, invoicing)
- `canon/business-requirements.md` §15 — pricing principle, packaging, pass-through + caps
- `canon/technical-requirements.md` §17.2 + §9.8 — billing/metering resolution + `billing.*` DDL
- [`metric-engine`](../metric-engine/SKILL.md) — realized/delivered revenue + CM2 (the billing base)
- [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) — the per-brand LLM cap feeding pass-through
- [`idempotency-handling`](../idempotency-handling/SKILL.md) — invoice-generation idempotency
</content>
