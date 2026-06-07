---
name: version-upgrade-policy
description: Deliberate dependency/runtime upgrades — LTS baseline, cadence (patch now / minor quarterly / major ADR), EOL watch, Dependabot/Renovate triage. Owner Platform/SRE + Architect.
---

# Version & Upgrade Policy — change deliberately, not frequently

A product's stack should be **neither frozen nor chased.** Freezing it ossifies (security debt, EOL'd runtimes, deprecated APIs); chasing every release churns the team. The middle path is a **policy**: a known LTS-tracking baseline, a fixed upgrade *cadence*, and an EOL/deprecation *watch* so nothing rots silently. The classic failure this prevents: an audit finding the stack table 12–18 months behind (an EOL'd runtime in prod, an abandoned client library, a deprecated index type, an SDK heading for end-of-support). **Owner: Platform/SRE (cadence) + Architect (approves majors via ADR).**

## 1. The pinned baseline

Source of truth: the product's `STACK.md` in the Canon (`.engineering-os/knowledge-base/`) + `docs/technical-context.md` (if present). Re-confirm at every quarterly review. Drift from it is a finding.

The baseline is **per product** — `STACK.md` is authoritative. The table below is an *illustrative* shape (a reference-implementation stack), not a mandate; bind each row to whatever your `STACK.md` declares:

| Layer | Pinned (example) | Track | Notes |
|---|---|---|---|
| Server runtime (typed) | Active **LTS** | Active LTS | Ride the LTS line; never run an EOL runtime in prod |
| Scripting/data runtime | latest stable −0/1 | latest stable −0/1 | Adopt a new major only when load-bearing deps confirm support |
| Web framework / UI lib | latest stable −0/1 major | latest stable −0/1 major | Adopt stable features only |
| Mobile SDK / framework | latest stable | latest stable | Track the vendor's supported line |
| Async/messaging client | a **maintained** client | maintained | Never reintroduce an abandoned/broken client |
| ORM / data-access | latest major | latest major | Keep a sanctioned alternative noted |
| Data stores (OLTP/OLAP/vector) | managed where possible | managed | Use the index type appropriate to the workload (e.g. HNSW for write-heavy vectors) |
| Model(s) | pinned IDs | per model-migration policy | governed by `llm-evals` (re-baseline on any model change) |
| Security baselines (OWASP / MASVS) | latest edition | latest edition | re-map when a new edition lands |

> The locked *patterns* (DDD, event-driven, OLTP/OLAP split, cheapest-sufficient-effort routing, multi-tenancy, contract-as-single-source) do not change on this cadence — only versions/libraries do. A pattern change is a `tech-stack-evaluation` ADR, not an upgrade.

## 2. The cadence

| Change class | When | Who | Gate |
|---|---|---|---|
| **Security patch** (CVE meeting the SLA) | **Immediately** — out of cadence | Platform/SRE | `vulnerability-scanning` SLA; CI green; deploy |
| **Patch** (x.y.**Z**) | Auto-merge weekly if CI green | bot + Platform/SRE spot-check | full CI + contract tests |
| **Minor** (x.**Y**.0) | **Quarterly** stack-review batch | Platform/SRE | CI + contract + real-network smoke |
| **Major** (**X**.0.0) of a load-bearing dep | **Deliberate — its own requirement + ADR** | Architect approves, Platform/SRE executes | migration plan, breaking-change scan, staged rollout, rollback recipe |
| **Pattern / new layer** | only on real need | Architect ADR (`tech-stack-evaluation`) | full architecture review |

**Rule of thumb:** patches flow, minors batch quarterly, majors are planned. Never adopt an x.0.0 in its first ~8 weeks unless a security fix forces it.

## 3. The EOL / deprecation watch (prevents silent rot — the actual failure mode)

At the **quarterly stack review**, Platform/SRE checks each pinned dep against its EOL calendar + deprecation notices:

- **Runtime EOL** (server/scripting runtime, database): plan the bump **≥1 quarter before EOL** — never reach EOL in prod. Watch [endoflife.date](https://endoflife.date).
- **Library abandonment** (no release ~12mo / archived / maintainer gone): migrate proactively. A load-bearing dep going unmaintained is a P1 finding.
- **API/SDK deprecation** (renamed config, maintenance-mode SDK): schedule in the next window.
- **Model deprecation**: a model reaching EOL → migrate per `llm-evals` (re-baseline + A/B + cost/latency check + rollback).
- **Compliance/edition refresh** (OWASP, MASVS, and whatever regime `COMPLIANCE.md` declares — tax, telecom, data-protection rules): re-map when a new edition lands; `worker-compliance-drift` + `worker-canon-drift` surface these between reviews.

Output: a short `version-review-<quarter>.md` in `.engineering-os/memory/` listing each dep, its status (current / minor-behind / major-behind / EOL-risk / abandoned), and the action. Zero EOL-risk + zero abandoned deps in prod is the pass bar.

## 4. Dependency-update triage (the bot rules)

- **Renovate/Dependabot** runs continuously: **patch → auto-merge** on green CI; **minor → quarterly batch PR**; **major → a tracked requirement** (never auto-merged).
- Every new dependency must be **justified in writing** (which existing dep can't do this, maintenance cost) — fewer deps = less churn.
- Pin exactly (lockfiles committed; container base images pinned by digest). Generated code (protos, ORM client) regenerates on bump and is contract-tested (`api-contract-testing`).

## 5. Anti-patterns

❌ Running an **EOL runtime** in prod · ❌ a **load-bearing dep abandoned** 12+ months · ❌ chasing an **x.0.0 in week one** · ❌ a **major bump merged reactively** without ADR + migration plan + rollback · ❌ a **stack table not reconciled in >1 quarter** · ❌ bumping a **model without re-baselining evals** · ❌ reintroducing a **retired/abandoned lib** (or an index type wrong for the workload).

## Verification

- The pinned baseline (§1) matches the Canon's `STACK.md` + `docs/technical-context.md` — run `worker-canon-drift` if unsure.
- The latest `version-review-<quarter>.md` exists, zero EOL-risk / abandoned deps in prod.
- No skill or canon doc references a version this policy retired.

## 2026 market update

- **License posture is now part of dependency triage**, not just version/EOL. Worked example: HashiCorp's **BSL relicense** + **IBM acquisition (Dec 2024)** triggered the **OpenTofu** fork — a deliberate, ADR-grade migration decision, not a reactive swap (`devops-aws`, `tech-stack-evaluation`). Watch for relicensing as a first-class upgrade trigger.
