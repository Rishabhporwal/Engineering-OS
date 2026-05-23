---
name: soc2-readiness
description: Map Brain's EXISTING controls to the SOC 2 Trust Service Criteria (+ ISO 27001 crosswalk) and collect evidence AS-YOU-BUILD, not reconstructed under deal pressure. Which controls already exist (RBAC, audit log + Decision Log, vuln scanning + SBOM, change management via the pipeline, encryption/KMS, incident response, residency) mapped to TSC (Security/Availability/Confidentiality/Processing-Integrity/Privacy); the evidence artifact each control produces; the readiness gaps; Phase-4 timing (Type 1 → Type 2, India-friendly vendor Sprinto). Use when prepping for an enterprise security review, scoping a SOC 2 effort, or deciding what evidence a new control must emit. Owner: Shreya.
---

# SOC 2 readiness — map what exists, collect evidence as you build

Brain targets SOC 2 in **Phase 4** when enterprise demand arrives (TECH/09 §9, TECH/16 §8 Q3). The trap is treating it as a Phase-4 *project* — scrambling to reconstruct 12 months of evidence under a deal deadline. The cheaper path: Brain **already does most of the controls**; this skill maps them to the Trust Service Criteria now and ensures each one **emits its evidence artifact continuously**, so the audit window is observation, not archaeology.

> **The one rule:** *every control already in the stack is mapped to a TSC point and emits a dated, retrievable evidence artifact — collected as-you-build, never reconstructed.*

**Canonical source:** TECH/09 §9 (compliance roadmap, Type 1→Type 2, vendor) + §16 (security checklist), TECH/16 §7 (Phase 4 SOC 2). Owned by **Shreya** (security/compliance). Vendor: **Sprinto** (India-friendly pricing — §17 open-Q), 12-month Type 2 window, ~$30–60K/yr. Scope the five TSC; **Security (Common Criteria) is mandatory**, the other four are opt-in by customer demand.

## Controls Brain ALREADY has → TSC mapping + evidence

| Brain control (where) | TSC point(s) | Evidence artifact it emits |
|---|---|---|
| **RBAC** — 5 roles, JWT claims + RLS + `requireRole` on every mutation (`auth-and-access`) | CC6.1, CC6.3 | Role matrix, RLS policies, JWT claim schema, `requireRole` test suite |
| **Multi-tenancy isolation** — 4-layer `workspace_id` (`multi-tenancy-isolation`) | CC6.1, **C1.1** (confidentiality) | Cross-tenant denial tests, query-gateway rejection logs |
| **Audit log + Decision Log** — append-only + tamper-evidence (`audit-log-immutability`) | CC7.2, CC7.3, **PI1.x** | Audit `audit_log`, S3 Object Lock config, hash-chain verifier runs |
| **Vulnerability scanning** — Snyk/Trivy/Bandit/pip-audit + SBOM in CI (`vulnerability-scanning`) | CC7.1, **CC8.1** | CI scan results, SBOMs, severity-SLA suppression file with expiries |
| **Change management** — PR + CI gates + ArgoCD + Stage-4/5 review gates (Shreya/Tanvi VETO) | **CC8.1** | PR history, required-reviewer config, deploy logs, the 8-stage pipeline record |
| **Encryption** — TLS 1.2+, KMS envelope for OAuth tokens, SSE-KMS, EBS/MSK at rest (`security-baseline`) | CC6.7, **C1.1** | KMS key policies, TLS/HSTS config, encryption-at-rest inventory |
| **Secrets management** — Secrets Manager + per-service IRSA + rotation | CC6.1, CC6.7 | Secrets Manager config, rotation schedule, IAM/IRSA policies |
| **Logging + monitoring** — OpenSearch/CloudWatch/X-Ray/Sentry, correlation IDs, PII redaction (`observability`) | CC7.1, CC7.2 | Log schema, redaction config, alert monitors, dashboards |
| **Incident response** — Sev1–4, on-call, blameless postmortems (TECH/09 §13) | CC7.3, **CC7.4, CC7.5** | Postmortems, PagerDuty rotation, severity matrix |
| **Backup + DR** — PG PITR, CH/MSK snapshots, RTO/RPO, monthly+quarterly drills (TECH/09 §14) | **A1.2, A1.3** (availability) | Backup configs, DR drill records, RTO/RPO targets |
| **Data residency** — ap-south-1 default, SCPs + residency test (`data-residency-enforcement`) | C1.1, **P-series** | SCP config, residency test runs, AWS Config drift reports |
| **Privacy / DPDP** — consent primitive, minimization, erasure/export (`data-privacy-dpdp`) | **P1–P8** (privacy) | Consent schema, erasure-job runs, DPA, sub-processor list |
| **Access reviews** — quarterly IAM/DB-role review (TECH/09 §15) | CC6.2, CC6.3 | Quarterly review records, deprovisioning logs |

The headline: **the Security common criteria (CC1–CC9) are largely covered today.** SOC 2 is mostly *evidencing* what Brain built, not building new controls.

## The five Trust Service Criteria (what each covers, for Brain)

