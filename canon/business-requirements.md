# Brain Business Requirements

> **Version:** Standalone v1.1  
> **Updated:** 2026-05-23  
> **Audience:** AI builder agents, product builders, business operators, implementation reviewers, QA agents, sales-enablement agents, and onboarding agents  
> **Product:** Brain  
> **Category:** AI-native commerce operating system for DTC brands in India, UAE, and GCC  
> **Document status:** Source-of-truth business requirements

---

## 0. Prime Directive

Brain is the AI-native commerce operating system for DTC brands that want one place to read, decide, and act on revenue and profit.

Brain must never be treated as a passive analytics dashboard. It must become the operator's high-frequency commerce surface: the place a founder, growth lead, operator, finance lead, retention lead, or support head opens repeatedly because it shows live revenue movement, margin quality, leaks, recovery opportunities, customer risk, and executable next actions.

The product promise is not "better reporting." The promise is:

> Brain helps DTC brands grow realized revenue, recover lost revenue, protect contribution margin, and compound decision quality across marketing, lifecycle, support, logistics, inventory, and finance.

Every builder agent working on Brain must optimize for five non-negotiable outcomes:

1. **Revenue booked:** orders, repeat purchases, recovered carts, winbacks, referrals, upsells, cross-sells, prepaid conversions, resolved support-led saves.
2. **Profit protected:** CM2, CM3, RTO cost, COD leakage, refund leakage, wasted ad spend, low-quality discounting, overstock, stockout loss, courier leakage.
3. **Decision quality improved:** recommendations become more accurate because Brain logs conditions, actions, approvals, rejections, reversals, and outcomes.
4. **Operator time compressed:** the operator gets the same or better decision in minutes instead of checking five to ten tools manually.
5. **Safe execution:** Brain can recommend, queue, execute, reverse, and audit actions with guardrails.

If a feature cannot be tied to revenue, profit, risk reduction, operator time saved, compliance, or decision memory, it should not ship.

---

## 1. Product Boundary and Naming Rules

### 1.1 Product Name

- The product name is **Brain**.
- All product copy, prompts, schemas, seed data, route names, documents, demo examples, and internal agent instructions must use Brain-only language.
- Do not frame Brain as a clone, replica, version, layer, wrapper, or comparison to another product.
- Provider names are allowed only when describing real integrations Brain connects to, such as Shopify, Meta Ads, Google Ads, WhatsApp Business, Razorpay, Shiprocket, Unicommerce, Salla, Zid, Noon, Amazon, Flipkart, Klaviyo, Gupshup, Interakt, Exotel, Plivo, Zendesk, Freshdesk, or similar execution/data rails.

### 1.2 What Brain Is

Brain is the operating layer above a DTC brand's fragmented commerce stack. It ingests the brand's data, computes honest revenue and margin metrics, detects conditions, recommends actions, executes approved workflows, and tracks outcomes.

Brain combines these functions in one system:

| Function | Brain requirement |
|---|---|
| Analytics | Honest revenue, margin, acquisition, lifecycle, product, logistics, support, and finance metrics. |
| Intelligence | Diagnostic, predictive, and prescriptive reasoning over brand-specific data. |
| Memory | Decision Log, Brand Fingerprint, customer segment memory, creative memory, condition-outcome memory. |
| Execution | Lifecycle campaigns, WhatsApp journeys, ad actions, ticket resolution, refund/replacement flows, courier changes, inventory alerts, audience pushes. |
| Governance | Roles, approvals, guardrails, caps, audit trails, compliance checks, kill switches. |

### 1.3 What Brain Is Not

Brain is not:

- A passive dashboard that only shows historical charts.
- A chatbot with data access.
- A helpdesk wrapper.
- A channel-specific WhatsApp sender.
- A generic CRM.
- A per-seat SaaS product.
- A manufacturer ERP.
- A wholesale/B2B order management system.
- A media agency.
- A tool that optimizes for platform ROAS without contribution-margin context.

### 1.4 The Revenue and Profit Centre Standard

Brain should earn its place in the brand's P&L by producing measurable value. Every module must answer at least one of these questions:

- What revenue did Brain generate, recover, protect, or prevent from being lost?
- What happened to CM1, CM2, CM3, cash conversion, CAC, MER, aMER, RTO, COD realization, refunds, support cost, inventory capital, or settlement timing?
- What should the operator do next?
- Can Brain safely execute the next action?
- What did Brain learn after 7 days and 30 days?

Brain's internal value ledger must distinguish:

1. **Placed revenue:** order placed because of a Brain-driven action.
2. **Realized revenue:** order delivered/paid/settled after cancellations, RTO, refund, and payment failure.
3. **Recovered CM2:** realized revenue minus product, fulfillment, payment, discount, COD, RTO, return, and marketing costs.
4. **Protected CM2:** margin preserved by avoiding a bad action, pausing waste, preventing RTO, reducing refund leakage, or retaining a customer.
5. **Operator time saved:** hours not spent manually checking tools, reconciling sheets, answering repeated tickets, or building audiences.

---

## 2. The Operator Problem Brain Solves

### 2.1 The High-Frequency Commerce Loop

DTC operators do not check tools because they love dashboards. They check because revenue is moving and the movement creates urgency.

A founder or operator typically rotates through:

- Store orders to see sales momentum.
- Ad accounts to see spend, ROAS, CAC, CPC, CPM, CTR, and conversion movement.
- Payment dashboards to understand settlement and prepaid/COD mix.
- Logistics dashboards to catch stuck shipments, NDR, RTO, courier failures, and delivery delays.
- WhatsApp or support inboxes to see angry customers, abandoned carts, refunds, and sales opportunities.
- Inventory sheets to avoid stockouts or dead stock.
- Finance sheets to reconcile whether the business is actually making money.

This creates a dopamine loop: refresh, interpret, react, refresh again. The loop is addictive because revenue feedback is immediate. It is also fragile because each tool shows only one slice.

Brain must consolidate this loop into one profit-quality operating surface.

### 2.2 The Core Pain

The operator's real question is rarely "what was ROAS yesterday?" The real question is:

> "Are we making high-quality money today, and what should I do before the day gets away from me?"

Current tool fragmentation causes these failures:

| Failure | Business consequence |
|---|---|
| Platform ROAS looks good but COD/RTO quality is poor | Brand scales bad revenue and bleeds cash later. |
| Revenue rises but CM2 falls | Founder celebrates growth while profit quality collapses. |
| Support tickets are handled as cost | Revenue saves, repeat purchases, and refund prevention are not captured. |
| WhatsApp campaigns are sent as discount blasts | Retention becomes margin-destructive. |
| Courier and pincode failures are seen too late | RTO loss compounds before anyone reacts. |
| Ad changes are not logged | No one knows which human decision caused which outcome. |
| AI recommendations are not outcome-tracked | Intelligence does not compound. |
| Teams work in separate tools | Marketing, support, logistics, and finance make conflicting decisions. |

### 2.3 The Brain Replacement Loop

Brain's daily operating loop must be:

1. **Sense:** ingest fresh commerce, ads, logistics, support, payment, and lifecycle data.
2. **Normalize:** convert fragmented source data into one canonical profit model.
3. **Detect:** find meaningful movement in revenue, margin, customers, support, logistics, inventory, and cash.
4. **Decide:** rank the top actions by expected CM2 impact, urgency, confidence, and reversibility.
5. **Act:** recommend, queue, or execute with guardrails.
6. **Log:** write the condition, recommendation, approval/rejection/edit, execution, reversal, and outcome into Decision Log.
7. **Learn:** update Brand Fingerprint and future recommendation quality.

Brain must be designed so an operator feels less need to refresh disconnected tools because Brain already shows what changed, why it matters, and what to do.

---

## 3. Target Customers and Use Cases

### 3.1 Primary ICP

Brain is built for DTC brands in India, UAE, and GCC that already have real monthly commerce volume, margin pressure, and multi-tool complexity.

Minimum practical ICP:

- **Monthly GMV:** ₹50L+ or local-currency equivalent.
- **Commerce stack:** Shopify, WooCommerce, Salla, Zid, marketplace, or custom storefront.
- **Paid media:** Meta and/or Google active.
- **Fulfillment complexity:** shipping, returns, RTO, NDR, delivery delays, or multiple courier/logistics providers.
- **Customer communication:** WhatsApp, email, SMS, Instagram DM, support inbox, or calls.
- **Business pain:** founder/operator checks numbers daily but lacks one margin-correct decision surface.

The **₹50L/month GMV floor is a hard qualification line.** Brands below ~₹50L/month equivalent are not the initial target because the data volume, willingness to pay, and operational complexity usually do not justify the required onboarding and support. Brands in the ₹25L–₹50L band are case-by-case exceptions, not the default ICP.

### 3.2 Customer Tiers

#### Tier 1: Operator-Led DTC Brand

| Dimension | Requirement |
|---|---|
| GMV band | ₹50L to ₹3Cr/month or equivalent. |
| Team | Founder plus 1-5 operators/marketers/support staff. |
| Stack | Storefront, Meta, Google, payments, logistics, WhatsApp, support inbox. |
| Main question | "Are we profitable, and what should I fix today?" |
| Brain value | CM waterfall, MER/aMER, RTO/COD analytics, Morning Brief, top actions, WhatsApp recovery, support-ticket saves. |
| Buying trigger | Founder feels tool sprawl and cannot trust ROAS or manual sheets. |

