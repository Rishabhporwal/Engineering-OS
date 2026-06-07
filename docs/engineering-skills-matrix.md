# Engineering Skills Matrix

> **Scope.** The competency, ownership, and growth model for the Engineering OS team — a fixed roster of agent-roles that takes any requirement from intake to production for a **high-scale, AI-native, cloud-native SaaS** product. Where [`skill-mapping-matrix.md`](skill-mapping-matrix.md) answers *which skill belongs to whom* and [`role-empowerment-model.md`](role-empowerment-model.md) answers *what each role does with it*, this document answers **how deep each role must be, who backs them up, where the gaps are, and how each role grows.**
>
> **Subject of the matrix.** Proficiency is assigned to the **EOS agent-roles** (the team members of this OS). Each agent-role also stands in for a recognised human discipline (noted per role) — so this doubles as a hiring/leveling reference when the OS is operated by, or alongside, a human team.
>
> Grounded in current (2024–2026) market standards — the Dreyfus skill-acquisition model, public engineering career ladders (Dropbox, Square, CircleCI via progression.fyi), the Google SRE definition, Team Topologies, the MLOps-vs-ML-Platform role split, and the 70‑20‑10 L&D model. Sources at the end.

---

## 1. Team structure

**12 standing engineering roles**, a runtime **persona generator**, and the human **Stakeholder** gate. The two roles marked ★ were added in the Phase 2 expansion to carry the data-plane and ML-platform load a high-scale AI-native product places on the team.

```
                          Stakeholder (human gate — Stage 7)
                                     │
                    Engineering Advisor  (CTOA)  ── intake + final review (VETO)
                                     │
                         Architect  (ARC)  ── binding plan (Stage 2)
                                     │
        ┌──────────────┬─────────────┼──────────────┬───────────────┬──────────────┐
   Backend (BE)   Frontend (FEW)  Mobile (FEM)   AI/ML (AIE)   ★Data Eng (DE)  ★ML Platform (MLP)
        └──────────────┴─────────────┴──────────────┴───────────────┴──────────────┘
                          Stage 3 — parallel build lanes
                                     │
                 Security Reviewer (SEC, VETO) → QA Engineer (QA, VETO)
                                     │
                       Platform / SRE (OPS) — deploy + bake + rollback (Stage 8)

   Delivery Coordinator (PM) ── cross-cuts the pipeline
   Dynamic Persona Generator (DYN) ── 0–2 stress-test personas at Stage 1
```

| # | Agent-role | Code | Human discipline it stands in for | Pipeline locus |
|---|-----------|------|-----------------------------------|----------------|
| 1 | Engineering Advisor | CTOA | Eng Director / Principal + Eng Manager | Stage 1 intake, Stage 6 final review (VETO) |
| 2 | Architect | ARC | Software/Systems Architect | Stage 2 plan |
| 3 | Backend Engineer | BE | Backend Engineer | Stage 3 build |
| 4 | Frontend/Web Engineer | FEW | Frontend/Web Engineer | Stage 3 build |
| 5 | Mobile Engineer | FEM | Mobile Engineer | Stage 3 build |
| 6 | AI/ML Engineer | AIE | AI Engineer (LLM/agents) + applied ML/analytics | Stage 3 build |
| 7 ★ | Data Engineer | DE | Data Engineer | Stage 3 build |
| 8 ★ | ML Platform Engineer | MLP | ML Platform / MLOps Engineer | Stage 3 build |
| 9 | Security Reviewer | SEC | AppSec / Security Engineer | Stage 4 (VETO) |
| 10 | QA Engineer | QA | QA / SDET | Stage 5 (VETO) |
| 11 | Platform/SRE | OPS | Platform Engineer + SRE + DevOps | Stage 8 deploy/run |
| 12 | Delivery Coordinator | PM | Eng Program/Delivery Manager | cross-cutting |
| — | Dynamic Persona Generator | DYN | (rotating stress-test lens) | Stage 1 |
| — | Stakeholder | — | Product owner / business sponsor | Stage 7 gate (human) |

