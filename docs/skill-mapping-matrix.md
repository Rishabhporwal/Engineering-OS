# Section 2.1 — Skill Mapping Matrix

This document is the **authoritative skill-to-role binding** for the Engineering OS. It maps every **domain skill** in [`skills/`](../skills/). (The **command-skills** carrying `disable-model-invocation: true` — requirement, status, recall, handoff, approve, reject, deploy, rollback, persona, invoke-skill, eos-init, **foundation**, propose-rule, adopt-rule, reject-rule, plus recall-similar, reindex, qa-browser, design-review, worker-test-gap, worker-canon-drift, worker-compliance-drift, test-pipeline, resume, new-skill, team-digest, watch, monitor, dashboard, decide — are human/schedule-triggered and not mapped here.) Each domain skill is mapped to:

- A **domain category** (one of 14).
- One or more **primary role owners** (which agent must auto-load it).
- Optional **shared roles** (other agents that should also know it).
- Optional **plugin command** that exposes the skill to humans.

**How agents use this matrix at runtime:** each agent's prompt (in [`agents/`](../agents/)) explicitly lists the skills it owns. When the agent picks up a task, it auto-loads its owned skills and consults the matrix to know whether to call peer agents whose skills are relevant.

---

## Domain key

| Domain | Description |
|--------|------------|
| **ARCH** | Architecture & system design |
| **BE** | Backend services, APIs, OLTP |
| **FE-W** | Frontend (web) |
| **FE-M** | Frontend (mobile) |
| **DATA** | Data layer (OLTP, OLAP, schema, query optimization) |
| **AI** | AI / LLM / agents |
| **SEC** | Security & compliance |
| **OBS** | Observability (logs, metrics, traces, errors, dashboards) |
| **TEST** | Testing & verification |
| **PERF** | Performance (web + data) |
| **OPS** | DevOps / infra / deployment |
| **INTG** | Integrations / connectors |
| **DISC** | Engineering discipline / process |
| **STREAM** | Stream processing (real-time compute) |
| **BATCH** | Batch processing (large-scale offline compute) |
| **LAKE** | Lakehouse / open table format (raw + historical store) |
| **GRAPH** | Graph / identity resolution |
| **SEARCH** | Search / retrieval (lexical + vector) |
| **MLOPS** | ML platform & model lifecycle (features, registry, serving) |
| **WF** | Durable workflow / orchestration |

> A skill tagged to a vendor-specific domain (e.g. a Next.js or ClickHouse skill) is a **reference implementation** of a seam — the *patterns* transfer, the vendor does not. See `engineering-os-blueprint/09-reference-architecture.md`. The product's `STACK.md` declares which technology actually binds each seam.

## Role key

| Code | Role | Agent file |
|------|------|------------|
| **CTOA** | Engineering Advisor | `cto-advisor` / `final-reviewer` |
| **ARC** | Architect | `architect` |
| **BE** | Backend Engineer | `backend-developer` |
| **FEW** | Frontend/Web Engineer | `frontend-web-developer` |
| **FEM** | Mobile Engineer | `mobile-developer` |
| **AIE** | AI/ML Engineer | `intelligence-engineer` |
| **DE** | Data Engineer | `data-engineer` |
| **MLP** | ML Platform Engineer | `ml-platform-engineer` |
| **SEC** | Security Reviewer | `security-reviewer` |
| **QA** | QA Engineer | `qa-agent` |
| **OPS** | Platform/SRE | `platform-devops` |
| **PM** | Delivery Coordinator | `product-manager` |
| **DYN** | Dynamic Persona (runtime) | `dynamic-persona-generator` |

---

