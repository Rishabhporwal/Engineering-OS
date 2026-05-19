---
name: operational-readiness
description: Production-readiness checklist for every shippable service — root handler, health check, port selection, real-network smoke test, env var validation, native-dep gotchas. Used by Vikram before declaring a service "done" and by Tanvi before issuing a PASS verdict. Encoded from real failures the team hit (pnpm 11 native-build gate, port 3000 collisions, in-memory tests masking real-network bugs, API-only services that look broken in browsers).
---

# Operational Readiness — the "won't look broken in production" checklist

Every shippable service must clear this checklist before Vikram hands off and before Tanvi issues PASS. These rules exist because the team hit each of them in production-like tests. They're cheap to satisfy and expensive to skip.

## 1. Root handler (`GET /`) is required, even for API-only services

A service that 404s on `GET /` looks "broken" to a human hitting the URL. `GET /` must return either a minimal description page, a JSON `{"service", "version", "endpoints"}`, or a redirect to `/health`. Five lines of code that save 30 minutes of "is the server down?".

## 2. `/health` endpoint is non-negotiable

Returns `{"status": "ok"}` minimum; better includes `version` (git SHA) and `deps` reachability:

```typescript
app.get('/health', async (c) => {
  const [db, redis] = await Promise.allSettled([pingDb(), pingRedis()]);
  return c.json({
    status: [db, redis].every(r => r.status === 'fulfilled') ? 'ok' : 'degraded',
    version: process.env.GIT_SHA ?? 'dev',
    deps: { db: db.status, redis: redis.status },
  });
});
```

