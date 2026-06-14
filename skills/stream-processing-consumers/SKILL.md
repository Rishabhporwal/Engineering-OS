---
name: stream-processing-consumers
description: Reference implementation — app-level stream processing on consumer groups (KafkaJS/TypeScript on Kubernetes): the deliberate NON-framework path. Manual-commit at-least-once + idempotency, validation/dedup/enrichment/identity-resolution/sessionization/quality as consumer patterns, DLQ/retry, graceful SIGTERM drain. You build state + windowing yourself. Partition key IS the tenant key. Owner Data/Backend Engineer.
---

# Consumer Stream Processing — KafkaJS on Kubernetes (the non-Flink path)

> **Reference implementation.** One concrete binding of the **stream-processing seam** — the *deliberate app-level alternative* to `stream-processing-flink`. The OS is stack-agnostic — `STACK.md` may bind real-time compute to Flink/Kafka Streams/a different client. The *patterns* — consumer-group parallelism = partitions, manual-commit at-least-once made safe by idempotency, externalized state (Redis/Postgres) for dedup/sessionization, tenant-keyed processing, DLQ/retry, graceful SIGTERM drain — transfer; KafkaJS on EKS is the example.

> **This is a real decision, not a default.** A consumer-group client gives you parallelism and *nothing else* — **no state store, no windowing engine, no event-time/watermarks, no exactly-once stream processing**. You build dedup, sessionization, and idempotency on Redis/Postgres. Choose it for **stateless-to-lightly-stateful per-tenant transforms** (validate, enrich, upsert) when you want to stay in your TypeScript mesh with no Flink cluster to run. The moment you need real event-time windows, large keyed state, or end-to-end exactly-once → `stream-processing-flink`. Reimplementing windowing+state+EOS in app code is "a worse Flink" — an ADR-worthy crossover (`tech-stack-evaluation`).

> **Client reality (2025–26):** `tulios/kafkajs` is effectively **unmaintained** (no release since ~Feb 2023; gaps vs Kafka 4.0). For new builds prefer Confluent's GA **`@confluentinc/kafka-javascript` (CJSK)** — librdkafka-based, KafkaJS-compatible API, adds real transactions + cooperative-sticky rebalancing (note: native dep → build-toolchain per `operational-readiness`). The patterns hold for both.