## The matrix (domain skills)

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 1 | [`agentic-safety`](../skills/agentic-safety/SKILL.md) | SEC + AI | SEC | AIE, ARC | yes |
| 2 | [`api-discipline`](../skills/api-discipline/SKILL.md) (contracts, versioning, pagination, rate-limiting) | BE + ARCH + TEST | BE | AIE, FEW, FEM, OPS, SEC, QA, ARC, CTOA | yes |
| 3 | [`app-store-deployment`](../skills/app-store-deployment/SKILL.md) | OPS | OPS | FEM | yes |
| 4 | [`architecture-patterns`](../skills/architecture-patterns/SKILL.md) | ARCH | ARC | CTOA, BE, AIE | yes |
| 5 | [`auth-and-access`](../skills/auth-and-access/SKILL.md) (sessions + RBAC) | SEC | SEC | BE, FEW, FEM, AIE, ARC | yes |
| 6 | [`backend-fastify-trpc-grpc`](../skills/backend-fastify-trpc-grpc/SKILL.md) (reference impl) | BE | BE | ARC | yes |
| 7 | [`caching-strategy`](../skills/caching-strategy/SKILL.md) | DATA + PERF | BE | AIE, OPS, SEC | yes |
| 8 | [`claude-api`](../skills/claude-api/SKILL.md) | AI | AIE | ARC, OPS (cost monitoring) | yes |
| 9 | [`clickhouse-olap`](../skills/clickhouse-olap/SKILL.md) (reference impl) | DATA | AIE | BE, ARC | yes |
| 10 | [`code-review`](../skills/code-review/SKILL.md) | DISC | CTOA | QA, ARC, all devs | yes |
| 11 | [`compliance-attestation`](../skills/compliance-attestation/SKILL.md) | SEC + DATA + DISC | SEC | BE, AIE, ARC, OPS, CTOA | yes |
| 12 | [`compliance-engine`](../skills/compliance-engine/SKILL.md) | SEC | SEC | AIE, **ALL** | yes |
| 13 | [`cost-routing-paradigms`](../skills/cost-routing-paradigms/SKILL.md) | DISC + AI | CTOA, AIE | all devs, QA, OPS | yes |
| 14 | [`data-layer`](../skills/data-layer/SKILL.md) (reference impl; OLTP + query optimization) | DATA + PERF | ARC | BE, AIE, SEC | yes |
| 15 | [`data-quality`](../skills/data-quality/SKILL.md) | DATA + AI | AIE | BE, QA | yes |
| 16 | [`decision-log`](../skills/decision-log/SKILL.md) | AI + DATA | AIE | BE, ARC, SEC, **ALL** | yes |
| 17 | [`devops-aws`](../skills/devops-aws/SKILL.md) (reference impl) | OPS | OPS | ARC | yes |
| 18 | [`domain-driven-design`](../skills/domain-driven-design/SKILL.md) | ARCH | ARC | **ALL** builders | yes |
| 19 | [`engineering-discipline`](../skills/engineering-discipline/SKILL.md) | DISC | CTOA | **ALL** roles | yes |
| 20 | [`event-driven-kafka`](../skills/event-driven-kafka/SKILL.md) (reference impl) | DATA + BE | BE | AIE, ARC, OPS | yes |
| 21 | [`experimentation-holdouts`](../skills/experimentation-holdouts/SKILL.md) | AI + TEST | AIE, PM | CTOA | yes |
| 22 | [`finishing-a-development-branch`](../skills/finishing-a-development-branch/SKILL.md) | OPS + DISC | OPS | **ALL** (commit discipline) | yes |
| 23 | [`frontend-web`](../skills/frontend-web/SKILL.md) (reference impl) | FE-W | FEW | ARC, QA | yes |
| 24 | [`grpc-buf`](../skills/grpc-buf/SKILL.md) (reference impl) | BE | BE | AIE, ARC | yes |
| 25 | [`idempotency-handling`](../skills/idempotency-handling/SKILL.md) | BE | BE | AIE, QA | yes |
| 26 | [`incident-response`](../skills/incident-response/SKILL.md) | OPS | OPS | CTOA, SEC | yes |
| 27 | [`integration-connectors`](../skills/integration-connectors/SKILL.md) | INTG | AIE | BE, ARC | yes |
| 28 | [`kpi-dashboard-design`](../skills/kpi-dashboard-design/SKILL.md) | FE-W | FEW | FEM, PM | yes |
| 29 | [`llm-evals`](../skills/llm-evals/SKILL.md) | AI + TEST | AIE, QA | ARC | yes |
| 30 | [`llm-gateway`](../skills/llm-gateway/SKILL.md) (reference impl) | AI | AIE | ARC, CTOA, OPS | yes |
| 31 | [`mcp-protocol`](../skills/mcp-protocol/SKILL.md) (incl. building an MCP server) | AI + ARCH | AIE | ARC, BE | yes |
| 32 | [`metric-engine`](../skills/metric-engine/SKILL.md) (single-source metric registry, cross-runtime parity) | DATA + AI | AIE | BE, QA, FEW | yes |
| 33 | [`mobile-surface`](../skills/mobile-surface/SKILL.md) (reference impl) | FE-M | FEM | ARC, QA, BE | yes |
| 34 | [`multi-tenancy-isolation`](../skills/multi-tenancy-isolation/SKILL.md) | SEC + DATA | SEC | ARC, BE, AIE, **ALL** | yes |
| 35 | [`oauth-implementation`](../skills/oauth-implementation/SKILL.md) (reference impl) | SEC + INTG | AIE | BE, SEC | yes |
| 36 | [`observability`](../skills/observability/SKILL.md) (incl. structured logging) | OBS | OPS | **ALL** roles | yes |
| 37 | [`operational-readiness`](../skills/operational-readiness/SKILL.md) (incl. health-check endpoints) | OPS + OBS | OPS, QA | all devs, CTOA, BE, AIE | yes |
| 38 | [`progressive-delivery`](../skills/progressive-delivery/SKILL.md) | OPS | OPS | ARC | yes |
| 39 | [`python-services`](../skills/python-services/SKILL.md) (reference impl) | BE | AIE | BE (parity), ARC | yes |
| 40 | [`region-and-locale`](../skills/region-and-locale/SKILL.md) | ARCH + FE-W + FE-M + OPS | ARC | FEW, FEM, OPS, SEC, PM, CTOA, **ALL** builders | yes |
| 41 | [`security-baseline`](../skills/security-baseline/SKILL.md) (incl. XSS prevention) | SEC | SEC | BE, AIE, QA, FEW, FEM, OPS, **ALL** roles | yes |
| 42 | [`subagent-orchestration`](../skills/subagent-orchestration/SKILL.md) (fan-out + pipeline dispatch) | DISC | CTOA | ARC | yes |
| 43 | [`systematic-debugging`](../skills/systematic-debugging/SKILL.md) (incl. root-cause tracing) | DISC | all devs, QA | CTOA, SEC | yes |
| 44 | [`task-tracker-integration`](../skills/task-tracker-integration/SKILL.md) | DISC + OPS | PM | OPS, CTOA | yes |
| 45 | [`tech-stack-evaluation`](../skills/tech-stack-evaluation/SKILL.md) | ARCH | ARC | CTOA | yes (rare) |
| 46 | [`testing-tdd`](../skills/testing-tdd/SKILL.md) (incl. mutation testing) | TEST | QA | all devs, AIE | yes |
| 47 | [`turborepo`](../skills/turborepo/SKILL.md) (reference impl) | OPS | OPS | BE, FEW, FEM | yes |
| 48 | [`verification-before-completion`](../skills/verification-before-completion/SKILL.md) | DISC | **ALL** roles | — | yes |
| 49 | [`version-upgrade-policy`](../skills/version-upgrade-policy/SKILL.md) | OPS + ARCH | OPS, ARC | BE | yes |
| 50 | [`web-performance`](../skills/web-performance/SKILL.md) (audit + optimization) | PERF + FE-W | FEW | QA, OPS, ARC | yes |
| 51 | [`writing-plans`](../skills/writing-plans/SKILL.md) | DISC | PM, ARC | **ALL** plan-emitting agents | yes |
| 52 | [`accessibility`](../skills/accessibility/SKILL.md) | FE-W + FE-M | FEW, FEM | QA | yes |

