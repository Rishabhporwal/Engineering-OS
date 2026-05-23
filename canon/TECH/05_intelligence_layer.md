# TECH/05 — Intelligence Layer (intelligence-service + Memory Layer)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 (Analytics/ML) | **Reviewers:** E1, E3, Founder
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/03_metrics_engine.md](03_metrics_engine.md), [TECH/12_cost_routing_compute.md](12_cost_routing_compute.md), [TECH/13_mcp_protocol.md](13_mcp_protocol.md), [TECH/14_agent_roster.md](14_agent_roster.md)

---

## 0. Memory Layer — The Moat

Per Brain's first architectural principle: **Memory Is the Moat.** The Memory Layer is what makes Brain compound over time and become harder to replicate the longer a brand stays on it. A competitor with the same dashboards and integrations cannot match a brand's Brain after 12 months of accumulated condition-outcome pairs.

### 0.1 Five Memory Subsystems

| # | Subsystem | Storage | Used By |
|---|-----------|---------|---------|
| 1 | **Brand Fingerprint Vector** (16-dim daily) | pgvector in Postgres | Every agent's daily tick; cross-brand similarity |
| 2 | **Condition-Outcome Pair Log** | Postgres + pgvector | Every agent queries "find similar past conditions"; the engine of compounding learning |
| 3 | **Cross-Brand Benchmark Database** | Postgres (aggregated) | New brands cold-start; sparse-data brands; pattern surfacing |
| 4 | **Seasonal Codebook** (per-brand festival uplifts) | Postgres | AICMO-Festival; forecasting; Morning Brief seasonal narrative |
| 5 | **Customer Segment Memory** (daily RFM per customer) | Postgres | Lifecycle Layer audience builder; Customer-state lifecycle (TECH/03) |

### 0.2 Brand Fingerprint — The Business Moment Vector

16 dimensions capturing brand-state on a given day. Built each morning at 07:00 IST in the Daily Intelligence Loop.

