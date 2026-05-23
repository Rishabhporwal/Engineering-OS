---
name: api-traffic-patterns
description: Brain's list + traffic discipline for every API surface (tRPC, gRPC, MCP) — cursor (keyset) pagination (OFFSET is banned in prod paths) AND rate limiting (token bucket / sliding window, ElastiCache-backed distributed state, per-tier quotas, per-vendor outbound throttling). Use when adding a list endpoint (orders, customers, decision_log, audiences), shipping infinite-scroll UI, an OFFSET endpoint slows down, implementing per-brand quotas, protecting api-gateway from abuse, enforcing tier limits (Launch 1.0% / Growth 0.75% / Scale 0.5% / Enterprise of realized GMV), or preventing connector spikes from blowing vendor quotas.
---

# API Traffic Patterns

Two disciplines that govern how Brain's API surfaces handle volume: **how lists are paged** (cursor pagination — Part 1) and **how request rate is bounded** (rate limiting — Part 2). Both apply across tRPC, gRPC, and MCP tools.

---

# Part 1 — Cursor pagination

Brain ships **cursor (keyset) pagination** for every list endpoint. OFFSET is banned in production paths — it scans the rows it discards, so page 50 of a tenant's audit log is 50× slower than page 1.

## Strategies — pick by use case

| Strategy | Brain use | Performance | When |
|---|---|---|---|
| **Cursor (keyset)** | Default for every list endpoint | O(1) per page | Orders, audit log, decision log, customers, audiences, integration data |
| **OFFSET / LIMIT** | Admin tooling only | O(n) | Internal admin pages with bounded data; never tenant-facing |
| **Sliding window over time** | Time-series views | O(1) per window | Cohort heatmap, daily metrics; windowed reads, not really pagination |

## The Brain pattern (tRPC + cursor)

```typescript
const listInput = z.object({
  cursor: z.string().datetime().nullish(),  // ISO timestamp from previous page's last item
  limit:  z.number().min(1).max(200).default(50),
});

export const ordersRouter = router({
  list: protectedProcedure.input(listInput).query(async ({ ctx, input }) => {
    const rows = await ctx.db.query(
      `SELECT id, gross_revenue, currency, created_at FROM orders
       WHERE workspace_id = current_setting('app.workspace_id')::uuid
         AND ($1::timestamptz IS NULL OR created_at < $1)
       ORDER BY created_at DESC, id DESC LIMIT $2`,
      [input.cursor ?? null, input.limit + 1],   // fetch +1 to detect hasMore
    );
    const hasMore = rows.length > input.limit;
    const data    = hasMore ? rows.slice(0, input.limit) : rows;
    return { data, nextCursor: hasMore ? data.at(-1)!.created_at.toISOString() : null };
  }),
});
```

The cursor is the **last item's sort key**. For ties (multiple rows with the same `created_at`), use a compound cursor of `(created_at, id)`.

## Composite cursor (when timestamps tie)

```typescript
const encodeCursor = (r: { created_at: Date; id: string }) =>
  Buffer.from(JSON.stringify({ t: r.created_at.toISOString(), i: r.id })).toString('base64url');
const decodeCursor = (c: string) =>
  JSON.parse(Buffer.from(c, 'base64url').toString()) as { t: string; i: string };

// SQL keyset condition handles ties:
//   AND ($1::timestamptz IS NULL OR (created_at, id) < ($1, $2))
//   ORDER BY created_at DESC, id DESC LIMIT $3
```

Use this for high-write tables where rows can share a `created_at` (decision_log, raw events).

## ClickHouse pagination (Maya)

Cursors are cheap when the `ORDER BY` matches the primary key:

```sql
SELECT event_id, event_ts, payload FROM events
WHERE workspace_id = 'xxxx-...'
  AND (event_ts, event_id) < ({cursor_ts: DateTime64}, {cursor_id: String})
ORDER BY event_ts DESC, event_id DESC LIMIT 50;
```

For drill-downs over 5k rows ClickHouse reads multiple parts — prefer **server-side aggregation** before paginating; never pull raw points to the client.

