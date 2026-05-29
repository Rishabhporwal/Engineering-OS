---
name: data-quality
description: Correctness + freshness of the analytics transform layer — ingest data contracts, dbt/GE-style assertions, freshness SLAs, the "estimated until the quality gate passes" rule.
---

# Data Quality — Correctness + Freshness of the Transform Layer

> **"Stale data → bad recs"** and **"wrong RTO/COD model"** are named top risks (business §22). `integration-connectors` guards **ingestion** ("did the data arrive?"). This skill guards the **transform** ("is what arrived correct, complete, and fresh enough to compute an authoritative number and bill on it?"). An agent acting on bad data does damage no kill switch can undo after the fact.

The transform DAGs in **analytics-service** turn raw CH facts into the `daily_metrics` master, customer states, RFM, attribution, and the **realized-GMV billing base** — each feeds the 06:55→07:15 Morning Brief loop or `billing.gmv_meter`. A silent transform defect is invisible (the number still renders) and authoritative (an agent acts on it, the brand is billed on it). Owned by **Maya**.

## The Iron Law
```
A METRIC IS AUTHORITATIVE ONLY AFTER ITS DATA-QUALITY GATE PASSES.
UNTIL THEN IT IS LABELLED "ESTIMATED" — NEVER SILENTLY SHOWN AS TRUTH.
```
Stale/incomplete/contract-violating data must **block** the authoritative number, not degrade it quietly. A wrong RTO-adjusted CM2 shown as fact is worse than a clearly-labelled estimate.

**Canon:** `canon/TECH/01_data_architecture.md`, `03_metrics_engine.md`, `15_billing_metering.md`, `02_integrations.md` §7.5.

## Three lines of defense

### 1. Data contracts on ingest (the transform-layer boundary)
Every event off `integrations.*.v1` and every row into a CH canonical table is validated against an explicit contract (schema + type + non-null + enum + range) **before** entering a transform. Avro/Glue enforces shape; the contract adds the semantic constraints the schema can't:
```yaml
# contracts/orders.yml — asserted at the analytics-service consumer boundary
columns:
  workspace_id:      { type: uuid,  not_null: true }                 # cross-tenant guard
  order_total_minor: { type: int64, not_null: true, min: 0 }         # integer minor units — never float
  currency_code:     { type: string, not_null: true, enum: [INR, AED, SAR, USD] }
  financial_status:  { type: enum, values: [paid, pending, refunded, voided, partially_refunded] }
  payment_method:    { type: enum, values: [cod, prepaid, upi, card, netbanking, bnpl] }
  occurred_at:       { type: timestamp, not_null: true, max: now()+5m }  # reject future-dated clock skew
  pincode:           { type: string, pattern: '^[1-9][0-9]{5}$', nullable: true }
```
A violating row is **quarantined** (`analytics.quarantine.v1` + CH `quarantined_rows`), never silently dropped, never let into a metric — caught here, not three transforms downstream where it corrupts an aggregate.

### 2. Assertions on transforms (dbt-test / Great-Expectations-style)
Assert invariants after each transform produces its output, before the table is marked ready:
| Class | Example |
|---|---|
| Row-count anomaly | `daily_metrics` yesterday within ±3σ of trailing-30d (festival spike OK; 90% drop = broken sync) |
| Null-rate | `cm2_minor` null = 0 on delivered orders; `sku_cost_minor` null drives the coverage gate |
| Distribution drift | RTO rate / COD share / AOV shift > threshold vs baseline (the wrong-RTO-model risk) |
| Referential integrity | every `line_item.order_id` resolves; every shipment matches an order or explicit `order_id=NULL` |
| Uniqueness | one `(workspace_id, order_id)` after `ReplacingMergeTree` `FINAL` dedup — dupe = double-counted GMV |
| Range / sign | `billable_gmv_minor ≥ 0`; `placed ≥ billable`; CM2 not impossibly large vs revenue |
| Cross-store reconciliation | Postgres 90-day hot mirror agrees with CH canonical within tolerance |

