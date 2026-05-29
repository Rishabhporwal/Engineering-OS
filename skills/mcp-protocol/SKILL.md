---
name: mcp-protocol
description: Brain's MCP — building a server (primitives, transport, Zod schemas, errors) + wiring into api-gateway (4 auth layers, scopes, tenancy, Decision Log on writes). Schemas from protos/.
---

# MCP Protocol — Brain's Agent + External Surface

MCP is Brain's contract for: agents calling agents · agents querying the Memory Layer · agents reaching external systems (Shopify, Meta, calling vendors) via adapters · external clients (Claude native, partners, Enterprise) calling Brain agents. The MCP server lives **inside api-gateway**, sharing auth + multi-tenancy + rate-limit with tRPC. Canon: `canon/technical-requirements.md`.

---

# Part 1 — Building an MCP server

> A tool is its schema. The model's only view is the name, description, and JSON schema — spend your effort there.

## Primitives — pick the right one
| Primitive | Use when | Example |
|---|---|---|
| **Tool** | take an action / fetch dynamic data | `meta.pause_ad_set`, `analytics.get_daily_metrics` |
| **Resource** | read a stable, addressable document | metric registry, an ADR |
| **Prompt** | reusable parameterized template | "draft a Morning Brief signal from these rows" |
Most Brain surfaces are tools — don't model an action as a resource.

## Server skeleton (TypeScript, stdio)
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
const server = new McpServer({ name: 'brain-meta-ads', version: '1.0.0' });
server.tool('meta.get_ad_sets', 'List ad sets for a workspace. Read-only.',
  { workspace_id: z.string().describe('whose ad sets'), campaign_id: z.string().optional() },
  async ({ workspace_id, campaign_id }) => ({ content: [{ type: 'text', text: JSON.stringify(await metaClient.listAdSets({ workspace_id, campaign_id })) }] }));
