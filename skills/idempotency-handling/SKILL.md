---
name: idempotency-handling
description: Idempotent API operations with idempotency keys, Redis/ElastiCache caching, Postgres constraints. Use for webhook handlers (Shopify, Meta, Google, Shiprocket, Klaviyo), MCP write tools, every mutating endpoint in Brain. Avoids duplicate orders, double-charged calls, doubled Decision Log entries on retry.
---

# Idempotency Handling

Ensure operations produce identical results regardless of execution count. **In Brain, idempotency is not optional** — every external webhook can be retried by the vendor, every MCP write tool can be re-invoked by an agent, every gRPC call can be retried by the client. The system must converge to the same state.

## Why this matters for Brain

| Surface | Why idempotency is mandatory |
|---|---|
| `ingestion-service` (Maya) | Shopify/Meta/Google/Shiprocket webhooks **retry on any non-2xx**. Same order delivered twice → revenue counted twice → CM2 wrong → Founder loses trust in the entire MER number. |
| `api-gateway` MCP write tools (Vikram) | Every MCP write writes a Decision Log entry. An agent retrying its own tool call on transient failure must NOT produce two log rows. |
| `lifecycle-service` outbound (Maya) | An AI call placed twice = compliance violation (48h frequency cap) AND a customer complaint. The call dispatcher MUST dedupe by `(customer_id, campaign_id, scheduled_at)` before queuing. |
| `notifications-service` (Vikram) | A push notification sent twice into the 06:55–07:15 Morning Brief window destroys the product experience. |

## Idempotency Key Pattern (Fastify + ElastiCache)

```typescript
import { FastifyPluginAsync } from 'fastify';
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL!);

export const idempotencyPlugin: FastifyPluginAsync = async (app) => {
  app.addHook('preHandler', async (req, reply) => {
    const key = req.headers['idempotency-key'] as string | undefined;
    if (!key) return; // only enforce when client sent a key

    const cached = await redis.get(`idempotency:${key}`);
    if (cached) {
      const { status, body } = JSON.parse(cached);
      // MUST return the reply — without it, a cached hit falls through and the
      // handler double-executes (the exact double-write this skill exists to prevent).
      return reply.status(status).send(body);
    }
  });

  app.addHook('onSend', async (req, reply, payload) => {
    const key = req.headers['idempotency-key'] as string | undefined;
    if (!key) return payload;
    if (reply.statusCode >= 500) return payload; // never cache 5xx — let client retry

    await redis.setex(
      `idempotency:${key}`,
      86400, // 24 hours
      JSON.stringify({ status: reply.statusCode, body: payload }),
    );
    return payload;
  });
};
```

## Database-Backed Idempotency (Supabase Postgres)

For mutations where losing the key on Redis eviction would be catastrophic (payments, AI calls, ad-spend writebacks), back the key with Postgres:

```sql
-- per-workspace idempotency; RLS automatically scopes lookups
CREATE TABLE idempotency_keys (
  workspace_id   UUID        NOT NULL,
  key            TEXT        NOT NULL,
  request_hash   VARCHAR(64) NOT NULL,
  response       JSONB,
  status         VARCHAR(20) DEFAULT 'processing',
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  expires_at     TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
  PRIMARY KEY (workspace_id, key)
);

CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);

ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_idem ON idempotency_keys
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

```typescript
import crypto from 'crypto';