### Data-plane + ML-platform seams (Phase 2 expansion)

> These 10 reference-implementation skills bind the data-infra and ML-platform seams a high-scale, AI-native product needs. They are owned primarily by the two roles added in this expansion — **Data Engineer (DE)** and **ML Platform Engineer (MLP)**. Numbering continues the table above; they are listed alphabetically within this block. Like every vendor-named skill, they are **reference impls** — the product's `STACK.md` binds the seam to the actual technology.

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 53 | [`agent-orchestration-langgraph`](../skills/agent-orchestration-langgraph/SKILL.md) (reference impl) | AI + MLOPS | AIE | MLP, SEC, ARC | yes |
| 54 | [`batch-processing-spark`](../skills/batch-processing-spark/SKILL.md) (reference impl) | BATCH + DATA | DE | AIE, MLP, ARC | yes |
| 55 | [`feature-store-feast`](../skills/feature-store-feast/SKILL.md) (reference impl) | MLOPS + DATA + AI | MLP | DE, AIE, QA | yes |
| 56 | [`graph-identity-neo4j`](../skills/graph-identity-neo4j/SKILL.md) (reference impl) | GRAPH + DATA | DE | AIE, BE, SEC, ARC | yes |
| 57 | [`lakehouse-iceberg`](../skills/lakehouse-iceberg/SKILL.md) (reference impl) | LAKE + DATA | DE | AIE, MLP, ARC, OPS | yes |
| 58 | [`ml-lifecycle`](../skills/ml-lifecycle/SKILL.md) (reference impl; MLflow registry + serving) | MLOPS + AI | MLP | AIE, QA, OPS | yes |
| 59 | [`search-opensearch`](../skills/search-opensearch/SKILL.md) (reference impl) | SEARCH + DATA + BE | BE | DE, OPS, SEC | yes |
| 60 | [`stream-processing-flink`](../skills/stream-processing-flink/SKILL.md) (reference impl) | STREAM + DATA | DE | AIE, MLP, BE, ARC, OPS | yes |
| 61 | [`vector-search-pgvector`](../skills/vector-search-pgvector/SKILL.md) (reference impl) | SEARCH + AI + MLOPS | MLP | AIE, DE, SEC | yes |
| 62 | [`workflow-engine-temporal`](../skills/workflow-engine-temporal/SKILL.md) (reference impl) | WF + BE + OPS | BE | AIE, MLP, OPS, ARC | yes |

