---
name: mcp-builder
description: How to BUILD an MCP server from scratch — tool/resource/prompt definitions, transport (stdio vs streamable-HTTP), input schemas, error handling, auth, and testing with the MCP Inspector. Adapted from the Anthropic mcp-builder skill. Auto-load when Maya or Aryan is authoring a new MCP server (e.g. exposing a Brain integration or internal service to agents). Distinct from `mcp-protocol`, which covers wiring tools into Brain's existing auth + Decision Log + tenant model — read THIS to build the server, then `mcp-protocol` to make it Brain-compliant.
---

# MCP Builder — Building an MCP Server

> An MCP server is a typed contract between a model and the world. Get the schema, the transport, and the error shape right, and the model uses it correctly without prompting tricks.

Use this when you are **creating a new MCP server** — for example, exposing a Brain integration (Meta Ads, Shopify) or an internal service as agent-callable tools. Once the server works, switch to [`mcp-protocol`](../mcp-protocol/SKILL.md) to make it Brain-compliant (auth scopes, per-workspace tenancy, Decision Log middleware) and to [`agentic-actions-auditor`](../agentic-actions-auditor/SKILL.md) to audit any write tools before they ship.

Brain is TypeScript-first, so this skill uses `@modelcontextprotocol/sdk` (TS). The same shapes apply to the Python SDK.

## The Iron Law

```
A TOOL IS ITS SCHEMA. If the input schema, description, and error shape are wrong, no prompt fixes it.
```

The model's only view of your tool is the name, description, and JSON schema. Spend your effort there.

## The three primitives — pick the right one

| Primitive | Use when | Brain example |
|---|---|---|
| **Tool** | The model should *take an action* or *fetch dynamic data* | `meta.pause_ad_set`, `analytics.get_daily_metrics` |
| **Resource** | The model should *read* a stable, addressable document | a workspace's metric registry, an ADR |
| **Prompt** | You want to expose a reusable, parameterized prompt template | "draft a Morning Brief signal from these rows" |

Most Brain surfaces are **tools**. Don't model an action as a resource.

## Server skeleton (TypeScript, stdio)

```typescript
// servers/meta-ads/src/index.ts
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const server = new McpServer({ name: 'brain-meta-ads', version: '1.0.0' });

server.tool(
  'meta.get_ad_sets',
  'List ad sets for a workspace, optionally filtered by campaign. Read-only.',
  {
    workspace_id: z.string().describe('The workspace whose ad sets to list'),
    campaign_id: z.string().optional().describe('Filter to one campaign'),
  },
  async ({ workspace_id, campaign_id }) => {
    const rows = await metaClient.listAdSets({ workspace_id, campaign_id });
    return { content: [{ type: 'text', text: JSON.stringify(rows) }] };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

## Transport — choose deliberately

| Transport | Use when |
|---|---|
| **stdio** | Local/sidecar server, single client, launched as a child process. Default for agent-side tools. |
| **streamable-HTTP** | Remote/shared server, multiple clients, needs auth headers + horizontal scale. Use for a hosted Brain MCP service behind the gateway. |

Don't expose a write-capable server over HTTP without auth (see Auth below). For Brain, prefer stdio for agent-local tools; use streamable-HTTP only behind the API gateway with the standard auth middleware.

## Schema discipline (this is 80% of the work)

- **Name** tools `domain.verb_noun` (`meta.pause_ad_set`), lowercase, stable. The name is an API; don't rename casually.
- **Describe** every tool and every parameter in plain language — say what it does, its side effects, and its units (`amount_minor: paise, not rupees`).
- **Constrain** with Zod: enums over free strings, `.min()/.max()` on numbers, required vs `.optional()` deliberately. A tight schema prevents action-injection.
- **Return** structured JSON as text content; keep it small (the model pays for every token). Don't dump a 10K-row table — paginate or summarize.
- **Idempotency:** for write tools, accept an `idempotency_key` (see `idempotency-handling`).

## Error handling — fail loud and useful

```typescript
async ({ workspace_id, amount_minor }) => {
  if (amount_minor <= 0) {
    return { isError: true, content: [{ type: 'text', text: 'amount_minor must be positive (paise)' }] };
  }
  try {
    const result = await metaClient.updateBudget({ workspace_id, amount_minor });
    return { content: [{ type: 'text', text: JSON.stringify(result) }] };
  } catch (e) {
    // Return a model-readable error, not a stack trace
    return { isError: true, content: [{ type: 'text', text: `update_budget failed: ${e.code ?? 'unknown'}` }] };
  }
}
```

- Validation failures → `isError: true` with a message the model can act on.
- Never leak secrets, tokens, or full stack traces in error content.
- Distinguish *retryable* (network) from *terminal* (bad input) errors in the message.

## Auth (for HTTP transport / any write tool)

- HTTP server: require a bearer token; map it to a `workspace_id` + scopes. Reject unscoped calls.
- Write tools: enforce the minimum OAuth scope and the per-workspace tenancy check — do this in the handler, not just at the transport. (Then `mcp-protocol` makes it Brain-standard.)
- Never ship a tool that uses a god-mode token. One workspace's call must not touch another's data.

## Testing — MCP Inspector + integration test

```bash
# Interactive: launch the server under the Inspector and exercise every tool by hand
npx @modelcontextprotocol/inspector node servers/meta-ads/dist/index.js

# Automated: spin the server in-process and assert each tool's contract
pnpm test servers/meta-ads
```

A tool isn't done until: every parameter is exercised (valid + invalid), the error path returns `isError`, and a real (or sandboxed) backend call succeeds. Per `verification-before-completion`, capture the Inspector output before claiming the server works.

## Red flags — STOP

- A tool with a one-word description or undescribed parameters — the model will misuse it.
- Free-string parameters where an enum belongs — invites action-injection.
- A write tool with no `idempotency_key` and no tenancy check.
- Returning raw exceptions / stack traces / secrets in tool output.
- HTTP transport exposed without auth.
- Renaming a shipped tool without a deprecation path — breaks every caller.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Build the server + tool schemas | **Maya** (intelligence-engineer) | this skill |
| Make it Brain-compliant (auth, tenancy, Decision Log) | Maya + **Aryan** | `mcp-protocol` |
| Audit write tools before ship | **Shreya** | `agentic-actions-auditor` |
| No double-fire on writes | Maya | `idempotency-handling` |

## The bottom line

Build the schema first, the handler second. Constrain inputs, describe everything, return small structured results, fail loud. Then make it Brain-compliant and audit the writes. The model is only as good as the contract you give it.

Related: `mcp-protocol` (Brain auth + Decision Log + tenancy), `agentic-actions-auditor` (audit write tools), `idempotency-handling`, `agentic-design`.
