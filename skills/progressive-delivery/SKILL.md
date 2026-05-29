---
name: progressive-delivery
description: Feature flags + canary that decouple release from deploy — workspace-scoped flags, 60s kill switches, SLO-analysed canary + auto-rollback, per-brand graduation. Owner Jatin.
---

# Progressive Delivery — Decouple Release from Deploy

> **Deploy** = code running in production. **Release** = behavior exposed to a user. `devops-aws` ships the artifact (CI → ECR → ArgoCD); this skill decides *who sees the new behavior and when*, and *how fast to retreat* — without a redeploy.

Brain has high-stakes releases: a flag controls whether an AI agent **auto-executes real money actions** on a regulated channel for a specific brand. Progressive delivery is the mechanism behind the canon's auto-execute graduation and the Owner kill switch.

## Owner: Jatin. Three capabilities, one mental model

1. **Feature flags** — turn behavior on/off without a deploy.
2. **Gradual rollout** — expose to a growing slice (canary %, then per-brand) with automated analysis + auto-rollback.
3. **Flag lifecycle** — every flag has a death date; stale flags are debt.

## 1. Flag management

Flags are **typed, workspace-scoped, and cached** — never a loose `if (env === 'prod')`. They live in Redis (hot read, `~60s` TTL, workspace-keyed per `caching-strategy`) backed by a Postgres source of truth in core-service, evaluated at the api-gateway / service boundary.

```typescript
// packages/lib-flags — typed registry; the compiler is the first guard
type FlagKind = 'release' | 'ops' | 'experiment' | 'permission';
interface Flag<T> { key: string; kind: FlagKind; default: T; owner: string; expiresAt: string; }
const FLAGS = {
  'sale_event_mode':   flag<boolean>({ kind: 'ops',     default: false, owner: 'jatin' }),
  'autoexec.pause_ad': flag<boolean>({ kind: 'ops',     default: false, owner: 'maya'  }),
  'inbox_v2':          flag<boolean>({ kind: 'release', default: false, owner: 'ananya', expiresAt: '2026-07-01' }),
} as const;
const on = await flags.eval('inbox_v2', { workspaceId: ctx.workspaceId });  // ALWAYS workspace-scoped
```

A flag default is the **safe** state (new behavior OFF, kill switch armable). Every flag carries an `owner` and an `expiresAt`. Reads are workspace-scoped because nearly every Brain flag varies per brand.

### Kill-switch wiring (ops flags — safety-critical)

Some flags are **emergency brakes** that take effect in seconds independent of deploy:

- **Auto-execute Owner kill switch** — the canon's global + per-action-class switch letting an **Owner pause all auto-execution in 60s** (`agentic-design`, `agentic-actions-auditor`). Evaluated *before* any MCP write tool fires; flipping it OFF must propagate within the Redis TTL (or pub/sub invalidation for instant effect). The single most important flag in Brain.
- **Sale / Event-Mode toggle** — switches the daily-tick to the higher-cadence config (hourly Path-A rollup + ML anomaly + Sonnet only at digest).
- **Per-vendor / per-paradigm circuit toggles** — disable a misbehaving connector or force a degraded path (pairs with the circuit breakers in `observability`).

Kill switches are drilled: flip the switch, verify the next agent tick refuses to auto-execute. "We'll add the kill switch later" on an autonomous loop is a Stage-4 blocker.

## 2. Flag lifecycle / cleanup (stale-flag debt)

A flag at 100% for a month is dead code with a runtime cost. The OFF branch silently breaks; flags interact unexpectedly.

- Every **release** flag has an `expiresAt`. CI fails when a release flag is past expiry and still referenced.
- After a release reaches 100% and bakes, **delete the flag and the dead branch** in the next PR.
- **Ops** flags (kill switches, Sale Mode) are permanent by design — exempt from expiry but still owned + inventoried.
- A monthly flag inventory (owner, kind, rollout %, age) surfaces debt.

## 3. Canary / gradual rollout (release flags)

A growing audience slice with a bake window and automated analysis, not a big-bang flip. Sits on top of ArgoCD/EKS via Argo Rollouts-style canary steps gated by **automated canary analysis against SLOs + error budget**.

