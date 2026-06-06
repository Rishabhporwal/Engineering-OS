---
name: experimentation-holdouts
description: A/B testing, holdouts, and incrementality — deterministic holdout assignment, cohort lift vs a counterfactual, A/B power/MDE, guardrail metrics, and writing every experiment to the audit log.
---

# Experimentation & Holdouts — measuring what an action actually caused

When the product makes an *intervention* (a campaign, a recommendation, an automated action) and claims it produced an outcome, that claim is only honest if the outcome is **incremental** — the effect the intervention *caused*, not what would have happened anyway. Attributed-without-a-counterfactual numbers inflate the claim and break trust the first time a stakeholder checks. **The holdout is the counterfactual; this skill is how you build and measure it.**

> **The one rule:** an effect claim comes from **holdout-measured incrementality** (or a labelled baseline), never from raw "attributed" volume. Keep the views distinct: *exposed/attributed* vs **incremental** (treatment cohort vs holdout/baseline) — and the headline claim rides on the incremental one.

**Canonical doc:** the Product Canon's `METRICS.md` (the metrics under test) + `engineering-os-blueprint/06-quality-gates-and-metrics.md`. Owner: **AI/ML Engineer** (analysis) + **Delivery Coordinator** (experiment intent, success criteria, sign-off).

## Deterministic holdout assignment

Assignment must be **stable, deterministic, and tenant-scoped** — the same subject lands in the same arm across days, jobs, and replays. Hash; never roll a random number per event (that re-randomises on retry and contaminates the holdout).

```python
# assignment is deterministic computation — never an LLM, never ML
def assign_arm(tenant_id: str, experiment_id: str, subject_id: str, holdout_pct: int) -> str:
    bucket = cityhash64(f"{tenant_id}:{experiment_id}:{subject_id}") % 100   # tenant-scoped, salted per experiment
    return "holdout" if bucket < holdout_pct else "treatment"
```

Rules: salt by tenant **and** `experiment_id` (a subject can be treatment in one experiment, holdout in another, independently); assign at the **segment** the experiment targets (a holdout is within the eligible segment, not the whole base); the holdout is **durable for the experiment's window** (a held-out subject is not "rescued" mid-test by another intervention — that's contamination); record the arm so analysis and the audit log can read it. Tenant isolation is law — see [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md).

## Incrementality measurement (cohort vs holdout)

Incremental lift = **treatment cohort outcome − holdout cohort outcome**, on the *realized/settled* metric (not the placed/exposed one), over the same window:

```
incremental_value_minor = realized(treatment) − realized(holdout)   -- per subject, then summed (money in minor units)
lift_pct                = (rate(treatment) − rate(holdout)) / rate(holdout)
```

All of this is **deterministic / statistical computation** ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)) — a query diff of two cohorts, with significance tests in a stats library. **A model never computes lift, a confidence interval, or an effect number** — that would be metric fabrication, banned by the Iron Rule. A narration step may *describe* "this flow produced X incremental units," but X comes from the metric registry, computed against the holdout ([`metric-engine`](../metric-engine/SKILL.md)). Where a per-subject holdout isn't feasible, fall back to a **baseline** (pre/post or matched-period) and label the number baseline-derived; a geo-holdout design is a later-phase capability.

An intervention with a cost ships only when its expected net effect stays positive *after* its cost, and "it worked" means it **beat the holdout on the target metric** — not merely that the metric rose.

## A/B sizing & power (don't ship an underpowered test)

Before launch, the Delivery Coordinator + AI/ML Engineer fix the design so the test can detect the effect:

- **MDE (minimum detectable effect)** — the smallest lift worth acting on (e.g. +2pp on the target rate, or +X per subject). Below the MDE, "no result" is expected, not failure.
- **Sample size** — from the baseline rate/variance, the MDE, α (0.05), and power (0.80). A holdout too small to power the MDE is **wasted suppressed effect**.
- **Duration** — long enough to cover the realized window (settlement/refund/reversal effects land days later — measuring on exposure-day data overstates lift) and at least a full weekly cycle; cap it so a winning treatment isn't suppressed longer than necessary.
- **One change per arm** — confounded arms aren't attributable. Stop rules + sequential-testing guards prevent peeking-to-significance.

Power math is a statistical computation (`statsmodels`/`scipy`), not an LLM.

## Guardrail metrics (win the test, don't lose the business)

Every experiment declares **guardrails** that fail it even if the primary metric wins:

| Guardrail | Why |
|---|---|
| **A net/margin metric** | a treatment can lift volume while turning the net metric negative — a "win" that loses money |
| **Opt-out / unsubscribe rate** | over-intervening wins this week and burns the channel; opt-out overrides the primary metric |
| **Compliance violations = 0** | a non-negotiable guardrail, not a tradeable metric ([`security-baseline`](../security-baseline/SKILL.md)) |
| **A downstream quality metric** (e.g. returns/reversals) | a push that lifts the headline but spikes a downstream cost can be net-negative |
| **Frequency-cap breaches** | the cap must hold inside the test |

A test that wins the primary metric but trips a guardrail **does not ship**.

## Every experiment writes to the audit log

An experiment is a product decision, so it lives in the system-of-record audit log like any other ([`decision-log`](../decision-log/SKILL.md)): a row at design (hypothesis, MDE, arms, holdout %, guardrails, success criteria — the Delivery Coordinator signs off), updated at launch, and updated at readout with the outcome windows and the **holdout-measured incremental numbers**, plus a `learning_note`. A scheduled attribution job reads realized facts and backfills the same rows — and because the holdout arm is recorded, it computes *incremental*, not exposed, attribution. Money is integer minor units throughout. This is also what makes a result a reusable condition→outcome pair for the OS's memory.

## Anti-patterns (code-review / analysis blockers)

- **Claiming an effect from exposed (or holdout-less) numbers** → the claim is fiction; blocker.
- **Random per-event arm assignment** → re-randomises on retry, contaminates the holdout. Use the stable hash.
- **A model computing lift / CI / an effect number** → metric fabrication; lift math is deterministic/statistical only.
- **Rescuing held-out subjects mid-test** with another intervention → contamination; the holdout is durable.
- **Underpowered holdout** (too small for the MDE) → suppressed effect with no learning.
- **Measuring lift on exposure-day data** → overstates incrementality; measure over the realized window.
- **No guardrails** → optimises one metric while burning a net/opt-out/compliance guardrail.
- **Holdout/arm not tenant-scoped** → cross-tenant contamination (P0).

## References

- Product Canon `METRICS.md` (the metrics under test, realized vs exposed) · `engineering-os-blueprint/06-quality-gates-and-metrics.md`
- [`metric-engine`](../metric-engine/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)
