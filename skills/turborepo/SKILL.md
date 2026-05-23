---
name: turborepo
description: Turborepo monorepo build system — task pipelines, dependsOn, local + remote cache, --filter, --affected. Use when configuring tasks for apps/web, apps/mobile, services/*, packages/*, pylibs/*, when CI is slow because turbo cache misses, when adding a new internal package, or when debugging "build runs everything instead of only what changed".
---

# Turborepo

Brain's monorepo runner. Tasks are cached, parallelized by dependency graph, and (in CI) backed by a remote cache so successive builds share work across machines.

## The cardinal rule: package tasks, NOT root tasks

**DO NOT put task logic in the root `package.json`.** Every script lives in the package it belongs to; root only delegates.

```jsonc
// apps/web/package.json — each app/package owns its script
{ "scripts": { "build": "next build", "lint": "eslint .", "test": "vitest run", "typecheck": "tsc --noEmit" } }

// services/api-gateway/package.json
{ "scripts": { "build": "tsc -p tsconfig.build.json", "lint": "eslint .", "test": "vitest run" } }

// packages/lib-metrics/package.json
{ "scripts": { "build": "tsc -p tsconfig.build.json", "lint": "eslint .", "test": "vitest run" } }
```

```jsonc
// turbo.json — register the pipeline
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build":     { "dependsOn": ["^build"], "outputs": ["dist/**", ".next/**", "!.next/cache/**"] },
    "lint":      {},
    "typecheck": { "dependsOn": ["^build"] },
    "test":      { "dependsOn": ["build"], "outputs": ["coverage/**"] },
    "dev":       { "cache": false, "persistent": true }
  }
}
```

```jsonc
// Root package.json — ONLY delegates, no task logic
{
  "scripts": {
    "build":     "turbo run build",
    "lint":      "turbo run lint",
    "typecheck": "turbo run typecheck",
    "test":      "turbo run test",
    "dev":       "turbo run dev --parallel"
  }
}
```

**Anti-pattern (defeats parallelization):**
```jsonc
{
  "scripts": {
    "build": "cd apps/web && next build && cd ../api-gateway && tsc",
    "lint":  "eslint apps/ packages/"
  }
}
```

Root tasks (`//#taskname`) exist only for tasks that genuinely cannot live in a package (rare — release tagging, monorepo-wide schema generation). Don't reach for them.

## `turbo run` vs `turbo`

| Context | Form | Reason |
|---|---|---|
| In `package.json` scripts | `turbo run build` | Explicit, no ambiguity |
| In CI workflows | `turbo run build --filter=...` | Same |
| One-off terminal command | `turbo build` is fine | Saves typing |

Never write `turbo build` into a script file.

## Brain's task pipeline (canonical)

```jsonc
// turbo.json — Brain version
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local", ".env"],
  "globalEnv": ["NODE_ENV", "GIT_SHA"],
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"],
      "inputs": ["src/**", "tsconfig*.json", "package.json"]
    },
    "lint":      { "outputs": [] },
    "typecheck": { "dependsOn": ["^build"], "outputs": [] },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"],
      "env": ["CI"]
    },
    "test:e2e:web":    { "dependsOn": ["build"], "cache": false },
    "test:e2e:mobile": { "dependsOn": ["build"], "cache": false },
    "dev":             { "cache": false, "persistent": true },

    // gRPC codegen — when protos change, downstream rebuilds
    "proto:generate": {
      "dependsOn": ["^proto:generate"],
      "inputs": ["protos/**/*.proto", "buf.gen.yaml"],
      "outputs": ["src/generated/**"]
    }
  }
}
```

## Cache discipline (the speed win)

### Local cache

By default, every successful task is cached in `.turbo/`. Re-running an unchanged task is instant.

```bash
pnpm test               # cold: 90s; cached: 0.5s
turbo run test --force  # bypass cache when you must
```

### Remote cache (CI) — Brain's AWS-native approach

Brain is on AWS (locked stack — no Vercel). Run a **self-hosted Turborepo remote cache** backed by S3, deployed via CDK alongside the rest of Brain's infra. CI workers and devs share the same cache. Two production-ready open implementations exist (`ducktors/turborepo-remote-cache` and `Tapico/turborepo-remote-cache`); pick one, deploy as a small Fargate task or Lambda + S3 bucket, secure with a bearer token in AWS Secrets Manager.

```yaml
# .github/workflows/ci.yml
- run: pnpm install --frozen-lockfile
- run: turbo run lint typecheck test --affected
  env:
    TURBO_TOKEN:    ${{ secrets.TURBO_TOKEN }}        # bearer token (Secrets Manager)
    TURBO_TEAM:     brain                              # any non-empty string
    TURBO_API:      https://turbo-cache.brain.internal # the self-hosted endpoint
