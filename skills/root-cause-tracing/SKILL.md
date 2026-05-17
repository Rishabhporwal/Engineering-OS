---
name: root-cause-tracing
description: Trace bugs backward through the call stack to find the original trigger. Use when an error appears deep in execution, when the stack trace is long, when invalid data manifests far from its source, when you need to find which test/code-path/agent triggered a problem in a Brain service.
---

# Root Cause Tracing

Bugs often manifest deep in the call stack — Kafka consumer offset commit failure traced to a tRPC handler that didn't await; ClickHouse insert failure traced to a Pydantic model with a stray None; AI call placed outside calling hours traced to a Decision Log replay that bypassed the compliance engine. Your instinct is to fix where the error appears. That's symptom-treatment.

**Core principle:** Trace backward through the call chain until you find the original trigger. Then fix at the source.

## When to use

- Error happens deep in execution, not at the entry point
- Stack trace shows a long chain across multiple services
- Unclear where invalid data originated (which agent? which connector? which migration?)
- Need to find which test polluted shared state in a CI run
- Brain-specific: cross-service issues where OpenSearch shows the failure 4 hops downstream of the cause

## The tracing process

### 1. Observe the symptom

```
Error: ClickHouse insert failed:
  Code: 50. DB::Exception: Mandatory column 'workspace_id' has no value
  Block: insert into events_raw FORMAT JSONEachRow
```

### 2. Find the immediate cause

What code directly causes this? Open the ClickHouse client call in the ingestion-service.

```python
await ch.insert("events_raw", rows)
```

### 3. Ask: what called this? What's `rows`?

```python
rows = [event.dict() for event in batch.events]
# batch comes from ShopifyConnector.poll()
```

### 4. Keep tracing upward

```
ShopifyConnector.poll()
  → fetches /admin/api/2025-01/orders.json
  → maps to ShopifyOrderEvent
  → produces to Kafka topic shopify.orders.v1
  → ingestion-service consumer batches
  → BatchProcessor.process(batch)
  → ch.insert("events_raw", rows)
```

What value was passed at each hop?
- `batch.events` — list of `ShopifyOrderEvent`
- `ShopifyOrderEvent.workspace_id` — **None** for one row

### 5. Find the original trigger

Where did `workspace_id=None` come from?

```python
# In ShopifyConnector.poll()
async def poll(self):
    config = await self.config_repo.get(self.connector_id)
    # config.workspace_id is None when connector was created by a migration script
    # that ran before workspace_id became a mandatory field
    for raw in shopify_orders:
        yield ShopifyOrderEvent(workspace_id=config.workspace_id, ...)
```

**Root cause:** an old migration left some `integrations` rows with `workspace_id=NULL`. Every poll for those connectors emits broken events.

**Fix at source, not at symptom:**

- Wrong: filter out the bad rows in the ClickHouse insert
- Right:
  1. Backfill the missing `workspace_id` in `integrations`
  2. Add a NOT NULL constraint to prevent recurrence
  3. Add defense-in-depth (`defense-in-depth-validation`): ShopifyConnector raises on missing workspace_id, never produces an event

## Adding stack traces when manual tracing fails

When the call chain crosses async boundaries (Kafka, gRPC, BullMQ jobs), the stack is lost. Add explicit instrumentation:

```python
# Before the problematic operation
async def insert_events(rows):
    if any(r.workspace_id is None for r in rows):
        import traceback
        logger.error(
            "DEBUG events with null workspace_id",
            extra={
                "row_count": len(rows),
                "null_count": sum(1 for r in rows if r.workspace_id is None),
                "first_null_event_id": next((r.event_id for r in rows if r.workspace_id is None), None),
                "stack": traceback.format_stack(),
                "request_id": correlation_id.get(),
            },
        )
    await ch.insert("events_raw", rows)
```

Use `logger.error()` not `print()` so it lands in OpenSearch with the request_id correlation. Searchable later.

