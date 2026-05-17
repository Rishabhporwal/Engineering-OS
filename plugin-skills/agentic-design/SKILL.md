---
name: agentic-design
description: Brain's product-internal agent pattern — the 15 AICMO/AICOO/AICFO agents that live inside intelligence-service. Auto-load whenever creating a new agent, modifying the agent base class, wiring the daily tick (06:55–07:15 IST), implementing graduation tracker, registering MCP tools, or querying the Memory Layer (Brand Fingerprint via pgvector). Every agent action carries @paradigm + @mcp_tool decorators.
---

# Agentic Design — Brain's Product-Internal AI Agents

This skill covers **Brain's product-internal AI agents** — the 15 AICMO/AICOO/AICFO recommenders Brain ships (TECH/14). These are product features, NOT engineering team members. Maya implements them; Aryan reviews the contracts.

**Canonical doc:** `docs/TECH/14_agent_roster.md`. This skill is operational.

## The 15 agents

**AICMO (Marketing Intelligence) — 8:**
- AICMO-Meta · AICMO-Google · AICMO-TikTok · AICMO-Snap · AICMO-Cross-Channel · AICMO-Creative · AICMO-Pricing · AICMO-Festival

**AICOO (Operations Intelligence) — 4:**
- AICOO-Logistics · AICOO-Returns · AICOO-Inventory · AICOO-Marketplace

**AICFO (Financial Intelligence) — 3:**
- AICFO-Conversion · AICFO-Cashflow · AICFO-Pricing-Margin

Phase mapping (TECH/14 §7): Phase 1–2 ship NO agents — wedge features only. Phase 3 W23–36 ships them progressively, alert-only at first. Phase 4 = first auto-execute graduations.

## Universal agent pattern (TECH/14 §1, §8)

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

## Daily Tick Orchestration (TECH/14 §8)

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
notifications-service receives ai.morning_brief.generated.v1 → push at 07:00 IST
```

**The Morning Brief Synthesizer is the only Frontier-LLM call in the daily loop.** Everything upstream is paradigm 1 or 2.

## Memory Layer (TECH/05 — Maya owns the schema)

```sql
-- Brand Fingerprint: one vector per brand per day
CREATE TABLE memory.brand_fingerprint (
  workspace_id        UUID NOT NULL,
  as_of_date          DATE NOT NULL,
  fingerprint         vector(128) NOT NULL,    -- pgvector
  metrics_snapshot    JSONB NOT NULL,
  outcomes_7d         JSONB,
  outcomes_30d        JSONB,
  cross_brand_opt_in  BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, as_of_date)
);
CREATE INDEX brand_fingerprint_ivfflat ON memory.brand_fingerprint USING ivfflat (fingerprint vector_cosine_ops);
```

Query helper:

```python
async def query_brand_fingerprint(workspace_id, as_of, k=5, cross_brand=False):
    """Cosine k-NN on Brand Fingerprint. Paradigm 2 (ML)."""
    consent_filter = "" if cross_brand else " AND workspace_id = $1"
    return await db.fetch(f"""
        SELECT workspace_id, as_of_date, similarity_score, outcomes_7d, outcomes_30d
        FROM (
          SELECT *, 1 - (fingerprint <=> (SELECT fingerprint FROM memory.brand_fingerprint WHERE workspace_id = $1 AND as_of_date = $2)) AS similarity_score
          FROM memory.brand_fingerprint
          WHERE as_of_date != $2 {consent_filter}
        ) sub
        ORDER BY similarity_score DESC
        LIMIT $3
    """, workspace_id, as_of, k)
```

## Graduation framework (TECH/14 §6)

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

## Cross-agent choreography (TECH/14 §5)

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
- **Stale Memory Layer** — fingerprint not updated daily → k-NN returns outdated patterns. Detection: `max(memory.brand_fingerprint.as_of_date) < now() - 2 days`.
- **Graduated agent regression** — outcome accuracy drops below T_acc but tool stays auto-execute. Nightly job auto-degraduates; ops follow-up.
- **Cross-brand pattern leak** — fingerprint query without `cross_brand_opt_in = TRUE` filter on consenting brand. Detection: pgvector query has no consent filter.
- **Recommendation spam** — agent produces >5 recommendations per workspace per day; Morning Brief Synthesizer drowns. Cap at agent.rank_and_score level.

## References

- `docs/TECH/14_agent_roster.md` — canonical roster + graduation framework
- `docs/TECH/05_intelligence_layer.md` — Memory Layer + Plan Module + AI Chat
- `docs/TECH/13_mcp_protocol.md` — MCP tool registration + Decision Log
- `docs/TECH/12_cost_routing_compute.md` — paradigm decorator
- `skills/cost-routing-paradigms/SKILL.md` — the four-paradigm gate
- `skills/forecasting-prophet/SKILL.md` — Prophet for AICMO-Festival, AICOO-Inventory, AICFO-Cashflow
- `skills/mcp-protocol/SKILL.md` — agent.invoke + tool schemas
