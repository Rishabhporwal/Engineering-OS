---
name: health-check-endpoints
description: Health check endpoints for EKS liveness, readiness, and dependency probes. Use when wiring Fastify or FastAPI services for K8s, configuring ArgoCD auto-rollback triggers, or diagnosing probe failures, startup delays, dependency-down cascades, timeout misconfiguration.
---

# Health Check Endpoints

Implement K8s-style health checks so EKS pods are restarted when broken, removed from the LB when not ready, and ArgoCD rolls back automatically when the composite alarm fires.

## Probe Types

| Probe | Question | EKS action on failure | What to check in Brain |
|---|---|---|---|
| **Liveness** | Is the process responsive? | Restart pod | Process up, event loop not blocked, can produce a response in <100ms |
| **Readiness** | Can the pod serve traffic? | Remove from Service endpoints | Postgres pool warm, ClickHouse reachable, ElastiCache connected, Kafka producer connected |
| **Startup** | Has the app finished booting? | Delay liveness/readiness | First Prisma migration applied; proto codegen loaded; first ClickHouse query succeeds |
| **Deep** (separate endpoint) | Are upstream deps healthy? | Page on-call (alerting only) | Vendor APIs (Shopify, Meta, Google) reachable; Anthropic API reachable |

## Implementation (Fastify, Node services — Vikram)

```typescript
import { FastifyPluginAsync } from 'fastify';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { Kafka } from 'kafkajs';

interface CheckResult { status: 'healthy' | 'unhealthy'; latencyMs?: number; error?: string; }

class HealthChecker {
  constructor(
    private readonly pg: Pool,
    private readonly redis: Redis.Cluster,
    private readonly kafka: Kafka,
  ) {}

  private async time<T>(fn: () => Promise<T>): Promise<CheckResult> {
    const t0 = Date.now();
    try {
      await fn();
      return { status: 'healthy', latencyMs: Date.now() - t0 };
    } catch (err) {
      return { status: 'unhealthy', error: (err as Error).message };
    }
  }

  postgres()    { return this.time(() => this.pg.query('SELECT 1')); }
  redis_()      { return this.time(() => this.redis.ping()); }
  clickhouse()  { return this.time(() => clickhouse.query({ query: 'SELECT 1', format: 'JSON' })); }
  kafka_()      { return this.time(async () => { const a = this.kafka.admin(); await a.connect(); await a.disconnect(); }); }

  async readiness() {
    const [pg, rd, ch, kf] = await Promise.all([this.postgres(), this.redis_(), this.clickhouse(), this.kafka_()]);
    const checks = { postgres: pg, redis: rd, clickhouse: ch, kafka: kf };
    const healthy = Object.values(checks).every((c) => c.status === 'healthy');
    return { healthy, checks };
  }
}

export const healthPlugin: FastifyPluginAsync = async (app) => {
  const hc = new HealthChecker(app.pg, app.redis, app.kafka);

  // Liveness — no external deps, must respond instantly
  app.get('/health/live', async () => ({ status: 'ok', ts: new Date().toISOString() }));

  // Readiness — checks all critical deps; failure removes pod from LB
  app.get('/health/ready', async (_, reply) => {
    const r = await hc.readiness();
    reply.code(r.healthy ? 200 : 503).send(r);
  });

  // Deep — for on-call diagnostics only; never gates traffic
  app.get('/health/deep', async () => {
    const r = await hc.readiness();
    // ALSO check vendor reachability — does not affect status code
    const vendors = await Promise.all([
      hc.time(() => fetch('https://api.shopify.com/admin/api/2025-01/shop.json').then((r) => r.text())),
      hc.time(() => fetch('https://graph.facebook.com/v22.0/me').then((r) => r.text())),
    ]);
    return { ...r, vendors: { shopify: vendors[0], meta: vendors[1] } };
  });
};
```

## Implementation (FastAPI, Python services — Maya)

