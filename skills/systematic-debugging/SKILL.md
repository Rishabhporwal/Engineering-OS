---
name: systematic-debugging
description: Four-phase debugging — Root Cause → Pattern Analysis → Hypothesis → Implementation. Never jump to fixes. Use for any test failure, production incident, unexpected behaviour, performance regression, or build failure on the Brain stack (Fastify, FastAPI, ClickHouse, Kafka, Expo, gRPC).
---

# Systematic Debugging

Random fixes waste time and create new bugs. Quick patches mask underlying issues, and in a 7-service distributed system with 14 dependent layers (Postgres, ClickHouse, Kafka, Redis, gRPC, MCP, Expo, CloudFront…) every "quick fix" risks creating a worse one.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to use

Use for ANY technical issue: test failure, prod bug, unexpected behaviour, perf regression, build failure, integration drift.

**Use this ESPECIALLY when:**
- Under time pressure (P0/P1 incidents are when guessing is most tempting and most expensive)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Founder wants it fixed NOW (systematic IS faster than thrashing)

---

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1 — Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read errors carefully** — Brain logs land in OpenSearch (Fluent Bit → OpenSearch per canon/BRAIN_TECHNICAL.md). The exact error message + stack trace + `request_id` + `workspace_id` is almost always already there. Don't paraphrase. Don't skim. Read every line.

2. **Reproduce consistently**
   - Can you trigger it reliably? In staging? In a specific tenant?
   - What are the exact steps?
   - If not reproducible → gather more data (more logs, more traces). Don't guess.

3. **Check recent changes**
   - `git log --since='24 hours ago'` — what shipped?
   - ArgoCD application history — which deployment landed when?
   - New connector config? New ADR? New MCP tool?

4. **Gather evidence at component boundaries** (Brain is distributed — assume nothing about which service is broken)

   For each boundary the request crosses, log what enters and exits:
   ```
   - Web BFF → api-gateway:     log request_id, workspace_id, auth claim
   - api-gateway → core-service: log gRPC request, response, latency
   - core-service → Postgres:    log SQL, params (sanitized), row count
   - core-service → Kafka:       log topic, partition, offset, message_id
   - ingestion-service → vendor: log endpoint, status, retry count
   ```

   Brain's single correlation ID (see canon/BRAIN_TECHNICAL.md) runs across all surfaces — use it. Search OpenSearch for `request_id:abc123` and you see every hop.

5. **Trace data flow backwards** — see `root-cause-tracing` skill. When the error is deep in the call stack, the fix usually isn't there. Trace up until you find the original trigger.

### Phase 2 — Pattern Analysis

Find the pattern before fixing.

1. **Find working examples** — does another Brain service do this correctly? Another connector? Another tenant?
2. **Compare against references** — TECH docs, ADRs, the canonical implementation. Don't skim.
3. **Identify differences** — list every difference between working and broken; don't assume "that can't matter."
4. **Understand dependencies** — what does this need? Postgres extension? Kafka topic? An EKS IAM role? Vendor token rotation?

### Phase 3 — Hypothesis and Testing

Scientific method:

1. **Form one hypothesis** — "I think X is the root cause because Y." Be specific. Write it down.
2. **Test minimally** — smallest possible change to verify. One variable at a time. Never bundle fixes.
3. **Verify before continuing** — yes → Phase 4. No → new hypothesis (do NOT pile fixes).
4. **Say "I don't understand X"** — don't fake it. Ask `aryan-architect`, `shreya-security`, or `rohan-cto-advisor` depending on the layer.

### Phase 4 — Implementation

Fix the root cause, not the symptom.

1. **Create a failing test** that reproduces the bug. Smallest possible repro. MUST exist before the fix.
   ```bash
   pnpm test path/to/repro.test.ts   # or uv run pytest path/to/repro_test.py
   ```
