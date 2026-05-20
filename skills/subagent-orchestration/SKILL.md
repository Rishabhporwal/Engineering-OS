---
name: subagent-orchestration
description: How to drive multi-agent work — fan-out cap discipline (0/1/2, never reflexively more) for parallel subagents AND the stage-by-stage Agent()-handoff pipeline pattern where each stage plans, executes, self-reviews, verifies, then invokes the next stage. Adapted from the superpowers parallel-agent-dispatch + subagent-driven pipeline patterns. Auto-load when CTOA chooses persona count, when Aryan splits Stage 3 across builders, when orchestrating a requirement through stages, or any time an agent considers spawning subagents.
---

# Subagent Orchestration

> Parallelism is a tool for *independent* work, not a reflex — and a pipeline is only autonomous if each stage *invokes* the next. Two agents on one coupled problem produce merge conflicts; a stage that writes "HANDOFF-TO-X.md" and stops produces a relay race where the baton lands on the ground.

This skill covers two intertwined disciplines: **fan-out** (how many agents to spawn in parallel, and how) and **hand-off** (how a multi-stage flow drives itself stage to stage). The Brain 8-stage pipeline (Intake → Architect → Parallel Dev → Security → QA → Final Review → Founder Approval → DevOps) is the concrete implementation; this is the reusable pattern.

## The Iron Law

```
SPAWN THE MINIMUM NUMBER OF AGENTS THE WORK REQUIRES — 0 IS A VALID ANSWER.
EACH STAGE PLANS → EXECUTES → SELF-REVIEWS → VERIFIES → INVOKES THE NEXT VIA Agent().
```

Default to doing it yourself. Add an agent only when it buys real isolation (independent work) or real context savings (a search/audit that would flood your window). A stage that finishes without invoking the next stage has failed, even if its own work is perfect.

---

## Part 1 — Fan-out: how many agents, and how

The core question is never "can I parallelize?" — it's "is this work actually independent, and is the count justified?"

### When to fan out vs. do it yourself

| Situation | Action |
|---|---|
| One coherent task, you have the context | Do it yourself. 0 agents. |
| A bounded lookup/search that would bloat your context | 1 subagent (Explore), return a summary. |
| 2 genuinely independent workstreams (e.g. web + mobile of one feature) | 2 agents in parallel. |
| 3+ "nice to have" perspectives on a small task | STOP — over-spawning. Cap at 2. |
| Work where step B needs step A's output | Sequential, not parallel. |

This mirrors the **persona-count classifier** (0/1/2 by complexity) — trivial work gets 0, standard gets 1, genuinely multi-faceted gets 2. The same logic governs every fan-out decision.

### The count decision (record it)

```
BEFORE spawning, answer in one line each:
1. Is the work independent? (no shared files, no A→B dependency)  If no → sequential.
2. What is the minimum count? (0/1/2 — justify 2; never default to 3+)
3. What does each agent OWN? (disjoint scope → no merge conflict)
4. How will I MERGE results? (summaries, not raw dumps, back into my context)
THEN spawn.
```

CTOA records this in `02-cto-advisor-review.md` under "Persona-count decision". Other agents record it in their plan (TodoWrite or stage plan).

### Running them in parallel

To run concurrently, make **all the Agent calls in a single message** — multiple tool-use blocks in one turn. Sequential messages run sequentially.

```
# CONCURRENT (correct) — one message, two Agent calls:
Agent(description="Web build for <req>", subagent_type="frontend-web-developer", prompt="...")
Agent(description="Mobile build for <req>", subagent_type="mobile-developer", prompt="...")

# SEQUENTIAL (wrong, if independent) — two messages, one call each → no speedup
```

Each prompt must be **self-contained**: the subagent has none of your context. State the goal, the run folder, the exact scope it owns, what to return, and the length cap.

### Isolation — prevent merge conflicts

- Give each agent a **disjoint file scope**. Two agents editing `packages/lib-metrics/` will collide.
- If the work shares files, it isn't independent — make it sequential.
- For risky parallel edits, consider git worktrees (one branch per agent) so they never touch the same working tree.

### Merging results without context bloat

- Ask each subagent for a **short report** (findings + what changed), not raw file dumps.
- Trust-but-verify: a summary is intent, not proof. Re-run the verification commands yourself (see `verification-before-completion`) before claiming the combined work is done.
- Reconcile overlaps explicitly; never assume two parallel agents stayed in their lanes.

---

## Part 2 — Hand-off: driving the stage pipeline

