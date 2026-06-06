---
name: mcp-protocol
description: An MCP reference implementation — building a server (primitives, transport, Zod schemas, errors) + wiring it behind the edge gateway (4 auth layers, scopes, tenancy, audit log on writes). Schemas from the contract.
---

# MCP Protocol — an Agent + External Tool Surface

> **Reference implementation.** This skill documents one concrete binding of the agent/external-tool seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (schema-is-the-tool,
> schema-from-contract, four auth layers, audit-on-write) are what transfer.

MCP is a contract for: agents calling agents · agents querying memory · agents reaching external systems via adapters · external clients calling your agents. The MCP server lives **inside the edge gateway**, sharing auth + tenant isolation + rate-limit with the rest of the edge API. Contract details: the Product Canon's API/contract section.

---

# Part 1 — Building an MCP server

> A tool is its schema. The model's only view is the name, description, and JSON schema — spend your effort there.

## Primitives — pick the right one
| Primitive | Use when | Example |
|---|---|---|
| **Tool** | take an action / fetch dynamic data | `ads.pause_ad_set`, `analytics.get_daily_metrics` |
| **Resource** | read a stable, addressable document | the metric registry, an ADR |
| **Prompt** | reusable parameterized template | "draft a summary signal from these rows" |
Most surfaces are tools — don't model an action as a resource.

## Server skeleton (TypeScript, stdio)
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
const server = new McpServer({ name: 'ads', version: '1.0.0' });
server.tool('ads.get_ad_sets', 'List ad sets for a tenant. Read-only.',
  { tenant_id: z.string().describe('whose ad sets'), campaign_id: z.string().optional() },
  async ({ tenant_id, campaign_id }) => ({ content: [{ type: 'text', text: JSON.stringify(await adsClient.listAdSets({ tenant_id, campaign_id })) }] }));
