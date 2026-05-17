# Section 1.1 — Folder Analysis & Context Extraction

**Goal:** Inventory every file in the workspace, label what is relevant to the Engineering OS, and flag anything missing, conflicting, or ambiguous before any code is generated.

This document satisfies the prompt's mandate: *"Start by showing your work."*

---

## 1. Workspace inventory (as discovered)

Discovered at the repo root `/Users/rishabhporwal/Desktop/Engineering OS/`:

| Path | Type | Size | Relevant? | Notes |
|------|------|------|-----------|-------|
| `claude_prompt.md` | file | 11 KB / 206 lines | **yes (build spec)** | The team-building prompt. Preserved verbatim as the contract for this deliverable. |
| `Requirements/BRAIN_BUSINESS.md` | file | 87 KB / 1,226 lines | **yes (canon)** | Authoritative business + product source of truth. |
| `Requirements/BRAIN_TECHNICAL.md` | file | 229 KB / 4,557 lines | **yes (canon)** | Authoritative technical source of truth. |
| `Requirements/skills/` | dir | 54 folders | **yes (canon)** | 54 curated skills. Each folder contains a `SKILL.md` with YAML frontmatter (`name`, `description`) and a detailed body. Two folders (`devops-aws/`, `security-baseline/`) also contain a `references/` subdirectory. |

**Nothing else exists at the repo root prior to this build.** No prior plugin, no prior `.engineering-os/` state, no prior `docs/`. This is a green-field implementation grounded in the canon.

---

## 2. All 54 curated skills (extracted from `Requirements/skills/`)

Every folder name is exactly the skill ID. The one-line description below was extracted from each `SKILL.md`'s `description:` YAML frontmatter.