### Skill modernization (Phase 4 — 2026 standards)

> Ten net-new skills closing the gaps a GitHub-grounded market scan surfaced (supply-chain integrity, AI/LLM security + observability + retrieval + agent-eval, the dbt transformation layer, AI-native frontend, policy-as-code, the IDP, and cloud FinOps). Numbering continues the table; listed alphabetically within this block.

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 63 | [`agent-evaluation`](../skills/agent-evaluation/SKILL.md) | AI + TEST + MLOPS | AIE | MLP, QA | yes |
| 64 | [`ai-llm-security`](../skills/ai-llm-security/SKILL.md) | SEC + AI | SEC | AIE, MLP, ARC | yes |
| 65 | [`ai-observability-tracing`](../skills/ai-observability-tracing/SKILL.md) | OBS + AI | AIE | MLP, OPS | yes |
| 66 | [`ai-streaming-ui`](../skills/ai-streaming-ui/SKILL.md) (reference impl) | FE-W + AI | FEW | AIE, FEM | yes |
| 67 | [`data-transformation-dbt`](../skills/data-transformation-dbt/SKILL.md) (reference impl) | DATA + BATCH | DE | AIE, QA | yes |
| 68 | [`finops-cost`](../skills/finops-cost/SKILL.md) | OPS + DISC | OPS | CTOA, AIE, ARC | yes |
| 69 | [`platform-engineering-idp`](../skills/platform-engineering-idp/SKILL.md) | OPS | OPS | ARC, PM, all builders | yes |
| 70 | [`policy-as-code`](../skills/policy-as-code/SKILL.md) | SEC + OPS | SEC | OPS, ARC | yes |
| 71 | [`rag-retrieval`](../skills/rag-retrieval/SKILL.md) | SEARCH + AI | MLP | AIE, DE | yes |
| 72 | [`supply-chain-security`](../skills/supply-chain-security/SKILL.md) | SEC + OPS | OPS | SEC, ARC, all builders | yes |