## MCP + canonical response shape

MCP tools that return lists carry the cursor in the response envelope; external clients (Claude native, partners) honor `nextCursor` exactly like internal callers.

```json
{ "data": [ {...}, {...} ], "nextCursor": "2026-05-15T12:34:56.789Z", "hasMore": true }
```

For the BFF, TanStack Query's `useInfiniteQuery` consumes `nextCursor` directly:

```tsx
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['orders', filters],
  queryFn: ({ pageParam }) => trpc.orders.list.query({ cursor: pageParam, ...filters }),
  getNextPageParam: (last) => last.nextCursor, initialPageParam: null,
});
```

## Pagination best practices + anti-patterns

- **Cursor always**, OFFSET never (prod tenant-facing). **Max limit 200, default 50** — never "unlimited."
- **Sort column must be indexed**, with `workspace_id` first. Use a compound `(timestamp, id)` cursor where ties are possible.
- **Don't return total count** unless the UI needs it — `COUNT(*)` over a multi-million-row table is full-scan.
- **UI: "load more" / infinite scroll, not "page X of Y"** — cursors have no stable page numbers.

| Anti-pattern | Why it fails in Brain |
|---|---|
| `OFFSET 5000 LIMIT 50` on decision_log | Scans 5050 rows for a page-100 read; times out at scale |
| `SELECT COUNT(*)` for "show 2,341,892 results" | Full-scan over a multi-million-row table |
| Page numbers in URLs (`?page=5`) | Cursors aren't stable page numbers; bookmarked URLs break when data shifts |
| Ordering by `id` only | Doesn't match the chronological mental model; use `created_at` |
| `limit=10000` "because the customer asked" | One bad request blows the BFF budget for everyone in the cluster |

---

# Part 2 — Rate limiting

Protect api-gateway and downstream services from abuse, throttle per-brand by pricing tier, and prevent connector spikes from blowing through vendor quotas.

## Why this matters for Brain

| Surface | Concern |
|---|---|
| `api-gateway` external tRPC + MCP (Vikram) | Per-brand quotas align with GMV % tiers; an abusive workspace can't degrade other tenants |
| `ingestion-service` outbound (Maya) | Meta ~200 calls/hr/app-user; Shopify 2 req/s per shop — stay under or get banned |
| `lifecycle-service` AI calling (Maya) | Vapi/Bolna concurrency caps; per-brand call-queue depth |
| `intelligence-service` Claude (Maya) | Anthropic limits + the per-brand monthly LLM cap (see `memory/business-context.md`) |

## Algorithm choice

| Algorithm | When |
|---|---|
| **Token bucket** | api-gateway per-brand limiting — allows bursts within capacity (dashboard refreshes) |
| **Sliding window log** | High-precision endpoints (Decision Log writes, AI call dispatch) where exact count matters for compliance |
| **Fixed window** | Cheap per-IP defense at CloudFront; not for per-brand quotas |

## Token bucket (in-process — single-replica only)

```typescript
class TokenBucket {
  private tokens: number; private lastRefill = Date.now();
  constructor(private capacity: number, private refillRate: number) { this.tokens = capacity; }
  consume(): boolean { this.refill(); if (this.tokens >= 1) { this.tokens -= 1; return true; } return false; }
  private refill() {
    const now = Date.now();
    this.tokens = Math.min(this.capacity, this.tokens + ((now - this.lastRefill) / 1000) * this.refillRate);
    this.lastRefill = now;
  }
}
```

Fine for a quick spike-killer but **does not work across EKS replicas** — always use distributed (ElastiCache) state for per-brand quotas.

## Distributed (ElastiCache Redis) — Fastify plugin

