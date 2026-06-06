# TECH/06 — API Contracts

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E1 (Tech Lead) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md)

This document specifies:
- The api-gateway external surface (tRPC over HTTPS)
- Internal gRPC service-to-service contracts (Protobuf)
- Kafka event schemas (Avro)
- Pagination, filtering, error conventions
- Auth, multi-tenancy, rate-limiting
- Versioning strategy

---

## 1. API Surface Topology

Brain exposes **three API surfaces** at the edge (tRPC + MCP + Public REST in Phase 4) plus internal gRPC + Kafka:

```
┌─────────────────────────────────────────────────────────────┐
│ EXTERNAL: Web + Mobile clients ↔ api-gateway                │
│   Clients: Next.js web, React Native (Expo) mobile app      │
│   Protocol: tRPC over HTTPS (JSON + superjson)              │
│   Auth: Supabase JWT in Authorization header                │
│   Type Safety: end-to-end via shared TS types               │
│   Streaming: SSE/WebSocket for AI Chat, live dashboards     │
│                                                              │
│   Mobile uses same router, same auth, same types.           │
│   No mobile-specific API surface — only additive endpoints  │
│   for push token registration + min-version check.          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ INTERNAL: api-gateway ↔ backend services                    │
│   Protocol: gRPC over HTTP/2 (Protobuf)                     │
│   Auth: AWS IAM (service-to-service via IAM roles)          │
│   mTLS: yes (Phase 2+ via service mesh)                     │
│   Schema: protos/ directory; buf for codegen                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EVENTS: services ↔ Kafka                                     │
│   Format: Avro (registered with Glue Schema Registry)       │
│   Topic naming: <domain>.<entity>.<event_type>.v<n>         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MCP: agent + external tool surface                          │
│   Protocol: MCP over HTTPS (Anthropic-style tool-use)       │
│   Auth: Supabase JWT OR brain_mcp_key (scoped)              │
│   Tools: memory.*, analytics.*, integrations.*,             │
│          lifecycle.*, ai.agent.*, core.*, decision_log.*    │
│   Use cases:                                                │
│     • Brain agents call each other (inter-agent)            │
│     • Anthropic Claude / OpenAI Assistants call Brain       │
│     • Future partner / Enterprise integrations              │
│   Detailed in TECH/13_mcp_protocol.md                       │
└─────────────────────────────────────────────────────────────┘
```

### Why This Split

- **tRPC at the edge:** frontend developers get type inference; one codebase
- **gRPC between services:** binary efficiency, streaming support, strong typing across TS + Python
- **Kafka for async state:** durable, replayable, decoupling

A public REST API (Phase 4+) will be a thin adapter over the api-gateway's tRPC routers.

---

## 2. External Surface: tRPC

### Router Hierarchy (Exposed by api-gateway)

```
appRouter
├── auth           # Supabase Auth orchestration
├── workspace      # Workspace metadata, members
├── settings       # Costs, goals, campaign tags
├── integrations   # OAuth flows, sync status
│
├── store          # Store Analytics dashboard
├── pnl            # P&L module
├── products       # Products + First Product Cascade
├── ltv            # LTV curves
├── cohorts        # Cohort heatmap
├── acquisition    # Acquisition + MER/aMER
├── customers      # NAC report
├── inventory      # Inventory
├── distributions  # Order value histograms
├── timing         # Time-between-orders
│
├── calendar       # Calendar Report
├── waterfall      # CM Waterfall
├── regional       # Region-specific endpoints (pincode, NDR, COD-economics)
├── goals          # Goal CRUD
├── actions        # Marketing actions log
├── alerts         # Alert feed + rules
│
├── ai             # Insights + Chat (streaming)
├── plan           # Plan Module forecasts
│
├── notifications  # Push token registration (mobile), in-app feed
├── app            # Mobile-app metadata: min supported version, feature flags
│
└── admin          # Brain team only
```

### Mobile-Specific Additions

The mobile app uses the same router as web. Only two additions exist for mobile-specific concerns:

```typescript
// apps/api-gateway/src/routers/notifications.ts
export const notificationsRouter = router({
  // ... existing in-app + alert rule endpoints ...

  registerPushToken: workspaceProcedure
    .input(z.object({
      pushToken: z.string(),
      platform: z.enum(['ios', 'android']),
      deviceId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      return await notificationsClient.registerPushToken({
        workspaceId: ctx.workspaceId,
        userId: ctx.auth.userId,
        ...input,
      }, { metadata: buildMetadata(ctx) });
    }),

  unregisterPushToken: workspaceProcedure
    .input(z.object({ deviceId: z.string() }))
    .mutation(async ({ ctx, input }) => {
      return await notificationsClient.unregisterPushToken({
        userId: ctx.auth.userId,
        deviceId: input.deviceId,
      }, { metadata: buildMetadata(ctx) });
    }),
});

// apps/api-gateway/src/routers/app.ts
export const appRouter_app = router({
  // Force-update enforcement
  minVersion: publicProcedure
    .input(z.object({ platform: z.enum(['ios', 'android']) }))
    .query(async ({ input }) => {
      const min = await coreClient.getMinSupportedAppVersion({ platform: input.platform });
      return { version: min.version, releasedAt: min.releasedAt };
    }),

  // Feature flags for mobile rollout
  featureFlags: workspaceProcedure
    .input(z.object({ platform: z.enum(['ios', 'android']) }))
    .query(async ({ ctx, input }) => {
      return await coreClient.getMobileFeatureFlags({
        workspaceId: ctx.workspaceId,
        platform: input.platform,
        version: ctx.clientVersion,
      });
    }),
});
```

Mobile and web differ in `User-Agent` header (mobile sends `Brain-Mobile/1.0.0 (ios)`) so api-gateway can apply mobile-specific rate limits or feature gates per call.

### Authentication

Every request must include `Authorization: Bearer <supabase_jwt>` header.

```typescript
// apps/api-gateway/src/middleware/auth.ts
import jwt from "jsonwebtoken";

export async function authMiddleware(req: FastifyRequest, ctx: Context): Promise<AuthContext> {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) throw new TRPCError({ code: 'UNAUTHORIZED' });

  const decoded = jwt.verify(token, SUPABASE_JWT_SECRET) as SupabaseJWTPayload;
  return {
    userId: decoded.sub,
    activeWorkspaceId: decoded.app_metadata.active_workspace_id,
    role: decoded.app_metadata.role,
    isAdmin: decoded.app_metadata.is_admin === true,
  };
}
```

### Procedure Tiers

```typescript
// apps/api-gateway/src/trpc/trpc.ts
import { initTRPC } from "@trpc/server";
import { z } from "zod";

const t = initTRPC.context<Context>().create();

export const publicProcedure = t.procedure;

export const authedProcedure = t.procedure.use(({ ctx, next }) => {
  if (!ctx.auth) throw new TRPCError({ code: "UNAUTHORIZED" });
  return next({ ctx: { ...ctx, auth: ctx.auth } });
});

export const workspaceProcedure = authedProcedure.use(({ ctx, next }) => {
  if (!ctx.auth.activeWorkspaceId) throw new TRPCError({ code: "FORBIDDEN" });
  return next({ ctx: { ...ctx, workspaceId: ctx.auth.activeWorkspaceId } });
});

export const ownerProcedure = workspaceProcedure.use(({ ctx, next }) => {
  if (ctx.auth.role !== 'owner') throw new TRPCError({ code: "FORBIDDEN" });
  return next();
});
```

### Multi-Tenant Context Propagation

api-gateway resolves `workspace_id` from JWT and propagates via gRPC metadata to downstream services:

```typescript
// apps/api-gateway/src/grpc/metricsClient.ts
import { Metadata } from "@grpc/grpc-js";

export function buildMetadata(ctx: WorkspaceContext): Metadata {
  const md = new Metadata();
  md.set('x-workspace-id', ctx.workspaceId);
  md.set('x-user-id', ctx.auth.userId);
  md.set('x-request-id', ctx.requestId);
  // IAM auth via AWS Sigv4 — handled by interceptor
  return md;
}

export async function getDailyMetrics(ctx, req) {
  return metricsClient.getDailyMetrics(req, { metadata: buildMetadata(ctx) });
}
```

### Common Conventions

#### Pagination (Cursor-Based for Large Sets)

