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

## Brain verification commands (canonical)

```bash
# TypeScript / Node (api-gateway, core, notifications, lifecycle Node)
pnpm test ; pnpm test:e2e ; pnpm typecheck ; pnpm lint ; pnpm build
# Python (ingestion, analytics, intelligence, lifecycle Python)
uv run pytest ; uv run pytest --cov ; uv run mypy . ; uv run ruff check .
# gRPC contracts (proto changes)
buf generate ; buf lint ; buf breaking --against '.git#branch=main'
# ClickHouse migrations
dbt run --target staging ; dbt test --target staging
# Mobile (RN + Expo)
pnpm --filter mobile typecheck ; pnpm --filter mobile test ; pnpm --filter mobile detox test
# Real-network smoke (the floor for PASS)
curl -s -o /dev/null -w "%{http_code}\n" https://staging.brain.pipadacapital.com/api/health/ready
```

**Inverted-handoff fallback** (subagent Bash denied, per prompts/system-prompt.md): the agent enumerates the exact commands; the orchestrator runs them; the agent verifies the reported output — do NOT trust on faith, ask for the failing test names and counts.

## Common claims and what they actually require

| Claim | Requires | NOT sufficient |
|---|---|---|
| "Tests pass" | Fresh run, 0 failures, count shown | Yesterday's pass; "should pass" |
| "Build succeeds" | Fresh `pnpm build` exit 0 OR `uv run` install+import | Linter clean; "logs look good" |
| "Lint clean" | Fresh `pnpm lint` / `ruff check` exit 0 | Eyeballing the diff |
| "Type check passes" | Fresh `pnpm typecheck` / `mypy` exit 0 | "I followed the types" |
| "Bug fixed" | Test reproducing the original symptom now passes | Code changed, assumed fixed |
| "Regression test works" | Red-green cycle: revert fix → FAILS → restore → PASSES | Test passes once |
| "Tanvi PASS" | k6 smoke + Playwright/Detox green + paradigm-audit + metric-parity | Component tests green |
| "Shreya APPROVED" | Each threat-model finding has a verification snippet AND it succeeds | "Looks safe" |
| "Sub-agent done" | Diff inspected (`git diff`) + verification re-run by orchestrator | Sub-agent's report |
| "Requirements met" | Line-by-line spec checklist, each item verified | "Tests pass, must be done" |

## Red flags — STOP

"should pass / should work / probably works"; "Great! / Perfect! / Done! / All set!"; about to commit/push/open PR; about to emit a `→ <next-agent>` handoff; trusting a sub-agent or vendor success report (did you OPEN the Stryker report?); partial verification (unit pass when integration matters); "just this once"; wording implying success without saying it ("ready for QA", "shipping it").

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "I'm confident" | Confidence ≠ evidence |
| "Linter passed" | Linter ≠ compiler ≠ tests ≠ smoke |
| "Tests passed yesterday" | Code changed; run them again |
| "The orchestrator will run it" | Then wait for the output, with counts, before claiming PASS |
| "I'm tired and want to move on" | Exhaustion is when most regressions ship |
| "PR template doesn't ask for proof" | Add the proof anyway |

## Key patterns

```
Tests:      ✅ [pnpm test] [49/49 passed, 0 failed, exit 0] → "Tests pass"   ❌ "Should pass now"
Regression: ✅ write→FAIL→fix→PASS→revert→FAIL→restore→PASS → "confirmed"    ❌ "I wrote a regression test" (no revert)
Build:      ✅ [pnpm build] [exit 0, dist/main.js created] → "Build passes"  ❌ "Types compile, build should work"
Smoke:      ✅ [curl health/ready 200][curl happy-path 200, valid JSON]      ❌ "in-process app.request() returned 200"
Sub-agent:  ✅ runs git diff + re-runs verification + reads counts           ❌ trust the "all good"
```

## Why this matters for Brain

Brain ships financial-adjacent metrics (CM2, MER, recovered-revenue) and a regulated channel (AI calling under DLT/NCPR). A false "PASS" costs the Founder's trust in the entire MER dashboard the moment a customer asks "why did CM2 drop ₹2L last week?" and the answer is "a test that wasn't actually run masked a bug." The 7d/30d attribution windows mean a bug shipped today shows up two weeks later, past the ability to map cause to effect.

## When to apply

ALWAYS before: any completion/success/ready claim; any expression of satisfaction; committing/pushing/opening a PR; emitting a `→ <next-agent>` handoff; moving to the next task; delegating to a sub-agent (verify its output); writing in `memory/qa/<slug>.md` that Tanvi cleared a feature; writing in `memory/incidents/<date>-<slug>.md` that an incident is resolved.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Every builder's verification floor | Vikram, Maya, Ananya, Karan | their agent MDs + Iron Law #5 |
| QA PASS/FAIL discipline | **Tanvi** | canon/technical-requirements.md |
| Inverted-handoff verification | orchestrator | prompts/system-prompt.md |
| Audit trail of verification claims | `memory/qa/<slug>.md` + Decision Log | |

Related: `testing-tdd`, `systematic-debugging`, `operational-readiness`.

No shortcuts. Run the command. Read the output. **Then** claim the result.
