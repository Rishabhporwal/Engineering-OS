---
name: backend-fastify-trpc-grpc
description: A Node backend stack (Fastify + tRPC + Prisma + grpc-js + Kafka + Zod) for the api-gateway and Node-side services. Locked-choice discipline + pre-handoff checklist.
---

# Backend (Node) — Fastify + tRPC + Prisma + gRPC

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the Node backend seam to different technology. The *patterns* here (one locked stack per layer, tenant-scoped procedures, deadlines on every gRPC call, audit-log middleware on write tools, real-network smoke) are what transfer, not the specific vendors.

Node-side stack for the **api-gateway and the Node-side services** (e.g. core, notifications, lifecycle orchestration). Owned by the Backend Engineer. The choices below are locked by `STACK.md` in this binding — no NestJS, no Apollo, no GraphQL.

## Stack invariants (this binding)
| Layer | Choice | Why |
|---|---|---|
| Runtime | Node 24 LTS | LTS = security patches |
| Framework | **Fastify** | 5K+ RPS/pod; small surface; good TS DX |
| Edge API | **tRPC** | type-safe end-to-end web+mobile; no codegen |
| Internal API | **gRPC** via `@grpc/grpc-js` + protos via `buf generate` | typing, multiplexing, deadlines, streaming |
| MCP surface | inside api-gateway, shares auth+tenancy+rate-limit | Canon |
| ORM | **Prisma 7** | type-safe, reliable migrations |
| Validation | **Zod** | tRPC + MCP input + DTO + env |
| Kafka | **@confluentinc/kafka-javascript** + a schema registry | client maintained under current Kafka |
| Cache | Redis via `ioredis` | rate limits, idempotency, hot metrics |
| Email / Push | provider SDKs (e.g. SES / Expo Push) | |
| Messaging | direct HTTP to the channel's Cloud API | Canon |
| PDF | headless Chromium + object storage | reports |
| Logs / Errors | **pino** JSON → log shipper → log store / error tracker | correlation |
| Tests | **Vitest** + Supertest + real-network smoke | mandatory smoke |

## Service skeleton (every Node service)
```typescript
// apps/<service>/src/main.ts
const app = Fastify({ logger: false, bodyLimit: 1024 * 1024, trustProxy: true });
await registerLogger(app);
await registerTracing(app);            // distributed tracing + AsyncLocalStorage: trace_id+request_id+tenant_id+user_id
await registerHealthRoutes(app);       // GET / + GET /health
await app.register(import('./auth'));  // JWT verification
await app.register(import('./trpc'), { prefix: '/trpc' });   // api-gateway only
await app.register(import('./mcp'),  { prefix: '/mcp' });    // api-gateway only
try { await app.listen({ port: config.PORT, host: '0.0.0.0' }); }
catch (err) { app.log.fatal({ err }, 'failed to bind'); process.exit(1); }
```
pino registered separately for correlation IDs; env Zod-validated at startup (`process.exit(1)` if missing).

## tRPC layer (api-gateway)
```typescript
const t = initTRPC.context<Context>().create();
export const router = t.router;
export const tenantProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.tenantId) throw new TRPCError({ code: 'UNAUTHORIZED', message: 'no tenant context' });
  return next({ ctx });
});
```
Every procedure uses `tenantProcedure` unless explicitly public.

## gRPC clients (codegen via buf)
```typescript
import { AnalyticsServiceClient } from 'grpc-clients/analytics';
export const analyticsClient = new AnalyticsServiceClient(process.env.ANALYTICS_SERVICE_GRPC_HOST!, credentials.createInsecure()); // mTLS via the service mesh in later phases
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }); // deadline on EVERY call
```

## MCP tool standard (api-gateway)
```typescript
export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build', scope: 'lifecycle:write',
  input: z.object({ tenant_id: z.string().uuid(), preview_only: z.boolean().default(true) }),
  output: z.object({ audience_id: z.string().uuid(), size: z.number().int(), projected_value_minor: z.number().int() }),
  handler: async (input, ctx) => { await requireScope('lifecycle:write', ctx); await requireTenant(input.tenant_id, ctx); return lifecycleClient.buildAudience(input); },
});
```
The MCP middleware auto-writes an audit-log entry for **every** write tool call where the Canon requires one (see `mcp-protocol`, `decision-log`).

## Prisma + RLS
Prisma models map snake_case (`@map`); composite PKs `@@id([tenantId, userId])`. Migrations create the RLS policy:
```sql
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenants USING (id = current_setting('app.tenant_id')::uuid);
```
Connection pool sets `app.tenant_id` on acquisition (see `data-layer`).

## Kafka producer (@confluentinc/kafka-javascript)
```typescript
await producer.send({ topic, messages: [{ key: event.tenant_id, value: await encodeAvro(topic, event), headers: { trace_id: getTraceId(), schema_version: '1' } }] });
```
Key MUST be the tenant key (partition + scope). See `event-driven-kafka`.

## Operational Readiness checklist (pre-handoff to QA)
- [ ] `GET /` returns `{service, version}`, not bare 404 · [ ] `GET /health` 200 with `{status, version, deps}` checking DB+Kafka+Redis
- [ ] `PORT` supported; crash on `EADDRINUSE` with clear log · [ ] env vars Zod-validated at startup
- [ ] logger correlation IDs (request_id+trace_id+tenant_id+user_id) · [ ] PII redaction at logger + shipper
- [ ] error tracker init; trace spans propagate · [ ] **real-network smoke** (`pnpm --filter <svc> smoke` spawns server + curls — never `fastify.inject()`)
- [ ] gRPC deadlines on every call · [ ] MCP write tools declare `scope` · [ ] audit-log middleware wired
- [ ] every Prisma query tenant-scoped; RLS test in `tests/security/`

## Common pitfalls
`fastify.inject()` for smoke (no real port — PASS requires real network) · gRPC without deadline (hangs the fan-out) · missing `requireTenant` (cross-tenant pull) · schema-breaking Kafka change (use additive evolution) · audit-log bypass (writing to an external API outside `mcpTool`) · missing tenant key in the Kafka envelope.

## References
`STACK.md` (the product's Node binding), HLD/LLD (gRPC+tRPC+MCP, Postgres+RLS+CDC, Kafka topology, MCP server) · `grpc-buf` · `mcp-protocol` · `event-driven-kafka` · `security-baseline` · `operational-readiness` · `data-layer`.
