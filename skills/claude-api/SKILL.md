---
name: claude-api
description: Anthropic Messages API for the intelligence-service — streaming, prompt caching (the single biggest cost lever for Brain), tool use for AI Chat, vision, error handling. Models pinned to Brain canon — Sonnet 4.6 for synthesis, Haiku 4.5 for bounded NL. Use when wiring a new Claude call site in Maya's services, when adding a new MCP-mediated tool use flow, when investigating cost-cap breaches, when prompt caching isn't hitting.
---

# Claude API (Anthropic Messages API)

> **Note:** This is Brain's **local** `claude-api` skill (not the Claude Code bundled one). Brain-pinned model IDs (Sonnet 4.6 / Haiku 4.5), Brain's cost-router integration, Brain's per-brand monthly LLM cap enforcement. Always read this one over any generic bundled equivalent.

Brain's intelligence layer (Maya, see canon/technical-requirements.md) is built on Claude — **Sonnet 4.6** for multi-step synthesis and brand-voice, **Haiku 4.5** for bounded NL (classification, extraction, short rewrites). This skill is the operational depth for every call site that touches the Anthropic SDK.

## Why this matters for Brain

- **GMV % pricing only works because most calls are SQL or ML, not LLM** (prompts/system-prompt.md, Iron Law #4). Every Claude call must be either (a) part of the human-language interface boundary (Morning Brief synthesis, AI Chat, agent narrative wrap) or (b) bounded NL routed to Haiku.
- **Prompt caching is the single biggest cost lever.** 90% cost savings on the cached portion of repeated prompts. Brand Fingerprint context (~3–10K tokens) reused across every brief synthesis = enormous savings.
- **Per-brand monthly LLM cap** (`memory/business-context.md`): ₹3K founding / ₹5K standard / ₹15K growth / ₹50K+ enterprise. Cap enforcement is in the SDK wrapper, NOT a downstream alert.
- **Frontier-LLM creep above 1% of total calls is a tier-1 incident** (see canon/technical-requirements.md). Every Sonnet call shows up in the cost-discipline dashboard.

## Brain model canon (NEVER use stale IDs)

| Model | Family alias | Pinned ID | When |
|---|---|---|---|
| **Sonnet 4.6** | `sonnet` | `claude-sonnet-4-6` | Morning Brief synthesis, AI Chat orchestration, agent narrative wrap |
| **Haiku 4.5** | `haiku` | `claude-haiku-4-5-20251001` | Classification, extraction, short rewrites, WhatsApp template personalisation |
| Opus 4.7 | `opus` | `claude-opus-4-7` | Reserved (heavy reasoning slots only — special-case approval) |

**Stale model IDs are bugs.** Don't write `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-sonnet-4-5`. prompts/system-prompt.md is explicit on this.

## Quick start (Node — intelligence-service)

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Synthesize three signals for workspace 7d…' }],
});
console.log(msg.content[0].type === 'text' ? msg.content[0].text : '');
```

## Quick start (Python — intelligence-service)

```python
import anthropic

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=512,
    messages=[{"role": "user", "content": "Classify this ticket: ..."}],
)
print(msg.content[0].text)
```

## Critical rules (Brain canon)

### ✅ Always

1. **Use a Brain pinned model ID** (Sonnet 4.6 / Haiku 4.5)
2. **Set `max_tokens` explicitly** — required, and a budget guard
3. **Enable prompt caching** for any repeated context > ~1K tokens (Brand Fingerprint, system prompts, tool catalogues)
4. **Wrap with `@paradigm("small_llm" | "frontier_llm", model=…, token_budget=…)`** (the cost-routing decorator)
5. **Stream long responses** for AI Chat UX (`stream: true`)
6. **Implement retry with exponential backoff** for 429 and 529
7. **Validate user input** before injection into prompts (prompt injection is real — see `defense-in-depth-validation`)
8. **Set a request timeout** (Brain default: 60s for synthesis, 10s for Haiku classification)
9. **Track tokens per call** to the cost-discipline registry
10. **Use tool use correctly** — return `tool_result` in the follow-up message

### ❌ Never

1. **Expose API key client-side** — calls go through intelligence-service, never browser/mobile
2. **Skip `max_tokens`** — API errors, and you lose the cost guard
3. **Use `*-latest` model aliases** — pin the version
4. **Use a stale model ID** (`claude-3-*`, anything below 4.5/4.6)
5. **Ignore `stop_reason`** — `tool_use` vs `end_turn` vs `max_tokens` mean different things downstream
6. **Assume single content block** — `content` is an array
7. **Skip error handling**
8. **Mix message roles incorrectly** — alternate user/assistant
9. **Store API key in logs / DB / cache** (PII redaction in `observability` covers this)
10. **Default to Sonnet** — start at Haiku; escalate only when bounded NL fails

## Prompt caching (the single biggest cost lever)

Caches are 5-minute TTL by default (or 1-hour with cache control + extended TTL). The savings compound on Brain's high-frequency synthesis (every workspace's brief at 06:55–07:15 IST shares its system prompt + tool catalogue).

```typescript
// Brain pattern: cache the system prompt + Brand Fingerprint + tool catalogue
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 1024,
  system: [
    {
      type: 'text',
      text: BRAIN_SYNTHESIS_SYSTEM_PROMPT,         // ~3K tokens
      cache_control: { type: 'ephemeral' },        // cache this
    },
  ],
  messages: [
    {
      role: 'user',
      content: [
        {
          type: 'text',
          text: brandFingerprint(workspaceId),     // ~5K tokens — workspace-specific
          cache_control: { type: 'ephemeral' },    // cache this too
        },
        {
          type: 'text',
          text: `Today is ${date}. Synthesize three signals from the last 24h.`,
        },
      ],
    },
  ],
});

