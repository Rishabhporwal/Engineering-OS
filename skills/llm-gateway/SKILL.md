---
name: llm-gateway
description: Brain's model-agnostic LLM gateway — LiteLLM (OSS, self-hosted on EKS, ap-south-1) is the single OpenAI-format entry point every Python service calls instead of the Anthropic SDK directly. Routes @paradigm("small_llm"|"frontier_llm") to the cheapest model that passes that tier's eval bar (small → Nova Micro / Gemini Flash-Lite / Haiku; frontier → Claude Sonnet 4.6 default, eval-gated + swappable); does fallback, retries, semantic cache, per-workspace virtual-key budgets, cost tracking, OTel observability. Model-agnostic = "right model, justified on cost", NOT "avoid Claude". Backend (Bedrock vs native direct) deferred + reversible; India-resident inference for PII. Use when wiring a new LLM call site, adding a routed model, debugging fallback/budget, or wiring the Morning Brief SLO latency budget.
---

# LLM Gateway — Brain's Model-Agnostic Intelligence Front Door

Brain's intelligence layer is **model-agnostic behind a LiteLLM gateway** — not always Claude, but Claude where it earns its place. Every service that needs an LLM calls **one OpenAI-format API** (the gateway); the gateway decides *which model* runs the call. This is the runtime implementation of cost-routing paradigms 3 and 4: `@paradigm("small_llm")` / `@paradigm("frontier_llm")` names a **routed policy tier**, and the gateway routes each call to the **cheapest model that passes that tier's eval bar**.

> **Model-agnostic ≠ avoid Claude.** It means *the right model, justified on cost*. Claude **Sonnet 4.6 is the frontier default** (earned via synthesis quality + prompt caching) — it just has to keep earning it through the `llm-evals` gate, and it's swappable if a cheaper model passes the same bar.

**Canonical doc:** `canon/technical-requirements.md` §17.1 + `canon/TECH/12_cost_routing_compute.md` + `canon/TECH/05_intelligence_layer.md`. Owned by **Maya** (intelligence-service call sites) + **Jatin** (gateway infra/cost). This skill is the operational how-to. For the four-paradigm gate see [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md); for Claude-backend specifics see [`claude-api`](../claude-api/SKILL.md).

## What runs where — LiteLLM self-hosted on EKS (ap-south-1)

LiteLLM (OSS) runs **self-hosted on Brain's existing EKS** in **ap-south-1**, on the same Redis (ElastiCache) + Postgres it already operates — no new managed dependency. It is the unified OpenAI-format API + routing/fallback/semantic-cache/per-workspace-budgets/cost-tracking layer in front of every model backend.

- **HA:** **2+ stateless replicas behind the ALB** (the gateway holds no per-request state; Redis backs the semantic cache + budget counters, Postgres backs virtual-key config + the spend ledger). Lose a replica → ALB drains it; no call is lost.
- **No new region.** Inference egress respects DPDP residency (below); the gateway control plane stays in ap-south-1 with the rest of Brain.

## App code calls the gateway, NOT the Anthropic SDK directly

Every Brain Python service (intelligence-service, lifecycle-service, …) talks to the gateway through the **OpenAI-format client**, pointed at the gateway base URL. **Direct `anthropic.AsyncAnthropic()` / `import anthropic` call sites in app code are a code-review blocker** — they bypass routing, fallback, the virtual-key budget, the semantic cache, and the cost ledger.

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

- **Frontier default is Claude Sonnet 4.6**, earned on synthesis quality and prompt caching — documented eval-gated + swappable, never hard-pinned.
- **Small tier moves off Haiku** to Nova Micro / Gemini Flash-Lite — the cost win (below). Haiku stays as the small-tier safety net.
- The **fallback chain is a known-good degrade**: a failed swap or a single-provider stall drops to the next eval-passing model, never to "no answer". Claude stays in both chains as the fallback floor.

## Routing, fallback, retries, semantic cache

