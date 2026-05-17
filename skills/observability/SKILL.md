---
name: observability
description: Brain's centralized observability spine — Fluent Bit → OpenSearch (logs) + CloudWatch Metrics + AWS X-Ray (traces) + Sentry (errors) + PostHog (product). Single correlation ID (request_id + trace_id + workspace_id + user_id) propagates end-to-end through HTTP headers, gRPC metadata, Kafka envelope. PII redaction at logger + Fluent Bit Lua script. Auto-load whenever wiring instrumentation, debugging cross-service flows, building Kibana dashboards, or investigating an incident.
---

# Observability — Brain's Spine

## Five surfaces

| Surface | Tech | What it answers |
|---|---|---|
| **Logs** (centralized) | Fluent Bit DaemonSet on EKS → **OpenSearch** (multi-AZ; 14d hot, S3 archive after) + CloudWatch Logs (dual) | "What did service X do for workspace Y in the last minute?" |
| **Metrics** | CloudWatch Metrics + per-service dashboards | "Is p99 latency on api-gateway breaking SLO?" |
| **Traces** | AWS X-Ray via OpenTelemetry SDK | "Where in the cross-service fan-out is the slow span?" |
| **Errors** | Sentry (TS + Python + mobile native) | "What stack trace does this 500 correspond to?" |
| **Product** | PostHog (web + mobile) | "Are operators acknowledging insights? Approving Morning Brief signals?" |

Correlation: every log, span, error event carries `request_id + trace_id + workspace_id + user_id`. Kibana saved views stitch these. X-Ray trace_id renders as a deep link from Kibana custom field formatter.

## Correlation ID propagation

```
HTTP request enters CloudFront
   ↓ (X-Request-Id from CF; generate X-Trace-Id if absent)
ALB → api-gateway
   ↓ (Fastify hook reads X-Request-Id + X-Trace-Id + Authorization JWT → workspace_id + user_id)
   ↓ (AsyncLocalStorage carries them per request)
api-gateway → gRPC → backend service
   ↓ (gRPC metadata: request_id, trace_id, workspace_id, user_id)
   ↓ (Python contextvars / TS AsyncLocalStorage carry them)
backend service → Kafka producer
   ↓ (Kafka headers: request_id, trace_id, workspace_id, user_id)
Kafka consumer → service
   ↓ (resume contextvars/ALS from headers)
service → log line
   ↓ (structlog/pino adds all four)
Fluent Bit → OpenSearch + CloudWatch
```

Verification on every PR: a synthetic request through the full pipeline shows up with the same `request_id` in every log line.

## Node logging — pino (Fastify)

```typescript
// apps/<service>/src/logger.ts
import pino from 'pino';
import { AsyncLocalStorage } from 'node:async_hooks';

export const als = new AsyncLocalStorage<{
  requestId: string;
  traceId: string;
  workspaceId?: string;
  userId?: string;
}>();

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    log: (obj) => {
      const ctx = als.getStore();
      return { ...obj, ...ctx, service: SERVICE_NAME, version: VERSION };
    },
    level: (label) => ({ level: label }),
  },
  redact: ['email', 'phone', 'access_token', 'refresh_token', 'authorization', '*.password', '*.token'],
  timestamp: pino.stdTimeFunctions.isoTime,
});
```

Fastify hook:
```typescript
app.addHook('preHandler', async (req, reply) => {
  const requestId = req.headers['x-request-id'] || crypto.randomUUID();
  const traceId = req.headers['x-trace-id'] || crypto.randomUUID();
  als.enterWith({ requestId, traceId, workspaceId: req.workspaceId, userId: req.userId });
  reply.header('x-request-id', requestId);
});
```

## Python logging — structlog

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

def redact_pii(_, __, event_dict):
    REDACT_KEYS = {"email", "phone", "access_token", "refresh_token", "authorization", "pan_card", "aadhaar"}
    for key in list(event_dict.keys()):
        if key.lower() in REDACT_KEYS:
            event_dict[key] = "<redacted>"
    return event_dict

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        add_correlation,
        redact_pii,
        structlog.processors.dict_tracebacks,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
)

log = structlog.get_logger()
```

## Fluent Bit → OpenSearch

```ini
# infra/k8s/fluent-bit/fluent-bit.conf
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            cri
    Tag               kube.*
    Refresh_Interval  5

[FILTER]
    Name              kubernetes
    Match             kube.*
    Merge_Log         On

[FILTER]
    Name              lua
    Match             kube.*
    script            redact.lua
    call              redact

[OUTPUT]
    Name              opensearch
    Match             kube.*
    Host              ${OPENSEARCH_HOST}
    Port              443
    TLS               On
    Index             brain-logs-${SERVICE_NAME}
    Logstash_Format   On
    Logstash_Prefix   brain-logs-${SERVICE_NAME}

[OUTPUT]
    Name              cloudwatch_logs
    Match             kube.*
    region            ap-south-1
    log_group_name    /aws/eks/brain/${SERVICE_NAME}
    log_stream_prefix ${HOSTNAME}-
    auto_create_group On
```

`redact.lua`:
```lua
function redact(tag, ts, record)
  local fields = {"email","phone","access_token","refresh_token","authorization","pan_card","aadhaar"}
  for _, k in ipairs(fields) do
    if record[k] then record[k] = "<redacted>" end
  end
  return 2, ts, record
