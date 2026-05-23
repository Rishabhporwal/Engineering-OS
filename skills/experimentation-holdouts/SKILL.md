---
name: experimentation-holdouts
description: Brain's measurement discipline that makes the value claim PROVABLE — the recovered-revenue ÷ Brain-fee proof must come from holdout-measured incrementality, never placed revenue. Deterministic holdout assignment (stable hashing on customer_id, workspace_id-scoped, per-segment, durable), incrementality measurement (campaign cohort vs holdout — canon's "campaign incrementality vs holdout"; lifecycle is always CM2-gated vs holdout/baseline), A/B sizing & power (MDE, sample size, duration), guardrail metrics (don't win the test but lose CM2 / spike unsubscribes), and the placed→realized→incremental attribution ladder. All lift math is the SQL/ML paradigm (@paradigm) — an LLM NEVER computes lift. Every experiment + outcome writes to the Decision Log. Owner Maya (analytics) + Priya (PM). Use when designing an A/B test, a holdout, or proving Brain's recovered-revenue claim.
---

# Experimentation & Holdouts — making Brain's value provable

Brain prices as **% of realized GMV** and defends that fee with one number: **recovered revenue ÷ Brain fee** (canon target > 3× by month 3, > 5× by month 6). That ratio is only honest if the numerator is **incremental** — revenue Brain *caused*, not revenue that would have happened anyway. Placed revenue, or "attributed" revenue with no counterfactual, inflates the claim and breaks trust the first time a Founder checks. **The holdout is the counterfactual; this skill is how you build and measure it.**

> **The one rule:** the value proof comes from **holdout-measured incrementality**, never placed revenue. Canon §11.5 mandates three attribution views — *placed* (clicked/replied + ordered in window), *realized* (delivered/paid/settled), and **incremental** (campaign cohort vs holdout or baseline) — and the fee-coverage headline rides on the incremental one.

**Canonical doc:** `canon/business-requirements.md` §6 (metrics), §11.5 (lifecycle attribution) + `canon/TECH/11_lifecycle_revenue_layer.md`. Owner: **Maya** (analytics) + **Priya** (PM — experiment intent, success criteria, sign-off).

## Deterministic holdout assignment

Assignment must be **stable, deterministic, and `workspace_id`-scoped** — the same customer lands in the same arm across days, jobs, and replays. Hash; never roll a random number per send (that re-randomises on retry and contaminates the holdout).

```python
@paradigm("sql")  # assignment is deterministic computation — never an LLM, never ML
def assign_arm(workspace_id: str, experiment_id: str, customer_id: str, holdout_pct: int) -> str:
    # stable hash → [0,100); brand-scoped so brands don't share an arm; salted per experiment
    bucket = cityhash64(f"{workspace_id}:{experiment_id}:{customer_id}") % 100
    return "holdout" if bucket < holdout_pct else "treatment"
```

Rules: salt by `workspace_id` **and** `experiment_id` (a customer can be treatment in one experiment, holdout in another, independently); assign at the **segment** the experiment targets (a winback holdout is within the winback-eligible segment, not the whole base); the holdout is **durable for the experiment's window** (a held-out customer is not "rescued" mid-test by another campaign — that's contamination); record the arm so attribution and the Decision Log can read it. Multi-tenant isolation is law — see [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md).

## Incrementality measurement (cohort vs holdout)

Incremental lift = **treatment cohort outcome − holdout cohort outcome**, measured on **realized** revenue and CM2 (not placed), over the same window:

```
incremental_revenue_minor = realized(treatment) − realized(holdout)        -- per customer, then summed
incremental_cm2_minor      = cm2(treatment)      − cm2(holdout)            -- the number that actually matters
recovered_revenue_ratio    = incremental_revenue_minor / brain_fee_minor    -- the value-proof headline
```

All of this is the **SQL/ML paradigm** ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)) — a SQL diff of two cohorts, with statistical-significance tests in `pylibs` (paradigm 2). **An LLM never computes lift, a confidence interval, or a recovered-revenue number** — that would be metric hallucination, banned by the Iron Rule. The synthesis Sonnet may *narrate* "this winback flow recovered ₹X incremental CM2," but the ₹X comes from the metric registry, computed against the holdout — see [`metric-engine`](../metric-engine/SKILL.md) (define the metric once, TS↔Python parity). Where a per-customer holdout isn't feasible, fall back to **baseline** (pre/post or matched-period) and label the number as baseline-derived, not holdout-derived; geo-holdout iROAS is a Phase-4 capability (needs spend volume per geography).

