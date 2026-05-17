# Section 2.1 — Skill Mapping Matrix

This document is the **authoritative skill-to-role binding** for the Brain Engineering OS. Every one of the 53 curated skills in [`Requirements/skills/`](../Requirements/skills/) is mapped to:

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
| **CTOA** | (Shadow — Rishabh's) | CTO Advisor |
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

## The matrix (all 53 skills)

| # | Skill | Domain | Primary | Shared with | Exposed as `/skill` |
|---|-------|--------|---------|-------------|---------------------|
| 1 | [`access-control-rbac`](../skills/access-control-rbac/SKILL.md) | SEC | SEC | ARC, BE, AIE | yes |
| 2 | [`agentic-design`](../skills/agentic-design/SKILL.md) | AI | AIE | ARC, CTOA | yes |
| 3 | [`api-contract-testing`](../skills/api-contract-testing/SKILL.md) | TEST | QA | BE, AIE, ARC | yes |
| 4 | [`api-pagination`](../skills/api-pagination/SKILL.md) | BE | BE | AIE, FEW, FEM | yes |
| 5 | [`api-rate-limiting`](../skills/api-rate-limiting/SKILL.md) | BE | BE | OPS, SEC | yes |
| 6 | [`api-versioning-strategy`](../skills/api-versioning-strategy/SKILL.md) | ARCH | ARC | BE, AIE, CTOA | yes |
| 7 | [`app-store-deployment`](../skills/app-store-deployment/SKILL.md) | OPS | OPS | FEM | yes |
| 8 | [`architecture-patterns`](../skills/architecture-patterns/SKILL.md) | ARCH | ARC | CTOA, BE, AIE | yes |
| 9 | [`backend-fastify-trpc-grpc`](../skills/backend-fastify-trpc-grpc/SKILL.md) | BE | BE | ARC | yes |
| 10 | [`claude-api`](../skills/claude-api/SKILL.md) | AI | AIE | ARC, OPS (cost monitoring) | yes |
| 11 | [`clickhouse-olap`](../skills/clickhouse-olap/SKILL.md) | DATA | AIE | BE, ARC | yes |
| 12 | [`code-review`](../skills/code-review/SKILL.md) | DISC | CTOA | QA, ARC, all devs | yes (`/review` already) |
| 13 | [`cost-routing-paradigms`](../skills/cost-routing-paradigms/SKILL.md) | DISC + AI | CTOA, AIE | all devs, QA, OPS | yes |
| 14 | [`database-design`](../skills/database-design/SKILL.md) | DATA | ARC | BE, AIE, SEC | yes |
| 15 | [`defense-in-depth-validation`](../skills/defense-in-depth-validation/SKILL.md) | SEC | SEC | BE, AIE, QA | yes |
| 16 | [`devops-aws`](../skills/devops-aws/SKILL.md) | OPS | OPS | ARC | yes |
| 17 | [`engineering-discipline`](../skills/engineering-discipline/SKILL.md) | DISC | CTOA | **ALL** roles | yes |
| 18 | [`event-driven-kafka`](../skills/event-driven-kafka/SKILL.md) | DATA + BE | BE | AIE, ARC, OPS | yes |
| 19 | [`forecasting-prophet`](../skills/forecasting-prophet/SKILL.md) | AI | AIE | — | yes |
| 20 | [`frontend-mobile`](../skills/frontend-mobile/SKILL.md) | FE-M | FEM | ARC, QA | yes |
| 21 | [`frontend-web`](../skills/frontend-web/SKILL.md) | FE-W | FEW | ARC, QA | yes |
| 22 | [`grpc-buf`](../skills/grpc-buf/SKILL.md) | BE | BE | AIE, ARC | yes |
| 23 | [`health-check-endpoints`](../skills/health-check-endpoints/SKILL.md) | OBS + OPS | OPS | BE, AIE | yes |
| 24 | [`idempotency-handling`](../skills/idempotency-handling/SKILL.md) | BE | BE | AIE, QA | yes |
| 25 | [`india-commerce-economics`](../skills/india-commerce-economics/SKILL.md) | PROD | CTOA | **ALL** roles (it's the moat) | yes |
| 26 | [`integration-connectors`](../skills/integration-connectors/SKILL.md) | INTG | AIE (ingestion-service is Python) | BE, ARC | yes |
| 27 | [`kpi-dashboard-design`](../skills/kpi-dashboard-design/SKILL.md) | FE-W + PROD | FEW | FEM, PM | yes |
| 28 | [`lifecycle-revenue-layer`](../skills/lifecycle-revenue-layer/SKILL.md) | AI + PROD | AIE | BE, SEC (compliance engine) | yes |
| 29 | [`logging-best-practices`](../skills/logging-best-practices/SKILL.md) | OBS | OPS | BE, AIE | yes |
| 30 | [`mcp-protocol`](../skills/mcp-protocol/SKILL.md) | AI + ARCH | AIE | ARC, BE | yes |
| 31 | [`mobile-offline-support`](../skills/mobile-offline-support/SKILL.md) | FE-M | FEM | — | yes |
| 32 | [`morning-brief-mobile`](../skills/morning-brief-mobile/SKILL.md) | FE-M + AI + PROD | FEM | AIE, FEW (parity), PM | yes |
| 33 | [`mutation-testing`](../skills/mutation-testing/SKILL.md) | TEST | QA | BE, AIE | yes |
| 34 | [`oauth-implementation`](../skills/oauth-implementation/SKILL.md) | SEC + INTG | AIE | BE, SEC | yes |
| 35 | [`observability`](../skills/observability/SKILL.md) | OBS | OPS | **ALL** roles | yes |
| 36 | [`operational-readiness`](../skills/operational-readiness/SKILL.md) | OPS + DISC | OPS, QA | all devs, CTOA | yes |
| 37 | [`push-notification-setup`](../skills/push-notification-setup/SKILL.md) | FE-M | FEM | BE (notifications-service) | yes |
| 38 | [`python-services`](../skills/python-services/SKILL.md) | BE | AIE | BE (parity), ARC | yes |
| 39 | [`root-cause-tracing`](../skills/root-cause-tracing/SKILL.md) | DISC | all devs, QA, SEC | — | yes |
| 40 | [`security-baseline`](../skills/security-baseline/SKILL.md) | SEC | SEC | **ALL** roles (every build passes this gate) | yes |
| 41 | [`session-management`](../skills/session-management/SKILL.md) | SEC | SEC | BE, FEW, FEM | yes |
| 42 | [`sql-query-optimization`](../skills/sql-query-optimization/SKILL.md) | PERF + DATA | BE, AIE | ARC | yes |
| 43 | [`supabase-postgres-best-practices`](../skills/supabase-postgres-best-practices/SKILL.md) | DATA | BE | AIE, ARC, SEC | yes |
| 44 | [`systematic-debugging`](../skills/systematic-debugging/SKILL.md) | DISC | all devs, QA | CTOA | yes |
| 45 | [`task-tracker-integration`](../skills/task-tracker-integration/SKILL.md) | DISC + OPS | PM | OPS, CTOA | yes |
| 46 | [`tech-stack-evaluation`](../skills/tech-stack-evaluation/SKILL.md) | ARCH | ARC | CTOA | yes (rarely used) |
| 47 | [`testing-tdd`](../skills/testing-tdd/SKILL.md) | TEST | QA | all devs | yes |
| 48 | [`turborepo`](../skills/turborepo/SKILL.md) | OPS | OPS | BE, FEW, FEM | yes |
| 49 | [`verification-before-completion`](../skills/verification-before-completion/SKILL.md) | DISC | **ALL** roles | — | yes |
| 50 | [`vulnerability-scanning`](../skills/vulnerability-scanning/SKILL.md) | SEC | SEC | OPS | yes |
| 51 | [`web-performance-audit`](../skills/web-performance-audit/SKILL.md) | PERF | FEW | QA, OPS | yes |
| 52 | [`web-performance-optimization`](../skills/web-performance-optimization/SKILL.md) | PERF + FE-W | FEW | ARC | yes |
| 53 | [`writing-plans`](../skills/writing-plans/SKILL.md) | DISC | PM, ARC | **ALL** roles (every plan-emitting agent) | yes |
| 54 | [`xss-prevention`](../skills/xss-prevention/SKILL.md) | SEC + FE-W | SEC | FEW, FEM | yes |

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
- `verification-before-completion` (always)

### Dynamic Persona Generator (`dynamic-persona-generator`)
*No fixed skills — selects 3 personas at runtime based on the requirement. May invoke any of the 53 skills indirectly via the spawned persona.*

### Architect — Aryan (`architect`)
- `architecture-patterns` (primary)
- `tech-stack-evaluation` (rare)
- `database-design`
- `api-versioning-strategy`
- `engineering-discipline`
- `agentic-design` (when designing AI surfaces)
- `mcp-protocol` (when external surfaces are touched)
- `cost-routing-paradigms` (paradigm decision at design time)
- `india-commerce-economics`
- `writing-plans`
- `verification-before-completion`

### Backend Developer — Vikram (`backend-developer`)
- `backend-fastify-trpc-grpc` (primary)
- `grpc-buf`
- `supabase-postgres-best-practices`
- `database-design` (shared with ARC)
- `event-driven-kafka`
- `api-pagination`
- `api-rate-limiting`
- `idempotency-handling`
- `oauth-implementation` (shared with AIE)
- `sql-query-optimization` (shared with AIE)
- `health-check-endpoints` (shared with OPS)
- `defense-in-depth-validation` (shared with SEC)
- `engineering-discipline`
- `india-commerce-economics`
- `cost-routing-paradigms`
- `systematic-debugging`
- `root-cause-tracing`
- `verification-before-completion`

### Frontend Web Developer — Ananya (`frontend-web-developer`)
- `frontend-web` (primary)
- `kpi-dashboard-design`
- `web-performance-optimization`
- `web-performance-audit`
- `xss-prevention` (shared with SEC)
- `session-management` (shared with SEC)
- `api-pagination` (consumer side)
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
- `xss-prevention` (shared with SEC, RN context)
- `session-management` (shared with SEC, mobile context)
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
- `mcp-protocol`
- `clickhouse-olap`
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
- `access-control-rbac`
- `defense-in-depth-validation`
- `vulnerability-scanning`
- `xss-prevention`
- `session-management`
- `oauth-implementation` (security review side)
- `india-commerce-economics` (DLT/NCPR/DND compliance is hers)
- `engineering-discipline`
- `code-review` (security pass)
- `verification-before-completion`

### QA Agent — Tanvi (`qa-agent`)
- `testing-tdd` (primary)
- `api-contract-testing`
- `mutation-testing`
- `operational-readiness` (PASS verdict gate)
- `verification-before-completion` (her core discipline)
- `code-review`
- `engineering-discipline`
- `india-commerce-economics`
- `systematic-debugging`
- `root-cause-tracing`

### Platform / DevOps — Jatin (`platform-devops`)
- `devops-aws` (primary)
- `observability` (primary)
- `logging-best-practices`
- `health-check-endpoints`
- `turborepo`
- `api-rate-limiting` (gateway-level enforcement)
- `app-store-deployment` (shared with FEM)
- `vulnerability-scanning` (CI gates)
- `operational-readiness`
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

## Recommended additional skills (NOT sourced from `Requirements/skills/` — see [folder-context-summary.md](folder-context-summary.md))

Four candidate skills are flagged but not implemented in this build:

| Suggested skill | Primary | Why |
|-----------------|---------|-----|
| `requirement-intake` | CTOA, PM | Standard for converting a Founder ask into a structured requirement. |
| `dynamic-persona-spawning` | DYN | Discipline for choosing which 3 personas to spawn and how to weight inputs. |
| `production-readiness-checklist` | CTOA, OPS | Composed Stage 6 gate aggregating `operational-readiness` + `health-check-endpoints` + `observability` + `vulnerability-scanning`. |
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

The matrix is rebuilt whenever a new skill is added to `Requirements/skills/`. A CI check ([`hooks/`](../hooks/)) detects new skill folders and fails CI until this matrix is updated.

---

## Next

[role-empowerment-model.md](role-empowerment-model.md) describes *how* each agent uses its skills during execution — when to load, when to challenge, when to escalate.
