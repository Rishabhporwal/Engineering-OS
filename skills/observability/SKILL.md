---
name: observability
description: Brain's observability spine — Fluent Bit→OpenSearch, CloudWatch, X-Ray/OTel traces, Sentry, PostHog. Correlation IDs, structured logging, PII redaction, SLO budgets.
---

# Observability — Brain's Spine

## Five surfaces

| Surface | Tech | Answers |
|---|---|---|
| **Logs** | Fluent Bit DaemonSet → **OpenSearch** (14d hot, S3 archive) + CloudWatch Logs (dual) | "What did service X do for workspace Y in the last minute?" |
| **Metrics** | CloudWatch Metrics + per-service dashboards | "Is p99 latency on api-gateway breaking SLO?" |
| **Traces** | AWS X-Ray via OpenTelemetry SDK | "Where in the fan-out is the slow span?" |
| **Errors** | Sentry (TS + Python + mobile native) | "What stack trace does this 500 correspond to?" |
| **Product** | PostHog (web + mobile) | "Are operators approving Morning Brief signals?" |

Every log, span, and error carries `request_id + trace_id + workspace_id + user_id`.

## Correlation ID propagation (the non-negotiable)

```
CloudFront (X-Request-Id; generate X-Trace-Id if absent)
  → ALB → api-gateway (Fastify hook reads headers + JWT → workspace_id + user_id; AsyncLocalStorage per request)
  → gRPC (metadata: request_id, trace_id, workspace_id, user_id; TS ALS / Python contextvars carry them)
  → Kafka producer (same four as headers) → consumer (resume ALS/contextvars from headers)
  → log line (structlog/pino adds all four) → Fluent Bit → OpenSearch + CloudWatch
```

**Verification on every PR:** a synthetic request through the full pipeline shows the **same `request_id`** in every log line across every service it touches.

## Logging (pino / structlog)

Logs are the most expensive observability surface — log too much and you blow the budget AND hide the signal. Structured JSON is the **only** format: pino for Node, structlog for Python. Both attach the four correlation fields + `service` + `version` (git sha) and **redact PII at the field level**.

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

Python structlog mirrors this with `merge_contextvars` + `add_log_level` + `dict_tracebacks` + a `redact_pii` processor before `JSONRenderer`. Full scaffolds in canon/technical-requirements.md.

### Log levels + retention

| Level | Use for | Prod | Retention |
|---|---|---|---|
| DEBUG | Step-by-step tracing | **OFF** | dev only |
| INFO | Significant business events (order ingested, brief synthesized, call placed) | ON | 30 days |
| WARN | Recoverable issues (vendor rate-limit, retry exhausted) | ON | 90 days |
| ERROR | Errors handled (caught + degraded) | ON | 90 days |
| FATAL | Critical failures (DB unreachable, OOM, init failed) | ON | 365 days |

**Never DEBUG in production.**

### Correlation wiring at the call site

Carry `request_id` + `workspace_id` on every line via **AsyncLocalStorage** (Node) / **contextvars** (Python):

```typescript
const ctx = new AsyncLocalStorage<{ requestId: string; workspaceId?: string }>();
app.addHook('onRequest', (req, _, done) =>
  ctx.run({ requestId: (req.headers['x-request-id'] as string) ?? randomUUID() }, done));
app.addHook('preHandler', (req, _, done) => { ctx.getStore()!.workspaceId = req.workspaceId; done(); }); // from JWT, see auth-and-access
export const log = () => logger.child({ request_id: ctx.getStore()?.requestId, workspace_id: ctx.getStore()?.workspaceId });
```

OpenSearch search for `request_id:abc123` shows the **complete call chain** across all 7 services.

### What to log — and what not to

**DO:** business events (`orders.ingested`, `brief.synthesized`, `call.placed`, `decision_log.recorded`); state transitions (`consent.granted/revoked`, `session.refreshed`); external-call **summaries** (vendor, account, latency, count); errors with full context; perf-budget crossings (aggregated, once/min).

**DON'T:** DEBUG in prod; request/response bodies wholesale (sample 1% if you must); inside tight loops; stack traces for client 4xx (only 5xx); PII (mask); tokens/secrets (redact); `console.log`/`print` (skips redaction); >1 logging library per service.

