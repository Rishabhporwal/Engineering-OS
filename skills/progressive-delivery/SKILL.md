---
name: progressive-delivery
description: Feature flags + gradual rollout that decouple release from deploy across Brain. Covers typed workspace-scoped flags + kill-switch wiring (the auto-execute Owner kill switch, Sale/Event-Mode toggles), flag lifecycle/cleanup to kill stale-flag debt, canary/gradual rollout (traffic %, bake time, automated canary analysis against SLOs + error budget, auto-rollback), and — the Brain-specific case — per-brand graduated rollout that serves the canon's auto-execute graduation (per-tool, per-brand: recommend-only → graduated on outcome-accuracy / approval-rate / sample-size / reverse-rate thresholds). Use when shipping behind a flag, wiring a kill switch, planning a canary, cleaning up stale flags, or building the per-brand graduation rollout. Owner: Jatin. Distinct from `devops-aws` (the deploy mechanics) — this governs what's exposed to whom, when.
---

# Progressive Delivery — Decouple Release from Deploy

> **Deploy** = the code is running in production. **Release** = the behavior is exposed to a user. `devops-aws` ships the artifact (CI → ECR → ArgoCD); this skill decides *who sees the new behavior and when*, and *how fast to retreat*. The two are deliberately separate so a deploy is boring and a release is reversible in seconds — without a redeploy.

Brain has unusually high-stakes releases: a flag controls whether an AI agent **auto-executes real money actions** on a regulated channel for a specific brand. Progressive delivery is therefore not a nicety — it's the mechanism behind the canon's auto-execute graduation and the Owner kill switch. The same discipline (flag → canary → bake → auto-rollback) governs both ordinary feature rollout and the riskiest agentic surfaces.

## Owner: Jatin. Three capabilities, one mental model

1. **Feature flags** — turn behavior on/off without a deploy.
2. **Gradual rollout** — expose to a growing slice (canary %, then per-brand) with automated analysis + auto-rollback.
3. **Flag lifecycle** — every flag has a death date; stale flags are debt.

## 1. Flag management

Flags are **typed, workspace-scoped, and cached** — never a loose `if (env === 'prod')` or a stringly-typed map. They live in Redis (hot read, `~60s` TTL, workspace-keyed per `caching-strategy`) backed by a Postgres source of truth in core-service, and are evaluated at the api-gateway / service boundary.

```typescript
// packages/lib-flags — typed registry; the compiler is the first guard
type FlagKind = 'release' | 'ops' | 'experiment' | 'permission';
interface Flag<T> { key: string; kind: FlagKind; default: T; owner: string; expiresAt: string; }

const FLAGS = {
  'sale_event_mode':        flag<boolean>({ kind: 'ops',     default: false, owner: 'jatin' }),
  'autoexec.pause_ad':      flag<boolean>({ kind: 'ops',     default: false, owner: 'maya'  }),
  'inbox_v2':               flag<boolean>({ kind: 'release', default: false, owner: 'ananya', expiresAt: '2026-07-01' }),
} as const;

// Evaluation is ALWAYS workspace-scoped — flags differ per brand (graduation, Sale Mode, beta cohort)
const on = await flags.eval('inbox_v2', { workspaceId: ctx.workspaceId });
```

Rules: a flag default is the **safe** state (new behavior OFF, kill switch armable). Every flag carries an `owner` and an `expiresAt`. Flag reads are workspace-scoped because nearly every Brain flag varies per brand.

### Kill-switch wiring (ops flags — the safety-critical class)

Some flags are not features — they are **emergency brakes**, and they must take effect in seconds independent of any deploy:

