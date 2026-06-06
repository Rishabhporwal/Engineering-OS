# Developer Report — {{TRACK_ID}}

> Filled by the Backend / Frontend-Web / Mobile / AI-ML Engineer in Stage 3 when their in-lane Definition of Done is green.
> Validates against [schemas/development-report.schema.json](../schemas/development-report.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Track** | `{{TRACK_ID}}` |
| **Actor** | {{ACTOR_PERSONA}}  *(backend-developer / frontend-web-developer / mobile-developer / intelligence-engineer)* |
| **Timestamp** | {{TS}} |
| **Effort tier** | `{{PARADIGM}}`  *(deterministic / statistical-ml / small-model / large-model — must match plan or justify deviation)* |
| **Handoff signal** | **{{HANDOFF_SIGNAL}}**  *(READY-FOR-SECURITY / READY-FOR-QA / BLOCKED / BOUNCE-TO-ARCHITECT)* |

---

## Skills loaded

- `{{SKILL_1}}`
- `{{SKILL_2}}`
- `{{SKILL_3}}`

---

## Decisions made (within authority)

- {{DECISION_1}}
- {{DECISION_2}}

---

## Files touched

| Path | Kind | +Lines | −Lines |
|------|------|--------|--------|
| {{PATH_1}} | {{KIND_1}} | {{LA_1}} | {{LR_1}} |
| {{PATH_2}} | {{KIND_2}} | {{LA_2}} | {{LR_2}} |

---

## Tests added

| Category | Count |
|----------|------:|
| Unit | {{UNIT_COUNT}} |
| Integration | {{INTEGRATION_COUNT}} |
| Contract | {{CONTRACT_COUNT}} |
| E2E | {{E2E_COUNT}} |
| **Coverage on new code** | {{COVERAGE_PCT}}% |

---

## Definition of Done — in-lane self-check

> Each builder ticks the items relevant to their lane. Composite DoD (whole change) is gate-checked by QA in Stage 5.

### Universal
- [ ] Effort-tier declaration on every new code path
- [ ] Per-feature model token budget set (if any model involved)
- [ ] Idempotency keys cached for all write operations
- [ ] Input-validation schemas on every API input; server-side re-validation
- [ ] Timestamps explicit (UTC, or the product's declared timezone)
- [ ] `tenant_id` assertion in every service handler
- [ ] `requireRole(...)` on every mutation endpoint
- [ ] Custom metrics + error-monitoring instrumentation present

### Lane-specific (check the ones that apply)

**Backend Engineer:**
- [ ] Cursor pagination on any new list endpoint (no offset)
- [ ] No sequential DB queries in a layout (batch/parallelize)
- [ ] Connection-pooler-safe patterns

**Frontend/Web Engineer:**
- [ ] Server-rendered by default where the framework supports it
- [ ] Perf run + Core Web Vitals targets met (LCP < 2.0s, INP < 200ms, CLS < 0.1 — per the Product Canon perf budget)
- [ ] Locale-aware number/format applied where relevant (per the RegionAdapter seam)
- [ ] Raw HTML injection only via a sanitizer

**Mobile Engineer:**
- [ ] Secure on-device token storage
- [ ] Offline path tested
- [ ] OTA vs native bump decision documented

**AI/ML Engineer:**
- [ ] Prompt caching applied where possible
- [ ] Tool-decorator + audit-log middleware on any new agent/tool surface
- [ ] Tick/scheduled-run simulation passes locally (if applicable)
- [ ] Per-tenant token cap honored (soft 80% / hard 100%)

---

## Open questions

- {{OPEN_QUESTION_1}}

---

## Verification

> Every "done" claim must have a command + actual output. No "should work."

### Verification 1
- **Command:** `{{CMD_1}}`
- **Expected:** {{EXPECTED_1}}
- **Actual output (snippet):**
  ```
  {{ACTUAL_OUTPUT_1}}
  ```
- **Passed:** {{PASSED_1}}

### Verification 2
- **Command:** `{{CMD_2}}`
- **Expected:** {{EXPECTED_2}}
- **Actual output (snippet):**
  ```
  {{ACTUAL_OUTPUT_2}}
  ```
- **Passed:** {{PASSED_2}}

### Real-network smoke (mandatory for PASS)
- **Command:** `{{SMOKE_CMD}}`
- **Actual output (snippet):**
  ```
  {{SMOKE_OUTPUT}}
  ```
- **Passed:** {{SMOKE_PASSED}}

---

## Blocker (if HANDOFF_SIGNAL = BLOCKED)

{{BLOCKER_DETAIL}}

---

## Handoff note

> Sentence to the next stage owner. What they should know.

{{HANDOFF_NOTE}}
