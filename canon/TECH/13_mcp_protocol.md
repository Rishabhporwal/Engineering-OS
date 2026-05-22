# TECH/13 — Model Context Protocol (MCP)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E1 (architecture) + E4 (agent implementations) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/05_intelligence_layer.md](05_intelligence_layer.md), [TECH/14_agent_roster.md](14_agent_roster.md)

**Truncation note:** the source brief referenced Section 12 (MCP details) but cut off before that section. This doc constructs MCP design based on the brief's stated intent ("inter-agent and external surface protocol") and MCP's open specification. Flagged where the brief might override.

---

## 1. What MCP Is in Brain

Model Context Protocol (MCP) is **the contract** through which:

1. **Agents call other agents** (AICMO-Cross-Channel queries AICMO-Meta for current campaign state)
2. **Agents query the Memory Layer** (any agent asks Brand Fingerprint or Customer Segment Memory)
3. **Agents reach external systems** (Shopify, Meta, Razorpay, calling vendors) through MCP-server adapters
4. **External clients call Brain's agents** (third-party tooling, future partner integrations, custom client integrations on Enterprise tier)

**Why MCP, not custom RPC:**
- Tool-use semantics native to LLMs (Anthropic, OpenAI, others natively speak MCP)
- Future-proof against multi-vendor LLM scenarios — same agent code works regardless of which LLM is driving
- Standardised auth, schema, streaming, error semantics
- Inspectable: an agent's tool inventory is discoverable at runtime

**Why MCP, not just gRPC:**
- gRPC stays as the internal service-to-service contract (api-gateway ↔ core-service, analytics-service, etc.). Strongly typed, fast, well-suited for synchronous service calls.
- MCP is for **agent semantics**: tool discovery, capability advertisement, streaming reasoning, structured tool results. Built for LLM-driven flows.

Both exist. Agents internally call gRPC for fast hot-path data, and use MCP for tool-use orchestration where the LLM is deciding what to call.

---

## 2. MCP Architecture in Brain

```
┌───────────────────────────────────────────────────────────────────────┐
│                          MCP TOPOLOGY                                  │
└───────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐                  ┌─────────────────────────┐
│  AICMO-Cross-Channel│                  │  External MCP Clients   │
│  (acting as MCP     │                  │  (future partners,      │
│   CLIENT)           │                  │   Enterprise customers, │
│                     │                  │   third-party tooling)  │
└──────────┬──────────┘                  └────────────┬────────────┘
           │                                          │
           │ MCP (call_tool)                          │ MCP (call_tool)
           ▼                                          ▼
┌───────────────────────────────────────────────────────────────────────┐
│                  Brain MCP Server Layer                                │
│  (lives inside api-gateway; auth at the edge; routes to backend)      │
│                                                                        │
│  Tool registry:                                                        │
│   • memory.brand_fingerprint.query                                     │
│   • memory.condition_outcome.search                                    │
│   • memory.seasonal_codebook.lookup                                    │
│   • memory.customer_segment.get                                        │
│   • analytics.metric.get                                               │
│   • analytics.waterfall.compute                                        │
│   • analytics.cohort.get                                               │
│   • integrations.shopify.list_orders                                   │
│   • integrations.meta.adjust_campaign_budget                           │
│   • integrations.google.add_negative_keyword                           │
│   • integrations.shiprocket.create_label                               │
│   • lifecycle.audience.build                                           │
│   • lifecycle.outreach.trigger                                         │
│   • lifecycle.call.place                                               │
│   • ai.agent.invoke (call another Brain agent)                         │
│   • decision_log.record                                                │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌───────────────────┐
   │ analytics-service│ │ core-service     │ │ lifecycle-service │
   │ (gRPC)           │ │ (gRPC)           │ │ (gRPC)            │
   └──────────────────┘ └──────────────────┘ └───────────────────┘
              │                  │                  │
              ▼                  ▼                  ▼
   ┌──────────────────┐ ┌──────────────────┐ ┌───────────────────┐
   │ ClickHouse       │ │ Postgres         │ │ AI calling vendor │
   └──────────────────┘ └──────────────────┘ │ WhatsApp Cloud    │
                                              │ SES               │
                                              └───────────────────┘
```

**Key points:**
- Brain's **MCP server lives inside api-gateway**, sharing the same auth + multi-tenancy + rate-limit middleware as the rest of the public surface
- Internally, MCP tools route to the appropriate gRPC service
- Brain agents in `intelligence-service` act as MCP **clients** when invoking tools or calling each other
- External callers (Anthropic Claude, OpenAI Assistants, partner tooling) can connect as MCP clients with scoped credentials

