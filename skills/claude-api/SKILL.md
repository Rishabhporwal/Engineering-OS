---
name: claude-api
description: Claude as the frontier-default model backend behind the gateway — pinned IDs, prompt caching (biggest lever), tool use, Batch API, thinking, errors. Calls route via the gateway.
---

# Claude API (Anthropic Messages API)

> **Reference implementation.** This skill documents one concrete binding of the model-backend seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the LLM seam to a different provider. The *patterns* here (pinned IDs, prompt caching as the top cost lever, typed tool use through your own tool layer, batch for non-interactive work, per-tenant budget enforcement) transfer; the Claude specifics are the worked example.

> **Note:** This is the **local** `claude-api` skill (not the Claude Code bundled one). It carries pinned model IDs, cost-router integration, and the per-tenant monthly model cap shape. Always read this one over any generic bundled equivalent.

> **Read first — Claude is the frontier-default BACKEND behind the model gateway.** App code calls the **model gateway** (OpenAI-format), **NOT the Anthropic SDK directly**. The gateway routes the "frontier" tier to Claude Sonnet as the eval-gated default and the "small" tier to the cheapest eval-passing model. Routing, fallback, retries, semantic cache, and per-tenant budgets all live in the gateway — see [`llm-gateway`](../llm-gateway/SKILL.md). **This skill is the authority on the Claude-backend specifics**: pinned model IDs, prompt caching, tool use, Batch API, extended thinking. The SDK snippets describe **how the Claude backend behaves**; in service code those calls go *through the gateway*, not a direct `AsyncAnthropic()`.

## Why this matters

- **Usage-based pricing only works because most calls are deterministic or ML, not LLM** (the cost doctrine — [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)). Every Claude call must be (a) part of the natural-language interface boundary (synthesis, chat, agent narrative wrap) or (b) bounded NL routed to the small tier.
- **Prompt caching is the single biggest cost lever.** ~90% saving on the cached portion of repeated prompts. Reusing a stable context block (~3–10K tokens) across many calls = enormous savings.
- **Per-tenant monthly model cap** — enforced as the gateway's per-key (virtual-key) budget, NOT a downstream alert.
- **Frontier-LLM creep above ~1% of total calls is a tier-1 incident.** Every frontier call shows up in the cost-discipline dashboard.

## Model canon (NEVER use stale IDs)

| Model | Family alias | Pinned ID | When |
|---|---|---|---|
| **Sonnet 4.6** | `sonnet` | `claude-sonnet-4-6` | synthesis, chat orchestration, agent narrative wrap |
| **Haiku 4.5** | `haiku` | `claude-haiku-4-5-20251001` | classification, extraction, short rewrites, template personalisation |
| Opus 4.7 | `opus` | `claude-opus-4-7` | Reserved (heavy reasoning slots only — special-case approval) |

**Stale model IDs are bugs.** Don't write `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-sonnet-4-5`. Confirm the current pinned IDs against the bundled `claude-api` reference / provider docs before shipping.

## Quick start (Claude-backend shape — routed through the gateway)

> The snippets show **how the Claude backend behaves** (message shape, caching, tool use). In service code these run **through the model gateway via the OpenAI-format client** ([`llm-gateway`](../llm-gateway/SKILL.md)), not a direct `AsyncAnthropic()`.

```typescript
import Anthropic from '@anthropic-ai/sdk';
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Synthesize three signals for the last 7d…' }],
});
```

```python
import anthropic
client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[{"role": "user", "content": "Classify this ticket: ..."}],
)
```

## Critical rules

**✅ Always:** use a pinned model ID · set `max_tokens` explicitly (budget guard) · enable prompt caching for any repeated context > ~1K tokens · route through the cost gate ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)) · stream long responses for chat · retry with exponential backoff for 429/529 · validate user input before prompt injection ([`agentic-safety`](../agentic-safety/SKILL.md)) · set a request timeout (60s synthesis / 10s small-model) · track tokens per call to the cost registry · return `tool_result` in the follow-up message.

**❌ Never:** expose API key client-side · skip `max_tokens` · use `*-latest` aliases · use a stale model ID · ignore `stop_reason` · assume single content block · skip error handling · mix message roles · store API key in logs/DB/cache · default to the frontier model (start at the small tier, escalate only when bounded NL fails).

## Prompt caching (the single biggest cost lever)

