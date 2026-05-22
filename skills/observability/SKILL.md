---
name: observability
description: Brain's centralized observability spine — Fluent Bit → OpenSearch (logs) + CloudWatch Metrics + AWS X-Ray (traces) + Sentry (errors) + PostHog (product). Structured JSON logging (pino/structlog) with level discipline, retention, and the what-to-log catalog; single correlation ID (request_id + trace_id + workspace_id + user_id) propagates end-to-end through HTTP headers, gRPC metadata, Kafka envelope; OTel instrumentation; circuit breakers. PII redaction at logger + Fluent Bit Lua script. Auto-load whenever wiring instrumentation or a new service's logging, debugging cross-service flows, building Kibana dashboards, investigating an incident, or when log volume blows the OpenSearch budget.
---

# Observability — Brain's Spine

## Five surfaces

| Surface | Tech | What it answers |
|---|---|---|
| **Logs** (centralized) | Fluent Bit DaemonSet on EKS → **OpenSearch** (multi-AZ; 14d hot, S3 archive) + CloudWatch Logs (dual) | "What did service X do for workspace Y in the last minute?" |
| **Metrics** | CloudWatch Metrics + per-service dashboards | "Is p99 latency on api-gateway breaking SLO?" |
| **Traces** | AWS X-Ray via OpenTelemetry SDK | "Where in the cross-service fan-out is the slow span?" |
| **Errors** | Sentry (TS + Python + mobile native) | "What stack trace does this 500 correspond to?" |
| **Product** | PostHog (web + mobile) | "Are operators acknowledging insights? Approving Morning Brief signals?" |

Correlation: every log, span, and error event carries `request_id + trace_id + workspace_id + user_id`. Kibana saved views stitch these; the X-Ray trace_id renders as a deep link from a Kibana custom field formatter.

## Correlation ID propagation (the non-negotiable)

```
CloudFront (X-Request-Id; generate X-Trace-Id if absent)
  → ALB → api-gateway (Fastify hook reads headers + JWT → workspace_id + user_id; AsyncLocalStorage per request)
  → gRPC (metadata: request_id, trace_id, workspace_id, user_id; TS ALS / Python contextvars carry them)
  → Kafka producer (same four as headers) → consumer (resume ALS/contextvars from headers)
  → log line (structlog/pino adds all four) → Fluent Bit → OpenSearch + CloudWatch
```

**Verification on every PR:** a synthetic request through the full pipeline shows up with the **same `request_id`** in every log line across every service it touches.

## Logging (pino / structlog)

Logs are the most expensive observability surface — log too much or the wrong things and you simultaneously blow the budget and hide the signal. Structured JSON is the **only** format Brain ships: pino for Node (matches Fastify), structlog for Python. Both attach the four correlation fields + `service` + `version` (git sha) to every line and **redact PII at the field level**. Representative Node config:

```typescript
export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  base: { service: SERVICE_NAME, env: process.env.NODE_ENV, version: VERSION },
  formatters: { level: (l) => ({ level: l }), log: (obj) => ({ ...obj, ...als.getStore() }) },
  redact: { paths: ['req.headers.authorization', 'req.headers.cookie', '*.token', '*.refresh_token',
    '*.access_token', '*.api_key', '*.brand_token', '*.phone', '*.email'], censor: '[REDACTED]' },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

Python structlog mirrors this with `merge_contextvars` + `add_log_level` + `dict_tracebacks` + a `redact_pii` processor before `JSONRenderer`, bound with `service`/`env`/`version`. Full scaffolds in canon/technical-requirements.md.

### Log levels + retention (Brain canon)

| Level | Use for | Prod | OpenSearch retention |
|---|---|---|---|
| DEBUG | Step-by-step tracing | **OFF** | dev only |
| INFO | Significant business events (order ingested, brief synthesized, call placed) | ON | 30 days |
| WARN | Recoverable issues (vendor rate-limit, retry exhausted, cache-miss spike) | ON | 90 days |
| ERROR | Errors handled (caught + degraded) | ON | 90 days |
| FATAL | Critical failures (DB unreachable, OOM, init failed) | ON | 365 days |

**Never DEBUG in production** — local dev only.

### Correlation wiring at the call site

Carry `request_id` + `workspace_id` on every line via **AsyncLocalStorage** (Node) / **contextvars** (Python) so anything in request scope logs them without threading args:

```typescript
const ctx = new AsyncLocalStorage<{ requestId: string; workspaceId?: string }>();
app.addHook('onRequest', (req, _, done) =>
  ctx.run({ requestId: (req.headers['x-request-id'] as string) ?? randomUUID() }, done));
