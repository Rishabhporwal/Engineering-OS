# Brain — Business Context (Agent Primer)

**Read this before doing anything for Brain.** Every agent loads this at the start of every task. It is a condensed, load-bearing extract from `canon/BRAIN_BUSINESS.md` (1,226 lines). When in doubt, the original document wins; this primer is what you must always remember.

---

## What Brain is — one paragraph

Brain is an **AI-native commerce operating system for D2C brands worldwide**, sequenced India-first. It consolidates the fragmented stack a D2C operator runs (Shopify + Meta + Google + Shiprocket + Razorpay + WhatsApp + Excel) into one system that **sees the brand's data, learns the brand's history, and acts before the founder has to**. It replaces manual chaos with three AI executives — **AICMO** (marketing intelligence), **AICOO** (operations intelligence), **AICFO** (financial intelligence) — delivered through a **Morning Brief on the phone (07:00–09:00 IST)** and a web workbench. Built global from line one; every region is a `RegionAdapter` implementation, not a rebuild.

---

## Who uses it (five personas per brand)

| Persona | Their question | Surface |
|---------|----------------|---------|
| **Founder / Owner** | "Is the business healthy and growing?" | Phone Morning Brief daily; web weekly. |
| **Operator / COO / Head of Growth** | Implements recommendations + adds operational context. | Web workbench daily. |
| **Performance Marketer / Media Buyer** | "Is advertising working? Where to optimize?" | Meta/Google reports, creative perf, MER/aMER. |
| **Finance / CFO** | "Cash flow, profitability, forecasting." | P&L, CM waterfall, CAC payback, Plan Module. |
| **Retention / CRM Manager** | "Loyalty, LTV, email performance." | Net Active Customer, RFM, at-risk count. |

**Three customer tiers** (by GMV/month):
- **Small** ₹50L–₹3Cr — 1–3 ad accounts, 5–15 SKUs; founder = operator.
- **Mid-Market** ₹3Cr–₹50Cr — 5–10 ad accounts, 30–100 SKUs; small marketing team.
- **Enterprise** ₹50Cr+ or multi-brand holding co — full team, multi-channel, 100+ SKUs.

**Out of scope:** Brands under ₹25L/month (DFY uneconomical), pure marketplace sellers, manufacturers, wholesale/B2B, per-seat pricing.

---

## Where it operates (sequencing matters)

1. **Phase 0–1 (Foundation):** India. INR. Asia/Kolkata default. Founding cohort = 20 brands at 0.5% locked forever.
2. **Phase 1 parallel (GCC):** UAE + KSA. AED + SAR. Salla/Zid/Noon/Tabby/Aramex/DHL.
3. **Phase 4 (Western expansion):** US + EU (UK, DE, FR). USD + EUR. Stripe/ACH. GDPR data residency `eu-central-1`. SOC 2 Type II required.
4. **Phase 5+:** LATAM, SEA, Africa — each is a new `RegionAdapter`, not a rewrite.

> **Why India first:** Founder network + India-native moat (RTO/COD/GST/Pincode/Festival) is structurally hard for Western tools to backfill in <5 years.

---

## Pricing (GMV-linked, never per-seat)

| Tier | GMV band | Rate |
|------|----------|------|
| **Founding Cohort** | Any | **0.5%** — 20 spots only, locked forever, 12-month commitment + structured feedback |
| **Standard — Early** | <₹1Cr/month | **1.0%** |
| **Standard — Growth** | ₹1Cr–₹50Cr/month | **0.5%** (auto-applied on crossing threshold) |
| **Enterprise** | ₹50Cr+, 3+ brands, or Enterprise Variant features | **Custom** (flat platform fee + reduced %, or annual) |

**What's included in every tier:** all analytics, all Lifecycle channels (call/WhatsApp/email/SMS/RCS/referral), AICMO/AICOO/AICFO, agentic auto-execute, all integrations, telephony pass-through + LLM tokens **up to per-brand monthly cap** (soft warning 80%, hard fail 100% — SQL+ML paths continue when LLM is throttled).

**Multi-Brand Holding Co:** Pricing per brand, not per Organisation. One rolled-up invoice.

**Agency billing:** Client brand billed to end-customer Org; Agency Org pays separate flat platform fee for agency tooling.

