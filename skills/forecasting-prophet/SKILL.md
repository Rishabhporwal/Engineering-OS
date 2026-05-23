---
name: forecasting-prophet
description: Brain's Plan Module forecasting — Prophet for trend + seasonality with festival regressors; isotonic regression for spend-aMER response curves; BG/NBD + Gamma-Gamma for LTV; Kaplan-Meier for cohort survival; ARIMA for cashflow. Auto-load whenever building forecasts, anomaly detection over time series, the Plan Module (Phase 3 W25-32), or any AICOO-Inventory / AICFO-Cashflow / AICMO-Festival agent work.
---

# Forecasting — Prophet + Isotonic + Probabilistic Models

The Plan Module (canon/TECH/05_intelligence_layer.md §2) is Brain's forecasting engine: **aMER response curve (isotonic) + returning-revenue model × festival multiplier**. Phase 1: simple aMER bucketing (paradigm 1 SQL + percentile). **Phase 3 (W25-32): Prophet with festival regressors** (paradigm 2 ML). Target **15% MAPE @30d** for active workspaces by Phase 3. All forecasting is paradigm 1 or 2 — **never LLM.**

> **Library maintenance note (May 2026):** **Prophet itself is now lightly maintained** — it still works and stays Brain's default, but if accuracy plateaus, **NeuralProphet** (neural, regressor-friendly) or **StatsForecast** (fast classical, Nixtla) are the alternatives. For LTV, **`lifetimes` is archived / maintenance-mode — migrate to PyMC-Marketing** (the official successor; same BG/NBD + Gamma-Gamma, actively maintained, Bayesian credible intervals), or `btyd` as a lighter alternative. See the LTV section below.

**Canonical doc:** `canon/TECH/05_intelligence_layer.md §2` (+ `canon/technical-requirements.md` §forecasting). This skill is operational.

## Phase 1 forecast (W7+ wedge) — paradigm 1, SQL + percentile

```sql
-- 90-day rolling aMER at P25 / P50 / P75 spend percentiles + seasonality multiplier
WITH historical AS (
  SELECT
    workspace_id,
    date,
    ad_spend_minor,
    amer,
    extractFestivalLift(date) AS lift_factor  -- RegionAdapter
  FROM daily_metrics_local
  WHERE workspace_id = $1
    AND date >= today() - INTERVAL 90 DAY
)
SELECT
  quantile(0.25)(amer) AS amer_p25,
  quantile(0.50)(amer) AS amer_p50,
  quantile(0.75)(amer) AS amer_p75,
  avg(lift_factor)     AS expected_lift
FROM historical
WHERE ad_spend_minor BETWEEN $2 * 0.8 AND $2 * 1.2;  -- spend bucket
```

Confidence intervals = P25-P75 band. No model fitting.

## Phase 3 forecast (W25-32) — Prophet with festival regressors

```python
from prophet import Prophet

@paradigm("ml", model="prophet_v1")
async def forecast_revenue(workspace_id, horizon_days=30):
    df = await fetch_daily_revenue(workspace_id, days=540)  # 18 months
    df = df.rename(columns={"date": "ds", "revenue_net_minor": "y"})

    # Festival regressors from RegionAdapter
    festivals_df = await fetch_festivals_ist(start=df.ds.min(), end=df.ds.max() + timedelta(days=horizon_days))

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",   # DTC sales scale with festival
    )
    m.add_country_holidays(country_name="IN")
    m.add_regressor("is_diwali")
    m.add_regressor("is_navratri")
    m.add_regressor("is_holi")
    m.add_regressor("is_eofy")

    m.fit(df.merge(festivals_df, on="ds"))

    future = m.make_future_dataframe(periods=horizon_days)
    future = future.merge(festivals_df, on="ds", how="left").fillna(0)
    forecast = m.predict(future)

    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(horizon_days)
```

