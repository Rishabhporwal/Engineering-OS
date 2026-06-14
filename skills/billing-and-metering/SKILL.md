---
name: billing-and-metering
description: Reference implementation — usage-based billing: the metering→rating→invoicing→reconciliation pipeline. Idempotent usage events (never lose, never double-bill), event-time aggregation, tiered/prepaid/proration rating, immutable invoices + credit-note corrections, an append-only ledger, PCI SAQ-A boundary, and the mandatory meter↔invoice↔payment↔ledger reconciliation. Owner Backend Engineer.
---

# Billing & Metering (Reference Patterns)

> **Reference implementation.** One concrete binding of the **billing/metering seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — `STACK.md` may bind it to Stripe Billing (Meters), Metronome, Orb, Lago (OSS), or OpenMeter. The *patterns* — idempotent metering, event-time aggregation, immutable invoices, an append-only ledger, tokenize-never-touch-the-card, and continuous reconciliation — transfer; the vendor is the example. **Money correctness is the whole job: never lose a usage event, never double-bill.**

**Owner:** Backend Engineer (the pipeline) + Data Engineer (the high-volume metering aggregation); Security Reviewer gates the PCI boundary + the audit trail. Canon: `STACK.md`, `COMPLIANCE.md`. This is a **high-stakes path** (`gate_check` / mutation-tested).

## Invariants (NON-NEGOTIABLE)
1. **Money is an integer count of the currency's minor unit + an explicit `currency_code`** — never a float (`metric-engine`). And **never assume ×100**: the minor-unit exponent is per-currency (JPY = 0-decimal; KWD/BHD/OMR = 3-decimal /1000). A hardcoded ×100 mis-bills ~10% of currencies.
2. **Never lose a usage event.** Durably persist the **raw** event *before* acking (inbox/outbox); at-least-once + replay + checkpoint. The raw event is the source you re-rate from.
3. **Never double-bill.** Every event carries a client-supplied **idempotency/dedup key**; ingestion dedups atomically. At-least-once *guarantees* duplicates — so chase exactly-once *effect* (at-least-once + idempotent sink), never exactly-once *delivery* (impossible).
4. **Never mutate a finalized invoice or a closed period.** Correct via **credit notes** or void→re-issue; late usage after period close → **correction events forward**, never overwrite a historical aggregate. **Never overwrite a ledger balance** — append-only double-entry; balances are *derived* from immutable debits/credits (this IS the audit trail).
5. **Never touch a raw card number.** Tokenize via the provider's client-side element loaded from the provider's domain → stay in **PCI SAQ-A**. Constructing the payment iframe server-side or self-hosting the provider JS drops you to SAQ A-EP (bigger scope).
6. **Never skip the reconciliation loop, and never bill without an immutable audit/decision log.** Continuously reconcile **meter ↔ invoice ↔ payment ↔ ledger**; every line item traces raw input → derived quantity → rating decision (who/what/when/why) → `decision-log`. The tenant key rides every event/aggregate/invoice/ledger-entry — a cross-tenant billing leak is a P0 (`multi-tenancy-isolation`).

## The pipeline
```
Ingest (at-least-once, dedup key, durable raw)
  → Aggregate (per tenant×meter×period; EVENT-TIME + watermarks; late events re-agg the OPEN period)
  → Rate (price plans + prepaid-credit drawdown + proration + min-commit true-up)
  → Invoice (draft → FINALIZE=immutable → pay; corrections = credit notes)
  → Collect (dunning / smart retries; halt on hard declines)
  → Reconcile (append-only double-entry ledger)
```

### Idempotent ingestion — the atomic claim (the #1 double-bill fix)
The classic bug is check-then-insert (a race). Make it atomic:
```sql
INSERT INTO processed_events (event_id, tenant_id, processed_at)
VALUES ($1, $2, now())
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id;          -- empty result ⇒ already processed ⇒ skip the side effect
```
**Dedup windows are finite — know your provider's.** Stripe meter-event `identifier` uniqueness is "a rolling period of **at least 24 hours**," but its ingestion *backdating* window is **35 days** — a duplicate arriving >24h later may not be caught, so **dedup long-horizon yourself** if you replay (OpenMeter ~32d, Lago on `transaction_id`).

