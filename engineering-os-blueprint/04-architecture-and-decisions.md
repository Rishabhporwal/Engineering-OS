# 04 — Architecture & Technical Decisions

> How the OS designs systems and makes consequential technical choices: the architecture review
> process, the decision-record discipline, the plan as a binding contract, and the framework that
> turns a choice into a recorded, defensible decision.

---

## 1. Architecture as a stage, not a ceremony

Architecture is **Stage 2** of the pipeline ([03](03-delivery-lifecycle.md)) and a cross-cutting
function ([01](01-organization-structure.md)). It is owned by the **Architect**, who produces the
**binding plan** that all downstream stages execute against. Architecture is not a document phase
that precedes "real work" — it is the step that makes the real work small, safe, and reversible.

The Architect's mandate is the **minimal sufficient design**: the smallest change that fulfils the
requirement while respecting the invariants in the Canon. Over-engineering fails the requirement as
surely as under-engineering ([00 §4](00-first-principles.md)).

---

## 2. The binding plan (the contract)

Every requirement above the trivial lane gets a binding plan before any code is written. A valid plan
has:

- **Vertical slices.** Each slice is end-to-end and independently verifiable — not a horizontal layer.
- **Concrete file paths.** Every task names the file(s) it touches. "Update the service" is not a task.
- **A verification step per task.** Each task states how it will be proven done (the command/observation),
  not "tested."
- **Explicit contract changes.** Any change to an API, schema, event, or shared interface is called
  out, with a versioning/compatibility plan.
- **A decision record.** Consequential choices are captured as ADRs (§4).
- **An owner per task.** A role is accountable for each task.

The plan is **the single source of truth for what gets built**. Deviations require an amendment (§3),
never a silent change. See [writing-plans discipline] — tasks are sized to a few minutes of work,
each with one path, one verification, one owner.

---

## 3. The plan-amendment loop

```
 Builder discovers the plan is wrong / insufficient
        │
        ▼
 Raise to Architect (with the specific gap + evidence)
        │
        ▼
 Architect revises the binding plan (and ADR if consequential)
        │
        ▼
 Build resumes against the amended plan
```

This is the **only** legitimate way the plan changes during build. A mid-build discovery — a library
limitation, a missing edge case, a better approach — is a *reason to amend*, not a license to drift.
The loop keeps the plan trustworthy: at any moment, the plan describes what is actually being built.

---

## 4. Architecture Decision Records (ADRs)

Consequential decisions are recorded as ADRs so the *why* survives the people. An ADR is required
when a decision is **hard to reverse** or **affects more than one team/contract**:

- Choice of a technology, framework, datastore, or protocol (a stack decision — see [09](09-reference-architecture.md)).
- A public or cross-service contract shape.
- A data model or partitioning strategy.
- A security, tenancy, or compliance posture.
- A trade-off that sacrifices one design goal for another.

**ADR shape:** context → options considered → decision → consequences (including what it forecloses)
→ status (proposed / accepted / superseded). ADRs are append-only and live with the Canon; a
reversed decision is *superseded by a new ADR*, never edited away.

---

## 5. The technical decision framework

When a choice must be made, the OS applies a consistent test rather than deciding by preference. A
decision is **made and recorded** when it can answer:

1. **What requirement or constraint forces this?** (Grounded in the Canon — Iron Law 1.)
2. **What are the real options?** At least two, stated fairly, including "do nothing / use what
   exists" (don't reinvent a primitive).
3. **What does each option cost across the design goals?** ([00 §1](00-first-principles.md)) —
   correctness, security, reliability, performance, maintainability, cost.
4. **How reversible is it?** Prefer the most reversible option that meets the bar. Irreversible
   choices are escalation candidates.
5. **What does it foreclose?** Every choice closes doors; name them.
6. **What evidence supports it?** Benchmarks, prior art, a spike — not assertion.

Choices that are reversible and within a single team are decided by the owning role. Choices that are
irreversible, cross-team, or change an invariant route to the **Engineering Advisor**, who decides
whether to escalate to the stakeholder ([01 §Escalation](01-organization-structure.md)).

---

## 6. Architecture review

Architecture is reviewed at three moments:

| Moment | Reviewer | What is checked |
|---|---|---|
| **Plan time** (Stage 2) | Architect (self) + Advisor at intake framing | Minimal sufficiency; invariant adherence; contract impact; reversibility. |
| **Final review** (Stage 6) | Engineering Advisor | Did the build adhere to the plan? Were amendments recorded? Is cross-team work coherent? |
| **Governance cadence** | Architecture & Governance function | Drift from the Canon; accumulating ADR debt; patterns worth promoting or retiring ([08](08-technical-governance.md)). |

Review is **evidence-based**, not performative. A reviewer who cannot point to a specific concern
approves; a reviewer with a concern states it concretely with a suggested resolution. Vague approval
and vague objection are both anti-patterns ([code-review discipline]).

---

## 7. Architectural patterns the OS assumes are available

The OS is stack-agnostic but **pattern-opinionated**. It expects designs to be able to reach for —
and ADR their use of — the following, all detailed as a reference in [09](09-reference-architecture.md):

- **Bounded contexts / domain-driven internals.** Services and modules are organized by domain, not
  by technical layer (no "controllers / services / models" top-level split).
- **Clear contracts at every seam.** APIs, events, and shared schemas are explicit, versioned, and
  contract-tested.
- **Event-driven decoupling** where asynchrony and replay matter; **request/response** where
  synchronous consistency matters. The choice is an ADR, not a default.
- **Separation of OLTP and OLAP** concerns; the right datastore for the access pattern.
- **Idempotency** on every mutating operation and external side-effect.
- **Statelessness** in compute where possible; state pushed to purpose-built stores.
- **Tenant isolation** as a primitive enforced at multiple layers, not bolted on.

The OS does not mandate *which* technology implements each pattern — that is the Canon's stack
decision. It mandates that the pattern's intent (isolation, idempotency, traceability, contract
safety) is met and recorded.

---

## 8. Designing for the long-life concerns

Architecture decisions are made with operations in mind from the start ([07](07-operations-and-reliability.md)):

- **Observability is designed in** — the correlation identity and the signals an SRE needs are part
  of the plan, not added after an incident.
- **Failure is designed for** — timeouts, retries with backoff, circuit-breaking, graceful
  degradation, and a rollback path are part of the design.
- **Scale is designed for** — partitioning keys, statelessness, and back-pressure are chosen up
  front, because retrofitting them is a rewrite.
- **Change is designed for** — contracts are versioned and seams are clear so the system can be
  refactored and extended without a big-bang migration.
