# Engineering OS — Onboarding

> The complete picture of the AI engineering team. If you're new, read this top to bottom once. Current version: **v2.0.0**. This is a **universal, domain-agnostic AI engineering organization**, delivered as a Claude Code plugin: you file a requirement and a fixed roster of engineering roles takes it from intake to production — on any stack, for any product. The OS itself carries **no** product, business, or domain knowledge; everything domain-specific is supplied **once per adoption** through a **Foundation phase** that produces the **Product Canon** (in your repo's `.engineering-os/knowledge-base/`). The full framework is documented in [`engineering-os-blueprint/`](engineering-os-blueprint/); the condensed primers agents read live in `docs/business-context.md` + `docs/technical-context.md` (per adoption). **Product engineers: jump to §12 — "Get the most from the team."**

---

## 1. What it is
A **universal AI engineering organization delivered as a Claude Code plugin**. You give it a requirement; it runs that requirement through a staged pipeline — intake → architecture → parallel build → security → QA → final review → Stakeholder approval → deploy — producing production-grade, audited, journaled work every time. It exists so a team can ship correct, secure, observable, reliable software without standing up a large engineering org first. The OS is **domain-free**; the source of truth for *what* you're building is the **Product Canon**, grounded once in the Foundation phase and condensed for agents in `docs/business-context.md`. See [`engineering-os-blueprint/00-first-principles.md`](engineering-os-blueprint/00-first-principles.md).

## 2. Distribution & memory model
- **Installed, not cloned.** The plugin lives in `~/.claude/plugins/.../engineering-os/`. You install it; you don't clone its source into your project. Everything it ships (agents, skills, canon templates, docs, prompts, templates, schemas, workflows, hooks) resolves via `${CLAUDE_PLUGIN_ROOT}`.
- **Shared memory lives in YOUR repo.** `/engineering-os:eos-init` scaffolds `.engineering-os/` into your product repo (committed to git, resolved via `${CLAUDE_PROJECT_DIR}`). Journals, the audit log, state, and per-run artifacts accrue there; every teammate inherits the full history on `git pull`. **Memory is the moat.**

## 3. The team — 11 roles
10 roles + a runtime stress-test persona generator. Human/team names are optional and assigned per adoption in `.engineering-os/team-roster.md`. VETO = can block the pipeline.

| Role | Agent file | Tier | Stage(s) | Authority |
|---|---|---|---|---|
| **Engineering Advisor** | `cto-advisor` (intake) / `final-reviewer` (final) | standard (intake) / deep (final) | 1 + 6 | **VETO** at final review; sole `/escalate` |
| Stress-test Persona | `dynamic-persona-generator` | mechanical/standard | 1 | spawns **0–2** stress-test personas by complexity |
| **Architect** | `architect` | deep | 2 | the binding plan; contract/boundary decisions |
| **Backend Engineer** | `backend-developer` | standard | 3 | services, data, integration, idempotency within plan |
| **Frontend/Web Engineer** | `frontend-web-developer` | standard | 3 | web UI, accessibility, web perf within plan |
| **Mobile Engineer** | `mobile-developer` | standard | 3 | mobile app, offline, store delivery within plan |
| **AI/ML Engineer** | `intelligence-engineer` | standard | 3 | model integration, evals, agentic systems, data |
| **Security Reviewer** | `security-reviewer` | standard/deep | 4 | **VETO** on critical/high + compliance + traceability |
| **QA Engineer** | `qa-agent` | standard | 5 | **VETO** on missing/invalid verification |
| **Platform/SRE** | `platform-devops` | standard | 8 | deploy, monitor, auto-rollback |
| **Delivery Coordinator** | `product-manager` | mechanical/standard | cross-cuts (not a stage) | release notes, tracker sync, escalation queue |
| **Stakeholder** (human) | — | — | 7 | the only approval gate |

