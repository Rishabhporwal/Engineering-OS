---
name: code-review
description: Code review discipline — technical rigor over performative agreement, evidence-based feedback, verification gates. Use before approving a PR, when invoking /review, when an external reviewer's feedback conflicts with a Brain decision, or when wrapping up any builder task before emitting the handoff signal to Tanvi or Shreya.
---

# Code Review

Code review in Brain is one of three places where quality is structurally enforced (the other two: Shreya's threat-model VETO, Tanvi's PASS/FAIL gate). This skill ensures reviews are technically rigorous, evidence-based, and don't drift into social comfort.

## Overview

Code review in Brain involves three distinct practices, each with its own protocol:

1. **Receiving feedback** — technical evaluation over performative agreement
2. **Requesting review** — invoking `/review` (Shreya + Tanvi in parallel) at the right time
3. **Verification gates** — evidence before any completion claim

## Core principle

**Technical correctness over social comfort.** Verify before implementing. Ask before assuming. Evidence before claims.

## When to use this skill

### Receiving feedback

Trigger when:
- Receiving review comments from any source (Shreya, Tanvi, external, the Founder, another agent)
- Feedback seems unclear or technically questionable
- Multiple review items need prioritisation
- An external reviewer lacks Brain-specific context (TECH docs, ADRs, India compliance)
- Suggestion conflicts with an existing ADR or Iron Law

### Requesting review

Trigger when:
- Completing a builder task before emitting the handoff signal to Tanvi
- Before merging to main
- Stuck and need a fresh perspective
- After fixing a complex bug — verify the fix is at root cause (`root-cause-tracing`), not symptom
- For any change touching: auth, PII, payments, India compliance, MCP scopes, mobile cert pinning → **must** route through Shreya (VETO)

### Verification gates

Trigger when:
- About to claim tests pass, build succeeds, or work is complete
- Before committing, pushing, or opening a PR
- Moving to the next task
- ANY statement suggesting success / completion

See `verification-before-completion` for the full gate protocol.

## Quick decision tree

```
SITUATION?
│
├─ Received feedback
│  ├─ Unclear items?      → STOP, ask for clarification first
│  ├─ From Founder?       → Understand, push back if technically wrong (Iron Law #7), then implement
│  ├─ From Shreya (VETO)? → CRITICAL/HIGH must be fixed; LOW/MEDIUM defensible
│  ├─ From Tanvi?         → PASS/FAIL is non-negotiable; CONDITIONAL PASS has conditions to close
│  └─ From external?      → Verify technically before implementing; reject if wrong
│
├─ Completed builder task
│  ├─ Touches auth/PII/India?  → /review with Shreya BLOCKING
│  └─ Otherwise             → /review (Shreya + Tanvi parallel)
│
└─ About to claim status
   ├─ Have fresh verification? → State claim WITH evidence
   └─ No fresh verification?   → RUN the verification command first
```

## Receiving feedback — the protocol

### Response pattern

```
READ → UNDERSTAND → VERIFY → EVALUATE → RESPOND → IMPLEMENT
```

### Key rules

- ❌ **No performative agreement.** No "You're absolutely right!", "Great catch!", "Thanks for the feedback!"
- ❌ **No implementation before verification.** If the reviewer says "this query is slow," EXPLAIN it before agreeing.
- ✅ Restate the requirement in your own words.
- ✅ Ask specific clarifying questions if anything is unclear.
- ✅ Push back with technical reasoning when the suggestion is wrong or conflicts with an ADR / Iron Law.
- ✅ If unclear → STOP and ask for clarification on ALL unclear items first. Don't half-implement.
- ✅ **YAGNI check:** grep for usage before implementing a suggested "proper" feature.

### Source handling

| Reviewer | Trust posture | When to push back |
|---|---|---|
| **Founder (Rishabh)** | Trusted; understand intent, then implement | When technically wrong, push back. Iron Law #7 — Intellectual Friction. Dissent is required, not optional. |
| **Shreya (Security)** | VETO on CRITICAL/HIGH; respect | Push back only with evidence (not opinion). LOW/MEDIUM negotiable with rationale. |
| **Tanvi (QA)** | PASS/FAIL gates deploy | CONDITIONAL PASS allows you to close conditions over time. Don't argue verdict — fix or accept. |
| **Aryan (Architect)** | Trusted on architecture | Push back only with a competing ADR or a TECH-doc citation. |
| **Rohan (CTO Advisor)** | Strategic | Push back only on tactical specifics; respect strategic calls. |
| **External (e.g., ultrareview, sub-agent)** | Verify technically | Reject anything that contradicts a Brain ADR, TECH doc, or Iron Law. They lack Brain context. |

