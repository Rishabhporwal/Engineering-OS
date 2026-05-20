# Section 2.1 — Skill Mapping Matrix

This document is the **authoritative skill-to-role binding** for the Brain Engineering OS. It maps every one of the **55 domain skills** in [`skills/`](../skills/). (The **27 command-skills** carrying `disable-model-invocation: true` — requirement, status, recall, handoff, approve, reject, deploy, rollback, persona, invoke-skill, eos-init, propose-rule, adopt-rule, reject-rule, plus recall-similar, reindex, qa-browser, design-review, worker-test-gap, worker-canon-drift, worker-compliance-drift, test-pipeline, resume, new-skill, team-digest, watch, monitor — are human/schedule-triggered and not mapped here. 55 + 27 = 82 skill folders.) Each domain skill is mapped to:

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
| **BE** | Backend (Node + Python services, APIs, OLTP) |
| **FE-W** | Frontend (web — Next.js) |
| **FE-M** | Frontend (mobile — RN + Expo) |
| **DATA** | Data layer (OLTP, OLAP, schema, query optimization) |
| **AI** | AI/LLM/agents (intelligence-service) |
| **SEC** | Security & compliance |
| **OBS** | Observability (logs, metrics, traces, errors, dashboards) |
| **TEST** | Testing & verification |
| **PERF** | Performance (web + SQL) |
| **OPS** | DevOps / infra / deployment |
| **INTG** | Integrations / connectors |
| **DISC** | Engineering discipline / process |
| **PROD** | Product / business domain knowledge |

## Role key

| Code | Persona | Title |
|------|---------|-------|
| **CTOA** | Rohan | CTO Advisor |
| **ARC** | Aryan | Architect |
| **BE** | Vikram | Backend Developer |
| **FEW** | Ananya | Frontend Web Developer |
| **FEM** | Karan | Mobile Developer |
| **AIE** | Maya | Intelligence Engineer |
| **SEC** | Shreya | Security Reviewer |
| **QA** | Tanvi | QA Agent |
| **OPS** | Jatin | Platform / DevOps |
| **PM** | Priya | Product Manager |
| **DYN** | (runtime) | Dynamic Persona |

---

## The matrix (55 domain skills)