### Process-discipline completions (Phase 5)

> The four skills this matrix itself had flagged as "recommended but not implemented," now implemented, plus the persona discipline wired into the persona agent.

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 73 | [`requirement-intake`](../skills/requirement-intake/SKILL.md) | DISC | CTOA, PM | ARC | yes |
| 74 | [`dynamic-persona-spawning`](../skills/dynamic-persona-spawning/SKILL.md) | DISC | DYN | CTOA | yes |
| 75 | [`production-readiness-checklist`](../skills/production-readiness-checklist/SKILL.md) | OPS + DISC | CTOA, OPS | QA, all builders | yes |
| 76 | [`release-notes-and-changelog`](../skills/release-notes-and-changelog/SKILL.md) | OPS + DISC | OPS, PM | CTOA | yes |

### Product-stack seam bindings (Phase 6)

> Five reference-impl skills binding seams a concrete AI-native commerce stack needs (StarRocks serving, the Redpanda→Iceberg backbone, KafkaJS consumer processing, Argo Workflows orchestration, and local-dev parity). Like every vendor-named skill, these are **reference implementations** — `STACK.md` binds the actual technology. Numbered continuation; alphabetical within the block.

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 77 | [`local-dev-environment`](../skills/local-dev-environment/SKILL.md) | OPS + DISC | OPS | all builders | yes |
| 78 | [`pipeline-orchestration`](../skills/pipeline-orchestration/SKILL.md) (reference impl; Argo Workflows) | OPS + DATA | DE, OPS | ARC, AIE | yes |
| 79 | [`redpanda-apicurio-avro`](../skills/redpanda-apicurio-avro/SKILL.md) (reference impl) | STREAM + DATA | DE | BE, ARC, MLP | yes |
| 80 | [`starrocks-olap`](../skills/starrocks-olap/SKILL.md) (reference impl) | DATA + SEARCH | DE | AIE, MLP, BE, OPS | yes |
| 81 | [`stream-processing-consumers`](../skills/stream-processing-consumers/SKILL.md) (reference impl) | STREAM + DATA | DE | BE, AIE | yes |

> `decision-log` covers the system-of-record audit log where the product's Canon requires one (condition → recommendation → approval/edit → execution → reversal → outcome). `metric-engine` covers the single-source metric registry (`METRICS.md`) with cross-runtime parity. Vendor-named skills (`backend-fastify-trpc-grpc`, `clickhouse-olap`, `data-layer`, `devops-aws`, `event-driven-kafka`, `frontend-web`, `grpc-buf`, `llm-gateway`, `mobile-surface`, `oauth-implementation`, `python-services`, `turborepo`, and the Phase 2 data/ML seams `stream-processing-flink`, `batch-processing-spark`, `lakehouse-iceberg`, `graph-identity-neo4j`, `search-opensearch`, `feature-store-feast`, `vector-search-pgvector`, `workflow-engine-temporal`, `agent-orchestration-langgraph`, `ml-lifecycle`, and the Phase 6 stack bindings `starrocks-olap`, `redpanda-apicurio-avro`, `stream-processing-consumers`, `pipeline-orchestration`, `local-dev-environment`) are **reference implementations** of a seam — the patterns transfer; the product's `STACK.md` may bind the seam to different technology.

> The skill list above is generated from `skills/` — keep it in sync (CI: `knowledge_lint.py`). When a skill folder is added or removed from `skills/`, update this matrix.

---

## Skills by role (the agent's owned-skill list)

> Each agent's prompt embeds this exact list as its "auto-loaded skills." This is the source of truth — when you edit the matrix above, regenerate this section.

### Engineering Advisor (`cto-advisor` / `final-reviewer`)
- `engineering-discipline` (universal meta-rules)
- `code-review` (final review gate)
- `cost-routing-paradigms` (final effort-tier audit)
- `architecture-patterns` (architectural review)
- `tech-stack-evaluation` (rare; only when a new layer is proposed)
- `task-tracker-integration` (cross-team coordination)
- `subagent-orchestration` (persona-count + fan-out + stage-pipeline dispatch)
- `requirement-intake` (the Stage-1 conversion standard)
- `production-readiness-checklist` (the composed Stage-6 walk, via `final-reviewer`)
- `verification-before-completion` (always)

