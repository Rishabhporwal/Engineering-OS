---
name: cost-routing-paradigms
description: The cheapest-sufficient-effort cost gate — deterministic logic ≫ statistical/ML ≫ small model ≫ large model (~1:100:1k:10k cost). A per-PR routing audit + an effort-tier declaration on every path that calls a model.
---

# Cost-Routing Paradigms — cheapest sufficient effort

**Use the least-cost method that meets the bar.** A large-model call is on the order of **10,000×** a deterministic query, so one mis-routed feature can dwarf the budget of everything around it. Much of what the industry calls "agentic AI" is statistics in a model costume — don't pay frontier-model prices for problems statistics solved 40 years ago. This is a core OS principle (`engineering-os-blueprint/11-runtime-and-cost-doctrine.md §1`); this skill is the operational checklist.

> Where the product's economics make model cost a first-order constraint (e.g. usage-priced or thin-margin products), the Canon (`METRICS.md` / `THE-MOAT.md`) says so — and this gate becomes a hard release requirement, not a guideline.

## Phase-gate requirement (measure from day one, don't retrofit)

The cost-routing audit only works if it's **measured from the start, not bolted on later.**

- **Before any feature ships that calls a model, the effort-tier declaration + the cost telemetry are live:**
  - An effort-tier declaration (`@effort("deterministic" | "ml" | "small_model" | "large_model", model=..., token_budget=...)` or equivalent) on every path that calls a model.
  - A **cost-mix dashboard** (per-tenant per-day stacked bar; target most calls at the deterministic/ML tiers — see the default target mix below).
  - A **CI gate**: every PR adding an endpoint, action, or decision path that calls a model is rejected without an effort-tier declaration that matches the implementation.

- **A per-tenant spend cap (a throttle) must be live before the highest-model-cost feature ships.** Without it, one tenant ramping usage can blow past its budget. Thresholds are per-tier (see the cap table below).

Large-model creep above a small fraction of total calls (e.g. **1%**) is a high-priority incident the Platform/SRE role pages on.

## The four effort tiers

| # | Tier | When | Relative cost / call | Examples |
|---|---|---|---|---|
| 1 | **Deterministic logic** | Threshold, aggregation, lookup, rule | ~0 | Daily rollups, scoring against a formula, threshold alerts, "did X cross its goal?" |
| 2 | **Statistical / ML** | Pattern recognition, prediction, similarity, anomaly | very low | Moving averages / trend (e.g. fatigue detection), probabilistic forecasting, survival models, tree models for risk, vector cosine similarity |
| 3 | **Small model** | Bounded NL: classification, extraction, short structured output | low | Ticket classification on a bounded label set, short template personalization, headline rewriting |
| 4 | **Large model** | Multi-step synthesis, voice/tone, deep tool use, ambiguous reasoning | high | Narrative synthesis (the writing), conversational orchestration, ambiguous agent reasoning |

**Cost ratio roughly 1 : 100 : 1,000 : 10,000.** Wrong tier = 1–2 orders of magnitude wrong.

> **Tiers 3 & 4 are model-agnostic routed policy tiers.** `small_model` / `large_model` name a **routed policy tier** that a model gateway resolves to the **cheapest model that passes that tier's eval bar** (the Canon's `STACK.md` binds the gateway and the concrete models; the OS does not). The audit asks not just *which tier* but **which model the gateway routed to, and did it pass the eval bar at that cost.** Model-agnostic = "right model, justified on cost", **not** "avoid any one vendor." For routing/fallback/budget mechanics see `llm-gateway`.

## The four questions — ask in order, escalate only when the prior fails

```
Q1: Can deterministic logic solve this?  → tier 1; cron / stored proc / materialized view / rule
Q2: Can statistical/ML solve this?        → tier 2; classical stats / ML / vector similarity
Q3: Can a small model solve this?         → tier 3; bounded NL only
Q4: Does this need a large model?         → tier 4; reserved for the human-language interface / deep synthesis
```

## Mandatory PR template

Every PR that introduces a new endpoint, action, or decision path includes:

```markdown
## Cost Routing Audit

**Feature:** [name]
**Tier chosen:** [Deterministic / ML / Small model / Large model]
**Why:**
- Q1 Deterministic: [Yes — task is X / No because Y]
- Q2 ML: [Yes — chose <model> / No because]
- Q3 Small model: [Yes / No because]
- Q4 Large model: [Yes / N/A]

**Per-call cost estimate:** [amount, minor units + currency]
**Per-tenant monthly projection at <volume>:** [amount]
**Fallback if the tier fails:** [degrade to tier N-1]
```

The Architect blocks PRs missing this or with a mis-routed tier. CI parses the effort-tier declarations and rejects mismatched ones.

## The effort-tier declaration (mandatory on every endpoint + action)

```python
@effort("deterministic")
async def compute_daily_total(tenant_id, date):
    """Tier: deterministic. Reason: aggregation. Cost: ~0."""
    return await db.fetchval("SELECT SUM(...)", tenant_id, date)

@effort("ml", model="forecast_v1")
async def predict_value_30d(tenant_id, subject_id):
    """Tier: ML. Reason: probabilistic forecast. Cost: very low."""
    return value_model.predict(tenant_id, subject_id, horizon=30)

@effort("small_model")
async def classify_ticket(ticket_text):
    """Tier: small model. Reason: NL classification on a bounded label set."""
    return await small_model.classify(ticket_text, labels=TOP_LABELS)

@effort("large_model", token_budget=2000)
async def synthesize_brief(tenant_id, signals):
    """Tier: large model. Reason: multi-signal synthesis + tone. Cost: high."""
    return await large_model.synthesize(tenant_id, signals, prompt=BRIEF_PROMPT)
```