```

Hits/misses surface in `turbo run --summarize` and in CloudWatch metrics on the cache service. Aim for **>80% cache hit rate** on PR CI. Watch S3 storage growth — set a lifecycle rule to expire artifacts older than 30 days.

(Vercel Remote Cache exists and is the easiest path if you can use Vercel infra, but Brain doesn't — it'd add a non-AWS vendor surface that conflicts with the locked stack. Stay on AWS.)

## Running only what changed

```bash
turbo run build test --affected              # changed packages + their dependents
turbo run build --affected --affected-base=origin/main
turbo run build --filter=web                 # by name
turbo run build --filter='./services/*'      # by directory glob
turbo run build --filter=web...              # web + its dependencies
turbo run build --filter=...web              # web + its dependents (CI-flavoured)
```

`--affected` is the primary tool — it's what makes Brain's CI fast as the monorepo grows.

## Environment variables (a common foot-gun)

Turborepo's cache key includes the explicit `env` you declare. **If you don't declare it, you cache across env values** — and you'll ship a build with the wrong `NEXT_PUBLIC_*` baked in.

```jsonc
{
  "tasks": {
    "build": {
      "env": [
        "NODE_ENV",
        "GIT_SHA",
        "NEXT_PUBLIC_API_URL",
        "NEXT_PUBLIC_POSTHOG_KEY",
        "NEXT_PUBLIC_SENTRY_DSN"
      ]
    }
  }
}
```

Brain rule: any env var read at build time appears in `env` (or `inputs` if it's a file like `.env.production`).

## Internal packages (`packages/*` + `pylibs/*`)

| Package | Type | Notes |
|---|---|---|
| `packages/lib-metrics` (TS) | Compiled (`tsc`) | Consumed by api-gateway, core, notifications, web BFF |
| `packages/ui` | Compiled | shadcn primitives + Brain design tokens (Ananya) |
| `packages/proto-ts` | Codegen output | Generated by `buf generate`; never edited by hand |
| `pylibs/brain_metrics` | Python wheel | Parity with `lib-metrics` — covered by mutation tests |
| `pylibs/brain_clickhouse` | Python | The query gateway that enforces `workspace_id` |

For TS packages, prefer **JIT (no build step)** for ESM-only packages with `"exports"` pointing at `.ts` (consumers transpile). Use **compiled** when distributing across language runtimes or when you need `.d.ts` for IDE speed. Brain's `lib-metrics` is compiled (consumed by Node services AND can be inspected by Python via FFI in future).

## Watch mode

```bash
turbo watch
turbo run dev --parallel --persistent
```

`with` lets a dev task wait for its dep:

```jsonc
{
  "tasks": {
    "dev": { "cache": false, "persistent": true, "with": ["api#dev"] }
  }
}
```

Use `interruptible: true` on a dev task to restart it when a dep emits new output.

## Brain CI recipe (canonical)

```yaml
# .github/workflows/ci.yml — runs on every PR
name: CI
on: [pull_request, push]
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }            # required for --affected
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: '24', cache: 'pnpm' }
      - run: pnpm install --frozen-lockfile
      - run: turbo run lint typecheck test build --affected
        env:
          TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
          TURBO_TEAM:  ${{ vars.TURBO_TEAM }}
```

Add a Python job for FastAPI services (uv + pytest, mirror structure).

## Quick debug commands

```bash
turbo run build --dry --summarize        # show what would run, why
turbo run build --summarize              # actual + hit/miss summary
turbo prune <pkg-name>                   # subset the monorepo for a Docker image
turbo run build --cache-dir=/tmp/turbo   # custom cache location
```

## Best practices (Brain)

- **`turbo run <task>` in scripts**, never `turbo <task>`
- **Package tasks**, never root tasks (with rare exceptions)
- **Declare every env var** read at build time in the task's `env`
- **`--affected` in CI** — never run the full suite on every PR
- **Remote cache from day one** — the speed-up compounds as the monorepo grows
- **Outputs scoped tightly** — don't `outputs: ["**"]` (cache balloons)
- **Inputs scoped tightly** — don't include `node_modules` or generated files
- **No persistent tasks** in CI (`dev`, watchers); add `cache: false` so they don't break the cache key

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Monorepo layout + task pipeline | **Aryan** | TECH overall + stack ADR |
| Remote cache config | **Jatin** | CI infra |
| Per-package script discipline | each builder | their service/package |
| proto:generate task | **Aryan** + Vikram | `grpc-buf` skill |
| Cypress / Detox / k6 (uncached) tasks | **Tanvi** | `testing-tdd` |

Related Brain skills: `grpc-buf` (proto codegen task), `python-services` (uv counterpart), `operational-readiness` (CI build gates).