```typescript
export const paginationInput = z.object({
  cursor: z.string().nullish(),
  limit: z.number().int().min(1).max(200).default(50),
});

export type PaginatedResponse<T> = {
  items: T[];
  nextCursor: string | null;
  hasMore: boolean;
};
```

#### Date Range Filter

```typescript
export const dateRangeInput = z.object({
  from: z.string().datetime(),
  to: z.string().datetime(),
  granularity: z.enum(["day", "week", "month", "quarter", "year"]).default("day"),
});
```

#### Error Codes (stable for frontend)

```typescript
throw new TRPCError({
  code: "BAD_REQUEST",
  message: "Goal value must be positive",
  cause: { code: "GOAL_VALUE_INVALID" }
});
```

Stable codes:
- `WORKSPACE_NOT_FOUND`
- `INTEGRATION_NOT_CONNECTED`
- `INTEGRATION_AUTH_EXPIRED`
- `GOAL_VALUE_INVALID`
- `CAMPAIGN_UNCLASSIFIED`
- `BUDGET_EXCEEDED`
- `RATE_LIMITED`
- `BACKEND_SERVICE_UNAVAILABLE`

#### Money Fields

All money is `bigint` minor units; `superjson` serializes preserving `bigint`. Currency code accompanies every monetary response field:

```typescript
{
  revenue_minor: 48_20_00_000n,
  revenue_currency: "INR",
  // or
  revenue_minor: 1_50_000n,
  revenue_currency: "USD",
}
```

### Example: store.kpis

```typescript
export const storeRouter = router({
  kpis: workspaceProcedure
    .input(dateRangeInput.extend({
      compareTo: z.enum(['previous_period', 'previous_year', 'none']).default('previous_period'),
    }))
    .query(async ({ ctx, input }) => {
      // Fan out to multiple downstream services in parallel
      const [metrics, goals, integrations] = await Promise.all([
        analyticsClient.getDailyMetricsSummary({
          workspaceId: ctx.workspaceId,
          dateFrom: input.from,
          dateTo: input.to,
          metricNames: STORE_KPI_METRICS,
        }, { metadata: buildMetadata(ctx) }),

        coreClient.listGoals({
          workspaceId: ctx.workspaceId,
          periodStart: startOfMonth(input.from),
        }, { metadata: buildMetadata(ctx) }),

        coreClient.listIntegrations({
          workspaceId: ctx.workspaceId,
        }, { metadata: buildMetadata(ctx) }),
      ]);

      return {
        current: metrics.current,
        previous: input.compareTo !== 'none' ? metrics.previous : null,
        delta: metrics.delta,
        goals: goals.goals,
        rag: computeRAG(metrics.current, goals.goals),
        integrationsHealthy: integrations.integrations.every(i => i.status === 'connected'),
      };
    }),
});
```

The frontend never sees the gRPC contract or the fan-out logic. It just calls `trpc.store.kpis.useQuery({ from, to })`.

---

## 3. Internal Surface: gRPC (Protobuf)

Source of truth: `protos/` directory. Codegen via `buf`.

### Service Contracts

```proto
// protos/core/workspace.proto
syntax = "proto3";

package brain.core.v1;
import "google/protobuf/timestamp.proto";

service WorkspaceService {
  rpc GetWorkspace(GetWorkspaceRequest) returns (Workspace);
  rpc ListMembers(ListMembersRequest) returns (ListMembersResponse);
  rpc ListIntegrations(ListIntegrationsRequest) returns (ListIntegrationsResponse);
  rpc ListGoals(ListGoalsRequest) returns (ListGoalsResponse);
  rpc UpsertGoal(UpsertGoalRequest) returns (Goal);
  // ...
}

message Workspace {
  string id = 1;
  string name = 2;
  string slug = 3;
  string home_region = 4;          // 'IN', 'US', 'GB', ...
  string default_currency = 5;     // 'INR', 'USD', ...
  string default_timezone = 6;
  string tier = 7;
  google.protobuf.Timestamp created_at = 8;
}
```