### Aggregation
**Event-time, not processing-time** + watermarks bound completeness; a late event after period close becomes a correction, never an overwrite (mirrors `stream-processing-flink`). Note provider limits: **Stripe meters do only `sum`/`count`/`last`** — anything else (peak-concurrent, daily-avg) you compute and report as `last`. Stripe meters track usage **per customer, not per subscription** — per-project billing needs separate customers or your own split.

### Rating — pin to the math, not the overloaded word
| Model | Rule |
|---|---|
| **Graduated** (`tiers_mode=graduated`) | each tier's units at *that* tier's rate, summed |
| **Volume** (`tiers_mode=volume`) | **all** units at the rate of the tier the total lands in |
| **Package** (`transform_quantity`) | priced per block of N (round up) |
Plus prepaid credit wallets (usage draws down a balance), minimum-commitment true-up (charge the period-end shortfall), and proration (credit unused old + charge remaining new). **Rounding:** decide *where* (per-line vs invoice-total — they legitimately differ by cents, some jurisdictions mandate one) and *which rule* (banker's/round-half-even), and **allocate the residual cent deterministically** so nothing is lost.

### Webhooks (idempotent, order-independent)
Verify the signature on the **raw** body (don't set tolerance 0); dedup on the event ID (atomic claim); process **order-independently** — providers don't guarantee delivery order or once-only delivery and redeliver for days.

## Build vs buy (2026)
Even Stripe and Salesforce *bought* metering rather than build — roll-your-own is rarely justified.
| Option | When |
|---|---|
| **Stripe Billing (Meters)** | simple metered SaaS, modest volume (accept the usage-fee + per-customer-not-per-sub limit) |
| **Metronome** (Stripe-owned, Jan 2026) | complex/real-time AI billing at scale (powers OpenAI/Anthropic/NVIDIA) |
| **Orb** | complex rating + rev-rec, per-sub granularity; Stripe as the rail |
| **Lago / OpenMeter** (OSS, self-host) | data-control/cost/high-volume metering; Lago wallets-first; OpenMeter CloudEvents + multi-PSP |
**Canonical pattern:** usage event → aggregate/rate in the metering layer → push finalized invoices (or meter events) to the payment provider for collection. **Stripe's legacy `UsageRecord` API is REMOVED (not deprecated)** as of API `2025-03-31.basil` — use **Billing Meters + Meter Events** (`/v1/billing/meter_events` + a dedup `identifier`; the v2 Meter Event Stream does ≤100k ev/s).

## Effort-tier & cost note (`cost-routing-paradigms`)
Metering + rating + reconciliation are **deterministic compute** — never let an LLM produce a billed number (`metric-engine`; the gateway's "model only narrates" rule). High-volume metering (10⁴–10⁵ events/s) is a Kafka→idempotent-dedup→OLAP (ClickHouse/StarRocks) pre-aggregation problem (`stream-processing-consumers`, `event-driven-kafka`), not an app-DB problem.

## Anti-patterns
Money as a float / hardcoded ×100 · ack-before-persist (lost events) · check-then-insert dedup (race → double-bill) · no client dedup key · dedup window too short for your replay horizon · mutating a finalized invoice / overwriting a closed period / overwriting a ledger balance · touching raw PAN (PCI scope blowup) · trusting webhook order/once-only · proration surprises (negative not refunded, positive silently held) · **enforcement lagging metering → bill shock** (the Cursor-2025 episode: communicate + cap before switching pricing) · no meter↔invoice↔payment↔ledger reconciliation · no audit/decision-log trace from raw input to charge · a billing query/row without the tenant key.

## References
`metric-engine` (money = minor units; deterministic numbers) · `decision-log` (the billing audit trail) · `idempotency-handling` (dedup keys, webhook handlers) · `multi-tenancy-isolation` (tenant key on every billing row) · `compliance-attestation` (PCI SAQ-A boundary; Security Reviewer gate) · `event-driven-kafka` / `stream-processing-consumers` (high-volume metering) · `data-layer` (the control-plane billing tables) · `region-and-locale` (currency/locale formatting at display).
