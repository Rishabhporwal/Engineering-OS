---
name: mcp-protocol
description: Brain's Model Context Protocol — the contract for agent-to-agent + external-client tool use. MCP server lives inside api-gateway, sharing auth + multi-tenancy + rate-limit with tRPC. Auto-load whenever defining/implementing a new MCP tool, wiring agent invocation, handling MCP auth scopes, or hooking the Decision Log. Tool schemas come from proto files (single source of truth — cannot drift). Every MCP write tool auto-writes Decision Log via middleware.
---

# MCP Protocol — Brain's Agent + External Surface

Model Context Protocol (MCP) is Brain's contract for:

1. **Agents calling other agents** (AICMO-Cross-Channel queries AICMO-Meta)
2. **Agents querying the Memory Layer** (any agent asks Brand Fingerprint or Customer Segment Memory)
3. **Agents reaching external systems** (Shopify, Meta, Razorpay, calling vendors) via MCP adapters
4. **External clients** (Anthropic Claude native MCP, OpenAI Assistants, partner integrations, Enterprise tier) calling Brain agents

**Canonical doc:** `docs/TECH/13_mcp_protocol.md`. This skill is the operational reference.

## Architecture (TECH/13 §2)

```
External MCP clients (Claude, partners, Enterprise)        Brain agents (intelligence-service) as MCP clients
                              │                                                                  │
                              ▼                                                                  ▼
                  ┌──────────────────────────────────────────────────────────┐
                  │   Brain MCP Server (inside api-gateway)                   │
                  │   - Auth (Supabase JWT OR brain_mcp_key)                  │
                  │   - Scope check                                            │
                  │   - Tenant check                                           │
                  │   - Tool-specific gate (Owner role? Decision Log ref?)    │
                  │   - Decision Log auto-write on write tools                │
                  └─────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
              (routes via gRPC to analytics-service / core-service / lifecycle-service / intelligence-service)
```

## Tool naming convention (TECH/13 §3)

```
<domain>.<resource>.<action>
```

| Domain | Owned by | Examples |
|---|---|---|
| `memory` | intelligence-service | `memory.brand_fingerprint.query`, `memory.condition_outcome.search`, `memory.seasonal_codebook.lookup` |
| `analytics` | analytics-service | `analytics.metric.get`, `analytics.waterfall.compute`, `analytics.cohort.get`, `analytics.drill_down` |
| `integrations` | ingestion-service (read) + core-service (writebacks) | `integrations.shopify.list_orders`, `integrations.meta.adjust_campaign_budget`, `integrations.google.add_negative_keyword`, `integrations.shiprocket.create_label` |
| `lifecycle` | lifecycle-service | `lifecycle.audience.build`, `lifecycle.outreach.trigger`, `lifecycle.call.place`, `lifecycle.ticket.resolve` |
| `ai` | intelligence-service | `ai.agent.invoke`, `ai.chat.message`, `ai.insight.generate`, `ai.morning_brief.generate` |
| `decision_log` | analytics-service | `decision_log.record`, `decision_log.attribute_outcome` |
| `core` | core-service | `core.brand.get`, `core.member.list`, `core.consent.update`, `core.goal.set` |

## Tool schemas — from proto files (single source of truth)

Schemas generated from `protos/*.proto` so MCP and gRPC contracts cannot drift.

```typescript
// apps/api-gateway/src/mcp/tools/lifecycle.ts
import { z } from 'zod';
import { mcpTool } from '../decorator';

export const buildAudience = mcpTool({
  name: 'lifecycle.audience.build',
  description: 'Build an RFM-triggered audience. Returns size + projected response rate + projected revenue recovery + recommended channel mix. NOT triggered — that requires separate call to lifecycle.outreach.trigger.',
  scope: 'brain:lifecycle:write',
  input: z.object({
    workspace_id: z.string().uuid(),
    segment_or_filter: z.union([
      z.enum(['champions','loyal','potential_loyal','new_customers','promising','need_attention','about_to_sleep','at_risk','cant_lose_them','hibernating','lost']),
      CustomFilterSchema,
    ]),
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
    await requireTenant(input.workspace_id, ctx);
    await requireScope('brain:lifecycle:write', ctx);
    return await lifecycleClient.buildAudience(input);
  },
});
```

## Auth (TECH/13 §5) — four layers, all mandatory

1. **Auth** — JWT or brain_mcp_key valid?
2. **Scope** — does the caller's scope include this tool's required scope?
3. **Tenant** — does `workspace_id` in arguments match caller's accessible workspaces?
4. **Tool-specific** — e.g., write tools require Owner role + Decision Log reference if agent not graduated

All four mandatory. Failures return standardized MCP error.

### Scopes

