# Engineering OS — A Universal Technology Delivery Framework

> A complete, domain-agnostic **Engineering Operating System**: an autonomous, highly-skilled
> software engineering organization expressed as a reusable framework. It takes any requirement
> from intake to production and long-term operation, for any software product, on any stack.

This blueprint describes a **technology-first engineering organization** — its structure, roles,
delivery lifecycle, standards, quality gates, operations, and governance — with **no business,
product, or domain knowledge baked in**. Domain specifics (the product being built, the stack,
the compliance regime, the metrics that matter) are not hard-coded; they are **supplied once, per
adoption**, through a Foundation phase ([10 — Adoption & Product Canon](10-adoption-and-product-canon.md))
and then drive everything else.

The OS is designed to be reused across **startups, scale-ups, enterprises, agencies, product
companies, consulting firms, SaaS / AI / data / infrastructure organizations, and internal
platform teams** — without modification to the OS itself.

---

## The core idea: two layers, cleanly separated

| Layer | What it is | Where it's defined | Changes when |
|---|---|---|---|
| **The Engineering OS** (this blueprint) | The *organization that builds software* — roles, pipeline, standards, gates, governance. Stable, reusable, domain-free. | These documents. | Almost never. |
| **The Product Canon** (per adoption) | The *thing being built* — its requirements, chosen stack, architecture, compliance regime, invariants, the asset that compounds. | A consuming repo's `knowledge-base/`, produced in the Foundation phase. | Per product, per major decision. |

The OS never assumes what you're building. It assumes only that you are building **software that
must be correct, secure, observable, reliable, and maintainable** — and it supplies the
organization, process, and discipline to do that well.

---

## How to read this

Read in order for a full mental model; jump by need otherwise.

| # | Document | What it answers |
|---|---|---|
| 00 | [First Principles](00-first-principles.md) | What the OS is and is not; design goals; the laws every role obeys. |
| 01 | [Organization Structure](01-organization-structure.md) | The engineering functions, the roster, authority & VETO model, escalation. |
| 02 | [Engineering Roles](02-engineering-roles.md) | Every role's scope, deliverables, decision rights, and model/effort tier. |
| 03 | [Delivery Lifecycle](03-delivery-lifecycle.md) | The SDLC: Foundation + the staged requirement→release pipeline, lanes, touchpoints, state. |
| 04 | [Architecture & Technical Decisions](04-architecture-and-decisions.md) | Architecture review, ADR/RFC, the decision framework, plan-binding, research discipline. |
| 05 | [Engineering Standards](05-engineering-standards.md) | Code review, testing, security, observability, API/data/infra/documentation standards. |
| 06 | [Quality Gates & Engineering Metrics](06-quality-gates-and-metrics.md) | The gate at every stage; engineering KPIs; delta re-review; verification validity. |
| 07 | [Operations & Reliability](07-operations-and-reliability.md) | Deployment & release management, incident management, SRE/SLOs, production support. |
| 08 | [Technical Governance](08-technical-governance.md) | Tech radar, standards governance, version/dependency policy, compliance-as-capability. |
| 09 | [Reference Architecture](09-reference-architecture.md) | A stack-agnostic cloud-native reference and the adapters that make any stack pluggable. |
| 10 | [Adoption & Product Canon](10-adoption-and-product-canon.md) | How to instantiate the OS for a new product; the Foundation phase; the canon template. |
| 11 | [Runtime & Cost Doctrine](11-runtime-and-cost-doctrine.md) | When the OS is run by AI agents: model tiering, caching, telemetry, spend discipline. |

---

## The shape of the organization, in one picture

```
                              ┌────────────────────────────────────────┐
                              │              PRODUCT CANON               │
                              │  Requirements · Stack · Architecture ·   │
                              │  Invariants · Compliance regime · Moat   │
                              │        (supplied once, in Foundation)    │
                              └───────────────────┬──────────────────────┘
                                                  │ grounds every role & gate
   ┌──────────────────────────────────────────────▼─────────────────────────────────────────┐
   │                                   THE ENGINEERING OS                                      │
   │                                                                                           │
   │   Requirement ─▶ ① Intake ─▶ ② Architecture ─▶ ③ Build ─▶ ④ Security ║ ⑤ QA ─▶ ⑥ Final   │
   │                    │             (binding plan)   (vertical    (VETO)    (VETO)   review  │
   │                    │                              slices)                          (VETO) │
   │                    │                                                                  │    │
   │                    ▼                                                                  ▼    │
   │            Stakeholder gate ◀──────────────── ⑦ Approve/Reject ◀──────────────────────┘    │
   │                    │                                                                        │
   │                    ▼                                                                        │
   │            ⑧ Deploy ─▶ Monitor (bake window) ─▶ Auto-rollback on breach ─▶ Release notes    │
   │                                                                                           │
   │   Cross-cutting: Architecture review · Code review · Testing · Observability ·            │
   │   Security · Incident mgmt · SRE/SLOs · Governance · Documentation · DX                   │
   └───────────────────────────────────────────────────────────────────────────────────────────┘
```

Lanes scale the rigor to the risk: a copy change and a change to an auth boundary do **not**
travel the same path ([03 — Delivery Lifecycle](03-delivery-lifecycle.md)).

---

## What makes this an *operating system*, not a process doc

1. **Roles are agents, not titles.** Each function has a defined scope, decision rights, inputs,
   outputs, and a gate it owns. It can be staffed by a human, an AI agent, or both — the contract
   is identical.
2. **The pipeline is deterministic control-flow.** Which stages run, who owns them, and what each
   produces is declared data ([03](03-delivery-lifecycle.md)), not re-improvised per task.
3. **Gates carry VETO, and a VETO routes back — it is never silently overridden.**
4. **Memory compounds.** Every decision, review, and outcome is recorded in the consuming repo so
   the organization gets smarter with each requirement ([01](01-organization-structure.md) §Memory).
5. **The OS applies its own discipline to itself** — cost, verification, and observability doctrine
   bind the OS's own operation ([11](11-runtime-and-cost-doctrine.md)).

---

## Adopting it

See [10 — Adoption & Product Canon](10-adoption-and-product-canon.md). In short:

1. Run the **Foundation phase** once: supply requirements + technical constraints, and the OS
   produces the Product Canon (`knowledge-base/`).
2. Approve the Foundation. This unlocks the recurring pipeline.
3. File requirements. The OS delivers them to production, end to end, and records everything.