---

## 3. MCP Tool Naming Convention

```
<domain>.<resource>.<action>
```

| Domain | Owned By | Example Tools |
|--------|----------|--------------|
| `memory` | intelligence-service (Memory Layer) | `memory.brand_fingerprint.query`, `memory.condition_outcome.search`, `memory.seasonal_codebook.lookup` |
| `analytics` | analytics-service | `analytics.metric.get`, `analytics.waterfall.compute`, `analytics.cohort.get`, `analytics.drill_down` |
| `integrations` | ingestion-service + core-service (writebacks) | `integrations.shopify.list_orders`, `integrations.meta.adjust_campaign_budget`, `integrations.google.add_negative_keyword`, `integrations.shiprocket.create_label` |
| `lifecycle` | lifecycle-service | `lifecycle.audience.build`, `lifecycle.outreach.trigger`, `lifecycle.call.place`, `lifecycle.ticket.resolve` |
| `ai` | intelligence-service | `ai.agent.invoke` (call another agent), `ai.chat.message`, `ai.insight.generate` |
| `decision_log` | analytics-service | `decision_log.record`, `decision_log.attribute_outcome` |
| `core` | core-service | `core.brand.get`, `core.member.list`, `core.consent.update`, `core.goal.get`, `core.goal.set` |

---

## 4. Tool Schemas

Every MCP tool advertises a strict JSON Schema for its inputs and outputs. Generated from the same proto definitions as gRPC so the contracts cannot drift.

### Example 1: Memory Tool

```json
{
  "name": "memory.brand_fingerprint.query",
  "description": "Find historical brand-states most similar to the current brand-state. Returns top-K similar conditions with their outcomes. Used by agents to ask 'what happened last time the brand was in this state?'",
  "inputSchema": {
    "type": "object",
    "required": ["brand_id"],
    "properties": {
      "brand_id":      { "type": "string", "format": "uuid" },
      "as_of_date":    { "type": "string", "format": "date", "default": "today" },
      "k":             { "type": "integer", "default": 5, "minimum": 1, "maximum": 50 },
      "cross_brand":   { "type": "boolean", "default": false, "description": "Include similar conditions from other brands in the network (anonymised)" }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "matches": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "match_date": { "type": "string", "format": "date" },
            "similarity_score": { "type": "number" },
            "fingerprint_summary": { "type": "string" },
            "outcomes_7d": { "type": "object" },
            "outcomes_30d": { "type": "object" }
          }
        }
      }
    }
  }
}
```

### Example 2: Lifecycle Tool

```json
{
  "name": "lifecycle.audience.build",
  "description": "Build an RFM-triggered audience. Returns audience size + projected response rate + projected revenue recovery + recommended channel mix. Audience is NOT triggered — that requires a separate call to lifecycle.outreach.trigger with the returned audience_id.",
  "inputSchema": {
    "type": "object",
    "required": ["brand_id", "segment_or_filter"],
    "properties": {
      "brand_id":         { "type": "string", "format": "uuid" },
      "segment_or_filter": {
        "oneOf": [
          { "type": "string", "enum": ["champions","loyal","potential_loyal","new_customers","promising","need_attention","about_to_sleep","at_risk","cant_lose_them","hibernating","lost"] },
          { "$ref": "#/definitions/CustomFilter" }
        ]
      },
      "preview_only":     { "type": "boolean", "default": true }
    }
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "audience_id":               { "type": "string", "format": "uuid" },
      "size":                      { "type": "integer" },
      "projected_response_rate":   { "type": "number" },
      "projected_revenue_minor":   { "type": "integer" },
      "channel_mix":               { "type": "object" }
    }
  }
}
```

### Example 3: Integration Writeback Tool

```json
{
  "name": "integrations.meta.adjust_campaign_budget",
  "description": "Adjust daily budget on a Meta Ads campaign. Requires Owner-level brand auth AND, in human-in-the-loop mode, an approved Decision Log entry. Returns the new budget after Meta API acceptance.",
  "inputSchema": {
    "type": "object",
    "required": ["brand_id", "campaign_id", "new_daily_budget_minor"],
    "properties": {
      "brand_id":               { "type": "string", "format": "uuid" },
      "campaign_id":            { "type": "string" },
      "new_daily_budget_minor": { "type": "integer", "minimum": 0 },
      "decision_log_id":        { "type": "string", "format": "uuid", "description": "Required if agent is not yet graduated to auto-execute" }
    }
  }
}
```

