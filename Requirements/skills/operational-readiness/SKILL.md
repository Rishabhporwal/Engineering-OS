---
name: operational-readiness
description: Production-readiness checklist for every shippable service — root handler, health check, port selection, real-network smoke test, env var validation, native-dep gotchas. Used by Vikram before declaring a service "done" and by Tanvi before issuing a PASS verdict. Encoded from real failures the team hit (pnpm 11 native-build gate, port 3000 collisions, in-memory tests masking real-network bugs, API-only services that look broken in browsers).
---

# Operational Readiness — the "won't look broken in production" checklist

Every shippable service must clear this checklist before Vikram hands off and before Tanvi issues PASS. These rules exist because the team hit each of them in production-like tests. They're cheap to satisfy and expensive to skip.

## 1. Root handler (`GET /`) is required, even for API-only services

**Wrong**: API service responds 404 to `GET /`. A human hitting the URL in a browser sees "broken".

**Right**: `GET /` returns either:
- A minimal HTML page describing what the service does, links to `/health` and any docs
- OR a JSON response: `{"service": "<name>", "version": "<sha>", "endpoints": {...}}` if Content-Type negotiation says JSON
- OR a redirect to `/health` if there is genuinely no UI

The cost is 5 lines of code. The signal it sends ("yes this service exists") prevents 30 minutes of "is the server down?" debugging.

## 2. `/health` endpoint is non-negotiable

Returns `{"status": "ok"}` minimum. Better: include `version` (git SHA), `deps` (DB / cache / external API reachability), `uptime`.

```typescript
app.get('/health', async (c) => {
  const [db, redis] = await Promise.allSettled([
    pingDb(), pingRedis()
  ])
  return c.json({
    status: [db, redis].every(r => r.status === 'fulfilled') ? 'ok' : 'degraded',
    version: process.env.GIT_SHA ?? 'dev',
    deps: { db: db.status, redis: redis.status },
  })
})
```

Why: EKS / ALB / CloudFront all need this (Brain's locked stack — TECH/09). Without a working liveness + readiness probe, your service can't be deployed. See [health-check-endpoints](../health-check-endpoints/SKILL.md) for Brain's full Fastify + FastAPI probe pattern.

## 3. Port selection — never hardcode, never assume :3000 is free

**Wrong**:
```typescript
const port = 3000
```

**Right** (order of preference):
```typescript
const port = Number(process.env.PORT ?? 0)   // 0 = OS picks a free port
// OR if you must default to a number:
const port = Number(process.env.PORT ?? 3000)
// AND log clearly:
console.log(`listening on http://localhost:${actualPort}`)
```

When `EADDRINUSE` fires, the server crashes loudly — don't try to "retry on next port". The operator must know the port is taken, not have it silently start on a port they can't find.

**Real failure pattern the team hit**:
- Default port 3000 was occupied by an unrelated dev service
- Our server crashed with `EADDRINUSE`
- Test client hit localhost:3000 anyway and got `307 → /login` from the OTHER service
- Looked like our app was responding wrong, not that it had failed to bind

**Mitigation**: smoke test should `lsof -i :$PORT` before binding, OR bind to port 0 and read back the chosen port.

## 4. Smoke test against a REAL listening server — `app.request()` mocks are not enough

In-process request mocks (Hono's `app.request()`, NestJS `Test.createTestingModule`, FastAPI `TestClient`) skip the network stack entirely. They miss:
- Port binding failures
- TLS / cert issues
- HTTP/2 vs HTTP/1.1 negotiation
- Reverse proxy / load balancer quirks
- Network timeouts
- DNS

**Two test layers required**:

1. **Integration tests** (fast, in-process): `app.request()` / `TestClient` — these are your hot loop, run on every save.
2. **Smoke tests** (slow, real network): spawn the actual server on a real port, curl/fetch against it. Run before PASS verdict and in CI post-deploy.

Smoke test template (TypeScript / Node):
```typescript
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

describe('smoke', () => {
  let proc: ReturnType<typeof spawn>
  let port: number

  beforeAll(async () => {
    port = 4000 + Math.floor(Math.random() * 1000)  // random free-ish port
    proc = spawn('node', ['dist/server.js'], {
      env: { ...process.env, PORT: String(port) },
      stdio: 'pipe',
    })
    // wait for "listening on" log
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('server did not start within 10s')), 10_000)
      proc.stdout!.on('data', (d) => {
        if (d.toString().includes('listening')) { clearTimeout(timer); resolve() }
      })
    })
  })

  afterAll(() => proc?.kill())

  it('GET /health returns 200 over real network', async () => {
    const res = await fetch(`http://localhost:${port}/health`)
    expect(res.status).toBe(200)
    expect((await res.json()).status).toBe('ok')
  })

  it('GET / returns identifiable content (not a 404)', async () => {
    const res = await fetch(`http://localhost:${port}/`)
    expect(res.status).toBe(200)
    const text = await res.text()
    expect(text).toMatch(/<service-name>|api/i)
  })
})
```

## 5. Native dependencies — declare the build trust list

For Node projects using `better-sqlite3`, `node-gyp`-based packages, `esbuild`, `sharp`, etc.:

Add to `package.json`:
```json
{
  "pnpm": {
    "onlyBuiltDependencies": ["better-sqlite3", "esbuild", "sharp"]
  }
}
```

**pnpm 11 gotcha**: even with `onlyBuiltDependencies` declared, pnpm's pre-flight `runDepsStatusCheck` may still block commands with `[ERR_PNPM_IGNORED_BUILDS]`, AND can leave native binaries unbuilt while `pnpm install` reports success. This bit a multi-tenant analytics build twice in one session. Don't trust the install exit code.

**Pre-flight verification** (drop into every project that uses native deps):
```bash
# scripts/check-native-builds.sh
set -e
# pnpm.onlyBuiltDependencies is an ARRAY of package names, not an object — read directly.
for pkg in $(node -p "(require('./package.json').pnpm && require('./package.json').pnpm.onlyBuiltDependencies || []).join(' ')"); do
  if [ -n "$pkg" ]; then
    node -e "require('$pkg')" 2>/dev/null \
      || { echo "FAIL: $pkg native binary missing — run: pnpm rebuild $pkg"; exit 1; }
  fi