```proto
// protos/analytics/metrics.proto
syntax = "proto3";

package brain.analytics.v1;
import "google/protobuf/timestamp.proto";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc GetDailyMetricsSummary(GetDailyMetricsSummaryRequest) returns (DailyMetricsSummaryResponse);
  rpc GetCalendarReport(CalendarReportRequest) returns (CalendarReportResponse);
  rpc GetWaterfall(WaterfallRequest) returns (WaterfallResponse);
  rpc GetFirstProductCascade(FirstProductCascadeRequest) returns (FirstProductCascadeResponse);
  rpc GetCohortHeatmap(CohortHeatmapRequest) returns (CohortHeatmapResponse);
  rpc GetLifecycleReport(LifecycleReportRequest) returns (LifecycleReportResponse);
  rpc GetProductsTable(ProductsTableRequest) returns (ProductsTableResponse);
  rpc GetLTVCurves(LTVRequest) returns (LTVResponse);
  rpc DrillDown(DrillDownRequest) returns (DrillDownResponse);

  // Server streaming for live updates
  rpc StreamMetricUpdates(StreamMetricsRequest) returns (stream MetricUpdate);
}
```

```proto
// protos/intelligence/intelligence.proto
syntax = "proto3";

package brain.intelligence.v1;

service IntelligenceService {
  rpc GetForecast(GetForecastRequest) returns (ForecastResponse);
  rpc ListInsights(ListInsightsRequest) returns (ListInsightsResponse);
  rpc AcknowledgeInsight(AcknowledgeInsightRequest) returns (AcknowledgeInsightResponse);
  rpc GetPredictedLTV(GetPredictedLTVRequest) returns (PredictedLTVResponse);
  rpc GetBudgetRecommendation(BudgetRecommendationRequest) returns (BudgetRecommendationResponse);

  // Bidi streaming for AI Chat with tool use
  rpc Chat(stream ChatMessage) returns (stream ChatMessage);
}

message ChatMessage {
  oneof content {
    UserMessage user_message = 1;
    AssistantMessage assistant_message = 2;
    ToolCall tool_call = 3;
    ToolResult tool_result = 4;
  }
}
```

```proto
// protos/notifications/notifications.proto
syntax = "proto3";

package brain.notifications.v1;

service NotificationsService {
  rpc ListAlertRules(ListAlertRulesRequest) returns (ListAlertRulesResponse);
  rpc UpsertAlertRule(UpsertAlertRuleRequest) returns (AlertRule);
  rpc DeleteAlertRule(DeleteAlertRuleRequest) returns (DeleteAlertRuleResponse);
  rpc ListAlertEvents(ListAlertEventsRequest) returns (ListAlertEventsResponse);
  rpc AcknowledgeAlert(AcknowledgeAlertRequest) returns (AcknowledgeAlertResponse);
  rpc EnqueueExport(EnqueueExportRequest) returns (EnqueueExportResponse);
  rpc GetExportStatus(GetExportStatusRequest) returns (ExportJob);
}
```

```proto
// protos/integrations/integrations.proto
syntax = "proto3";

package brain.integrations.v1;

service IntegrationsService {
  rpc TriggerSync(TriggerSyncRequest) returns (TriggerSyncResponse);
  rpc GetSyncProgress(GetSyncProgressRequest) returns (SyncProgressResponse);
}
```

### Code Generation

```bash
# tools/codegen-proto.sh
buf generate protos/

# Produces:
#   packages/lib-grpc-clients/src/   (TypeScript clients for api-gateway)
#   pylibs/brain_grpc/                (Python servers + clients)
```

### gRPC Auth (Service-to-Service)

Two layers:

1. **AWS IAM (network-level):** EKS uses IAM Roles for Service Accounts (IRSA). Each pod has an IAM role. Service-to-service connections happen within the VPC; egress policies restrict cross-service connectivity to expected callers.

2. **mTLS (application-level, Phase 2+):** Once we adopt a service mesh (Istio or AWS App Mesh), every service-to-service call is mTLS-authenticated. Cert rotation handled by mesh.

### gRPC Metadata Propagation

Every gRPC call carries:

- `x-workspace-id` — tenant context
- `x-user-id` — for audit
- `x-request-id` — request tracing
- `x-traceparent` — W3C trace context (X-Ray)

Server-side middleware on every Python and Node service:

