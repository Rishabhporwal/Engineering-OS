---
name: compliance-attestation
description: SOC 2 / ISO 27001 evidence-as-you-build + PCI SAQ-A scope boundary + WORM/hash-chain audit immutability, and how to PROVE integrity to an auditor. Owner: Shreya.
---

# Compliance Attestation — prove it to an auditor

Three jobs that share an auditor: map Brain's existing controls to SOC 2 TSC and collect evidence continuously (not reconstructed under deal pressure); keep PCI scope empty (SAQ-A by design); and make the audit trail provably tamper-evident. The data-privacy/telecom regime itself is owned by `compliance-engine` — reference it, don't restate it. Owned by **Shreya** (+ **Vikram** on the data layer for immutability). VETO surface.

---

## Part 1 — SOC 2 readiness (map what exists, evidence as-you-build)

Targets **Phase 4** when enterprise demand arrives. The trap is treating it as a Phase-4 *project* — scrambling to reconstruct 12 months of evidence. Brain already does most of the controls; map them to the Trust Service Criteria NOW and ensure each **emits its evidence artifact continuously**.

> **The one rule:** every control in the stack is mapped to a TSC point and emits a dated, retrievable evidence artifact — collected as-you-build, never reconstructed.

Vendor: **Sprinto** (India-friendly), 12-month Type 2 window, ~$30–60K/yr. **Security (Common Criteria) is mandatory**; the other four TSC are opt-in by customer demand.

### Controls Brain ALREADY has → TSC mapping + evidence
| Control (where) | TSC | Evidence artifact |
|---|---|---|
| RBAC — 5 roles, JWT+RLS+`requireRole` (`auth-and-access`) | CC6.1, CC6.3 | role matrix, RLS policies, JWT claim schema, `requireRole` tests |
| Multi-tenancy — 4-layer `workspace_id` (`multi-tenancy-isolation`) | CC6.1, C1.1 | cross-tenant denial tests, query-gateway rejection logs |
| Audit log + Decision Log — append-only + tamper-evidence (Part 3) | CC7.2/7.3, PI1.x | `audit_log`, S3 Object Lock config, hash-chain verifier runs |
| Vuln scanning — Snyk/Trivy/Bandit/pip-audit + SBOM (`security-baseline`) | CC7.1, CC8.1 | CI scan results, SBOMs, suppression file w/ expiries |
| Change management — PR + CI gates + ArgoCD + Stage-4/5 VETO | CC8.1 | PR history, required-reviewer config, deploy logs, 8-stage record |
| Encryption — TLS1.2+, KMS envelope, SSE-KMS, at-rest (`security-baseline`) | CC6.7, C1.1 | KMS key policies, TLS/HSTS config, at-rest inventory |
| Secrets — Secrets Manager + IRSA + rotation | CC6.1, CC6.7 | config, rotation schedule, IAM/IRSA policies |
| Logging+monitoring — OpenSearch/CloudWatch/X-Ray/Sentry, redaction (`observability`) | CC7.1, CC7.2 | log schema, redaction config, monitors |
| Incident response — Sev1–4, on-call, postmortems | CC7.3/7.4/7.5 | postmortems, PagerDuty rotation, severity matrix |
| Backup + DR — PITR, snapshots, RTO/RPO, drills | A1.2, A1.3 | backup configs, DR drill records, RTO/RPO targets |
| Data residency — ap-south-1 + SCPs + test (`data-residency-enforcement`) | C1.1, P-series | SCP config, residency test runs, AWS Config drift |
| Privacy/DPDP — consent, minimization, erasure (`compliance-engine`) | P1–P8 | consent schema, erasure-job runs, DPA, sub-processor list |
| Access reviews — quarterly IAM/DB-role review | CC6.2, CC6.3 | review records, deprovisioning logs |

The headline: the Security common criteria (CC1–CC9) are largely covered today. SOC 2 is mostly *evidencing* what Brain built.

### The five TSC (for Brain)
Security (CC, mandatory — strongest area) · Availability (SLOs API 99.5%→99.95%, Brief by 07:20 IST >99.5% days + DR drills) · Confidentiality (isolation + encryption + residency) · **Processing Integrity** (metric-engine TS↔Python parity, deterministic billing/no-LLM, Decision Log create-before-display, idempotency — a strong differentiated PI story) · Privacy (DPDP/PDPL consent + minimization + erasure).

### ISO 27001 crosswalk
Same controls double as Annex A: RBAC → A.5.15/A.8.3; logging → A.8.15/A.8.16; crypto → A.8.24; vuln → A.8.8; change → A.8.32; backup → A.8.13; supplier → A.5.19–A.5.22; incident → A.5.24–A.5.28. Build evidence once, satisfy both. The ISMS (risk register, SoA, management review) is the ISO-specific add-on.

