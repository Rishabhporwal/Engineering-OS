---
name: memory-layer-pgvector
description: The Memory Layer — THE MOAT with the Decision Log. 5 subsystems (Brand Fingerprint, Condition-Outcome, Cross-Brand k≥5, Seasonal, Segment RFM); HNSW pgvector; SQL/ML economics.
---

# Memory Layer — the moat at SQL economics

**Memory Is the Moat.** A competitor with the same dashboards and integrations cannot match a brand's Brain after 12 months of accumulated condition-outcome pairs. The Memory Layer (canon/TECH/05 §0) lives in `intelligence-service` over Postgres + **pgvector**, and — crucially — **almost every operation is SQL or ML (paradigm 1/2), not LLM.** That's why Brain can query it constantly: every agent, every daily tick.

> Don't confuse this with the **Engineering OS's** own semantic index (`.engineering-os/index`, [`recall-similar`](../recall-similar/SKILL.md)) — that is the build team's memory. This is the **product's** memory that Maya builds *inside Brain*.

**Canonical source:** `canon/TECH/05_intelligence_layer.md` §0 · technical-requirements §16.1.

## The 5 memory subsystems

| # | Subsystem | Store | Consumed by |
|---|---|---|---|
| 1 | **Brand Fingerprint** (16-dim daily vector) | `ai.brand_fingerprint` (pgvector) | every agent's daily tick; cross-brand similarity |
| 2 | **Condition-Outcome pairs** | `ai.condition_outcome` (pgvector) | every agent: "find similar past conditions" — the engine of compounding learning |
| 3 | **Cross-Brand Benchmarks** | `ai.cross_brand_pattern` (k≥5) | new/sparse-data brand cold-start; pattern surfacing |
| 4 | **Seasonal Codebook** | Postgres | AICMO-Festival, forecasting, Morning Brief seasonal narrative |
| 5 | **Customer Segment Memory** (daily RFM) | Postgres | lifecycle audience builder ([`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md)) |

*(`brand_id` = `workspace_id` = tenant; every memory row is workspace-scoped — see isolation below.)*

## 1. Brand Fingerprint — the business-moment vector

A **16-dim** vector capturing brand-state on a day, built each morning at **07:00 IST** (SQL aggregation + numpy normalization — paradigm 1):

```sql
CREATE TABLE ai.brand_fingerprint (
  workspace_id UUID NOT NULL,
  date DATE NOT NULL,
  vector vector(16) NOT NULL,
  components JSONB NOT NULL,                    -- human-readable per-component values
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, date)
);
CREATE INDEX ON ai.brand_fingerprint USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

The 16 dims (tunable): CM2 % · revenue trajectory (7d) · MER · aMER · CAC (delivered) · AOV · new-customer share · repeat share · COD share · RTO rate · active inventory days · discount depth · channel concentration (Herfindahl) · creative-fatigue (mean EWMA) · seasonality position (days from nearest festival) · cashflow runway. Each is **normalized to the brand's own history**, not industry benchmarks.

## 2. Condition-Outcome pairs — compounding learning

Every recommendation becomes a Condition-Outcome pair when its outcome attributes back (it `REFERENCES ai.decision_log` — the two moats are linked; see [`decision-log`](../decision-log/SKILL.md)):

```sql
CREATE TABLE ai.condition_outcome (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL,
  decision_log_id UUID NOT NULL REFERENCES ai.decision_log(id),
  brand_fingerprint_at_decision vector(16) NOT NULL,    -- the brand-state when we decided
  condition_metadata JSONB,
  agent_name TEXT NOT NULL, recommendation_type TEXT NOT NULL, recommendation_payload JSONB,
  was_approved BOOLEAN, was_auto_executed BOOLEAN,
  outcome_7d JSONB, outcome_30d JSONB,
  recovered_revenue_7d_minor BIGINT, recovered_revenue_30d_minor BIGINT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON ai.condition_outcome USING hnsw (brand_fingerprint_at_decision vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**The query every agent runs on every tick** — "when this brand looked like it looks today, what did we recommend and did it work?":

```sql
SELECT co.recommendation_type, co.was_approved, co.outcome_7d, co.outcome_30d,
       1 - (co.brand_fingerprint_at_decision <=> :current_fingerprint) AS similarity
FROM ai.condition_outcome co
WHERE co.workspace_id = :workspace_id          -- ISOLATION: always present
  AND co.outcome_30d IS NOT NULL
ORDER BY co.brand_fingerprint_at_decision <=> :current_fingerprint   -- cosine distance
LIMIT 5;
```

`<=>` is pgvector cosine distance; `1 - distance` = similarity. This is paradigm-1 SQL — no LLM in the retrieval.

## 3. Cross-Brand Benchmarks — k≥5 anonymity (cold-start)

Aggregated, anonymized network patterns; **k-anonymity enforced in schema** (`brand_count CHECK (brand_count >= 5)`). New/sparse brands fall back to similar-category, similar-region patterns and **Bayesian-blend** with their own data as it accumulates. No row-level brand data exposed; brand-level opt-in (DPA) to contribute but a brand always *receives* patterns. A cross-brand pattern that exposes a competitor's raw values is a CRITICAL leak ([`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md), [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)).

