---
name: observability
description: Reference observability spine — log shipper → log store, a metrics backend, OTel traces, error tracking, product analytics. Correlation IDs, structured logging, PII redaction, SLO budgets.
---

# Observability — Reference Implementation

> **Reference implementation.** This skill documents one concrete binding of a seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (correlation IDs, structured
> logging, PII redaction, SLO budgets) are what transfer, not the specific vendors.

## Five surfaces

| Surface | Tech (example) | Answers |
|---|---|---|
| **Logs** | log-shipper DaemonSet → **a log store** (e.g. OpenSearch, 14d hot, object-store archive) + a dual sink | "What did service X do for tenant Y in the last minute?" |
| **Metrics** | a metrics backend + per-service dashboards | "Is p99 latency on the API gateway breaking SLO?" |
| **Traces** | a distributed-tracing backend via the OpenTelemetry SDK | "Where in the fan-out is the slow span?" |
| **Errors** | an error tracker (e.g. Sentry — typed runtime + Python + mobile native) | "What stack trace does this 500 correspond to?" |
| **Product** | a product-analytics tool (web + mobile) | "Are users approving the actions the product surfaces?" |

Every log, span, and error carries `request_id + trace_id + tenant_id + user_id`.

## Correlation ID propagation (the non-negotiable)

```
edge/CDN (X-Request-Id; generate X-Trace-Id if absent)
  → load balancer → API gateway (hook reads headers + token → tenant_id + user_id; AsyncLocalStorage per request)
  → gRPC (metadata: request_id, trace_id, tenant_id, user_id; typed-runtime ALS / Python contextvars carry them)
  → Kafka producer (same four as headers) → consumer (resume ALS/contextvars from headers)
  → log line (structlog/pino adds all four) → log shipper → log store + dual sink
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
    '*.access_token', '*.api_key', '*.tenant_token', '*.phone', '*.email'], censor: '[REDACTED]' },
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

Python structlog mirrors this with `merge_contextvars` + `add_log_level` + `dict_tracebacks` + a `redact_pii` processor before `JSONRenderer`. Full scaffolds belong in the Product Canon.

### Log levels + retention

| Level | Use for | Prod | Retention |
|---|---|---|---|
| DEBUG | Step-by-step tracing | **OFF** | dev only |
| INFO | Significant business events (record ingested, report generated, action dispatched) | ON | 30 days |
| WARN | Recoverable issues (vendor rate-limit, retry exhausted) | ON | 90 days |
| ERROR | Errors handled (caught + degraded) | ON | 90 days |
| FATAL | Critical failures (DB unreachable, OOM, init failed) | ON | 365 days |

**Never DEBUG in production.**

### Correlation wiring at the call site

Carry `request_id` + `tenant_id` on every line via **AsyncLocalStorage** (Node) / **contextvars** (Python):

```typescript
const ctx = new AsyncLocalStorage<{ requestId: string; tenantId?: string }>();
app.addHook('onRequest', (req, _, done) =>
  ctx.run({ requestId: (req.headers['x-request-id'] as string) ?? randomUUID() }, done));
app.addHook('preHandler', (req, _, done) => { ctx.getStore()!.tenantId = req.tenantId; done(); }); // from token, see auth-and-access
export const log = () => logger.child({ request_id: ctx.getStore()?.requestId, tenant_id: ctx.getStore()?.tenantId });
```

A log-store search for `request_id:abc123` shows the **complete call chain** across every service.

### What to log — and what not to

**DO:** business events (`records.ingested`, `report.generated`, `action.dispatched`, `audit_log.recorded`); state transitions (`consent.granted/revoked`, `session.refreshed`); external-call **summaries** (vendor, account, latency, count); errors with full context; perf-budget crossings (aggregated, once/min).

**DON'T:** DEBUG in prod; request/response bodies wholesale (sample 1% if you must); inside tight loops; stack traces for client 4xx (only 5xx); PII (mask); tokens/secrets (redact); `console.log`/`print` (skips redaction); >1 logging library per service.

### Cost discipline — log batches, not items

For high-volume topics (ingestion), Kafka itself is the log of record — log only the **batch summary**:

```typescript
// BAD: for (const e of events) log().info({ id: e.id }, 'event.processed');  // 5,000 lines/poll
// GOOD:
log().info({ count: events.length, source: 'vendor-x', latency_ms: t1 - t0, error_count: failed.length }, 'ingestion.batch.completed');
```

### Standard log schema

```json
{ "timestamp": "...", "level": "info", "service": "api-gateway", "version": "v1.4.2",
  "request_id": "01HX...", "trace_id": "1-..-trace", "tenant_id": "0182...", "user_id": "0193...",
  "method": "POST", "path": "/trpc/<route>", "status": 200, "duration_ms": 47, "msg": "..." }