**Owner:** Backend/Data Engineer; Architect reviews the build-vs-Flink call. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Partition key IS the tenant key** → a tenant's events are ordered in one partition, owned by one consumer. **Every** pattern below (dedup, identity, sessionization) is tenant-scoped by construction — keyed state lives under a `tenant_id`-leading key; a cross-tenant state read is a P0 (`multi-tenancy-isolation`).
2. **At-least-once + idempotency. NEVER `autoCommit`.** `autoCommit:false`; commit **after** the side effect succeeds. Auto-commit is at-most-once → data loss on crash. Redelivery is normal, so every write MUST be idempotent (upsert / dedup key) — at-least-once + idempotent = effectively-once without Flink.
3. **Commit the NEXT offset (`offset+1`), not the processed offset** — committing the processed offset reprocesses it forever on restart (a known KafkaJS doc gap; `resolveOffset` adds the +1 for you, a manual `commitOffsets` doesn't).
4. **Graceful shutdown on SIGTERM — drain, don't drop.** Trap SIGTERM, stop taking new work, finish + commit in-flight, then `await consumer.disconnect()` (leaves the group cleanly → fast rebalance, not a `sessionTimeout` stall). Uncommitted work is safely reprocessed (Invariant #2).
5. **Consumers ≤ partitions** — parallelism is capped by partition count; extra pods idle. Scale = raise partitions first. Externalize all state so a pod is disposable across rebalances.
6. **Every path has a DLQ** — a poison pill routes to `<topic>.dlq` after bounded retries; never block the partition (head-of-line) with infinite in-place retry, never silently drop.
7. **`sessionTimeout`/`maxPollInterval` must exceed worst-case processing, or `await heartbeat()` through it** — else the broker evicts the member mid-message → duplicates + rebalance churn.

## When this vs a stream framework
| | **KafkaJS consumers (this)** | **Flink / Kafka Streams** |
|---|---|---|
| State store | none — bring Redis/Postgres | built-in, checkpointed |
| Windowing / event-time | none — timeouts + stored state | native watermarks + windows |
| Exactly-once stream | no — at-least-once + your idempotency | EOS via checkpoint + 2PC sink |
| Ops | just your K8s service | a Flink cluster to run + tune |
| Best for | validate/enrich/upsert, light per-tenant state | large keyed state, true windows, CEP/attribution |

## Skeleton (manual commit, batch, heartbeat, drain)
```ts
const consumer = kafka.consumer({ groupId: 'analytics-orders', sessionTimeout: 30000, heartbeatInterval: 3000 });
await consumer.run({
  autoCommit: false, eachBatchAutoResolve: false, partitionsConsumedConcurrently: 3,  // ≤ partitions
  eachBatch: async ({ batch, resolveOffset, heartbeat, commitOffsetsIfNecessary, isRunning, isStale }) => {
    for (const message of batch.messages) {
      if (!isRunning() || isStale()) break;          // stop fast on shutdown / after rebalance
      await processIdempotently(batch.partition, message);   // SIDE EFFECT FIRST
      resolveOffset(message.offset);                 // mark processed (commit adds +1)
      await heartbeat();
    }
    await commitOffsetsIfNecessary();
  },
});
for (const sig of ['SIGTERM','SIGINT'] as const) process.on(sig, async () => { await consumer.disconnect(); process.exit(0); });
```
`eachBatch` (vs simpler `eachMessage`) gives `resolveOffset`/`isStale`/manual heartbeat — needed for clean-shutdown offset safety + backpressure. `partitionsConsumedConcurrently` keeps per-partition ordering. **KafkaJS does EAGER rebalancing only** (stop-the-world; no cooperative-sticky — CJSK has it) → minimize rebalances: stable pods, tuned timeouts, fast drain; break on `isStale()`.

## The patterns, as consumers
- **Validation** — decode (schema registry) + validate (Zod/Avro) at the handler edge; invalid → DLQ with the reason, never to the side effect.
- **Dedup** — natural-key upsert `INSERT ... ON CONFLICT (tenant_id, event_id) DO UPDATE` (the write itself is idempotent — preferred), or a Redis `SET dedup:{tenant}:{event_id} 1 NX EX <ttl>` backstop when the effect isn't a natural upsert. Stable `event_id = (tenant_id, source, source_event_id)`.
- **Enrichment** — **cache-aside** against the dimension store, keyed `(tenant_id, key)` + TTL (`caching-strategy`); never an uncached per-message lookup on a hot partition (your throughput ceiling). Pass an idempotency key on any enriching downstream *call* (`idempotency-handling`).
- **Identity resolution** — resolve to a deterministic stable key (hash of normalized email/phone *within tenant*) → upsert identity edges; the real probabilistic/transitive graph is `graph-identity-neo4j`. Subgraph tenant-scoped.
- **Sessionization (no windowing engine)** — emulate session windows with **state + a timeout**: per-`(tenant_id, subject)` session in Redis (`HSET` + sliding `EXPIRE = gap`); each event extends it; a **separate sweeper** (scheduled job / keyspace-expiry listener) closes elapsed sessions and emits the session event. You own the gap (from the data contract), late-data, and the timer.
- **Quality checks** — assert freshness/row/range inline or as a parallel consumer; failures emit a `data-quality` signal and/or DLQ.

## DLQ / retry + backpressure
`topic → retry-1 (60s) → retry-2 (5m) → topic.dlq` — a wrapper increments a `retryCount` header and re-publishes to a delayed topic; after N, lands in `<topic>.dlq` with the error + offset. Alarm on DLQ **depth + age**. Distinguish transient (retry) from poison (straight to DLQ). The consumer naturally backpressures (won't fetch the next batch until the handler returns) → **consumer lag is the primary health metric, alarm on sustained lag**; levers: `partitionsConsumedConcurrently`, `maxBytesPerPartition`, `consumer.pause()/resume()`. Don't fan out unbounded async inside a handler (breaks backpressure + offset safety).

## Anti-patterns
`autoCommit:true` (at-most-once loss) · committing the processed offset not `+1` (infinite reprocess) · no idempotency under at-least-once (dup rows/orders) · no SIGTERM drain · consumers > partitions (idle pods) · infinite in-place retry of a poison pill (head-of-line block) · uncached per-message lookups on a hot partition · sessionization with no sweeper (sessions never close) · state keyed without `tenant_id` (P0 leak) · long handler with no `heartbeat()` (rebalance churn + dupes) · unbounded async fan-out in a handler · reimplementing windowing/large-state/EOS instead of using Flink · building new on unmaintained KafkaJS when CJSK fits.

## References
`event-driven-kafka` / `redpanda-apicurio-avro` (the backbone consumed) · `stream-processing-flink` (the framework alternative — when to cross over) · `idempotency-handling` · `caching-strategy` · `graph-identity-neo4j` · `data-quality` · `multi-tenancy-isolation` · `operational-readiness` (SIGTERM, native-dep for CJSK) · `observability` (consumer-lag SLO) · `local-dev-environment`.
