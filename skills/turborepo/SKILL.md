---
name: turborepo
description: Turborepo runner — package-level task pipelines, dependsOn, local+S3 remote cache, --filter, --affected (drives the CI deploy matrix). Use when tasks/CI cache is slow.
---

# Turborepo

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the monorepo-runner seam to different technology. The *patterns* here (package-level tasks, dependency-graph parallelism, remote cache, run-only-what-changed) are what transfer, not the vendor.

A monorepo task runner. Tasks are cached, parallelized by dependency graph, and (in CI) backed by a remote cache (e.g. object storage) shared across machines.

## The cardinal rule: package tasks, NOT root tasks

**DO NOT put task logic in the root `package.json`.** Every script lives in the package it belongs to; root only delegates.

```jsonc
// apps/web/package.json
{ "scripts": { "build": "next build", "lint": "eslint .", "test": "vitest run", "typecheck": "tsc --noEmit" } }
// packages/metrics/package.json
{ "scripts": { "build": "tsc -p tsconfig.build.json", "lint": "eslint .", "test": "vitest run" } }
// Root package.json — ONLY delegates
{ "scripts": { "build": "turbo run build", "lint": "turbo run lint", "test": "turbo run test", "dev": "turbo run dev --parallel" } }
```

**Anti-pattern (defeats parallelization):** `"build": "cd apps/web && next build && cd ../api-gateway && tsc"`.

Root tasks (`//#taskname`) exist only for tasks that genuinely cannot live in a package (rare — release tagging, monorepo-wide schema gen).

## `turbo run` vs `turbo`

In `package.json` scripts and CI: always `turbo run build` (explicit). One-off terminal: `turbo build` is fine. **Never write `turbo build` into a script file.**

## Task pipeline (example)

```jsonc
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local", ".env"],
  "globalEnv": ["NODE_ENV", "GIT_SHA"],
  "tasks": {
    "build":     { "dependsOn": ["^build"], "outputs": ["dist/**", ".next/**", "!.next/cache/**"], "inputs": ["src/**", "tsconfig*.json", "package.json"] },
    "lint":      { "outputs": [] },
    "typecheck": { "dependsOn": ["^build"], "outputs": [] },
    "test":      { "dependsOn": ["build"], "outputs": ["coverage/**"], "env": ["CI"] },
    "test:e2e:web":    { "dependsOn": ["build"], "cache": false },
    "test:e2e:mobile": { "dependsOn": ["build"], "cache": false },
    "dev":             { "cache": false, "persistent": true },
    "proto:generate":  { "dependsOn": ["^proto:generate"], "inputs": ["protos/**/*.proto", "buf.gen.yaml"], "outputs": ["src/generated/**"] }
  }
}
```

## Cache discipline (the speed win)

**Local:** every successful task is cached in `.turbo/`. `pnpm test` cold 90s, cached 0.5s. `turbo run test --force` to bypass.

**Remote (CI):** run a **self-hosted remote cache backed by your object store**, deployed via your IaC (e.g. `ducktors/turborepo-remote-cache` or equivalent as a small task / function + object storage), secured with a bearer token in your managed secret store.

```yaml
- run: turbo run lint typecheck test --affected
  env:
    TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}         # bearer token (managed secret store)
    TURBO_TEAM:  <team>
    TURBO_API:   https://turbo-cache.<internal>     # self-hosted endpoint
```

Aim for **>80% cache hit rate** on PR CI. Set a lifecycle rule to expire cache artifacts older than 30 days. (Prefer a self-hosted cache aligned with your `STACK.md` over a third-party SaaS cache that adds a vendor surface outside your stack.)

## Running only what changed

```bash
turbo run build test --affected                  # changed packages + their dependents
turbo run build --affected --affected-base=origin/main
turbo run build --filter=web                      # by name
turbo run build --filter='./services/*'           # by directory glob
turbo run build --filter=web...                   # web + its dependencies
turbo run build --filter=...web                   # web + its dependents
```