```

## Log shipper → log store (+ dual sink)

The log shipper `tail`s container logs, applies the orchestrator filter, runs a **`redact.lua`** second-pass redaction (same field list as the logger), then fans out to the log store (`logs-${SERVICE_NAME}`) and a dual sink. Conf + lua live in the infra config.

## Saved views (log explorer)

1. **System Health** — error rate + p99 + throughput per service
2. **Per-Service Deep Dive**
3. **Per-Tenant Investigation** — every line for a `tenant_id`
4. **Trace Stitching** — filter by `trace_id` across services
5. **Cost-Routing Audit** — effort-tier distribution per service (tier-bypass-spike trigger)

## Metrics — standard set per service

`RequestCount` (by status), `RequestDuration` (p50/p95/p99), `GrpcCallCount` (by downstream), `KafkaConsumerLag` (by topic+group), `OlapQueryDuration` (by table), `PostgresQueryDuration` (by class), plus tool-call counters + cost meters where the product exposes tools. Emit under a per-service namespace. Keep under ~100 unique metric streams per service (billing).

## Monitors → alerting/paging

```
error-rate-spike       — error rate per service > 5% over 5 min
p99-latency-spike      — p99 > 2s per service over 5 min
auth-failure-spike     — 4xx + 401/403 > threshold (potential attack)
tier-bypass-spike      — large-model call rate > 1% of total (cost-routing violation)
kafka-consumer-lag     — lag > threshold per consumer group
olap-stale             — max(date) on a freshness-critical table < now() - 30 min
```

## Traces + errors

- **Traces:** auto-instrument the HTTP framework/gRPC/Kafka via the OpenTelemetry instrumentation packages, exporting via the **OTel Collector** to the product's chosen tracing backend. Wrap business logic in manual spans. Pair traces with SLO/RED metrics and span search. Sampling: **5% prod, 100% staging** — never blanket 100% prod.
- **Error tracking:** `init({ dsn, release: '<service>@<version>', tracesSampleRate: 0.05, beforeSend })`; `beforeSend` tags `request_id`/`trace_id`/`tenant_id` from ALS so errors stitch to logs.

## OpenTelemetry as the instrumentation API (NOT a backend swap)

OTel is the **vendor-neutral instrumentation API in code** — the SDK + auto-instrumentation produce spans/metrics/logs; the **OTel Collector ships them to whichever backends `STACK.md` binds**: traces → a tracing backend, metrics → a metrics backend, logs → the log store. The instrumentation API is portable; the chosen backends are a Canon decision.

**Don't mix N competing observability stacks.** Once `STACK.md` binds the metrics/trace/log backends, switching them is an ADR-level decision, not a per-PR choice — the cost is migrating every dashboard, alert, and instrumentation export.

## Circuit breakers (every cross-service call)

Every cross-service call (gRPC downstream, external vendor API, DB/cache) is wrapped in a circuit breaker so a slow/failing dependency degrades gracefully instead of cascading.

| State | Behavior |
|---|---|
| **Closed** | Calls pass; failures counted |
| **Open** | Threshold crossed → fail fast (fallback/cached/degraded) without calling |
| **Half-open** | After cooldown, allow a probe; success → close, failure → re-open |

- Pair with **timeouts** (no call without a deadline) + **bounded retries** (exponential backoff + jitter).
- Degradation: an API-gateway breaker on analytics opens → serve last cached metrics; a breaker on the LLM provider opens → return template responses (mirrors the chaos drill in `devops-aws`).
- Emit breaker state as `CircuitBreakerState` (by downstream) + alarm on sustained Open.

## Every service has (the observability floor)

Verified before "done" (`operational-readiness`): OTel instrumentation (auto + manual spans); metrics; distributed tracing with correlation IDs; structured logging (four fields, PII-redacted); bounded retries (backoff+jitter); health checks (liveness + readiness + dependency); circuit breakers on every cross-service/external call.

## PII redaction rules

NEVER log: `access_token`/`refresh_token`/JWTs/API keys; `email` (SHA-256 hash if you need identity comparison); `phone`; any government/financial identifiers the product handles; full card or amount+name combos; addresses; message content (unless explicit per-event opt-in). Whatever `COMPLIANCE.md` classifies as PII is redacted. Three layers: logger field filter → log-shipper redaction pass → field mapping at display.

## SLOs (illustrative — the product sets its own targets in the Canon)

| Service | SLO |
|---|---|
| api-gateway | 99.9% availability; p99 < 500ms on reads |
| core-service | 99.95% availability; p99 < 200ms on tenant mutations |
| analytics-service | 99.5% availability; p99 < 500ms on metric reads (cached) |
| intelligence-service | 99% availability; the scheduled batch completes by its deadline |
| outbound-service | 99.9% availability; **0** out-of-policy dispatches (channel/window rules per `COMPLIANCE.md`) |
| notifications-service | 99.5%; primary push delivered within its SLO window |
| Mobile app | < 1% crash rate; p95 cold-start < 3s |

## Common failure modes

- **Forgetting correlation IDs** → can't stitch across services (the log-explorer filter returns a partial trace).
- **Logging tokens/PII** — synthetic test injects `email:'test@x.com'` and asserts it never reaches the log store raw.
- **No OTel propagation on Kafka** — trace breaks at the topic boundary; use the Kafka instrumentation, consumers extract headers.
- **Log-store hot-tier disk full** — the shipper drops logs silently; monitor cluster disk weekly.
- **Metrics over-billed** — too many custom metrics × dimensions.
- **No trace sampling rule** — 100% prod = $$$; default 5% prod, 100% staging.
- **No circuit breaker on a cross-service call** — wrap every gRPC/vendor/DB call with a breaker + timeout.
- **Swapping observability backends per-PR** — that's an ADR-level Canon decision, not an ad-hoc change.

## SLO error-budget policy

An SLO without an error budget is a wish. Budget = `(1 − target) × window`.

| SLO | Target | Monthly budget (30d) |
|---|---|---|
| Primary push within SLO window | >99.5% | ~0.15 tenant-days/tenant/mo |
| Audit-log write availability | >99.99% | ~4.3 min/mo |
| API p95 | <2s | <0.5% of reqs may exceed 2s |
| Critical connector freshness | <1h | <0.5% of poll-windows stale >1h |
| Auto-execute reversal rate | <8% | reversals are the budget; >8% burns it |

**Burn-rate alerting (two-window):** fast-burn — 2% of monthly budget in 1h → **page**; slow-burn — sustained drain → **ticket**. Alert at **50% / 75% / 90%** consumed. When exhausted: **freeze non-critical releases** to the affected service until the SLI recovers + run a postmortem. The auto-execute reversal SLO is special: crossing 15% trips an **auto-revert to recommend-only** (where the Canon defines such a path), not just a freeze. Monthly review: Platform/SRE + service owner.

## Wiring

| Concern | Owner | Reference |
|---|---|---|
| Typed-runtime log standard (pino) | **Backend Engineer** | Product Canon |
| Python log standard (structlog) | **AI/ML Engineer** | Product Canon |
| Log shipping + retention/cost | **Platform/SRE** | Product Canon |
| PII redaction policy | **Security Reviewer** | Product Canon (`COMPLIANCE.md`) |

Related: `devops-aws` (log-store/shipper deploy + chaos drills), `security-baseline` (PII posture), `operational-readiness` (probes), `systematic-debugging` (logs are the trail).

## 2026 market update

- **OpenTelemetry graduated CNCF (May 2026)** — OTLP-everywhere is the assumed transport; vendor-locked SDKs are a liability.
- **Continuous profiling is now a first-class signal** (Pyroscope 2.0 / Parca; OTel profiling signal) — add it to the readiness set.
- **eBPF auto-instrumentation** (Beyla / Pixie / Coroot) reduces manual span wiring (`ebpf-observability` if bound).
- **LLM/agent spans** use the `gen_ai.*` semantic conventions — that layer is `ai-observability-tracing`. **Cloud cost** is its own signal — `finops-cost`.
