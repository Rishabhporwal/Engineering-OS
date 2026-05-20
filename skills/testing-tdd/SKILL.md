---
name: testing-tdd
description: Brain's testing discipline — Vitest (Node + Web + RNTL), pytest (Python), Cypress (web E2E), Detox (mobile E2E), k6 (load — Phase 3+ 5K RPS target), real-network smoke tests (mandatory for PASS), the testing anti-patterns catalog, mutation testing for test effectiveness (Stryker for TS, mutmut for Python), metric registry parity (TS↔Python), cost-routing paradigm audit verification, India compliance test matrix. Auto-load whenever Tanvi or any builder is writing tests.
---

# Testing — Brain's TDD Discipline

## TDD by Mode

| Mode | Rule |
|---|---|
| SCALE | Failing test before code (Iron Law TDD). Real-network smoke before PASS. Cost-routing paradigm audit verified. India compliance matrix runs. |
| SPEED | Tests on critical business logic only. Real-network smoke still required for PASS. |

## Testing pyramid (Brain)

```
                    ▲
            E2E (Cypress + Detox) — critical journeys only
        Integration (Supertest + pytest) — real Postgres + ClickHouse + Kafka (docker compose)
                Unit (Vitest + pytest) — business logic + utilities
                    ▼
```

Plus, for any user-facing service: **real-network smoke test** (the PASS gate).

## Unit + integration — representative example

One canonical Vitest unit test (the same shape applies to pytest on the Python services). Note the **tenant-scoping assertion** — every Brain test asserts `workspace_id` propagation, not just the happy value:

```typescript
// apps/api-gateway/src/trpc/routers/store.test.ts
describe('store.kpis', () => {
  it('returns KPIs scoped to the requested workspace', async () => {
    const caller = createCaller({
      workspaceId: 'ws-1',
      grpc: { analytics: { getDailyMetrics: vi.fn().mockResolvedValue({ rows: [/* … */] }) } },
    });
    const result = await caller.store.kpis({ from, to });
    expect(result.rows).toHaveLength(3);
    expect(caller.grpc.analytics.getDailyMetrics).toHaveBeenCalledWith(
      expect.objectContaining({ workspace_id: 'ws-1' }),
    );
  });
});
```

- **Integration tests run against real Postgres + ClickHouse + Kafka via docker compose** — never mocked. Mocking the stores masks RLS + query-gateway + tenant-scoping bugs. Supertest hits a real Fastify server; pytest hits a real `brain_clickhouse` client; both assert the cross-workspace `403` and unscoped-query rejection.
- **Python parity:** the analytics-service metric tests mirror the TS examples (e.g. `compute_amer` → `None` on zero acquisition spend, `2.0` on a 2:1 ratio). See canon/BRAIN_TECHNICAL.md for the full layer-by-layer test layout.

## E2E + load (Cypress / Detox / k6)

These are pointers, not full configs — the canonical scaffolds live in the repo and canon/BRAIN_TECHNICAL.md:

- **Web — Cypress** (`apps/frontend/cypress/e2e/`): critical journeys only — KPI load with RAG coloring, campaign drill-down drawer. Assert on `data-testid` + RAG class.
- **Mobile — Detox** (`apps/mobile/e2e/`, canon/BRAIN_TECHNICAL.md): the Morning Brief journey — login → push deep link (`brain://morning-brief`) → three signal cards visible → swipe-approve writes a Decision Log row.
- **Load — k6** (`load-tests/`, Phase 3+ 5K RPS target): `constant-arrival-rate` at `rate: 5000`, thresholds `p(95)<500ms` and `http_req_failed rate<0.01` on `trpc.store.kpis`.

## Real-network smoke test — PASS gate (NON-NEGOTIABLE)

In-process request mocks (`fastify.inject()`, FastAPI `TestClient`) **skip the network stack** — they miss port-binding failures, TLS/reverse-proxy quirks, missing root handlers, EADDRINUSE, and real connection-pool behavior.

**PASS verdict requires** a smoke test that spawns the server on a real port and curls it:

```bash
# apps/api-gateway/scripts/smoke.sh
set -euo pipefail
PORT=3001 node dist/main.js & SERVER_PID=$!; trap "kill $SERVER_PID" EXIT
for i in {1..30}; do curl -fs http://localhost:3001/health && break || sleep 1; done
curl -fs http://localhost:3001/health | jq -e '.status == "ok"' > /dev/null
curl -fs -X POST http://localhost:3001/trpc/store.kpis \
  -H "Authorization: Bearer $TEST_JWT" -H "Content-Type: application/json" \
  -d '{"from":"2026-04-01","to":"2026-04-30"}' | jq -e '.result.data.rows' > /dev/null
echo "SMOKE PASS"
```

Tanvi's PASS gate: the smoke script ran in THIS session AND exited 0. Otherwise FAIL.

## Brain-specific verifications (mandatory on every relevant PR)

