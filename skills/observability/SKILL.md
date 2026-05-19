---
name: observability
description: Brain's centralized observability spine — Fluent Bit → OpenSearch (logs) + CloudWatch Metrics + AWS X-Ray (traces) + Sentry (errors) + PostHog (product). Single correlation ID (request_id + trace_id + workspace_id + user_id) propagates end-to-end through HTTP headers, gRPC metadata, Kafka envelope. PII redaction at logger + Fluent Bit Lua script. Auto-load whenever wiring instrumentation, debugging cross-service flows, building Kibana dashboards, or investigating an incident.
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

Both loggers attach the four correlation fields + `service` + `version` to every line and **redact PII at the field level** (`email`, `phone`, `access_token`, `refresh_token`, `authorization`, `pan_card`, `aadhaar`, `*.token`). Representative Node config:

```typescript
export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: { log: (obj) => ({ ...obj, ...als.getStore(), service: SERVICE_NAME, version: VERSION }) },
  redact: ['email', 'phone', 'access_token', 'refresh_token', 'authorization', '*.token'],
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

Python structlog mirrors this with an `add_correlation` processor (reads contextvars) + a `redact_pii` processor before `JSONRenderer`. Full pino/structlog/Fastify-hook scaffolds are in canon/BRAIN_TECHNICAL.md.

### Standard log schema

```json
{ "timestamp": "...", "level": "info", "service": "api-gateway", "version": "v1.4.2",
  "request_id": "01HX...", "trace_id": "1-..-xray", "workspace_id": "0182...", "user_id": "0193...",
  "method": "POST", "path": "/trpc/store.kpis", "status": 200, "duration_ms": 47, "msg": "..." }
```

## Fluent Bit → OpenSearch (+ CloudWatch dual)

Fluent Bit `tail`s container logs, applies the `kubernetes` filter, runs a **`redact.lua`** second-pass redaction (same field list as the logger), then fans out to the `opensearch` output (`brain-logs-${SERVICE_NAME}` index) and `cloudwatch_logs` (`/aws/eks/brain/${SERVICE_NAME}`). The conf + lua live in `infra/k8s/fluent-bit/` and canon/BRAIN_TECHNICAL.md.

## Kibana saved views (canon/BRAIN_TECHNICAL.md)

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

## PII redaction rules

NEVER log: `access_token`/`refresh_token`/JWTs/API keys; `email` (SHA-256 hash if you need identity comparison); `phone` (India customer PII); `pan_card`/`aadhaar`; full card or order-total+name combos; addresses; WhatsApp message content (unless explicit per-call opt-in). Three layers: logger field filter → Fluent Bit Lua → OpenSearch field mapping at display.

## SLOs (canon/BRAIN_TECHNICAL.md)

| Service | SLO |
|---|---|
| api-gateway | 99.9% availability; p99 < 500ms on tRPC reads |
| core-service | 99.95% availability; p99 < 200ms on workspace mutations |
| analytics-service | 99.5% availability; p99 < 500ms on metric reads (Redis cached) |
| intelligence-service | 99% availability; daily tick completes by 07:15 IST |
| lifecycle-service | 99.9% availability; **0** out-of-window dial attempts; **0** DND-blocked dials succeeded |
| notifications-service | 99.5% availability; Morning Brief push delivered by 07:30 IST |
| Mobile app | < 1% crash rate; p95 cold-start < 3s |

## Common failure modes

- **Forgetting correlation IDs** — request_id missing → can't stitch across services. Detection: Kibana filter returns a partial trace.
- **Logging tokens / PII** — three-layer redaction misses a field. Detection: synthetic test injects `email:'test@x.com'` and asserts it never reaches OpenSearch raw indices.
- **No OTel propagation on Kafka** — trace breaks at the topic boundary. Use `instrumentation-kafkajs`; consumers must extract headers.
- **OpenSearch hot-tier disk full** — Fluent Bit drops logs silently. Monitor cluster disk weekly.
- **CloudWatch over-billed** — too many custom metrics × dimensions.
- **No X-Ray sampling rule** — 100% prod = $$$. Default 5% prod, 100% staging.

## References

- `canon/BRAIN_TECHNICAL.md` — canonical log spine + logger scaffolds + Kibana dashboards + monitors + cost-discipline dashboard
- `skills/devops-aws/SKILL.md` — OpenSearch + Fluent Bit deployment
- `skills/security-baseline/SKILL.md` — PII redaction posture
