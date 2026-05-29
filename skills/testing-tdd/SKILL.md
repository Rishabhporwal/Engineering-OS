---
name: testing-tdd
description: Brain's testing discipline — Vitest/pytest/Playwright/Detox/k6, mandatory real-network smoke, anti-pattern catalog, mutation testing, metric-parity + paradigm audit + India compliance matrix.
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
            E2E (Playwright + Detox) — critical journeys only
        Integration (Supertest + pytest) — real Postgres + ClickHouse + Kafka (docker compose)
                Unit (Vitest + pytest) — business logic + utilities
                    ▼
```

Plus, for any user-facing service: **real-network smoke test** (the PASS gate).

## Unit + integration — representative example

One canonical Vitest unit test (same shape applies to pytest on the Python services). Note the **tenant-scoping assertion** — every Brain test asserts `workspace_id` propagation, not just the happy value:

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
- **Python parity:** analytics-service metric tests mirror the TS examples (e.g. `compute_amer` → `None` on zero acquisition spend, `2.0` on a 2:1 ratio). See canon/technical-requirements.md for the full layer-by-layer layout.

## E2E + load (Playwright / Detox / k6)

Pointers, not full configs — canonical scaffolds live in the repo and canon/technical-requirements.md:

- **Web — Playwright** (`apps/web/e2e/`): critical journeys only — KPI load with RAG coloring, campaign drill-down drawer. Assert with `page.getByTestId(...)` + web-first assertions on the RAG class. Cross-browser, parallel + sharding in CI, trace viewer for flake.
- **Mobile — Detox** (`apps/mobile/e2e/`): the Morning Brief journey — login → push deep link (`brain://morning-brief`) → three signal cards visible → swipe-approve writes a Decision Log row.
- **Load — k6** (`load-tests/`, Phase 3+ 5K RPS target): `constant-arrival-rate` at `rate: 5000`, thresholds `p(95)<500ms` and `http_req_failed rate<0.01` on `trpc.store.kpis`.

## Real-network smoke test — PASS gate (NON-NEGOTIABLE)

In-process mocks (`fastify.inject()`, FastAPI `TestClient`) **skip the network stack** — they miss port-binding failures, TLS/reverse-proxy quirks, missing root handlers, EADDRINUSE, real connection-pool behavior.

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

- **Cost-routing paradigm audit:** `tools/check-paradigm-audit.ts` FAILs any endpoint/agent action missing `@paradigm(...)`, or routing Sonnet where ML/SQL suffices. (Owner skill: `cost-routing-paradigms`.)
- **Metric registry parity (TS ↔ Python):** `tools/check-metrics-parity.py` diffs `packages/lib-metrics` against `brain_metrics.registry.list_names()` — any drift FAILs.
- **Multi-tenant isolation:** workspace A reading B via tRPC returns `403`; the ClickHouse query gateway rejects any query without a `workspace_id` predicate.
- **India compliance matrix** (any lifecycle touch): parametrized calling-hours boundaries (08:59 blocked, 09:00 ok, 21:00 blocked at IST `tz_offset=5.5`), 48h frequency cap, DLT-unregistered block. (Owner skill: `india-commerce-economics`.)

## Coverage targets

| Layer | Target |
|---|---|
| Services (business logic) | > 80% |
| Controllers / tRPC procedures | > 60% |
| Utils + formatters | > 90% |
| Critical paths (auth, payment, India compliance) | > 95% |
| Overall (excl. generated + third-party) | > 70% |

## Common failure modes

- **`fastify.inject()` for smoke** — doesn't bind a real port.
- **Tests dropped under session truncation** — write tests alongside production code, not as phase-4 polish.
- **Coverage theater** — 90% line coverage on no-op getters/setters.
- **Mocking ClickHouse + Postgres** — masks RLS + query gateway bugs.
- **Forgetting the India compliance matrix** — every lifecycle change needs the full matrix.

## Testing anti-patterns catalog

A green suite is only worth something if the tests would fail when the code is wrong. Tanvi bounces on any of these; every builder self-checks before handoff.