- **Security (CC, mandatory):** access control, change management, vuln management, monitoring, incident response — Brain's strongest area.
- **Availability:** uptime/DR/backup — Brain has SLOs (API 99.5%→99.95%, Morning Brief by 07:20 IST >99.5% days) + DR drills.
- **Confidentiality:** protecting data designated confidential — multi-tenant isolation + encryption + residency.
- **Processing Integrity:** processing is complete, accurate, timely, authorized — Brain's **metric-engine TS↔Python parity**, **deterministic billing** (no LLM in billing, TECH/15 §7), **Decision Log create-before-display**, and **idempotency** are exactly PI controls. (A strong, differentiated PI story.)
- **Privacy:** notice/choice/collection/use/retention/disclosure — DPDP/PDPL consent + minimization + erasure.

## ISO 27001 crosswalk

The same controls double as ISO 27001 Annex A evidence (TECH/09 §9 Phase 5): RBAC → **A.5.15/A.8.3**; logging/monitoring → **A.8.15/A.8.16**; crypto → **A.8.24**; vuln mgmt → **A.8.8**; change mgmt → **A.8.32**; backup → **A.8.13**; supplier/sub-processor → **A.5.19–A.5.22**; incident → **A.5.24–A.5.28**. Build the evidence once; satisfy both frameworks. The ISMS (risk register, Statement of Applicability, management review) is the ISO-specific add-on.

## Evidence collection as-you-build (the actual ask)

The discipline, not a tool: **every control's artifact is dated, retrievable, and continuous** — not screenshotted the week before the audit.

- **Automate the pull:** the GRC platform (Sprinto) connects to AWS, GitHub, the IdP, and ticketing to *continuously* pull config + control state — not manual uploads.
- **Make new controls emit evidence by default:** when a new control ships, define its artifact + where it lands at design time (e.g. a new gate writes to CI logs S3-archived; a new policy is versioned in `infra/`). A control with no retrievable evidence isn't audit-ready.
- **Map it the day you build it:** tag the control to its TSC point in the readiness register so the map never goes stale.

## Readiness gaps (build before/at Phase 4)

| Gap | TSC | Action |
|---|---|---|
| **MFA** optional today | CC6.1 | Mandatory for owners/admins (Phase 3→4, TECH/09 §1) |
| Audit log **Object Lock** not yet on | CC7.2/PI1 | Bring forward when a deal needs it (`audit-log-immutability`) |
| **Penetration test** | CC4.1 | Internal pre-Phase-3; external annual from Phase 4 (TECH/09 §7) |
| **Vendor/sub-processor** management formalized | CC9.2 | DPA + sub-processor list before first paying brand (TECH/16 §8 Q5) |
| **Policies** (infosec, IR, access, BCP) written + acknowledged | CC1.x | Author + employee acknowledgement workflow |
| **Risk assessment** documented | CC3.x | Formal risk register (also ISO ISMS input) |
| **HR/onboarding-offboarding** controls | CC1.4 | Background checks, deprovisioning checklist |
| DPO appointed | P-series | Phase 3 when revenue justifies (TECH/09 §9) |

## Phase timing

- **Phase 1:** internal hygiene — Privacy Policy + Terms + DPA template + security FAQ (the FAQ already cites SAQ-A from `pci-compliance-scope`).
- **Phase 2:** DPDP compliance live (residency done, consent collection documented).
- **Phase 3:** engage Sprinto, turn on continuous evidence collection, write policies, internal pen test, MFA for owners — **start the clock early so the Type 2 window is already accumulating.**
- **Phase 4:** SOC 2 **Type 1** (point-in-time) → **Type 2** (12-month observation); external pen test; required for enterprise sales. ISO 27001 follows if EU/global demand appears.

## Anti-patterns (Shreya VETO)

- Treating SOC 2 as a **Phase-4 project** instead of continuous evidence collection — guarantees an evidence scramble.
- A control with **no evidence artifact** defined — invisible to an auditor.
- A **new control that doesn't emit evidence by default** — re-creates the reconstruction problem.
- Claiming a TSC is in scope with a **known gap unmapped** (e.g. asserting Availability with no DR-drill records).
- Building SOC 2 + ISO evidence **separately** instead of crosswalking the shared controls once.

## Verify

- The readiness register maps every shipped control to a TSC point + a named, dated, retrievable artifact.
- Pick any control (e.g. quarterly access review) → its evidence is pullable today, not "we'll screenshot it later."
- Each readiness gap has an owner + a phase.
- A new gate/policy PR includes its evidence-artifact definition.

## References
- TECH/09 §9 (compliance roadmap, Type 1→2, Sprinto) + §13–15 (IR, DR, access reviews) + §16 (checklist)
- TECH/16 §7 (Phase-4 SOC 2) + §8 Q3/Q5 (timing, sub-processors)
- [`security-baseline`](../security-baseline/SKILL.md) — the CC-mapped security posture + Shreya VETO
- [`vulnerability-scanning`](../vulnerability-scanning/SKILL.md) — CC7.1/CC8.1 scan + SBOM evidence
- [`audit-log-immutability`](../audit-log-immutability/SKILL.md) — CC7.2/PI1/C1 tamper-evidence
- [`incident-response`](../incident-response/SKILL.md) — CC7.3–7.5 IR control + postmortems
- [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) — the P-series privacy controls
- [`data-residency-enforcement`](../data-residency-enforcement/SKILL.md) — C1/residency evidence
