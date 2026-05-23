---
name: api-versioning-strategy
description: API versioning across Brain's three surfaces — tRPC (web/mobile BFF), gRPC (internal services via buf), MCP tools (external partners + agent inter-comms). Deprecation timelines, the v1↔v2 reconciliation window during a legacy-tenant migration, safe vs breaking changes, sunset headers. Use when bumping a procedure/tool, when proto changes, when planning the v1 shutdown after migration completes.
---

# API Versioning Strategy

Brain has three contract surfaces, each with a slightly different versioning model:

1. **tRPC** (web/mobile BFF) — typed end-to-end; drift surfaces as TS build errors
2. **gRPC** between services (`.proto` via `buf`) — `buf breaking` enforces compatibility
3. **MCP tools** (see canon/technical-requirements.md) — external partners + agent inter-comms; tool name carries version

Plus the special case: **Brain v1 (legacy single-tenant at `{BRAIN_DOMAIN}`) ↔ Brain v2 (multi-tenant)** during a legacy single-tenant → multi-tenant migration.

## Why this matters for Brain

| Surface | Risk if versioning slips |
|---|---|
| tRPC | Web/mobile breaks for users on the old client; bad for releases that span > a deploy |
| gRPC | Service A starts; service B hasn't restarted yet → cross-service breakage during deploy |
| MCP tools | External partner (Anthropic Claude native, Enterprise tier) hits 4xx silently |
| v1↔v2 | a migrating brand sees inconsistent CM2 between the v1 and v2 dashboards during migration — the Founder loses trust |

## Versioning by surface

### 1. tRPC — additive-by-default, version on breaking

End-to-end typed inference is the protection. Drift surfaces as a CI build error.

**Safe changes (no version bump):**
- Adding optional fields to inputs (`z.string().optional()`)
- Adding fields to outputs (clients ignore unknown fields)
- Adding new procedures

**Breaking changes (route under `v2`):**
- Removing or renaming a field
- Changing a field's type
- Changing an enum's accepted values
- Adding a required input field
- Removing a procedure

For breaking changes, Brain's pattern is to add the new procedure alongside the old, deprecate the old, and remove it one release later:

```typescript
// apps/api-gateway/src/router/orders.ts
export const ordersRouter = router({
  list:   listV1Procedure,      // deprecated, returns Deprecation header
  listV2: listV2Procedure,      // new shape
});
```

```typescript
// Mark v1 deprecated in the response header
export const listV1Procedure = protectedProcedure
  .meta({ openapi: { deprecated: true } })
  .input(/* old shape */)
  .query(async ({ ctx }) => {
    ctx.res?.headers.set('Deprecation', 'true');
    ctx.res?.headers.set('Sunset', 'Wed, 01 Jul 2026 00:00:00 GMT');
    ctx.res?.headers.set('Link', '</api/trpc/orders.listV2>; rel="successor-version"');
    /* ... */
  });
```

### 2. gRPC (`.proto` via `buf`) — `buf breaking` is the gate

See `api-contract-testing` and `grpc-buf` skills. The discipline:

- **Never renumber a tag** (`= 5` → `= 7` is a break)
- **Never change a field's type** (`int32` → `int64` is a break)
- **Never remove a field** — mark `reserved` and add a new one
- **Always add new fields with new tag numbers**

For intentionally breaking changes (rare):
```protobuf
// New version is a new package — keep v1 alive alongside
package brain.analytics.v2;

service AnalyticsService {
  rpc GetWaterfall(GetWaterfallRequestV2) returns (GetWaterfallResponseV2);
}
```

The old v1 package stays registered for at least one minor release. The deprecation lifecycle below applies.

### 3. MCP tools — version in the name

```typescript
mcp.registerTool({
  name: 'analytics.waterfall.compute.v2',          // version explicit in name
  description: '...',
  inputSchema:  WaterfallV2Input,
  outputSchema: WaterfallV2Output,
  handler: /* ... */,
});

mcp.registerTool({
  name: 'analytics.waterfall.compute.v1',
  deprecated: true,                                // surfaces in tool catalog with warning
  description: 'DEPRECATED: use analytics.waterfall.compute.v2. Sunset: 2026-07-01.',
  inputSchema: WaterfallV1Input,
  // Translates v1 input → v2 internally
  handler: async (input, ctx) => mcp.invoke('analytics.waterfall.compute.v2', translateV1(input)),
});
```

External partner keys (Anthropic Claude native consumers, Enterprise tier) see the deprecation warning at tool-discovery time and can plan migration.

