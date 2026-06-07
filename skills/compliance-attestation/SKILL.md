---
name: compliance-attestation
description: SOC 2 / ISO 27001 evidence-as-you-build + PCI SAQ-A scope boundary + WORM/hash-chain audit immutability, and how to PROVE integrity to an auditor. Owner: Security Reviewer.
---

# Compliance Attestation — prove it to an auditor

Three jobs that share an auditor: map the product's existing controls to SOC 2 TSC and collect evidence continuously (not reconstructed under deal pressure); keep PCI scope empty (SAQ-A by design); and make the audit trail provably tamper-evident. The product's own data-protection / channel regime is owned by `compliance-engine` (and declared in `COMPLIANCE.md`) — reference it, don't restate it. Owned by the **Security Reviewer** (+ the **Backend Engineer** on the data layer for immutability). VETO surface.

---

## Part 1 — SOC 2 readiness (map what exists, evidence as-you-build)

Targets a later phase, when enterprise demand arrives. The trap is treating it as a project — scrambling to reconstruct 12 months of evidence. A well-built product already does most of the controls; map them to the Trust Service Criteria NOW and ensure each **emits its evidence artifact continuously**.

> **The one rule:** every control in the stack is mapped to a TSC point and emits a dated, retrievable evidence artifact — collected as-you-build, never reconstructed.

Vendor: a continuous-compliance platform (e.g. Sprinto/Vanta/Drata), 12-month Type 2 window. **Security (Common Criteria) is mandatory**; the other four TSC are opt-in by customer demand.

### Controls the product ALREADY has → TSC mapping + evidence
| Control (where) | TSC | Evidence artifact |
|---|---|---|
| RBAC — level-ordered roles, JWT+RLS+`requireRole` (`auth-and-access`) | CC6.1, CC6.3 | role matrix, RLS policies, JWT claim schema, `requireRole` tests |
| Multi-tenancy — tenant key at every layer (`multi-tenancy-isolation`) | CC6.1, C1.1 | cross-tenant denial tests, query-gateway rejection logs |
| Audit log — append-only + tamper-evidence (Part 3) | CC7.2/7.3, PI1.x | `audit_log`, object-lock config, hash-chain verifier runs |
| Vuln scanning — SCA/container/SAST scanners + SBOM (`security-baseline`) | CC7.1, CC8.1 | CI scan results, SBOMs, suppression file w/ expiries |
| Change management — PR + CI gates + GitOps + the VETO gates | CC8.1 | PR history, required-reviewer config, deploy logs, pipeline-stage record |
| Encryption — TLS1.2+, KMS envelope, at-rest (`security-baseline`) | CC6.7, C1.1 | KMS key policies, TLS/HSTS config, at-rest inventory |
| Secrets — a secrets manager + workload identity + rotation | CC6.1, CC6.7 | config, rotation schedule, IAM policies |
| Logging+monitoring — the observability spine + redaction (`observability`) | CC7.1, CC7.2 | log schema, redaction config, monitors |
| Incident response — severity ladder, on-call, postmortems | CC7.3/7.4/7.5 | postmortems, on-call rotation, severity matrix |
| Backup + DR — PITR, snapshots, RTO/RPO, drills | A1.2, A1.3 | backup configs, DR drill records, RTO/RPO targets |
| Data residency — in-region + guardrails + test | C1.1, P-series | residency-policy config, residency test runs, drift detection |
| Privacy — consent, minimization, erasure (`compliance-engine`) | P1–P8 | consent schema, erasure-job runs, DPA, sub-processor list |
| Access reviews — quarterly IAM/DB-role review | CC6.2, CC6.3 | review records, deprovisioning logs |

The headline: the Security common criteria (CC1–CC9) are largely covered by a well-engineered product today. SOC 2 is mostly *evidencing* what you built.

### The five TSC
Security (CC, mandatory — usually the strongest area) · Availability (SLOs + DR drills) · Confidentiality (isolation + encryption + residency) · **Processing Integrity** (cross-runtime metric parity, deterministic billing/no-model-invented-numbers, audit create-before-display, idempotency — a strong, differentiated PI story) · Privacy (consent + minimization + erasure, per `COMPLIANCE.md`).

### ISO 27001 crosswalk
Same controls double as Annex A: RBAC → A.5.15/A.8.3; logging → A.8.15/A.8.16; crypto → A.8.24; vuln → A.8.8; change → A.8.32; backup → A.8.13; supplier → A.5.19–A.5.22; incident → A.5.24–A.5.28. Build evidence once, satisfy both. The ISMS (risk register, SoA, management review) is the ISO-specific add-on.