---

## 5. Auth & Multi-Tenancy in MCP

### Authentication

MCP requests carry a Supabase JWT (same as tRPC requests from web + mobile clients) OR an MCP-specific API key (for external integrations + Enterprise tier).

```http
POST /mcp/call_tool HTTP/1.1
Host: api.{BRAIN_DOMAIN}
Authorization: Bearer <supabase_jwt OR brain_mcp_key>
Content-Type: application/json

{
  "tool": "memory.brand_fingerprint.query",
  "arguments": { "brand_id": "...", "k": 5 }
}
```

### Authorisation Layers

1. **Auth layer** — JWT or API key valid?
2. **Scope layer** — does the caller have permission for this tool? Each tool has a required scope (e.g. `analytics:read`, `lifecycle:write`, `integrations:meta:write`)
3. **Tenant layer** — does the `brand_id` in the argument match the caller's accessible brand list?
4. **Tool-specific layer** — some tools have additional gates (e.g. integration writebacks need Owner role + Decision Log approval reference if agent not graduated)

All four layers are mandatory. Failures return a standardised MCP error.

### API Key Scopes (Enterprise + Partner Use)

```
brain:analytics:read         — read-only metric queries
brain:memory:read            — Memory Layer read access
brain:lifecycle:read         — read outreach + ticket data
brain:lifecycle:write        — trigger audiences + outreach
brain:integrations:read      — read connected platforms
brain:integrations:write     — push changes to platforms (budgets, keywords, etc.)
brain:agent:invoke           — call Brain agents as MCP tools
brain:admin                  — superuser; rare; audited
```

Scopes are additive. Default new key has `brain:analytics:read + brain:memory:read`. Higher scopes require explicit Owner approval.

---

## 6. Streaming Semantics

MCP supports streaming responses for long-running operations. Used in Brain for:

- **Agent reasoning streams** (`ai.agent.invoke`): the agent's intermediate thinking + sub-tool calls stream back, ending with a final structured result
- **Morning Brief generation** (`ai.morning_brief.generate`): synthesis streams as it composes
- **AI Chat** (`ai.chat.message`): standard streaming

```
POST /mcp/call_tool
{
  "tool": "ai.agent.invoke",
  "arguments": { "agent": "aicmo-cross-channel", "brand_id": "..." },
  "stream": true
}

Response (SSE / chunked):

event: tool_start
data: { "tool": "memory.brand_fingerprint.query", "args": {...} }

event: tool_result
data: { "matches": [...] }

event: tool_start
data: { "tool": "analytics.metric.get", "args": {...} }

event: tool_result
data: { "value": ... }

event: agent_reasoning
data: { "text": "Three similar historical states found. CTR fatigue pattern matches..." }

event: agent_recommendation
data: { "action": "reduce_meta_budget", "amount_minor": 50000, "rationale": "..." }

event: done
data: { "decision_log_id": "..." }
```

---

## 7. Inter-Agent Invocation via MCP

Agents call other agents via `ai.agent.invoke`. Standardised request envelope:

```json
{
  "tool": "ai.agent.invoke",
  "arguments": {
    "agent": "aicmo-meta",
    "operation": "evaluate_creative_fatigue",
    "brand_id": "...",
    "context": {
      "as_of_date": "2026-05-13",
      "campaigns": ["camp_123", "camp_456"]
    }
  }
}
```

Receiving agent (`aicmo-meta`) executes its paradigm-appropriate logic (typically ML for fatigue detection — EWMA on CTR), records to Decision Log, returns structured result.

Calling agent (`aicmo-cross-channel`) receives the result, uses it as input for its own reasoning (budget reallocation across platforms).

### Why MCP for Inter-Agent (Not Direct gRPC)

Inter-agent calls happen inside LLM reasoning loops (in the frontier-LLM paradigm). MCP's tool-use semantics are natively understood by LLMs — the agent doesn't need bespoke client code per peer-agent. The tool registry is discoverable; an agent can ask "what other agents exist?" and dispatch accordingly.

For non-LLM agent code paths (paradigm 1/2/3), direct gRPC remains acceptable when the call graph is statically known.

---

## 8. Decision Log Integration

**Every MCP tool call that mutates state or triggers external action MUST be logged to Decision Log.**