```python
# pylibs/brain_grpc/server.py
class TenancyInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        workspace_id = metadata.get('x-workspace-id')
        if not workspace_id:
            raise grpc.RpcError(grpc.StatusCode.UNAUTHENTICATED, "Missing x-workspace-id")
        # Set context
        set_current_workspace_id(workspace_id)
        return await continuation(handler_call_details)
```

---

## 4. Kafka Event Schemas (Avro)

Schemas registered with **AWS Glue Schema Registry**. Source files in `protos/events/`.

### Naming Convention

`<domain>.<entity>.<event_type>.v<n>`

Examples:
- `integrations.orders.v1`
- `integrations.shipments.v1`
- `operations.workspace.changed.v1`
- `analytics.metrics.daily_materialized.v1`
- `intelligence.insight.generated.v1`
- `notifications.alert.fired.v1`

### Standard Event Envelope

Every event has a common envelope:

```avro
{
  "type": "record",
  "name": "EventEnvelope",
  "fields": [
    {"name": "event_id", "type": "string"},
    {"name": "event_type", "type": "string"},
    {"name": "workspace_id", "type": "string"},
    {"name": "occurred_at", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "produced_at", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "producer_service", "type": "string"},
    {"name": "trace_id", "type": ["null", "string"], "default": null},
    {"name": "schema_version", "type": "string"},
    {"name": "payload", "type": "bytes"}                         // Avro-encoded payload
  ]
}
```

### Example: OrderEvent Payload

```avro
{
  "type": "record",
  "name": "OrderEventPayload",
  "namespace": "brain.events.integrations.v1",
  "fields": [
    {"name": "source_integration", "type": {"type": "enum", "name": "Integration",
      "symbols": ["SHOPIFY", "WOOCOMMERCE", "BIGCOMMERCE"]}},
    {"name": "source_record_id", "type": "string"},
    {"name": "order_event_type", "type": {"type": "enum", "name": "OrderEventType",
      "symbols": ["CREATED", "UPDATED", "REFUNDED", "CANCELLED"]}},
    {"name": "version", "type": "long"},
    {"name": "order_data", "type": {
      "type": "record",
      "name": "OrderData",
      "fields": [
        {"name": "customer_id", "type": ["null", "string"], "default": null},
        {"name": "customer_orders_count", "type": "int"},
        {"name": "created_at_source", "type": "long", "logicalType": "timestamp-millis"},
        {"name": "subtotal_minor", "type": "long"},
        {"name": "discount_minor", "type": "long"},
        {"name": "total_tax_minor", "type": "long"},
        {"name": "total_minor", "type": "long"},
        {"name": "currency_code", "type": "string"},
        {"name": "payment_method", "type": "string"},
        {"name": "financial_status", "type": "string"},
        {"name": "fulfillment_status", "type": "string"},
        {"name": "ship_country", "type": "string"},
        {"name": "ship_state", "type": ["null", "string"], "default": null},
        {"name": "ship_pincode", "type": ["null", "string"], "default": null},
        {"name": "line_items", "type": {"type": "array", "items": "LineItem"}}
      ]
    }}
  ]
}
```

### Schema Evolution Rules

- **Backward compatible by default:** new fields have defaults; consumers older than producers still work.
- **Breaking changes:** bump topic version (`.v1` → `.v2`). Producers write to both during migration. Consumers migrate to new topic over time.
- **Schema review:** every new/changed schema requires PR review by E1.

---

## 5. Rate Limiting

### Per-User / Per-Workspace Limits

Enforced at api-gateway in Redis:

| Tier | Per-User Limit | Per-Workspace Limit |
|------|---------------|---------------------|
| Standard read | 1,000 RPM | 5,000 RPM |
| Mutations | 100 RPM | 500 RPM |
| AI Chat messages | 50 RPM | 200 RPM |
| Exports | 5 concurrent | 20 concurrent |
| Public API (Phase 4) | tier-dependent | tier-dependent |

### Implementation