> **Why the split (★).** Pre-expansion, the AI/ML Engineer owned model integration, agents, evaluation, *and* the entire data pipeline + analytics + ML infra. For a stack with Kafka/Flink streaming, Spark batch, an Iceberg lakehouse, a Neo4j identity graph, OpenSearch, a Feast feature store, MLflow/BentoML serving, and LangGraph/Temporal orchestration, that is three jobs. The market splits them: **Data Engineer** ("is the data correct, fresh, queryable?"), **ML Platform Engineer** ("can DS + MLOps self-serve a reproducible, gated lifecycle?"), and **AI Engineer** ("ship the product on top of models"). This matrix follows that split.

---

## 2. Proficiency levels (the rubric)

Four tiers mapped onto the **Dreyfus model of skill acquisition**. The load-bearing axis is **autonomy + how the role relates to rules vs. intuition** — *not* years. Anchors are behavioural (what the role can actually *do* unaided), per the behavior-anchored-rating-scale standard.

| Level | Dreyfus stage | Can do **autonomously** | Rules vs. intuition | Counts toward coverage? |
|------|---------------|-------------------------|--------------------|--------------------------|
| **1 · Beginner** | Novice / Adv. Beginner | Completes well-scoped tasks against a runbook; needs the problem framed; responds to review. | Rigidly rule-bound; little context judgment. | **No** — not a bus-factor owner for the area. |
| **2 · Intermediate** | Competent | Works independently day-to-day on a known area; plans deliberately; picks an approach given objectives; syncs on bigger calls. | Standardized procedures applied analytically. | **Yes — 1 owner.** This is the "can do it alone" bar. |
| **3 · Advanced** | Proficient | Sees the situation holistically; spots what matters + deviations from normal; makes trade-offs alone; reviews others. | Pattern-recognition; maxims interpreted to context. | **Yes** — primary owner; can back up several areas. |
| **4 · Expert** | Expert | Operates from problem + desired outcome with maximum autonomy; sets the standard/direction; teaches; analyses only on novel problems. | Intuitive + holistic; analytic only when novel. | **Yes — anchor owner.** Their absence *is* the bus-factor risk. |

**Operational rule (industry standard):** on this 1–4 scale, **3–4 = "can do it independently."** For any skill area, **coverage = the count of roles at level ≥ 2 who can own it independently**, and **bus factor ≈ the minimum independent coverage across critical areas.** Target **≥ 2 independent owners** for every critical area, **≥ 3** for the most business-critical (deploy, incident response, cross-tenant isolation, the metric registry, the compliance regime, the system-of-record audit log).

---

## 3. Domain categories

The 20 domains this team must cover, each with its lead role. (Domain codes extend [`skill-mapping-matrix.md`](skill-mapping-matrix.md).)

| Domain | Lead role | Backup lead |
|--------|-----------|-------------|
| **Architecture & system design** (ARCH) | Architect | Engineering Advisor |
| **Backend services / APIs / OLTP** (BE) | Backend Engineer | Architect |
| **Frontend — web** (FE-W) | Frontend/Web Engineer | QA |
| **Frontend — mobile** (FE-M) | Mobile Engineer | Frontend/Web Engineer |
| **Data layer (OLTP/OLAP/query)** (DATA) | Data Engineer | Backend Engineer |
| **Stream processing** (STREAM) | Data Engineer | Backend Engineer |
| **Batch processing** (BATCH) | Data Engineer | AI/ML Engineer |
| **Lakehouse** (LAKE) | Data Engineer | ML Platform Engineer |
| **Graph / identity** (GRAPH) | Data Engineer | AI/ML Engineer |
| **Search / retrieval** (SEARCH) | Backend Engineer | Data Engineer / ML Platform |
| **AI / LLM / agents** (AI) | AI/ML Engineer | ML Platform Engineer |
| **ML platform & lifecycle** (MLOPS) | ML Platform Engineer | AI/ML Engineer |
| **Durable workflow / orchestration** (WF) | Backend Engineer | AI/ML Engineer |
| **Security & compliance** (SEC) | Security Reviewer | Engineering Advisor |
| **Observability** (OBS) | Platform/SRE | all roles |
| **Testing & verification** (TEST) | QA Engineer | all builders |
| **Performance (web + data)** (PERF) | Frontend/Web Engineer | Platform/SRE |
| **DevOps / infra / deploy** (OPS) | Platform/SRE | Architect |
| **Integrations / connectors** (INTG) | AI/ML Engineer | Data Engineer |
| **Engineering discipline / process** (DISC) | Engineering Advisor | all roles |

