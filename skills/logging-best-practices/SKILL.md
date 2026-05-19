---
name: logging-best-practices
description: Structured JSON logging with request_id + workspace_id correlation, level discipline, PII redaction, and Fluent Bit → OpenSearch shipping. Use when wiring a new Brain service, when investigating a "we don't have logs for that" gap, when an audit reveals PII in logs, or when log volume blows the OpenSearch budget.
---

# Logging Best Practices

Brain's observability stack (canon/BRAIN_TECHNICAL.md): **Fluent Bit → OpenSearch (logs) + CloudWatch Metrics + AWS X-Ray (traces) + Sentry (errors) + PostHog (product)**. Logs are the most expensive observability surface — if you log too much or log the wrong things, you simultaneously blow the budget and hide the signal.

This skill is the operational depth behind the `observability` skill — what good logs *look like* at the call site.

## Log levels (Brain canon)

| Level | Use for | Prod | OpenSearch retention |
|---|---|---|---|
| DEBUG | Detailed step-by-step tracing | **OFF** | 0 days (dev only) |
| INFO | Significant business events (order ingested, brief synthesized, call placed) | ON | 30 days |
| WARN | Recoverable issues (vendor rate-limit hit, retry exhausted, cache miss spike) | ON | 90 days |
| ERROR | Errors that completed handling (we caught + degraded) | ON | 90 days |
| FATAL | Critical failures (DB unreachable, OOM, init failed) | ON | 365 days |

Brain rule: **never DEBUG in production.** Local dev only.

## Structured JSON (the only format Brain ships)

```typescript
// Node services — pino is the Brain standard (matches Fastify)
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  base: {
    service: process.env.SERVICE_NAME ?? 'unknown',     // api-gateway | core | notifications | lifecycle
    env: process.env.NODE_ENV,
    version: process.env.GIT_SHA?.slice(0, 7),
  },
  timestamp: pino.stdTimeFunctions.isoTime,
  formatters: { level: (label) => ({ level: label }) }, // emit string level, not numeric
  redact: {
    paths: [
      'req.headers.authorization',
      'req.headers.cookie',
      'req.body.password',
      '*.token',
      '*.refresh_token',
      '*.access_token',
      '*.api_key',
      '*.brand_token',
      '*.phone',          // PII
      '*.email',          // PII
    ],
    censor: '[REDACTED]',
  },
});
```

```python
# Python services — structlog is the Brain standard
import structlog, logging, os

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, os.environ.get("LOG_LEVEL", "INFO"))
    ),
)
log = structlog.get_logger().bind(
    service=os.environ.get("SERVICE_NAME", "unknown"),
    env=os.environ.get("ENV", "dev"),
    version=os.environ.get("GIT_SHA", "")[:7],
)
```

## Correlation: request_id + workspace_id on every log line

This is the single most important Brain logging rule. Every log line — from web BFF through api-gateway through gRPC through service through Kafka — must carry the same `request_id` and `workspace_id`.

```typescript
// Fastify — using AsyncLocalStorage
import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';

const ctx = new AsyncLocalStorage<{ requestId: string; workspaceId?: string }>();

app.addHook('onRequest', (req, _, done) => {
  const requestId = (req.headers['x-request-id'] as string) ?? randomUUID();
  ctx.run({ requestId, workspaceId: undefined }, done);
});

app.addHook('preHandler', (req, _, done) => {
  // workspaceId set from JWT — see session-management
  const store = ctx.getStore()!;
  store.workspaceId = req.workspaceId;
  done();
});

export function log() {
  const store = ctx.getStore();
  return logger.child({ request_id: store?.requestId, workspace_id: store?.workspaceId });
}

// Usage anywhere in the request scope:
log().info({ orders_count: 42 }, 'orders.ingested');
```

```python
# FastAPI — using contextvars
from contextvars import ContextVar
import structlog

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
workspace_id_ctx: ContextVar[str] = ContextVar("workspace_id", default="")

@app.middleware("http")
async def add_correlation(request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid4())
    request_id_ctx.set(rid)
    structlog.contextvars.bind_contextvars(request_id=rid)
    # workspace_id_ctx + bind set in JWT middleware later
    return await call_next(request)
```

