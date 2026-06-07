---
name: grpc-buf
description: An internal-API reference implementation — gRPC over Protobuf via buf (TS+Python codegen). The proto package is the single source of truth for internal contracts AND tool schemas.
---

# gRPC + buf — an Internal-API Reference Implementation

> **Reference implementation.** This skill documents one concrete binding of the internal-API seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology (REST+OpenAPI, GraphQL, etc.). The *patterns*
> here (contract-as-source-of-truth, codegen-no-drift, deadlines, tenant assertion) are what transfer.

gRPC over HTTP/2 for service-to-service calls; **buf** for proto management + codegen. Contract details live in the Product Canon's API/contract section (`STACK.md`, HLD/LLD).

## Why gRPC (not REST internal)
Strong typing across multiple languages from one `.proto` · binary, ~5–10x lower latency than HTTP/JSON · HTTP/2 multiplexing · built-in deadlines · server-streaming for live dashboards + chat · **tool schemas generate from the same `.proto` (no drift)**.

## Repo layout
`protos/` holds `buf.yaml` + `buf.lock` and one versioned package per service: e.g. `core/v1`, `analytics/v1`, etc. Async event schemas (`.avsc`) live under `protos/events/...`. Codegen → a TS client lib + a Python client lib.

## Proto standard
```proto
// protos/analytics/v1/metrics.proto
syntax = "proto3";
package product.analytics.v1;
import "google/protobuf/timestamp.proto";

service MetricsService {
  rpc GetDailyMetrics(GetDailyMetricsRequest) returns (DailyMetricsResponse);
  rpc StreamLiveMetrics(LiveMetricsRequest) returns (stream LiveMetricsEvent);  // server-streaming
}
message GetDailyMetricsRequest {
  string tenant_id = 1;                          // ALWAYS field 1 (tenant isolation)
  google.protobuf.Timestamp from = 2;
  optional CustomerType customer_type = 5;       // optional → distinguishes unset from zero
}
message DailyMetricRow {
  map<string, int64>  metric_values_minor = 3;   // monetary in minor units — never double
  map<string, double> metric_values_ratio = 4;   // ratio metrics
}
```
**Rules:** the tenant key is field 1 on every request · monetary = `int64` minor units never `double` · enums include `UNSPECIFIED = 0` · never reuse field numbers (mark deprecated) · `optional` for nullable scalars.

## buf workflow
`buf.yaml`: `breaking: { use: [FILE] }` + `lint: { use: [DEFAULT] }`; `buf.gen.yaml` lists the codegen plugins. `buf generate` regenerates every client lib. **`buf breaking` runs in CI and rejects breaking changes to a deployed service — don't bypass** (see `api-discipline`).

## Server pattern — assert tenant on every handler
```python
class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    async def GetDailyMetrics(self, request, context):
        if not request.tenant_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "tenant_id required")
        if context.invocation_metadata().get("tenant_id") != request.tenant_id:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "tenant mismatch")
        return await self.repo.get_daily_metrics(tenant_id=request.tenant_id, ...)
```
Node servers do the same via `call.metadata.get('tenant_id')` → `PERMISSION_DENIED` on mismatch. Scaffolds: `python-services` / `backend-fastify-trpc-grpc`.

## Client pattern — a deadline on EVERY call
```python
await analytics_stub.GetDailyMetrics(request, timeout=1.0)
```
```typescript
analyticsClient.getDailyMetrics(request, { deadline: Date.now() + 1000 }, cb);
```
Defaults: dashboard read 1s · cross-service join 2s · heavy compute 5s · streaming per-message 30s. **Never call without a deadline** — a hanging downstream hangs the whole fan-out.

## Error semantics
| Code | When |
|---|---|
| `INVALID_ARGUMENT` | malformed input |
| `PERMISSION_DENIED` | tenant mismatch / scope fail |
| `NOT_FOUND` | resource absent |
| `RESOURCE_EXHAUSTED` | per-tenant rate limit |
| `FAILED_PRECONDITION` | state disallows op (e.g. a required precondition not met) |
| `UNAVAILABLE` | downstream down (the gateway retries w/ backoff) |
| `DEADLINE_EXCEEDED` | timeout |
The edge gateway maps these to user-meaningful errors — never leak opaque `INTERNAL`.

## Streaming + tool schemas
Server-streaming (`returns (stream …)`): a live dashboard → the gateway forwards to a subscription → SSE/WS. Bidi (`Chat(stream…) returns (stream…)`): a chat service streams tool calls + final response. **Tool schemas (e.g. MCP) generate from the same `.proto`** via a codegen plugin — hand-writing them = drift = prod bugs.

## Auth metadata
Every call propagates `authorization: Bearer <jwt>`, the tenant key, `trace_id`, `request_id`, and `user_id` or `agent_id`. The edge gateway sets these; downstream reads + validates.

## Common failure modes
No deadline (hangs callers) · field-number reuse (wire breakage) · breaking change without version bump (`buf breaking` catches) · hand-written tool schema (drifts) · missing tenant key (tenancy hole) · unmapped gRPC errors at the gateway · forgetting `optional` on nullable scalars (`0` looks like unset).

## References
Product Canon API/contract section · `backend-fastify-trpc-grpc` (Node) · `python-services` (Python grpcio) · `mcp-protocol` (tool registration) · `api-discipline` (versioning + breaking gate).

## 2026 market update

- **Connect-RPC** (joined CNCF) is the browser/HTTP-friendly gRPC variant — production at Bluesky, Dropbox, PlanetScale, Redpanda — using the **same buf proto toolchain** as the single source of truth. Prefer it when a service needs both native gRPC and browser/HTTP clients without a separate gateway. `buf breaking` remains the contract-evolution CI gate.