#### Tier 2: Scaling DTC Brand

| Dimension | Requirement |
|---|---|
| GMV band | ₹3Cr to ₹50Cr/month or equivalent. |
| Team | Growth lead, media buyers, retention lead, support head, operations/logistics lead, finance owner. |
| Stack | Multi-channel ads, retention tools, OMS, support desk, logistics providers, marketplace channels. |
| Main question | "Which actions grow revenue without breaking CM2 or cash?" |
| Brain value | cohort LTV, first-product repeat cascade, creative intelligence, lifecycle automation, AI ticket management, budget optimizer, inventory and courier actions. |
| Buying trigger | Team works harder but decisions do not compound across functions. |

#### Tier 3: Enterprise or Multi-Brand Operator

| Dimension | Requirement |
|---|---|
| GMV band | ₹50Cr+/month, multiple brands, multiple regions, or complex enterprise requirements. |
| Team | CMO, CFO, COO, brand teams, regional teams, analytics, agency partners. |
| Stack | Multiple storefronts, POS/ERP/OMS, warehouses, marketplaces, support desks, ad accounts, BI warehouse. |
| Main question | "How do we manage portfolio profit, cash, inventory, customer quality, and execution accountability?" |
| Brain value | portfolio rollups, region adapters, enterprise data controls, custom benchmarks, private deployment options, approval matrices, advanced auto-execute. |
| Buying trigger | Existing BI shows numbers but not cross-functional action accountability. |

### 3.3 Geographic Scope

Brain is **multi-region by architecture from day one** (the region-adapter pattern) and **India-first by go-to-market sequencing.** India, UAE, and GCC are all first-class *adapters*; India is the launch market, and UAE/GCC are activated for live customers in a later phase (see §21 Roadmap). This keeps the global ambition without forking product logic and without diluting the India wedge.

| Region | Brain must support |
|---|---|
| India | INR, GST 2.0 slabs (0/5/18/40) with GST-inclusive pricing handled per-SKU slab, COD/prepaid economics, RTO, NDR, pincode intelligence, Indian festival calendar, channel-specific messaging/voice compliance (DLT for SMS/voice, NCPR/DND, 9am–9pm calling window; Meta opt-in for WhatsApp), DPDP Act data-protection compliance, Shiprocket and Indian payment/logistics stack. |
| UAE | AED, VAT 5%, WhatsApp-first commerce, COD where relevant, marketplace and delivery-app concentration, retail/offline influence, Tabby/Tamara/BNPL where applicable, Emirates-level location logic. |
| KSA/GCC | SAR/AED/local currencies, country-specific VAT (KSA 15%, UAE 5%, Bahrain 10%, Oman 5%; Qatar/Kuwait none yet), Ramadan/Eid seasonality, Arabic/English templates, Salla/Zid/Noon/Namshi integrations, regional logistics providers, higher marketplace concentration, UAE/KSA PDPL data-protection compliance. |
| Future regions | Implemented through region adapters, not forks. |

### 3.4 Account Structures

Brain must support four account structures:

#### Model A: Single Brand

One organization owns one brand. Founder is Owner. Most common at launch.

#### Model B: Multi-Brand Group

One organization owns multiple brands. Each brand has isolated data, integrations, users, costs, goals, Decision Log, and billing basis. Cross-brand views require explicit permission.

#### Model C: Agency-Managed Brand

Agency users can access client brands only when invited. The brand retains Owner control. Agency actions are fully logged. Agencies cannot see other agencies' clients or raw data from other client brands.

#### Model D: Enterprise Overlay

Available to any sufficiently complex customer. Includes advanced security reviews, custom SLA, private data warehouse options, custom integrations, data residency controls, approval matrices, custom model governance, and dedicated support.

---

## 4. Personas and Roles

### 4.1 Personas

| Persona | Daily concern | Brain surface |
|---|---|---|
| Founder / Owner | Is revenue high quality? Is cash safe? What should I approve today? | Mobile Morning Brief, Home, Decision Log, Weekly Review, Month-End Compound Report. |
| Operator / COO | What needs action now across ads, logistics, support, inventory, and retention? | Command Center, queues, alerts, auto-execute review, integration health. |
| Growth Lead / Media Buyer | Which spend, creative, channel, and audience decisions improve CM2? | Acquisition, creative intelligence, budget optimizer, campaign classification, ad actions. |
| Retention / CRM Lead | Which customers should be contacted, through what channel, with what offer? | RFM, lifecycle campaigns, WhatsApp journeys, winback, replenishment, VIP retention. |
| Support Head | Which tickets can be resolved, saved, escalated, or turned into revenue? | AI Inbox, ticket queue, refund/replacement guardrails, support-to-revenue ledger. |
| Finance / CFO | Are sales translating into CM2, CM3, settlement, and cash? | P&L, Plan, cash timing, refunds, payment fees, margin waterfall, decision ROI. |
| Operations / Logistics Lead | Where are shipments, RTO, courier, NDR, inventory, and warehouse risks? | Logistics, pincode heatmap, inventory, courier actions, NDR queue. |
| Agency User | Which client needs intervention first? | Multi-brand cockpit, scoped views, action queues, client reporting. |
| Investor / Advisor | How is the brand performing at a high level? | Read-only selected reports, no raw PII, no execution rights. |

### 4.2 Roles

| Role | Rights |
|---|---|
| Owner | Full control. Billing, integrations, users, cost settings, approvals, auto-execute settings, exports, deletion. |
| Operator | Operational read/write. Can approve most recommendations, execute campaigns, manage queues, edit costs if granted. Cannot change billing or delete brand. |
| Analyst | Read-only analytics plus comments. Cannot approve, execute, or change settings. |
| Agency | Scoped per-brand access. Rights configured by Owner. All actions tagged as agency actions. |
| Read-only | Limited reports only. No raw PII. No execution. |

### 4.3 Approval Matrix

Brain must support approval levels by action type:

| Action class | Default approver |
|---|---|
| View analytics | Any role with report access. |
| Add comment/context | Analyst+. |
| Create draft campaign | Operator+. |
| Send lifecycle campaign | Operator+, unless discount or large audience requires Owner. |
| Pause ad or reduce budget | Operator+, can auto-execute if enabled. |
| Increase ad budget | Owner by default; Operator if configured with caps. |
| Issue refund | Owner by default; Operator within cap. |
| Replace item | Operator within policy; Owner above cap. |
| Change courier rule | Operator+, auto-execute if confidence/cap allows. |
| Create purchase order | Owner unless under pre-approved reorder policy. |
| Enable auto-execute | Owner only. |
| Change billing or delete brand | Owner only. |

---

## 5. Core Product Pillars

### 5.1 Pillar 1: Honest Profit Analytics

Brain must calculate commerce performance from the brand's true economics, not just source-platform numbers.

Core outputs:

- Net sales with tax handling.
- COGS per SKU and blended by product/order/customer/cohort/channel.
- Variable costs including payment fees, packaging, shipping, COD handling, returns, refunds, support concessions.
- Ad spend by channel and campaign classification.
- CM1, CM2, CM3, operating profit.
- MER, aMER, CAC, CAC payback, LTV:CAC.
- RTO-adjusted CM2 and delivered revenue.
- Cash timing and settlement-aware views.

The default product hierarchy must move operators away from vanity ROAS and toward contribution margin.

### 5.2 Pillar 2: Regional Commerce Intelligence

Brain must model local operating reality. India and GCC are not plug-and-play versions of US ecommerce.

India-native intelligence:

- COD vs prepaid margin difference.
- RTO by pincode, city, courier, channel, product, payment method, offer, and ad campaign.
- NDR workflow as leading indicator of RTO.
- GST-inclusive price correction.
- Pincode/city tier scoring.
- Indian festival and sale seasonality.
- WhatsApp-first retention with consent and template rules.
- Settlement timing and cash-conversion impact.

UAE/GCC intelligence:

- VAT-aware revenue.
- WhatsApp-first support and selling.
- Smaller audience pools and faster creative fatigue.
- Marketplace/delivery platform contribution-margin leakage.
- Retail/offline influence where relevant.
- Ramadan/Eid and local sale calendar.
- BNPL/payment-fee effects.
- Cross-border shipping, duties, and return-cost complexity.

### 5.3 Pillar 3: Decision Memory

Brain must remember not only what happened, but what was recommended, what was done, who did it, why, and what happened after.

The Decision Log is the core compounding asset. It must record:

- Condition snapshot at the time of recommendation.
- Recommendation text and structured action parameters.
- Expected impact, confidence, risk, reversibility, and time horizon.
- User response: approved, rejected, edited, deferred, ignored.
- Execution details: channel, provider, payload, timestamp, actor.
- Reversal details if any.
- 7-day outcome and 30-day outcome.
- Revenue, CM2, time saved, support outcome, refund avoided, or cost reduced.
- Learnings used to update future recommendations.

No official Brain action exists unless it is logged.

### 5.4 Pillar 4: Lifecycle as a Revenue Engine

Brain must turn lifecycle from manual campaigns into margin-aware revenue execution.

