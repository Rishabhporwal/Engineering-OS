---
name: grpc-buf
description: Brain's internal API — gRPC over Protobuf via buf (TS+Python codegen). protos/ is the single source of truth for internal contracts AND MCP tool schemas.
---

# gRPC + buf — Brain's Internal API

gRPC over HTTP/2 for all service-to-service calls; **buf** for proto management + codegen. Canonical contract details: `canon/technical-requirements.md`.

## Why gRPC (not REST internal)
Strong typing across TS+Python from one `.proto` · binary, ~5–10x lower latency than HTTP/JSON · HTTP/2 multiplexing · built-in deadlines · server-streaming for live dashboard + AI Chat · **MCP tool schemas generate from the same `.proto` (no drift)**.

## Repo layout
`protos/` holds `buf.yaml` + `buf.lock` and one versioned package per service: `core/v1`, `analytics/v1`, `intelligence/v1`, `lifecycle/v1`, `notifications/v1`. Kafka Avro `.avsc` under `protos/events/{integrations,operations,analytics,intelligence,notifications}/`. Codegen → `packages/lib-grpc-clients/` (TS) + `pylibs/brain_grpc/` (Python).

## Proto standard
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
  string workspace_id = 1;                       // ALWAYS field 1 (multi-tenancy)
  google.protobuf.Timestamp from = 2;
  optional CustomerType customer_type = 5;       // optional → distinguishes unset from zero
}
message DailyMetricRow {
  map<string, int64>  metric_values_minor = 3;   // monetary in paisa — never double
  map<string, double> metric_values_ratio = 4;   // MER/aMER/AOV ratios
}
```
**Rules:** `workspace_id` is field 1 on every request · monetary = `int64` paisa never `double` · enums include `UNSPECIFIED = 0` · never reuse field numbers (mark deprecated) · `optional` for nullable scalars.

## buf workflow
`buf.yaml`: `breaking: { use: [FILE] }` + `lint: { use: [DEFAULT] }`; `buf.gen.yaml` lists TS+Python plugins. `buf generate` regenerates both libs. **`buf breaking` runs in CI and rejects breaking changes to a deployed service — don't bypass** (see `api-discipline`).

## Server pattern — assert tenant on every handler
```python
class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    async def GetDailyMetrics(self, request, context):
        if not request.workspace_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "workspace_id required")
        if context.invocation_metadata().get("workspace_id") != request.workspace_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace mismatch")
        return await self.repo.get_daily_metrics(workspace_id=request.workspace_id, ...)
```
Node servers do the same via `call.metadata.get('workspace_id')` → `PERMISSION_DENIED` on mismatch. Scaffolds: `python-services` / `backend-fastify-trpc-grpc`.

## Client pattern — a deadline on EVERY call
```python
await analytics_stub.GetDailyMetrics(request, timeout=1.0)
```
```typescript
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }, cb);
```
Defaults: dashboard read 1s · cross-service join 2s · heavy compute (waterfall, cascade) 5s · streaming per-message 30s. **Never call without a deadline** — a hanging downstream hangs the whole tRPC fan-out.

## Error semantics
| Code | When |
|---|---|
| `INVALID_ARGUMENT` | malformed input |
| `PERMISSION_DENIED` | tenant mismatch / scope fail |
| `NOT_FOUND` | resource absent |
| `RESOURCE_EXHAUSTED` | per-workspace rate limit |
| `FAILED_PRECONDITION` | state disallows op (e.g. DLT not registered) |
| `UNAVAILABLE` | downstream down (api-gateway retries w/ backoff) |
| `DEADLINE_EXCEEDED` | timeout |
api-gateway maps these to user-meaningful tRPC/HTTP errors — never leak opaque `INTERNAL`.

## Streaming + MCP
Server-streaming (`returns (stream …)`): live dashboard → api-gateway forwards to a tRPC subscription → SSE/WS. Bidi (`Chat(stream…) returns (stream…)`): `intelligence-service.Chat` streams tool calls + final response. **MCP tool schemas generate from the same `.proto`** via the buf-mcp plugin — hand-writing them = drift = prod bugs.

## Auth metadata
Every call propagates `authorization: Bearer <jwt>`, `workspace_id`, `trace_id`, `request_id`, and `user_id` or `agent_id`. api-gateway sets; downstream reads + validates.

## Common failure modes
No deadline (hangs callers) · field-number reuse (wire breakage) · breaking change without version bump (`buf breaking` catches) · hand-written MCP schema (drifts) · missing `workspace_id` (tenancy hole) · unmapped gRPC errors at api-gateway · forgetting `optional` on nullable scalars (`0` looks like unset).

## References
`canon/technical-requirements.md` · `backend-fastify-trpc-grpc` (Node) · `python-services` (Python grpcio) · `mcp-protocol` (tool registration) · `api-discipline` (versioning + breaking gate).
