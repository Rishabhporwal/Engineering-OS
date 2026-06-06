# 02 — Engineering Roles

> Every role specified as a contract: scope, inputs, outputs, decision rights, the gate it owns, and
> the capability tier it runs at. A role is staffable by a human, an AI agent, or both — the contract
> is identical either way.

Each role is defined by the same shape:

- **Scope** — what it is accountable for.
- **Inputs → Outputs** — what it consumes and the artifact it produces.
- **Decision rights** — what it may decide, what it must escalate, whether it holds a VETO.
- **Tier** — the capability/effort level appropriate to the work (see [11](11-runtime-and-cost-doctrine.md)).
- **Definition of Done** — when its hand-off is valid.

Tiers are abstract (`deep`, `standard`, `mechanical`) so the OS is model- and vendor-agnostic; the
mapping to concrete models/effort is set per adoption.

---

## 1. Engineering Advisor — intake & final review

The technical conscience of the organization. Appears at both ends of the pipeline.

- **Scope.** Frames incoming requirements; co-leads the Foundation phase; runs the final go/no-go
  review; owns technical coherence across teams; sole authority to escalate to the stakeholder.
- **Inputs → Outputs.** Stakeholder requirement → intake framing (problem statement, constraints,
  lane selection, concerns surfaced). At the far end: the reconciled change → a final-review verdict.
- **Decision rights.** Sets review rigor and persona count (0–2). **Holds the Final-review VETO.**
  Decides, alone, whether any escalation reaches the stakeholder. Answers from the Canon and
  lessons-learned whenever possible rather than escalating.
- **Tier.** `deep` for final review and Foundation; `standard` for routine intake framing.
- **Definition of Done.** Intake: requirement is unambiguous, lane is chosen, concerns are recorded.
  Final: cross-team work reconciles, the plan was adhered to, no open VETO, commit boundaries are
  correct — or an explicit, recorded BOUNCE.

---

## 2. Stress-test Persona(s) — adversarial risk surfacing

Bounded, on-demand adversaries that pressure-test a requirement from a specific angle.

- **Scope.** Inhabit exactly one risk lens derived per product (e.g. compliance officer, cost
  realist, scale/operations skeptic, integration realist) and attack the requirement from it.
- **Inputs → Outputs.** The framed requirement → ≥1 concrete concern with a suggested mitigation.
- **Decision rights.** Advisory only. Must surface at least one real concern; cannot block.
- **Tier.** `mechanical`–`standard`, scaled to depth needed. **Count is capped at 2** — fan-out is a
  deliberate choice, not a reflex.

---

## 3. Architect — system design & the binding plan

Turns an approved requirement into the smallest, safest, most reversible plan that ships the value.

- **Scope.** High- and low-level design; the binding implementation plan; the plan-amendment loop;
  architectural coherence with the Canon; ADRs for consequential decisions.
- **Inputs → Outputs.** Framed requirement + Canon → a **binding plan**: vertical slices, concrete
  file paths, per-task verification steps, contract/interface changes, and the decision record.
- **Decision rights.** Owns the plan; the plan is the contract for all downstream stages. Approves or
  rejects plan amendments. Raises irreducible concerns to the Engineering Advisor (who decides on
  escalation). Does **not** hold a VETO — the plan's authority is structural, not adversarial.
- **Tier.** `deep` — runs once per requirement; deep design reasoning is justified here.
- **Definition of Done.** Every downstream task has a file path, a verification step, and an owner;
  contract changes are explicit; the design is the *minimal sufficient* one, not the most elaborate.

---

## 4. Backend Engineer

- **Scope.** Services, APIs, business logic, data access, async processing, integration, schema and
  query work, idempotency.
- **Inputs → Outputs.** The plan → working backend slices + a build journal; every endpoint and
  message consumer trace-instrumented; migrations reversible.
- **Decision rights.** Executes the plan. Any required deviation routes to the Architect's amendment
  loop — never silent. Owns correctness, security posture, and observability of its code.
- **Tier.** `standard`.
- **Definition of Done.** Slice works end-to-end under a real environment; tests are valid (negative
  controls pass — see [06](06-quality-gates-and-metrics.md)); trace IDs propagate; no contract broken
  without a versioning plan.

---

## 5. Frontend / Web Engineer

- **Scope.** Web UI, client state, rendering strategy, accessibility, web performance, surfacing
  errors with correlation IDs.
- **Inputs → Outputs.** The plan → working UI slices that propagate trace context and meet the
  accessibility and performance budgets in [05](05-engineering-standards.md).
- **Decision rights.** Executes the plan; deviations → Architect. Owns not reinventing UI primitives.
- **Tier.** `standard`.
- **Definition of Done.** Meets accessibility gate (keyboard/focus, non-color-only state, reduced
  motion), performance budget, and surfaces request IDs on error states.

---

## 6. Mobile Engineer

- **Scope.** Native/cross-platform mobile apps, offline-first behavior, push, deep links, store
  delivery and over-the-air vs. native-binary release rules.
- **Inputs → Outputs.** The plan → working mobile slices with trace-context propagation and an
  appropriate release channel.
