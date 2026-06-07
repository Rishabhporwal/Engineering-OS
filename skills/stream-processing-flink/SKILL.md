---
name: stream-processing-flink
description: Reference implementation — stateful stream processing on Apache Flink: event-time + watermarks, keyed state, exactly-once via checkpoints + two-phase-commit sinks, real-time enrichment/attribution/identity/signals. Tenant key IS the partition/key-by.
---

# Stream Processing — Apache Flink (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **stream-processing seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind real-time compute to a different engine (Kafka Streams, Spark Structured Streaming, Arroyo, ksqlDB). The *patterns* here — event-time over processing-time, watermarked windows, keyed state scoped to the tenant, exactly-once via checkpoint + transactional sink, and the same job replaying history as it processes live — are what transfer; Flink is the example.

Flink consumes the Kafka backbone (`event-driven-kafka`) and produces enriched events, attribution, identity edges, and real-time signals into OLAP (`clickhouse-olap`), the lakehouse (`lakehouse-iceberg`), and the graph (`graph-identity-neo4j`). **Owner:** Data Engineer (operationally); Architect reviews job topology. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Event-time, not processing-time.** Every record carries `occurred_at_ms`; windows fire on watermarks, never wall-clock. Processing-time logic silently corrupts attribution when data arrives late or replays.
2. **The key-by IS the tenant key.** `stream.keyBy(r -> r.tenantId)` — keyed state, windows, and joins are all tenant-scoped. A keyed state access that crosses tenants is a P0 (see `multi-tenancy-isolation`).
3. **Exactly-once end-to-end or document why not.** `EXACTLY_ONCE` checkpointing + a transactional/2PC sink (Kafka transactional producer, Iceberg commit, JDBC XA). At-least-once is allowed only for idempotent sinks (a `ReplacingMergeTree`-style OLAP table) and must be declared in the job's header comment.
4. **Bounded state.** Every keyed/window state has a TTL or a clear retention bound. Unbounded state is the #1 Flink outage cause.
5. **The same job handles live + replay.** Reading from a Kafka offset/timestamp or an Iceberg snapshot uses the identical operator graph — no separate "backfill" code path (mirrors `integration-connectors`).

## Watermarks + late data
```java
WatermarkStrategy.<Event>forBoundedOutOfOrderness(Duration.ofSeconds(30))
    .withTimestampAssigner((e, ts) -> e.occurredAtMs())
    .withIdleness(Duration.ofMinutes(1));   // don't stall a window on a quiet partition
```
- Pick allowed-lateness from the data contract (`data-quality` freshness SLA), not a guess.
- Route dropped-late records to a **side output** → DLQ topic → re-pull window. Never silently discard (a discarded late conversion is a missed attribution).

## Keyed state, windows, joins
- **State backend:** RocksDB (incremental checkpoints) for large state; heap only for tiny state. Checkpoint to object storage.
- **Windows:** prefer tumbling/sliding event-time windows; session windows for journey/identity stitching. Use `reduce`/`aggregate` (incremental) over `process` (buffers the whole window) wherever possible.
- **Joins:** interval joins (bounded) or temporal table joins for enrichment against slowly-changing dimensions. An unbounded regular join is a memory leak.

## Exactly-once + checkpoints
```java
env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30_000);
env.getCheckpointConfig().setExternalizedCheckpointCleanup(RETAIN_ON_CANCELLATION);
env.getCheckpointConfig().setTolerableCheckpointFailureNumber(3);
```
- Sinks must be transactional for the exactly-once chain to hold (Kafka `Sink` with `DeliveryGuarantee.EXACTLY_ONCE`, Iceberg `FlinkSink`, or a 2PC sink). A non-transactional sink downgrades the whole job to at-least-once.
- **Savepoints** for upgrades: take a savepoint, deploy new job version, restore. State schema must evolve compatibly (Avro/POJO state migration) — breaking state schema = rebuild from replay.

## Operability
- **Backpressure** is the primary health signal — alarm on it; it means a downstream sink/operator is the bottleneck. (`observability`, `incident-response`.)
- **Checkpoint duration + failure rate**, **records-lag-max** on source, **state size** per operator are the four dashboard metrics that matter.
- Parallelism: set per-operator, key by tenant for even distribution; watch for **data skew** (one hot tenant) — pre-aggregate or salt the key for that tenant.
- Trace propagation: carry the correlation/trace ID from the source event through to the sink (Stage-4 traceability requirement).

## Effort-tier note (`cost-routing-paradigms`)
Stream processing is **deterministic/statistical compute** — the cheapest tier. Enrichment, attribution windows, and identity stitching belong here, NOT in a model call. Reaching for an LLM to do what a keyed window + rule can do is the wrong tier. Real-time **features** computed here land in the feature store (`feature-store-feast`) for online serving.

## Anti-patterns
Processing-time windows · unbounded state / regular joins · non-transactional sink claimed as exactly-once · a separate backfill codebase · per-record external lookups instead of a temporal-table join · ignoring backpressure · keying by anything but the tenant for tenant-scoped aggregates.