```
deploy (ArgoCD, both code paths live, flag default OFF)
  ▼
canary 5%  ── bake 30m ──►  AnalysisRun: error rate, p99, Sentry new-error rate,
  ▼                          paradigm-bypass rate, Decision-Log write success
canary 25% ── bake 1h  ──►  vs SLO + error budget (observability)
  ▼
canary 50% ── bake 2h
  ▼
100% ──► bake 24h ──► delete flag + dead branch
   └─ ANY analysis breach at any step → AUTO-ROLLBACK (flag→OFF, traffic→0) + alert
```

- **Traffic %** is the slice; **bake time** lets slow signals surface before widening.
- **Automated canary analysis** compares against the SLO targets + remaining error budget (`observability` SLO table). A breach **auto-rolls-back by flipping the flag** (seconds), complementing the deploy-level auto-rollback in `devops-aws` (composite CloudWatch alarm → ArgoCD previous revision, minutes).
- For mobile, the analogue is EAS Update staged rollout % (OTA JS) vs full store review (native bump) — `app-store-deployment`.

## 4. Per-brand graduated rollout (the Brain-specific case)

The canon's **auto-execute graduation is a per-tool, per-brand gradual rollout**: an agent's action starts **recommend-only** and graduates to **auto-execute** for a brand only after its track record clears thresholds over a 90-day rolling window (`agentic-design`, `canon/TECH/14` §6).

| Stage | Brain meaning | Flag state for `(workspace, tool)` |
|---|---|---|
| **Recommend-only** | surfaces in Morning Brief for Owner approval | `autoexec.<tool>` = OFF |
| **Eligible** | thresholds met; Owner offered graduation | OFF, eligible banner |
| **Graduated** | Owner enabled; auto-executes within caps | ON for that brand |
| **De-graduated** | accuracy/reversal regressed → auto-revert | flipped OFF by nightly job |

| Tool class | T_acc | T_app | N_min | R_max | Magnitude cap |
|---|---|---|---|---|---|
| Low-risk (negative keyword) | 75% | 65% | 30 | 5% | n/a |
| Medium (budget ≤10%) | 80% | 70% | 50 | 3% | ±10% |
| High (price change) | 85% | 75% | 100 | 2% | ≤5%; SKU <20% rev |
| Very high (courier reallocation) | 90% | 80% | 200 | 1% | brand opt-in only |

The graduation tracker (nightly job in intelligence-service) IS automated canary analysis: watches outcome accuracy, approval rate, sample size, and **reverse-rate** per brand, graduates when all clear, and **auto-de-graduates** the instant a graduated tool regresses. The Owner can revoke anytime; the global kill switch overrides everything. Per-brand because a tool can be trustworthy for one brand's data and not another's.

## Red flags — STOP and BOUNCE

- A risky behavior shipped **without a flag** (no retreat without redeploy).
- An **auto-execute path with no kill switch**, or one that needs a deploy to flip.
- A canary with **no bake time or no automated analysis**.
- **No auto-rollback** wired to SLO / error-budget breach.
- A release flag with **no owner or no expiry**.
- A flag evaluated **not workspace-scoped** — leaks one brand's beta/graduation to another.
- An agent graduated to auto-execute **without the per-brand threshold check**.
- A dead 100%-for-a-month flag left in the tree.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "Small change, no flag" | A flag is the difference between a 5-second retreat and a redeploy under pressure |
| "Roll it to everyone, it's fine" | Canary + bake catch the slow regressions a big-bang flip hides |
| "The Owner can just not enable auto-execute" | Per-brand graduation + kill switch are the guardrails *for when they do* |
| "Flags are temporary, cleanup later" | "Later" is 80 stale flags + an OFF branch nobody can prove works |
| "Auto-rollback = deploy rollback" | Deploy rollback is minutes; flag rollback is seconds — for a money-moving loop, you want the flip |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Flag system + canary steps + auto-rollback | **Jatin** | `devops-aws` |
| Auto-execute kill switch + graduation tracker | **Maya** + Aryan | `agentic-design`, `agentic-actions-auditor` |
| Canary analysis vs SLO / error budget | **Jatin** + Maya | `observability` |
| Sale/Event-Mode toggle | Jatin + Maya | `morning-brief-mobile`, `agentic-design` |
| Mobile staged rollout (EAS Update %) | **Karan** | `app-store-deployment` |
| Incident retreat (flip flag) | Jatin + on-call | `incident-response` |

Make deploys boring and releases reversible. Ship dark behind a typed workspace-scoped flag; widen by canary with automated SLO analysis and auto-rollback; arm a kill switch on anything autonomous; treat auto-execute graduation as a per-brand, per-tool rollout that auto-retreats. Then delete the flag when done.