// Check cache hit
console.log('Cache reads:', msg.usage.cache_read_input_tokens);
console.log('Cache writes:', msg.usage.cache_creation_input_tokens);
```

### When caching DOESN'T hit (top causes)

| Symptom | Cause | Fix |
|---|---|---|
| `cache_read_input_tokens: 0` | First call in the 5-min window | Expected once per window per cache breakpoint |
| Still 0 on the 2nd call | Content of the cached block changed (even by one char) | Make the cached block byte-stable |
| Cached block < 1024 tokens | Caching only works on blocks ≥ 1024 tokens | Pad or combine with other context |
| `cache_control` on the wrong block | It must be on the LAST block of cached content | Move to the end of the cacheable region |

Aim for **>70% cache_read rate** on Brain's high-frequency call sites.

## Cost + capability features (now standard — Brain call sites)

Beyond prompt caching, three Anthropic features are now standard and Brain-relevant. Each is still subject to the `@paradigm` gate + per-brand cap — they make an *already-justified* LLM call cheaper or more capable, never an excuse to skip SQL/ML.

### Batch API — 50% cheaper, for non-interactive bulk work

The Batch API runs a set of Messages requests asynchronously at **50% of standard token cost** (results typically within an hour, well under the 24h SLA). Use it for any LLM work that **isn't** on the interactive path:

- **23:55 IST outcome-attribution backfill** — the nightly 7d/30d Decision Log outcome write-ups across all workspaces are a perfect batch (no user is waiting; halve the bill).
- **Nightly insight generation** — bulk narrative/summary passes that feed the next morning's brief.

Do **not** batch the 07:15 Morning Brief synthesis or AI Chat — those are latency-sensitive and stay on the synchronous path.

```python
# Python — submit a batch of synthesis/attribution jobs at 50% cost
batch = client.messages.batches.create(requests=[
    {
        "custom_id": f"attribution-{workspace_id}-{date}",
        "params": {
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": attribution_prompt(workspace_id, date)}],
        },
    }
    for workspace_id, date in nightly_jobs
])
# poll batch.id → retrieve results; each still records tokens to the cost registry
```

### Extended / adaptive thinking (Sonnet 4.6)

Sonnet 4.6 supports **extended (adaptive) thinking** — give the model a thinking budget for harder reasoning before it answers. Use it where the *reasoning* is the hard part, not the writing:

- **Agent reasoning** on ambiguous multi-signal situations.
- **Cross-channel budget allocation** (the AICMO-Cross-Channel reasoning over response curves before it narrates).

```python
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 4000},  # adaptive reasoning budget
    messages=[{"role": "user", "content": cross_channel_allocation_prompt(...)}],
)
```

Thinking tokens count toward cost + the per-brand cap — budget them deliberately; don't enable thinking on bounded Haiku-class work.

### Files API (vision / creative-benchmark flows)

The **Files API** uploads a file once and references it by `file_id` across calls (instead of re-encoding bytes per request) — relevant to Brain's **vision / creative-benchmark** flows (e.g. evaluating ad creative). Cache-friendly and avoids re-sending large image payloads.

```python
f = client.beta.files.upload(file=("creative.png", open("creative.png", "rb"), "image/png"))
msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "file", "file_id": f.id}},
        {"type": "text", "text": "Score this creative against the brand benchmark."},
    ]}],
)
```

## Tool use (AI Chat — MCP-mediated)

```typescript
const msg = await client.messages.create({
  model: 'claude-sonnet-4-6',
  max_tokens: 4096,
  tools: [
    {
      name: 'analytics_waterfall_compute',
      description: 'Compute the CM2 waterfall for a workspace + date range',
      input_schema: {
        type: 'object',
        properties: {
          workspace_id: { type: 'string', format: 'uuid' },
          date_from:    { type: 'string', format: 'date' },
          date_to:      { type: 'string', format: 'date' },
        },
        required: ['workspace_id', 'date_from', 'date_to'],
      },
    },
  ],
  messages: [/* ... */],
});

