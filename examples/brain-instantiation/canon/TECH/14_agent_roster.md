# TECH/14 — Agent Roster (AICMO + AICOO + AICFO)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 (agent implementations) + Founder (scope decisions) | **Reviewers:** E1
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/05_intelligence_layer.md](05_intelligence_layer.md), [TECH/12_cost_routing_compute.md](12_cost_routing_compute.md), [TECH/13_mcp_protocol.md](13_mcp_protocol.md)

This document defines Brain's agent roster: 8 sub-agents under AICMO, 4 under AICOO, 3 under AICFO. Each agent's:
- Scope
- Compute paradigm (per cost-routing principle)
- MCP tools it exposes
- Graduation criteria (when it moves from human-in-the-loop to auto-execute)

**Truncation note:** the source brief Section 7.2 listed the roster; Section 11 (graduation to auto-execute) was truncated. Graduation criteria below are constructed from the brief's stated intent.

---

## 1. Agent Architecture Pattern

Every agent in the roster follows the same shape:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          <Agent Name>                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Daily Tick (06:55–07:15 IST window)                           │ │
│  │  • Pulls inputs from data layer                                │ │
│  │  • Queries Memory Layer for relevant condition-outcome history│ │
│  │  • Runs paradigm-appropriate model(s)                          │ │
│  │  • Generates recommendation with priority score                │ │
│  │  • Writes to Decision Log (state: pending if not graduated)    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ MCP Surface (exposed via ai.agent.invoke)                     │ │
│  │  • Recommendations queryable                                   │ │
│  │  • Direct operations callable (e.g. adjust_meta_budget)        │ │
│  │  • Streaming reasoning (when invoked from frontier LLM)        │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Graduation Tracker                                             │ │
│  │  • Outcome accuracy (predicted vs actual at 7d + 30d)          │ │
│  │  • Owner approval rate                                         │ │
│  │  • Recovered revenue / cost ratio                              │ │
│  │  • Auto-execute graduation when thresholds met                 │ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Default Compute Paradigm (Cost-Routed)

Every agent uses **the cheapest paradigm that solves its task** ([TECH/12](12_cost_routing_compute.md)). Most agents are paradigm 2 (ML) + paradigm 4 only at the synthesis-and-explanation boundary (when the Morning Brief includes their recommendation).

---

## 2. AICMO — Marketing Intelligence (8 sub-agents)

**Multi-platform from day one.** Meta does not get more depth than Google. Brand-facing positioning is multi-platform, not Meta-first.

### 2.1 AICMO-Meta

**Scope:** Meta Ads. Creative performance, budget pacing, ad-set optimisation, audience expansion, CM2-aligned scaling.

**Paradigm:**
- **ML (paradigm 2):** EWMA on CTR / CPM / CPA for creative fatigue detection; XGBoost on creative metadata for performance prediction; isotonic regression for budget-vs-aMER curves
- **Small LLM (paradigm 3):** Creative copy variation suggestions (only when ML signals creative refresh need)
- **Frontier LLM (paradigm 4):** None directly — the Morning Brief synthesis aggregates AICMO-Meta output

**MCP tools exposed:**
- `ai.agent.aicmo_meta.evaluate_creative_fatigue`
- `ai.agent.aicmo_meta.recommend_budget_change`
- `ai.agent.aicmo_meta.recommend_audience_expansion`
- `integrations.meta.adjust_campaign_budget` (writeback)
- `integrations.meta.pause_ad_set` (writeback)

**Graduation criteria (auto-execute eligibility):**
- Outcome accuracy on budget change recommendations > 75% over trailing 30 recommendations
- Owner approval rate > 70% over trailing 30 recommendations
- Per-write tool: minimum 50 logged outcomes before graduation considered
- Auto-execute is per-tool: budget changes might graduate while ad-set pauses stay manual

**Daily tick output (example):**
```json
{
  "agent": "aicmo-meta",
  "brand_id": "...",
  "as_of_date": "2026-05-13",
  "recommendations": [
    {
      "type": "creative_fatigue",
      "priority_score": 0.84,
      "rationale": "Campaign X CTR declined 18% over 7d (EWMA). Similar historical conditions led to 22% spend waste before refresh.",
      "action": "Pause ads in campaign X; queue creative brief for AICMO-Creative",
      "supporting_data": { ... }
    }
  ]
}
```

### 2.2 AICMO-Google

**Scope:** Google Ads (Search + Shopping). Keyword bid management, negative keyword discovery, shopping feed health, audience expansion.

