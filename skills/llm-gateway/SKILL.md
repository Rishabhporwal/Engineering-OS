---
name: llm-gateway
description: A model-gateway reference implementation — a single OpenAI-format entry point in front of every model. Routes small/frontier tiers to the cheapest eval-passing model; fallback, cache, key budgets.
---

# LLM Gateway — a Model-Agnostic Intelligence Front Door

> **Reference implementation.** This skill documents one concrete binding of the model-access seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology (a managed gateway, a different proxy, or a
> direct SDK). The *patterns* here (one entry point, routed policy tiers, eval-gated routing, fallback,
> per-tenant budgets) are what transfer.

A model-agnostic gateway puts every LLM call behind **one OpenAI-format API** — the gateway decides *which model* runs the call. This is the runtime implementation of the cheapest-sufficient-effort doctrine for the small-model and large-model tiers: a tier name (`small_llm` / `frontier_llm`) names a **routed policy tier**, and the gateway routes each call to the **cheapest model that passes that tier's eval bar**.

> **Model-agnostic ≠ avoid any one provider.** It means *the right model, justified on cost*. A frontier model is the default only as long as it keeps earning it through the `llm-evals` gate, and it's swappable if a cheaper model passes the same bar.

**Canonical doc:** the Product Canon's cost/runtime + intelligence sections (`STACK.md`, `engineering-os-blueprint/11-runtime-and-cost-doctrine.md`). Owned by the **AI/ML Engineer** (call sites) + **Platform/SRE** (gateway infra/cost). For the cost-routing gate see [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md); for a Claude-backend reference see [`claude-api`](../claude-api/SKILL.md).

## What runs where — a self-hosted proxy (e.g. LiteLLM)

A self-hostable proxy runs in your own infra, on the cache + database it already operates — no new managed dependency. It is the unified OpenAI-format API + routing/fallback/semantic-cache/per-tenant-budgets/cost-tracking layer in front of every model backend.

- **HA:** **2+ stateless replicas behind a load balancer** (the gateway holds no per-request state; the cache backs the semantic cache + budget counters, the database backs virtual-key config + the spend ledger). Lose a replica → the LB drains it; no call is lost.
- **Residency:** inference egress respects the product's data-residency regime (below); the control plane stays in-region.

## App code calls the gateway, NOT a provider SDK directly

Every service talks to the gateway through the **OpenAI-format client**, pointed at the gateway base URL. **Direct provider-SDK call sites in app code are a code-review blocker** — they bypass routing, fallback, the virtual-key budget, the semantic cache, and the cost ledger.

```python
# the ONE entry point. Never instantiate a provider SDK in a service.
from openai import AsyncOpenAI

gateway = AsyncOpenAI(
    base_url=settings.LLM_GATEWAY_URL,            # the in-cluster load balancer, in-region
    api_key=tenant_virtual_key(tenant_id),        # per-tenant virtual key = the budget (below)
)

@paradigm("frontier_llm", token_budget=2000)      # names the TIER; the gateway picks the model
async def synthesize_brief(tenant_id, signals):
    resp = await gateway.chat.completions.create(
        model="frontier_llm",                     # a ROUTED POLICY TIER, not a hard model id
        max_tokens=2000,
        messages=[{"role": "system", "content": SYNTHESIS_PROMPT}, ...],
        extra_headers={"x-tenant-id": str(tenant_id), "x-trace-id": ctx.trace_id},
    )
    return resp.choices[0].message.content
```

`model="small_llm"` / `model="frontier_llm"` are **named tiers** (gateway `model_group`s), not model IDs. The `@paradigm` decorator and tier name agree; the gateway resolves the tier to a concrete model per the routing policy and eval bar.

## Routed policy tiers + the model routing policy table

Two LLM tiers map to the two model tiers of the cost doctrine. Within a tier, the gateway routes to the cheapest **eval-passing** model and falls down a chain on failure.

