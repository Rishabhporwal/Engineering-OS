# TECH/12 — Cost-Routed Compute Paradigm

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E1 (architecture) + E4 (paradigm decisions per feature) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/05_intelligence_layer.md](05_intelligence_layer.md)

**Mandate:** every feature decision passes through a routing question before it is built. Most of what the industry calls "agentic AI" is actually SQL or ML wearing a costume. Brain refuses to pay LLM prices for problems statistics already solved 40 years ago.

This is enforced as a **build-pipeline gate**, not a code-review preference.

This principle is the structural reason Brain can bundle every channel (call + WhatsApp + email + SMS + ads) into one GMV % fee without margin collapse. A competitor running every decision through a frontier LLM cannot match Brain's per-brand cost economics and cannot price-match.

---

## 1. The Four Paradigms, Ranked by Cost

| # | Paradigm | When to Use | Cost Per Call | Examples in Brain |
|---|----------|-------------|---------------|------------------|
| **1** | **SQL** | Deterministic, threshold-based, aggregation. The answer exists in the data, you just need to query it. | ~0 (CPU + I/O) | Daily CM2 rollup; RFM scoring; threshold alerts; pincode-level aggregates; "did revenue cross goal today?" |
| **2** | **ML / Statistical** | Pattern recognition, prediction, similarity, anomaly detection over historical data. The math is well-known. | Training: one-time. Inference: <$0.001/call. | EWMA on CTR (creative fatigue); BG/NBD + Gamma-Gamma (LTV); Kaplan-Meier (cohort survival); XGBoost (RTO risk per pincode); pgvector cosine (Brand Fingerprint similarity); Prophet / isotonic regression (forecasting) |
| **3** | **Small LLM** | Bounded-domain natural-language understanding: classification, extraction, short summarisation, structured-output generation. | $0.001–$0.01/call (Claude Haiku, GPT-4o-mini equivalent) | Ticket classification (top-10 types); WhatsApp template personalisation; Morning Brief headline rewriting; call-script template selection |
| **4** | **Frontier LLM** | Multi-step synthesis, brand-voice generation, ambiguous reasoning, deep tool use. | $0.05–$0.50/call (Claude Sonnet) | Morning Brief synthesis (the actual writing); AI Chat tool-use orchestration; agent reasoning (AICMO recommendations) |

**The cost ratio is roughly 1 : 100 : 1,000 : 10,000.** A feature built on the wrong paradigm is not 10% more expensive — it is 1-2 orders of magnitude more expensive.

---

## 2. The Routing Decision Is a Required Gate

Every feature ticket entering the build pipeline must answer **four questions in order**, escalating only when the previous paradigm cannot solve the problem. Answers documented in the ticket. No feature ships without this audit trail.

### Question 1: Can SQL solve this?

- Task is deterministic, threshold-based, or aggregation?
- The answer exists in the data, you just need to query it?
- **If yes → paradigm 1.** Build as a CRON job, stored procedure, or scheduled materialisation. Cost approximates zero.

### Question 2: Can ML solve this?

- Task is pattern recognition, prediction, similarity, anomaly detection over historical data?
- The mathematical approach is well-known (regression, classification, clustering, time-series, survival analysis)?
- **If yes → paradigm 2.** Use the existing model library (Prophet, BG/NBD, XGBoost, pgvector, scikit-learn). Cost = one-time training + minimal inference.

### Question 3: Can a small LLM solve this?

- Task requires natural-language understanding on a bounded domain?
- Output is a classification, an extraction, or a short structured response?
- **If yes → paradigm 3.** Claude Haiku, GPT-4o-mini, or equivalent. ~10-50x ML cost but acceptable when language understanding is genuinely required.

### Question 4: Does this require a frontier LLM?

- Task involves multi-step synthesis, brand-voice generation, or ambiguous reasoning that smaller models fail at?
- **If yes → paradigm 4.** Reserved for highest-value, lowest-frequency operations.

### PR Template (Required)

Every PR introducing a new feature includes:

```markdown
## Cost Routing Audit

**Feature:** [name]
**Paradigm chosen:** [SQL / ML / Small LLM / Frontier LLM]
**Why this paradigm:**
- Question 1 (SQL): [Yes — task is X / No because Y]
- Question 2 (ML): [Yes / No because]
- Question 3 (Small LLM): [Yes / No because]
- Question 4 (Frontier LLM): [Yes / N/A]

**Per-call cost estimate:** [$X.XX]
**Per-brand monthly cost projection:** [$Y.YY]
**Fallback path if paradigm fails:** [degrade to paradigm N-1]
```

Build pipeline check: if a PR declares LLM but the reviewer judges SQL or ML would suffice, the PR is blocked. Documented decision required to escalate.

