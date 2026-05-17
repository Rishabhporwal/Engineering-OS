# BRAIN — Consolidated Business Document

> **Document version:** 1.0 (Consolidated)
> **Compiled:** 2026-05-17
> **Audience:** Founders, investors, hiring partners, agency partners, brand operators
> **Companion:** [BRAIN_TECHNICAL.md](BRAIN_TECHNICAL.md) — the engineering blueprint
> **Domain:** brain.pipadacapital.com

---

## 0. About This Document & Conflict Resolution Log

This document is the single source of truth for **Brain's business definition** — vision, positioning, market, customer, pricing, features, partnerships, compliance, and operating model. It supersedes every prior business write-up in this folder.

It is the consolidation of five prior source documents that contradicted each other on important points. Conflicts were resolved using these rules, applied in order:

1. **Most recent date wins** when two docs disagree on the same topic.
2. **Brand name is BRAIN.** Prior docs that named the product "Looqus" describe a precursor codebase audit on the `kushal-app` branch. Those audits are treated as institutional knowledge about what the team has already built and learned, not as a competing product.
3. **The "Sugandh Lok" example is illustrative.** Brain serves many brands. Every reference to "Sugandh Lok," "Kumkumadi Face Oil," "Sandalwood Soap," etc. is an example of how a beauty brand uses Brain; the same shape works for any onboarded brand.
4. **The Brain-Technical-Brief (May 2026) is authoritative on business strategy** — pricing, agents, lifecycle, MCP, partnerships, geographic expansion.
5. **The Brain Platform Complete Spec (March 2026) is authoritative on product features and formulas** — what each report does, how each metric is computed, what the operator sees in the UI.
6. **The Technical Documentation v2.0 (May 13, 2026, PDF + MD) is authoritative on technical realization** — but the business document only references it for the build phases.

### Conflicts resolved (summary)

| # | Topic | Conflict | Resolution |
|---|-------|----------|-----------|
| 1 | Product name | "Looqus" vs "Brain" | **Brain.** Looqus = prior internal name on the existing codebase. |
| 2 | Pricing model | SaaS tiers (Free/Starter/Growth/Enterprise) vs GMV-linked | **GMV-linked.** Founding cohort 0.5% locked; Standard 1.0% under ₹1Cr GMV/month, 0.5% above; Enterprise custom. No per-seat fee ever. |
| 3 | Target customer GMV | ₹1 Cr–₹100 Cr **ARR** vs ₹30L–₹3Cr **GMV/month** vs ₹50L–₹50Cr **GMV/month** vs "enterprise too" (user clarification 2026-05-17) | **Full DTC spectrum.** Brain serves every paying DTC brand from ₹50L/month upwards, with explicit tiering: Small (₹50L–₹3Cr/month), Mid-Market (₹3Cr–₹50Cr/month), Enterprise (₹50Cr+/month or multi-brand holding co). Enterprise tier is **available from launch**, not gated to Phase 4 — though enterprise-only features (private data warehouse, custom model fine-tuning, BYO-VPC) phase in Phase 3/4. DFY uneconomical only below ₹25L/month. |
| 4 | Geographic scope | India-only vs India + GCC + US | **Global product, India-first launch sequence.** Brain is built for DTC brands worldwide from day one — every data model, every region adapter, every currency/timezone primitive is multi-region capable. India + GCC are the Phase 1 launch markets because (a) the founders' network is there, (b) the India-native moat (RTO/COD/GST/Pincode/Festival) is structurally hard for Western tools to backfill, and (c) GCC has clean marketplace APIs. US/EU markets activate in Phase 4 by enabling the existing regional adapter pattern — not by rebuilding the engine. |
| 5 | Role hierarchy | OWNER/ADMIN/MANAGER/ANALYST/VIEWER vs Owner/Operator/Analyst/Agency/Read-only | **Owner / Operator / Analyst / Agency / Read-only** (Brain-Technical-Brief). Existing OWNER→Owner, ADMIN→Operator, MANAGER deprecated, ANALYST→Analyst, VIEWER→Read-only, plus new Agency role. |
| 6 | Scope of platform | Analytics dashboard vs operating system vs revenue execution platform | **AI-native commerce operating system + revenue execution layer.** Brain reports, interprets, decides, and acts. |
| 7 | Build phases | 4 phases × 28 weeks (Statlas parity → India Moat → AI OS → Network Effects) vs Phase 1/2/3/4 (Data → Memory → Agentic → Enterprise) vs Phase 0–4 (Foundation → Wedge → Customer Intel → Scale → Global) | **Master phasing = the Phase 0–4 in the v2.0 Technical Doc.** Other phase models are mapped into it. |
| 8 | Integration scope at launch | Just Shopify/Meta/Google/Shiprocket vs every commerce surface in India and GCC | **Phase 0/1 wedge = Shopify, Meta, Google, Shiprocket, Razorpay.** Wider matrix (Amazon, Flipkart, Myntra, Nykaa, Blinkit, Salla, Zid, Noon, etc.) is Phase 2+. |
| 9 | Lifecycle execution (calling, WhatsApp, email) | Out of scope (analytics only) vs core revenue layer | **In scope.** Lifecycle Layer is what turns Brain from a cost centre into a revenue centre. Outbound first (v1a), inbound second (v1b). |
| 10 | Agentic commerce | Not mentioned vs 30-day auto-execute commitment | **In scope, with kill switch.** 8 initial actions move from human-in-the-loop to auto-execute on confidence ≥ thresholds. |
| 11 | MCP server | Not mentioned vs strategic position above platform MCPs | **In scope.** Brain's MCP is the decision-log layer above Shopify/Meta/Razorpay MCPs. |
| 12 | Brand example | Sugandh Lok everywhere | **Sugandh Lok is illustrative.** Any onboarded brand follows the same product shape. |
| 13 | LLM provider | Claude Sonnet 4 + Opus 4 vs Claude Sonnet 4.6 + Haiku 4.5 vs GPT-4 alternatives | **Claude Sonnet 4.6 + Haiku 4.5 primary;** Haiku for brief drafting / small classification, Sonnet for strategic synthesis. |
| 14 | Daily delivery time | Email 8:00 AM IST vs Morning Brief at 07:15 IST | **Data pull 06:55, vector built 07:00, agents run 07:10, Morning Brief delivered ~07:15 IST. Email digest (longer form) at 08:00 IST.** Two surfaces, one shared content pipeline. |
| 15 | Decision Log vs Marketing Actions Log | Two names for related things | **Decision Log is the unified, immutable record** of every recommendation, response, and outcome. The "Marketing Actions Log" UI from the spec is a brand-facing view onto a subset of Decision Log entries (operator-logged actions). |
| 16 | "Plan Module" vs "Plan" vs forecasting | Same feature, different names | **The Plan Module** — forward P&L forecasting with aMER curve, retention model, and seasonality adjustment. |

The full Section 0 conflict map is intentionally explicit so future contributors can trace every consolidated claim back to its source.

---

## 1. Executive Summary

### 1.1 What Brain Is, In One Line

Brain is the **AI-native commerce operating system for D2C brands worldwide** — it replaces the WhatsApp + Excel + manual chaos that Indian D2C brands run on today (and the disconnected tool sprawl that global DTC operators run on) with a single system that sees the brand's data, learns the brand's history, and acts before the founder has to.

**Built global from line 1, sequenced India-first.** Every data model, region adapter, currency primitive, and timezone helper is multi-region capable from day one. India + GCC are the Phase 1 launch markets; US/EU activate by enabling the existing regional adapter — not by rewriting the engine.

**Built for the full DTC spectrum.** Brain serves the founding-cohort brand at ₹50L/month the same product that serves the multi-brand enterprise holding company at ₹500Cr+/month — same Three-Layer Architecture, same Memory Layer, same Agent Layer, different deployment depth (shared-tenant vs private warehouse) and different pricing rate.

### 1.2 What Brain Is Not

- **Not a dashboard.** Dashboards display data and walk away. Brain interprets, decides, and acts.
- **Not a chatbot.** The natural-language layer is one surface, not the product.
- **Not per-seat SaaS.** Pricing is capped percentage of GMV — adding teammates never costs more.
- **Not a replacement** for WhatsApp, Gmail, or messaging tools. Brain drives into them via API.
- **Not for manufacturers.** Different sales motion, different buyer; out of scope.

### 1.3 The One-Sentence Bet

Brain becomes the **AICMO + AICOO + AICFO** — a marketing chief, an operations chief, and a finance chief in one platform — delivered through a phone Morning Brief and a web app with full operational depth.

### 1.4 Why Now

- D2C operators in India ship today on a stack of disconnected tools (Shopify, Meta, Google, Shiprocket, Razorpay, Klaviyo, GoKwik) plus WhatsApp + Excel. Nothing connects them. The reporting tools that exist (Triple Whale, Northbeam, GobbleCube) hand insights and walk away.
- LLMs are now cheap enough at the small-model tier (Haiku 4.5, GPT-4o-mini) that AI can summarize and decide on hot operational data without breaking unit economics — provided the system runs SQL and ML for everything an LLM doesn't need to do.
- The Indian D2C market has matured to a point where ₹30L/month brands have real margin pressure that better analytics and lifecycle execution can solve. The same operator wants to be at ₹3Cr/month in 6 months and ₹10Cr/month in 18 months.

### 1.5 The Three Architectural Layers (Conceptual)

For a business reader, Brain is built across three layers, each with a distinct job:

| Layer | What It Does | Status |
|-------|---------------|--------|
| **Data Layer** | Normalized signals from Shopify, Meta, Google, Shiprocket, Razorpay (Phase 1). Marketplaces, quick commerce, GCC platforms added in Phase 2+. The prerequisite, not the product. | Live |
| **Memory Layer** | Multi-timescale embeddings of brand performance, customer cohorts, market patterns across the Brain network, and decision-outcome history. **The moat lives here.** | Building |
| **Agentic Layer** | Three executive agents — AICMO, AICOO, AICFO — each with sub-agents. They read context, query memory, and produce daily decisions. Human-in-the-loop in the founding cohort phase; graduating to auto-execute under guardrails. | Next |

---

## 2. Market Context & Competition

### 2.1 The Two Benchmarks We're Reframing

| Tool | Strength | Where They Lose |
|------|----------|----------------|
| **Kleio** ($29/mo) | Simple, cheap, excellent basic profit tracking. | No intelligence. No forecasting. No customer lifecycle. Stops at Level 1–2 analytics. |
| **Statlas** ($499/mo) | Deep analytical rigor; gold standard for DTC analytics. Built by Common Thread Collective for $3B GMV operations. | Bad UI. Zero AI. Zero Indian market support (no RTO, no COD, no GST, no pincode, no festival calendar). |

### 2.2 Brain's Position

> Statlas-depth analytics + beautiful UI + native AI intelligence layer + India-native metrics + revenue execution layer (Lifecycle).