- **Decision rights.** Executes the plan; deviations → Architect. Owns store-policy compliance and
  the native-vs-OTA decision per change.
- **Tier.** `standard`.
- **Definition of Done.** Works offline where specified; correct release channel chosen; trace
  propagation verified.

---

## 7. AI/ML Engineer

- **Scope.** Model integration and inference services, evaluation harnesses, agentic systems, data
  pipelines, the cost-routing of compute (cheapest method that meets the bar).
- **Inputs → Outputs.** The plan → AI/ML or data slices, each gated by an **evaluation** (golden
  set, groundedness/quality, regression vs. baseline) before it ships.
- **Decision rights.** Executes the plan; deviations → Architect. Owns the evaluation gate for any
  model/prompt/pipeline change — ships only if quality ≥ baseline. Owns choosing the cheapest
  compute paradigm that meets the requirement.
- **Tier.** `standard` (with `deep` for evaluation design).
- **Definition of Done.** Eval passes vs. baseline; LLM/model calls are trace-instrumented;
  non-deterministic behavior is bounded and observable.

---

## 8. Security Reviewer — Stage 4 VETO

- **Scope.** Threat modeling, application security, input validation, output encoding, secrets and
  key management, access control, and **compliance enforcement** (the regime is product-defined).
- **Inputs → Outputs.** The built change → a security verdict with findings classified by severity.
- **Decision rights.** **VETO** on any critical/high finding, any compliance violation in the
  product's regime, or **missing traceability**. A VETO routes the work back. Surfaces
  rubric-matching findings to the Engineering Advisor.
- **Tier.** `standard` for the checklist + scanner sweep; `deep` only on a genuine critical/ambiguous
  finding that needs reasoning.
- **Definition of Done.** No open critical/high; threat surfaces reviewed; secrets/access verified;
  traceability present.

---

## 9. QA Engineer — Stage 5 VETO

- **Scope.** Test strategy, real-environment verification, contract tests, cross-runtime/contract
  parity, regression safety, mutation testing on high-stakes paths, verification *validity*.
- **Inputs → Outputs.** The built change → a QA verdict with evidence (real-network smoke, contract
  results, parity, end-to-end trace confirmation).
- **Decision rights.** **VETO** on missing real-environment verification, missing contract tests,
  cross-runtime parity failure, mutation-test gaps on high-stakes paths, or trace IDs not appearing
  end-to-end. Also VETO on **invalid** tests (passing under bypassed protection, inert probes,
  tautological parity). A VETO routes the work back.
- **Tier.** `standard`.
- **Definition of Done.** Verification ran against a real environment and was observed; negative
  controls pass; the full prior-passing suite still passes; trace IDs appear end-to-end.

---

## 10. Platform / SRE — deploy, monitor, rollback

- **Scope.** CI/CD, infrastructure-as-code, the runtime platform, reliability and SLOs, on-call and
  incident response, release orchestration, and the post-deploy bake window.
- **Inputs → Outputs.** The approved change → a release: progressive rollout, a monitored bake
  window, and **auto-rollback on SLO breach**; verifies the observability pipeline is healthy
  post-deploy.
- **Decision rights.** Owns deployment strategy, the bake window length, and rollback thresholds
  (per the deploy playbook in the Canon). Can halt a rollout. Owns production health.
- **Tier.** `standard`.
- **Definition of Done.** Released via the documented strategy; health signals green through the bake
  window; rollback rehearsed and ready; observability confirmed.

---

## 11. Delivery Coordinator — cross-cutting

- **Scope.** Release notes, external tracker synchronization, surfacing escalations into one visible
  queue, documentation hygiene. Cross-cuts the pipeline; owns no single stage.
- **Inputs → Outputs.** Pipeline state → release notes, tracker updates, a maintained
  `pending-stakeholder-attention` queue.
- **Decision rights.** No VETO. Ensures nothing is silently waiting and that every shipped change is
  documented and traceable to its requirement.
- **Tier.** `mechanical`–`standard`.
- **Definition of Done.** Every shipped requirement has release notes and a tracker record; the
  escalation queue reflects reality.

---

## 12. Mapping roles to functions

The 11 roles carry the 21 functions of [01](01-organization-structure.md):

| Function | Primary role | Supporting |
|---|---|---|
| Product / Backend / Frontend / Mobile / AI-ML / Data engineering | the matching builder | Architect (design) |
| Platform / Infrastructure / DevOps / SRE / Reliability / Release | Platform / SRE | Architect |
| Database / Integration / Performance | Backend Engineer | Architect, Platform/SRE |
| Security / Compliance | Security Reviewer | all builders (shift-left) |
| QA / Test automation | QA Engineer | all builders |
| Architecture / System design / Governance | Architect + Engineering Advisor | — |
| Documentation / DX | Delivery Coordinator + owning builder | all |
| Incident management | Platform / SRE (Incident Commander) | Engineering Advisor |

> A small organization collapses many roles onto few agents; a large one expands each into a team.
> The **contracts above never change** — that is what lets a requirement move through the same
> pipeline regardless of how the roles are staffed.
