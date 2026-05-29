---
name: caching-strategy
description: Brain's ElastiCache (Redis) layer — cache-aside, TTL discipline, workspace_id-scoped keys, invalidate-on-write, stampede protection. A perf AND cost lever (cached = LLM/CH call not paid).
---

# Caching Strategy — ElastiCache (Redis)

Brain runs **one ElastiCache (Redis) cluster** (canon §12.2). Caching is both a **performance** and a **cost** lever: a cached daily-metric is a ClickHouse query you didn't run; a cached agent answer is a Sonnet call you didn't pay for (`cost-routing-paradigms`).

## What lives in Redis
| Use | Key shape | TTL | Notes |
|---|---|---|---|
| Idempotency keys | `idem:{workspace_id}:{key}` | 24h | `idempotency-handling` |
| Rate-limit counters | `rl:{workspace_id}:{route}` | window | `api-discipline` |
| Session / auth cache | `sess:{workspace_id}:{user_id}` | token TTL | `auth-and-access` |
| Hot metric/query results | `metric:{workspace_id}:{metric}:{date}` | 5–60 min | the big read-cost saver |
| Agent/LLM answer cache | `ai:{workspace_id}:{hash(prompt)}` | feature-dependent | pairs with claude-api prompt caching |

## Non-negotiable rules
1. **Every key is `workspace_id`-prefixed.** No exceptions — a cross-tenant cache hit is a data leak (`multi-tenancy-isolation`).
2. **Cache-aside is the default:** read cache → miss → load from source → write cache with TTL. Never write-through without a reason.
3. **TTL is mandatory.** No unbounded keys. Shortest TTL that meets the freshness need.
4. **Invalidate on write.** A mutation deletes (not updates) dependent keys — delete-on-write + lazy-repopulate avoids partial-write skew.
5. **Stampede protection** on hot keys: short lock or `SET NX` "refresh in progress" sentinel so 1000 concurrent misses don't all hit ClickHouse. For very hot keys, serve-stale-while-revalidate.
6. **Never cache PII unencrypted; never cache secrets** (`data-privacy-dpdp`).

## Anti-patterns
Caching without a `workspace_id` prefix (cross-tenant leak — CRITICAL) · no TTL (bloat + permanent staleness) · caching an LLM answer that depends on live data without an invalidation trigger · using Redis as a database (it's a cache; source of truth is Postgres/ClickHouse).

## Verify
`redis-cli --scan --pattern 'idem:*' | head` to confirm key shapes; `TTL <key>` never `-1` for cache entries. A write to the source row must be observably followed by a cache delete (assert in an integration test).