**Why GMV-linked:** Aligns Brain's revenue with brand's growth. Profit attribution is hard to defend; GMV is auditable.

---

## Core value propositions (ranked by emphasis)

1. **Honest, operator-grade analytics.** MER/aMER replaces ROAS vanity. RAG goal-setting. "Am I making money?" answered in 10 seconds.
2. **India-native intelligence (THE MOAT).** RTO as a P&L line, COD vs Prepaid economics, pincode reliability (RTO ranges 5–45%), GST stripped at source, festival seasonality (Diwali/Navratri/Onam multipliers), NDR resolution, COD handling fees. No Western tool can backfill this quickly.
3. **Proactive intelligence (not reactive dashboards).** Daily anomaly detection (Z-score on 14-day window with attribution), AI Morning Brief at ~07:15 IST with **3 ranked actions** (Approve / Reject / Edit), evening pulse vs forecast, weekly review, month-end report.
4. **Lifecycle as a revenue centre.** Brain performs revenue-generating outreach (abandoned cart, COD confirmation, post-delivery follow-up, winback, VIP, replenishment, WhatsApp). RFM-segmented multi-channel routing. **Target Recovered Revenue / Fee ratio: >3× by month 3, >5× by month 6.**
5. **Agentic commerce with kill switch.** 8 initial auto-execute actions (pause ad, reduce budget, refund, replace item, reorder inventory, transfer inventory, apply discount, switch courier). Graduates from human-in-the-loop → auto on confidence ≥ threshold. Guardrails: confidence gating, per-action spend caps, single kill switch, immutable Auto-Execute Log, 7-day/30-day outcome tracking.
6. **Three-layer architecture, Memory as the moat.** Data Layer (integrations normalized) → **Memory Layer** (multi-timescale embeddings of brand performance, customer cohorts, decision-outcome history — **the moat**) → Agentic Layer (AICMO/AICOO/AICFO with sub-agents).
7. **Decision Log + MCP Server.** Every recommendation/response/outcome logged immutably. Brain's MCP sits *above* every other MCP (Shopify, Meta, Razorpay), exposing `brand_fingerprint`, `decision_log`, `condition_outcome_pairs`, `rfm_segments`, `recovered_revenue_ledger`, `creative_fingerprint`, `cross_brand_benchmarks`.
8. **Global product, India-first sequencing.** Every primitive is multi-region capable from day one; `RegionAdapter` adds a region without rewriting the engine.

---

## Product surfaces (what agents may be asked to build)

A non-exhaustive list of named modules — agents will encounter these by name in requirements. Full descriptions live in `BRAIN_BUSINESS.md` §6.

**Daily / proactive:** Morning Brief (phone), Daily Email Digest (08:00 IST), Anomaly Detection.

**Analytics:** Store Dashboard, P&L Module, CM Waterfall (RTO-adjusted), Calendar Report, MER/aMER/paMER/iROAS, Acquisition vs Non-Acquisition split, Creative Intelligence (aggregate + agentic), Net Active Customer Lifecycle Report, P40/P80 churn thresholds, First Product → Repeat Cascade, Cohort Analysis, LTV Engine (BG/NBD + Gamma-Gamma), LTV Drivers, RFM / RFMC Segmentation.

**India-specific:** RTO Analytics, COD vs Prepaid Analytics, Pincode Intelligence, Festival Seasonality Engine, GST-Aware Revenue, Shiprocket Deep Integration.

**Operations:** Products Module (Pareto A/B/C by CM1), Inventory Module (Lead Time, Sell-Through, Stockout prediction, Reorder).

**Forecasting:** The Plan Module (forward P&L next 1–3 months), Budget Allocation Optimizer.

**Lifecycle revenue:** Abandoned Cart Recovery, COD Confirmation Calls, Multi-Channel Inbox, RFM-Triggered Audience Builder, Referral Engine.

**Memory / API:** Decision Log, Auto-Execute Log, MCP Server (read + action endpoints).

---

## Integrations (what we connect to)

**Phase 0–1 commit:** Shopify, Meta Ads, Google Ads, Shiprocket, Razorpay. (Add Klaviyo + WooCommerce as Phase 1 stretch.)