**Paradigm:**
- **ML:** Bid-response curves, search-query NLP clustering for negative keyword discovery, shopping feed quality scoring
- **Small LLM:** Negative keyword suggestion validation (semantic check)
- **Frontier LLM:** None directly

**MCP tools:**
- `ai.agent.aicmo_google.recommend_bid_changes`
- `ai.agent.aicmo_google.suggest_negative_keywords`
- `ai.agent.aicmo_google.audit_shopping_feed`
- `integrations.google.adjust_keyword_bid` (writeback)
- `integrations.google.add_negative_keyword` (writeback)

**Graduation criteria:** mirror AICMO-Meta. Negative keyword additions are lowest-risk and graduate first.

### 2.3 AICMO-TikTok

**Scope:** TikTok Ads creative + audience expansion. Spark Ads vs in-feed routing logic. **GCC only — TikTok is banned in India, so this agent is region-gated to UAE/GCC** (consistent with the region-gated TikTok connector in TECH/02 §7a / BR §9.2).

**Paradigm:** Same as AICMO-Meta (ML for creative fatigue + performance prediction).

**MCP tools:** Mirror AICMO-Meta with `tiktok` namespace.

**Graduation criteria:** Mirror AICMO-Meta. Lower default volume → may take longer to reach graduation thresholds per brand.

### 2.4 AICMO-Snap

**Scope:** Snapchat Ads. **GCC priority** (regional active.)

**Paradigm:** Same as TikTok.

**MCP tools:** Mirror AICMO-Meta with `snap` namespace.

**Graduation criteria:** Same.

### 2.5 AICMO-Cross-Channel

**Scope:** Media-mix budget allocation across Meta, Google, TikTok, Snap. The **single agent that decides budget split** by CM2 contribution per channel.

**Paradigm:**
- **ML:** Linear / convex optimisation over per-channel response curves with CM2 weighting; pgvector cosine on historical mix-vs-outcome from Memory Layer
- **Frontier LLM:** Used in synthesis when explanation goes into Morning Brief

**MCP tools:**
- `ai.agent.aicmo_cross_channel.recommend_allocation`
- `ai.agent.aicmo_cross_channel.simulate_allocation` (what-if without executing)

**Graduation criteria:** Higher bar than per-platform agents because allocation decisions are higher-stakes. Outcome accuracy > 80%; minimum 100 allocation cycles. Auto-execute only with ±10% allocation change cap per cycle (large shifts always need approval).

### 2.6 AICMO-Creative

**Scope:** Platform-agnostic creative performance benchmarking + creative brief generation. Consumed by AICMO-Meta, AICMO-Google, AICMO-TikTok, AICMO-Snap.

**Paradigm:**
- **ML:** Creative feature extraction (using vision models on cross-brand anonymised data); performance pattern matching
- **Small LLM:** Brief generation (template-driven, short-output)
- **Frontier LLM:** Used when brand-voice generation required (rare, on-demand)

**MCP tools:**
- `ai.agent.aicmo_creative.benchmark` — rank brand's creatives against (anonymised) network performance for similar product categories
- `ai.agent.aicmo_creative.generate_brief` — produce a creative brief for the brand's design team

**Graduation criteria:** Recommendations only; no auto-execute writeback. Briefs go to humans by design. Graduation here = recommendation quality threshold.

### 2.7 AICMO-Pricing

**Scope:** SKU-level price elasticity. Recommends price changes based on cross-brand patterns and brand's own historical price experiments.