- **Cost-routing paradigm audit** (canon/BRAIN_TECHNICAL.md): `tools/check-paradigm-audit.ts` parses `@paradigm(...)` decorators across `apps/` and FAILs any endpoint/agent action missing one, or routing Sonnet where ML/SQL suffices.
- **Metric registry parity (TS ↔ Python):** `tools/check-metrics-parity.py` diffs `packages/lib-metrics` exported names against `brain_metrics.registry.list_names()` — any drift FAILs.
- **Multi-tenant isolation:** workspace A reading workspace B via tRPC returns `403`; the ClickHouse query gateway rejects any query without a `workspace_id` predicate (`rejects.toThrow(/workspace_id/)`).
- **India compliance matrix** (any lifecycle touch): parametrized calling-hours boundaries (08:59 blocked, 09:00 ok, 21:00 blocked at IST `tz_offset=5.5`), 48h frequency cap, DLT-unregistered block. Detection: a lifecycle PR without `tests/compliance/` updates.

## Coverage targets

| Layer | Target |
|---|---|
| Services (business logic) | > 80% line coverage |
| Controllers / tRPC procedures | > 60% |
| Utils + formatters | > 90% |
| Critical paths (auth, payment, India compliance) | > 95% |
| Overall (excluding generated + third-party) | > 70% |

## Common failure modes

- **`fastify.inject()` for smoke** — doesn't bind a real port. PASS requires real network.
- **Tests dropped under session truncation** — write tests alongside production code, not as phase-4 polish.
- **Coverage theater** — 90% line coverage on no-op getters/setters. Cover the critical paths.
- **Mocking ClickHouse + Postgres** — integration tests run against real (docker compose) instances. Mocking masks RLS + query gateway bugs.
- **Forgetting India compliance matrix** — every lifecycle change needs the full matrix.

## Testing anti-patterns catalog

A green test suite is only worth something if the tests would actually fail when the code is wrong. These are the ways a suite looks healthy but isn't. Tanvi bounces on any of these; every builder self-checks against them before handoff.

| Anti-pattern | Symptom | Why it's dangerous | Fix |
|---|---|---|---|
| **Assertion-free test** | Test calls the code but has no `expect`/`assert`, or only asserts "didn't throw" | Passes even when the output is wrong | Assert the actual value/shape, not just absence of error |
| **Over-mocking** | The unit under test (or its core collaborators like ClickHouse/Postgres) is mocked | Tests the mock, not the code; integration bugs (RLS, query gateway, tenant scoping) ship green | Mock only at true boundaries (external HTTP, time, randomness). Use docker-compose Postgres/ClickHouse for integration |
| **Testing implementation details** | Asserts on private methods, internal call order, or exact object internals | Brittle — refactors break tests even when behavior is unchanged | Assert observable behavior (return value, DB state, HTTP response), not internals |
| **Test interdependence** | Tests fail when run in isolation or in a different order; rely on shared mutable state | Hides real failures; flaky in CI sharding | Each test sets up + tears down its own state; no order dependence |
| **Snapshot abuse** | Giant auto-snapshots; failures "fixed" by blind `--update` | Snapshots stop meaning anything; regressions get rubber-stamped in | Snapshot small, intentional output; review every snapshot diff like code |
| **Non-determinism** | `Date.now()`, `Math.random()`, real network, real timers in tests → flaky | Flaky tests get ignored, then mask real breakage | Freeze time (`freeze_time`/fake timers), seed randomness, stub network at the boundary |
| **Happy-path only** | Only the success case is tested | Error handling, auth rejection, edge inputs are unverified | Test the 403/401, the empty set, the boundary (paise rounding, division-by-zero → None), the compliance-blocked path |
| **Logic in tests** | Conditionals/loops/computation inside the test body | Bugs in the test itself; the test can be "right" for the wrong reason | Tests are straight-line: arrange, act, assert literal expected values |
| **Mystery guest** | Test depends on external/global fixture data not visible in the test | Breaks when the hidden data changes; unreadable | Make fixtures local and explicit in the test (or a clearly-named factory) |
| **Coverage as the goal** | Targets the % number, tests trivial getters to hit it | High coverage, low confidence | Cover critical paths (auth, payment, India compliance, metric math); ignore generated/trivial code |
| **Asserting against the code, not the spec** | Expected value copied from current output ("change detector") | Locks in current behavior including bugs | Derive the expected value from the requirement/spec independently |

**Brain-specific must-cover edges** (not optional): cross-workspace 403 (multi-tenant isolation), metric registry parity (TS↔Python), paise/BigInt rounding, division-by-zero metrics → `None`, and the full India compliance matrix on any lifecycle touch.

## Test effectiveness — mutation testing

Coverage tells you "this line was executed." Mutation testing tells you "this line was *meaningfully* asserted" — the gap between a test that runs your code and one that catches a bug. **Mutants** are tiny automatic edits (`a + b` → `a - b`, `>` → `>=`, `true` → `false`). A mutant is **killed** when a test fails (good) and **survives** when all tests still pass (your test was weak). Score = % killed. Aim **80%+** on critical paths.

