---
name: systematic-debugging
description: Four-phase debugging (Root Cause → Pattern → Hypothesis → Implementation) + backward call-stack tracing. Never jump to fixes. Use for any test failure, incident, regression, or build failure.
---

# Systematic Debugging

Random fixes waste time and create new bugs. In a 7-service distributed system (Postgres, ClickHouse, Kafka, Redis, gRPC, MCP, Expo, CloudFront…) every "quick fix" risks creating a worse one.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to use

ANY technical issue: test failure, prod bug, unexpected behaviour, perf regression, build failure, integration drift. ESPECIALLY when under time pressure, when "one quick fix" seems obvious, when you've already tried multiple fixes, or when the Founder wants it fixed NOW (systematic IS faster than thrashing). Simple bugs have root causes too — don't skip.

---

## The Four Phases

Complete each before proceeding to the next.

### Phase 1 — Root Cause Investigation

1. **Read errors carefully** — Brain logs land in OpenSearch (Fluent Bit → OpenSearch). The exact message + stack trace + `request_id` + `workspace_id` is almost always already there. Don't paraphrase. Don't skim.
2. **Reproduce consistently** — can you trigger it reliably? In staging? In a specific tenant? Exact steps? If not reproducible → gather more data, don't guess.
3. **Check recent changes** — `git log --since='24 hours ago'`; ArgoCD application history; new connector config / ADR / MCP tool?
4. **Gather evidence at component boundaries** (Brain is distributed — assume nothing about which service is broken). For each boundary the request crosses, log what enters and exits:
   ```
   Web BFF → api-gateway:      request_id, workspace_id, auth claim
   api-gateway → core-service: gRPC request, response, latency
   core-service → Postgres:    SQL, params (sanitized), row count
   core-service → Kafka:       topic, partition, offset, message_id
   ingestion-service → vendor: endpoint, status, retry count
   ```
   Brain's single correlation ID runs across all surfaces — search OpenSearch for `request_id:abc123` and you see every hop.
5. **Trace data flow backwards** (see below). When the error is deep in the call stack, the fix usually isn't there.

### Phase 2 — Pattern Analysis

1. **Find working examples** — another Brain service / connector / tenant that does this correctly?
2. **Compare against references** — TECH docs, ADRs, the canonical implementation.
3. **Identify differences** — list every difference; don't assume "that can't matter."
4. **Understand dependencies** — Postgres extension? Kafka topic? EKS IAM role? Vendor token rotation?

### Phase 3 — Hypothesis and Testing

1. **Form one hypothesis** — "I think X is the root cause because Y." Be specific. Write it down.
2. **Test minimally** — smallest change to verify. One variable at a time. Never bundle.
3. **Verify before continuing** — yes → Phase 4. No → new hypothesis (do NOT pile fixes).
4. **Say "I don't understand X"** — ask `aryan-architect`, `shreya-security`, or `rohan-cto-advisor` per layer.

### Phase 4 — Implementation