```typescript
// apps/api-gateway/src/middleware/rateLimit.ts
import { Ratelimit } from "@upstash/ratelimit";

const userLimiter = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(1000, "1 m"),
  prefix: "rl:user",
});

const workspaceLimiter = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(5000, "1 m"),
  prefix: "rl:workspace",
});

export async function checkRateLimits(ctx: WorkspaceContext) {
  const [userResult, wsResult] = await Promise.all([
    userLimiter.limit(ctx.auth.userId),
    workspaceLimiter.limit(ctx.workspaceId),
  ]);

  if (!userResult.success) {
    throw new TRPCError({ code: 'TOO_MANY_REQUESTS', cause: { code: 'RATE_LIMIT_USER' }});
  }
  if (!wsResult.success) {
    throw new TRPCError({ code: 'TOO_MANY_REQUESTS', cause: { code: 'RATE_LIMIT_WORKSPACE' }});
  }
}
```

### WAF Layer

CloudFront + WAF apply global rate limits:
- 10,000 RPM per IP (anti-abuse)
- Geographic rules (Phase 4)
- Bot detection (managed rule sets)

### Capacity Calculations

At 100k req/min sustained:
- 80% reads (cached): 80k RPM → minimal load
- 15% live queries: 15k RPM → analytics-service handles
- 5% mutations: 5k RPM → core-service handles

Per-pod throughput:
- api-gateway Node pod: ~500 RPS = 30k RPM
- 4 pods baseline = 120k RPM capacity, scales to 40 pods = 1.2M RPM at full HPA

---

## 6. Public API (Phase 4+)

A REST surface for programmatic consumers. Adapter pattern over tRPC routers.

```
GET /api/v1/workspaces/{workspace_id}/metrics/daily
  ?metric=mer,amer,revenue
  &from=2026-01-01
  &to=2026-01-31
  &granularity=day

Authorization: Bearer <api_token>
```

### API Tokens

```sql
CREATE TABLE api_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id),
  name TEXT NOT NULL,
  token_hash BYTEA NOT NULL,                   -- bcrypt of the token
  token_prefix TEXT NOT NULL,                  -- first 8 chars, visible in UI
  scope TEXT[] NOT NULL,                       -- read:metrics, write:goals, etc.
  rate_limit_tier TEXT NOT NULL DEFAULT 'starter',
  created_by UUID,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  last_used_at TIMESTAMPTZ
);
```

Tokens are issued once (shown to user once at creation), stored hashed. Used via `Authorization: Bearer brain_tk_<prefix>_<secret>`.

### Webhooks (Outbound)

For brands integrating Brain into their own systems:

```sql
CREATE TABLE outbound_webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL,
  url TEXT NOT NULL,
  secret TEXT NOT NULL,                        -- for HMAC signing
  events TEXT[] NOT NULL,                      -- ['alert.fired', 'insight.generated', 'export.completed']
  enabled BOOLEAN NOT NULL DEFAULT TRUE
);
```

Standard signed payload (HMAC SHA-256 of body with `secret`). Retried with exponential backoff (5 attempts).

---

## 7. Versioning

### tRPC (Internal Frontend Contract)

No versioning. Frontend and api-gateway deploy in lockstep. tRPC routes refactor freely.

### Public REST API (Phase 4+)

URL versioning: `/api/v1/`, `/api/v2/`. Breaking changes increment major version. Major versions supported for ≥12 months after deprecation announcement.

### gRPC Internal

Schema evolution via Protobuf field numbering (no breaking changes). New fields → new field numbers. Removed fields → reserved.

### Kafka Topics

Major version in topic name (`.v1`). Dual-write during migration; consumers migrate independently.

---

## 8. Error Handling

### Error Codes (Stable for Frontend)

```typescript
export const ERROR_CODES = {
  // Auth
  UNAUTHORIZED: 'UNAUTHORIZED',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',

  // Workspace
  WORKSPACE_NOT_FOUND: 'WORKSPACE_NOT_FOUND',
  WORKSPACE_INVITE_EXPIRED: 'WORKSPACE_INVITE_EXPIRED',

  // Integration
  INTEGRATION_NOT_CONNECTED: 'INTEGRATION_NOT_CONNECTED',
  INTEGRATION_AUTH_EXPIRED: 'INTEGRATION_AUTH_EXPIRED',
  INTEGRATION_RATE_LIMITED: 'INTEGRATION_RATE_LIMITED',

  // Data
  INSUFFICIENT_DATA: 'INSUFFICIENT_DATA',
  GOAL_VALUE_INVALID: 'GOAL_VALUE_INVALID',

  // System
  BACKEND_SERVICE_UNAVAILABLE: 'BACKEND_SERVICE_UNAVAILABLE',
  BUDGET_EXCEEDED: 'BUDGET_EXCEEDED',
  RATE_LIMIT_USER: 'RATE_LIMIT_USER',
  RATE_LIMIT_WORKSPACE: 'RATE_LIMIT_WORKSPACE',
};
```

