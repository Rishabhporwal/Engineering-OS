---
name: api-contract-testing
description: Contract testing for Brain's gRPC (buf-generated protos), tRPC (Zod inferred), and MCP (tool schemas) surfaces — Pact for service-to-service, buf breaking for proto, schema-version checks for MCP, OpenAPI/JSON-Schema fallback. Use when changing a .proto, when adding/modifying an MCP tool, when bumping a tRPC procedure, when an integration breaks across the TS↔Python boundary, or to verify backward compatibility before deploy.
---

# API Contract Testing

Brain has three contract surfaces:

1. **gRPC** between services (`.proto` files compiled via `buf` to TS + Python — see `grpc-buf` skill)
2. **tRPC** for the web/mobile BFF (Zod-inferred end-to-end types)
3. **MCP tools** for agent inter-comms + external partners (see canon/BRAIN_TECHNICAL.md)

A breaking change in any of these silently propagates: Maya ships a new `OrderEvent.timestamp_field` rename, the analytics-service stops materializing, the dashboard MER value drops to zero, and the Founder notices three days later. Contract testing is the structural alternative to "we'll review carefully."

## Key concepts

| Term | Definition |
|---|---|
| Consumer | Service that calls the API |
| Provider | Service that exposes it |
| Contract | Agreed request/response format |
| Pact | Consumer-driven contract testing tool |
| Schema | Structure definition (proto, Zod, JSON Schema) |
| Broker | Central repo for contracts (Pact Broker on AWS, or Pactflow SaaS) |

## Three surfaces, three approaches

### 1. gRPC contracts — `buf breaking`

Brain's gRPC contracts are the `.proto` files in the monorepo. `buf` is the source of truth.

```bash
# Generate TS + Python code from .proto
buf generate

# Lint protos (style, naming, package conventions)
buf lint

# Check for breaking changes vs main
buf breaking --against '.git#branch=main'
```

**`buf breaking` is the gate** on every PR that touches `protos/`. CI fails if a PR removes a field, changes a type, or renumbers a tag — all of which break clients in-flight.

```yaml
# .github/workflows/proto.yml
- name: Buf lint + breaking check
  uses: bufbuild/buf-action@v1
  with:
    breaking_against: '.git#branch=main,subdir=protos'
```

For intentionally-breaking changes (rare; usually a `v1` → `v2` package bump), the PR description must call out the migration plan and the deprecated v1 stays alongside v2 for one minor release.

### 2. tRPC contracts — Zod inference + version gates

tRPC's appeal is end-to-end typed inference — the web client and the api-gateway server share types. Drift surfaces as a TypeScript build error in CI. That's most of the protection you need.

The remaining gap: when the **same procedure** changes its output shape between two deploys (web deploys before api-gateway, or vice versa). Cover this with:

- **Forward compat:** new optional fields added to the response are fine (Zod `.optional()`).
- **Removing/renaming fields:** treat as a breaking change. Add the new field, deploy both, wait one release, then remove.
- **`.strict()` on inputs only.** Outputs should be `.passthrough()` (extra fields are OK; missing required is a bug).

### 3. MCP tool contracts (canon/BRAIN_TECHNICAL.md)

MCP tools are versioned via the tool name + schema version. External partners (Anthropic Claude native, Enterprise tier customers) consume these.

```typescript
// MCP tool registration (in api-gateway)
mcp.registerTool({
  name: 'analytics.waterfall.compute.v2',          // include version in name for clarity
  description: '...',
  inputSchema: WaterfallV2Input,                    // Zod schema, .strict()
  outputSchema: WaterfallV2Output,
  handler: async (input, ctx) => { /* ... */ },
});

// v1 stays registered for backward compat for at least 1 release
mcp.registerTool({
  name: 'analytics.waterfall.compute.v1',
  // marked deprecated; redirects internally to v2 with translation
  deprecated: true,
  ...
});
```

For breaking changes to MCP tool inputs/outputs, **never edit in place** — register a new `vN+1` and deprecate the old.

## Pact (consumer-driven contracts) for cross-language service calls