| Tier (`@paradigm`) | Task type | Default model | Fallback chain | Why |
|---|---|---|---|---|
| **`small_llm`** | Classification, intent, extraction, template personalisation, headline rewrite | the cheapest small model that passes the small-tier evals | → next eval-passing small model → a known-good small model | Bounded NL; far cheaper than a frontier model once it passes the small-tier evals |
| **`frontier_llm`** | Synthesis, chat orchestration, anomaly explanation, ambiguous agent reasoning | the cheapest frontier model that passes the frontier evals (eval-gated, swappable) | → next eval-passing frontier model → a known-good frontier model for the rare heavy slot | Synthesis quality + prompt caching justify the default; not pinned forever |

- **Each tier's default is eval-gated + swappable**, never hard-pinned.
- The **fallback chain is a known-good degrade**: a failed swap or single-provider stall drops to the next eval-passing model, never to "no answer".

## Routing, fallback, retries, semantic cache

- **Routing:** per-tier `model_group` with least-cost-among-eval-passing ordering; the gateway load-balances within a model across keys/regions.
- **Fallback:** on provider error / timeout / 429-overload, the gateway advances down the tier's fallback chain automatically — the caller never sees a single-provider outage as a failed call.
- **Retries:** bounded exponential backoff per attempt before advancing the chain; deterministic 4xx does **not** retry — it fails fast.
- **Semantic cache:** near-duplicate prompts return a cached completion (a cache hit is an LLM call you didn't pay for — same lever family as [`caching-strategy`](../caching-strategy/SKILL.md)). **Tenant-scope the cache key** — never serve one tenant's completion to another (cross-tenant leak = P0, [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)). Provider-side prompt caching on the frontier backend (below) is separate and additive.

## Per-tenant virtual-key budgets = the cost caps

The per-tenant monthly LLM cap is **implemented as a virtual-key budget** — one virtual key per tenant carrying its monthly cap. This **is** the runtime layer of cost-routing enforcement:

| Threshold | Behaviour |
|---|---|
| Soft (e.g. 70%) | non-critical LLM features (per-message personalisation, periodic creative briefs) pause; deterministic + ML paths run normally |
| Hard (100%) | only critical-path continues — the defining surface, NL query, auto-resolution. The system never breaks; it gets quieter |

The paradigm mix, the cost ratio, and the **`@paradigm` PR gate are UNCHANGED** — the gateway is *how* the model tiers run, not a change to the gate ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)).

## Cost tracking + observability

The gateway emits per-call cost + tokens **tagged by tenant + feature + resolved model** to the cost ledger; spans export via OpenTelemetry, stitched under the one correlation ID (`request_id` + `trace_id` + tenant key) propagated in `extra_headers`. Track per tenant+feature: tokens, cost, **which model the gateway actually routed to**, cache-hit rate, fallback rate, p50/95/99 latency. **Frontier-tier creep above its expected share of total calls is a tier-1 incident** (Platform/SRE pages). See [`observability`](../observability/SKILL.md).

## Prompt caching stays on the frontier backend

**Provider-side prompt caching is still the single biggest LLM cost lever** and is kept on the **frontier backend** — the synthesis system prompt + tool catalogue + stable context reused across calls. This is **separate from and additive to** the gateway's semantic cache. Mechanics live in [`claude-api`](../claude-api/SKILL.md); a cache miss on a stable prompt is a cost bug.

## Backend choice is DEFERRED + reversible behind the gateway

Whether a tier reaches a model via a **managed inference service** or **native-provider direct clients** is **deferred and picked later per cost** — **do NOT hard-pin it.** Because every service calls the gateway (not a provider SDK), the backend is a config change behind a stable interface; swapping touches **only** the gateway. Hard constraints on **any** backend:

- **Prompt caching MUST be available on the frontier backend** (a backend without it is disqualified for frontier).
- **Data residency** (below) — non-negotiable for PII-bearing calls.

## Data residency — in-region inference for PII calls

PII-bearing calls (carrying customer PII) **must run on in-region inference** per the product's residency regime (`COMPLIANCE.md`):

