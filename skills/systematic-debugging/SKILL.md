---
name: systematic-debugging
description: Four-phase debugging (Root Cause → Pattern → Hypothesis → Implementation) + backward call-stack tracing. Never jump to fixes. Use for any test failure, incident, regression, or build failure.
---

# Systematic Debugging

Random fixes waste time and create new bugs. In a distributed system (e.g. multiple services over Postgres, an OLAP store, a message bus, a cache, RPC, an agent/tool layer, a mobile runtime, a CDN…) every "quick fix" risks creating a worse one.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to use

ANY technical issue: test failure, prod bug, unexpected behaviour, perf regression, build failure, integration drift. ESPECIALLY when under time pressure, when "one quick fix" seems obvious, when you've already tried multiple fixes, or when the Stakeholder wants it fixed NOW (systematic IS faster than thrashing). Simple bugs have root causes too — don't skip.

---

## The Four Phases

Complete each before proceeding to the next.

### Phase 1 — Root Cause Investigation

1. **Read errors carefully** — your log aggregator almost always already holds the exact message + stack trace + correlation IDs (`request_id` + the tenant/user keys). Don't paraphrase. Don't skim.
2. **Reproduce consistently** — can you trigger it reliably? In staging? For a specific tenant? Exact steps? If not reproducible → gather more data, don't guess.
3. **Check recent changes** — `git log --since='24 hours ago'`; deploy/release history; new connector config / ADR / tool definition?
4. **Gather evidence at component boundaries** (a distributed system — assume nothing about which service is broken). For each boundary the request crosses, log what enters and exits:
   ```
   web/BFF → API gateway:    request_id, tenant key, auth claim
   gateway → core service:   RPC request, response, latency
   service → datastore:      query, params (sanitized), row count
   service → message bus:    topic, partition, offset, message_id
   ingestion → external API: endpoint, status, retry count
   ```
   A single correlation ID runs across all surfaces — search the log aggregator for `request_id:abc123` and you see every hop.
5. **Trace data flow backwards** (see below). When the error is deep in the call stack, the fix usually isn't there.

### Phase 2 — Pattern Analysis

1. **Find working examples** — another service / connector / tenant that does this correctly?
2. **Compare against references** — the Product Canon (HLD/LLD, INVARIANTS), ADRs, the canonical implementation.
3. **Identify differences** — list every difference; don't assume "that can't matter."
4. **Understand dependencies** — a datastore extension? A message-bus topic? An infra/IAM role? Vendor token rotation?

### Phase 3 — Hypothesis and Testing

1. **Form one hypothesis** — "I think X is the root cause because Y." Be specific. Write it down.
2. **Test minimally** — smallest change to verify. One variable at a time. Never bundle.
3. **Verify before continuing** — yes → Phase 4. No → new hypothesis (do NOT pile fixes).
4. **Say "I don't understand X"** — ask the `architect`, `security-reviewer`, or `cto-advisor` per layer.

### Phase 4 — Implementation

