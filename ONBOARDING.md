# Brain Engineering OS — Onboarding

> The complete picture of the AI engineering team. If you're new, read this top to bottom once. Current version: **v0.17.0**. The team builds **Brain** — the AI-native commerce operating system for DTC brands, **India-first** at launch with **UAE/GCC** sequenced for Phase 4. The full canon is `canon/business-requirements.md` (BRD) + `canon/technical-requirements.md` + `canon/TECH/00–17` (TRD/knowledge-base), condensed for agents in `docs/business-context.md` + `docs/technical-context.md`. New since 0.7.1: risk-based lanes, semantic memory, parallel review, background workers, paradigm gate, browser/visual QA, the `/careful` guard, the pipeline doctor, 6 new domain skills, cross-engineer `/team-digest`, the **top-level orchestrator** (one `/requirement` runs the team end-to-end), **live activity logs** (`/watch`), **live monitoring mode** (`/monitor`), an **interactive PM-grade dashboard** (`/dashboard` — agent performance, bugs, features, tokens & cost), and **token-usage logging**. **Product engineers: jump to §12 — "Get the most from the team."**

---

## 1. What it is
An **AI engineering team delivered as a Claude Code plugin**. You give it a requirement; it runs that requirement through an 8-stage pipeline — intake → architecture → parallel build → security → QA → final review → Founder approval → deploy — producing production-grade, audited, journaled work every time. It exists so **Brain** — the AI-native commerce OS for DTC brands (India-first, UAE/GCC sequenced) — can ship software without hiring a large engineering team early. The product/domain is the source of truth in `canon/business-requirements.md` (condensed in `docs/business-context.md`).

## 2. Distribution & memory model
- **Installed, not cloned.** The plugin lives in `~/.claude/plugins/brain-engineering-os/`. You install it; you don't clone its source into your project. Everything it ships (agents, skills, canon, docs, prompts, templates, schemas, workflows, hooks) resolves via `${CLAUDE_PLUGIN_ROOT}`.
- **Shared memory lives in YOUR repo.** `/brain-engineering-os:eos-init` scaffolds `.engineering-os/` into the Brain product repo (committed to git, resolved via `${CLAUDE_PROJECT_DIR}`). Journals, decision log, state, and per-run artifacts accrue there; every teammate inherits the full history on `git pull`. **Memory is the moat.**

## 3. The team — 11 agents
10 named roles + a runtime persona generator. VETO = can block the pipeline.