```python
from fastapi import FastAPI, Response
from sqlalchemy import text
import asyncio, time

app = FastAPI()

async def check(coro):
    t0 = time.time()
    try:
        await coro
        return {"status": "healthy", "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/health/live")
async def live():
    return {"status": "ok", "ts": time.time()}

@app.get("/health/ready")
async def ready(response: Response):
    pg, ch, kafka = await asyncio.gather(
        check(db.execute(text("SELECT 1"))),
        check(clickhouse.query("SELECT 1")),
        check(kafka_admin_ping()),
    )
    checks = {"postgres": pg, "clickhouse": ch, "kafka": kafka}
    healthy = all(c["status"] == "healthy" for c in checks.values())
    response.status_code = 200 if healthy else 503
    return {"healthy": healthy, "checks": checks}
```

## Kubernetes Configuration (EKS — Jatin's CDK)

```yaml
livenessProbe:
  httpGet: { path: /health/live, port: 3000 }
  initialDelaySeconds: 15      # let process settle
  periodSeconds: 10
  failureThreshold: 3          # 30s before restart

readinessProbe:
  httpGet: { path: /health/ready, port: 3000 }
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 2          # 20s before removed from LB
  timeoutSeconds: 3            # readiness checks must be fast

startupProbe:
  httpGet: { path: /health/live, port: 3000 }
  failureThreshold: 30         # 5 min to start (cold migrations + cache warm)
  periodSeconds: 10
```

## Best Practices

- **Liveness MUST NOT depend on external services.** Postgres down ≠ container broken. If liveness fails on Postgres down, K8s restart-loops every container and you make the outage worse.
- **Readiness MUST check what the pod needs to serve traffic.** Includes Postgres, ClickHouse (for analytics-service), Redis (for api-gateway sessions + rate limit), Kafka (for ingestion-service producers).
- **Return 200 for healthy, 503 for unhealthy.** Anything else (500, timeout) confuses K8s and the ALB.
- **Timeouts < probe period.** A 10s probe with a 30s timeout means a slow check holds the pod in undefined state.
- **Health endpoints are exempt from rate limiting and auth.** Configure the rate-limit plugin and Supabase Auth middleware to bypass `/health/*`.
- **Log readiness transitions** — every flap from healthy → unhealthy → healthy is a signal something is wrong with a dep.

## Composite alarm + auto-rollback (Jatin)

ArgoCD watches a CloudWatch composite alarm: readiness failure rate > 10% over 2 minutes triggers automatic rollback to the previous deployment. This is the safety net that lets the team ship multiple times per day without paging the Founder.

```hcl
# CDK / CloudWatch
const compositeAlarm = new cloudwatch.CompositeAlarm(this, 'pod-readiness-composite', {
  alarmRule: cloudwatch.AlarmRule.allOf(
    apiGatewayReadinessAlarm,
    overallErrorRateAlarm,
  ),
});
```

## Never Do

- Make liveness depend on Postgres / Redis / Kafka. Cascading restart loops are how outages turn into 4-hour pages.
- Return 200 while a critical dependency is unreachable. The LB will send real user traffic into the failure.
- Skip readiness checks because "the service is simple." Every Brain service has at least one dep (Postgres OR ClickHouse OR Kafka).
- Make `/health/deep` part of the LB or autoscaler decision. It exists for humans, not robots.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Fastify probes (api-gateway, core, notifications, lifecycle Node side) | **Vikram** | |
| FastAPI probes (ingestion, analytics, intelligence) | **Maya** | |
| EKS probe config + composite alarm | **Jatin** | canon/BRAIN_TECHNICAL.md (SLOs + auto-rollback) |
| Probe failure → page-or-rollback decision tree | **Jatin** | canon/BRAIN_TECHNICAL.md (incident playbook) |

Related Brain skills: `observability` (probe metrics), `devops-aws` (EKS + ArgoCD config), `operational-readiness` (pre-deploy smoke).