---

## 3. What "Agentic Commerce" Actually Means in Brain

A substantial portion of what the industry calls "agentic AI" is not AI at all. It is ML and pattern recognition with an LLM wrapper used only at the natural-language interface boundary. Brain enforces this distinction at the engineering layer.

| Industry framing | Brain implementation | Paradigm |
|------------------|---------------------|----------|
| "AI detects when an ad is fatiguing" | EWMA on CTR + threshold cross | SQL + ML — **not LLM** |
| "AI predicts which customer will repeat" | BG/NBD + Gamma-Gamma probabilistic model | ML — **not LLM** |
| "AI scores RTO risk" | XGBoost on historical features (pincode, courier, AOV, COD flag, time-of-day, customer history) | ML — **not LLM** |
| "AI finds similar historical conditions" | pgvector cosine similarity on Brand Fingerprint vector | ML — **not LLM** |
| "AI recommends budget reallocation" | Linear optimization over forecast vectors | ML — **not LLM** |
| "AI writes the Morning Brief" | Pulls the above ML outputs, synthesises in plain English | **Frontier LLM (Claude Sonnet)** — yes, this genuinely needs language |

**The result:** Brain executes most of its intelligence at SQL-and-ML cost economics, then uses LLMs only at the human-language interface boundary. This is the engineering invariant behind the pricing model.

### The Industry Mistake (Avoided)

Most "AI startup" architectures route every decision through GPT-4 or Claude Sonnet because LLM APIs are easy. The cost lands on the customer (per-seat $99 plans) or on the runway (negative gross margin). Brain refuses this trade.

---

## 4. Token Economics Enforcement — Three Layers

The cost-routing principle is enforced at three layers, **all hard-coded**:

### Layer 1 — Default Routing

- Every API endpoint and agent action declares its paradigm in the codebase
- Defaults to the cheapest paradigm that can solve the problem
- Upgrading the paradigm requires a documented justification in code comments + PR description
- Build pipeline check: PR blocked if reviewer judges a cheaper paradigm would suffice

**Implementation:**

```python
# Every endpoint/agent declares its paradigm explicitly

@paradigm("sql")
async def compute_daily_revenue(brand_id, date):
    """Paradigm: SQL. Reason: aggregation. Cost: ~$0."""
    return await db.fetchval("""
        SELECT SUM(cm2_minor) FROM orders
        WHERE brand_id = $1 AND order_date = $2
    """, brand_id, date)

@paradigm("ml", model="bg_nbd_gg_v1")
async def predict_ltv_30d(brand_id, customer_id):
    """Paradigm: ML (BG/NBD + Gamma-Gamma). Reason: probabilistic LTV. Cost: <$0.001."""
    return ltv_model.predict(brand_id, customer_id, horizon=30)

@paradigm("small_llm", model="claude-haiku")
async def classify_ticket(ticket_text):
    """Paradigm: Small LLM. Reason: NL classification on bounded label set. Cost: ~$0.005."""
    return await haiku_client.classify(ticket_text, labels=TOP_10_TICKET_TYPES)

@paradigm("frontier_llm", model="claude-sonnet")
async def synthesize_morning_brief(brand_id, signals):
    """Paradigm: Frontier LLM. Reason: multi-signal synthesis + brand voice. Cost: ~$0.10/brief."""
    return await sonnet_client.synthesize(brand_id, signals, prompt=MORNING_BRIEF_PROMPT)
```

The `@paradigm` decorator is a registry hook. Cost-routing dashboard reads it. Build pipeline parses it for the audit gate.

### Layer 2 — Per-Feature Token Budgets

- Every LLM-using feature has a token budget per call
- Soft warning at 80% of budget; hard fail at 100%
- Failed calls fall back to degraded SQL or ML path where possible; surface graceful error where not
- Token budget overruns log to cost-discipline dashboard; repeated overruns trigger prompt audit

**Implementation:**

```python
@paradigm("frontier_llm", model="claude-sonnet", token_budget=2000)
async def synthesize_morning_brief(brand_id, signals):
    response = await sonnet_client.synthesize(
        ...,
        max_tokens=2000,
        on_budget_warning=lambda: log_event("token_budget_80", brand_id),
        on_budget_exceeded=lambda: fallback_to_template_brief(brand_id, signals),
    )
    return response
```

When a feature exceeds budget repeatedly:

1. **Cost-discipline dashboard** flags the feature
2. **Prompt audit** by E4: is the system prompt too verbose? Can context be cached? Can the task be split?
3. Either prompt is optimised, budget is raised with explicit approval, or paradigm is downgraded

### Layer 3 — Per-Brand Monthly Caps