| Persona | Role | Model | Stage(s) | Authority |
|---|---|---|---|---|
| **Rohan** | CTO Advisor (Founder's shadow) | opus | 1 (intake) + 6 (final review) | **VETO** at Stage 6 |
| (runtime) | Dynamic Persona Generator | sonnet | 1 | spawns **0–2** stress-test personas by complexity |
| **Aryan** | Architect | opus | 2 | API/schema/paradigm/service-boundary decisions |
| **Vikram** | Backend Developer (Node/Fastify) | sonnet | 3 | implementation within plan |
| **Ananya** | Frontend Web (Next.js) | sonnet | 3 | component/state/UI within plan |
| **Karan** | Mobile (React Native + Expo) | sonnet | 3 | the Morning Brief — the primary product surface |
| **Maya** | Intelligence Engineer (Python/AI) | sonnet | 3 | the 15 AICMO/AICOO/AICFO agents, RAG, cost-routing |
| **Shreya** | Security Reviewer | opus | 4 | **VETO** on CRITICAL/HIGH + compliance (DPDP/PDPL/DLT/NCPR) |
| **Tanvi** | QA Agent | sonnet | 5 | **VETO** on missing verification |
| **Jatin** | Platform/DevOps | sonnet | 8 | deploy, infra, rollback |
| **Priya** | Product Manager | sonnet | cross-cuts (not a stage) | release notes, tracker sync |
| **Rishabh** | Founder/CTO (human) | — | 7 | the only approval gate |

## 4. The 8-stage pipeline
```
Founder /requirement
  → Stage 1  Rohan: intake + 0–2 personas; challenge/decompose weak reqs (ADVANCE / CHALLENGE-BACK / KILL)
  → Stage 2  Aryan: technical plan, paradigm, schema, DDD structure, test strategy
  → Stage 3  Vikram ∥ Ananya ∥ Karan ∥ Maya: parallel build (stage code, never commit)
  → Stage 4  Shreya: security + India-compliance review (VETO)
  → Stage 5  Tanvi: QA — real-network smoke, parity, gates (VETO)
  → Stage 6  Rohan: final review + over-engineering audit + retro (VETO)
  → Stage 7  Rishabh: /approve or /reject  ← the human gate
  → Stage 8  Jatin: stage product code, commit .engineering-os, CI → ArgoCD → 48h monitor
```
Each stage **plans → executes → self-reviews → verifies → returns a `HANDOFF` block**; the **top-level `/requirement` orchestrator** reads it + `state/active.json` and spawns the next stage (subagents can't spawn subagents on this platform — orchestration lives at the top level; see [docs/orchestration.md](docs/orchestration.md)). The Founder intervenes only at Stage 7 and at the final push.

## 5. The skill library — 85 folders (57 domain + 28 command)
**Domain skills** are model-auto-loaded per each agent's owned-skill list (see [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md)). **Command-skills** carry `disable-model-invocation: true` and run only when a human types `/brain-engineering-os:<name>`.

- **Architecture/discipline:** architecture-patterns, domain-driven-design, region-adapter, api-versioning-strategy, tech-stack-evaluation, engineering-discipline, code-review, writing-plans, verification-before-completion, systematic-debugging, subagent-orchestration, finishing-a-development-branch, cost-routing-paradigms
- **Backend/data:** backend-fastify-trpc-grpc, grpc-buf, python-services, database-design, clickhouse-olap, sql-query-optimization, event-driven-kafka, api-traffic-patterns, idempotency-handling, caching-strategy, integration-connectors, mcp-protocol, turborepo, multi-tenancy-isolation, metric-engine
- **Frontend/mobile:** frontend-web, frontend-mobile, web-performance, kpi-dashboard-design, morning-brief-mobile, mobile-offline-support, push-notification-setup
- **AI:** agentic-design, claude-api, forecasting-prophet, agentic-actions-auditor, memory-layer-pgvector
- **Security:** security-baseline, auth-and-access, defense-in-depth-validation, vulnerability-scanning, oauth-implementation, data-privacy-dpdp
- **Ops/testing/product:** devops-aws, observability, operational-readiness, testing-tdd, api-contract-testing, task-tracker-integration, lifecycle-revenue-layer, india-commerce-economics
- **Command-skills (28):** requirement, status, recall, handoff, approve, reject, deploy, rollback, persona, invoke-skill, eos-init, propose-rule, adopt-rule, reject-rule, recall-similar, reindex, qa-browser, design-review, worker-test-gap, worker-canon-drift, worker-compliance-drift, test-pipeline, resume, new-skill, team-digest, watch, monitor, dashboard

## 6. Durable rules (the non-negotiables, in every agent's system prompt)
1. **Commit discipline** — agents stage product code (`git add`, explicit paths, never `-A`); the **Founder** commits product code; agents commit only the `.engineering-os/` audit trail as `chore(eos):`; **never** rewrite git history.
2. **No over-engineering** — build the minimum that solves the requirement; 10 STOP signals; Rohan runs an over-engineering audit at Stage 6.
3. **Persona calibration** — 0/1/2 personas by complexity, capped at 2 (never 3+).
4. **Plan-first + self-review + explicit handoff** — every agent plans before acting, self-reviews against its DoD, and invokes the next agent via `Agent()`.
5. **Cost-routed paradigms** — SQL > ML > Haiku > Sonnet; every code path declares `@paradigm` (keeps LLM cost down — the engineering invariant behind Brain's realized-GMV %-pricing).
6. **Single-Primitive Rule** — every cross-cutting concern built once, consumed N times.
7. **Multi-tenant `workspace_id`** enforced at 4 layers; **compliance is P0** — DPDP Act 2023 + Rules 2025, TCCCPR/DLT + NCPR/DND + 9am–9pm calling window, WhatsApp opt-in, UAE/KSA PDPL.
8. **Verification before completion** — no "done" claim without fresh captured command output.
9. **UTC timestamp discipline**; **append-only journals**.

## 7. Canon, primers, gates & hooks
- **Canon (source of truth):** `canon/business-requirements.md`, `canon/technical-requirements.md`.
- **Primers (what agents read — condensed):** `docs/business-context.md`, `docs/technical-context.md`.
- **Quality gates (G0–G9):** [docs/quality-gates.md](docs/quality-gates.md) — pre-flight dependency check, Stage-4 fast-pass rules, QA re-runs skipped gates, Rohan re-runs QA's gates at Stage 6.
- **Hooks:** `on-session-start` (rehydrate state), `on-post-tool-use` (journal append, skips read-only Bash), `on-pre-handoff` (handoff-event logger — observability only; enforcement lives in the agents).

## 8. Self-improvement substrate
- Stage 6 writes a **retro** (`14-retro.md`) → distilled into the append-only **`lessons-learned.md`** registry → **Rohan reads relevant lessons at every Stage 1 intake** (a compounding learning loop).
- **Rule governance:** any agent can `/propose-rule`; the Founder `/adopt-rule` or `/reject-rule` (Founder-only). Adopted rules become durable rules.
- `pending-founder-attention.md` surfaces items needing the Founder.

## 9. What the team builds — Brain (the AI-native commerce OS)
> Brain helps DTC brands grow realized revenue, recover lost revenue, protect contribution margin, and compound decision quality across marketing, lifecycle, support, logistics, inventory, and finance. India-first at launch; UAE/GCC are first-class adapters activated in Phase 4. The **moat** is the **Decision Log** (no Brain action exists unless it's logged) + the **Brand Fingerprint** memory layer.

A **7-service, DDD, event-driven** architecture:
- **Services:** api-gateway, core-service, ingestion-service, analytics-service, intelligence-service, notifications-service, lifecycle-service (+ frontend-web, mobile). Each is DDD-structured by bounded context, owns its own DB, communicates via gRPC (sync) / Kafka (async). Realtime, background jobs, cron, and workflows live *inside* these services — not as separate services.
- **Locked stack:** Fastify + FastAPI, AWS CDK + ArgoCD + EKS, MSK/Kafka, ClickHouse, Supabase Postgres + pgvector, CloudWatch/OpenSearch/X-Ray/Sentry/PostHog (+ OpenTelemetry instrumentation), Turborepo, Next.js + React Native/Expo, Redux, Anthropic Claude (Sonnet 4.6 synthesis + Haiku 4.5 bounded NL); region `ap-south-1`.
- **Day-one invariants:** cost-routing paradigms, the Single-Primitive Rule, multi-tenant `workspace_id` (4 layers), integer minor-units money, the Decision Log, the region-adapter, the metric registry (TS↔Python parity), proto-defined gRPC contracts, OLTP/OLAP split, idempotency, and the Morning Brief as the primary surface.

## 10. Using it
```
/plugin marketplace add Rishabhporwal/Engineering-OS
/plugin install brain-engineering-os
# in your Brain repo:
/brain-engineering-os:eos-init                       # one-time scaffold of .engineering-os/
/brain-engineering-os:requirement <what to build>    # start the pipeline
/brain-engineering-os:status                          # what's in flight
/brain-engineering-os:recall <feat-slug>              # full per-feature history (exact)
/brain-engineering-os:recall-similar <description>    # semantic search across ALL memory
/brain-engineering-os:team-digest                     # what the whole team built + challenges
/brain-engineering-os:approve <req-id>                # the Founder gate (Stage 7)
/brain-engineering-os:test-pipeline                   # validate plugin health (pipeline doctor)
```

## 11. Repo layout (the plugin)
```
agents/      11 subagent definitions
skills/      85 skill folders (57 domain + 28 command)  +  tools/  (uv scripts: memory, browse, pipeline_doctor, team_digest, paradigm_check, dashboard)
prompts/     system-prompt, anti-blind-agreement, challenge-framework
canon/       business-requirements.md, technical-requirements.md (source of truth)
docs/        operating manual, primers, matrix, quality-gates, role-empowerment, …
templates/   per-stage artifact templates    schemas/  JSON schemas
workflows/   requirement-to-release / state-machine / approval-flow (YAML)
hooks/       session-start, post-tool-use, pre-handoff
.claude-plugin/  plugin.json, marketplace.json
```

## 12. Get the most from the team (product engineers)

You don't write the features — you direct the team and let it run. Here's how to extract maximum value, especially with several engineers on one Brain repo.

### Your daily loop
1. **Start with awareness.** `git pull`, then `/team-digest` — see what every engineer has built, what's in flight, and the challenges they hit. Before starting anything, `/recall-similar "<your idea>"` — the team may have already solved it (reuse the decision; don't re-derive).
2. **Submit a requirement, not a spec.** `/requirement <plain-English ask>`. The team handles intake → architecture → build → security → QA → review autonomously. You're the Founder gate at Stage 7 only.
3. **Let the lane do the work.** Rohan auto-classifies risk:
   - **Express** (copy/config/docs/trivial) — skips Architect/Security/Final-review; ~5 agent touches.
   - **Standard** — full pipeline, lean, Security ∥ QA in parallel.
   - **High-stakes** (auth/money/multi-tenancy/PII/connectors/schema/India-compliance) — full rigor, 2 personas, mandatory Shreya VETO, mutation tests.
   You don't pick the lane; you can trust the conservative tie-break (ambiguity routes *up*).
4. **Approve or reject.** Read the Stage-6 review, then `/approve <req-id>` or `/reject <req-id> <reason>`.

### Powers worth knowing
- **Memory is shared and semantic.** Every decision/journal/challenge from every engineer is git-synced and searchable by *meaning* via `/recall-similar` (it self-refreshes — always current after a pull). Agents use it automatically in their pre-flight, so they reuse the team's prior work without you asking.
- **Real-browser + visual QA.** Web changes get `/qa-browser` (walks real flows, catches console/network errors, generates a Cypress regression test) and `/design-review` (0–10 scored visual audit) — the Morning Brief + KPI surfaces have the highest bar.
- **Proactive workers.** Schedule `/worker-test-gap`, `/worker-canon-drift`, `/worker-compliance-drift` to scan the repo between requirements and file findings.
- **Safety rails.** The `/careful` guard blocks catastrophic commands (rm -rf ~, force-push, DROP/TRUNCATE) with an easy override; the paradigm gate keeps cost discipline; `workspace_id` + compliance (DPDP/PDPL/DLT/NCPR) are enforced at every layer.
- **Recover & validate.** `/resume <req-id>` picks up an interrupted pipeline with no lost work; `/test-pipeline` validates the orchestration is healthy; `/new-skill` scaffolds a new skill when a real gap surfaces.

### Multi-engineer guarantee
Because `.engineering-os/` is committed and pulled, **the team knows about every feature and challenge across all engineers** — your agents see Priya's bounces and Karan's decisions the same as your own. `/team-digest` is the overview; `/recall-similar` is the deep pull. Two engineers won't unknowingly collide or repeat a solved problem.

> The mental model: **you bring intent and judgment; the team brings memory, knowledge, skills, and execution.** The more the team runs, the smarter its shared memory gets — for everyone.

---
*See [docs/operating-system.md](docs/operating-system.md) for the full operating manual, [docs/team-collaboration.md](docs/team-collaboration.md) for the multi-engineer model, and [docs/REBUILD-PROMPT.md](docs/REBUILD-PROMPT.md) to regenerate the team from scratch.*