When Maya's Python `ingestion-service` calls Vikram's Node `core-service` over gRPC, the `.proto` covers the wire format but NOT the *semantic contract* ("when I call `CreateOrder` with `currency=INR`, you store `gst_excluded = round(amount * 100/118)`"). Pact captures that.

```typescript
// Consumer test (core-service consumer of intelligence-service)
import { PactV3, MatchersV3 } from '@pact-foundation/pact';

const provider = new PactV3({ consumer: 'core-service', provider: 'intelligence-service' });

describe('intelligence.morning_brief.generate contract', () => {
  it('returns three signals for a workspace with active integrations', async () => {
    await provider
      .given('workspace has Shopify+Meta connected and 7d of data')
      .uponReceiving('a request to generate brief for 2026-05-13')
      .withRequest({
        method: 'POST',
        path: '/v1/morning_brief/generate',
        body: { workspace_id: '...', date: '2026-05-13' },
      })
      .willRespondWith({
        status: 200,
        body: MatchersV3.like({
          brief_id: MatchersV3.uuid(),
          signals: MatchersV3.eachLike(
            { headline: MatchersV3.string(), severity: MatchersV3.string() },
            { min: 3 },                            // at least 3 signals
          ),
        }),
      })
      .executeTest(async (mockServer) => {
        const r = await fetch(`${mockServer.url}/v1/morning_brief/generate`, { /* ... */ });
        expect(r.status).toBe(200);
      });
  });
});
```

```typescript
// Provider verification (intelligence-service)
import { Verifier } from '@pact-foundation/pact';

new Verifier({
  provider: 'intelligence-service',
  providerBaseUrl: 'http://localhost:3000',
  pactBrokerUrl: process.env.PACT_BROKER_URL,
  publishVerificationResult: true,
  providerVersion: process.env.GIT_SHA,
  stateHandlers: {
    'workspace has Shopify+Meta connected and 7d of data': async () => {
      await seedDb({ /* ... */ });
    },
  },
}).verifyProvider();
```

## OpenAPI / JSON Schema (only the external read-only surface)

Brain's external API surface is mostly tRPC + MCP. For partner integrations that need OpenAPI (e.g., Enterprise customers writing their own client), generate an OpenAPI doc from the tRPC schemas using `trpc-to-openapi` and gate on schema validation in middleware.

## Best practices

**Do:**
- Test from the consumer's perspective
- Use matchers (`MatchersV3.like`, `eachLike`) for flexible matching
- Validate structure, not specific values
- Version every contract explicitly
- Test error responses too (404, 409, 429, 503 paths)
- Run `buf breaking` in CI on every proto change
- Run Pact verification in CI on every provider change
- Test backward compatibility on every minor release

**Don't:**
- Hard-code business-logic values in contracts (those are integration tests' job)
- Skip error-scenario coverage
- Edit gRPC tags in-place (always add new tags; deprecate the old)
- Edit MCP tool schemas in-place (register vN+1)
- Deploy without Pact verification result

## Brain CI gates (canonical)

| PR touches | Gate |
|---|---|
| `protos/**` | `buf lint`, `buf breaking --against main`, `buf generate` clean |
| `apps/web/**` + `apps/mobile/**` tRPC clients | TypeScript build (Zod inference) |
| Service code (any) | Pact verifier against published consumer contracts |
| MCP tool registry change | MCP schema diff check; no in-place edits |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| `.proto` contracts + `buf` | **Aryan** + Vikram | canon/BRAIN_TECHNICAL.md (contracts), `grpc-buf` skill |
| Pact broker config | **Jatin** | canon/BRAIN_TECHNICAL.md |
| MCP tool versioning | **Vikram** + **Maya** + Aryan | canon/BRAIN_TECHNICAL.md (tool registry) |
| Cross-language semantic checks | **Tanvi** | metric-registry parity etc. |
| External OpenAPI doc | **Vikram** | canon/BRAIN_TECHNICAL.md |

Related Brain skills: `grpc-buf` (the proto stack), `mcp-protocol` (tool catalogue + auth scopes), `testing-tdd`, `verification-before-completion`.