Required lifecycle workflows:

- Abandoned cart recovery.
- Browse abandonment where tracking consent exists.
- COD confirmation and prepaid conversion.
- Post-delivery education and review request.
- Replenishment/reorder journeys.
- Winback for dormant customers.
- VIP retention.
- New customer second-order conversion.
- Refund-save and exchange-first flows.
- WhatsApp marketing broadcasts to RFM segments.
- Referral/advocate activation.

Lifecycle should always be margin-gated. Brain must avoid discounting customers where the expected CM2 is negative after message cost, offer cost, and return/RTO risk.

### 5.5 Pillar 5: AI Ticket Management as Revenue Protection

Support is not only a cost centre. Support affects refund rate, repeat rate, COD realization, review quality, delivery recovery, exchange conversion, and customer trust.

Brain must treat support tickets as commerce events.

Required outcomes:

- Faster first response.
- Autonomous resolution of repetitive tickets.
- Refund leakage reduction.
- Exchange over refund where policy permits.
- Delivery issue recovery before RTO/refund.
- Product education that drives repeat purchase.
- Support insights flowing back to product, logistics, ads, and lifecycle.

### 5.6 Pillar 6: Safe Agentic Execution

Brain must graduate from "recommend" to "act" where actions are safe, reversible, capped, and outcome-tracked.

The first version of autonomy should focus on low-risk, high-frequency actions:

- Pause underperforming ads.
- Reduce budget on fatiguing campaigns.
- Apply discount code to eligible abandoned-cart customer.
- Trigger WhatsApp/email winback to approved segment.
- Switch courier for a pincode/city rule within cap.
- Approve replacement under warranty policy.
- Issue refund under strict confidence and amount cap.
- Create reorder alert or draft purchase order.

Autonomy must always have visible guardrails and an Owner kill switch.

---

## 6. Metric and Formula Requirements

### 6.1 Revenue Definitions

Brain must support configurable revenue definitions because brands and regions differ. The selected default must be visible in every report.

| Revenue definition | Formula |
|---|---|
| Gross Sales | Sum of product price before discounts, refunds, taxes, and shipping adjustments. |
| Net Sales | Gross Sales - Discounts - Returns/Refunds. |
| Net Sales Net Tax | Net Sales - Included Tax. Recommended for India and VAT regions. |
| Net Revenue | Net Sales Net Tax + Shipping Revenue - Shipping Refunds - Payment Failures (captured-then-failed / chargeback corrections; failed-at-checkout orders never enter Net Sales). |
| Realized Revenue | Delivered/settled revenue after cancellations, RTO, payment failure, and refunds. |

### 6.2 Contribution Margin Waterfall

Brain must compute contribution margin at order, SKU, customer, cohort, campaign, day, week, month, channel, and workspace levels.

| Metric | Formula |
|---|---|
| Revenue Net Tax | Computed **per line item** as tax-inclusive price / (1 + SKU tax_rate), then summed. Must use each SKU's GST/VAT slab (India GST 2.0: 0/5/18/40), never a single blended rate, because real carts mix slabs. |
| COGS | Sum of landed SKU cost × quantity sold. |
| Gross Product Margin | Revenue Net Tax - COGS. |
| Variable Costs | Payment fees + packaging + shipping + COD fee + marketplace fee + return cost + support concession + other variable costs. |
| CM1 | Revenue Net Tax - COGS - non-marketing variable costs. |
| Marketing Spend | Paid media spend + influencer cost + affiliate commission + lifecycle message cost where configured. |
| CM2 | CM1 - Marketing Spend. |
| Fixed Costs | Salaries + agency + rent + software + warehouse fixed cost + other monthly overhead. |
| CM3 | CM2 - allocated Fixed Costs. |
| Operating Profit | CM3 - founder salary if included - financing cost - one-off expenses. |

### 6.3 Marketing Metrics

| Metric | Formula | Business use |
|---|---|---|
| MER | Net Revenue / Total Marketing Spend | Blended efficiency, hard to game. |
| aMER | New Customer Revenue / Acquisition Ad Spend | Acquisition engine truth. |
| paMER | Paid Revenue / Paid Marketing Spend | Paid-channel health. |
| CAC | Acquisition Ad Spend / New Customers | Cost to acquire. |
| CAC Payback | CAC / Monthly CM2 per new customer cohort | Cash recovery timeline. |
| LTV:CAC | Cohort cumulative CM2 / cohort CAC | Long-term acquisition quality. |
| Incremental ROAS | Incremental Revenue / Incremental Spend from holdout or experiment | Incrementality where testing exists. |
| Creative Fatigue Score | Function of CTR decay, hook-rate decay, conversion decay, frequency, spend, and time since launch | When to refresh creative. |

### 6.4 RTO and COD Metrics

| Metric | Formula | Use |
|---|---|---|
| RTO Rate | RTO Orders / Shipped Orders | Logistics leakage. |
| RTO Cost | Forward shipping + return shipping + COD fee + packaging + damage provision + lost contribution | True RTO impact. |
| True CM2 | CM2 - RTO Cost - late refund provision - payment failure provision | Margin after India/GCC delivery realities. |
| COD Share | COD Orders / Total Orders | Payment quality. |
| COD Realization Rate | Delivered COD Orders / COD Orders | Cash collection quality. |
| Break-even COD RTO Rate | r* = M / (M + C), where M = contribution margin on a delivered order and C = RTO cost per failed order. (A simple Margin/RTO-cost ratio understates the true break-even.) | When COD becomes unprofitable. |
| Prepaid Conversion ROI | Incremental delivered CM2 from prepaid conversions / incentive cost | Whether prepaid discount works. |

### 6.5 Lifecycle Metrics

| Metric | Formula |
|---|---|
| Recovered Cart Revenue | Realized revenue from recovered abandoned carts. |
| Recovered Cart CM2 | Recovered Cart Revenue - COGS - variable costs - offer cost - message/call cost - attributable marketing cost. |
| Winback Revenue | Realized revenue from customers inactive beyond threshold after Brain-triggered campaign. |
| Reorder Capture Rate | Reorders placed within expected depletion window / customers eligible for reorder. |
| VIP Retention Rate | VIP customers active in current period / VIP customers active in prior period. |
| Campaign Incrementality | Campaign cohort performance - holdout cohort performance where holdout exists. |
| Recovered Revenue / Brain Fee | Realized recovered revenue attributed to Brain / monthly Brain fee. |

### 6.6 Support and CX Metrics

| Metric | Formula |
|---|---|
| First Response Time | Time from customer message to first Brain/human response. |
| Resolution Time | Time from ticket creation to resolution. |
| AI Resolution Rate | Tickets resolved without human intervention / total eligible tickets. |
| Refund Save Rate | Refund requests converted to exchange/credit/education retention / refund requests. |
| Support-Saved Revenue | CM2 preserved from prevented refunds, exchanges, delivery saves, and retention actions. |
| Escalation Rate | Tickets escalated to human / total AI-handled tickets. |
| CSAT/NPS where collected | Survey outcome by ticket type and resolution type. |

### 6.7 Goal RAG Logic

Every metric must support a goal and RAG status.

- Higher-is-better metrics: Green ≥95% of goal, Amber 80-95%, Red <80%.
- Lower-is-better metrics: Green ≤105% of goal, Amber 105-125%, Red >125%.
- Goal period: daily, weekly, monthly, event-specific.
- Goal type: minimum, maximum, target, range.
- RAG output must include explanation and recommended action.

---

## 7. Decision Log and Memory Requirements

### 7.1 Decision Log Principle

Decision Log is mandatory infrastructure, not a reporting add-on.

Brain must write to Decision Log for:

- AI recommendations.
- User approvals, rejections, edits, deferrals, ignores.
- Manual decisions logged by operators.
- Auto-executed actions.
- Reversals.
- Lifecycle sends and campaign launches.
- WhatsApp journeys.
- Support resolutions.
- Refunds, replacements, exchanges, concessions.
- Courier changes and logistics actions.
- Inventory actions and purchase-order recommendations.
- Budget changes and ad pauses.
- Agent failures and guardrail blocks.
- 7-day and 30-day outcomes.

### 7.2 Decision Log Fields

Every Decision Log entry must include:

| Field | Requirement |
|---|---|
| decision_id | Unique immutable ID. |
| workspace_id | Brand/workspace isolation key. |
| actor_type | brain_agent, user, automation, external_api, system_guardrail. |
| actor_id | User ID, agent name, or system component. |
| domain | marketing, lifecycle, support, logistics, inventory, finance, product, pricing, compliance. |
| trigger | anomaly, schedule, user_query, ticket, campaign_event, stock_event, integration_event, manual_log. |
| condition_snapshot | Structured metrics at decision time. |
| recommendation | Human-readable summary. |
| action_payload | Structured executable action. |
| expected_impact | Revenue, CM2, cost, time, or risk impact. |
| confidence | Numeric score plus reason. |
| risk_level | low, medium, high, critical. |
| reversibility | reversible, partially_reversible, irreversible. |
| approval_state | proposed, approved, rejected, edited, auto_executed, blocked, reversed, expired. |
| execution_state | not_started, queued, sent, executed, failed, reversed. |
| channel/provider | Where action happened, if any. |
| cost | Message, call, discount, ad spend, refund, or other cost. |
| revenue_attributed | Placed, realized, and CM2 revenue fields. |
| outcome_7d | Structured outcome after 7 days. |
| outcome_30d | Structured outcome after 30 days. |
| learning_note | Short explanation for future recommendations. |