### Evidence as-you-build (the discipline, not a tool)
- **Automate the pull:** the compliance platform connects to the cloud/VCS/IdP/ticketing to continuously pull config + control state — not manual uploads.
- **New controls emit evidence by default:** at design time, define the artifact + where it lands. A control with no retrievable evidence isn't audit-ready.
- **Map it the day you build it:** tag the control to its TSC point in the readiness register.

### Readiness gaps (build before/at the enterprise phase)
MFA mandatory for owners/admins (CC6.1) · object-lock on the audit log (CC7.2/PI1 — Part 3) · pen test (internal early, external annual at scale) · vendor/sub-processor DPA + list before the first paying tenant (CC9.2) · policies (infosec/IR/access/BCP) written + acknowledged (CC1.x) · documented risk register (CC3.x) · HR onboarding/offboarding (CC1.4) · a privacy owner appointed (P-series).

### Phase timing
Early: internal hygiene (Privacy Policy + Terms + DPA template + security FAQ incl. SAQ-A). Mid: the compliance regime live. Then: engage the compliance platform, turn on continuous evidence, write policies, internal pen test, owner MFA — **start the clock so the Type 2 window accumulates.** At enterprise scale: SOC 2 Type 1 → Type 2; external pen test; ISO 27001 if global demand appears.

---

## Part 2 — PCI scope (SAQ-A by design)

If the product is an analytics + execution layer, **not** a payment processor, it never touches a PAN. The single decision that keeps it on **SAQ-A** (~22 questions) vs SAQ-D (300+ controls, on-site assessment): *delegate all card capture to a licensed gateway via redirect/hosted fields.* Standard: **PCI-DSS v4.0.1** (v4.0 retired 31 Dec 2024).

> **The one rule:** cardholder data never enters any product system, server, log, database, or network segment. If a feature would require receiving/transmitting/storing a PAN/CVV, the answer is no — route it through the gateway.

**Never stored** (enforced by `compliance-engine` minimization): PAN, CVV/CVC, expiry, track data, PIN; full payment-instrument identifiers; bank-account / linked details. What the product *does* store: payment-method classification (`card|wallet|bnpl|cod|bank`), an opaque gateway transaction/order reference, settlement amounts in minor units, payment status. None is cardholder data → the **CDE is empty**.

**The boundary — two compliant shapes:** *Redirect* (customer lands on the gateway's page; the product gets a token callback; strongest isolation) and *Hosted fields/iframe* (gateway-served iframe; the product's DOM never sees the PAN — but v4.0.1 **6.4.3** (manage payment-page scripts) + **11.6.1** (tamper detection) then apply; pure redirect avoids even those). Customer checkouts and the product's own fee/invoice billing both route this way; `billing.invoices` stores only `provider_invoice_id`, status, `total_minor`, `currency_code`. Recurring → gateway tokenization/mandate vault, never a stored card.

**Would pull the product into scope (all prohibited — Security Reviewer VETO):** receiving a raw PAN/CVV in any request/webhook/form/CSV (even transiently); logging/caching a card number; storing card-on-file; proxying card data between checkout and processor; building a product-controlled card input form.

**Enterprise-review answer:** "The product does not store, process, or transmit cardholder data. All capture — customer checkouts and our own fee billing — is delegated to PCI-DSS Level 1 providers via redirect/hosted fields. We ingest only opaque references, amounts, status, and a payment-method class. Our CDE is empty, so we validate as **SAQ-A** under v4.0.1. We can share gateway AOCs + our SAQ-A on request." Keep on file: gateway AOCs, their service-provider registry entries, the completed SAQ-A.

---

## Part 3 — Audit-log immutability (tamper-evidence)

Where the Canon requires a system-of-record audit log, it carries the product's integrity story: `audit_log` (who did what) and any decision/outcome ledger. "Append-only by convention" ≠ "provably unaltered." An auditor will ask: *can an engineer with DB access silently rewrite a record or delete a row, and would anyone know?* Make the answer demonstrably **no**. Audit write-availability SLO **>99.99%**.

> **The one rule:** the audit trail is append-only and tamper-evident — any alteration is physically prevented (WORM) or cryptographically detectable (hash chain), provable on demand.

**1. WORM — object-lock COMPLIANCE mode.** The audit mirror + any ledger archive land in buckets with Object Lock COMPLIANCE + retention. Under compliance mode **no one — not root, not an admin — can delete/overwrite before retention expires.** (Governance mode is bypassable — use Compliance for a legal record.) Retention = the policy window (e.g. 7y) for `audit_log`; a decision/outcome archive effectively permanent (tiered storage → object store). Versioning ON + MFA-delete + SSE-KMS.
```
audit_log (hot) ──streaming──▶ object store (Object Lock COMPLIANCE, policy window)
decision/outcome events ──topic──▶ tiered storage ▶ object-store archive (long-lived)
```

