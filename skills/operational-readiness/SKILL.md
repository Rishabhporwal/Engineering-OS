---
name: operational-readiness
description: Production-readiness checklist for every shippable service — root handler, four K8s health probes, port selection, real-network smoke, env validation, native-dep + build-output gotchas.
---

# Operational Readiness — the "won't look broken in production" checklist

Every shippable service must clear this before Vikram hands off and before Tanvi issues PASS. These rules exist because the team hit each in production-like tests. Cheap to satisfy, expensive to skip.

## 1. Root handler (`GET /`) is required, even for API-only services

A service that 404s on `GET /` looks "broken" to a human hitting the URL. `GET /` must return a minimal description page, a JSON `{"service","version","endpoints"}`, or a redirect to `/health`. Five lines that save 30 minutes of "is the server down?".

## 2. Health checks — four probe types (non-negotiable)

EKS / ALB / CloudFront all need health endpoints. Without working liveness + readiness probes the service can't deploy.

| Probe | Question | EKS action on failure | What to check |
|---|---|---|---|
| **Liveness** (`/health/live`) | Process responsive? | Restart pod | Process up, event loop unblocked, <100ms — **no external deps** |
| **Readiness** (`/health/ready`) | Can serve traffic? | Remove from Service endpoints | Postgres pool warm, ClickHouse reachable, ElastiCache connected, Kafka producer connected |
| **Startup** (`/health/live`) | Finished booting? | Delay liveness/readiness | First Prisma migration applied; proto codegen loaded; first ClickHouse query succeeds |
| **Deep** (`/health/deep`) | Upstream deps healthy? | Page on-call (alerting only) | Vendor APIs (Shopify, Meta, Google) + Anthropic reachable. Never gates traffic. |

### Fastify (Node — Vikram)

```typescript
class HealthChecker {
  constructor(private pg: Pool, private redis: Redis.Cluster, private kafka: Kafka) {}
  private async time<T>(fn: () => Promise<T>) {
    const t0 = Date.now();
    try { await fn(); return { status: 'healthy', latencyMs: Date.now() - t0 }; }
    catch (e) { return { status: 'unhealthy', error: (e as Error).message }; }
  }
  async readiness() {
    const [pg, rd, ch, kf] = await Promise.all([
      this.time(() => this.pg.query('SELECT 1')),
      this.time(() => this.redis.ping()),
      this.time(() => clickhouse.query({ query: 'SELECT 1', format: 'JSON' })),
      this.time(async () => { const a = this.kafka.admin(); await a.connect(); await a.disconnect(); }),
    ]);
    const checks = { postgres: pg, redis: rd, clickhouse: ch, kafka: kf };
    return { healthy: Object.values(checks).every(c => c.status === 'healthy'), checks };
  }
}
export const healthPlugin: FastifyPluginAsync = async (app) => {
  const hc = new HealthChecker(app.pg, app.redis, app.kafka);
  app.get('/health/live', async () => ({ status: 'ok', ts: new Date().toISOString() })); // no deps
  app.get('/health/ready', async (_, reply) => {
    const r = await hc.readiness();
    reply.code(r.healthy ? 200 : 503).send(r);   // 503 removes pod from LB
  });
  app.get('/health/deep', async () => hc.readiness()); // + vendor reachability; humans only
};
```

### FastAPI (Python — Maya)

```python
async def check(coro):
    t0 = time.time()
    try: await coro; return {"status": "healthy", "latency_ms": int((time.time()-t0)*1000)}
    except Exception as e: return {"status": "unhealthy", "error": str(e)}

@app.get("/health/live")
async def live(): return {"status": "ok", "ts": time.time()}  # no deps

@app.get("/health/ready")
async def ready(response: Response):
    pg, ch, kafka = await asyncio.gather(
        check(db.execute(text("SELECT 1"))), check(clickhouse.query("SELECT 1")), check(kafka_admin_ping()))
    checks = {"postgres": pg, "clickhouse": ch, "kafka": kafka}
    healthy = all(c["status"] == "healthy" for c in checks.values())
    response.status_code = 200 if healthy else 503
    return {"healthy": healthy, "checks": checks}
```

### EKS probe config (Jatin's CDK)