For Brain the priority paths are where wrong-but-tested code is most expensive: the metric engine, the India compliance engine, the Decision Log writer, cost-routing paradigm enforcement, and the JWT/RLS auth layer.

| Module | Score target | Owner |
|---|---|---|
| `packages/lib-metrics` (TS) + `pylibs/brain_metrics` (Python, parity-critical) | **90%+** | Maya + Tanvi |
| `lifecycle-service` compliance engine (calling hours, NCPR, 48h cap) | **95%+** | Maya + Shreya |
| `core-service` Decision Log writer | **90%+** | Vikram |
| `api-gateway` JWT + RLS-context middleware | **90%+** | Vikram + Shreya |
| Service-internal business logic | **80%+** | each builder |
| Glue / DI / boilerplate | n/a — not worth mutating | |

### TS/Vitest — Stryker

```bash
pnpm add -D @stryker-mutator/core @stryker-mutator/vitest-runner
```
```javascript
// stryker.config.mjs
export default {
  packageManager: 'pnpm', testRunner: 'vitest', coverageAnalysis: 'perTest',
  mutate: ['src/**/*.ts', '!src/**/*.test.ts', '!src/**/index.ts'],   // skip barrels
  thresholds: { high: 90, low: 75, break: 75 },   // CI fails below 75
  incremental: true,
};
```
```bash
pnpm dlx stryker run                          # full (nightly CI)
pnpm dlx stryker run --incremental            # changed files — dev loop
pnpm dlx stryker run --mutate "src/metrics/**/*.ts"   # investigate one module
```

### Python/pytest — mutmut

```bash
uv add --dev mutmut
```
```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = ["src/brain_metrics", "src/compliance", "src/decision_log"]
tests_dir = "tests"
runner = "uv run pytest -x --tb=no -q"
```
```bash
uv run mutmut run && uv run mutmut results
uv run mutmut show 42        # inspect a surviving mutant
```

### Weak vs strong (kill the mutants)

```typescript
// ❌ WEAK — survives mutation; passes even when calculateCM2 returns 0
test('computes CM2', () => { expect(calculateCM2(100, 30, 10)).toBeDefined(); });

// ✅ STRONG — kills arithmetic, sign, and boundary mutants
test('computes CM2', () => {
  expect(calculateCM2(100, 30, 10)).toBe(60);
  expect(calculateCM2(0, 0, 0)).toBe(0);
  expect(calculateCM2(50, 80, 10)).toBe(-40);   // negative CM2 must be representable
});
```

Boundary mutants are non-negotiable on the India compliance bounds — the mutant that flips `<` to `<=` at the 09:00/21:00 IST calling-hours edge MUST be killed:
```typescript
expect(isCallable(new Date('2026-05-13T08:59:59+05:30'))).toBe(false);
expect(isCallable(new Date('2026-05-13T09:00:00+05:30'))).toBe(true);
expect(isCallable(new Date('2026-05-13T21:00:01+05:30'))).toBe(false);
```

### Mutation types Brain cares about

| Mutation | Concern |
|---|---|
| Arithmetic (`+`→`-`) | Metric formulas (CM1/2/3, MER/aMER), GST extraction |
| Relational (`>`→`>=`) | Calling-hours bounds, 48h frequency cap edge |
| Logical (`&&`→`\|\|`) | India compliance OR-chain (NCPR OR opt-out OR pending consent) |
| Boolean (`true`→`false`) | Paradigm-audit gate, RLS context flag |
| Return-value (early `null`) | Auth middleware bypass tests |
| String (UUID swap) | Workspace-scoping — do tests notice the scope changed? |

### Score + practice
- **90%+** maintain · **80–89%** chip away · **70–79%** OK for non-critical only · **<60%** weak, backlog before more features.
- Start with critical paths (mutating glue wastes CPU); ensure 80%+ line coverage first; run incrementally locally, full nightly in CI (`cron: '0 19 * * *'` = 00:30 IST quiet period, upload the HTML report as an artifact); PR-time runs `--incremental` and fails if a critical module's score drops.
- Investigate every survivor on a critical path — kill it or document why it's an *equivalent mutant*. Don't chase 100% (equivalent mutants and unreachable branches are real; diminishing returns past 90%).

## References

- `canon/BRAIN_TECHNICAL.md` — Definition of Done per layer + full test scaffolds
- `skills/operational-readiness/SKILL.md` — pre-handoff checklist + real-network smoke
- `skills/cost-routing-paradigms/SKILL.md` — paradigm audit verification
- `skills/india-commerce-economics/SKILL.md` — compliance test matrix
- `skills/clickhouse-olap/SKILL.md` — query gateway test patterns
- `skills/auth-and-access/SKILL.md` — JWT + RLS middleware (a 90%+ mutation target)
- `skills/verification-before-completion/SKILL.md` — PASS discipline (mutation score is verified, not trusted)
- `skills/code-review/SKILL.md` — mutation score is a `/review` discussion input
