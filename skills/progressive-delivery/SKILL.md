---
name: progressive-delivery
description: Feature flags + canary that decouple release from deploy — tenant-scoped flags, 60s kill switches, SLO-analysed canary + auto-rollback, per-tenant graduation. Owner Platform/SRE.
---

# Progressive Delivery — Decouple Release from Deploy

> **Deploy** = code running in production. **Release** = behavior exposed to a user. `devops-aws` ships the artifact (CI → image registry → deploy controller); this skill decides *who sees the new behavior and when*, and *how fast to retreat* — without a redeploy.

Some products have high-stakes releases: a flag controls whether an automated agent **auto-executes consequential, money-moving actions** on a regulated channel for a specific tenant. Progressive delivery is the mechanism behind any auto-execute graduation and the tenant-owner kill switch the Canon may require.

## Owner: Platform/SRE. Three capabilities, one mental model

1. **Feature flags** — turn behavior on/off without a deploy.
2. **Gradual rollout** — expose to a growing slice (canary %, then per-tenant) with automated analysis + auto-rollback.
3. **Flag lifecycle** — every flag has a death date; stale flags are debt.

## 1. Flag management

Flags are **typed, tenant-scoped, and cached** — never a loose `if (env === 'prod')`. They live in a hot cache (`~60s` TTL, tenant-keyed per `caching-strategy`) backed by a Postgres source of truth in the core service, evaluated at the API-gateway / service boundary.

```typescript
// packages/lib-flags — typed registry; the compiler is the first guard
type FlagKind = 'release' | 'ops' | 'experiment' | 'permission';
interface Flag<T> { key: string; kind: FlagKind; default: T; owner: string; expiresAt: string; }
const FLAGS = {
  'high_load_mode':    flag<boolean>({ kind: 'ops',     default: false, owner: 'platform-sre' }),
  'autoexec.pause':    flag<boolean>({ kind: 'ops',     default: false, owner: 'intelligence' }),
  'inbox_v2':          flag<boolean>({ kind: 'release', default: false, owner: 'frontend',     expiresAt: '2026-07-01' }),
} as const;
const on = await flags.eval('inbox_v2', { tenantId: ctx.tenantId });  // ALWAYS tenant-scoped
```

A flag default is the **safe** state (new behavior OFF, kill switch armable). Every flag carries an `owner` and an `expiresAt`. Reads are tenant-scoped because most flags vary per tenant.

### Kill-switch wiring (ops flags — safety-critical)

Some flags are **emergency brakes** that take effect in seconds independent of deploy:

- **Auto-execute kill switch** — a global + per-action-class switch letting a tenant owner **pause all auto-execution in 60s** (pairs with `agentic-safety`). Evaluated *before* any write tool fires; flipping it OFF must propagate within the cache TTL (or pub/sub invalidation for instant effect). The single most important flag in an autonomous product.
- **High-load / event-mode toggle** — switches a scheduled job to a higher-cadence or degraded-cost config.
- **Per-vendor / per-tier circuit toggles** — disable a misbehaving connector or force a degraded path (pairs with the circuit breakers in `observability`).

Kill switches are drilled: flip the switch, verify the next agent tick refuses to auto-execute. "We'll add the kill switch later" on an autonomous loop is a Stage-4 blocker.

## 2. Flag lifecycle / cleanup (stale-flag debt)

A flag at 100% for a month is dead code with a runtime cost. The OFF branch silently breaks; flags interact unexpectedly.

- Every **release** flag has an `expiresAt`. CI fails when a release flag is past expiry and still referenced.
- After a release reaches 100% and bakes, **delete the flag and the dead branch** in the next PR.
- **Ops** flags (kill switches, high-load mode) are permanent by design — exempt from expiry but still owned + inventoried.
- A monthly flag inventory (owner, kind, rollout %, age) surfaces debt.

## 3. Canary / gradual rollout (release flags)

A growing audience slice with a bake window and automated analysis, not a big-bang flip. Sits on top of ArgoCD/EKS via Argo Rollouts-style canary steps gated by **automated canary analysis against SLOs + error budget**.

```
deploy (deploy controller, both code paths live, flag default OFF)
  ▼
canary 5%  ── bake 30m ──►  AnalysisRun: error rate, p99, new-error rate,
  ▼                          tier-bypass rate, audit-log write success
canary 25% ── bake 1h  ──►  vs SLO + error budget (observability)
  ▼
canary 50% ── bake 2h
  ▼
100% ──► bake 24h ──► delete flag + dead branch
   └─ ANY analysis breach at any step → AUTO-ROLLBACK (flag→OFF, traffic→0) + alert
```

