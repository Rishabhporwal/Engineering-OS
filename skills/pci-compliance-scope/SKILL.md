---
name: pci-compliance-scope
description: Brain's PCI-DSS scope boundary + SAQ-A posture. Brain NEVER stores card numbers / CVV / full UPI IDs / full bank accounts (canon §21.1); all payment capture is delegated to licensed rails (Razorpay/Stripe) via redirect or hosted iframe, which keeps Brain OUT of the cardholder-data environment and on the lightest validation tier, SAQ-A. Covers what would PULL Brain into scope (and why we never do it), how the billing-metering invoice flow stays SAQ-A, and the crisp answer to "what's your PCI scope?" in an enterprise security review. Use when wiring any payment/invoice flow, integrating a payment connector, or answering a security questionnaire. Owner: Shreya.
---

# PCI compliance scope — Brain is SAQ-A by design

Brain is an analytics + execution OS, **not** a payment processor. It never touches a primary account number (PAN). The single architectural decision that makes this true — *delegate all card capture to a licensed gateway via redirect/hosted fields* — is what keeps Brain on **SAQ-A**, the lightest PCI-DSS validation tier (a ~22-question self-assessment), instead of SAQ-D (300+ controls, on-site assessment, the cost of a small team). This skill defends that boundary.

> **The one rule:** *cardholder data never enters a Brain system, server, log, database, or network segment.* If a feature would require Brain to receive, transmit, or store a PAN/CVV, the answer is no — route it through the gateway instead.

**Canonical source:** technical-requirements §21.1 (never-store list), TECH/16 §4.1, TECH/15 (billing on licensed rails). Standard: **PCI-DSS v4.0.1** (v4.0 retired 31 Dec 2024; v4.0.1 is the in-force version, all future-dated requirements live as of 31 Mar 2025). Owned by **Shreya** (security/compliance VETO).

## What Brain never stores (the scope-defining list)

Per canon §21.1 — hard-coded into the data model, enforced by `data-privacy-dpdp` minimization:

