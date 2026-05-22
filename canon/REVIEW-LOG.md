# Brain — Review & Audit Log

> Consolidated audit trail: **Phase 1** business-requirements review + **Phase 3** technical alignment audit. Both rounds are RESOLVED & APPLIED to the live docs. This is rationale/history (and the verified market-fact sources) — not a requirements document. Merged from business-review-findings.md + technical-review-findings.md on 2026-05-23.

---

# Brain — Business Requirements Review: Findings

> **Reviewer:** Claude (Opus 4.7)
> **Date:** 2026-05-23
> **Source reviewed:** `business-requirements.md` (Standalone v1.0, 1,804 lines, 26 sections)
> **Method:** line-by-line read of all 26 sections, checked for (a) market/factual correctness, (b) internal consistency, (c) completeness/gaps, (d) soundness of the assumption. Market claims verified against current (2026) sources, listed at the bottom.
> **Status:** ✅ RESOLVED & APPLIED (2026-05-23). All B/C/E/F items applied to `business-requirements.md` (now v1.1). All four A/D strategic decisions made by the founder: **D1 = realized/delivered GMV**, **A1 = India-first, UAE/GCC sequenced**, **A3 = ₹50L/month hard floor**, **A2 = keep %s + minimum fee + CM2 guardrail**. This file is retained as the audit trail of the review.

---

## 0. Verdict in one paragraph

The business document is **strong, internally coherent in most places, and unusually disciplined** — it ties every surface to revenue/profit/risk/time/compliance/memory, it refuses vanity ROAS, and it treats the Decision Log as the compounding moat. The issues below are not structural; they are (1) a few **factual updates** the market has moved on (GST 2.0, GCC per-country VAT, named privacy/telecom laws), (2) two **internal contradictions** (ICP floor, geographic "day one" vs the phased roadmap), and (3) a handful of **commercial gaps** that will bite later — chiefly *what GMV number Brain actually bills on* in a 25–35% RTO market. Fix those and the doc is investment- and build-grade.

| Severity | Count | Auto-apply? |
|---|---|---|
| **A. Strategic decisions (need your call)** | 3 | No — decide first |
| **B. Market-fact corrections (verified)** | 6 | Yes, on approval |
| **C. Internal inconsistencies** | 3 | Yes, on approval |
| **D. Gaps / missing requirements** | 6 | Mixed — 2 need your call |
| **E. Metric precision** | 2 | Yes (or defer to tech doc) |
| **F. Minor / editorial** | 4 | Yes, on approval |

---

## A. Strategic decisions — these need your call before I edit

