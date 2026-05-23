---
name: backend-fastify-trpc-grpc
description: Brain's Node backend stack. Auto-load whenever editing apps/api-gateway, apps/core-service, apps/notifications-service, or apps/lifecycle-service Node side; or whenever wiring Fastify routes, tRPC procedures, gRPC servers/clients, Prisma migrations, @confluentinc/kafka-javascript producers/consumers, MCP tool implementations, or Zod schemas. Covers Brain's locked Node tech choices (Fastify + tRPC + Prisma + grpc-js + @confluentinc/kafka-javascript + Zod) and the operational pre-handoff checklist.
---

# Backend (Node) — Fastify + tRPC + Prisma + gRPC

The Node-side stack for **api-gateway, core-service, notifications-service, lifecycle-service (Node orchestration)**. Owned by Vikram. Stack is locked by `canon/technical-requirements.md` §4 — no NestJS, no Apollo, no GraphQL.

## Stack invariants

| Layer | Choice | Why |
|---|---|---|
| Runtime | Node 24 LTS | Fastify v5 needs ≥18; Node 20 is EOL Apr 2026; LTS = stable security patches |
| Framework | **Fastify** | 5K+ RPS per pod; smaller surface than Express; better TS DX |
| Edge API | **tRPC** | Type-safe end-to-end (web + mobile); no codegen step |
| Internal API | **gRPC** via `@grpc/grpc-js` + protos from `protos/` via `buf generate` | Strong typing, multiplexing, deadlines, streaming |
| MCP surface | Inside api-gateway, sharing auth + multi-tenancy + rate-limit | canon/technical-requirements.md |
| ORM | **Prisma 7** | Type-safe queries; reliable migrations; Supabase Postgres-compatible. Prisma 7 dropped the Rust engine — smaller client + native edge runtime |
| Validation | **Zod** | tRPC + MCP input + DTO + env validation |
| Kafka | **@confluentinc/kafka-javascript** + Avro via Glue Schema Registry | Async backbone. KafkaJS is abandoned/broken under Kafka 4.0 — use Confluent's client (KafkaJS-compatible API) |
| Cache | Redis via `ioredis` | Rate limits, idempotency keys, hot metric cache |
| Email | `@aws-sdk/client-sesv2` | AWS SES |
| Push | `expo-server-sdk` | Expo Push API (APNS + FCM) |
| WhatsApp | Direct HTTP to Cloud API (Gupshup BSP) | canon/technical-requirements.md |
| PDF | Playwright headless Chromium + S3 | Investor reports |
| Logs | **pino** JSON | → Fluent Bit → OpenSearch + CloudWatch |
| Errors | `@sentry/node` | Trace + breadcrumb correlation |
| Tests | **Vitest** + Supertest + real-network smoke test | Mandatory smoke |

## Service skeleton (every Node service)

```typescript
// apps/<service>/src/main.ts
import Fastify from 'fastify';
import { config } from './config';     // Zod-validated env
import { registerLogger } from './logger';
import { registerTracing } from './tracing';
import { registerHealthRoutes } from './health';

const app = Fastify({
  logger: false,  // pino registered separately for correlation IDs
  bodyLimit: 1024 * 1024,
  trustProxy: true,
});

await registerLogger(app);
await registerTracing(app);              // X-Ray + AsyncLocalStorage for trace_id + request_id + workspace_id + user_id
await registerHealthRoutes(app);          // GET / + GET /health
await app.register(import('./auth'));     // Supabase JWT verification
await app.register(import('./trpc'), { prefix: '/trpc' });   // api-gateway only
await app.register(import('./mcp'), { prefix: '/mcp' });     // api-gateway only

const port = config.PORT;
try {
  await app.listen({ port, host: '0.0.0.0' });
} catch (err) {
  app.log.fatal({ err }, 'failed to bind');
  process.exit(1);
}
```

## tRPC layer (api-gateway)

```typescript
// apps/api-gateway/src/trpc/middleware.ts
import { initTRPC, TRPCError } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.context<Context>().create();
export const router = t.router;
export const procedure = t.procedure;

export const workspaceProcedure = procedure
  .use(async ({ ctx, next }) => {
    if (!ctx.workspaceId) {
      throw new TRPCError({ code: 'UNAUTHORIZED', message: 'no workspace context' });
    }
    return next({ ctx: { ...ctx, workspaceId: ctx.workspaceId } });
  });
```

Every tRPC procedure uses `workspaceProcedure` unless explicitly public.

## gRPC clients (codegen via buf)

```bash
buf generate
# produces packages/lib-grpc-clients/ (TS) + pylibs/brain_grpc/ (Python)
```

```typescript
// apps/api-gateway/src/grpc/clients.ts
import { credentials } from '@grpc/grpc-js';
import { AnalyticsServiceClient } from 'brain-grpc-clients/analytics';

export const analyticsClient = new AnalyticsServiceClient(
  process.env.ANALYTICS_SERVICE_GRPC_HOST!,
  credentials.createInsecure()  // mTLS via App Mesh in Phase 3+
);
```

