---
name: event-driven-kafka
description: Brain's async backbone — Amazon MSK + AWS Glue Schema Registry + Avro. Auto-load whenever designing topics, writing producers/consumers, handling idempotency, exactly-once delivery, DLQ + retry, schema evolution. Multi-tenant: every event envelope carries workspace_id; partition key IS workspace_id. Backed by infinite retention via MSK tiered storage to S3 — every downstream materialization is replayable.
---

# Event-Driven — MSK + Glue Schema Registry + Avro

Brain's async backbone is **Amazon MSK** (managed Kafka) + **AWS Glue Schema Registry** (Avro) + **MSK Connect** (Debezium for Postgres → Kafka CDC). **Topics with infinite retention** (S3-backed tiered storage) so every downstream materialization is replayable.

## When to use Kafka (in Brain context)

Brain uses Kafka for:

- **Source data ingestion** — Maya publishes canonical events (`integrations.orders.v1`, etc.)
- **Cross-service state propagation** — `operations.workspace.changed.v1`, `analytics.metrics.daily_materialized.v1`
- **Trigger fan-out** — `intelligence.anomaly.detected.v1` → notifications-service + alerts
- **Replay** — late-data backfills, reconciliation jobs replay from infinite retention
- **CDC** — Debezium streams Postgres WAL → Kafka so analytics-service can mirror recent OLTP state