```sql
CREATE TABLE brand_fingerprint (
  brand_id UUID NOT NULL,
  date DATE NOT NULL,
  vector vector(16) NOT NULL,
  components JSONB NOT NULL,                 -- human-readable per-component values
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (brand_id, date)
);
CREATE INDEX ON brand_fingerprint USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**Dimensions (initial 16):**
1. CM2 % of revenue (normalised to brand history)
2. Revenue trajectory (7d rolling)
3. MER (blended)
4. aMER (acquisition)
5. CAC (delivered)
6. AOV
7. New-customer share
8. Repeat-customer share
9. COD share
10. RTO rate (rolling)
11. Active inventory days
12. Discount depth
13. Channel concentration (Herfindahl)
14. Creative fatigue signal (mean EWMA across campaigns)
15. Seasonality position (days from nearest festival)
16. Cashflow runway (per AICFO-Cashflow)

16 is empirically tunable — start here, instrument, iterate.

### 0.3 Condition-Outcome Pair Log

Every recommendation becomes a Condition-Outcome pair when outcomes attribute back.

```sql
CREATE TABLE condition_outcome (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL,
  decision_log_id UUID NOT NULL REFERENCES decision_log(id),

  brand_fingerprint_at_decision vector(16) NOT NULL,
  condition_metadata JSONB,                  -- which signals triggered the agent

  agent_name TEXT NOT NULL,
  recommendation_type TEXT NOT NULL,
  recommendation_payload JSONB,
  was_approved BOOLEAN,
  was_auto_executed BOOLEAN,

  outcome_7d JSONB,
  outcome_30d JSONB,
  recovered_revenue_7d_minor BIGINT,
  recovered_revenue_30d_minor BIGINT,

  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  outcome_7d_recorded_at TIMESTAMPTZ,
  outcome_30d_recorded_at TIMESTAMPTZ
);
CREATE INDEX ON condition_outcome (brand_id, recorded_at DESC);
CREATE INDEX ON condition_outcome USING hnsw (brand_fingerprint_at_decision vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**Query pattern** every agent uses on every daily tick:

```sql
SELECT
  co.recommendation_type, co.was_approved,
  co.outcome_7d, co.outcome_30d,
  1 - (co.brand_fingerprint_at_decision <=> :current_fingerprint) AS similarity
FROM condition_outcome co
WHERE co.brand_id = :brand_id AND co.outcome_30d IS NOT NULL
ORDER BY co.brand_fingerprint_at_decision <=> :current_fingerprint
LIMIT 5;
```

This is the engine of compounding learning. Brain gets better at decisions for a specific brand because every prior decision + outcome lives here.

### 0.4 Cross-Brand Benchmark Database

Aggregated, anonymised patterns across the Brain network. **K-anonymity k≥5 enforced.**

```sql
CREATE TABLE cross_brand_pattern (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_type TEXT NOT NULL,
  pattern_signature_vector vector(16),
  brand_count INT NOT NULL CHECK (brand_count >= 5),
  category TEXT,
  region TEXT,
  aggregated_outcome JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);
CREATE INDEX ON cross_brand_pattern USING hnsw (pattern_signature_vector vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX ON cross_brand_pattern (pattern_type, category, region);
```

New brands without history → fall back to similar-category similar-region patterns. Bayesian blend with own data as it accumulates.

**Privacy:**
- Patterns derived from ≥5 brands (k-anonymity)
- No row-level brand data exposed
- Brand-level opt-in (in DPA) for contributing
- Brand always receives cross-brand patterns regardless of contribution opt-in

### 0.5 Seasonal Codebook + Customer Segment Memory

- **Seasonal Codebook:** per-brand per-event uplift multipliers. New brands fall back to cross-brand benchmark; learn own coefficients year over year.
- **Customer Segment Memory:** per-customer daily RFM scores + segment classification. Powered by single primitive in [TECH/11 §4](11_lifecycle_revenue_layer.md).

---

## 0.7 Daily Intelligence Loop (Per Brief Section 2.3)

The Memory Layer is built and queried in the Daily Intelligence Loop. **The product's heartbeat.** Timing is non-negotiable.

| Time (IST) | Event | What Runs |
|------------|-------|-----------|
| 06:55 | **Data pull** | All live integrations synced; yesterday's actuals committed |
| 07:00 | **Vector generation** | 16-dim Brand Fingerprint built per brand (paradigm 1 — SQL aggregation + numpy) |
| 07:05 | **Memory query** | pgvector cosine similarity finds 5 closest historical conditions per brand + cross-brand baseline |
| 07:10 | **Agent processing** | All agents (TECH/14) run in parallel; each returns priority score + recommended action |
| 07:15 | **Morning Brief assembly** | Top 3 priority actions selected; Brief synthesised by Claude Sonnet (paradigm 4); pushed to phone |
| Throughout day | **Approve / reject feedback** | Owner decisions flow into Decision Log |
| 18:00 | **Evening pulse** | Day's actuals vs forecast; exceptions flagged |
| 23:55 | **Outcome attribution (7d / 30d)** | Past decisions whose outcomes have matured update `condition_outcome` |
| Month-end | **Compound report** | Per-brand learnings summarised |

**The 20-minute window (06:55 → 07:15)** is the SLO-critical span. Failure = no Morning Brief = the product's defining surface is broken.

SLO: Morning Brief delivered by 07:20 IST > 99.5% of days.

---

## 0.8 Compute-Paradigm Map for the Memory Layer

Per [TECH/12](12_cost_routing_compute.md). Memory Layer operations:

| Operation | Paradigm |
|-----------|----------|
| Build Brand Fingerprint (SQL aggregation + numpy normalisation) | **1 — SQL** |
| pgvector cosine similarity query (top-K matches) | **1 — SQL** |
| Outcome attribution job (write back 7d/30d outcomes) | **1 — SQL** |
| Cross-brand pattern computation (k-anonymous aggregates) | **1 — SQL** |
| Seasonal codebook uplift calculation | **1 — SQL** + **2 — ML** (Prophet residuals) |
| Compound report monthly narrative | **4 — Frontier LLM** (only here) |

**Almost zero LLM cost in the Memory Layer.** This is why Brain can afford to query it constantly — every agent on every daily tick. Compounding learning at SQL economics.

---

This document continues with the original intelligence-service architecture and forecasting / anomaly / proactive AI / chat sections (Sections 1+ below). Those remain accurate; Section 0 above adds the Memory Layer specification.

---

This document specifies:
- intelligence-service architecture
- Forecasting (the Plan Module)
- Anomaly detection
- Proactive AI insight generation
- AI Chat with Claude tool use
- Predictive LTV
- Claude API integration: prompt caching, cost management

**Philosophy:** AI is a feature, not the foundation. Every claim Brain makes via LLM must trace back to a metric you can audit. The LLM enriches and summarizes — it does not invent numbers.

---

## 1. intelligence-service Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  intelligence-service (Python)                        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ gRPC Server                                                     ││
│  │  • GetForecast                                                  ││
│  │  • ListInsights                                                 ││
│  │  • SendChatMessage (streaming)                                  ││
│  │  • GetBudgetRecommendation                                      ││
│  │  • GetPredictedLTV                                              ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Sub-systems                                                     ││
│  │                                                                 ││
│  │  • Forecasting (Prophet, isotonic regression)                  ││
│  │  • Anomaly Detection (z-score, isolation forest)               ││
│  │  • Insight Generator (Claude orchestration)                    ││
│  │  • Chat Engine (Claude tool use)                               ││
│  │  • Budget Optimizer (constrained optimization)                 ││
│  │  • LTV Predictor (cohort extrapolation)                        ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Kafka Consumers                                                 ││
│  │  • analytics.metrics.daily_materialized.v1                      ││
│  │    → trigger anomaly scan + insight generation                  ││
│  │  • analytics.customer_state.changed.v1                          ││
│  │    → update predicted LTV                                       ││
│  │  • operations.settings_changed.v1                               ││
│  │    → invalidate forecasts                                       ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  Data Access:                                                         │
│   • Read: ClickHouse (historical metrics) via gRPC to analytics       │
│   • Read: Postgres (config) via gRPC to core                          │
│   • Write: Postgres `ai.*` schema (insights, forecasts, anomalies)    │
│   • External: Anthropic Claude API                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### Scaling

- Compute-light, LLM-bound (Claude rate limits)
- 2–10 pods; HPA on Claude call queue depth + CPU
- LLM calls funnel through a per-pod rate limiter to stay under Anthropic's limits

---

## 2. Forecasting — The Plan Module

The hardest engineering problem in Brain. Target: 15% MAPE at 30 days for active workspaces by Phase 3.

### Three Combined Models

```
┌─────────────────────────────────────────────────────────────────────┐
│                       COMBINED FORECAST                              │
└──────┬──────────────────────────────┬───────────────────────────────┘
       │                                │
   New Revenue                  Retention Revenue
       │                                │
   ┌───▼─────────┐                 ┌───▼─────────┐
   │ aMER curve  │                 │ Repeat order│
   │ × Spend plan│                 │ probability │
   │             │                 │ × Active    │
   │             │                 │   base      │
   └─────────────┘                 └─────────────┘
       │                                │
       └────────────┬───────────────────┘
                    │
              × Festival multiplier (regional)
              × Marketing event lift
                    │
                    ▼
              Final revenue forecast
              (with confidence intervals)
```

### Phase 1 Simple Forecast

```python
# apps/intelligence-service/src/forecast/simple.py

async def simple_forecast(workspace_id: str, target_dates: list[date]) -> list[Forecast]:
    """Phase 1: aMER-based forecast with three scenarios."""
    history = await analytics_client.get_daily_metrics(
        workspace_id=workspace_id,
        metric_names=['amer', 'ad_spend_minor', 'revenue_net_minor'],
        date_from=datetime.utcnow() - timedelta(days=90),
        date_to=datetime.utcnow(),
    )

    aMER_by_spend_q = bucket_amer_by_spend_quartile(history)

    workspace = await core_client.get_workspace(workspace_id)
    adapter = get_regional_adapter(workspace.home_region)

    spend_plan = await get_spend_plan(workspace_id, target_dates)

    forecasts = []
    for d in target_dates:
        spend = spend_plan.get(d, recent_avg_spend(history))
        quartile = which_quartile(spend, history)
        amer_dist = aMER_by_spend_q[quartile]

        festival_mult = await get_festival_lift(workspace_id, d, 'revenue_net_minor', adapter)

        new_rev_p25 = spend * amer_dist['p25'] * festival_mult
        new_rev_p50 = spend * amer_dist['p50'] * festival_mult
        new_rev_p75 = spend * amer_dist['p75'] * festival_mult

        ret_rev = await forecast_returning_revenue(workspace_id, d, festival_mult)

        forecasts.extend([
            Forecast(d, 'conservative', new_rev_p25 + ret_rev),
            Forecast(d, 'base',          new_rev_p50 + ret_rev),
            Forecast(d, 'optimistic',    new_rev_p75 + ret_rev),
        ])
    return forecasts
```

### Phase 3 Prophet-Based Forecast

```python
# apps/intelligence-service/src/forecast/prophet.py

from prophet import Prophet
import pandas as pd

async def build_revenue_forecast(workspace_id: str, horizon_days: int = 60) -> ForecastBundle:
    history = await fetch_history(workspace_id, days=540)
    df = pd.DataFrame({
        'ds': history.dates,
        'y':  history.revenue_net_minor,
        'spend': history.ad_spend_minor,
    })

    workspace = await core_client.get_workspace(workspace_id)
    adapter = get_regional_adapter(workspace.home_region)
    festivals_df = adapter.get_seasonal_events(year=datetime.utcnow().year)
    next_year = adapter.get_seasonal_events(year=datetime.utcnow().year + 1)
    festivals_df.extend(next_year)

    holidays = pd.DataFrame([
        {'holiday': f['event_type'], 'ds': pd.Timestamp(f['shopping_lift_start']),
         'lower_window': 0, 'upper_window': (f['shopping_lift_end'] - f['shopping_lift_start']).days}
        for f in festivals_df
    ])

    model = Prophet(
        holidays=holidays,
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='multiplicative',
        interval_width=0.80,
    )
    model.add_regressor('spend')
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon_days)
    future['spend'] = future['ds'].map(await get_planned_spend(workspace_id))
    forecast = model.predict(future)

    bundle = ForecastBundle(workspace_id=workspace_id, model_id='prophet_v1')
    for _, row in forecast.tail(horizon_days).iterrows():
        bundle.add(date=row['ds'].date(),
                   base=int(row['yhat']),
                   conservative=int(row['yhat_lower']),
                   optimistic=int(row['yhat_upper']))
    return bundle
```

### aMER Response Curve

```python
from sklearn.isotonic import IsotonicRegression

async def fit_amer_curve(workspace_id: str):
    history = await fetch_daily_metrics(workspace_id, ['ad_spend_minor', 'amer'], days=180)
    df = clean_spend_amer(history)

    iso = IsotonicRegression(increasing=False, out_of_bounds='clip')
    iso.fit(df['spend'].values, df['amer'].values)
    return iso
```

Used in budget recommendations: "If you increase Meta acquisition spend ₹2L → ₹3L/day, expected aMER drops 2.4x → 1.9x."

### Persistence

```sql
-- ai.forecasts table (TECH/01)
-- One row per (workspace, metric, target_date, scenario, model_id)
```

Forecasts regenerated nightly. Old versions retained for accuracy tracking.

### Accuracy Tracking

```sql
-- ai.forecast_accuracy
SELECT
  ws.id AS workspace_id,
  metric_name,
  AVG(ABS(error_pct)) AS mape_7d,
  AVG(ABS(error_pct)) FILTER (WHERE horizon_days = 30) AS mape_30d
FROM ai.forecast_accuracy
WHERE workspace_id = ws.id
  AND target_date >= NOW() - INTERVAL '30 days'
GROUP BY ws.id, metric_name;
```

A workspace with 30-day MAPE > 25% triggers an admin investigation alert.

---

## 3. Anomaly Detection

### Triggered By

Kafka event `analytics.metrics.daily_materialized.v1`. Anomaly detection runs immediately after daily metrics are ready.

```python
async def on_metrics_materialized(event):
    workspace_id = event['workspace_id']
    date = event['date']

    # Skip if too few historical days
    if await days_of_history(workspace_id) < 30:
        return

    anomalies = []
    for metric_name in ANOMALY_DETECTION_METRICS:
        anomalies.extend(await detect_zscore(workspace_id, metric_name, date))

    multivariate = await detect_multivariate(workspace_id, date)
    anomalies.extend(multivariate)

    for anomaly in anomalies:
        await persist_anomaly(anomaly)
        await kafka_producer.emit('intelligence.anomaly.detected.v1', anomaly)
```

### Z-Score Method

```python
async def detect_zscore(workspace_id, metric_name, today):
    """Standard statistical method. Festival-aware baseline."""
    series = await get_daily_metric_series(workspace_id, metric_name, today, days=60)
    baseline = series[-30:-1]

    # Festival adjustment
    workspace = await core_client.get_workspace(workspace_id)
    adapter = get_regional_adapter(workspace.home_region)
    festival_mult = await get_festival_lift(workspace_id, today, metric_name, adapter)
    expected = np.mean(baseline) * festival_mult
    sigma = np.std(baseline)

    if sigma == 0:
        return []
    z = (series[-1] - expected) / sigma
    if abs(z) > 2.0:
        return [Anomaly(
            workspace_id=workspace_id,
            metric_name=metric_name,
            date=today,
            observed_value=series[-1],
            expected_value=expected,
            deviation_z_score=z,
            detection_method='zscore',
            severity='warning' if abs(z) < 3 else 'critical',
        )]
    return []
```

### Multivariate (Isolation Forest)

For multi-metric anomalies (revenue normal but CAC abnormally high):

```python
from sklearn.ensemble import IsolationForest

async def detect_multivariate(workspace_id, today):
    features = ['revenue_net_minor', 'mer', 'amer', 'cac_blended_minor', 'aov_minor', 'orders_count']
    history = await fetch_multimetric_history(workspace_id, features, days=180)

    iso = IsolationForest(contamination=0.05, random_state=42)
    iso.fit(history.iloc[:-1])
    score = iso.decision_function(history.iloc[[-1]])[0]

    if score < -0.2:
        worst_feature = find_worst_outlier(history.iloc[-1], history.iloc[:-1])
        return [Anomaly(...)]
    return []
```

---

## 4. Proactive AI Insights

Shift from reactive (operator asks) to proactive (Brain pushes).

### Daily Insight Generation

Triggered by Kafka event `analytics.metrics.daily_materialized.v1` (after anomaly detection has run).

```python
async def generate_daily_insights(workspace_id: str, for_date: date):
    """Generates 3–7 prioritized insights for a workspace."""
    # 1. Assemble context (pure-data, auditable)
    context = await assemble_insight_context(workspace_id, for_date)

    # 2. Generate via Claude
    insights = await call_claude_for_insights(workspace_id, context)

    # 3. Persist with dedup
    for insight in insights:
        if not await is_duplicate(workspace_id, insight):
            insight_id = await save_insight(workspace_id, insight)
            await kafka_producer.emit('intelligence.insight.generated.v1', {
                'workspace_id': workspace_id,
                'insight_id': insight_id,
                **insight.to_dict()
            })
```

### Context Assembly

```python
async def assemble_insight_context(workspace_id, for_date):
    """Pure-data assembly. No LLM. Auditable."""
    return {
        'workspace': await core_client.get_workspace(workspace_id),
        'date': for_date.isoformat(),
        'metrics_snapshot': await analytics_client.get_metrics_snapshot(workspace_id, for_date),
        'metrics_vs_goals': await evaluate_goals(workspace_id, for_date),
        'anomalies': await fetch_anomalies(workspace_id, for_date),
        'trends': await detect_trend_changes(workspace_id, for_date),
        'inventory_warnings': await fetch_inventory_warnings(workspace_id),
        'pincode_updates': await fetch_pincode_recommendation_changes(workspace_id, days=7),
        'top_first_products': await fetch_top_first_products(workspace_id, days=30),
        'underperforming_first_products': await fetch_underperforming_first_products(workspace_id, days=30),
    }
```

### Claude Integration with Prompt Caching

```python
# pylibs/brain_intelligence/llm.py

from anthropic import AsyncAnthropic

client = AsyncAnthropic()

SYSTEM_PROMPT = """You are Brain, an analytics operating system for DTC brand operators in {region}.
You generate proactive daily insights from a workspace's metrics data.

CRITICAL RULES:
1. Every claim must reference a specific number from the provided context.
2. Never invent metrics. If a number isn't in the context, don't mention it.
3. Use {region_currency_format} number formatting.
4. Be specific, not generic. "CAC up 18% week-over-week" beats "marketing performance changed."
5. Prioritize insights by business impact, not just by anomaly magnitude.
6. Each insight has: title (≤80 chars), body (≤400 chars), evidence (metric refs), recommended_actions (1-3 specific steps).

Brand context:
{brand_context}

{regional_notes}
"""

INDIA_REGIONAL_NOTES = """
Indian DTC context to keep in mind:
- COD orders are 60-75% of volume and have higher RTO risk
- Festivals (Diwali, Navratri, Holi) drive 3-5x revenue spikes
- aMER is the diagnostic metric; MER alone hides acquisition problems
- Pincode-level economics matter
"""

US_REGIONAL_NOTES = """
US DTC context:
- Black Friday / Cyber Monday drives 4-7x revenue spikes
- BNPL adoption (Klarna, Affirm) affects checkout conversion
- Chargebacks are the post-purchase risk to watch
"""

async def call_claude_for_insights(workspace_id: str, context: dict) -> list[Insight]:
    region = context['workspace'].home_region
    brand_context_text = format_brand_context(context['workspace'])

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT.format(
                    region=region,
                    region_currency_format=currency_format_hint(region),
                    brand_context=brand_context_text,
                    regional_notes=regional_notes(region),
                ),
                "cache_control": {"type": "ephemeral"}                    # CRITICAL: cache the prompt prefix
            }
        ],
        messages=[{
            "role": "user",
            "content": f"Generate 3-7 prioritized insights for {context['date']}:\n\n{format_daily_context(context)}"
        }],
    )

    return parse_insights_response(response.content[0].text)
```

### Why Prompt Caching Matters at 100k req/min Scale

Without caching:
- 1,000 workspaces × 5K-token system prompt × $3/MTok input × 1 daily insight call
- = $15/day = **$450/month** just for daily insights

With caching (95% hit rate after first call per workspace per day):
- Cache writes: 1,000 × $0.0188/Mtok × 5K = $94/month
- Cache reads: 1,000 × $0.30/Mtok × 5K × 30 = $45/month
- Plus user message: 1,000 × $3/Mtok × 1.5K × 30 = $135/month
- **Total: ~$275/month**

At 1,000 workspaces with multiple insights/day, savings scale to **$2K+/month**.

Discipline: cache anything stable per workspace (brand metadata, prompt template, glossary). Don't cache anything that changes per call.

### Insight Schema

Same as v1.0. Persisted to `ai.insights` (Postgres).

### Dedupe

Same as v1.0 — signature-based, 3-day window, severity-aware.

---

## 5. AI Chat with Tool Use

Upgrades AI Chat from "summarize my dashboard" to "answer specific questions by querying real data."

### Architecture

```
User message
    │
    ▼
api-gateway gRPC → intelligence-service.SendChatMessage (streaming)
    │
    ▼
Claude (with tool definitions)
    │
    ├─► (decides to call query_metric)
    │       │
    │       ▼
    │   intelligence-service calls analytics-service.GetDailyMetrics via gRPC
    │       │
    │       ▼
    │   Returns to Claude as tool_result
    │
    └─► Claude generates user-facing response
            │
            ▼
        Streamed back to frontend via SSE
```

### Tool Definitions

```python
TOOLS = [
    {
        "name": "query_metric",
        "description": "Query a single metric for a date range and optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "enum": list(METRICS.keys())},
                "date_range": {"type": "array", "items": {"type": "string", "format": "date"}, "minItems": 2, "maxItems": 2},
                "granularity": {"type": "string", "enum": ["daily", "weekly", "monthly", "total"], "default": "total"},
                "filters": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string"},
                        "customer_type": {"type": "string", "enum": ["new", "returning"]},
                        "campaign_classification": {"type": "string"}
                    }
                }
            },
            "required": ["metric_name", "date_range"]
        }
    },
    {"name": "query_orders", "description": "..."},
    {"name": "query_products", "description": "..."},
    {"name": "query_pincode_reliability", "description": "..."},                    # India-specific
    {"name": "query_cohort", "description": "..."},
    {"name": "query_customer_lifecycle", "description": "..."}
]
```

### Chat Loop

```python
async def chat_loop_stream(workspace_id: str, conversation_id: str, user_message: str):
    messages = await fetch_conversation_history(workspace_id, conversation_id, limit=20)
    messages.append({"role": "user", "content": user_message})

    while True:
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT_CHAT_CACHED,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            async for chunk in stream:
                yield {'type': 'content_chunk', 'data': chunk.delta}

            response = await stream.get_final_message()

        await save_assistant_turn(workspace_id, conversation_id, response)

        if response.stop_reason == "end_turn":
            yield {'type': 'done'}
            return

        if response.stop_reason == "tool_use":
            tool_use = next(b for b in response.content if b.type == "tool_use")
            yield {'type': 'tool_call', 'data': {'name': tool_use.name, 'input': tool_use.input}}

            result = await execute_tool(workspace_id, tool_use.name, tool_use.input)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": json.dumps(result)}]
            })
            yield {'type': 'tool_result', 'data': {'name': tool_use.name}}
            continue

        # Other stop reasons
        yield {'type': 'done'}
        return
```

### Tool Execution

```python
async def execute_tool(workspace_id: str, tool_name: str, input: dict) -> dict:
    if tool_name == "query_metric":
        return await analytics_client.get_daily_metrics(
            workspace_id=workspace_id,
            **input,
        )
    elif tool_name == "query_orders":
        return await analytics_client.query_orders(workspace_id=workspace_id, **input)
    elif tool_name == "query_pincode_reliability":
        return await analytics_client.query_pincode_reliability(workspace_id=workspace_id, **input)
    # ...
```

### Cost Control

- Max 5 tool calls per user message (prevents loops)
- Conversation history capped at 20 turns (older summarized)
- Daily per-workspace token budget (enforced via `ai.workspace_llm_budget`)

---

## 6. Predictive LTV

### Cohort-Calibrated Extrapolation

```python
async def predict_ltv(workspace_id: str, customer_id: str, horizon_days: int = 180) -> int:
    customer = await analytics_client.get_customer(workspace_id, customer_id)
    cohort_month = customer.first_order_at.replace(day=1).date()

    cohort_curve = await fetch_cohort_revenue_curve(workspace_id, cohort_month)
    days_since_first = (date.today() - customer.first_order_at.date()).days
    current_revenue = customer.total_spent_minor

    cohort_expected_now = interpolate(cohort_curve, days_since_first)
    cohort_expected_horizon = interpolate(cohort_curve, days_since_first + horizon_days)

    customer_ratio = current_revenue / cohort_expected_now if cohort_expected_now > 0 else 1.0
    predicted_horizon = cohort_expected_horizon * customer_ratio

    return int(predicted_horizon - current_revenue)
```

### Phase 4: BG/NBD + Gamma-Gamma

```python
from lifetimes import BetaGeoFitter, GammaGammaFitter

# Standard DTC LTV pipeline
bgf = BetaGeoFitter(penalizer_coef=0.0001)
bgf.fit(rfm['frequency'], rfm['recency'], rfm['T'])

ggf = GammaGammaFitter(penalizer_coef=0.01)
ggf.fit(rfm[rfm['frequency'] > 0]['frequency'], rfm[rfm['frequency'] > 0]['monetary_value'])

ltv_180 = ggf.customer_lifetime_value(bgf, rfm['frequency'], rfm['recency'], rfm['T'],
                                       rfm['monetary_value'], time=6, freq='D')
```

### Storage

`customer_lifetime_value_local` (ClickHouse). Predicted columns populated nightly.

---

## 7. Budget Allocation Recommendations

```python
from scipy.optimize import minimize

async def recommend_budget_allocation(workspace_id, total_budget_minor, horizon_days):
    channels_classifications = [
        ('meta', 'acquisition'), ('meta', 'non_acquisition'),
        ('google_ads', 'acquisition'), ('google_ads', 'non_acquisition'),
    ]

    curves = {ch_cls: await fit_response_curve(workspace_id, *ch_cls)
              for ch_cls in channels_classifications}

    def neg_total_revenue(spends):
        return -sum(curves[cc](s) * s for cc, s in zip(channels_classifications, spends))

    constraints = [{"type": "eq", "fun": lambda s: sum(s) - total_budget_minor}]
    bounds = [(0, total_budget_minor)] * len(channels_classifications)
    x0 = [total_budget_minor / len(channels_classifications)] * len(channels_classifications)

    result = minimize(neg_total_revenue, x0, constraints=constraints, bounds=bounds)
    return {cc: int(spend) for cc, spend in zip(channels_classifications, result.x)}
```

Surfaced as weekly insight: "Shifting ₹50K/day from Meta Acquisition to Google Acquisition would lift projected revenue by ₹4.2L over 30 days."

Brain **suggests**; does not auto-execute. Phase 5+ for opt-in autopilot.

---

## 8. Cost Management

### Per-Workspace Token Budgets

```sql
CREATE TABLE ai.workspace_llm_budget (
  workspace_id UUID PRIMARY KEY,
  monthly_budget_usd_micros BIGINT NOT NULL DEFAULT 5000000,           -- $5
  current_month_spent_usd_micros BIGINT NOT NULL DEFAULT 0,
  current_month_started_at DATE NOT NULL DEFAULT date_trunc('month', NOW())::date,
  blocked_until TIMESTAMPTZ
);
```

### LLM Call Wrapper

```python
async def llm_call(workspace_id: str, purpose: str, **kwargs):
    if not await check_budget(workspace_id):
        raise BudgetExceeded(workspace_id)

    start = time.time()
    response = await client.messages.create(**kwargs)
    duration = time.time() - start
    cost_micros = compute_cost(response.usage, kwargs['model'])

    await emit_cloudwatch_metrics({
        'llm.duration_seconds': duration,
        'llm.tokens_input': response.usage.input_tokens,
        'llm.tokens_output': response.usage.output_tokens,
        'llm.cost_usd_micros': cost_micros,
    }, dimensions={'workspace_id': workspace_id, 'model': kwargs['model'], 'purpose': purpose})

    await increment_workspace_spend(workspace_id, cost_micros)
    return response
```

### Model Routing

| Task | Model | Why |
|------|-------|-----|
| Daily proactive insights | Claude Sonnet 4.6 | Quality + caching |
| AI Chat | Claude Sonnet 4.6 | Quality over speed |
| Insight summarization (digest) | Claude Haiku 4.5 | Cheap rewording |
| Anomaly explanation | Claude Sonnet 4.6 | Reasoning required |
| Title generation | Claude Haiku 4.5 | Trivial |

Hard-coded routing in `pylibs/brain_intelligence/model_router.py`. Phase 5: dynamic routing based on workspace plan tier.

---

## 9. Observability

CloudWatch metric namespace `Brain/Intelligence`:

- `llm.calls_total{workspace_id, model, purpose}` — counter
- `llm.tokens_input_total{cache_hit}` — counter
- `llm.tokens_output_total` — counter
- `llm.cost_usd_micros_total{workspace_id}` — counter
- `llm.call_duration_seconds{model}` — histogram
- `llm.errors_total{error_type}` — counter
- `forecast.runs_total{workspace_id, model_id}` — counter
- `anomaly.detected_total{workspace_id, severity}` — counter
- `insight.generated_total{workspace_id, insight_type}` — counter

CloudWatch alarms:
- Workspace LLM spend >80% of monthly budget → ops alert
- `llm.errors_total` rate >1/min → P3
- A forecast MAPE >25% sustained 7 days → admin email
- Anthropic rate-limit error rate >0.1% → P2

---

## 10. Scaling at 100k req/min

Most intelligence-service work is **asynchronous** (scheduled jobs). User-facing surface (AI Chat) is the synchronous path.

### AI Chat Capacity

- Each chat message: ~3s avg (Claude latency)
- Streaming: holds connection open for full duration
- 100 RPS sustained chat = 300 concurrent streams = ~10 pods comfortable
- Anthropic rate limit (Tier 4): 4000 RPM = 67 RPS — this becomes the bottleneck, not us
- Phase 3: enterprise customers may need dedicated Anthropic capacity (Anthropic Bedrock with Provisioned Throughput on AWS)

### Forecast / Insight Jobs

- Nightly at 04:30 IST
- 1,000 workspaces × 30s/insight job = 30,000s = needs to complete in 90 min window
- 30,000s / 5400s = 6 parallel workers minimum; we run 10–15 for buffer

### Anomaly Detection

- Triggered per workspace per day; 5-15s per workspace
- Runs in parallel; consumer group scales naturally

---

## 11. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Prophet vs custom model? | E4 | Prophet for Phase 3. Custom only if accuracy plateaus. |
| LLM output validation? | E4 | Pydantic schema; retry once; fallback to generic insight. |
| Anthropic via API directly or via AWS Bedrock? | E1 + E4 | Direct API for Phase 1-3 (better latency, simpler). Switch to Bedrock when Provisioned Throughput economics improve at scale. |
| Open-source LLM for cost-sensitive tasks? | E4 | Phase 5+. Llama 3.x for cheap summarization. Not yet. |
| Embeddings provider? | E4 | Phase 3. Start with Sentence-Transformers (free, runs on workers). |
| Can AI take actions, not just suggest? | E1 | Opt-in "autopilot" Phase 5+. Whitelisted safe actions only. |
| Geo-holdout iROAS? | E4 | Phase 4 — sufficient spend volume per geography required. |
| Forecast for brand-new workspaces? | E4 | Cross-workspace baselines until 60d history. "Low confidence" flagged. |
