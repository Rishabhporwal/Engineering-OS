---
name: api-rate-limiting
description: API rate limiting with token bucket, sliding window, and ElastiCache-backed distributed algorithms. Use when implementing Brain's per-brand quotas, protecting api-gateway from abuse, enforcing tier-specific limits (founding 0.5%, standard 1.0%, growth, enterprise), preventing connector spikes from blowing through vendor quotas.
---

# API Rate Limiting

Protect Brain's api-gateway and downstream services from abuse, throttle per-brand by pricing tier, and prevent connector spikes from blowing through vendor (Shopify, Meta, Google) quotas.

## Why this matters for Brain

| Surface | Concern |
|---|---|
| `api-gateway` external tRPC + MCP (Vikram) | Per-brand quotas align with GMV % tiers; an abusive workspace can't degrade other tenants. |
| `ingestion-service` outbound (Sahil) | Meta Marketing API: ~200 calls/hr/app-user; Shopify: 2 req/s per shop. Brain MUST stay under or we get banned. |
| `lifecycle-service` AI calling vendor (Neel) | Vapi/Bolna concurrency caps; per-brand call queue depth. |
| `intelligence-service` Claude API (Maya) | Anthropic rate limits + the per-brand monthly LLM cap (₹3K founding / ₹5K standard / ₹15K growth / ₹50K+ enterprise — see `memory/business-context.md`). |

## Algorithm choice

| Algorithm | When to use in Brain |
|---|---|
| **Token bucket** | api-gateway per-brand limiting (allows bursts within capacity — what you want for dashboard refreshes) |
| **Sliding window log** | High-precision endpoints (Decision Log writes, AI call dispatch) where exact count matters for compliance |
| **Fixed window** | Cheap per-IP defense-in-depth at CloudFront; not for per-brand quotas |

## Token bucket (in-process — single-replica only)

```typescript
class TokenBucket {
  private tokens: number;
  private lastRefill: number;

  constructor(
    private readonly capacity: number,
    private readonly refillRate: number, // tokens per second
  ) {
    this.tokens = capacity;
    this.lastRefill = Date.now();
  }

  consume(): boolean {
    this.refill();
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return true;
    }
    return false;
  }

  private refill() {
    const now = Date.now();
    const elapsedSec = (now - this.lastRefill) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsedSec * this.refillRate);
    this.lastRefill = now;
  }
}
```

This is fine for a quick spike-killer but **does not work** across EKS replicas. Always use distributed (ElastiCache) state for per-brand quotas.

## Distributed (ElastiCache Redis) — Fastify plugin

```typescript
import { FastifyPluginAsync } from 'fastify';
import Redis from 'ioredis';

const redis = new Redis.Cluster([{ host: process.env.ELASTICACHE_HOST!, port: 6379 }]);

// Lua script: atomic GET + INCR + EXPIRE
const SLIDING_WINDOW_LUA = `
  local current = redis.call('INCR', KEYS[1])
  if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
  return current
`;

interface Limit { max: number; windowSec: number; }

const TIER_LIMITS: Record<string, Limit> = {
  founding:   { max: 60,   windowSec: 60 }, // 60 rpm
  standard:   { max: 120,  windowSec: 60 },
  growth:     { max: 600,  windowSec: 60 },
  enterprise: { max: 6000, windowSec: 60 },
};

export const rateLimitPlugin: FastifyPluginAsync = async (app) => {
  app.addHook('preHandler', async (req, reply) => {
    const workspaceId = req.workspaceId; // set by auth hook from JWT
    const tier = req.workspace?.tier ?? 'standard';
    const limit = TIER_LIMITS[tier];

    const key = `rl:${workspaceId}:${Math.floor(Date.now() / 1000 / limit.windowSec)}`;
    const count = (await redis.eval(SLIDING_WINDOW_LUA, 1, key, limit.windowSec)) as number;

    reply.header('X-RateLimit-Limit', limit.max);
    reply.header('X-RateLimit-Remaining', Math.max(0, limit.max - count));
    reply.header('X-RateLimit-Reset', Math.ceil(Date.now() / 1000 / limit.windowSec) * limit.windowSec);

    if (count > limit.max) {
      reply.header('Retry-After', limit.windowSec);
      reply.code(429).send({ error: 'RATE_LIMITED', tier });
    }
  });
};
```

## Per-vendor (outbound) limiting

Sahil's ingestion-service must throttle **outbound** calls to Shopify, Meta, Google. Use ElastiCache as the global semaphore — multiple replicas pulling from the same vendor account share the budget.

```python
# Python ingestion: per-Shopify-shop budget
async def with_shopify_budget(shop_domain: str, fn):
    key = f"shopify:budget:{shop_domain}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 1)  # 1-second window
    if count > 2:                   # Shopify: 2 rps per shop
        await asyncio.sleep(1.0 - (time.time() % 1.0))
        return await with_shopify_budget(shop_domain, fn)
    return await fn()
```

## Response headers (canonical)

```
X-RateLimit-Limit:     120
X-RateLimit-Remaining: 45
X-RateLimit-Reset:     1705320000
Retry-After:           60         (only on 429)
```

These are tRPC headers AND MCP transport headers — the MCP client surface should respect Retry-After exactly like external HTTP clients.

## Tier mapping (canonical, from `memory/business-context.md`)

| Tier | GMV fee | Request budget per brand | Notes |
|---|---|---|---|
| Founding | 0.5% | 60 rpm | Anchor + cohort #1 |
| Standard | 1.0% | 120 rpm | Default |
| Growth | 0.5% above ₹1Cr GMV | 600 rpm | High-volume DTC |
| Enterprise | Negotiated | 6,000 rpm or custom | Per-contract |

## Best Practices

- **Always emit `X-RateLimit-*` headers** — clients use them to back off intelligently.
- **429 with `Retry-After`** — never 503, never 500. 429 tells the client "you, slow down"; 503 tells them "we're down."
- **Distributed state via ElastiCache.** In-process buckets break under EKS auto-scaling.
- **Don't rate-limit health endpoints** — exclude `/health/*` from the plugin or the readiness probe will trip.
- Per-brand AND per-IP (defense in depth). CloudFront does the IP layer; api-gateway does the brand layer.
- **Cost-cap-aware throttling for AI** (Maya): if a brand has consumed > 80% of monthly LLM budget, throttle Sonnet calls and route to Haiku. See `cost-routing-paradigms`.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Inbound api-gateway per-brand quotas | **Vikram** | TECH/06 §"Rate limit" |
| Outbound connector throttling | **Sahil** | TECH/02 §"Vendor quotas" |
| AI calling vendor concurrency | **Neel** | TECH/11 §5 |
| Claude API budget enforcement | **Maya** | TECH/12 + `cost-routing-paradigms` |

Related Brain skills: `cost-routing-paradigms` (budget-aware throttling), `observability` (`429` rate as an SLO), `integration-connectors` (per-vendor specific limits).
