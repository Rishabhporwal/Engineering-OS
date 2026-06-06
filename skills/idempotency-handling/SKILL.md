---
name: idempotency-handling
description: Idempotent operations — idempotency keys, cache + database-backed dedup, key TTL. For webhook handlers, write tools, every mutating endpoint. No duplicate orders/calls/rows.
---

# Idempotency Handling

> **Reference implementation.** This skill documents one concrete binding of a seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (not the vendor) are what transfer.

Operations must produce identical results regardless of execution count. **Idempotency is not optional** — every external webhook can retry, every write tool can re-invoke, every RPC can retry. The system must converge to the same state.

## Why mandatory
| Surface | Why |
|---|---|
| Ingestion connectors | External webhooks **retry on any non-2xx**. The same source event twice → values double-counted → metrics wrong → the Stakeholder distrusts the numbers. |
| Write tools (e.g. an MCP/RPC mutation) | Every write writes a system-of-record audit entry. A retried tool call must NOT produce two rows. |
| Outbound side-effects (notifications, calls, external actions) | An action taken twice = a compliance violation (frequency cap) + a complaint. Dedupe by a stable logical key before queuing. |
| Notification fan-out | A push sent twice into a defining surface's window destroys the experience. |

## Idempotency key pattern (HTTP middleware + cache)
```typescript
export const idempotencyPlugin: FastifyPluginAsync = async (app) => {
  app.addHook('preHandler', async (req, reply) => {
    const key = req.headers['idempotency-key'] as string | undefined;
    if (!key) return;
    const cached = await redis.get(`idempotency:${key}`);
    if (cached) {
      const { status, body } = JSON.parse(cached);
      // MUST return — without it a cached hit falls through and the handler double-executes
      return reply.status(status).send(body);
    }
  });
  app.addHook('onSend', async (req, reply, payload) => {
    const key = req.headers['idempotency-key'] as string | undefined;
    if (!key) return payload;
    if (reply.statusCode >= 500) return payload;  // never cache 5xx — let client retry
    await redis.setex(`idempotency:${key}`, 86400, JSON.stringify({ status: reply.statusCode, body: payload }));
    return payload;
  });
};
```

## Database-backed
For mutations where losing the key on cache eviction is catastrophic (payments, outbound actions, financial write-backs):
```sql
CREATE TABLE idempotency_keys (
  tenant_id UUID NOT NULL, key TEXT NOT NULL,
  request_hash VARCHAR(64) NOT NULL, response JSONB,
  status VARCHAR(20) DEFAULT 'processing',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
  PRIMARY KEY (tenant_id, key)        -- tenant_id first: two tenants may reuse the same client key
);
CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_idem ON idempotency_keys USING (tenant_id = current_setting('app.tenant_id')::uuid);
```
```typescript
async function processOnce<T>(key: string, payload: unknown, exec: () => Promise<T>): Promise<T> {
  const requestHash = crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
  // Race-free claim: only one request inserts; others NO-OP and read.
  const claimed = await db.query(
    `INSERT INTO idempotency_keys (tenant_id, key, request_hash, status)
       VALUES (current_setting('app.tenant_id')::uuid, $1, $2, 'processing')
       ON CONFLICT (tenant_id, key) DO NOTHING RETURNING 1`, [key, requestHash]);
  if (claimed.rowCount === 1) {
    try { const result = await exec();
      await db.query(`UPDATE idempotency_keys SET status='completed', response=$1 WHERE key=$2`, [JSON.stringify(result), key]);
      return result;
    } catch (err) {
      await db.query(`UPDATE idempotency_keys SET status='failed', response=$1 WHERE key=$2`, [JSON.stringify({ error: (err as Error).message }), key]);
      throw err;
    }
  }
  const row = (await db.query(`SELECT * FROM idempotency_keys WHERE key=$1`, [key])).rows[0];
  if (row.request_hash !== requestHash) throw new Error('IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_BODY'); // 422 client bug
  if (row.status === 'completed') return JSON.parse(row.response);
  if (row.status === 'processing') throw new Error('REQUEST_IN_FLIGHT_RETRY_LATER');                   // 409
  if (row.status === 'failed') throw new Error(`PREVIOUS_ATTEMPT_FAILED: ${row.response.error}`);
  throw new Error(`UNKNOWN_STATUS: ${row.status}`);
}
```

## Connector-side — key derived from the source event, not the client
```python
def make_key(event: SourceOrderEvent) -> str:
    return f"{event.source}:order:{event.source_domain}:{event.id}:{event.updated_at}"  # stable per logical state
```
Polled pulls (e.g. ad-spend by day): key `(account_id, date, campaign_id)` — re-pulling the same day must converge, never increment. Columnar inserts: a `ReplacingMergeTree`-style engine keyed `(tenant_id, event_id)` collapses dupes at merge — but query via the engine's dedup view (raw reads see both during the merge window).

## When NOT to require a key
Read-only `GET` · long-poll/streaming · pure projections (no side effects). Everything that writes (`orders.import`, `spend.adjust`, `outreach.trigger`, `consent.update`, `call.place`, `audit.record`, `notification.send`) **MUST** accept a key (client-supplied or derived).

## TTL cleanup
```sql
DELETE FROM idempotency_keys WHERE expires_at < NOW() LIMIT 1000;  -- scheduled, hourly, batched
```
Alert if row count > 10M (something is writing without key rotation).

## Best practices
Always validate `request_hash` (same key + different body = client bug, reject 422) · never cache 5xx (cache only 2xx/4xx terminal states) · TTL 24h most ops, 7d for financial, 5min for high-volume webhook dedup if source-event uniqueness is solid · `tenant_id` first in PK · monitor hit rate (high = client retrying excessively).

## Wiring
Ingestion connectors, write tools, outbound actions, notification fan-out, and columnar-insert dedup each carry an idempotency key — assigned to the owning builder per the Canon.

Related: `event-driven-kafka` (producer dedup keys), `integration-connectors` (per-source retry), `security-baseline` (idempotency keys are not auth — never derive from session tokens), `data-layer` (key TTL via a scheduler), `mcp-protocol`.