### Cost discipline — log batches, not items

For high-volume topics (ingestion), Kafka itself is the log of record — log only the **batch summary**:

```typescript
// BAD: for (const e of events) log().info({ id: e.id }, 'event.processed');  // 5,000 lines/poll
// GOOD:
log().info({ count: events.length, source: 'shopify', latency_ms: t1 - t0, error_count: failed.length }, 'ingestion.batch.completed');
```

### Standard log schema

```json
{ "timestamp": "...", "level": "info", "service": "api-gateway", "version": "v1.4.2",
  "request_id": "01HX...", "trace_id": "1-..-xray", "workspace_id": "0182...", "user_id": "0193...",
  "method": "POST", "path": "/trpc/store.kpis", "status": 200, "duration_ms": 47, "msg": "..." }
```

## Fluent Bit → OpenSearch (+ CloudWatch dual)

Fluent Bit `tail`s container logs, applies the `kubernetes` filter, runs a **`redact.lua`** second-pass redaction (same field list as the logger), then fans out to `opensearch` (`brain-logs-${SERVICE_NAME}`) and `cloudwatch_logs`. Conf + lua in `infra/k8s/fluent-bit/`.

## Kibana saved views

1. **System Health** — error rate + p99 + throughput per service
2. **Per-Service Deep Dive**
3. **Per-Workspace Investigation** — every line for a `workspace_id`
4. **Trace Stitching** — filter by `trace_id` across services
5. **Cost-Routing Audit** — paradigm distribution per service (paradigm-bypass-spike trigger)

## CloudWatch metrics — standard set per service

`RequestCount` (by status), `RequestDuration` (p50/p95/p99), `GrpcCallCount` (by downstream), `KafkaConsumerLag` (by topic+group), `ClickHouseQueryDuration` (by table), `PostgresQueryDuration` (by class), plus `Brain/MCP/tool_calls_total` + `Brain/MCP/tool_cost_micros`. Emit under namespace `Brain/${SERVICE_NAME}`. Keep under 100 unique metric streams per service (billing).

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

- **Traces:** auto-instrument Fastify/gRPC/Kafka via `@opentelemetry/instrumentation-*`, exporting via the **ADOT (OTel) Collector** — NOT the X-Ray SDKs/Daemon (maintenance Feb 2026 / EOS Feb 2027; no new instrumentation on them). Wrap business logic in manual spans. Modern target: **CloudWatch Application Signals** (SLOs/RED metrics) + **Transaction Search** (100%-sampled span search), X-Ray as the trace store. Sampling: **5% prod, 100% staging** — never blanket 100% prod.
- **Sentry:** `Sentry.init({ dsn, release: '<service>@<version>', tracesSampleRate: 0.05, beforeSend })`; `beforeSend` tags `request_id`/`trace_id`/`workspace_id` from ALS so errors stitch to logs.

## OpenTelemetry as the instrumentation API (NOT a backend swap)

OTel is allowed **only as the vendor-neutral instrumentation API in code** — the SDK + auto-instrumentation produce spans/metrics/logs; the **ADOT Collector ships them to Brain's EXISTING AWS backends**: traces → X-Ray (via Application Signals + Transaction Search), metrics → CloudWatch, logs → OpenSearch. The instrumentation API is portable; the backends are locked. The **ADOT exporter is mandated**.

**Do NOT introduce Prometheus, Grafana, Loki, or Tempo.** Anyone proposing a Prometheus/Grafana migration is changing a locked decision and needs an explicit ADR (and the answer is no).

## Circuit breakers (every cross-service call)

Every cross-service call (gRPC downstream, external vendor API, DB/cache) is wrapped in a circuit breaker so a slow/failing dependency degrades gracefully instead of cascading.

| State | Behavior |
|---|---|
| **Closed** | Calls pass; failures counted |
| **Open** | Threshold crossed → fail fast (fallback/cached/degraded) without calling |
| **Half-open** | After cooldown, allow a probe; success → close, failure → re-open |

