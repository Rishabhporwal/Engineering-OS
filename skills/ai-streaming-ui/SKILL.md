---
name: ai-streaming-ui
description: Reference implementation — AI-native frontend surfaces (Vercel AI SDK + assistant-ui) — streaming chat, token-by-token rendering, tool-call/generative UI, stop/abort, optimistic + error/retry states, and trust UX (citations, loading, guardrails). Owner Frontend/Web Eng + AI/ML Eng.
---

# AI Streaming UI (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **AI-frontend seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to the Vercel AI SDK + assistant-ui, a custom SSE/WebSocket layer, or another toolkit. The *patterns* — stream tokens as they arrive, render tool-calls/generative UI, always offer stop/abort, handle partial + error states, and design for trust — are what transfer; the SDK is the example.

Streaming AI surfaces are now a first-class part of the web product, not an experiment. This skill is the frontend counterpart to the backend `claude-api`/`llm-gateway`/`agent-orchestration-langgraph` work. **Owner:** Frontend/Web Engineer (the UI) + AI/ML Engineer (the model/agent contract behind it). Builds on `frontend-web`. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Stream, don't block.** Render tokens as they arrive (SSE/streaming). A spinner for 8 seconds then a wall of text is the wrong UX; first-token latency is the metric users feel. Use the SDK's streaming primitives (`useChat`/`streamText`).
2. **Stop/abort is always available.** Every in-flight generation can be cancelled by the user, and cancellation **actually aborts the upstream request** (AbortController → gateway) so it stops billing tokens (`cost-routing-paradigms`). A stop button that only hides the UI is a lie.
3. **Partial + error + retry are designed states, not afterthoughts.** Handle: streaming, partial-then-error mid-stream, tool-call-in-progress, refusal/guardrail, rate-limit, and network drop — each with a clear UI and a retry path. The happy path is the easy 20%.
4. **Tool calls + generative UI are rendered, not hidden.** When the agent calls a tool or returns structured/generative UI, render it as a first-class component (a chart, a form, a confirmation) — not raw JSON. Streamed UI maps to the agent's tool contract.
5. **Trust UX: show sources, state, and limits.** Citations for RAG answers (link to source — `rag-retrieval`), visible "thinking/using tool X" state, and honest handling of low-confidence/guardrail responses. Money/metrics rendered from the registry (`metric-engine`), never invented by the model.

## Shape (Vercel AI SDK)
```tsx
const { messages, input, handleSubmit, stop, status, error, reload } = useChat({ api: "/api/chat" });
// status: 'submitted' | 'streaming' | 'ready' | 'error'  → drive distinct UI states
{messages.map(m => <Message key={m.id} parts={m.parts} />)}   // parts: text | tool-call | tool-result | ui
{status === "streaming" && <button onClick={stop}>Stop</button>}   // real abort
{error && <Retry onClick={reload} message={friendly(error)} />}
```
- The server route streams from the **gateway** (`llm-gateway`) — the frontend never holds a provider key. Tenant/auth context flows through the route (`auth-and-access`).
- Generative UI: the agent emits typed UI parts; the client maps each part type to a component (the same contract the agent's tools declare).

## Accessibility + performance (with `accessibility`, `web-performance`)
- Streaming text must be announced sanely to screen readers (aria-live with sensible granularity — not every token); respect reduced-motion for typewriter effects.
- Keep the streaming render cheap (don't re-render the whole thread per token); virtualize long threads. Code-split the AI surface so it doesn't bloat the main bundle.

## Operability
- Surface online quality signals (thumbs/edit/regenerate) back to `ai-observability-tracing` → `agent-evaluation`. The UI is where production feedback is captured.
- Show degraded state honestly when the tenant hits a cost cap (graceful degradation, not a crash — `cost-routing-paradigms`).

## Anti-patterns
Block-then-dump instead of streaming · a stop button that doesn't abort the upstream call (keeps billing) · only handling the happy path · rendering raw tool-call JSON · no citations on RAG answers · model-generated numbers shown as fact (bypassing the metric registry) · provider key in the browser · token-by-token full-thread re-render (jank) · ignoring screen-reader/reduced-motion for streaming.