**`--affected` drives the CI *deploy* matrix, not just local builds.** CI reads the affected set (`turbo run build --affected --dry-run=json`) and builds/pushes/deploys ONLY those services + their transitive dependents — what enables per-service deployment (own image + own deploy unit). A bare CI path-filter (`apps/x/**`) is insufficient: it misses any service that imports a *changed shared package or contract* (a metrics lib, the `protos/**` directory). Cross-ref `devops-aws` §Selective deployment.

## Environment variables (a common foot-gun)

Turborepo's cache key includes the explicit `env` you declare. **If you don't declare it, you cache across env values** — shipping a build with the wrong `NEXT_PUBLIC_*` baked in.

```jsonc
{ "tasks": { "build": { "env": ["NODE_ENV", "GIT_SHA", "NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_POSTHOG_KEY", "NEXT_PUBLIC_SENTRY_DSN"] } } }
```

Rule: any env var read at build time appears in `env` (or `inputs` if it's a file like `.env.production`).

## Internal packages (`packages/*` + sibling cross-runtime libs)

| Package (illustrative) | Type | Notes |
|---|---|---|
| a metrics lib (TS) | Compiled (`tsc`) | Consumed by the API surfaces + web BFF |
| a UI package | Compiled | shared UI primitives + design tokens (Frontend Engineer) |
| a generated-contracts package | Codegen output | Generated from the contract definitions; never hand-edited |
| a metrics lib (other runtime) | wheel/artifact | Parity with the TS metrics lib — covered by mutation tests |
| the analytics query-gateway lib | other runtime | Enforces the tenant-isolation key on every query |

Prefer **JIT (no build step)** for ESM-only TS packages with `"exports"` pointing at `.ts`; use **compiled** when distributing across runtimes or needing `.d.ts`. The metrics lib is compiled.

## Watch mode

```bash
turbo watch
turbo run dev --parallel --persistent
```

`"with": ["api#dev"]` lets a dev task wait for its dep; `interruptible: true` restarts it when a dep emits new output.

## CI recipe (example)

```yaml
# .github/workflows/ci.yml — every PR
jobs:
  build-and-test:
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }            # required for --affected
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: '<LTS>', cache: 'pnpm' }
      - run: pnpm install --frozen-lockfile
      - run: turbo run lint typecheck test build --affected
        env: { TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}, TURBO_TEAM: ${{ vars.TURBO_TEAM }} }
```

Add a parallel job per additional runtime in the monorepo (e.g. a second-runtime test job), mirroring the structure.

## Quick debug commands

```bash
turbo run build --dry --summarize        # show what would run, why
turbo run build --summarize              # actual + hit/miss summary
turbo prune <pkg-name>                   # subset the monorepo for a Docker image
```

## Best practices

- `turbo run <task>` in scripts, never `turbo <task>`
- Package tasks, never root tasks (rare exceptions)
- Declare every build-time env var in the task's `env`
- `--affected` in CI — never the full suite on every PR
- Remote cache from day one — the speed-up compounds
- Scope `outputs` + `inputs` tightly (no `["**"]`, no `node_modules`/generated)
- No persistent tasks (`dev`, watchers) in CI — add `cache: false`

## Wiring

| Concern | Owner | Reference |
|---|---|---|
| Monorepo layout + task pipeline | **Architect** | the Canon's `STACK.md` + stack ADR |
| Remote cache config | **Platform/SRE** | CI infra |
| Per-package script discipline | each builder | their service/package |
| Contract-codegen task | **Architect** + Backend Engineer | `grpc-buf` |
| E2E / load (uncached) tasks | **QA Engineer** | `testing-tdd` |

Related: `grpc-buf`, `python-services` (other-runtime counterpart), `operational-readiness`, `devops-aws`.

## 2026 market update

- **Nx** is the main monorepo alternative — richer plugin/generator/codegen ecosystem and a broader task graph, where Turborepo is lighter and config-light. The Nx-vs-Turborepo choice is the live build-orchestration decision; bind in `STACK.md`. The `--affected`-drives-CI pattern transfers to both.