done
echo "OK: all native deps loadable"
```
Wire it into `predev`, `pretest`, and CI. A green test run while `better-sqlite3` is silently unbuilt is exactly the failure mode this catches.

Workarounds when the gate fires (in order of preference — Brain is pnpm-locked; do NOT adopt bun):
1. `pnpm rebuild <package>` — explicit build, usually fixes it
2. Run the binary directly: `node_modules/.bin/vitest run` instead of `pnpm test`
3. `pnpm approve-builds` interactively (one-time)
4. Set `CI=true` in the command
5. Pin `onlyBuiltDependencies` in `package.json` to whitelist the package permanently

Document the chosen workaround in the service's README.

## 5b. Don't rely on transitive dependencies you import directly

If your code has `import { json } from 'express'`, `express` MUST be in your direct `dependencies` — not borrowed from `@nestjs/platform-express`'s tree.

**Lived failure**: a NestJS service imported `express`'s `json` middleware to install a `rawBody` verifier for third-party webhook HMAC. The smoke test passed in CI (transitive resolution worked). At server start in production-like demo: `MODULE_NOT_FOUND: express`. The transitive path resolves only under specific hoisting layouts.

**Rule**: if it appears in an `import` / `require`, it appears in `dependencies`. Run `grep -r "from 'express'" src/` (and equivalents for any common transitively-pulled dep) on the way to PASS verdict.

## 5c. Tests using ESM features need their own tsconfig

If tests use `import.meta.url`, top-level `await`, or other ESM-only features while the app compiles to CommonJS for Node, your main `tsconfig.json` will fight you forever. Split:

```jsonc
// tsconfig.json — production build (CommonJS for Node)
{
  "compilerOptions": { "module": "commonjs", "moduleResolution": "node" },
  "include": ["src/**/*"],
  "exclude": ["test/**", "**/*.test.ts", "**/*.spec.ts"]
}

// tsconfig.test.json — what vitest/jest typecheck against
{
  "extends": "./tsconfig.json",
  "compilerOptions": { "module": "esnext", "moduleResolution": "bundler", "noEmit": true },
  "include": ["test/**/*", "src/**/*"]
}
```

Point `typecheck` at the test config: `"typecheck": "tsc -p tsconfig.test.json --noEmit"`. The production build still uses the strict CommonJS config.

## 5d. Non-TS runtime files must be declared in the build output

`tsc`, `esbuild`, `swc`, `tsup`, `nest` — none copy `.sql`, `.proto`, `.yaml`, `.json` fixture files to `dist/` by default. If your code reads them at runtime, they vanish in production.

**General rule** (do this first, every time): grep `src/` for runtime file reads and confirm every match is either (a) declared in the bundler's asset config, or (b) inlined as a string at build time.

```bash
grep -rE "readFileSync|readFile|fs\.readFile|fs/promises.*readFile|require\(['\"].*\\.(sql|proto|yaml|yml|json|hbs|html|graphql)['\"]" services/<service>/src/
```

Don't ship the gap to production.

**Brain Fastify + tsup (Node services — Vikram)**

```typescript
// tsup.config.ts
import { defineConfig } from 'tsup';
import { copy } from 'esbuild-plugin-copy';