- **Auto-execute Owner kill switch** — the canon's global + per-action-class switch that lets an **Owner pause all auto-execution in 60s** (`agentic-design`, `agentic-actions-auditor`). It is an ops flag, evaluated *before* any MCP write tool fires; flipping it OFF must propagate within the Redis TTL (or a pub/sub invalidation for instant effect). This is the single most important flag in Brain.
- **Sale / Event-Mode toggle** — switches the daily-tick to the higher-cadence configuration (hourly Path-A rollup + ML anomaly + Sonnet only at digest, with the margin-trap alert). An ops flag the Owner arms for a sale window.
- **Per-vendor / per-paradigm circuit toggles** — disable a misbehaving connector or force a degraded path (pairs with the circuit breakers in `observability`).

Kill switches are tested like any safety control: a drill flips the switch and verifies the next agent tick refuses to auto-execute. "We'll add the kill switch later" on an autonomous loop is a Stage-4 blocker (`agentic-actions-auditor`).

## 2. Flag lifecycle / cleanup (stale-flag debt)

A flag that has been at 100% for a month is dead code wearing a runtime cost. Stale flags rot: the OFF branch silently breaks, two flags interact unexpectedly, and nobody remembers which brands are on which path.

- Every **release** flag has an `expiresAt`. A CI check fails the build when a release flag is past expiry and still referenced.
- After a release reaches 100% and bakes, **delete the flag and the dead branch** in the next PR — close the loop, don't leave it.
- **Ops** flags (kill switches, Sale Mode) are permanent by design — they're exempt from expiry but still owned and inventoried.
- A monthly flag inventory (owner, kind, rollout %, age) surfaces debt; an `experiment` flag past its readout date is a smell.

## 3. Canary / gradual rollout (release flags)

A new behavior rolls out by a **growing audience slice with a bake window and automated analysis**, not a big-bang flip. Brain's deploy spine is ArgoCD on EKS (`devops-aws`); progressive delivery sits on top via Argo Rollouts-style canary steps gated by **automated canary analysis against the SLOs + error budget**.

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
   │
   └─ ANY analysis breach at any step → AUTO-ROLLBACK (flag→OFF, traffic→0) + alert
