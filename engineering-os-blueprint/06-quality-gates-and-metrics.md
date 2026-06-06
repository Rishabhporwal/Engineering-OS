# 06 — Quality Gates & Engineering Metrics

> The enforcement layer. Every standard in [05](05-engineering-standards.md) becomes a **gate** here:
> a concrete, owned, pass/fail checkpoint a change must clear to advance. Plus the metrics by which
> the OS measures its own delivery health, and the discipline that keeps re-review cheap without
> losing rigor.

---

## 1. What a gate is

A gate is a checkpoint with four properties:

1. **An owner** — exactly one role is accountable ([01 §3](01-organization-structure.md)).
2. **A pass condition** — objective, evidence-based, stated in advance.
3. **A consequence on failure** — routes the work back to a named stage; never a silent override.
4. **A record** — the verdict and its evidence are written to the requirement's decision log.

Gates are **not** advisory. A VETO gate that fails stops advancement until the failure is resolved or
the work is explicitly bounced.

---

## 2. The gate at every stage

| Stage | Gate owner | Pass condition (evidence required) | On fail |
|---|---|---|---|
| **Foundation** | Stakeholder | Canon is coherent, complete, approved | Pipeline stays locked |
| **1 — Intake** | Engineering Advisor | Requirement unambiguous; lane chosen; concerns recorded; Foundation sentinel present | Challenge back to stakeholder |
| **2 — Architecture** | Architect | Plan is minimal-sufficient; every task has path + verification + owner; contracts explicit | Re-plan |
| **3 — Build** | Builder (self) | Vertical slice works in a real env; tests valid; trace IDs propagate; plan adhered to | Fix before hand-off |
| **4 — Security** *(VETO)* | Security Reviewer | No open critical/high; compliance regime satisfied; traceability present | Bounce to Build/Arch |
| **5 — QA** *(VETO)* | QA Engineer | Real-env verification observed; contracts + parity pass; tests valid; full suite green; trace IDs end-to-end | Bounce to Build/Arch |
| **6 — Final** *(VETO)* | Engineering Advisor | Cross-team coherent; plan adhered to; no open VETO; commit boundaries correct | Bounce to responsible stage |
| **7 — Stakeholder** | Stakeholder | Business/owner acceptance | Reject → back to intake |
| **8 — Deploy** | Platform / SRE | Released via playbook; health green through bake window; rollback ready; observability healthy | Auto-rollback |

The **accessibility gate** ([05 §9](05-engineering-standards.md)) and the **test-validity scan**
(§4) run inside QA — and the test-validity scan runs on **every lane**, even express.

---

## 3. Verification validity — the gate behind "done"

The most important gate is the one that decides whether a "pass" is real. It encodes Iron Law 4
("verify before you claim") and the anti-pattern ban on tautological/inert verification:

- **Ran under real conditions.** Verification executed against a real environment / real security
  context — not mocks, not with isolation bypassed.
- **Negative control present.** The test fails when its protection is removed. A green test that stays
  green with the guard gone is a **failure**, not a pass.
- **Independent oracle.** Equality/parity is checked against an independent source of truth.
- **No silent truncation.** If coverage was bounded, it is stated.

A "done" claim without this evidence is rejected at the QA and Final gates. *A green test under
bypassed protection is worse than no test* — it is treated as a defect.

---

## 4. Delta re-review — rigor without re-paying

When a VETO bounces work and a fix lands, re-reviewing the *entire* surface is wasteful. The OS
re-reviews the **delta** while keeping a hard regression backstop. Two things are deliberately
decoupled:

- **The review reasoning is delta-scoped.** The reviewer reads the prior PASS record + the diff +
  the changed code's direct callers/importers/tests — enough to catch local and near-neighbor
  interactions, far cheaper than re-reasoning the whole surface.
- **The test suite is NOT delta-scoped.** On every bounce-fix the **full prior-passing suite runs**
  (it's CI, cheap to execute). Any test that passed before and now fails — even in an untouched file
  the diff silently broke via a transitive import, shared type, or migration side-effect — **auto-blocks**.

This exploits the asymmetry: *cheap to run all the tests, expensive to re-reason the whole surface.*
The full-suite run is exactly the backstop for the cross-cutting regressions that delta reasoning
structurally cannot see.

**A fix forces a FULL re-review (not delta) when it touches a high-stakes path** — compliance,
tenant isolation, a shared-contract parity surface, system-of-record/audit writes, money, auth, or an
outbound side-effect — **or** when the diff exceeds the bounced finding's blast radius (new files,
endpoints, or migrations the bounce didn't name).

---

## 5. Engineering KPIs & metrics

The OS measures its own delivery health. Metrics are **diagnostic, not targets to game** — they exist
to surface where the system is slow, fragile, or wasteful.

### Delivery performance (DORA)

| Metric | What it tells you |
|---|---|
| **Deployment frequency** | How often change reaches production safely. |
| **Lead time for change** | Requirement filed → running in production. |
| **Change failure rate** | Share of deploys that cause a rollback/incident. |
| **Mean time to restore (MTTR)** | How fast a degraded service recovers. |

### Quality & rigor

| Metric | What it tells you |
|---|---|
| **Escaped-defect rate** | Defects found in production vs. caught at a gate. |
| **Gate bounce rate (by stage & cause)** | Where the pipeline most often sends work back, and why. |
| **Verification validity rate** | Share of "passes" with a real negative control. |
| **Test/mutation coverage on high-stakes paths** | Whether the riskiest code is actually guarded. |
| **Rework ratio** | Effort spent re-doing vs. doing. |

### Reliability & operations

| Metric | What it tells you |
|---|---|
| **SLO attainment & error-budget burn** | Whether reliability targets hold ([07](07-operations-and-reliability.md)). |
| **Incident rate, severity mix, MTTA/MTTR** | Operational health and response capability. |
| **Auto-rollback rate** | How often the bake window catches a bad deploy. |
| **Toil ratio** | Share of operational work that is manual/repetitive (a target to *reduce*). |

### Efficiency

| Metric | What it tells you |
|---|---|
| **Cost per change / per requirement** | Delivery economics ([11](11-runtime-and-cost-doctrine.md)). |
| **CI/build time and cache hit rate** | Developer-experience friction. |
| **Lane distribution** | How much work travels each rigor lane; drift signals mis-classification. |

> **Anti-gaming rule.** No metric is an individual performance target. Metrics drive **system**
> changes (a high bounce rate at security means shift security further left; a high escaped-defect
> rate means a gate is too weak). Goodhart's law is assumed: the moment a metric becomes a target, it
> stops measuring.

---

## 6. The gate ledger

Every gate verdict — pass, VETO, bounce, amendment, and its **outcome** — is appended to the
requirement's decision log and survives in the consuming repo's memory ([01 §6](01-organization-structure.md)).
This is what lets the OS compute the metrics above honestly (from recorded reality, not
self-report) and what lets the next requirement learn from this one. A verdict without a recorded
outcome is an open loop the Delivery Coordinator surfaces.