**Phase 2+:**
- Marketplaces (Green / clean API): Salla, Zid, Amazon SP-API (IN/AE), Flipkart v3, Noon, BigBasket.
- Marketplaces (Yellow / gated): Myntra, Ajio, Meesho, Namshi, Talabat.
- Marketplaces (Red / no API): Nykaa, Blinkit, Zepto, Instamart, Ounass — Gmail OAuth + LLM PDF extraction workaround.
- Email: Klaviyo, Omnisend, Mailmodo (read first, native engine later).
- WhatsApp: Wati, AiSensy (same pattern).
- OMS: Unicommerce, Eshopbox.
- Logistics direct: Delhivery, Bluedart.

**Partner relationships (not competitors):**
- **GoKwik** — read RTO Shield + KwikChat + KwikFlo signals. Brain operates intelligence layer above their checkout/RTO/cashflow.
- **Razorpay** — payments + agentic execution; partner around Agent Studio.
- **Shiprocket** — core integration + logistics partner.

**Platform programs to earn:** Meta Business Partner (Phase 2), Shopify Plus Technology Partner (Phase 2–3), Google Premier Partner, Salla/Zid Partner (Phase 1), Noon Seller Partner.

---

## Compliance — non-negotiable

| Regime | Rule | What it means for agents |
|--------|------|--------------------------|
| **DPDP Act 2023 (India)** | Brain = Data Processor; brand = Data Fiduciary | DPA available to every paying customer. |
| **GDPR (EU)** | SCCs + sub-processor list; EU residency option (Enterprise) | `eu-central-1` deployment path Phase 4. |
| **CCPA (California)** | Same as GDPR for CA residents | Honor data-rights requests via brand. |
| **DLT / NCPR / DND (India telecom)** | Calling hours 09:00–21:00 IST; two-layer DND check (brand opt-out + TRAI NCPR); consent + disclosure + recording consent; max 1 call / 48h per customer; DLT registration per template | **P0 incident on any violation.** Hard-coded at queue level. |
| **TLS / encryption** | TLS 1.2+ in transit, AES-256 at rest, OAuth tokens AES-256-GCM per-brand key in Secrets Manager | PII never in logs (hashed). |
| **Cross-brand isolation** | Every row tagged `workspace_id`; every query filtered at DB layer; RLS on every table | Cross-brand benchmarks **aggregated/anonymized only**. |
| **Right to deletion (DSR)** | Brand triggers in Brain → hard-delete in 30 days; aggregated metrics retained (re-link impossible) | Deletion logged. |
| **What Brain never stores** | Card numbers, CVVs, full addresses, national IDs, passwords, health/biometric data. | Reject any requirement that would change this. |

**SOC 2 Type II:** Phase 1 kickoff, 9–12 month certification. **ISO 27001:** after SOC 2.

---

## Competitors and where Brain wins

| Competitor | Strength | Where Brain wins |
|-----------|----------|------------------|
| **Kleio** ($29/mo) | Simple, cheap, basic profit tracking | Depth: forecasting, lifecycle, Level 4 (Prescriptive) intelligence |
| **Statlas** ($499/mo) | Gold-standard analytical rigor | Beautiful UI + native AI intelligence + India-native metrics + Lifecycle revenue execution |
| **Triple Whale / Northbeam** | US-built, Level 2–3 analytics + shallow Level 4 | Full Level 4, India-native moat, Lifecycle revenue layer; no US tools serve India |
| **GoKwik** | Checkout, RTO Shield (5+ yrs, 15K brands, 29K pincodes), WhatsApp, cashflow | **Partner, not competitor.** Brain operates intelligence layer above. |
| **Wati / AiSensy** | WhatsApp automation | Brain reads first; native multi-channel execution later. |
| **Klaviyo / Omnisend / Mailmodo** | Email lifecycle | Same pattern — read first, replace Phase 2. |

---

## Roadmap (terse)