**2. Append-only DB enforcement.** Revoke `DELETE` from every service role (only the time-boxed retention job deletes, past the legal window — and erasure tombstones PII without deleting the audit row). `audit_log` is insert-only (revoke `UPDATE`). A status-bearing ledger allows **status-transition UPDATEs only**: a `BEFORE UPDATE` trigger rejects changes to immutable columns (`id`, `tenant_id`, `created_at`, `input_snapshot`, `proposed_action`, `agent_name`) and validates the transition is legal (`executed→reversed` ok; `executed→proposed` rejected). Delete-then-reinsert blocked (breaks the immutable `id` + any outcome FK).

**3. Hash-chaining.** Each row carries a hash of its own canonical content + the prior row's hash, per tenant partition. Altering any historical row breaks every subsequent hash.
```
row_n.row_hash = SHA256( canonical(row_n.payload) || row_{n-1}.row_hash )
```
Store `row_hash` + `prev_hash`; genesis chains from a constant seed per `(tenant_id, ledger)`. A nightly **integrity verifier** (deterministic — SQL/CPU, no model) re-walks each chain against periodic **anchor hashes** written to the object-lock bucket (catches even a full-table rewrite vs the WORM anchor). Mismatch → P1 alert + page the Security Reviewer. For a status-bearing ledger, the chain covers the row's terminal snapshot at each transition — the *history of transitions* is itself tamper-evident.

**Why append-then-update still must be tamper-evident:** a status ledger legitimately moves through transitions and nightly jobs backfill outcome fields — that mutability is the point, which is exactly why it needs proof. Legal updates (transition, outcome backfill, user response) are chained; illegal ones (rewriting `input_snapshot`, editing `proposed_action`, deleting a rejected record) are blocked by the trigger and would break the chain if forced via direct SQL. This is what lets the product claim its history is real: an engineer structurally can't fake it.

### Proving integrity to an auditor
| Question | Evidence |
|---|---|
| "Can audit records be deleted/altered?" | Object Lock COMPLIANCE config + retention; revoked DELETE/UPDATE grants |
| "How do you detect tampering?" | hash-chain schema + nightly verifier run logs + WORM anchor hashes |
| "Show an integrity check passing" | verifier output: every chain walks clean to its anchor for the period |
| "Retention meets policy?" | Object Lock window + retention-job schedule |
| "Erasure vs audit retention?" | PII tombstoned, PII-free audit row retained — documented + tested |
Maps to SOC 2 CC7.x, PI1.x, C1.x and ISO A.8.15/A.8.16.

---

## Anti-patterns (Security Reviewer VETO)
- SOC 2 as a one-off project; a control with no evidence artifact defined; a new control that doesn't emit evidence by default; asserting a TSC with a known gap unmapped; building SOC 2 + ISO evidence separately instead of crosswalking once.
- Any field/column/log/event that could carry a PAN/CVV/full payment-instrument/bank account; a product-controlled card form; storing card-on-file; asserting "we're SAQ-A" with no SAQ on file.
- `DELETE` granted on a ledger to a service role; delete-then-reinsert on a status change; editing an immutable ledger column; Object Lock in Governance mode for a legal record; a hash chain with no verifier/anchor; erasure that deletes the audit row.

## Verify
- Readiness register maps every shipped control → TSC point + a named dated retrievable artifact; pick any control → evidence pullable today.
- Grep schema + `protos/events/` + log redaction set: no `card_number`/`pan`/`cvv`/`account_number` exists or is loggable; the security FAQ has the SAQ-A statement + gateway AOCs.
- `DELETE FROM audit_log` / `UPDATE <ledger> SET input_snapshot=…` as a service role → rejected; delete an audit object before retention → denied; tamper a staging row → verifier flags the broken chain vs the WORM anchor; an erasure clears PII everywhere but keeps the audit row + clean chain.

## References
`engineering-os-blueprint/08-technical-governance.md` (compliance machinery + audit immutability) · `COMPLIANCE.md` (the product's regime) · `compliance-engine` (the privacy/channel regime) · `security-baseline` (CC-mapped posture, scanners, SBOM) · `decision-log` (append-then-update lifecycle) · `incident-response`.

## 2026 market update

- **Policy-as-code is the enforcement mechanism:** controls become tested, admission-enforced rules (OPA/Gatekeeper, Kyverno) — see `policy-as-code`. "The policy says X" is now "the cluster *rejects* not-X".
- **Provenance + signing = auditor-grade attestation evidence:** SLSA provenance and Sigstore signatures (`supply-chain-security`) literally satisfy "prove what produced this artifact" — feed them as control evidence.
