---
name: llm-gateway
description: LiteLLM (self-hosted EKS) — single OpenAI-format entry point, not the Anthropic SDK. Routes small_llm/frontier_llm to cheapest eval-passing model; fallback, cache, key budgets.
---

# LLM Gateway — Brain's Model-Agnostic Intelligence Front Door

Brain's intelligence layer is **model-agnostic behind a LiteLLM gateway** — not always Claude, but Claude where it earns its place. Every service that needs an LLM calls **one OpenAI-format API** (the gateway); the gateway decides *which model* runs the call. This is the runtime implementation of cost-routing paradigms 3 and 4: `@paradigm("small_llm")` / `@paradigm("frontier_llm")` names a **routed policy tier**, and the gateway routes each call to the **cheapest model that passes that tier's eval bar**.

> **Model-agnostic ≠ avoid Claude.** It means *the right model, justified on cost*. Claude **Sonnet 4.6 is the frontier default** (earned via synthesis quality + prompt caching) — it just has to keep earning it through the `llm-evals` gate, and it's swappable if a cheaper model passes the same bar.

**Canonical doc:** `canon/technical-requirements.md` §17.1 + `canon/TECH/12_cost_routing_compute.md` + `canon/TECH/05_intelligence_layer.md`. Owned by **Maya** (intelligence-service call sites) + **Jatin** (gateway infra/cost). For the four-paradigm gate see [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md); for Claude-backend specifics see [`claude-api`](../claude-api/SKILL.md).

## What runs where — LiteLLM self-hosted on EKS (ap-south-1)

LiteLLM (OSS) runs **self-hosted on Brain's existing EKS** in **ap-south-1**, on the same Redis (ElastiCache) + Postgres it already operates — no new managed dependency. It is the unified OpenAI-format API + routing/fallback/semantic-cache/per-workspace-budgets/cost-tracking layer in front of every model backend.

- **HA:** **2+ stateless replicas behind the ALB** (the gateway holds no per-request state; Redis backs the semantic cache + budget counters, Postgres backs virtual-key config + the spend ledger). Lose a replica → ALB drains it; no call is lost.
- **No new region.** Inference egress respects DPDP residency (below); the control plane stays in ap-south-1.

## App code calls the gateway, NOT the Anthropic SDK directly

Every Brain Python service talks to the gateway through the **OpenAI-format client**, pointed at the gateway base URL. **Direct `anthropic.AsyncAnthropic()` / `import anthropic` call sites in app code are a code-review blocker** — they bypass routing, fallback, the virtual-key budget, the semantic cache, and the cost ledger.

```python
# pylibs/brain_llm/client.py — the ONE entry point. Never instantiate AsyncAnthropic in a service.
from openai import AsyncOpenAI

gateway = AsyncOpenAI(
    base_url=settings.LITELLM_GATEWAY_URL,        # the in-cluster ALB, ap-south-1
    api_key=workspace_virtual_key(workspace_id),  # per-workspace virtual key = the budget (below)
)

@paradigm("frontier_llm", token_budget=2000)      # names the TIER; the gateway picks the model
async def synthesize_morning_brief(workspace_id, signals):
    resp = await gateway.chat.completions.create(
        model="frontier_llm",                     # a ROUTED POLICY TIER, not a hard model id
        max_tokens=2000,
        messages=[{"role": "system", "content": SYNTHESIS_PROMPT}, ...],
        extra_headers={"x-workspace-id": str(workspace_id), "x-trace-id": ctx.trace_id},
    )
    return resp.choices[0].message.content
```

`model="small_llm"` / `model="frontier_llm"` are **named tiers** (LiteLLM `model_group`s), not model IDs. The `@paradigm` decorator and tier name agree; the gateway resolves the tier to a concrete model per the routing policy and eval bar.

## Routed policy tiers + the model routing policy table

Two LLM tiers map 1:1 to the cost-routing paradigms. Within a tier, the gateway routes to the cheapest **eval-passing** model and falls down a chain on failure.

| Tier (`@paradigm`) | Task type | Default model (cheapest eval-passing) | Fallback chain | Why |
|---|---|---|---|---|
| **`small_llm`** (paradigm 3) | Ticket classification, intent, extraction, WhatsApp template personalisation, headline rewrite | **Amazon Nova Micro** (~$0.035/$0.14 per 1M) | → Gemini 2.5 Flash-Lite (~$0.10/$0.40) → Claude Haiku 4.5 | Bounded NL; 10–30× cheaper than Haiku-only once it passes the small-tier evals |
| **`frontier_llm`** (paradigm 4) | Morning Brief synthesis, AI Chat orchestration, anomaly explanation, ambiguous agent reasoning | **Claude Sonnet 4.6** (DEFAULT — eval-gated, swappable) | → (next frontier model that passed) → Claude Opus 4.7 for the rare heavy slot | Synthesis quality + prompt caching keep Sonnet the justified default; not pinned forever |