| # | Skill ID | One-line purpose |
|---|----------|------------------|
| 1 | `access-control-rbac` | Owner/Admin/Analyst/Viewer per workspace + agency multi-workspace context — JWT claims + Postgres RLS. |
| 2 | `agentic-design` | Brain's 15 AICMO/AICOO/AICFO agent pattern — base class, daily tick (06:55–07:15 IST), graduation tracker, `@paradigm`/`@mcp_tool` decorators. |
| 3 | `api-contract-testing` | Pact for service-to-service, buf-breaking for proto, schema-version checks for MCP. |
| 4 | `api-pagination` | Cursor pagination on every list endpoint. Offset is banned in prod paths. |
| 5 | `api-rate-limiting` | Token-bucket + sliding-window + ElastiCache. Per-brand quotas, tier-specific limits. |
| 6 | `api-versioning-strategy` | Versioning across tRPC + gRPC + MCP; v1↔v2 reconciliation window. |
| 7 | `app-store-deployment` | EAS Build → TestFlight + Play Internal → manual approval → EAS Submit. OTA-vs-store rules. |
| 8 | `architecture-patterns` | Microservices + Monorepo + Event-Driven (Kafka) + BFF + MCP server. Single-Primitive Rule enforced. |
| 9 | `backend-fastify-trpc-grpc` | Brain's locked Node stack — Fastify + tRPC + Prisma + grpc-js + KafkaJS + Zod. |
| 10 | `claude-api` | Anthropic Messages API for intelligence-service. Sonnet 4.6 + Haiku 4.5. Prompt caching is the cost lever. |
| 11 | `clickhouse-olap` | MergeTree, `workspace_id`-first primary key, materialized views, query gateway rejects un-scoped queries. |
| 12 | `code-review` | Technical rigor over performative agreement. Evidence-based feedback. Verification gates. |
| 13 | `cost-routing-paradigms` | The 4-tier cost gate behind GMV % pricing. SQL > ML > Haiku >> Sonnet. `@paradigm` decorator enforced by CI. |
| 14 | `database-design` | Supabase Postgres + ClickHouse Cloud split. RLS, multi-tenant `workspace_id`, Debezium CDC. |
| 15 | `defense-in-depth-validation` | Validate at every layer — entry boundary, business logic, environment guard, audit log. |
| 16 | `devops-aws` | AWS CDK (TypeScript) IaC; EKS + Karpenter + ArgoCD; MSK; ClickHouse Cloud; ElastiCache; OpenSearch; EAS. |
| 17 | `engineering-discipline` | Universal meta-rules — 7 principles (Karpathy 4 + gstack ETHOS 2 + Right-Sized Stack) + vertical-slice + persona brainstorming. |
| 18 | `event-driven-kafka` | MSK + AWS Glue Schema Registry + Avro. `workspace_id` partition key. Infinite retention via S3 tiered storage. |
| 19 | `forecasting-prophet` | Prophet + isotonic regression + BG/NBD + Gamma-Gamma + Kaplan-Meier + ARIMA. Plan Module backbone. |
| 20 | `frontend-mobile` | React Native + Expo. Tamagui + tRPC + Redux + TanStack + redux-persist + expo-secure-store + expo-notifications + Victory Native + EAS. |
| 21 | `frontend-web` | Next.js 14 App Router + tRPC + Redux + TanStack + nuqs + shadcn + Tailwind + Recharts + Visx. |
| 22 | `grpc-buf` | gRPC over Protobuf via buf. `protos/` is the SINGLE SOURCE OF TRUTH for internal contracts AND MCP tool schemas. |
| 23 | `health-check-endpoints` | EKS liveness/readiness/dependency probes. ArgoCD auto-rollback triggers. |
| 24 | `idempotency-handling` | Idempotency keys + Redis cache + Postgres constraints. Webhook handlers, MCP write tools, every mutation. |
| 25 | `india-commerce-economics` | **THE MOAT.** RTO, COD, GST, pincode, NDR, festivals, multi-3PL, DLT, NCPR, DND, IST discipline. |
| 26 | `integration-connectors` | Shopify, Meta, Google, Shiprocket, Klaviyo, TikTok, Snap. OAuth + idempotent UPSERT + Kafka producer + raw archive. |
| 27 | `kpi-dashboard-design` | Canonical metric registry (never reinvent). 3-min Founder scan visual hierarchy. India rendering. |
| 28 | `lifecycle-revenue-layer` | RFM, 11 canonical segments, the audience builder (SINGLE PRIMITIVE), channel routers, AI calling abstraction, compliance engine. |
| 29 | `logging-best-practices` | Structured JSON logging with `request_id` + `workspace_id`. Fluent Bit → OpenSearch. PII redaction. |
| 30 | `mcp-protocol` | MCP server lives inside api-gateway sharing auth + multi-tenancy + rate limit. Tool schemas come from proto files. |
| 31 | `mobile-offline-support` | AsyncStorage cache, queued mutations, NetInfo transitions, conflict resolution. |
| 32 | `morning-brief-mobile` | THE primary product surface. Three signals per morning; 06:55–07:15 IST agent fan-out; 07:00–09:00 IST push. |
| 33 | `mutation-testing` | Stryker (TS, Vitest runner) + mutmut (Python, pytest). Validates test effectiveness. |
| 34 | `oauth-implementation` | OAuth 2.0 flows for Shopify, Meta, Google Ads, Shiprocket, Klaviyo. Long-lived refresh tokens, scope upgrades. |
| 35 | `observability` | Fluent Bit → OpenSearch + CloudWatch Metrics + X-Ray + Sentry + PostHog. Single correlation ID end-to-end. |
| 36 | `operational-readiness` | Root handler, health check, port selection, real-network smoke test, env var validation, native-dep gotchas. |
| 37 | `push-notification-setup` | Expo Push (APNS + FCM) + notifications-service producer. Morning Brief 06:55–09:00 IST. |
| 38 | `python-services` | FastAPI + grpcio + asyncpg + clickhouse-driver + aiokafka + httpx + Prophet/sklearn + Anthropic SDK + structlog + uv + pytest. |
| 39 | `root-cause-tracing` | Trace bugs backward through the call stack to the original trigger. |
| 40 | `security-baseline` | OWASP Top 10 + Supabase Auth + JWT + multi-tenant `workspace_id` enforcement at 4 layers + STRIDE + MASVS L1/L2 + India compliance gates. **Shreya VETO on CRITICAL/HIGH.** |
| 41 | `session-management` | Session lifecycle, token refresh, cookie config, revocation for Supabase Auth + JWT. |
| 42 | `sql-query-optimization` | EXPLAIN/EXPLAIN PIPELINE, index strategy, cursor pagination, materialized-view discipline. |
| 43 | `supabase-postgres-best-practices` | `workspace_id`-leading indexes, RLS discipline, transaction-vs-session pooler, partial indexes, pg_cron. |
| 44 | `systematic-debugging` | Four-phase: Root Cause → Pattern Analysis → Hypothesis → Implementation. Never jump to fixes. |
| 45 | `task-tracker-integration` | ClickUp / Linear / GitHub Projects / Jira. Opt-in via env var. Tool-agnostic. |
| 46 | `tech-stack-evaluation` | Stack is LOCKED (ADR-001). Only use when adding a new layer not in the stack. |
| 47 | `testing-tdd` | Vitest + pytest + Cypress + Detox + k6. Real-network smoke tests mandatory for PASS. |
| 48 | `turborepo` | Task pipelines, dependsOn, local + remote cache, `--filter`, `--affected`. |
| 49 | `verification-before-completion` | Run verification commands and confirm output before claiming success. Iron Law #5. |
| 50 | `vulnerability-scanning` | pnpm audit + Snyk + Bandit + safety + pip-audit + Trivy + OWASP Dep-Check + Dependabot. |
| 51 | `web-performance-audit` | Pre-deploy Lighthouse + Core Web Vitals + budget gate + RUM check. |
| 52 | `web-performance-optimization` | Next.js 14 Server Components, dynamic imports, image opt, Visx chart perf, LCP/INP/CLS targets. |
| 53 | `writing-plans` | Discipline for breaking work into 2–5 minute tasks with concrete file paths and verification steps. Used by Priya (PM), by Aryan (Architect), and by any agent producing a TODO list. |
| 54 | `xss-prevention` | Output encoding, DOMPurify, CSP nonce, URL allowlisting, safe React patterns. |

