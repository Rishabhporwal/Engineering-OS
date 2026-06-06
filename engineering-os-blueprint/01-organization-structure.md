# 01 — Engineering Organization Structure

> The shape of the organization: the engineering functions it contains, the roster that staffs them,
> who owns which decision, how authority and escalation work, and how the organization remembers.

---

## 1. Engineering functions (the complete department)

The Engineering OS is a complete software engineering department. Every function below is a
first-class capability of the OS. In a small organization one role may carry several functions; in a
large one each function is a team. The **function set is fixed**; the **staffing is elastic**.

| # | Function | Responsibility (what it owns) |
|---|---|---|
| 1 | **Product Engineering** | Turning requirements into working, vertically-sliced product capability. |
| 2 | **Platform Engineering** | Internal platforms, paved roads, shared services, and developer self-service. |
| 3 | **Backend Engineering** | Services, APIs, business logic, data access, asynchronous processing. |
| 4 | **Frontend / Web Engineering** | Web user interfaces, client state, rendering, accessibility, web performance. |
| 5 | **Mobile Engineering** | Native/cross-platform mobile apps, offline behavior, store delivery. |
| 6 | **AI / ML Engineering** | Model integration, inference services, evaluation, agentic systems, ML pipelines. |
| 7 | **Data Engineering** | Ingestion, transformation, OLAP/warehouse, data contracts, data quality. |
| 8 | **DevOps & SRE** | CI/CD, infrastructure delivery, reliability, SLOs, on-call, incident response. |
| 9 | **Security Engineering** | Threat modeling, app-sec, secrets, access control, compliance enforcement. |
| 10 | **QA & Test Automation** | Test strategy, real-environment verification, contract tests, regression safety. |
| 11 | **Architecture & System Design** | High/low-level design, decision records, technical coherence across teams. |
| 12 | **Infrastructure Engineering** | Compute, networking, storage, cluster/runtime platform, IaC. |
| 13 | **Database Engineering** | Schema design, indexing, query performance, migrations, partitioning. |
| 14 | **Integration Engineering** | External/internal system integration, connectors, event contracts, idempotency. |
| 15 | **Developer Experience (DX)** | Tooling, build systems, local environments, golden paths, internal docs. |
| 16 | **Performance Engineering** | Latency/throughput/cost budgets, load testing, profiling, capacity. |
| 17 | **Reliability Engineering** | Error budgets, resilience patterns, chaos/failure testing, graceful degradation. |
| 18 | **Technical Documentation** | Architecture docs, runbooks, API references, ADRs, onboarding material. |
| 19 | **Release Management** | Release trains, change control, deployment orchestration, release notes. |
| 20 | **Incident Management** | Severity ladder, incident command, mitigation, blameless postmortems. |
| 21 | **Technical Governance** | Standards, tech radar, version policy, architectural review authority. |

These functions are not org-chart boxes; they are **capabilities the OS guarantees are present and
owned** for any requirement. The roster (§3) maps them onto a small number of agents.

---

## 2. Organizing principle: capability over hierarchy

The OS is organized by **capability and decision rights**, not by reporting lines. Three structural
rules:

1. **Single owner per gate.** Every quality gate has exactly one accountable owner. Shared ownership
   of a gate is treated as no ownership.
2. **Authority is scoped, not seniority-based.** A role's VETO applies only within its domain
   (security, QA, final). Authority does not leak across domains.
3. **Cross-cutting concerns have a home.** Architecture, security, observability, and governance
   cross every team but are *owned* by a named function so they are never "everyone's job, therefore
   no one's."

This mirrors a **bounded-context** organization: each function owns its domain end-to-end, exposes a
clear contract to the others, and does not reach into another's internals.

---

## 3. The roster (the agents that staff the functions)

The OS staffs the 21 functions with a compact roster of roles. Each role is fully specified in
[02 — Engineering Roles](02-engineering-roles.md); summarized here for the org view. Roles are
**role-named** (not person-named) so the OS is reusable; a consuming organization may attach human or
team identities in the Foundation phase.

| Role | Functions carried | Owns the gate? | Authority |
|---|---|---|---|
| **Engineering Advisor** (intake + final review) | Technical governance, intake, coherence | **Final review (VETO)** | Sole authority to escalate to the stakeholder; sets review rigor. |
| **Stress-test Persona(s)** | Risk surfacing (compliance / cost / scale / ops, derived per product) | — | Must surface ≥1 concern; advisory. |
| **Architect** | Architecture & system design | Binding plan (the contract) | Owns the plan and the plan-amendment loop; raises concerns to the Advisor. |
| **Backend Engineer** | Backend, database, integration | — | Executes the plan; deviations route to the Architect. |
| **Frontend / Web Engineer** | Frontend, web performance, accessibility | — | Executes the plan. |
| **Mobile Engineer** | Mobile, app-store delivery | — | Executes the plan. |
| **AI/ML Engineer** | AI/ML, data, agentic systems | — | Executes the plan; evaluation-gated. |
| **Security Reviewer** | Security engineering, compliance enforcement | **Security review (VETO)** | VETO on critical/high findings, compliance gaps, missing traceability. |
| **QA Engineer** | QA & test automation | **QA review (VETO)** | VETO on missing real-environment verification, contract gaps, invalid tests. |
| **Platform / SRE** | DevOps, SRE, infrastructure, reliability, release | Deploy + monitor + rollback | Owns deployment, the bake window, and auto-rollback. |
| **Delivery Coordinator** | Release management, documentation, coordination | — | Cross-cuts; release notes, tracker sync, surfaces escalations. |

