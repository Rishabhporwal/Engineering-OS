---
name: grpc-buf
description: Brain's internal API protocol — gRPC over Protocol Buffers via buf for codegen (TS + Python). Auto-load whenever defining a new proto, adding a service method, generating clients, setting deadlines / streaming, handling errors. Proto files in protos/ are the SINGLE SOURCE OF TRUTH for all internal contracts AND for MCP tool schemas (which generate from the same protos to prevent drift).
---

# gRPC + buf — Brain's Internal API

Brain uses **gRPC over HTTP/2** for all service-to-service communication. **buf** is the toolchain for proto management + codegen.

**Canonical doc:** `docs/TECH/06_api_contracts.md`. This skill is operational.

## Why gRPC (not REST internal)

| Reason | Detail |
|---|---|
| Strong typing across TS + Python | Same `.proto` → both languages |
| Performance | Binary protocol; 5–10x lower latency than HTTP/JSON for internal calls |
| HTTP/2 multiplexing | Many concurrent calls over one connection |
| Deadlines built in | Every RPC has explicit timeout |
| Streaming | Server-streaming for live dashboard refresh + AI Chat agent reasoning |
| Single source of truth | MCP tool schemas generate from same `.proto` (no drift) |

## Repo layout

```
protos/
├── buf.yaml                      # buf config
├── buf.lock                      # dep lock
├── core/                          # core-service
│   ├── v1/
│   │   ├── workspace.proto
│   │   ├── members.proto
│   │   ├── goals.proto
│   │   ├── consent.proto
│   │   └── campaigns.proto
├── analytics/
│   ├── v1/
│   │   ├── metrics.proto
│   │   ├── waterfall.proto
│   │   ├── cascade.proto
│   │   ├── calendar.proto
│   │   ├── lifecycle.proto       # NAC / segments
│   │   └── pincode.proto
├── intelligence/
│   ├── v1/
│   │   ├── chat.proto
│   │   ├── insights.proto
│   │   ├── forecast.proto
│   │   ├── anomaly.proto
│   │   └── agents.proto          # ai.agent.invoke
├── lifecycle/
│   ├── v1/
│   │   ├── audience.proto
│   │   ├── outreach.proto
│   │   ├── call.proto
│   │   └── ticket.proto
├── notifications/
│   ├── v1/
│   │   ├── alerts.proto
│   │   ├── digests.proto
│   │   ├── exports.proto
│   │   └── push.proto
└── events/                        # Kafka event schemas (Avro)
    ├── integrations/
    │   ├── orders.v1.avsc
    │   ├── ads.v1.avsc
    │   ├── shipments.v1.avsc
    │   ├── refunds.v1.avsc
    │   └── customers.v1.avsc
    ├── operations/
    │   ├── settings_changed.v1.avsc
    │   └── workspace_changed.v1.avsc
    ├── analytics/
    │   ├── metrics_daily_materialized.v1.avsc
    │   └── customer_state_changed.v1.avsc
    ├── intelligence/
    │   ├── anomaly_detected.v1.avsc
    │   ├── insight_generated.v1.avsc
    │   └── morning_brief_generated.v1.avsc
    └── notifications/
        └── alert_fired.v1.avsc
```

## Proto standard

```proto
// protos/analytics/v1/metrics.proto
syntax = "proto3";
package brain.analytics.v1;

import "google/protobuf/timestamp.proto";

option go_package = "brain.com/protos/analytics/v1;analyticsv1";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc GetWaterfall(WaterfallRequest) returns (WaterfallResponse);
  rpc GetFirstProductCascade(CascadeRequest) returns (CascadeResponse);
  rpc GetCalendarReport(CalendarRequest) returns (CalendarResponse);
  rpc StreamLiveMetrics(LiveMetricsRequest) returns (stream LiveMetricsEvent);   // server-streaming
}

message GetDailyMetricsRequest {
  string workspace_id = 1;
  google.protobuf.Timestamp from = 2;
  google.protobuf.Timestamp to = 3;
  repeated string metric_names = 4;
  optional CustomerType customer_type = 5;
  optional string channel = 6;
}

enum CustomerType {
  CUSTOMER_TYPE_UNSPECIFIED = 0;
  ALL = 1;
  NEW = 2;
  RETURNING = 3;
}

message DailyMetricsResponse {
  repeated DailyMetricRow rows = 1;
}

message DailyMetricRow {
  string workspace_id = 1;       // echo for sanity
  google.protobuf.Timestamp date = 2;
  map<string, int64> metric_values_minor = 3;     // monetary in paisa
  map<string, double> metric_values_ratio = 4;     // MER, aMER, AOV ratios
}
```

Rules:
- Every request has `workspace_id` as field 1 (multi-tenancy)
- Monetary values in `int64` paisa, never `double`
- Enums: include `UNSPECIFIED = 0` (proto3 default)
- Field numbers never reused
- Use `optional` for nullable scalars (proto3 syntax)

## buf workflow

```bash
# buf.yaml
version: v1
breaking:
  use: [FILE]
lint:
  use: [DEFAULT]
deps:
  - buf.build/googleapis/googleapis

# generate
buf generate

# output:
#   packages/lib-grpc-clients/      (TS)
#   pylibs/brain_grpc/              (Python)
```

```yaml
# buf.gen.yaml
version: v1
plugins:
  - plugin: buf.build/grpc/node:v1.12.4
    out: packages/lib-grpc-clients/src
  - plugin: buf.build/protocolbuffers/python:v25.1
    out: pylibs/brain_grpc
  - plugin: buf.build/grpc/python:v1.62.1
    out: pylibs/brain_grpc
```