```

- **Traffic %** is the slice; **bake time** lets slow signals (error budget burn, a metric regression, a Sentry spike) surface before widening.
- **Automated canary analysis** compares the canary against the SLO targets and remaining error budget (`observability` SLO table — api p95, Morning Brief 07:20 IST, Decision Log write availability > 99.99%, auto-execute reversal rate). A breach **auto-rolls-back** by flipping the flag, not (only) by reverting the deploy — release-level rollback is seconds; redeploy is minutes. This complements the deploy-level auto-rollback in `devops-aws` (composite CloudWatch alarm → ArgoCD previous revision).
- For mobile, the analogue is EAS Update staged rollout % (OTA JS) vs full store review (native bump) — `app-store-deployment`.

## 4. Per-brand graduated rollout (the Brain-specific case)

This is where progressive delivery *is* a core product mechanic, not just infra. The canon's **auto-execute graduation is a per-tool, per-brand gradual rollout**: an agent's action starts **recommend-only** and graduates to **auto-execute** for a specific brand only after its track record clears thresholds over a 90-day rolling window (`agentic-design`, `canon/TECH/14_agent_roster.md` §6).

| Stage | Brain meaning | Flag state for `(workspace, tool)` |
|---|---|---|
| **Recommend-only** | action surfaces in Morning Brief for Owner approval | `autoexec.<tool>` = OFF |
| **Eligible** | thresholds met; Owner offered the graduation | OFF, eligible banner shown |
| **Graduated** | Owner enabled; tool auto-executes within caps | `autoexec.<tool>` = ON for that brand |
| **De-graduated** | accuracy/reversal regressed → auto-revert to recommend-only | flipped OFF by the nightly job |

The graduation thresholds are the canary analysis of the agentic world:

| Tool class | T_acc (outcome accuracy) | T_app (approval) | N_min (sample) | R_max (reverse rate) | Magnitude cap |
|---|---|---|---|---|---|
| Low-risk (negative keyword) | 75% | 65% | 30 | 5% | n/a |
| Medium (budget ≤10%) | 80% | 70% | 50 | 3% | ±10% |
| High (price change) | 85% | 75% | 100 | 2% | ≤5%; SKU <20% rev |
| Very high (courier reallocation) | 90% | 80% | 200 | 1% | brand opt-in only |

The graduation tracker (a nightly job in intelligence-service) is exactly an automated canary analysis: it watches outcome accuracy, approval rate, sample size, and **reverse-rate** per brand, **graduates** when all clear, and **auto-de-graduates** (auto-rollback) the instant a graduated tool regresses below threshold or its reversal rate spikes. The Owner can revoke at any time (a manual kill switch), and the global auto-execute kill switch (capability 1) overrides everything. Per-brand because a tool can be trustworthy for one brand's data and not another's.

## Red flags — STOP and BOUNCE

- A risky behavior shipped **without a flag** (no way to retreat without a redeploy).
- An **auto-execute path with no kill switch**, or a kill switch that needs a deploy to flip.
- A canary with **no bake time or no automated analysis** — a manual-eyeball flip is not progressive delivery.
- **No auto-rollback** wired to SLO / error-budget breach.
- A flag with **no owner or no expiry** (release kind) — future stale-flag debt.
- Flag evaluated **not workspace-scoped** — leaks one brand's beta/graduation state to another.
- An agent graduated to auto-execute **without the per-brand threshold check** (skips the canary of the agentic world).
- A dead 100%-for-a-month flag left in the tree.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "It's a small change, no flag needed" | Small changes break too; a flag is the difference between a 5-second retreat and a redeploy under pressure. |
| "We'll roll it to everyone, it's fine" | Canary + bake catch the slow regressions (error-budget burn, a metric drift) a big-bang flip hides. |
| "The Owner can just not enable auto-execute" | Per-brand graduation + the kill switch are the guardrails *for when they do* — they're mandatory, not optional. |
| "Flags are temporary, cleanup later" | "Later" is how you get 80 stale flags and an OFF branch nobody can prove still works. Expiry + CI gate. |
| "Auto-rollback is the same as the deploy rollback" | Deploy rollback is minutes (redeploy); flag rollback is seconds (flip). For a money-moving loop, you want the flip. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Flag system + canary steps + auto-rollback | **Jatin** (devops) | `devops-aws` (ArgoCD/EKS deploy spine) |
| Auto-execute kill switch + per-brand graduation tracker | **Maya** + Aryan | `agentic-design`, `agentic-actions-auditor` |
| Canary analysis vs SLO / error budget | **Jatin** + Maya | `observability` (SLO table + monitors) |
| Sale/Event-Mode toggle | Jatin + Maya | `morning-brief-mobile`, `agentic-design` |
| Mobile staged rollout (EAS Update %) | **Karan** | `app-store-deployment` |
| Incident retreat (flip flag, contain) | Jatin + on-call | `incident-response` / Stage 8 monitor |

## When to apply

- Shipping any **new behavior** that could regress a surface — wrap it in a release flag with a canary plan.
- Wiring any **autonomous / auto-execute** path — the kill switch + per-brand graduation are mandatory before it can fire.
- Arming **Sale/Event Mode** or any ops toggle.
- Periodic **flag inventory** / stale-flag cleanup.

## The bottom line

Make deploys boring and releases reversible. Ship dark behind a typed, workspace-scoped flag; widen by canary with automated SLO analysis and auto-rollback; arm a kill switch on anything autonomous; and treat the auto-execute graduation as exactly what it is — a per-brand, per-tool gradual rollout that auto-retreats the moment the numbers turn. Then delete the flag when it's done.

Related: `devops-aws` (deploy spine + deploy-level auto-rollback), `agentic-design` (the graduation tracker + recommend-only default), `agentic-actions-auditor` (the kill switch is an audited control), `observability` (SLOs + error budget the canary analysis reads), `incident-response` / Stage 8 (flip the flag to contain), `app-store-deployment` (mobile OTA staged rollout), `caching-strategy` (flag cache + invalidation).
