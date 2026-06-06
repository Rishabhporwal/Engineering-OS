---
name: data-quality
description: Correctness + freshness of the analytics transform layer — ingest data contracts, dbt/GE-style assertions, freshness SLAs, the "estimated until the quality gate passes" rule.
---

# Data Quality — Correctness + Freshness of the Transform Layer

> **"Stale data → bad decisions"** and **"wrong model"** are common top risks (the Canon's risk register). `integration-connectors` guards **ingestion** ("did the data arrive?"). This skill guards the **transform** ("is what arrived correct, complete, and fresh enough to compute an authoritative number and act/bill on it?"). An automated action on bad data does damage no kill switch can undo after the fact.

The transform DAGs turn raw facts into the canonical metric tables, derived states, and any billing/metering base — each feeds a decision surface or a financial meter. A silent transform defect is invisible (the number still renders) and authoritative (something acts on it, the customer may be billed on it). Owned by the **AI/ML Engineer** (or whoever owns the transform layer in the Canon).

## The Iron Law
```
A METRIC IS AUTHORITATIVE ONLY AFTER ITS DATA-QUALITY GATE PASSES.
UNTIL THEN IT IS LABELLED "ESTIMATED" — NEVER SILENTLY SHOWN AS TRUTH.
```
Stale/incomplete/contract-violating data must **block** the authoritative number, not degrade it quietly. A wrong financial metric shown as fact is worse than a clearly-labelled estimate.

**Canon:** the Product Canon's `METRICS.md` (the metric registry) + the data-architecture HLD/LLD + the metering/billing spec where one exists.

## Three lines of defense

### 1. Data contracts on ingest (the transform-layer boundary)
Every event off the ingest stream and every row into a canonical table is validated against an explicit contract (schema + type + non-null + enum + range) **before** entering a transform. A schema registry enforces shape; the contract adds the semantic constraints the schema can't:
```yaml
# contracts/orders.yml — asserted at the transform consumer boundary
columns:
  tenant_id:         { type: uuid,  not_null: true }                 # cross-tenant guard
  order_total_minor: { type: int64, not_null: true, min: 0 }         # integer minor units — never float
  currency_code:     { type: string, not_null: true }                # required alongside every money field
  financial_status:  { type: enum, values: [paid, pending, refunded, voided, partially_refunded] }
  payment_method:    { type: enum }
  occurred_at:       { type: timestamp, not_null: true, max: now()+5m }  # reject future-dated clock skew
```
A violating row is **quarantined** (a dedicated quarantine stream + table), never silently dropped, never let into a metric — caught here, not three transforms downstream where it corrupts an aggregate.

### 2. Assertions on transforms (dbt-test / Great-Expectations-style)
Assert invariants after each transform produces its output, before the table is marked ready:
| Class | Example |
|---|---|
| Row-count anomaly | a daily table's row count within ±3σ of trailing-30d (a known seasonal spike OK; a 90% drop = broken sync) |
| Null-rate | a derived money field null = 0 on completed records; an input-cost null drives the coverage gate |
| Distribution drift | a key rate / share / average shifts > threshold vs baseline (the "wrong model" risk) |
| Referential integrity | every `line_item.order_id` resolves; every shipment matches an order or an explicit `order_id=NULL` |
| Uniqueness | one `(tenant_id, order_id)` after dedup — a dupe = double-counted money |
| Range / sign | a money field `≥ 0`; a derived margin not impossibly large vs revenue |
| Cross-store reconciliation | the OLTP hot mirror agrees with the OLAP canonical within tolerance |

A failing **critical** assertion blocks the dependent metric and pages; a **warn** assertion labels the metric estimated and alerts.
```python
@assertion(table="daily_metrics", severity="critical")
def margin_present_on_completed(tenant_id, date):
    bad = olap.count("daily_metrics", f"date='{date}' AND status='completed' AND margin_minor IS NULL")
    return bad == 0, f"{bad} completed rows with null margin — blocking daily_metrics for {tenant_id}"
```

### 3. Freshness SLAs tied to product SLOs
The *transform output* must be current enough for its consuming surface (distinct from connector freshness).
- **Decision-surface SLO:** the transforms feeding a time-boxed decision surface must complete within their window. A transform whose input is stale at the cutoff must **fail loud and the surface labels the signal**, never synthesize off yesterday's numbers as current. Backstop monitor: `max(date) on the canonical table < now − threshold` — see `observability`.
- **Metering / billing:** a financial meter must not finalize on incomplete data — a provisional → later-final true-up encodes "don't bill on unsettled data" (e.g. when refunds/returns resolve late). The gate marks a meter row safe to finalize: reconciliation passed, no quarantined records, coverage met.

## The estimated→authoritative gate
Reports stay **"estimated"** until the gate passes for the tenant: source reconciliation within tolerance · **≥ the Canon's input-coverage threshold** (without complete inputs, derived margins are guesses — and margin often decides scaling decisions) · identity-join complete · timezone/currency/tax validated · consent state ingested. Until all pass, the UI shows the estimated label, **no automated action executes**, **no invoice issues**. Crossing is a logged state transition, not a vibe.

## Alerting + quarantine on failure
```
contract violation  → quarantine row                                  → low sev if rate spikes
critical assertion  → BLOCK dependent metric, mark estimated, page     → high sev (decision surface at risk)
freshness breach    → label affected signal estimated, alert           → high sev if in a decision window
reconciliation gap  → hold the meter at provisional, flag              → high sev (billing correctness)
distribution drift  → flag metric, alert the transform owner           → low/medium sev
```
Never auto-resolve by guessing. Quarantine → label → alert → root-cause (`systematic-debugging`) → replay from the event log (retained → every materialization rebuildable) → re-run assertions before re-promoting.

## Red flags — STOP and BOUNCE
New transform with **no assertions** · metric shown authoritative before the gate passes · **a financial meter finalized on un-reconciled data** · contract violation silently dropped instead of quarantined · "connector says healthy" used as a proxy for "data is correct" (auth-OK ≠ data-OK) · a transform that degrades quietly (yesterday's number as today's) · below-coverage-threshold inputs but a derived margin surfaced as fact · no row-count/volume guard.

## Rationalization prevention
| Excuse | Reality |
|---|---|
| "The connector freshness alert covers it" | That covers *arrival*. A transform can join stale dims onto fresh facts and produce a wrong number on time. |
| "The number renders fine" | Rendering proves nothing about correctness — that's why silent transform bugs are dangerous. |
| "We'll reconcile at month-end" | Something acts on the daily number today; late reconciliation can't unwind a wrong action. |
| "Close enough to full coverage" | The coverage threshold is the floor *to leave estimated*. Below it, the margin that decides scaling is a guess. |
| "The shift is just seasonality" | The assertion is seasonality-aware; an *unexpected* shift is the wrong-model risk surfacing. |

## When to apply
Any PR adding/changing an analytics transform, metric materialization, financial meter, or OLAP rollup · a number disagrees between two surfaces (or OLTP mirror vs OLAP) · onboarding a tenant (the gate) · adding a data source whose facts feed metrics.

## Wiring
contracts+assertions → AI/ML Engineer · quarantine+DLQ+replay → AI/ML Engineer · freshness SLO+monitors → AI/ML Engineer + Platform/SRE · meter quality gate → AI/ML Engineer + the OLTP owner · cross-runtime metric parity → QA Engineer.

Related: `integration-connectors` (ingestion freshness — upstream half), `clickhouse-olap`, `metric-engine`, `observability`, `systematic-debugging`, `testing-tdd`.