1. **Create a failing test** that reproduces the bug. Smallest possible repro. MUST exist before the fix.
2. **Implement one fix** at the root cause. ONE change. No "while I'm here" cleanups (Iron Law #4 — Surgical Changes).
3. **Verify the fix** — full suite + the repro test (see `verification-before-completion`).
4. **If fix doesn't work — STOP. Count attempts.** <3: return to Phase 1 with new info. **≥3: STOP — question the architecture.**
5. **3+ fixes failed → architecture question.** Pattern: each fix reveals new shared state/coupling elsewhere, requires "massive refactoring," or creates new symptoms in different paths. Ask: is this pattern fundamentally sound? Escalate the architecture call to the Architect + Engineering Advisor. This is NOT a failed hypothesis — it's a wrong architecture.

---

## Backward root-cause tracing

Phase 1's hardest step. Bugs manifest deep in the call stack — a message-bus offset-commit failure traced to a handler that didn't `await`; an OLAP insert failure traced to a model with a stray `None`; an action emitted outside a permitted window traced to an audit-log replay that bypassed the compliance check. Your instinct is to fix where the error appears. That's symptom-treatment.

**Trace backward through the call chain until you find the original trigger. Fix at the source.**

1. **Observe the symptom** — read the exact error (e.g. `Mandatory column 'tenant_id' has no value`).
2. **Find the immediate cause** — what directly throws? `await store.insert("events_raw", rows)`.
3. **Ask what called this, with what value?** — `rows` from `batch.events`; `batch` from `Connector.poll()`.
4. **Keep tracing upward**, recording the value at each hop:
   ```
   Connector.poll() → maps OrderEvent → bus topic orders.v1
     → ingestion consumer batches → BatchProcessor.process() → store.insert(...)
   #  OrderEvent.tenant_id == None for one row
   ```
5. **Find the original trigger.** Here: an old migration left `integrations` rows with `tenant_id=NULL`.

**Fix at source, not symptom:** wrong — filter bad rows in the insert. Right — (1) backfill the missing tenant key; (2) add a NOT NULL constraint; (3) defense-in-depth — `Connector` raises on a missing tenant key, never produces the event (see `multi-tenancy-isolation`).

### When async boundaries lose the stack

Across a message bus, RPC, or a job queue the call stack is gone. Instrument **before** the dangerous call (after-fail loses inputs):

```python
async def insert_events(rows):
    if any(r.tenant_id is None for r in rows):
        import traceback
        logger.error("DEBUG events with null tenant_id", extra={
            "null_count": sum(1 for r in rows if r.tenant_id is None),
            "stack": traceback.format_stack(),
            "request_id": correlation_id.get(),
        })
    await store.insert("events_raw", rows)
```

Use `logger.error()` not `print()` so it lands in the log aggregator with the `request_id`.

### Cross-service tracing

A single correlation ID runs web/BFF → API gateway → RPC → service → message bus → consumer. Search the log aggregator for one `request_id` to get the complete chain across every service. For span timing use the distributed-tracing backend (OpenTelemetry / X-Ray / equivalent), querying its trace-summaries API over the relevant window.

### Finding which test polluted shared state

```bash
<test-runner> --bail              # stop at first failure
<test-runner> --shard 1/4         # narrow by shard
for f in $(find . -name '*.test.*' | sort); do
  echo "=== $f ===" && <test-runner> run "$f" || break   # find the polluter
done
for i in {1..20}; do <e2e-runner> --spec e2e/<flow>.spec.* || echo "Failed at run $i"; done
```

### Worked example — the JWT entropy bug

**Symptom:** integration tests intermittently failed JWT verification with "bad signature." **Trace:** test signs JWT with a local secret → the gateway verify hook reads `JWT_SECRET` (12 chars) → the HMAC-SHA256 library tolerates short secrets → parallel tests mutated `JWT_SECRET` mid-flight. **Root cause:** `JWT_SECRET` was both `< 32` bytes (a Security HIGH) AND mutated, breaking parallel test isolation. **Fix (layered):** (1) fail-fast on missing `JWT_SECRET`; (2) fail-fast on `< 32` bytes — entropy floor; (3) fresh per-test secret + hermetic verifier; (4) an audit-log row on `session.invalidate_all`. Stop at "bump the secret length" and the pollution bug survives.

---

## Debugging cheatsheet

| Symptom | Where to look first | Owner |
|---|---|---|
| "Tests pass locally, fail in CI" | build-config drift; missing build output; module-format (ESM/CJS) mismatch | Backend Engineer |
| "OLAP query suddenly slow" | query plan; partition pruning; materialized-view merge lag; storage-parts stats | AI/ML Engineer |
| "Webhook from a connector fires twice" | idempotency key cardinality; vendor retry; consumer offset | AI/ML Engineer |
| "Audit-log row missing" | gateway logs for request_id; tx rollback; write-tool scope | Backend Engineer + AI/ML Engineer |
| "Scheduled notification didn't arrive" | push receipt; APNS/FCM error; opt-out state; synthesis log | Mobile Engineer + AI/ML Engineer |
| "Action emitted outside the permitted window" | compliance-check config; time-window guard; consent/registry cache freshness | AI/ML Engineer + Security Reviewer |
| "A metric differs between dashboard and store" | metric-registry parity across runtimes; version reconciliation | AI/ML Engineer + QA Engineer |
| "Pod restart loop" | liveness probe failure mode; cold cache; OOMKilled | Platform/SRE + Backend Engineer |
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

## OS wiring

| Concern | Owner | Reference |
|---|---|---|
| Incident debugging | **Platform/SRE** | Product Canon `PLAYBOOK-incident.md` |
| Service-level debugging | each builder | service-specific skill |
| Cross-service correlation | request_id + the tenant/user keys everywhere | `observability` |
| Postmortems with root cause | **Platform/SRE** + the builder | `incident-response` |

Related: `multi-tenancy-isolation`, `verification-before-completion`, `observability`.

Impact of working systematically: 15–30 min to fix vs 2–3 hrs thrashing; first-time fix rate ~95% vs ~40%; near-zero new bugs vs common.
