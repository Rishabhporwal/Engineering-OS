---
name: event-driven-kafka
description: Reference implementation — an async backbone on Kafka + a schema registry: topics/producers/consumers, broker-level idempotence, DLQ/retry, schema evolution. Partition key IS the tenant key; replayable.
---

# Event-Driven — Kafka + Schema Registry + Avro

> **Reference implementation.** This skill documents one concrete binding of the async-backbone seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind this seam to a different broker (e.g. a managed pub/sub, Pulsar, RabbitMQ) or schema format. The *patterns* here — tenant-keyed partitioning, broker-level idempotence as the primary guarantee, manual commit, DLQ/retry, backward-compatible schema evolution, replayable retention — are what transfer; Kafka + a schema registry is the example.

One async backbone: **Kafka** (e.g. Amazon MSK) + a **schema registry** (Avro) + a **CDC connector** (e.g. Debezium for OLTP→Kafka). **Long/infinite retention** (tiered storage to object storage) so every downstream materialization is replayable.

> **The diskless / S3-direct shift (2026).** For new **high-volume** workloads the **diskless broker** model (KIP-1150 — brokers write directly to object storage, no inter-broker replication of local disk) went from experiment to a default consideration in ~18 months, because it removes the cross-AZ replication + local-storage cost that dominates high-throughput topics (a `finops-cost` lever). Reference bindings: **WarpStream** and **AutoMQ** (S3-direct, Kafka-API-compatible). **Redpanda** is the drop-in alternative that keeps the broker-centric model (good for ops simplicity / JVM-pain, weaker on the structural cloud-cost problem diskless targets). All speak the Kafka API — the patterns below (tenant-keyed partitioning, broker-level idempotence, manual commit, replayable retention) transfer unchanged; `STACK.md` binds the broker. For the **Redpanda + Apicurio + Avro** binding — including **native Iceberg-Topics broker→Iceberg Bronze materialization** (no hand-rolled writers) — see `redpanda-apicurio-avro`; for **app-level consumer processing** (KafkaJS/CJSK on Kubernetes) see `stream-processing-consumers`.

## When to use the event bus
Source data ingestion (`integrations.orders.v1`, …) · cross-service state propagation (`operations.tenant.changed.v1`) · trigger fan-out (`intelligence.anomaly.detected.v1` → notifications) · replay (late-data backfills, reconciliation) · CDC (OLTP WAL → bus).
**NOT for:** synchronous service calls (RPC) · simple cron jobs (a scheduler) · in-process queues (push to the bus instead).

## Topic naming: `<domain>.<entity>.<event_type>.v<version>`
Producers/consumers (representative): `integrations.{orders,shipments,events,refunds,customers}.v1` (ingestion → analytics/intelligence) · `operations.{tenant,settings,goals}.changed.v1` (core → all) · `analytics.metrics.daily_materialized.v1` + `analytics.subject_state.changed.v1` (analytics → downstream) · `intelligence.{anomaly.detected,insight.generated,brief.generated}.v1` (→ notifications) · `lifecycle.outreach.completed.v1` + `lifecycle.recovered_value.attributed.v1` · `notifications.alert.fired.v1`.

## Topic config
```yaml
partitions: 24                  # tenant-key hash distribution
replicationFactor: 3
configs: { retention.ms: -1, compression.type: zstd, cleanup.policy: delete, segment.ms: 86400000, min.insync.replicas: 2 }
```
Per-domain retention: source `integrations.*` infinite (replay) · `analytics.*`/`operations.*`/`notifications.*` bounded (e.g. 30d) · `intelligence.*` medium (e.g. 90d) · audit-class topics (outreach + attributed-value, and the system-of-record audit log) infinite.

## Partition key — the tenant key (NON-NEGOTIABLE)
```python
await producer.send_and_wait(topic="integrations.orders.v1", key=tenant_id.encode(), value=avro_encoded)
```
A tenant's events always land in the same partition → per-tenant ordering guaranteed. Cross-tenant ordering is not preserved (and is typically irrelevant).

## Avro schemas + schema registry
Schemas in `protos/events/<domain>/<entity>.v<n>.avsc` with the **tenant key**, `source`, `source_event_id` (idempotency), `occurred_at_ms`, `ingested_at_ms`, monetary `*_minor` (long, minor units) + `currency_code`, nullable fields as `["null", T]` with defaults. Registered with the schema registry. **Compatibility: BACKWARD** by default (consumers older than producers still work).

