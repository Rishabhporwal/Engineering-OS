---
name: python-services
description: Brain's Python service stack — FastAPI + grpcio + asyncpg + clickhouse-driver + aiokafka + httpx + Prophet/sklearn/statsmodels + Anthropic SDK + structlog + Sentry + uv workspace + pytest. Auto-load whenever editing apps/ingestion-service, apps/analytics-service, apps/intelligence-service, or apps/lifecycle-service Python side. Covers project layout, dependency management with uv, structured logging with correlation IDs, async patterns, and operational-readiness checklist.
---

# Python Services — Brain's Stack

Python 3.12 is Brain's choice for ingestion, analytics, intelligence, and lifecycle Python orchestration. TypeScript is Brain's choice for I/O-heavy + edge work (api-gateway, core-service, notifications-service, lifecycle Node side, web, mobile).

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
| HTTP client | **`httpx`** | Async; mature retries via `tenacity` |
| Pkg mgmt | **`uv`** workspace | Fast resolver; one repo lockfile |
| Logging | **`structlog`** JSON → Fluent Bit → OpenSearch | Correlation IDs |
| Errors | **`sentry-sdk`** | Same org as Node |
| LLM | **`anthropic`** SDK | Prompt caching default-on for Brain |
| Vector | **`pgvector`** Python binding | Memory Layer queries |
| ML | scikit-learn, statsmodels, Prophet, lifelines, scipy, numpy, pandas | Per `forecasting-prophet` skill |
| Tests | **`pytest`** + pytest-asyncio + `respx` (httpx mocks) + ClickHouse Docker | |
| Lint | `ruff` | Single tool; replaces black + isort + flake8 |
| Type check | `mypy --strict` | |

## Repo layout (per service)

```
apps/<service>/
├── pyproject.toml                 # uv workspace member
├── README.md
├── Dockerfile
└── src/
    ├── main.py                    # FastAPI + grpcio server bootstrap
    ├── config.py                  # Pydantic settings
    ├── logger.py                  # structlog with correlation IDs
    ├── tracing.py                 # X-Ray + contextvars wiring
    ├── grpc/
    │   ├── server.py
    │   └── handlers/<domain>.py
    ├── http/
    │   └── routes.py              # FastAPI router (health + webhooks)
    ├── repositories/              # data layer
    │   ├── postgres.py
    │   └── clickhouse.py
    ├── consumers/                 # Kafka consumers
    │   └── <topic>.py
    └── domain/                    # business logic; no I/O imports

tests/
├── unit/
├── integration/
│   └── conftest.py                # ClickHouse + Postgres + Kafka via docker compose
└── smoke/
    └── test_real_network.py       # spawns real server + curls it
```

## uv workspace

```toml
# pyproject.toml at repo root
[tool.uv.workspace]
members = ["apps/*", "pylibs/*"]

[tool.uv.sources]
brain-db = { workspace = true }
brain-clickhouse = { workspace = true }
brain-kafka = { workspace = true }
brain-metrics = { workspace = true }
brain-regional = { workspace = true }
brain-grpc = { workspace = true }
brain-cost-router = { workspace = true }
```

Single lockfile at repo root. `uv sync` installs everything.

## FastAPI + grpcio bootstrap

```python
# apps/<service>/src/main.py
import asyncio
import signal
from fastapi import FastAPI
from grpc import aio as grpc_aio

from .config import settings
from .logger import setup_logging
from .tracing import setup_tracing
from .grpc.server import register_grpc_servicers
from .http.routes import router

async def main():
    setup_logging()
    setup_tracing()

    # gRPC server
    grpc_server = grpc_aio.server()
    register_grpc_servicers(grpc_server)
    grpc_server.add_insecure_port(f"0.0.0.0:{settings.GRPC_PORT}")
    await grpc_server.start()

    # FastAPI for health + webhooks
    app = FastAPI(title=settings.SERVICE_NAME, version=settings.VERSION)
    app.include_router(router)

    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=settings.HTTP_PORT))

    # Graceful shutdown
    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await asyncio.gather(server.serve(), grpc_server.wait_for_termination(), stop.wait())

if __name__ == "__main__":
    asyncio.run(main())
```

## Structured logging with correlation IDs

```python
# apps/<service>/src/logger.py
import structlog
import contextvars

request_id_var = contextvars.ContextVar("request_id", default=None)
trace_id_var = contextvars.ContextVar("trace_id", default=None)
workspace_id_var = contextvars.ContextVar("workspace_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)

def add_correlation(_, __, event_dict):
    event_dict.update(
        request_id=request_id_var.get(),
        trace_id=trace_id_var.get(),
        workspace_id=workspace_id_var.get(),
        user_id=user_id_var.get(),
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
    )
    return event_dict

def setup_logging():
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            add_correlation,
            structlog.processors.dict_tracebacks,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
    )

log = structlog.get_logger()
```

PII redaction: logger-level field filter for `email`, `phone`, `access_token`, `refresh_token`, `pan_card`, `aadhaar`. Fluent Bit Lua redaction script as second line of defense (TECH/09 §10.12).

## Tracing — X-Ray via OpenTelemetry

```python
# apps/<service>/src/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.propagate import set_global_textmap

def setup_tracing():
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    set_global_textmap(AwsXRayPropagator())
```