### Downstream Service Errors

api-gateway translates gRPC status codes to tRPC errors:

```typescript
function grpcToTrpcError(err: grpc.ServiceError): TRPCError {
  switch (err.code) {
    case grpc.status.NOT_FOUND:
      return new TRPCError({ code: 'NOT_FOUND', cause: { code: 'WORKSPACE_NOT_FOUND', upstream: err.details }});
    case grpc.status.UNAVAILABLE:
      return new TRPCError({ code: 'INTERNAL_SERVER_ERROR', cause: { code: 'BACKEND_SERVICE_UNAVAILABLE' }});
    case grpc.status.RESOURCE_EXHAUSTED:
      return new TRPCError({ code: 'TOO_MANY_REQUESTS', cause: { code: 'RATE_LIMITED' }});
    default:
      Sentry.captureException(err);
      return new TRPCError({ code: 'INTERNAL_SERVER_ERROR' });
  }
}
```

---

## 9. Caching Strategy at the Gateway

api-gateway maintains an L1 cache for hot read paths:

```typescript
import { LRUCache } from "lru-cache";

const kpiCache = new LRUCache<string, KpiResponse>({
  max: 5000,
  ttl: 30_000,                                  // 30s
});

storeRouter.kpis.useQuery(input) → cache key based on (workspaceId, from, to, compareTo)
```

Cache invalidation on Kafka event `analytics.metrics.daily_materialized.v1` → api-gateway also subscribes and invalidates matching keys.

---

## 10. Streaming Endpoints

### AI Chat (Bidi SSE → gRPC)

```typescript
// apps/api-gateway/src/routers/ai.ts
import { observable } from "@trpc/server/observable";

export const aiRouter = router({
  chatStream: workspaceProcedure
    .input(z.object({
      conversationId: z.string().uuid().optional(),
      message: z.string().min(1).max(4000),
    }))
    .subscription(({ ctx, input }) => {
      return observable<ChatChunk>((emit) => {
        const stream = intelligenceClient.chat({ metadata: buildMetadata(ctx) });
        stream.write({ user_message: { content: input.message } });

        stream.on('data', (chunk: ChatMessage) => {
          emit.next(translateGrpcChunk(chunk));
        });
        stream.on('end', () => emit.complete());
        stream.on('error', (err) => emit.error(translateError(err)));

        return () => stream.end();
      });
    }),
});
```

Frontend uses tRPC `useSubscription` over WebSocket transport.

### Live Dashboard Updates (Phase 3)

```typescript
storeRouter.kpisLive.subscription(...)   // pushed via Kafka → api-gateway → WebSocket
```

Subscribes to `analytics.metrics.daily_materialized.v1` filtered by workspace.

---

## 11. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| GraphQL surface for power users? | E1 | Phase 5+. Single-frontend + small partner API doesn't justify it. |
| Internal API HTTP/JSON fallback? | E1 | No. gRPC only. Simplifies tooling. |
| API Gateway: Fastify or Hono? | E1 | Fastify (mature, well-typed). Hono if cold-start latency becomes important. |
| Tracing: AWS X-Ray native or OpenTelemetry? | E1 | OTel SDK with X-Ray exporter — vendor-portable. |
| Service mesh (Istio vs App Mesh)? | E1 | Defer to Phase 2. Istio is more featured; App Mesh is more AWS-native. |
| Stream backpressure handling? | E1 | gRPC supports it natively; tRPC subscription wraps. Manual cancellation on client disconnect. |
| Webhook signing scheme details? | E1 | Phase 4. HMAC SHA-256 + replay-protection nonce. |
