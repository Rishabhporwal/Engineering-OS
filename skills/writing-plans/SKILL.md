---
name: writing-plans
description: Break work into 2-5 minute tasks, each with one file path, one verification step, one owner. Used by Priya (spec subtasks), Aryan (build tracks), and any agent producing a TODO list.
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
- Small tasks are auditable: ClickUp status is meaningful when each card is genuinely 2-5 min.
- Small tasks unblock the Three-Fix Threshold: after 2 failed attempts you know what *specifically* is wrong.

## The Splitting Heuristic

If you can't answer each in one sentence, split: What single file does this change? What's the verification command? Is this <= 5 minutes for someone fluent in the stack?

## Bad → Good Examples

Note the task tag convention `[OWNER][service]` and the `verify:` command. **Maya owns the Python data plane (ingestion, analytics, intelligence, lifecycle build); Vikram owns the Node tRPC surfaces — keep boundaries distinct.**

### Backend (Node — Vikram)
- ❌ "Implement first-product cascade endpoint"
- ✅ "[VIKRAM][api-gateway] Add `FirstProductCascadeInput` Zod schema in apps/api-gateway/src/trpc/routers/analytics.ts — verify: `pnpm --filter api-gateway typecheck`"
- ✅ "[VIKRAM][api-gateway] Add `analytics.firstProductCascade.get` tRPC procedure (same file) — verify: `pnpm --filter api-gateway test -- analytics.test.ts`"

### Ingestion (Python — Maya)
- ❌ "Add Shopify connector"
- ✅ "[MAYA][ingestion] Add `ShopifyOrderEvent` Pydantic model in apps/ingestion-service/src/connectors/shopify/models.py — verify: `uv run mypy src/connectors/shopify`"
- ✅ "[MAYA][ingestion] Add idempotent UPSERT + Kafka producer in .../shopify/consumer.py — verify: `uv run pytest tests/connectors/shopify/test_consumer.py`"

### Analytics (Python — Maya)
- ❌ "Compute First Product Cascade"
- ✅ "[MAYA][analytics] Add `first_product_cascade_daily_mv` MV in apps/analytics-service/src/materializations/first_product_cascade_daily_mv.sql — verify: `uv run pytest tests/materializations/test_first_product_cascade.py`"
- ✅ "[MAYA][analytics] Add `computeFirstProductCascade()` to packages/lib-metrics (TS) + pylibs/brain_metrics (Python) with parity test — verify: `pnpm --filter lib-metrics test && uv run pytest pylibs/brain_metrics/tests/test_parity.py`"

### Lifecycle (Node + Python — Maya / Vikram)
- ✅ "[MAYA][lifecycle] Add RFM scoring SQL job (paradigm 1 — SQL only) in apps/lifecycle-service/python/src/rfm/score.py — verify: `uv run pytest tests/rfm/test_score.py`"
- ✅ "[MAYA][lifecycle] Add 09:00–21:00 IST calling-hours guard in .../node/src/compliance/calling-hours.ts — verify: `pnpm --filter lifecycle-service test -- calling-hours.test.ts` (boundaries at 08:59:59 and 21:00:00 IST)"

### Web (Ananya)
- ✅ "[ANANYA][web] Add `app/(dashboard)/first-product-cascade/page.tsx` Server Component consuming `trpc.analytics.firstProductCascade.get` — verify: `pnpm --filter web typecheck`"
- ✅ "[ANANYA][web] Wire infinite scroll via TanStack `useInfiniteQuery` (cursor pagination) — verify: Playwright `e2e/first-product-cascade.spec.ts`"

### Mobile (Karan)
- ✅ "[KARAN][mobile] Add `<CascadeSignal>` Tamagui component in apps/mobile/src/screens/morning-brief/signals/CascadeSignal.tsx — verify: `pnpm --filter mobile typecheck && pnpm --filter mobile test`"
- ✅ "[KARAN][mobile] Wire approve/reject/edit to `trpc.decisionLog.record` with ULID idempotency keys — verify: Detox `e2e/morning-brief-cascade.test.ts`"

### Platform (Jatin)
- ✅ "[JATIN][infra] Add `analytics-service` HPA to infra/cdk/lib/eks/analytics-service.ts (target 70% CPU, min 3 max 20) — verify: `pnpm --filter infra synth && cdk diff`"
- ✅ "[JATIN][infra] Add ClickHouse readiness check to `/health/ready` — verify: `curl -s -o /dev/null -w '%{http_code}' https://staging.api.brain.pipadacapital.com/health/ready` returns 200"

## Plan Output Format (Priya's spec)

```markdown
## Tasks (2-5 min each)

### Phase 1: Contracts (if breaking / new gRPC or MCP surface)
- [ ] [ARYAN] Define gRPC `.proto` in protos/brain/<service>/v1/<service>.proto
      Verify: `buf lint && buf breaking --against '.git#branch=main'`
### Phase 2: API surface (Node — tRPC + MCP)  — [VIKRAM][api-gateway]
### Phase 3: Web UI                            — [ANANYA][web]
### Phase 4: Mobile (if in scope)              — [KARAN][mobile]
### Phase 5: Ingestion (if connector touch)    — [MAYA][ingestion]
### Phase 6: Analytics (if new metric/MV)      — [MAYA][analytics]
### Phase 7: Intelligence (if agent/LLM/Memory)— [MAYA][intelligence]
### Phase 8: Lifecycle (if outbound/compliance)— [MAYA][lifecycle]
### Phase 9: Quality gates                     — [SHREYA][security] + [TANVI][qa]
### Phase 10: Deploy                           — [JATIN][devops]
```

Only include phases the slice touches. Trivial/Small tier may have 1–2 phases. Phases 5–8 are usually mutually exclusive in any one slice. This list is what Priya pushes to ClickUp as subtasks of the Epic.

## When NOT to apply this rule

- **Discovery / brainstorm tasks** — exploratory, can't be planned to 5 minutes.
- **Architecture decisions / ADRs** — Aryan's output is contracts, not 5-min tasks.
- **Incident response** — speed > planning during a fire.

## Failure Mode: "But this task is genuinely big"

Almost always one of: (1) **hidden complexity** — split by exposing subdecisions ("decide schema for X" before "implement X"); (2) **missing prerequisites** — name the setup task ("scaffold module skeleton" before "add resolver"); (3) **a research task in disguise** — flag as a spike (boxed 30-60 min), output to `memory/plans/`. "I don't know how to split this" is a request for clarification — surface it.