- **Routing:** per-tier `model_group` with least-cost-among-eval-passing ordering; LiteLLM load-balances within a model across keys/regions.
- **Fallback:** on provider error / timeout / 429-overload, LiteLLM advances down the tier's fallback chain automatically — the caller never sees a single-provider outage as a failed call.
- **Retries:** bounded exponential backoff per attempt before advancing the chain; deterministic 4xx (bad request) does **not** retry — it fails fast.
- **Semantic cache (Redis):** near-duplicate prompts return a cached completion (a cache hit is an LLM call you didn't pay for — same lever family as [`caching-strategy`](../caching-strategy/SKILL.md)). **Workspace-scope the cache key** — never serve one workspace's completion to another (cross-brand leak = P0). Prompt caching on the Claude backend (below) is separate and additive.

## Per-workspace virtual-key budgets = the cost caps

The per-workspace monthly LLM cap is **implemented as a LiteLLM virtual-key budget** — one virtual key per workspace, carrying that workspace's monthly INR cap. This **is** Layer 3 of the cost-routing enforcement (it replaces the bespoke `callClaudeWithBudget` wrapper as the runtime mechanism; the thresholds are unchanged):

| Tier | Virtual-key monthly budget (INR) | Behaviour |
|---|---|---|
| Founding (0.5%) | ₹3,000 | Soft 70% throttle non-critical · hard 100% critical-path only |
| Standard (1.0%) | ₹5,000 | Same |
| Growth (0.5% > ₹1Cr GMV) | ₹15,000 | Same |
| Enterprise | ₹50,000+ negotiated | Same |

- **Soft 70%:** non-critical LLM features (per-message personalisation, weekly creative briefs) pause; SQL/ML paths run normally.
- **Hard 100%:** only critical-path continues — **Morning Brief, NL query, ticket auto-resolution**. The system never breaks; it gets quieter.
- The 85/12/2.5/0.5 paradigm mix, the 1:100:1,000:10,000 cost ratio, and the **`@paradigm` PR gate are UNCHANGED** — the gateway is *how* paradigm 3/4 run, not a change to the gate. See [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md).

## Cost tracking + observability (OTel → CloudWatch)

LiteLLM emits per-call cost + tokens **tagged by `workspace_id` + feature + resolved model** to the cost ledger; spans export via **OpenTelemetry → CloudWatch** (+ X-Ray), stitched under Brain's one correlation ID (`request_id` + `trace_id` + `workspace_id`) propagated in `extra_headers`. Track per workspace+feature: tokens, cost, **which model the gateway actually routed to**, cache-hit rate, fallback rate, p50/95/99 latency. **Frontier-tier creep above 1% of total calls is a tier-1 incident** (Jatin pages) — unchanged. See [`observability`](../observability/SKILL.md).

## Prompt caching stays on the frontier backend

**Prompt caching is still the single biggest LLM cost lever** and is kept on the **frontier backend** (Anthropic prompt caching on the Claude path) — the synthesis system prompt + tool catalogue + Brand Fingerprint context (~3–10K tokens) reused across every workspace's 06:55–07:15 brief. This is **separate from and additive to** the gateway's semantic cache. Claude-backend prompt-caching mechanics live in [`claude-api`](../claude-api/SKILL.md); a cache miss on a stable prompt is a cost bug.

## Backend choice is DEFERRED + reversible behind the gateway

Whether the frontier (and small) tiers reach a model via **AWS Bedrock** or **native-provider direct clients** is **deferred and picked later per cost** — **do NOT hard-pin it.** Because every service calls the gateway (not a provider SDK), the backend is a config change behind a stable interface; swapping Bedrock ↔ native direct touches **only** the gateway, never app code. Hard constraints on **any** backend:

- **Prompt caching MUST be available on the frontier backend** (it's the biggest lever — a backend without it is disqualified for frontier).
- **DPDP residency** (below) — non-negotiable for PII-bearing calls.

## DPDP residency — India-resident inference for PII calls

PII-bearing calls (anything carrying customer phone/email/address/order PII) **must run on India-resident inference**. Concretely:

- **Redact PII before the gateway** wherever the task doesn't need it — hash/strip at the call site (see [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)); the gateway is the choke point to assert "no raw PII left ap-south-1".
- **For PII-bearing calls, route only to India-resident inference.** On the Bedrock backend this means **do NOT use Bedrock global cross-region inference (CRIS)** for those calls — global CRIS can dispatch inference outside India and breaks DPDP residency.
- Tag PII-bearing calls so the gateway pins them to an India-resident model/endpoint; non-PII calls may use the broader routing pool.

## Morning Brief SLO — the latency budget + fallback

The daily loop must deliver the **Morning Brief by 07:20 IST on >99.5% of days** (07:15 Sonnet synthesis → push 07:00–09:00 IST). The gateway protects this SLO:

- **A single-provider stall never misses the Brief.** The frontier fallback chain advances to the next eval-passing model within the latency budget rather than waiting out one provider's overload.
- The synthesis call carries a **latency budget**; on breach the gateway degrades down the chain (and the caller's own paradigm fallback drops to a template brief — see [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) Layer 2) so the 07:20 SLO holds.
- **Never** put an eval scorer on the 07:15 synthesis latency path — score asynchronously ([`llm-evals`](../llm-evals/SKILL.md)).

## Every model swap is `llm-evals`-gated

**No model serves a tier in production until it passes that tier's eval suite**, and the baseline is **re-run on any routed-model version bump**. Adding Nova Micro / Gemini Flash-Lite to `small_llm`, or swapping the `frontier_llm` default off Sonnet, is an evidence-gated change through [`llm-evals`](../llm-evals/SKILL.md) (golden-set + faithfulness + cost/latency re-check) coordinated with [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md). **Claude stays the frontier fallback** so a failed swap degrades to a known-good model. A new model wired into a routing policy without an eval pass is a blocker.

## The cost win (why this exists)

Moving the cheap tier off Haiku (~$1/$5 per 1M) to **Nova Micro (~$0.035/$0.14)** or **Gemini Flash-Lite (~$0.10/$0.40)** is **10–30× cheaper** on the small tier, for **~25–35% total LLM savings at Phase 3** — without touching the frontier quality bar (Sonnet stays the default there). The win comes from routing each tier to its cheapest eval-passing model, not from downgrading what frontier does.

## Production hardening (LiteLLM is battle-tested — but self-hosting means you own these)
LiteLLM is production-proven (1B+ requests, on the AWS Marketplace), but a self-hosted gateway has real production failure modes — harden for them:
- **Supply chain (P0 — this has bitten LiteLLM):** a **March 2026 PyPI supply-chain attack compromised LiteLLM 1.82.7/1.82.8** with credential-stealing malware. So: **pin the image by digest** (not a floating tag), build from a verified base, run **`vulnerability-scanning`** (Trivy/Snyk/pip-audit) + SBOM on the gateway image in CI, and treat any gateway dependency bump under the **`version-upgrade-policy`** EOL/security watch (avoid the compromised range). The gateway holds every provider key — it is the highest-value supply-chain target in the stack.
- **Throughput / GIL:** Python's GIL caps single-process throughput; benches show good P95 to ~1K RPS/replica. Run **2+ stateless replicas behind the ALB** (state in Redis/Postgres), autoscale on RPS/latency, and treat the gateway as **not a SPOF**. Brain's cost-routing keeps ~97% of calls off the LLM path, so the gateway sees modest RPS — but the daily-tick agent fan-out is bursty, so size for the 07:10–07:15 IST spike.
- **Graduation trigger:** if sustained RPS or latency outgrows the self-hosted proxy, evaluate LiteLLM Enterprise (SLA) or a managed gateway — a `tech-stack-evaluation` ADR, not a reactive swap. The OpenAI-format client makes that reversible.
- **Ops:** the gateway's Postgres (keys/spend) + Redis (cache) need the same backup/rotation/alerting as any service; rotate provider keys via `secrets-rotation`; trace it through OTel like everything else.

## Anti-patterns (code-review blockers)

- **App code instantiates `AsyncAnthropic()` / imports `anthropic` directly** → bypasses routing/fallback/budget/cache/cost-ledger. Call the gateway via the OpenAI-format client.
- **Hard-pinning a concrete model id at a call site** instead of a tier (`small_llm`/`frontier_llm`) → defeats model-agnostic routing + the eval gate.
- **Wiring a new model into a routing policy with no `llm-evals` pass** → an unproven model can serve production traffic.
- **PII-bearing call on Bedrock global CRIS** (or any non-India-resident endpoint) → DPDP residency violation (Shreya VETO).
- **Semantic-cache key not scoped to `workspace_id`** → cross-brand completion leak (P0).
- **Hard-pinning the Bedrock-vs-native backend in app code** → the backend must stay deferred + reversible behind the gateway.
- **No fallback chain on a tier** → a single-provider stall misses the 07:20 Morning Brief SLO.

## References

- `canon/technical-requirements.md` §17.1 — model-agnostic gateway + routed policy tiers
- `canon/TECH/12_cost_routing_compute.md` — paradigm 3/4 are gateway-implemented; virtual-key budgets
- `canon/TECH/05_intelligence_layer.md` — intelligence-service calls the gateway; synthesis default eval-gated
- [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) — the four-paradigm gate (the gateway runs paradigm 3/4)
- [`claude-api`](../claude-api/SKILL.md) — Claude as the frontier-default backend (model IDs, prompt caching, tool use, Batch API)
- [`agentic-design`](../agentic-design/SKILL.md) — the 15 product agents call the gateway
- [`llm-evals`](../llm-evals/SKILL.md) — the per-tier model-swap eval gate
- [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) — cadenced model-version bumps
- [`observability`](../observability/SKILL.md) — OTel → CloudWatch cost + routing telemetry
- [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) — PII redaction + India residency