**Total: 54 skills.** No skills were skipped or invented. All names match the folder names in `Requirements/skills/` exactly. The full skill-to-role mapping is in [skill-mapping-matrix.md](skill-mapping-matrix.md).

---

## 3. Context extraction (high level — see specific docs for full detail)

- **Business primer extracted** → [business-context.md](business-context.md). Brain = AI-native commerce OS for D2C brands worldwide, India-first. AICMO/AICOO/AICFO. GMV-linked pricing. Memory Layer = moat. 0.5% founding cohort (20 brands), 1.0%/0.5% tiers. Phases 0–5+ from India → GCC → US/EU → Capital/Retail.
- **Technical primer extracted** → [technical-context.md](technical-context.md). Six microservices (api-gateway, core, ingestion, analytics, intelligence, notifications) + lifecycle-service. TS (Fastify + tRPC + Prisma) + Python (FastAPI + asyncpg + clickhouse-driver). Supabase Postgres + ClickHouse Cloud + MSK Kafka + Redis + S3. EKS + Karpenter + ArgoCD on AWS, CDK IaC. Claude Sonnet 4.6 + Haiku 4.5.
- **Curated skills extracted** → 53 listed above; categorized in [skill-mapping-matrix.md](skill-mapping-matrix.md).
- **Roles inferred from skill bodies** → Aryan (Architect), Vikram (Backend), Ananya (Frontend Web), Karan (Mobile), Maya (Intelligence/AI), Shreya (Security — VETO authority), Tanvi (QA), Jatin (DevOps), Priya (PM). The CTO Advisor is a new role (shadow CTO for Rishabh).

---

## 4. Conflicts found

None that block the build. The Brain canon is internally consistent. Two minor observations:

1. **Service count varies between sources.** `BRAIN_TECHNICAL.md` describes **six microservices** (api-gateway, core, ingestion, analytics, intelligence, notifications). The `architecture-patterns` skill lists **seven** (adds `lifecycle-service`). **Resolution:** Treat `lifecycle-service` as the seventh — the skill body is more recent and aligns with `lifecycle-revenue-layer` and the explicit "Auto-load on any lifecycle-service work" trigger.

2. **Tech stack lock vs. evaluation skill.** `tech-stack-evaluation` says "Brain's stack is LOCKED." But `cost-routing-paradigms` requires every new feature to declare its paradigm, which is itself an evaluation. **Resolution:** The lock applies to *layers* (Node/Python/Postgres/ClickHouse/EKS); cost routing operates *within* the locked stack. No conflict in practice.

