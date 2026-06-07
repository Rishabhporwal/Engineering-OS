---
name: workflow-engine-temporal
description: Reference implementation — durable execution on Temporal: deterministic workflows + side-effecting activities, automatic retries, human-approval signals, sagas/compensation for reversible actions, timers/timeouts. The macro-orchestrator for approvals and multi-step execution.
---

# Durable Workflows — Temporal (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **durable-workflow / orchestration seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to a different engine (AWS Step Functions, Cadence, Netflix Conductor, Airflow for pure DAGs). The *patterns* here — durable state that survives process death, deterministic workflow code vs side-effecting activities, retries/timeouts as first-class, human-in-the-loop via signals, and sagas/compensation for reversibility — are what transfer; Temporal is the example.

Temporal is the **macro-orchestrator** for long-running, multi-step, human-gated, reversible business processes: approval workflows, execution workflows, reconciliation pipelines. It complements (does not replace) the micro-level agent reasoning of `agent-orchestration-langgraph`: Temporal owns the durable *macro* flow; LangGraph owns the in-step *reasoning*. **Owner:** Backend Engineer (workflow code) + Platform/SRE (cluster); AI/ML Engineer for agentic execution flows. Canon: `STACK.md`.

## Why durable execution
A long, multi-step process with human approvals and external side effects cannot live in a single request, a cron, or in-memory state — a crash loses it. Temporal persists every step's state and **replays** the workflow deterministically to reconstruct it after any failure. The process becomes crash-proof and resumable by construction.

## Invariants (NON-NEGOTIABLE)
1. **Workflow code is deterministic; all side effects are Activities.** No clocks, randomness, network calls, or direct I/O in workflow code — those go in Activities. Non-determinism breaks replay (the whole guarantee). Use `workflow.now()`, `workflow.sleep()`, deterministic IDs.
2. **Every consequential action is reversible — model compensation.** Use the saga pattern: each step has a compensating action; a failure later triggers compensations in reverse. This is how the platform delivers the "reversible actions" promise (mirrors `incident-response` kill switches at the workflow level).
3. **Human approval is a first-class wait, not a poll.** Pause on a `Signal`/`Update` for approval; the workflow sleeps durably (days if needed) at zero cost until the signal arrives. Gate auto-execution above a threshold behind this (ties to `decision-log` + `agentic-safety`).
4. **Idempotent Activities + workflow IDs.** A workflow ID = a stable business key (e.g. `(tenant_id, approval_id)`) so a duplicate start is deduped (`idempotency-handling`). Activities must be idempotent — Temporal retries them.
5. **Tenant + trace on every workflow.** `tenant_id` in the workflow ID/search attributes; the correlation/trace ID propagates through activities to model/DB calls (traceability, `observability`).

## Workflow vs Activity
```python
@workflow.defn
class ApprovalWorkflow:
    def __init__(self): self._approved = None

    @workflow.run
    async def run(self, req: ActionRequest) -> Result:
        plan = await workflow.execute_activity(prepare_action, req,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=5))
        if plan.requires_human:
            await workflow.wait_condition(lambda: self._approved is not None,
                    timeout=timedelta(days=3))            # durable human gate
            if not self._approved:
                return Result(status="rejected")
        try:
            return await workflow.execute_activity(execute_action, plan, ...)
        except ActivityError:
            await workflow.execute_activity(compensate_action, plan, ...)  # saga rollback
            raise

    @workflow.signal
    def approve(self, decision: bool): self._approved = decision
```

## Retries, timeouts, timers
- **Retry policy per activity** (backoff, max attempts, non-retryable error types) — transient failures self-heal; permanent ones fail fast to a compensation path.
- **Heartbeats** for long activities so a stuck worker is detected and retried.
- Use durable **timers** for SLAs/escalations ("if not approved in 24h, escalate") — not an external scheduler.

## Operability
- **Workers are stateless + horizontally scaled**; the Temporal cluster (or Temporal Cloud) holds the durable state. Platform/SRE owns cluster capacity, task-queue backlog, and persistence health.
- **Versioning:** changing a running workflow's code must use patching/versioning APIs or new task queues, or in-flight workflows break replay determinism. This is the #1 Temporal foot-gun — treat workflow code like a migration.
- Monitor: workflow-task latency, activity failure/retry rates, task-queue backlog, and stuck/terminated workflows.

## Effort-tier note (`cost-routing-paradigms`)
Orchestration itself is **deterministic plumbing** — cheap. Keep the model calls inside Activities, tiered and cached as usual; don't let "agentic workflow" become an excuse to put an LLM in the control flow where a deterministic branch belongs. The workflow decides *structure*; a model decides only what genuinely needs judgment.

## Anti-patterns
Side effects / clocks / randomness in workflow code (breaks replay) · a non-idempotent activity · changing running workflow code without versioning · polling for approval instead of a durable signal · no compensation for a reversible action · workflow ID that isn't a stable business key · putting an LLM in the control flow where a branch suffices · using Temporal for a simple stateless cron.
