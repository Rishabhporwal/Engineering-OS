---
name: data-quality
description: Data-pipeline correctness + freshness for the analytics/transform layer — the DAGs that turn raw ingested facts into the daily_metrics master, the Decision Log outcome attribution, and the realized-GMV billing base. Covers data contracts on ingest (schema/type/non-null/enum), assertions (row-count anomaly, null-rate, distribution/volume drift, referential integrity), freshness SLAs tied to the 07:20 IST Morning Brief SLO and realized-GMV metering, and the gate that labels reports "estimated" until quality passes (≥80% SKU-cost coverage + reconciliation). dbt-test / Great-Expectations-style checks, alerting + quarantine on failure. "Bad data → bad recs" is a named top risk. Use when building/changing an analytics transform, a metric materialization, the GMV meter, or debugging a number that disagrees. Distinct from `integration-connectors` (ingestion freshness) — this is the TRANSFORM layer.
---

# Data Quality — Correctness + Freshness of the Transform Layer

> **"Stale data → bad recs"** and **"wrong RTO/COD model"** are two of the named top risks in business §22. The P0-connector freshness alert (`integration-connectors`) guards **ingestion** — "did the data arrive?". This skill guards the **transform** — "is the data that arrived correct, complete, and fresh enough to compute an authoritative number and bill on it?" An agent that recommends off bad data does damage no kill switch can undo after the fact.

Brain's first obligation is **Truth**: every number auditable, reproducible, traceable to source events; LLMs never invent numbers (`metric-engine`). That obligation is only as strong as the data feeding the metric engine. The transform DAGs in **analytics-service** turn raw ClickHouse facts into the `daily_metrics` master, customer states, RFM, attribution, and the **realized-GMV billing base** — every one of those feeds either the **06:55→07:15 Morning Brief loop** or `billing.gmv_meter`. A silent transform defect there is invisible (the number still renders) and authoritative (an agent acts on it, the brand is billed on it).

## The Iron Law

```
A METRIC IS AUTHORITATIVE ONLY AFTER ITS DATA-QUALITY GATE PASSES.
UNTIL THEN IT IS LABELLED "ESTIMATED" — NEVER SILENTLY SHOWN AS TRUTH.
```

Stale, incomplete, or contract-violating data must **block** the authoritative number, not degrade it quietly. A wrong RTO-adjusted CM2 surfaced as fact is worse than a clearly-labelled estimate.

**Canonical docs:** `canon/TECH/01_data_architecture.md` (data layer), `canon/TECH/03_metrics_engine.md` (metric registry), `canon/TECH/15_billing_metering.md` (GMV meter), `canon/TECH/02_integrations.md` §7.5 (onboarding gate). Owned by **Maya** (analytics-service transforms + metric materializations).

## Three lines of defense

### 1. Data contracts on ingest (the boundary into the transform layer)

Every canonical event consumed off `integrations.*.v1` and every row inserted into a ClickHouse canonical table is validated against an explicit contract **before** it enters a transform. Contract = schema + type + non-null + enum + range. The Avro schema in Glue Schema Registry enforces shape; the contract adds semantic constraints the schema can't:

```yaml
# contracts/orders.yml — asserted at the analytics-service consumer boundary
columns:
  workspace_id:    { type: uuid,   not_null: true }                 # cross-tenant guard
  order_total_minor: { type: int64, not_null: true, min: 0 }        # integer minor units — never float
  currency_code:   { type: string, not_null: true, enum: [INR, AED, SAR, USD] }
  financial_status: { type: enum, values: [paid, pending, refunded, voided, partially_refunded] }
  payment_method:  { type: enum, values: [cod, prepaid, upi, card, netbanking, bnpl] }
  occurred_at:     { type: timestamp, not_null: true, max: now()+5m } # reject future-dated clock skew
  pincode:         { type: string, pattern: '^[1-9][0-9]{5}$', nullable: true } # India 6-digit
```

