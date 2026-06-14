---
name: redpanda-apicurio-avro
description: Reference implementation — a Redpanda event backbone (Raft, no JVM/ZooKeeper, tiered storage to S3) + Apicurio schema registry (Confluent ccompat) + Avro, with native Redpanda→Iceberg topic-materialization for the lakehouse Bronze layer (no hand-rolled writers). Kafka-API-compatible; partition key IS the tenant key. Owner Data Engineer.
---

# Event Backbone — Redpanda + Apicurio + Avro (+ Iceberg Topics)

> **Reference implementation.** One concrete binding of the **async-backbone seam** + the **Bronze-ingest path** of the lakehouse seam (`lakehouse-iceberg`). The OS is stack-agnostic — `STACK.md` may bind the broker to Apache Kafka (MSK)/WarpStream/AutoMQ and the registry to Confluent SR / Glue Schema Registry. The *patterns* — tenant-keyed partitioning, broker-level idempotence, BACKWARD Avro evolution, the Confluent 5-byte wire format, replayable tiered retention, and **letting the broker materialize Iceberg instead of a sink connector** — transfer; Redpanda + Apicurio is the example.

> **Redpanda is Kafka-API-compatible, not Kafka.** Everything in `event-driven-kafka` (topic naming, tenant-key partitioning, consumer groups, DLQ/retry, idempotent producer, manual commit) transfers **unchanged** — KafkaJS/librdkafka/Java clients connect with no code change. **Redpanda-specific:** Raft-per-partition + Raft controller (no ZooKeeper, **no separate KRaft quorum to run**), C++/thread-per-core (no JVM, no GC pauses), the `rpk` CLI, the `cloud_storage_*`/`retention.local.*` tiered-storage split, and **Iceberg Topics**. (Apache Kafka 4.0 also removed ZooKeeper → KRaft-only, so "no ZK" no longer differentiates; the live differentiators are *no JVM / no controller quorum / Iceberg Topics*.)

**Owner:** Data Engineer; Architect reviews topic/partition layout + the catalog binding. Canon: `STACK.md`, `COMPLIANCE.md`.