---

## 4. Skill coverage matrix (ownership · backup · target proficiency)

Every skill in [`skills/`](../skills/), its **primary owner**, **backup owner(s)**, and the **target proficiency** the primary must hit. Backups target one tier lower unless noted. Rows are grouped by domain.

> Reading the columns: **Primary** must hit the target level and is the anchor. **Backup** is the named bus-factor insurance (independent ≥ level 2). A skill with no backup is a **bus-factor‑1 gap** — flagged in §5.

### Architecture & discipline
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `architecture-patterns` | ARC (Expert) | CTOA |
| `domain-driven-design` | ARC (Expert) | all builders (Advanced) |
| `tech-stack-evaluation` | ARC (Advanced) | CTOA |
| `region-and-locale` | ARC (Advanced) | OPS, FEW, FEM |
| `engineering-discipline` | CTOA (Expert) | **ALL** (Advanced) |
| `subagent-orchestration` | CTOA (Advanced) | ARC |
| `writing-plans` | PM, ARC (Advanced) | all plan-emitting roles |
| `cost-routing-paradigms` | CTOA + AIE + MLP (Expert) | all builders (Advanced) |
| `verification-before-completion` | **ALL** (Expert) | — (universal) |
| `systematic-debugging` | all builders + QA (Advanced) | CTOA, SEC |
| `code-review` | CTOA (Expert) | QA, ARC |

### Backend, API, workflow
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `backend-fastify-trpc-grpc` | BE (Expert) | ARC |
| `grpc-buf` | BE (Advanced) | AIE, ARC |
| `api-discipline` | BE (Expert) | AIE, FEW, OPS, ARC |
| `idempotency-handling` | BE (Expert) | AIE, QA |
| `caching-strategy` | BE (Advanced) | AIE, OPS |
| `python-services` | AIE (Advanced) | BE (parity), DE |
| `workflow-engine-temporal` ★ | BE (Advanced) | AIE, MLP, OPS |

### Data plane (Data Engineer–led)
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `event-driven-kafka` | DE (Expert) | BE, AIE, OPS |
| `stream-processing-flink` ★ | DE (Advanced) | BE, AIE |
| `batch-processing-spark` ★ | DE (Advanced) | AIE, MLP |
| `lakehouse-iceberg` ★ | DE (Advanced) | MLP, ARC |
| `graph-identity-neo4j` ★ | DE (Intermediate→Advanced) | AIE, BE |
| `clickhouse-olap` | DE (Advanced) | AIE, BE |
| `data-layer` | ARC (Advanced) | DE, BE |
| `data-quality` | DE (Expert) | AIE, QA |
| `metric-engine` | AIE (Expert) | DE, QA, FEW |
| `search-opensearch` ★ | BE (Intermediate→Advanced) | DE, OPS |

### AI / ML platform (AI/ML + ML Platform–led)
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `claude-api` | AIE (Expert) | ARC, OPS |
| `llm-gateway` | AIE + MLP (Advanced) | ARC, OPS |
| `llm-evals` | AIE + MLP + QA (Expert) | ARC |
| `agent-orchestration-langgraph` ★ | AIE (Advanced) | MLP, SEC |
| `ml-lifecycle` ★ | MLP (Advanced) | AIE, QA |
| `feature-store-feast` ★ | MLP (Advanced) | DE, AIE |
| `vector-search-pgvector` ★ | MLP (Advanced) | AIE, DE |
| `mcp-protocol` | AIE (Advanced) | MLP, ARC, BE |
| `experimentation-holdouts` | AIE + PM (Advanced) | CTOA |
| `decision-log` | AIE (Expert) | DE, ARC, SEC |
| `integration-connectors` | AIE (Advanced) | DE, BE |
| `agentic-safety` | SEC (Expert) | AIE, MLP, ARC |

