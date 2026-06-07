---
name: rag-retrieval
description: The retrieval pattern behind RAG — hybrid lexical+dense with RRF fusion, rerankers, contextual retrieval, chunking discipline, late-interaction/agentic routing, and recall@k as the ship gate. Fix retrieval before blaming the model. Owner ML Platform + AI/ML Eng.
---

# RAG Retrieval (Reference Patterns)

> **Reference implementation.** This skill documents the **retrieval-pattern seam** for RAG (see `engineering-os-blueprint/09-reference-architecture.md`). It sits above the *stores* — `vector-search-pgvector` (vectors), `search-opensearch` (lexical) — and defines how to retrieve *well*. The OS is stack-agnostic; the stores in `STACK.md` may differ. The *patterns* — hybrid + fusion, rerank, contextual retrieval, measured recall — transfer.

The most common cause of a "hallucinating" RAG system is **bad retrieval**, not a bad model. Vanilla single-vector search is no longer the standard; the 2026 production baseline is **hybrid → rerank → contextualize**. **Owner:** ML Platform Engineer (the retrieval pipeline) + AI/ML Engineer (the RAG app on top). Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Hybrid by default.** Combine lexical (BM25 — `search-opensearch` / Postgres FTS) with dense vector (`vector-search-pgvector`) and fuse with **Reciprocal Rank Fusion**. Hybrid+RRF beats dense-only on recall (~91% vs ~78% recall@10 in the cited benchmarks) — exact-term queries break pure-vector, semantic queries break pure-lexical.
2. **Retrieve wide, then rerank narrow.** Fetch top-20–50 candidates cheaply, then a **cross-encoder reranker** cuts to the top-3–5 that actually go in the prompt. Skipping the rerank step is the single biggest quality-left-on-the-table.
3. **Tenant filter is applied in retrieval, server-side, before scoring.** Every candidate is tenant-scoped (`multi-tenancy-isolation`). A retrieved chunk from another tenant is a P0 leak — and for HNSW, filter correctly so recall isn't silently gutted by post-filtering.
4. **Recall@k is the ship gate.** Changes to chunking, embeddings, fusion weights, or reranker are validated against a golden query set and **must not regress recall@k** — the same discipline as `llm-evals`. "Feels better" is not a merge criterion.
5. **Chunking + contextual retrieval are part of the contract.** Chunk size/overlap and **contextual retrieval** (prepend chunk-specific context before embedding — ~67% fewer retrieval failures) are fixed, versioned decisions; changing them invalidates stored embeddings (`vector-search-pgvector` re-embed migration).

## Pipeline
```
query → [rewrite/expand?] → ┌ lexical (BM25, tenant-filtered) ┐
                            ├ dense (ANN, tenant-filtered)     ┤→ RRF fuse → top-N
                            └ (optional) late-interaction      ┘
       → cross-encoder rerank → top-k (3–5)
       → assemble context (dedup, cite sources, fit token budget) → model (via llm-gateway)
```

## Techniques, by when to reach for them
| Technique | Use when |
|---|---|
| Hybrid + RRF | **Always** — the baseline. |
| Cross-encoder rerank | Almost always — precision matters and you over-fetched. |
| **Contextual retrieval** (Anthropic) | Chunks lose meaning without doc context (most corpora). Standard preprocessing. |
| Late-interaction / ColBERT | High-precision retrieval over large corpora; cost permits. |
| GraphRAG | Multi-hop / relationship questions over a knowledge graph (`graph-identity-neo4j`). |
| **Agentic RAG** | A router decides per query: answer-from-weights / cache / single retrieve / multi-step. Adds an effort tier — measure it earns its cost. |
| Self-correction (CRAG) | Retrieval quality is variable and a wrong answer is expensive. |

## Effort-tier & cost note (`cost-routing-paradigms`)
Retrieval is the **cheap, mostly-deterministic front half** of RAG; the model call is the expensive tail. So: spend on *good retrieval* (it's cheap) to shrink/skip the expensive generation, cache embeddings + reranker results, and only escalate to agentic/multi-step retrieval when measured recall demands it. Better retrieval is usually cheaper *and* more accurate than a bigger model.

## Evaluation (with `llm-evals`)
- Maintain a golden set of (query → relevant-doc-ids); report **recall@k, MRR/nDCG** on every retrieval change; gate in CI.
- Faithfulness/groundedness of the *answer* belongs to `llm-evals`; **retrieval recall** is this skill's gate. Trace retrieval spans (`ai-observability-tracing`) so a bad answer links to what was (or wasn't) retrieved.

## Anti-patterns
Pure single-vector search as the default · no reranker · tenant filter applied after scoring (leak or gutted recall) · no recall@k gate ("feels better") · changing chunking/embeddings without re-embedding · stuffing 50 chunks into the prompt instead of reranking to 5 · reaching for a bigger model when the real bug is retrieval · agentic RAG everywhere without measuring that it earns its added cost.
