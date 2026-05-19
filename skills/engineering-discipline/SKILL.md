---
name: engineering-discipline
description: Universal meta-rules for HOW to engineer with AI — applies to every agent on every task. The 7 principles (Karpathy 4 + gstack ETHOS 2 + Right-Sized Stack), plus vertical-slice delivery, context discipline, and persona brainstorming. One skill, not five, because they're one mental model. Sourced from Karpathy, gstack/Garry Tan, shanraisshan/claude-code-best-practice.
---

# Engineering Discipline — meta-rules for AI engineering

How to think while writing code. Apply to every task. Project-stack-agnostic.

> Sources: [Karpathy](https://github.com/forrestchang/andrej-karpathy-skills), [gstack/Garry Tan](https://github.com/garrytan/gstack), [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice).

## The 7 Principles (the Iron Laws)

### 1. Boil the Lake
Understand fully before coding. Read the spec, related ADRs, surrounding code. THEN start. Time spent understanding is reclaimed 10× in not-redoing.

### 2. Search Before Building
Solution probably already exists. Grep the codebase. Web-search vendor docs. Check npm. Don't reimplement.

### 3. Simplicity First
Minimum code that solves the problem. No features beyond what was asked. No abstractions for single-use code.

❌ Strategy pattern with abstract base class for a one-line discount calculation.
✅ `def apply_discount(amount, percent): return amount * (1 - percent/100)`

### 4. Surgical Changes
Touch only what the task requires. No drive-by refactoring. No style drift. No "while I'm here" cleanups in unrelated code. Dead code you notice → mention in handoff, don't delete.

❌ Bug fix PR also reformats 12 comments, renames a function, changes quote style in 47 lines.
✅ 1 file, +3/-1 lines, test reproduces the bug, fix makes it pass.

### 5. Goal-Driven Execution (folds in TDD)
Every task names a verification command. Test-first when feasible. Verify after each step, not at the end of 10.

### 6. Think Before Coding
State assumptions. Surface tradeoffs. If unclear, name what's confusing — don't guess.

❌ Silently hardcodes `/tmp/users.csv` and exports all fields for `export_users()`.
✅ "Before writing: scope = current tenant? format = CSV? fields = public only? Defaulting to those — say otherwise."

### 7. Right-Sized Stack
**For Brain specifically: the stack is LOCKED.** Fastify + tRPC + gRPC (buf) + Supabase Postgres + ClickHouse Cloud + Amazon MSK + EKS + Karpenter + ArgoCD + AWS CDK + React Native + Expo + Anthropic Claude. See prompts/system-prompt.md ("The Stack — NOT negotiable") and canon/BRAIN_TECHNICAL.md. Aryan only runs `tech-stack-evaluation` when **adding a new layer** that isn't already chosen (e.g., picking the AI calling vendor — see canon/BRAIN_TECHNICAL.md). Do NOT re-evaluate the stack per feature; that was the pre-v6 universal-plugin posture.

## Vertical Slices (the delivery pattern)

Ship full-stack slices, not horizontal phases.

- ❌ Phase 1 design all DB → Phase 2 build all API → Phase 3 build all UI → Phase 4 connect → discover schemas don't match
- ✅ Slice 1 = one user flow end-to-end (DB+API+UI, happy path only) → Slice 2 = next flow → Slice 3 = error handling on slice 1

Rules:
- **Slice 1 ships in <1 hour.** If it can't, find a thinner one.
- Slice 1 is the THINNEST possible end-to-end path — NOT the most important feature.
- Every slice ends in a passing test.
- Hardcoded values in slice 1 are fine — generalize in slice 2.

Priya structures `/spec` task lists as slices, not phases.

## Context Discipline (token efficiency)

Reasoning quality degrades past ~40% context. The "dumb zone".

| Utilization | State | Action |
|---|---|---|
| 0-30% | Healthy | Continue |
| 30-40% | Yellow | Plan compactions / subagent dispatches |
| 40-60% | Dumb zone | Offload expensive reads to subagents |
| 60-80% | Red | Wrap up current task |
| 80%+ | Danger | New session NOW |

Tactics:
1. **`/rewind` over corrections** — backtrack rather than write correction turns
2. **Subagents for expensive isolated work** — agent reads 10 files in *its* context, returns 1 paragraph
3. **New unrelated task = new session**
4. **Read with offset/limit** — don't read a 400-line file when 10 lines suffice
5. **Memory > context** — persist via `memory/`, not chat scrollback

## Persona Brainstorming (for design ambiguity)

Used by Aryan during `/design` when scope is unclear. **Optional for Trivial/Small tier, mandatory only for Medium+.**

Each agent voices ≥1 persona from its domain:
- Frontend → a primary end-user from `business-context.md`
- Security → "The Auditor: how do I exfiltrate one tenant's data?"
- Backend → "The Scale Worrier: what happens at 10× current load?"

Each persona: 3-5 NEEDS · what would FAIL them · one wildcard "what if".

Aryan synthesizes: confirmed (all agree) · tensions (need decision) · hidden requirements · out-of-scope v1.

**Skip this protocol for trivial tasks.** Most build phases don't need it. Over-applying it is a process tax.

## Anti-patterns

- ❌ "I noticed this could be cleaner so I refactored it" (in a bug fix PR)
- ❌ "I assumed you wanted X" (when X wasn't stated)
- ❌ "Let me add a base class in case we need more types later" (single-use)
- ❌ "I'll write tests after the implementation"
- ❌ "We'll build all the DB schemas first" (horizontal phasing)
- ❌ Carrying old PR conversations into unrelated new work
- ❌ Correcting bad output with more turns rather than `/rewind`

## When this skill is working

- Fewer unnecessary changes in diffs
- Fewer rewrites due to overcomplication
- Clarifying questions come *before* implementation, not after mistakes
- PRs review in minutes, not hours
- "Why did you change X?" rarely needs to be asked