export default defineConfig({
  entry: ['src/server.ts'],
  outDir: 'dist',
  format: ['cjs'],
  sourcemap: true,
  clean: true,
  esbuildPlugins: [
    copy({
      assets: [
        { from: 'src/**/*.sql', to: 'dist/' },           // ClickHouse DDL fixtures
        { from: 'src/**/*.proto', to: 'dist/' },         // gRPC contracts (if not loaded via @bufbuild/protobuf codegen)
        { from: 'src/**/*.yaml', to: 'dist/' },          // config / OpenAPI specs
      ],
    }),
  ],
});
```

**Brain Python (uv + FastAPI — Sahil / Kabir / Maya / Neel)**

```toml
# pyproject.toml — include non-py runtime files in the wheel
[tool.hatch.build.targets.wheel]
packages = ["src/<package>"]

[tool.hatch.build.targets.wheel.force-include]
"src/<package>/materializations" = "<package>/materializations"  # ClickHouse .sql
"src/<package>/proto"           = "<package>/proto"             # generated proto stubs
```

For Docker images, the COPY step copies everything under `src/` into the image — runtime file reads "just work" as long as the path stays under `src/`. The trap is in compiled-only flows (npm publish, library wheels) where assets must be explicitly declared.

**Lived failure**: a service's bootstrap module did `fs.readFileSync('./schema.sql')` to apply migrations. Worked in dev (reads from `src/`). Broke at first prod deploy (no `schema.sql` in `dist/`). The same class of bug bit a FastAPI service that did `Path(__file__).parent / 'materializations' / 'orders_daily.sql'` — the wheel didn't ship the materializations dir.

## 6. Env vars — fail fast, never silent

At server startup, validate every required env var:
```typescript
const required = ['DATABASE_URL', 'JWT_SECRET']
const missing = required.filter(k => !process.env[k])
if (missing.length) {
  console.error(`Missing env vars: ${missing.join(', ')}`)
  process.exit(1)
}
```

For optional vars (e.g., `SENTRY_DSN`, `CLICKUP_API_KEY`), document explicitly which features they enable. Log a single line at startup naming what's degraded:
```
[startup] CLICKUP_API_KEY not set — ClickUp integration disabled
```

Silent feature loss is the worst kind of bug.

## 7. README — minimum bar

Every service ships with a `README.md` that contains:
- One-line description
- How to run locally (`pnpm dev` or equivalent)
- Required env vars (with example values, never real secrets)
- How to run tests
- How to verify it's working (curl examples + browser URL)

Without this, the operator (you, in 3 months) won't remember.

## 8. Logs at startup — print what matters

```
url-shortener v0.1.2 listening on http://localhost:3456
  DB:       urls.db (3 records)
  Features: shorten=on, analytics=off (no CLICKUP_API_KEY)
  Env:      development
```

Not a dump, not silence. Three to five lines that answer: "what service, what version, where, what's enabled".

## The Vikram/Tanvi handoff checklist

Before Vikram says "done" and hands off to Tanvi, this must be true:
- [ ] `GET /` returns a real response (not 404)
- [ ] `GET /health` returns 200 with status JSON
- [ ] `PORT` env var works, default is documented
- [ ] Required env vars are validated at startup
- [ ] Optional env vars log a single-line degradation notice when missing
- [ ] Native deps (if any) are in `pnpm.onlyBuiltDependencies` AND `scripts/check-native-builds.sh` passes AND README mentions the workaround
- [ ] Every package imported in `src/` appears in `dependencies` (no transitive borrowing)
- [ ] Non-TS files read at runtime (`.sql`, `.graphql`, `.proto`, etc.) are declared in the build's asset config and verified present in `dist/`
- [ ] Test config and production tsconfig do not share ESM/CommonJS settings unless the app is one or the other end-to-end
- [ ] Time-bucketed queries ("today", "this week") are tenant-timezone aware, not server-UTC (see `database-design` → Time + Timezones)
- [ ] Smoke test file exists and runs the server on a real port
- [ ] README has run + test + verify instructions

Before Tanvi says PASS:
- [ ] All unit + integration tests pass
- [ ] **Smoke test against a real running server passes** (not just `app.request()`)
- [ ] `curl localhost:<PORT>/` returns something — not 404
- [ ] `curl localhost:<PORT>/health` returns 200
- [ ] Server starts cleanly when PORT is set
- [ ] Server crashes loudly (not silently) when PORT is taken

If any of these is unchecked, the verdict is FAIL with the specific gap named.

## Anti-patterns this skill explicitly forbids

- ❌ "It works in tests" without ever having `curl`'d the running server
- ❌ Hardcoded port 3000 with no env var override
- ❌ Silent skip on missing optional env vars (must log)
- ❌ Loud crash on missing required env vars (must fail fast at startup)
- ❌ Shipping a service whose `GET /` returns 404 with no body
- ❌ `pnpm install` succeeding but native binaries unbuilt (the "ignored build scripts" warning is a real error, treat it as one)
- ❌ "We'll add the smoke test later" — later is never