```typescript
import { effort } from '<cost-router>';
export const computeDailyTotal = effort('deterministic')(
  async (tenantId: string, date: string) => { /* ... */ }
);
```

## What "agentic" actually means here

| Industry framing | Reality | Tier |
|---|---|---|
| "AI detects when something is fatiguing" | moving average + threshold cross | Deterministic + ML — **not a model call** |
| "AI predicts future value" | probabilistic forecast model | ML — **not a model call** |
| "AI scores risk" | tree model on structured features | ML — **not a model call** |
| "AI finds similar past conditions" | vector cosine on an embedding | ML — **not a model call** |
| "AI recommends reallocation" | optimization over response curves | ML — **not a model call** |
| "AI writes the narrative" | large model on ML outputs | **Large model — yes** |

## Three layers of enforcement

### Layer 1 — Default routing
Every endpoint declares its tier in code. Default to the cheapest tier that solves the problem. Upgrading the tier requires PR-comment justification.

### Layer 2 — Per-feature token budget
```python
@effort("large_model", token_budget=2000)
async def synthesize_brief(tenant_id, signals):
    response = await large_model.synthesize(
        ...,
        max_tokens=2000,
        on_budget_warning=lambda: log_event("token_budget_80", tenant_id),
        on_budget_exceeded=lambda: fallback_to_template(tenant_id, signals),
    )
    return response
```
Soft warning at 80%; hard fail at 100% with graceful fallback (template or tier downgrade).

#### Two cost levers inside tiers 3/4 (apply once the model call is already justified)

Picking the right tier is the first-order lever. Once a call is *correctly* a model call, two features cut its cost further — **not** a substitute for choosing deterministic/ML:

| Lever | Saving | Where it applies |
|---|---|---|
| **Prompt caching** | large reduction on the cached portion | The biggest model lever — cache the stable prefix (system prompt + tool catalogue + shared context) reused across many calls. A cache miss on a stable prompt is a cost bug (`claude-api`). |
| **Batch / async API** | substantial discount | Non-interactive bulk work (backfills, nightly generation). **Never** batch latency-sensitive paths. |

Both still record tokens to the cost registry and stay under the per-tenant cap; they reduce the *cost per justified call*, leaving the target mix and the effort-tier gate unchanged.

### Layer 3 — Per-tenant spend cap (= gateway virtual-key budgets)

| Tier (product plan) | Monthly model-spend cap | Throttle behavior |
|---|---|---|
| (per the Canon's pricing tiers) | (per-tier cap, minor units + currency) | Soft warn ~70%; hard stop at 100% on non-critical |

The per-tenant cap is **implemented as a gateway virtual-key budget** — one virtual key per tenant carrying its monthly cap, enforced **in the gateway** (the runtime mechanism). Above cap: only critical-path work continues. The system never breaks; it gets quieter. See `llm-gateway`.

## Target cost mix

Most calls should land at the deterministic/ML tiers, a minority at small-model, and only a small fraction at the large-model tier. Large-model creep above ~1% of total calls is a high-priority incident — Platform/SRE investigates; the AI/ML Engineer audits prompts.

## Periodic streamlining audit

- Review the codebase for anti-pattern drift; flag duplication of cross-cutting concerns (Single-Primitive Rule violations).
- Document any tier-bypass (a model used where ML would have worked).
- **Refactoring time allocated explicitly** in the next cycle's plan — not optional.

## Common failure modes

- **Defaulting to a model** — the costliest engineering mistake. Detection: a `large_model` tier where ML would work. The Architect blocks at design.
- **No prompt caching** — inflates the model bill many-fold. Detection: a large-model call whose stable prefix has no cache marker.
- **Missing token budget** — an uncapped large-model call blows the per-tenant cap. Detection: a `large_model` tier without a `token_budget`.
- **No fallback on budget breach** — feature errors instead of degrading. Detection: error spike at the tenant cap.
- **Bypassing the effort-tier declaration** — call goes uncounted. Detection: a gateway model call (or, worse, a direct provider-SDK call — itself a blocker per `llm-gateway`) outside a declared function.

## References

- `engineering-os-blueprint/11-runtime-and-cost-doctrine.md` — the cheapest-sufficient-effort doctrine (tiers, caching, telemetry-as-gate)
- `llm-gateway` — the gateway that runs tiers 3/4 (routed tiers + virtual-key budgets)
- `claude-api` — prompt caching + batch mechanics for a justified model call
- The Product Canon's `METRICS.md` / `THE-MOAT.md` — whether (and how hard) cost is a first-order constraint for this product

## 2026 market update

- **Concrete model-cost mechanisms (verified 40–85% levers):** preference routing (**RouteLLM**) · **semantic caching** (GPTCache) · provider **prompt caching** · **Batch APIs** for non-latency-critical work. The gateway implements these (`llm-gateway`).
- **Infra cost is the peer discipline:** `finops-cost` (FOCUS / OpenCost) covers compute/storage/egress. Total unit economics = **model + infra** — quote both.
- **The effort ladder extends to post-training:** Prompt → RAG → **Fine-tune (LoRA/QLoRA)** → Distill. Fine-tune (a `model-fine-tuning` skill, if bound) only when routing + RAG can't clear the bar at cost.