> **Two reviewer hats, one judgment.** The Engineering Advisor appears at both **intake** (framing
> the requirement, picking the lane) and **final review** (the go/no-go VETO). These are the same
> judgment applied at two ends of the pipeline; the final-review hat warrants the most capable tier
> because it is the last line before the stakeholder gate.

The number of stress-test personas is **bounded** (0–2; see [04](04-architecture-and-decisions.md)
and [11](11-runtime-and-cost-doctrine.md)) — fan-out is a tool, not a reflex.

---

## 4. The authority & VETO model

```
                 Stakeholder (human)  ── files requirements · approves Foundation · deploy gate
                          ▲
                          │ escalation (rubric-gated, last resort)
                          │
                 Engineering Advisor ── sole escalation authority · Final-review VETO
                    ▲            ▲
        raises concern        raises concern
                    │            │
   ┌───────────┬────┴───┬────────┴────┬─────────────┐
 Architect  Security  QA Engineer  Builders     Platform/SRE
 (plan)     (VETO)    (VETO)       (execute)     (deploy gate)
```

Rules of authority:

- **Three VETO gates:** Security (Stage 4), QA (Stage 5), Final review (Stage 6). A VETO does not
  block forever — it **routes the work back** to the responsible stage (Build, or Architecture if the
  plan itself is wrong). See [03](03-delivery-lifecycle.md) and [06](06-quality-gates-and-metrics.md).
- **Escalation is not democratic.** Any role hitting an escalation-rubric condition raises it to the
  Engineering Advisor. The Advisor — and only the Advisor — decides whether to escalate to the
  stakeholder. If the Advisor can answer in good conscience from the Canon and lessons-learned, the
  Advisor answers. Escalation is a last resort, not a status update.
- **The stakeholder is touched at a minimal, fixed set of points** ([03 §Touchpoints](03-delivery-lifecycle.md)).
  No mid-build pings, no per-change reviews. The organization runs autonomously between gates.

---

## 5. The escalation rubric

Defined per product in the Foundation phase; the OS supplies the **categories**, the Canon supplies
the **thresholds**. An escalation *may* be warranted when a change would:

- Make an **irreversible or high-blast-radius** decision (data migration, public API contract, a
  security/tenancy boundary).
- Enter **compliance or regulatory ambiguity** the Canon does not resolve.
- **Threaten a cost, performance, or reliability budget** beyond an agreed threshold.
- Create a **cross-team conflict** of patterns or contracts that the Architect cannot reconcile.
- Change an **invariant** or the product's compounding asset (the "moat").

Flow: any role → Engineering Advisor → Advisor decides. The Delivery Coordinator mirrors any pending
escalation into a single visible queue so nothing is silently waiting.

---

## 6. Memory — the organization that gets smarter

The OS keeps a durable, version-controlled memory in the **consuming repository** (not in the OS
framework itself). This is what makes the organization compound rather than restart.

```
<repo>/.engineering-os/
├── foundation-approved.<sentinel>     # gate: the Foundation is approved (unlocks the pipeline)
├── knowledge-base/                    # the approved Product Canon (stack, design, invariants, moat)
├── team-roster.<doc>                  # human/team identities attached to roles (optional)
├── lessons-learned.<doc>              # compounding learnings; feeds escalation judgment
├── pending-stakeholder-attention.<doc># escalations awaiting a decision
├── requirements/<id>/                 # per-requirement working set
│   ├── 01-intake.<doc>                # framing + lane + concerns
│   ├── 02-architecture-plan.<doc>     # the binding plan
│   ├── journal.<doc>                  # build journal (decisions, deviations, amendments)
│   └── decision-log.<doc>             # stage decisions, VETOs, outcomes
└── state/                             # pipeline state (what is in flight, the routing cursor)
```

Memory rules (Iron Law 7):

- **Committed, never ignored.** The audit trail lives in git so every teammate who pulls inherits
  the full history of every prior requirement.
- **Separate commit boundary.** Product code and the `.engineering-os/` audit trail are committed
  separately, with explicit paths — never blanket-staged together. See
  [07 — Release Management](07-operations-and-reliability.md).
- **Append-and-outcome.** Decisions are recorded when made and **updated with their outcome** later
  (e.g. did the change hold up at the next review, at the bake window). A decision without an outcome
  is an open loop.
- **Lessons feed forward.** `lessons-learned` is consulted at intake and during escalation judgment
  so the same mistake is not re-litigated.

---

## 7. Scaling the structure (startup → enterprise)

The OS does not change shape as the organization grows; three dials do:

| Dial | Small org | Large org |
|---|---|---|
| **Staffing of roles** | One person carries several roles; one AI agent per function. | A team per function; multiple parallel builder tracks. |
| **Lane thresholds** | Generous lean/express lanes for velocity. | Tighter lanes; more changes routed to full rigor. |
| **Parallelism / fan-out caps** | Low (cost-sensitive). | Higher caps; parallel reviews and builder tracks. |

The gates, the VETO model, the escalation rubric, and the memory model are **identical at every
scale**. That invariance is what lets the same OS run anywhere.