- **Frontier default is Claude Sonnet 4.6**, documented eval-gated + swappable, never hard-pinned.
- **Small tier moves off Haiku** to Nova Micro / Gemini Flash-Lite (the cost win, below). Haiku stays as the small-tier safety net.
- The **fallback chain is a known-good degrade**: a failed swap or single-provider stall drops to the next eval-passing model, never to "no answer". Claude stays in both chains as the fallback floor.

## Routing, fallback, retries, semantic cache

- **Routing:** per-tier `model_group` with least-cost-among-eval-passing ordering; LiteLLM load-balances within a model across keys/regions.
- **Fallback:** on provider error / timeout / 429-overload, LiteLLM advances down the tier's fallback chain automatically — the caller never sees a single-provider outage as a failed call.
- **Retries:** bounded exponential backoff per attempt before advancing the chain; deterministic 4xx does **not** retry — it fails fast.
- **Semantic cache (Redis):** near-duplicate prompts return a cached completion (a cache hit is an LLM call you didn't pay for — same lever family as [`caching-strategy`](../caching-strategy/SKILL.md)). **Workspace-scope the cache key** — never serve one workspace's completion to another (cross-brand leak = P0, [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)). Prompt caching on the Claude backend (below) is separate and additive.

## Per-workspace virtual-key budgets = the cost caps

The per-workspace monthly LLM cap is **implemented as a LiteLLM virtual-key budget** — one virtual key per workspace carrying its monthly INR cap. This **is** Layer 3 of the cost-routing enforcement (it replaces the bespoke `callClaudeWithBudget` wrapper as the runtime mechanism; thresholds unchanged):

| Tier | Virtual-key monthly budget (INR) | Behaviour |
|---|---|---|
| Launch (~1.0%) | ₹3,000 | Soft 70% throttle non-critical · hard 100% critical-path only |
| Growth (~0.75%) | ₹5,000 | Same |
| Scale (~0.5%) | ₹15,000 | Same |
| Enterprise (custom) | ₹50,000+ negotiated | Same |

- **Soft 70%:** non-critical LLM features (per-message personalisation, weekly creative briefs) pause; SQL/ML paths run normally.
- **Hard 100%:** only critical-path continues — **Morning Brief, NL query, ticket auto-resolution**. The system never breaks; it gets quieter.
- The 85/12/2.5/0.5 paradigm mix, the 1:100:1,000:10,000 cost ratio, and the **`@paradigm` PR gate are UNCHANGED** — the gateway is *how* paradigm 3/4 run, not a change to the gate ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)).

## Cost tracking + observability (OTel → CloudWatch)

LiteLLM emits per-call cost + tokens **tagged by `workspace_id` + feature + resolved model** to the cost ledger; spans export via **OpenTelemetry → CloudWatch** (+ X-Ray), stitched under Brain's one correlation ID (`request_id` + `trace_id` + `workspace_id`) propagated in `extra_headers`. Track per workspace+feature: tokens, cost, **which model the gateway actually routed to**, cache-hit rate, fallback rate, p50/95/99 latency. **Frontier-tier creep above 1% of total calls is a tier-1 incident** (Jatin pages). See [`observability`](../observability/SKILL.md).

## Prompt caching stays on the frontier backend

**Prompt caching is still the single biggest LLM cost lever** and is kept on the **frontier backend** (Anthropic prompt caching on the Claude path) — the synthesis system prompt + tool catalogue + Brand Fingerprint (~3–10K tokens) reused across every workspace's 06:55–07:15 brief. This is **separate from and additive to** the gateway's semantic cache. Mechanics live in [`claude-api`](../claude-api/SKILL.md); a cache miss on a stable prompt is a cost bug.

## Backend choice is DEFERRED + reversible behind the gateway

Whether the frontier (and small) tiers reach a model via **AWS Bedrock** or **native-provider direct clients** is **deferred and picked later per cost** — **do NOT hard-pin it.** Because every service calls the gateway (not a provider SDK), the backend is a config change behind a stable interface; swapping Bedrock ↔ native touches **only** the gateway. Hard constraints on **any** backend:

- **Prompt caching MUST be available on the frontier backend** (a backend without it is disqualified for frontier).
- **DPDP residency** (below) — non-negotiable for PII-bearing calls.

## DPDP residency — India-resident inference for PII calls

PII-bearing calls (carrying customer phone/email/address/order PII) **must run on India-resident inference**:

- **Redact PII before the gateway** wherever the task doesn't need it ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)); the gateway is the choke point to assert "no raw PII left ap-south-1".
- **For PII-bearing calls, route only to India-resident inference.** On Bedrock this means **do NOT use Bedrock global cross-region inference (CRIS)** for those calls — global CRIS can dispatch outside India and breaks DPDP residency.
- Tag PII-bearing calls so the gateway pins them to an India-resident model/endpoint; non-PII calls may use the broader routing pool.