This is defensible because:
- Kleio cannot add depth without rebuilding their stack.
- Statlas cannot add India support without rebuilding 5+ years of pincode/RTO/COD/GST infrastructure that doesn't exist outside India.
- Triple Whale and Northbeam are US-built and stop at Level 2–3 with shallow Level 4 attempts (Moby AI).

### 2.3 The Adjacent Indian Players

| Player | What They Do | Brain's Position |
|--------|--------------|-----------------|
| **GoKwik** | Checkout, RTO Shield, KwikFlo cashflow financing, KwikChat WhatsApp. ~15K Indian D2C brands; ~5 years of pincode-level RTO data. | **Partner, not competitor.** Brain reads RTO Shield signals; Brain operates the intelligence layer above. KwikChat overlap is direct; Brain offers deeper RFM-driven multi-channel routing. |
| **Triple Whale / Northbeam** | US analytics for DTC. | Direct competitor in US Phase 4. India market is uncovered by them. |
| **Wati / AiSensy** | WhatsApp lifecycle automation. | Pragmatic: Brain reads from these initially; offers native execution when Brain's WhatsApp execution is hardened. |
| **Klaviyo / Omnisend / Mailmodo** | Email lifecycle. | Same pattern — read first, replace with native engine in Phase 2 (Section 12). |
| **Razorpay** | Payments + Agent Studio. | Core integration. Partner-level engagement around Agent Studio. |
| **Shiprocket** | Logistics aggregation. | Core integration; partner. |

### 2.4 The Four-Tier Intelligence Pyramid

```
Level 4: PRESCRIPTIVE — "What should I do?"   (Brain target)
         Budget optimizer, anomaly alerts with specific actions

Level 3: PREDICTIVE — "What will happen?"
         LTV forecasting, churn prediction, revenue modeling

Level 2: DIAGNOSTIC — "Why did it happen?"
         Variance decomposition, contribution analysis, cohort attribution

Level 1: DESCRIPTIVE — "What happened?"       (Table stakes — every tool)
         Revenue, ROAS, CAC, AOV, basic P&L
```

- Kleio: L1–2
- Statlas: L2–3
- Triple Whale: L2–3 with shallow L4
- **Brain (target):** Full L4

---

## 3. Target Customer (ICP)

Brain serves **every DTC brand globally**, with three explicit customer tiers. Each tier gets the same core product; the depth of deployment, pricing rate, and certain enterprise-only features differ.

### 3.1 The Three Customer Tiers

#### Tier 1 — Small / Founding-Stage DTC (₹50L–₹3Cr GMV/month)

- **Profile:** 1–3 ad accounts; 5–15 products; CAC/ROAS tracked manually in Excel
- **Common stack:** Shopify + Meta + Google + Shiprocket + Razorpay
- **Their question:** *"Am I profitable? Should I spend more?"*
- **What Brain delivers:** CM1/CM2/CM3 waterfall, MER/aMER, basic cohort view, RTO-adjusted P&L, Morning Brief, daily digest
- **Operating reality:** Founder is the operator. Reads numbers daily but can't act fast enough.

#### Tier 2 — Mid-Market / Scaling DTC (₹3Cr–₹50Cr GMV/month)

- **Profile:** 5–10 ad accounts across Meta/Google/TikTok; 30–100 products; small marketing team
- **Common stack:** Above + Klaviyo + GoKwik + Unicommerce/Eshopbox; sometimes additional marketplaces (Amazon, Flipkart)
- **Their question:** *"Which campaigns to scale? Which products drive LTV? Where is CAC payback?"*
- **What Brain delivers:** Acquisition vs Non-Acquisition split, First Product Cascade, LTV:CAC by segment, Creative Intelligence, Budget Allocation Optimizer, full Lifecycle Layer (calling/WhatsApp/email/SMS/RCS/referral), agentic creative
- **Operating reality:** Operator/Head of Growth lives in the app daily; founder reviews weekly.

#### Tier 3 — Enterprise / Multi-Brand DTC (₹50Cr+ GMV/month, or multi-brand holding co)