### Dynamic Persona Generator (`dynamic-persona-generator`)
- `dynamic-persona-spawning` (auto-loaded — the count rule, type selection, ≥1-concern contract)
*Plus: reads exactly the ONE domain skill matching its assigned persona lens at runtime (e.g. `compliance-officer` → `compliance-engine`).*

### Architect (`architect`)
- `architecture-patterns` (primary)
- `region-and-locale` (multi-region/locale from day one)
- `domain-driven-design` (mandatory — every backend service is bounded-context structured)
- `tech-stack-evaluation` (rare)
- `data-layer`
- `api-discipline`
- `engineering-discipline`
- `mcp-protocol` (external surfaces + building an MCP server)
- `subagent-orchestration` (splitting Stage 3 across builders + stage handoff)
- `cost-routing-paradigms` (effort-tier decision at design time)
- `writing-plans`
- `verification-before-completion`

### Backend Engineer (`backend-developer`)
- `backend-fastify-trpc-grpc` (primary — reference impl of the backend seam)
- `domain-driven-design` (every service is DDD-structured)
- `grpc-buf`
- `data-layer` (shared with ARC)
- `event-driven-kafka`
- `api-discipline` (pagination + rate-limiting)
- `idempotency-handling`
- `caching-strategy`
- `workflow-engine-temporal` (primary — durable workflows/sagas; shared with AIE, MLP, OPS)
- `search-opensearch` (primary — query + mapping; DE owns the indexing pipeline)
- `oauth-implementation` (shared with AIE)
- `operational-readiness` (incl. health-check endpoints; shared with OPS)
- `security-baseline` (shared with SEC)
- `engineering-discipline`
- `cost-routing-paradigms`
- `systematic-debugging` (incl. root-cause tracing)
- `verification-before-completion`

### Frontend/Web Engineer (`frontend-web-developer`)
- `frontend-web` (primary — reference impl of the web seam)
- `kpi-dashboard-design`
- `web-performance` (audit + optimization)
- `accessibility`
- `security-baseline` (incl. XSS prevention; shared with SEC)
- `auth-and-access` (sessions + RBAC; shared with SEC)
- `api-discipline` (consumer side)
- `region-and-locale` (locale-aware rendering)
- `engineering-discipline`
- `cost-routing-paradigms`
- `systematic-debugging`
- `verification-before-completion`

### Mobile Engineer (`mobile-developer`)
- `mobile-surface` (primary — reference impl of the mobile seam)
- `app-store-deployment` (shared with OPS)
- `accessibility`
- `security-baseline` (incl. mobile context; shared with SEC)
- `auth-and-access` (sessions + RBAC, mobile context; shared with SEC)
- `engineering-discipline`
- `cost-routing-paradigms`
- `kpi-dashboard-design`
- `systematic-debugging`
- `verification-before-completion`

### AI/ML Engineer (`intelligence-engineer`)
*Scope narrowed in the Phase 2 expansion: the data plane moved to the Data Engineer and the ML platform to the ML Platform Engineer. This role now owns the **model/agent layer + the analytics math** on top of those platforms, and remains the cost-routing champion.*
- `claude-api` (primary)
- `python-services` (primary — reference impl of the data/ML service seam)
- `llm-gateway` (shared with MLP)
- `llm-evals` (shared with QA, MLP)
- `agent-orchestration-langgraph` (builds agents on the MLP-owned runtime)
- `ml-lifecycle` (consumes — trains/promotes models on the MLP platform)
- `vector-search-pgvector` (consumes — RAG retrieval)
- `feature-store-feast` (consumes — training/serving features)
- `domain-driven-design`
- `mcp-protocol` (incl. building a new MCP server / tool surface)
- `clickhouse-olap` (analytics math; DE owns the pipelines that feed it)
- `metric-engine` (single-source metric registry + cross-runtime parity)
- `decision-log` (the system-of-record audit log — every recommendation/action is logged where the Canon requires it)
- `data-quality` (shared with DE)
- `experimentation-holdouts`
- `integration-connectors`
- `oauth-implementation` (shared with BE)
- `cost-routing-paradigms` (this is **the primary discipline** of this role)
- `engineering-discipline`
- `systematic-debugging`
- `verification-before-completion`