The single most common pipeline failure is a stage that does great work and then writes a file describing what should happen next, instead of making it happen. Don't write the baton down — hand it off.

### The per-stage contract (five-beat loop)

```
1. PLAN       — TodoWrite snapshot or <stage>-plan.md. State what you'll do BEFORE acting.
2. EXECUTE    — do the work in your lane only; journal at meaningful checkpoints.
3. SELF-REVIEW— walk your in-lane Definition of Done line-by-line; fix gaps before handoff.
4. VERIFY     — run the verification commands; capture output (verification-before-completion).
5. HAND OFF   — invoke the next stage:
                Agent(description="<Stage N+1> for <req_id>",
                      subagent_type="<next-agent>",
                      prompt="<self-contained: run folder, what you produced, what they must do, the gate they enforce>")
```

### The handoff rule (the heart of the pattern)

| Do | Don't |
|---|---|
| Call `Agent(subagent_type="architect", ...)` to start Stage 2 | Write `HANDOFF-TO-ARCHITECT.md` and stop |
| Pass a self-contained prompt with the run folder + your output | Assume the next agent can see your context |
| On Agent-call failure, fall back to the handoff-file pattern AND log `type="handoff-file-fallback"` | Use the file as the primary mechanism |

The handoff-file pattern is a **fallback for when the Agent tool fails**, recorded in the decision log — never the default.

### Stage gates — verify before you pass the baton

- The sender runs its verification commands and captures output **before** invoking the next stage.
- The receiver re-runs any duty it owns (QA re-runs upstream skipped gates; CTOA spot-re-runs QA's gates) — trust but verify.
- A gate SKIPPED upstream must be re-run downstream, not assumed.

### Isolation + audit trail between stages

- Each stage owns disjoint outputs (its artifact, its journal). Parallel stages own disjoint file scopes (Part 1).
- Shared state (run folder, decision log, `active.json`) is append-only or last-write-with-backup (write `.bak` first).
- A stage isn't done until it has appended: its **journal** entry, a typed **decision-log** event, a **state** update, and its **per-feature journal** line. This is what lets `/status` and `/recall` reconstruct any run.

---

## Red flags — STOP

- Spawning 3+ agents "to be thorough" on a small task — token burn, not rigor.
- Parallelizing work where one stream depends on another's output.
- Two agents with overlapping file scope (guaranteed merge conflict).
- Making Agent calls in separate messages and expecting concurrency.
- A stage that writes a handoff file as its *primary* exit instead of invoking the next agent.
- A handoff prompt that assumes shared context ("continue where I left off" with no run folder).
- Passing the baton without running verification first.
- A downstream stage trusting an upstream SKIPPED gate instead of re-running it.
- Accepting parallel or stage subagent reports as done without re-running verification.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "More agents = more thorough" | More agents = more merge surface + more tokens. Thoroughness comes from scope, not count. |
| "Three personas give better coverage" | The classifier exists because 3 was the default that wasted time. 0/1/2 by need. |
| "I'll parallelize then sort out conflicts" | Sorting out conflicts costs more than the sequential run would have. |
| "The handoff file documents what's next" | Documentation isn't invocation. The pipeline stalls waiting for a human to read it. |
| "The next agent will figure out the context" | It has zero context. Self-contained prompt or it guesses wrong. |
| "The subagents said they're done" | Verify their output yourself; a report is a claim, not evidence. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Persona count at Stage 1 | **CTOA** | persona-count classifier in `cto-advisor.md` |
| Splitting Stage 3 across builders | **Aryan** (architect) | handoff-depth calibration |
| The concrete 8-stage flow | CTOA + each agent's operating loop | `workflows/requirement-to-release.yaml`, `docs/workflow.md` |
| The gates between stages | each receiving agent | `docs/quality-gates.md` |
| Verifying merged / handed-off work | the dispatcher / each stage | `verification-before-completion` |
| Commit discipline at the final stage | Jatin | `finishing-a-development-branch` |

## The bottom line

Ask "is this independent?" before "can I parallelize?". Cap at 2 unless you can justify more; fire them in one message; merge summaries; verify yourself. Then each stage plans, executes, self-reviews, verifies, and *invokes* the next stage — handoff files are a logged fallback, never the default. That's what makes the pipeline run without a human nudging it between stages.

Related: `verification-before-completion` (gate evidence), `writing-plans` (the plan each stage emits), `engineering-discipline` (context discipline), `cost-routing-paradigms` (count affects cost), `finishing-a-development-branch` (the last stage).