**Paradigm:**
- **ML:** Elasticity estimation via log-log regression + cross-brand similarity (Memory Layer's pgvector); demand forecasts at different price points
- **Small LLM:** Plain-English rationale for price changes

**MCP tools:**
- `ai.agent.aicmo_pricing.recommend_sku_price`
- `ai.agent.aicmo_pricing.simulate_price_change`

**Graduation criteria:** Higher bar. Pricing mistakes are visible. Outcome accuracy > 85% on demand prediction at proposed price; minimum 50 implemented price changes with measured outcomes; auto-execute only on small-magnitude changes (≤5%) and only for SKUs below 20% of brand revenue.

### 2.8 AICMO-Festival

**Scope:** Demand calibration around festivals — Diwali, Ramadan, Eid, regional events. Adjusts forecasts and recommends spend timing.

**Paradigm:**
- **ML:** Festival-aware time-series models (Prophet with custom regressors); per-brand festival uplift coefficients learned from prior years; cross-brand festival pattern matching for new brands without history
- **Small LLM:** Festival-narrative for Morning Brief

**MCP tools:**
- `ai.agent.aicmo_festival.forecast_festival_demand`
- `ai.agent.aicmo_festival.recommend_spend_timing`

**Graduation criteria:** Recommendation-only by default (festivals are too high-stakes for auto-execute). Graduation here = brand opting in to higher trust per year-over-year accuracy.

---

## 3. AICOO — Operations Intelligence (4 sub-agents)

### 3.1 AICOO-Logistics

**Scope:** Courier scoring, RTO mitigation, regional courier reallocation.

**Paradigm:**
- **ML:** DBSCAN clustering of RTO patterns by pincode × courier × AOV; XGBoost RTO-risk-per-order; Bayesian courier-performance scoring with shrinkage to prior

**MCP tools:**
- `ai.agent.aicoo_logistics.score_courier_for_order`
- `ai.agent.aicoo_logistics.recommend_courier_reallocation`
- `integrations.shiprocket.set_courier_priority` (writeback — Phase 3+)

**Graduation criteria:** Auto-execute courier reallocation when (a) outcome accuracy > 80% over 90 days AND (b) brand confirms cost-of-error tolerance. Most brands stay in approval mode here.

### 3.2 AICOO-Returns

**Scope:** Return reason clustering, refund-vs-replace routing.

**Paradigm:**
- **ML:** Return reason clustering (NLP embeddings + DBSCAN); refund-vs-replace decision model
- **Small LLM:** Return-reason classification when free-text reason is provided

**MCP tools:**
- `ai.agent.aicoo_returns.cluster_reasons`
- `ai.agent.aicoo_returns.recommend_resolution`

**Graduation criteria:** Refund-vs-replace can auto-execute once outcome (customer satisfaction post-resolution) > 85% over 200 cases.

### 3.3 AICOO-Inventory

**Scope:** Demand forecasting per SKU per channel, transfer recommendations between warehouses, reorder triggers.

**Paradigm:**
- **ML:** Per-SKU per-channel Prophet/ARIMA + cross-brand similar-SKU pattern matching (Memory Layer) for sparse-history SKUs

**MCP tools:**
- `ai.agent.aicoo_inventory.forecast_demand`
- `ai.agent.aicoo_inventory.recommend_reorder`
- `ai.agent.aicoo_inventory.recommend_transfer`

**Graduation criteria:** Reorder triggers auto-execute at small magnitudes (within ±20% of brand-set rolling reorder quantity). Larger changes need approval. Transfer recommendations never auto-execute (logistics + accounting implications).

### 3.4 AICOO-Marketplace

**Scope:** Marketplace-specific intelligence — BSR (Best Seller Rank) tracking on Amazon, listing health, A+ content optimisation, ratings recovery.

**Paradigm:**
- **ML:** BSR trend modelling; competitor pattern matching
- **Small LLM:** Listing copy review + suggestions
- **Frontier LLM:** A+ content generation (rare)

**MCP tools:**
- `ai.agent.aicoo_marketplace.audit_listing`
- `ai.agent.aicoo_marketplace.recommend_listing_changes`

**Graduation criteria:** Listing changes are recommendation-only by default (marketplace policy risk on auto-changes).

---

## 4. AICFO — Financial Intelligence (3 sub-agents)

### 4.1 AICFO-Conversion

**Scope:** COD vs Prepaid conversion patterns. Payment-method reallocation recommendations.

**Paradigm:**
- **ML:** Logistic regression on COD-conversion vs prepaid-conversion per pincode × AOV × time-of-day; Memory Layer cross-brand patterns for new pincodes

**MCP tools:**
- `ai.agent.aicfo_conversion.recommend_payment_routing`
- `ai.agent.aicfo_conversion.flag_high_risk_orders`

**Graduation criteria:** Per-order COD-block recommendations auto-execute when outcome > 80% (block correctly predicts RTO/non-payment) over 500 orders. High-impact, so graduation conservative.

### 4.2 AICFO-Cashflow

**Scope:** 30-day cashflow projection using GMV trajectory and CM2-correct P&L. Complements Razorpay's GoKwik Cashflow data.

**Paradigm:**
- **ML:** Time-series cashflow forecasting; settlement-lag modelling per payment provider; Memory Layer for seasonal cashflow patterns

**MCP tools:**
- `ai.agent.aicfo_cashflow.forecast_30d`
- `ai.agent.aicfo_cashflow.flag_cash_shortfall_risk`

**Graduation criteria:** Forecast-and-alert only. No auto-execute (cashflow decisions involve external action — vendor payments, credit lines).

### 4.3 AICFO-Pricing-Margin

**Scope:** Margin protection. Alerts when discount stacking, COD overheads, or RTO surges threaten CM2.

**Paradigm:**
- **ML:** CM2 anomaly detection + decomposition (which cost line broke margin); pgvector to surface similar past breakdowns from Memory

**MCP tools:**
- `ai.agent.aicfo_margin.audit_cm2_breakdown`
- `ai.agent.aicfo_margin.flag_margin_compression`

**Graduation criteria:** Alert-only. The "remediation" is recommending a price or policy change, executed via AICMO-Pricing or AICOO-Returns based on root cause.

---

## 5. Cross-Agent Choreography

The agents are NOT siloed. Many recommendations require choreographed multi-agent reasoning:

### Example: Creative Fatigue → Budget Reallocation → Recovered Revenue Estimate

```
AICMO-Meta detects creative fatigue (paradigm 2, ML)
       │
       ▼
AICMO-Meta MCP-calls AICMO-Cross-Channel for budget reallocation
       │
       ▼
AICMO-Cross-Channel optimises new allocation across Meta/Google/TikTok/Snap (paradigm 2, ML)
       │
       ▼
AICMO-Cross-Channel MCP-calls AICFO-Cashflow to verify allocation doesn't break cashflow
       │
       ▼
AICFO-Cashflow returns "OK with this allocation; cashflow stays positive"
       │
       ▼
Morning Brief Synthesizer (paradigm 4, Claude Sonnet) writes single Morning Brief item:
  "Pause campaign X creative; reallocate ₹50K/day from Meta to Google;
   expected to recover ₹2.8L over 30 days; cashflow neutral."
       │
       ▼
Owner approves on phone
       │
       ▼
MCP writebacks fire:
  integrations.meta.pause_ad_set
  integrations.google.adjust_keyword_bid
       │
       ▼
Decision Log records the chain. 7-day + 30-day outcome attribution backfills.
```

This is the agentic pattern. Each agent is a specialist; the **Morning Brief Synthesizer** (the only Frontier-LLM step) does the cross-agent narrative work.

---

## 6. Graduation Framework Detail

Graduation moves an agent's recommendations from **human-approve** to **auto-execute**. Per-tool, per-brand.

### Universal Graduation Criteria

An agent's tool graduates when ALL of the following hold over a 90-day rolling window:

1. **Outcome Accuracy ≥ T_acc** — predicted direction matches actual 7d + 30d outcome
2. **Owner Approval Rate ≥ T_app** — Owner approves at least this fraction of recommendations of this type
3. **Sample Size ≥ N_min** — minimum number of logged recommendations
4. **Reverse Outcomes ≤ R_max** — when recommendations DID fire (approved), the % that produced worse outcomes than baseline

| Tool Class | T_acc | T_app | N_min | R_max | Auto-execute Magnitude Cap |
|-----------|-------|-------|-------|-------|---------------------------|
| Low-risk writeback (e.g. add negative keyword) | 75% | 65% | 30 | 5% | n/a |
| Medium-risk (e.g. budget change ≤10%) | 80% | 70% | 50 | 3% | ±10% per cycle |
| High-risk (e.g. price change, large budget shift) | 85% | 75% | 100 | 2% | ≤5%; below 20% of revenue |
| Very-high-risk (e.g. courier reallocation) | 90% | 80% | 200 | 1% | Off by default; brand opt-in |

### Per-Brand Graduation

Graduation is per-brand. AICMO-Google's negative-keyword tool can be graduated for Brand A but not Brand B. Memory Layer's per-brand condition history drives the difference.

### Owner Override

Brand Owner can:
- **Revoke graduation** at any time (returns tool to human-approve mode)
- **Disable an agent** entirely
- **Set magnitude caps** stricter than the system default
- **Require explicit approval for specific SKUs / campaigns / customers**

All overrides logged in audit log.

### Graduation Telemetry

Per-agent dashboard in admin view shows:
- Graduation status per tool per brand
- Active outcome-accuracy in the rolling window
- Time-to-graduation forecast (when will this brand graduate this tool?)
- Reverse-outcome alerts (auto-degraduate if accuracy drops below threshold)

---

## 7. Phase Mapping

Per [TECH/03 §17](03_metrics_engine.md) and the implementation plan:

| Phase | Agents Live |
|-------|------------|
| **Phase 1** | None — wedge features only (web Calendar Report, First Product Cascade, MER/aMER) |
| **Phase 2** | None — Memory Layer scaffolding + RFM audience builder |
| **Phase 3 W23-26** | AICMO-Meta, AICMO-Google, AICFO-Conversion (alert-only) |
| **Phase 3 W27-30** | AICMO-Cross-Channel, AICOO-Logistics, AICOO-Returns, AICFO-Cashflow |
| **Phase 3 W31-36** | AICMO-Creative, AICMO-Pricing, AICOO-Inventory, AICFO-Pricing-Margin |
| **Phase 4** | AICMO-TikTok, AICMO-Snap, AICMO-Festival, AICOO-Marketplace; first graduations to auto-execute |

Each agent ships with **human-in-the-loop only**. Auto-execute graduation happens later, per the universal criteria above.

---

## 8. Agent Code Layout

```
apps/intelligence-service/
├── agents/
│   ├── _base/
│   │   ├── agent.py              # Base class; daily-tick hook; Decision Log writer; graduation tracker
│   │   ├── memory_query.py       # Shared memory-layer query helpers
│   │   └── mcp_decorator.py      # Auto-register tools to MCP server
│   ├── aicmo/
│   │   ├── meta.py
│   │   ├── google.py
│   │   ├── tiktok.py
│   │   ├── snap.py
│   │   ├── cross_channel.py
│   │   ├── creative.py
│   │   ├── pricing.py
│   │   └── festival.py
│   ├── aicoo/
│   │   ├── logistics.py
│   │   ├── returns.py
│   │   ├── inventory.py
│   │   └── marketplace.py
│   └── aicfo/
│       ├── conversion.py
│       ├── cashflow.py
│       └── pricing_margin.py
└── orchestration/
    ├── daily_tick.py             # 06:55–07:15 IST orchestrator; fans out to all agents
    └── morning_brief.py          # Paradigm-4 synthesis at 07:15
```

Every agent file follows the same template:

```python
# apps/intelligence-service/agents/aicmo/meta.py

from .._base import Agent, mcp_tool, paradigm
from .._base.memory_query import query_brand_fingerprint

class AICMOMeta(Agent):
    name = "aicmo-meta"
    description = "Meta Ads creative, budget pacing, ad-set optimisation"

    async def daily_tick(self, brand_id: UUID, as_of: date) -> list[Recommendation]:
        # 1. Memory query
        history = await query_brand_fingerprint(brand_id, as_of, k=5)
        # 2. Run paradigm-2 models
        fatigue_signals = await self.detect_creative_fatigue(brand_id, as_of)
        budget_signals = await self.recommend_budget_change(brand_id, as_of, history)
        # 3. Return ranked recommendations
        return self.rank_and_score([*fatigue_signals, *budget_signals])

    @paradigm("ml", model="ewma_ctr_v1")
    @mcp_tool("ai.agent.aicmo_meta.evaluate_creative_fatigue")
    async def detect_creative_fatigue(self, brand_id, as_of) -> list[Recommendation]: ...

    @paradigm("ml", model="budget_response_curve_v1")
    @mcp_tool("ai.agent.aicmo_meta.recommend_budget_change")
    async def recommend_budget_change(self, brand_id, as_of, history) -> list[Recommendation]: ...

    @paradigm("integration_writeback")
    @mcp_tool("integrations.meta.adjust_campaign_budget")
    async def adjust_campaign_budget(
        self, brand_id, campaign_id, new_daily_budget_minor, decision_log_id=None
    ) -> AdjustmentResult: ...
```

The `@paradigm` and `@mcp_tool` decorators are the link to [TECH/12](12_cost_routing_compute.md) (cost-routing) and [TECH/13](13_mcp_protocol.md) (MCP). Every tool advertised in MCP automatically registers; every paradigm declared automatically flows into the cost-discipline dashboard.

---

## 9. Open Questions

| # | Question | Owner | Resolution |
|---|----------|-------|-----------|
| 1 | Section 11 from source brief (graduation to auto-execute) — what specific criteria does the founder want overridden? | E1 + Founder | TBD when full brief available |
| 2 | Per-agent SLOs (latency on daily tick) | E1 + E4 | Daily tick window is 06:55-07:15 IST (20 min); each agent must complete within 5 min |
| 3 | Agent versioning — how do agents evolve while preserving Decision Log meaning? | E4 | Agent + tool versions tagged in Decision Log; outcome attribution segregates by version |
| 4 | Cross-brand pattern matching consent — explicit opt-in language? | E1 + Legal | Drafted in DPA; brands opt-in for cross-brand anonymised pattern contribution; receive cross-brand patterns in return |
| 5 | What if two agents disagree (AICMO recommends spend up, AICFO-Cashflow says down)? | E4 | Morning Brief Synthesizer arbitrates with priority on cashflow when difference is material; logs the conflict in Decision Log |
| 6 | Agent retirement — when an agent's recommendations consistently lose money? | E4 | Auto-degraduate; then disable after 30 days of degraded performance; founder reviews before deprecation |
