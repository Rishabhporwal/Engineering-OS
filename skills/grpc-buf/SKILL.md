---
name: grpc-buf
description: Brain's internal API protocol — gRPC over Protocol Buffers via buf for codegen (TS + Python). Auto-load whenever defining a new proto, adding a service method, generating clients, setting deadlines / streaming, handling errors. Proto files in protos/ are the SINGLE SOURCE OF TRUTH for all internal contracts AND for MCP tool schemas (which generate from the same protos to prevent drift).
---

# gRPC + buf — Brain's Internal API

Brain uses **gRPC over HTTP/2** for all service-to-service communication. **buf** is the toolchain for proto management + codegen. This skill is operational; the canonical contract details are in `canon/technical-requirements.md`.

## Why gRPC (not REST internal)

| Reason | Detail |
|---|---|
| Strong typing across TS + Python | Same `.proto` → both languages |
| Performance | Binary; 5–10x lower latency than HTTP/JSON for internal calls |
| HTTP/2 multiplexing | Many concurrent calls over one connection |
| Deadlines built in | Every RPC has an explicit timeout |
| Streaming | Server-streaming for live dashboard refresh + AI Chat reasoning |
| Single source of truth | MCP tool schemas generate from the same `.proto` (no drift) |

## Repo layout

`protos/` holds `buf.yaml` + `buf.lock` and one versioned package per service: `core/v1` (workspace, members, goals, consent, campaigns), `analytics/v1` (metrics, waterfall, cascade, calendar, lifecycle, pincode), `intelligence/v1` (chat, insights, forecast, anomaly, agents), `lifecycle/v1` (audience, outreach, call, ticket), `notifications/v1` (alerts, digests, exports, push). Kafka event schemas (Avro `.avsc`) live under `protos/events/{integrations,operations,analytics,intelligence,notifications}/`. codegen lands in `packages/lib-grpc-clients/` (TS) and `pylibs/brain_grpc/` (Python).

## Proto standard (one representative file)

```proto
// protos/analytics/v1/metrics.proto
syntax = "proto3";
package brain.analytics.v1;
import "google/protobuf/timestamp.proto";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc StreamLiveMetrics(LiveMetricsRequest) returns (stream LiveMetricsEvent);  // server-streaming
}

message GetDailyMetricsRequest {
  string workspace_id = 1;                          // ALWAYS field 1 (multi-tenancy)
  google.protobuf.Timestamp from = 2;
  google.protobuf.Timestamp to = 3;
  repeated string metric_names = 4;
  optional CustomerType customer_type = 5;          // optional → distinguishes unset from zero
}

message DailyMetricRow {
  string workspace_id = 1;                          // echo for sanity
  map<string, int64>  metric_values_minor = 3;      // monetary in paisa — never double
  map<string, double> metric_values_ratio = 4;      // MER, aMER, AOV ratios
}
```

**Rules:** `workspace_id` is field 1 on every request; monetary values are `int64` paisa, never `double`; enums include `UNSPECIFIED = 0`; field numbers are never reused (mark deprecated instead); use `optional` for nullable scalars.

## buf workflow

`buf.yaml` sets `breaking: { use: [FILE] }` + `lint: { use: [DEFAULT] }`; `buf.gen.yaml` lists the TS + Python gRPC plugins. `buf generate` regenerates both client libs. **`buf breaking` runs in CI and rejects any breaking proto change to a deployed service — don't bypass it.**

## Server pattern — assert tenant on every handler

Every handler validates `workspace_id` is present AND matches the call metadata before doing work. Python representative:

```python
class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    async def GetDailyMetrics(self, request, context):
        if not request.workspace_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "workspace_id required")
        if context.invocation_metadata().get("workspace_id") != request.workspace_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace mismatch")
        rows = await self.repo.get_daily_metrics(workspace_id=request.workspace_id, ...)
        return metrics_pb2.DailyMetricsResponse(rows=rows)
```

The Node servers (core-service, notifications-service) do the same check via `call.metadata.get('workspace_id')` → `PERMISSION_DENIED` on mismatch. Full server + client scaffolds: `python-services` / `backend-fastify-trpc-grpc`.

## Client pattern — a deadline on EVERY call

```python
response = await analytics_stub.GetDailyMetrics(request, timeout=1.0)
```
```typescript
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }, cb);
```

Default deadlines: dashboard read 1s; cross-service join 2s; heavy compute (waterfall, cascade) 5s; streaming per-message 30s. **Never call without a deadline** — a hanging downstream hangs the entire tRPC fan-out.

## Error semantics

| gRPC code | When |
|---|---|
| `INVALID_ARGUMENT` | Malformed input (missing required field, bad enum) |
| `PERMISSION_DENIED` | Tenant mismatch, scope failure |
| `NOT_FOUND` | Resource doesn't exist |
| `RESOURCE_EXHAUSTED` | Per-workspace rate limit |
| `FAILED_PRECONDITION` | State doesn't allow the op (e.g., DLT not registered) |
| `UNAVAILABLE` | Downstream down (api-gateway retries with backoff) |
| `DEADLINE_EXCEEDED` | Timeout |

api-gateway maps these to user-meaningful tRPC/HTTP errors — never leak an opaque `INTERNAL` to the client.

## Streaming + MCP

- **Server-streaming** (`returns (stream …)`): live dashboard refresh — api-gateway forwards to a tRPC subscription → SSE/WebSocket.
- **Bidi-streaming** (`rpc Chat(stream …) returns (stream …)`): `intelligence-service.Chat` — Maya's agent streams intermediate tool calls + final response.
- **MCP tool schemas generate from the same `.proto`** (via the buf-mcp plugin → `inputSchema`/`outputSchema` JSON Schema). Hand-writing MCP schemas = drift = production bugs (canon/technical-requirements.md).

## Auth metadata

Every gRPC call propagates: `authorization: Bearer <jwt>`, `workspace_id`, `trace_id`, `request_id`, `user_id` (if user-initiated) or `agent_id` (if agent-initiated). api-gateway sets these; downstream servers read + validate.

## Common failure modes

- **No deadline on client call** — hanging downstream hangs callers. Always set one.
- **Field number reuse** — wire-format breakage. Never reuse; mark deprecated.
- **Breaking change without version bump** — `buf breaking` catches in CI. Don't bypass.
- **Hand-written MCP schema** — drifts from proto. Generate.
- **Missing `workspace_id` in request** — multi-tenancy hole. Required field 1.
- **gRPC errors not mapped at api-gateway** — client gets opaque `INTERNAL`. Map status → meaningful error.
- **Forgetting `optional` on nullable scalars** — a `0` looks like "unset" downstream.

## References

- `canon/technical-requirements.md` — canonical gRPC + tRPC + MCP contract details, MCP schemas from proto
- `skills/backend-fastify-trpc-grpc/SKILL.md` — Node gRPC server / client
- `skills/python-services/SKILL.md` — Python gRPC server / client (grpcio + grpcio-tools)
- `skills/mcp-protocol/SKILL.md` — MCP tool registration
