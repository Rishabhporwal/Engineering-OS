# 00 — First Principles

> The non-negotiable foundations. Everything else in this blueprint is downstream of this document.
> If a later rule appears to contradict these principles, these principles win.

---

## 0. What the Engineering OS is — and is NOT

The **Engineering OS** is a complete, autonomous software engineering organization expressed as a
reusable framework. It delivers any requirement from intake to production and operates it for the
long term. It is staffed by a fixed roster of engineering **roles**, each with a defined scope and
the authority to own a gate, coordinated by a deterministic delivery **pipeline**.

It **is**:

- A *technology-first organization* — engineering functions, processes, and software delivery
  capability, and nothing else.
- *Domain-agnostic* — it carries no product, business, market, or commercial knowledge.
- *Stack-agnostic* — it mandates patterns and standards, not a specific technology choice.
- *Reusable* — the same OS runs a two-person startup and a thousand-engineer enterprise; only the
  Product Canon and the lane thresholds differ.

It is **NOT**:

- A product. The product is defined elsewhere, in the **Product Canon** ([10](10-adoption-and-product-canon.md)).
- A business plan. It contains no strategy, marketing, sales, finance, pricing, or
  customer-acquisition content. Those are explicitly out of scope.
- A fixed stack. It names a *reference* architecture ([09](09-reference-architecture.md)) as one
  illustrative example, never a requirement.

> **The separation is load-bearing.** The OS knows *how to build software well*. The Product Canon
> knows *what to build and under what constraints*. Keeping these apart is what makes the OS reusable
> across every domain and industry.

---

## 1. Design goals (the OS optimizes for these, in tension, deliberately)

| Goal | What it means in practice |
|---|---|
| **Correctness** | Behavior is verified against an independent source of truth before "done." False confidence is treated as worse than no test. |
| **Security** | Threats are modeled, inputs validated, secrets managed, least-privilege enforced. Security owns a VETO gate. |
| **Reliability** | Systems have explicit SLOs, error budgets, health signals, and rehearsed rollback. Release is decoupled from deploy. |
| **Observability** | Every request is traceable end-to-end through one correlation identity. Un-traceable code does not ship. |
| **Performance** | Latency, throughput, and cost budgets are set before build and enforced as gates. |
| **Scalability** | Designs assume horizontal growth, statelessness where possible, and partitioned data from day one. |
| **Maintainability** | Code reads like its surroundings; bounded contexts; small reversible changes; documentation as a deliverable. |
| **Modularity & extensibility** | Clear seams, contracts, and adapters so capabilities are added without rewrites. |
| **Reusability** | Primitives are built once and shared; reinventing an existing capability is a review finding. |

These goals conflict (e.g. performance vs. simplicity, velocity vs. rigor). The OS resolves the
tension **explicitly and per-change**, via lanes ([03](03-delivery-lifecycle.md)) and the technical
decision framework ([04](04-architecture-and-decisions.md)) — never implicitly.

---

## 2. The Iron Laws (every role, every task, no exceptions)

These are the behavioral invariants. They are enforced by gates and hooks, not by goodwill.

1. **Ground every decision in the Canon.** No work proceeds on assumption when an authoritative
   source exists. If the Canon is silent or contradictory, surface it — do not invent.
2. **Plan before building; build to the plan.** A change has a binding plan before code is written.
   Mid-build discoveries route through a plan-amendment loop, never ad-hoc freelancing.
3. **Deliver in vertical slices.** Each unit of work is a thin, end-to-end, independently
   verifiable increment — not a horizontal layer that integrates "later."
4. **Verify before you claim.** "Done," "passing," "ready," and "fixed" are claims that require
   running the verification and observing the result. See [06](06-quality-gates-and-metrics.md).
5. **A VETO routes back; it is never overridden.** Security, QA, and Final review hold VETO. On a
   VETO, work returns to the responsible stage. No stage advances past an open VETO.
6. **Make it traceable or it does not ship.** One correlation identity propagates through every
   hop. Missing traceability is a VETO surface.
7. **Memory is the moat — it is committed, never discarded.** Decisions, reviews, and outcomes are
   recorded in the consuming repo and survive every hand-off and every teammate.

> A task that cannot satisfy the Iron Laws is not "blocked by process" — it is **under-specified**,
> and the correct action is to surface the gap, not to bypass the law.

---

## 3. The anti-patterns (explicitly forbidden)

- **Freelancing past the plan.** Discovering a "better way" mid-build authorizes a plan amendment,
  not a silent deviation.
- **Horizontal slices.** "Build all the models, then all the services, then wire the UI" defers
  integration risk to the worst possible moment.
- **Tautological / inert verification.** A test that passes with the protection removed, a probe
  that cannot fail, or a parity check asserted against itself proves nothing and is a gate failure.
- **Silent truncation.** If coverage is bounded (sampled, top-N, no-retry), it is stated — never
  presented as completeness.
- **Reinventing a primitive.** Re-implementing something the Canon or the codebase already provides
  is a review finding, not initiative.
- **History rewrite / blanket staging.** Commits use explicit paths; history is append-only; the
  audit trail is never `git add -A`'d away. See [07 — Release Management](07-operations-and-reliability.md).
- **Status-theater.** Mid-build pings, performative agreement, and unverified "looks good" are
  noise. The organization communicates through gates and recorded decisions.

---

## 4. Build the minimum that fulfils the requirement

The OS is biased toward **the smallest, safest, most reversible change that ships the value**. It is
not biased toward elaborate architecture. Over-engineering is a defect of the same severity as
under-engineering: both fail the requirement. The architecture role's job at plan time
([04](04-architecture-and-decisions.md)) is to find the *minimal sufficient* design, not the most
impressive one.

---

## 5. How the principles are enforced (not merely stated)

| Principle | Enforcement mechanism |
|---|---|
| Ground in Canon | Foundation gate; roles load the relevant Canon section as stable context. |
| Plan-binding | The architecture stage produces a binding plan; deviations require an amendment. |
| Vertical slices | Build-stage Definition of Done; QA gate. |
| Verify before claim | Verification-validity gate; negative controls required ([06](06-quality-gates-and-metrics.md)). |
| VETO routes back | Deterministic routing in the pipeline ([03](03-delivery-lifecycle.md)). |
| Traceability | Security VETO on missing traceability; QA verifies trace IDs end-to-end. |
| Memory compounds | The audit trail is committed to the consuming repo as a separate, explicit commit boundary. |

The throughline: **principles the OS cannot enforce are principles the OS does not rely on.** Every
law above maps to a gate, a hook, or a deterministic routing rule — described in the documents that
follow.
