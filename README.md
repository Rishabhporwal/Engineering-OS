# Engineering OS

A **universal, domain-agnostic AI engineering organization**, delivered as a Claude Code plugin. You
give it a requirement; a fixed roster of engineering roles takes it from intake to production —
designed, built, security-reviewed, QA'd, deployed, and monitored — producing audited, journaled work
every time, **on any stack, for any product**.

The OS itself carries **no** product, business, or domain knowledge. Everything domain-specific (what
you're building, the stack, the compliance regime, the invariants, the metrics that matter) is supplied
**once per adoption** through a **Foundation phase** that produces the **Product Canon**. After that,
you just file requirements.

> **The full framework is documented in [`engineering-os-blueprint/`](engineering-os-blueprint/)** —
> first principles, org structure, roles, the delivery lifecycle, standards, quality gates, operations,
> governance, the stack-agnostic reference architecture, the adoption guide, and the runtime/cost
> doctrine. Read that to understand the OS as an organization; read this to install and run it.

---

## The two layers (why it's reusable)

| Layer | What it is | Where it lives |
|---|---|---|
| **The Engineering OS** (this plugin) | The organization that *builds* software — roles, pipeline, standards, gates, governance. Stable, reusable, domain-free. | the plugin (`~/.claude/plugins/.../engineering-os/`) |
| **The Product Canon** (per adoption) | The *thing being built* — requirements, chosen stack, architecture, compliance regime, invariants, the asset that compounds. | your repo's `.engineering-os/knowledge-base/` |

A fully-worked example instantiation lives under [`examples/`](examples/) — a complete Product Canon
and product-specific skill set for one real, demanding product — so you can see what "filled in" looks
like.

---

## Distribution & memory model

- **Installed, not cloned.** The plugin lives in `~/.claude/plugins/.../engineering-os/`. You install
  it; you don't clone its source into your project. Everything it ships (agents, skills, canon
  templates, docs, prompts, templates, schemas, workflows, hooks) resolves via `${CLAUDE_PLUGIN_ROOT}`.
- **Shared memory lives in YOUR repo.** `/engineering-os:eos-init` scaffolds `.engineering-os/` into
  your product repo (committed to git, resolved via `${CLAUDE_PROJECT_DIR}`). Journals, the audit log,
  state, and per-run artifacts accrue there; every teammate inherits the full history on `git pull`.
  **Memory is the moat.**

---

## The team — 11 roles

10 roles + a runtime stress-test persona generator. Human/team names are optional and assigned per
adoption in `team-roster.md`. **VETO = can block the pipeline.** Full specs in
[`engineering-os-blueprint/02-engineering-roles.md`](engineering-os-blueprint/02-engineering-roles.md).

| Role | Agent file | Tier | Stage(s) | Authority |
|---|---|---|---|---|
| **Engineering Advisor** | `cto-advisor` / `final-reviewer` | standard (intake) / deep (final) | 1 + 6 | **VETO** at final review; sole `/escalate` |
| Stress-test Persona | `dynamic-persona-generator` | mechanical/standard | 1 | spawns **0–2** stress-test personas |
| **Architect** | `architect` | deep | 2 | the binding plan; contract/boundary decisions |
| **Backend Engineer** | `backend-developer` | standard | 3 | services, data, integration, idempotency |
| **Frontend/Web Engineer** | `frontend-web-developer` | standard | 3 | web UI, a11y, web perf |
| **Mobile Engineer** | `mobile-developer` | standard | 3 | mobile app, offline, store delivery |
| **AI/ML Engineer** | `intelligence-engineer` | standard | 3 | model integration, evals, agentic systems, data |
| **Security Reviewer** | `security-reviewer` | standard/deep | 4 | **VETO** on critical/high + compliance + traceability |
| **QA Engineer** | `qa-agent` | standard | 5 | **VETO** on missing/invalid verification |
| **Platform/SRE** | `platform-devops` | standard | 8 | deploy, monitor, auto-rollback |
| **Delivery Coordinator** | `product-manager` | mechanical/standard | cross-cuts | release notes, tracker sync, escalation queue |
| **Stakeholder** (human) | — | — | 7 | the only approval gate |

---