A failing **critical** assertion blocks the dependent metric and pages; a **warn** assertion labels the metric estimated and alerts.
```python
@assertion(table="daily_metrics", severity="critical")
def cm2_present_on_delivered(ws_id, date):
    bad = ch.count("daily_metrics", f"date='{date}' AND status='delivered' AND cm2_minor IS NULL")
    return bad == 0, f"{bad} delivered rows with null CM2 — blocking daily_metrics for {ws_id}"
```

### 3. Freshness SLAs tied to product SLOs
The *transform output* must be current enough for its consuming surface (distinct from connector freshness).
- **07:20 IST Morning Brief SLO:** daily-tick transforms (06:55 committed → 07:00 fingerprint → metrics materialized) must complete in the 20-min window. A transform whose input is stale at 06:55 must **fail loud and the Brief labels the signal**, never synthesize off yesterday's numbers as current. Backstop monitor `clickhouse-stale` (`max(date) on daily_metrics < now − 30 min`) — `observability`.
- **Realized-GMV metering:** `billing.gmv_meter` (canon/TECH/15) must not finalize on incomplete data — the provisional → T+35 final true-up encodes "don't bill on unsettled data" (RTO resolves ~30d late). The gate marks a meter row safe to finalize: reconciliation passed, no quarantined orders, coverage met.

## The estimated→authoritative gate (canon §7.5)
Reports stay **"estimated"** until the gate passes for the workspace: order+ad reconciliation within tolerance · **≥80% SKU-cost coverage** (without COGS, CM1/CM2 are guesses — and CM2 decides scaling) · identity-join complete · timezone/currency/tax validated (GST per-SKU slab, not blended) · consent state ingested. Until all pass, UI shows the estimated label, **no agent auto-executes**, **no GMV invoice issues**. Crossing is a state transition logged in core-service, not a vibe.

## Alerting + quarantine on failure
```
contract violation  → quarantine row (analytics.quarantine.v1)        → P3 if rate spikes
critical assertion  → BLOCK dependent metric, mark estimated, page     → P2 (Morning Brief at risk)
freshness breach    → label affected signal estimated, alert           → P2 if Brief window
reconciliation gap  → hold GMV meter at provisional, flag              → P2 (billing correctness)
distribution drift  → flag metric, alert Maya                          → P3
```
Never auto-resolve by guessing. Quarantine → label → alert → root-cause (`systematic-debugging`) → replay from Kafka (infinite retention → every materialization rebuildable) → re-run assertions before re-promoting.

## Red flags — STOP and BOUNCE
New transform with **no assertions** · metric shown authoritative before the gate passes · **GMV meter finalized on un-reconciled data** · contract violation silently dropped instead of quarantined · "connector says healthy" used as a proxy for "data is correct" (auth-OK ≠ data-OK) · a transform that degrades quietly (yesterday's number as today's) · `<80%` SKU-cost coverage but CM2 surfaced as fact · no row-count/volume guard.

## Rationalization prevention
| Excuse | Reality |
|---|---|
| "The connector freshness alert covers it" | That covers *arrival*. A transform can join stale dims onto fresh facts and produce a wrong number on time. |
| "The number renders fine" | Rendering proves nothing about correctness — that's why silent transform bugs are dangerous. |
| "We'll reconcile at month-end" | An agent acts on the daily number today; late reconciliation can't unwind a wrong action. |
| "80% is close enough to 100%" | 80% is the floor *to leave estimated*. Below it, CM2 (which decides scaling) is a guess. |
| "Distribution shift is just the festival" | The assertion is festival-aware; an *unexpected* shift is the wrong-RTO-model risk surfacing. |

## When to apply
Any PR adding/changing an analytics transform, metric materialization, GMV meter, or CH rollup · a number disagrees between web and the daily tick (or Postgres mirror vs CH) · onboarding a workspace (the gate) · adding a data source whose facts feed metrics.

## Wiring
contracts+assertions → Maya · quarantine+DLQ+replay → Maya · freshness SLO+monitors → Maya+Jatin · GMV-meter quality gate → Maya+core-service · TS↔Python parity → Tanvi.

Related: `integration-connectors` (ingestion freshness — upstream half), `clickhouse-olap`, `metric-engine`, `billing-metering`, `observability`, `systematic-debugging`, `testing-tdd`, `india-commerce-economics`.