```bash
# Find every instance in OpenSearch
GET /brain-logs-*/_search
{
  "query": { "match": { "message": "events with null workspace_id" } },
  "sort": [{ "@timestamp": "desc" }]
}
```

## Cross-service tracing in Brain (TECH/09)

Brain runs **a single correlation ID** across web BFF → api-gateway → gRPC → service → Kafka → consumer. Use it.

```bash
# Find every log line for one user request
GET /brain-logs-*/_search
{
  "query": { "match": { "request_id": "req_abc123" } },
  "sort": [{ "@timestamp": "asc" }]
}
```

This shows the complete call chain across all 7 services. If the failure is in `analytics-service` at hop 5, the request_id ties it back to the originating tRPC call in api-gateway at hop 1 and the click in the web dashboard at hop 0.

For traces, use AWS X-Ray:
```bash
aws xray get-trace-summaries --start-time $(date -u -d '-1 hour' +%s) --end-time $(date +%s)
```

## Finding which test polluted shared state

If something appears during the CI test suite but you don't know which test:

```bash
# Bisect with vitest
pnpm test --bail        # stop at first failure
pnpm test --shard 1/4   # narrow down by shard

# Or run tests one at a time to find polluter
for f in $(find . -name '*.test.ts' | sort); do
  echo "=== $f ===" && pnpm vitest run "$f" || break
done
```

For Cypress/Detox flake hunting, run the suspect tests in isolation 20 times each:
```bash
for i in {1..20}; do pnpm test:e2e --spec cypress/e2e/morning-brief.cy.ts || echo "Failed at run $i"; done
```

## Real Brain example — the JWT entropy bug (slice-3)

**Symptom:** integration tests intermittently failed JWT verification with "bad signature" errors.

**Trace chain:**
1. Test calls `/api/orders` with a JWT signed by the test's local secret
2. api-gateway's JWT verify hook tries to validate
3. The hook reads `JWT_SECRET` env var — got a 12-character string
4. `jose` library used HMAC-SHA256, which works fine with short secrets...
5. ...except some tests parallelized and one set `JWT_SECRET` mid-flight after another had cached the wrong value

**Root cause:** `JWT_SECRET` was both shorter than 32 chars (Shreya's HIGH finding) AND being mutated in a test setup that broke parallel test isolation.

**Fix at source:**
- Layer 1: fail-fast on missing JWT_SECRET (was in ADR-006)
- Layer 2: **fail-fast on JWT_SECRET < 32 bytes** (Shreya's add) — entropy floor
- Layer 3: tests use a fresh per-test secret + a hermetic JWT verifier instance
- Layer 4: Decision Log row on `session.invalidate_all` so cross-test pollution shows up

Stop at "I'll bump the secret length" and the parallel-test pollution bug survives. Trace to the source, then defense-in-depth.

## Key principle

**NEVER fix just where the error appears.** Trace back to find the original trigger. Then `defense-in-depth-validation` ensures the same class of bug can't recur.

## Stack trace tips

- **In tests:** use `console.error()` or `logger.error()` — `print()` may be swallowed by the test runner
- **Before the operation:** log before the dangerous call, not after it fails (after-fail loses the inputs)
- **Include context:** correlation_id, workspace_id, user, environment, key inputs
- **Capture the stack:** `new Error().stack` (Node) or `traceback.format_stack()` (Python) shows the complete call chain
- **Across services:** rely on the correlation ID, X-Ray traces, OpenSearch — not just local stacks

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Single correlation ID across all surfaces | **Vikram** + **Jatin** | TECH/09 §"Correlation" |
| Cross-service trace (X-Ray) | **Jatin** | TECH/09 |
| Service-internal tracing | each builder | service-specific skill |
| Postmortem trace template | **Aarav** | `blueprints/postmortem.md` |

Related Brain skills: `systematic-debugging` (the 4-phase wrapper), `defense-in-depth-validation` (what to do at the source once you find it), `observability` (where the logs/traces live).
