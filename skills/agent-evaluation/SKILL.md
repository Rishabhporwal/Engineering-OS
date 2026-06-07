---
name: agent-evaluation
description: Evaluate agentic systems — trajectory/tool-call correctness, step-level + end-to-end success, multi-turn, and regression gates in CI (DeepEval/promptfoo/Ragas + LLM-judge). The ship gate for agent changes, distinct from prompt/RAG evals. Owner AI/ML + ML Platform Eng.
---

# Agent Evaluation (Reference Patterns)

> **Reference implementation.** This skill documents the **agent-evaluation seam** (see `engineering-os-blueprint/09-reference-architecture.md`). It extends `llm-evals` (golden-set, faithfulness, RAG recall@k for single-shot prompts) to **multi-step agents**, where the unit under test is a *trajectory*, not a single completion. The OS is stack-agnostic — `STACK.md` may bind eval tooling to DeepEval, promptfoo, Ragas, Langfuse, or Phoenix. The *patterns* transfer.

A durable, tool-using, multi-turn agent (`agent-orchestration-langgraph`) can produce a right final answer via a wrong, expensive, or unsafe path — and a single-output eval won't catch it. Agent evaluation scores the **path and the outcome**. **Owner:** AI/ML Engineer (builds the agent) + ML Platform Engineer (owns the eval harness/gate). This is the agent's `verification-before-completion`. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **An agent change ships only through the eval gate.** New prompt, new tool, new model, new graph edge → run the harness; merge only if it's **≥ baseline** on every guardrail metric. No "looks better." (Same law as `llm-evals`, applied to trajectories.)
2. **Evaluate the trajectory, not just the answer.** Score **tool-call correctness** (right tool, right args, no unneeded calls), **step success**, path efficiency (steps/tokens/cost), and **final-outcome** success. A correct answer reached via a destructive or wildly expensive path is a fail.
3. **Multi-turn + state.** Evaluate across turns where the agent is conversational/stateful — context retention, recovery from a bad tool result, not repeating itself. Single-turn evals miss the failure modes that matter.
4. **Safety + cost are guardrail metrics, not afterthoughts.** Every eval run reports refusal/guardrail-trip behavior (ties to `ai-llm-security`, `agentic-safety`) and cost/latency per task (ties to `cost-routing-paradigms`). A change that improves accuracy but doubles cost or weakens safety does not pass silently.
5. **Deterministic, versioned golden tasks.** A fixed suite of tasks with graded success criteria, version-controlled and expanded when a production failure is found (every incident → a new eval case). Run in CI.

## What to measure
| Dimension | Metric |
|---|---|
| Tool use | tool-selection accuracy, argument validity, unnecessary-call rate |
| Step quality | per-step success, recovery-after-failure rate |
| Trajectory | path efficiency (steps/tokens/$), loop/no-progress detection |
| Outcome | task success (LLM-judge + programmatic checks), faithfulness |
| Multi-turn | context retention, consistency across turns |
| Guardrails | refusal correctness, injection resistance, safety trips, cost/latency |

## Harness shape (CI gate)
```python
# pytest-style gate (DeepEval/promptfoo/Ragas) over golden tasks
for task in golden_tasks:                      # versioned, deterministic
    trace = run_agent(task.input)              # captured via ai-observability-tracing
    assert score_tool_calls(trace) >= baseline.tool_calls
    assert judge_outcome(trace, task.rubric) >= baseline.outcome     # LLM-judge + checks
    assert trace.cost_usd <= baseline.cost * 1.2 and trace.steps <= task.max_steps
```
- LLM-as-judge for fuzzy outcomes (with a rubric); **programmatic checks** for anything verifiable (did the tool actually create the row? is the number right?) — never judge what you can assert.
- Read trajectories from the **trace store** (`ai-observability-tracing`) so eval and production share one source of truth; a failing eval links to the exact trace.

## Effort-tier note (`cost-routing-paradigms`)
The judge model is itself a cost — use the **cheapest sufficient judge** (a small model or programmatic check where it suffices; a frontier judge only for genuinely subjective outcomes), and cache. Don't run a frontier-model judge on a task a regex can grade.

## Three-point CI gate (mirrors `llm-evals`)
1. **Offline golden-task suite** — trajectory + outcome ≥ baseline.
2. **Guardrail check** — safety/injection/cost not regressed.
3. **Online signal** — post-deploy, the production quality score (`ai-observability-tracing`) doesn't drop; if it does, roll back the agent version.

## Anti-patterns
Shipping an agent change on "it seemed better" · scoring only the final answer (path blind) · single-turn evals for a multi-turn agent · ignoring cost/safety in the eval · a frontier-model judge for verifiable outputs · golden tasks that never grow from production failures · evals disconnected from the trace store (can't debug a failure) · no online regression check after deploy.