## 4. The pipeline
```
Stakeholder /requirement
  → Stage 1  Engineering Advisor: intake + 0–2 personas; challenge/decompose weak reqs (ADVANCE / CHALLENGE-BACK / KILL)
  → Stage 2  Architect: the binding plan — contracts, boundaries, data model, effort tier, test strategy
  → Stage 3  Backend ∥ Frontend/Web ∥ Mobile ∥ AI/ML: parallel build in vertical slices (stage code, never commit)
  → Stage 4  Security Reviewer: security + compliance-regime review (VETO)
  → Stage 5  QA Engineer: QA — real-network smoke, metric parity, gates (VETO)
  → Stage 6  Engineering Advisor: final review + over-engineering audit + retro (VETO)
  → Stage 7  Stakeholder: /approve or /reject  ← the human gate
  → Stage 8  Platform/SRE: stage product code, commit .engineering-os, CI → deploy → bake-window monitor + auto-rollback
```
Each stage **plans → executes → self-reviews → verifies → returns a `HANDOFF` block**; the **top-level `/requirement` orchestrator** reads it + `state/active.json` and spawns the next stage (subagents can't spawn subagents on this platform — orchestration lives at the top level; see [pipeline/orchestrator.md](pipeline/orchestrator.md)). The Stakeholder intervenes only at Stage 7 and at the final push.

## 5. The skill library
The library has two kinds of skill. **Engineering-discipline + domain skills** are model-auto-loaded per each agent's owned-skill list (see [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md)) and read on demand when the task surface matches a skill's trigger. **Command-skills** carry `disable-model-invocation: true` and run only when a human types `/engineering-os:<name>`.

- **Architecture/discipline:** architecture-patterns, domain-driven-design, region-and-locale, api-discipline, tech-stack-evaluation, engineering-discipline, code-review, writing-plans, verification-before-completion, systematic-debugging, subagent-orchestration, finishing-a-development-branch, cost-routing-paradigms
- **Backend/data:** backend-fastify-trpc-grpc, grpc-buf, python-services, data-layer, clickhouse-olap, event-driven-kafka, idempotency-handling, caching-strategy, integration-connectors, mcp-protocol, turborepo, multi-tenancy-isolation, metric-engine
- **Frontend/mobile:** frontend-web, mobile-surface, web-performance, kpi-dashboard-design
- **AI:** claude-api, llm-gateway, llm-evals, agentic-safety
- **Security/compliance:** security-baseline, auth-and-access, oauth-implementation, compliance-engine, compliance-attestation
- **Ops/testing/governance:** devops-aws, observability, operational-readiness, testing-tdd, task-tracker-integration, version-upgrade-policy, incident-response, progressive-delivery, data-quality, experimentation-holdouts, accessibility
- **Command-skills:** requirement, status, recall, recall-similar, handoff, approve, reject, deploy, rollback, persona, invoke-skill, eos-init, propose-rule, adopt-rule, reject-rule, reindex, qa-browser, design-review, test-pipeline, resume, new-skill, team-digest, watch, monitor, dashboard

> Skills documenting a specific technology (e.g. `backend-fastify-trpc-grpc`, `python-services`, `clickhouse-olap`) are **reference implementations** — one concrete binding of a seam. The OS is stack-agnostic; your product's `STACK.md` may bind that seam to different technology. The *patterns* transfer, not the vendor. See [`engineering-os-blueprint/09-reference-architecture.md`](engineering-os-blueprint/09-reference-architecture.md).

## 6. Durable rules (the non-negotiables, in every agent's system prompt)
1. **Commit discipline** — agents stage product code (`git add`, explicit paths, never `-A`); the **Stakeholder** commits/pushes product code; agents commit only the `.engineering-os/` audit trail as `chore(eos):`; **never** rewrite git history.
2. **No over-engineering** — build the minimum that solves the requirement; the STOP-signal table; the Engineering Advisor runs an over-engineering audit at Stage 6.
3. **Persona calibration** — 0/1/2 stress-test personas by complexity, capped at 2 (never 3+).
4. **Plan-first + self-review + explicit handoff** — every agent plans before acting, self-reviews against its DoD, and **RETURNS a `HANDOFF` block**; the top-level `/requirement` orchestrator reads it + `state/active.json` and spawns the next stage (subagents can't spawn subagents on this platform).
5. **Cheapest sufficient effort** — deterministic logic ≫ statistical/ML ≫ small model ≫ large model; reach up a tier only when the one below can't meet the bar, and record why.
6. **Single-Primitive Rule** — every cross-cutting concern built once, consumed N times (abstract only after the 3rd caller).
7. **Tenant isolation + compliance P0** — the product's isolation key (declared in the Canon, e.g. `tenant_id`) is carried on every row/event/cache-key/log and enforced at **every** layer; the product's compliance regime — whatever `COMPLIANCE.md` declares (data protection, residency, retention, consent, channel rules) — has **zero violations** (Security VETO).
8. **Verification before completion** — no "done" claim without fresh captured command output; a check that *cannot* run is a blocker, never a SKIP; verification must be able to fail.
9. **UTC timestamp discipline**; **append-only journals**; money = integer **minor units** + a `currency_code`.

## 7. Canon, primers, gates & hooks
- **Product Canon (source of truth):** the per-adoption `.engineering-os/knowledge-base/` slots — `STACK.md`, `HLD/LLD`, `INVARIANTS.md`, `TRIGGER-SURFACES.md`, `COMPLIANCE.md`, `METRICS.md`, `PLAYBOOK-*.md`, `ESCALATION-RUBRIC.md`, `THE-MOAT.md`. The OS ships a **canon template** under `canon/` (index: `canon/INDEX.md`).
- **Primers (what agents read — condensed):** `docs/business-context.md`, `docs/technical-context.md` (produced per adoption).
- **Quality gates:** the gate at every stage — pre-flight dependency check, Stage-4 fast-pass rules, QA re-runs skipped gates, the Engineering Advisor re-runs QA's gates at Stage 6. See [`engineering-os-blueprint/06-quality-gates-and-metrics.md`](engineering-os-blueprint/06-quality-gates-and-metrics.md).
- **Hooks:** `on-session-start` (rehydrate state), `on-post-tool-use` (journal append, skips read-only Bash), `on-pre-handoff` (handoff-event logger — observability only; enforcement lives in deterministic tools), `on-secret-guard` (blocks any write containing a live secret before disk), `on-subagent-usage` (records every spawn return for telemetry/heartbeat).

## 8. Self-improvement substrate
- Stage 6 writes a **retro** → distilled into the append-only **`lessons-learned.md`** registry → **the Engineering Advisor reads relevant lessons at every Stage 1 intake** (a compounding learning loop).
- **Rule governance:** any agent can `/propose-rule`; the Stakeholder `/adopt-rule` or `/reject-rule` (Stakeholder-only). Adopted rules become durable rules, indexed in `.engineering-os/durable-rules/INDEX.md` and read by every agent at session start.
- `pending-stakeholder-attention.md` surfaces items needing the Stakeholder.

## 9. What the team builds — the product (per adoption)
> The OS never assumes what you're building. It assumes only that you are building **software that must be correct, secure, observable, reliable, and maintainable** — and supplies the organization, process, and discipline to do that well. The *thing being built* is defined once, per adoption, in the **Product Canon**.

A fully-worked example instantiation lives under [`examples/brain-instantiation/`](examples/) — a complete Product Canon and product-specific skill set for one real, demanding product — so you can see what "filled in" looks like. Your product's own Canon in `.engineering-os/knowledge-base/` **wins** over any example.

The Foundation phase fixes, per product:
- **The stack:** `STACK.md` binds each architectural seam (services, data store(s), async backbone, frontend, mobile, model gateway, region/locale, infra) to concrete technology. The OS is stack-agnostic; the reference architecture in [`engineering-os-blueprint/09-reference-architecture.md`](engineering-os-blueprint/09-reference-architecture.md) shows one cloud-native binding.
- **Day-one invariants** (`INVARIANTS.md`): typically cheapest-sufficient-effort routing, the Single-Primitive Rule, the tenant-isolation key enforced at every layer, integer minor-units money, the system-of-record audit log (where required), the region/locale seam, a single-source metric registry with cross-runtime parity, defined sync/async contracts, idempotency, and any product-specific surfaces.

## 10. Using it

> ⚠️ **Plugin changes only take effect after you RESTART your Claude Code session** (the running session holds the old plugin in memory). After any `/plugin update`, restart — then `/status` shows the loaded version. This is the #1 silent gotcha.

```
/plugin marketplace add Rishabhporwal/Engineering-OS
/plugin install engineering-os                        # then RESTART the session
/engineering-os:eos-init                              # one-time scaffold of .engineering-os/ + the Canon template
```
**Happy path:** `/requirement <what to build>` (add `--lean` to A/B the one-session lane) · `/status` (what's in flight) · `/watch [req-id]` (live play-by-play + a STALE banner if the pipeline went dark) · `/dashboard` (agents/bugs/features/tokens & cost — snapshot, re-run to refresh) · `/approve <req-id>` / `/reject <req-id> <reason>` (Stakeholder gate — `/approve` shows a cost/risk **decision card**).

**When stuck** (the commands you need most under stress): `/resume <req-id>` (recover an interrupted pipeline, no lost work) · `/decide <req-id> <ruling>` (resolve a HARD gate — e.g. a compliance-basis block — that `/resume` can't clear) · `/handoff <req-id> <stage>` (manual move; VETOs still apply) · `/rollback <req-id>` · `/test-pipeline` (orchestration health).

**Memory + review:** `/recall <feat-slug>` (exact) · `/recall-similar <description>` (semantic) · `/team-digest` (cross-engineer overview).

## 11. Repo layout (the plugin)
```
engineering-os-blueprint/  the framework, as readable docs (start here)
agents/      12 subagent definitions (the 11 roles; cto-advisor=standard intake, final-reviewer=deep final)
skills/      the engineering-discipline + command skill library  +  tools/ (uv scripts: memory, browse, pipeline_doctor, team_digest, paradigm_check, dashboard)
canon/       the Product Canon template (filled per adoption into .engineering-os/knowledge-base/); index: canon/INDEX.md
pipeline/    the deterministic control-flow (lanes, stages, routing, delta-review, caching, telemetry)
prompts/     system-prompt, anti-blind-agreement, challenge-framework
docs/        operating manual, primers, matrix, quality-gates, role-empowerment, …
templates/   per-stage artifact templates    schemas/  JSON schemas
workflows/   requirement-to-release / state-machine / approval-flow (YAML)
hooks/       session-start, post-tool-use, pre-handoff, secret-guard, subagent-usage
examples/    a fully-worked example instantiation (one product's Canon + product skills)
.claude-plugin/  plugin.json, marketplace.json
```

## 12. Get the most from the team (product engineers)

You don't write the features — you direct the team and let it run. Here's how to extract maximum value, especially with several engineers on one repo.

### Your daily loop
1. **Start with awareness.** `git pull`, then `/team-digest` — see what every engineer has built, what's in flight, and the challenges they hit. Before starting anything, `/recall-similar "<your idea>"` — the team may have already solved it (reuse the decision; don't re-derive).
2. **Submit a requirement, not a spec.** `/requirement <plain-English ask>`. The team handles intake → architecture → build → security → QA → review autonomously. You're the Stakeholder gate at Stage 7 only.
3. **Let the lane do the work.** The Engineering Advisor auto-classifies risk; lanes scale rigor to risk:
   - **Lean / Express** (copy/config/docs/trivial, zero trigger surfaces) — skips Architect/Security/Final-review; minimal agent touches.
   - **Standard** — full pipeline, lean, Security ∥ QA in parallel.
   - **High-stakes** (auth/money/multi-tenancy/PII/connectors/schema/compliance) — full rigor, 2 personas, mandatory Security VETO, mutation tests.
   You don't pick the lane; you can trust the conservative tie-break (ambiguity routes *up*). A **post-build reclassification gate** re-scans the actual diff, so a change that grows into a trigger surface mid-build is upgraded automatically.
4. **Approve or reject.** Read the Stage-6 review, then `/approve <req-id>` or `/reject <req-id> <reason>`.

### Powers worth knowing
- **Memory is shared and semantic.** Every decision/journal/challenge from every engineer is git-synced and searchable by *meaning* via `/recall-similar` (it self-refreshes — always current after a pull). Agents use it automatically in their pre-flight, so they reuse the team's prior work without you asking.
- **Real-browser + visual QA.** Web changes get `/qa-browser` (walks real flows, catches console/network errors, generates a Playwright regression spec) and `/design-review` (0–10 scored visual audit) — the highest-traffic surfaces have the highest bar.
- **Proactive workers.** Schedule background workers to scan the repo between requirements and file findings (test-gap, canon-drift, compliance-drift).
- **Safety rails.** The secret guard blocks any write containing a live secret before disk; the cost-routing gate keeps spend discipline; the tenant-isolation key + the product's compliance regime are enforced at every layer.
- **Recover & validate.** `/resume <req-id>` picks up an interrupted pipeline with no lost work; `/test-pipeline` validates the orchestration is healthy; `/new-skill` scaffolds a new skill when a real gap surfaces.

### Multi-engineer guarantee
Because `.engineering-os/` is committed and pulled, **the team knows about every feature and challenge across all engineers** — your agents see every bounce and decision the same as your own. `/team-digest` is the overview; `/recall-similar` is the deep pull. Two engineers won't unknowingly collide or repeat a solved problem.

> The mental model: **you bring intent and judgment; the team brings memory, knowledge, skills, and execution.** The more the team runs, the smarter its shared memory gets — for everyone.

---
*See [`engineering-os-blueprint/`](engineering-os-blueprint/) for the full framework, [pipeline/orchestrator.md](pipeline/orchestrator.md) for how the team runs end-to-end, and [`engineering-os-blueprint/03-delivery-lifecycle.md`](engineering-os-blueprint/03-delivery-lifecycle.md) for the stage-by-stage flow.*
</content>
</invoke>