### Frontend (web + mobile)
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `frontend-web` | FEW (Expert) | ARC, QA |
| `kpi-dashboard-design` | FEW (Advanced) | FEM, PM |
| `web-performance` | FEW (Advanced) | QA, OPS |
| `accessibility` | FEW + FEM (Advanced) | QA |
| `mobile-surface` | FEM (Expert) | ARC, QA, BE |
| `app-store-deployment` | OPS (Advanced) | FEM |

### Security & compliance
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `security-baseline` | SEC (Expert) | BE, AIE, FEW, FEM, OPS (Advanced) |
| `auth-and-access` | SEC (Expert) | BE, FEW, FEM, AIE |
| `multi-tenancy-isolation` | SEC (Expert) | ARC, BE, DE, AIE, MLP |
| `oauth-implementation` | AIE (Advanced) | BE, SEC |
| `compliance-engine` | SEC (Expert) | AIE, **ALL** |
| `compliance-attestation` | SEC (Advanced) | BE, AIE, ARC, OPS |

### Platform / SRE / observability / testing
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `devops-aws` | OPS (Expert) | ARC |
| `observability` | OPS (Expert) | **ALL** (Advanced) |
| `progressive-delivery` | OPS (Advanced) | ARC |
| `incident-response` | OPS (Expert) | CTOA, SEC |
| `operational-readiness` | OPS + QA (Advanced) | all builders |
| `turborepo` | OPS (Advanced) | BE, FEW, FEM |
| `version-upgrade-policy` | OPS + ARC (Advanced) | BE |
| `finishing-a-development-branch` | OPS (Advanced) | **ALL** |
| `testing-tdd` | QA (Expert) | all builders, AIE |
| `task-tracker-integration` | PM (Advanced) | OPS, CTOA |

---

### Modernization skills (Phase 4 — 2026 standards)
| Skill | Primary (target) | Backup |
|-------|------------------|--------|
| `supply-chain-security` | OPS (Advanced) | SEC, ARC, all builders |
| `policy-as-code` | SEC (Advanced) | OPS, ARC |
| `platform-engineering-idp` | OPS (Advanced) | ARC, PM |
| `finops-cost` | OPS (Advanced) | CTOA, AIE |
| `ai-llm-security` | SEC (Expert) | AIE, MLP, ARC |
| `ai-observability-tracing` | AIE (Advanced) | MLP, OPS |
| `rag-retrieval` | MLP (Advanced) | AIE, DE |
| `agent-evaluation` | AIE (Advanced) | MLP, QA |
| `data-transformation-dbt` | DE (Advanced) | AIE, QA |
| `ai-streaming-ui` | FEW (Advanced) | AIE, FEM |

## 5. Gap analysis (ownership · coverage · bus-factor)

### 5.1 Ownership gaps — **CLOSED by this expansion**
Before Phase 2, six seams the product's stack depends on had **no owning skill at all** — they could not be planned, built, reviewed, or QA'd to standard:

| Seam | Was | Now |
|------|-----|-----|
| Stream processing (Flink) | no skill | `stream-processing-flink` → **DE** |
| Batch processing (Spark) | no skill | `batch-processing-spark` → **DE** |
| Lakehouse (Iceberg) | partial (S3 only) | `lakehouse-iceberg` → **DE** |
| Graph / identity (Neo4j) | no skill | `graph-identity-neo4j` → **DE** |
| Search (OpenSearch) | no skill | `search-opensearch` → **BE** |
| Feature store (Feast) | no skill | `feature-store-feast` → **MLP** |
| Vector store (pgvector) | partial | `vector-search-pgvector` → **MLP** |
| Workflow engine (Temporal) | no skill | `workflow-engine-temporal` → **BE** |
| Agent orchestration (LangGraph) | partial (concepts only) | `agent-orchestration-langgraph` → **AIE** |
| Model lifecycle (MLflow/BentoML) | partial | `ml-lifecycle` → **MLP** |