Deadlines on every call:
```typescript
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 });
```

## MCP tool standard (api-gateway)

```typescript
// apps/api-gateway/src/mcp/tools/lifecycle.ts
import { z } from 'zod';
import { mcpTool } from '../decorator';

export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build',
  description: 'Build an RFM-triggered audience...',
  scope: 'brain:lifecycle:write',
  input: z.object({
    workspace_id: z.string().uuid(),
    segment_or_filter: z.union([z.enum(['champions','loyal',/* ... */]), CustomFilterSchema]),
    preview_only: z.boolean().default(true),
  }),
  output: z.object({
    audience_id: z.string().uuid(),
    size: z.number().int(),
    projected_response_rate: z.number(),
    projected_revenue_minor: z.number().int(),
    channel_mix: z.record(z.number()),
  }),
  handler: async (input, ctx) => {
    await requireScope('brain:lifecycle:write', ctx);
    await requireTenant(input.workspace_id, ctx);
    return await lifecycleClient.buildAudience(input);
  },
});
```

The MCP middleware automatically writes a Decision Log entry for **every** write tool call.

## Prisma + RLS

```prisma
// apps/core-service/src/prisma/schema.prisma
model workspace {
  id    String @id @default(uuid()) @db.Uuid
  name  String
  ...
}

model members {
  workspaceId String   @map("workspace_id") @db.Uuid
  userId      String   @map("user_id") @db.Uuid
  role        String

  workspace   workspace @relation(fields: [workspaceId], references: [id], onDelete: Cascade)
  @@id([workspaceId, userId])
  @@map("members")
}
```

Migration creates RLS policy:
```sql
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workspaces
  USING (id = current_setting('app.workspace_id')::uuid);
```

Connection pool sets `app.workspace_id` on acquisition.

## Kafka producer + consumer (@confluentinc/kafka-javascript)

```typescript
// apps/core-service/src/kafka/producer.ts
import { kafka } from '../lib/kafka';

export async function publishOperationsEvent(topic: string, event: any) {
  await producer.send({
    topic,
    messages: [{
      key: event.workspace_id,
      value: await encodeAvro(topic, event),
      headers: { trace_id: getTraceId(), schema_version: '1' },
    }],
  });
}
```

## Operational Readiness checklist (pre-handoff to Tanvi)

- [ ] `GET /` returns identifiable content (`{service, version}`), not bare 404
- [ ] `GET /health` returns 200 with `{status, version, deps}` — checks DB, Kafka, Redis
- [ ] `PORT` env var supported; crash on `EADDRINUSE` with clear log
- [ ] Required env vars validated at startup (Zod) — `process.exit(1)` if missing
- [ ] Logger has correlation IDs (request_id + trace_id + workspace_id + user_id)
- [ ] PII redaction at logger level + Fluent Bit Lua script
- [ ] Sentry initialized; X-Ray spans propagate
- [ ] Real-network smoke test — `pnpm --filter <service> smoke` spawns server + curls it (no `fastify.inject()`)
- [ ] gRPC client deadlines on every call
- [ ] MCP write tools all declare `scope`
- [ ] Decision Log middleware wired
- [ ] Multi-tenant: every Prisma query is workspace-scoped; RLS test in `tests/security/`

## Common pitfalls

- **`fastify.inject()` for smoke**: doesn't bind to a real port. PASS verdict requires real network. Use Supertest spawning the actual server.
- **gRPC without deadline**: a hanging downstream service hangs the entire tRPC fan-out. Always set a deadline.
- **Missing `requireTenant`**: an MCP tool that accepts `workspace_id` but doesn't assert membership lets one workspace pull another's data. The `requireTenant` check is non-negotiable.
- **Avro schema-breaking change**: renaming or removing fields breaks consumers. Use additive evolution.
- **Decision Log bypass**: writing to an external API directly without going through the `mcpTool({...})` path skips Decision Log. Always go through the decorator.
- **Forgetting `workspaceId` in Kafka envelope**: downstream can't partition or scope. Producer call MUST include it.

## References

- `canon/technical-requirements.md` — full gRPC + tRPC + MCP contract details
- `canon/technical-requirements.md` — MCP server design
- `canon/technical-requirements.md` — Postgres + RLS + Debezium
- `canon/technical-requirements.md` — Kafka topology
- `skills/grpc-buf/SKILL.md` — proto codegen workflow
- `skills/mcp-protocol/SKILL.md` — tool naming + auth scopes + Decision Log
- `skills/event-driven-kafka/SKILL.md` — MSK + Glue + Avro patterns
- `skills/security-baseline/SKILL.md` — Supabase Auth + RLS + Secrets Manager
- `skills/operational-readiness/SKILL.md` — pre-handoff checklist
