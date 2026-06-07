---
name: python-services
description: Reference Python services stack — FastAPI + grpcio + asyncpg + an OLAP driver + an async Kafka client + sklearn/statsmodels + an LLM SDK + uv + pytest. Three safety patterns + the effort-tier gate.
---

# Python Services — Reference Implementation

> **Reference implementation.** This skill documents one concrete binding of a seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (not the vendor) are what transfer.

Python is a common choice for analytics, intelligence, and async-orchestration services (AI/ML Engineer territory); a typed runtime like TypeScript often handles I/O-heavy + edge work (Backend Engineer). A useful boundary to enforce: **typed-runtime services don't do heavy math; Python services don't serve user-facing latency-critical paths.**

## Stack invariants

| Layer | Choice | Why |
|---|---|---|
| Runtime | **Python 3.13** | New typing + better asyncio |
| Framework | **FastAPI** | Async-first; auto-docs |
| gRPC | `grpcio` + `grpcio-tools` | Generated from `protos/` via `buf generate` |
| Postgres | **`asyncpg`** via a shared `db` lib | Fastest async client |
| OLAP store | a driver (e.g. `clickhouse-driver`) via a shared gateway lib | Rejects queries missing the tenant-isolation key |
| Kafka | **`aiokafka`** + Avro via a schema-registry client | Native asyncio |
| HTTP client | **`httpx`** + `tenacity` | Async; mature |
| Pkg mgmt | **`uv`** workspace (single root lockfile; `uv sync`) | Fast resolver |
| Logging | **`structlog`** JSON → log shipper → log store | Correlation IDs |
| Errors | **`sentry-sdk`** | Same org as the typed runtime |
| LLM | the provider's SDK | Prompt caching default-on |
| Vector | a `pgvector` (or equivalent) binding | Semantic-retrieval queries |
| ML | scikit-learn, statsmodels, lifelines, scipy, numpy, pandas | Statistical/forecasting work |
| Tests | **`pytest`** + pytest-asyncio + `respx` + OLAP-store Docker | |
| Lint / Types | `ruff` / `mypy --strict` | |

## Repo layout (per service)

```
apps/<service>/
├── pyproject.toml          # uv workspace member
├── Dockerfile
└── src/
    ├── main.py             # FastAPI + grpcio server bootstrap
    ├── config.py           # Pydantic settings (validate env at startup)
    ├── logger.py           # structlog + correlation IDs (contextvars)
    ├── tracing.py          # distributed tracing via OpenTelemetry
    ├── grpc/{server.py, handlers/<domain>.py}
    ├── http/routes.py      # FastAPI router (health + webhooks)
    ├── repositories/{postgres.py, clickhouse.py}
    ├── consumers/<topic>.py
    └── domain/             # business logic; NO I/O imports
tests/{unit, integration (docker-compose conftest), smoke (real server + curl)}
```

The `uv` workspace root declares `members = ["apps/*", "pylibs/*"]` with each shared lib (e.g. `db`, `olap`, `kafka`, `metrics`, `cost_router`) as `{ workspace = true }`. Full bootstrap scaffolds (`main.py` running gRPC + uvicorn with graceful SIGTERM, `logger.py`, `tracing.py`) belong in the Product Canon — copy them.

## The load-bearing safety patterns (NON-NEGOTIABLE — review block if skipped)

**1. asyncpg pool sets the tenant GUC so RLS engages:**
```python
async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        settings.DATABASE_URL, min_size=2, max_size=20,
        setup=set_tenant_context,   # SET app.tenant_id from the contextvar
    )
```
Forgetting `setup=set_tenant_context` means RLS never engages — a cross-tenant test that should FAIL passes.

**2. Every OLAP query goes through the gateway** (a columnar store typically has no native RLS):
```python
TENANT_PREDICATE = re.compile(r"tenant_id\s*=", re.IGNORECASE)
async def query(sql: str, params: dict):
    if not TENANT_PREDICATE.search(sql):
        raise RuntimeError("OLAP query missing tenant_id predicate")
    return await client.execute(sql, params)
```
Direct `client.execute(sql)` bypasses the safety net — never do it.

**3. Every LLM call caches the system prompt** (10–30x cost reduction at scale):
```python
await client.messages.create(
    model="<pinned-model-id>", max_tokens=2000,
    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": user_prompt}],
)
```

## Async + structured logging discipline

- **httpx + `tenacity`** for outbound: `wait_exponential_jitter`, honor `Retry-After` on 429, `timeout=10.0`. Never block the event loop with sync I/O.
- **aiokafka** consumers: `enable_auto_commit=False`, manual `consumer.commit(...)` only AFTER the OLAP/Postgres write succeeds (at-least-once + idempotent write).
- **structlog** emits JSON with `request_id`/`trace_id`/`tenant_id`/`user_id` from `contextvars` + service + version. PII redaction at the logger (filter `email`, `phone`, `access_token`, `refresh_token`, and any product-specific identifiers) with a log-shipper redaction pass as the second line (see `observability`).

## Cost-routing — the effort-tier decorator

Every LLM/ML function carries an effort-tier decorator (e.g. `@paradigm(kind, model=..., token_budget=...)`). It registers into a registry (CI parses it for the cost-routing audit) and, for `small_llm`/`frontier_llm` kinds, runs a per-tenant cap check before the call. Missing the decorator = the cost-discipline dashboard can't track it = CI FAIL. (Owner skill: `cost-routing-paradigms`.)

## Operational Readiness (pre-handoff)

- [ ] `GET /` returns identifiable JSON; `GET /health` returns 200 with `{status, version, deps: {postgres, olap, kafka, cache}}`
- [ ] `HTTP_PORT` + `GRPC_PORT` env vars; crash on `EADDRINUSE`
- [ ] Required env vars validated at startup (Pydantic) — `sys.exit(1)` if missing
- [ ] structlog correlation IDs via contextvars; PII redaction at logger + log shipper
- [ ] Sentry initialized; trace spans propagate
- [ ] Real-network smoke test (`pytest tests/smoke/` spawns server + curls)
- [ ] The effort-tier decorator on every LLM/ML function; every OLAP query via the gateway lib; every gRPC handler asserts the `tenant_id` match

(Full checklist: `operational-readiness`.)

## Common pitfalls

- **Blocking I/O in async path** — kills throughput. Always `await`.
- **Skipping the OLAP gateway lib** — bypasses the tenant_id safety net.
- **No `cache_control` on LLM calls** — 10–30x cost.
- **Missing the effort-tier decorator** — cost dashboard can't track; CI catches.
- **Forgetting `setup=set_tenant_context`** — RLS doesn't engage.
- **Bare `except:`** — swallows `KeyboardInterrupt`. Use `except Exception:` and log.
- **`asyncio.run` in nested contexts** — restructure rather than nesting event loops.

## References

- Product Canon (`STACK.md`, `INVARIANTS.md`) — service bootstrap scaffolds, log spine + trace + Sentry wiring, Postgres + OLAP usage
- Related: `grpc-buf`, `cost-routing-paradigms`, `clickhouse-olap`, `event-driven-kafka`, `operational-readiness`, `domain-driven-design`

## 2026 market update

- **Polars** (Rust dataframes) is the default over pandas for new dataframe work; **DuckDB** for in-process analytics (`embedded-analytics-duckdb` if bound). **DBOS-Python** offers in-process durable execution on Postgres (a `workflow-engine-temporal` alternative). FastAPI + uv remains the current stack.