- **Redact PII before the gateway** wherever the task doesn't need it; the gateway is the choke point to assert "no raw PII left the region".
- **For PII-bearing calls, route only to in-region inference.** Avoid any cross-region inference routing for those calls — it can dispatch outside the residency boundary and break the regime.
- Tag PII-bearing calls so the gateway pins them to an in-region model/endpoint; non-PII calls may use the broader routing pool.

## Defining-surface SLO — the latency budget + fallback

When a defining surface has a delivery SLO (the Canon's `TRIGGER-SURFACES.md`), the gateway protects it:

- **A single-provider stall never misses the deadline.** The frontier fallback chain advances to the next eval-passing model within the latency budget rather than waiting out one provider's overload.
- The synthesis call carries a **latency budget**; on breach the gateway degrades down the chain (and the caller's own fallback drops to a deterministic template — [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)) so the SLO holds.
- **Never** put an eval scorer on the synthesis latency path — score asynchronously ([`llm-evals`](../llm-evals/SKILL.md)).

## Every model swap is `llm-evals`-gated

**No model serves a tier in production until it passes that tier's eval suite**, and the baseline is **re-run on any routed-model version bump**. Swapping a tier's default, or adding a model to a tier, is an evidence-gated change through [`llm-evals`](../llm-evals/SKILL.md) coordinated with [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md). **A known-good model stays in the fallback chain** so a failed swap degrades safely. A new model wired into a routing policy without an eval pass is a blocker.

## The cost win (why this exists)

Routing the cheap tier to the cheapest eval-passing small model (instead of a one-size-fits-all model) can be **10–30× cheaper** on the small tier, for meaningful total LLM savings — without touching the frontier quality bar. The win comes from routing each tier to its cheapest eval-passing model, not from downgrading what frontier does.

## Production hardening (self-hosting means you own these)

A self-hosted gateway has real failure modes:
- **Supply chain (P0):** the gateway holds every provider key — the highest-value supply-chain target in the stack. **Pin the image by digest** (not a floating tag), build from a verified base, run vulnerability scanning (Trivy/Snyk/pip-audit) + SBOM on the gateway image in CI, and treat any gateway dependency bump under the **[`version-upgrade-policy`](../version-upgrade-policy/SKILL.md)** EOL/security watch.
- **Throughput:** a Python proxy's GIL caps single-process throughput. Run **2+ stateless replicas behind the LB**, autoscale on RPS/latency, treat the gateway as **not a SPOF**. Cost-routing keeps most calls off the LLM path, but bursty fan-outs need headroom — size for the spike.
- **Graduation trigger:** if sustained RPS/latency outgrows the self-hosted proxy, evaluate a managed gateway — a [`tech-stack-evaluation`](../tech-stack-evaluation/SKILL.md) ADR, not a reactive swap.
- **Ops:** the gateway's database (keys/spend) + cache need the same backup/rotation/alerting as any service; rotate provider keys regularly; trace via OTel.

## Anti-patterns (code-review blockers)

- **App code instantiates a provider SDK directly** → bypasses routing/fallback/budget/cache/cost-ledger.
- **Hard-pinning a concrete model id at a call site** instead of a tier → defeats model-agnostic routing + the eval gate.
- **Wiring a new model into a routing policy with no `llm-evals` pass** → an unproven model serves production traffic.
- **PII-bearing call on cross-region inference** (or any out-of-region endpoint) → data-residency violation (Security VETO).
- **Semantic-cache key not scoped to the tenant** → cross-tenant completion leak (P0).
- **Hard-pinning the inference backend in app code** → must stay deferred + reversible behind the gateway.
- **No fallback chain on a tier** → a single-provider stall misses a defining-surface SLO.

## References

- Product Canon cost/runtime section — model-agnostic gateway + routed policy tiers
- `engineering-os-blueprint/11-runtime-and-cost-doctrine.md` — the cheapest-sufficient-effort doctrine
- [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`claude-api`](../claude-api/SKILL.md) · [`llm-evals`](../llm-evals/SKILL.md) · [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) · [`observability`](../observability/SKILL.md)
