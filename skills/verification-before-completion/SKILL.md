---
name: verification-before-completion
description: Run verification commands and confirm output before claiming success. The operational depth behind Iron Law #5 (Goal-Driven Execution). Use before any "done" / "ready" / "tests pass" / "should work" claim, before committing, before opening a PR, before signaling a handoff in Brain's agent pipeline.
---

# Verification Before Completion

> Claiming work is complete without verification is dishonesty, not efficiency.

This skill is the **operational depth behind Iron Law #5 — Goal-Driven Execution** in prompts/system-prompt.md. It's also what `.engineering-os/lessons-learned.md` already references as "don't fake green-tests claims" (slice-3). Both apply: every builder agent, on every handoff signal, every PR description, every status update.

**Core principle:** Evidence before claims, always.
**Violating the letter of this rule is violating the spirit.**

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
4. VERIFY:    Does output confirm the claim?
   - If NO: state the actual status with evidence
   - If YES: state the claim WITH evidence
5. ONLY THEN: make the claim

Skip any step = lying, not verifying.
```

## Brain verification commands (canonical)

These match the locked stack. Use these in handoff signals and PR descriptions.

```bash
# TypeScript / Node services (api-gateway, core, notifications, lifecycle Node)
pnpm test
pnpm test:e2e        # Cypress for web; Detox for mobile
pnpm typecheck
pnpm lint
pnpm build

# Python services (ingestion, analytics, intelligence, lifecycle Python)
uv run pytest
uv run pytest --cov
uv run mypy .
uv run ruff check .

# gRPC contracts (when proto changes)
buf generate
buf lint
buf breaking --against '.git#branch=main'

# ClickHouse migrations
dbt run --target staging
dbt test --target staging

# Mobile (RN + Expo)
pnpm --filter mobile typecheck
pnpm --filter mobile test
pnpm --filter mobile detox test

# Real-network smoke (the floor for PASS)
curl -s -o /dev/null -w "%{http_code}\n" https://staging.brain.pipadacapital.com/api/health/ready
```

For the **inverted-handoff fallback** (subagent Bash denied per prompts/system-prompt.md, "Inverted-handoff fallback"): the agent enumerates the exact commands above; the orchestrator runs them; the agent verifies the orchestrator's reported output (do NOT trust on faith, ask for the failing test names and counts).

## Common claims and what they actually require

| Claim | Requires | NOT sufficient |
|---|---|---|
| "Tests pass" | Fresh test run output, 0 failures, count shown | A test pass from yesterday; "they should pass" |
| "Build succeeds" | Fresh `pnpm build` exit 0 OR `uv run` install + import | Linter clean; "logs look good" |
| "Lint clean" | Fresh `pnpm lint` / `ruff check` exit 0 | Eyeballing the diff |
| "Type check passes" | Fresh `pnpm typecheck` / `mypy` exit 0 | "I followed the types" |
| "Bug fixed" | Test reproducing the original symptom now passes | Code changed, assumed fixed |
| "Regression test works" | Red-green cycle: revert fix → test FAILS → restore fix → test PASSES | Test passes once |
| "Tanvi PASS" | k6 smoke + Cypress/Detox green + paradigm-audit verified + metric-parity check | Component tests green |
| "Shreya APPROVED" | Threat-model findings each have a verification snippet AND the snippet's assertion succeeds | "Looks safe" |
| "Sub-agent done" | Diff inspected (`git diff`) + the verification commands re-run by orchestrator | Sub-agent's success report |
| "Requirements met" | Line-by-line spec checklist with each item verified | "Tests pass, must be done" |

## Red flags — STOP

If you catch yourself about to write any of these without fresh verification evidence, stop:

- "should pass", "should work", "probably works"
- "Great!", "Perfect!", "Done!", "All set!"
- About to commit / push / open PR
- About to emit a `→ <next-agent>` handoff signal
- Trusting a sub-agent or vendor success report ("Stryker says 80% mutation score" — did you open the report?)
- Partial verification ("the unit tests pass" when integration matter for the claim)
- "Just this once" — there are no exceptions
- Wording that *implies* success without saying the word ("ready for QA"; "shipping it")

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "I'm confident" | Confidence ≠ evidence |
| "Linter passed" | Linter ≠ compiler ≠ tests ≠ smoke |
| "Tests passed yesterday" | Code changed since; run them again |
| "The orchestrator will run it" | Then wait for the orchestrator's output, with counts, before claiming PASS |
| "I'm tired and want to move on" | Exhaustion is when most regressions ship |
| "Slack said it works" | Run it yourself |
| "The PR template doesn't ask for proof" | Add the proof to the description anyway |

## Key patterns

**Tests:**
```
✅ [pnpm test] [49/49 passed, 0 failed, exit 0] → "Tests pass"
❌ "Should pass now" / "I made the change cleanly"
```

**Regression tests (Red-Green):**
```
✅ Write test → run (FAILS) → make fix → run (PASSES) → revert fix → run (FAILS) → restore → run (PASSES) → "Regression test confirmed"
❌ "I've written a regression test" (without revert step)
```

**Build:**
```
✅ [pnpm build] [exit 0, dist/main.js created] → "Build passes"
❌ "Types compile, build should work"
```

**Real-network smoke (the floor for Tanvi's PASS):**
```
✅ [curl health/ready, 200] [curl one happy-path endpoint, 200, valid JSON] → "Smoke green at <sha>"
❌ "in-process app.request() returned 200" (in-process ≠ real network)
```

**Sub-agent delegation (every orchestrator + every sub-agent):**
```
✅ Sub-agent reports done → orchestrator runs `git diff`, runs the verification commands, reads counts → "Verified, commit a1b2c3 passes 49 tests"
❌ Trust the sub-agent's "all good"
```

## Why this matters for Brain specifically

Brain ships financial-adjacent metrics (CM2, MER, recovered-revenue) and a regulated channel (AI calling under DLT/NCPR). A false "PASS" doesn't just cost engineering rework — it costs the Founder's trust in the entire MER dashboard the moment the first customer asks "why did CM2 drop ₹2L last week?" and the answer is "a test that wasn't actually run masked a bug." The 7d/30d attribution windows on the Decision Log mean a bug shipped today shows up two weeks later, way past the ability to map cause to effect.

## When to apply

**ALWAYS, before:**
- Any variation of completion / success / ready claim
- Any expression of satisfaction with the work
- Committing, pushing, opening a PR
- Emitting a `→ <next-agent>` handoff signal in the Brain pipeline
- Moving to the next task
- Delegating to a sub-agent (verify the sub-agent's output)
- Writing in `memory/qa/<slug>.md` that Tanvi has cleared a feature
- Writing in `memory/incidents/<date>-<slug>.md` that an incident is resolved

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Every builder's verification floor | Vikram, Maya, Ananya, Karan | their agent MDs + Iron Law #5 in prompts/system-prompt.md |
| QA PASS/FAIL discipline | **Tanvi** | canon/BRAIN_TECHNICAL.md (SLO + test gates) |
| Inverted-handoff verification (Bash-denied subagents) | orchestrator | prompts/system-prompt.md (Inverted-handoff fallback) |
| Audit trail of verification claims | `memory/qa/<slug>.md` + Decision Log | |

Related Brain skills: `testing-tdd` (the tests themselves), `systematic-debugging` (when a verification fails, don't guess), `operational-readiness` (real-network smoke patterns).

## The bottom line

No shortcuts for verification. Run the command. Read the output. **Then** claim the result. This is non-negotiable for every agent on the Brain team.
