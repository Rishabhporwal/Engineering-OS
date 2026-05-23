---
name: agentic-design
description: Brain's product-internal AI-agent build pattern — the 15 AICMO/AICOO/AICFO + AI CX recommenders that live in intelligence-service. Agent base class, @paradigm + @mcp_tool decorators, the daily tick (06:55→07:15 IST fan-out → Sonnet Morning Brief synthesis), Memory Layer (Brand Fingerprint via pgvector) query pattern, graduation tracker, Decision Log writes, recommendation-only-until-graduated. These are PRODUCT agents, NOT the Engineering OS build team. Auto-load when creating/modifying a product-internal agent.
---

# Agentic Design — Brain's Product-Internal AI Agents

This skill covers **the product's internal AI agents** — the 15 AICMO/AICOO/AICFO + AI CX recommenders that Brain ships, living in `intelligence-service`. These are product features, NOT engineering-team members. Maya implements them; Aryan reviews the contracts. **Do not conflate these product agents with the 11-agent Engineering OS build team** (TECH/17) — they are different things.

> **Agents call the LiteLLM gateway, not the Anthropic SDK directly.** Every LLM step below resolves through Brain's model-agnostic gateway: `@paradigm("small_llm"|"frontier_llm")` names a **routed policy tier** and the gateway routes to the cheapest eval-passing model (frontier default = Claude Sonnet 4.6, eval-gated + swappable). The `@paradigm` + `@mcp_tool` decorators are unchanged; the model behind a tier is now gateway policy. See [`llm-gateway`](../llm-gateway/SKILL.md).

**Canonical doc:** `canon/TECH/14_agent_roster.md` (+ `canon/TECH/05_intelligence_layer.md`, `canon/technical-requirements.md` §9). This skill is operational.

## The agent roster — 15 product agents (canon/TECH/14)

Three groups + AI CX, all in `intelligence-service`. Every agent runs the daily tick, queries the Memory Layer, picks the cheapest paradigm per task (mostly ML), writes the Decision Log, and is **recommendation-only until graduated** (auto-execute is Phase 3, per-tool, per-brand, Owner-enabled).

**AICMO — Marketing Intelligence (8):** Meta · Google · TikTok *(GCC only — banned in India)* · Snap *(GCC only)* · Cross-Channel · Creative · Pricing · Festival.

**AICOO — Operations Intelligence (4):** Logistics · Returns · Inventory · Marketplace.

**AICFO — Financial Intelligence (3):** Conversion · Cashflow · Pricing-Margin.

**+ AI CX** — support-as-revenue agent (ticket classification → commerce-truth enrichment → impact estimate → autonomous/draft/escalate), counted alongside the 15 group agents.

> Phase mapping (TECH/14 §rollout): Phase 3 W23-26 brings Meta/Google/Conversion (alert-only); W27-30 Cross-Channel/Logistics/Returns/Cashflow; W31-36 Creative/Pricing/Inventory/Pricing-Margin; **Phase 4** TikTok/Snap/Festival/Marketplace + first auto-execute graduations. Every agent ships human-in-the-loop first.

## Universal agent pattern (canon/TECH/14_agent_roster.md §1, §5)

```python
# apps/intelligence-service/src/agents/_base/agent.py
from abc import ABC, abstractmethod

class Agent(ABC):
    name: str
    description: str

    async def daily_tick(self, workspace_id: UUID, as_of: date) -> list[Recommendation]:
        # 1. Memory query (find similar past states)
        history = await query_brand_fingerprint(workspace_id, as_of, k=5)
        # 2. Run paradigm-appropriate models (mostly ML)
        signals = await self._run_paradigm_models(workspace_id, as_of, history)
        # 3. Return ranked recommendations
        return self.rank_and_score(signals)

    @abstractmethod
    async def _run_paradigm_models(self, ...): ...
```

Every agent method carries `@paradigm(...)` + `@mcp_tool(...)`:

