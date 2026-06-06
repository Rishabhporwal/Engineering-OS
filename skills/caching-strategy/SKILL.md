---
name: caching-strategy
description: A Redis cache layer — cache-aside, TTL discipline, tenant-scoped keys, invalidate-on-write, stampede protection. A perf AND cost lever (cached = a model/OLAP call not paid).
---

# Caching Strategy — Redis

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the cache seam to a different technology. The *patterns* here (tenant-scoped keys, cache-aside, mandatory TTL, invalidate-on-write, stampede protection) are what transfer, not the Redis vendor.

This binding runs **one Redis cluster** (see `STACK.md` §cache). Caching is both a **performance** and a **cost** lever: a cached daily-metric is an OLAP query you didn't run; a cached agent answer is a large-model call you didn't pay for (`cost-routing-paradigms`).

## What lives in Redis
| Use | Key shape | TTL | Notes |
|---|---|---|---|
| Idempotency keys | `idem:{tenant_id}:{key}` | 24h | `idempotency-handling` |
| Rate-limit counters | `rl:{tenant_id}:{route}` | window | `api-discipline` |
| Session / auth cache | `sess:{tenant_id}:{user_id}` | token TTL | `auth-and-access` |
| Hot metric/query results | `metric:{tenant_id}:{metric}:{date}` | 5–60 min | the big read-cost saver |
| Agent/model answer cache | `ai:{tenant_id}:{hash(prompt)}` | feature-dependent | pairs with `claude-api` prompt caching |

## Non-negotiable rules
1. **Every key is tenant-prefixed.** No exceptions — a cross-tenant cache hit is a data leak (`multi-tenancy-isolation`).
2. **Cache-aside is the default:** read cache → miss → load from source → write cache with TTL. Never write-through without a reason.
3. **TTL is mandatory.** No unbounded keys. Shortest TTL that meets the freshness need.
4. **Invalidate on write.** A mutation deletes (not updates) dependent keys — delete-on-write + lazy-repopulate avoids partial-write skew.
5. **Stampede protection** on hot keys: short lock or `SET NX` "refresh in progress" sentinel so 1000 concurrent misses don't all hit the source. For very hot keys, serve-stale-while-revalidate.
6. **Never cache PII unencrypted; never cache secrets** (`compliance-engine`).

## Anti-patterns
Caching without a tenant prefix (cross-tenant leak — CRITICAL) · no TTL (bloat + permanent staleness) · caching a model answer that depends on live data without an invalidation trigger · using Redis as a database (it's a cache; source of truth is the OLTP/OLAP store).

## Verify
`redis-cli --scan --pattern 'idem:*' | head` to confirm key shapes; `TTL <key>` never `-1` for cache entries. A write to the source row must be observably followed by a cache delete (assert in an integration test).