A row that violates the contract is **quarantined** (DLQ-style `analytics.quarantine.v1` + ClickHouse `quarantined_rows`), never silently dropped and never let into a metric. Float money, an unknown currency, a future timestamp, a missing `workspace_id` — all caught here, not three transforms downstream where they corrupt an aggregate.

### 2. Assertions on the transforms (dbt-test / Great-Expectations-style)

After each transform produces its output table, assert invariants before the table is marked ready. These are the data-engineering equivalent of unit tests, run on every materialization:

| Assertion class | Example for Brain |
|---|---|
| **Row-count anomaly** | `daily_metrics` row count for yesterday within ±3σ of trailing-30d (a festival spike is expected; a 90% drop is a broken sync) |
| **Null-rate** | `cm2_minor` null rate = 0 on delivered orders; `sku_cost_minor` null rate drives the coverage gate (below) |
| **Distribution / volume drift** | RTO rate, COD share, AOV distribution shift > threshold vs trailing baseline → flag (the wrong-RTO-model risk) |
| **Referential integrity** | every `line_item.order_id` resolves to an `orders` row; every shipment matches an order or is explicitly `order_id = NULL` (per `integration-connectors`) |
| **Uniqueness** | one `(workspace_id, order_id)` after `ReplacingMergeTree(version)` `FINAL` dedup — duplicate = double-counted GMV |
| **Range / sign** | `billable_gmv_minor ≥ 0`; `placed ≥ billable`; CM2 not impossibly large vs revenue |
| **Cross-store reconciliation** | Postgres 90-day hot mirror agrees with ClickHouse canonical within tolerance (the "healthy auth but stale data" trap) |

Assertions run as part of the scheduled Python rollups (join-heavy metrics) and as Materialized-View post-checks. A failing critical assertion **blocks** the dependent metric and pages; a failing warn-level assertion labels the metric estimated and alerts.

```python
@assertion(table="daily_metrics", severity="critical")
def cm2_present_on_delivered(ws_id, date):
    # CM2 is THE most important metric (business §6). Missing CM2 on a delivered order = blocker.
    bad = ch.count("daily_metrics", f"date='{date}' AND status='delivered' AND cm2_minor IS NULL")
    return bad == 0, f"{bad} delivered rows with null CM2 — blocking daily_metrics for {ws_id}"
```

### 3. Freshness SLAs tied to the product SLOs

Freshness here means the *transform output* is current enough for the surface that consumes it — distinct from the connector freshness in `integration-connectors`.

- **07:20 IST Morning Brief SLO:** the daily-tick transforms (06:55 data committed → 07:00 fingerprint → metrics materialized) must complete in the 20-minute window. A transform whose input is stale at 06:55 must **fail loud and the Brief labels the affected signal**, not synthesize off yesterday's numbers as if current. `observability` monitor `clickhouse-stale` (max(date) on `daily_metrics` < now − 30 min) is the backstop.
- **Realized-GMV metering:** `billing.gmv_meter` is computed from delivered ClickHouse facts (`canon/TECH/15`). The meter must not finalize on incomplete data — the **provisional → T+35 final true-up** flow already encodes "don't bill on data that hasn't settled" (RTO resolves ~30d late). The data-quality gate is what marks a meter row safe to finalize: reconciliation passed, no quarantined orders in the period, coverage met.

## The onboarding / authoritative-metric gate (canon TECH §7.5)

Reports stay labelled **"estimated"** until the data-quality gate passes for the workspace. The gate requires:

- order + ad reconciliation (placed vs reported agrees within tolerance),
- **≥80% SKU-cost coverage** (without COGS, CM1/CM2 are guesses — and CM2 is the metric that decides scaling),
- identity-join complete (customers de-duplicated across sources),
- timezone / currency / tax extraction validated (GST per-SKU slab, not blended — `india-commerce-economics`),
- consent state ingested.

Until all pass, the UI shows the explicit estimated label and **no agent auto-executes** and **no GMV invoice issues** off those numbers. Crossing the gate is a state transition logged in core-service, not a vibe.

