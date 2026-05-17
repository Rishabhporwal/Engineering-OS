---
name: mutation-testing
description: Validate test effectiveness with mutation testing — Stryker for TypeScript (Vitest runner), mutmut for Python (pytest). Find weak tests that pass even when code is broken. Use to raise Tanvi's confidence on metric-registry parity, on India compliance engine paths, on Decision Log integrity, on any code path where "tests pass but the system is wrong" would be catastrophic.
---

# Mutation Testing

Coverage tells you "this line was executed." Mutation testing tells you "this line was *meaningfully* asserted." The difference is the gap between a test that runs your code and a test that catches a bug.

For Brain, the priority paths for mutation testing are the ones where wrong-but-tested code would be the most expensive to ship: **the metric engine, the India compliance engine, the Decision Log writer, the cost-routing paradigm enforcement, and the JWT/RLS auth layer.**

## Core concept

- **Mutants** — small automatic edits to your code (`a + b` → `a - b`, `>` → `>=`, `true` → `false`)
- **Killed** — the mutated code makes a test fail → the test caught the bug (good)
- **Survived** — the mutated code still passes all tests → your test wasn't strong enough (bad)
- **Score** — % of mutants killed. **Aim for 80%+ on critical paths.**

## Brain targets

| Module | Score target | Owner |
|---|---|---|
| `packages/lib-metrics` (TS metric registry) | **90%+** | Kabir + Tanvi |
| `pylibs/brain_metrics` (Python metric registry, parity-critical) | **90%+** | Kabir + Tanvi |
| `lifecycle-service` compliance engine (calling hours, NCPR, 48h cap) | **95%+** | Neel + Shreya |
| `core-service` Decision Log writer | **90%+** | Vikram |
| `api-gateway` JWT + RLS-context middleware | **90%+** | Vikram + Shreya |
| Service-internal business logic | **80%+** | each builder |
| Glue / DI / boilerplate | n/a — not worth mutating | |

## TypeScript / Vitest (Vikram, Ananya, Karan)

### Installation

```bash
pnpm add -D @stryker-mutator/core @stryker-mutator/vitest-runner
```

### Configuration

```typescript
// stryker.config.mjs
export default {
  packageManager: 'pnpm',
  testRunner: 'vitest',
  coverageAnalysis: 'perTest',           // map tests to mutants for speed
  reporters: ['html', 'clear-text', 'progress'],
  mutate: [
    'src/**/*.ts',
    '!src/**/*.test.ts',
    '!src/**/*.spec.ts',
    '!src/**/index.ts',                  // barrel files = boilerplate
  ],
  thresholds: { high: 90, low: 75, break: 75 },  // CI fails below 75
  incremental: true,
};
```

### Running

```bash
# Full run (slow; do nightly in CI)
pnpm dlx stryker run

# Incremental (only changed files) — local dev loop
pnpm dlx stryker run --incremental

# Specific files (when investigating a module)
pnpm dlx stryker run --mutate "src/metrics/**/*.ts"

# Open report
open reports/mutation/html/index.html
```

### Example — weak vs strong test

```typescript
function calculateCM2(revenue: number, adSpend: number, fulfillment: number): number {
  return revenue - adSpend - fulfillment;
}

// ❌ WEAK — passes even when calculateCM2 returns 0
test('computes CM2', () => {
  expect(calculateCM2(100, 30, 10)).toBeDefined();
});

// ✅ STRONG — kills arithmetic, sign, and boundary mutants
test('computes CM2 correctly', () => {
  expect(calculateCM2(100, 30, 10)).toBe(60);
  expect(calculateCM2(100, 0, 0)).toBe(100);
  expect(calculateCM2(0, 0, 0)).toBe(0);
  expect(calculateCM2(50, 80, 10)).toBe(-40);   // negative CM2 must be representable
});
```

## Python / mutmut (Sahil, Kabir, Maya, Neel-Python-side)

### Installation

```bash
uv add --dev mutmut
```

### Configuration

```toml
# pyproject.toml
[tool.mutmut]
paths_to_mutate = [
  "src/brain_metrics",
  "src/compliance",
  "src/decision_log",
]
tests_dir = "tests"
runner = "uv run pytest -x --tb=no -q"
```

### Running

