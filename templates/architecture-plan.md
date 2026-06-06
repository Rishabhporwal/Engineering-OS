# Architecture Plan — {{REQ_ID}}

> Filled by the Architect (Stage 2). **Scale depth to risk** (per `docs/role-empowerment-model.md` handoff bands): a small/standard task gets a short plan — fill a section in one line or mark `n/a — <why>`; reserve full detail for high-stakes work. `TBD` is never allowed at Stage 3. Cite the Product Canon by reference (e.g. `per INVARIANTS.md`), don't restate it.

| req_id | actor | timestamp |
|---|---|---|
| `{{REQ_ID}}` | architect | {{TS}} |

## 1. Context & proposed solution
*What we're solving, why now, and the plain-English approach (scale to risk).*
{{CONTEXT_AND_SOLUTION}}

```mermaid
{{MERMAID_DIAGRAM}}
```

## 2. Effort tier
**Declared:** `{{PARADIGM}}` (deterministic / statistical-ml / small-model / large-model). **Justification:** {{PARADIGM_JUSTIFICATION}}
*(Cheapest sufficient effort: deterministic logic ≫ statistical/ML ≫ small model ≫ large model — see skill `cost-routing-paradigms`.)*

## 3. API design (fill only the surfaces touched; else `n/a`)
- **Internal RPC contracts:** {{PROTO}} · **In-process/typed procedures:** {{TRPC}} · **Agent/tool surfaces (MCP):** {{MCP}} · **REST:** {{REST}}
*(Per the API seams bound in the Product Canon's STACK.md — e.g. gRPC/protos, tRPC, MCP tools, REST.)*
- **Breaking changes + versioning:** {{BREAKING_AND_VERSIONING}} *(skill `api-discipline`)*

## 4. Data model changes
- **OLTP store:** tables ±{{PG_TABLES}}, indexes {{INDEXES}}, row-level tenant policies {{RLS_POLICIES}}
- **OLAP/analytics store:** tables ±{{CH_TABLES}}, materialized views {{MV_ADDED}}
*(Per the data-store seams bound in STACK.md.)*
- **Migration plan** (reversible): {{MIGRATION_PLAN}}

## 5. Event model
Topics ±{{TOPICS}} · partition key = the tenant-isolation key `tenant_id` (always) · exactly-once: {{EXACTLY_ONCE}}
*(Per the async-backbone seam bound in STACK.md.)*

## 6. Single-Primitive sweep
*Per cross-cutting concern: reused / extended / violated-needs-discussion. Flag any per-channel fork.*
{{SINGLE_PRIMITIVE_SWEEP}}

## 7. Multi-tenancy enforcement (all 4 layers)
- [ ] identity claim (gateway JWT) · [ ] service-side (`request.tenant_id == metadata`) · [ ] data-store row-level policy + analytics query-gateway · [ ] async-message envelope assert

## 8. Observability
Metrics {{METRICS}} · Logs {{LOGS}} · Traces {{TRACES}} · Alarms {{ALARMS}} · Dashboards {{DASHBOARDS}}

## 9. Test strategy
Unit {{UNIT}} · Integration {{INTEGRATION}} · Contract {{CONTRACT}} (buf breaking/Pact/tRPC+MCP diff) · E2E {{E2E}} · Load {{LOAD}} (Phase 3+) · **Real-network smoke {{SMOKE}} (mandatory for PASS)** · Mutation targets {{MUTATION}}
**Verification validity:** tests run under the real (non-bypassed) security context; every probe has a negative control (fails when protection removed); parity vs an independent source. *(pipeline `verification_validity`.)*

## 10. Security (→ Security Reviewer), compliance & region-adapter impact
- **Security notes:** {{SECURITY_NOTES}}
- **Compliance impact:** {{REGION_CONTEXT}} *(against the product's compliance regime per COMPLIANCE.md)* · **Region-adapter impact:** {{REGION_ADAPTER_IMPACT}}

## 11. Cost estimate
Daily volume {{LOAD}} · model tokens/day {{TOKENS_PER_DAY}} · money/month {{INR_PER_MONTH}} *(integer minor units + currency_code)*

## 12. Risks & alternatives
| Risk | Sev | Mitigation |  ·  | Alternative | Why rejected |
|---|---|---|---|---|---|
| {{RISK}} | {{SEV}} | {{MIT}} |  | {{ALT}} | {{ALT_WHY}} |

## 13. Tracks (Stage-3 decomposition)
Per track: `@owner` + dependencies + 2–5 min tasks with `file:line`. **Every persona/synthesis `must-fix` is a REQUIRED pass-1 item here** (kills the O7 bounce). **Every pinned version is real** (verified or "resolve latest-stable"). **Any service create/change includes its deploy-pipeline track.**
{{TRACKS}}

**Over-engineering self-check:** {{PASS_or_trims}} — plan length matches the band; no unrequested files/deps/abstractions/observability; tests target behavior at integration points.

## 14. Engineering Advisor effort-tier sign-off
{{PARADIGM_SIGNOFF_TS}}