await server.connect(new StdioServerTransport());
```

## Transport
**stdio** for agent-local sidecar tools (default). **streamable-HTTP** only behind api-gateway with the standard auth middleware (Part 2). Never expose a write-capable server over HTTP without auth.

## Schema discipline (80% of the work)
- Name `domain.verb_noun`, lowercase, stable — the name is an API, don't rename casually.
- Describe every tool + param: what it does, side effects, units (`amount_minor: paise, not rupees`).
- Constrain with Zod: enums over free strings, `.min()/.max()`, deliberate required vs `.optional()` — a tight schema prevents action-injection.
- Return small structured JSON as text (model pays per token) — paginate/summarize, don't dump a 10K-row table.
- Write tools accept an `idempotency_key` (see `idempotency-handling`).

## Error handling — fail loud and useful
```typescript
if (amount_minor <= 0) return { isError: true, content: [{ type: 'text', text: 'amount_minor must be positive (paise)' }] };
try { return { content: [{ type: 'text', text: JSON.stringify(await metaClient.updateBudget({...})) }] }; }
catch (e) { return { isError: true, content: [{ type: 'text', text: `update_budget failed: ${e.code ?? 'unknown'}` }] }; }
```
Distinguish retryable (network) from terminal (bad input). Never leak secrets/tokens/stack traces.

## Testing
```bash
npx @modelcontextprotocol/inspector node servers/meta-ads/dist/index.js   # exercise every tool by hand
pnpm test servers/meta-ads
```
Not done until every param is exercised (valid+invalid), the error path returns `isError`, and a real/sandboxed backend call succeeds. Capture Inspector output (`verification-before-completion`).

### Red flags — STOP
One-word description / undescribed params · free-string where an enum belongs · write tool with no `idempotency_key` and no tenancy check · raw exceptions/secrets in output · HTTP transport without auth · renaming a shipped tool with no deprecation path.

---

# Part 2 — Wiring into Brain

## Architecture (canon §2)
External clients + Brain agents (as MCP clients) → **Brain MCP Server inside api-gateway** (auth → scope → tenant → tool-specific gate → Decision Log auto-write on writes) → routes via gRPC to analytics/core/lifecycle/intelligence services.

## Tool naming: `<domain>.<resource>.<action>`
| Domain | Owner | Examples |
|---|---|---|
| `memory` | intelligence | `memory.brand_fingerprint.query`, `memory.condition_outcome.search` |
| `analytics` | analytics | `analytics.metric.get`, `analytics.waterfall.compute`, `analytics.drill_down` |
| `integrations` | ingestion (read) + core (writeback) | `integrations.shopify.list_orders`, `integrations.meta.adjust_campaign_budget` |
| `lifecycle` | lifecycle | `lifecycle.audience.build`, `lifecycle.outreach.trigger`, `lifecycle.call.place` |
| `ai` | intelligence | `ai.agent.invoke`, `ai.chat.message`, `ai.morning_brief.generate` |
| `decision_log` | analytics | `decision_log.record`, `decision_log.attribute_outcome` |
| `core` | core | `core.consent.update`, `core.goal.set` |

## Tool schemas — from proto (single source of truth, cannot drift)
```typescript
export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build',
  description: 'Build an RFM-triggered audience. Returns size + projected response + revenue recovery + channel mix. NOT triggered — separate lifecycle.outreach.trigger call.',
  scope: 'brain:lifecycle:write',
  input: z.object({ workspace_id: z.string().uuid(), segment_or_filter: z.union([z.enum([...]), CustomFilterSchema]), preview_only: z.boolean().default(true) }),
  output: z.object({ audience_id: z.string().uuid(), size: z.number().int(), projected_revenue_minor: z.number().int() }),
  handler: async (input, ctx) => { await requireTenant(input.workspace_id, ctx); await requireScope('brain:lifecycle:write', ctx); return lifecycleClient.buildAudience(input); },
});
```

## Auth (canon §5) — four layers, all mandatory
1. **Auth** — JWT or `brain_mcp_key` valid?
2. **Scope** — caller's scope includes the tool's required scope?
3. **Tenant** — `workspace_id` in args matches caller's accessible workspaces?
4. **Tool-specific** — e.g. write tools need Owner role + Decision Log ref if the agent isn't graduated.
All four mandatory; failures return the standardized MCP error.

### Scopes
`brain:analytics:read` · `brain:memory:read` · `brain:lifecycle:read|write` · `brain:integrations:read|write` · `brain:agent:invoke` · `brain:admin` (rare, audited). Default new key: `analytics:read + memory:read`; higher needs Owner approval (audit-logged).

## Decision Log integration (canon §8) — MANDATORY
**Every MCP write tool writes a Decision Log entry via middleware. Never bypass.** Auto-write on any `integrations.*.write`, `lifecycle.outreach.*`, `lifecycle.call.place`, `core.consent.update`, `core.goal.set`. Entry: caller (user/agent/api-key id), tool + args (PII-redacted), outcome, 7d+30d attribution (Maya's nightly job). This is what makes the Decision Log Brain's source of truth for "what did Brain do?" — see `decision-log`.

## Human-in-the-loop (canon §9)
Un-graduated agent → recommendation (Decision Log `pending`) → Owner approves (write fires with `decision_log_id` ref) or rejects (logged, no write). Graduated agent → write fires automatically, marked `auto_approved`.

## Streaming + inter-agent
Long ops stream SSE (`tool_start`/`tool_result`/`agent_reasoning`/`agent_recommendation`/`done` with `decision_log_id`). Inter-agent via `ai.agent.invoke` — MCP's tool-use semantics are LLM-native and the registry is discoverable; for non-LLM code paths direct gRPC is fine.

## Observability + versioning
Every call emits `tool_calls_total{tool,status,paradigm}`, `tool_duration_seconds`, `tool_cost_micros{paradigm,brand}`, OpenSearch log + X-Ray span. Versioning: `…/v2` in name for breaking; old ≥6 months; non-breaking (new optional fields) same version (see `api-discipline`).

## Common failure modes
Missing `scope` on the tool def (Shreya blocks) · bypassing the decorator (skips Decision Log) · no `requireTenant` (cross-tenant pull) · hand-written schema drift · streaming without backpressure.

## References
`canon/technical-requirements.md` · `agentic-design` (`@mcp_tool` on agent methods) · `grpc-buf` (proto codegen) · `agentic-actions-auditor` (audit write tools) · `idempotency-handling` · `security-baseline` · `auth-and-access`.
