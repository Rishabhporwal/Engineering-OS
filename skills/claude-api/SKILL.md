---
name: claude-api
description: Claude backend behind the gateway — pinned IDs (Sonnet 4.6/Haiku 4.5), prompt caching (biggest lever), tool use, Batch API, thinking, errors. Calls route via the gateway.
---

# Claude API (Anthropic Messages API)

> **Note:** This is Brain's **local** `claude-api` skill (not the Claude Code bundled one). Brain-pinned model IDs, cost-router integration, per-brand monthly LLM cap. Always read this one over any generic bundled equivalent.

> **Read first — Claude is the frontier-default BACKEND behind the LiteLLM gateway.** App code calls the **LiteLLM gateway** (OpenAI-format), **NOT the Anthropic SDK directly**. The gateway routes `@paradigm("frontier_llm")` to **Claude Sonnet 4.6 as the eval-gated default** and `small_llm` to the cheapest eval-passing model. Routing, fallback, retries, semantic cache, and per-workspace budgets all live in the gateway — see [`llm-gateway`](../llm-gateway/SKILL.md). **This skill is the authority on the Claude-backend specifics**: pinned model IDs, prompt caching, tool use, Batch API, extended thinking. The SDK snippets describe **how the Claude backend behaves**; in service code those calls go *through the gateway*, not a direct `AsyncAnthropic()`.

## Why this matters for Brain

- **GMV % pricing only works because most calls are SQL or ML, not LLM** (Iron Law #4 — [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)). Every Claude call must be (a) part of the human-language interface boundary (Morning Brief synthesis, AI Chat, agent narrative wrap) or (b) bounded NL routed to Haiku.
- **Prompt caching is the single biggest cost lever.** ~90% saving on the cached portion of repeated prompts. Brand Fingerprint context (~3–10K tokens) reused across every brief synthesis = enormous savings.
- **Per-brand monthly LLM cap:** ₹3K Launch / ₹5K Growth / ₹15K Scale / ₹50K+ Enterprise — enforced as the LiteLLM virtual-key budget in the gateway, NOT a downstream alert.
- **Frontier-LLM creep above 1% of total calls is a tier-1 incident.** Every Sonnet call shows up in the cost-discipline dashboard.

## Brain model canon (NEVER use stale IDs)

| Model | Family alias | Pinned ID | When |
|---|---|---|---|
| **Sonnet 4.6** | `sonnet` | `claude-sonnet-4-6` | Morning Brief synthesis, AI Chat orchestration, agent narrative wrap |
| **Haiku 4.5** | `haiku` | `claude-haiku-4-5-20251001` | Classification, extraction, short rewrites, WhatsApp template personalisation |
| Opus 4.7 | `opus` | `claude-opus-4-7` | Reserved (heavy reasoning slots only — special-case approval) |

**Stale model IDs are bugs.** Don't write `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-sonnet-4-5`.

## Quick start (Claude-backend shape — routed through the gateway)

> The snippets show **how the Claude backend behaves** (message shape, caching, tool use). In service code these run **through the LiteLLM gateway via the OpenAI-format client** ([`llm-gateway`](../llm-gateway/SKILL.md)), not a direct `AsyncAnthropic()`.

```typescript
import Anthropic from '@anthropic-ai/sdk';
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Synthesize three signals for workspace 7d…' }],
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

## Critical rules (Brain canon)

**✅ Always:** use a Brain pinned model ID · set `max_tokens` explicitly (budget guard) · enable prompt caching for any repeated context > ~1K tokens · wrap with `@paradigm(...)` · stream long responses for AI Chat · retry with exponential backoff for 429/529 · validate user input before prompt injection ([`defense-in-depth-validation`](../defense-in-depth-validation/SKILL.md)) · set a request timeout (60s synthesis / 10s Haiku) · track tokens per call to the cost registry · return `tool_result` in the follow-up message.

**❌ Never:** expose API key client-side · skip `max_tokens` · use `*-latest` aliases · use a stale model ID · ignore `stop_reason` · assume single content block · skip error handling · mix message roles · store API key in logs/DB/cache · default to Sonnet (start at Haiku, escalate only when bounded NL fails).

## Prompt caching (the single biggest cost lever)

Caches are 5-minute TTL by default (or 1-hour with extended TTL). Savings compound on Brain's high-frequency synthesis (every workspace's brief at 06:55–07:15 IST shares its system prompt + tool catalogue).

```typescript
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  system: [
    { type: 'text', text: BRAIN_SYNTHESIS_SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } },  // ~3K tokens
  ],
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: brandFingerprint(workspaceId), cache_control: { type: 'ephemeral' } },  // ~5K tokens
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

Aim for **>70% cache_read rate** on Brain's high-frequency call sites.

## Cost + capability features (now standard)

Each is still subject to the `@paradigm` gate + per-brand cap — they make an *already-justified* LLM call cheaper/more capable, never an excuse to skip SQL/ML.

### Batch API — 50% cheaper, non-interactive bulk work

Runs Messages requests asynchronously at **50% of standard token cost** (results typically within an hour). Use for work **not** on the interactive path: the **23:55 IST outcome-attribution backfill** and **nightly insight generation**. Do **not** batch the 07:15 Morning Brief synthesis or AI Chat — latency-sensitive, stay synchronous.

```python
batch = client.messages.batches.create(requests=[
    {"custom_id": f"attribution-{workspace_id}-{date}",
     "params": {"model": "claude-sonnet-4-6", "max_tokens": 1024,
                "messages": [{"role": "user", "content": attribution_prompt(workspace_id, date)}]}}
    for workspace_id, date in nightly_jobs
])
```

### Extended / adaptive thinking (Sonnet 4.6)