### Evidence as-you-build (the discipline, not a tool)
- **Automate the pull:** Sprinto connects to AWS/GitHub/IdP/ticketing to continuously pull config + control state — not manual uploads.
- **New controls emit evidence by default:** at design time, define the artifact + where it lands. A control with no retrievable evidence isn't audit-ready.
- **Map it the day you build it:** tag the control to its TSC point in the readiness register.

### Readiness gaps (build before/at Phase 4)
MFA mandatory for owners/admins (CC6.1) · Object Lock on audit log (CC7.2/PI1 — Part 3) · pen test (internal pre-Phase-3, external annual Phase 4) · vendor/sub-processor DPA + list before first paying brand (CC9.2) · policies (infosec/IR/access/BCP) written + acknowledged (CC1.x) · documented risk register (CC3.x) · HR onboarding/offboarding (CC1.4) · DPO appointed (P-series, Phase 3).

### Phase timing
Phase 1 internal hygiene (Privacy Policy + Terms + DPA template + security FAQ incl. SAQ-A). Phase 2 DPDP live. Phase 3 engage Sprinto, turn on continuous evidence, write policies, internal pen test, owner MFA — **start the clock so the Type 2 window accumulates.** Phase 4 SOC 2 Type 1 → Type 2; external pen test; ISO 27001 if EU/global demand appears.

---

## Part 2 — PCI scope (SAQ-A by design)

Brain is an analytics + execution OS, **not** a payment processor — it never touches a PAN. The single decision that keeps it on **SAQ-A** (~22 questions) vs SAQ-D (300+ controls, on-site assessment): *delegate all card capture to a licensed gateway via redirect/hosted fields.* Standard: **PCI-DSS v4.0.1** (v4.0 retired 31 Dec 2024).

> **The one rule:** cardholder data never enters a Brain system, server, log, database, or network segment. If a feature would require Brain to receive/transmit/store a PAN/CVV, the answer is no — route it through the gateway.

**Never stored** (canon §21.1, enforced by `compliance-engine` minimization): PAN, CVV/CVC, expiry, track data, PIN; full UPI VPA, full bank accounts, IFSC-linked details. What Brain *does* store: payment-method classification (`card|upi|cod|wallet|bnpl`), an opaque gateway transaction/order reference, settlement amounts in minor units, payment status. None is cardholder data → Brain's **CDE is empty**.