---

## 5. Missing information & assumptions made (labeled)

The prompt explicitly says: *"If information is missing, document the gap and create a clear, labeled assumption — do not block the work."* Logged here, all reversible.

| # | Gap | Assumption (labeled) |
|---|-----|----------------------|
| A1 | The plugin's git host (GitHub Enterprise? self-hosted Gitea?) is unspecified. | Assume **GitHub**, with PRs/issues integration optional and behind env vars (per `task-tracker-integration`). |
| A2 | Founder Approval channel (Stage 7) is unspecified — Slack? email? in-CLI? | Assume **in-CLI primary** (`/approve <req-id>` and `/reject <req-id>`), with optional Slack notification behind an env var. |
| A3 | Auto-execute action set during plugin operation (e.g., can the plugin auto-merge PRs after Founder approval?) is unspecified. | Assume **no auto-merge in MVP**. DevOps (Jatin) opens PRs; humans merge until Phase 2. |
| A4 | Memory size budget on `.engineering-os/` (git repo bloat over years) is unspecified. | Assume **git LFS for `runs/` artifacts >1 MB**; journals stay in plain markdown; archival policy ships in V2. |
| A5 | Concurrency model when two operators run the plugin simultaneously is unspecified. | Assume **last-pull-wins on state, append-only on journals, per-run folders ensure zero artifact collisions** (see [docs/memory-and-git-sync.md](memory-and-git-sync.md)). |
| A6 | The CTO Advisor's name is not present in the Brain canon (Aryan etc. are, but the CTO Advisor isn't). | Assume CTO Advisor is **unnamed (shadow role for Rishabh)** to avoid implying a co-founder. |
| A7 | Whether the plugin should *also* manage non-feature work (incidents, on-call, ad-hoc analysis) is unspecified. | Assume **MVP = feature pipeline only**; incident response and on-call are V2 additions. |

If any assumption is wrong, flag it and we update the affected agent/doc only — none are load-bearing on the architecture.

---

## 6. Recommended additional skills (NOT sourced from `Requirements/skills/` — clearly labeled)

The 53 curated skills cover ~95% of what the agents need. The following are recommended additions, clearly marked as **not currently in `Requirements/skills/`**:

| Suggested skill | Why | Owner if added |
|-----------------|-----|----------------|
| `requirement-intake` | A standard for turning a Founder's one-sentence ask into a structured requirement payload (problem, user, success criteria, non-goals, constraints). Used by CTO Advisor in Stage 1. | CTO Advisor + Priya |
| `dynamic-persona-spawning` | Discipline for choosing which 3 personas to spawn for a given requirement and how to weight their inputs. Used in Stage 1. | CTO Advisor |
| `production-readiness-checklist` | A composed checklist that aggregates `operational-readiness` + `health-check-endpoints` + `observability` + `vulnerability-scanning` into a Stage 6 gate. | CTO Advisor + Jatin |
| `release-notes-and-changelog` | Conventions for human-readable release notes from per-run journals at Stage 8. | Jatin + Priya |

These four are flagged but **not auto-created** in this build. Founder may approve creating them in V2.

---

## 7. What was *not* used (and why)

- **Nothing in `Requirements/` was ignored.** Every file was inventoried.
- **The two `references/` subdirectories** (`devops-aws/references/`, `security-baseline/references/`) were not opened during this analysis — they are deep-reading materials the corresponding agent will load lazily via `Read`/`Grep` when the skill is invoked at runtime. They are *available* to the agent, not *prefetched* into the plugin manifest.

---

## 8. Output of this section

The remaining Section 1 deliverables:
- [business-context.md](business-context.md) — Brain business primer for every agent (extracted from `BRAIN_BUSINESS.md`).
- [technical-context.md](technical-context.md) — Brain technical primer for every agent (extracted from `BRAIN_TECHNICAL.md`).

Section 2 (Skill Mapping & Role Empowerment) is in [skill-mapping-matrix.md](skill-mapping-matrix.md) and [role-empowerment-model.md](role-empowerment-model.md).