**`buf breaking` runs in CI** — rejects any breaking proto change to a deployed service.

## Server pattern

### Python (analytics-service, ingestion-service, intelligence-service, lifecycle-service Python)

```python
import grpc
from grpc import aio
from brain_grpc.analytics.v1 import metrics_pb2, metrics_pb2_grpc

class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    async def GetDailyMetrics(self, request, context):
        # Multi-tenant assertion
        if not request.workspace_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "workspace_id required")

        # Tenant check vs metadata
        auth_workspace_id = context.invocation_metadata().get("workspace_id")
        if auth_workspace_id != request.workspace_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace mismatch")

        rows = await self.repo.get_daily_metrics(
            workspace_id=request.workspace_id,
            from_dt=request.from_.ToDatetime(),
            to_dt=request.to.ToDatetime(),
            metric_names=list(request.metric_names),
        )
        return metrics_pb2.DailyMetricsResponse(rows=rows)
```

### Node (core-service, notifications-service)

```typescript
import { ServerUnaryCall } from '@grpc/grpc-js';
import { MetricsServiceService } from '@brain/lib-grpc-clients/analytics/v1';

const server = new Server();
server.addService(MetricsServiceService, {
  getDailyMetrics: async (call: ServerUnaryCall<GetDailyMetricsRequest, DailyMetricsResponse>, callback) => {
    const wsId = call.metadata.get('workspace_id')[0]?.toString();
    if (!wsId || wsId !== call.request.workspaceId) {
      callback({ code: status.PERMISSION_DENIED });
      return;
    }
    // ...
    callback(null, response);
  },
});
```

## Client pattern — deadlines on EVERY call

```typescript
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }, (err, response) => {
  if (err) {
    if (err.code === status.DEADLINE_EXCEEDED) { /* fallback */ }
  }
});
```

```python
response = await analytics_stub.GetDailyMetrics(request, timeout=1.0)
```

Default deadlines:
- Dashboard read path: 1s
- Cross-service join: 2s
- Heavy compute (waterfall, cascade): 5s
- Streaming subscription: per-message 30s

Never call without a deadline. A hanging downstream service hangs the entire tRPC fan-out.

## Error semantics

| gRPC code | When |
|---|---|
| `INVALID_ARGUMENT` | Malformed input (missing required field, bad enum value) |
| `PERMISSION_DENIED` | Tenant mismatch, scope failure |
| `NOT_FOUND` | Resource doesn't exist |
| `RESOURCE_EXHAUSTED` | Per-workspace rate limit |
| `FAILED_PRECONDITION` | State doesn't allow this op (e.g., DLT not registered) |
| `UNAVAILABLE` | Downstream service down (api-gateway retries with backoff) |
| `DEADLINE_EXCEEDED` | Timeout |

## Streaming patterns

### Server-streaming — for live dashboard refresh
```proto
rpc StreamLiveMetrics(LiveMetricsRequest) returns (stream LiveMetricsEvent);
```
api-gateway forwards to tRPC subscription → SSE / WebSocket to web/mobile.

### Bidi-streaming — for AI Chat agent reasoning
```proto
rpc Chat(stream ChatMessage) returns (stream ChatEvent);
```
Used by `intelligence-service.Chat` — Maya's agent streams intermediate tool calls + final response.

## MCP tools from proto (TECH/13 §4)

MCP tool schemas are generated from the same `.proto` to prevent drift:

```typescript
// generated from protos/lifecycle/v1/audience.proto by buf-mcp-plugin
export const buildAudienceTool = {
  name: 'lifecycle.audience.build',
  inputSchema: AudienceBuildRequestSchema.toJSONSchema(),
  outputSchema: AudienceBuildResponseSchema.toJSONSchema(),
};
```

Hand-writing MCP schemas = drift = production bugs.

## Auth metadata

Every gRPC call propagates auth via metadata:

```
authorization: Bearer <supabase-jwt>
workspace_id: <uuid>
trace_id: <uuid>
request_id: <uuid>
user_id: <uuid>          # if user-initiated; absent if agent-initiated
agent_id: <name>         # if agent-initiated
```

api-gateway sets these; downstream servers read + validate.

## Common failure modes

- **No deadline on client call** — hanging downstream hangs callers. Always set deadline.
- **Field number reuse** — wire-format breakage. Never reuse a number; mark deprecated.
- **Breaking change without version bump** — buf catches in CI. Don't bypass.
- **Hand-written MCP schema** — drifts from proto. Generate.
- **Missing `workspace_id` in request** — multi-tenancy hole. Required field 1.
- **gRPC errors not mapped at api-gateway** — tRPC client gets opaque "INTERNAL" code. Map gRPC status to user-meaningful HTTP / tRPC error.
- **Forgetting `optional` on nullable scalars** — proto3 distinguishes zero-value from missing only with `optional`. Detection: a "0" looks like "unset" downstream.

## References

- `docs/TECH/06_api_contracts.md` — canonical gRPC + tRPC + MCP contract details
- `docs/TECH/13_mcp_protocol.md` — MCP schemas generated from proto
- `skills/backend-fastify-trpc-grpc/SKILL.md` — Node gRPC server / client
- `skills/python-services/SKILL.md` — Python gRPC server / client (grpcio + grpcio-tools)
- `skills/mcp-protocol/SKILL.md` — MCP tool registration via decorator
