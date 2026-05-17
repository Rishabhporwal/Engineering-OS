# Architecture Plan — {{REQ_ID}}

> Filled by Aryan (Architect) in Stage 2.
> Validates against [schemas/architecture.schema.json](../schemas/architecture.schema.json).
> Every section must be filled. `TBD` is not allowed when this goes to Stage 3.

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | architect (Aryan) |
| **Timestamp** | {{TS}} |

---

## 1. Context

*What we're solving and why now.*

{{CONTEXT}}

---

## 2. Proposed solution

*Plain-English summary. 2–5 paragraphs.*

{{PROPOSED_SOLUTION}}

### Diagram

```mermaid
{{MERMAID_DIAGRAM}}
```

---

## 3. Paradigm

**Declared paradigm:** `{{PARADIGM}}`  *(sql / ml / haiku / sonnet)*

**Justification (≥20 words):**

{{PARADIGM_JUSTIFICATION}}

> Reminder: SQL > ML > Haiku >> Sonnet. See [skill: cost-routing-paradigms](../skills/cost-routing-paradigms/SKILL.md).

---

## 4. API design

### gRPC protos added or changed
- {{PROTO_1}}

### tRPC procedures added or changed
- {{TRPC_1}}

### MCP tools added or changed
- {{MCP_1}}

### REST endpoints added or changed
- {{REST_1}}

### Breaking changes
- {{BREAKING_1}}

### Versioning strategy
*(See [`api-versioning-strategy`](../skills/api-versioning-strategy/SKILL.md).)*

{{VERSIONING_STRATEGY}}

---

## 5. Data model changes

### Postgres
- **Tables added:** {{PG_TABLES_ADDED}}
- **Tables changed:** {{PG_TABLES_CHANGED}}
- **Indexes:** {{INDEXES}}
- **RLS policies:** {{RLS_POLICIES}}

### ClickHouse
- **Tables added:** {{CH_TABLES_ADDED}}
- **Materialized views added:** {{MV_ADDED}}

### Migration plan
*(Step-by-step; reversible; reviewed by 2 people.)*

{{MIGRATION_PLAN}}

---

## 6. Event model

- **Topics added:** {{TOPICS_ADDED}}
- **Topics changed:** {{TOPICS_CHANGED}}
- **Partition key:** `workspace_id` (always)
- **Exactly-once strategy:** {{EXACTLY_ONCE_STRATEGY}}

---

## 7. Single-Primitive sweep

> Did this introduce any per-channel forks? Check each cross-cutting concern.

| Primitive | Status |
|-----------|--------|
| Audience Builder | {{AUDIENCE_BUILDER_STATUS}} |
| Consent | {{CONSENT_STATUS}} |
| Decision Log | {{DECISION_LOG_STATUS}} |
| Notifications | {{NOTIFICATIONS_STATUS}} |
| Attribution | {{ATTRIBUTION_STATUS}} |
| Identity | {{IDENTITY_STATUS}} |

*(reused / extended / violated-needs-discussion)*

---

## 8. Multi-tenancy enforcement (4 layers)

- [ ] **JWT** — claim validation in api-gateway
- [ ] **Service-side** — `request.workspace_id == metadata.workspace_id`
- [ ] **DB RLS** — Postgres + ClickHouse query gateway
- [ ] **Kafka envelope** — consumer asserts `workspace_id`

---

## 9. Observability plan

| Pillar | Items |
|--------|-------|
| **Metrics** | {{METRICS}} |
| **Logs** | {{LOGS}} |
| **Traces** | {{TRACES}} |
| **Alarms** | {{ALARMS}} |
| **Dashboards** | {{DASHBOARDS}} |

---

## 10. Test strategy

| Layer | Plan |
|-------|------|
| **Unit** | {{TEST_UNIT}} |
| **Integration** | {{TEST_INTEGRATION}} |
| **Contract** | {{TEST_CONTRACT}}  *(`buf breaking`, Pact, tRPC schema diff, MCP schema diff)* |
| **E2E (web)** | {{TEST_E2E_WEB}}  *(Cypress)* |
| **E2E (mobile)** | {{TEST_E2E_MOBILE}}  *(Detox)* |
| **Load** | {{TEST_LOAD}}  *(k6 — Phase 3+)* |
| **Real-network smoke** | {{TEST_SMOKE}}  *(mandatory for PASS)* |
| **Mutation testing targets** | {{TEST_MUTATION_TARGETS}} |

---

## 11. Security considerations (forwarded to Shreya)

{{SECURITY_NOTES}}

---

## 12. India context

{{INDIA_CONTEXT}}

---

## 13. Region adapter impact

{{REGION_ADAPTER_IMPACT}}

---

## 14. Cost estimate

| Item | Value |
|------|-------|
| **Expected daily volume** | {{ASSUMED_LOAD}} |
| **LLM tokens / day** | {{TOKENS_PER_DAY}} |
| **₹ / month at expected load** | {{INR_PER_MONTH}} |

---

## 15. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| {{RISK_1}} | {{RISK_1_SEV}} | {{RISK_1_MIT}} |
| {{RISK_2}} | {{RISK_2_SEV}} | {{RISK_2_MIT}} |

---

## 16. Alternatives considered (≥1)

| Alternative | Why rejected |
|-------------|--------------|
| {{ALT_1}} | {{ALT_1_WHY}} |
| {{ALT_2}} | {{ALT_2_WHY}} |

---

## 17. Tracks (work decomposition for Stage 3)

### Track 1 — {{TRACK_1_ID}}  *(owner: @{{TRACK_1_OWNER}})*

Dependencies: {{TRACK_1_DEPS}}

Tasks (2–5 min each, per [`writing-plans`](../skills/writing-plans/SKILL.md) discipline):
1. {{TASK_1_1}}
2. {{TASK_1_2}}
3. {{TASK_1_3}}

### Track 2 — {{TRACK_2_ID}}  *(owner: @{{TRACK_2_OWNER}})*

Dependencies: {{TRACK_2_DEPS}}

Tasks:
1. {{TASK_2_1}}
2. {{TASK_2_2}}

*(Add more tracks as needed.)*

---

## 18. CTO Advisor paradigm sign-off

> One-line confirmation from CTO Advisor that the paradigm choice is acceptable. Recorded in `cto-advisor.journal.md`.

**Confirmed by CTO Advisor:** {{PARADIGM_SIGNOFF_TS}}