## Invariants (NON-NEGOTIABLE)
1. **Partition key IS the tenant key** — `send({ messages:[{ key: tenantId, value }] })`. Per-tenant ordering within one partition; cross-tenant ordering not provided (irrelevant). Same rule as `event-driven-kafka`/`stream-processing-flink`.
2. **No hand-rolled TS Iceberg writers — the broker materializes (Flag B).** Bronze tables come from **Redpanda Iceberg Topics** (`redpanda.iceberg.mode`), not a consumer opening Parquet/Iceberg files (which re-implements atomic commits, schema mapping, partitioning, compaction badly). Fallback if `STACK.md` can't use Iceberg Topics: a **managed sink** (Tableflow / Iceberg Sink Connector) — still never bespoke writer code.
3. **The registry is the contract; Avro is BACKWARD-compatible.** Register before publishing; the payload carries the schema ID (5-byte Confluent format). A breaking change is a new `.v2` subject/topic, never an in-place edit.
4. **Apicurio enforces NO compatibility rule until you configure one — set it explicitly.** Unlike Confluent SR (BACKWARD on by default), a fresh Apicurio registry applies *no* rule on write — the ccompat endpoint *reports* BACKWARD but writes are ungated. **Set a global `BACKWARD` (or `BACKWARD_TRANSITIVE`) COMPATIBILITY rule** or evolution is silently ungated (the #1 migration trap).
5. **Broker-level idempotent producer is the primary dedup guarantee** (`enable.idempotence=true` default + `acks=all`); a cache/DB SETNX is the cross-session backstop only.
6. **Source topics carry long/infinite retention via tiered storage** — `retention.local.target.*` bounds the local-disk *cache*; `retention.ms/bytes` bound the *total* (S3) history. Finite total retention on a source topic defeats replay + Iceberg backfill.
7. **Region-pinned object storage** — `cloud_storage_bucket` + the Iceberg warehouse live in the tenant's region (`region-and-locale`); a cross-region raw read is a residency breach unless `COMPLIANCE.md` allows it.

## Topic + tiered storage (rpk)
```bash
rpk topic create integrations.orders.v1 --partitions 24 --replicas 3 \
  -c retention.ms=-1 -c compression.type=zstd \
  -c retention.local.target.bytes=20000000000   # ~20GB on local SSD; rest in S3 (infinite total)
```
Sizing ceilings: ≤ ~1,000 partitions/core (`topic_partitions_per_shard`), ≥2 MB RAM/partition-replica, ≥2 GB RAM/core. Tiered storage (`cloud_storage_enabled=true` + bucket/region/creds) makes local disk a cache and S3 the durable tier → effectively infinite retention; `remote read` serves historical fetches + Iceberg backfill.

## Iceberg Topics — the Bronze materialization
Maturity: **beta 24.3 → GA 25.1** (first GA Kafka→Iceberg; DLQ + custom partitioning landed in 25.1) → **25.2** added JSON-Schema + Unity + **AWS Glue**. Enterprise license; Parquet output.
```bash
# cluster: iceberg_enabled=true
rpk topic create analytics.events.v1 --partitions 24 \
  -c redpanda.iceberg.mode=value_schema_id_prefix \
  -c redpanda.iceberg.partition.spec='(tenant_id, hour(redpanda.timestamp))' \
  -c redpanda.iceberg.invalid.record.action=dlq
```
- **Modes:** `disabled` · `key_value` (no schema; opaque payload) · **`value_schema_id_prefix`** (columnar; producers write the Confluent wire format — **the normal Avro path**) · `value_schema_latest` (raw payload, no magic byte; table shifts as the latest schema changes — riskier, avoid for evolving topics).
- **Partitioning:** default `hour(redpanda.timestamp)` — but **AWS Glue applies an empty spec (unpartitioned table) unless you set an explicit `redpanda.iceberg.partition.spec`**. Set `(tenant_id, hour(...))` to honor Invariant #1.
- **DLQ (25.1+):** untranslatable records go to a sibling **`<topic>~dlq`** table; `invalid.record.action=drop` silently discards — **don't drop**, triage the `~dlq` table (`data-quality`).
- **Catalog:** `iceberg_catalog_type=rest` (recommended — enables table maintenance + safe multi-engine concurrency) pointed at **Glue Iceberg REST** with `iceberg_rest_catalog_authentication_mode=aws_sigv4` (required for Glue). Glue is one global catalog per account → each cluster uses a **distinct namespace** to avoid collisions. Read from Athena/Spark/Trino/StarRocks/PyIceberg.
- **Semantics — read carefully:** files commit via atomic snapshots (time-travel works), but Iceberg Topics is **at-least-once into the table, NOT exactly-once**. Treat Bronze as at-least-once: carry a stable `event_id = (tenant_id, source, source_event_id)` and **dedup at the Silver `MERGE INTO`** (`lakehouse-iceberg`), exactly as for a sink connector.

## Apicurio + Avro wire format (KafkaJS)
Apicurio 3.x speaks the Confluent API at **`/apis/ccompat/v7`**; the 5-byte wire format (`[0x00][4-byte schema id][Avro body]`) Just Works. KafkaJS has no native serializer → use `@kafkajs/confluent-schema-registry`:
```ts
const registry = new SchemaRegistry({ host: 'http://apicurio:8080/apis/ccompat/v7' });
const { id } = await registry.register({ type: SchemaType.AVRO, schema: avscString });
await producer.send({ topic, messages: [{ key: tenantId, value: await registry.encode(id, payload) }] });
// consumer: const decoded = await registry.decode(message.value);
```
**The same encoded bytes feed both your KafkaJS consumers and the broker's Iceberg materialization** (`value_schema_id_prefix`). Evolution discipline = BACKWARD (add-with-default / remove-defaulted / widen int→long); breaking → `.v2`; use `*_TRANSITIVE` for long-lived Bronze where any replay/historical reader must hold. CI gate: the registry's compatibility check rejects the schema — but only if Invariant #4 set the rule.

## Anti-patterns
Hand-rolled Iceberg/Parquet writer instead of Iceberg Topics · assuming Apicurio enforces BACKWARD by default (it enforces nothing until configured) · `value_schema_latest` for an evolving topic · default partition spec on Glue (unpartitioned table) · `invalid.record.action=drop` (silent loss — use `~dlq`) · treating Iceberg Topics as exactly-once (dedup at Silver) · finite total retention on a source topic · partitioning Iceberg by anything but `(tenant_id, time)` · carrying Kafka JVM/ZooKeeper ops habits onto Redpanda · publishing without registering · cross-region bucket.

## References
`event-driven-kafka` (the generic Kafka patterns this specializes) · `lakehouse-iceberg` (Bronze/Silver, MERGE dedup) · `stream-processing-consumers` (the KafkaJS consumers) · `data-quality` (`~dlq` triage) · `multi-tenancy-isolation` · `region-and-locale` · `idempotency-handling` · `local-dev-environment` (Redpanda in Compose).
