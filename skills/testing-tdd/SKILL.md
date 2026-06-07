---
name: testing-tdd
description: Generic testing discipline — TDD by mode, the test pyramid (unit/integration/contract/e2e), mandatory real-network smoke, the anti-pattern catalog, mutation testing, and verification validity (negative controls + tenant-scoping). Tools are examples; bind them to the product's STACK.md.
---

# Testing — TDD Discipline

> Tools named below (e.g. a test runner, an e2e driver, a load tool) are **illustrative examples**. The product's `STACK.md` binds the actual tools; the *discipline* is what transfers.

## TDD by Mode

| Mode | Rule |
|---|---|
| SCALE | Failing test before code (Iron Law TDD). Real-network smoke before PASS. Cost-tier (cheapest-sufficient-effort) audit verified. The Canon's compliance regime exercised. |
| SPEED | Tests on critical business logic only. Real-network smoke still required for PASS. |

## Testing pyramid

```
                    ▲
            E2E (web + mobile drivers) — critical journeys only
        Integration — real datastores + message bus (via docker compose)
                Unit — business logic + utilities
                    ▼
```

Plus, for any user-facing service: **real-network smoke test** (the PASS gate). Where the product has internal API contracts, add a **contract-test** layer (consumer/provider or breaking-change checks) between integration and e2e.

## Unit + integration — representative example

One canonical unit test (the same shape applies to whatever runners the product uses). Note the **tenant-scoping assertion** — every test asserts the isolation key propagates, not just the happy value:

```typescript
// example: a procedure that returns metrics scoped to a tenant
describe('store.kpis', () => {
  it('returns KPIs scoped to the requested tenant', async () => {
    const caller = createCaller({
      tenantId: 'tenant-1',
      rpc: { analytics: { getDailyMetrics: vi.fn().mockResolvedValue({ rows: [/* … */] }) } },
    });
    const result = await caller.store.kpis({ from, to });
    expect(result.rows).toHaveLength(3);
    expect(caller.rpc.analytics.getDailyMetrics).toHaveBeenCalledWith(
      expect.objectContaining({ tenant_id: 'tenant-1' }),
    );
  });
});
```

- **Integration tests run against real datastores + the real message bus via docker compose** — never mocked. Mocking the stores masks isolation (row-level security), query-gateway, and tenant-scoping bugs. The integration harness hits a real server and a real client; both assert the cross-tenant `403` and the unscoped-query rejection.
- **Cross-runtime parity:** where a calculation exists in more than one runtime/language, its tests mirror each other (e.g. `compute_ratio` → `None` on zero denominator, `2.0` on a 2:1 ratio) and are checked against an independent oracle. See the Canon's `METRICS.md` for the registry.

## E2E + load

Pointers, not full configs — canonical scaffolds live in the product repo and the Canon:

- **Web — e2e driver** (`apps/web/e2e/`): critical journeys only — e.g. a KPI load with conditional (RAG) coloring, a drill-down drawer. Assert with stable test IDs + web-first assertions on the state class. Cross-browser, parallel + sharding in CI, trace viewer for flake.
- **Mobile — e2e driver** (`apps/mobile/e2e/`): the primary journey — login → deep link → cards visible → an approve action writes a system-of-record audit row.
- **Load** (`load-tests/`): a `constant-arrival-rate` profile at the target RPS, thresholds like `p(95)<500ms` and `http_req_failed rate<0.01` on the hottest endpoint.

## Real-network smoke test — PASS gate (NON-NEGOTIABLE)

In-process mocks (`inject()`/`TestClient`-style harnesses) **skip the network stack** — they miss port-binding failures, TLS/reverse-proxy quirks, missing root handlers, address-in-use, real connection-pool behavior.

**PASS verdict requires** a smoke test that spawns the server on a real port and curls it:

```bash
# scripts/smoke.sh
set -euo pipefail
PORT=3001 <start the built server> & SERVER_PID=$!; trap "kill $SERVER_PID" EXIT
for i in {1..30}; do curl -fs http://localhost:3001/health && break || sleep 1; done
curl -fs http://localhost:3001/health | jq -e '.status == "ok"' > /dev/null
curl -fs -X POST http://localhost:3001/<happy-path-endpoint> \
  -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" \
  -d '{"from":"2026-04-01","to":"2026-04-30"}' | jq -e '.result.data.rows' > /dev/null
echo "SMOKE PASS"
```