**The boundary — two compliant shapes:** *Redirect* (customer lands on the gateway's page; Brain gets a token callback; strongest isolation) and *Hosted fields/iframe* (gateway-served iframe; Brain's DOM never sees the PAN — but v4.0.1 **6.4.3** (manage payment-page scripts) + **11.6.1** (tamper detection) then apply; pure redirect avoids even those). Commerce checkouts (brand's store) and Brain's own %-GMV fee invoices both route this way; `billing.invoices` stores only `provider_invoice_id`, status, `total_minor`, `currency_code`. Recurring → gateway tokenization/mandate vault (Razorpay subscriptions / Stripe payment-method tokens), never a Brain-stored card.

**Would pull Brain into scope (all prohibited — Shreya VETO):** receiving a raw PAN/CVV in any request/webhook/form/CSV (even transiently); logging/caching a card number; storing card-on-file; proxying card data between checkout and processor; building a Brain-controlled card input form.

**Enterprise-review answer:** "Brain does not store, process, or transmit cardholder data. All capture — commerce checkouts and our own SaaS-fee billing — is delegated to PCI-DSS Level 1 providers (Razorpay, Stripe) via redirect/hosted fields. Brain ingests only opaque references, amounts, status, and a payment-method class. Our CDE is empty, so Brain validates as **SAQ-A** under v4.0.1. We can share gateway AOCs + our SAQ-A on request." Keep on file: gateway AOCs, their service-provider registry entries, Brain's completed SAQ-A.

---

## Part 3 — Audit-log immutability (tamper-evidence)

Two ledgers carry Brain's integrity story: `audit_log` (who did what) and `ai.decision_log` (the moat). "Append-only by convention" ≠ "provably unaltered." An auditor will ask: *can a Brain engineer with DB access silently rewrite a decision or delete an audit row, and would anyone know?* Make the answer demonstrably **no**. Decision Log write-availability SLO **>99.99%**.

> **The one rule:** the audit trail + Decision Log are append-only and tamper-evident — any alteration is physically prevented (WORM) or cryptographically detectable (hash chain), provable on demand.

**1. WORM — S3 Object Lock COMPLIANCE mode.** Audit mirror + Decision Log topic archive land in buckets with Object Lock COMPLIANCE + retention. Under compliance mode **no one — not root, not an admin — can delete/overwrite before retention expires.** (Governance mode is bypassable via `BypassGovernanceRetention` — use Compliance for a legal record.) Retention = 7y for `audit_log`; Decision Log archive effectively permanent (MSK tiered storage → S3). Versioning ON + MFA-delete + SSE-KMS.
```
audit_log (PG hot) ──Firehose──▶ s3://brain-audit/ (Object Lock COMPLIANCE, 7y)
ai.decision_log ──intelligence.decision.logged.v1──▶ MSK tiered storage ▶ s3 archive (infinite)
```

**2. Append-only DB enforcement.** Revoke `DELETE` from every service role (only the time-boxed retention job deletes, past the legal window — and erasure tombstones PII without deleting the audit row). `audit_log` is insert-only (revoke `UPDATE`). `ai.decision_log` allows **status-transition UPDATEs only**: a `BEFORE UPDATE` trigger rejects changes to immutable columns (`id`, `workspace_id`, `created_at`, `input_snapshot`, `proposed_action`, `agent_name`) and validates the transition is legal (`executed→reversed` ok; `executed→proposed` rejected). Delete-then-reinsert blocked (breaks immutable `id` + the `condition_outcome` FK).

**3. Hash-chaining.** Each row carries a hash of its own canonical content + the prior row's hash, per `workspace_id` partition. Altering any historical row breaks every subsequent hash.
```
row_n.row_hash = SHA256( canonical(row_n.payload) || row_{n-1}.row_hash )
```
Store `row_hash` + `prev_hash`; genesis chains from a constant seed per `(workspace_id, ledger)`. A nightly **integrity verifier** (paradigm 1 — SQL/CPU, no LLM) re-walks each chain against periodic **anchor hashes** written to the Object-Lock bucket (catches even a full-table rewrite vs the WORM anchor). Mismatch → Sentry P1 + Shreya page. For the Decision Log, the chain covers the row's terminal snapshot at each transition — the *history of transitions* (proposed→approved→executed→reversed) is itself tamper-evident.

**Why append-then-update still must be tamper-evident:** the Decision Log's `status` legitimately moves through transitions and nightly jobs backfill `outcome_7d`/`outcome_30d` — that mutability is the point, which is exactly why it needs proof. Legal updates (transition, outcome backfill, user_response) are chained; illegal ones (rewriting `input_snapshot`, editing `proposed_action`, deleting a rejected rec) are blocked by the trigger and would break the chain if forced via direct SQL. This is what lets Brain claim the moat is real: a competitor can't fake their condition→outcome history because Brain's own engineers structurally can't either.

### Proving integrity to an auditor
| Question | Evidence |
|---|---|
| "Can audit records be deleted/altered?" | Object Lock COMPLIANCE config + retention; revoked DELETE/UPDATE grants |
| "How do you detect tampering?" | hash-chain schema + nightly verifier run logs + WORM anchor hashes |
| "Show an integrity check passing" | verifier output: every chain walks clean to its anchor for the period |
| "Retention meets policy?" | Object Lock 7y + retention-job schedule |
| "Erasure vs audit retention?" | PII tombstoned, PII-free audit row retained — documented + tested |
Maps to SOC 2 CC7.x, PI1.x, C1.x and ISO A.8.15/A.8.16.

---

## Anti-patterns (Shreya VETO)
- SOC 2 as a Phase-4 project; a control with no evidence artifact defined; a new control that doesn't emit evidence by default; asserting a TSC with a known gap unmapped; building SOC 2 + ISO evidence separately instead of crosswalking once.
- Any field/column/log/event that could carry a PAN/CVV/full UPI/bank account; a Brain-controlled card form; storing card-on-file; asserting "we're SAQ-A" with no SAQ on file.
- `DELETE` granted on a ledger to a service role; delete-then-reinsert on a status change; editing an immutable Decision Log column; Object Lock in Governance mode for a legal record; a hash chain with no verifier/anchor; erasure that deletes the audit row.

## Verify
- Readiness register maps every shipped control → TSC point + named dated retrievable artifact; pick any control → evidence pullable today.
- Grep schema + `protos/events/` + log redaction set: no `card_number`/`pan`/`cvv`/`vpa`/`account_number` exists or is loggable; security FAQ has the SAQ-A statement + gateway AOCs.
- `DELETE FROM audit_log` / `UPDATE ai.decision_log SET input_snapshot=…` as a service role → rejected; delete an audit object before retention → denied; tamper a staging row → verifier flags the broken chain vs the WORM anchor; an erasure clears PII everywhere but keeps the audit row + clean chain.

## References
`canon/TECH/09` §6 (audit_log + S3 mirror, 7y), §9 (compliance roadmap, Sprinto), §13–15 (IR/DR/access reviews) · `canon/TECH/16_compliance_engine.md` §4.1/4.4/4.5/7/8 · `canon/technical-requirements.md` §21.1 (never-store) · `canon/TECH/15` (billing on licensed rails) · `compliance-engine` (the privacy/telecom regime) · `security-baseline` (CC-mapped posture, scanners, SBOM) · `decision-log` (append-then-update lifecycle) · `data-residency-enforcement` · `incident-response` · `billing-metering`.