```python
# apps/intelligence-service/src/agents/aicmo/meta.py
from .._base import Agent, mcp_tool, paradigm
from .._base.memory_query import query_brand_fingerprint

class AICMOMeta(Agent):
    name = "aicmo-meta"
    description = "Meta Ads creative, budget pacing, ad-set optimisation"

    async def daily_tick(self, workspace_id, as_of):
        history = await query_brand_fingerprint(workspace_id, as_of, k=5)
        fatigue = await self.detect_creative_fatigue(workspace_id, as_of)
        budget = await self.recommend_budget_change(workspace_id, as_of, history)
        return self.rank_and_score([*fatigue, *budget])

    @paradigm("ml", model="ewma_ctr_v1")
    @mcp_tool("ai.agent.aicmo_meta.evaluate_creative_fatigue")
    async def detect_creative_fatigue(self, workspace_id, as_of) -> list[Recommendation]:
        # EWMA on CTR / CPM / CPA per campaign per ad set; threshold cross
        ...

    @paradigm("ml", model="budget_response_curve_v1")
    @mcp_tool("ai.agent.aicmo_meta.recommend_budget_change")
    async def recommend_budget_change(self, workspace_id, as_of, history) -> list[Recommendation]:
        # Isotonic regression on (spend, aMER); pick spend maximizing CM2 contribution
        ...

    @paradigm("integration_writeback")
    @mcp_tool("integrations.meta.adjust_campaign_budget")
    async def adjust_campaign_budget(self, workspace_id, campaign_id, new_daily_budget_minor, decision_log_id=None) -> AdjustmentResult:
        # Calls api-gateway MCP write tool; middleware auto-writes Decision Log
        ...
```

## Daily Tick Orchestration (canon/TECH/05_intelligence_layer.md; canon/technical-requirements.md §9)

```
06:55 IST — daily_tick.py fires
   ▼
For each workspace × each agent (parallel; each agent < 5 min budget):
   1. Memory query (Brand Fingerprint k=5 similar past states)
   2. Paradigm-appropriate models (mostly ML — EWMA, XGBoost, BG/NBD, pgvector cosine)
   3. Generate ranked recommendations
   4. Persist to Decision Log (state: pending if agent not graduated)
   ▼
07:15 IST — morning_brief.py fires
   ▼
Top-3 priority-scored across all agents per workspace
   ▼
@paradigm("frontier_llm", model="claude-sonnet-4-6", token_budget=2000)
   Sonnet synthesizes plain-English Morning Brief: action + magnitude + outcome + safety
   ▼
notifications-service receives ai.morning_brief.generated.v1 → push 07:00–09:00 IST
```

**The Morning Brief Synthesizer is the only Frontier-LLM call in the daily loop.** Everything upstream is paradigm 1 or 2. SLO: Morning Brief delivered by **07:20 IST on >99.5% of days**. (18:00 Evening Pulse · 23:55 7d/30d outcome attribution backfill run the same primitives at lower cadence.)

## Memory Layer (canon/TECH/05_intelligence_layer.md — Maya owns the schema)

```sql
-- Brand Fingerprint: one vector per brand per day
CREATE TABLE ai.brand_fingerprint (
  workspace_id        UUID NOT NULL,
  as_of_date          DATE NOT NULL,
  fingerprint         vector(16) NOT NULL,     -- pgvector; 16-dim daily brand-state vector (canon TECH/05)
  metrics_snapshot    JSONB NOT NULL,
  outcomes_7d         JSONB,
  outcomes_30d        JSONB,
  cross_brand_opt_in  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, as_of_date)
);
CREATE INDEX brand_fingerprint_hnsw ON ai.brand_fingerprint USING hnsw (fingerprint vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

Query helper:

```python
async def query_brand_fingerprint(workspace_id, as_of, k=5, cross_brand=False):
    """Cosine k-NN on Brand Fingerprint. Paradigm 2 (ML)."""
    consent_filter = "" if cross_brand else " AND workspace_id = $1"
    return await db.fetch(f"""
        SELECT workspace_id, as_of_date, similarity_score, outcomes_7d, outcomes_30d
        FROM (
          SELECT *, 1 - (fingerprint <=> (SELECT fingerprint FROM ai.brand_fingerprint WHERE workspace_id = $1 AND as_of_date = $2)) AS similarity_score
          FROM ai.brand_fingerprint
          WHERE as_of_date != $2 {consent_filter}
        ) sub
        ORDER BY similarity_score DESC
        LIMIT $3
    """, workspace_id, as_of, k)
