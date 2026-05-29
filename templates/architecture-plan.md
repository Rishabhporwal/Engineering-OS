# Architecture Plan — {{REQ_ID}}

> Filled by Aryan (Stage 2). **Scale depth to risk** (per `docs/role-empowerment-model.md` handoff bands): a small/standard task gets a short plan — fill a section in one line or mark `n/a — <why>`; reserve full detail for high-stakes work. `TBD` is never allowed at Stage 3. Cite canon by reference (e.g. `per TECH/15`), don't restate it.

| req_id | actor | timestamp |
|---|---|---|
| `{{REQ_ID}}` | architect (Aryan) | {{TS}} |

## 1. Context & proposed solution
*What we're solving, why now, and the plain-English approach (scale to risk).*
{{CONTEXT_AND_SOLUTION}}

```mermaid
{{MERMAID_DIAGRAM}}
```

## 2. Paradigm
**Declared:** `{{PARADIGM}}` (sql / ml / small_llm / frontier_llm). **Justification:** {{PARADIGM_JUSTIFICATION}}
*(SQL > ML > small_llm ≫ frontier_llm — see skill `cost-routing-paradigms` + `TECH/12`.)*

## 3. API design (fill only the surfaces touched; else `n/a`)
- **gRPC protos:** {{PROTO}} · **tRPC procedures:** {{TRPC}} · **MCP tools:** {{MCP}} · **REST:** {{REST}}
- **Breaking changes + versioning:** {{BREAKING_AND_VERSIONING}} *(skill `api-discipline`)*

## 4. Data model changes
- **Postgres:** tables ±{{PG_TABLES}}, indexes {{INDEXES}}, RLS {{RLS_POLICIES}}
- **ClickHouse:** tables ±{{CH_TABLES}}, MVs {{MV_ADDED}}
- **Migration plan** (reversible): {{MIGRATION_PLAN}}

## 5. Event model
Topics ±{{TOPICS}} · partition key `workspace_id` (always) · exactly-once: {{EXACTLY_ONCE}}

## 6. Single-Primitive sweep
*Per cross-cutting concern: reused / extended / violated-needs-discussion. Flag any per-channel fork.*
{{SINGLE_PRIMITIVE_SWEEP}}

## 7. Multi-tenancy enforcement (all 4 layers)
- [ ] JWT (api-gateway claim) · [ ] service-side (`request.workspace_id == metadata`) · [ ] DB RLS + CH query-gateway · [ ] Kafka envelope assert

## 8. Observability
Metrics {{METRICS}} · Logs {{LOGS}} · Traces {{TRACES}} · Alarms {{ALARMS}} · Dashboards {{DASHBOARDS}}

## 9. Test strategy
Unit {{UNIT}} · Integration {{INTEGRATION}} · Contract {{CONTRACT}} (buf breaking/Pact/tRPC+MCP diff) · E2E {{E2E}} · Load {{LOAD}} (Phase 3+) · **Real-network smoke {{SMOKE}} (mandatory for PASS)** · Mutation targets {{MUTATION}}
**Verification validity:** tests run under real (non-`BYPASSRLS`) security context; every probe has a negative control (fails when protection removed); parity vs an independent source. *(pipeline `verification_validity`.)*

## 10. Security (→ Shreya), India context, region-adapter impact
- **Security notes:** {{SECURITY_NOTES}}
- **India context:** {{INDIA_CONTEXT}} · **Region-adapter impact:** {{REGION_ADAPTER_IMPACT}}

## 11. Cost estimate
Daily volume {{LOAD}} · LLM tokens/day {{TOKENS_PER_DAY}} · ₹/month {{INR_PER_MONTH}}

## 12. Risks & alternatives
| Risk | Sev | Mitigation |  ·  | Alternative | Why rejected |
|---|---|---|---|---|---|
| {{RISK}} | {{SEV}} | {{MIT}} |  | {{ALT}} | {{ALT_WHY}} |

## 13. Tracks (Stage-3 decomposition)
Per track: `@owner` + dependencies + 2–5 min tasks with `file:line`. **Every persona/synthesis `must-fix` is a REQUIRED pass-1 item here** (kills the O7 bounce). **Every pinned version is real** (verified or "resolve latest-stable"). **Any service create/change includes its deploy-pipeline track.**
{{TRACKS}}

**Over-engineering self-check:** {{PASS_or_trims}} — plan length matches the band; no unrequested files/deps/abstractions/observability; tests target behavior at integration points.

## 14. CTO Advisor paradigm sign-off
{{PARADIGM_SIGNOFF_TS}}