Searching OpenSearch for `request_id:abc123` then shows you the **complete call chain** across all 7 services. This is the difference between a 5-minute debug session and a 4-hour one.

## PII redaction (Shreya VETO territory)

Brain handles PII (customer phone, email, address) and PCI-adjacent data (order amounts, AOV). **Never log unsanitized PII.**

```typescript
// Generic redactor for ad-hoc payloads
const SENSITIVE = new Set(['password', 'token', 'refresh_token', 'access_token', 'api_key', 'brand_token']);
const PII = new Set(['phone', 'email', 'address', 'pan', 'gstin']);

function sanitize(obj: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj).map(([k, v]) => {
      if (SENSITIVE.has(k)) return [k, '[REDACTED]'];
      if (PII.has(k)) return [k, maskPII(String(v))];
      if (v && typeof v === 'object') return [k, sanitize(v as Record<string, unknown>)];
      return [k, v];
    }),
  );
}

function maskPII(s: string) {
  if (s.includes('@')) return s.replace(/(.{2}).*@/, '$1***@');
  if (/^\+?\d/.test(s)) return s.slice(0, 4) + '***' + s.slice(-2);
  return '[REDACTED]';
}
```

Pino's `redact` config (above) covers the structured case. The `sanitize()` helper covers ad-hoc `JSON.stringify(somePayload)` calls — which you should avoid anyway.

## What to log (and what not to)

### DO

- Business events: `orders.ingested`, `brief.synthesized`, `call.placed`, `decision_log.recorded`
- State transitions: `consent.granted`, `consent.revoked`, `session.refreshed`
- External call summaries: `shopify.poll completed` with vendor, account, latency, count
- Errors with full context (request_id, workspace_id, actor, stack, the inputs that triggered it)
- Performance crossings: "query exceeded 100ms p95 budget" — once per minute aggregated

### DON'T

- DEBUG in production
- Request/response bodies wholesale (sample at 1% if you must)
- Inside tight loops (one log line per Kafka message at 5K msg/s is 5K log lines/s)
- Stack traces for client 4xx errors (it's not our fault, it's a client bug)
- PII (phone, email, address — always mask)
- Tokens, secrets, brand API keys (always redact)
- `console.log` (use the structured logger or you skip redaction)

## Cost discipline

OpenSearch storage cost is real. For high-volume topics (raw events from Maya's ingestion), don't ship every event to logs — Kafka itself is the log of record. Log only the *batch summary* (start, end, count, errors).

```typescript
// BAD — 5,000 log lines per poll
for (const evt of events) {
  log().info({ event_id: evt.id }, 'event.processed');
}

// GOOD — one log line per batch
log().info(
  { count: events.length, source: 'shopify', latency_ms: t1 - t0, error_count: failed.length },
  'ingestion.batch.completed',
);
```

## Best practices (summary)

- Structured JSON only (pino / structlog)
- request_id + workspace_id on every line via AsyncLocalStorage / contextvars
- Redact configured at logger level, not per-call
- Per-service `service` + `version` (git sha) base fields
- Log at the right level; never DEBUG in prod
- Aggregate batches; don't log per-item in tight loops
- Sanitize PII before logging; never log secrets

## Never do

- Log passwords, tokens, refresh tokens, brand API keys
- Use `console.log` / `print` in production
- Log inside tight loops
- Include stack traces for 4xx (client errors) — only 5xx
- Ship full request bodies wholesale
- Spread logging libraries across one service (pick one per language)

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Node services log standard (pino) | **Vikram** | canon/BRAIN_TECHNICAL.md (logs) |
| Python services log standard (structlog) | **Maya** | canon/BRAIN_TECHNICAL.md |
| Fluent Bit → OpenSearch shipping | **Jatin** | canon/BRAIN_TECHNICAL.md (log shipping) |
| Retention policy + cost | **Jatin** | |
| PII redaction policy | **Shreya** | canon/BRAIN_TECHNICAL.md (privacy) |

Related Brain skills: `observability` (the broader stack), `root-cause-tracing` (logs are the trail), `security-baseline` (PII + secrets).