### Data Engineer (`data-engineer`)
*Phase 2 expansion role. Owns the **data plane** — every dataset the other layers read. Two laws: tenant-keyed everywhere; every dataset replayable (live + backfill share one code path).*
- `stream-processing-flink` (primary — reference impl of the stream seam)
- `stream-processing-consumers` (primary — the KafkaJS/consumer-group alternative to a framework)
- `batch-processing-spark` (primary — reference impl of the batch seam)
- `lakehouse-iceberg` (primary — reference impl of the lakehouse seam)
- `redpanda-apicurio-avro` (primary — the Redpanda+Apicurio backbone + Iceberg-Topics Bronze writer)
- `starrocks-olap` (primary — sub-second analytics serving over the lakehouse)
- `pipeline-orchestration` (primary — Argo Workflows job/data DAGs; shared with OPS)
- `graph-identity-neo4j` (primary — identity resolution)
- `event-driven-kafka` (shared with BE — consumes/produces the backbone)
- `clickhouse-olap` (builds the materializations AIE reads)
- `data-layer` (shared with ARC, BE)
- `search-opensearch` (indexing pipeline; shared with BE)
- `metric-engine` (stream/batch parity vs the single-source registry)
- `data-quality` (primary — freshness SLAs, assertions, reconciliation)
- `integration-connectors` (shared with AIE)
- `region-and-locale` (residency-pinned storage)
- `multi-tenancy-isolation` (tenant key on every pipeline/store)
- `cost-routing-paradigms`
- `engineering-discipline`
- `systematic-debugging`
- `verification-before-completion`

### ML Platform Engineer (`ml-platform-engineer`)
*Phase 2 expansion role. Owns the **ML platform** the AI/ML Engineer and Data Engineer self-serve on. Two laws: online/offline parity; gated promotion (ship only ≥ baseline).*
- `feature-store-feast` (primary — reference impl of the feature-store seam)
- `ml-lifecycle` (primary — registry + serving + gated promotion)
- `vector-search-pgvector` (primary — semantic retrieval store)
- `agent-orchestration-langgraph` (owns the runtime; AIE builds agents on it)
- `llm-gateway` (shared with AIE)
- `llm-evals` (the ship gate; shared with AIE, QA)
- `mcp-protocol` (tool surfaces for agents)
- `agentic-safety` (shared with SEC — tool blast-radius)
- `metric-engine` (the ML analogue: one feature definition, parity-checked)
- `data-quality` (drift monitoring; shared with DE)
- `multi-tenancy-isolation`
- `operational-readiness` (serving health probes)
- `cost-routing-paradigms` (co-champion with AIE — a trained model beats a frontier LLM for structured prediction)
- `engineering-discipline`
- `systematic-debugging`
- `verification-before-completion`