### 7.3 Brand Fingerprint

Brain must maintain a Brand Fingerprint that summarizes the brand's operating patterns across time.

Required dimensions:

- Revenue by day of week and hour where available.
- CM2 and CM3 trend by period.
- Channel efficiency curves.
- Acquisition vs returning revenue mix.
- First-product repeat curves.
- RTO and COD baseline by region/pincode/courier/product.
- Creative fatigue half-life.
- Discount sensitivity.
- WhatsApp response behavior.
- Support issue mix.
- Refund/replacement patterns.
- Inventory velocity and stockout impact.
- Festival and sale-event multipliers.
- Cash settlement patterns.

### 7.4 Condition-Outcome Memory

Brain must store condition-outcome pairs:

```
condition = what was true at the time
recommendation = what Brain suggested
action = what was actually done
outcome = what happened after 7 and 30 days
learning = what should change next time
```

This is the learning loop that makes Brain more valuable after every week of use.

### 7.5 Cross-Brand Benchmarks

Brain may create benchmark insights only when privacy thresholds are met.

Requirements:

- No raw cross-brand data visible to another brand.
- Minimum benchmark cohort size before display.
- Benchmarks aggregated and anonymized by category, region, GMV band, AOV band, and channel maturity.
- Benchmark output must show sample size and confidence label.
- Owner can opt out of benchmark contribution where required by enterprise policy.

---

## 8. Product Surfaces

### 8.1 Home / Command Center

The Brain Home surface must answer the operator's current-day question within seconds.

Required components:

1. **Live Revenue + Profit Strip**
   - Today revenue, yesterday revenue, MTD revenue.
   - CM2 and CM3 estimate.
   - MER/aMER.
   - New vs returning revenue.
   - Realized vs placed revenue where delivery/payment lag applies.

2. **Revenue Quality Panel**
   - Prepaid vs COD mix.
   - RTO risk today.
   - Refund spike.
   - Support issue spike.
   - Low-margin SKU contribution.

3. **Top 3 Actions**
   - Ranked by expected CM2 impact and urgency.
   - Approve / reject / edit / ask why.
   - Visible confidence and risk.

4. **Queues**
   - Lifecycle queue.
   - Support queue.
   - Logistics queue.
   - Ad action queue.
   - Inventory queue.

5. **Decision ROI**
   - Revenue booked by Brain this month.
   - Realized revenue recovered.
   - CM2 recovered/protected.
   - Brain fee coverage ratio.

6. **Integration Health**
   - Freshness by provider.
   - Broken syncs.
   - Data quality warnings.

### 8.2 Morning Brief

The Morning Brief is the daily executive surface.

Requirements:

- Delivered around local morning time configured per workspace.
- Contains at most three actions, not a dump of charts.
- Each action includes: problem, evidence, recommended action, expected impact, risk, confidence, action buttons.
- Must reference margin/revenue impact whenever possible.
- Must write user response into Decision Log.

Example structure:

```
Brain | {Brand} | {Date}
Yesterday: {Revenue} | CM2 {CM2%} | MER {MER} | RTO Risk {RTO%}

1. {Highest-priority action}
Evidence: {specific numbers}
Expected impact: {revenue/CM2/time/risk}
Action: Approve / Edit / Reject

2. {Second action}
3. {Third action}

This month: {Brain recovered revenue} realized revenue | {CM2} recovered CM2 | {fee coverage}x Brain fee
```

### 8.3 Evening Pulse

The Evening Pulse is not a full report. It should answer:

- Are we on pace today?
- What broke after the morning?
- Which queue needs action before day-end?
- Did any approved action produce early signal?

### 8.4 Weekly Review

Weekly Review must connect strategy and accountability:

- Revenue, CM2, CM3 vs plan.
- Channel efficiency vs prior week and goal.
- New vs returning revenue.
- Customer lifecycle movement.
- RTO/COD/logistics movement.
- Support and refund movement.
- Top 3 wins.
- Top 3 leaks.
- Decision Log: recommendations made, approved, rejected, ignored, executed, reversed.
- Outcome accuracy.
- Next week's top priorities.

### 8.5 Month-End Compound Report

The Month-End Compound Report must answer:

> What did Brain learn about this brand this month?

Required sections:

- What drove realized revenue.
- What improved or hurt CM2.
- Which actions worked.
- Which actions failed or were reversed.
- Which customer segments changed.
- Which products improved repeat behavior.
- Which creatives fatigued or won.
- Which regions/pincodes/couriers changed.
- Which support issue themes affected revenue.
- What Brain will do differently next month.

### 8.6 Sale/Event Mode

For sale events, launches, festivals, or campaign pushes, Brain must support high-frequency monitoring.

Requirements:

- Event goal, start/end time, channel plan, forecast curve.
- Hourly revenue and CM2 pace.
- Expected vs actual by hour.
- Ad spend pace.
- Inventory pressure.
- Support/ticket spike.
- COD/RTO risk by region.
- Alert if hourly revenue drops materially vs pace.
- Alert if CM2 falls below event threshold even if revenue rises.
- Decision Log overlay of every action taken during event.

### 8.7 Natural Language Query

Users may ask business questions in plain language. Brain must answer with:

- The direct answer.
- Exact numbers and formulas used.
- Filters/time period.
- Confidence or caveat if data is incomplete.
- Suggested next action.
- Link to underlying report/table.

LLMs must not invent numbers. All numbers must come from deterministic queries or approved model outputs.

---

## 9. Integration Requirements

### 9.1 Integration Philosophy

Brain is the operating system above the stack, not a replacement for every underlying tool on day one. It should integrate, read, write, and progressively internalize workflows where Brain's intelligence and Decision Log create durable advantage.

Provider names are implementation targets. They are not positioning anchors.

### 9.2 Integration Categories

| Category | Purpose | Example providers |
|---|---|---|
| Storefront / commerce | Orders, customers, products, inventory, discounts, refunds | Shopify, WooCommerce, Magento, custom storefronts, Salla, Zid. |
| Marketplaces | Marketplace sales and profitability | Amazon, Flipkart, Myntra, Nykaa, Noon, Namshi, marketplace seller exports. |
| Ads | Spend, campaigns, creatives, conversions, audiences | Meta Ads, Google Ads, Snapchat Ads, Amazon Ads; TikTok Ads (UAE/GCC only — banned in India, so region-gated). |
| Analytics / tracking | Sessions, attribution, product page conversion | GA4, first-party events, server-side event streams. |
| Payments | Payment method, fees, settlements, refunds, failed payments | Razorpay, Cashfree, PayU, Stripe, checkout providers, BNPL providers. |
| Logistics | Shipments, NDR, RTO, delivery speed, courier performance | Shiprocket, Delhivery, Blue Dart, Aramex, DHL, SMSA, regional couriers. |
| OMS / ERP / inventory | Stock, purchase orders, warehouses, allocation | Unicommerce, Eshopbox, Zoho Inventory, ERPNext, custom ERP, POS/ERP systems. |
| Messaging | WhatsApp, SMS, RCS, email, push | WhatsApp Cloud API, Gupshup, Interakt, Wati, AiSensy, Twilio, Exotel, Plivo, Klaviyo, Mailmodo. |
| Support | Tickets, conversations, tags, resolutions | Zendesk, Freshdesk, Gorgias, Intercom, email inboxes, Instagram DM where available. |
| Reviews / loyalty / referrals | Reviews, loyalty points, referral attribution | Review platforms, loyalty platforms, referral platforms. |
| Finance/accounting | P&L, invoices, expenses, settlement reconciliation | Tally exports, Zoho Books, QuickBooks, Xero, Google Sheets imports. |

### 9.3 Integration Quality Levels

Brain must label integration quality honestly:

| Level | Meaning | UX requirement |
|---|---|---|
| Green | Clean API or stable first-party integration. | Normal setup and health monitoring. |
| Yellow | API exists but access is gated, inconsistent, or requires per-brand onboarding. | Show setup caveats and owner follow-up tasks. |
| Red | No reliable API; import/export, email parsing, or manual upload required. | Label brittle, monitor strongly, notify on breakage, never hide limitations. |

### 9.4 Data Freshness Requirements

| Data type | Freshness target |
|---|---|
| Orders | 5-15 minutes for webhooks; hourly fallback. |
| Ads spend | Hourly where API permits; daily finalized correction. |
| Logistics/NDR | Hourly for active shipments. |
| Payments/settlements | Hourly or daily depending on provider. |
| Support tickets | Near-real-time for connected inboxes. |
| Inventory | Hourly for connected OMS; daily for manual imports. |
| Benchmarks | Daily or weekly, not real-time. |

### 9.5 Integration Health Surface

Every integration must expose:

- Connected/disconnected state.
- Last successful sync.
- Current lag.
- Error type.
- Affected reports/workflows.
- Data completeness score.
- Owner action required.
- Retry status.
- Whether recommendations are blocked, degraded, or safe.

Brain must not make high-risk recommendations using stale or incomplete data without clearly saying so.