- **Card number (PAN), CVV/CVC, expiry, track data, PIN** — never. Not in Postgres, ClickHouse, S3, Redis, Kafka, or logs.
- **Full UPI VPA, full bank account numbers, IFSC-linked account details** — never (these are India's equivalent sensitive payment data).
- What Brain *does* store: a **payment method classification** (`card | upi | cod | wallet | bnpl`, from `RegionAdapter.classify_payment_method`), a **gateway transaction/order reference token** (opaque, issued by Razorpay/Stripe), settlement amounts in **minor units**, and payment *status*. None of these are cardholder data.

Because no PAN ever enters a Brain system, Brain's **cardholder-data environment (CDE) is empty** — and an empty CDE is the whole game.

## How the boundary is built — redirect / hosted fields

Two compliant integration shapes, both keeping the PAN off Brain's surfaces:

```
Customer's commerce checkout (the BRAND's store)        Brain's own SaaS fee invoice
   │  card entered on Shopify / Razorpay / Stripe          │  Brain bills brand its %-GMV fee
   ▼  hosted page or PCI-validated iframe                   ▼  Razorpay (INR) / Stripe (intl) hosted
gateway captures + tokenizes the PAN                     gateway-hosted payment page / Checkout
   │  Brain only ever ingests via webhook/API:              │  Brain stores only:
   ▼     order ref, amount(minor), status, method-class     ▼     provider_invoice_id, status, amount
Brain DB / events  ──  NO PAN, NO CVV, ever              billing.invoices  ──  NO card data
```

- **Redirect:** customer/operator lands on the gateway's own page; PAN entered there; Brain gets a callback with a token. Strongest isolation.
- **Hosted fields / iframe (SAQ-A eligible under v4.0.1):** the card input is an iframe served *by the gateway* embedded in a Brain/brand page; the DOM Brain controls never sees the PAN. v4.0.1 added requirements **6.4.3** (manage all scripts on the payment page) + **11.6.1** (tamper/change detection on the payment page) for this model — if Brain ever embeds gateway iframes directly, those two apply; pure redirect avoids even those.

## Billing-metering stays SAQ-A too

Brain charging its **own** fee (% of realized GMV, TECH/15) is itself a payment — and it stays out of scope the same way. `billing.invoices` routes by currency to a **licensed rail** (Razorpay for INR, Stripe for AED/SAR/USD in Phase 4); the brand pays on the **gateway-hosted** page; Brain persists only `provider_invoice_id`, status, `total_minor`, and `currency_code`. No card-on-file is stored by Brain — if recurring/auto-charge is added, it uses the **gateway's** tokenization/mandate vault (Razorpay subscriptions / Stripe customer + payment-method tokens), never a Brain-stored card. Dunning toggles feature degradation (analytics stay, outbound pauses) off invoice *status*, never off card data.

## What would PULL Brain into scope — and we never do it

Each of these would create a CDE and force SAQ-D — all are prohibited:

- **Receiving a raw PAN/CVV** in any API request, webhook payload, form field Brain controls, or CSV import. (Even transiently in memory counts.)
- **Logging or caching** a card number / CVV — `data-privacy-dpdp` redaction + the Fluent Bit Lua scrub already strip token/secret patterns; a PAN must be added to the never-log set if any path could carry one.
- **Storing card-on-file** ourselves instead of using the gateway vault.
- **Proxying card data** between a brand's checkout and a processor (becoming a transmission point).
- **Building our own checkout form** that collects card fields into Brain-controlled DOM/inputs (this is exactly what hosted fields exist to prevent).

A PR that introduces any of the above is a Shreya **VETO** — same gravity as a cross-tenant leak.

## The enterprise security-review answer

When a prospect's security team asks *"What's your PCI-DSS scope?"*:

> "Brain does not store, process, or transmit cardholder data. All payment capture — both our customers' commerce checkouts and our own SaaS-fee billing — is delegated to PCI-DSS Level 1 service providers (Razorpay, Stripe) via redirect/hosted fields. Brain ingests only opaque transaction references, amounts, status, and a payment-method classification. Our cardholder-data environment is empty, so Brain validates as **SAQ-A** under PCI-DSS v4.0.1. We can share our gateways' AOCs and our SAQ-A on request."

Keep on file for the security FAQ (TECH/09 §9 Phase-1 deliverable): the gateways' **Attestations of Compliance (AOC)**, their entry in the Visa/Mastercard service-provider registries, and Brain's own completed SAQ-A.

## Anti-patterns (code-review blockers / Shreya VETO)

- Any field, column, log line, or event envelope that could carry a **PAN/CVV/full UPI/full bank account**.
- A Brain-controlled **card input form** (instead of gateway redirect/hosted fields).
- **Storing card-on-file** in Brain rather than using the gateway vault for recurring charges.
- Treating PCI as "the gateway's problem" while **embedding gateway scripts** without 6.4.3/11.6.1 controls when hosted fields are used.
- Asserting "we're SAQ-A" with **no SAQ on file** and no gateway AOCs collected.

## Verify

- Grep the schema + event schemas (`protos/events/`) + log redaction set: no `card_number`/`pan`/`cvv`/`vpa`/`account_number` field exists or is loggable.
- Trace every payment path (commerce ingestion + `billing.invoices`): each terminates at a gateway redirect/hosted page; Brain persists only references + amounts + status.
- The security FAQ contains the SAQ-A statement + links to gateway AOCs.

## References
- technical-requirements §21.1 — the never-store list (scope-defining)
- TECH/16 §4.1 — data minimization (PII + payment data)
- TECH/15 — billing on licensed rails (Razorpay/Stripe), provider routing by currency
- [`billing-metering`](../billing-metering/SKILL.md) — invoice flow + provider routing
- [`security-baseline`](../security-baseline/SKILL.md) — Shreya VETO + the broader posture
- [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) — minimization + redaction enforcing the never-store list
