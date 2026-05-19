---
name: python-services
description: Brain's Python service stack — FastAPI + grpcio + asyncpg + clickhouse-driver + aiokafka + httpx + Prophet/sklearn/statsmodels + Anthropic SDK + structlog + Sentry + uv workspace + pytest. Auto-load whenever editing apps/ingestion-service, apps/analytics-service, apps/intelligence-service, or apps/lifecycle-service Python side. Covers project layout, dependency management with uv, structured logging with correlation IDs, async patterns, and operational-readiness checklist.
---

# Python Services — Brain's Stack

Python 3.12 is Brain's choice for ingestion, analytics, intelligence, and lifecycle Python orchestration (all owned by Maya). TypeScript handles I/O-heavy + edge work (api-gateway, core-service, notifications-service, lifecycle Node side, web, mobile — Vikram).

The boundary is enforced: **TS services don't do heavy math; Python services don't serve user-facing latency-critical paths.**

## Stack invariants

| Layer | Choice | Why |
|---|---|---|
| Runtime | **Python 3.12** | New typing + better asyncio |
| Framework | **FastAPI** | Async-first; great ergonomics; auto-docs |
| gRPC | `grpcio` + `grpcio-tools` | Generated from `protos/` via `buf generate` |
| Postgres | **`asyncpg`** via `pylibs/brain_db` | Fastest async Postgres client |
| ClickHouse | **`clickhouse-driver`** via `pylibs/brain_clickhouse` query gateway | Rejects un-workspace_id queries |
| Kafka | **`aiokafka`** + Avro via `python-schema-registry-client` | Native asyncio |
| HTTP client | **`httpx`** + `tenacity` retries | Async; mature |
| Pkg mgmt | **`uv`** workspace (single root lockfile; `uv sync`) | Fast resolver |
| Logging | **`structlog`** JSON → Fluent Bit → OpenSearch | Correlation IDs |
| Errors | **`sentry-sdk`** | Same org as Node |
| LLM | **`anthropic`** SDK | Prompt caching default-on |
| Vector | **`pgvector`** Python binding | Memory Layer queries |
| ML | scikit-learn, statsmodels, Prophet, lifelines, scipy, numpy, pandas | Per `forecasting-prophet` |
| Tests | **`pytest`** + pytest-asyncio + `respx` + ClickHouse Docker | |
| Lint / Types | `ruff` / `mypy --strict` | One tool each |

## Repo layout (per service)

```
apps/<service>/
├── pyproject.toml          # uv workspace member
├── Dockerfile
└── src/
    ├── main.py             # FastAPI + grpcio server bootstrap
    ├── config.py           # Pydantic settings (validate env at startup)
    ├── logger.py           # structlog + correlation IDs (contextvars)
    ├── tracing.py          # X-Ray via OpenTelemetry
    ├── grpc/{server.py, handlers/<domain>.py}
    ├── http/routes.py      # FastAPI router (health + webhooks)
    ├── repositories/{postgres.py, clickhouse.py}
    ├── consumers/<topic>.py  # Kafka consumers
    └── domain/             # business logic; NO I/O imports
tests/{unit, integration (docker-compose conftest), smoke (real server + curl)}
```

The `uv` workspace root declares `members = ["apps/*", "pylibs/*"]` with each shared lib (`brain_db`, `brain_clickhouse`, `brain_kafka`, `brain_metrics`, `brain_cost_router`, …) as `{ workspace = true }`. Full bootstrap (`main.py` running gRPC + uvicorn with graceful SIGTERM), `logger.py`, and `tracing.py` scaffolds are in canon/BRAIN_TECHNICAL.md — copy them rather than re-deriving.

## The load-bearing safety patterns (NON-NEGOTIABLE)

These three are why Brain's Python services are multi-tenant-safe and cost-disciplined. Skipping any one is a review block.

**1. asyncpg pool sets the tenant GUC so RLS engages:**
```python
async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        settings.DATABASE_URL, min_size=2, max_size=20,
        setup=set_tenant_context,   # SET app.workspace_id from the contextvar
    )
```
Forgetting `setup=set_tenant_context` means RLS never engages — a cross-workspace integration test that should FAIL will pass.