The QA Engineer's PASS gate: the smoke script ran in THIS session AND exited 0. Otherwise FAIL.

## Mandatory verifications (on every relevant PR)

These are the highest-signal gates; bind the exact commands to `STACK.md`:

- **Cost-tier audit:** the audit check FAILs any endpoint/agent action that reaches for a more expensive tier (e.g. a large model) where a cheaper one (deterministic logic / statistical-ML / small model) suffices, or that is missing its declared cost annotation. (Owner skill: `cost-routing-paradigms`.)
- **Metric registry parity (cross-runtime):** the parity check diffs the registry across runtimes against an independent oracle — any drift FAILs. (Owner: `METRICS.md` + skill `metric-engine`.)
- **Multi-tenant isolation:** tenant A reading tenant B returns `403`; the analytics query gateway rejects any query without a tenant-key predicate.
- **Compliance regime** (any touch of a regulated surface): parametrized boundary tests for whatever `COMPLIANCE.md` declares — e.g. channel-window edges, frequency caps, consent/registration gates, residency. (Owner skill: `compliance-engine`.)

## Coverage targets

| Layer | Target |
|---|---|
| Services (business logic) | > 80% |
| Controllers / API procedures | > 60% |
| Utils + formatters | > 90% |
| Critical paths (auth, money, the compliance regime) | > 95% |
| Overall (excl. generated + third-party) | > 70% |

## Common failure modes

- **In-process inject for smoke** — doesn't bind a real port.
- **Tests dropped under session truncation** — write tests alongside production code, not as polish.
- **Coverage theater** — 90% line coverage on no-op getters/setters.
- **Mocking the datastores** — masks row-level-security + query-gateway bugs.
- **Forgetting the compliance regime** — every change to a regulated surface needs the full boundary matrix.

## Testing anti-patterns catalog

A green suite is only worth something if the tests would fail when the code is wrong. The QA Engineer bounces on any of these; every builder self-checks before handoff.

| Anti-pattern | Symptom | Fix |
|---|---|---|
| **Assertion-free** | No `expect`/`assert`, or only "didn't throw" | Assert the actual value/shape |
| **Over-mocking** | Unit-under-test or core stores mocked | Mock only true boundaries (HTTP, time, randomness); docker-compose for integration |
| **Implementation details** | Asserts private methods / internal call order | Assert observable behavior |
| **Test interdependence** | Fails in isolation / different order | Each test sets up + tears down its own state |
| **Snapshot abuse** | Giant auto-snapshots blind-`--update`ed | Snapshot small, intentional output; review every diff |
| **Non-determinism** | `Date.now()`, random, real network/timers | Freeze time, seed randomness, stub network |
| **Happy-path only** | Only the success case tested | Test 403/401, empty set, boundary, compliance-blocked path |
| **Logic in tests** | Conditionals/loops/computation in the test body | Straight-line: arrange, act, assert literals |
| **Mystery guest** | Depends on hidden external fixture data | Make fixtures local + explicit |
| **Coverage as goal** | Tests trivial getters to hit a % | Cover critical paths; ignore generated/trivial |
| **Asserting against code, not spec** | Expected value copied from current output | Derive expected value from the requirement independently |

**Must-cover edges** (not optional): cross-tenant 403, metric registry parity (cross-runtime), money minor-unit/rounding, division-by-zero metrics → `None`, the full compliance boundary matrix on any regulated-surface touch.

## Verification validity — negative controls (a test must be able to fail)

A green test under a bypassed security/tenancy context is worse than no test. Enforce:
- Security/tenancy/auth tests run under the **real, non-bypassed** context.
- Every protection probe **fails when the protection is removed** (a negative control) — if removing the guard still passes, the test is tautological.
- No tautological parity: derive the expected number from the requirement, never copy it from current output.

## Test effectiveness — mutation testing