Give the model a thinking budget for harder reasoning before it answers — where the *reasoning* is the hard part, not the writing (ambiguous multi-signal agent reasoning, cross-channel budget allocation).

```python
msg = client.messages.create(
    model="claude-sonnet-4-6", max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": cross_channel_allocation_prompt(...)}],
)
```

Thinking tokens count toward cost + the per-brand cap — budget deliberately; don't enable on bounded Haiku-class work.

### Files API (vision / creative-benchmark flows)

Upload a file once, reference by `file_id` across calls (instead of re-encoding bytes per request) — relevant to vision / creative-benchmark flows.

```python
f = client.beta.files.upload(file=("creative.png", open("creative.png", "rb"), "image/png"))
msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1024,
    messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "file", "file_id": f.id}},
        {"type": "text", "text": "Score this creative against the brand benchmark."}]}])
```

## Tool use (AI Chat — MCP-mediated)

```typescript
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6', max_tokens: 4096,
  tools: [{
    name: 'analytics_waterfall_compute',
    description: 'Compute the CM2 waterfall for a workspace + date range',
    input_schema: { type: 'object', properties: {
      workspace_id: { type: 'string', format: 'uuid' },
      date_from: { type: 'string', format: 'date' }, date_to: { type: 'string', format: 'date' },
    }, required: ['workspace_id', 'date_from', 'date_to'] },
  }],
  messages: [/* ... */],
});

if (msg.stop_reason === 'tool_use') {
  const toolUse = msg.content.find((b) => b.type === 'tool_use');
  // Route through Brain's MCP server, NOT a direct Anthropic Tool Use response — MCP is the contract.
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

Tool schemas are **generated from the same `.proto` files** as gRPC so the MCP tool catalogue and the Anthropic Tool Use schema never drift ([`mcp-protocol`](../mcp-protocol/SKILL.md), [`grpc-buf`](../grpc-buf/SKILL.md)). Routing through MCP preserves the Decision Log contract ([`decision-log`](../decision-log/SKILL.md)).

## Error handling — Brain wrapper

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

## Cost-cap enforcement (per-brand monthly LLM budget)

The per-brand monthly cap is now the **LiteLLM virtual-key budget in the gateway** (the runtime mechanism; thresholds unchanged). The conceptual shape:

```typescript
async function callClaudeWithBudget(workspaceId: string, fn: () => Promise<...>) {
  const spentInr = await costRegistry.monthToDateForWorkspace(workspaceId);
  const cap = workspaces.budget(workspaceId);  // ₹3K Launch / ₹5K Growth / ₹15K Scale / ...
  if (spentInr >= cap) throw new BudgetExhaustedError({ workspaceId, spentInr, cap });
  if (spentInr >= cap * 0.8) log().warn({ workspaceId, spentInr, cap }, 'llm_budget.throttle');  // route to Haiku where bounded NL ok
  const result = await fn();
  await costRegistry.record(workspaceId, result.usage);
  return result;
}
```

### Phase-gate requirement (non-negotiable — architecture review 2026-05-16)

**The per-brand monthly LLM cap MUST be live before AI Chat ships in W18.** AI Chat is the feature most likely to push a brand past their tier cap (5 → 50 msg/day ≈ ₹1,500/brand/month, half the Launch ₹3K cap on chat alone). Layer 3 of the four-layer cost control (Layer 1 `@paradigm`, Layer 2 token budget, **Layer 3 per-brand cap**, Layer 4 global dashboard alarm).

**Acceptance criteria for "the cap is live":**
- The **LiteLLM gateway is the only entry point** any Brain service uses to reach an LLM; the per-workspace **virtual-key budget** carries the cap (supersedes the `callClaudeWithBudget` wrapper above). **Direct `client.messages.create()` / `AsyncAnthropic()` calls in app code fail PR review** — they bypass routing/fallback/semantic-cache/budget. See [`llm-gateway`](../llm-gateway/SKILL.md).
- Costs ingested per call (input/cached/output + the **resolved model**) with per-workspace partition.
- Throttle at 70% (warn + pause non-critical; route frontier-eligible to a cheaper eval-passing tier); hard-stop at 100% (gateway serves critical-path only). CloudWatch alarm at 90% pages Maya. Brand-facing dashboard shows month-to-date spend vs cap.

See `memory/decisions/ADR-DRAFT-2026-05-16-stack-review.md` §Recommendations #6.

## Top errors (with Brain context)

1. **Rate limit 429** — use the backoff wrapper. Frequent 429 on Haiku usually means misrouting work that could be SQL/ML — check the paradigm audit.
2. **Prompt cache not activating** — `cache_read_input_tokens: 0` on a stable prompt: cached block changed / block < 1024 tokens / `cache_control` on the wrong block.
3. **Tool use schema invalid** — `input_schema` must be JSON Schema with `type: 'object'`; generate from proto rather than copying a Zod schema ([`grpc-buf`](../grpc-buf/SKILL.md)).
4. **Sonnet used where Haiku would do** — caught in the paradigm audit at PR time; Aryan blocks.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| intelligence-service call sites | **Maya** | canon/technical-requirements.md |
| Cost-cap registry + paradigm audit | **Maya** + **Aryan** | `cost-routing-paradigms` |
| MCP tool integration | **Vikram** + **Maya** | `mcp-protocol` |
| Prompt caching hit-rate dashboards | **Maya** + **Jatin** | `observability` |
| Per-brand budget enforcement | **Maya** | `llm-gateway` (virtual-key budget) |

Related: [`llm-gateway`](../llm-gateway/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`mcp-protocol`](../mcp-protocol/SKILL.md) · [`grpc-buf`](../grpc-buf/SKILL.md) · [`defense-in-depth-validation`](../defense-in-depth-validation/SKILL.md) · [`observability`](../observability/SKILL.md)
</content>