### 5.1b Market-currency gaps — CLOSED by the Phase 4 modernization
A GitHub-grounded 2026 market scan surfaced ten capabilities that are now industry-standard but had **no owning skill**. All ten were added (see the modernization table in §4):

| Capability | Now |
|-----------|-----|
| Software supply-chain integrity (SBOM/SLSA/Sigstore) | `supply-chain-security` → **OPS** |
| Policy-as-code enforcement (OPA/Kyverno) | `policy-as-code` → **SEC** |
| Internal Developer Platform (Backstage/Score) | `platform-engineering-idp` → **OPS** |
| Cloud FinOps (FOCUS/OpenCost) | `finops-cost` → **OPS** |
| LLM/agent security (OWASP LLM/Agentic Top 10) | `ai-llm-security` → **SEC** |
| LLM/agent observability (OTel GenAI) | `ai-observability-tracing` → **AIE** |
| RAG retrieval pattern (hybrid/rerank/contextual) | `rag-retrieval` → **MLP** |
| Agent trajectory evaluation | `agent-evaluation` → **AIE** |
| The dbt/SQLMesh transformation layer | `data-transformation-dbt` → **DE** |
| AI-native streaming UI (Vercel AI SDK) | `ai-streaming-ui` → **FEW** |

A further 34 existing skills were refreshed to current tooling/practice (premise-exposed rewrites + additive "2026 market update" notes) — the OS stays stack-agnostic; refreshes add alternatives + decision rubrics, they don't swap the reference vendor.

### 5.2 Remaining bus-factor risk (the "red zone")
Skills where **only one role** is at target proficiency and the named backup is thin. These need a Backup‑A + Backup‑B, a ≤1‑page playbook, and a real rotation (the backup does the task, the expert only reviews):

| Skill / area | Single point | Mitigation |
|--------------|-------------|------------|
| `graph-identity-neo4j` ★ | DE only; graph skills are scarce industry-wide | Cross-train AIE (probabilistic matching already pairs here); 1-page traversal/merge playbook. **Highest-priority backup to build.** |
| `multi-tenancy-isolation` | SEC is the only Expert; it's a P0 / VETO surface | Already broad shared-with, but force **≥3 independent** (ARC, BE, DE) via a tenant-isolation checklist all builders run. |
| `decision-log` (system-of-record audit log) | AIE Expert; high-stakes immutability | Promote DE + SEC backups to independent; mutation-test the ledger path (QA gate). |
| `ml-lifecycle` + `feature-store-feast` ★ | MLP is new and sole owner | AIE is the natural backup (consumes both); schedule a rotation within the first two cycles. |
| `incident-response` | OPS Expert; on-call bus factor | CTOA + SEC must run a real game-day to reach independent. |

### 5.3 Coverage / load gaps
- **DE is now the single owner of five new seams** (Flink, Spark, Iceberg, Neo4j, plus Kafka/OLAP). That is the same overload pattern that justified the split — watch DE's lane width; BE backs streaming/search, AIE backs batch/graph, MLP backs lakehouse. If DE saturates, the next role to add is a **Streaming/Realtime specialist**.
- **MLP is new** — until it reaches Expert on the lifecycle, the eval gate and online/offline parity are bus-factor‑1. AIE is the designated backup.
- **No dedicated Designer / UX role** — `accessibility` + `kpi-dashboard-design` live with FEW/FEM; acceptable for an internal-tooling/dashboard product, a gap for a consumer surface. Flag if the product grows a heavy consumer UI.