```yaml
livenessProbe:  { httpGet: { path: /health/live,  port: 3000 }, initialDelaySeconds: 15, periodSeconds: 10, failureThreshold: 3 }   # 30s → restart
readinessProbe: { httpGet: { path: /health/ready, port: 3000 }, initialDelaySeconds: 5,  periodSeconds: 10, failureThreshold: 2, timeoutSeconds: 3 }  # 20s → off LB
startupProbe:   { httpGet: { path: /health/live,  port: 3000 }, failureThreshold: 30, periodSeconds: 10 }  # 5 min cold migrations + cache warm
```

### Probe rules (lived failures)

- **Liveness MUST NOT depend on external services.** Postgres down ≠ container broken — liveness failing on Postgres restart-loops every container and makes the outage worse.
- **Readiness MUST check what the pod needs to serve.**
- **Return 200 healthy / 503 unhealthy** — anything else confuses K8s and the ALB.
- **Timeouts < probe period.**
- **`/health/*` is exempt from rate limiting and auth.**
- **Log readiness transitions** — every flap is a signal.
- **`/health/deep` is for humans, never the LB or autoscaler.**

### Composite alarm + auto-rollback (Jatin)

ArgoCD watches a CloudWatch composite alarm: readiness failure rate > 10% over 2 minutes → automatic rollback to the previous deployment.

```typescript
const compositeAlarm = new cloudwatch.CompositeAlarm(this, 'pod-readiness-composite', {
  alarmRule: cloudwatch.AlarmRule.allOf(apiGatewayReadinessAlarm, overallErrorRateAlarm),
});
```

## 3. Port selection — never hardcode, never assume :3000 is free

Read `PORT` from env (`Number(process.env.PORT ?? 0)` lets the OS pick a free port), and **log the actual bound port**. On `EADDRINUSE`, crash loudly — never silently retry on the next port. **Lived failure:** port 3000 was occupied by another dev service; ours crashed with `EADDRINUSE`; the test client hit :3000 and got a `307 → /login` from the OTHER service — looked like our app responding wrong. Mitigation: `lsof -i :$PORT` before binding, or bind to port 0 and read back.

## 4. Smoke test against a REAL listening server

In-process mocks (`app.request()`, FastAPI `TestClient`) skip the network stack — they miss port binding, TLS, HTTP/2, reverse-proxy quirks, timeouts, DNS. **Two layers:** (1) integration (fast, in-process, hot loop on every save); (2) smoke (slow, real network) — `spawn` the server on a real port, wait for "listening", then `curl GET /health` (200 + `status:ok`) and `GET /` (200, not 404). Run before PASS and in CI post-deploy. Templates in `testing-tdd` + canon/technical-requirements.md.

## 5. Native dependencies — declare the build trust list

For Node projects using `better-sqlite3`, `node-gyp` packages, `esbuild`, `sharp`, declare them in `package.json` → `pnpm.onlyBuiltDependencies` (an array). **pnpm 11 gotcha:** even with it declared, pre-flight `runDepsStatusCheck` may block with `[ERR_PNPM_IGNORED_BUILDS]` AND leave native binaries unbuilt while `pnpm install` reports success — **don't trust the install exit code.** Wire a `predev`/`pretest`/CI check that loops `onlyBuiltDependencies` and runs `node -e "require('$pkg')"`, failing with `pnpm rebuild $pkg`. Workarounds (Brain is pnpm-locked, do NOT adopt bun): `pnpm rebuild <pkg>` → run binary directly → `pnpm approve-builds` → `CI=true` → pin. Document in README.

## 5b. Don't rely on transitive dependencies you import directly

If it appears in an `import`/`require`, it appears in `dependencies`. **Lived failure:** a service imported `express`'s `json` middleware; CI smoke passed (transitive resolution worked) but production-like start threw `MODULE_NOT_FOUND: express`. Grep `src/` for the import on the way to PASS.

## 5c. Tests using ESM features need their own tsconfig

If tests use `import.meta.url` / top-level `await` while the app compiles to CommonJS, split configs: `tsconfig.json` (production, `module: commonjs`, excludes tests) and `tsconfig.test.json` (extends it, `module: esnext`, `moduleResolution: bundler`, `noEmit`, includes tests). Point `typecheck` at the test config.

## 5d. Non-TS runtime files must be declared in the build output