```

## AI infrastructure layers (the `ai/` dir)

The monorepo's top-level `ai/` dir holds the cross-cutting AI infrastructure that every agent + AI workflow consumes (Single-Primitive Rule applied to AI). KEEP the custom agent base class + `@paradigm` cost-routing + Memory Layer — these layers sit *on top*, not instead.

| Layer | What it is | Brain rule |
|---|---|---|
| **Prompts** | Versioned, testable, evaluated prompt templates | Every prompt is a versioned artifact (`ai/prompts/<name>.vN`); no inline string prompts in agent code; changes go through eval before ship |
| **Guardrails** | Input/output validation, PII redaction, jailbreak + injection checks, schema enforcement on LLM output | Every Frontier-LLM call passes guardrails in + out; bad output → fallback, never raw-through to the user |
| **Evaluations / benchmarks** | Golden-set + regression evals per prompt/agent (accuracy, faithfulness, cost, latency) | A prompt change ships only if its eval ≥ baseline; CI gate (see `testing-tdd`) |
| **RAG** | Retrieval over Brand Fingerprint + decision history + brand notes | Retrieve-then-synthesize; cite supporting_data; retrieval is paradigm 1/2 (SQL/ML), synthesis is the only Frontier step |
| **Embeddings + vector-search** | Embedding generation + cosine k-NN on **pgvector** (NOT a dedicated vector DB) | Vectors live in `ai.brand_fingerprint` (pgvector); HNSW index; query via the Memory Layer helper |
| **Orchestration** | The agent base class + daily-tick + cross-agent choreography | Custom base class (NOT LangGraph); `@paradigm` + `@mcp_tool` on every action |

**Every AI workflow supports: tracing + retries + fallback + guardrails + observability.**

```
input → guardrails(in) → RAG retrieve (pgvector k-NN, paradigm 1/2)
      → paradigm-routed model (SQL>ML>small_llm>>frontier_llm — cost-routing gate)
      → guardrails(out) → schema-validated result
   with: X-Ray span per step · retry+backoff on transient LLM errors
        · fallback (template / lower-tier model) on budget breach or guardrail fail
        · structured log + cost metric per call (request_id/trace_id/workspace_id)
```

- **Tracing:** wrap each step in an X-Ray span (`observability`); the whole chain stitches under one `trace_id`.
- **Retries + provider fallback:** transient LLM errors → the gateway retries with backoff and advances down the tier's fallback chain (`llm-gateway`); deterministic failures → fallback, not retry.
- **Fallback:** budget breach or guardrail rejection → drop to a lower paradigm (small_llm, then template) rather than failing the Morning Brief.
- **Guardrails + observability:** mandatory on every call; the cost-routing audit (Frontier-LLM rate > 1%) is a tier-1 trigger (`cost-routing-paradigms`, `observability`).

Vectors stay on **pgvector** in `intelligence-service`'s Postgres (per-service DB ownership — `architecture-patterns`). Do NOT add a dedicated vector DB; do NOT replace the base class with LangGraph.

## Graduation framework (canon/TECH/14_agent_roster.md §6)

Per-agent, per-tool, per-brand. 90-day rolling window.

| Tool class | T_acc | T_app | N_min | R_max | Magnitude cap |
|---|---|---|---|---|---|
| Low-risk (add negative keyword) | 75% | 65% | 30 | 5% | n/a |
| Medium (budget change ≤10%) | 80% | 70% | 50 | 3% | ±10% |
| High (price change) | 85% | 75% | 100 | 2% | ≤5%; SKU <20% revenue |
| Very high (courier reallocation) | 90% | 80% | 200 | 1% | brand opt-in only |

**T_acc** = predicted-direction-matches-actual outcome (7d + 30d)
**T_app** = Owner approval rate
**N_min** = minimum logged recommendations
**R_max** = max % of fired recommendations that produced worse outcome than baseline

Owner can revoke graduation any time. Auto-degraduate when accuracy drops below threshold. Founder reviews retirement after 30 days of degraded performance.

## Recommendation shape

```python
@dataclass
class Recommendation:
    agent: str                          # "aicmo-meta"
    workspace_id: UUID
    as_of_date: date
    type: str                           # "creative_fatigue" | "budget_change" | ...
    priority_score: float               # 0-1
    rationale: str                      # for Morning Brief / web Insights
    action: str                         # what would happen if approved
    supporting_data: dict               # the math behind it
    mcp_writeback_tool: Optional[str]   # tool to invoke on approve
    mcp_writeback_args: Optional[dict]
    paradigm: str                       # which @paradigm produced this
