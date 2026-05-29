---
name: backend-fastify-trpc-grpc
description: Brain's Node backend stack (Fastify + tRPC + Prisma + grpc-js + Confluent Kafka + Zod) for api-gateway, core, notifications, lifecycle. Locked choices + pre-handoff checklist.
---

# Backend (Node) — Fastify + tRPC + Prisma + gRPC

Node-side stack for **api-gateway, core-service, notifications-service, lifecycle-service (Node orchestration)**. Owned by Vikram. Locked by `canon/technical-requirements.md` §4 — no NestJS, no Apollo, no GraphQL.

## Stack invariants
| Layer | Choice | Why |
|---|---|---|
| Runtime | Node 24 LTS | Node 20 EOL Apr 2026; LTS = security patches |
| Framework | **Fastify** | 5K+ RPS/pod; small surface; good TS DX |
| Edge API | **tRPC** | type-safe end-to-end web+mobile; no codegen |
| Internal API | **gRPC** via `@grpc/grpc-js` + protos via `buf generate` | typing, multiplexing, deadlines, streaming |
| MCP surface | inside api-gateway, shares auth+tenancy+rate-limit | canon |
| ORM | **Prisma 7** | type-safe, reliable migrations, Supabase-compatible; Rust engine dropped (smaller client) |
| Validation | **Zod** | tRPC + MCP input + DTO + env |
| Kafka | **@confluentinc/kafka-javascript** + Avro via Glue | KafkaJS abandoned/broken under Kafka 4.0 |
| Cache | Redis via `ioredis` | rate limits, idempotency, hot metrics |
| Email / Push | `@aws-sdk/client-sesv2` / `expo-server-sdk` | SES / Expo Push |
| WhatsApp | direct HTTP to Cloud API (Gupshup BSP) | canon |
| PDF | Playwright headless Chromium + S3 | investor reports |
| Logs / Errors | **pino** JSON → Fluent Bit → OpenSearch+CloudWatch / `@sentry/node` | correlation |
| Tests | **Vitest** + Supertest + real-network smoke | mandatory smoke |

## Service skeleton (every Node service)
```typescript
// apps/<service>/src/main.ts
const app = Fastify({ logger: false, bodyLimit: 1024 * 1024, trustProxy: true });
await registerLogger(app);
await registerTracing(app);            // X-Ray + AsyncLocalStorage: trace_id+request_id+workspace_id+user_id
await registerHealthRoutes(app);       // GET / + GET /health
await app.register(import('./auth'));  // Supabase JWT verification
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
export const workspaceProcedure = t.procedure.use(async ({ ctx, next }) => {
  if (!ctx.workspaceId) throw new TRPCError({ code: 'UNAUTHORIZED', message: 'no workspace context' });
  return next({ ctx });
});
```
Every procedure uses `workspaceProcedure` unless explicitly public.

## gRPC clients (codegen via buf)
```typescript
import { AnalyticsServiceClient } from 'brain-grpc-clients/analytics';
export const analyticsClient = new AnalyticsServiceClient(process.env.ANALYTICS_SERVICE_GRPC_HOST!, credentials.createInsecure()); // mTLS via App Mesh Phase 3+
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }); // deadline on EVERY call
```

## MCP tool standard (api-gateway)
```typescript
export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build', scope: 'brain:lifecycle:write',
  input: z.object({ workspace_id: z.string().uuid(), preview_only: z.boolean().default(true) }),
  output: z.object({ audience_id: z.string().uuid(), size: z.number().int(), projected_revenue_minor: z.number().int() }),
  handler: async (input, ctx) => { await requireScope('brain:lifecycle:write', ctx); await requireTenant(input.workspace_id, ctx); return lifecycleClient.buildAudience(input); },
});
```
The MCP middleware auto-writes a Decision Log entry for **every** write tool call (see `mcp-protocol`, `decision-log`).

## Prisma + RLS
Prisma models map snake_case (`@map`); composite PKs `@@id([workspaceId, userId])`. Migrations create the RLS policy:
```sql
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workspaces USING (id = current_setting('app.workspace_id')::uuid);
```
Connection pool sets `app.workspace_id` on acquisition (see `data-layer`).

## Kafka producer (@confluentinc/kafka-javascript)
```typescript
await producer.send({ topic, messages: [{ key: event.workspace_id, value: await encodeAvro(topic, event), headers: { trace_id: getTraceId(), schema_version: '1' } }] });
```
Key MUST be `workspace_id` (partition + scope). See `event-driven-kafka`.

## Operational Readiness checklist (pre-handoff to Tanvi)
- [ ] `GET /` returns `{service, version}`, not bare 404 · [ ] `GET /health` 200 with `{status, version, deps}` checking DB+Kafka+Redis
- [ ] `PORT` supported; crash on `EADDRINUSE` with clear log · [ ] env vars Zod-validated at startup
- [ ] logger correlation IDs (request_id+trace_id+workspace_id+user_id) · [ ] PII redaction at logger + Fluent Bit
- [ ] Sentry init; X-Ray spans propagate · [ ] **real-network smoke** (`pnpm --filter <svc> smoke` spawns server + curls — never `fastify.inject()`)
- [ ] gRPC deadlines on every call · [ ] MCP write tools declare `scope` · [ ] Decision Log middleware wired
- [ ] every Prisma query workspace-scoped; RLS test in `tests/security/`

## Common pitfalls
`fastify.inject()` for smoke (no real port — PASS requires real network) · gRPC without deadline (hangs the fan-out) · missing `requireTenant` (cross-tenant pull) · Avro schema-breaking change (use additive evolution) · Decision Log bypass (writing to an external API outside `mcpTool`) · missing `workspaceId` in Kafka envelope.

## References
`canon/technical-requirements.md` (gRPC+tRPC+MCP, Postgres+RLS+Debezium, Kafka topology, MCP server) · `grpc-buf` · `mcp-protocol` · `event-driven-kafka` · `security-baseline` · `operational-readiness` · `data-layer`.