```bash
uv run mutmut run
uv run mutmut results
uv run mutmut show 42         # see the surviving mutant
uv run mutmut html && open html/index.html
```

## Common mutation types Brain cares about

| Mutation | Brain-specific concern |
|---|---|
| Arithmetic (`+` → `-`) | Metric formulas (CM1/CM2/CM3, MER/aMER), GST extraction |
| Relational (`>` → `>=`) | Calling-hours bounds (09:00 vs 09:01), 48h frequency cap edge |
| Logical (`&&` → `\|\|`) | India compliance OR-chain (NCPR OR brand-opt-out OR pending consent) |
| Boolean literal (`true` → `false`) | Feature flags, paradigm-audit gate, RLS context flag |
| Return-value (return early `null`) | Auth middleware bypass tests |
| String replacement (UUID → other) | Workspace-scoping tests; do tests notice the scope changed? |

## Score interpretation

| Score | Action |
|---|---|
| **90%+** | Excellent — maintain |
| **80–89%** | Good — chip away at the long tail |
| **70–79%** | Acceptable for non-critical paths; **NOT acceptable** for the priority paths above |
| **<60%** | Tests are weak; mutation testing is now a backlog item before the module ships more features |

Note: 100% is rarely achievable — *equivalent mutants* (semantically identical to original) and unreachable branches are real. The goal is "tests catch real bugs," not "all mutants killed."

## Improving weak tests — patterns

### Pattern: insufficient assertions

```typescript
// Before: mutation survives
test('compute MER', () => {
  expect(computeMER(orders, spend)).toBeGreaterThan(0);  // weak
});

// After: mutation killed
test('compute MER', () => {
  expect(computeMER([{ rev: 100 }], [{ amount: 25 }])).toBe(4);
  expect(computeMER([{ rev: 0 }], [{ amount: 0 }])).toBe(null); // div-by-zero contract
  expect(computeMER([{ rev: 100 }], [])).toBe(null);            // no spend
});
```

### Pattern: boundary conditions (India compliance)

```typescript
test('blocks calls outside 09:00–21:00 IST', () => {
  expect(isCallable(new Date('2026-05-13T08:59:59+05:30'))).toBe(false); // 08:59:59
  expect(isCallable(new Date('2026-05-13T09:00:00+05:30'))).toBe(true);  // 09:00:00
  expect(isCallable(new Date('2026-05-13T21:00:00+05:30'))).toBe(true);  // 21:00:00
  expect(isCallable(new Date('2026-05-13T21:00:01+05:30'))).toBe(false); // 21:00:01
});
```

The mutant that flips `<` to `<=` MUST be killed. The compliance bound is non-negotiable.

## CI integration

```yaml
# .github/workflows/mutation.yml — nightly on main
name: Mutation Testing
on:
  schedule: [{ cron: '0 19 * * *' }]   # 00:30 IST — quiet period
  workflow_dispatch:
jobs:
  stryker:
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - run: pnpm install
      - run: pnpm dlx stryker run
      - uses: actions/upload-artifact@v4
        with:
          name: mutation-report
          path: reports/mutation/
```

PR-time check: `pnpm dlx stryker run --incremental` against the diff, fail if score drops below the configured threshold for a critical module.

## Best practices

- **Start with critical paths**, not "every file." Mutating glue is wasted CPU.
- **Ensure 80%+ line coverage first**; mutation testing assumes the line is exercised at all.
- **Run incrementally** during dev; nightly full run in CI.
- **Investigate every survivor on a critical path.** Either kill it with a better test or document why it's equivalent.
- **Don't chase 100%.** Diminishing returns past 90%.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Metric registry parity (TS + Python) | **Kabir** + **Tanvi** | TECH/03 §"Metric registry" |
| India compliance engine | **Neel** + **Shreya** | TECH/11 §6 |
| Decision Log write integrity | **Vikram** | TECH/05 §"Decision Log" |
| JWT + RLS middleware | **Vikram** + **Shreya** | `session-management`, TECH/09 |
| Nightly mutation CI | **Jatin** + **Tanvi** | |

Related Brain skills: `testing-tdd` (the test stack — Vitest for Node, pytest for Python via `python-services`), `verification-before-completion` (PASS discipline), `code-review` (mutation score is a `/review` discussion input).
