---
name: subagent-driven-development
description: The reusable pattern behind Brain's 8-stage pipeline — drive multi-stage work by having each stage run as a subagent that plans, executes, self-reviews, verifies, then explicitly hands off to the next stage via the Agent tool (not a handoff file). Adapted from the superpowers subagent-driven-development pattern. Auto-load when CTOA or Aryan is orchestrating a requirement through stages, or when designing any new multi-step autonomous flow. The abstract pattern; the concrete stages live in `workflows/requirement-to-release.yaml` and each agent's operating loop.
---

# Subagent-Driven Development

> A pipeline is only autonomous if each stage *invokes* the next. A stage that writes a "HANDOFF-TO-X.md" file and stops is not a pipeline — it's a relay race where the baton lands on the ground.

This is the abstract pattern that the Brain 8-stage flow (Intake → Architect → Parallel Dev → Security → QA → Final Review → Founder Approval → DevOps) implements. Read this to understand *why* the pipeline works the way it does, and to build any new multi-step autonomous flow correctly.

## The Iron Law

```
EACH STAGE PLANS → EXECUTES → SELF-REVIEWS → VERIFIES → INVOKES THE NEXT STAGE VIA Agent().
A stage that finishes without invoking the next stage has failed, even if its own work is perfect.
```

The single most common pipeline failure is a stage that does great work and then writes a file describing what should happen next, instead of making it happen. Don't write the baton down — hand it off.

## The per-stage contract

Every stage (subagent) follows the same five-beat loop:

```
1. PLAN       — TodoWrite snapshot or <stage>-plan.md. State what you'll do BEFORE acting (announce-at-start).
2. EXECUTE    — do the work in your lane only; journal mid-execution at meaningful checkpoints.
3. SELF-REVIEW— walk your in-lane Definition of Done line-by-line; fix gaps before handoff (see two-stage review).
4. VERIFY     — run the verification commands; capture output (see verification-before-completion). No green claim without evidence.
5. HAND OFF   — invoke the next stage:
                Agent(description="<Stage N+1> for <req_id>",
                      subagent_type="<next-agent>",
                      prompt="<self-contained: run folder, what you produced, what they must do, the gate they enforce>")
```

The handoff prompt is self-contained — the next agent has none of your context. Give it the run folder path, what you produced, what it must do, and the gate it owns.

## The handoff rule (the heart of the pattern)

| Do | Don't |
|---|---|
| Call `Agent(subagent_type="architect", ...)` to start Stage 2 | Write `HANDOFF-TO-ARCHITECT.md` and stop |
| Pass a self-contained prompt with the run folder + your output | Assume the next agent can see your context |
| On Agent-call failure, fall back to the handoff-file pattern AND log `type="handoff-file-fallback"` | Use the file as the primary mechanism |

The handoff-file pattern is a **fallback for when the Agent tool fails**, recorded in the decision log — never the default.

## Stage gates — verify before you pass the baton

Each handoff crosses a gate. The receiving stage must be able to trust the sending stage's claims:

- The sender runs its verification commands and captures output **before** invoking the next stage.
- The receiver, where it owns a re-verification duty (e.g. QA re-runs upstream skipped gates; CTOA spot-re-runs QA's gates), does so — trust but verify.
- A gate that was SKIPPED upstream must be re-run downstream, not assumed.

## Isolation between stages

- Each stage owns disjoint outputs (its artifact file, its journal). Parallel stages (e.g. web + mobile in Stage 3) own disjoint file scopes — see `dispatching-parallel-agents`.
- Shared state (run folder, decision log, `active.json`) is append-only or last-write-with-backup, so concurrent stages don't clobber each other.

## Audit trail (every stage, every time)

A stage isn't done until it has appended:
- its **journal** entry (what it did, verdict, next),
- a **decision-log** event (machine-readable, typed),
- a **state** update (`active.json` current owner + status; write `.bak` first),
- its **per-feature journal** line.

This is what lets `/status` and `/recall` reconstruct any run, and what the audit-trail (`chore(eos)`) commit captures.

## Red flags — STOP

- A stage that writes a handoff file as its *primary* exit instead of invoking the next agent.
- A handoff prompt that assumes shared context ("continue where I left off" with no run folder/path).
- Passing the baton without running verification first ("Stage 3 done" with no captured test output).
- Skipping the audit-trail append "to save time" — then `/status` can't see the stage ran.
- A downstream stage trusting an upstream SKIPPED gate instead of re-running it.
- One stage editing another stage's files.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "The handoff file documents what's next, that's enough" | Documentation isn't invocation. The pipeline stalls waiting for a human to read the file. |
| "The next agent will figure out the context" | It has zero context. Self-contained prompt or it guesses wrong. |
| "I'll verify at the end of the pipeline" | A bad artifact compounds through every later stage. Verify at each gate. |
| "Appending to the journal slows me down" | Skipping it makes the run unreconstructable when something breaks two weeks later. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| The concrete 8-stage flow | CTOA + each agent's operating loop | `workflows/requirement-to-release.yaml`, `docs/workflow.md` |
| The gates between stages | each receiving agent | `docs/quality-gates.md` |
| Parallel stages (Stage 3 fan-out) | Aryan | `dispatching-parallel-agents` |
| Verification at each gate | each stage | `verification-before-completion` |
| Commit discipline at the final stage | Jatin | `finishing-a-development-branch` |

## The bottom line

Each stage plans, executes, self-reviews, verifies, and *invokes* the next stage. Handoff files are a logged fallback, never the default. Verify before you pass the baton, and leave an audit trail every time. That's what makes the pipeline run without a human nudging it between stages.

Related: `dispatching-parallel-agents` (fan-out within a stage), `verification-before-completion` (gate evidence), `writing-plans` (the plan each stage emits), `finishing-a-development-branch` (the last stage).