app.addHook('preHandler', (req, _, done) => { ctx.getStore()!.workspaceId = req.workspaceId; done(); }); // from JWT, see auth-and-access
export const log = () => logger.child({ request_id: ctx.getStore()?.requestId, workspace_id: ctx.getStore()?.workspaceId });
// log().info({ orders_count: 42 }, 'orders.ingested');
```

Searching OpenSearch for `request_id:abc123` then shows the **complete call chain** across all 7 services — the difference between a 5-minute debug session and a 4-hour one.

### What to log — and what not to

**DO:** business events (`orders.ingested`, `brief.synthesized`, `call.placed`, `decision_log.recorded`); state transitions (`consent.granted/revoked`, `session.refreshed`); external-call **summaries** (vendor, account, latency, count); errors with full context (request_id, workspace_id, actor, stack, triggering inputs); perf-budget crossings (aggregated, once/min).

**DON'T:** DEBUG in prod; request/response bodies wholesale (sample at 1% if you must); inside tight loops; stack traces for client 4xx (their bug, not ours — only 5xx); PII (always mask); tokens/secrets/brand keys (always redact); `console.log`/`print` (skips redaction); spreading >1 logging library per service.

### Cost discipline — log batches, not items

OpenSearch storage cost is real. For high-volume topics (Maya's ingestion), Kafka itself is the log of record — log only the **batch summary**, never per-item:

```typescript
// BAD — 5,000 log lines per poll:  for (const e of events) log().info({ id: e.id }, 'event.processed');
// GOOD — one line per batch:
log().info({ count: events.length, source: 'shopify', latency_ms: t1 - t0, error_count: failed.length }, 'ingestion.batch.completed');
```

### Standard log schema

```json
{ "timestamp": "...", "level": "info", "service": "api-gateway", "version": "v1.4.2",
  "request_id": "01HX...", "trace_id": "1-..-xray", "workspace_id": "0182...", "user_id": "0193...",
  "method": "POST", "path": "/trpc/store.kpis", "status": 200, "duration_ms": 47, "msg": "..." }