```

## Cross-agent choreography (canon/TECH/14_agent_roster.md §5)

```
AICMO-Meta detects creative fatigue (ML)
   ▼
AICMO-Meta MCP-calls AICMO-Cross-Channel for reallocation
   ▼
AICMO-Cross-Channel optimises new allocation (ML)
   ▼
AICMO-Cross-Channel MCP-calls AICFO-Cashflow for verification
   ▼
AICFO-Cashflow returns "OK with this allocation"
   ▼
Morning Brief Synthesizer (Sonnet) writes the unified item
   ▼
Owner approves → MCP write-backs fire → Decision Log records the chain
```

This is the agentic pattern. Each agent is a specialist; the Morning Brief Synthesizer (only Frontier-LLM step) does cross-agent narrative.

## Agent ADR (one per agent — `memory/decisions/ADR-<NNN>-agent-<name>.md`)

Includes:
- Scope (one line)
- Paradigm map (per method)
- MCP tools exposed
- Graduation criteria + magnitude cap
- Cross-agent dependencies (who this agent calls, who calls it)
- Per-brand cost projection at expected volume
- Failure modes + auto-degraduation triggers

## Common failure modes

- **Defaulting to LLM in `_run_paradigm_models`** — Brain invariant violation; Aryan blocks. Detection: agent method uses Sonnet for what EWMA / XGBoost would solve.
- **Missing `@paradigm` on agent method** — cost-discipline dashboard can't track. CI rejects.
- **Stale Memory Layer** — fingerprint not updated daily → k-NN returns outdated patterns. Detection: `max(ai.brand_fingerprint.as_of_date) < now() - 2 days`.
- **Graduated agent regression** — outcome accuracy drops below T_acc but tool stays auto-execute. Nightly job auto-degraduates; ops follow-up.
- **Cross-brand pattern leak** — fingerprint query without `cross_brand_opt_in = TRUE` filter on consenting brand. Detection: pgvector query has no consent filter.
- **Recommendation spam** — agent produces >5 recommendations per workspace per day; Morning Brief Synthesizer drowns. Cap at agent.rank_and_score level.

## References

- `canon/TECH/14_agent_roster.md` — canonical 15-agent roster + graduation framework + rollout
- `canon/TECH/05_intelligence_layer.md` — Memory Layer (Brand Fingerprint, condition_outcome), daily loop, Plan Module, AI Chat
- `canon/TECH/13_mcp_protocol.md` — MCP tool registration + Decision Log middleware
- `canon/TECH/12_cost_routing_compute.md` — paradigm decorator
- `skills/cost-routing-paradigms/SKILL.md` — the four-paradigm gate
- `skills/llm-gateway/SKILL.md` — the LiteLLM gateway agents call for every LLM step (routed tiers, fallback, budgets)
- `skills/forecasting-prophet/SKILL.md` — Prophet for AICMO-Festival, AICOO-Inventory, AICFO-Cashflow
- `skills/mcp-protocol/SKILL.md` — agent.invoke + tool schemas
- `skills/claude-api/SKILL.md` — Claude as the frontier-default backend behind the gateway (prompt caching, retries — the Frontier-LLM step)
- `skills/observability/SKILL.md` — tracing + cost metrics + guardrail/fallback observability
- `skills/architecture-patterns/SKILL.md` — the `ai/` dir + pgvector per-service DB ownership
