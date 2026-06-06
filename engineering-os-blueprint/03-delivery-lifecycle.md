# 03 — Delivery Lifecycle (the SDLC)

> How a requirement becomes operating production software. The lifecycle has two phases: a one-time
> **Foundation** that grounds the OS in a product, and a **recurring pipeline** that delivers each
> requirement. The pipeline is **deterministic control-flow** — which stages run, who owns them, and
> what each produces is declared, not re-improvised per task.

---

## 1. The two-phase operating model

```
 ┌─────────────────────────────────────────┐         ┌──────────────────────────────────────────────┐
 │ PHASE 0 — FOUNDATION  (once per product) │         │ RECURRING PIPELINE  (per requirement)         │
 │                                          │  gate   │                                               │
 │  Requirements + constraints  ──▶ Canon   │ ──────▶ │  Intake → Architecture → Build → Sec ║ QA →    │
 │  (knowledge-base/) ──▶ approve            │ unlocks │  Final → Stakeholder gate → Deploy/Monitor    │
 └─────────────────────────────────────────┘         └──────────────────────────────────────────────┘
```

- **Phase 0 — Foundation** runs once per product (and again only on an explicit foundation
  amendment). It converts raw requirements and constraints into the **Product Canon**
  (`knowledge-base/`) and gates the rest of the OS behind an approval sentinel. Detailed in
  [10 — Adoption & Product Canon](10-adoption-and-product-canon.md).
- **The recurring pipeline** delivers each requirement to production, mostly autonomously, touching
  the stakeholder at a small fixed set of points (§6).

**The pipeline is gated on the Foundation.** No intake proceeds until the approval sentinel exists;
the gate is enforced by a hook, not by prose.

---

## 2. The pipeline stages

Per requirement, after the Foundation is approved. Pattern for every stage: **plan → execute →
self-review → verify → hand off** to the next stage.

| # | Stage | Owner | Input → Output | Gate / VETO | Stakeholder? |
|---|---|---|---|---|---|
| **1** | **Intake** | Engineering Advisor (+ 0–2 personas) | Requirement → framing, lane, concerns | Foundation sentinel must exist | **Files the requirement** |
| **2** | **Architecture** | Architect | Framing → **binding plan** (slices, paths, verification) | The plan is the contract | — |
| **3** | **Build** | Builder(s), in parallel tracks | Plan → vertically-sliced code + journal; trace-instrumented | Self-review + verify-before-done | — |
| **4** | **Security review** | Security Reviewer | Code → findings | **VETO** on critical/high, compliance gap, missing traceability | — |
| **5** | **QA** | QA Engineer | Code → verified evidence | **VETO** on missing real-env verification, contract/parity gaps, invalid tests | — |
| **6** | **Final review** | Engineering Advisor | Reconciled change → go/no-go | **VETO**; verifies plan adherence + commit-boundary discipline | — |
| **7** | **Stakeholder gate** | Stakeholder (human) | Reviewed change → decision | Approve / Reject | **Approve or Reject** |
| **8** | **Deploy + monitor + rollback** | Platform / SRE | Approved change → release | Bake window + auto-rollback; release notes | — |

**Stages 4 and 5 run in parallel** (security ∥ QA) — they are independent and both required.

**Routing on a VETO.** Any VETO (4, 5, 6) routes work **back** — to Build, or to Architecture if the
plan itself is wrong — never overridden silently. After a fix, re-review is **delta-scoped**
([06 — Delta re-review](06-quality-gates-and-metrics.md)) to avoid re-paying for unchanged surfaces.

---

## 3. Lanes — scaling rigor to risk

Not every change deserves the same path. A copy edit and a change to an authentication boundary must
not travel the same pipeline. The **lane** is assigned at intake and re-checked against the actual
diff before QA (see §4, the post-build reclassification gate).

| Lane | When | Stages run | Personas | Extra |
|---|---|---|---|---|
| **lean** *(opt-in)* | Zero trigger surfaces; one disciplined builder session that builds **and** self-gates against the review checklists. | Build (self-gating) | 0 | Escalates to full pipeline if any trigger surface is discovered mid-build. |
| **express** | Zero trigger surfaces **and** purely trivial (copy, docs, config, styling, zero-behavior refactor). | Intake, Build, QA | 0 | Always runs the test-validity scan even here. |
| **standard** | Zero trigger surfaces, not trivial. | Intake, Architecture, Build, Security, QA, Final | 0–1 | — |
| **high-stakes** | **≥1 trigger surface touched.** | All stages | 2 | Mutation tests required. |

**The conservative rule:** on any doubt between two lanes, pick the **higher** one. A wrong cheap
lane ships unreviewed risk; a wrong expensive lane only costs time.

**Trigger surfaces** (product-defined in the Foundation, but the OS supplies the categories — any
change touching one forces high-stakes):

