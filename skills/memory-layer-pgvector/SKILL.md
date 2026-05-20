---
name: memory-layer-pgvector
description: Brain's Memory Layer (canon Layer 2) — the Brand Fingerprint in Postgres `memory.brand_fingerprint` via pgvector. How the AICMO/AICOO/AICFO agents store and semantically retrieve per-brand history (decisions, outcomes, brand voice, learned patterns) so they "learn the brand's history and act before the founder has to." Use when wiring agent memory, embedding brand context, or doing semantic retrieval inside intelligence-service. Distinct from the Engineering OS's own .engineering-os semantic index — this is the PRODUCT's memory.
---

# Memory Layer — Brand Fingerprint (pgvector)

Brain's Layer 2 (canon/BRAIN_TECHNICAL.md §2) is what makes it more than a dashboard: each brand has a **Brand Fingerprint** — accumulated history, decisions, outcomes, and voice — stored as embeddings in Postgres `memory.brand_fingerprint` (pgvector). The product agents retrieve from it semantically so their actions are grounded in *this* brand's past, not generic advice.

> Don't confuse this with the **Engineering OS's** own semantic memory (`.engineering-os/index`, [`recall-similar`](../recall-similar/SKILL.md)). That is the engineering *team's* memory. This skill is the **product's** memory layer that Maya builds *inside Brain*.

## What goes in the fingerprint

- Past decisions + their outcomes (did the recommended action work?).
- Brand voice / positioning (for message generation).
- Learned patterns (e.g., "this brand's COD RTO spikes on Tier-3 pincodes during sale events").
- Significant events the agents should remember next tick.

## Discipline

1. **`workspace_id`-scoped vectors.** Every embedding row carries `workspace_id`; retrieval filters by it. A cross-brand fingerprint hit is a leak ([`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)).
2. **Source of truth stays relational.** The fingerprint is a *retrieval* layer over facts that also live as structured rows / the Decision Log — it is not the sole record (mirrors the OS's "derived index" principle).
3. **Pinned embedding model.** One model, versioned; changing it requires re-embedding (incomparable vectors otherwise).
4. **Append + supersede, don't silently overwrite** — the Decision Log is append-only; fingerprint entries reference it.
5. **Cost-aware** ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)): retrieval is cheap; only embed what earns its keep. Don't embed every raw row — embed summaries/decisions.
6. **pgvector indexing** (HNSW/IVFFlat) tuned for the row count; `workspace_id` predicate first ([`database-design`](../database-design/SKILL.md)).

## Anti-patterns

- Unscoped vector search (no `workspace_id` filter) → cross-brand leak.
- Embedding raw high-volume data instead of distilled decisions/summaries → cost + noise.
- Treating the fingerprint as the source of truth instead of a retrieval lens.
- Mixing embedding-model versions in one index.

## Verify

- A retrieval for workspace A returns zero rows from workspace B (isolation test).
- The agent's recommendation cites the fingerprint entries it used (traceability into the Decision Log).
