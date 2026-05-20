---
name: writing-plans
description: Discipline for breaking work into 2-5 minute tasks with concrete file paths and verification steps. Used by Priya (PM) when generating spec subtasks, by Aryan (Architect) when emitting build tracks, and by any agent producing a TODO list. The rule is non-negotiable — vague big tasks hide blockers and inflate the cycle. Borrowed and adapted from obra/superpowers writing-plans skill.
---

# Writing Plans — 2-5 Minute Task Discipline

## The Rule

Every leaf task in any plan must satisfy **ALL** of:

1. **2-5 minutes** of estimated effort. Not "small". Not "medium". Actual minutes.
2. **One concrete file path** named in the title or description.
3. **One verification step** — the test, lint, type check, build, or assertion that confirms done.
4. **One owner agent** — no shared ownership.

If a task is bigger than 5 minutes, **split it**. There is no exception. Big tasks hide blockers, hide complexity, and break the parallel-track coordination model.

## Why this matters

- Small tasks are honest: complexity surfaces during planning, not during build.
- Small tasks are parallelizable: one agent isn't blocking three others on a single huge step.
- Small tasks are auditable: ClickUp status is meaningful when each card is genuinely 2-5 min.
- Small tasks unblock the Three-Fix Threshold: after 2 failed attempts, you know what *specifically* is wrong because the scope is tight.

## The Splitting Heuristic

If you wrote a task and you can't immediately answer these in one sentence each, split it:
- What single file does this change?
- What's the verification command (test name, build target, lint rule)?
- Is this <= 5 minutes for someone fluent in the stack?

## Bad → Good Examples

### Backend (Node — Vikram in api-gateway / core-service / notifications-service / lifecycle-service Node side)
- ❌ "Implement first-product cascade endpoint"
- ✅ "[VIKRAM][api-gateway] Add FirstProductCascadeInput Zod schema in services/api-gateway/src/trpc/routers/analytics.ts — verify: `pnpm --filter api-gateway typecheck`"
- ✅ "[VIKRAM][api-gateway] Add `analytics.firstProductCascade.get` tRPC procedure in services/api-gateway/src/trpc/routers/analytics.ts — verify: `pnpm --filter api-gateway test -- analytics.test.ts`"
- ✅ "[VIKRAM][api-gateway] Register `analytics.first_product_cascade.compute.v1` MCP tool in services/api-gateway/src/mcp/tools/analytics/first-product-cascade.ts — verify: `pnpm --filter api-gateway test -- mcp.test.ts`"

### Ingestion (Python — Maya in ingestion-service)
- ❌ "Add Shopify connector"
- ✅ "[MAYA][ingestion] Add ShopifyOrderEvent Pydantic model in services/ingestion-service/src/connectors/shopify/models.py — verify: `uv run mypy src/connectors/shopify`"
- ✅ "[MAYA][ingestion] Add idempotent UPSERT to raw_shopify_orders + Kafka producer in services/ingestion-service/src/connectors/shopify/consumer.py — verify: `uv run pytest tests/connectors/shopify/test_consumer.py`"
- ✅ "[MAYA][ingestion] Register `integrations.shopify.order.v1` Avro schema with Glue Schema Registry — verify: `uv run python scripts/register_schema.py --topic integrations.shopify.order.v1`"

### Analytics (Python — Maya in analytics-service)
- ❌ "Compute First Product Cascade"
- ✅ "[MAYA][analytics] Add `first_product_attribution_local` ClickHouse table + ReplacingMergeTree in services/analytics-service/src/materializations/first_product_attribution.sql — verify: `clickhouse-client --query 'DESCRIBE first_product_attribution_local'`"
- ✅ "[MAYA][analytics] Add `first_product_cascade_daily_mv` MV in services/analytics-service/src/materializations/first_product_cascade_daily_mv.sql — verify: `uv run pytest tests/materializations/test_first_product_cascade.py`"
- ✅ "[MAYA][analytics] Add `computeFirstProductCascade()` to packages/lib-metrics (TS) + pylibs/brain_metrics (Python) with parity test — verify: `pnpm --filter lib-metrics test && uv run pytest pylibs/brain_metrics/tests/test_parity.py`"

### Intelligence (Python — Maya in intelligence-service)
- ❌ "Add AICMO First-Product agent"
- ✅ "[MAYA][intelligence] Implement AICMO-FirstProduct agent on the base pattern in services/intelligence-service/src/agents/aicmo_first_product.py — verify: `uv run pytest tests/agents/test_aicmo_first_product.py`"
- ✅ "[MAYA][intelligence] Add Brand Fingerprint refresh job in services/intelligence-service/src/memory/brand_fingerprint.py — verify: `uv run pytest tests/memory/test_brand_fingerprint.py` (covers pgvector insert + cosine similarity)"

### Lifecycle (Node + Python — Maya in lifecycle-service; Vikram on the Node tRPC side)
- ❌ "Build RFM audience"
- ✅ "[MAYA][lifecycle] Add RFM scoring SQL job (paradigm 1 — SQL only) in services/lifecycle-service/python/src/rfm/score.py — verify: `uv run pytest tests/rfm/test_score.py`"
- ✅ "[VIKRAM][lifecycle] Add `audience.build` tRPC mutation in services/lifecycle-service/node/src/trpc/routers/audience.ts — verify: `pnpm --filter lifecycle-service test -- audience.test.ts`"
- ✅ "[MAYA][lifecycle] Add 09:00–21:00 IST calling-hours guard to channel router in services/lifecycle-service/node/src/compliance/calling-hours.ts — verify: `pnpm --filter lifecycle-service test -- calling-hours.test.ts` (boundary cases at 08:59:59 and 21:00:00 IST)"