```
brain:analytics:read         — read-only metric queries
brain:memory:read            — Memory Layer read
brain:lifecycle:read         — outreach + ticket read
brain:lifecycle:write        — trigger audiences + outreach
brain:integrations:read      — connected platforms read
brain:integrations:write     — write back to platforms (budgets, keywords, etc.)
brain:agent:invoke           — call Brain agents
brain:admin                  — superuser; rare; audited
```

Default new key: `brain:analytics:read + brain:memory:read`. Higher scopes need Owner approval (audit-logged).

## Streaming (TECH/13 §6)

For long-running operations (agent reasoning, Morning Brief generation, AI Chat):

```
POST /mcp/call_tool { "tool": "ai.agent.invoke", "stream": true, ... }

Response (SSE):

event: tool_start         data: { "tool": "memory.brand_fingerprint.query", "args": {...} }
event: tool_result        data: { "matches": [...] }
event: tool_start         data: { "tool": "analytics.metric.get", "args": {...} }
event: tool_result        data: { "value": ... }
event: agent_reasoning    data: { "text": "Three similar historical states..." }
event: agent_recommendation data: { "action": "reduce_meta_budget", "amount_minor": 50000, "rationale": "..." }
event: done               data: { "decision_log_id": "..." }
```

## Inter-agent invocation (TECH/13 §7)

```json
{
  "tool": "ai.agent.invoke",
  "arguments": {
    "agent": "aicmo-meta",
    "operation": "evaluate_creative_fatigue",
    "workspace_id": "...",
    "context": { "as_of_date": "2026-05-13", "campaigns": [...] }
  }
}
```

Why MCP (not direct gRPC) for inter-agent? Inter-agent calls happen inside LLM reasoning loops. MCP's tool-use semantics are LLM-native. The tool registry is discoverable — an agent asks "what other agents exist?" and dispatches.

For non-LLM agent code paths, direct gRPC is acceptable.

## Decision Log integration (TECH/13 §8) — MANDATORY

**Every MCP write tool call writes a Decision Log entry via middleware.** Never bypass.

Auto-write on:
- Any `integrations.*.write` call
- Any `lifecycle.outreach.*` call
- Any `lifecycle.call.place` call
- Any `core.consent.update` call
- Any `core.goal.set` call

Decision Log entry includes:
- Caller (user_id OR agent_id OR external_api_key_id)
- Tool name + arguments (PII-redacted)
- Outcome (success / error / partial)
- 7d + 30d outcome attribution (backfilled by Kabir's nightly job)

This is what makes the Decision Log Brain's single source of truth for "what did Brain do?"

## Human-in-the-loop mode (TECH/13 §9)

For un-graduated agents (TECH/14 §6 graduation criteria not yet met):
- Agent generates **recommendation** (Decision Log entry in `pending` state)
- Owner sees it on Morning Brief or web app
- Owner approves → MCP write tool fires with `decision_log_id` reference
- Owner rejects → recommendation logged; no write fires

For graduated agents: write fires automatically; entry marked `auto_approved`.

## Observability (TECH/13 §10)

Every MCP call emits:
- `Brain/MCP/tool_calls_total{tool, status, paradigm}` (CloudWatch)
- `Brain/MCP/tool_duration_seconds{tool}` (CloudWatch)
- `Brain/MCP/tool_cost_micros{tool, paradigm, brand}` (cost-routing audit)
- OpenSearch log entry with correlation IDs
- X-Ray span via `traceparent` header

## Versioning (TECH/13 §11)

- Tool versions in URL: `memory.brand_fingerprint.query/v2` for breaking changes
- Old versions supported ≥ 6 months after new version ships
- Non-breaking changes (new optional fields) ship under same version

## Common failure modes

- **Missing scope on tool definition**: Shreya blocks. Detection: `mcpTool({...})` missing `scope` field.
- **Bypassing the decorator**: writing to an external API directly skips Decision Log. Detection: handler calls Meta/Google/Shopify SDK without going through `mcpTool`.
- **No `requireTenant` check**: a tool that accepts `workspace_id` but doesn't assert membership lets workspace A pull workspace B's data.
- **Schema drift from proto**: MCP schema written by hand diverges from `.proto`. Always generate from proto.
- **Streaming response without backpressure**: client falls behind; agent reasoning hangs. Use SSE with bounded buffer.

## References

- `docs/TECH/13_mcp_protocol.md` — canonical
- `docs/TECH/06_api_contracts.md` — gRPC + tRPC + MCP intersection
- `docs/TECH/14_agent_roster.md` — agents that produce MCP tool catalogues
- `skills/agentic-design/SKILL.md` — `@mcp_tool` decorator wiring on agent methods
- `skills/grpc-buf/SKILL.md` — proto codegen workflow
- `skills/security-baseline/SKILL.md` §mcp-auth — scope check + tenant check + tool-specific gate