EKS / ALB / CloudFront all need this (Brain's locked stack — canon/BRAIN_TECHNICAL.md). Without working liveness + readiness probes the service can't deploy. Full Fastify + FastAPI probe pattern: [health-check-endpoints](../health-check-endpoints/SKILL.md).

## 3. Port selection — never hardcode, never assume :3000 is free

Read `PORT` from env (`Number(process.env.PORT ?? 0)` lets the OS pick a free port), and **log the actual bound port**. On `EADDRINUSE`, crash loudly — never silently retry on the next port.

**Real failure the team hit**: default port 3000 was occupied by another dev service; ours crashed with `EADDRINUSE`; the test client hit :3000 anyway and got a `307 → /login` from the OTHER service — looked like our app responding wrong, not failing to bind. Mitigation: the smoke test `lsof -i :$PORT` before binding, or bind to port 0 and read back the chosen port.

## 4. Smoke test against a REAL listening server — `app.request()` mocks are not enough

In-process mocks (Hono `app.request()`, NestJS `Test.createTestingModule`, FastAPI `TestClient`) skip the network stack — they miss port binding, TLS, HTTP/2 negotiation, reverse-proxy quirks, timeouts, DNS.

**Two test layers required:**
1. **Integration** (fast, in-process) — your hot loop on every save.
2. **Smoke** (slow, real network) — `spawn` the actual server on a real port, wait for the "listening" log, then `fetch`/`curl` `GET /health` (expect 200 + `status:ok`) and `GET /` (expect 200, not 404). Run before PASS and in CI post-deploy. (Node `child_process.spawn` template + the bash variant are in `testing-tdd` and canon/BRAIN_TECHNICAL.md.)

## 5. Native dependencies — declare the build trust list

For Node projects using `better-sqlite3`, `node-gyp` packages, `esbuild`, `sharp`, etc., declare them in `package.json` → `pnpm.onlyBuiltDependencies` (an **array** of package names).

**pnpm 11 gotcha**: even with `onlyBuiltDependencies` declared, the pre-flight `runDepsStatusCheck` may block commands with `[ERR_PNPM_IGNORED_BUILDS]` AND leave native binaries unbuilt while `pnpm install` reports success. This bit a multi-tenant analytics build twice in one session — **don't trust the install exit code.**

Wire a pre-flight check into `predev`/`pretest`/CI that loops `onlyBuiltDependencies` and `node -e "require('$pkg')"` on each, failing with `run: pnpm rebuild $pkg` if a binary is missing. A green test run while `better-sqlite3` is silently unbuilt is exactly the failure this catches.

Workarounds when the gate fires (Brain is pnpm-locked; do NOT adopt bun): `pnpm rebuild <pkg>` → run the binary directly (`node_modules/.bin/vitest`) → `pnpm approve-builds` → `CI=true` → pin in `onlyBuiltDependencies`. Document the choice in the README.

## 5b. Don't rely on transitive dependencies you import directly

If it appears in an `import`/`require`, it appears in `dependencies`. **Lived failure**: a NestJS service imported `express`'s `json` middleware for a webhook HMAC `rawBody` verifier; CI smoke passed (transitive resolution worked) but production-like start threw `MODULE_NOT_FOUND: express` — the transitive path only resolves under specific hoisting layouts. Grep `src/` for the import on the way to PASS.

## 5c. Tests using ESM features need their own tsconfig

If tests use `import.meta.url` / top-level `await` while the app compiles to CommonJS for Node, split configs: `tsconfig.json` (production, `module: commonjs`, excludes tests) and `tsconfig.test.json` (extends it, `module: esnext`, `moduleResolution: bundler`, `noEmit`, includes tests). Point `typecheck` at the test config.

## 5d. Non-TS runtime files must be declared in the build output

`tsc`/`esbuild`/`swc`/`tsup`/`nest` don't copy `.sql`/`.proto`/`.yaml`/`.json` to `dist/` by default. First, every time, grep `src/` for runtime file reads and confirm each is declared in the bundler's asset config or inlined:

```bash
grep -rE "readFileSync|readFile|require\(['\"].*\.(sql|proto|yaml|yml|json|hbs|html|graphql)['\"]" services/<service>/src/
```

- **Node (tsup):** add an `esbuild-plugin-copy` step copying `src/**/*.sql` (ClickHouse DDL), `*.proto`, `*.yaml` into `dist/`.
- **Python (uv + hatch):** `[tool.hatch.build.targets.wheel.force-include]` the `materializations/` (`.sql`) and generated `proto/` dirs into the wheel.
- Docker images COPY everything under `src/`, so runtime reads "just work" there — the trap is compiled-only flows (npm publish, library wheels).

**Lived failure**: a bootstrap did `fs.readFileSync('./schema.sql')` (worked in dev from `src/`, broke at prod deploy with no `schema.sql` in `dist/`). Same class bit a FastAPI service whose wheel didn't ship `materializations/orders_daily.sql`.

## 6. Env vars — fail fast, never silent

At startup, validate every required var and `process.exit(1)` listing what's missing. For optional vars (`SENTRY_DSN`, `CLICKUP_API_KEY`), log a single line naming what's degraded (`[startup] CLICKUP_API_KEY not set — ClickUp integration disabled`). Silent feature loss is the worst kind of bug.

## 7. README — minimum bar

One-line description, how to run locally, required env vars (example values, never real secrets), how to run tests, how to verify it works (curl + browser URL). Without it, the operator (you, in 3 months) won't remember.

## 8. Logs at startup — print what matters

Three to five lines answering "what service, what version, where, what's enabled" (e.g. `url-shortener v0.1.2 listening on http://localhost:3456 — DB: urls.db, Features: shorten=on analytics=off`). Not a dump, not silence.

## The Vikram/Tanvi handoff checklist

Before Vikram says "done":
- [ ] `GET /` returns a real response (not 404); `GET /health` returns 200 with status JSON
- [ ] `PORT` env var works, default documented; crashes loudly on `EADDRINUSE`
- [ ] Required env vars validated at startup; optional vars log a single-line degradation notice
- [ ] Native deps in `pnpm.onlyBuiltDependencies` AND the native-build check passes AND README notes the workaround
- [ ] Every package imported in `src/` appears in `dependencies` (no transitive borrowing)
- [ ] Non-TS runtime files (`.sql`, `.proto`, …) declared in the build's asset config and verified present in `dist/`
- [ ] Test config and production tsconfig don't share ESM/CommonJS settings unless the app is one end-to-end
- [ ] Time-bucketed queries ("today", "this week") are tenant-timezone aware, not server-UTC (see `database-design` → Time + Timezones)
- [ ] Smoke test file exists and runs the server on a real port; README has run + test + verify instructions

Before Tanvi says PASS:
- [ ] All unit + integration tests pass
- [ ] **Smoke test against a real running server passes** (not just `app.request()`)
- [ ] `curl localhost:<PORT>/` returns something (not 404); `curl localhost:<PORT>/health` returns 200
- [ ] Server starts cleanly when PORT is set; crashes loudly (not silently) when PORT is taken

If any is unchecked, the verdict is FAIL with the specific gap named.

## Anti-patterns this skill explicitly forbids

- ❌ "It works in tests" without ever having `curl`'d the running server
- ❌ Hardcoded port 3000 with no env var override
- ❌ Silent skip on missing optional env vars (must log); loud crash on missing required vars (must fail fast)
- ❌ Shipping a service whose `GET /` returns 404 with no body
- ❌ `pnpm install` succeeding but native binaries unbuilt (treat the "ignored build scripts" warning as a real error)
- ❌ "We'll add the smoke test later" — later is never