- **Phase 0–1 (W1–12):** India launch. Data Layer (Shopify/Meta/Google/Shiprocket/Razorpay normalized). Memory Layer building (Brand Fingerprint, P40/P80, RFM, Decision Log). Analytics + reporting. Lifecycle outbound v1a. India regional (RTO/COD/Pincode/Festival/GST/Shiprocket deep). AICMO/AICOO/AICFO in human-in-the-loop. Founding cohort = 20 brands.
- **Phase 1 GCC parallel (W5–22):** GCC RegionAdapter live. Salla/Zid partner programs. 50–100 brands by exit.
- **Phase 2 (W13–24):** Memory compounds. Marketplaces (Amazon/Flipkart/Myntra/Nykaa/Blinkit/Noon). Lifecycle v1b (multi-channel inbox, native email engine, SMS, RCS, referral engine). 8 auto-execute actions hardened. LTV engine. Plan Module. Budget Allocation Optimizer. 200–300 brands. Meta Business Partner.
- **Phase 3 (W25–36):** MCP external surfaces live (read + action). Enterprise variant features (private warehouse, fine-tuning). Bidirectional MCP. Multi-agent action chains. Shopify Plus Tech Partner. 400–500 brands. SOC 2 Type II.
- **Phase 4 (W37–48+):** US/EU RegionAdapter live. Triple Whale/Northbeam competitive positioning. White-label reporting. 1000+ brands.
- **Phase 5+:** Capital products (inventory-backed lending, RBF) + Retail OS (apply AICMO/AICOO/AICFO to physical retail). LATAM/SEA/Africa adapters.

---

## Engineering Operating Principles (from `BRAIN_BUSINESS.md` §16.2)

1. **Make requirements less dumb first.** Delete what doesn't exist. Simplify. Then automate.
2. **If SQL can solve it, never reach for ML. If ML can solve it, never reach for an LLM.** Cost compounds. (See [skill: cost-routing-paradigms](../skills/cost-routing-paradigms/SKILL.md).)
3. **Memory is the moat.** Every architectural decision must preserve and extend brand decision-outcome history.
4. **Data isolation is non-negotiable.** Every workspace lives in its own logical partition.
5. **Human-in-the-loop until graduation.** Agents graduate to autonomous only after brand-specific accuracy thresholds, with kill switch.

---

## The Single-Primitive Rule (from `BRAIN_BUSINESS.md` §16.5)

Build every cross-cutting concern once; consume it from every channel/agent.

- **One Audience Builder** — call, WhatsApp, email, SMS, RCS, ad-platform sync, referral.
- **One Decision Log** — all agents write; all outcomes attribute.
- **One Consent model** — per customer, per brand, per-channel granularity.
- **One Notification system** — in-app, email, push, WhatsApp.
- **One Attribution model** — customer touches → one revenue number.
- **One Identity resolver** — hashed email + phone joining touches across channels/devices.

**Anti-patterns explicitly forbidden:**
- "The email version of the audience builder"
- "The call-specific consent flow"
- "The WhatsApp Decision Log"
- "Per-channel customer profiles"

> This is why Brain can charge a flat GMV % bundling every channel. A competitor with per-channel stacks pays N× engineering for N channels.

---

## The three AI executives — "Lyfe"

| Exec | Domain | Owns |
|------|--------|------|
| **AICMO** | Marketing intelligence | Meta, Google, TikTok, Snap, Cross-Channel, Creative, Pricing, Festival sub-agents. Pauses ads, allocates spend. |
| **AICOO** | Operations intelligence | Logistics, Returns, Inventory, Marketplace sub-agents. Reorders inventory, switches couriers, issues refunds, replaces items. |
| **AICFO** | Financial intelligence | Conversion, Cashflow, Pricing-Margin sub-agents. Forecasts cash, prices margin. |

Not "one big AI" — three specialists with clear domains. They recommend together; they own distinct actions.

---

## Founding Cohort economics (the immediate context)

- 20 brands, 0.5% locked forever, 12-month commitment, structured product feedback.
- Daily quality review of agent outputs.
- Weekly per-brand check-in.
- Monthly memory audit.
- These brands are reference customers + product feedback loops.

> **Sugandh Lok** (beauty, Kumkumadi Face Oil, Sandalwood Soap, 18% GST, Diwali seasonality) is the illustrative example throughout the docs. It is *not* the only target — every paying DTC brand from ₹50L/month upwards follows the same product shape.

---

## When in doubt

1. **Re-read this primer.**
2. **Open `canon/BRAIN_BUSINESS.md`** — it is the source of truth; this primer is the curated summary.
3. **Check the relevant curated skill** (see [skill-mapping-matrix.md](skill-mapping-matrix.md) for the role-to-skill map).
4. **Escalate to CTO Advisor** if business intent is ambiguous.
5. **Escalate to Founder/Rishabh** if the business model itself is being touched.