| # | Skill | Domain | Primary | Shared with | Exposed as command |
|---|-------|--------|---------|-------------|---------------------|
| 1 | [`agentic-actions-auditor`](../skills/agentic-actions-auditor/SKILL.md) | SEC + AI | SEC | AIE, ARC | yes |
| 2 | [`agentic-design`](../skills/agentic-design/SKILL.md) | AI | AIE | ARC, CTOA | yes |
| 3 | [`api-contract-testing`](../skills/api-contract-testing/SKILL.md) | TEST | QA | BE, AIE, ARC | yes |
| 4 | [`api-traffic-patterns`](../skills/api-traffic-patterns/SKILL.md) (pagination + rate-limiting) | BE | BE | AIE, FEW, FEM, OPS, SEC | yes |
| 5 | [`api-versioning-strategy`](../skills/api-versioning-strategy/SKILL.md) | ARCH | ARC | BE, AIE, CTOA | yes |
| 6 | [`app-store-deployment`](../skills/app-store-deployment/SKILL.md) | OPS | OPS | FEM | yes |
| 7 | [`architecture-patterns`](../skills/architecture-patterns/SKILL.md) | ARCH | ARC | CTOA, BE, AIE | yes |
| 8 | [`auth-and-access`](../skills/auth-and-access/SKILL.md) (sessions + RBAC) | SEC | SEC | BE, FEW, FEM, AIE, ARC | yes |
| 9 | [`backend-fastify-trpc-grpc`](../skills/backend-fastify-trpc-grpc/SKILL.md) | BE | BE | ARC | yes |
| 10 | [`claude-api`](../skills/claude-api/SKILL.md) | AI | AIE | ARC, OPS (cost monitoring) | yes |
| 11 | [`clickhouse-olap`](../skills/clickhouse-olap/SKILL.md) | DATA | AIE | BE, ARC | yes |
| 12 | [`code-review`](../skills/code-review/SKILL.md) | DISC | CTOA | QA, ARC, all devs | yes |
| 13 | [`cost-routing-paradigms`](../skills/cost-routing-paradigms/SKILL.md) | DISC + AI | CTOA, AIE | all devs, QA, OPS | yes |
| 14 | [`database-design`](../skills/database-design/SKILL.md) (incl. Supabase/Postgres patterns) | DATA | ARC | BE, AIE, SEC | yes |
| 15 | [`defense-in-depth-validation`](../skills/defense-in-depth-validation/SKILL.md) (incl. XSS prevention) | SEC | SEC | BE, AIE, QA, FEW, FEM | yes |
| 16 | [`devops-aws`](../skills/devops-aws/SKILL.md) | OPS | OPS | ARC | yes |
| 17 | [`domain-driven-design`](../skills/domain-driven-design/SKILL.md) | ARCH | ARC | **ALL** builders | yes |
| 18 | [`engineering-discipline`](../skills/engineering-discipline/SKILL.md) | DISC | CTOA | **ALL** roles | yes |
| 19 | [`event-driven-kafka`](../skills/event-driven-kafka/SKILL.md) | DATA + BE | BE | AIE, ARC, OPS | yes |
| 20 | [`finishing-a-development-branch`](../skills/finishing-a-development-branch/SKILL.md) | OPS + DISC | OPS | **ALL** (commit discipline) | yes |
| 21 | [`forecasting-prophet`](../skills/forecasting-prophet/SKILL.md) | AI | AIE | — | yes |
| 22 | [`frontend-mobile`](../skills/frontend-mobile/SKILL.md) | FE-M | FEM | ARC, QA | yes |
| 23 | [`frontend-web`](../skills/frontend-web/SKILL.md) | FE-W | FEW | ARC, QA | yes |
| 24 | [`grpc-buf`](../skills/grpc-buf/SKILL.md) | BE | BE | AIE, ARC | yes |
| 25 | [`idempotency-handling`](../skills/idempotency-handling/SKILL.md) | BE | BE | AIE, QA | yes |
| 26 | [`india-commerce-economics`](../skills/india-commerce-economics/SKILL.md) | PROD | CTOA | **ALL** roles (the moat) | yes |
| 27 | [`integration-connectors`](../skills/integration-connectors/SKILL.md) | INTG | AIE | BE, ARC | yes |
| 28 | [`kpi-dashboard-design`](../skills/kpi-dashboard-design/SKILL.md) | FE-W + PROD | FEW | FEM, PM | yes |
| 29 | [`lifecycle-revenue-layer`](../skills/lifecycle-revenue-layer/SKILL.md) | AI + PROD | AIE | BE, SEC | yes |
| 30 | [`mcp-protocol`](../skills/mcp-protocol/SKILL.md) (incl. building an MCP server) | AI + ARCH | AIE | ARC, BE | yes |
| 31 | [`mobile-offline-support`](../skills/mobile-offline-support/SKILL.md) | FE-M | FEM | — | yes |
| 32 | [`morning-brief-mobile`](../skills/morning-brief-mobile/SKILL.md) | FE-M + AI + PROD | FEM | AIE, FEW, PM | yes |
| 33 | [`oauth-implementation`](../skills/oauth-implementation/SKILL.md) | SEC + INTG | AIE | BE, SEC | yes |
| 34 | [`observability`](../skills/observability/SKILL.md) (incl. structured logging) | OBS | OPS | **ALL** roles | yes |
| 35 | [`operational-readiness`](../skills/operational-readiness/SKILL.md) (incl. health-check endpoints) | OPS + OBS | OPS, QA | all devs, CTOA, BE, AIE | yes |
| 36 | [`push-notification-setup`](../skills/push-notification-setup/SKILL.md) | FE-M | FEM | BE (notifications-service) | yes |
| 37 | [`python-services`](../skills/python-services/SKILL.md) | BE | AIE | BE (parity), ARC | yes |
| 38 | [`security-baseline`](../skills/security-baseline/SKILL.md) | SEC | SEC | **ALL** roles | yes |
| 39 | [`sql-query-optimization`](../skills/sql-query-optimization/SKILL.md) | PERF + DATA | BE, AIE | ARC | yes |
| 40 | [`subagent-orchestration`](../skills/subagent-orchestration/SKILL.md) (fan-out + pipeline dispatch) | DISC | CTOA | ARC | yes |
| 41 | [`systematic-debugging`](../skills/systematic-debugging/SKILL.md) (incl. root-cause tracing) | DISC | all devs, QA | CTOA, SEC | yes |
| 42 | [`task-tracker-integration`](../skills/task-tracker-integration/SKILL.md) | DISC + OPS | PM | OPS, CTOA | yes |
| 43 | [`tech-stack-evaluation`](../skills/tech-stack-evaluation/SKILL.md) | ARCH | ARC | CTOA | yes (rare) |
| 44 | [`testing-tdd`](../skills/testing-tdd/SKILL.md) (incl. mutation testing) | TEST | QA | all devs, AIE | yes |
| 45 | [`turborepo`](../skills/turborepo/SKILL.md) | OPS | OPS | BE, FEW, FEM | yes |
| 46 | [`verification-before-completion`](../skills/verification-before-completion/SKILL.md) | DISC | **ALL** roles | — | yes |
| 47 | [`vulnerability-scanning`](../skills/vulnerability-scanning/SKILL.md) | SEC | SEC | OPS | yes |
| 48 | [`web-performance`](../skills/web-performance/SKILL.md) (audit + optimization) | PERF + FE-W | FEW | QA, OPS, ARC | yes |
| 49 | [`writing-plans`](../skills/writing-plans/SKILL.md) | DISC | PM, ARC | **ALL** plan-emitting agents | yes |
| 50 | [`caching-strategy`](../skills/caching-strategy/SKILL.md) | DATA + PERF | BE | AIE, OPS, SEC | yes |
| 51 | [`metric-engine`](../skills/metric-engine/SKILL.md) | DATA + AI + PROD | AIE | BE, QA, FEW | yes |
| 52 | [`region-adapter`](../skills/region-adapter/SKILL.md) | ARCH | ARC | CTOA, **ALL** builders | yes |
| 53 | [`multi-tenancy-isolation`](../skills/multi-tenancy-isolation/SKILL.md) | SEC + DATA | SEC | ARC, BE, AIE, **ALL** | yes |
| 54 | [`memory-layer-pgvector`](../skills/memory-layer-pgvector/SKILL.md) | AI + DATA | AIE | ARC | yes |
| 55 | [`data-privacy-dpdp`](../skills/data-privacy-dpdp/SKILL.md) | SEC + PROD | SEC | AIE, **ALL** | yes |

