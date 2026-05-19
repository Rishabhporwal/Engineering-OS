---
name: dispatching-parallel-agents
description: When and how to fan out work to multiple subagents in parallel — deciding the persona/agent count (0/1/2, not always more), making the Agent calls in a single message so they run concurrently, isolating their work, and merging their results without context bloat. Adapted from the superpowers dispatching-parallel-agents pattern, generalized from CTOA Stage-1 persona spawning to the whole pipeline. Auto-load when CTOA chooses persona count, when Aryan splits Stage 3 across builders, or any time an agent considers spawning subagents.
---

# Dispatching Parallel Agents

> Parallelism is a tool for *independent* work, not a reflex. Two agents on one coupled problem produce merge conflicts and burned tokens, not speed.

This generalizes the persona-count discipline (CTOA Stage 1) and the Stage-3 parallel-build pattern into one reusable rule for the whole team. The core question is never "can I parallelize?" — it's "is this work actually independent, and is the count justified?"

## The Iron Law

```
SPAWN THE MINIMUM NUMBER OF AGENTS THE WORK REQUIRES — 0 IS A VALID ANSWER.
```

Default to doing it yourself. Add an agent only when it buys real isolation (independent work) or real context savings (a search/audit that would flood your window).

## When to fan out vs. do it yourself

| Situation | Action |
|---|---|
| One coherent task, you have the context | Do it yourself. 0 agents. |
| A bounded lookup/search that would bloat your context | 1 subagent (Explore), return a summary. |
| 2 genuinely independent workstreams (e.g. web + mobile of one feature) | 2 agents in parallel. |
| 3+ "nice to have" perspectives on a small task | STOP — this is over-spawning. Cap at 2. |
| Work where step B needs step A's output | Sequential, not parallel. |

This mirrors the **persona-count classifier** (0/1/2 by complexity) — trivial work gets 0 personas, standard gets 1, genuinely multi-faceted gets 2. The same logic governs every fan-out decision.

## The count decision (record it)

```
BEFORE spawning, answer in one line each:
1. Is the work independent? (no shared files, no A→B dependency)  If no → sequential.
2. What is the minimum count? (0/1/2 — justify 2; never default to 3+)
3. What does each agent OWN? (disjoint scope, no overlap → no merge conflict)
4. How will I MERGE results? (summaries, not raw dumps, back into my context)
THEN spawn.
```

CTOA records this in `02-cto-advisor-review.md` under "Persona-count decision". Other agents record it in their plan (TodoWrite or stage plan).

## How to actually run them in parallel

To run concurrently, make **all the Agent calls in a single message** — multiple tool-use blocks in one turn. Sequential messages run sequentially.

```
# CONCURRENT (correct) — one message, two Agent calls:
Agent(description="Web build for <req>", subagent_type="frontend-web-developer", prompt="...")
Agent(description="Mobile build for <req>", subagent_type="mobile-developer", prompt="...")

# SEQUENTIAL (wrong, if independent) — two messages, one call each → no speedup
```

Each prompt must be **self-contained**: the subagent has none of your context. State the goal, the run folder, the exact scope it owns, what to return, and the length cap.

## Isolation — prevent merge conflicts

- Give each agent a **disjoint file scope**. Two agents editing `packages/lib-metrics/` will collide.
- If the work shares files, it isn't independent — make it sequential.
- For risky parallel edits, consider git worktrees (one branch per agent) so they never touch the same working tree.

## Merging results without context bloat

- Ask each subagent for a **short report** (findings + what changed), not raw file dumps.
- Trust-but-verify: a subagent's summary is its intent, not proof. Re-run the verification commands yourself (see `verification-before-completion`) before claiming the combined work is done.
- Reconcile overlaps explicitly; never assume two parallel agents stayed in their lanes.

## Red flags — STOP

- Spawning 3+ agents "to be thorough" on a small task — token burn, not rigor.
- Parallelizing work where one stream depends on another's output.
- Two agents with overlapping file scope (guaranteed merge conflict).
- Spawning a subagent for something you could do in two tool calls yourself.
- Accepting parallel subagent reports as done without re-running verification.
- Making Agent calls in separate messages and expecting concurrency.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "More agents = more thorough" | More agents = more merge surface + more tokens. Thoroughness comes from scope, not count. |
| "I'll parallelize then sort out conflicts" | Sorting out conflicts costs more than the sequential run would have. |
| "Three personas give better coverage" | The persona classifier exists because 3 was the default that wasted time. 0/1/2 by need. |
| "The subagents said they're done" | Verify their output yourself; their report is a claim, not evidence. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Persona count at Stage 1 | **CTOA** | persona-count classifier in `cto-advisor.md` |
| Splitting Stage 3 across builders | **Aryan** (architect) | handoff-depth calibration |
| Driving the stage pipeline by dispatch | CTOA / pipeline | `subagent-driven-development` |
| Verifying merged parallel work | the dispatcher | `verification-before-completion` |

## The bottom line

Ask "is this independent?" before "can I parallelize?". Cap at 2 unless you can justify more. Give each agent a disjoint scope, fire them in one message, merge summaries, and verify the result yourself. Zero agents is often the right answer.

Related: `subagent-driven-development` (the pipeline-level dispatch pattern), `verification-before-completion` (verify merged work), `engineering-discipline` (context discipline), `cost-routing-paradigms` (count affects cost).