`changepoint_prior_scale=0.05` — DTC trends shift quickly; don't over-smooth.
`seasonality_mode="multiplicative"` — festival lift is multiplicative, not additive.

## Spend-aMER response curve — isotonic regression

```python
from sklearn.isotonic import IsotonicRegression

@paradigm("ml", model="isotonic_aMER_v1")
async def fit_amer_response_curve(workspace_id, channel="meta_acquisition"):
    df = await fetch_spend_amer_history(workspace_id, channel, days=180)
    iso = IsotonicRegression(out_of_bounds="clip", increasing=False)  # diminishing returns
    iso.fit(df.spend_minor, df.amer)
    return iso

# At inference:
amer_at_spend = iso.predict([proposed_spend_minor])
```

**Why isotonic:** spend → aMER has diminishing returns (monotonic decreasing); we don't want overfitting through polynomial regression. Isotonic guarantees the curve doesn't turn upward.

## LTV — BG/NBD + Gamma-Gamma via PyMC-Marketing (paradigm 2)

**Monetary value is `CM2/order` (paisa), NOT gross order value** — Brain's LTV is contribution-margin LTV (canon TECH/03, TECH/05). Feeding gross AOV inflates LTV:CAC and breaks the spend decision.

> **Use `pymc-marketing`, not `lifetimes`.** `lifetimes` is archived / maintenance-mode; **PyMC-Marketing is the official successor** — same BG/NBD + Gamma-Gamma models, actively maintained, and it returns Bayesian **credible intervals** (better than `lifetimes`' point estimates for a spend decision). `btyd` is a lighter alternative if a full PyMC dependency is too heavy. The model choice (BG/NBD + Gamma-Gamma) and the CM2/order monetary input are unchanged.

```python
from pymc_marketing.clv import BetaGeoModel, GammaGammaModel

@paradigm("ml", model="bg_nbd_gg_v1")
async def predict_ltv_30d(workspace_id, customer_id):
    # BG/NBD: probability customer is alive + frequency
    # Gamma-Gamma: expected monetary value given alive
    # rfm_df.monetary_value = CM2 per order (minor units), not gross AOV

    bg = BetaGeoModel(data=rfm_df)        # columns: customer_id, frequency, recency, T
    bg.fit()
    gg = GammaGammaModel(data=rfm_df)      # columns: customer_id, frequency, monetary_value (CM2/order)
    gg.fit()

    return gg.expected_customer_lifetime_value(
        transaction_model=bg,
        customer_id=rfm_df["customer_id"],
        frequency=rfm_df["frequency"],
        recency=rfm_df["recency"],
        T=rfm_df["T"],
        monetary_value=rfm_df["monetary_value"],  # CM2/order
        time=1,                                    # 1 month horizon
        discount_rate=0.0,
    )  # returns a posterior → take the mean + a credible interval for the band
```

Per-brand model. **Requires min 6 months history + ≥500 repeat customers; train monthly; flag if MAPE > 40%** (canon technical-requirements §lifecycle). Below the data floor, fall back and label the estimate in the UI.

## Cohort survival — Kaplan-Meier

```python
from lifelines import KaplanMeierFitter

@paradigm("ml", model="km_cohort_v1")
async def cohort_survival(workspace_id, cohort_month):
    df = await fetch_cohort_orders(workspace_id, cohort_month)
    kmf = KaplanMeierFitter()
    kmf.fit(df.days_to_churn, df.event_observed, label=str(cohort_month))
    return kmf.survival_function_
```

## Cashflow — ARIMA (AICFO-Cashflow)

```python
from statsmodels.tsa.statespace.sarimax import SARIMAX

@paradigm("ml", model="sarima_cashflow_v1")
async def forecast_cashflow_30d(workspace_id):
    df = await fetch_daily_cashflow(workspace_id, days=180)
    # Settlement lag is per-payment-provider (modelled separately)
    model = SARIMAX(df.cashflow_minor, order=(1,1,1), seasonal_order=(0,1,1,7))
    res = model.fit(disp=False)
    return res.get_forecast(steps=30).summary_frame()
```

## Accuracy tracking — `ai.forecast_accuracy`

```sql
CREATE TABLE ai.forecast_accuracy (
  workspace_id        UUID NOT NULL,
  agent_name          TEXT NOT NULL,            -- 'aicmo-festival', 'aicfo-cashflow', etc.
  forecast_date       DATE NOT NULL,            -- when forecast was made
  target_date         DATE NOT NULL,            -- date being forecast
  metric_kind         TEXT NOT NULL,            -- 'money_minor' | 'ratio' (disambiguates the value columns)
  forecasted_minor    BIGINT,                   -- money forecasts in minor units (NEVER NUMERIC/float for money)
  actual_minor        BIGINT,
  forecasted_ratio    DOUBLE PRECISION,         -- ratio forecasts (aMER, MER) only
  actual_ratio        DOUBLE PRECISION,
  abs_pct_error       DOUBLE PRECISION,         -- |actual - forecast| / actual
  model_version       TEXT NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, agent_name, forecast_date, target_date)
);
```

**Phase 3 exit criterion: 30-day MAPE < 15% across active workspaces** (canon TECH/05 §2). A workspace whose 30-day MAPE stays **> 25% for 7 days triggers an admin investigation alert**; LTV models that drift past **MAPE > 40%** are flagged and fall back.

## Anomaly detection — z-score with festival baseline

```python
@paradigm("ml", model="zscore_v1")
async def detect_anomaly(workspace_id, metric, date):
    history = await fetch_daily_metric(workspace_id, metric, days=90)
    festival_adjusted = await apply_festival_baseline(history)  # RegionAdapter
    z = compute_zscore(festival_adjusted, today=date)
    if abs(z) > 3.0:
        return Anomaly(severity="high", z=z, festival_baseline=festival_adjusted[-1])
    return None
```

Festival baseline matters: Diwali revenue isn't an anomaly; it's an expected lift.

## Switching from Phase 1 (simple) → Phase 3 (Prophet)

```python
def pick_forecast_model(workspace_id):
    history_days = get_workspace_data_age(workspace_id)
    if history_days < 540:                       # < 18 months
        return SimpleForecast(workspace_id)      # SQL + percentile
    return ProphetForecast(workspace_id)         # full model
```

Don't run Prophet on < 18 months — overfits seasonal patterns.

## Common failure modes

- **Forgetting festival regressors** — Diwali revenue looks like a 5σ anomaly. Always add festival regressors.
- **`changepoint_prior_scale` too smooth** — Prophet misses recent trend shift. Default 0.05 works for DTC.
- **`seasonality_mode="additive"`** — wrong for DTC where festival lift is multiplicative. Use multiplicative.
- **Refitting Prophet per-request** — slow. Cache fitted model 24h; refit nightly.
- **Reporting point estimate, not confidence band** — operators rely on the band for spend decisions. Always return `yhat_lower / yhat / yhat_upper`.
- **Cross-brand pattern matching without consent** — privacy violation. Only use `cross_brand_opt_in = TRUE` brand fingerprints when borrowing patterns for sparse-history workspaces.

## References

- `canon/TECH/05_intelligence_layer.md` §2 — Plan Module spec (isotonic aMER + returning-revenue × festival multiplier, MAPE targets)
- `canon/TECH/14_agent_roster.md` — AICMO-Festival + AICOO-Inventory + AICFO-Cashflow (agents that use these models)
- `canon/TECH/04_regional_adapters.md` — festival calendar + learned-lift source (RegionAdapter)
- `skills/cost-routing-paradigms/SKILL.md` — forecasting is paradigm 2; never paradigm 4
- `skills/agentic-design/SKILL.md` — wiring forecasts into agent daily ticks
- `skills/python-services/SKILL.md` — Prophet / sklearn / statsmodels / lifelines patterns