### Web (Ananya in apps/web)
- ❌ "Build First Product Cascade page"
- ✅ "[ANANYA][web] Add `app/(dashboard)/first-product-cascade/page.tsx` Server Component consuming `trpc.analytics.firstProductCascade.get` — verify: `pnpm --filter web typecheck`"
- ✅ "[ANANYA][web] Add `<FirstProductCascadeTable>` component in apps/web/components/cascade/FirstProductCascadeTable.tsx — verify: `pnpm --filter web test -- FirstProductCascadeTable`"
- ✅ "[ANANYA][web] Wire infinite scroll via TanStack Query `useInfiniteQuery` consuming cursor pagination — verify: Cypress test `cypress/e2e/first-product-cascade.cy.ts`"

### Mobile (Karan in apps/mobile)
- ❌ "Add cascade widget to Morning Brief"
- ✅ "[KARAN][mobile] Add `<CascadeSignal>` Tamagui component in apps/mobile/src/screens/morning-brief/signals/CascadeSignal.tsx — verify: `pnpm --filter mobile typecheck && pnpm --filter mobile test`"
- ✅ "[KARAN][mobile] Wire approve/reject/edit handlers to `trpc.decisionLog.record` mutation with ULID idempotency keys — verify: Detox e2e `e2e/morning-brief-cascade.test.ts`"

### Platform (Jatin in infra/)
- ❌ "Scale analytics-service"
- ✅ "[JATIN][infra] Add `analytics-service` HPA to infra/cdk/lib/eks/analytics-service.ts (target 70% CPU, min 3 max 20) — verify: `pnpm --filter infra synth && cdk diff`"
- ✅ "[JATIN][infra] Add ClickHouse readiness check to `/health/ready` per operational-readiness — verify: `curl -s -o /dev/null -w '%{http_code}' https://staging.api.brain.pipadacapital.com/health/ready` returns 200"

## Plan Output Format (Priya's spec includes this)

```markdown
## Tasks (2-5 min each)

### Phase 1: Contracts (if breaking / new gRPC or MCP surface)
- [ ] [ARYAN] Define gRPC `.proto` for <RPC> in protos/brain/<service>/v1/<service>.proto
      Verify: `buf lint && buf breaking --against '.git#branch=main'`

### Phase 2: API surface (Node — tRPC + MCP)
- [ ] [VIKRAM][api-gateway] <tRPC procedure or MCP tool task with file path>
      Verify: <command>

### Phase 3: Web UI
- [ ] [ANANYA][web] <task>
      Verify: <command>

### Phase 4: Mobile (only if mobile in scope)
- [ ] [KARAN][mobile] <task>
      Verify: <command>

### Phase 5: Ingestion (only if new data source / connector touch)
- [ ] [SAHIL][ingestion] <connector / Kafka producer / Avro schema task>
      Verify: <command>

### Phase 6: Analytics (only if new metric / MV / drill-down)
- [ ] [KABIR][analytics] <ClickHouse MV / metric registry entry / RegionAdapter task>
      Verify: <command>

### Phase 7: Intelligence (only if new agent capability / LLM call / Memory Layer change)
- [ ] [MAYA][intelligence] <agent base-pattern / synthesis / Brand Fingerprint task>
      Verify: <command>

### Phase 8: Lifecycle (only if outbound channel / compliance touch)
- [ ] [NEEL][lifecycle] <audience / channel router / compliance / AI calling task>
      Verify: <command>

### Phase 9: Quality gates
- [ ] [SHREYA][security] <threat-model surface + verification snippet>
- [ ] [TANVI][qa] <test plan + paradigm audit + metric registry parity check>

### Phase 10: Deploy
- [ ] [JATIN][devops] <CI / EKS / EAS task>
      Verify: <command>
```

Only include phases the slice actually touches. Trivial / Small tier slices may have only 1–2 phases. Phases 5–8 are usually mutually exclusive in any one slice (a single slice rarely changes ingestion + analytics + intelligence + lifecycle simultaneously). **Maya owns the Python data plane (ingestion, analytics, intelligence, lifecycle build); Vikram owns the Node tRPC surfaces — keep the service boundaries distinct in each task tag.**

This list is what Priya pushes to ClickUp as subtasks of the Epic.

## When NOT to apply this rule

- **Discovery / brainstorm tasks** — these are exploratory, can't be planned to 5 minutes.
- **Architecture decisions / ADRs** — Aryan's design output isn't a task list of 5-min things; it's contracts.
- **Incident response** — speed > planning during a fire.

For everything else: 2-5 minutes or it's not a task yet.

## Failure Mode: "But this task is genuinely big"

If you find a task that *cannot* be split smaller, that's almost always one of:
1. **Hidden complexity** — split by exposing subdecisions as their own tasks ("decide schema for X" before "implement X")
2. **Missing prerequisites** — there's a setup task you haven't named ("scaffold module skeleton" before "add resolver")
3. **A research task in disguise** — flag as a spike (boxed at 30-60 min) and put output in `memory/plans/`

The Founder sees "I don't know how to split this" as a request for clarification — surface it.