Caches are 5-minute TTL by default (or 1-hour with extended TTL). Savings compound on high-frequency synthesis (many tenants' batch jobs share a system prompt + tool catalogue).

```typescript
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  system: [
    { type: 'text', text: SYNTHESIS_SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } },  // ~3K tokens
  ],
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: tenantContext(tenantId), cache_control: { type: 'ephemeral' } },  // ~5K tokens
      { type: 'text', text: `Today is ${date}. Synthesize three signals from the last 24h.` },
    ],
  }],
});
console.log('Cache reads:', msg.usage.cache_read_input_tokens);
```

### When caching DOESN'T hit (top causes)

| Symptom | Cause | Fix |
|---|---|---|
| `cache_read_input_tokens: 0` | First call in the 5-min window | Expected once per window per breakpoint |
| Still 0 on the 2nd call | Cached block changed (even one char) | Make the cached block byte-stable |
| Cached block < 1024 tokens | Caching only works on blocks ≥ 1024 tokens | Pad or combine with other context |
| `cache_control` on the wrong block | Must be on the LAST block of cached content | Move to the end of the cacheable region |

Aim for **>70% cache_read rate** on high-frequency call sites.

## Cost + capability features (now standard)

Each is still subject to the cost gate + per-tenant cap — they make an *already-justified* LLM call cheaper/more capable, never an excuse to skip deterministic/ML.

### Batch API — 50% cheaper, non-interactive bulk work

Runs Messages requests asynchronously at **50% of standard token cost** (results typically within an hour). Use for work **not** on the interactive path: nightly attribution/outcome backfills and nightly insight generation. Do **not** batch latency-sensitive synthesis or chat — keep those synchronous.

```python
batch = client.messages.batches.create(requests=[
    {"custom_id": f"attribution-{tenant_id}-{date}",
     "params": {"model": "claude-sonnet-4-6", "max_tokens": 1024,
                "messages": [{"role": "user", "content": attribution_prompt(tenant_id, date)}]}}
    for tenant_id, date in nightly_jobs
])
```

### Extended / adaptive thinking (Sonnet 4.6)

Give the model a thinking budget for harder reasoning before it answers — where the *reasoning* is the hard part, not the writing (ambiguous multi-signal agent reasoning, cross-channel allocation).

```python
msg = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": cross_channel_allocation_prompt(...)}],
)
```

Thinking tokens count toward cost + the per-tenant cap — budget deliberately; don't enable on bounded small-model work.

### Files API (vision / benchmark flows)

Upload a file once, reference by `file_id` across calls (instead of re-encoding bytes per request) — relevant to vision / benchmark flows.

```python
f = client.beta.files.upload(file=("creative.png", open("creative.png", "rb"), "image/png"))
msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1024,
    messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "file", "file_id": f.id}},
        {"type": "text", "text": "Score this against the benchmark."}]}])
```

## Tool use (chat — MCP-mediated)

```typescript
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6', max_tokens: 4096,
  tools: [{
    name: 'analytics_waterfall_compute',
    description: 'Compute the metric waterfall for a tenant + date range',
    input_schema: { type: 'object', properties: {
      tenant_id: { type: 'string', format: 'uuid' },
      date_from: { type: 'string', format: 'date' }, date_to: { type: 'string', format: 'date' },
    }, required: ['tenant_id', 'date_from', 'date_to'] },
  }],
  messages: [/* ... */],
});

if (msg.stop_reason === 'tool_use') {
  const toolUse = msg.content.find((b) => b.type === 'tool_use');
  // Route through the MCP server, NOT a direct Anthropic Tool Use response — MCP is the contract.
  const result = await mcp.invoke(toolUse.name, toolUse.input);
  const follow = await client.messages.create({
    model: 'claude-sonnet-4-6', max_tokens: 4096, tools: [/* same */],
    messages: [
      { role: 'assistant', content: msg.content },
      { role: 'user', content: [{ type: 'tool_result', tool_use_id: toolUse.id, content: JSON.stringify(result) }] },
    ],
  });
}
```

Tool schemas are **generated from the same `.proto` files** as gRPC so the MCP tool catalogue and the Anthropic Tool Use schema never drift ([`mcp-protocol`](../mcp-protocol/SKILL.md), [`grpc-buf`](../grpc-buf/SKILL.md)). Routing through MCP preserves the audit-log contract ([`decision-log`](../decision-log/SKILL.md)).

## Error handling — wrapper

```typescript
async function anthropicCall<T>(fn: () => Promise<T>, opts: { maxRetries?: number } = {}): Promise<T> {
  const maxRetries = opts.maxRetries ?? 3;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try { return await fn(); }
    catch (err: any) {
      if (err.status === 429 || err.status === 529) {           // rate limit / overloaded
        const delay = err.headers?.['retry-after'] ? parseInt(err.headers['retry-after']) * 1000 : 1000 * 2 ** attempt;
        await new Promise((r) => setTimeout(r, delay)); continue;
      }
      if (err.status >= 400 && err.status < 500) throw err;     // 4xx — don't retry
      if (err.status >= 500) { await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt)); continue; }
      throw err;
    }
  }
  throw new Error('anthropic.max_retries_exceeded');
}
```

## Cost-cap enforcement (per-tenant monthly model budget)

The per-tenant monthly cap is the **gateway's per-key (virtual-key) budget** (the runtime mechanism). The conceptual shape:

```typescript
async function callWithBudget(tenantId: string, fn: () => Promise<...>) {
  const spentMinor = await costRegistry.monthToDateForTenant(tenantId);
  const cap = tenants.budgetMinor(tenantId);  // per-tier cap, in currency minor units
  if (spentMinor >= cap) throw new BudgetExhaustedError({ tenantId, spentMinor, cap });
  if (spentMinor >= cap * 0.8) log().warn({ tenantId, spentMinor, cap }, 'llm_budget.throttle');  // route to small tier where bounded NL ok
  const result = await fn();
  await costRegistry.record(tenantId, result.usage);
  return result;
}
```

### Phase-gate requirement (non-negotiable)

**The per-tenant monthly model cap MUST be live before any high-volume chat surface ships.** Interactive chat is the feature most likely to push a tenant past their cap. It is one layer of the four-layer cost control (Layer 1 the cost gate, Layer 2 token budget, **Layer 3 per-tenant cap**, Layer 4 global dashboard alarm).

**Acceptance criteria for "the cap is live":**
- The **model gateway is the only entry point** any service uses to reach an LLM; the per-tenant **virtual-key budget** carries the cap (supersedes the `callWithBudget` wrapper above). **Direct `client.messages.create()` / `AsyncAnthropic()` calls in app code fail PR review** — they bypass routing/fallback/semantic-cache/budget. See [`llm-gateway`](../llm-gateway/SKILL.md).
- Costs ingested per call (input/cached/output + the **resolved model**) with per-tenant partition.
- Throttle at ~70% (warn + pause non-critical; route frontier-eligible to a cheaper eval-passing tier); hard-stop at 100% (gateway serves critical-path only). An alarm at ~90% pages the AI/ML Engineer. A tenant-facing dashboard shows month-to-date spend vs cap.

## Top errors (with context)

1. **Rate limit 429** — use the backoff wrapper. Frequent 429 on the small tier usually means misrouting work that could be deterministic/ML — check the cost audit.
2. **Prompt cache not activating** — `cache_read_input_tokens: 0` on a stable prompt: cached block changed / block < 1024 tokens / `cache_control` on the wrong block.
3. **Tool use schema invalid** — `input_schema` must be JSON Schema with `type: 'object'`; generate from proto rather than copying a Zod schema ([`grpc-buf`](../grpc-buf/SKILL.md)).
4. **Frontier model used where the small tier would do** — caught in the cost audit at PR time; the Architect blocks.

## Wiring

| Concern | Role | Reference |
|---|---|---|
| intelligence-service call sites | **AI/ML Engineer** | `STACK.md` |
| Cost-cap registry + cost audit | **AI/ML Engineer** + **Architect** | `cost-routing-paradigms` |
| MCP tool integration | **Backend Engineer** + **AI/ML Engineer** | `mcp-protocol` |
| Prompt caching hit-rate dashboards | **AI/ML Engineer** + **Platform/SRE** | `observability` |
| Per-tenant budget enforcement | **AI/ML Engineer** | `llm-gateway` (virtual-key budget) |

Related: [`llm-gateway`](../llm-gateway/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`mcp-protocol`](../mcp-protocol/SKILL.md) · [`grpc-buf`](../grpc-buf/SKILL.md) · [`agentic-safety`](../agentic-safety/SKILL.md) · [`observability`](../observability/SKILL.md)