## Async patterns

### httpx with retry

```python
from tenacity import retry, wait_exponential_jitter, stop_after_attempt

@retry(wait=wait_exponential_jitter(initial=1, max=30, jitter=2), stop=stop_after_attempt(5))
async def fetch_with_retry(url, headers):
    response = await httpx_client.get(url, headers=headers, timeout=10.0)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 4))
        await asyncio.sleep(retry_after)
        raise httpx.HTTPStatusError("rate-limited", request=response.request, response=response)
    response.raise_for_status()
    return response
```

### asyncpg pool

```python
# pylibs/brain_db/pool.py
import asyncpg

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2, max_size=20,
            setup=set_tenant_context,    # sets app.workspace_id from contextvar
        )
    return _pool

async def set_tenant_context(conn):
    await conn.execute(f"SET app.workspace_id = '{workspace_id_var.get()}'")
```

RLS policy automatically scopes every query.

### ClickHouse query gateway

```python
# pylibs/brain_clickhouse/query.py
import re

WORKSPACE_PREDICATE = re.compile(r"workspace_id\s*=", re.IGNORECASE)

async def query(sql: str, params: dict):
    if not WORKSPACE_PREDICATE.search(sql):
        raise RuntimeError("CH query missing workspace_id predicate")
    return await client.execute(sql, params)
```

### aiokafka consumer

```python
# apps/analytics-service/src/consumers/orders.py
from aiokafka import AIOKafkaConsumer

async def consume_orders():
    consumer = AIOKafkaConsumer(
        "integrations.orders.v1",
        bootstrap_servers=settings.KAFKA_BROKERS,
        group_id="analytics-orders",
        enable_auto_commit=False,        # manual commit after CH write
        value_deserializer=avro_deserializer,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            await process_order(msg.value)
            await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
    finally:
        await consumer.stop()
```

## Anthropic Claude — prompt caching default-on

```python
# pylibs/brain_llm/client.py
from anthropic import AsyncAnthropic
client = AsyncAnthropic()

async def synthesize(workspace_id, system_prompt, user_prompt, model="claude-sonnet-4-6", max_tokens=2000):
    return await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}],
    )
```

`cache_control` on the system prompt gives 10–30x cost reduction at scale. **Never call Anthropic without it.**

## Cost-routing — `@paradigm` decorator

```python
# pylibs/brain_cost_router/decorator.py
from functools import wraps

PARADIGM_REGISTRY = []

def paradigm(kind: str, *, model: str | None = None, token_budget: int | None = None):
    def decorator(fn):
        PARADIGM_REGISTRY.append({"fn": fn.__qualname__, "kind": kind, "model": model, "token_budget": token_budget})

        @wraps(fn)
        async def wrapper(*args, **kwargs):
            # Pre-call: per-brand cap check for LLM paradigms
            if kind in ("small_llm", "frontier_llm"):
                await check_brand_cap(args, kwargs)
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
```

CI parses `PARADIGM_REGISTRY` for cost-routing audit (TECH/12 §4).

## Operational Readiness (pre-handoff)

- [ ] `GET /` returns identifiable JSON
- [ ] `GET /health` returns 200 with `{status, version, deps: {postgres, clickhouse, kafka, redis}}`
- [ ] `HTTP_PORT` + `GRPC_PORT` env vars; crash on `EADDRINUSE`
- [ ] Required env vars validated at startup (Pydantic) — `sys.exit(1)` if missing
- [ ] structlog correlation IDs propagate via contextvars
- [ ] PII redaction at logger + Fluent Bit
- [ ] Sentry initialized; X-Ray spans propagate
- [ ] Real-network smoke test (`pytest tests/smoke/` spawns server + curls)
- [ ] Every `@paradigm` decorator on LLM/ML functions
- [ ] Every CH query goes through `brain_clickhouse.query()`
- [ ] Every gRPC handler asserts `workspace_id` match

## Common pitfalls

- **Blocking I/O in async path** — kills throughput. Always `await`.
- **Skipping `brain_clickhouse.query()`** — direct `client.execute(sql)` bypasses workspace_id safety net.
- **No `cache_control` on Anthropic calls** — 10–30x cost. Always cache the system prompt.
- **Missing `@paradigm`** — cost-discipline dashboard can't track. CI catches.
- **Forgetting `setup=set_tenant_context`** on asyncpg pool — RLS doesn't engage. Detection: a cross-workspace integration test passes when it should fail.
- **Bare `except:`** — swallows BaseException incl. `KeyboardInterrupt`. Use `except Exception:` and log.
- **`asyncio.run` in nested contexts** — crashes. Use `asyncio.get_event_loop().run_until_complete(...)` if you must, or restructure.

## References

- `docs/TECH/09_security_observability.md` — log spine + X-Ray + Sentry wiring
- `docs/TECH/01_data_architecture.md` — Postgres + ClickHouse usage
- `skills/grpc-buf/SKILL.md` — server / client patterns
- `skills/cost-routing-paradigms/SKILL.md` — `@paradigm` decorator + token budgets
- `skills/clickhouse-olap/SKILL.md` — query gateway
- `skills/event-driven-kafka/SKILL.md` — MSK + Avro consumer patterns
- `skills/operational-readiness/SKILL.md` — pre-handoff checklist