## Alerting + quarantine on failure

```
contract violation  → quarantine row (analytics.quarantine.v1)        → P3 if rate spikes
critical assertion  → BLOCK dependent metric, mark estimated, page     → P2 (Morning Brief at risk)
freshness breach    → label affected signal estimated, alert           → P2 if Brief window
reconciliation gap  → hold GMV meter at provisional, flag for review   → P2 (billing correctness)
distribution drift  → flag metric, alert Maya (possible model/data shift) → P3
```

Never auto-resolve a quality failure by guessing. Quarantine, label, alert, fix the root cause (`systematic-debugging`), replay from Kafka (topics are infinite-retention → every materialization is rebuildable), then re-run assertions before re-promoting the metric.

## Red flags — STOP and BOUNCE

- A new transform with **no assertions** — it can corrupt a metric silently.
- A metric shown as **authoritative before the gate passes** (no estimated label, agent acting on it).
- **GMV meter finalized on un-reconciled data** — billing on numbers that haven't settled.
- A contract violation **silently dropped** instead of quarantined (you lose the row *and* the signal).
- "Connector says healthy" used as a proxy for "data is correct" — auth-OK ≠ data-OK (named anti-pattern).
- A transform that **degrades quietly** (shows yesterday's number as today's) instead of failing loud.
- `< 80%` SKU-cost coverage but CM2 surfaced as fact.
- No row-count / volume guard, so a half-finished sync produces a plausible-but-wrong aggregate.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "The connector freshness alert covers it" | That covers *arrival*. A transform can join stale dims onto fresh facts and produce a wrong number that arrived on time. |
| "The number renders fine" | Rendering proves nothing about correctness — that's exactly why silent transform bugs are the dangerous ones. |
| "We'll reconcile at month-end" | An agent acts on the daily number *today*; the brand is billed on the meter. Late reconciliation can't unwind a wrong action. |
| "80% coverage is close enough to 100%" | 80% is the canon floor *to leave estimated*. Below it, CM2 is a guess and CM2 decides whether to scale spend. |
| "Distribution shift is just the festival" | Maybe — the assertion is festival-aware (`india-commerce-economics`); an *unexpected* shift is the wrong-RTO-model risk surfacing. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Contracts + assertions on analytics transforms | **Maya** (analytics-service) | `clickhouse-olap`, `metric-engine` |
| Quarantine + DLQ + replay | **Maya** | `event-driven-kafka`, `integration-connectors` |
| Freshness SLO wiring + monitors | **Maya** + **Jatin** | `observability` (`clickhouse-stale`) |
| GMV-meter quality gate (don't finalize on bad data) | **Maya** + core-service | `billing-metering` |
| TS↔Python metric parity (a quality dimension) | **Tanvi** gates | `metric-engine`, `testing-tdd` |

## When to apply

- Any PR that adds or changes an **analytics transform, a metric materialization, the GMV meter**, or a ClickHouse rollup.
- When a number **disagrees** between web and the daily tick, or between Postgres mirror and ClickHouse (`systematic-debugging` + this).
- When onboarding a new workspace (the estimated→authoritative gate), or adding a new data source whose facts feed metrics.

## The bottom line

Brain bets its entire value on Truth. The transform layer is where Truth is either preserved or quietly broken. Contract the inputs, assert the transforms, tie freshness to the surfaces that consume the output, and block — don't degrade — when a check fails. A wrong number that renders cleanly is the most expensive bug Brain can ship.

Related: `integration-connectors` (ingestion freshness — the upstream half), `clickhouse-olap` (where transforms run), `metric-engine` (the single definition + TS↔Python parity), `billing-metering` (the realized-GMV base this gate protects), `observability` (`clickhouse-stale` + alerting), `systematic-debugging` (root-causing a quality failure), `testing-tdd` (assertions as tests), `india-commerce-economics` (RTO/COD/GST correctness the assertions defend).