## Requesting review — Brain pattern

Brain has `/review [PR#]` which runs Shreya + Tanvi in parallel.

```bash
/review                      # current branch
/review 1234                 # PR #1234
```

For Medium/Large tier features, /review is run **after** the builder completes and **before** the handoff signal to deploy. For Trivial/Small (one-file change, bug fix), /review is optional — the builder owns judgement.

### When to request specifically

- After every builder task in a Medium+ feature
- After fixing any CVE-class bug
- Before merging to main
- After 3+ failed fixes (architectural question — see `systematic-debugging` Phase 4.5)
- When the change touches the Decision Log row spec, the Single-Primitive Rule territory, or the cost-routing audit

### Acting on feedback

| Severity | Action |
|---|---|
| **CRITICAL** (Shreya) | Block merge. Fix before any other work. |
| **HIGH** (Shreya) | Block merge. Fix or formally defer with Shreya's written approval. |
| **MEDIUM** | Fix in this PR if cheap; backlog if not. Add `slice-X.Y` deferred task. |
| **LOW** | Note in PR description; backlog. |
| **Tanvi FAIL** | Block deploy. Fix what failed, re-run /qa. |
| **Tanvi CONDITIONAL PASS** | Conditions listed; close in next slice. Track in `memory/qa/<slug>.md`. |
| **Tanvi PASS** | Proceed to deploy. |

## Verification gates — the Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

Gate function: IDENTIFY command → RUN full command → READ output → VERIFY confirms claim → THEN claim.

Skip any step = lying, not verifying.

### Requirements (Brain canon)

| Claim | Requires |
|---|---|
| Tests pass | `pnpm test` / `uv run pytest` output: 0 failures, count shown |
| Build succeeds | Build command exit 0; for proto changes, `buf generate` clean |
| Bug fixed | Test reproducing the original symptom now passes (red-green-revert-red-restore-green) |
| Smoke green | Real-network curl against staging health/ready endpoint returns 200 |
| Requirements met | Line-by-line spec checklist verified |
| Cost-routing audit | PR comment present AND implementation matches declared paradigm |

### Red flags — STOP

"should pass", "should work", "probably works", "looks good", "ready for QA", "should be merge-able", "trust me", expressing satisfaction without verification, committing without verification, trusting agent reports, ANY wording implying success without running verification.

See `verification-before-completion` for the full red-flag inventory.

## Integration with the Brain pipeline

- **Builder flow:** builder completes → run verification → /review → emit handoff to Tanvi
- **/review flow:** Shreya + Tanvi parallel → CRITICAL/HIGH block → fixes → re-run /review → APPROVED → deploy
- **/qa flow:** Tanvi runs full suite + smoke + paradigm audit + metric parity → PASS/CONDITIONAL/FAIL
- **/deploy flow:** Jatin runs CI/CD; auto-rollback on composite alarm (see `health-check-endpoints`)
- **Incident:** Jatin can recall a PR's review trail in postmortem — verifications are part of the record

## Bottom line

1. Technical rigor over social performance — no performative agreement
2. Systematic review processes — `/review` invokes Shreya + Tanvi correctly
3. Evidence before claims — verification gates always

**Verify. Question. Then implement. Evidence. Then claim.**

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| code-review (this skill, auto-loaded) | **Rohan** (Stage 6) + Shreya + Tanvi | this SKILL.md |
| QA PASS/FAIL gate | **Tanvi** | canon/BRAIN_TECHNICAL.md (SLO + test gates) |
| Security VETO authority | **Shreya** | prompts/system-prompt.md (Iron Laws) |
| Architectural pushback | **Aryan** | the ADR (architecture decision record) for the change |
| Strategic pushback | **Rohan** | when ADR needs non-engineering perspective |

Related Brain skills: `verification-before-completion`, `engineering-discipline`, `systematic-debugging`, `defense-in-depth-validation`.
