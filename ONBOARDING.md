# Brain Engineering OS — Onboarding

> The complete picture of the AI engineering team. If you're new, read this top to bottom once. Current version: **v0.7.1**.

---

## 1. What it is
An **AI engineering team delivered as a Claude Code plugin**. You give it a requirement; it runs that requirement through an 8-stage pipeline — intake → architecture → parallel build → security → QA → final review → Founder approval → deploy — producing production-grade, audited, journaled work every time. It exists so **Brain (Pipada Capital)** can ship its AI-native D2C commerce OS without hiring a large engineering team early.

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
| **Karan** | Mobile (React Native + Expo) | sonnet | 3 | the Morning Brief surface |
| **Maya** | Intelligence Engineer (Python/AI) | sonnet | 3 | the 15 AI agents, RAG, cost-routing |
| **Shreya** | Security Reviewer | opus | 4 | **VETO** on CRITICAL/HIGH + India compliance |
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
Each stage **plans → executes → self-reviews → verifies → invokes the next stage via the `Agent` tool** (handoff files are a logged fallback only). The Founder intervenes only at Stage 7 and at the final push.

## 5. The skill library — 63 folders (49 domain + 14 command)
**Domain skills** are model-auto-loaded per each agent's owned-skill list (see [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md)). **Command-skills** carry `disable-model-invocation: true` and run only when a human types `/brain-engineering-os:<name>`.

- **Architecture/discipline:** architecture-patterns, domain-driven-design, api-versioning-strategy, tech-stack-evaluation, engineering-discipline, code-review, writing-plans, verification-before-completion, systematic-debugging, subagent-orchestration, finishing-a-development-branch, cost-routing-paradigms
- **Backend/data:** backend-fastify-trpc-grpc, grpc-buf, python-services, database-design, clickhouse-olap, sql-query-optimization, event-driven-kafka, api-traffic-patterns, idempotency-handling, integration-connectors, mcp-protocol, turborepo
- **Frontend/mobile:** frontend-web, frontend-mobile, web-performance, kpi-dashboard-design, morning-brief-mobile, mobile-offline-support, push-notification-setup
- **AI:** agentic-design, claude-api, forecasting-prophet, agentic-actions-auditor
- **Security:** security-baseline, auth-and-access, defense-in-depth-validation, vulnerability-scanning, oauth-implementation
- **Ops/testing/product:** devops-aws, observability, operational-readiness, testing-tdd, api-contract-testing, task-tracker-integration, lifecycle-revenue-layer, india-commerce-economics
- **Command-skills (14):** requirement, status, recall, handoff, approve, reject, deploy, rollback, persona, invoke-skill, eos-init, propose-rule, adopt-rule, reject-rule

## 6. Durable rules (the non-negotiables, in every agent's system prompt)
1. **Commit discipline** — agents stage product code (`git add`, explicit paths, never `-A`); the **Founder** commits product code; agents commit only the `.engineering-os/` audit trail as `chore(eos):`; **never** rewrite git history.
2. **No over-engineering** — build the minimum that solves the requirement; 10 STOP signals; Rohan runs an over-engineering audit at Stage 6.
3. **Persona calibration** — 0/1/2 personas by complexity, capped at 2 (never 3+).
4. **Plan-first + self-review + explicit handoff** — every agent plans before acting, self-reviews against its DoD, and invokes the next agent via `Agent()`.
5. **Cost-routed paradigms** — SQL > ML > Haiku > Sonnet; every code path declares `@paradigm` (this is what makes GMV-% pricing work).
6. **Single-Primitive Rule** — every cross-cutting concern built once, consumed N times.
7. **Multi-tenant `workspace_id`** enforced at 4 layers; **India compliance is P0** (DLT/NCPR/DND/calling-hours/GST).
8. **Verification before completion** — no "done" claim without fresh captured command output.
9. **UTC timestamp discipline**; **append-only journals**.

## 7. Canon, primers, gates & hooks
- **Canon (source of truth):** `canon/BRAIN_BUSINESS.md`, `canon/BRAIN_TECHNICAL.md`.
- **Primers (what agents read — condensed):** `docs/business-context.md`, `docs/technical-context.md`.
- **Quality gates (G0–G9):** [docs/quality-gates.md](docs/quality-gates.md) — pre-flight dependency check, Stage-4 fast-pass rules, QA re-runs skipped gates, Rohan re-runs QA's gates at Stage 6.
- **Hooks:** `on-session-start` (rehydrate state), `on-post-tool-use` (journal append, skips read-only Bash), `on-pre-handoff` (handoff-event logger — observability only; enforcement lives in the agents).

## 8. Self-improvement substrate
- Stage 6 writes a **retro** (`14-retro.md`) → distilled into the append-only **`lessons-learned.md`** registry → **Rohan reads relevant lessons at every Stage 1 intake** (a compounding learning loop).
- **Rule governance:** any agent can `/propose-rule`; the Founder `/adopt-rule` or `/reject-rule` (Founder-only). Adopted rules become durable rules.
- `pending-founder-attention.md` surfaces items needing the Founder.

## 9. What the team builds — Brain
A **7-service, DDD, event-driven** D2C commerce OS:
- **Services:** api-gateway, core-service, ingestion-service, analytics-service, intelligence-service, notifications-service, lifecycle-service (+ frontend-web, mobile). Each is DDD-structured by bounded context, owns its own DB, communicates via gRPC (sync) / Kafka (async). Realtime, background jobs, cron, and workflows live *inside* these services — not as separate services.
- **Locked stack:** Fastify + FastAPI, AWS CDK + ArgoCD + EKS, MSK/Kafka, ClickHouse, Supabase Postgres + pgvector, CloudWatch/OpenSearch/X-Ray/Sentry/PostHog (+ OpenTelemetry instrumentation), Turborepo, Next.js + React Native/Expo, Redux, Anthropic Claude.
- **The moat:** India-commerce economics (RTO/COD/GST/festivals/DLT), cost-routing paradigms, the Morning Brief, the Single-Primitive Rule.

## 10. Using it
```
/plugin marketplace add Rishabhporwal/Engineering-OS
/plugin install brain-engineering-os
# in your Brain repo:
/brain-engineering-os:eos-init                       # one-time scaffold of .engineering-os/
/brain-engineering-os:requirement <what to build>    # start the pipeline
/brain-engineering-os:status                          # what's in flight
/brain-engineering-os:recall <feat-slug>              # full per-feature history
/brain-engineering-os:approve <req-id>                # the Founder gate (Stage 7)
```

## 11. Repo layout (the plugin)
```
agents/      11 subagent definitions
skills/      63 skill folders (49 domain + 14 command)
prompts/     system-prompt, anti-blind-agreement, challenge-framework
canon/       BRAIN_BUSINESS.md, BRAIN_TECHNICAL.md (source of truth)
docs/        operating manual, primers, matrix, quality-gates, role-empowerment, …
templates/   per-stage artifact templates    schemas/  JSON schemas
workflows/   requirement-to-release / state-machine / approval-flow (YAML)
hooks/       session-start, post-tool-use, pre-handoff
.claude-plugin/  plugin.json, marketplace.json
```

---
*See [docs/operating-system.md](docs/operating-system.md) for the full operating manual and [docs/REBUILD-PROMPT.md](docs/REBUILD-PROMPT.md) to regenerate the team from scratch.*
