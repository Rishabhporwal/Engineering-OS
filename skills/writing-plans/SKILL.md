---
name: writing-plans
description: Break work into 2-5 minute tasks, each with one file path, one verification step, one owner. Used by the Delivery Coordinator (spec subtasks), the Architect (build tracks), and any agent producing a TODO list.
---

# Writing Plans — 2-5 Minute Task Discipline

## The Rule

Every leaf task in any plan must satisfy **ALL** of:

1. **2-5 minutes** of estimated effort. Actual minutes — not "small"/"medium".
2. **One concrete file path** named in the title or description.
3. **One verification step** — the test, lint, type check, build, or assertion that confirms done.
4. **One owner agent** — no shared ownership.

If a task is bigger than 5 minutes, **split it**. No exception. Big tasks hide blockers and break parallel-track coordination.

## Why this matters

- Small tasks are honest: complexity surfaces during planning, not build.
- Small tasks are parallelizable: one agent isn't blocking three on a single huge step.
- Small tasks are auditable: tracker status is meaningful when each card is genuinely 2-5 min.
- Small tasks unblock the Three-Fix Threshold: after 2 failed attempts you know what *specifically* is wrong.

## The Splitting Heuristic

If you can't answer each in one sentence, split: What single file does this change? What's the verification command? Is this <= 5 minutes for someone fluent in the stack?

## Bad → Good Examples

Note the task tag convention `[ROLE][service]` and the `verify:` command. **Keep ownership boundaries distinct — one owner per leaf task, by the role that owns that seam.** (Service/file names below are illustrative; bind them to your product's actual layout in the Canon's `STACK.md`.)

### Backend
- ❌ "Implement the cascade endpoint"
- ✅ "[BACKEND][api-gateway] Add `CascadeInput` validation schema in apps/api-gateway/src/routers/analytics.ts — verify: `<typecheck command for that package>`"
- ✅ "[BACKEND][api-gateway] Add `analytics.cascade.get` procedure (same file) — verify: `<test command for analytics.test.ts>`"

### Ingestion
- ❌ "Add the connector"
- ✅ "[BACKEND][ingestion] Add `OrderEvent` model in apps/ingestion-service/src/connectors/<vendor>/models.py — verify: `<type-check command>`"
- ✅ "[BACKEND][ingestion] Add idempotent UPSERT + producer in .../<vendor>/consumer.py — verify: `<test command for test_consumer.py>`"

### Analytics / metrics
- ❌ "Compute the cohort metric"
- ✅ "[AI/ML][analytics] Add the daily materialization in apps/analytics-service/src/materializations/<metric>_daily.sql — verify: `<test command for the materialization>`"
- ✅ "[AI/ML][analytics] Add `computeCohortMetric()` to the metric registry in BOTH runtimes with a parity test against the oracle — verify: `<registry test in each runtime>`"

### Lifecycle / outbound (cheapest-sufficient-effort tiering applies)
- ✅ "[BACKEND][lifecycle] Add the scoring job (deterministic/SQL tier — no model) in apps/lifecycle-service/src/scoring/score.py — verify: `<test command for test_score.py>`"
- ✅ "[BACKEND][lifecycle] Add the channel-window compliance guard (per `COMPLIANCE.md`) in .../src/compliance/channel-window.ts — verify: `<test command>` (assert both boundary edges)"

### Web
- ✅ "[FRONTEND][web] Add `app/(dashboard)/cohort/page.tsx` consuming the cohort procedure — verify: `<web typecheck command>`"
- ✅ "[FRONTEND][web] Wire infinite scroll via cursor pagination — verify: E2E `e2e/cohort.spec.ts`"

### Mobile
- ✅ "[MOBILE][mobile] Add `<SignalCard>` component in apps/mobile/src/screens/<surface>/SignalCard.tsx — verify: `<mobile typecheck + test command>`"
- ✅ "[MOBILE][mobile] Wire approve/reject/edit to the audit-log record procedure with idempotency keys — verify: E2E `e2e/<surface>.test.ts`"

### Platform
- ✅ "[PLATFORM][infra] Add the service autoscaler config in infra/<iac>/<service>.* (target 70% CPU, min 3 max 20) — verify: `<infra synth + diff command>`"
- ✅ "[PLATFORM][infra] Add the data-store readiness check to `/health/ready` — verify: `curl -s -o /dev/null -w '%{http_code}' https://staging.<product-domain>/health/ready` returns 200"

## Plan Output Format (the Delivery Coordinator's spec)

```markdown
## Tasks (2-5 min each)

### Phase 1: Contracts (if breaking / new internal-API or tool surface)
- [ ] [ARCHITECT] Define the contract in protos/<service>/v1/<service>.proto
      Verify: `<lint + breaking-change check against main>`
### Phase 2: API surface                       — [BACKEND][api-gateway]
### Phase 3: Web UI                             — [FRONTEND][web]
### Phase 4: Mobile (if in scope)              — [MOBILE][mobile]
### Phase 5: Ingestion (if connector touch)    — [BACKEND][ingestion]
### Phase 6: Analytics (if new metric)          — [AI/ML][analytics]
### Phase 7: Intelligence (if agent/model)      — [AI/ML][intelligence]
### Phase 8: Lifecycle (if outbound/compliance)— [BACKEND][lifecycle]
### Phase 9: Quality gates                     — [SECURITY] + [QA]
### Phase 10: Deploy                           — [PLATFORM]
```

Only include phases the slice touches. Trivial/Small tier may have 1–2 phases. Phases 5–8 are usually mutually exclusive in any one slice. This list is what the Delivery Coordinator pushes to the task tracker as subtasks of the Epic.

## When NOT to apply this rule

- **Discovery / brainstorm tasks** — exploratory, can't be planned to 5 minutes.
- **Architecture decisions / ADRs** — the Architect's output is contracts, not 5-min tasks.
- **Incident response** — speed > planning during a fire.

## Failure Mode: "But this task is genuinely big"

Almost always one of: (1) **hidden complexity** — split by exposing subdecisions ("decide schema for X" before "implement X"); (2) **missing prerequisites** — name the setup task ("scaffold module skeleton" before "add resolver"); (3) **a research task in disguise** — flag as a spike (boxed 30-60 min), output to `memory/plans/`. "I don't know how to split this" is a request for clarification — surface it.