> v0.7.1 consolidation: 10 merge groups folded 59 domain skills → 49 (clean 1–49 numbering). Absorbed: root-cause-tracing→systematic-debugging, supabase-postgres-best-practices→database-design, health-check-endpoints→operational-readiness, mutation-testing→testing-tdd, logging-best-practices→observability, mcp-builder→mcp-protocol, xss-prevention→defense-in-depth-validation. New merged folders: api-traffic-patterns (pagination+rate-limiting), auth-and-access (sessions+RBAC), subagent-orchestration (dispatching+subagent-driven-development).

---

## Skills by role (the agent's owned-skill list)

> Each agent's prompt embeds this exact list as its "auto-loaded skills." This is the source of truth — when you edit the matrix above, regenerate this section.

### CTO Advisor (`cto-advisor`)
- `engineering-discipline` (universal meta-rules)
- `code-review` (final review gate)
- `cost-routing-paradigms` (final cost-routing audit)
- `india-commerce-economics` (the moat — challenges any requirement that misses it)
- `architecture-patterns` (architectural review)
- `tech-stack-evaluation` (rare; only when a new layer is proposed)
- `task-tracker-integration` (cross-team coordination)
- `agentic-design` (when reviewing AI surfaces)
- `subagent-orchestration` (persona-count + fan-out + stage-pipeline dispatch)
- `verification-before-completion` (always)

### Dynamic Persona Generator (`dynamic-persona-generator`)
*No fixed skills — selects 0–2 personas at runtime based on the requirement's complexity. May invoke any of the domain skills indirectly via the spawned persona.*

### Architect — Aryan (`architect`)
- `architecture-patterns` (primary)
- `region-adapter` (multi-region from day one)
- `domain-driven-design` (mandatory — every backend service is bounded-context structured)
- `tech-stack-evaluation` (rare)
- `database-design`
- `api-versioning-strategy`
- `engineering-discipline`
- `agentic-design` (when designing AI surfaces)
- `mcp-protocol` (external surfaces + building an MCP server)
- `subagent-orchestration` (splitting Stage 3 across builders + stage handoff)
- `cost-routing-paradigms` (paradigm decision at design time)
- `india-commerce-economics`
- `writing-plans`
- `verification-before-completion`