```

## Fluent Bit → OpenSearch (+ CloudWatch dual)

Fluent Bit `tail`s container logs, applies the `kubernetes` filter, runs a **`redact.lua`** second-pass redaction (same field list as the logger), then fans out to the `opensearch` output (`brain-logs-${SERVICE_NAME}` index) and `cloudwatch_logs` (`/aws/eks/brain/${SERVICE_NAME}`). The conf + lua live in `infra/k8s/fluent-bit/` and canon/technical-requirements.md.

## Kibana saved views (canon/technical-requirements.md)

1. **System Health** — error rate + p99 + throughput per service
2. **Per-Service Deep Dive** — one service's logs over a window
3. **Per-Workspace Investigation** — every log line for a `workspace_id`
4. **Trace Stitching** — filter by `trace_id` across all services for one request
5. **Cost-Routing Audit** — paradigm distribution per service (paradigm-bypass-spike trigger)

## CloudWatch metrics — standard set per service

`RequestCount` (by status), `RequestDuration` (p50/p95/p99), `GrpcCallCount` (by downstream), `KafkaConsumerLag` (by topic+group), `ClickHouseQueryDuration` (by table), `PostgresQueryDuration` (by query class), plus `Brain/MCP/tool_calls_total` and `Brain/MCP/tool_cost_micros` (cost-routing audit). Emit via `@aws-sdk/client-cloudwatch` `PutMetricDataCommand` under namespace `Brain/${SERVICE_NAME}`. Keep under 100 unique metric streams per service (billing).

## OpenSearch monitors → PagerDuty/Slack

```
error-rate-spike       — error rate per service > 5% over 5 min
p99-latency-spike      — p99 > 2s per service over 5 min
auth-failure-spike     — 4xx + 401/403 > threshold (potential attack)
paradigm-bypass-spike  — Frontier LLM call rate > 1% of total (cost-routing violation)
kafka-consumer-lag     — lag > threshold per consumer group
clickhouse-stale       — max(date) on daily_metrics < now() - 30 min
```

## Traces + errors

- **X-Ray:** auto-instrument Fastify/gRPC/Kafka via the matching `@opentelemetry/instrumentation-*` packages + OTLP exporter; wrap business logic in manual spans (`tracer.start_as_current_span("amer_computation")`). Sampling: **5% prod, 100% staging** — never 100% prod ($$$).
- **Sentry:** `Sentry.init({ dsn, release: '<service>@<version>', tracesSampleRate: 0.05, beforeSend })`; `beforeSend` tags the event with `request_id`/`trace_id`/`workspace_id` from ALS so errors stitch to logs.

## OpenTelemetry as the instrumentation API (NOT a backend swap)

OpenTelemetry is allowed **only as the vendor-neutral instrumentation API in code** — the OTel SDK + auto-instrumentation packages produce spans/metrics/logs, and the **OTLP exporter ships them to Brain's EXISTING AWS backends**: traces → **AWS X-Ray**, metrics → **CloudWatch**, logs → **OpenSearch** (via Fluent Bit). The instrumentation API is portable; the backends are locked.

```
code (OTel SDK: @opentelemetry/* / opentelemetry-python)
  → OTLP exporter / ADOT Collector
     → X-Ray (traces) + CloudWatch (metrics) + OpenSearch (logs)
```

**Do NOT introduce Prometheus, Grafana, Loki, or Tempo.** OTel ≠ a new backend stack — it's the instrumentation layer in front of the backends Brain already runs. Anyone proposing a Prometheus/Grafana migration is changing a locked decision and needs an explicit ADR (and the answer is no).

## Circuit breakers (every cross-service call)

Every cross-service call (gRPC to a downstream, an external vendor API, a DB/cache dependency) is wrapped in a **circuit breaker** so a slow/failing dependency degrades gracefully instead of cascading.

| State | Behavior |
|---|---|
| **Closed** | Calls pass through; failures counted |
| **Open** | Failure threshold crossed → fail fast (return fallback / cached / degraded) without calling the dependency |
| **Half-open** | After a cooldown, allow a probe call; success → close, failure → re-open |

- Pair with **timeouts** (no call without a deadline — gRPC deadline, vendor httpx timeout) + **bounded retries** (exponential backoff + jitter).
- Graceful degradation examples: api-gateway breaker on analytics-service opens → serve last Redis-cached KPIs; intelligence breaker on Anthropic opens → AI Chat returns template responses (mirrors the AWS FIS chaos drill in `devops-aws`).
- Emit breaker state as a CloudWatch metric (`CircuitBreakerState` by downstream) + alarm on sustained Open.

## Every service has (the observability floor)

Non-negotiable per service — verified before a service is "done" (`operational-readiness`):

- **OTel instrumentation** (auto + manual spans) exporting to X-Ray/CloudWatch/OpenSearch
- **Metrics** (CloudWatch standard set below)
- **Tracing** (X-Ray, correlation IDs propagated)
- **Structured logging** (pino/structlog, four correlation fields, PII-redacted)
- **Retries** (bounded, backoff+jitter on transient failures)
- **Health checks** (liveness + readiness + dependency probes — `operational-readiness`)
- **Circuit breakers** (on every cross-service / external call)

## PII redaction rules

NEVER log: `access_token`/`refresh_token`/JWTs/API keys; `email` (SHA-256 hash if you need identity comparison); `phone` (India customer PII); `pan_card`/`aadhaar`; full card or order-total+name combos; addresses; WhatsApp message content (unless explicit per-call opt-in). Three layers: logger field filter → Fluent Bit Lua → OpenSearch field mapping at display.

## SLOs (canon/technical-requirements.md)

| Service | SLO |
|---|---|
| api-gateway | 99.9% availability; p99 < 500ms on tRPC reads |
| core-service | 99.95% availability; p99 < 200ms on workspace mutations |
| analytics-service | 99.5% availability; p99 < 500ms on metric reads (Redis cached) |
| intelligence-service | 99% availability; daily tick completes by 07:15 IST |
| lifecycle-service | 99.9% availability; **0** out-of-window dial attempts; **0** DND-blocked dials succeeded |
| notifications-service | 99.5% availability; **Morning Brief delivered by 07:20 IST on >99.5% of brand-days** (canon SLO) |
| Mobile app | < 1% crash rate; p95 cold-start < 3s |

## Common failure modes

- **Forgetting correlation IDs** — request_id missing → can't stitch across services. Detection: Kibana filter returns a partial trace.
- **Logging tokens / PII** — three-layer redaction misses a field. Detection: synthetic test injects `email:'test@x.com'` and asserts it never reaches OpenSearch raw indices.
- **No OTel propagation on Kafka** — trace breaks at the topic boundary. Use `instrumentation-kafkajs`; consumers must extract headers.
- **OpenSearch hot-tier disk full** — Fluent Bit drops logs silently. Monitor cluster disk weekly.
- **CloudWatch over-billed** — too many custom metrics × dimensions.
- **No X-Ray sampling rule** — 100% prod = $$$. Default 5% prod, 100% staging.
- **No circuit breaker on a cross-service call** — a slow downstream cascades into the caller's latency budget. Wrap every gRPC/vendor/DB call with a breaker + timeout.
- **Proposing Prometheus/Grafana** — OTel is the instrumentation API; the backends (X-Ray/CloudWatch/OpenSearch) are locked. Don't swap the backend stack.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Node services log standard (pino) | **Vikram** | canon/technical-requirements.md (logs) |
| Python services log standard (structlog) | **Maya** | canon/technical-requirements.md |
| Fluent Bit → OpenSearch shipping + retention/cost | **Jatin** | canon/technical-requirements.md (log shipping) |
| PII redaction policy | **Shreya** | canon/technical-requirements.md (privacy) |

## References

- `canon/technical-requirements.md` — canonical log spine + logger scaffolds + Kibana dashboards + monitors + cost-discipline dashboard
- `skills/devops-aws/SKILL.md` — OpenSearch + Fluent Bit deployment; AWS FIS chaos (breaker behavior under failure)
- `skills/security-baseline/SKILL.md` — PII redaction posture
- `skills/operational-readiness/SKILL.md` — liveness/readiness/dependency probes
- `skills/systematic-debugging/SKILL.md` — logs are the trail (backward root-cause tracing)