1. **Create a failing test** that reproduces the bug. Smallest possible repro. MUST exist before the fix.
2. **Implement one fix** at the root cause. ONE change. No "while I'm here" cleanups (Iron Law #4 — Surgical Changes).
3. **Verify the fix** — full suite + the repro test (see `verification-before-completion`).
4. **If fix doesn't work — STOP. Count attempts.** <3: return to Phase 1 with new info. **≥3: STOP — question the architecture.**
5. **3+ fixes failed → architecture question.** Pattern: each fix reveals new shared state/coupling elsewhere, requires "massive refactoring," or creates new symptoms in different paths. Ask: is this pattern fundamentally sound? Escalate the architecture call to Aryan + Rohan. This is NOT a failed hypothesis — it's a wrong architecture.

---

## Backward root-cause tracing

Phase 1's hardest step. Bugs manifest deep in the call stack — a Kafka offset-commit failure traced to a tRPC handler that didn't `await`; a ClickHouse insert failure traced to a Pydantic model with a stray `None`; an AI call placed outside calling hours traced to a Decision Log replay that bypassed the compliance engine. Your instinct is to fix where the error appears. That's symptom-treatment.

**Trace backward through the call chain until you find the original trigger. Fix at the source.**

1. **Observe the symptom** — read the exact error (`Code: 50. DB::Exception: Mandatory column 'workspace_id' has no value`).
2. **Find the immediate cause** — what directly throws? `await ch.insert("events_raw", rows)`.
3. **Ask what called this, with what value?** — `rows` from `batch.events`; `batch` from `ShopifyConnector.poll()`.
4. **Keep tracing upward**, recording the value at each hop:
   ```
   ShopifyConnector.poll() → maps ShopifyOrderEvent → Kafka shopify.orders.v1
     → ingestion consumer batches → BatchProcessor.process() → ch.insert(...)
   #  ShopifyOrderEvent.workspace_id == None for one row
   ```
5. **Find the original trigger.** Here: an old migration left `integrations` rows with `workspace_id=NULL`.

**Fix at source, not symptom:** wrong — filter bad rows in the insert. Right — (1) backfill the missing `workspace_id`; (2) add NOT NULL constraint; (3) defense-in-depth — `ShopifyConnector` raises on missing `workspace_id`, never produces the event (see `defense-in-depth-validation`).

### When async boundaries lose the stack

Across Kafka, gRPC, BullMQ the call stack is gone. Instrument **before** the dangerous call (after-fail loses inputs):

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

Use `logger.error()` not `print()` so it lands in OpenSearch with the `request_id`.

### Cross-service tracing

A single correlation ID runs web BFF → api-gateway → gRPC → service → Kafka → consumer. Search OpenSearch for one `request_id` for the complete chain across all 7 services. For span timing use AWS X-Ray:
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
for i in {1..20}; do pnpm test:e2e --spec e2e/morning-brief.spec.ts || echo "Failed at run $i"; done
```

### Real Brain example — the JWT entropy bug (slice-3)

**Symptom:** integration tests intermittently failed JWT verification with "bad signature." **Trace:** test signs JWT with local secret → api-gateway verify hook reads `JWT_SECRET` (12 chars) → `jose` HMAC-SHA256 tolerates short secrets → parallel tests mutated `JWT_SECRET` mid-flight. **Root cause:** `JWT_SECRET` was both `< 32` bytes (Shreya HIGH) AND mutated, breaking parallel test isolation. **Fix (layered):** (1) fail-fast on missing `JWT_SECRET`; (2) fail-fast on `< 32` bytes — entropy floor; (3) fresh per-test secret + hermetic verifier; (4) Decision Log row on `session.invalidate_all`. Stop at "bump the secret length" and the pollution bug survives.

---

## Brain-specific debugging cheatsheet

| Symptom | Where to look first | Owner |
|---|---|---|
| "Tests pass locally, fail in CI" | tsconfig drift; missing build output; ESM/CJS mismatch | Vikram |
| "ClickHouse query suddenly slow" | EXPLAIN PIPELINE; partition pruning; MV merge lag; `system.parts` | Maya |
| "Webhook from Shopify fires twice" | idempotency key cardinality; Shopify retry; consumer offset | Maya |
| "Decision Log row missing" | api-gateway logs for request_id; tx rollback; MCP write scope | Vikram + Maya |
| "Push didn't arrive at 07:05 IST" | EAS push receipt; APNS/FCM error; opt-out state; synthesis log | Karan + Maya |
| "AI call placed at 22:00 IST" | compliance engine config; calling-hours guard; NCPR cache freshness | Maya + Shreya |
| "MER differs between dashboard and DB" | metric-registry parity (TS vs Python); v1↔v2 reconciliation | Maya + Tanvi |
| "EKS pod restart loop" | liveness probe failure mode; cold cache; OOMKilled | Jatin + Vikram |
| "Sub-agent reported success but code is broken" | `git diff`; re-run verification; trust nothing | orchestrator |

## Red flags — STOP and return to Phase 1

"Quick fix for now," "just try changing X," "add multiple changes then test," "skip the test, I'll manually verify," "it's probably X," "this might work," "one more fix attempt" (after 2+), each fix revealing a new problem elsewhere.

## Common rationalisations

| Excuse | Reality |
|---|---|
| "Issue is simple" | Simple issues have root causes too |
| "Emergency, no time" | Systematic IS faster than guess-and-check |
| "Try this first, investigate later" | First fix sets the pattern |
| "Test after confirming the fix" | Untested fixes don't stick |
| "Multiple fixes at once" | Can't isolate what worked |
| "One more attempt" (after 2+) | 3+ failures = architectural problem |

## When the process reveals "no root cause"

If investigation truly leaves it environmental/external/timing-dependent: (1) document in `memory/incidents/<date>-<slug>.md`; (2) implement handling (retry, timeout, circuit breaker, clearer error); (3) add monitoring so the next instance has more evidence. But 95% of "no root cause" cases are incomplete investigation.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Incident debugging | **Jatin** | canon/technical-requirements.md (incident playbook) |
| Service-level debugging | each builder | service-specific skill |
| Cross-service correlation | request_id + workspace_id everywhere | canon/technical-requirements.md |
| Postmortems with root cause | **Jatin** + the builder | `blueprints/postmortem.md` |

Related: `defense-in-depth-validation`, `verification-before-completion`, `observability`.

Slice-3 impact: systematic 15–30 min to fix vs 2–3 hrs thrashing; first-time fix rate 95% vs 40%; near-zero new bugs vs common.
