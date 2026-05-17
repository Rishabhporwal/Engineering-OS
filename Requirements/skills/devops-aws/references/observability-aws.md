# Observability on AWS — Deep Reference

The AWS-native observability triad: **CloudWatch + X-Ray + ADOT**.
Plus **Sentry** for application error tracking (best-in-class for that;
CloudWatch can't replace it).

## CloudWatch Logs

### Log group strategy
- One log group per service: `/ecs/<service>` (or `/aws/lambda/<fn>`)
- Retention by env: 7d local/dev, 30d staging, 90d prod, 1y for audit-relevant
- KMS encryption for any group with potential PII

```hcl
resource "aws_cloudwatch_log_group" "service" {
  name              = "/ecs/<service>"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.logs.arn
  tags              = local.tags
}
```

### Structured logs
Always JSON. CloudWatch Insights can query JSON natively.

```
fields @timestamp, level, traceId, tenantId, msg, duration_ms
| filter level = 'error'
| stats count() by traceId, msg
| sort count desc
| limit 50
```

Saved queries per service: store in `infra/cloudwatch-queries/<service>.json` and apply via Terraform.

### Log Insights cost
$0.005 per GB scanned. Watch out for "scan everything for the last 30 days" — bound queries with `@logStream` filters or shorter time ranges.

### Subscription filters → Lambda → S3 (long-term archive)
For audit logs you must retain >1y but query rarely:
- CloudWatch Logs subscription → Firehose → S3 (Glacier after 90d)
- Query via Athena with Glue catalog
- Cost: ~10x cheaper than CloudWatch retention beyond 1y

## CloudWatch Metrics

### Standard metrics (free)
ECS, ALB, RDS, ElastiCache, MSK, etc. all emit basic metrics. Use them.

### Custom metrics (paid: $0.30 per metric/mo)
Emit only what you'd alarm on or graph:
- Per-tenant request rate (high cardinality — use carefully)
- Business KPIs (orders/min, revenue/hour) — see business-context.md
- Per-route latency breakdowns

Use **EMF (Embedded Metric Format)** to emit metrics as part of normal log lines (no extra API call):

```typescript
import { Metrics, Unit } from '@aws-lambda-powertools/metrics'
const metrics = new Metrics({ namespace: '<App>/<Service>', serviceName: '<service>' })
metrics.addMetric('OrdersCreated', Unit.Count, 1)
metrics.addDimension('region', process.env.AWS_REGION!)
metrics.publishStoredMetrics()    // emits a structured log line that CloudWatch parses as metric
```

### Composite alarms
Reduce alarm noise. Page only when multiple signals agree:

```hcl
resource "aws_cloudwatch_composite_alarm" "service_unhealthy" {
  alarm_name          = "<service>-unhealthy"
  alarm_description   = "Service is unhealthy by multiple signals"
  alarm_rule = join(" AND ", [
    "ALARM(\"${aws_cloudwatch_metric_alarm.error_rate.alarm_name}\")",
    "ALARM(\"${aws_cloudwatch_metric_alarm.p95_latency.alarm_name}\")",
  ])
  alarm_actions = [aws_sns_topic.pagerduty.arn]
  ok_actions    = [aws_sns_topic.pagerduty_resolve.arn]
}
```

### SLO-based alarms (better than threshold-based)

Burn-rate alarms: page on SLO consumption, not raw thresholds.

For a 99.9% availability SLO over 30 days:
- Error budget: 43.2 minutes/month
- Fast-burn alarm: > 14.4× normal burn rate over 1h → page (would consume budget in 2 days)
- Slow-burn alarm: > 6× normal burn rate over 6h → ticket (would consume in 5 days)

```hcl
resource "aws_cloudwatch_metric_alarm" "slo_fast_burn" {
  alarm_name          = "<service>-slo-fast-burn"
  metric_query {
    id          = "burn_rate"
    expression  = "(errors / total) / (1 - 0.999) "      # normalized burn
    return_data = true
  }
  metric_query {
    id = "errors"
    metric {
      metric_name = "5XXError"
      namespace   = "AWS/ApplicationELB"
      period      = 3600
      stat        = "Sum"
      dimensions  = { TargetGroup = aws_lb_target_group.blue.arn_suffix }
    }
  }
  metric_query {
    id = "total"
    metric {
      metric_name = "RequestCount"
      namespace   = "AWS/ApplicationELB"
      period      = 3600
      stat        = "Sum"
      dimensions  = { TargetGroup = aws_lb_target_group.blue.arn_suffix }
    }
  }
  threshold           = 14.4
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  alarm_actions       = [aws_sns_topic.pagerduty.arn]
}
```

## X-Ray (distributed tracing)

### Enable for ECS
Sidecar pattern (X-Ray daemon) OR ADOT collector (preferred — also exports OTLP).

```json
// Add to task definition
{
  "name": "otel-collector",
  "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
  "essential": true,
  "command": ["--config=/etc/ecs/ecs-default-config.yaml"],
  "environment": [
    { "name": "AWS_REGION", "value": "<region>" }
  ]
}
```

App code uses OTel SDK → exports to localhost:4317 → ADOT forwards to X-Ray.

### Trace sampling
Sample 10% in prod. 100% in staging. Rules in X-Ray console or Terraform:

```hcl
resource "aws_xray_sampling_rule" "default" {
  rule_name      = "default"
  priority       = 9000
  reservoir_size = 1
  fixed_rate     = 0.1            # 10%
  service_name   = "*"
  service_type   = "*"
  host           = "*"
  http_method    = "*"
  url_path       = "*"
  resource_arn   = "*"
  version        = 1
}

# Sample 100% of /health and 5xx responses
resource "aws_xray_sampling_rule" "errors" {
  rule_name      = "errors-and-health"
  priority       = 8000
  reservoir_size = 1
  fixed_rate     = 1.0
  service_name   = "*"
  http_method    = "*"
  url_path       = "*"
  resource_arn   = "*"
  attributes     = { "http.status_code" = "5*" }
}
```

### Service Map
X-Ray's service map auto-renders dependencies. Annotate spans with custom attributes (`tenantId`, `featureFlag`) so you can filter the map.

## ADOT (AWS Distro for OpenTelemetry)

Use ADOT collector instead of X-Ray daemon when:
- You also send traces to Sentry / Tempo / Honeycomb
- You want to send custom metrics to Prometheus / Grafana Cloud
- You want vendor-neutrality

ADOT exports to: X-Ray, CloudWatch (logs + metrics), Prometheus, Tempo, Jaeger, OTLP-compatible vendors.

## Grafana

Self-host on ECS Fargate (small tasks) OR use **Amazon Managed Grafana** ($9/active editor/mo).

Connect to:
- CloudWatch (built-in plugin)
- AMP (Managed Prometheus) for high-cardinality metrics
- ClickHouse (for product analytics dashboards)

Dashboards as code: Terraform `grafana_dashboard` resource + JSON exports in `infra/grafana/`.

## Sentry (errors)

Best for: app-level exceptions, breadcrumbs, source map upload, release tracking.

Setup:
```typescript
import * as Sentry from '@sentry/node'
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.GIT_SHA,
  tracesSampleRate: 0.1,
  profilesSampleRate: 0.1,
  beforeSend(event) {
    delete event.request?.headers?.authorization
    return event
  },
})
```

Source maps: upload during CI build:
```bash
sentry-cli releases new $GIT_SHA
sentry-cli releases files $GIT_SHA upload-sourcemaps ./dist
sentry-cli releases finalize $GIT_SHA
```

Sentry → CloudWatch alarm:
- Configure Sentry Alert Rule: error rate > 50/min for 2 min
- Webhook → Lambda → CloudWatch metric → composite alarm

## Cost Snapshot (typical mid-sized prod)

| Service | Monthly cost |
|---|---|
| CloudWatch Logs (ingestion + storage) | $50-200 |
| CloudWatch Metrics (custom) | $30-100 |
| X-Ray | $5-30 (mostly sampling) |
| Container Insights | $50-150 |
| AMG / Grafana | $9-100 |
| Sentry (Team plan) | $26-200 |
| **Total** | **~$170-780** |

Tradeoffs:
- Reduce CloudWatch Logs by sampling INFO logs in prod (keep ERROR + WARN)
- Reduce Container Insights by using "default" tier instead of "enhanced"
- Increase X-Ray sample rate above 10% only for high-stakes services

## Anti-Patterns

- ❌ Logging at DEBUG level in prod — costs explode
- ❌ Per-tenant custom metrics in CloudWatch (high cardinality) — use a TS DB instead (AMP)
- ❌ One CloudWatch dashboard per developer — central + per-service only
- ❌ Alarms without an OK action — they latch into ALARM forever
- ❌ Alarms without runbook links — operators don't know what to do
- ❌ Tracing 100% in prod — use 10% sampling + force-sample errors
