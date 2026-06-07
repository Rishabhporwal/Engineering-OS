---
name: graph-identity-neo4j
description: Reference implementation — an identity graph on Neo4j: nodes/edges for customer identity resolution, deterministic + probabilistic stitching, tenant-scoped subgraphs, indexed lookups, write-from-the-stream. Identity is a graph problem, not a JOIN.
---

# Graph / Identity Resolution — Neo4j (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **graph / identity-resolution seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to a different graph store (Neptune, TigerGraph, JanusGraph) or even a relational closure-table approach. The *patterns* here — model identity as nodes + edges, deterministic-then-probabilistic stitching, tenant-scoped subgraphs, indexed anchor lookups, and writing the graph from the event stream — are what transfer; Neo4j is the example.

Identity resolution ("are these the same customer?") is a **connected-components problem**, not a SQL JOIN. A graph models persons, devices, emails, phones, accounts, and the edges that link them, and resolves a stable canonical identity. **Owner:** Data Engineer (graph + stitching); AI/ML Engineer pairs on probabilistic matching. Canon: `STACK.md`. Marked **target state** in many adoptions — build the seam behind an interface so it's additive.

## Invariants (NON-NEGOTIABLE)
1. **Tenant-scoped subgraphs.** Every node carries `tenant_id`; every traversal is rooted in one tenant. A path that crosses tenants is a P0 identity leak (`multi-tenancy-isolation`). Enforce with a `tenant_id` property on the root + a composite index; never traverse globally.
2. **Deterministic before probabilistic.** Link on exact, high-trust keys first (verified email, phone, account ID, login). Only then apply probabilistic/fuzzy matching, and **gate every probabilistic merge behind a confidence threshold + an audit record** — a wrong merge silently fuses two real people (a privacy incident).
3. **Merges are reversible + logged.** Identity merges write to the Decision Log (`decision-log`): which signals, what confidence, who/what approved. A merge above an auto-threshold may need human approval (`workflow-engine-temporal`). Un-merge must be possible.
4. **The canonical ID is stable.** Downstream systems key on a durable `canonical_customer_id`, not on the volatile underlying node. Re-resolution updates the mapping, never breaks the downstream key.
5. **Written from the stream, queried by services.** Flink/connectors (`stream-processing-flink`, `integration-connectors`) upsert nodes/edges; services do bounded, indexed lookups — never an unbounded traversal on a request path.

## Model
```cypher
// Anchor identifiers as nodes; the person as the hub; edges carry provenance + confidence
(:Customer {tenant_id, canonical_id})-[:HAS_EMAIL {verified, source, first_seen}]->(:Email {tenant_id, value})
(:Customer)-[:HAS_DEVICE {confidence, source}]->(:Device {tenant_id, fingerprint})
(:Customer)-[:SAME_AS {confidence, method, decided_at}]->(:Customer)   // a stitching edge
```
- Put identifiers (email/phone/device) as **their own nodes** so a shared identifier is one node many customers can link to — that shared node IS the stitch signal.
- **Index the anchors:** `CREATE INDEX FOR (e:Email) ON (e.tenant_id, e.value)` — every lookup starts from an indexed anchor, never a label scan.

## Stitching
```cypher
// deterministic: two customers sharing a verified email → candidate same-person
MATCH (a:Customer)-[:HAS_EMAIL {verified:true}]->(e:Email)<-[:HAS_EMAIL {verified:true}]-(b:Customer)
WHERE a.tenant_id = $tenant AND b.tenant_id = $tenant AND a <> b
MERGE (a)-[:SAME_AS {confidence:1.0, method:'verified_email'}]->(b)
```
- Resolve a canonical identity = the connected component over `SAME_AS` edges above threshold. Recompute incrementally as edges arrive.
- **Probabilistic** (name + address + behaviour similarity) is computed by the AI/ML layer (an effort-tier decision — statistical/ML, NOT an LLM for routine matching) and only *writes* an edge when confidence clears the bar.

## Query discipline (or it melts)
- **Bound every traversal:** `MATCH p=(c)-[:SAME_AS*1..3]-(o)` — cap hops. An unbounded variable-length traversal on a hot node is an outage.
- Start from an **indexed anchor**, traverse outward; never scan a label.
- Keep request-path queries to point lookups + shallow neighbourhoods; do component-wide recomputation in the batch/stream layer.
- Watch **supernodes** (a shared device/IP linking millions) — cap fan-out or down-weight ubiquitous identifiers, or one node poisons every traversal.

## Effort-tier note (`cost-routing-paradigms`)
Deterministic key-matching is the cheapest tier — do the bulk of resolution there. Probabilistic matching is **statistical/ML**, not an LLM job. Reserve any model call for genuinely ambiguous, high-value merges, and cache. Identity is mostly a graph + rules problem.

## Anti-patterns
Cross-tenant traversal · unbounded variable-length paths · probabilistic merge with no confidence gate or audit record · an irreversible auto-merge · keying downstream on the raw node instead of a stable canonical ID · label scans instead of anchor-indexed lookups · ignoring supernodes · using an LLM for routine identifier matching.