### 5.4 Hire-vs-upskill signal (when operated by a human team)
| Signal | Action |
|--------|--------|
| DE lane consistently saturated across cycles | **Hire** a second Data Engineer (streaming specialist). |
| Neo4j red-zone unresolved after 2 cycles | **Hire/contract** a graph specialist, or formally accept DE-only with a playbook. |
| Eval-gate throughput blocks releases | **Upskill** AIE→MLP backup, then hire an MLOps Engineer. |
| Compliance regime expands (new region/regulation) | **Upskill** SEC backups to ≥3; consider a dedicated Compliance Engineer. |

---

## 6. Growth & learning roadmap

Driven off the matrix gaps using the **70‑20‑10** model — 70% on-the-job, 20% social/coaching, 10% formal — **tilted toward more formal learning (≈20–25%) for the fast-moving AI-native skills** (LLM/agents, lakehouse, feature store), where the standard 10% is too low. Each role's roadmap moves it from its current floor to its target, and turns a red-zone backup into an independent owner.

| Role | Reach target on (Expert) | Build backup-independence in | 70% on-the-job | 20% coaching | 10–25% formal |
|------|--------------------------|------------------------------|----------------|--------------|----------------|
| **Architect** | architecture-patterns, DDD | region-and-locale, tech-stack-evaluation | Lead the next multi-region plan end-to-end | Pair w/ CTOA on final reviews | Residency-by-design + Iceberg table-design study |
| **Backend Eng** | api-discipline, idempotency | **workflow-engine-temporal**, search-opensearch (own these new seams to Advanced) | Build the first Temporal saga + OpenSearch index | Pair w/ DE on indexing pipeline | Temporal patterns + durable-execution course |
| **AI/ML Eng** | claude-api, llm-evals, cost-routing | **agent-orchestration-langgraph** to Expert; back up MLP lifecycle | Ship a LangGraph agent through the eval gate | Pair w/ MLP on a model promotion | LangGraph + agent-eval formal track |
| **★ Data Eng** | event-driven-kafka, data-quality | Flink/Spark/Iceberg → Advanced; Neo4j → Advanced | Own the streaming + reconciliation build | Pair w/ AIE on probabilistic identity | Flink (event-time/state) + Iceberg maintenance course (formal-heavy) |
| **★ ML Platform Eng** | — (new role, → Advanced first) | feature-store, ml-lifecycle, vector-search → Advanced; → Expert next cycle | Stand up the registry + feature store + serving | Pair w/ AIE (consumer) + DE (upstream) | MLOps lifecycle + feature-store formal track (formal-heavy) |
| **Frontend/Web** | frontend-web | web-performance, accessibility → Advanced | Hit the perf budget on the next dashboard | Pair w/ QA on a11y gate | Core Web Vitals + WCAG 2.2 study |
| **Mobile** | mobile-surface | accessibility, app-store-deployment | Ship an OTA + a native bump correctly | Pair w/ OPS on release pipeline | MASVS + EAS release study |
| **Security** | security-baseline, multi-tenancy, compliance | agentic-safety to Expert | Review the first agent write-tool fleet | Game-day w/ OPS | Agentic-safety + compliance-regime study |
| **QA** | testing-tdd, verification | ml-lifecycle + parity gates (back up MLP) | Own the eval-gate + parity checks | Pair w/ MLP/AIE | Mutation testing + ML-eval study |
| **Platform/SRE** | devops-aws, observability, incident | progressive-delivery; cluster-ops for new data/ML infra | Run Flink/OpenSearch/Temporal clusters | Game-day rotations | Karpenter/ArgoCD + stateful-stream ops study |
| **Delivery Coord** | task-tracker-integration, writing-plans | experimentation-holdouts | Map the next spec 1:1 to tasks | Pair w/ CTOA on escalations | — |

**Cadence:** recheck the bus factor every **4–6 weeks**; a red-zone item that hasn't moved to ≥2 independent owners in two cycles becomes a hire signal (§5.4). Each role carries a 1-page Individual Development Plan derived from its row above.

---

