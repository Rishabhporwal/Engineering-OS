# Security Review — {{REQ_ID}}

> Filled by the Security Reviewer in Stage 4. **VETO authority** on CRITICAL/HIGH and the product's compliance regime.
> Validates against [schemas/security-review.schema.json](../schemas/security-review.schema.json).

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | security-reviewer |
| **Timestamp** | {{TS}} |
| **Verdict** | **{{VERDICT}}**  *(PASS / BOUNCE — a Security Reviewer BOUNCE is a VETO; nothing advances past it)* |

---

## Change-class scope (fast-path)

Declare the change's **surface class first** — it determines which gate sections apply. You must still scan the code, but a section for a surface the change genuinely does not touch is legitimately **N/A — out of scope** with this declaration as the justification. **Do NOT fabricate findings for absent surfaces, and do NOT N/A a surface the change actually touches.**

| Surface | Touched? | If "No" → these sections are N/A |
|---|:---:|---|
| Network / API (any RPC / typed-procedure / tool endpoint, any mutation) | {{TOUCH_API}} | "mutation endpoint guarded", "tool surface" gates |
| Outbound channel (any user-facing channel — call / message / email / audience) | {{TOUCH_OUTBOUND}} | the entire **compliance checks (P0)** section |
| Connector / external credential | {{TOUCH_CONNECTOR}} | "connector OAuth / secrets" gate |
| Customer PII (any personal data the Canon classifies as PII) | {{TOUCH_PII}} | PII-in-logs gate + data-protection data-flow review |
| Money movement (billing / pricing / refund / payout) | {{TOUCH_MONEY}} | money-handling review |
| Agent-emitted action / auto-execute | {{TOUCH_AGENT_ACTION}} | agentic-actions-auditor gate |

**ALWAYS-ON (run regardless of class — the VETO still holds on anything these find):** dependency / vuln scans · secrets grep on the staged diff · supply-chain (every new dep justified) · input validation on any new boundary · and for ANY money-*derived* code, the **minor-units / no-float / no-model-produced-numbers** check.

> **Library / registry-only fast-path:** if every surface above is "No" (a pure library / metric / util change — no network/auth/PII/outbound/connector/money-movement surface), say so here, run the ALWAYS-ON checks, and mark the surface-specific gates + the compliance section **N/A — out of scope (library-only)**. This is a *scoping* statement, not a gate skip.

---

## Gate checks

| Gate | Status | Notes |
|------|:------:|-------|
| No CRITICAL findings | {{NO_CRITICAL}} | |
| No HIGH findings | {{NO_HIGH}} | |
| No compliance-regime violation | {{NO_COMPLIANCE_VIOLATION}} | against the product's compliance regime (per COMPLIANCE.md) |
| Every mutation endpoint guarded (`requireRole` + tenant-membership check + input-validation schema + `tenant_id` assertion) | {{MUTATION_GUARDED}} | |
| Every new tool surface / agent-emitted action audited (blast radius classified, human gate on irreversible/financial, idempotency, arg validation) | {{ACTIONS_AUDITED}} | per [`agentic-safety`](../skills/agentic-safety/SKILL.md) |
| Every new tool surface tenant-checked + audit-log middleware + auth scope | {{MCP_TENANT_CHECKED}} | |
| Every new connector: OAuth with authenticated encryption + webhook signature + per-tenant managed key | {{CONNECTORS_TOKEN_ENCRYPTED}} | |
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

> The concrete scanners are bound per runtime in the Product Canon's STACK.md. Examples below; fill the rows that apply, mark the rest `n/a`.

| Tool | Result |
|------|--------|
| Dependency audit (package manager) | {{PNPM_AUDIT}} |
| SCA / vuln scanner | {{SNYK}} |
| Static analysis (SAST) | {{BANDIT}} |
| Dependency safety check | {{SAFETY}} |
| Dependency audit (secondary runtime) | {{PIP_AUDIT}} |
| Image + filesystem scanner | {{TRIVY}} |
| OWASP Dependency-Check | {{OWASP_DC}} |

---

## Compliance checks (P0)

> Drawn from the product's compliance regime (per COMPLIANCE.md). The rows below are *examples* of channel/consent/retention controls; replace with the specific controls the Canon declares, and mark any that don't apply `n/a`.

| Check | Status | Evidence |
|-------|:------:|----------|
| Channel send-window enforced at queue level (per COMPLIANCE.md) | {{CALLING_HOURS}} | |
| Opt-out / do-not-contact block enforced (regime + per-tenant) | {{CHANNEL_OPTOUT_CHECK}} | |
| AI/automated-contact disclosure present (if required) | {{AI_DISCLOSURE}} | |
| Recording/processing consent present + decline path verified | {{RECORDING_CONSENT}} | |
| Channel template/registration check enforced (if required) | {{CHANNEL_TEMPLATE_CHECK}} | |
| Per-recipient frequency cap enforced | {{FREQ_CAP}} | |

> If any compliance check is RED, this is a **P0 bounce** and a Stakeholder page.

---

## Re-review *(if this is a re-review after a fix)*

| Field | Value |
|-------|-------|
| **Original bounce ts** | {{ORIG_BOUNCE_TS}} |
| **Re-review ts** | {{REREVIEW_TS}} |
| **Original findings re-checked** | {{REREVIEW_NOTES}} |

---

## Self-review (before handoff)

> Walk this before invoking Stage 5. Per [system-prompt §Plan-first + Self-review](../prompts/system-prompt.md).

- [ ] Every finding has a file path + line and a verification snippet (not "looks unsafe")
- [ ] Secrets grep run on the staged diff; result captured
- [ ] Every CRITICAL/HIGH has an explicit bounce target (no silent pass)
- [ ] Scan output captured for each tool above (not assumed clean)
- [ ] If any agent-emitted action was added, the agentic-actions-auditor classification is recorded

---

## Handoff

- **If PASS:** QA Engineer (Stage 5).
- **If BOUNCE:** {{BOUNCE_TARGET_PERSONA}} (Stage 3).
