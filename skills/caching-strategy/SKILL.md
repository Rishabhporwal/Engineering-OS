---
name: caching-strategy
description: Brain's ElastiCache (Redis) caching layer (canon §12.2) — cache-aside, TTL discipline, workspace_id-scoped keys, invalidation on write, stampede protection, and what to cache (sessions, rate-limit counters, idempotency keys, hot metric/query results). Use when adding a cache, debugging a stale read, cutting repeat ClickHouse/LLM cost, or designing a read-heavy endpoint. Caching is also a COST lever — a cached metric is an LLM/CH call you didn't pay for.
---

# Caching Strategy — ElastiCache (Redis)

Brain runs **one ElastiCache (Redis) cluster** (canon/technical-requirements.md §12.2). Caching is both a **performance** and a **cost** lever: a cached daily-metric is a ClickHouse query you didn't run; a cached agent answer is a Sonnet call you didn't pay for (ties to [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)).

## What lives in Redis

| Use | Key shape | TTL | Notes |
|---|---|---|---|
| Idempotency keys | `idem:{workspace_id}:{key}` | 24h | See [`idempotency-handling`](../idempotency-handling/SKILL.md) |
| Rate-limit counters | `rl:{workspace_id}:{route}` | window | See [`api-traffic-patterns`](../api-traffic-patterns/SKILL.md) |
| Session / auth cache | `sess:{workspace_id}:{user_id}` | token TTL | See [`auth-and-access`](../auth-and-access/SKILL.md) |
| Hot metric/query results | `metric:{workspace_id}:{metric}:{date}` | 5–60 min | The big read-cost saver |
| Agent/LLM answer cache | `ai:{workspace_id}:{hash(prompt)}` | feature-dependent | Pairs with claude-api prompt caching |

## Non-negotiable rules

1. **Every key is `workspace_id`-prefixed.** No exceptions — a cross-tenant cache hit is a data leak ([`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)).
2. **Cache-aside is the default pattern:** read cache → miss → load from source → write cache with TTL. Never write-through without a reason.
3. **TTL is mandatory.** No unbounded keys. Pick the shortest TTL that meets the freshness need.
4. **Invalidate on write.** A mutation to the underlying row deletes (not updates) the dependent cache keys. Prefer delete-on-write + lazy-repopulate over update-in-place (avoids partial-write skew).
5. **Stampede protection** on hot keys: a short lock or `SET NX` "refresh in progress" sentinel so 1000 concurrent misses don't all hit ClickHouse. For very hot keys, serve-stale-while-revalidate.
6. **Never cache PII unencrypted** and never cache secrets ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)).

## Anti-patterns

- Caching without a `workspace_id` prefix → cross-tenant leak. **CRITICAL.**
- No TTL → memory bloat + permanent staleness.
- Caching an LLM answer that depends on live data without an invalidation trigger.
- Using Redis as a database (durability) — it's a cache; the source of truth is Postgres/ClickHouse.

## Verify

- `redis-cli --scan --pattern 'idem:*' | head` to confirm key shapes; `TTL <key>` is never `-1` (no expiry) for cache entries.
- A write to the source row must be observably followed by a cache delete (assert in an integration test).
