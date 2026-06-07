---
name: vector-search-pgvector
description: Reference implementation — semantic / vector retrieval on Postgres + pgvector: tenant-filtered ANN search, HNSW indexing, hybrid lexical+vector, embedding lifecycle, RAG retrieval for decision/brand/creative memory. Embeddings are a tier, not a default.
---

# Vector Search — Postgres + pgvector (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **vector-store / semantic-retrieval seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to a dedicated vector DB (Qdrant, Pinecone, Weaviate, Milvus) or another extension. The *patterns* here — tenant-filtered ANN, the right index for the distance metric, hybrid retrieval, an explicit embedding lifecycle, and retrieval quality measured with recall@k — are what transfer; pgvector is the example.

pgvector keeps vectors **next to the relational data** in Postgres (`data-layer`) — one store, one transaction, one backup, tenant RLS for free. It powers decision/brand/creative memory and RAG knowledge retrieval. **Owner:** ML Platform Engineer / AI/ML Engineer; Architect reviews when it's a new store. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Tenant filter is enforced in the query + by RLS.** ANN search runs `WHERE tenant_id = $t` and the table has row-level security keyed on the tenant — a vector search that returns another tenant's memory is a P0 (`multi-tenancy-isolation`). For HNSW + a hard filter, use a partial index per tenant or filtered search so recall isn't silently destroyed by post-filtering.
2. **Match the index to the distance metric.** The operator class must match how the embeddings were trained (`vector_cosine_ops` for cosine, `vector_l2_ops` for L2, `vector_ip_ops` for inner product). A mismatch returns plausible-looking garbage.
3. **Embeddings have a lifecycle + a model version.** Store `embedding_model` + dimension with every vector. Changing the embedding model means a **re-embed migration**; never mix vectors from two models in one index (their spaces are incomparable).
4. **Retrieval quality is measured (recall@k).** Tune `m`/`ef_construction`/`ef_search` against a golden set and report recall — the same ship-gate discipline as `llm-evals`. ANN trades recall for speed; an untuned index silently drops relevant results.
5. **Vector search is a higher effort tier — justify it.** Reach for embeddings only when lexical/filtered search (`search-opensearch`) demonstrably can't meet the recall need. An embedding call + ANN is more expensive than a `WHERE` clause.

## Schema + index
```sql
CREATE TABLE memory (
  tenant_id     uuid    NOT NULL,
  id            uuid    PRIMARY KEY,
  kind          text    NOT NULL,                 -- decision | brand | creative
  content       text    NOT NULL,
  embedding     vector(1536) NOT NULL,
  embedding_model text  NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE memory ENABLE ROW LEVEL SECURITY;       -- tenant RLS (data-layer)

CREATE INDEX ON memory USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```
HNSW for high-recall low-latency reads (build cost higher); IVFFlat only when build time/memory dominates. Set `ef_search` per-query to trade recall vs latency.

## Query (tenant-scoped ANN + hybrid)
```sql
SET hnsw.ef_search = 100;
SELECT id, content, 1 - (embedding <=> $query_vec) AS score
FROM memory
WHERE tenant_id = $t AND kind = $kind            -- hard filters first
ORDER BY embedding <=> $query_vec                -- cosine distance
LIMIT 10;
```
- **Hybrid retrieval:** combine lexical (`search-opensearch`/Postgres FTS) with vector scores (reciprocal-rank fusion) when exact-term recall *and* semantic recall both matter — usually beats either alone for RAG.
- Always over-fetch then re-rank/cut to the context budget for the model step.

## Embedding lifecycle
- Generate embeddings via the model gateway (`llm-gateway`), **cache** them (an embedding is a model call — `cost-routing-paradigms`), and store with their model id.
- A model upgrade ⇒ a backfill migration that re-embeds (batch — `batch-processing-spark`), written under a new column/index, then atomic cutover. Never serve mixed-model vectors.
- Chunking strategy (size/overlap) is part of the contract — changing it invalidates stored vectors for affected docs.

## RAG note (with `llm-evals`)
Retrieval is the cheap, deterministic-ish front half of RAG; the model call is the expensive tail. Measure **recall@k** on a golden set and gate changes on it. Bad retrieval (low recall, wrong tenant, stale embeddings) is the most common cause of a "hallucinating" RAG system — fix retrieval before blaming the model.

## Anti-patterns
ANN without the tenant filter (leak) or post-filtering that guts recall · index opclass ≠ training metric · mixing embedding-model versions in one index · no recall measurement · re-embedding on every query instead of caching · using vectors where a keyword filter suffices (wrong tier) · ignoring chunking changes that invalidate stored vectors.