Lifecycle is **always CM2-gated vs holdout/baseline**: an offer ships only when expected CM2 stays positive *after* message/offer/RTO cost, and "it worked" means it beat the holdout on CM2 — not that revenue rose ([`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md)).

## A/B sizing & power (don't ship an underpowered test)

Before launch, Priya + Maya fix the design so the test can actually detect the effect:

- **MDE (minimum detectable effect)** — the smallest lift worth acting on (e.g. +2pp COD-confirm rate, or +₹X CM2/customer). Below the MDE, "no result" is expected, not a failure.
- **Sample size** — from baseline rate/variance, the MDE, α (0.05), and power (0.80). A holdout too small to power the MDE is **wasted suppressed revenue** — you sacrificed sends and learned nothing.
- **Duration** — long enough to cover the realized window (delivery/RTO/refund leakage lands days later — measuring on placed-day data overstates lift) and at least a full weekly cycle; cap it so a winning treatment isn't suppressed from the holdout longer than necessary.
- **One change per arm** — confounded arms aren't attributable. Stop rules + sequential-testing guards prevent peeking-to-significance.

Power math is paradigm 2 (`statsmodels`/`scipy` in `pylibs`), not an LLM.

## Guardrail metrics (win the test, don't lose the business)

Every experiment declares **guardrails** that fail it even if the primary metric wins — so Brain never optimises a local metric while damaging the brand:

| Guardrail | Why |
|---|---|
| **CM2 (true, RTO-adjusted)** | a discount can lift orders while turning CM2 negative — a "win" that loses money |
| **Unsubscribe / opt-out rate** | over-messaging wins this week and burns the channel; opt-out overrides all marketing |
| **DND / compliance violations = 0** | a non-negotiable guardrail, not a tradeable metric ([`security-baseline`](../security-baseline/SKILL.md)) |
| **RTO rate** | a COD-push test that lifts orders but spikes RTO can be net-negative on CM2 |
| **Frequency-cap breaches** | the 48h cap must hold inside the test |

A test that wins the primary metric but trips a guardrail **does not ship**.

## Every experiment writes to the Decision Log

An experiment is a Brain decision, so it lives in `ai.decision_log` like any other ([`decision-log`](../decision-log/SKILL.md)): a row at design (hypothesis, MDE, arms, holdout %, guardrails, success criteria — Priya signs off), updated at launch, and updated at readout with `outcome_7d`/`outcome_30d`, `attributed_*_minor`, and `recovered_revenue_*_minor` populated **from the holdout-measured incremental numbers**, plus a `learning_note`. The nightly 23:55 IST attribution job reads realized facts from ClickHouse and backfills the same rows — and because the holdout arm is recorded, it computes *incremental*, not placed, attribution. Money is integer minor units throughout (never float/NUMERIC). This is also what makes a result a reusable Condition-Outcome pair in the Brand Fingerprint ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md)) — the brand's experiments compound into the moat. The fee-coverage view itself lives in billing ([`billing-metering`](../billing-metering/SKILL.md), value-proof ledger).

## Anti-patterns (code-review / analytics blockers)

- **Claiming recovered revenue from placed (or holdout-less) numbers** → the value proof is fiction; blocker.
- **Random per-send arm assignment** → re-randomises on retry, contaminates the holdout. Use the stable hash.
- **An LLM computing lift / CI / recovered revenue** → metric hallucination; lift math is SQL/ML only.
- **Rescuing held-out customers mid-test** with another campaign → contamination; the holdout is durable.
- **Underpowered holdout** (too small for the MDE) → suppressed revenue with no learning.
- **Measuring lift on placed-day data** → overstates incrementality; measure over the realized window.
- **No guardrails** → optimises a metric while burning CM2 / unsubscribes / compliance.
- **Holdout/arm not `workspace_id`-scoped** → cross-brand contamination (P0).

## References

- `canon/business-requirements.md` §6 (metrics ladder, Recovered Revenue ÷ Brain Fee) · §11.5 (placed / realized / incremental attribution)
- `canon/TECH/11_lifecycle_revenue_layer.md` — recovered-revenue attribution, CM2-gating, 7d/30d windows
- [`metric-engine`](../metric-engine/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`billing-metering`](../billing-metering/SKILL.md) · [`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md) · [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)