## Morning Brief SLO — the latency budget + fallback

The daily loop must deliver the **Morning Brief by 07:20 IST on >99.5% of days** (07:15 Sonnet synthesis → push 07:00–09:00 IST). The gateway protects this SLO:

- **A single-provider stall never misses the Brief.** The frontier fallback chain advances to the next eval-passing model within the latency budget rather than waiting out one provider's overload.
- The synthesis call carries a **latency budget**; on breach the gateway degrades down the chain (and the caller's own paradigm fallback drops to a template brief — [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) Layer 2) so the 07:20 SLO holds.
- **Never** put an eval scorer on the 07:15 synthesis latency path — score asynchronously ([`llm-evals`](../llm-evals/SKILL.md)).

## Every model swap is `llm-evals`-gated

**No model serves a tier in production until it passes that tier's eval suite**, and the baseline is **re-run on any routed-model version bump**. Adding Nova Micro / Gemini Flash-Lite to `small_llm`, or swapping the `frontier_llm` default off Sonnet, is an evidence-gated change through [`llm-evals`](../llm-evals/SKILL.md) coordinated with [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md). **Claude stays the frontier fallback** so a failed swap degrades to a known-good model. A new model wired into a routing policy without an eval pass is a blocker.

## The cost win (why this exists)

Moving the cheap tier off Haiku (~$1/$5 per 1M) to **Nova Micro (~$0.035/$0.14)** or **Gemini Flash-Lite (~$0.10/$0.40)** is **10–30× cheaper** on the small tier, for **~25–35% total LLM savings at Phase 3** — without touching the frontier quality bar. The win comes from routing each tier to its cheapest eval-passing model, not from downgrading what frontier does.

## Production hardening (self-hosting means you own these)

LiteLLM is production-proven (1B+ requests, on the AWS Marketplace), but a self-hosted gateway has real failure modes:
- **Supply chain (P0 — this has bitten LiteLLM):** a **March 2026 PyPI supply-chain attack compromised LiteLLM 1.82.7/1.82.8** with credential-stealing malware. So: **pin the image by digest** (not a floating tag), build from a verified base, run **[`vulnerability-scanning`](../vulnerability-scanning/SKILL.md)** (Trivy/Snyk/pip-audit) + SBOM on the gateway image in CI, and treat any gateway dependency bump under the **[`version-upgrade-policy`](../version-upgrade-policy/SKILL.md)** EOL/security watch. The gateway holds every provider key — the highest-value supply-chain target in the stack.
- **Throughput / GIL:** Python's GIL caps single-process throughput (~1K RPS/replica P95). Run **2+ stateless replicas behind the ALB**, autoscale on RPS/latency, treat the gateway as **not a SPOF**. Cost-routing keeps ~97% of calls off the LLM path, but the daily-tick fan-out is bursty — size for the 07:10–07:15 IST spike.
- **Graduation trigger:** if sustained RPS/latency outgrows the self-hosted proxy, evaluate LiteLLM Enterprise or a managed gateway — a [`tech-stack-evaluation`](../tech-stack-evaluation/SKILL.md) ADR, not a reactive swap.
- **Ops:** the gateway's Postgres (keys/spend) + Redis (cache) need the same backup/rotation/alerting as any service; rotate provider keys via `secrets-rotation`; trace via OTel.

## Anti-patterns (code-review blockers)

- **App code instantiates `AsyncAnthropic()` / imports `anthropic` directly** → bypasses routing/fallback/budget/cache/cost-ledger.
- **Hard-pinning a concrete model id at a call site** instead of a tier → defeats model-agnostic routing + the eval gate.
- **Wiring a new model into a routing policy with no `llm-evals` pass** → an unproven model serves production traffic.
- **PII-bearing call on Bedrock global CRIS** (or any non-India-resident endpoint) → DPDP residency violation (Shreya VETO).
- **Semantic-cache key not scoped to `workspace_id`** → cross-brand completion leak (P0).
- **Hard-pinning the Bedrock-vs-native backend in app code** → must stay deferred + reversible behind the gateway.
- **No fallback chain on a tier** → a single-provider stall misses the 07:20 Morning Brief SLO.

## References

- `canon/technical-requirements.md` §17.1 — model-agnostic gateway + routed policy tiers
- `canon/TECH/12_cost_routing_compute.md` — paradigm 3/4 are gateway-implemented; virtual-key budgets
- `canon/TECH/05_intelligence_layer.md` — intelligence-service calls the gateway; synthesis default eval-gated
- [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`claude-api`](../claude-api/SKILL.md) · [`agentic-design`](../agentic-design/SKILL.md) · [`llm-evals`](../llm-evals/SKILL.md) · [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) · [`observability`](../observability/SKILL.md) · [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)
</content>