```typescript
const redis = new Redis.Cluster([{ host: process.env.ELASTICACHE_HOST!, port: 6379 }]);
const SLIDING_WINDOW_LUA = `local c = redis.call('INCR', KEYS[1])
  if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
  return c`;

const TIER_LIMITS: Record<string, { max: number; windowSec: number }> = {
  launch: { max: 60, windowSec: 60 }, growth: { max: 120, windowSec: 60 },
  scale:  { max: 600, windowSec: 60 }, enterprise: { max: 6000, windowSec: 60 },
};

export const rateLimitPlugin: FastifyPluginAsync = async (app) => {
  app.addHook('preHandler', async (req, reply) => {
    const limit = TIER_LIMITS[req.workspace?.tier ?? 'launch'];
    const key = `rl:${req.workspaceId}:${Math.floor(Date.now() / 1000 / limit.windowSec)}`;
    const count = (await redis.eval(SLIDING_WINDOW_LUA, 1, key, limit.windowSec)) as number;
    reply.header('X-RateLimit-Limit', limit.max)
         .header('X-RateLimit-Remaining', Math.max(0, limit.max - count))
         .header('X-RateLimit-Reset', Math.ceil(Date.now() / 1000 / limit.windowSec) * limit.windowSec);
    if (count > limit.max) { reply.header('Retry-After', limit.windowSec).code(429).send({ error: 'RATE_LIMITED' }); }
  });
};
```

## Per-vendor (outbound) limiting

Ingestion-service throttles **outbound** calls. ElastiCache is the global semaphore — replicas pulling from the same vendor account share the budget:

```python
async def with_shopify_budget(shop_domain: str, fn):
    key = f"shopify:budget:{shop_domain}"
    count = await redis.incr(key)
    if count == 1: await redis.expire(key, 1)   # 1-second window
    if count > 2:                               # Shopify: 2 rps per shop
        await asyncio.sleep(1.0 - (time.time() % 1.0))
        return await with_shopify_budget(shop_domain, fn)
    return await fn()
```

## Headers + tier mapping

```
X-RateLimit-Limit: 120   X-RateLimit-Remaining: 45   X-RateLimit-Reset: 1705320000   Retry-After: 60 (429 only)
```

These are tRPC AND MCP transport headers — MCP clients respect `Retry-After` like external HTTP clients.

| Tier | GMV fee | Request budget per brand | Notes |
|---|---|---|---|
| Launch | ~1.0% of realized GMV | 60 rpm | Default entry tier |
| Growth | ~0.75% of realized GMV | 120 rpm | Scaling DTC |
| Scale | ~0.5% of realized GMV | 600 rpm | High-volume DTC |
| Enterprise | Custom | 6,000 rpm or custom | Per-contract |

## Rate-limiting best practices

- **Always emit `X-RateLimit-*` headers** so clients back off intelligently.
- **429 with `Retry-After`** — never 503/500. 429 = "you, slow down"; 503 = "we're down."
- **Distributed state via ElastiCache** — in-process buckets break under EKS auto-scaling.
- **Don't rate-limit `/health/*`** — exclude it or the readiness probe trips.
- Per-brand AND per-IP (defense in depth) — CloudFront does the IP layer, api-gateway the brand layer.
- **Cost-cap-aware AI throttling** (Maya): if a brand has consumed > 80% of monthly LLM budget, throttle Sonnet and route to Haiku (see `cost-routing-paradigms`).

---

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| tRPC list endpoints + cursor | **Vikram** | canon/technical-requirements.md (list endpoints) |
| MCP tool list responses | **Vikram** + **Maya** | canon/technical-requirements.md |
| ClickHouse drill-down pagination | **Maya** | `clickhouse-olap` |
| `useInfiniteQuery` / mobile infinite scroll | **Ananya** / **Karan** | canon/technical-requirements.md |
| Inbound api-gateway per-brand quotas | **Vikram** | canon/technical-requirements.md (rate limit) |
| Outbound connector + AI vendor throttling | **Maya** | canon/technical-requirements.md (vendor quotas) |
| Claude API budget enforcement | **Maya** | `cost-routing-paradigms` |

Related Brain skills: `sql-query-optimization` (cursor needs the right index), `database-design` (schema + indexes), `mcp-protocol` (tool response envelopes + transport headers), `cost-routing-paradigms` (budget-aware throttling), `observability` (`429` rate as an SLO), `integration-connectors` (per-vendor limits), `auth-and-access` (refresh-storm protection uses the same limiter).