Coverage says "this line ran." Mutation testing says "this line was *meaningfully* asserted." **Mutants** are tiny automatic edits (`a+b`→`a-b`, `>`→`>=`, `true`→`false`). A mutant is **killed** when a test fails (good), **survives** when all tests pass (weak test). Score = % killed. Aim **80%+** on critical paths.

| Module (illustrative) | Score | Owner |
|---|---|---|
| The metric registry (cross-runtime parity) | **90%+** | AI/ML + QA |
| The compliance engine (window/frequency/registration gates) | **95%+** | AI/ML + Security |
| The system-of-record audit-log writer | **90%+** | Backend |
| The auth + tenant-context middleware | **90%+** | Backend + Security |
| Service-internal business logic | **80%+** | each builder |
| Glue / DI / boilerplate | n/a | |

### Running mutation tests (tool-agnostic)

```bash
# whichever mutation tool STACK.md binds; CI fails below the break threshold
<mutation-tool> run                  # full (nightly CI)
<mutation-tool> run --incremental    # changed files — dev loop
<mutation-tool> show <id>            # inspect a surviving mutant
```

Set a config-level `thresholds: { high: 90, low: 75, break: 75 }`-style gate so CI fails below the floor; restrict the mutation scope to source (exclude tests, generated code, index/barrel files).

### Weak vs strong (kill the mutants)

```typescript
// ❌ WEAK — survives mutation; passes even when computeMargin returns 0
test('computes margin', () => { expect(computeMargin(100, 30, 10)).toBeDefined(); });

// ✅ STRONG — kills arithmetic, sign, boundary mutants
test('computes margin', () => {
  expect(computeMargin(100, 30, 10)).toBe(60);
  expect(computeMargin(0, 0, 0)).toBe(0);
  expect(computeMargin(50, 80, 10)).toBe(-40);   // negative margin must be representable
});
```

Boundary mutants are non-negotiable on the compliance bounds — the mutant flipping `<`→`<=` at a channel-window edge MUST be killed:
```typescript
expect(isAllowed(new Date('2026-05-13T08:59:59Z'))).toBe(false);
expect(isAllowed(new Date('2026-05-13T09:00:00Z'))).toBe(true);
expect(isAllowed(new Date('2026-05-13T21:00:01Z'))).toBe(false);
```

### Mutation types that matter

| Mutation | Concern |
|---|---|
| Arithmetic (`+`→`-`) | Metric formulas, tax/fee extraction |
| Relational (`>`→`>=`) | Channel-window bounds, frequency-cap edge |
| Logical (`&&`→`\|\|`) | Compliance OR-chain (registration OR opt-out OR pending consent) |
| Boolean (`true`→`false`) | The cost-tier audit gate, the tenant-context flag |
| Return-value (early `null`) | Auth-middleware bypass tests |
| String (id swap) | Tenant-scoping — do tests notice the scope changed? |

### Score + practice
- **90%+** maintain · **80–89%** chip away · **70–79%** non-critical only · **<60%** weak, backlog before more features.
- Start with critical paths (mutating glue wastes CPU); ensure 80%+ line coverage first; run incrementally locally, full nightly in CI (a quiet-period cron). PR-time runs `--incremental` and fails if a critical module's score drops.
- Investigate every survivor on a critical path — kill it or document the *equivalent mutant*. Don't chase 100%.

## References

- The Canon's `METRICS.md` (registry + parity) and `COMPLIANCE.md` (the regime) — Definition of Done per layer + scaffolds
- `engineering-os-blueprint/06-quality-gates-and-metrics.md`
- Related skills: `cost-routing-paradigms`, `compliance-engine`, `metric-engine`, `multi-tenancy-isolation`, `operational-readiness`, `verification-before-completion`, `code-review`

## 2026 market update

- **Playwright is the E2E + component-test standard** (overtook Cypress); **Vitest** is the Jest successor for unit/integration. **Pact** is the contract-testing standard.
- **Now-standard practices to include:** chaos engineering (LitmusChaos / Gremlin) and **per-PR ephemeral preview environments** (`platform-engineering-idp`, `database-branching-dev-data`). Mutation testing (Stryker/PIT/cargo-mutants) already core here.
- For LLM/agent surfaces the "test" is the eval gate — `llm-evals` / `agent-evaluation`.
