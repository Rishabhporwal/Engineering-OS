# Rebuild Prompt — Brain Engineering OS

> Copy everything in the fenced block below into a fresh Claude Code session (in an empty git repo) to regenerate the Brain Engineering OS plugin from scratch. It encodes every load-bearing decision of the current v0.7.1 build. Adjust the bracketed `[…]` bits if the company/stack changes.

---

```
You are building the **Brain Engineering OS** — an AI engineering team delivered as a
Claude Code PLUGIN (installable, not cloned). It takes a Founder's requirement through an
8-stage requirement-to-release pipeline and produces production-grade, audited, journaled
work. It is built for **Brain (Pipada Capital)** — an India-first, AI-native D2C commerce OS
that replaces a brand's fragmented stack (Shopify + Meta + Google + Shiprocket + Razorpay +
WhatsApp + Excel) with one system that sees the data, learns the history, and acts before
the founder has to.

Build the complete plugin. Do NOT over-engineer; build the minimum that fulfils this spec.

== DISTRIBUTION & MEMORY MODEL ==
- It is a Claude Code plugin in `.claude-plugin/plugin.json` + a `marketplace.json`. Installed
  to ~/.claude/plugins/, never cloned into the user's project.
- Plugin-shipped files resolve via ${CLAUDE_PLUGIN_ROOT}; the consuming Brain product repo's
  shared memory resolves via ${CLAUDE_PROJECT_DIR}/.engineering-os/ (committed to git, so it
  survives `git pull` for every teammate). Memory is the moat.
- Slash commands are implemented as SKILLS with `disable-model-invocation: true` (there is no
  commands/ folder). Domain skills are `skills/<name>/SKILL.md` with just name+description.
  Plugin skills are namespaced: /brain-engineering-os:<name>.

== THE TEAM: 11 agents in agents/<name>.md (YAML frontmatter: name, description, tools, model) ==
1. cto-advisor — "Rohan", model opus, tools incl. Agent. Stage 1 intake + Stage 6 final review.
   VETO at Stage 6. Decides persona count 0/1/2 by complexity (capped at 2, never 3+).
2. dynamic-persona-generator — model sonnet. Spawned by Rohan to inhabit ONE stress-test persona
   (compliance-officer, ai-cost-realist, regional-expansion-officer, …); must surface ≥1 concern.
3. architect — "Aryan", model opus, tools incl. Agent. Stage 2 technical plan.
4. backend-developer — "Vikram", model sonnet. Node/Fastify services (api-gateway, core, notifications).
5. frontend-web-developer — "Ananya", model sonnet. Next.js dashboard.
6. mobile-developer — "Karan", model sonnet. React Native + Expo; the Morning Brief surface.
7. intelligence-engineer — "Maya", model sonnet. Python services + the 15 AI agents + RAG + cost-routing.
8. security-reviewer — "Shreya", model opus. Stage 4. VETO on CRITICAL/HIGH + India compliance.
9. qa-agent — "Tanvi", model sonnet. Stage 5. VETO on missing real-network verification.
10. platform-devops — "Jatin", model sonnet. Stage 8 deploy + 48h monitor + rollback.
11. product-manager — "Priya", model sonnet. Cross-cuts (not a stage): release notes, tracker sync.
The human Founder is "Rishabh" (Stage 7 approval — the only human gate).

== THE 8-STAGE PIPELINE ==
1 Rohan intake (+0–2 personas; ADVANCE/CHALLENGE-BACK/KILL) → 2 Aryan architecture plan →
3 parallel build (Vikram∥Ananya∥Karan∥Maya) → 4 Shreya security → 5 Tanvi QA →
6 Rohan final review (+over-engineering audit +retro) → 7 Rishabh /approve → 8 Jatin deploy.
Each stage: PLAN → EXECUTE → SELF-REVIEW → VERIFY → invoke the next stage via the Agent tool
(handoff files are a logged fallback only). Founder gates are Stage 7 + the final push.
Run-folder artifacts are numbered: 01-requirement, 02-cto-advisor-review, 03/04-persona-*,
06-architecture-plan, 07-handoff-to-developer, 08-developer-report-<persona>, 09-security-review,
10-qa-review, 11-final-review, 12-founder-decision.json, 13-deployment-report, 14-retro.

== DURABLE RULES (put in prompts/system-prompt.md; every agent inherits it) ==
- Commit discipline: agents STAGE product code (git add, explicit paths, never -A); the FOUNDER
  commits product code; agents commit only .engineering-os/ as `chore(eos):`; NEVER rewrite git history.
- No over-engineering: build the minimum; 10 STOP signals; Rohan audits for it at Stage 6.
- Persona calibration: 0/1/2 by complexity, capped at 2.
- Plan-first + self-review + explicit Agent() handoff for every agent, every stage.
- Cost-routed paradigms: SQL > ML > Haiku > Sonnet; every code path declares @paradigm (GMV-% pricing).
- Single-Primitive Rule: each cross-cutting concern built once, consumed N times.
- Multi-tenant workspace_id at 4 layers (JWT→service→DB RLS→Kafka envelope).
- India compliance P0: DLT/NCPR/DND/calling-hours 09:00–21:00 IST/recording consent/GST.
- Verification before completion: no "done" claim without fresh captured command output.
- UTC timestamps everywhere; append-only journals (never overwrite).
Also create prompts/anti-blind-agreement.md and prompts/challenge-framework.md (constructive
dissent with a path forward — agents must challenge weak requirements, even the Founder's).

== SKILL LIBRARY: skills/<name>/SKILL.md, house style ==
Each skill: frontmatter (name==folder, description that says what it is + when to auto-load) +
a one-line tagline + "## The Iron Law" code block + a gate/process + classification tables +
"Red flags — STOP" + an Excuse→Reality rationalization table + "## Brain wiring" owner table +
"Related" links. Keep skills focused and right-sized (≤~300 lines). Ground everything in Brain's
locked stack. Author ~49 DOMAIN skills across: architecture/discipline (architecture-patterns,
domain-driven-design, engineering-discipline, code-review, writing-plans, verification-before-
completion, systematic-debugging, subagent-orchestration, finishing-a-development-branch,
cost-routing-paradigms, api-versioning-strategy, tech-stack-evaluation); backend/data
(backend-fastify-trpc-grpc, grpc-buf, python-services, database-design, clickhouse-olap,
sql-query-optimization, event-driven-kafka, api-traffic-patterns, idempotency-handling,
integration-connectors, mcp-protocol, turborepo); frontend/mobile (frontend-web, frontend-mobile,
web-performance, kpi-dashboard-design, morning-brief-mobile, mobile-offline-support,
push-notification-setup); AI (agentic-design, claude-api, forecasting-prophet,
agentic-actions-auditor); security (security-baseline, auth-and-access, defense-in-depth-validation,
vulnerability-scanning, oauth-implementation); ops/testing/product (devops-aws, observability,
operational-readiness, testing-tdd, api-contract-testing, task-tracker-integration,
lifecycle-revenue-layer, india-commerce-economics). Plus 14 COMMAND-skills (disable-model-invocation):
requirement, status, recall, handoff, approve, reject, deploy, rollback, persona, invoke-skill,
eos-init, propose-rule, adopt-rule, reject-rule. Maintain docs/skill-mapping-matrix.md as the
authoritative skill→role binding (table + per-role owned-skill lists).

== WHAT THE TEAM BUILDS (canon) ==
Author canon/BRAIN_BUSINESS.md + canon/BRAIN_TECHNICAL.md (full source of truth) and condensed
agent-facing primers docs/business-context.md + docs/technical-context.md.
Brain = a 7-service, DDD, event-driven D2C commerce OS:
  Services: api-gateway, core-service, ingestion-service, analytics-service, intelligence-service,
  notifications-service, lifecycle-service (+ frontend-web, mobile). Each is DDD-structured by
  bounded context (bootstrap/domain/<context>/{entities,services,repositories,value-objects,dto,
  validators,mappers,events,policies,exceptions,factories,aggregates}/application/{commands,queries,
  use-cases}/infrastructure/interfaces/observability/security/testing — NEVER controllers-services-
  models), owns its own DB (no shared DBs), talks via gRPC (sync) + Kafka (async, versioned topics
  + DLQ + retries). Realtime/jobs/cron/workflows live INSIDE these 7 services, not as separate ones.
LOCKED STACK (do not swap): Fastify + FastAPI; AWS CDK + ArgoCD + EKS+Karpenter (NOT Terraform/Helm);
MSK/Kafka + Glue Schema Registry; ClickHouse; Supabase Postgres + pgvector; CloudWatch + OpenSearch +
X-Ray + Sentry + PostHog with OpenTelemetry as the instrumentation API (NOT Prometheus/Grafana/Loki/
Tempo); Turborepo (NOT Nx); Next.js + Redux; React Native + Expo; Anthropic Claude (Sonnet for
synthesis, Haiku for bounded NL); custom agent base class + pgvector Memory Layer (NOT LangGraph/
dedicated vector DB). THE MOAT: India-commerce economics, cost-routing paradigms, the Morning Brief,
the Single-Primitive Rule — never drop these.

== SUPPORTING PIECES ==
- templates/ (per-stage artifact templates: requirement, cto-advisor-review, dynamic-persona-review,
  architecture-plan, developer-report, security-review, qa-review, final-review, deployment-report,
  retro, rule-proposal, durable-rule) + schemas/ (matching JSON schemas for the JSON artifacts).
- workflows/ (requirement-to-release.yaml, state-machine.yaml, approval-flow.yaml).
- hooks/ (hooks.json + on-session-start.sh rehydrate state; on-post-tool-use.sh journal append that
  SKIPS read-only Bash; on-pre-handoff.sh handoff-event LOGGER only — gate enforcement lives in the
  agents, not the hook).
- docs/: operating-system.md (the manual), workflow.md, quality-gates.md (G0–G9), role-empowerment-
  model.md (incl. the canonical handoff-depth bands), escalation-rules.md, plugin-architecture.md,
  memory-and-git-sync.md, skill-authoring-guide.md, technical-implementation.md.
- SELF-IMPROVEMENT SUBSTRATE: Stage 6 writes 14-retro.md → distilled into an append-only
  .engineering-os/lessons-learned.md that Rohan reads at every Stage 1 intake. Rule governance:
  any agent /propose-rule; Founder-only /adopt-rule and /reject-rule. .engineering-os/eos-init
  scaffolds memory/{agents,features}, state/{active,registry}.json, decision-log/, runs/, artifacts/,
  rule-proposals/, durable-rules/, lessons-learned.md, pending-founder-attention.md, + a .gitattributes
  with merge=union for append-only files.

== DELIVERABLES ==
Produce the full plugin: .claude-plugin/{plugin.json,marketplace.json}; agents/ (11);
prompts/ (3); skills/ (49 domain + 14 command); canon/ (2) + docs/ primers; templates/ + schemas/;
workflows/ (3); hooks/ (3 + hooks.json); docs/ (operating manual set); README.md + ONBOARDING.md.
Keep it consistent: no dead references, counts accurate everywhere, every frontmatter name==folder,
every agent's owned-skill list matches the matrix. Version it (semantic) in plugin.json + marketplace.json.
```

---

## How to use this prompt
1. Create an empty git repo (`git init`).
2. Open it in Claude Code with this plugin's author available.
3. Paste the fenced block above as your first message.
4. Iterate: build canon first, then prompts, then agents, then skills, then templates/schemas/workflows/hooks/docs, then package as a plugin and test `/plugin install`.

## What this prompt deliberately leaves to judgment
- Exact prose/examples inside each skill and canon doc (regenerate in house style).
- Phase-specific Brain detail (Phase 0–4 roadmap, the 15 named AI agents, exact metric formulas) — pull from `canon/BRAIN_TECHNICAL.md` if it exists, or have the CTO Advisor + Architect derive them.
- Anything the Founder later changes (stack swaps, new region, new service) goes through the normal pipeline + ADR, not a rebuild.