- Pair with **timeouts** (no call without a deadline) + **bounded retries** (exponential backoff + jitter).
- Degradation: api-gateway breaker on analytics opens → serve last Redis-cached KPIs; intelligence breaker on Anthropic opens → AI Chat returns template responses (mirrors the AWS FIS chaos drill in `devops-aws`).
- Emit breaker state as `CircuitBreakerState` (by downstream) + alarm on sustained Open.

## Every service has (the observability floor)

Verified before "done" (`operational-readiness`): OTel instrumentation (auto + manual spans); CloudWatch metrics; X-Ray tracing with correlation IDs; structured logging (four fields, PII-redacted); bounded retries (backoff+jitter); health checks (liveness + readiness + dependency); circuit breakers on every cross-service/external call.

## PII redaction rules

NEVER log: `access_token`/`refresh_token`/JWTs/API keys; `email` (SHA-256 hash if you need identity comparison); `phone` (India customer PII); `pan_card`/`aadhaar`; full card or order-total+name combos; addresses; WhatsApp message content (unless explicit per-call opt-in). Three layers: logger field filter → Fluent Bit Lua → OpenSearch field mapping at display.

## SLOs

| Service | SLO |
|---|---|
| api-gateway | 99.9% availability; p99 < 500ms on tRPC reads |
| core-service | 99.95% availability; p99 < 200ms on workspace mutations |
| analytics-service | 99.5% availability; p99 < 500ms on metric reads (Redis cached) |
| intelligence-service | 99% availability; daily tick completes by 07:15 IST |
| lifecycle-service | 99.9% availability; **0** out-of-window dial attempts; **0** DND-blocked dials succeeded |
| notifications-service | 99.5%; **Morning Brief delivered by 07:20 IST on >99.5% of brand-days** |
| Mobile app | < 1% crash rate; p95 cold-start < 3s |

## Common failure modes

- **Forgetting correlation IDs** → can't stitch across services (Kibana filter returns a partial trace).
- **Logging tokens/PII** — synthetic test injects `email:'test@x.com'` and asserts it never reaches OpenSearch raw.
- **No OTel propagation on Kafka** — trace breaks at the topic boundary; use `instrumentation-kafkajs`, consumers extract headers.
- **OpenSearch hot-tier disk full** — Fluent Bit drops logs silently; monitor cluster disk weekly.
- **CloudWatch over-billed** — too many custom metrics × dimensions.
- **No X-Ray sampling rule** — 100% prod = $$$; default 5% prod, 100% staging.
- **No circuit breaker on a cross-service call** — wrap every gRPC/vendor/DB call with a breaker + timeout.
- **Proposing Prometheus/Grafana** — the backends are locked.

## SLO error-budget policy

An SLO without an error budget is a wish. Budget = `(1 − target) × window`.

| SLO | Target | Monthly budget (30d) |
|---|---|---|
| Morning Brief by 07:20 IST | >99.5% | ~0.15 brand-days/brand/mo |
| Decision-Log write availability | >99.99% | ~4.3 min/mo |
| API p95 | <2s | <0.5% of reqs may exceed 2s |
| P0 connector freshness | <1h | <0.5% of poll-windows stale >1h |
| Auto-execute reversal rate | <8% | reversals are the budget; >8% burns it |

**Burn-rate alerting (two-window):** fast-burn — 2% of monthly budget in 1h → **page**; slow-burn — sustained drain → **ticket**. Alert at **50% / 75% / 90%** consumed. When exhausted: **freeze non-critical releases** to the affected service until the SLI recovers + run a postmortem. The auto-execute reversal SLO is special: crossing 15% trips the canon **auto-revert to recommend-only**, not just a freeze. Monthly review: Jatin + service owner.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Node log standard (pino) | **Vikram** | canon/technical-requirements.md |
| Python log standard (structlog) | **Maya** | canon/technical-requirements.md |
| Fluent Bit shipping + retention/cost | **Jatin** | canon/technical-requirements.md |
| PII redaction policy | **Shreya** | canon/technical-requirements.md |

Related: `devops-aws` (OpenSearch/Fluent Bit deploy + FIS chaos), `security-baseline` (PII posture), `operational-readiness` (probes), `systematic-debugging` (logs are the trail).