async function processOnce<T>(
  key: string,
  payload: unknown,
  exec: () => Promise<T>,
): Promise<T> {
  const requestHash = crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');

  // Race-free claim: only one request inserts; others NO-OP and read.
  const claimed = await db.query(
    `INSERT INTO idempotency_keys (workspace_id, key, request_hash, status)
       VALUES (current_setting('app.workspace_id')::uuid, $1, $2, 'processing')
       ON CONFLICT (workspace_id, key) DO NOTHING
       RETURNING 1`,
    [key, requestHash],
  );

  if (claimed.rowCount === 1) {
    try {
      const result = await exec();
      await db.query(
        `UPDATE idempotency_keys SET status='completed', response=$1 WHERE key=$2`,
        [JSON.stringify(result), key],
      );
      return result;
    } catch (err) {
      await db.query(
        `UPDATE idempotency_keys SET status='failed', response=$1 WHERE key=$2`,
        [JSON.stringify({ error: (err as Error).message }), key],
      );
      throw err;
    }
  }

  // Someone else is/was processing — check status
  const existing = await db.query(`SELECT * FROM idempotency_keys WHERE key=$1`, [key]);
  const row = existing.rows[0];

  if (row.request_hash !== requestHash) {
    // Same key, different body → client bug. Reject loudly.
    throw new Error('IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_BODY');
  }
  if (row.status === 'completed') return JSON.parse(row.response);
  if (row.status === 'processing') throw new Error('REQUEST_IN_FLIGHT_RETRY_LATER'); // 409
  if (row.status === 'failed') throw new Error(`PREVIOUS_ATTEMPT_FAILED: ${row.response.error}`);
  throw new Error(`UNKNOWN_STATUS: ${row.status}`);
}
```

## Connector-side idempotency (Maya's ingestion pattern)

For ingestion, the idempotency key is **derived from the source event**, not supplied by client:

```python
# ingestion-service: Shopify order webhook
def make_key(event: ShopifyOrderEvent) -> str:
    # Shopify guarantees order id + updated_at is stable per logical state.
    return f"shopify:order:{event.shop_domain}:{event.id}:{event.updated_at}"
```

For Meta/Google ad-spend pulls (polling, not webhook), the key is `(account_id, date, campaign_id)`. Re-pulling the same day must converge — never increment.

For ClickHouse inserts (Maya), idempotency is handled by `ReplacingMergeTree` keyed on `(workspace_id, event_id)`. Insert the same event twice and the merge collapses to one — but ONLY query through `FINAL` or a deduplicated materialized view, otherwise you'll see both during the merge window.

## When NOT to require an idempotency key

- Read-only endpoints (`GET`)
- Long-poll / streaming endpoints
- Pure projections (no side effects)

Everything else in Brain that writes (orders.import, ad_spend.adjust, audience.outreach.trigger, customer.consent.update, call.place, decision_log.record, notification.send) **MUST** accept an idempotency key, either from the client or derived from the input.

## TTL Cleanup (avoid table bloat)

```sql
-- pg_cron job, hourly, batched
DELETE FROM idempotency_keys
WHERE expires_at < NOW()
LIMIT 1000;
```

Brain runs this hourly via pg_cron in Supabase. Alert if row count > 10M (something is writing without `key` rotation).

## Best Practices

- **Always validate** `request_hash` — same key + different body is a client bug, reject with 422.
- **Never cache 5xx responses** — let the client retry. Cache only 2xx/4xx (terminal states).
- TTL: 24h for most operations; 7d for payments / financial mutations; 5min for high-volume webhook dedup if you're confident in source-event uniqueness.
- **`workspace_id` first in the primary key.** Two different brands can legitimately use the same client-supplied `idempotency-key`.
- Monitor idempotency hit rate as a signal: high hit rate = client retrying excessively (network issues, missing 2xx response handling).

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Ingestion connectors (Shopify/Meta/Google/Shiprocket/Klaviyo) | **Maya** | canon/technical-requirements.md (idempotent UPSERT) |
| MCP write tools | **Vikram** | canon/technical-requirements.md (Decision Log discipline) |
| Lifecycle outbound (calls, WhatsApp, SMS, email) | **Maya** | canon/technical-requirements.md (frequency cap + dedup) |
| Notifications fan-out | **Vikram** | canon/technical-requirements.md |
| ClickHouse insert dedup | **Maya** | canon/technical-requirements.md (ReplacingMergeTree) |

Related Brain skills: `event-driven-kafka` (Kafka producer dedup keys), `integration-connectors` (per-vendor retry semantics), `security-baseline` (idempotency keys are not auth — never derive them from session tokens).