| Anti-pattern | Symptom | Fix |
|---|---|---|
| **Assertion-free** | No `expect`/`assert`, or only "didn't throw" | Assert the actual value/shape |
| **Over-mocking** | Unit-under-test or core stores (CH/PG) mocked | Mock only true boundaries (HTTP, time, randomness); docker-compose for integration |
| **Implementation details** | Asserts private methods / internal call order | Assert observable behavior |
| **Test interdependence** | Fails in isolation / different order | Each test sets up + tears down its own state |
| **Snapshot abuse** | Giant auto-snapshots blind-`--update`ed | Snapshot small, intentional output; review every diff |
| **Non-determinism** | `Date.now()`, `Math.random()`, real network/timers | Freeze time, seed randomness, stub network |
| **Happy-path only** | Only the success case tested | Test 403/401, empty set, boundary, compliance-blocked path |
| **Logic in tests** | Conditionals/loops/computation in the test body | Straight-line: arrange, act, assert literals |
| **Mystery guest** | Depends on hidden external fixture data | Make fixtures local + explicit |
| **Coverage as goal** | Tests trivial getters to hit a % | Cover critical paths; ignore generated/trivial |
| **Asserting against code, not spec** | Expected value copied from current output | Derive expected value from the requirement independently |

**Brain must-cover edges** (not optional): cross-workspace 403, metric registry parity (TS↔Python), paise/BigInt rounding, division-by-zero metrics → `None`, full India compliance matrix on any lifecycle touch.

## Test effectiveness — mutation testing

Coverage says "this line ran." Mutation testing says "this line was *meaningfully* asserted." **Mutants** are tiny automatic edits (`a+b`→`a-b`, `>`→`>=`, `true`→`false`). A mutant is **killed** when a test fails (good), **survives** when all tests pass (weak test). Score = % killed. Aim **80%+** on critical paths.

| Module | Score | Owner |
|---|---|---|
| `packages/lib-metrics` (TS) + `pylibs/brain_metrics` (Python parity) | **90%+** | Maya + Tanvi |
| `lifecycle-service` compliance engine (calling hours, NCPR, 48h cap) | **95%+** | Maya + Shreya |
| `core-service` Decision Log writer | **90%+** | Vikram |
| `api-gateway` JWT + RLS-context middleware | **90%+** | Vikram + Shreya |
| Service-internal business logic | **80%+** | each builder |
| Glue / DI / boilerplate | n/a | |

### TS/Vitest — Stryker

```javascript
// stryker.config.mjs
export default {
  packageManager: 'pnpm', testRunner: 'vitest', coverageAnalysis: 'perTest',
  mutate: ['src/**/*.ts', '!src/**/*.test.ts', '!src/**/index.ts'],
  thresholds: { high: 90, low: 75, break: 75 },   // CI fails below 75
  incremental: true,
};
```
```bash
pnpm dlx stryker run                       # full (nightly CI)
pnpm dlx stryker run --incremental         # changed files — dev loop
```

### Python/pytest — mutmut

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

// ✅ STRONG — kills arithmetic, sign, boundary mutants
test('computes CM2', () => {
  expect(calculateCM2(100, 30, 10)).toBe(60);
  expect(calculateCM2(0, 0, 0)).toBe(0);
  expect(calculateCM2(50, 80, 10)).toBe(-40);   // negative CM2 must be representable
});
```

Boundary mutants are non-negotiable on the India compliance bounds — the mutant flipping `<`→`<=` at the 09:00/21:00 IST edge MUST be killed:
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
- **90%+** maintain · **80–89%** chip away · **70–79%** non-critical only · **<60%** weak, backlog before more features.
- Start with critical paths (mutating glue wastes CPU); ensure 80%+ line coverage first; run incrementally locally, full nightly in CI (`cron: '0 19 * * *'` = 00:30 IST quiet period). PR-time runs `--incremental` and fails if a critical module's score drops.
- Investigate every survivor on a critical path — kill it or document the *equivalent mutant*. Don't chase 100%.

## References

- `canon/technical-requirements.md` — Definition of Done per layer + full test scaffolds
- Owner skills for the Brain-specific gates: `cost-routing-paradigms`, `india-commerce-economics`, `clickhouse-olap`, `auth-and-access`, `operational-readiness`, `verification-before-completion`, `code-review`