- **Profile:** Full marketing team; multi-channel (Meta/Google/YouTube/influencer/affiliate); 100+ SKUs; multi-warehouse; multi-region or multi-brand portfolio
- **Common stack:** All of the above + enterprise tools (Snowflake/BigQuery, custom data warehouses, dedicated DevOps)
- **Their question:** *"Cross-brand portfolio P&L, forecasting, cash flow planning, team-level reporting, inventory orchestration, custom model fine-tuning on our own historical data."*
- **What Brain delivers:** Everything above + The Plan Module + Predictive LTV + Benchmarking + Role-based dashboards + RFM-driven audience automation + 30-day Agentic Commerce + Cross-brand portfolio rollups + Enterprise tier features (private data warehouse / BYO-VPC deployment, custom model fine-tuning on brand's own historical data, dedicated support + integration engineering, EU/US data residency, dedicated partner/CSM)
- **Operating reality:** A portfolio CFO, a brand CMO per brand, multiple marketing managers per channel — each with their own role-tailored dashboard and notification cadence.

### 3.2 Geographic Tiers

| Tier | Markets | Activation |
|------|---------|-----------|
| **India** | All DTC brands operating on Shopify/WooCommerce + Meta + Google + Indian marketplaces | Phase 0–1 (launch market) |
| **GCC** | UAE, KSA D2C brands on Salla/Zid/Noon + Meta/Google/TikTok/Snap | Phase 1 (parallel build) |
| **US/EU** | Mid-market and enterprise DTC currently on Triple Whale, Northbeam, Klaviyo, Polar Analytics | Phase 4 (regional adapter activation) |
| **Other (LATAM, SEA, Africa)** | Future | Phase 5+ (each region needs a RegionAdapter implementation — same engine) |

### 3.3 Out of Scope (Permanently)

- Brands under ₹25L/month equivalent (DFY uneconomical at any tier — even self-serve trial only)
- Pure marketplace sellers without their own storefront (no canonical customer data)
- Manufacturers (different sales motion, different buyer)
- Wholesale or B2B order management
- Per-seat pricing, ever (regardless of customer tier)

### 3.3 What Changes As The Brand Scales

| Stage | Reality | What Brain Provides That Matters Most |
|-------|---------|---------------------------------------|
| **₹30L/month** | 1–3 ad accounts; 5–15 products; tracks CAC/ROAS manually; question is *"Am I profitable? Should I spend more?"* | CM1/CM2/CM3 waterfall, MER, aMER, basic cohort view, RTO-adjusted P&L |
| **₹3Cr/month (~6 months out)** | 5–10 ad accounts across Meta/Google/TikTok; 30–100 products; question is *"Which campaigns to scale? Which products drive LTV? Where is CAC payback?"* | Acquisition vs Non-Acquisition split, First Product Cascade, LTV:CAC by segment, creative intelligence, budget allocation optimizer |
| **₹10Cr/month (~18 months out)** | Full marketing team; multiple channels (Meta/Google/YouTube/influencer/affiliate); question is *"Forecasting, cash flow planning, team reporting, inventory planning"* | The Plan Module, predictive LTV, benchmarking, role-based dashboards, automated alerts, RFM-based audience automation, auto-execute on agentic actions |

Brain is built to serve all three stages. Features for ₹30L must not break as brands scale; data models must support ₹10Cr from day one.

### 3.4 Account Structures (Three Models + Enterprise Variants)

The hierarchy is: **Organisation → Brand (= Workspace) → Store(s) → Users.** Every Brand has its own data store, integrations, team, dashboard, and pricing — fully isolated.

**Model A — Single-Brand Account.** One Organisation, one Brand. Most common at founding-cohort and small-tier stages. Founder is Owner.

**Model B — Multi-Brand Holding Co.** One Organisation, **N Brands fully isolated** from each other. The Organisation owns billing (one invoice covers all Brands); each Brand has its own dashboards, integrations, team, and roles. Cross-brand visibility (e.g., group CFO sees a portfolio rollup) is granted only by **explicit role assignment** — never implicit data sharing.
- *Example structure:* Pipada Capital (Organisation) → Sugandh Lok (Brand) + Bodd Active India (Brand) + Bodd Active UAE (Brand). Each brand has its own Owner, Operators, Analysts. Group CFO can be granted cross-brand read access for the portfolio view.
- **Portfolio rollup features** (Tier 3 / Enterprise): cross-brand P&L, blended MER across the portfolio, brand-level RAG indicators, cross-brand benchmarks within the same Org.

**Model C — Agency Account.** Agency Organisation with scoped read/write across **Client Brands** belonging to different end-customer Organisations. Agency users authenticate against the agency Org, get scoped roles per Client Brand. The **Client Brand always retains Owner control** and can revoke agency access in one click. Cross-brand benchmarks computed in the agency view only expose aggregated, anonymized statistics — never another client's raw data. **Agencies cannot see each other's clients.** Agency billing is separate from Client Brand billing.

**Model D — Enterprise Variant (overlay on Models A or B).** Available at any time, not gated to Phase 4:
- Private data warehouse deployment (brand-controlled cloud / BYO-VPC)
- Custom model fine-tuning on the brand's own historical data (with explicit opt-in)
- Dedicated CSM + integration engineering
- Per-region data residency (EU brands' data in eu-central-1, etc.)
- SOC 2 Type II DPA + Vendor Security Questionnaire support
- Custom SLA + 24/7 priority support
- Custom integrations to brand's internal ERP / data lake
- Higher per-brand LLM cap (or pass-through billing for token cost)
- White-label reporting (for agencies and consulting firms)

Enterprise Variant pricing is custom; see Section 5.

---

## 4. Value Proposition & Product Pillars

Brain solves four problems that no single existing tool solves end-to-end.

### Pillar 1 — Honest, Operator-Grade Analytics

The whole industry runs on **ROAS as a vanity metric** — platform-reported, inflated by attribution windows, double-counted across channels. Brain replaces it with the **MER / aMER framework**:

- **MER** = Total Net Revenue ÷ Total Marketing Spend (all channels combined). Cannot be gamed.
- **aMER** = New Customer Revenue ÷ Acquisition Ad Spend. The surgical metric that isolates whether the acquisition engine works.

Combined with **CM1 / CM2 / CM3 / Net Profit** waterfall, **RTO-adjusted True CM**, and a **goal-setting layer** with RAG indicators on every metric, Brain makes the founder's morning question — *"Am I making money?"* — answerable in 10 seconds.

### Pillar 2 — India-Native Intelligence (The Moat)

No Western tool models any of these correctly. Every Indian D2C brand has them. Brain treats them as first-class:

- **RTO (Return to Origin) as a P&L line.** Forward shipping + return shipping + restocking + COGS damage on every order that's returned. A "25% RTO rate" eats ~30% of headline CM2.
- **COD vs Prepaid economics.** A ₹999 order is worth ~32% more prepaid than COD. Brain quantifies the break-even COD RTO rate and the ROI of prepaid-incentive discounts.
- **Pincode intelligence.** India has ~29,000 active pincodes; RTO ranges from 5% to 45%. Brain ships an India map heatmap and an AI pincode-blacklist recommender.
- **GST-aware revenue.** Indian prices are tax-inclusive (₹999 contains ₹152 of 18% GST). Most brands compute margins on ₹999; Brain strips GST at the first calculation step.
- **Festival seasonality engine.** A forecasting model without Diwali/Navratri/Onam/Dhanteras/Eid/Holi multipliers is wrong 4–5 months of the year.
- **NDR (Non-Delivery Reports) workflow.** Before an order becomes an RTO, it spends time in NDR. Brain tracks NDR resolution rate as a leading indicator.
- **COD handling fees.** ₹25–50 per COD order or 1–2% of order value; Brain factors this into CM2 per order.

### Pillar 3 — Proactive Intelligence (Not Reactive Dashboards)

- **Daily anomaly detection** scans every workspace's metrics overnight (Z-score on 14-day rolling window, with attribution: "Revenue dropped because Meta CPC spiked AND Kumkumadi Face Oil went out of stock"). Surfaces 3 alerts to the founder before they open the app.
- **AI Morning Brief** at ~07:15 IST: top 3 actions, ranked by priority, with Approve / Reject / Edit buttons.
- **Evening pulse** at 18:00 IST: actuals vs forecast, exceptions flagged.
- **Weekly review** Monday 08:00 IST: CM2 vs forecast, channel efficiency, top 3 wins, top 3 leaks.
- **Month-end compound report**: *what did Brain learn about this brand this month?*

### Pillar 4 — Lifecycle as a Revenue Centre

The reframe: Brain itself **performs the revenue-generating outreach**, not just recommends it. This is what makes the GMV-linked pricing model defensible.

- **Outbound (v1a):** abandoned cart recovery, COD confirmation calls, post-delivery follow-up, winback, VIP retention, replenishment, WhatsApp marketing campaigns to RFM segments.
- **Inbound (v1b):** multi-channel inbox (WhatsApp, Instagram DM, email, web chat) with autonomous resolution of top 10 ticket types.

The brand's team approves the strategy; Brain runs the operation.

---

## 5. Pricing & Business Model

### 5.1 Business Model in One Line

Brain charges a **capped percentage of monthly GMV under management.** Brands pay only when Brain is connected to their commerce stack. There is no per-seat fee, no minimum lock-in beyond the founding cohort agreement, and no surcharge for additional users, integrations, storage, or channel features.

### 5.2 Pricing Tiers

| Tier | GMV Band | Rate | Notes |
|------|----------|------|-------|
| **Founding Cohort** | Any GMV | **0.5%** | Locked forever. 20 spots only. In return: 12-month commitment + structured product feedback. |
| **Standard — Early** | Under ₹1Cr GMV/month (or local-currency equivalent) | **1.0%** | Most small-tier brands at launch. |
| **Standard — Growth** | ₹1Cr–₹50Cr GMV/month | **0.5%** | Auto-applies on crossing threshold. Covers most mid-market brands. |
| **Enterprise** | Above ₹50Cr/month, multi-brand holding co (Model B with 3+ Brands), or any brand requiring Enterprise Variant features | **Custom** (typically a flat platform fee + reduced GMV % rate, or a fully flat annual contract for very large customers) | **Available from launch, not gated to Phase 4.** Includes: private data warehouse / BYO-VPC, custom model fine-tuning, dedicated CSM, custom SLA, EU/US data residency, white-label option, custom integrations. Sales-led motion. |

**Multi-Brand Holding Co billing (Model B):**
- Pricing applied **per Brand**, not per Organisation
- Each Brand falls into its own tier based on its individual GMV
- One invoice rolls up all Brands under the Organisation
- Enterprise Variant overlay (Model D) can apply to the entire Org or to specific high-volume Brands

**Agency billing (Model C):**
- Each Client Brand is billed to its end-customer Organisation (not the agency)
- Agency Organisation pays a separate platform fee for agency tooling + multi-client dashboards (flat monthly, tier-based on number of Client Brands managed)
- Agencies retain margin on services delivered on top of Brain, not on Brain's licence fee

### 5.3 What's Included in the GMV Fee

- All analytics, intelligence, and reporting (Pillars 1–3)
- All Lifecycle Layer channels: AI calling, WhatsApp marketing, email engine, SMS, RCS, referral engine
- All agents (AICMO, AICOO, AICFO + sub-agents) and the 30-day agentic commerce auto-execute features
- All integrations in the integration matrix
- All channel feature additions as they ship
- Telephony pass-through and LLM token costs **up to a per-brand monthly cap** (set at onboarding). Above cap, Brain communicates to the brand and discusses upgrade or volume reduction — the system never breaks, it gets quieter.

### 5.4 What's Explicitly Excluded

- Stripe integration fees for billing
- Enterprise-tier custom model training (separate)
- Anything outside the Brain platform (e.g., paid media buy itself, designer salaries)

### 5.5 Why GMV-Linked, Not Per-Seat

- Per-seat pricing punishes the brand for adding team members. Brain is the operator, so adding users should never cost more.
- GMV-linked pricing aligns Brain's revenue with the brand's growth. If Brain is doing its job, the brand grows, and Brain earns more.
- It's self-regulating: small brand pays small fee, large brand pays more but at lower rate.
- Pricing is **GMV-linked, not profit-linked**, because profit attribution to Brain is hard to defend cleanly.

### 5.6 Billing Operational Rules

- **Billing cycle:** monthly, in arrears. GMV computed from connected Shopify and marketplace integrations for the trailing calendar month.
- **Currency:** INR for India brands, AED for UAE brands, USD for international brands. No FX margin.
- **Free trial:** 14 days, full access, no credit card required. Cohort metrics from the trial included in the brand's first month of memory.
- **No success-fee or performance-fee component.**
- **Billing is charged to the Organisation, not the Brand.** One invoice covers all Brands under an Organisation.
- **Account cancellation:** 30-day re-activation grace period → 90-day archival → permanent deletion unless export requested.
- **Brand ownership transfer:** requires Owner action and cooling-off period (prevents disputes and wrongful access).

---

## 6. Customer Journey & Onboarding

### 6.1 The Founder's Path In

| Step | Time | What Happens |
|------|------|--------------|
| **1. Awareness** | — | D2C founder discovers Brain via founder network, content, or partner referral. |
| **2. Fit Call** | 20 min | Look at their numbers together — CAC, CM2, top SKUs, biggest leak. Honest answer on whether Brain is the right fit. |
| **3. Trial Activation** | Day 0 | Owner connects Shopify, Meta, Google, Shiprocket, Razorpay via OAuth. 14-day free trial begins. |
| **4. Data Hydration** | Day 1–3 | Brain pulls historical data back to brand's earliest available records (typically 2–4 hours per integration). |
| **5. Memory Warm-Up** | Day 3 | Initial Brand Fingerprint computed. P40/P80 churn thresholds calculated. RFM scores assigned. |
| **6. First Morning Brief** | Day 4 | First top-3 actions sent to phone. |
| **7. Operating Rhythm** | Day 7–14 | Founder approves/rejects daily. Decision Log starts compounding. First Weekly Review on Day 7 — Owner signs off on metric accuracy. |
| **8. Trial → Paid** | Day 14 | GMV-linked billing begins. |
| **9. Month 1+** | Ongoing | Daily Morning Brief, weekly Monday review, monthly compound report. Memory compounds. |

### 6.2 Cost Data Setup (Critical for CM2 Accuracy)

During onboarding, the Owner enters or uploads:
- **COGS per SKU** (landed cost: product + freight in + customs + warehousing per unit)
- **Fulfilment cost rules** (forward shipping, packaging, COD fees)
- **Variable cost defaults** (payment gateway %, COD handling fee, RTO provisions)
- **Fixed costs** (rent, tooling, salaries — for CM3 → Net Profit)
- **Founder salary** (separate field, OWNER-only)

Without this, CM2 cannot be computed accurately and Brain's first weekly review is unreliable.

### 6.3 Brand Switching (Multi-Brand Users)

A user with access to multiple Brands sees a Brand switcher in the UI. The session rebinds to the selected Brand on switch. The same email can be invited to many Brands with different roles in each.

---

## 7. User Personas & Roles

### 7.1 The Five Personas

| Persona | Primary Concern | What They Use |
|---------|------------------|---------------|
| **Founder / Owner** | *Is the business healthy and growing?* | Morning Brief on phone daily; web app weekly; month-end compound report; owns billing, integrations, team. |
| **Operator / COO / Head of Growth** | *Implementing what Brain recommends and adding operational context.* | Lives in the web app daily. |
| **Performance Marketer / Media Buyer** | *Is advertising working? Where to optimize?* | Meta/Google reports, creative performance, MER/aMER by platform, budget optimizer. |
| **Finance / CFO** | *Cash flow, profitability, forecasting.* | Full CM waterfall, CAC payback, working capital, the Plan Module. |
| **Retention / CRM Manager** | *Customer loyalty, LTV, email performance.* | Net Active Customer report, email/SMS revenue report, RFM distribution, First Product Cascade, at-risk customer count. |
| **Operations / Supply Chain** | *Inventory, logistics, fulfillment quality.* | Inventory dashboard, Shiprocket dashboard, pincode intelligence. |
| **Agency Account Manager** | *Multiple brands; where to intervene first.* | Multi-workspace switcher; scoped per-brand data; never sees other agencies' clients. |
| **Analyst / Marketer (Junior)** | *Read-only reporting; comments add context.* | Read-only across dashboards; can comment but cannot approve/reject. |
| **Investor / Advisor** | *Health check.* | Read-only on a defined subset of metrics; no raw data, no PII, no financials beyond what Owner enables. |

### 7.2 The Five Canonical Roles (Per Brand)

| Role | Typical Persona | Permissions |
|------|------------------|------------|
| **Owner** | Founder | Full read/write. Add/remove users. Approve/reject all agent recommendations. Change billing. Disconnect integrations. Delete the brand. |
| **Operator** | COO / Head of Growth | Full read/write on operational data. Approve/reject agent recommendations. Cannot change billing. Cannot delete the brand. |
| **Analyst** | Internal team member | Read-only on all dashboards and reports. Can comment on recommendations. Cannot approve/reject. Cannot change settings. |
| **Agency** | External agency staff | Scoped read/write as granted by Owner. Always logged. Owner can revoke in one click. |
| **Read-only** | Investor / advisor | Read-only on a defined subset of metrics. No raw data, no PII, no financials beyond what Owner explicitly enables. |

> **Migration note from the existing codebase:** the prior 5-level hierarchy (OWNER, ADMIN, MANAGER, ANALYST, VIEWER) maps to the new model as Owner / Operator / (deprecated) / Analyst / Read-only. Agency role is new. Existing MANAGER assignments should be upgraded to Operator or downgraded to Analyst on a per-brand basis during the migration.

### 7.3 Notification Preferences Per Role

Each user has notification preferences per channel (email, WhatsApp, push, in-app) per alert type. Defaults differ by role:

- **Owner:** all alerts + daily digest 08:00 IST.
- **Media Buyer:** ad-performance alerts only + ad-focused digest at 08:00 IST.
- **Finance:** financial + inventory alerts + weekly summary on Mondays.
- **Retention:** retention alerts (at-risk spike, churn rate change) + Net Active Customer report on Mondays.
- **Operations:** inventory + logistics alerts.
- **Agency:** as configured per Client Brand.

---

## 8. Features & Capabilities

This section organizes Brain's feature set by product area. Mapping to build phases is in Section 12.

### 8.1 Analytics & Reporting

#### 8.1.1 Store Analytics Dashboard
The daily heartbeat. KPI cards for Gross Sales, Net Sales, Discounts, Tax, Orders, COGS, Material Margin, Material Margin %, Other Costs, CM1, AOV, Prepaid Orders %, Meta Ad Spend, Google Ad Spend, Total Ad Spend, CM2, Misc Expenses, CM3, ACOS, Net Profit. Plus the **Marketing Efficiency** section: MER, aMER, ACOS, CAC — each with a goal value and RAG status.

#### 8.1.2 P&L Module
Daily/weekly/monthly/quarterly granularity. Columns for Discounts, Sales, Net Sales, Refunds, Product Refunds, Shipping Refunds, Revenue, Net Revenue, COGS, Variable Costs, Ad Spend, CM1, CM2, CM3, Fixed Costs, Net Profit. Absolute and percentage-of-revenue view modes. CSV/Excel export.

#### 8.1.3 Contribution Margin Waterfall (RTO-adjusted)
Horizontal step-down bar chart showing the full margin chain. Filter for **All / New Customers / Returning Customers** — this is what reveals "your new customers are loss-making; all profit comes from retention" diagnostically. Includes India-specific lines: COD handling fee, RTO cost, GST stripped at top.

#### 8.1.4 Calendar Report
Wide table view. Rows = days. Columns = all key metrics with actual + goal values. Color-coded by RAG status. **Marketing Actions column** with icons (📧 email, 📱 SMS, 🏷️ promo, 📦 launch, 🤝 influencer, 🎨 new creative) on the date they occurred — the overlay turns the calendar into a story, not just numbers. CSV export.

#### 8.1.5 BFCM / Sale Event Hourly Mode
When a Marketing Action is tagged as a Sale Event with start/end datetime, the Calendar Report automatically enables hourly mode. Pace indicator: "₹8.4L of ₹15L goal reached (56%) with 14 hours remaining." Alert if hourly revenue drops >30% from prior hour.

### 8.2 Acquisition & Marketing

#### 8.2.1 MER / aMER / paMER / iROAS
Four marketing-efficiency metrics replacing ROAS as the primary marketing performance metric. Each with goal-setting and RAG status.

#### 8.2.2 Acquisition vs Non-Acquisition Split
For every ad platform, every metric viewable split into Acquisition / Non-Acquisition / Brand campaigns. Reveals what blended numbers hide.

#### 8.2.3 Campaign Classification
Manual classification system where operators tag each Meta/Google campaign as Acquisition / Non-Acquisition / Brand / Unclassified. Drives aMER calculation; unclassified spend is flagged.

#### 8.2.4 Shopping Funnel Metrics in Paid Media
For each ad campaign/ad set/individual ad: Impressions → Clicks → ATC → CI → Purchase, with conversion rates between each stage. Diagnoses WHERE the funnel is leaking.

#### 8.2.5 Video Ad Creative Metrics
Hook Rate (3-Second View Rate), Hold Rate (ThruPlay), 25/50/75/95% completion, Average Watch Time. Diagnostic framework distinguishes weak-hook vs weak-content vs weak-CTA problems.

#### 8.2.6 Creative Intelligence Module
Aggregate analysis across creatives. Identifies winning patterns (UGC vs studio, hook formats, product performance in ads). Creative fatigue detection via EWMA on CTR.

#### 8.2.7 Agentic Creative Intelligence
Confidence-routed decision tree (not just an image generator):
- **High (>0.85)** → auto-generate and ship variant against the current control
- **Medium (0.55–0.85)** → generate, route to Creative Queue for approval
- **Low (0.30–0.55)** → structured brief to human designer
- **Very low (<0.30)** → escalate as strategic question to founder

### 8.3 Customer Intelligence

#### 8.3.1 Net Active Customer Lifecycle Report
5 customer states: **New / Returning / Reactivated / At-Risk / Churned**. Stacked area chart over time, count and revenue views, summary cards (Net Active Customers, At-Risk revenue, Reactivation rate).

#### 8.3.2 Data-Driven Churn Thresholds (P40/P80)
Churn thresholds derived from the brand's actual order data (not arbitrary 90-day window):
- **At-Risk Threshold** = P40 of all order-gap durations
- **Churned Threshold** = P80 of all order-gap durations
Recalculated monthly using trailing 12 months.

#### 8.3.3 First Product → Repeat Purchase Cascade
Groups customers by first product. Shows 2nd / 3rd / 4th+ order rate and average LTV per cohort. Reveals "which products are customer acquisition vehicles vs dead ends." Wedge feature for Phase 1.

#### 8.3.4 Cohort Analysis
Monthly cohort heatmap with CM3, Revenue, Repeat Rate, Repurchase Rate, %, LTV:CAC views. Phase 2: segmentation by channel, first product, discount code.

#### 8.3.5 Lifetime Value (LTV) Engine — BG/NBD + Gamma-Gamma
Probabilistic LTV prediction per customer. Predicts purchases in next 30/90/180/365 days. Uses CM2 (not gross revenue) as monetary value. Requires 6 months of data and 500+ repeat customers minimum.

#### 8.3.6 LTV Drivers Report
Segment analysis: predicted LTV by first product, acquisition channel, discount code used, payment method, city tier. Surfaces "customers who first used FLAT30 have 60% lower LTV — discontinue or restrict."

#### 8.3.7 RFM / RFMC Segmentation
- **R/F/M** scored 1–5 against the brand's own customer base (not industry benchmarks)
- **C (COD behaviour)** scored 1–3 — India-specific 4th dimension
- 11 canonical segments emitted by default: Champions, Loyal, Potential Loyalists, New Customers, Promising, Need Attention, About to Sleep, At Risk, Cannot Lose Them, Hibernating, Lost
- Export to Meta Custom Audience, Google Customer Match, Klaviyo segment tags, CSV

#### 8.3.8 Customer Lifecycle Segmentation
Active / Returning / Lapsed / At-Risk / Churned classification, plus Repurchase Timings, Distributions, First Product Cascade.

### 8.4 India Regional Features (The Moat)

#### 8.4.1 RTO Analytics
- True CM2 (RTO-adjusted) formula
- RTO by Product / Pincode / Channel (Meta vs Google) / Courier / City / State / Tier / Day of Week
- AI Pincode Blacklisting recommendations
- RTO cost model with configurable return shipping, restocking, damage rate

#### 8.4.2 COD vs Prepaid Analytics
- COD vs Prepaid economics formula per order
- Break-even COD RTO Rate calculator
- COD Realization Rate
- Prepaid Conversion Incentive ROI (the 5%-off-for-prepaid math)

#### 8.4.3 Pincode Intelligence
- India map heatmap (state → district → pincode drill-down)
- Per-pincode profitability score
- City tier classification (Tier 1 / 2 / 3)
- AI geo-targeting recommendations

#### 8.4.4 Indian Festival Seasonality Engine
- Pre-loaded festival calendar (Navratri, Dussehra, Karwa Chauth, Dhanteras, Diwali, Christmas/NY, Republic Day Sale, Valentine, Holi, Ugadi/Gudi Padwa, Eid, Independence Day Sale, Onam, Wedding seasons)
- Brand-specific seasonal index calculated from 2+ years of data; industry default before 6 months
- Overlay on all time-series charts and Plan Module forecasts

#### 8.4.5 GST-Aware Revenue
- All revenue calculations strip GST at the first step
- Configurable per-workspace default + per-product override
- Standard slabs pre-loaded (18% beauty premium, 12% ayurvedic, 5% packaged food, etc.)

#### 8.4.6 Shiprocket Deep Integration
- Full order/shipment/NDR data ingestion
- Avg Time to Delivery, First-Attempt Delivery Rate, NDR Rate, NDR Resolution Rate
- Per-courier performance scoring (delivery rate 50% + speed 30% + first-attempt 20%)
- Logistics dashboard, courier comparison table, NDR management queue with AI suggestions

### 8.5 Products & Inventory

#### 8.5.1 Products Module
Pareto Grade (A/B/C by CM1 contribution), CM1, CM1 %, CM1 Total, Sales, Refunds, Revenue, Sold, Refunded, Net Quantity, Return Rate, NC Return Rate, EC Return Rate, Orders, NC Orders, EC Orders, AOV, NC AOV, EC AOV.

#### 8.5.2 Inventory Module
Lead Time, Status (Healthy/Low/Restock Soon/Overstocked/Severely Overstocked/Dead), Quantity, Cost Value, Sell-Through %, Qty sold L30/L90/L180/L360, Qty sold N14LY (next 14 days last year). Predicted stockout date, reorder quantity calculator, safety stock — Phase 2 additions.

#### 8.5.3 Market Basket Analysis
Apriori algorithm finds product combinations bought together more than chance. Bundle recommendations and cross-sell triggers.

### 8.6 Forecasting & Planning

#### 8.6.1 The Plan Module
Forward P&L for the next 1–3 months using three combined models:
1. **aMER Model** — spend → aMER response curve (isotonic regression). Conservative (P25) / Base (P50) / Optimistic (P75) scenarios.
2. **Retention Model** — projects returning revenue from past cohorts using historical repeat-rate-by-month.
3. **Seasonality Adjustment** — brand-specific seasonal index or industry default.

Operator inputs planned acquisition spend per channel, event tags (Diwali Sale Nov 1–5, etc.), and gets a forecast with confidence bands and a weekly breakdown. AI suggests aMER target with commentary on trend direction.

#### 8.6.2 Budget Allocation Optimizer
Estimates spend-response curve per channel (power-law fit). Calculates marginal aMER per channel. Allocates budget greedily to highest marginal aMER channels with 10% min / 60% max per channel. Confidence level indicator based on data volume.

#### 8.6.3 What-If Scenario Builder
"What if I increase Meta budget by ₹2L?" "What if Diwali underperforms — only 2x lift?" Recalculates the full forward P&L.

### 8.7 Goals & Targets

#### 8.7.1 Goal-Setting Infrastructure
Every metric in the platform supports a goal value with RAG indicator:
- Higher-is-better metrics (MER, aMER, CM3%, Revenue): Green ≥95% of goal, Amber 80–95%, Red <80%
- Lower-is-better metrics (CAC, ACOS, RTO Rate): inverted
Goal period: daily, weekly, monthly. Goal type: minimum, maximum, target.

#### 8.7.2 Goals Dashboard
Settings → Goals page: all metrics with current period's goal values, inline editing, period selector.

### 8.8 Marketing Actions Log
Operator log of marketing activities (campaign launches, budget changes, creative tests, promotions, product launches, influencer campaigns, external events). Overlays as icons on Calendar Report and other time-series charts. Feeds Decision Log.

### 8.9 Multiple Revenue Type Definitions

Settings → General → Revenue Definition dropdown:
- Gross Sales
- Net Sales (default)
- **Net Sales Net Tax** — recommended for Indian DTC
- Net Revenue
- Total Sales

Once set, all revenue across the platform uses this definition.

### 8.10 Email / SMS Performance (Klaviyo & Beyond)

Phase 1: Klaviyo integration with campaign and flow performance (delivered, opens, clicks, revenue, unsubscribes, spam). Day-of-week heatmap. Phase 2: native email engine replacing Klaviyo for brands ready to switch.

### 8.11 Notifications

In-app notification center: workspace invite, invite accepted, integration connected, sync completed/failed, data alert, goal reached, system announcement. 13 notification types.

### 8.12 Store Explorer

Raw data access: paginated orders / customers / products tables with filters. For audit and ad-hoc inspection.

---

## 9. Lifecycle & Revenue Execution Layer

This is what turns Brain into a **revenue centre** instead of a cost centre. Every feature here is judged on incremental rupees recovered or retained.

### 9.1 What This Replaces (or Reframes)

- Gorgias-style helpdesk and CX automation
- SagePilot-style agentic CX
- Wati / AiSensy-style WhatsApp lifecycle (overlaps GoKwik's KwikChat)
- Klaviyo / Mailmodo-style email lifecycle
- Telecalling teams and outsourced call-center vendors for COD confirmation, winback, VIP retention, post-delivery NPS
- ReferralCandy / Yotpo Referrals / Friendbuy

Brain does not replace WhatsApp, email, or telephony themselves — it drives into them via API.

### 9.2 Outbound (v1a — build first)

| Workflow | What It Does | CM2 Impact |
|----------|--------------|-----------|
| **Abandoned Cart Recovery** | Cart abandoned >30 min → RFM-segmented response (call for high-value, WhatsApp for mid, email for low) | High |
| **COD Confirmation Calls** | Every COD order: call within 15 min to confirm and convert to prepaid where possible | Direct CM2 lift, ~3–5 points per converted order |
| **Post-Delivery Follow-Up** | 3-day and 7-day touchpoints: NPS, review request, replenishment cue | Retention |
| **Winback Campaigns** | Dormant customers (typically 60+ days inactive in cohort) re-engaged via RFM-triggered audience | Revenue recovery |
| **VIP Retention** | Top decile of LTV: human-style outreach on defined cadence | Retention of best customers |
| **Replenishment / Repeat Purchase** | For consumable categories: trigger at modelled depletion point per SKU | Repeat rate |
| **WhatsApp Marketing Campaigns** | Structured broadcasts to RFM segments with two-way conversational follow-up | Channel revenue |

### 9.3 Inbound (v1b — build second)

- **Multi-channel inbox**: WhatsApp, Instagram DM, email, web chat unified
- **Autonomous resolution** for top 10 ticket types: order status, return initiation, address change, refund status, product info, COD-to-prepaid conversion, cancellation, replacement, missing item, delivery delay
- **Human escalation** when confidence drops below threshold or customer requests it
- Every ticket logs back into customer profile and Decision Log

### 9.4 RFM-Triggered Audience Builder (Architectural Primitive)

One engineering object, consumed by every channel:
- Pick an RFM segment (or build custom with filters: SKU, channel, geography, AOV band, last product purchased, etc.)
- Brain returns audience size, modelled response rate, projected revenue recovery, recommended channel mix
- **One click** triggers simultaneous push to call queue, WhatsApp queue, email queue, ad-platform custom audience sync
- Channel routing per customer: high-value → call, mid-value → WhatsApp, low-value → email

This is why Brain bundles all channels into one GMV % fee — the marginal cost of one more channel on top of the shared audience layer is small; marginal recovered revenue per brand is large.

### 9.5 Referral Engine (Loyal-Fan Amplification)

Sits inside the Lifecycle Layer; consumes RFM segment memory.
- Auto-enrolls Champions + Loyal as advocates
- Generates unique trackable links/codes per advocate
- Two-sided incentive (advocate cashback/credit/free product after N referrals; referred customer discount/free add-on)
- Tier mechanics: first 3 referrals at base rate, 4–10 boosted, 10+ premium
- Server-side attribution (first-party cookie + server record)
- Fraud detection: self-referral block, circular ring detection, velocity caps, cohort quality check, manual review queue
- Replaces: ReferralCandy, Yotpo Referrals, Friendbuy

### 9.6 AI Calling Architecture (Path Decision Open)

Three paths documented; engineering team owns the selection (detail in Technical Doc):

| Path | When | Pros | Cons |
|------|------|------|------|
| **A — Partner Indian voice AI vendor** (Bolna, Smallest.ai) | Months 1–6 | 4–6 week time-to-market; Indian regional language coverage; vendor handles TRAI DLT compliance | Vendor stability dependency; per-minute margins squeezed |
| **B — Partner global voice AI** (Vapi, Retell, ElevenLabs, Bland) | Months 1–6 | Best voice quality + latency; mature SDKs | Pricier per-minute; requires Indian SIP trunk (Plivo/Exotel) |
| **C — Build Native** | Months 6+ if volume crosses ~5K calls/day | Full control over voice/latency/pricing; long-term margin protection | 4–6 month build; voice-agent engineer hire needed |

Default heuristic: partner months 1–6, parallel-build months 6–12 if volume justifies, migrate primary traffic to native stack months 12+ while keeping partner as overflow.

### 9.7 Call Compliance (India — Non-Negotiable)

- **Calling hours:** 09:00–21:00 IST. Outside-window calls blocked at queue level.
- **DND check:** every number against brand's opt-out list AND TRAI's NCPR. Two-layer block.
- **Consent:** customer must have opted-in in brand storefront.
- **Disclosure:** every AI call opens with clear disclosure that caller is automated assistant.
- **Recording consent** at call start; declined → call proceeds, no audio retained.
- **DLT registration** per brand for every template message after a call.
- **Frequency cap:** max one Brain-driven call per customer per 48 hours, override only for VIP segments with Owner approval.

### 9.8 Success Metrics for Lifecycle Layer

Revenue-aligned (the metrics that matter):
- **Recovered revenue per brand per month** — north-star metric for this layer
- **Recovered revenue / Brain GMV fee ratio** — target >3× by month 3, >5× by month 6 with Phase 2 channels live
- **COD-to-prepaid conversion lift** — target >15% over baseline
- **Winback response rate** — target >8% within 14 days

Operational:
- **Call answer rate** — target >35% (industry baseline ~25%)
- **Ticket resolution rate (autonomous)** — target >60% by month 6, >75% by month 12
- **First-response time on inbound** — <60s WhatsApp, <2 min email

Compliance & trust:
- **DND violations:** zero. Any violation is a P0 incident.
- **Out-of-hours calls:** zero.
- **Customer complaints per 1,000 outreach attempts:** <0.5

### 9.9 What This Section Does Not Cover

- Outbound cold acquisition (calling non-customers) — out of scope for v1
- Live human agent management (HR for the human team) — out of scope
- Outbound to non-Indian numbers in v1 — UAE/US come with geo expansion
- Voice cloning of the founder — technically available, disabled by default; only enabled with explicit Owner approval and hard-coded disclosure

---

## 10. Agentic Commerce: The 30-Day Auto-Execute Commitment

### 10.1 Definition: Brand-Facing, Not Customer-Facing

Brain's agentic commerce is Brain agents acting autonomously **on behalf of the brand**, not on behalf of the customer. The distinction matters:

- **Customer-facing agentic commerce** (Razorpay Agent Studio model) — AI agents transact for customers. **Not in 30-day scope.** May surface in future phases as MCP server exposing brand catalog to external agents (ChatGPT, Perplexity, Claude).
- **Brand-facing agentic commerce** — Brain agents take operational actions in brand's accounts and systems (pause ad, reorder SKU, issue refund, transfer inventory) without waiting for human approval, within explicit guardrails. **This is the 30-day commitment.**

### 10.2 The 30-Day Deliverable: 8 Initial Auto-Execute Actions

| Action | Owning Agent | Confidence Threshold | Reversibility |
|--------|--------------|---------------------|---------------|
| Pause an underperforming ad | AICMO | >0.90 | Fully reversible |
| Reduce daily budget on fatiguing campaign by 20% | AICMO | >0.85 | Fully reversible |
| Issue full refund on verified return | AICOO | >0.95 | Irreversible (cash leaves bank) |
| Replace defective item under warranty | AICOO | >0.90 | Partially reversible (inventory) |
| Reorder inventory via automated PO to vendor | AICOO | >0.90 | Partially reversible (cancel PO) |
| Transfer inventory between warehouses | AICOO | >0.85 | Reversible (reverse transfer) |
| Apply discount code to abandoned-cart customer | AICMO | >0.80 | Reversible (revoke code) |
| Switch courier for a region with elevated RTO | AICOO | >0.85 | Partially reversible |

Each action lives inside its agent's existing recommendation logic. The 30-day work hardens the execution path, not new agent intelligence.

### 10.3 Guardrails (Mandatory, Hard-Coded, Visible to Brand)

- **Confidence gating** — below threshold, action falls back to human-in-the-loop. Per-brand tunable upward, never below default.
- **Per-action spend caps** — daily budget per agent (e.g., AICMO can auto-pause up to 10 ads/day; AICOO can auto-issue refunds up to ₹50,000 aggregate/day).
- **The kill switch** — single button in UI: "Pause all auto-execute." Reverts all agents to recommend-only mode within 60 seconds.
- **Auto-revert trigger** — if any agent's outcome accuracy drops below threshold over trailing 7 days, that agent auto-reverts to recommend-only, Owner notified.
- **Audit & reversal** — every action logs to immutable Auto-Execute Log with agent, action, parameters, confidence score, time, 7-day and 30-day outcome, reversal status. Owner can reverse any reversible action in one click.
- **Compliance boundaries** — no action that issues cash beyond daily refund cap; no new financial liability (new PO above threshold, new vendor contract); no action touching customer PII not pre-authorised; no action against EU/CA customers conflicting with stored consent.

### 10.4 30-Day Build Plan

- **Week 1: Foundation** — Auto-Execute Log table, confidence scoring framework, spend caps, kill switch, Owner consent flow at onboarding.
- **Week 2: First Three Actions Live** — Pause ad, reduce budget, apply discount (lowest-risk, fully reversible). 2 founding-cohort brands with full Owner consent + daily review.
- **Week 3: Next Three Actions** — Transfer inventory, switch courier, replace defective item. 4 brands.
- **Week 4: Final Two + Hardening** — Issue refund (highest-risk, irreversible) + automated PO reorder. Cross-brand outcome accuracy review; stress-test kill switch; ship docs + Owner training + escalation runbook.

### 10.5 Success Metrics

- **Auto-execute actions per day** — target >50 per active brand by end of week 4
- **Outcome accuracy** — % of actions with 7-day/30-day outcome matching predicted direction. Target >80%.
- **Reversal rate** — % reversed by Owner within 24 hours. Target <8%; above 15% means thresholds mis-calibrated.
- **Time saved per brand per week** — target >5 hours of founder time freed
- **Recovered revenue from auto-execute** — net incremental CM2 vs counterfactual baseline

### 10.6 What 30 Days Does Not Cover

- Customer-facing agentic commerce (Razorpay Agent Studio, MCP servers for external AI agents) — future phase
- Multi-agent action chains ("detect stockout → reorder → adjust ad spend → notify CS") — Phase 2 of agentic
- Auto-execute on competitor/external systems — out of scope
- Voice/text commands triggering auto-execute ("hey Brain, pause Meta") — out of scope; auto-execute is system-initiated

---

## 11. MCP Server Surface: The Decision Layer Above Every Other MCP

### 11.1 The Strategic Position

Model Context Protocol (MCP) is becoming the default standard for AI agents to access external systems. Meta, Shopify, Razorpay, Stripe, Salesforce, Google — all are shipping MCP surfaces. Each exposes its own data and actions to AI agents like Claude, ChatGPT, Perplexity.

**Every platform MCP exposes its own surface — none have the decision log.** Shopify's MCP knows the brand's orders. Meta's MCP knows ad spend. Razorpay's MCP knows payments. **None of them know which action was recommended, which was approved, what the outcome was, or which pattern is emerging across all of them together.**

Brain's MCP server is the **decision-log-and-context layer that sits above every other MCP.** Brain becomes the layer that makes other MCPs intelligent.

### 11.2 What Brain's MCP Surface Exposes

**Read surface:**
- `brand_fingerprint` — multi-timescale embedding of brand performance
- `decision_log` — every recommendation, response, 7-day and 30-day outcome (unique to Brain)
- `condition_outcome_pairs` — historical conditions matched against historical outcomes
- `rfm_segments` — live RFM segmentation
- `recovered_revenue_ledger` — attribution of incremental revenue to Brain-driven actions
- `creative_fingerprint` — high-performing creative patterns + decay curves
- `cross_brand_benchmarks` — aggregated, anonymized network statistics

**Action surface:**
- `trigger_audience` — build audience by RFM filter / custom criteria and push to channels
- `propose_action` — ask Brain's agents to evaluate hypothetical action; returns confidence score + projected outcome before executing
- `query_memory` — free-form natural-language query against brand data with prose + underlying numbers
- `log_external_decision` — write into Decision Log from external context (decisions made outside Brain that should still be tracked for outcome attribution)

### 11.3 How Teams Use Brain Through Other AI Surfaces

- **Founder in Claude:** "What's my CM2 trajectory the last 90 days, and which agent recommendations drove the biggest wins?" → Claude calls Brain's MCP, pulls `decision_log` + `brand_fingerprint`, answers with actual numbers.
- **Marketing lead in ChatGPT:** "Build me an audience of Champions in Maharashtra who haven't bought in 30 days, and propose the right outreach." → ChatGPT calls `trigger_audience` + `propose_action`.
- **CFO in their finance tool:** "Projected cashflow next 30 days based on current operations and pending recommendations?" → Tool composes answer using `condition_outcome_pairs` + `rfm_segments`.

This is **anti-lock-in by design.** Brand teams aren't forced to live in Brain's UI to get Brain's value. And it's why brands stay: the intelligence is portable, but the data and decision history are not — they live in Brain.

### 11.4 Build Sequence

- **Months 1–3:** Internal MCP first. Audience Builder, agents, Lifecycle execution speak MCP to each other. Establishes schema and tooling without external compliance burden.
- **Months 3–6:** External read-only MCP. Brands' AI tools can query `brand_fingerprint`, `decision_log`, `rfm_segments`, `cross_brand_benchmarks`.
- **Months 6–9:** External action MCP. `trigger_audience` and `propose_action` callable from external AI surfaces with explicit per-action consent.
- **Months 9–12:** Bidirectional with platform MCPs (Shopify, Meta, Razorpay). Brain orchestrates calls to other MCPs on behalf of brands' AI agents, combining cross-platform context with Brain's decision log.

---

## 12. Partnerships & Ecosystem

### 12.1 GoKwik — Partner, Not Competitor

GoKwik is the closest reference point in the Indian D2C operator-tools landscape. GoKwik operates the **checkout, RTO, and cashflow** layer; Brain operates the **operating intelligence layer above it.** Complementary, not competitive, when the layers are kept distinct.

| GoKwik Product | What It Does | Brain's Position |
|----------------|--------------|------------------|
| **Smart Checkout** | Replaces Shopify checkout with higher-conversion flow | Brain doesn't build this; integrates with brand's existing checkout (Shopify native, GoKwik Smart Checkout, Razorpay Magic Checkout) |
| **RTO Shield** | Real-time RTO risk scoring at checkout using GoKwik's pincode-level RTO database (5+ years, ~15K brands) | Brain ingests RTO Shield scores via partnership API; does not rebuild the underlying database |
| **KwikFlo Cashflow** | Working capital + revenue-based financing using GMV as underwriting signal | Brain co-positions for the capital layer later; CM2-correct P&L is complementary signal |
| **KwikChat** | WhatsApp commerce (abandoned cart, order updates, COD via WhatsApp) | **Direct overlap.** Brain's Lifecycle Layer does this with deeper RFM intelligence + multi-channel routing. Per-brand decision: use both, or Brain alone if WhatsApp routing is sufficient. |

### 12.2 The Integration Shape

Brain treats GoKwik (and equivalents) as data sources and execution rails, like Razorpay or Shiprocket:
- **Read:** pull conversion data, RTO scores, cashflow signals, KwikChat outcomes into Brain's data layer
- **Write:** push actions to GoKwik APIs when Brain's agents decide (e.g., disable COD on a flagged pincode via the GoKwik checkout API)
- **No data duplication:** Brain stores what it needs for intelligence; source-of-truth for checkout/payment/RTO stays with GoKwik

### 12.3 The General Rule for Partner vs Build

- **Build it when:** it sits in the operating intelligence layer (Brain's core competence), feeds back into Memory Layer compounding effect, or no acceptable partner exists.
- **Partner when:** it sits in an adjacent layer (checkout, payment, logistics, fulfilment, capital) where the partner has structural moat Brain cannot rebuild economically.
- **Read and route around** when: it occupies a layer where Brain may eventually compete but the partner has too much current adoption to ignore (Klaviyo for email today, Wati for WhatsApp today).

### 12.4 Other Partner-Layer Players to Engage Similarly

- **Razorpay** (payments + agentic execution) — core integration; partner-level around Agent Studio
- **Cashfree, PayU** (payments) — Phase 1 integrations
- **Shiprocket** (logistics aggregator) — core integration; partner
- **Delhivery, Bluedart** (logistics direct) — Phase 2 direct integrations
- **Unicommerce, Eshopbox** (OMS) — Phase 1; many brands sit on these
- **Klaviyo, Mailmodo** (email) — read first, offer native engine alternative when ready
- **Wati, AiSensy** (WhatsApp) — same pattern

### 12.5 Platform Partner Status (Why It Matters)

Being officially recognized changes Brain's economics, distribution, technical access, and credibility. It's a business workstream that engineering supports; founders own the relationship.

#### Meta Business Partner Program
- **Tier 1 — Meta Business Partner (entry):** baseline managed ad spend, Meta Blueprint certifications, demonstrated client base. **Apply Phase 1, achieve Phase 2 (months 12–24).**
- **Tier 2 — Premier:** higher thresholds, dedicated partner manager.
- **Tier 3 — Strategic/Marketing Partner:** reserved for largest tools globally.

#### Shopify Plus Technology Partner
The Brain Shopify App is a **product**, not an integration. It has its own user base, onboarding, App Store reviews. Someone owns the app's UX, App Store reviews, version cadence, uninstall rate.
- **Shopify App Partner (entry)** — Phase 1
- **Shopify Plus Technology Partner** — Phase 2 once documented Plus merchants exist
- **Shopify Plus Certified App** — highest tier, Phase 3

#### Other Platform Programs
- **Google Premier Partner** (Google Ads) — same shape as Meta
- **Amazon Ads Partner Network** — once Brain manages Amazon ad spend
- **Razorpay / Cashfree / PayU Partner Networks** — co-marketing for payment integrations
- **Salla and Zid Partner Programs** (Saudi GCC) — smaller programs, faster onboarding, target Phase 1
- **Noon Seller Partner Program** (UAE/KSA marketplace)

### 12.6 Compliance & Trust Marks

- **SOC 2 Type II:** kicked off Phase 1; certification 9–12 months from kick-off
- **ISO 27001:** pursued after SOC 2
- **Meta Tech Provider Designation:** required for handling Meta's customer data
- **Shopify Built for Shopify badge**

---

## 13. Geographic Plan

**Brain is a global product from day one.** The engine is region-agnostic; every region-specific economic (tax model, payment fees, logistics, return culture, festival seasonality, postal/pincode system, currency formatting, language) lives behind a `RegionAdapter` interface. Adding a region = implementing the interface, not rewriting the product. This is what makes the global ambition real rather than aspirational.

The phase plan below is **launch sequencing**, not product gating. Enterprise customers in any region with a working RegionAdapter can be onboarded at any phase via the sales-led motion.

### 13.1 Launch Sequence

| Sequence | Markets | Activation Phase | Notes |
|-----------|---------|-----------|-------|
| **Launch (Phase 0–1)** | India | Weeks 1–12 | INR billing, Asia/Kolkata timezone default, India RegionAdapter (RTO/COD/GST/Pincode/Festival) live. Founding cohort + first 50 brands here. |
| **Parallel (Phase 1)** | GCC (UAE, KSA) | Weeks 5–22 | AED + SAR billing, Asia/Dubai + Asia/Riyadh timezones, GCC RegionAdapter (VAT 5%, Ramadan/Eid, GCC payment + logistics). Salla, Zid, Noon, Tabby, Tamara, Aramex, DHL, SMSA. |
| **Expansion (Phase 4)** | US, EU (UK + Germany + France first) | Weeks 37+ | USD/EUR billing, multi-timezone, US/EU RegionAdapter (state-level sales tax / per-country VAT, BFCM seasonality, USPS/UPS/FedEx/DHL, Stripe/ACH payments). GDPR data residency in eu-central-1. SOC 2 Type II required. |
| **Future (Phase 5+)** | LATAM (Brazil, Mexico), SEA (Indonesia, Vietnam, Thailand), Africa (Nigeria, South Africa, Egypt) | TBD | Each new region = one RegionAdapter implementation. Order of activation driven by enterprise customer demand + partner relationships. |

### 13.2 Why India + GCC First, US/EU Later

- **India:** Founder network + market depth; India-native moat (RTO/COD/GST/Pincode/Festival) is structurally hard for Western tools to backfill. Once established here, no Western tool can credibly compete in India.
- **GCC:** Indian-style D2C operating model translates well; same Shopify/Meta/Google stack; marketplace platforms (Salla/Zid/Noon) have clean APIs; volume concentrated in fewer brands at higher GMV — better unit economics during early scaling.
- **US/EU later:** Crowded competitive landscape (Triple Whale, Northbeam, Polar, Klaviyo) — best entered when Brain has differentiated moat (Memory Layer + Decision Log + India-validated agentic commerce track record) rather than as the 12th US analytics tool.

### 13.3 Global from Day One — What This Means in Practice

- Every database table has `workspace_id` + region-aware tax/currency fields
- Every metric formula is currency-agnostic (`amount: Decimal` with `currency: ISO 4217 code`)
- Every report renders in the workspace's home currency + locale (₹1,23,456 vs $123,456 vs €123.456 vs د.إ 123,456.78)
- Every notification template supports multi-language rendering (English + the workspace's primary local language)
- Festival/event calendars are plug-in (India calendar today, Ramadan/Eid for GCC today, BFCM for US in Phase 4)
- Multi-region deployment ready (Phase 4 activation switches on the secondary region; primary region per workspace via `core.workspaces.home_region`)

### 13.4 Retail OS (Future Bet)

Apply the AICMO + AICOO + AICFO model to physical retail (POS, ERP, CRM/loyalty as data sources). Piloted in UAE first because GCC retail-meets-D2C is a more mature commercial pattern. Phase 5+ scope.

### 13.5 Capital Products (Future Bet)

Inventory-backed lending and revenue-based financing pilots, built on Brain's CM2-correct P&L data. Phase 5+.

---

## 14. Compliance, Privacy & Trust

### 14.1 Posture by Regulation

| Regulation | Posture |
|-----------|---------|
| **DPDP Act 2023 (India)** | Brain operates as **Data Processor** on behalf of brands (who are Data Fiduciaries). DPA available to all paying customers. |
| **GDPR (EU)** | For brands with EU customers: Standard Contractual Clauses + sub-processor list. Data residency option (EU region) on enterprise tier. |
| **CCPA (California)** | Same as GDPR for California-resident customers. |

### 14.2 What Brain Stores (and What It Doesn't)

**Stores:**
| Data Type | What | Retention |
|-----------|------|-----------|
| Order data | Order ID, line items, amounts, status, timestamps, ship-to pincode (not full address) | Active brand life + 90 days |
| Customer identifiers | Hashed email and hashed phone. Plain only if brand explicitly enables for outreach | Active brand life + 90 days |
| Ad platform data | Campaign, ad-set, ad, creative, spend, impressions, clicks, conversions | Active brand life + 90 days |
| Logistics data | Order ID, courier, status, RTO flag, timestamps. No customer address | Active brand life + 90 days |
| Payment data | Payment method, settlement timestamps, fees. No card numbers, no UPI IDs | Active brand life + 90 days |
| Decision history | Every Brain recommendation, user action, 7-day/30-day outcome | Active brand life — no auto-delete (**this is the moat**) |

**Never stores:**
- Card numbers, CVVs, full UPI IDs, full bank account numbers
- Full customer addresses (only ship-to pincode retained)
- Customer national IDs (PAN, Aadhaar, SSN, passport) — even if Shopify exposes in customer notes
- Plain-text passwords (Supabase Auth with hashed credentials)
- Health data, biometric data, or any other special-category data

### 14.3 Customer Consent Workflows

- Brain does **not** collect end-customer consent directly. Consent is the brand's responsibility, captured in the storefront and CRM.
- Brain expects every ingested customer record to carry `consent_status`: `opted_in`, `opted_out`, `unknown`, `withdrawn`.
- Customers with `opted_out` or `withdrawn` are excluded from any agent-driven outreach. They remain in cohort analytics in aggregated, anonymized form only.
- Brand Owners can mass-import consent state from existing CRM or Shopify tags during onboarding.

### 14.4 Right to Deletion (DSR)

- Customer asks the brand to delete their data → brand triggers deletion request inside Brain via Owner UI or API
- Brain hard-deletes the customer's identifying records within 30 days
- Aggregated metrics derived from that customer's orders are retained (cannot be re-linked to the individual)
- Deletion logged in audit log

### 14.5 Brand-Level Data Export & Account Closure

- Owner can request full data export at any time. Delivered as structured ZIP within 7 days.
- Account closure: 30-day grace → 90-day archival → permanent deletion (Owner can fast-track to immediate)

### 14.6 Technical Compliance

- **Encryption:** TLS 1.2+ in transit; AES-256 at rest. Per-brand encryption key for sensitive integrations.
- **PII in logs:** never. PII hashed in any log output.
- **Brain does not train its models on any single brand's data** without explicit, written opt-in. Cross-brand patterns derived only from aggregated, anonymized statistics.

### 14.7 Multi-Brand Data Isolation Rules

- Every database row tagged with `brand_id` (workspace_id)
- Every query filtered by `brand_id` at the database access layer
- **Row-Level Security (RLS) enabled on Supabase for every table** containing brand data — second line of defence after application-level filtering
- Cross-brand benchmarks computed in a separate analytics pipeline emitting only aggregated, anonymized statistics. Raw rows never leave the brand's data partition.
- API keys, OAuth tokens, integration credentials stored encrypted at rest with per-brand keys
- Every approve/reject, settings change, integration change logged with user, timestamp, IP. Owner can export the log.

---

## 15. Reporting & Operating Rhythm

### 15.1 Daily Reports

#### Morning Brief — Phone (~07:15 IST)
The daily heartbeat. **Three actions per morning**, ranked by priority. Each has: one-line summary, data backing it, recommended action, Approve / Reject / Edit buttons. Sent to phone.

#### Daily Email Digest — 08:00 IST
HTML email (responsive, mobile-first). Six sections:
1. **Header:** `🧠 Brain | {Brand} | ₹{revenue} | MER {x}x | {alert_count} Alert(s)`
2. **Yesterday's Snapshot:** Revenue, CM3, MER, aMER, New Customers, CAC — each with 7-day avg, change, RAG status
3. **Alerts** (max 5, ordered by severity) — severity emoji + one-line description + one-line recommended action
4. **Monthly Progress** (from Day 2): MTD revenue vs goal, pace indicator, days remaining, revenue needed per day
5. **Top Movers** (optional): top campaign by ROAS, top product by CM1, unusual refund spike
6. **CTA:** "View Full Report →" link to brain.pipadacapital.com

#### Daily WhatsApp Digest (Condensed)
```
🧠 Brain | {Brand} | {Date}
Yesterday: ₹{revenue} | MER {x}x | aMER {x}x
New Customers: {nc} | CAC: ₹{cac}
🚨 Alerts:
1. {short_alert_1}
2. {short_alert_2}
This month: ₹{mtd}L / ₹{goal}L ({pct}%)
{pace_emoji} {pace_description}
brain.pipadacapital.com
```

#### Evening Pulse — 18:00 IST
Day's actuals vs forecast, exceptions flagged.

### 15.2 Weekly Reports

#### Weekly Review — Monday 08:00 IST
On the web app. CM2 vs forecast, channel efficiency vs benchmark, top 3 wins, top 3 leaks. Signed off by Owner.

#### Weekly Performance Email — Monday
Covers Mon-Sun. Sections:
1. Week summary card (Revenue/CM3/Ad Spend/MER/aMER/New Customers/CAC vs prior week + goals + RAG)
2. Goal Performance Table (every goal set for the week)
3. P&L Waterfall (weekly: CM1 → CM2 → CM3)
4. Top 5 Products by CM1
5. Top 3 Campaigns by aMER
6. Customer Health (Net Active Customers, At-Risk count, Churned this week, Reactivated)
7. **3 AI-generated actions for next week** — specific, actionable, with supporting data

### 15.3 Monthly Reports

#### Month-End Compound Report — Day 1 of Month
**What did Brain learn about this brand this month?** Which conditions led to which outcomes. Which patterns are emerging. Which recommendations worked and which didn't.

#### Monthly P&L Statement
CM-waterfall view: Net Revenue → COGS → CM1 → variable costs → CM2 → marketing → CM3 → opex → operating profit.

### 15.4 On-Demand Reports

- **Cohort report:** acquisition cohorts with retention curves and LTV trajectories
- **SKU report:** per-SKU CM2, velocity, days of cover
- **Channel report:** per-channel CAC, LTV, CM2 contribution
- **RTO report:** pincode, courier, AOV-band breakdowns

### 15.5 Natural Language Query

"Why did CM2 drop on Tuesday?" "What happened to my COD conversion in Maharashtra?" Brain converts to SQL, runs against brand data, returns prose answer plus underlying numbers.

### 15.6 Real-Time Monitoring

#### Standard Mode (Default Dashboard)
Yesterday's data + current-day running total with pacing indicator using historical intraday distribution.

#### Sale Event Mode
When a Marketing Action is tagged as a Sale Event, dashboard switches to hourly granularity with running totals + pace vs goal, "Revenue left to goal" countdown, alert if hourly revenue drops >30% from prior hour.

---

## 16. Internal Operations (Brain Team)

### 16.1 Founding-Cohort Operational Cadence

- **Per-brand founder check-in:** weekly during founding cohort. Brain PM reviews the brand's recommendations, outcomes, feedback.
- **Quality review of agent outputs:** daily during founding cohort. Each agent's recommendations sampled and reviewed before showing to brands.
- **Memory audit:** monthly. Verify Decision Log, Brand Fingerprint, benchmark database growing as expected.
- **Integration health check:** continuous. Each integration emits a health signal. If a brand's integration breaks, brand AND Brain team notified within 1 hour.

### 16.2 Operating Principles

- **Make requirements less dumb first.** Delete what doesn't need to exist. Simplify what does. Then automate.
- **If SQL can solve it, never reach for ML.** If ML can solve it, never reach for an LLM. Cost compounds.
- **Memory is the moat.** Every architectural decision should preserve and extend the brand's decision-outcome history.
- **Data isolation is non-negotiable.**
- **Human-in-the-loop until agent's outcome accuracy crosses brand-specific threshold.** Then graduate to autonomous, with kill switch.

### 16.3 The Three Things Engineering Should Optimize For

1. **Data freshness and pipeline reliability** — single biggest source of failed recommendations is stale data.
2. **Memory layer integrity** — Decision Log and Brand Fingerprint must never be corrupted, lost, or mis-attributed. **This is the moat.**
3. **Cost discipline** — LLM cost per brand can run away fast. Every agent and endpoint has a cost budget and an alarm.

### 16.4 What Engineering Should Push Back On

- Any feature using an LLM where SQL or ML would do
- Any request to mix raw cross-brand data into a single query without going through the aggregation layer
- Any feature without first defining success metric and cost budget
- Any request breaking the rule: **pricing is per Brand, never per User**

### 16.5 Streamlining: The Single-Primitive Rule

Every cross-cutting concern is built once and consumed by every channel, every agent, every workflow:
- **Audience** — one builder consumed by call, WhatsApp, email, SMS, RCS, ad-platform sync, referral engine
- **Decision Log** — one log; every agent writes to it; every outcome attributes back to it
- **Consent** — one consent model per customer per brand with per-channel granularity
- **Notification framework** — one delivery system for in-app, email, push, WhatsApp
- **Attribution** — one attribution model resolving customer touches across channels into one revenue number
- **Identity resolution** — one customer record per brand joining touches across email, phone, device, account

**Anti-patterns to refactor:** "The email version of the audience builder." "The call-specific consent flow." "The WhatsApp Decision Log." "A new notification service for SMS alerts." "Per-channel customer profiles."

This is what lets Brain charge a flat GMV percentage and still bundle in every channel. A competitor that builds channel-specific stacks pays N times the engineering cost for N channels.

---

## 17. Success Metrics & KPIs

### 17.1 Brand-Level Health (Per Active Brand)

| Metric | Target | Why |
|--------|--------|-----|
| **Daily Active Founders** | >80% | % of Brand Owners who opened the Morning Brief in last 24 hours |
| **Approval Rate** | 50–70% | % of recommendations approved by Owner. Too high = obvious; too low = bad recs |
| **Outcome Accuracy** | >70% | % of approved recommendations whose 7-day/30-day outcome matched predicted direction |
| **Brand CM2 Improvement** | Trending up | % change in CM2 over first 90 days on Brain. **North star metric for product impact.** |

### 17.2 Lifecycle Layer Health

| Metric | Target | Why |
|--------|--------|-----|
| **Recovered revenue per brand per month** | Trending up | North star for Lifecycle |
| **Recovered revenue / GMV fee ratio** | >3× by month 3, >5× by month 6 (Phase 2 live) | Below 3× = brand is paying for cost centre, not revenue centre |
| **COD-to-prepaid lift** | >15% over baseline | India-specific |
| **Winback response rate** | >8% within 14 days | Direct recovery |
| **Call answer rate** | >35% | Industry baseline ~25% |
| **Autonomous ticket resolution** | >60% by month 6, >75% by month 12 | Inbound efficiency |
| **First-response time (inbound)** | <60s WhatsApp, <2 min email | CX quality |

### 17.3 Agentic Commerce Health

| Metric | Target | Why |
|--------|--------|-----|
| **Auto-execute actions per day** | >50 per active brand by end of week 4 | Volume signal |
| **Outcome accuracy** | >80% (7d/30d) | Quality signal |
| **Reversal rate** | <8%; alarm at 15% | Threshold calibration |
| **Time saved per brand per week** | >5 hours founder time freed | Original promise of revenue centre |

### 17.4 System-Level Health

| Metric | Target | Why |
|--------|--------|-----|
| **Data freshness** | Max integration lag <1 hour | Failed recommendations come from stale data |
| **Morning Brief latency** | <20 min from data pull to delivery | Operational reliability |
| **Agent uptime** | >99% of days all agents ran successfully | Service reliability |
| **Cost per brand per month** | Within budget per tier | Infra + LLM cost discipline |

### 17.5 Business-Level Health (Internal)

- **Active brands** — growing per quarter
- **Total GMV under management** — growing per quarter
- **Net revenue** — sum of GMV × tier rate
- **Brand churn rate** — target <5% / quarter for founding cohort
- **NPS** — quarterly survey, target >50

---

## 18. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **LLM cost runs away per brand** | High | Token budgets per feature; soft warning at 80%, hard fail at 100%; per-brand monthly LLM cap (70% throttle / 100% hard throttle, but SQL+ML paths continue) |
| **Integration breakage on red-tier (no-API) marketplaces** | High | Monitor health continuously; notify brand within 1 hour; UI disclaimer for Red integrations |
| **OAuth token plaintext storage** | High (legacy risk from existing codebase) | Application-level AES-256 encryption wrapper on token read/write; per-brand encryption key |
| **Role enforcement gaps in mutation endpoints** | High (legacy risk from existing codebase) | Standardize `requireRole()` guard applied to every mutation endpoint |
| **DND or compliance violation in Lifecycle Layer** | Critical | Two-layer block (brand opt-out + TRAI NCPR); calling hours hard-coded at queue level; P0 incident on any violation |
| **Auto-execute action causes financial damage** | Critical | Confidence thresholds + spend caps + kill switch + immutable Auto-Execute Log + Owner one-click reversal + auto-revert on accuracy drop |
| **Cross-brand data leak via benchmarking** | Critical | Aggregated/anonymized statistics only; raw rows never leave brand's data partition; separate analytics pipeline |
| **Memory layer corruption or loss** | Critical | Replay from immutable Kafka event store; Decision Log is the moat — protected first |
| **Stale data → wrong recommendation** | High | Data freshness SLO (<1h); integration health alerts; nightly anomaly scan validates yesterday's data exists |
| **Concentration risk on Sugandh Lok as first reference** | Medium | Sugandh Lok is illustrative; founding cohort of 20 distinct brands by Phase 1 exit |
| **Partner API contract changes (GoKwik, Shiprocket, Klaviyo)** | Medium | Each partner integration has an owner on engineering team and documented runbook; data deduplication enforced in data layer |

---

## 19. Out of Scope

- Replacing WhatsApp, Gmail, or any messaging tool. Brain drives into them via API.
- Building a CRM. Brain reads from the brand's CRM but does not maintain its own customer database of record.
- Manufacturer-side workflows (production planning, raw material procurement, factory floor).
- Wholesale or B2B order management.
- Per-seat pricing, ever.
- Customer-facing agentic commerce (transacting on behalf of end customers) in the 30-day commitment.
- Outbound cold acquisition (calling people who are not yet customers).
- Live human agent management (shift scheduling, HR).
- Programmatic display ads or DSP integration (Phase 2 scope excludes this).
- Print, OOH, or any offline media — **permanently out of scope.**
- Generative long-form video (hero spots) at scale — Brain handles short-form variant generation only.
- Direct creative buying or media planning — Brain optimises within the brand's existing ad accounts; does not become an ad agency.
- Voice cloning of the brand founder, by default (disabled; only enabled with explicit Owner approval + hard-coded disclosure on every call).

---

## 20. Glossary

| Term | Meaning |
|------|---------|
| **AICMO** | AI Chief Marketing Officer — Brain's marketing intelligence agent group |
| **AICOO** | AI Chief Operations Officer — Brain's operations intelligence agent group |
| **AICFO** | AI Chief Financial Officer — Brain's financial intelligence agent group |
| **aMER** | Acquisition Marketing Efficiency Ratio = New Customer Revenue / Acquisition Ad Spend |
| **AOV** | Average Order Value |
| **ATC** | Add to Cart |
| **BG/NBD** | Beta Geometric / Negative Binomial Distribution — probabilistic LTV model |
| **BFCM** | Black Friday / Cyber Monday — peak-sale event mode |
| **Brand Fingerprint** | Multi-timescale embedding of brand performance — part of Memory Layer |
| **CAC** | Customer Acquisition Cost |
| **CI** | Checkout Initiated |
| **CM1 / CM2 / CM3** | Contribution Margin 1/2/3 — see formulas in Technical Document |
| **CMA** | Custom Match Audience |
| **COD** | Cash on Delivery |
| **Cohort** | Group of customers acquired in the same period |
| **Compound Report** | Month-end summary of what Brain learned about a brand |
| **CPC** | Cost Per Click |
| **CPM** | Cost Per Thousand impressions |
| **CTR** | Click-Through Rate |
| **Decision Log** | Immutable record of every Brain recommendation, response, outcome — **the moat** |
| **DLT** | TRAI's Distributed Ledger Technology — Indian regulatory framework for commercial messages |
| **DPDP** | India's Digital Personal Data Protection Act 2023 |
| **DSR** | Data Subject Request — customer right to deletion/export |
| **EWMA** | Exponentially Weighted Moving Average — used for ad-fatigue detection |
| **Founding Cohort** | First 20 brands; 0.5% GMV locked forever; 12-month commitment + product feedback |
| **GMV** | Gross Merchandise Value |
| **GST** | India's Goods and Services Tax (typically 18% for premium beauty, 12% ayurvedic, etc.) |
| **iROAS** | Incremental ROAS — measured via geo holdout testing |
| **KwikChat / KwikFlo / RTO Shield** | GoKwik products in adjacent layers |
| **LTV** | Lifetime Value (use CM2-based, not revenue-based) |
| **MCP** | Model Context Protocol — open standard for AI agents to access external systems |
| **MER** | Marketing Efficiency Ratio = Total Net Revenue / Total Marketing Spend |
| **Morning Brief** | The daily phone deliverable — top 3 actions for Owner |
| **NDR** | Non-Delivery Report — courier couldn't deliver on first attempt |
| **paMER** | Paid Marketing Efficiency Ratio |
| **P40 / P80** | Percentile-based At-Risk / Churned thresholds derived from brand's order data |
| **Pincode** | Indian postal code |
| **Plan Module** | Brain's forward P&L forecasting feature |
| **Prepaid** | Online payment at checkout (vs COD) |
| **Prophit System** | Taylor Holiday's framework (CTC); philosophical foundation for Brain's metrics |
| **RAG** | Red / Amber / Green status indicator |
| **RFM / RFMC** | Recency-Frequency-Monetary segmentation; RFMC adds COD-behaviour dimension |
| **ROAS** | Return on Ad Spend (vanity metric — Brain replaces with MER/aMER) |
| **RTO** | Return to Origin — failed delivery returned to seller |
| **Statlas** | DTC analytics tool by Common Thread Collective; Brain's depth benchmark |
| **TRAI NCPR** | Telecom Regulatory Authority of India's National Customer Preference Register (DND list) |
| **Workspace** | A single brand's tenancy in Brain |

---

*End of BRAIN_BUSINESS.md*
*Sources reconciled: PROJECT_SCOPE.md (Looqus audit, 2026-05-04), TECHNICAL_ARCHITECTURE.md (Looqus audit, 2026-05-04), brain-platform-complete-spec.md (March 2026), Brain-Technical-Brief.docx (May 2026), Technical Document.pdf/md v2.0 (2026-05-13).*