### Schema evolution
Allowed (BACKWARD): add a field WITH a default · remove a field that always had a default · promote `int→long`, `float→double`.
Forbidden (→ `.v2`): rename a field · remove a required field · incompatible type change.
CI gate: `buf breaking` for contracts; the registry rejects incompatible Avro.

## Idempotency (NON-NEGOTIABLE) — broker-level is primary
Stable `event_id` per source: e.g. `(tenant_id, order.id)` for an orders connector · `(tenant_id, account_id, campaign_id, date)` for an ads connector · `(tenant_id, shipment_id, status)` for a logistics connector · `(tenant_id, table, date, …)` for a rollup.

1. **Broker-level idempotent producer — the primary guarantee:** `enable.idempotence=true` (default-on since Kafka 3.0) + **`acks=all`** dedupes producer retries at the broker so a retry never double-publishes. This is exactly-once-into-the-log, not a cache.
2. **Transactional producer + `read_committed` consumers** for outbox / audit-log cross-partition writes — wrap produce(s) in `producer.transaction()` so a partial multi-partition write never becomes visible.
3. **A cache SETNX is the app-level backstop only** (dedup across separate producer sessions / connector re-runs), NOT the primary guarantee.
```typescript
const producer = kafka.producer({ 'enable.idempotence': true, 'acks': 'all' });  // PRIMARY
const setResult = await cache.set(`idempotency:${source}:${tenantId}:${eventId}`, '1', 'NX', 'EX', 86400);
if (!setResult) return;  // app-level backstop only
```
Consumer side: an OLAP `ReplacingMergeTree`-style engine handles late-arriving updates.

## Manual commit (no auto-commit)
Auto-commit is at-most-once → data loss on crash. Commit manually after a successful write.
```python
consumer = AIOKafkaConsumer("integrations.orders.v1", group_id="analytics-orders",
    enable_auto_commit=False, value_deserializer=avro_deserializer)
async for msg in consumer:
    await write_to_olap_replacing(msg.value)
    await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
```
TS: use a maintained Kafka client — `consumer.run({ autoCommit: false, eachMessage })`.

## Consumer group naming: `<service>-<purpose>`
`analytics-orders-consumer` · `intelligence-anomaly-detector` · `notifications-alerts` · `lifecycle-segment-refresh`. One group per logical workload; same group shares partitions, different groups each get every message. Partition count = max parallelism.

## DLQ + retry
```
integrations.orders.v1 → (fail) → integrations.orders.retry-1.v1 (60s) → retry-2.v1 (5min) → orders.dlq.v1 (manual triage)
```
A per-service wrapper / stream processor re-publishes after a delay with retry count in headers. The DLQ has a manual triage consumer (an admin UI surfaces depth + age).

## CDC via a log-based connector
OLTP WAL → CDC connector → `cdc.public.<table>.v1` → the analytics service mirrors recent OLTP state in the OLAP store without querying the owning service's DB directly.

## Monitoring
Consumer lag per group/topic (alarm > threshold) · under-replicated partitions (alarm if non-zero) · bytes in/out. A monitor `consumer-lag-spike` → page after a sustained breach.

## Scale
24 partitions ≈ a few K msg/s/partition headroom · a tenant can occupy multiple consumers across services in different groups · large tenants use per-tenant key-based throttling at ingestion to avoid head-of-line blocking.

## Common failure modes
Auto-commit data loss (use manual) · non-idempotent producer (set `enable.idempotence=true` + `acks=all`; cache SETNX is backstop only) · schema-breaking change without a version bump (the registry rejects; use `.v2`) · missing the tenant key in the envelope · cross-tenant ordering assumption · rebalance loops (tune `session.timeout.ms`) · DLQ ignored (surface depth+age) · source topics on finite retention (defeats replay — configure long/infinite).

## References
The Product Canon's `STACK.md` (the concrete broker + registry binding) + the data architecture HLD/LLD · `backend-fastify-trpc-grpc` (a TS client) · `python-services` (an async consumer) · `integration-connectors` (producer side) · `clickhouse-olap` (OLAP consumer tables) · `devops-aws` §event-bus · `idempotency-handling`.
