---
name: verification-before-completion
description: Run verification commands and confirm output before any "done"/"tests pass"/"ready" claim. The operational depth behind Iron Law #5. Evidence before claims, always.
---

# Verification Before Completion

> Claiming work is complete without verification is dishonesty, not efficiency.

Operational depth behind **Iron Law #5 — Goal-Driven Execution** (prompts/system-prompt.md). Also what `.engineering-os/lessons-learned.md` calls "don't fake green-tests claims" (slice-3). Applies to every builder, on every handoff signal, PR description, and status update.

**Core principle:** Evidence before claims, always. Violating the letter violates the spirit.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:
1. IDENTIFY: What command proves this claim?
2. RUN:       Execute the FULL command (fresh, complete) — not a recollection
3. READ:      Full output. Exit code. Failure count. The actual numbers.
4. VERIFY:    Does output confirm the claim? NO → state actual status w/ evidence; YES → claim w/ evidence
5. ONLY THEN: make the claim
Skip any step = lying, not verifying.
```

## Verification commands (examples — bind to your `STACK.md`)

The exact commands come from the product's `STACK.md`; the *shape* is what transfers. Illustrative bindings:

```bash
# Compiled/typed runtime (e.g. TS/Node)
<test> ; <e2e> ; <typecheck> ; <lint> ; <build>
# Interpreted runtime (e.g. Python)
<unit tests> ; <coverage> ; <type check> ; <lint>
# Internal-API contracts (proto/schema changes)
<codegen> ; <schema lint> ; <breaking-change check against main>
# Data-store migrations
<run migrations --target staging> ; <test migrations --target staging>
# Mobile (if in scope)
<mobile typecheck> ; <mobile test> ; <mobile e2e>
# Real-network smoke (the floor for PASS)
curl -s -o /dev/null -w "%{http_code}\n" https://staging.<product-domain>/health/ready
```

**Inverted-handoff fallback** (subagent Bash denied, per prompts/system-prompt.md): the agent enumerates the exact commands; the orchestrator runs them; the agent verifies the reported output — do NOT trust on faith, ask for the failing test names and counts.

## Common claims and what they actually require

| Claim | Requires | NOT sufficient |
|---|---|---|
| "Tests pass" | Fresh run, 0 failures, count shown | Yesterday's pass; "should pass" |
| "Build succeeds" | Fresh build command exit 0 OR install+import | Linter clean; "logs look good" |
| "Lint clean" | Fresh lint command exit 0 | Eyeballing the diff |
| "Type check passes" | Fresh type-check command exit 0 | "I followed the types" |
| "Bug fixed" | Test reproducing the original symptom now passes | Code changed, assumed fixed |
| "Regression test works" | Red-green cycle: revert fix → FAILS → restore → PASSES | Test passes once |
| "QA PASS" | load/real-network smoke + e2e green + cost-tier audit + metric-parity | Component tests green |
| "Security APPROVED" | Each threat-model finding has a verification snippet AND it succeeds | "Looks safe" |
| "Sub-agent done" | Diff inspected (`git diff`) + verification re-run by orchestrator | Sub-agent's report |
| "Requirements met" | Line-by-line spec checklist, each item verified | "Tests pass, must be done" |

## Red flags — STOP

"should pass / should work / probably works"; "Great! / Perfect! / Done! / All set!"; about to commit/push/open PR; about to emit a `→ <next-agent>` handoff; trusting a sub-agent or vendor success report (did you OPEN the mutation/coverage report?); partial verification (unit pass when integration matters); "just this once"; wording implying success without saying it ("ready for QA", "shipping it").

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "I'm confident" | Confidence ≠ evidence |
| "Linter passed" | Linter ≠ type checker ≠ tests ≠ smoke |
| "Tests passed yesterday" | Code changed; run them again |
| "The orchestrator will run it" | Then wait for the output, with counts, before claiming PASS |
| "I'm tired and want to move on" | Exhaustion is when most regressions ship |
| "PR template doesn't ask for proof" | Add the proof anyway |

## Key patterns

```
Tests:      ✅ [<test cmd>] [49/49 passed, 0 failed, exit 0] → "Tests pass"   ❌ "Should pass now"
Regression: ✅ write→FAIL→fix→PASS→revert→FAIL→restore→PASS → "confirmed"     ❌ "I wrote a regression test" (no revert)
Build:      ✅ [<build cmd>] [exit 0, build artifact created] → "Build passes" ❌ "Types compile, build should work"
Smoke:      ✅ [curl health/ready 200][curl happy-path 200, valid JSON]       ❌ "in-process request() returned 200"
Sub-agent:  ✅ runs git diff + re-runs verification + reads counts            ❌ trust the "all good"
```

## Why this matters

When a product ships financial-adjacent metrics and operates regulated channels (see `COMPLIANCE.md`), a false "PASS" costs the Stakeholder's trust in the entire product the moment a user asks "why did this number drop last week?" and the answer is "a test that wasn't actually run masked a bug." Delayed-attribution windows mean a bug shipped today can surface weeks later, past the ability to map cause to effect.

## When to apply

ALWAYS before: any completion/success/ready claim; any expression of satisfaction; committing/pushing/opening a PR; emitting a `→ <next-agent>` handoff; moving to the next task; delegating to a sub-agent (verify its output); writing in `memory/qa/<slug>.md` that QA cleared a feature; writing in `memory/incidents/<date>-<slug>.md` that an incident is resolved.

## Wiring

| Concern | Owner | Reference |
|---|---|---|
| Every builder's verification floor | Backend, AI/ML, Frontend, Mobile Engineers | their agent MDs + Iron Law #5 |
| QA PASS/FAIL discipline | **QA Engineer** | the Product Canon (`.engineering-os/knowledge-base/`) |
| Inverted-handoff verification | orchestrator | prompts/system-prompt.md |
| Audit trail of verification claims | `memory/qa/<slug>.md` + the system-of-record audit log | |

Related: `testing-tdd`, `systematic-debugging`, `operational-readiness`.

No shortcuts. Run the command. Read the output. **Then** claim the result.
