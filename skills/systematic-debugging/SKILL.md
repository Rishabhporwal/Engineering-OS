---
name: systematic-debugging
description: Four-phase debugging (Root Cause → Pattern Analysis → Hypothesis → Implementation) plus backward root-cause tracing through the call stack. Never jump to fixes. Use for any test failure, production incident, unexpected behaviour, performance regression, build failure, or when an error manifests deep in execution far from its trigger on the Brain stack (Fastify, FastAPI, ClickHouse, Kafka, Expo, gRPC).
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

5. **Trace data flow backwards** — see "Backward root-cause tracing" below. When the error is deep in the call stack, the fix usually isn't there. Trace up until you find the original trigger.

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

## Backward root-cause tracing

Phase 1's hardest step. Bugs manifest deep in the call stack — a Kafka offset-commit failure traced to a tRPC handler that didn't `await`; a ClickHouse insert failure traced to a Pydantic model with a stray `None`; an AI call placed outside calling hours traced to a Decision Log replay that bypassed the compliance engine. Your instinct is to fix where the error appears. That's symptom-treatment.

**Core principle:** Trace backward through the call chain until you find the original trigger. Then fix at the source.

### The tracing process

1. **Observe the symptom** — read the exact error, don't paraphrase (`Code: 50. DB::Exception: Mandatory column 'workspace_id' has no value`).
2. **Find the immediate cause** — what code directly throws? `await ch.insert("events_raw", rows)`.
3. **Ask what called this, and with what value?** — `rows = [e.dict() for e in batch.events]`; `batch` comes from `ShopifyConnector.poll()`.
4. **Keep tracing upward**, recording the value at each hop:
   ```
   ShopifyConnector.poll() → maps ShopifyOrderEvent → Kafka shopify.orders.v1
     → ingestion consumer batches → BatchProcessor.process() → ch.insert(...)
   #  ShopifyOrderEvent.workspace_id == None for one row
   ```
5. **Find the original trigger.** Here: an old migration left some `integrations` rows with `workspace_id=NULL`; every poll for those connectors emits broken events.

**Fix at source, not symptom:** wrong — filter out the bad rows in the insert. Right — (1) backfill the missing `workspace_id` in `integrations`; (2) add a NOT NULL constraint; (3) add defense-in-depth — `ShopifyConnector` raises on missing `workspace_id`, never produces the event (see `defense-in-depth-validation`).

### When async boundaries lose the stack

Across Kafka, gRPC, BullMQ jobs the call stack is gone. Add explicit instrumentation **before** the dangerous call (after-fail loses the inputs):

```python
async def insert_events(rows):
    if any(r.workspace_id is None for r in rows):
        import traceback
        logger.error("DEBUG events with null workspace_id", extra={
            "null_count": sum(1 for r in rows if r.workspace_id is None),
            "stack": traceback.format_stack(),
            "request_id": correlation_id.get(),
        })
    await ch.insert("events_raw", rows)
```

Use `logger.error()` not `print()` so it lands in OpenSearch with the `request_id`, searchable later.

### Cross-service tracing in Brain

Brain runs **a single correlation ID** across web BFF → api-gateway → gRPC → service → Kafka → consumer (canon/BRAIN_TECHNICAL.md). Search OpenSearch for one `request_id` and you get the complete chain across all 7 services — a failure in `analytics-service` at hop 5 ties back to the originating tRPC call at hop 1 and the dashboard click at hop 0. For span timing use AWS X-Ray:
```bash
aws xray get-trace-summaries --start-time $(date -u -d '-1 hour' +%s) --end-time $(date +%s)
```

### Finding which test polluted shared state

```bash
pnpm test --bail              # stop at first failure
pnpm test --shard 1/4         # narrow by shard
for f in $(find . -name '*.test.ts' | sort); do
  echo "=== $f ===" && pnpm vitest run "$f" || break   # find the polluter
done
# Cypress/Detox flake hunt — run the suspect in isolation 20×
for i in {1..20}; do pnpm test:e2e --spec cypress/e2e/morning-brief.cy.ts || echo "Failed at run $i"; done
```

### Real Brain example — the JWT entropy bug (slice-3)

**Symptom:** integration tests intermittently failed JWT verification with "bad signature". **Trace chain:** test signs JWT with local secret → api-gateway verify hook reads `JWT_SECRET` (12 chars) → `jose` HMAC-SHA256 tolerates short secrets → but parallel tests mutated `JWT_SECRET` mid-flight after another cached the wrong value. **Root cause:** `JWT_SECRET` was both `< 32` bytes (Shreya HIGH finding) AND mutated in a setup that broke parallel test isolation. **Fix at source (layered):** (1) fail-fast on missing `JWT_SECRET`; (2) **fail-fast on `< 32` bytes** — entropy floor; (3) fresh per-test secret + hermetic verifier; (4) Decision Log row on `session.invalidate_all` so cross-test pollution surfaces. Stop at "I'll bump the secret length" and the parallel-test pollution bug survives.

**Stack-trace tips:** in tests use `logger.error()` not `print()` (runner swallows it); log **before** the dangerous call; include `correlation_id` + `workspace_id` + key inputs; capture `new Error().stack` (Node) / `traceback.format_stack()` (Python); across services rely on the correlation ID, X-Ray, OpenSearch — not local stacks.

**NEVER fix just where the error appears.** Trace to the original trigger, then `defense-in-depth-validation` ensures the class of bug can't recur.

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

Related Brain skills: `defense-in-depth-validation` (post-RC, add structural prevention), `verification-before-completion` (verify the fix is real), `observability` (where the logs/traces live).

## Real-world impact (from the slice-3 retro)

- Systematic approach: 15–30 min to fix
- Random fixes approach: 2–3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: near zero vs common

Slice-3 captured the team-wide version of this lesson in `.engineering-os/lessons-learned.md`: *"Don't fake green-tests claims."* This skill is the upstream discipline that makes that lesson hold.