Brain does NOT use Kafka for:
- Synchronous service-to-service calls (gRPC instead — see canon/technical-requirements.md)
- Simple cron-triggered jobs (EventBridge Scheduler)
- In-process job queues (we don't have BullMQ; if you need queues, push the event to Kafka)

## Topic naming convention

```
<domain>.<entity>.<event_type>.v<version>
```

| Topic | Producer | Consumers |
|---|---|---|
| `integrations.orders.v1` | ingestion-service | analytics-service, intelligence-service |
| `integrations.shipments.v1` | ingestion-service | analytics-service (RTO state) |
| `integrations.ads.v1` | ingestion-service | analytics-service |
| `integrations.refunds.v1` | ingestion-service | analytics-service |
| `integrations.customers.v1` | ingestion-service | analytics-service, intelligence-service (Brand Fingerprint) |
| `operations.workspace.changed.v1` | core-service | all |
| `operations.settings.changed.v1` | core-service | analytics-service (cache invalidation), intelligence-service |
| `operations.goals.changed.v1` | core-service | analytics-service (RAG re-evaluation), notifications-service |
| `analytics.metrics.daily_materialized.v1` | analytics-service | intelligence-service, notifications-service |
| `analytics.customer_state.changed.v1` | analytics-service | intelligence-service, lifecycle-service (RFM refresh) |
| `intelligence.anomaly.detected.v1` | intelligence-service | notifications-service |
| `intelligence.insight.generated.v1` | intelligence-service | notifications-service |
| `intelligence.morning_brief.generated.v1` | intelligence-service | notifications-service (push at 07:00 IST) |
| `lifecycle.outreach.completed.v1` | lifecycle-service | analytics-service (attribution job input) |
| `lifecycle.recovered_revenue.attributed.v1` | analytics-service | notifications-service |
| `notifications.alert.fired.v1` | notifications-service | (audit) |

## Topic configuration

```yaml
# infra/stacks/kafka.ts CDK config
topic:
  name: integrations.orders.v1
  partitions: 24                       # workspace_id hash distribution
  replicationFactor: 3
  configs:
    retention.ms: -1                   # infinite (tiered storage)
    compression.type: zstd
    cleanup.policy: delete
    segment.ms: 86400000               # 1 day
    min.insync.replicas: 2
```

Per-domain retention rule:
- `integrations.*` → infinite (S3 tiered storage; for replay)
- `analytics.*` → 30 days
- `operations.*` → 30 days
- `intelligence.*` → 90 days
- `lifecycle.*` → infinite for outreach + recovered_revenue (attribution audit trail)
- `notifications.*` → 30 days

## Partition key — workspace_id (NON-NEGOTIABLE)

```python
await producer.send_and_wait(
    topic="integrations.orders.v1",
    key=workspace_id.encode(),         # ← partition by workspace
    value=avro_encoded,
)
```

Single workspace's events always land in the same partition → ordering guaranteed per workspace. Cross-workspace ordering is not preserved (and is irrelevant for Brain).

## Avro schemas + Glue Schema Registry

```avro
// protos/events/integrations/orders.v1.avsc
{
  "type": "record",
  "namespace": "brain.events.integrations",
  "name": "OrderEvent",
  "doc": "Canonical order event from any source (Shopify, etc.)",
  "fields": [
    { "name": "workspace_id",    "type": "string", "doc": "Tenant UUID" },
    { "name": "source",          "type": "string", "doc": "shopify | woocommerce | manual" },
    { "name": "source_event_id", "type": "string", "doc": "Stable per source (idempotency)" },
    { "name": "order_id",        "type": "string" },
    { "name": "customer_id",     "type": "string" },
    { "name": "occurred_at_ms",  "type": "long", "logicalType": "timestamp-millis" },
    { "name": "ingested_at_ms",  "type": "long", "logicalType": "timestamp-millis" },
    { "name": "total_minor",     "type": "long", "doc": "Paisa (Int64)" },
    { "name": "discount_minor",  "type": "long", "default": 0 },
    { "name": "tax_minor",       "type": "long", "default": 0 },
    { "name": "shipping_minor",  "type": "long", "default": 0 },
    { "name": "payment_method",  "type": "string", "doc": "cod | prepaid" },
    { "name": "campaign_id",     "type": ["null", "string"], "default": null },
    { "name": "pincode",         "type": ["null", "string"], "default": null }
  ]
}
```

Registered with Glue Schema Registry. Compatibility mode: **BACKWARD** by default (consumers older than producers still work). Breaking changes → new topic version (`.v2`).

## Schema evolution rules

Allowed (BACKWARD compatible):
- Add a new field WITH a default
- Remove a field that always had a default
- Promote `int` → `long`, `float` → `double`

Forbidden (use `.v2`):
- Rename a field
- Remove a required field
- Change a field's type to incompatible

CI gate: `buf breaking` for proto files; Glue Schema Registry rejects incompatible Avro changes.

## Idempotency (NON-NEGOTIABLE)

Every event has a stable `event_id` per source:

| Source | event_id formula |
|---|---|
| Shopify orders | `(workspace_id, order.id)` |
| Meta insights | `(workspace_id, ad_account_id, campaign_id, date)` |
| Google insights | `(workspace_id, customer_id, campaign_id, date)` |
| Shiprocket shipments | `(workspace_id, awb_code, status)` |
| Klaviyo events | `(workspace_id, event_id)` |
| analytics rollups | `(workspace_id, table, date, customer_type, channel)` |

Producer side (TS):
```typescript
// Redis SETNX before publishing
const key = `idempotency:${source}:${workspaceId}:${eventId}`;
const setResult = await redis.set(key, '1', 'NX', 'EX', 86400);   // 24h TTL
if (!setResult) return;                                            // already seen
await producer.send({ topic, messages: [...] });
```

Consumer side (ReplicatedReplacingMergeTree in ClickHouse handles late-arriving updates):
```python
async for msg in consumer:
    await write_to_clickhouse_replacing(msg.value)
    await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
```

## Manual commit (no auto-commit)

Auto-commit at-most-once → data loss on crash. Manual commit after successful write:

```python
# Python — aiokafka
consumer = AIOKafkaConsumer(
    "integrations.orders.v1",
    bootstrap_servers=settings.KAFKA_BROKERS,
    group_id="analytics-orders",
    enable_auto_commit=False,            # MANUAL
    value_deserializer=avro_deserializer,
)
```

```typescript
// TS — KafkaJS
const consumer = kafka.consumer({
  groupId: 'notifications-alerts',
  sessionTimeout: 30000,
  heartbeatInterval: 3000,
});

await consumer.run({
  eachMessage: async ({ topic, partition, message, heartbeat }) => {
    await processMessage(message);
    // Auto-commits at the end if `autoCommit: true` (default) — set false for manual:
  },
  autoCommit: false,
});
```

## Consumer group naming

```
<service>-<purpose>
```

Examples:
- `analytics-orders-consumer` — analytics-service consuming `integrations.orders.v1`
- `intelligence-anomaly-detector` — intelligence-service consuming `analytics.metrics.daily_materialized.v1`
- `notifications-alerts` — notifications-service consuming `intelligence.anomaly.detected.v1`
- `lifecycle-rfm-refresh` — lifecycle-service consuming `analytics.customer_state.changed.v1`

One consumer group per logical workload. Two consumers in the same group share the partitions; two consumers in different groups both get every message.

## DLQ + retry pattern

```
Topic: integrations.orders.v1
  ↓ consumer fails
Retry topic: integrations.orders.retry-1.v1   (60s delay)
  ↓ fails again
Retry topic: integrations.orders.retry-2.v1   (5 min delay)
  ↓ fails again
DLQ topic: integrations.orders.dlq.v1         (manual triage)
```

Implementation: a Kafka Streams or per-service wrapper that re-publishes after a delay, with retry count in headers. DLQ has a manual consumer (admin UI) for triage.

## CDC via Debezium on MSK Connect

```
Postgres WAL  →  Debezium connector (MSK Connect)  →  Kafka topic: cdc.public.<table>.v1
                                                            ↓
                                                       analytics-service consumes for recent-OLTP mirror in CH
```

Used for `audience`, `outreach`, `rfm_score`, `ai.decision_log` — analytics needs recent state without querying core-service's Postgres directly.

## Monitoring (canon/technical-requirements.md)

CloudWatch metrics emitted:
- `MSK/KafkaConsumerLag` per consumer group per topic — alarm when > threshold
- `MSK/KafkaBytesIn` / `MSK/KafkaBytesOut`
- `MSK/UnderReplicatedPartitions` — alarm if non-zero

OpenSearch monitor:
- `kafka-consumer-lag-spike` — `MSK/KafkaConsumerLag > <threshold>` for 5 minutes → PagerDuty

## Per-workspace fan-out at scale

100k req/min target:
- 24 partitions per topic gives ~4K msg/sec/partition headroom
- Single workspace can occupy multiple consumers in parallel (different services in different groups)
- For very large workspaces, key-based throttling: ingestion-service backoffs per-workspace to avoid head-of-line blocking

## Common failure modes

- **Auto-commit producing data loss** — consumer crashes after commit, before processing. Use manual commit.
- **Non-idempotent producer** — retry double-publishes. Redis SETNX before send.
- **Schema-breaking change without bump** — Glue rejects. Use additive evolution; `.v2` for breaking.
- **Missing workspace_id in envelope** — downstream can't partition. Producer call MUST include it.
- **Cross-workspace ordering assumption** — don't make it. Partition key is workspace_id, not global.
- **Consumer group rebalance loops** — `session.timeout.ms` too low or sticky partition pressure. Tune timeout; partition count = max parallelism.
- **DLQ ignored** — DLQ messages pile up; manual triage missed. Admin dashboard surfaces DLQ depth + age.
- **`integrations.*` retention finite** — defeats replay. Configure infinite + tiered storage.

## References

- `canon/technical-requirements.md` — canonical Kafka topology + per-source flows
- `canon/technical-requirements.md` §kafka + §debezium
- `skills/backend-fastify-trpc-grpc/SKILL.md` — TS KafkaJS patterns (Brain's Node services consume + produce here)
- `skills/python-services/SKILL.md` §kafka — aiokafka patterns
- `skills/integration-connectors/SKILL.md` — producer side (Maya's domain)
- `skills/clickhouse-olap/SKILL.md` §kafka-engine-tables — CH consumer engine pattern
- `skills/devops-aws/SKILL.md` §msk — MSK CDK config