- **Compliance / regulatory** boundary (the product's regime).
- **Multi-tenancy / isolation** boundary (the tenant/data-isolation primitive at any layer).
- **Authentication / authorization** boundary.
- **Money / financial calculation** paths.
- **Shared contract** parity (a calculation or schema defined in more than one runtime/language).
- **System-of-record / audit-log** writes.
- **Outbound side-effects** to external systems or users.

---

## 4. The post-build reclassification gate (closing the lane-jump hole)

The lane is chosen at intake **from the requirement text, before any code exists**. A "rename a
label" can grow at build time into a change that touches an authorization boundary — and would
otherwise ship through a cheap lane with no security review.

So at the **build → QA** boundary, the OS **re-classifies the lane against the actual staged diff**:

- If the diff touched a trigger surface the intake text missed, the cheap lane is **voided** and the
  change **restarts in high-stakes** (reinstating architecture + security + final review).
- The **test-validity scan runs on every lane**, even express — a green test produced under bypassed
  protection cannot ride a "trivial" lane past the only gate.

This makes the lane a property of *what changed*, not merely *what was asked*.

---

## 5. Plan-binding and research discipline

- **The plan is binding.** Stage 1 frames; Stage 2 produces the binding plan; Stages 3–8 **execute
  against it**. A required deviation triggers a **plan-amendment loop**: the builder raises it to the
  Architect, the Architect revises the plan, build resumes. No freelancing (Iron Law 2).
- **Research is a planning input, never a build-time excuse.** Roles may research external facts
  (web, docs, prior art) during **planning** phases — Foundation, intake, architecture, and the
  amendment loop. During **build**, a newly-discovered fact that would change the design does not
  authorize ad-hoc deviation; it routes back through the amendment loop. This keeps the plan the
  single source of truth for what gets built.

---

## 6. Stakeholder touchpoints — the entire surface area

The organization runs autonomously *between* these points. There are no status pings, no mid-build
check-ins, no per-change reviews.

| When | What | Frequency |
|---|---|---|
| Foundation kickoff | Supplies requirements + constraints | Once per product (or amendment) |
| Foundation gate | Approves the Canon | Once per product (or amendment) |
| Intake | Files a requirement | Per requirement |
| Mid-pipeline escalation | Responds to a rubric-gated escalation | Rare |
| Post-final commit | Runs the mechanical commit the Advisor provides | Per requirement |
| Deploy gate | Approve / Reject | Per requirement |

**Nothing else.** The stakeholder is named in the Foundation and touched only here.

---

## 7. Per-requirement state

Each requirement carries a working set in the consuming repo's `.engineering-os/requirements/<id>/`
([01 §Memory](01-organization-structure.md)): the intake framing, the binding plan, the build
journal, and the decision log (stage decisions, VETOs, amendments, and outcomes). The pipeline's
**routing cursor** (current stage, outstanding work, spawn count, last route) lives in `state/` so a
run is resumable and a VETO bounce is fully reconstructable.

---

## 8. Safety bounds (loop protection without footguns)

The pipeline caps total work per requirement, **lane-aware** — a legitimate high-stakes feature with
parallel builder tracks, two reviewers, and a couple of bounces legitimately does more work than a
trivial change. At the cap, the OS does **not** hard-stop; it **pauses and surfaces the full history**
(stage, outstanding, spawns, last route) to the stakeholder so a runaway loop is *distinguishable*
from legitimate large work. The stakeholder confirms a one-time bump (resume) or kills it. State stays
consistent for resume either way.

---

## 9. The lifecycle as a whole

```
 Requirement
     │
     ▼
 ① INTAKE ─ lane? ─┬─ lean ───────────────▶ Build (self-gating) ──┐
                   ├─ express ─────────────▶ Build ─▶ QA ──────────┤
                   ├─ standard ─▶ ② ARCH ─▶ ③ Build ─▶ ④Sec ║ ⑤QA ─┤
                   └─ high-stakes ▶ ② ARCH ▶ ③ Build ▶ ④Sec ║ ⑤QA ─┤
                                                                   │
                              (post-build reclassification gate) ──┘
                                            │
                                  any VETO ─┴─▶ back to Build / Arch (delta re-review)
                                            │
                                            ▼
                                   ⑥ FINAL REVIEW (VETO)
                                            │ PASS
                                            ▼
                                   ⑦ STAKEHOLDER GATE ── reject ─▶ back to intake
                                            │ approve
                                            ▼
                                   ⑧ DEPLOY ─▶ bake window ─▶ auto-rollback on breach
                                            │
                                            ▼
                                   Release notes · outcome recorded · memory updated
```

This single lifecycle covers the full set of engineering activities the OS must perform — analyze,
design, specify, build, test, deploy, monitor, troubleshoot, scale, refactor, maintain, and govern —
because each is the responsibility of a named stage or a cross-cutting function ([01](01-organization-structure.md)),
operating against the standards in [05](05-engineering-standards.md) and the gates in
[06](06-quality-gates-and-metrics.md).
