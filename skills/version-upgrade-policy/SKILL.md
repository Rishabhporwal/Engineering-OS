---
name: version-upgrade-policy
description: Deliberate dependency/runtime upgrades — LTS baseline, cadence (patch now / minor quarterly / major ADR), EOL watch, Dependabot/Renovate triage. Owner Jatin + Aryan.
---

# Version & Upgrade Policy — change deliberately, not frequently

Brain's stack is **not frozen and not chased.** Freezing it ossifies (security debt, EOL'd runtimes, deprecated APIs); chasing every release churns the team. The middle path is a **policy**: a known LTS-tracking baseline, a fixed upgrade *cadence*, and an EOL/deprecation *watch* so nothing rots silently. Exists because an audit found the stack table ~18 months behind (Node 20 at EOL, KafkaJS abandoned, `lifetimes` archived, X-Ray heading to EOS, pgvector on the wrong index). **Owner: Jatin (cadence) + Aryan (approves majors via ADR).**

## 1. The pinned baseline (current — May 2026)

Source of truth: `canon/TECH/00_tech_stack_decision.md` + `docs/technical-context.md`. Re-confirm at every quarterly review. Drift from it is a finding.

| Layer | Pinned | Track | Notes |
|---|---|---|---|
| Node.js (TS services) | **24 LTS** | Active LTS | Node 20 EOL Apr 2026; ride the LTS line, never run EOL in prod |
| Python (data/ML/agents) | **3.13** | latest stable −0/1 | 3.14 added free-threading; adopt when asyncpg/clickhouse/aiokafka confirm |
| Next.js / React | **16 / 19** | latest stable −0/1 major | Turbopack + React Compiler stable; Server Actions idiomatic |
| Expo SDK / React Native | **SDK 56** (RN 0.85) | latest stable | New Architecture mandatory since SDK 55; Hermes v1 |
| Kafka client (Node) | **@confluentinc/kafka-javascript** | maintained | KafkaJS abandoned/broken under Kafka 4.0 — do not reintroduce |
| ORM | **Prisma 7** | latest major | Rust engine dropped; Drizzle is the sanctioned alt if needed |
| Postgres / pgvector | Supabase PG + **HNSW** indexes | managed | HNSW (m=16, ef_construction=64), not ivfflat, for write-heavy vectors |
| ClickHouse | Cloud (managed) | managed | — |
| LLMs | **Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5** | per model-migration policy | governed by `llm-evals` (re-baseline on any model change) |
| OWASP / MASVS | **Top 10:2025 / MASVS 2.1.0** | latest edition | re-map when a new edition lands |

> The locked *patterns* (DDD, event-driven, OLTP/OLAP split, cost-routing, multi-tenancy, proto-as-SSoT) do not change on this cadence — only versions/libraries do. A pattern change is a `tech-stack-evaluation` ADR, not an upgrade.

## 2. The cadence

| Change class | When | Who | Gate |
|---|---|---|---|
| **Security patch** (CVE meeting the SLA) | **Immediately** — out of cadence | Jatin | `vulnerability-scanning` SLA; CI green; deploy |
| **Patch** (x.y.**Z**) | Auto-merge weekly if CI green | bot + Jatin spot-check | full CI + contract tests |
| **Minor** (x.**Y**.0) | **Quarterly** stack-review batch | Jatin | CI + contract + real-network smoke |
| **Major** (**X**.0.0) of a load-bearing dep | **Deliberate — its own requirement + ADR** | Aryan approves, Jatin executes | migration plan, breaking-change scan, staged rollout, rollback recipe |
| **Pattern / new layer** | only on real need | Aryan ADR (`tech-stack-evaluation`) | full architecture review |

**Rule of thumb:** patches flow, minors batch quarterly, majors are planned. Never adopt an x.0.0 in its first ~8 weeks unless a security fix forces it.

## 3. The EOL / deprecation watch (prevents silent rot — the actual failure mode)

At the **quarterly stack review**, Jatin checks each pinned dep against its EOL calendar + deprecation notices:

- **Runtime EOL** (Node/Python/Postgres): plan the bump **≥1 quarter before EOL** — never reach EOL in prod. Watch [endoflife.date](https://endoflife.date).
- **Library abandonment** (no release ~12mo / archived / maintainer gone): migrate proactively — *how KafkaJS and `lifetimes` rotted.* A load-bearing dep going unmaintained is a P1 finding.
- **API/SDK deprecation** (renamed config, maintenance-mode SDK): schedule in the next window — *X-Ray→ADOT, Karpenter's `WhenUnderutilized` rename.*
- **Model deprecation**: Anthropic model EOL → migrate per `llm-evals` (re-baseline + A/B + cost/latency check + rollback).
- **Compliance/edition refresh** (OWASP, MASVS, tax slabs, telecom rules): re-map when a new edition lands; `worker-compliance-drift` + `worker-canon-drift` surface these between reviews.

Output: a short `version-review-<quarter>.md` in `.engineering-os/memory/` listing each dep, its status (current / minor-behind / major-behind / EOL-risk / abandoned), and the action. Zero EOL-risk + zero abandoned deps in prod is the pass bar.

## 4. Dependency-update triage (the bot rules)

- **Renovate/Dependabot** runs continuously: **patch → auto-merge** on green CI; **minor → quarterly batch PR**; **major → a tracked requirement** (never auto-merged).
- Every new dependency must be **justified in writing** (which existing dep can't do this, maintenance cost) — fewer deps = less churn.
- Pin exactly (lockfiles committed; Docker base images pinned by digest). Generated code (Buf protos, Prisma client) regenerates on bump and is contract-tested (`api-contract-testing`).

## 5. Anti-patterns

❌ Running an **EOL runtime** in prod · ❌ a **load-bearing dep abandoned** 12+ months · ❌ chasing an **x.0.0 in week one** · ❌ a **major bump merged reactively** without ADR + migration plan + rollback · ❌ a **stack table not reconciled in >1 quarter** · ❌ bumping a **model without re-baselining evals** · ❌ reintroducing a **retired lib** (KafkaJS, ivfflat-for-hot-vectors, `lifetimes`).

## Verification

- The pinned baseline (§1) matches `canon/TECH/00` + `docs/technical-context.md` — run `worker-canon-drift` if unsure.
- The latest `version-review-<quarter>.md` exists, zero EOL-risk / abandoned deps in prod.
- No skill or canon doc references a version this policy retired.