Implementation: the MCP server middleware automatically writes a Decision Log entry on:
- Any `integrations.*.write` call
- Any `lifecycle.outreach.*` call
- Any `lifecycle.call.place` call
- Any `core.consent.update` call
- Any `core.goal.set` call

Decision Log entry includes:
- Caller (user_id OR agent_id OR external_api_key_id)
- Tool name + arguments (PII-redacted)
- Outcome (success / error / partial)
- 7d + 30d outcome attribution (auto-filled by attribution job)

This is what makes the Decision Log the single source of truth for "what did Brain do?"

---

## 9. Human-in-the-Loop Mode

In the early-launch phase and for un-graduated agents (TECH/14 §3), the MCP server enforces human-in-the-loop on write tools:

- Agent generates a **recommendation** (a Decision Log entry in `pending` state)
- Owner sees it on Morning Brief or in web app
- Owner approves → MCP write tool fires with `decision_log_id` reference
- Owner rejects → recommendation is logged; no write fires

For graduated agents (proven outcome accuracy > threshold over time window), the write tool fires automatically. The recommendation still logs but with `auto_approved` flag.

The graduation criteria are documented per-agent in [TECH/14_agent_roster.md](14_agent_roster.md).

---

## 10. Observability

Every MCP call emits:

- CloudWatch metric: `Brain/MCP/tool_calls_total{tool, status, paradigm}`
- CloudWatch metric: `Brain/MCP/tool_duration_seconds{tool}`
- CloudWatch metric: `Brain/MCP/tool_cost_micros{tool, paradigm, brand}` (per cost-routing audit)
- OpenSearch log entry (centralised logging, TECH/09): every call with correlation IDs

X-Ray spans propagate across MCP boundaries via `traceparent` header.

---

## 11. Versioning

MCP tool schemas are versioned. Breaking changes increment the version:

- `memory.brand_fingerprint.query` (current)
- `memory.brand_fingerprint.query/v2` (next breaking change)

Old versions supported for ≥6 months after a new version ships. Clients can pin to a specific version via tool name or via `?version=v1` query parameter.

Non-breaking changes (new optional fields, additional output fields) ship under the same version.

---

## 12. SDKs

For external use:

- **Anthropic Claude (native MCP support):** zero-config connection. Add Brain as an MCP server in Claude's tool config; tools automatically available.
- **OpenAI Assistants:** Brain SDK exposes tool definitions that map to OpenAI's tool-use format.
- **Generic HTTP:** any client can POST to `/mcp/call_tool` with the JSON envelope above.

Internal SDKs in `packages/lib-mcp-clients/` (TS) and `pylibs/brain_mcp/` (Python) wrap the protocol for Brain's own services.

---

## 13. Why MCP Was Chosen

| Decision | Alternative Considered | Why MCP Won |
|----------|----------------------|-------------|
| **MCP for inter-agent** | Custom gRPC RPC, direct in-process calls | MCP's tool-use semantics are LLM-native; inter-agent inside an LLM reasoning loop benefits structurally |
| **MCP for external surface** | REST API, GraphQL | LLM clients (Claude, GPT) speak MCP natively; partners building agentic integrations connect with zero glue code |
| **MCP at api-gateway, not separate service** | Dedicated MCP service | Re-uses auth + multi-tenancy + rate limit at the edge; one less service to operate |
| **Schemas from same proto definitions** | Hand-written MCP schemas | Single source of truth; contracts cannot drift |

---

## 14. Open Questions

| # | Question | Owner | Resolution |
|---|----------|-------|-----------|
| 1 | Section 12 from source brief (truncated) — what specific MCP-details does the founder want overridden? | E1 + Founder | TBD when full brief available |
| 2 | Streaming protocol — SSE vs WebSocket? | E1 | SSE for now; WebSocket if MCP spec moves that direction or if Anthropic / OpenAI clients demand it |
| 3 | Brand-level MCP usage caps | E1 | Inherited from cost-routing per-brand monthly cap (TECH/12 §4 Layer 3) |
| 4 | Audit log retention for MCP calls vs ordinary API calls | E1 | Same — 7 years to S3 cold archive |
| 5 | Should brand-side webhooks register as MCP servers (so Brain can call them)? | E1 | Phase 4. Enterprise tier feature. |
| 6 | OAuth 2.1 PKCE flow for external partner MCP keys? | E1 | Phase 4. Phase 1-3 uses static API keys with scopes. |