### Backend Developer — Vikram (`backend-developer`)
- `backend-fastify-trpc-grpc` (primary)
- `domain-driven-design` (every service he builds is DDD-structured)
- `grpc-buf`
- `database-design` (shared with ARC; incl. Supabase/Postgres patterns)
- `event-driven-kafka`
- `api-traffic-patterns` (pagination + rate-limiting)
- `idempotency-handling`
- `caching-strategy` (ElastiCache/Redis)
- `oauth-implementation` (shared with AIE)
- `sql-query-optimization` (shared with AIE)
- `operational-readiness` (incl. health-check endpoints; shared with OPS)
- `defense-in-depth-validation` (shared with SEC)
- `engineering-discipline`
- `india-commerce-economics`
- `cost-routing-paradigms`
- `systematic-debugging` (incl. root-cause tracing)
- `verification-before-completion`

### Frontend Web Developer — Ananya (`frontend-web-developer`)
- `frontend-web` (primary)
- `kpi-dashboard-design`
- `web-performance` (audit + optimization)
- `defense-in-depth-validation` (incl. XSS prevention; shared with SEC)
- `auth-and-access` (sessions + RBAC; shared with SEC)
- `api-traffic-patterns` (consumer side)
- `engineering-discipline`
- `india-commerce-economics`
- `cost-routing-paradigms`
- `systematic-debugging`
- `verification-before-completion`

### Mobile Developer — Karan (`mobile-developer`)
- `frontend-mobile` (primary)
- `morning-brief-mobile` (primary — this is *the* product surface)
- `mobile-offline-support`
- `push-notification-setup`
- `app-store-deployment` (shared with OPS)
- `defense-in-depth-validation` (incl. XSS, RN context; shared with SEC)
- `auth-and-access` (sessions + RBAC, mobile context; shared with SEC)
- `engineering-discipline`
- `india-commerce-economics`
- `cost-routing-paradigms`
- `kpi-dashboard-design` (Morning Brief design)
- `systematic-debugging`
- `verification-before-completion`

### Intelligence Engineer — Maya (`intelligence-engineer`)
- `agentic-design` (primary)
- `claude-api` (primary)
- `python-services` (primary — intelligence-service is Python)
- `domain-driven-design` (her Python services are DDD-structured too)
- `mcp-protocol` (incl. building a new MCP server / tool surface)
- `clickhouse-olap`
- `metric-engine` (Formula Book + TS↔Python parity)
- `memory-layer-pgvector` (Brand Fingerprint)
- `forecasting-prophet`
- `lifecycle-revenue-layer` (when the agent affects revenue)
- `integration-connectors` (ingestion-service is Python; Maya owns Python connectors)
- `oauth-implementation` (shared with BE)
- `sql-query-optimization` (shared with BE)
- `cost-routing-paradigms` (this is **her primary discipline**)
- `engineering-discipline`
- `india-commerce-economics`
- `systematic-debugging`
- `verification-before-completion`

### Security Reviewer — Shreya (`security-reviewer`)
- `security-baseline` (primary — Shreya VETO authority)
- `auth-and-access` (sessions + RBAC)
- `defense-in-depth-validation` (incl. XSS prevention)
- `vulnerability-scanning`
- `agentic-actions-auditor` (audit agent-emitted actions before ship)
- `oauth-implementation` (security review side)
- `india-commerce-economics` (DLT/NCPR/DND compliance is hers)
- `multi-tenancy-isolation` (the 4-layer workspace_id contract — top VETO surface)
- `data-privacy-dpdp` (India DPDP Act + PII lifecycle)
- `engineering-discipline`
- `code-review` (security pass)
- `verification-before-completion`

### QA Agent — Tanvi (`qa-agent`)
- `testing-tdd` (primary; incl. mutation testing)
- `api-contract-testing`
- `operational-readiness` (PASS verdict gate; incl. health checks)
- `verification-before-completion` (her core discipline)
- `code-review`
- `engineering-discipline`
- `india-commerce-economics`
- `systematic-debugging` (incl. root-cause tracing)