---

## 10. Analytics and Reporting Requirements

### 10.1 Store Analytics

Store Analytics is the operational heartbeat.

Required cards:

- Gross Sales.
- Net Sales.
- Net Sales Net Tax.
- Revenue.
- Realized Revenue.
- Orders.
- AOV.
- New customer revenue.
- Returning customer revenue.
- Discounts.
- Refunds.
- Payment failures.
- COGS.
- Variable costs.
- CM1, CM2, CM3.
- MER, aMER, CAC.
- Prepaid %, COD %, COD realization.
- RTO rate and RTO cost.
- Support-saved revenue.
- Brain-attributed recovered revenue.

Each metric must support drill-down to source rows.

### 10.2 P&L Module

Required views:

- Daily, weekly, monthly, quarterly.
- Absolute value and percentage of revenue.
- All customers, new customers, returning customers.
- Product/SKU filter.
- Channel filter.
- Region/pincode/city filter.
- Campaign/ad filter where attribution exists.
- Export.

### 10.3 Acquisition Analytics

Required features:

- Campaign classification: Acquisition, Non-Acquisition, Brand, Retention, Unclassified.
- Unclassified spend warning.
- MER/aMER by day, week, campaign, channel.
- Funnel metrics: impression, click, add-to-cart, checkout initiated, purchase.
- Creative metrics: hook rate, hold rate, completion, CTR, CVR, CPA, CM2 contribution.
- New-customer quality by campaign: first order CM2, repeat rate, RTO, refund rate, LTV.
- Budget suggestions with expected impact and risk.

### 10.4 Product and SKU Analytics

Required features:

- SKU revenue, units, margin, return rate, RTO rate.
- First-product repeat cascade.
- Pareto contribution by CM1/CM2.
- Bundle and cross-sell recommendations.
- Product page conversion where data exists.
- Discount sensitivity by SKU.
- Stockout impact estimate.
- Dead stock and overstock flags.

### 10.5 Customer and Lifecycle Analytics

Required features:

- New, returning, reactivated, at-risk, churned states.
- P40/P80 churn thresholds based on actual order gaps.
- RFM/RFMC segmentation.
- Predicted LTV using CM2 as monetary value.
- First product cohort and channel cohort.
- Discount code cohort.
- Winback eligibility.
- Reorder timing by product.
- Segment-level channel preference.

### 10.6 Logistics and RTO Analytics

Required features:

- RTO by pincode, city, state/emirate, courier, product, payment method, channel, campaign, AOV band.
- NDR queue and resolution rate.
- Delivery attempt and delivery speed.
- Courier performance score.
- Courier switch recommendation.
- Pincode blacklist/watchlist recommendation.
- COD confirmation impact.
- Estimated RTO cost and CM2 drag.

### 10.7 Inventory Analytics

Required features:

- Current inventory by SKU/location.
- Days of cover.
- Sell-through.
- Forecasted stockout date.
- Reorder quantity.
- Safety stock.
- Inventory value.
- Overstock/dead stock.
- Demand forecast adjusted for campaigns, festivals, and seasonality.
- Ad-spend risk when inventory is insufficient.

### 10.8 Finance and Cash Analytics

Required features:

- Settlement timing by provider.
- COD cash delay.
- Refund liability.
- Payment fees.
- Marketplace receivables.
- Cash-conversion estimate.
- Forward P&L Plan.
- Scenario builder: spend change, discount change, sale target, RTO shock, stockout, payment mix shift.

---

## 11. Lifecycle and WhatsApp Marketing Requirements

### 11.1 Lifecycle Strategy

Brain must treat WhatsApp, email, SMS, calls, push, and ad audiences as execution rails controlled by one audience and decision layer.

The user should not have to rebuild the same segment separately for each channel.

Lifecycle workflow structure:

1. Select trigger or segment.
2. Brain estimates audience size, expected response, expected realized revenue, expected CM2, offer cost, channel cost, risk.
3. Brain recommends channel mix.
4. Operator approves or edits.
5. Brain executes or sends to connected provider.
6. Brain tracks placed revenue, realized revenue, CM2, unsubscribes, complaints, opt-outs, refunds, RTO, and repeat purchase.
7. Decision Log records outcome.

### 11.2 WhatsApp Requirements

Brain must support:

- WhatsApp template management.
- Consent-aware sending.
- Segment-based broadcast.
- Trigger-based journeys.
- Two-way replies.
- Human handoff.
- Opt-out handling.
- Message cost tracking (per delivered template message, by category — marketing/utility/authentication — per WhatsApp's post-July-2025 per-message model; service-window replies are free).
- UTM and coupon attribution.
- Revenue realization after delivery/payment/RTO.
- Frequency caps by customer and segment.
- Multilingual templates where configured.

### 11.3 Core WhatsApp Workflows

| Workflow | Trigger | Brain decision logic |
|---|---|---|
| Abandoned Cart | Cart abandoned after configured window | RFM value, cart value, prior discount usage, likelihood to convert, expected CM2. |
| COD Confirmation | COD order placed | RTO propensity, pincode/courier history, order value, customer history, call/WhatsApp route. |
| Prepaid Conversion | COD customer eligible | Incentive ROI vs RTO risk and margin. |
| Post-Delivery Education | Delivered order + product category | Education content, review request, replenishment timing. |
| Reorder/Replenishment | Expected depletion window | SKU consumption curve, last purchase date, inventory, offer necessity. |
| Winback | Customer inactive past threshold | LTV, discount sensitivity, prior response, channel preference. |
| VIP Retention | Top-value segment | Personal tone, early access, no unnecessary discounting. |
| Refund Save | Refund request | Policy, issue type, replacement/credit option, margin impact. |

### 11.4 Offer Governance

Brain must not default to discounts.

Offer ladder:

1. No discount: service, urgency, education, reminder, social proof.
2. Low-cost value add: bundle suggestion, sample, gift where margin permits.
3. Limited discount: only when expected CM2 remains positive.
4. Escalated retention offer: high-value customer or high-risk save.
5. Human review: low confidence, high cost, sensitive customer.

### 11.5 Lifecycle Attribution

Brain must support three attribution views:

- **Direct placed revenue:** customer clicked/replied and placed order within window.
- **Realized revenue:** order delivered/paid/settled after post-order leakage.
- **Incremental revenue:** campaign cohort vs holdout or baseline where available.

All lifecycle surfaces must show realized revenue and CM2, not only placed revenue.

---

## 12. AI Ticket Management Requirements

### 12.1 Ticket Scope

Brain must connect support to commerce outcomes. The initial AI ticket system must support:

- WhatsApp messages.
- Email tickets.
- Website chat.
- Instagram DMs where supported.
- Marketplace messages where available.
- Support desk integrations.

### 12.2 Initial Ticket Types

Brain must classify and resolve or route these ticket types:

1. Order status.
2. Delivery delay.
3. NDR/customer unavailable.
4. Address change.
5. Cancel order.
6. Return request.
7. Refund status.
8. Replacement/exchange.
9. Missing/damaged item.
10. Product recommendation.
11. Product usage education.
12. COD to prepaid conversion.
13. Payment failed but amount debited.
14. Discount/coupon issue.
15. Complaint/escalation.

### 12.3 Ticket Enrichment

Every ticket must be enriched with:

- Customer order history.
- RFM segment.
- LTV/predicted LTV.
- Last order status.
- Payment method.
- Courier/shipment status.
- Prior tickets.
- Refund/return history.
- Consent state.
- Policy eligibility.
- Suggested resolution and CM2 impact.

### 12.4 Resolution Logic

Brain must follow a structured flow:

1. Classify issue and urgency.
2. Pull commerce context.
3. Check policy and permissions.
4. Estimate revenue/profit impact of possible resolutions.
5. If low-risk and high-confidence, resolve automatically.
6. If medium confidence, draft response for human approval.
7. If high-risk or sensitive, escalate to human with summary.
8. Log resolution and outcome.

### 12.5 Support-to-Commerce Feedback

Support insights must feed other modules:

- Product complaints → SKU quality warnings.
- Delivery delay complaints → courier score and pincode risk.
- Refund reasons → product page, quality, sizing, expectation mismatch.
- Repeated ad promise mismatch → creative and landing page warning.
- High product education need → post-purchase content journey.
- Product recommendation questions → cross-sell/bundle opportunity.

### 12.6 AI Safety Rules for Support

Brain must not:

- Invent delivery status.
- Promise refund/replacement outside policy.
- Reveal internal margin, customer scores, or risk labels.
- Use sensitive personal data in responses.
- Continue automation if customer asks for human.
- Send messages without consent where consent is required.
- Make irreversible financial decisions above cap.

---

## 13. Agent Workflows

### 13.1 Agent Groups

Brain must organize intelligence around three executive agent groups.

| Agent group | Focus | Typical actions |
|---|---|---|
| AICMO | Growth, acquisition, creative, lifecycle, retention, pricing/promo | Pause ad, shift budget, launch segment, generate creative brief, adjust offer, trigger winback. |
| AICOO | Operations, logistics, inventory, support, fulfillment | Switch courier, flag pincode, resolve NDR, reorder SKU, route ticket, replace item. |
| AICFO | Profit, cash, planning, risk, unit economics | Update plan, flag margin leak, assess discount, forecast cash, enforce CM2 gates. |

### 13.2 Specialist Agents

Initial specialist agents:

1. **Morning Brief Agent:** ranks top 3 actions.
2. **Anomaly Agent:** detects meaningful metric movement and root causes.
3. **Budget Agent:** recommends spend changes using MER/aMER/CM2.
4. **Creative Agent:** detects creative fatigue and proposes variants/briefs.
5. **Lifecycle Agent:** selects segments, channel mix, offer, timing.
6. **Support Agent:** resolves or routes tickets.
7. **RTO/Courier Agent:** detects logistics leakage and action opportunities.
8. **Inventory Agent:** predicts stockout/overstock and drafts replenishment actions.
9. **Plan Agent:** forecasts forward P&L and scenario outcomes.
10. **Pricing/Discount Agent:** checks promotion margin quality.

### 13.3 Agent Output Contract

Every recommendation must include:

- Action title.
- Why now.
- Metrics used.
- Expected revenue impact.
- Expected CM2 impact.
- Confidence score.
- Risk level.
- Reversibility.
- Required approval level.
- Execution path.
- Fallback if user rejects.
- Outcome measurement plan.

### 13.4 Agent Ranking

Brain must rank recommendations using:

- Expected CM2 impact.
- Revenue impact.
- Urgency/time sensitivity.
- Confidence.
- Risk.
- Reversibility.
- Data freshness.
- Brand priorities/goals.
- Required operator effort.
- Whether action affects customer trust.

### 13.5 Human-in-the-Loop States

Every agent action must be in one of these states:

- Drafted.
- Recommended.
- Needs approval.
- Approved.
- Rejected.
- Edited.
- Queued.
- Executed.
- Failed.
- Blocked by guardrail.
- Reversed.
- Outcome pending.
- Outcome measured.

---

## 14. Auto-Execute Requirements

### 14.1 Auto-Execute Definition

Auto-execute means Brain takes an operational action on behalf of the brand without waiting for per-action human approval, because the Owner has pre-approved the action class, cap, conditions, and guardrails.

Auto-execute is not enabled by default. Owner must explicitly enable it per action class.

### 14.2 Initial Auto-Execute Actions

| Action | Default threshold | Risk | Reversibility |
|---|---:|---|---|
| Pause underperforming ad | 0.90 | Low-medium | Reversible. |
| Reduce daily budget by up to configured % | 0.85 | Medium | Reversible. |
| Apply approved abandoned-cart discount | 0.80 | Low | Reversible until used/expired. |
| Send approved lifecycle message to approved segment | 0.85 | Medium | Partially reversible; can stop future sends. |
| Switch courier rule for high-RTO pincode within cap | 0.85 | Medium | Partially reversible. |
| Approve replacement under policy | 0.90 | Medium | Partially reversible. |
| Issue refund under cap for verified case | 0.95 | High | Irreversible. |
| Draft purchase order / reorder alert | 0.90 | Low-medium | Draft only unless Owner enables PO send. |

### 14.3 Guardrails

Auto-execute requires:

- Owner opt-in.
- Action-level caps.
- Daily/weekly spend caps.
- Confidence threshold.
- Data freshness check.
- Consent check where customer communication is involved.
- Policy check where refund/replacement is involved.
- Approval fallback when confidence is low.
- Kill switch.
- Automatic revert to recommend-only if reversal/error rate crosses threshold.
- Decision Log entry for every action.

### 14.4 Kill Switch

Brain must expose a global kill switch:

- Owner can pause all auto-execute within 60 seconds.
- Operators can request pause if granted.
- System can auto-pause a specific agent/action class.
- Pausing does not stop analytics or recommendations.
- Pausing must be logged.

### 14.5 Reversal and Audit

For every auto-executed action, Brain must show:

- What happened.
- Why it happened.
- Which data was used.
- Which guardrails passed.
- Expected impact.
- Current outcome.
- Whether reversal is possible.
- Reverse button where safe.
- Owner-visible audit trail.

---

## 15. Pricing and Packaging Requirements

### 15.1 Pricing Principle

Brain pricing must align with commerce scale. It must not punish brands for inviting more teammates.

Core rule:

> Brain is priced as a percentage of GMV under management by tier, with enterprise contracts where complexity requires fixed annual pricing or custom deployment.

No per-seat pricing.

**GMV base.** "GMV under management" means **realized/delivered GMV** — order value that survives cancellation, payment failure, RTO, and refund — not placed GMV. Brain bills on the revenue the brand actually keeps. This is consistent with Brain's realized-revenue philosophy and is the only fair base in a market where COD RTO commonly runs 20–35%.

**Minimum monthly fee.** Each tier has a minimum monthly fee (a cost-to-serve floor); the GMV percentage applies above it. This protects unit economics for the smallest qualifying brands and during low-revenue months.

**CM2 affordability guardrail.** The GMV fee must remain a sane share of the brand's contribution margin. For thin-margin brands, Brain applies the **lower** of (the tier %-of-GMV) or (a configured cap as a % of CM2), so the fee never consumes a disproportionate share of profit. A brand should never feel that Brain's fee is the reason it became unprofitable.

**Activation period.** New brands get a time-boxed activation period (aligned with the Day 0–14 onboarding sequence) before the first GMV-based invoice, so cost setup and data quality reach the accuracy bar before billing begins.

### 15.2 Indicative Packaging

| Tier | Qualification | Pricing logic | Included |
|---|---|---|---|
| Launch / Self-Serve | Emerging and operator-led brands above minimum GMV threshold | ~1.0% of GMV under management or equivalent regional plan | Core analytics, Morning Brief, Decision Log, lifecycle basics, integrations, standard support. |
| Growth | Larger scaling brands with higher GMV | ~0.75% of GMV under management | Advanced lifecycle, AI inbox, budget/creative agents, inventory/logistics agents, expanded workflows. |
| Scale | High GMV, multi-channel, or multi-region brands | ~0.5% of GMV under management or custom | Auto-execute, advanced planning, deeper integration support, portfolio views where applicable. |
| Enterprise | Complex security, deployment, SLA, data residency, multi-brand, or custom requirements | Fixed annual contract and/or reduced GMV-linked component | Enterprise controls, custom integrations, private data options, SLA, security reviews, dedicated support. |

All percentages apply to **realized/delivered GMV above the tier minimum monthly fee**, subject to the CM2 affordability guardrail. Exact commercial terms can vary by region, customer size, onboarding burden, and support commitments, but product architecture must support these packaging boundaries.

### 15.3 Included Value

The GMV-linked fee should include:

- Core analytics and reporting.
- Decision Log and memory.
- Morning Brief, Evening Pulse, weekly and monthly reporting.
- Agent recommendations.
- Lifecycle orchestration.
- WhatsApp/email/SMS/call workflow orchestration, excluding pass-through provider costs where applicable.
- AI ticket management within plan limits.
- Standard integrations.
- Standard data retention.
- Standard support.

### 15.4 Pass-Through and Caps

Brain must track variable costs:

- LLM usage.
- Messaging cost (WhatsApp per delivered template message by category; SMS per DLT-registered template; email per volume).
- Call minutes.
- Email volume.
- Data warehouse/storage overages.
- Connector premium fees.

The product should expose usage and caps so Brain remains margin-safe.

### 15.5 Value Proof

Every paying customer should see:

- Brain-attributed placed revenue.
- Brain-attributed realized revenue.
- Brain-attributed recovered/protected CM2.
- Brain fee.
- Recovered revenue / Brain fee ratio.
- CM2 recovered / Brain fee ratio.
- Operator time saved.

This is essential because Brain is sold as a revenue/profit centre.

---

## 16. Onboarding Requirements

### 16.1 Onboarding Sequence

| Day | Requirement |
|---|---|
| Day 0 | Owner creates organization/brand, selects region, currency, timezone, revenue definition. |
| Day 0-1 | Connect commerce, ads, payments, logistics, messaging/support integrations. |
| Day 1-3 | Historical backfill, data quality scan, mapping, cost setup. |
| Day 3 | First Brand Fingerprint generated, initial customer segments computed. |
| Day 4 | First Morning Brief. |
| Day 7 | First weekly metric accuracy review. Owner signs off on cost assumptions and revenue definition. |
| Day 14 | Trial/activation review: recovered value, data gaps, next workflows to enable. |
| Day 30 | Decision Log and lifecycle ROI review. |

### 16.2 Cost Data Setup

Brain cannot compute honest CM2 without cost data.

Required onboarding fields:

- SKU-level landed COGS.
- Packaging cost.
- Forward shipping cost rules.
- Return shipping cost rules.
- COD fee rules.
- Payment gateway fee rules.
- Marketplace fee rules.
- Refund/restocking/damage provisions.
- Fixed monthly costs.
- Founder salary optional and Owner-visible.
- Warehouse/fulfillment cost if applicable.

Brain must label reports as estimated until cost data is sufficient.

### 16.3 Data Quality Checks

Onboarding must validate:

- Order totals reconcile with storefront.
- Ad spend totals reconcile with ad platforms.
- Payment method data exists.
- Refunds and returns are mapped.
- Logistics/RTO status is available.
- SKU costs cover top 80% of revenue.
- Customer identifiers can be joined across sources.
- Timezone and currency settings are correct.
- Tax settings match region.
- Consent data exists for lifecycle.

### 16.4 First Value Milestone

Within the first 7 days, Brain should deliver at least one of:

- CM2 truth that changes operator understanding.
- RTO/COD leak diagnosis.
- Wasted spend action.
- Lifecycle recovery action.
- Support refund-save action.
- Inventory/stockout warning.
- Concrete plan change.

---

## 17. Regional Adapter Requirements

### 17.1 Region Adapter Principle

Brain must not fork product logic by geography. Each region adapter provides regional rules to the same core engine.

Adapter responsibilities:

- Currency and formatting.
- Tax handling.
- Payment method economics.
- Logistics and return conventions.
- Local holidays and sale events.
- Consent and messaging constraints.
- Postal/geography hierarchy.
- Regional provider catalog.
- Default cost assumptions.
- Language/template defaults.

### 17.2 India Adapter

Required India support:

- INR and Indian numbering format.
- GST 2.0 slab handling (0/5/18/40) with GST-inclusive pricing and per-SKU slab overrides.
- COD/prepaid split.
- COD fees.
- RTO and NDR modeling (COD RTO commonly 20–35% vs prepaid ~2–8%; the single largest controllable margin leak in Indian DTC).
- Pincode hierarchy.
- City tier classification.
- Courier scoring.
- Channel-specific compliance guardrails: DLT (TCCCPR) for SMS/voice, NCPR/DND scrubbing, 9am–9pm promotional calling-hour window; Meta opt-in + template approval for WhatsApp; DPDP Act consent/retention/erasure for customer PII.
- Indian festival calendar: Diwali, Dhanteras, Navratri, Dussehra, Eid, Holi, Onam, Rakhi, Independence Day sale, Republic Day sale, wedding season, year-end sale.
- Payment settlement and COD cash delay.

### 17.3 UAE/GCC Adapter

Required UAE/GCC support:

- AED/SAR/local currencies.
- Country-specific VAT handling (KSA 15%, UAE 5%, Bahrain 10%, Oman 5%; Qatar/Kuwait none yet).
- UAE PDPL / KSA PDPL data-protection compliance (explicit opt-in marketing, consent withdrawal, erasure, cross-border transfer restrictions).
- Emirates/city/geography mapping.
- Ramadan/Eid and local shopping calendar.
- WhatsApp-first communication defaults.
- Arabic/English template support.
- BNPL and payment fee support.
- Cross-border shipping and duties fields.
- Marketplace/delivery-app margin leakage fields.
- Retail/POS data hooks where available.

### 17.4 Retail Extension

Brain should support DTC-first use cases now and retail-aware expansion where DTC brands operate offline or marketplace/retail channels.

Retail-aware requirements:

- POS data ingestion.
- Store-level sales and inventory.
- Store-level margin and staff/discount leakage where available.
- Online/offline customer identity resolution where consent permits.
- Inventory allocation recommendations.
- Marketplace vs owned-store profitability.
- Store ops accountability views.

The wedge is the decision/workflow layer, not ripping out mission-critical ERP/POS from day one.

---

## 18. Go-To-Market and Customer Success Requirements

### 18.1 Positioning

Brain's positioning:

> One operating system for DTC revenue and profit. Brain connects the stack, tells the operator what changed, recommends what to do, executes safely, and learns from every outcome.

Avoid positioning Brain as:

- A dashboard.
- A reporting tool.
- A chatbot.
- A cheaper analytics product.
- A helpdesk product.
- A WhatsApp product.

### 18.2 Sales Qualification Questions

Sales/onboarding agents should ask:

1. Monthly GMV and region.
2. Storefront and marketplace channels.
3. Ad channels and monthly spend.
4. COD/prepaid split.
5. RTO rate and delivery pain.
6. Gross margin and CM2 visibility.
7. Support volume and top ticket types.
8. WhatsApp/email/SMS usage.
9. Current reporting process.
10. Who makes daily decisions.
11. Which actions they take manually today.
12. What would make Brain pay for itself in 30 days.

### 18.3 Sales Demo Flow

The demo should follow operator truth:

1. Start with today's revenue quality, not feature list.
2. Show CM2 waterfall.
3. Show one leak: ad, RTO, lifecycle, support, or inventory.
4. Show the recommended action and expected value.
5. Show Decision Log and outcome tracking.
6. Show recovered revenue / Brain fee ratio.
7. Show safety guardrails for execution.

### 18.4 Customer Success Cadence

For first 30 days:

- Week 1: data accuracy and cost setup.
- Week 2: first lifecycle/support recovery workflow.
- Week 3: Decision Log adoption and action quality.
- Week 4: ROI review and next automation settings.

After 30 days:

- Weekly review for active customers.
- Monthly compound report.
- Quarterly operating review for larger brands.

### 18.5 Activation Metrics

A brand is activated when:

- At least three core integrations are healthy.
- Cost setup covers top 80% of revenue.
- Morning Brief has been delivered.
- At least five recommendations are logged.
- At least one action is approved/executed.
- At least one realized revenue/profit outcome is attributed.

---

## 19. Compliance, Privacy, and Trust Requirements

### 19.1 Compliance Posture

Brain acts as a processor/service provider for brand data. The brand remains responsible for its customer consent and legal basis, but Brain must provide tools and defaults that reduce compliance risk.

**Applicable regimes Brain must be built around:**

- **India — DPDP Act 2023 + DPDP Rules 2025** (notified 13 Nov 2025; phased: procedural now → registered Consent Managers ~Nov 2026 → core obligations of notice, security, breach notification, erasure, and Significant Data Fiduciary duties by ~May 2027). Consent-based processing, data minimization, retention limits, right to erasure, breach notification.
- **India telecom — TCCCPR 2018 (amended 12 Feb 2025):** DLT registration for A2P SMS/voice, NCPR/DND scrubbing, 9am–9pm promotional window, tightened complaint thresholds.
- **UAE — PDPL** (Federal Decree-Law 45/2021, in force Jan 2022) and **KSA — PDPL** (enforced 14 Sep 2024): explicit, revocable opt-in for direct marketing, erasure, cross-border transfer restrictions, penalties up to SAR 5M (KSA).

**Data residency default:** India customer data is stored in-region by default (not enterprise-only), consistent with DPDP and KSA/UAE transfer restrictions; enterprise customers can configure additional residency controls.

Required compliance support:

- Data processing agreement.
- Sub-processor list.
- Data export.
- Deletion workflows.
- Consent state tracking.
- Audit logs.
- Role-based access.
- PII minimization.
- Encryption.
- Regional data controls and in-region data storage (India in-region by default; additional residency configurable for enterprise).

### 19.2 Data Brain Should Store

| Data type | Storage requirement |
|---|---|
| Orders | Order ID, timestamps, line items, amounts, payment method, status. |
| Customers | Hashed identifiers by default; plain identifiers only where required for approved outreach. |
| Products | SKU, cost, inventory, category, tags, prices, bundles. |
| Ads | Campaign/ad/adset metrics, spend, creative metadata, classification. |
| Logistics | Shipment status, courier, RTO/NDR, delivery timing, pincode/city. |
| Payments | Payment method, fees, settlement timing, refund status; never card/UPI secrets. |
| Support | Tickets, messages, categories, outcomes, policies; PII minimized. |
| Decision Log | Recommendation/action/outcome history for the life of the brand unless deletion/export policy applies. |

### 19.3 Data Brain Must Not Store

- Card numbers, CVVs, raw bank account details, full UPI IDs.
- National ID numbers.
- Health/biometric/sensitive special-category data.
- Plain-text passwords.
- Full customer addresses unless explicitly required and approved for a workflow; default should be pincode/city-level analytics.
- PII in logs.

### 19.4 Consent Rules

Brain must track consent by:

- Customer.
- Channel.
- Purpose.
- Source.
- Timestamp.
- Region.
- Withdrawal state.

Outreach workflows must exclude opted-out or withdrawn customers. Analytics can retain aggregated anonymous metrics where legally permitted.

**Channel-specific outbound rules Brain must enforce:**

- **WhatsApp:** Meta opt-in, approved templates, frequency caps, and the free 24h service window for replies.
- **SMS/voice:** DLT-registered headers/templates, NCPR/DND scrubbing, and the 9am–9pm promotional calling-hour window.
- **AI voice calls:** the same calling-hour + DND rules, plus clear automated-agent disclosure and immediate human handoff on request.

**Consent Managers (forward-looking):** Brain's consent model must be compatible with DPDP-registered Consent Managers (registration phase ~Nov 2026), so brands can later honor consent granted or withdrawn through a third-party Consent Manager.

### 19.5 Audit Requirements

Audit log must record:

- Login and user changes.
- Role changes.
- Integration connect/disconnect.
- Token refresh failures.
- Cost setting changes.
- Goal changes.
- Lifecycle send approvals.
- Support resolutions.
- Refund/replacement actions.
- Auto-execute enable/disable.
- Kill switch events.
- Data export/deletion events.

---

## 20. KPIs and Success Metrics

### 20.1 Customer Value KPIs

| KPI | Target/Direction |
|---|---|
| Realized revenue recovered by Brain | Up month-over-month. |
| Recovered/protected CM2 | Up month-over-month. |
| Recovered revenue / Brain fee | >3x by month 3, >5x by month 6 for mature customers. |
| CM2 recovered / Brain fee | Positive and expanding. |
| RTO cost reduction | Region/category-specific target. |
| COD-to-prepaid conversion lift | Positive vs baseline. |
| Wasted ad spend reduced | Positive vs baseline. |
| Refund save rate | Positive vs baseline. |
| Support first-response time | <60s for WhatsApp/chat where connected. |
| Operator time saved | Tracked by actions automated and queues compressed. |

### 20.2 Product Engagement KPIs

| KPI | Target/Direction |
|---|---|
| Morning Brief open rate | >80% for Owners/Operators. |
| Recommendation approval rate | 40-70%; too low means poor quality, too high may mean obvious recommendations. |
| Decision Log coverage | 100% of Brain actions, high capture of manual decisions. |
| Outcome measurement coverage | >90% of eligible recommendations have 7d/30d outcomes. |
| Weekly active operator usage | High among active brands. |
| Integration health | >99% healthy for Green connectors. |
| Auto-execute reversal rate | <8%, alert at 15%. |

### 20.3 Business KPIs

| KPI | Direction |
|---|---|
| GMV under management | Up. |
| Net revenue | Up. |
| Gross margin | Expands as average brand GMV rises and automation improves. |
| Churn | Low among activated brands. |
| Expansion | More channels, workflows, and brands per organization. |
| Support cost per brand | Down as onboarding and AI support mature. |

---

## 21. Roadmap Requirements

### Phase 0: Foundation

Must ship:

- Multi-tenant workspace/organization/brand model.
- Core integrations: commerce, ads, payments, logistics.
- Cost setup.
- Metric engine.
- CM waterfall.
- Store Analytics.
- Decision Log schema.
- Integration health.
- Basic Morning Brief.
- India region adapter foundations.
- Security basics and audit log.

Exit criteria:

- A brand can connect stack, see truthful CM2, receive top actions, and log decisions.

### Phase 1: Operator Wedge

Must ship:

- High-frequency Home surface.
- MER/aMER acquisition module.
- RTO/COD/pincode intelligence.
- RFM/RFMC segmentation.
- WhatsApp abandoned cart and COD confirmation workflows.
- Weekly Review.
- First-product repeat cascade.
- Support ticket classification.
- UAE/GCC adapter foundations.

Exit criteria:

- Brain becomes daily operating surface for active brands.
- At least one revenue recovery workflow is live and measured.

### Phase 2: Lifecycle and AI CX

Must ship:

- Shared Audience Builder.
- WhatsApp marketing campaigns.
- Replenishment, winback, VIP retention.
- AI ticket management for top ticket types.
- Support-to-commerce feedback loops.
- Inventory and logistics action queues.
- Creative fatigue and budget recommendations.
- Plan/scenario module.

Exit criteria:

- Brain can show recovered revenue and CM2 across lifecycle/support workflows.

### Phase 3: Agentic Execution

Must ship:

- Owner-configured auto-execute settings.
- Initial auto-execute actions.
- Kill switch.
- Reversal workflows.
- Outcome accuracy dashboard.
- Advanced guardrails.
- Public/internal API surfaces for approved actions.

Exit criteria:

- Brain safely executes low-risk actions with measurable outcomes and low reversal rate.

### Phase 4: Scale and Enterprise

Must ship:

- Portfolio rollups.
- Enterprise data controls.
- Advanced benchmarking.
- Custom integration framework.
- Data residency options.
- Advanced approval matrices.
- Retail-aware extensions where demanded.
- Mature UAE/GCC provider coverage.

Exit criteria:

- Brain supports complex brands, multi-brand groups, agencies, and enterprise requirements without compromising data isolation.

---

## 22. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Brain becomes a dashboard | Critical | Every roadmap item must tie to action, value ledger, and Decision Log. |
| Decision Log not adopted | Critical | Capture Brain actions automatically; make manual logging one-click; show ROI from logged decisions. |
| Stale data causes bad recommendations | High | Data freshness gates; integration health; degraded-mode labels. |
| RTO/COD modeling wrong | High | Region-specific formulas, customer data validation, operator review, outcome feedback. |
| LLM hallucinated numbers | Critical | Deterministic metric engine; LLM only explains approved numbers. |
| WhatsApp overuse hurts trust | High | Frequency caps, consent, offer governance, unsubscribe/opt-out, complaint monitoring. |
| AI support causes bad customer experience | High | Confidence thresholds, human handoff, policy checks, escalation rules. |
| Auto-execute causes financial damage | Critical | Owner opt-in, caps, kill switch, reversibility, audit, auto-revert. |
| Cross-brand data leak | Critical | Strict tenant isolation, aggregated benchmarks only, privacy thresholds. |
| Integration fragility | High | Quality labels, health monitoring, fallback imports, transparent caveats. |
| Unit economics hurt by AI/call/message costs | High | Cost-routed compute, caps, usage dashboards, pass-through where needed. |
| Discount-led lifecycle destroys margin | High | CM2 gating and offer ladder. |

---

## 23. Out of Scope

Brain should not build or promise these in the initial product:

- Manufacturer production planning.
- Wholesale/B2B order management.
- Replacing the brand's full ERP/POS/OMS from day one.
- Cold outbound to non-customers.
- Human workforce scheduling.
- A generic CRM unrelated to commerce actions.
- Offline media planning.
- Long-form video production at scale.
- Fully autonomous high-risk financial actions without Owner controls.
- Per-seat pricing.
- Any feature whose only value is prettier reporting without action or outcome tracking.

---

## 24. Acceptance Criteria for AI Builder Agents

An implementation is acceptable only if:

1. It uses Brain-only naming and positioning.
2. It is tenant-safe and role-aware.
3. It ties every major surface to revenue, profit, risk, time saved, compliance, or decision memory.
4. It writes all recommendations/actions/outcomes into Decision Log.
5. It uses deterministic formulas for metrics.
6. It never lets LLMs invent numbers.
7. It exposes data freshness and caveats.
8. It supports India and UAE/GCC economics through adapters.
9. It treats lifecycle and support as revenue/profit workflows.
10. It provides guardrails before auto-execute.
11. It measures placed revenue, realized revenue, recovered/protected CM2, and fee coverage.
12. It keeps provider names limited to integration targets.
13. It avoids building duplicate primitives per channel.
14. It supports audit, export, deletion, consent, and PII minimization.
15. It can be understood without any other document.

---

## 25. Glossary

| Term | Meaning |
|---|---|
| AICMO | Brain's marketing intelligence agent group. |
| AICOO | Brain's operations intelligence agent group. |
| AICFO | Brain's finance intelligence agent group. |
| aMER | Acquisition Marketing Efficiency Ratio: new customer revenue divided by acquisition ad spend. |
| Brand Fingerprint | Memory representation of a brand's operating patterns. |
| CAC | Customer Acquisition Cost. |
| CM1 | Revenue after product and non-marketing variable costs. |
| CM2 | CM1 after marketing spend. |
| CM3 | CM2 after allocated fixed costs. |
| COD | Cash on Delivery. |
| Decision Log | Immutable record of recommendations, actions, approvals, rejections, reversals, and outcomes. |
| GMV | Gross Merchandise Value under management. |
| MER | Marketing Efficiency Ratio: net revenue divided by total marketing spend. |
| NDR | Non-Delivery Report before shipment becomes RTO. |
| RFM/RFMC | Recency, Frequency, Monetary, and COD-behavior customer segmentation. |
| RTO | Return to Origin: failed delivery returned to seller. |
| Realized Revenue | Revenue that survives cancellation, payment failure, RTO, refund, and settlement leakage. |
| Recovered CM2 | Contribution margin recovered or protected through Brain-driven action. |
| Region Adapter | Localized economic, tax, logistics, payment, consent, calendar, and provider rules. |
| Support-Saved Revenue | Revenue or CM2 preserved through support resolution. |
| True CM2 | CM2 adjusted for delivery, return, COD, refund, and payment leakage. |
| BNPL | Buy Now, Pay Later (e.g., Tabby, Tamara in UAE/GCC). |
| DPDP | India's Digital Personal Data Protection Act 2023 + Rules 2025. |
| PDPL | Personal Data Protection Law (UAE Federal Decree-Law 45/2021; KSA PDPL). |
| TCCCPR / DLT | India's Telecom Commercial Communications Customer Preference Regulations; DLT is the blockchain registration ledger for A2P SMS/voice senders and templates. |
| NCPR / DND | National Customer Preference Register / Do Not Disturb registry for commercial communications. |
| GST 2.0 | India's Sept 2025 GST rationalization to 0/5/18/40 slabs (12% and 28% abolished). |
| Realized/Delivered GMV | GMV that survives cancellation, payment failure, RTO, and refund; the base Brain bills on. |

---

## 26. Final Builder Instruction

Build Brain as the operator's profit command system. Do not stop at showing what happened. Brain must tell the brand what matters, why it matters, what to do, whether Brain can safely do it, and what happened after the action.

The product only compounds if the Decision Log compounds. Treat every recommendation, approval, rejection, lifecycle send, support resolution, auto-execute action, reversal, and outcome as permanent operating memory.