await server.connect(new StdioServerTransport());
```

## Transport
**stdio** for agent-local sidecar tools (default). **streamable-HTTP** only behind the edge gateway with the standard auth middleware (Part 2). Never expose a write-capable server over HTTP without auth.

## Schema discipline (80% of the work)
- Name `domain.verb_noun`, lowercase, stable — the name is an API, don't rename casually.
- Describe every tool + param: what it does, side effects, units (`amount_minor: minor units, not major`).
- Constrain with Zod: enums over free strings, `.min()/.max()`, deliberate required vs `.optional()` — a tight schema prevents action-injection.
- Return small structured JSON as text (model pays per token) — paginate/summarize, don't dump a 10K-row table.
- Write tools accept an `idempotency_key` (see `idempotency-handling`).

## Error handling — fail loud and useful
```typescript
if (amount_minor <= 0) return { isError: true, content: [{ type: 'text', text: 'amount_minor must be positive (minor units)' }] };
try { return { content: [{ type: 'text', text: JSON.stringify(await adsClient.updateBudget({...})) }] }; }
catch (e) { return { isError: true, content: [{ type: 'text', text: `update_budget failed: ${e.code ?? 'unknown'}` }] }; }
```
Distinguish retryable (network) from terminal (bad input). Never leak secrets/tokens/stack traces.

## Testing
```bash
npx @modelcontextprotocol/inspector node servers/ads/dist/index.js   # exercise every tool by hand
pnpm test servers/ads
```
Not done until every param is exercised (valid+invalid), the error path returns `isError`, and a real/sandboxed backend call succeeds. Capture Inspector output (`verification-before-completion`).

### Red flags — STOP
One-word description / undescribed params · free-string where an enum belongs · write tool with no `idempotency_key` and no tenancy check · raw exceptions/secrets in output · HTTP transport without auth · renaming a shipped tool with no deprecation path.

---

# Part 2 — Wiring it behind the edge gateway

## Architecture
External clients + agents (as MCP clients) → **the MCP server inside the edge gateway** (auth → scope → tenant → tool-specific gate → audit-log auto-write on writes) → routes via the internal API to the backend services.

## Tool naming: `<domain>.<resource>.<action>`
| Domain | Owner | Examples |
|---|---|---|
| `memory` | intelligence | `memory.context.query`, `memory.outcome.search` |
| `analytics` | analytics | `analytics.metric.get`, `analytics.waterfall.compute`, `analytics.drill_down` |
| `integrations` | ingestion (read) + core (writeback) | `integrations.store.list_orders`, `integrations.ads.adjust_budget` |
| `lifecycle` | lifecycle | `lifecycle.audience.build`, `lifecycle.outreach.trigger`, `lifecycle.call.place` |
| `ai` | intelligence | `ai.agent.invoke`, `ai.chat.message` |
| `audit_log` | analytics | `audit_log.record`, `audit_log.attribute_outcome` |
| `core` | core | `core.consent.update`, `core.goal.set` |

## Tool schemas — from the contract (single source of truth, cannot drift)
```typescript
export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build',
  description: 'Build a triggered audience. Returns size + projected response + channel mix. NOT triggered — separate lifecycle.outreach.trigger call.',
  scope: 'lifecycle:write',
  input: z.object({ tenant_id: z.string().uuid(), segment_or_filter: z.union([z.enum([...]), CustomFilterSchema]), preview_only: z.boolean().default(true) }),
  output: z.object({ audience_id: z.string().uuid(), size: z.number().int(), projected_value_minor: z.number().int() }),
  handler: async (input, ctx) => { await requireTenant(input.tenant_id, ctx); await requireScope('lifecycle:write', ctx); return lifecycleClient.buildAudience(input); },
});
```

## Auth — four layers, all mandatory
1. **Auth** — JWT or MCP API key valid?
2. **Scope** — caller's scope includes the tool's required scope?
3. **Tenant** — the tenant key in args matches caller's accessible tenants?
4. **Tool-specific** — e.g. write tools need the right role + an audit-log ref if the agent isn't graduated to auto-execute.
All four mandatory; failures return the standardized MCP error.

### Scopes
`analytics:read` · `memory:read` · `lifecycle:read|write` · `integrations:read|write` · `agent:invoke` · `admin` (rare, audited). Default new key: `analytics:read + memory:read`; higher needs role-holder approval (audit-logged).

## Audit-log integration — MANDATORY
**Every MCP write tool writes a system-of-record audit entry via middleware. Never bypass.** Auto-write on any `integrations.*.write`, `lifecycle.outreach.*`, `lifecycle.call.place`, `core.consent.update`, `core.goal.set`. Entry: caller (user/agent/api-key id), tool + args (PII-redacted), outcome, and any later outcome attribution. This is what makes the audit log the source of truth for "what did the product do?" — see `decision-log`.

## Human-in-the-loop
Un-graduated agent → recommendation (audit entry `pending`) → role-holder approves (write fires with the audit ref) or rejects (logged, no write). Graduated agent → write fires automatically, marked `auto_approved`.

## Streaming + inter-agent
Long ops stream SSE (`tool_start`/`tool_result`/`agent_reasoning`/`agent_recommendation`/`done` with the audit ref). Inter-agent via `ai.agent.invoke` — MCP's tool-use semantics are LLM-native and the registry is discoverable; for non-LLM code paths a direct internal call is fine.

## Observability + versioning
Every call emits `tool_calls_total{tool,status,paradigm}`, `tool_duration_seconds`, `tool_cost_micros{paradigm,tenant}`, a structured log + a trace span. Versioning: `…/v2` in the name for breaking; keep old ≥6 months; non-breaking (new optional fields) same version (see `api-discipline`).

## Common failure modes
Missing `scope` on the tool def (Security blocks) · bypassing the audit-write middleware · no `requireTenant` (cross-tenant pull) · hand-written schema drift · streaming without backpressure.

## References
Product Canon API/contract section · `grpc-buf` (contract codegen) · `agentic-safety` (audit + harden write tools) · `idempotency-handling` · `security-baseline` · `auth-and-access`.
