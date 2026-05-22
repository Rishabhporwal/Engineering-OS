---
name: cost-routing-paradigms
description: Brain's four-paradigm cost-routing gate. The engineering invariant behind %-of-GMV pricing — Brain bills a fraction of realized GMV, so per-decision LLM cost must stay near zero or the unit economics invert. Auto-load on every design + every PR that adds a new endpoint, agent action, or decision path. SQL ≫ ML ≫ Haiku ≫ Sonnet. Every feature passes Q1-Q4 audit before shipping. Build pipeline rejects PRs missing the @paradigm decorator or with a wrong-paradigm declaration. Cost ratio is 1:100:1,000:10,000.
---

# Cost-Routing Paradigms — Brain's Engineering Invariant

Brain bills **% of realized/delivered GMV** (Founding ~0.5% / Standard ~1.0% / Growth ~0.5% > ₹1Cr GMV / Enterprise custom) — never per-seat. That pricing only survives if **most decisions run at SQL or ML cost**, not frontier-LLM cost: a Sonnet call is ~10,000× an SQL query, so one mis-routed feature can eat a brand's entire monthly fee. Most of what the industry calls "agentic AI" is statistics in an LLM costume — don't pay frontier-LLM prices for problems statistics solved 40 years ago.

**Canonical doc:** `canon/TECH/12_cost_routing_compute.md` (+ `canon/technical-requirements.md` §9). This skill is the operational checklist.

## Phase-gate requirement (non-negotiable — from architecture review 2026-05-16)