## 4 + 5. Seasonal Codebook + Customer Segment Memory

- **Seasonal Codebook** — per-brand per-event uplift multipliers (learn own coefficients year over year; new brands fall back to the cross-brand benchmark). Feeds forecasting + festival narrative ([`india-commerce-economics`](../india-commerce-economics/SKILL.md), [`forecasting-prophet`](../forecasting-prophet/SKILL.md)).
- **Customer Segment Memory** — per-customer daily RFM scores + segment, the single primitive the audience builder consumes.

## Cost-paradigm map — almost zero LLM

| Operation | Paradigm |
|---|---|
| Build Brand Fingerprint | **1 — SQL + numpy** |
| pgvector cosine top-K | **1 — SQL** |
| Outcome attribution (7d/30d write-back) | **1 — SQL** |
| Cross-brand k-anonymous aggregates | **1 — SQL** |
| Seasonal uplift | **1 — SQL** + **2 — ML (Prophet residuals)** |
| Monthly compound-report narrative | **4 — Sonnet** (the *only* LLM in the layer) |

Compounding learning at SQL economics ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)). The fingerprint + Decision Log context are prime **prompt-cache** targets when they do reach the Sonnet synthesis step ([`claude-api`](../claude-api/SKILL.md)).

## Discipline

1. **`workspace_id`-scoped vectors, always.** Every retrieval filters by `workspace_id`. An unscoped vector search is a cross-brand leak — fail closed.
2. **Source of truth stays relational.** The fingerprint/CO log are a retrieval *lens* over facts that also live as structured rows + the Decision Log — not the sole record.
3. **Pinned vector definition.** The 16-dim layout is versioned; changing dimensions requires recomputing fingerprints (otherwise vectors are incomparable).
4. **`HNSW` cosine indexes** (`vector_cosine_ops` with `m = 16, ef_construction = 64`); set `hnsw.ef_search` at query time to trade recall for latency. HNSW is the 2026 default for Brain's write-heavy, daily-growing vectors (queried every tick, <1M rows/workspace): 95%+ recall out-of-box, absorbs inserts without an index rebuild (ivfflat needs periodic `REINDEX` and degrades on writes). `workspace_id` predicate leads the query ([`database-design`](../database-design/SKILL.md)).
   - **Escape hatch:** keep `ivfflat (vector_cosine_ops) WITH (lists = N)` **only** at the >50M-vector / memory-constrained extreme (HNSW costs ~2–5× the memory). Brain's per-workspace vectors are nowhere near that; default to HNSW.
5. **Memory references the Decision Log**, never silently overwrites — the Decision Log is append-only.

## Anti-patterns

- A vector search without a `workspace_id` filter → cross-brand leak (P0).
- Treating the fingerprint as the source of truth instead of a retrieval lens.
- Changing the 16-dim layout without recomputing → garbage similarity.
- A cross-brand pattern below k=5 or exposing a single brand's row.
- Reaching for an LLM where the cosine query / SQL aggregate suffices (paradigm bypass).

## Verify

- A top-K retrieval for workspace A returns zero rows from workspace B (isolation test).
- The "find similar past conditions" query uses `<=>` cosine + filters `workspace_id` + `outcome_30d IS NOT NULL`.
- `cross_brand_pattern` rejects an insert with `brand_count < 5`.
- An agent recommendation cites the Condition-Outcome rows it retrieved (traceability into the Decision Log).

## References

- `canon/TECH/05_intelligence_layer.md` §0 — the 5 subsystems, schemas, daily-tick timing, paradigm map
- `canon/technical-requirements.md` §16.1 — Memory Layer requirements
- [`agentic-design`](../agentic-design/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`forecasting-prophet`](../forecasting-prophet/SKILL.md) · [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md) · [`morning-brief-mobile`](../morning-brief-mobile/SKILL.md)
</content>