if (msg.stop_reason === 'tool_use') {
  const toolUse = msg.content.find((b) => b.type === 'tool_use');
  // Route the tool call through Brain's MCP server, NOT a direct Anthropic Tool Use response
  // (see canon/technical-requirements.md — MCP is the contract; this Anthropic Tool Use is just the trigger)
  const result = await mcp.invoke(toolUse.name, toolUse.input);

  const follow = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    tools: [/* same */],
    messages: [
      // ... prior history ...
      { role: 'assistant', content: msg.content },
      {
        role: 'user',
        content: [{ type: 'tool_result', tool_use_id: toolUse.id, content: JSON.stringify(result) }],
      },
    ],
  });
}
```

Tool schemas in Brain are **generated from the same `.proto` files** as gRPC so the MCP tool catalogue and the Anthropic Tool Use schema never drift (see `mcp-protocol` and `grpc-buf`).

## Error handling — Brain wrapper

```typescript
async function anthropicCall<T>(fn: () => Promise<T>, opts: { maxRetries?: number } = {}): Promise<T> {
  const maxRetries = opts.maxRetries ?? 3;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err: any) {
      // 429 rate limit, 529 overloaded
      if (err.status === 429 || err.status === 529) {
        const retryAfterHdr = err.headers?.['retry-after'];
        const delay = retryAfterHdr ? parseInt(retryAfterHdr) * 1000 : 1000 * 2 ** attempt;
        log().warn({ status: err.status, attempt, delayMs: delay }, 'anthropic.retry');
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      // 4xx (other) — don't retry; log + throw
      if (err.status >= 400 && err.status < 500) {
        log().error({ status: err.status, body: err.error }, 'anthropic.client_error');
        throw err;
      }
      // 5xx — retry with backoff
      if (err.status >= 500) {
        const delay = 1000 * 2 ** attempt;
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }
  throw new Error('anthropic.max_retries_exceeded');
}
```

## Cost-cap enforcement (per-brand monthly LLM budget)

```typescript
async function callClaudeWithBudget(workspaceId: string, fn: () => Promise<...>) {
  const spentInr = await costRegistry.monthToDateForWorkspace(workspaceId);
  const cap = workspaces.budget(workspaceId);  // ₹3K founding / ₹5K standard / ...
  if (spentInr >= cap) {
    throw new BudgetExhaustedError({ workspaceId, spentInr, cap });
  }
  if (spentInr >= cap * 0.8) {
    // Throttle Sonnet calls; route to Haiku where bounded NL is acceptable
    log().warn({ workspaceId, spentInr, cap }, 'llm_budget.throttle');
  }
  const result = await fn();
  await costRegistry.record(workspaceId, result.usage);
  return result;
}
```

`cost-routing-paradigms` skill has the full paradigm-decorator pattern; this is the budget enforcement piece.

### Phase-gate requirement (non-negotiable — from architecture review 2026-05-16)

**The per-brand monthly LLM cap MUST be live before AI Chat ships in W18.** AI Chat is the single feature most likely to push a brand past their tier cap — a moderately engaged user moves from 5 msg/day → 50 msg/day, which alone climbs to ~₹1,500/brand/month (half the founding-cohort ₹3K cap, on chat alone).

The throttle is Layer 3 of the four-layer cost control (per canon/technical-requirements.md):
- Layer 1 — paradigm decorator (`@paradigm`)
- Layer 2 — per-feature token budget (max_tokens, cache reuse)
- **Layer 3 — per-brand monthly cap (THIS — the `callClaudeWithBudget` wrapper above)**
- Layer 4 — global cost-discipline dashboard alarm (Jatin pages on per-brand burn > 100% of monthly budget)

**Acceptance criteria for "the cap is live":**
- The `callClaudeWithBudget` wrapper (or equivalent) is the only entry point any Brain service uses to call the Anthropic SDK. Direct `client.messages.create()` calls fail PR review.
- Costs ingested into `cost_registry` per call (Sonnet input/cached/output + Haiku input/output) with per-workspace partition.
- Throttling kicks in at 80% of cap (warn log + route Sonnet-eligible to Haiku where bounded NL is acceptable); hard-stop at 100% (Layer 3 raises `BudgetExhaustedError`).
- CloudWatch alarm at 90% of cap pages Maya (next-day budget review with brand).
- Brand-facing dashboard shows month-to-date LLM spend vs cap (transparency builds trust, prevents end-of-month bill shock).

See `memory/decisions/ADR-DRAFT-2026-05-16-stack-review.md` §Recommendations #6.

## Top errors (with Brain context)

### 1. Rate limit 429

Use the backoff wrapper above. If 429 is frequent on Haiku, you're probably misrouting work that could be SQL or ML — check the paradigm audit.

### 2. Prompt cache not activating

`cache_read_input_tokens: 0` on a stable system prompt. Causes (in order of frequency for Brain): the cached block changed (Brand Fingerprint regenerated with a different timestamp baked in); block < 1024 tokens (too small to cache); `cache_control` on the wrong block.

### 3. Tool use schema invalid

`input_schema` must be JSON Schema with `type: 'object'`. The mismatch is usually that you copied a Zod schema directly — use `zod-to-json-schema` or generate from proto (preferred — see `grpc-buf`).

### 4. Sonnet used where Haiku would do

Catch in the paradigm audit at PR time. Aryan blocks the PR.

## Best practices (Brain)

- **Start at Haiku.** Escalate to Sonnet only when bounded NL provably fails for the task.
- **Cache the system prompt + tool catalogue + Brand Fingerprint** — they're huge and stable.
- **Pin model versions.** Never `*-latest`.
- **Wrap every call** with the cost-cap + budget guard.
- **Log token usage** at INFO level per call (`observability` covers PII).
- **Stream user-facing responses** (AI Chat).
- **Tool use through MCP**, not directly — preserves the Decision Log contract.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| intelligence-service call sites | **Maya** | canon/technical-requirements.md |
| Cost-cap registry + paradigm audit | **Maya** + **Aryan** | canon/technical-requirements.md, `cost-routing-paradigms` |
| MCP tool integration | **Vikram** + **Maya** | canon/technical-requirements.md, `mcp-protocol` |
| Prompt caching hit-rate dashboards | **Maya** + **Jatin** | `observability` |
| Per-brand budget enforcement | **Maya** | canon/technical-requirements.md (budget) |

Related Brain skills: `cost-routing-paradigms` (the @paradigm decorator), `mcp-protocol` (tool catalogue), `grpc-buf` (proto-driven schemas), `defense-in-depth-validation` (prompt injection guards), `observability` (token usage logging).