### A1. Geographic scope: "first-class from day one" contradicts the phased roadmap *(also a consistency bug)*
- **Where:** §3.3 says *"India, UAE, and GCC are first-class markets from the beginning."* But §21 (Roadmap) sequences UAE/GCC: Phase 1 = "UAE/GCC adapter **foundations**", Phase 4 = "**Mature** UAE/GCC provider coverage." §5.2 and the TECH docs say "India first."
- **Why it matters:** Building India **+** UAE **+** KSA simultaneously on day one roughly doubles the surface area (3 tax regimes, 3 logistics ecosystems, Arabic localization, 3 consent regimes, different marketplaces) for an early team. It dilutes the wedge.
- **Recommendation:** Reword §3.3 to: *"Brain is multi-region by architecture from day one (region-adapter pattern), India-first by go-to-market sequencing. UAE/GCC is a first-class **adapter** but is activated for live customers in a later phase."* This keeps the global ambition, keeps the engineering honest, and removes the contradiction.
- **Your call:** (a) India-first, UAE/GCC sequenced [recommended], or (b) genuinely launch all three simultaneously (then I'll align the roadmap to match, and we accept the higher build cost).

### A2. Pricing: the 1.0% / 0.75% / 0.5% of GMV model needs a margin guardrail, a floor, and a defined GMV base
- **Where:** §15.2 — Launch ~1.0% of GMV, Growth ~0.75%, Scale ~0.5%.
- **What the market shows (verified):** Triple Whale ≈ $429/mo for a brand at ~$1M GMV/yr (~$83k/mo) → **≈0.5% of monthly GMV**, dropping to **~0.22%** at $6M/yr. Polar Analytics base ≈ $720/mo. These are **analytics-only** tools. Brain bundles execution (lifecycle, WhatsApp, AI support, auto-execute), so a premium is defensible — **but Brain's entry rate (1.0%) is ~2× the analytics incumbents' effective rate at the same scale.** That's fine *if* the recovered-revenue proof lands (your own KPI: >3× fee by month 3).
- **Three real problems with %-of-GMV as written:**
  1. **No CM2 affordability guardrail.** 1% of GMV is 4–7% of CM2 for a healthy 15–25% CM2 brand — acceptable. But for a thin-margin brand (~10% CM2), 1% of GMV = **~10% of all contribution margin** — unsellable. Pricing should be sanity-checked against CM2, with a soft cap (e.g. fee ≤ X% of CM2).
  2. **No minimum monthly fee.** At the ₹50L/mo floor, 1% = ₹50k/mo (~$600) — workable. But onboarding + support cost is roughly fixed; a floor brand at a bad month shouldn't drop below your cost-to-serve. Add a **minimum monthly fee** (the GMV % applies above it).
  3. **GMV base is undefined → see D1.** In a market with 25–35% COD RTO, billing on *placed* GMV means the brand pays a fee on revenue that physically came back. This is the single most important commercial definition in the doc.
- **Recommendation:** Keep %-of-GMV + no-per-seat (good differentiators). Add: (i) minimum monthly fee per tier, (ii) a CM2-based affordability note, (iii) define the GMV base as **realized/delivered GMV** (or net of RTO) — see D1.
- **Your call:** Confirm the headline %s stay (1.0/0.75/0.5), and pick the GMV base (D1). I'll draft the floor + CM2 guardrail language.

### A3. ICP floor contradiction: ₹50L vs ₹25L
- **Where:** §3.1 — *"Minimum practical ICP: Monthly GMV ₹50L+"* but two lines later *"Brands below ₹25L/month equivalent are not the initial target."* These imply two different floors and leave ₹25L–₹50L undefined.
- **Recommendation:** Pick one floor. Given the pricing math and onboarding burden, **₹50L/month (~₹6Cr/yr) is the right hard floor**; soften the ₹25L line to *"Brands below ~₹50L/month rarely justify the onboarding/support load; ₹25L–₹50L brands are case-by-case."* TAM check: India has ~11,000 D2C companies (~800 funded); a ₹50L/mo floor still leaves a multi-thousand-brand wedge.
- **Your call:** Confirm ₹50L as the hard floor (recommended), or keep ₹25L as an absolute floor with ₹50L as the "sweet spot."

---

## B. Market-fact corrections — verified, recommend auto-apply

### B1. India GST 2.0 — the slab structure changed (Sept 22, 2025)
- **Where:** §17.2 ("GST-inclusive pricing and slab overrides"), §6.2 (Revenue Net Tax = inclusive / (1+tax_rate)).
- **Fact:** Effective **22 Sep 2025**, India moved to **GST 2.0**: the 12% and 28% slabs were abolished; the structure is now **0% / 5% / 18% / 40%** (40% = luxury/sin goods). [Sources 1]
- **Edit:** Update the India adapter to state the current slabs (0/5/18/40). Add a note that tax extraction must be **per-line-item by the SKU's GST slab**, not a single blended rate (most DTC carts mix 5% and 18% goods). Connects to **E1**.

### B2. GCC VAT is not uniform — specify per country
- **Where:** §3.3 ("KSA/GCC … VAT"), §17.3 ("VAT handling").
- **Fact (verified):** **UAE 5%, KSA 15%, Bahrain 10%, Oman 5%; Qatar & Kuwait have not implemented VAT yet.** KSA raised to 15% on 1 Jul 2020. [Sources 2]
- **Edit:** Replace generic "VAT" with the per-country table in the UAE/GCC adapter section. This is a correctness bug — a single "GCC VAT 5%" assumption would overstate KSA margins by ~10 points.

### B3. Name the actual laws — compliance section is generic
- **Where:** §19 (Compliance/Privacy/Trust), §3.3, §17.2.
- **Fact (verified):**
  - **India — DPDP Act 2023** + **DPDP Rules 2025** notified **13 Nov 2025**, phased: procedural now → Consent Managers ~Nov 2026 → core obligations (notice, security, breach, erasure, SDF duties) **~May 2027**. Consent-based regime, right to erasure, breach notification. [Sources 6]
  - **Messaging/voice — TCCCPR 2018** (amended **12 Feb 2025**): **DLT** registration mandatory for A2P SMS & voice; **NCPR/DND**; **promotional calls/SMS only 9am–9pm**; 2025 amendment tightened complaint thresholds (5 complaints/10 days) and operator action windows. [Sources 5]
  - **UAE — PDPL** (Federal Decree-Law No. 45 of 2021, in force Jan 2022): explicit, revocable opt-in for marketing. [Sources 8]
  - **KSA — PDPL** (in force; enforcement from **14 Sep 2024**): opt-in consent for direct marketing, penalties up to SAR 5M, data-transfer restrictions. [Sources 8]
- **Edit:** Rewrite §19.1 to name these laws and map Brain's obligations (consent, retention limits, erasure, breach notice, data-transfer rules) to each. This is currently the weakest section relative to how much PII Brain touches.

### B4. RTO/COD reality — anchor the defaults to real numbers (validates the doc)
- **Where:** §5.2, §6.4, §10.6, §17.2.
- **Fact (verified):** COD RTO averages **~20–35%** (one industry report: **26%** on COD), prepaid **~2–8%**; COD is **58–64% of orders in Tier-2/3** and drives **76–83% of RTO volume**; RTO rises with delivery time (22% at 1–2 days → 35% at >5 days) and varies by zone/order-value. [Sources 4]
- **Edit:** No correction needed — this **validates** the doc's heavy RTO focus. Recommend adding a one-line "why this matters" stat in §5.2/§17.2 so the requirement is grounded (e.g., "COD RTO commonly 20–35%; the single largest controllable margin leak in Indian DTC"). Strengthens the doc; optional.

### B5. WhatsApp pricing model changed — per-message since Jul 1, 2025
- **Where:** §11.2, §15.4 (pass-through costs).
- **Fact (verified):** As of **1 Jul 2025**, WhatsApp bills **per delivered template message** (not per 24h conversation); **service/non-template messages within an open window are free**; rates vary by template category (marketing/utility/auth) and country; India is among the cheapest (marketing ≈ $0.012, with a rate increase effective Jan 1, 2026); volume discounts on utility/auth. [Sources 7]
- **Edit:** Update §15.4 / §11.2 wording from conversation-based to **per-message, category-based** cost tracking, and note the free service window (relevant to support economics). Low effort, keeps the cost model accurate.

### B6. TikTok Ads is not available for India-domestic targeting
- **Where:** §9.2 lists "TikTok Ads, Snapchat Ads" as ad integrations.
- **Fact:** TikTok has been **banned in India since 2020**; TikTok Ads is relevant for **UAE/GCC**, not India-domestic DTC. Snapchat is available in both.
- **Edit:** Annotate the ad-integration row to scope TikTok to UAE/GCC (region-gated connector), so India onboarding doesn't surface an unusable channel.

---

## C. Internal inconsistencies — recommend auto-apply

- **C1. ICP floor (₹25L vs ₹50L).** Covered in **A3** (needs your pick, then I fix).
- **C2. Geo "day one" vs phased roadmap (§3.3 vs §21).** Covered in **A1** (needs your pick, then I fix).
- **C3. Channel-specific compliance is conflated.** §3.3/§17.2 say "TRAI/DLT messaging constraints" as if DLT governs WhatsApp. **DLT governs SMS & voice;** WhatsApp is governed by **Meta opt-in + template approval + the 24h session window**; **calls** add NCPR/DND + 9am–9pm hours. **Edit:** split the compliance note by channel so the lifecycle engine applies the right rule per rail (this also de-risks §11/§14).

---

## D. Gaps / missing requirements

### D1. **(Needs your call)** The GMV base for billing is undefined — highest-impact gap
- Brain prices on "GMV under management" but never defines whether that's **placed GMV** (orders created) or **realized/delivered GMV** (after cancellations/RTO/refunds). In a 25–35% RTO market this is a 25–35% swing in the brand's bill.
- **Recommendation:** Bill on **realized/delivered GMV** (or placed GMV net of RTO/refunds). It aligns Brain's incentive with the customer's actual revenue and is consistent with the doc's own "realized revenue" gospel. Define it explicitly in §15.
- **Your call:** placed, realized, or placed-net-of-RTO.

### D2. **(Needs your call)** No minimum monthly fee / cost-to-serve floor
- See A2.3. Recommend a per-tier minimum (the GMV % applies above it). **Your call:** include a floor (recommended) or pure %.

### D3. Data residency default is implicit
- §3.4 (Model D) and §19.1 mention "regional data controls / residency for enterprise." Given **DPDP** (India) and **KSA PDPL** transfer restrictions, recommend stating that **India customer data is stored in-region by default** (not enterprise-only). **Edit (recommend auto-apply):** add a one-line default-residency statement to §19.1.

### D4. Calling-hour & AI-voice consent rules absent from the compliance section
- §11/§4 include **calls** (and the lifecycle layer implies AI calling), but §19 never states the **9am–9pm window, NCPR/DND scrubbing, DLT for voice**, or AI-voice disclosure. **Edit (recommend auto-apply):** add to §19 a "Outbound voice/messaging compliance" subsection.

### D5. Consent Manager concept (DPDP Rules) not referenced
- DPDP Rules introduce **registered Consent Managers** (phase ~Nov 2026). Brain's consent model (§19.4) should be forward-compatible. **Edit (recommend auto-apply):** one forward-looking line in §19.4.

### D6. Trial / activation commercial terms unstated
- §16 mentions a "Trial/activation review" at Day 14 and §15 a "Self-Serve" tier, but no trial length/terms. Low priority; recommend a single line (e.g., "time-boxed activation period before first invoice").

---

## E. Metric precision — recommend auto-apply (or defer to the technical doc)

- **E1. Revenue Net Tax assumes a single tax rate.** §6.2: `Revenue Net Tax = inclusive / (1 + tax_rate)`. With GST 2.0 multi-slab (5/18/40) and mixed carts, this must be **per-line-item by SKU slab**, then summed. **Edit:** note the per-line-item rule; keep the formula as the per-line primitive.
- **E2. Break-even COD RTO rate formula is imprecise.** §6.4: `Margin before RTO / RTO cost per failed COD order` (= M/C). The economically correct break-even RTO rate is **r\* = M / (M + C)** (where profit on delivered = loss on RTO). **Edit:** correct the formula or label the current one as a simplified heuristic.

---

## F. Minor / editorial — recommend auto-apply

- **F1.** §3.2 Tier 2 band (₹3Cr–₹50Cr/mo) is very wide (₹36Cr–₹600Cr/yr). Optional: split or note. No correctness issue.
- **F2.** §6.1 "Net Revenue … − Payment Failures": failed prepaid orders usually never enter Net Sales; clarify this is a correction term for partially-captured/charged-back cases. Minor.
- **F3.** §17.2 festival list is solid; optionally add major platform sale windows (e.g., end-of-season sales) as configurable events rather than fixed festivals.
- **F4.** Glossary (§25) defines RFMC well (C = COD behavior) — recommend adding **DPDP, PDPL, TCCCPR/DLT, NCPR, BNPL** to the glossary since the compliance edits introduce them.

---

## Sources
1. India GST 2.0 (slabs 0/5/18/40, eff. 22 Sep 2025): [Razorpay](https://razorpay.com/learn/gst-2-0-reforms-in-india/), [ClearTax](https://cleartax.in/s/gst-rates), [PIB GoI](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/sep/doc202594628401.pdf)
2. GCC VAT (UAE 5 / KSA 15 / Bahrain 10 / Oman 5; Qatar/Kuwait none): [VATupdate 2026](https://www.vatupdate.com/2026/01/05/global-vat-rates-by-country-2026-standard-and-reduced-rates/), [Avalara KSA](https://www.avalara.com/vatlive/en/country-guides/africa-and-middle-east/saudi-arabia/saudi-arabian-vat-rates.html)
3. Analytics pricing benchmarks: [Triple Whale pricing 2025 (Conjura)](https://www.conjura.com/blog/triple-whale-pricing-in-2025-costs-features-and-best-alternatives), [Polar pricing 2025 (Conjura)](https://www.conjura.com/blog/polar-analytics-pricing-in-2025-costs-features-and-best-alternatives)
4. India COD/RTO rates: [Shipway ShipNotes (26% COD RTO)](https://mediabrief.com/shipnotes-reveals-26-rto-rate-on-cod-orders-across-india/), [GoKwik RTO guide](https://www.gokwik.co/blog/what-is-return-to-origin-rto-in-ecommerce), [Dazeinfo (25%+ COD fail)](https://dazeinfo.com/2024/06/05/over-25-of-cod-orders-fail-a-major-dent-in-indias-e-commerce-business/)
5. TRAI/DLT/calling hours: [TRAI TCCCPR amendment 12 Feb 2025 (PDF)](https://www.trai.gov.in/sites/default/files/2025-02/Regulation_12022025.pdf), [Outbound call regs 2025 (TALK-Q)](https://talk-q.com/outbound-call-regulations-in-india), [SMS regs 2025 (TALK-Q)](https://talk-q.com/sms-messaging-regulation-in-india)
6. India DPDP Act + Rules 2025: [EY](https://www.ey.com/en_in/insights/cybersecurity/transforming-data-privacy-digital-personal-data-protection-rules-2025), [MeitY](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa), [PIB (PDF)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
7. WhatsApp per-message pricing (eff. 1 Jul 2025): [Meta developer docs](https://developers.facebook.com/docs/whatsapp/pricing/updates-to-pricing/), [Meta pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
8. UAE/KSA PDPL (marketing consent): [ICLG Saudi 2025-26](https://iclg.com/practice-areas/data-protection-laws-and-regulations/saudi-arabia/), [UAE PDPL guide](https://cookie-script.com/privacy-laws/uae-data-protection-law-pdpl), [KSA direct-marketing consent](https://saudiprivacylaw.com/blog/direct-marketing-and-consent-withdrawal-under-pdpl/)
9. India D2C sizing: [Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/india-d2c-ecommerce-market), [Indian Retailer (800+ brands)](https://www.indianretailer.com/article/d2c-new-commerce/trends/how-800-d2c-brands-are-shaking-indias-retail)
10. UAE/KSA BNPL (Tabby/Tamara): [UAE BNPL report 2025](https://www.businesswire.com/news/home/20251127330476/en/), [Tabby vs Tamara GMV](https://termsheet.substack.com/p/tabby-vs-tamara-gmv-and-market-share)



---
---

# Brain — Technical Alignment Audit: Findings & Fixes

> **Reviewer:** Claude (Opus 4.7) · **Date:** 2026-05-23
> **Scope:** Full re-read of every file in `Brain-docs/` after the v2.0 rewrite, checking for (a) discrepancies, (b) technical↔business misalignment, (c) missing coverage, (d) incorrect statements.
> **Status:** ✅ All items below FIXED. This file is the audit trail.

---

## Discrepancies found & corrected

| # | Severity | File(s) | Issue | Fix |
|---|---|---|---|---|
| **D1** | **Critical** | `TECH/03` §0.2, §0.6 | The metrics single-source-of-truth used a **different CM convention** than the business doc: it put non-marketing variable costs in **CM2** and marketing in **CM3** (`CM2 = CM1 − variable`, `CM3 = CM2 − CAC`). Business doc §6.2 (SSoT) puts variable in **CM1**, marketing in **CM2**, fixed in **CM3**. CM2 is the product's most important metric — two definitions is a correctness failure. | Rewrote §0.2 and §0.6 to the canonical convention (CM1 = Net Rev − COGS − non-marketing variable; CM2 = CM1 − marketing; CM3 = CM2 − fixed). Now matches `business-requirements.md` §6.2 and `technical-requirements.md` §11.2. |
| **D2** | High | `TECH/01` §workspace_members, `TECH/09` §2 | Legacy **4-role model** (`owner/admin/analyst/viewer`) contradicted the canonical **5-role** model (Owner/Operator/Analyst/Agency/Viewer) from BR §4.2 + TECH/00 R2. | Fixed the Postgres CHECK constraint and the authorization table to the 5-role model. |
| **D3** | High | `TECH/12` §4, `TECH/11` §8, `TECH/13` §9 | Pricing-tier names were inconsistent (`Founding cohort / Standard / Growth(>₹1Cr)`) vs the business tiers **Launch / Growth / Scale / Enterprise** (BR §15.2). | Relabeled the LLM-cap tier table to Launch/Growth/Scale; aligned the lifecycle pass-through reference; changed "founding cohort phase" → "early-launch phase". |
| **D4** | Medium | `TECH/09` §5 | Said customer-level deletion was "out of scope Phase 1, DPDPA evolving" — contradicts `TECH/16` §4.4 (erasure specified) and DPDP Rules 2025. | Updated to reference TECH/16 erasure workflow; phased per TECH/16 §7 (self-serve Phase 3). |
| **D5** | Minor | `TECH/03` §0.2 | "Brands under ₹25L/month" tied a stat to the abandoned ₹25L floor (now ₹50L). | Reworded to "early-stage Indian D2C brands" (no floor tie). |
| **M1** | Minor | `TECH/09` §5 PII inventory | "Customer address … Required for pincode analytics" understated the minimization default. | Clarified: default **pincode/city-level**; full address only if a workflow requires it + approved (BR §19.3). |

## Coverage gaps found & filled (added to `technical-requirements.md`)

| # | Business requirement | Gap | Fix |
|---|---|---|---|
| **G1** | BR §8.6 Sale/Event Mode | High-frequency event monitoring (expected curve, hourly revenue+CM2 pace, margin-trap alert, Decision Log overlay) was only named in the fulfillment map, not specified. | Added **§16.5 Sale/Event Mode** — reuses metric engine (hourly Path A), anomaly (ML), alerts (TECH/08); cost-routing respected. |
| **G2** | BR §16.3 Onboarding data-quality checks | The onboarding data-quality validation (order/ad reconciliation, ≥80% SKU-cost coverage, identity join, tz/currency/tax, consent) was not specified. | Added **§7.5 Onboarding & data-quality gate** — reports labelled "estimated" until the gate passes; ties to activation metrics (BR §18.5). |
| **G3** | BR §17.4 / §21 Phase 4 Retail extension | Retail-aware (POS/store-level) extension was in the business roadmap but absent from the technical Phase 4. | Added "retail-aware extensions (POS / store-level) where demanded" to the Phase 4 roadmap row. |

## Checked and confirmed already-correct (no change needed)

- Money = integer minor units everywhere (no `NUMERIC`/float money found; the `NUMERIC(20,6)` in `TECH/08 alert_events` is a metric value, not money — correct).
- `TECH/09` audit-log `actor_type` includes `'admin'` — this is an *actor type* (Brain-team admin action), not the workspace RBAC role; correct as-is.
- Model IDs (`claude-sonnet-4-6`, `claude-haiku-4-5`) consistent and current.
- Service boundaries (lifecycle-service separate from notifications-service), Decision Log, region-adapter, tenancy (4 layers), event spine, GST 2.0 (post-reconciliation), per-country VAT, realized-GMV billing — all consistent across docs after v2.0 + this audit.
- External-canon leakage (companion doc, example brand, competitor, vendor domain) — already removed in the v2.0 reconciliation pass.

## Net result
Every business requirement (BR §1–26) now traces to a consistent technical home; the CM/role/pricing definitions agree across all 19 files; the two genuine coverage gaps (event mode, onboarding data-quality) are specified.
