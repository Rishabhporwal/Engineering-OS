---
name: version-upgrade-policy
description: Brain's deliberate-not-frequent dependency & runtime upgrade policy — the LTS-tracking baseline (current pinned versions), the cadence (patch=now, minor=quarterly, major=ADR), the EOL/deprecation watch that prevents silent rot (the thing that let Node 20 / KafkaJS / lifetimes / X-Ray go stale), and the Dependabot/Renovate triage rules. Use when bumping any dependency, adding a new one, at the quarterly stack review, when a CVE or EOL notice lands, or when proposing a major framework jump. The stack is NOT hard-locked — it is changed deliberately, on a cadence, with evidence; never reactively, never frequently.
---

# Version & Upgrade Policy — change deliberately, not frequently

Brain's stack is **not frozen and not chased.** Freezing it ossifies (security debt, EOL'd runtimes, deprecated APIs); chasing every release churns the team. The middle path is a **policy**: a known LTS-tracking baseline, a fixed upgrade *cadence*, and an EOL/deprecation *watch* so nothing rots silently. This skill exists because an audit found the stack table had drifted ~18 months behind (Node 20 at EOL, KafkaJS abandoned, `lifetimes` archived, X-Ray heading to EOS, pgvector on the wrong index) — all avoidable with a policy. **Owner: Jatin (runs the cadence) + Aryan (approves majors via ADR).**

## 1. The pinned baseline (current — May 2026)
The single source of truth is `canon/TECH/00_tech_stack_decision.md` + `docs/technical-context.md`. This table is the *current pin* and must be re-confirmed at every quarterly review. Drift from it is a finding.

| Layer | Pinned | Track | Notes |
|---|---|---|---|
| Node.js (TS services) | **24 LTS** | Active LTS | Node 20 EOL Apr 2026; ride the LTS line, never run EOL in prod |
| Python (data/ML/agents) | **3.13** | latest stable −0/1 | 3.14 added free-threading; adopt when ecosystem (asyncpg/clickhouse/aiokafka) confirms |
| Next.js / React | **16 / 19** | latest stable −0/1 major | Turbopack + React Compiler now stable; Server Actions idiomatic |
| Expo SDK / React Native | **SDK 56** (RN 0.85) | latest stable | New Architecture mandatory since SDK 55; Hermes v1 |
| Kafka client (Node) | **@confluentinc/kafka-javascript** | maintained | KafkaJS is abandoned/broken under Kafka 4.0 — do not reintroduce |
| ORM | **Prisma 7** | latest major | Rust engine dropped (smaller, edge-ready); Drizzle is the sanctioned alt if a service needs it |
| Postgres / pgvector | Supabase PG + **HNSW** indexes | managed | HNSW (m=16, ef_construction=64), not ivfflat, for write-heavy vectors |
| ClickHouse | Cloud (managed) | managed | — |
| LLMs | **Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5** | per model-migration policy | governed by `llm-evals` (re-baseline evals on any model change) |
| OWASP / MASVS | **Top 10:2025 / MASVS 2.1.0** | latest edition | re-map when OWASP publishes a new edition |

> The locked *patterns* (DDD, event-driven, OLTP/OLAP split, cost-routing, multi-tenancy, proto-as-SSoT) do not change on this cadence — only versions/libraries do. A pattern change is a `tech-stack-evaluation` ADR, not an upgrade.

## 2. The cadence (how fast each class of change moves)
| Change class | When | Who | Gate |
|---|---|---|---|
| **Security patch** (CVE, any severity meeting the SLA) | **Immediately** — out of cadence | Jatin | `vulnerability-scanning` SLA; CI green; deploy |
| **Patch release** (x.y.**Z**) | Auto-merge weekly if CI green | bot + Jatin spot-check | full CI + contract tests |
| **Minor release** (x.**Y**.0) | **Quarterly** stack-review batch | Jatin | CI + contract + a real-network smoke; note in the review |
| **Major release** (**X**.0.0) of a load-bearing dep (Node, Next, React, Expo SDK, Prisma, ClickHouse, Postgres) | **Deliberate — its own requirement + ADR** | Aryan approves, Jatin executes | migration plan, breaking-change scan (`buf breaking` / typecheck / eval re-baseline for models), staged rollout, rollback recipe |
| **Pattern / new layer** | only on real need | Aryan ADR (`tech-stack-evaluation`) | full architecture review |

**Rule of thumb:** patches flow, minors batch quarterly, majors are planned. Never adopt an x.0.0 in its first ~8 weeks unless a security fix forces it (let the ecosystem shake out).

## 3. The EOL / deprecation watch (prevents silent rot — the actual failure mode)
At the **quarterly stack review**, Jatin checks each pinned dep against its EOL calendar and deprecation notices, and files a finding for anything within the danger window:
- **Runtime EOL** (Node/Python/Postgres): plan the bump **≥1 quarter before EOL** — never reach EOL in prod (no security patches). Watch [endoflife.date](https://endoflife.date).
- **Library abandonment** (no release in ~12mo / archived / maintainer gone): migrate proactively — *this is how KafkaJS and `lifetimes` rotted.* A load-bearing dep going unmaintained is a P1 finding.
- **API/SDK deprecation** (renamed config, maintenance-mode SDK): schedule the migration in the next cadence window — *this is X-Ray→ADOT and Karpenter's `WhenUnderutilized` rename.*
- **Model deprecation**: Anthropic model EOL → migrate per `llm-evals` (re-baseline + A/B + cost/latency check + rollback). Never let a model EOL become an emergency.
- **Compliance/edition refresh** (OWASP, MASVS, tax slabs, telecom rules): re-map when a new edition lands; `worker-compliance-drift` + `worker-canon-drift` surface these between reviews.

Output of the watch: a short `version-review-<quarter>.md` in `.engineering-os/memory/` listing each dep, its status (current / minor-behind / major-behind / EOL-risk / abandoned), and the action. Zero EOL-risk and zero abandoned deps in prod is the pass bar.

## 4. Dependency-update triage (the bot rules)
- **Renovate/Dependabot** runs continuously. Default routing: **patch → auto-merge** on green CI; **minor → quarterly batch PR**; **major → a tracked requirement** (never auto-merged).
- Every new dependency added in a build must be **justified in writing** (which existing dep can't do this, maintenance cost) per the over-engineering rule — fewer deps = less churn.
- Pin exactly (lockfiles committed; Docker base images pinned by digest). Generated code (Buf protos, Prisma client) regenerates on bump and is contract-tested (`api-contract-testing`).

## 5. Anti-patterns (this skill catches)
- ❌ Running an **EOL runtime** in prod (Node 20 after Apr 2026). · ❌ A **load-bearing dep that's been abandoned** for 12+ months. · ❌ Chasing an **x.0.0 in week one**. · ❌ A **major bump merged reactively** without an ADR + migration plan + rollback. · ❌ A **stack table that hasn't been reconciled in >1 quarter** (drift = finding). · ❌ Bumping a **model without re-baselining evals** (`llm-evals`). · ❌ Reintroducing a **deprecated/abandoned lib** the policy already retired (KafkaJS, ivfflat-for-hot-vectors, `lifetimes`).

## Verification
- The pinned baseline (§1) matches `canon/TECH/00` + `docs/technical-context.md` — run `worker-canon-drift` if unsure.
- The latest `version-review-<quarter>.md` exists and shows zero EOL-risk / abandoned deps in prod.
- No skill or canon doc references a version this policy has retired (grep for the retired pins).