## The pipeline

```
Requirement ─▶ ① Intake ─▶ ② Architecture ─▶ ③ Build ─▶ ④ Security ║ ⑤ QA ─▶ ⑥ Final review
                                              (vertical    (VETO)     (VETO)        (VETO)
                                               slices)                                 │
   Stakeholder gate ◀── ⑦ Approve/Reject ◀─────────────────────────────────────────────┘
        │
        ▼
   ⑧ Deploy ─▶ monitor (bake window) ─▶ auto-rollback on breach ─▶ release notes
```

**Lanes scale rigor to risk** — a copy change and a change to an auth boundary do not travel the same
path (lean / express / standard / high-stakes). A **post-build reclassification gate** re-scans the
actual diff so a change that grows into a trigger surface mid-build is upgraded automatically. See
[`engineering-os-blueprint/03-delivery-lifecycle.md`](engineering-os-blueprint/03-delivery-lifecycle.md).

---

## Setup (per teammate, one-time)

### 1. Add the marketplace and install the plugin

```
/plugin marketplace add Rishabhporwal/Engineering-OS
/plugin install engineering-os
```

### 2. Open your product repo in Claude Code

### 3. (First time per repo) Run the Foundation

```
/engineering-os:eos-init          # scaffolds .engineering-os/ + the Product Canon template
```

Then run the **Foundation phase** (supply requirements + technical constraints; the OS produces and
you approve the Product Canon). Details:
[`engineering-os-blueprint/10-adoption-and-product-canon.md`](engineering-os-blueprint/10-adoption-and-product-canon.md).
Commit `.engineering-os/` and push — every teammate who pulls inherits the shared memory baseline.

If you cloned a repo that already has `.engineering-os/`, **skip init** — it's already wired up.

---

## Daily use

All commands are invokable via the plugin namespace:

```
/engineering-os:requirement Add password reset via email magic link
/engineering-os:status                          # what's in flight
/engineering-os:recall feat-password-reset      # full history of one feature
/engineering-os:recall-similar re-engage idle users   # semantic search across all memory
/engineering-os:watch                           # live stream of what every agent is doing
/engineering-os:monitor http://localhost:3000   # live-watch the running app; auto-open fixes for errors
/engineering-os:dashboard                       # visual board of all work by stage
/engineering-os:qa-browser                      # real-Chromium QA: walk flows, capture errors, gen regression test
/engineering-os:design-review http://localhost:3000   # screenshot + scored visual audit
/engineering-os:approve feat-password-reset     # Stakeholder gate (Stage 7)
```

---

## What makes it an *operating system*, not a process doc

1. **Roles are agents, not titles** — each has a scope, decision rights, inputs, outputs, and a gate.
2. **The pipeline is deterministic control-flow** — declared in [`pipeline/pipeline.yaml`](pipeline/pipeline.yaml), not re-improvised per task.
3. **Gates carry VETO, and a VETO routes back** — never silently overridden.
4. **Memory compounds** — every decision, review, and outcome is recorded in your repo.
5. **The OS applies its own discipline to itself** — cost, verification, and observability doctrine bind its own operation ([`engineering-os-blueprint/11-runtime-and-cost-doctrine.md`](engineering-os-blueprint/11-runtime-and-cost-doctrine.md)).

---

## Repository layout

| Path | What |
|---|---|
| `engineering-os-blueprint/` | The framework, as readable docs (start here). |
| `agents/` | The 12 role agent files. |
| `skills/` | The engineering-discipline + command skill library. |
| `canon/` | The **Product Canon template** (filled per adoption into `.engineering-os/knowledge-base/`). |
| `pipeline/` | The deterministic control-flow (lanes, stages, routing, delta-review, caching, telemetry). |
| `workflows/` | State machine + requirement-to-release + approval flow. |
| `prompts/` | The shared system prompt + challenge framework. |
| `hooks/` | Session/secret/handoff/usage hooks. |
| `tools/` | Pipeline doctor, lane classifier, gate check, validity check, memory search, dashboard, etc. |
| `schemas/` · `templates/` | Artifact schemas and the per-stage report templates. |
| `examples/` | A fully-worked example instantiation (one product's Canon + product skills). |
