---
name: agent-orchestration-langgraph
description: Reference implementation — agent orchestration on LangGraph: explicit state-graph control flow, checkpointed state + memory, human-in-the-loop interrupts, tool nodes, bounded cycles. Deterministic structure around non-deterministic reasoning; every tool call audited + tiered.
---

# Agent Orchestration — LangGraph (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **agent-orchestration seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind agent control flow to a different framework (the Claude Agent SDK, OpenAI Agents SDK, Pydantic-AI, or hand-rolled). The *patterns* here — make the control flow an explicit graph (not an opaque "agent loop"), checkpoint state, interrupt for human approval, bound the cycles, and audit + tier every tool call — are what transfer; LangGraph is the example.

LangGraph models an agent as a **state graph**: nodes (model calls, tools, logic) and edges (including conditional + cyclic) over a typed shared state. It owns the **micro-level reasoning**; durable macro orchestration (long waits, multi-day approvals, saga rollback) belongs to `workflow-engine-temporal`. The two compose: Temporal runs the durable flow, calling a LangGraph agent inside an Activity for the reasoning step. **Owner:** AI/ML Engineer; Security Reviewer audits tool actions (`agentic-safety`). Canon: `STACK.md`.

## Why an explicit graph
An opaque "let the LLM loop until done" agent is unobservable, unbounded in cost, and untestable. An explicit graph makes the control flow **inspectable, checkpointable, resumable, and bounded** — you can see every state transition, replay from a checkpoint, interrupt for a human, and cap the cycles. The structure is deterministic; only the reasoning inside a node is not.

## Invariants (NON-NEGOTIABLE)
1. **The graph is explicit + bounded.** Define nodes and (conditional/cyclic) edges; **cap recursion/iterations** (`recursion_limit`). An uncapped agent loop is an unbounded cost + latency incident waiting to happen (`cost-routing-paradigms`).
2. **State is typed + checkpointed; memory is tenant-scoped.** A typed state object threads the graph; a checkpointer persists it (resume after failure / human pause). Conversation + long-term memory are namespaced by `tenant_id` (and the vector memory in `vector-search-pgvector`) — never cross tenants (`multi-tenancy-isolation`).
3. **Every tool call is audited, scoped, and tiered.** A tool that writes has an auth scope + tenant check + audit-log middleware (`agentic-safety`, `decision-log`); each model node declares its effort tier and uses the gateway (`llm-gateway`) with caching. A write tool with no scope or audit entry is a Security VETO.
4. **Human-in-the-loop via interrupts, not trust.** Consequential actions pause the graph (`interrupt`) for approval; for long/durable waits, hand the pause to Temporal. The agent proposes; a gated step disposes.
5. **Untrusted input is treated as hostile.** Tool outputs and retrieved documents can carry injected instructions — they steer the agent. Apply the `agentic-safety` input-hardening + blast-radius limits; the graph's edges, not the model's whim, decide what runs next.

## Graph shape
```python
graph = StateGraph(AgentState)
graph.add_node("plan",   plan_node)      # model node — declares effort tier
graph.add_node("tools",  ToolNode(tools))# scoped, audited tools
graph.add_node("reflect",reflect_node)
graph.add_conditional_edges("plan", route, {"tools": "tools", "done": END})
graph.add_edge("tools", "reflect")
graph.add_conditional_edges("reflect", route, {"plan": "plan", "done": END})
app = graph.compile(checkpointer=checkpointer, interrupt_before=["tools"])  # human gate on actions
result = app.invoke(state, config={"recursion_limit": 12,                    # bounded
                                    "configurable": {"thread_id": f"{tenant}:{session}"}})
```

## Evaluation (with `llm-evals`)
- An agent change is a model change — it ships only through the eval gate: golden tasks, tool-call correctness, step-level success, faithfulness/groundedness for RAG nodes. No "looks better" merges.
- Trace every node + tool call end-to-end (LangSmith-style); the trace ID propagates to the gateway and DB (traceability is a Stage-4 VETO surface).

## Effort-tier discipline (`cost-routing-paradigms`)
The graph is the cheap, deterministic skeleton; the expensive part is the model nodes. So: route each node to the **cheapest sufficient tier** (a deterministic branch or small model where it suffices; the frontier model only for the genuinely hard step), cache aggressively, and cap cycles. An agent that calls a frontier model on every loop iteration to do routing a conditional edge could do is the wrong tier.

## Anti-patterns
An opaque uncapped agent loop · unbounded recursion / cost · cross-tenant memory · a write tool with no scope or audit entry · no human gate on a consequential action · trusting tool/document text as instructions (injection) · shipping an agent change without the eval gate · a frontier model where a conditional edge or small model routes · putting durable multi-day waits in the graph instead of Temporal.
