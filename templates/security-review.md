# Security Review — {{REQ_ID}}

> Filled by Shreya in Stage 4. **VETO authority** on CRITICAL/HIGH and India compliance.
> Validates against [schemas/security-review.schema.json](../schemas/security-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | security-reviewer (Shreya) |
| **Timestamp** | {{TS}} |
| **Verdict** | **{{VERDICT}}**  *(PASS / BOUNCE)* |

---

## Gate checks

| Gate | Status | Notes |
|------|:------:|-------|
| No CRITICAL findings | {{NO_CRITICAL}} | |
| No HIGH findings | {{NO_HIGH}} | |
| No India compliance violation | {{NO_INDIA_VIOLATION}} | DLT / NCPR / DND / calling hours / recording consent |
| Every mutation endpoint guarded (`requireRole` + `requireWorkspaceMember` + Zod + `workspace_id` assertion) | {{MUTATION_GUARDED}} | |
| Every new MCP tool tenant-checked + Decision Log middleware + auth scope | {{MCP_TENANT_CHECKED}} | |
| Every new connector: OAuth AES-256-GCM + webhook signature + per-brand KMS key | {{CONNECTORS_TOKEN_ENCRYPTED}} | |
| PII not in logs (sampled log lines reviewed) | {{PII_NOT_IN_LOGS}} | |

---

## Findings

> Each finding = severity + category + evidence + remediation + responsible persona + bounce target.

### Finding 1 — {{F1_TITLE}}
- **Severity:** {{F1_SEVERITY}}
- **Category:** {{F1_CATEGORY}}  *(see schema for valid categories)*
- **Evidence:**
  ```
  {{F1_EVIDENCE}}
  ```
- **Recommended remediation:** {{F1_REMEDIATION}}
- **Responsible persona:** @{{F1_OWNER}}
- **Bounce target stage:** {{F1_BOUNCE_STAGE}}

### Finding 2 — {{F2_TITLE}}
- **Severity:** {{F2_SEVERITY}}
- **Category:** {{F2_CATEGORY}}
- **Evidence:**
  ```
  {{F2_EVIDENCE}}
  ```
- **Recommended remediation:** {{F2_REMEDIATION}}
- **Responsible persona:** @{{F2_OWNER}}
- **Bounce target stage:** {{F2_BOUNCE_STAGE}}

*(Add more findings as needed.)*

---

## Scan results

| Tool | Result |
|------|--------|
| `pnpm audit` | {{PNPM_AUDIT}} |
| Snyk | {{SNYK}} |
| Bandit (Python) | {{BANDIT}} |
| `safety check` (Python) | {{SAFETY}} |
| `pip-audit` | {{PIP_AUDIT}} |
| Trivy (image + filesystem) | {{TRIVY}} |
| OWASP Dependency-Check | {{OWASP_DC}} |

---

## India compliance checks (P0)

| Check | Status | Evidence |
|-------|:------:|----------|
| Calling hours hard-coded 09:00–21:00 IST at queue level | {{CALLING_HOURS}} | |
| Two-layer DND block (brand opt-out + TRAI NCPR) | {{DND_TWO_LAYER}} | |
| AI call disclosure prompt present | {{AI_DISCLOSURE}} | |
| Recording consent prompt present + decline path verified | {{RECORDING_CONSENT}} | |
| DLT template registration check enforced | {{DLT_CHECK}} | |
| 48h per-customer frequency cap enforced | {{FREQ_CAP}} | |

> If any India compliance check is RED, this is a **P0 bounce** and a Founder page.

---

## Re-review *(if this is a re-review after a fix)*

| Field | Value |
|-------|-------|
| **Original bounce ts** | {{ORIG_BOUNCE_TS}} |
| **Re-review ts** | {{REREVIEW_TS}} |
| **Original findings re-checked** | {{REREVIEW_NOTES}} |

---

## Handoff

- **If PASS:** Tanvi (Stage 5).
- **If BOUNCE:** {{BOUNCE_TARGET_PERSONA}} (Stage 3).