2. **Implement one fix.** Address the root cause. ONE change. No "while I'm here" cleanups. No bundled refactoring. (Iron Law #3 — Surgical Changes.)
3. **Verify the fix** — full test suite + the repro test. See `verification-before-completion`.
4. **If fix doesn't work** — STOP. Count fixes attempted.
   - <3 attempts: return to Phase 1 with new info.
   - **≥3 attempts: STOP — question the architecture.**

5. **3+ fixes failed → architecture question**

   Pattern indicating architectural problem:
   - Each fix reveals new shared state / coupling / problem elsewhere
   - Fixes require "massive refactoring"
   - Each fix creates new symptoms in different code paths

   STOP and ask: is this pattern fundamentally sound? Are we "sticking with it through inertia"? Should we refactor (likely escalate to Aryan + Rohan for the architecture call)?

   This is NOT a failed hypothesis — it's a wrong architecture. Discuss before attempting Fix #4.

---

## Brain-specific debugging cheatsheet

| Symptom | Where to look first | Owning agent |
|---|---|---|
| "Tests pass locally, fail in CI" | tsconfig drift; missing build output; ESM/CJS mismatch — see `operational-readiness` slice-1 lessons | Vikram |
| "ClickHouse query suddenly slow" | EXPLAIN PIPELINE; partition pruning; MV merge lag; `system.parts` row count | Maya |
| "Webhook from Shopify fires twice" | idempotency key cardinality; Shopify retry semantics; ingestion-service consumer offset | Maya |
| "Decision Log row missing" | look at api-gateway logs for the request_id; check tx rollback; check MCP write scope | Vikram + Maya |
| "Push notification didn't arrive at 07:05 IST" | EAS push receipt status; APNS/FCM error code; user opt-out state; Morning Brief synthesis log | Karan + Maya |
| "AI call placed at 22:00 IST" | compliance engine config; calling hours guard; NCPR cache freshness; was queue level blocked correctly | Maya + Shreya |
| "MER value differs between dashboard and DB" | metric-registry parity (TS lib-metrics vs Python brain_metrics); v1↔v2 reconciliation | Maya + Tanvi |
| "EKS pod restart loop" | liveness probe failure mode (don't depend on external deps); cold cache; OOMKilled | Jatin + Vikram |
| "Sub-agent reported success but code is broken" | check the diff (`git diff`); re-run the verification commands; trust nothing | orchestrator |

## Red flags — STOP and follow process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Here are the main problems: [lists fixes without investigation]"
- "One more fix attempt" (when you already tried 2+)
- Each fix reveals a new problem in a different place

**ALL of these mean: STOP. Return to Phase 1.**

## Common rationalisations

| Excuse | Reality |
|---|---|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic IS faster than guess-and-check thrashing. Jatin's incident playbook is literally this skill. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write the test after confirming the fix" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question pattern, don't fix again. |

## Quick reference

| Phase | Activities | Success criteria |
|---|---|---|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Identify the diff that matters |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass, no regressions |

## When the process reveals "no root cause"

If systematic investigation truly leaves it environmental / external / timing-dependent:
1. Document what you investigated (in `memory/incidents/<date>-<slug>.md`)
2. Implement appropriate handling (retry, timeout, circuit breaker, clearer error)
3. Add monitoring/logging so the next instance has more evidence

But: 95% of "no root cause" cases are incomplete investigation.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Incident debugging | **Jatin** | canon/BRAIN_TECHNICAL.md (incident playbook) |
| Service-level debugging | each builder for their service | service-specific skill |
| Cross-service correlation | request_id + workspace_id everywhere | canon/BRAIN_TECHNICAL.md (correlation) |
| Postmortems with root cause | **Jatin** + the builder | `blueprints/postmortem.md` |

Related Brain skills: `root-cause-tracing` (back-tracing through call stacks), `defense-in-depth-validation` (post-RC, add structural prevention), `verification-before-completion` (verify the fix is real), `observability` (where the logs/traces live).

## Real-world impact (from the slice-3 retro)

- Systematic approach: 15–30 min to fix
- Random fixes approach: 2–3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: near zero vs common

Slice-3 captured the team-wide version of this lesson in `.engineering-os/lessons-learned.md`: *"Don't fake green-tests claims."* This skill is the upstream discipline that makes that lesson hold.