end
```

## Standard log schema

```json
{
  "timestamp": "2026-05-13T07:15:32.482Z",
  "level": "info",
  "service": "api-gateway",
  "version": "v1.4.2",
  "request_id": "01HX...",
  "trace_id": "1-..-xrayformat",
  "workspace_id": "0182...",
  "user_id": "0193...",
  "method": "POST",
  "path": "/trpc/store.kpis",
  "status": 200,
  "duration_ms": 47,
  "msg": "trpc.store.kpis succeeded"
}
```

## Kibana saved views (TECH/09 §10.10)

1. **System Health** — error rate + p99 + throughput per service
2. **Per-Service Deep Dive** — drill into one service's logs over a time window
3. **Per-Workspace Investigation** — every log line for a specific `workspace_id`
4. **Trace Stitching** — filter by `trace_id` to see all logs across all services for one request
5. **Cost-Routing Audit** — paradigm distribution per service (paradigm-bypass-spike trigger)

## CloudWatch metrics

Emit standard metric set per service:

```typescript
// Node — using @aws-sdk/client-cloudwatch
await cloudwatch.send(new PutMetricDataCommand({
  Namespace: `Brain/${SERVICE_NAME}`,
  MetricData: [
    { MetricName: 'TrpcRequestDuration', Value: durationMs, Unit: 'Milliseconds', Dimensions: [{ Name: 'Procedure', Value: 'store.kpis' }] },
  ],
}));
```

Standard set:
- `<Service>/RequestCount` — by status code
- `<Service>/RequestDuration` — p50, p95, p99
- `<Service>/GrpcCallCount` — by downstream service
- `<Service>/KafkaConsumerLag` — by topic + consumer group
- `<Service>/ClickHouseQueryDuration` — by table
- `<Service>/PostgresQueryDuration` — by query class
- `Brain/MCP/tool_calls_total` — by tool + status + paradigm
- `Brain/MCP/tool_cost_micros` — for cost-routing audit

## OpenSearch monitors → PagerDuty/Slack

```
error-rate-spike       — error rate per service > 5% over 5 min
p99-latency-spike      — p99 > 2s per service over 5 min
auth-failure-spike     — 4xx + 401/403 > threshold (potential attack)
paradigm-bypass-spike  — Frontier LLM call rate > 1% of total (cost-routing violation)
kafka-consumer-lag     — lag > threshold per consumer group
clickhouse-stale       — max(date) on daily_metrics < now() - 30 min
```

## X-Ray spans

```typescript
// Fastify auto-instrumentation via @opentelemetry/instrumentation-fastify + OTLP exporter to X-Ray daemon
// gRPC: @opentelemetry/instrumentation-grpc
// Kafka: @opentelemetry/instrumentation-kafkajs
```

Manual spans for business logic:
```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("amer_computation"):
    result = compute_amer(rows)
```

## Sentry

```typescript
import * as Sentry from '@sentry/node';
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  release: `${SERVICE_NAME}@${VERSION}`,
  tracesSampleRate: 0.05,
  beforeSend: (event) => {
    const ctx = als.getStore();
    if (ctx) {
      event.tags = { ...event.tags, request_id: ctx.requestId, trace_id: ctx.traceId, workspace_id: ctx.workspaceId };
    }
    return event;
  },
});
```

## PII redaction rules

NEVER log:
- `access_token`, `refresh_token`, JWTs, API keys
- `email` (use SHA-256 hash if you need identity comparison)
- `phone` (especially India phone numbers — they're customer PII)
- `pan_card`, `aadhaar` (Indian government IDs)
- Full credit card or order total + name combos
- Customer addresses
- WhatsApp message content (unless explicit per-call opt-in)

Three-layer redaction:
1. **Logger field filter** (per-service config)
2. **Fluent Bit Lua redaction** (second pass)
3. **OpenSearch field mapping** (display-time)

## SLOs (TECH/09)

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

- **Forgetting correlation IDs** — request_id missing from log lines → can't stitch across services. Detection: Kibana saved-view filter returns partial trace.
- **Logging tokens / PII** — three-layer redaction misses one field. Detection: synthetic test injects `email: 'test@x.com'` and asserts it never appears in OpenSearch raw indices.
- **No OTel propagation on Kafka** — trace breaks at the topic boundary. Use `@opentelemetry/instrumentation-kafkajs` and ensure consumers extract headers.
- **OpenSearch hot-tier disk full** — Fluent Bit drops logs silently. Monitor cluster disk weekly.
- **CloudWatch over-billed** — too many custom metrics × dimensions. Stay under 100 unique metric streams per service.
- **No X-Ray sampling rule** — sampling 100% in prod = $$$. Default 5% prod, 100% staging.

## References

- `docs/TECH/09_security_observability.md` — canonical log spine + Kibana dashboards + monitors
- `docs/TECH/12_cost_routing_compute.md` §5 — cost-discipline dashboard (paradigm-bypass-spike monitor)
- `skills/devops-aws/SKILL.md` — OpenSearch + Fluent Bit deployment
- `skills/security-baseline/SKILL.md` §logging — PII redaction
