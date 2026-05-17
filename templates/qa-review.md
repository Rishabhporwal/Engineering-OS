# QA Review — {{REQ_ID}}

> Filled by Tanvi in Stage 5. **VETO** on missing real-network smoke or metric registry parity.
> Validates against [schemas/qa-review.schema.json](../schemas/qa-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | qa-agent (Tanvi) |
| **Timestamp** | {{TS}} |
| **Verdict** | **{{VERDICT}}**  *(PASS / FAIL / NEEDS-MORE-INFO)* |

---

## Gate checks

| Gate | Status |
|------|:------:|
| Coverage ≥70% on new code | {{COVERAGE_OK}} |
| **Real-network smoke** output captured | {{SMOKE_OK}} |
| Contract tests present where contracts changed | {{CONTRACT_OK}} |
| Metric registry parity (TS ↔ Python) | {{PARITY_OK}} |
| Operational-readiness checklist green | {{OPS_READINESS_OK}} |
| Mutation tests on high-stakes paths (metric registry, India compliance engine, Decision Log) | {{MUTATION_OK}} |
| No flaky tests introduced (3× re-run confirms) | {{FLAKY_OK}} |

---

## Test runs

> Every run: category + command + expected + actual snippet + passed.

### Test 1
- **Category:** {{T1_CAT}}
- **Command:** `{{T1_CMD}}`
- **Expected:** {{T1_EXPECTED}}
- **Actual output (snippet):**
  ```
  {{T1_OUTPUT}}
  ```
- **Passed:** {{T1_PASSED}}

### Test 2
- **Category:** {{T2_CAT}}
- **Command:** `{{T2_CMD}}`
- **Expected:** {{T2_EXPECTED}}
- **Actual output (snippet):**
  ```
  {{T2_OUTPUT}}
  ```
- **Passed:** {{T2_PASSED}}

### Real-network smoke
- **Command:** `{{SMOKE_CMD}}`
- **Expected:** {{SMOKE_EXPECTED}}
- **Actual output (snippet):**
  ```
  {{SMOKE_OUTPUT}}
  ```
- **Passed:** {{SMOKE_PASSED}}

### Metric registry parity check
- **Command:** `{{PARITY_CMD}}`
- **Actual output (snippet):**
  ```
  {{PARITY_OUTPUT}}
  ```
- **Passed:** {{PARITY_PASSED}}

### Contract tests
- **Command:** `buf breaking proto/ --against '.git#branch=main'`
- **Output:** {{BUF_OUTPUT}}
- **Pact (service-to-service):** {{PACT_OUTPUT}}
- **tRPC schema diff:** {{TRPC_DIFF}}
- **MCP schema diff:** {{MCP_DIFF}}

### Mutation tests
- **TS (Stryker):** {{STRYKER_OUTPUT}}
- **Python (mutmut):** {{MUTMUT_OUTPUT}}

---

## Operational-readiness checklist

| Item | Status | Evidence |
|------|:------:|----------|
| Root handler responds | {{ROOT_HANDLER}} | `GET /` returns valid response |
| Health endpoint responds | {{HEALTH}} | `GET /health` + `GET /health/ready` |
| Port selection correct (no 3000 collision) | {{PORT}} | |
| Env var validation present (fails fast on missing) | {{ENV_VARS}} | |
| Native deps build cleanly (pnpm 11 gotchas) | {{NATIVE_DEPS}} | |

*(From [`operational-readiness`](../skills/operational-readiness/SKILL.md).)*

---

## Findings

### Finding 1 — {{QA_F1_TITLE}}
- **Severity:** {{QA_F1_SEV}}  *(block / high / medium / low)*
- **Evidence:**
  ```
  {{QA_F1_EVIDENCE}}
  ```
- **Responsible persona:** @{{QA_F1_OWNER}}

*(Add more as needed.)*

---

## Handoff

- **If PASS:** CTO Advisor (Stage 6).
- **If FAIL:** {{FAIL_TARGET_PERSONA}} (Stage 3).
- **If NEEDS-MORE-INFO:** specify what's needed: {{INFO_NEEDED}}