`tsc`/`esbuild`/`tsup`/`nest` don't copy `.sql`/`.proto`/`.yaml`/`.json` to `dist/` by default. Grep `src/` for runtime reads and confirm each is declared:

```bash
grep -rE "readFileSync|readFile|require\(['\"].*\.(sql|proto|yaml|yml|json|hbs|html|graphql)['\"]" services/<service>/src/
```

- **Node (tsup):** `esbuild-plugin-copy` step copying `src/**/*.sql`, `*.proto`, `*.yaml` into `dist/`.
- **Python (uv + hatch):** `[tool.hatch.build.targets.wheel.force-include]` the `materializations/` (`.sql`) + generated `proto/` dirs.
- Docker COPYs everything under `src/`, so the trap is compiled-only flows (npm publish, library wheels). **Lived failure:** `fs.readFileSync('./schema.sql')` worked in dev, broke at prod deploy with no `schema.sql` in `dist/`.

## 6. Env vars — fail fast, never silent

Validate every required var at startup and `process.exit(1)` listing what's missing. For optional vars (`SENTRY_DSN`, `CLICKUP_API_KEY`), log a single line naming what's degraded. Silent feature loss is the worst kind of bug.

## 7. README — minimum bar

One-line description, how to run locally, required env vars (example values, never real secrets), how to run tests, how to verify (curl + browser URL).

## 8. Logs at startup — print what matters

Three to five lines: what service, what version, where, what's enabled. Not a dump, not silence.

## The Vikram/Tanvi handoff checklist

Before Vikram says "done":
- [ ] `GET /` returns a real response (not 404); `GET /health` returns 200 with status JSON
- [ ] `PORT` env var works, default documented; crashes loudly on `EADDRINUSE`
- [ ] Required env vars validated at startup; optional vars log a single-line degradation notice
- [ ] Native deps in `pnpm.onlyBuiltDependencies` AND native-build check passes AND README notes the workaround
- [ ] Every package imported in `src/` appears in `dependencies` (no transitive borrowing)
- [ ] Non-TS runtime files declared in the build's asset config and verified present in `dist/`
- [ ] Test config and production tsconfig don't share ESM/CommonJS settings unless the app is one end-to-end
- [ ] Time-bucketed queries are tenant-timezone aware, not server-UTC (see `database-design` → Time + Timezones)
- [ ] Smoke test file runs the server on a real port; README has run + test + verify instructions
- [ ] **The service's own CI/CD pipeline exists** — `turbo --affected` GitHub Actions workflow + Dockerfile + its own ECR image + its own ArgoCD Application (base + staging/production overlays) + canary + auto-rollback — built WITH the service from day one. Retrofitting CI/CD later is forbidden.

Before Tanvi says PASS:
- [ ] All unit + integration tests pass
- [ ] **Smoke test against a real running server passes** (not just `app.request()`)
- [ ] `curl localhost:<PORT>/` returns something (not 404); `curl localhost:<PORT>/health` returns 200
- [ ] Server starts cleanly when PORT is set; crashes loudly when PORT is taken

If any is unchecked, the verdict is FAIL with the specific gap named.

## Anti-patterns explicitly forbidden

- ❌ "It works in tests" without ever `curl`'ing the running server
- ❌ Hardcoded port 3000 with no env var override
- ❌ Silent skip on missing optional env vars; or shipping a service whose `GET /` 404s with no body
- ❌ `pnpm install` succeeding but native binaries unbuilt (treat the warning as a real error)
- ❌ "We'll add the smoke test later" — later is never
- ❌ Liveness depending on Postgres/Redis/Kafka — cascading restart loops turn outages into 4-hour pages
- ❌ Returning 200 while a critical dependency is unreachable
- ❌ Skipping readiness "because the service is simple" — every Brain service has at least one dep
- ❌ Making `/health/deep` part of the LB or autoscaler decision

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Fastify probes | **Vikram** | |
| FastAPI probes | **Maya** | |
| EKS probe config + composite alarm | **Jatin** | canon/technical-requirements.md (SLOs + auto-rollback) |
| Probe failure → page-or-rollback tree | **Jatin** | canon/technical-requirements.md (incident playbook) |
| Pre-ship readiness sign-off | **Vikram** → **Tanvi** | this skill |

Related: `observability`, `devops-aws`, `testing-tdd`, `verification-before-completion`.