## Brain's deprecation timeline (canonical)

| Phase | Duration | Actions |
|---|---|---|
| **Deprecated** | 3 months minimum | Add `Deprecation: true` + `Sunset` headers on every response. Add tool `deprecated: true` flag for MCP. Update docs. Email Enterprise consumers. |
| **Sunset announced** | 2 months minimum (overlaps with deprecated) | Email all known consumers with the sunset date + migration guide. Surface a UI nudge in the web dashboard for any internal call site still on v1. |
| **Read-only** | 1 month | Reject mutating calls on v1 with 410 Gone. Read calls still work to give consumers a final window to export. |
| **Shutdown** | — | All calls return `410 Gone` with the migration guide URL. Code is removed in the next release. |

**Minimum overall window: 6 months from Deprecated → Shutdown.** Sooner only with all-Owner approval + Decision Log entries from every consuming workspace.

## Brain v1 ↔ v2 reconciliation (the special case)

A migrating legacy tenant is on **v1** (legacy single-tenant at `{BRAIN_DOMAIN}`) through end of Phase 1. Migration is **W14–16** (shadow → cutover). Tanvi runs **parity tests** during the shadow window — every dashboard metric must be within 1% on v1 and v2 (canon/technical-requirements.md). The window is:

- **W14:** v2 runs in shadow — the tenant's data flows into v1 AND v2; v1 is canonical
- **W15:** Tanvi runs reconciliation tests daily; Founder spot-checks dashboards
- **W16:** Cutover — v2 becomes canonical; v1 read-only; v1 shutdown follows the 6-month timeline above

Any v1↔v2 metric divergence above 1% blocks cutover.

## Response shape (canonical for tRPC + MCP)

```http
HTTP/1.1 200 OK
Content-Type: application/json
Deprecation: true                                                    ; on deprecated endpoints only
Sunset: Wed, 01 Jul 2026 00:00:00 GMT                                ; on deprecated endpoints
Link: </api/trpc/orders.listV2>; rel="successor-version"             ; on deprecated endpoints
```

```http
HTTP/1.1 410 Gone                                                    ; after sunset
Content-Type: application/json

{
  "error": "VERSION_SUNSET",
  "message": "This endpoint was sunset on 2026-07-01. Migrate to /api/trpc/orders.listV2.",
  "migration_url": "https://docs.{BRAIN_DOMAIN}/migrations/orders-v1-to-v2"
}
```

## Safe vs breaking changes (cheat-sheet)

**Safe (no version bump):**
- Adding optional input field
- Adding output field
- Adding new endpoint / new MCP tool
- Adding new gRPC message field with a new tag number
- Loosening a validation (e.g., string min-length 5 → 3)

**Breaking (new version):**
- Removing / renaming any field
- Changing a field's type
- Removing an enum value
- Adding a required input field
- Tightening validation (would reject previously-accepted inputs)
- Changing the meaning of a field while keeping the name (silent break — worst kind)

## Best Practices

- **Support N-1 minimum** — when v3 ships, v2 is still alive; v1 is gone
- **Provide ≥6 months migration window** (3 deprecated + 2 sunset announced + 1 read-only)
- **Monitor version usage** — TanStack Query dashboard logs which version each request uses; deprecation cadence is informed by real usage
- **Migration guides with code examples** — every breaking change ships with a `docs/migrations/<from>-to-<to>.md`
- **Internal first, external second** — migrate Brain's own callers (web BFF, mobile, internal services) to vN+1 BEFORE announcing the v1 sunset to external partners
- **Audit log every shutdown** — Decision Log row when a sunset endpoint actually starts returning 410

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| tRPC versioning + deprecation headers | **Vikram** | canon/technical-requirements.md (versioning) |
| gRPC `buf breaking` + package versions | **Aryan** + Vikram | `grpc-buf`, `api-contract-testing` |
| MCP tool versioning | **Vikram** + **Maya** | canon/technical-requirements.md (tool registry) |
| v1↔v2 reconciliation window | **Tanvi** + **Maya** | canon/technical-requirements.md (reconciliation) |
| Migration guide authorship | feature owner + **Priya** | `docs/migrations/` |
| Sunset audit log | **Vikram** | Decision Log |

Related Brain skills: `api-contract-testing` (the enforcement), `grpc-buf` (proto specifics), `mcp-protocol` (tool catalogue), `code-review` (PR-time check that breaking changes use new versions).