- Every brand has a monthly LLM cap in INR (set per pricing tier)
- Soft throttle at 70% of cap (lower-priority LLM features pause)
- Hard throttle at 100% (only critical-path LLM features continue: Morning Brief, NL query, ticket resolution)
- Owner notified at 70% with clear breakdown of where tokens went + recommended actions

**Cap structure:**

| Tier | Monthly LLM cap (INR) | What happens above cap |
|------|----------------------|------------------------|
| Launch (~1.0% GMV) | ₹5,000 | Soft throttle 70%; hard throttle 100% on non-critical |
| Growth (~0.75% GMV) | ₹10,000 | Same |
| Scale (~0.5% GMV) | ₹15,000 | Same |
| Enterprise | Negotiated (typically ₹50K+) | Same logic; higher absolute number |

**Below cap:** all features run.
**70-100% range:** non-critical LLM features (per-message WhatsApp personalisation, weekly creative-brief generation) pause. SQL + ML paths continue normally.
**Above cap:** only critical-path LLM continues — Morning Brief, NL query, ticket auto-resolution. System never breaks; it gets quieter.

**Implementation:**

```python
# pylibs/brain_cost_router/middleware.py
async def llm_call_with_cap(brand_id: UUID, feature: str, priority: str, **kwargs):
    spent = await get_brand_monthly_spend(brand_id)
    cap = await get_brand_monthly_cap(brand_id)

    if spent >= cap:
        if priority != "critical_path":
            raise BudgetThrottled(brand_id, feature)
        # critical-path continues even above cap; logged for ops

    if spent >= 0.7 * cap and priority not in ("critical_path", "high"):
        raise BudgetSoftThrottled(brand_id, feature)

    response = await llm_client.call(**kwargs)
    await increment_brand_spend(brand_id, response.cost_micros_inr)

    if spent + response.cost_micros_inr >= 0.7 * cap and (spent < 0.7 * cap):
        await notify_owner_cap_warning(brand_id, threshold=0.7)

    return response
```

---

## 5. Cost-Discipline Dashboard

A first-class internal surface for the Brain team. Lives in admin UI.

| View | Purpose |
|------|---------|
| **Per-brand spend timeline** | Daily LLM + telephony + messaging cost per brand, with cap warning threshold overlay |
| **Per-feature spend ranking** | Which features cost the most? Where is the next optimisation? |
| **Paradigm distribution** | % of total calls in paradigm 1 / 2 / 3 / 4. Target: SQL > 80% by call count |
| **Budget breach log** | Every Layer-2 (per-feature) and Layer-3 (per-brand) breach |
| **Prompt audit queue** | Features flagged for prompt review |
| **Cost per recovered rupee (Lifecycle)** | LLM + telephony cost ÷ recovered revenue attributed. North-star unit economic. |

**Target:** average paradigm distribution across all brand activity: 85% SQL, 12% ML, 2.5% Small LLM, 0.5% Frontier LLM. If Frontier LLM creeps above 1% of total calls, that is a signal the routing gate is being bypassed.

---

## 6. Quarterly Streamlining Audit

The cost-routing principle is mirrored by the **Streamlining Audit** ([TECH/11 §1](11_lifecycle_revenue_layer.md)). Every quarter:

- Engineering team reviews the codebase for **anti-pattern drift**
- Any duplication of cross-cutting concerns is flagged and scheduled for refactor
- Any paradigm-bypass (Frontier LLM used where ML would have worked) is documented
- Refactoring time allocated **explicitly** in each quarter's plan. Not optional, not deferred.

The audit produces a quarterly memo: "Where Brain drifted, where we caught it, what's queued for next quarter."

---

## 7. The Engineering Invariant (One-Liner)

> Brain runs most decisions at paradigm-1 + paradigm-2 cost (SQL + ML). LLMs enter only at the human-language interface. The GMV % pricing model is structurally defensible because of this.

If a future engineer reads this doc and considers ignoring it: the pricing model dies the moment paradigm distribution flips. Don't.

---

## 8. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | What's the soft-throttle vs hard-throttle priority list per tier? | E1 + E4 | Drafted above; finalise after Phase 1 telemetry |
| 2 | Should the cost-discipline dashboard be brand-visible (transparency) or internal-only? | Founder | Default internal; brand-visible for Enterprise tier |
| 3 | How is the per-feature token budget set initially? | E4 | Empirical — 2 weeks of pre-launch traffic from the pilot brand sets baselines; reviewed monthly |
| 4 | Paradigm-1 SLO: what's "free" if SQL queries hit a slow read replica? | E1 | Treat as paradigm-1 still; flag for index optimisation, not paradigm upgrade |