## 7. How this matrix is kept honest

1. **Single source per fact.** Ownership lives in [`skill-mapping-matrix.md`](skill-mapping-matrix.md); this doc *cites* it for who-owns-what and adds the proficiency/backup/gap/growth layer. `knowledge_lint.py` fails the build on a dead pointer or a skill-count mismatch.
2. **Backups are real, not nominal.** A "backup" counts only if that role can run the task **independently (≥ level 2)** — verified by a rotation where the backup does it and the expert only reviews.
3. **Every new seam updates four files in lockstep:** the `skills/<x>/SKILL.md`, the agent that owns it, [`skill-mapping-matrix.md`](skill-mapping-matrix.md), and this matrix's §4 + §5.

---

## Sources

- **Dreyfus model of skill acquisition** — the four-tier autonomy rubric (§2). [en.wikipedia.org/wiki/Dreyfus_model_of_skill_acquisition](https://en.wikipedia.org/wiki/Dreyfus_model_of_skill_acquisition)
- **Google SRE** — SRE responsibilities + the DevOps/SRE/Platform relationship. [sre.google/workbook/how-sre-relates](https://sre.google/workbook/how-sre-relates/), [sre.google/sre-book/introduction](https://sre.google/sre-book/introduction/)
- **swyx, "The Rise of the AI Engineer" (Latent Space, 2023)** — the AI Engineer ("build *with* models") vs ML Engineer ("train the model") boundary. [latent.space/p/ai-engineer](https://www.latent.space/p/ai-engineer)
- **Public career ladders** — Dropbox Engineering Career Framework; progression.fyi; swyx's public-ladders index (levels = scope × autonomy × impact). [dropbox.github.io/dbx-career-framework](https://dropbox.github.io/dbx-career-framework/), [progression.fyi](https://progression.fyi/)
- **Team Topologies / Platform Engineering** — golden paths, cognitive load, the platform-vs-SRE split. [cncf.io — DevOps vs SRE vs Platform Engineering](https://www.cncf.io/blog/2022/07/01/devops-vs-sre-vs-platform-engineering-the-gaps-might-be-smaller-than-you-think/)
- **MLOps vs ML Platform Engineer** — the lifecycle-vs-platform split (§1, §5). [Yardstick role comparison](https://yardstick.team/compare-roles/mlops-engineer-vs-ml-platform-engineer-decoding-critical-ai-roles), [Databricks MLOps guide](https://www.databricks.com/blog/mlops-frameworks-complete-guide-tools-and-platforms-production-ml)
- **Behavior-anchored skills matrices + bus factor** — coverage = #independent owners; target bus factor ≥ 3 for critical areas. [Sprad skill-matrix guide](https://sprad.io/blog/engineering-skills-matrix-templates-excel-sheets-downloads-leveling-rubrics-by-ic-manager), [BlaBlaCar — operational coverage with skills matrices](https://medium.com/blablacar/increase-operational-coverage-with-skills-matrices-20f85f1dddc)
- **70‑20‑10 L&D model** (tilt formal share up for emerging tech). [Training Industry — 70‑20‑10](https://trainingindustry.com/wiki/content-development/the-702010-model-for-learning-and-development/)
- **Multi-region data residency as a designed-in property.** [InfoQ — Architectures for Multi-Region Data Residency](https://www.infoq.com/articles/understanding-architectures-multiregion-data-residency/)
- **Temporal + LangGraph two-layer (durable macro / reasoning micro)** — the §1 orchestration split. [anup.io — Temporal + LangGraph](https://www.anup.io/temporal-langgraph-a-two-layer-architecture-for-multi-agent-coordination/)

---

## Next

- [`skill-mapping-matrix.md`](skill-mapping-matrix.md) — the authoritative skill→role binding (who owns what).
- [`role-empowerment-model.md`](role-empowerment-model.md) — how each role uses its skills, with what authority.
- [`../AGENTS.md`](../AGENTS.md) — the cross-runtime (Claude Code + Codex) operating contract for this same roster.
