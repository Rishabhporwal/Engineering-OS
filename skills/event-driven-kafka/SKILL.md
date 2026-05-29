---
name: event-driven-kafka
description: Brain's async backbone — MSK + Glue Schema Registry + Avro. Topics/producers/consumers, broker-level idempotence, DLQ/retry, schema evolution. Partition key IS workspace_id; replayable.
---

# Event-Driven — MSK + Glue Schema Registry + Avro

Brain's async backbone: **Amazon MSK** + **AWS Glue Schema Registry** (Avro) + **MSK Connect** (Debezium for Postgres→Kafka CDC). **Infinite retention** (S3-backed tiered storage) so every downstream materialization is replayable.

## When to use Kafka
Source data ingestion (`integrations.orders.v1`, …) · cross-service state propagation (`operations.workspace.changed.v1`) · trigger fan-out (`intelligence.anomaly.detected.v1` → notifications) · replay (late-data backfills, reconciliation) · CDC (Postgres WAL → Kafka).
**NOT for:** synchronous service calls (gRPC) · simple cron jobs (EventBridge Scheduler) · in-process queues (no BullMQ — push to Kafka).

## Topic naming: `<domain>.<entity>.<event_type>.v<version>`
Producers/consumers (representative): `integrations.{orders,shipments,ads,refunds,customers}.v1` (ingestion → analytics/intelligence) · `operations.{workspace,settings,goals}.changed.v1` (core → all) · `analytics.metrics.daily_materialized.v1` + `analytics.customer_state.changed.v1` (analytics → intelligence/lifecycle) · `intelligence.{anomaly.detected,insight.generated,morning_brief.generated}.v1` (→ notifications) · `lifecycle.outreach.completed.v1` + `lifecycle.recovered_revenue.attributed.v1` · `notifications.alert.fired.v1`.

## Topic config
```yaml
partitions: 24                  # workspace_id hash distribution
replicationFactor: 3
configs: { retention.ms: -1, compression.type: zstd, cleanup.policy: delete, segment.ms: 86400000, min.insync.replicas: 2 }
```
Per-domain retention: `integrations.*` infinite (replay) · `analytics.*`/`operations.*`/`notifications.*` 30d · `intelligence.*` 90d · `lifecycle.*` infinite for outreach + recovered_revenue (attribution audit).

## Partition key — workspace_id (NON-NEGOTIABLE)
```python
await producer.send_and_wait(topic="integrations.orders.v1", key=workspace_id.encode(), value=avro_encoded)
```
A workspace's events always land in the same partition → per-workspace ordering guaranteed. Cross-workspace ordering is not preserved (irrelevant for Brain).

## Avro schemas + Glue Schema Registry
Schemas in `protos/events/<domain>/<entity>.v<n>.avsc` with `workspace_id`, `source`, `source_event_id` (idempotency), `occurred_at_ms`, `ingested_at_ms`, monetary `*_minor` (long/paisa), nullable fields as `["null", T]` with defaults. Registered with Glue. **Compatibility: BACKWARD** by default (consumers older than producers still work).

### Schema evolution
Allowed (BACKWARD): add a field WITH a default · remove a field that always had a default · promote `int→long`, `float→double`.
Forbidden (→ `.v2`): rename a field · remove a required field · incompatible type change.
CI gate: `buf breaking` for protos; Glue rejects incompatible Avro.

## Idempotency (NON-NEGOTIABLE) — broker-level is primary
Stable `event_id` per source: Shopify `(workspace_id, order.id)` · Meta `(workspace_id, ad_account_id, campaign_id, date)` · Google `(workspace_id, customer_id, campaign_id, date)` · Shiprocket `(workspace_id, awb_code, status)` · Klaviyo `(workspace_id, event_id)` · rollups `(workspace_id, table, date, customer_type, channel)`.

1. **Broker-level idempotent producer — the primary guarantee:** `enable.idempotence=true` (default-on since Kafka 3.0) + **`acks=all`** dedupes producer retries at the broker so a retry never double-publishes. This is exactly-once-into-the-log, not Redis.
2. **Transactional producer + `read_committed` consumers** for outbox / Decision-Log cross-partition writes — wrap produce(s) in `producer.transaction()` so a partial multi-partition write never becomes visible.
3. **Redis SETNX is the app-level backstop only** (dedup across separate producer sessions / connector re-runs), NOT the primary guarantee.
```typescript
const producer = kafka.producer({ 'enable.idempotence': true, 'acks': 'all' });  // PRIMARY
const setResult = await redis.set(`idempotency:${source}:${workspaceId}:${eventId}`, '1', 'NX', 'EX', 86400);
if (!setResult) return;  // app-level backstop only
```
Consumer side: ClickHouse `ReplicatedReplacingMergeTree` handles late-arriving updates.

## Manual commit (no auto-commit)
Auto-commit is at-most-once → data loss on crash. Commit manually after a successful write.
```python
consumer = AIOKafkaConsumer("integrations.orders.v1", group_id="analytics-orders",
    enable_auto_commit=False, value_deserializer=avro_deserializer)
async for msg in consumer:
    await write_to_clickhouse_replacing(msg.value)
    await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
```
TS: `@confluentinc/kafka-javascript` (KafkaJS abandoned under Kafka 4.0) — `consumer.run({ autoCommit: false, eachMessage })`.

## Consumer group naming: `<service>-<purpose>`
`analytics-orders-consumer` · `intelligence-anomaly-detector` · `notifications-alerts` · `lifecycle-rfm-refresh`. One group per logical workload; same group shares partitions, different groups each get every message. Partition count = max parallelism.

## DLQ + retry
```
integrations.orders.v1 → (fail) → integrations.orders.retry-1.v1 (60s) → retry-2.v1 (5min) → orders.dlq.v1 (manual triage)
```
A per-service wrapper / Kafka Streams re-publishes after a delay with retry count in headers. DLQ has a manual triage consumer (admin UI surfaces depth + age).

## CDC via Debezium on MSK Connect
Postgres WAL → Debezium → `cdc.public.<table>.v1` → analytics-service mirrors recent OLTP state in CH (`audience`, `outreach`, `rfm_score`, `ai.decision_log`) without querying core-service's Postgres directly.

## Monitoring
`MSK/KafkaConsumerLag` per group/topic (alarm > threshold) · `MSK/UnderReplicatedPartitions` (alarm if non-zero) · `MSK/KafkaBytesIn/Out`. OpenSearch monitor `kafka-consumer-lag-spike` → PagerDuty after 5 min.

## Scale (100k req/min)
24 partitions ≈ 4K msg/s/partition headroom · a workspace can occupy multiple consumers across services in different groups · large workspaces use per-workspace key-based throttling at ingestion to avoid head-of-line blocking.

## Common failure modes
Auto-commit data loss (use manual) · non-idempotent producer (set `enable.idempotence=true` + `acks=all`; Redis SETNX is backstop only) · schema-breaking change without bump (Glue rejects; use `.v2`) · missing `workspace_id` in envelope · cross-workspace ordering assumption · rebalance loops (tune `session.timeout.ms`) · DLQ ignored (surface depth+age) · `integrations.*` finite retention (defeats replay — configure infinite).

## References
`canon/technical-requirements.md` §kafka + §debezium · `backend-fastify-trpc-grpc` (TS Confluent client) · `python-services` (aiokafka) · `integration-connectors` (producer side) · `clickhouse-olap` (CH Kafka engine tables) · `devops-aws` §msk · `idempotency-handling`.