### Platform / DevOps — Jatin (`platform-devops`)
- `devops-aws` (primary)
- `observability` (primary; incl. structured logging)
- `turborepo`
- `api-traffic-patterns` (gateway-level rate-limiting)
- `app-store-deployment` (shared with FEM)
- `vulnerability-scanning` (CI gates)
- `operational-readiness`
- `finishing-a-development-branch` (Stage 8 commit/push discipline)
- `engineering-discipline`
- `verification-before-completion`

### Product Manager — Priya (`product-manager`)
- `task-tracker-integration` (primary)
- `engineering-discipline`
- `india-commerce-economics`
- `kpi-dashboard-design` (PM perspective)
- `morning-brief-mobile` (PM perspective on the product surface)
- `lifecycle-revenue-layer` (PM perspective)

---

## Shared & cross-cutting skills

Some skills are so foundational that **every role auto-loads them**. These are loaded once at the start of every task by every agent:

1. `engineering-discipline` — the 7 universal meta-rules.
2. `india-commerce-economics` — the moat; even non-India work needs context.
3. `verification-before-completion` — Iron Law #5.
4. `cost-routing-paradigms` — for any role that touches code, this is mandatory.
5. `observability` — every code path emits metrics/logs/traces.
6. `security-baseline` — security gate applies to everyone.

> Loading discipline: at session start, the agent reads these 6 first, then its role-specific list, then any skills implied by the requirement (looked up via the domain key + free-text matching against skill descriptions).

---

## Recommended additional skills (not yet implemented)

Four candidate skills are flagged but not implemented in this build:

| Suggested skill | Primary | Why |
|-----------------|---------|-----|
| `requirement-intake` | CTOA, PM | Standard for converting a Founder ask into a structured requirement. |
| `dynamic-persona-spawning` | DYN | Discipline for choosing the 0–2 personas to spawn and how to weight inputs. |
| `production-readiness-checklist` | CTOA, OPS | Composed Stage 6 gate aggregating `operational-readiness` (incl. health checks) + `observability` + `vulnerability-scanning`. |
| `release-notes-and-changelog` | OPS, PM | Human-readable release notes derived from per-run journals at Stage 8. |

Founder may approve creating these in V2.

---

## Notes on ambiguous mappings

A few mappings deserve explicit explanation:

- **`integration-connectors`** is **AIE-owned**, not BE-owned, because `ingestion-service` is Python (per `BRAIN_TECHNICAL.md` §4) and Maya owns the Python service. Vikram (BE) consumes the canonicalized output via Kafka but doesn't author the connector itself. Vikram is in *shared with* so he can debug downstream issues.
- **`clickhouse-olap`** is primarily **AIE** because `analytics-service` is Python. Vikram still pairs on schema decisions during architecture phase (shared with).
- **`oauth-implementation`** is primarily **AIE** (Phase 0–1 connectors live in `ingestion-service`, Python). **SEC** reviews the implementation; **BE** is shared when Node-side OAuth flows are needed (rare in current scope).
- **`india-commerce-economics`** appears as *shared with **ALL** roles* deliberately. Even a frontend chart needs to render ₹ with Indian numbering, RAG indicators for festival multipliers, and RTO-adjusted CM. Even a CI test needs to assert IST timezone discipline. It is not optional for anyone working on Brain.
- **`engineering-discipline`** and **`verification-before-completion`** are similarly **universal**. They are baked into the system prompt itself (see [prompts/system-prompt.md](../prompts/system-prompt.md)).

---

## How the matrix is consumed

1. **Static (build time):** Each agent prompt in [`agents/`](../agents/) embeds its owned-skill list from the table above.
2. **Dynamic (runtime):**
   - When a requirement is intaken (Stage 1), the CTO Advisor uses the **Domain key** to identify which roles must be involved.
   - When a developer agent picks up a task, it auto-loads its owned skills + any skills whose **description** matches keywords in the requirement.
   - The **Shared with** column tells an agent when to request peer review even if no failing gate triggers.

Update this matrix whenever a domain skill is added to or removed from `skills/`. (A CI check that fails when a skill folder isn't mapped here is planned for V2 — see ROADMAP.)

---

## Next

[role-empowerment-model.md](role-empowerment-model.md) describes *how* each agent uses its skills during execution — when to load, when to challenge, when to escalate.
