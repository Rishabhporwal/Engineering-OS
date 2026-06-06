# QA Review — {{REQ_ID}}

> Filled by the QA Engineer in Stage 5. **VETO** on missing real-network smoke or metric registry parity.
> Validates against [schemas/qa-review.schema.json](../schemas/qa-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | qa-agent |
| **Timestamp** | {{TS}} |
| **Verdict** | **{{VERDICT}}**  *(PASS / FAIL / NEEDS-MORE-INFO)* |

---

## Gate checks

| Gate | Status |
|------|:------:|
| Coverage ≥70% on new code | {{COVERAGE_OK}} |
| **Real-network smoke** output captured | {{SMOKE_OK}} |
| Contract tests present where contracts changed | {{CONTRACT_OK}} |
| Cross-runtime metric parity (single-source registry, every runtime) | {{PARITY_OK}} |
| Operational-readiness checklist green | {{OPS_READINESS_OK}} |
| Mutation tests on high-stakes paths (metric registry, compliance engine, audit log) | {{MUTATION_OK}} |
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
> Use the contract-testing tools bound per seam in STACK.md (examples below).
- **Command:** `{{CONTRACT_BREAKING_CMD}}` *(RPC-schema breaking check, e.g. `buf breaking`)*
- **Output:** {{BUF_OUTPUT}}
- **Consumer-driven contract (service-to-service):** {{PACT_OUTPUT}}
- **Typed-procedure schema diff:** {{TRPC_DIFF}}
- **Tool-surface schema diff:** {{MCP_DIFF}}

### Mutation tests
> Per the mutation-testing tool bound per runtime in STACK.md (examples below).
- **Primary runtime:** {{STRYKER_OUTPUT}}
- **Secondary runtime:** {{MUTMUT_OUTPUT}}

---

## Operational-readiness checklist

| Item | Status | Evidence |
|------|:------:|----------|
| Root handler responds | {{ROOT_HANDLER}} | `GET /` returns valid response |
| Health endpoint responds | {{HEALTH}} | `GET /health` + `GET /health/ready` |
| Port selection correct (no default-port collision) | {{PORT}} | |
| Env var validation present (fails fast on missing) | {{ENV_VARS}} | |
| Native deps build cleanly (package-manager gotchas) | {{NATIVE_DEPS}} | |

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

## Skipped-gates re-verified

> If any upstream gate was SKIPPED (e.g. a Stage 4 security fast-pass), re-run a minimal version of it here. Leave empty ONLY if nothing upstream was skipped. (Per quality-gates W13 — QA re-runs skipped gates.)

| Skipped gate | Re-run command | Output snippet | Verdict |
|---|---|---|---|
| {{SKIPPED_GATE_OR_NONE}} | `{{RERUN_CMD}}` | {{RERUN_OUTPUT}} | {{RERUN_VERDICT}} |

---

## Self-review (before handoff)

> Walk this before invoking Stage 6. Per [system-prompt §Plan-first + Self-review](../prompts/system-prompt.md).

- [ ] Every gate verdict + finding above is backed by captured command output (no "looks fine")
- [ ] Real-network smoke actually ran on a real port (not in-process inject)
- [ ] Metric registry parity check run (if any metric touched)
- [ ] Any upstream SKIPPED gate re-verified in the section above
- [ ] In-lane DoD walked line-by-line; each PASS/FAIL has evidence

---

## Handoff

- **If PASS:** CTO Advisor (Stage 6).
- **If FAIL:** {{FAIL_TARGET_PERSONA}} (Stage 3).
- **If NEEDS-MORE-INFO:** specify what's needed: {{INFO_NEEDED}}