- **Traffic %** is the slice; **bake time** lets slow signals surface before widening.
- **Automated canary analysis** compares against the SLO targets + remaining error budget (`observability` SLO table). A breach **auto-rolls-back by flipping the flag** (seconds), complementing the deploy-level auto-rollback in `devops-aws` (composite alarm → previous revision, minutes).
- For mobile, the analogue is the OTA staged-rollout % (JS-only update) vs full store review (native bump) — `app-store-deployment`.

## 4. Per-tenant graduated rollout (the autonomous-product case)

Where a product graduates automated actions, **auto-execute graduation is a per-tool, per-tenant gradual rollout**: an agent's action starts **recommend-only** and graduates to **auto-execute** for a tenant only after its track record clears thresholds over a rolling window (pairs with `agentic-safety`; see `examples/brain-instantiation/` for a worked instantiation).

| Stage | Meaning | Flag state for `(tenant, tool)` |
|---|---|---|
| **Recommend-only** | surfaces for owner approval | `autoexec.<tool>` = OFF |
| **Eligible** | thresholds met; owner offered graduation | OFF, eligible banner |
| **Graduated** | owner enabled; auto-executes within caps | ON for that tenant |
| **De-graduated** | accuracy/reversal regressed → auto-revert | flipped OFF by nightly job |

| Tool class | T_acc | T_app | N_min | R_max | Magnitude cap |
|---|---|---|---|---|---|
| Low-risk | 75% | 65% | 30 | 5% | n/a |
| Medium | 80% | 70% | 50 | 3% | ±10% |
| High | 85% | 75% | 100 | 2% | bounded |
| Very high | 90% | 80% | 200 | 1% | tenant opt-in only |

The graduation tracker (a nightly job) IS automated canary analysis: watches outcome accuracy, approval rate, sample size, and **reverse-rate** per tenant, graduates when all clear, and **auto-de-graduates** the instant a graduated tool regresses. The owner can revoke anytime; the global kill switch overrides everything. Per-tenant because a tool can be trustworthy for one tenant's data and not another's.

## Red flags — STOP and BOUNCE

- A risky behavior shipped **without a flag** (no retreat without redeploy).
- An **auto-execute path with no kill switch**, or one that needs a deploy to flip.
- A canary with **no bake time or no automated analysis**.
- **No auto-rollback** wired to SLO / error-budget breach.
- A release flag with **no owner or no expiry**.
- A flag evaluated **not tenant-scoped** — leaks one tenant's beta/graduation to another.
- An agent graduated to auto-execute **without the per-tenant threshold check**.
- A dead 100%-for-a-month flag left in the tree.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "Small change, no flag" | A flag is the difference between a 5-second retreat and a redeploy under pressure |
| "Roll it to everyone, it's fine" | Canary + bake catch the slow regressions a big-bang flip hides |
| "The owner can just not enable auto-execute" | Per-tenant graduation + kill switch are the guardrails *for when they do* |
| "Flags are temporary, cleanup later" | "Later" is 80 stale flags + an OFF branch nobody can prove works |
| "Auto-rollback = deploy rollback" | Deploy rollback is minutes; flag rollback is seconds — for a money-moving loop, you want the flip |

## Wiring

| Concern | Owner | Reference |
|---|---|---|
| Flag system + canary steps + auto-rollback | **Platform/SRE** | `devops-aws` |
| Auto-execute kill switch + graduation tracker | **AI/ML Engineer** + Architect | `agentic-safety` |
| Canary analysis vs SLO / error budget | **Platform/SRE** + AI/ML Engineer | `observability` |
| High-load / event-mode toggle | Platform/SRE + AI/ML Engineer | `agentic-safety` |
| Mobile staged rollout (OTA update %) | **Mobile Engineer** | `app-store-deployment` |
| Incident retreat (flip flag) | Platform/SRE + on-call | `incident-response` |

Make deploys boring and releases reversible. Ship dark behind a typed tenant-scoped flag; widen by canary with automated SLO analysis and auto-rollback; arm a kill switch on anything autonomous; treat auto-execute graduation as a per-tenant, per-tool rollout that auto-retreats. Then delete the flag when done.

## 2026 market update

- **Argo Rollouts** is the reference for canary / blue-green (Argo CD won GitOps vs Flux); analysis-driven promotion + auto-rollback on SLO breach unchanged.
- Pair flags/canary with **per-PR ephemeral preview environments** (`platform-engineering-idp`) so a change is exercised in a prod-like env before it canaries.
