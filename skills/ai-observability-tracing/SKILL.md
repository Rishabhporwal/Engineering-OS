---
name: ai-observability-tracing
description: Observability for LLM/agent systems — OpenTelemetry GenAI semantic conventions (gen_ai.* spans), trace every model/tool/agent step, token + cost + latency attribution, online quality signals. Vendor-neutral instrumentation (Langfuse/Phoenix as backends). Owner AI/ML + ML Platform Eng.
---

# AI Observability & Tracing (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **LLM/agent-observability seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the backend to Langfuse, Arize Phoenix, Braintrust, or any OTLP store. The *pattern* — instrument once with **OpenTelemetry GenAI semantic conventions** (`gen_ai.*`), so the backend is swappable — is what transfers; the backend is an example.

The app-spine `observability` skill covers logs/metrics/traces for services. This skill covers the **model/agent layer it doesn't**: every prompt, completion, tool call, retrieval, and agent step as a span, with token/cost/latency attribution and online quality signals. **Owner:** AI/ML Engineer + ML Platform Engineer; trace IDs propagate end-to-end (a Stage-4 traceability VETO surface). Canon: `STACK.md`.

## Why a dedicated skill
You cannot debug, cost-control, or eval an LLM/agent system you can't see. "It gave a bad answer" is unactionable without the trace: which prompt, which retrieved chunks, which tool calls, how many tokens, which model, how much it cost, how long it took. This is the substrate the eval skills (`llm-evals`, `agent-evaluation`) and `cost-routing-paradigms` read from.

## Invariants (NON-NEGOTIABLE)
1. **Instrument with OpenTelemetry GenAI semantic conventions** (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `gen_ai.operation.name`). Vendor-neutral by default — a backend swap is a config change, not a re-instrumentation. Bypassing OTel is now a switching-cost liability.
2. **Every model/tool/agent step is a span in one trace.** A request → its agent graph → each model node → each tool call → each retrieval is a single connected trace, carrying the **tenant_id** and the app correlation/trace ID. A model call with no parent trace is invisible.
3. **Token + cost are attributed per span, per tenant.** Input/output tokens, cached vs uncached, and computed cost land on the span. Per-tenant cost roll-up feeds `finops-cost` and the `cost-routing-paradigms` budget caps.
4. **PII redaction on captured prompts/outputs.** Prompts and completions are captured for debugging — apply the same redaction as `observability`/`security-baseline`. Tenant data in a trace store is still tenant data (residency + retention per `COMPLIANCE.md`).
5. **Online quality signals are captured, not just offline evals.** User feedback (thumbs, edits, regenerations), guardrail trips, and LLM-judge scores attach to traces so production quality is observable, not inferred.

## Span shape (OTel GenAI)
```python
with tracer.start_as_current_span("chat", attributes={
    "gen_ai.system": "anthropic",
    "gen_ai.request.model": model_id,
    "gen_ai.operation.name": "chat",
    "tenant.id": tenant_id,            # tenant on every span
}) as span:
    resp = gateway.chat(...)           # routes via llm-gateway
    span.set_attribute("gen_ai.usage.input_tokens",  resp.usage.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", resp.usage.output_tokens)
    span.set_attribute("gen_ai.usage.cached_tokens", resp.usage.cache_read_tokens)
    span.set_attribute("cost.usd", price(resp.usage, model_id))
```
Use auto-instrumentation (OpenLLMetry / OpenInference / OpenLIT) to capture this without hand-wiring every call; emit to any OTLP backend (Langfuse, Phoenix, …).

## What to dashboard / alarm
- **Cost + tokens per tenant per day** (alarm on a tenant approaching its cap → graceful degradation, not a surprise bill).
- **Latency p50/p95** per model node + tool; **cache-hit rate** (the top cost lever — `cost-routing-paradigms`).
- **Error/refusal/guardrail-trip rate**; retrieval recall proxy (`rag-retrieval`).
- **Quality drift**: rolling LLM-judge/user-feedback score per surface.

## Operability
- Tie traces to evals: a regression dashboard (`llm-evals`/`agent-evaluation`) reads the same spans; a failing online score links straight to the offending trace.
- Sampling: trace 100% of errors + a representative sample of successes; never sample away the failures you need to debug.
- Retention/residency of trace data follows `COMPLIANCE.md` (it contains prompts = user content).

## Anti-patterns
A model call with no parent trace · vendor-locked SDK instead of OTel GenAI semconv (re-instrumentation tax on a backend swap) · tokens/cost not attributed per tenant · raw PII in traces with no redaction · capturing latency but not quality signals · sampling away errors · trace store ignoring residency/retention.
