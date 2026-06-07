---
name: search-opensearch
description: Reference implementation — full-text + filtered search on OpenSearch: tenant-filtered queries, index-per-domain mappings, analyzers/relevance, bulk indexing from the stream, the search store is a derived projection (never the source of truth).
---

# Search — OpenSearch (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **search seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind search to a different engine (Elasticsearch, Typesense, Meilisearch, Postgres FTS for small scale). The *patterns* here — search as a derived projection, explicit mappings + analyzers, mandatory tenant filtering, bulk-index-from-the-stream, and relevance tuned against a golden set — are what transfer; OpenSearch is the example.

OpenSearch powers customer / order / ticket search. It is a **derived read projection** of the source-of-truth stores (OLTP, lakehouse), kept current from the event stream. **Owner:** Backend Engineer (query + mapping) with Data Engineer (indexing pipeline); Platform/SRE owns the cluster. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **The search index is NEVER the source of truth.** It is rebuildable from the stream/lakehouse at any time. Treat divergence as expected and reconcilable, not as data loss.
2. **Every query is tenant-filtered — in a `filter` clause, server-side.** `bool.filter: [{term: {tenant_id}}]` is added by the query gateway, never trusted from the client. A query without the tenant filter is a P0 cross-tenant leak (`multi-tenancy-isolation`). Prefer index-per-tenant or a tenant-routing alias for hard isolation at scale.
3. **Explicit mappings — no dynamic mapping in production.** Define field types, analyzers, and `keyword` vs `text` up front. Dynamic mapping causes type explosions and mapping conflicts that take the index down.
4. **Filters over queries for anything non-scoring.** Tenant, status, date-range, and ACL constraints go in `filter` (cacheable, no scoring cost); only the actual search terms go in `must`/relevance.
5. **Relevance is measured, not vibes.** Keep a golden query set; changes to analyzers/boosts are validated against it (the search analogue of `llm-evals` / `data-quality`).

## Mapping
```json
{ "mappings": { "properties": {
  "tenant_id":   { "type": "keyword" },
  "customer_id": { "type": "keyword" },
  "name":        { "type": "text", "analyzer": "standard",
                   "fields": { "raw": { "type": "keyword" } } },   // text for search, raw for sort/agg
  "email":       { "type": "keyword" },
  "status":      { "type": "keyword" },
  "created_at":  { "type": "date" },
  "amount_minor":{ "type": "long" }
}}}
```
- `text` (analyzed) for search; a `.raw` `keyword` sub-field for exact-match, sort, aggregation. Money stays integer minor units (`metric-engine`).
- Choose analyzers deliberately (language analyzers, edge-ngram for type-ahead). Reindex on analyzer change (use an alias to swap with zero downtime).

## Query
```json
{ "query": { "bool": {
  "filter": [ {"term": {"tenant_id": "<server-injected>"}}, {"term": {"status": "open"}} ],
  "must":   [ {"multi_match": {"query": "acme", "fields": ["name^3", "email", "notes"]}} ]
}}, "from": 0, "size": 20 }
```
- Boost fields by importance (`name^3`). Tune against the golden set.
- **Paginate with `search_after` (keyset), not deep `from`/`size`** — deep offset pagination is banned for the same reason as in `api-discipline` (it degrades and is unstable under writes).

## Indexing pipeline (from the stream)
- A consumer of the event backbone (`event-driven-kafka`) **bulk-indexes** changes; never index per-request synchronously on the write path.
- Use the source `event_id`/version as the document `_id` + `version` so re-delivery is idempotent (last-write-wins). Late/replayed events re-index the same doc — no duplicates.
- Bulk in batches with backoff; route to the tenant's shard/index. A full rebuild replays from the lakehouse (`lakehouse-iceberg`) — same code path.

## Cluster operability (Platform/SRE)
- Shard sizing: target ~10–50 GB/shard; over-sharding (thousands of tiny shards from index-per-tenant) is the common scaling failure — use shared indices with routing for small tenants, dedicated indices for large ones.
- Use **aliases** for every index so reindex/rollover is transparent to the app. ISM policies for rollover + retention.
- Monitor: query latency p99, rejected-thread-pool (backpressure), JVM heap, red/yellow cluster status.

## Effort-tier note (`cost-routing-paradigms`)
Lexical/filtered search is **deterministic** — the cheapest tier. Don't reach for an LLM/embedding search where a keyword + filter query answers the need. When semantic recall genuinely matters, that's `vector-search-pgvector` (or hybrid lexical+vector), declared as a higher tier with a measured recall justification.

## Anti-patterns
Treating the index as source of truth · a query missing the tenant filter · dynamic mapping in prod · scoring on fields that should be filters · deep `from`/`size` pagination · per-request synchronous indexing · non-idempotent indexing (dupes on replay) · thousands of tiny per-tenant shards · changing analyzers without re-validating relevance.

## 2026 market update

- **Hybrid lexical + vector with RRF fusion is the standard pattern now** (the retrieval discipline + recall@k gate live in `rag-retrieval`; reranking before the model step is standard). OpenSearch/Elasticsearch ship native hybrid; **Qdrant** is the vector-native alternative with first-class hybrid; **pgvector** absorbs simpler cases into Postgres. **Typesense / Meilisearch** for lightweight instant-search.