**2. Every ClickHouse query goes through the gateway** (CH has no native RLS):
```python
WORKSPACE_PREDICATE = re.compile(r"workspace_id\s*=", re.IGNORECASE)

async def query(sql: str, params: dict):
    if not WORKSPACE_PREDICATE.search(sql):
        raise RuntimeError("CH query missing workspace_id predicate")
    return await client.execute(sql, params)
```
Direct `client.execute(sql)` bypasses the safety net — never do it.

**3. Every Anthropic call caches the system prompt** (10–30x cost reduction at scale):
```python
await client.messages.create(
    model="claude-sonnet-4-6", max_tokens=2000,
    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": user_prompt}],
)
```

## Async + structured logging discipline

- **httpx + `tenacity`** for outbound: `wait_exponential_jitter` retry, honor `Retry-After` on 429, `timeout=10.0`. Never block the event loop with sync I/O.
- **aiokafka** consumers: `enable_auto_commit=False`, manual `consumer.commit(...)` only AFTER the ClickHouse/Postgres write succeeds (at-least-once + idempotent write).
- **structlog** emits JSON with `request_id`/`trace_id`/`workspace_id`/`user_id` from `contextvars`, plus service + version. PII redaction at the logger (filter `email`, `phone`, `access_token`, `refresh_token`, `pan_card`, `aadhaar`) with a Fluent Bit Lua script as the second line of defense (canon/BRAIN_TECHNICAL.md).

## Cost-routing — `@paradigm` decorator

Every LLM/ML function carries `@paradigm(kind, model=..., token_budget=...)`. It registers into `PARADIGM_REGISTRY` (CI parses it for the cost-routing audit — see canon/BRAIN_TECHNICAL.md) and, for `small_llm`/`frontier_llm` kinds, runs a per-brand cap check before the call. Missing `@paradigm` = the cost-discipline dashboard can't track it = CI FAIL.

## Operational Readiness (pre-handoff)

- [ ] `GET /` returns identifiable JSON; `GET /health` returns 200 with `{status, version, deps: {postgres, clickhouse, kafka, redis}}`
- [ ] `HTTP_PORT` + `GRPC_PORT` env vars; crash on `EADDRINUSE`
- [ ] Required env vars validated at startup (Pydantic) — `sys.exit(1)` if missing
- [ ] structlog correlation IDs propagate via contextvars; PII redaction at logger + Fluent Bit
- [ ] Sentry initialized; X-Ray spans propagate
- [ ] Real-network smoke test (`pytest tests/smoke/` spawns server + curls)
- [ ] Every `@paradigm` on LLM/ML functions; every CH query via `brain_clickhouse.query()`; every gRPC handler asserts `workspace_id` match

## Common pitfalls

- **Blocking I/O in async path** — kills throughput. Always `await`.
- **Skipping `brain_clickhouse.query()`** — direct `client.execute(sql)` bypasses the workspace_id safety net.
- **No `cache_control` on Anthropic calls** — 10–30x cost. Always cache the system prompt.
- **Missing `@paradigm`** — cost-discipline dashboard can't track. CI catches.
- **Forgetting `setup=set_tenant_context`** on the asyncpg pool — RLS doesn't engage.
- **Bare `except:`** — swallows `KeyboardInterrupt`. Use `except Exception:` and log.
- **`asyncio.run` in nested contexts** — crashes. Restructure rather than nesting event loops.

## References

- `canon/BRAIN_TECHNICAL.md` — service bootstrap scaffolds, log spine + X-Ray + Sentry wiring, Postgres + ClickHouse usage
- `skills/grpc-buf/SKILL.md` — server / client patterns
- `skills/cost-routing-paradigms/SKILL.md` — `@paradigm` decorator + token budgets
- `skills/clickhouse-olap/SKILL.md` — query gateway
- `skills/event-driven-kafka/SKILL.md` — MSK + Avro consumer patterns
- `skills/operational-readiness/SKILL.md` — pre-handoff checklist