### Security Reviewer (`security-reviewer`)
- `security-baseline` (primary — VETO authority)
- `auth-and-access` (sessions + RBAC)
- `agentic-safety` (audit agent-emitted actions before ship)
- `oauth-implementation` (security review side)
- `multi-tenancy-isolation` (the tenant-isolation contract enforced at every layer — top VETO surface)
- `compliance-engine` (the product's compliance regime + PII lifecycle)
- `compliance-attestation`
- `engineering-discipline`
- `code-review` (security pass)
- `verification-before-completion`

### QA Engineer (`qa-agent`)
- `testing-tdd` (primary; incl. mutation testing)
- `api-discipline`
- `operational-readiness` (PASS verdict gate; incl. health checks)
- `verification-before-completion` (the core discipline of this role)
- `code-review`
- `engineering-discipline`
- `systematic-debugging` (incl. root-cause tracing)

### Platform/SRE (`platform-devops`)
- `devops-aws` (primary — reference impl of the infra seam)
- `observability` (primary; incl. structured logging)
- `turborepo`
- `progressive-delivery`
- `incident-response`
- `api-discipline` (gateway-level rate-limiting)
- `app-store-deployment` (shared with FEM)
- `security-baseline` (CI gates)
- `operational-readiness`
- `version-upgrade-policy`
- `finishing-a-development-branch` (Stage 8 commit/push discipline)
- `production-readiness-checklist` (re-confirmed at Stage 8; shared with CTOA)
- `release-notes-and-changelog` (Stage-8 output; shared with PM)
- `local-dev-environment` (primary — owns the Compose/LocalStack parity stack; all builders consume)
- `pipeline-orchestration` (the Argo Workflows cluster; shared with DE)
- `engineering-discipline`
- `verification-before-completion`

### Delivery Coordinator (`product-manager`)
- `task-tracker-integration` (primary)
- `writing-plans`
- `requirement-intake` (shared with CTOA — the intake standard when mirroring scope)
- `release-notes-and-changelog` (audience-split notes; shared with OPS)
- `engineering-discipline`
- `kpi-dashboard-design` (coordination perspective)
- `experimentation-holdouts` (coordination perspective)

---

## Shared & cross-cutting skills

Some skills are so foundational that **every role auto-loads them**. These are loaded once at the start of every task by every agent:

1. `engineering-discipline` — the universal meta-rules.
2. `verification-before-completion` — the "valid verification" iron law.
3. `cost-routing-paradigms` — for any role that touches code, this is mandatory.
4. `observability` — every code path emits metrics/logs/traces.
5. `security-baseline` — the security gate applies to everyone.

> Loading discipline: at session start, the agent reads these first, then its role-specific list, then any skills implied by the requirement (looked up via the domain key + free-text matching against skill descriptions).

---

## Recommended additional skills — ALL IMPLEMENTED (Phase 5)

The four skills this section used to flag are now implemented and mapped (rows 73–76 above): `requirement-intake` (CTOA/PM), `dynamic-persona-spawning` (DYN — auto-loaded by the persona agent), `production-readiness-checklist` (CTOA/OPS — the composed Stage-6 walk), `release-notes-and-changelog` (OPS/PM — Stage-8 output). The agentic **Foundation** phase also shipped as the `/foundation` command-skill (drafts the whole Product Canon from a brief + repo scan; Stakeholder approves per file).

---

## Notes on ambiguous mappings

A few mappings deserve explicit explanation (the exact ownership depends on the product's `STACK.md` — the notes below describe the reference instantiation):

- **`integration-connectors`** is **AIE-owned** when the connector/ingestion layer is implemented in the AI/ML Engineer's runtime; the Backend Engineer consumes the canonicalized output and is in *shared with* so they can debug downstream issues.
- **`clickhouse-olap`** (a reference impl of the OLAP seam) is primarily **AIE** when the analytics layer lives in that role's runtime. The Backend Engineer still pairs on schema decisions during the architecture phase (shared with).
- **`oauth-implementation`** is primarily **AIE** when the connectors live in that runtime; **SEC** reviews the implementation; **BE** is shared when backend-side OAuth flows are needed.
- **`engineering-discipline`** and **`verification-before-completion`** are **universal**. They are baked into the system prompt itself (see [prompts/system-prompt.md](../prompts/system-prompt.md)).

---

## How the matrix is consumed

1. **Static (build time):** Each agent prompt in [`agents/`](../agents/) embeds its owned-skill list from the table above.
2. **Dynamic (runtime):**
   - When a requirement is intaken (Stage 1), the Engineering Advisor uses the **Domain key** to identify which roles must be involved.
   - When a developer agent picks up a task, it auto-loads its owned skills + any skills whose **description** matches keywords in the requirement.
   - The **Shared with** column tells an agent when to request peer review even if no failing gate triggers.

Update this matrix whenever a domain skill is added to or removed from `skills/`. (A CI check that fails when a skill folder isn't mapped here is planned — see ROADMAP.)

---

## Next

[role-empowerment-model.md](role-empowerment-model.md) describes *how* each agent uses its skills during execution — when to load, when to challenge, when to escalate.