The cost-routing audit only works if it's **measured from day one, not retrofitted in Phase 3.** Aryan's stack review (`memory/decisions/ADR-DRAFT-2026-05-16-stack-review.md` §Recommendations #1) makes this a hard requirement:

- **By W3–W6 (Phase 0 → Phase 1 boundary), Brain MUST have:**
  - `@paradigm("sql" | "ml" | "small_llm" | "frontier_llm", model=..., token_budget=...)` decorator implemented in `pylibs/brain_cost_router/`
  - **`paradigm_distribution` dashboard live** (per-workspace per-day stacked bar; target 85% SQL / 12% ML / 2.5% Haiku / 0.5% Sonnet)
  - **CI gate**: every PR adding an endpoint, agent action, or decision path that calls an LLM rejects without a `@paradigm` declaration that matches the implementation

- **Before any feature ships in Phase 1 that calls an LLM, the decorator + dashboard are live.** No "we'll add the telemetry in Phase 3" exceptions.

- **A per-workspace monthly LLM cost cap (Layer 3 throttle) must be live before the highest-LLM-cost feature ships** (e.g. AI Chat). Without it, a workspace ramping usage can blow past its %-of-GMV fee. Thresholds are per-tier (see the Layer 3 table below). See `skills/claude-api/SKILL.md` §"Per-brand monthly LLM cap".

Frontier-LLM creep above **1% of total calls** is a tier-1 incident (Jatin pages on it).

## The four paradigms

| # | Paradigm | When | Cost / call | Examples |
|---|---|---|---|---|
| 1 | **SQL** | Deterministic, threshold, aggregation | ~0 | Daily CM2 rollup, RFM scoring, threshold alerts, pincode aggregates, "did revenue cross goal?" |
| 2 | **ML / Statistical** | Pattern recognition, prediction, similarity, anomaly | <$0.001 | EWMA on CTR (creative fatigue), BG/NBD + Gamma-Gamma (LTV), Kaplan-Meier, XGBoost (RTO risk), pgvector cosine (Brand Fingerprint), Prophet / isotonic |
| 3 | **Small LLM (Haiku)** | Bounded NL: classification, extraction, short structured | $0.001–$0.01 | Ticket classification (top-10 types), WhatsApp template personalisation, Morning Brief headline rewriting |
| 4 | **Frontier LLM (Sonnet)** | Multi-step synthesis, brand voice, deep tool use | $0.05–$0.50 | Morning Brief synthesis (the writing), AI Chat orchestration, ambiguous agent reasoning |

**Cost ratio: 1 : 100 : 1,000 : 10,000.** Wrong paradigm = 1–2 orders of magnitude wrong.

## The four questions — ask in order, escalate only when the prior fails

```
Q1: Can SQL solve this?            → paradigm 1; CRON / stored proc / MV
Q2: Can ML solve this?              → paradigm 2; sklearn / statsmodels / Prophet / pgvector
Q3: Can a small LLM (Haiku) solve?  → paradigm 3; bounded NL only
Q4: Does this need Frontier (Sonnet)? → paradigm 4; reserved for human-language interface
```

## Mandatory PR template

Every PR that introduces a new endpoint, agent action, or decision path includes:

```markdown
## Cost Routing Audit

**Feature:** [name]
**Paradigm chosen:** [SQL / ML / Small LLM / Frontier LLM]
**Why:**
- Q1 SQL: [Yes — task is X / No because Y]
- Q2 ML: [Yes — chose <model> / No because]
- Q3 Small LLM: [Yes / No because]
- Q4 Frontier LLM: [Yes / N/A]

**Per-call cost estimate:** [$X.XX]
**Per-brand monthly projection at <volume>:** [₹Y]
**Fallback if paradigm fails:** [degrade to paradigm N-1]
```

Aryan blocks PRs missing this or with mis-routed paradigm. CI parses `@paradigm` decorators and rejects mismatched declarations.

## The `@paradigm` decorator (mandatory on every endpoint + agent action)

```python
# Python
@paradigm("sql")
async def compute_daily_revenue(workspace_id, date):
    """Paradigm: SQL. Reason: aggregation. Cost: ~$0."""
    return await db.fetchval("SELECT SUM(...)", workspace_id, date)

@paradigm("ml", model="bg_nbd_gg_v1")
async def predict_ltv_30d(workspace_id, customer_id):
    """Paradigm: ML (BG/NBD + Gamma-Gamma). Reason: probabilistic LTV. Cost: <$0.001."""
    return ltv_model.predict(workspace_id, customer_id, horizon=30)

@paradigm("small_llm", model="claude-haiku-4-5")
async def classify_ticket(ticket_text):
    """Paradigm: Small LLM. Reason: NL classification on bounded label set. Cost: ~$0.005."""
    return await haiku_client.classify(ticket_text, labels=TOP_10_TICKET_TYPES)

@paradigm("frontier_llm", model="claude-sonnet-4-6", token_budget=2000)
async def synthesize_morning_brief(workspace_id, signals):
    """Paradigm: Frontier. Reason: multi-signal synthesis + brand voice. Cost: ~$0.10/brief."""
    return await sonnet_client.synthesize(workspace_id, signals, prompt=MORNING_BRIEF_PROMPT)
```

```typescript
// TypeScript
import { paradigm } from '@brain/cost-router';

export const computeDailyRevenue = paradigm('sql')(
  async (workspaceId: string, date: string) => { /* ... */ }
);
```

## What "agentic" actually means in Brain (canon/TECH/12_cost_routing_compute.md §3)

| Industry framing | Brain | Paradigm |
|---|---|---|
| "AI detects when ad is fatiguing" | EWMA on CTR + threshold cross | SQL + ML — **not LLM** |
| "AI predicts customer LTV" | BG/NBD + Gamma-Gamma probabilistic model | ML — **not LLM** |
| "AI scores RTO risk" | XGBoost on (pincode, courier, AOV, COD flag, ...) | ML — **not LLM** |
| "AI finds similar past conditions" | pgvector cosine on Brand Fingerprint | ML — **not LLM** |
| "AI recommends budget reallocation" | Linear optimization over response curves | ML — **not LLM** |
| "AI writes the Morning Brief" | Sonnet on ML outputs | **Frontier LLM — yes** |

## Three layers of enforcement (canon/TECH/12_cost_routing_compute.md §4)

### Layer 1 — Default routing
Every endpoint declares paradigm in code. Defaulting to cheapest paradigm that solves the problem. Upgrading the paradigm requires PR comment justification.

### Layer 2 — Per-feature token budget
```python
@paradigm("frontier_llm", model="claude-sonnet-4-6", token_budget=2000)
async def synthesize_morning_brief(workspace_id, signals):
    response = await sonnet_client.synthesize(
        ...,
        max_tokens=2000,
        on_budget_warning=lambda: log_event("token_budget_80", workspace_id),
        on_budget_exceeded=lambda: fallback_to_template_brief(workspace_id, signals),
    )
    return response
```

Soft warning at 80%; hard fail at 100% with graceful fallback (template or paradigm downgrade).

### Layer 3 — Per-brand monthly cap

| Tier | Monthly LLM cap (INR) | Throttle behavior |
|---|---|---|
| Founding (0.5%) | ₹3,000 | Soft 70%; hard 100% on non-critical |
| Standard (1.0%) | ₹5,000 | Same |
| Growth (0.5% > ₹1Cr GMV) | ₹15,000 | Same |
| Enterprise | ₹50,000+ negotiated | Same |

`pylibs/brain_cost_router/middleware.py` enforces. Above cap: only critical-path (Morning Brief, NL query, ticket auto-resolution) continues. System never breaks; it gets quieter.

## Target paradigm distribution (canon/TECH/12_cost_routing_compute.md §5)

**85% SQL, 12% ML, 2.5% Haiku, 0.5% Sonnet.**

Frontier-LLM creep above 1% of total calls = tier-1 incident. Jatin investigates; Maya audits prompts.

## Quarterly streamlining audit (canon/TECH/12_cost_routing_compute.md §6)

Every quarter:
- Review codebase for anti-pattern drift
- Flag duplication of cross-cutting concerns (Single-Primitive Rule violations)
- Document any paradigm-bypass (LLM where ML would have worked)
- **Refactoring time allocated explicitly** in next quarter's plan — not optional

## Common failure modes

- **Defaulting to LLM** — the costliest engineering mistake at Brain. Detection: `@paradigm("frontier_llm")` on a feature where ML would work. Mitigation: Aryan blocks at design.
- **No prompt caching** — inflates Sonnet bill 10–30x. Anthropic best practice. Detection: `anthropic.messages.create(...)` without `cache_control`.
- **Missing token budget** — uncapped Sonnet blows per-brand cap. Detection: `@paradigm("frontier_llm")` without `token_budget=N`.
- **No fallback on budget breach** — feature errors instead of degrading. Detection: error spike at brand cap.
- **Bypassing the `@paradigm` decorator** — call goes uncounted in cost-discipline dashboard. Detection: `anthropic.messages.create` outside a `@paradigm`-decorated function.

## References

- `canon/TECH/12_cost_routing_compute.md` — canonical (four paradigms, three enforcement layers, target mix, quarterly audit)
- `canon/technical-requirements.md` §9 — AI/LLM layer & cost-routing summary
- `skills/agentic-design/SKILL.md` — how to wire @paradigm into agents
- `skills/mcp-protocol/SKILL.md` — paradigm tagging on MCP tools
