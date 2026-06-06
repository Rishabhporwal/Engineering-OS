# 08 — Technical Governance

> How the OS keeps technical coherence as it scales: standards governance, the tech radar, version and
> dependency policy, compliance-as-a-capability, and security governance. Governance here means
> *keeping the system's technical decisions coherent, current, and defensible* — not bureaucracy.

---

## 1. What governance owns

Governance is the **Technical Governance** function ([01](01-organization-structure.md)), co-owned by
the Engineering Advisor and the Architect. It owns the decisions that outlive a single requirement:

- The **standards** every change is held to ([05](05-engineering-standards.md)) — keeping them current.
- The **tech radar** — what to adopt, trial, hold, or retire.
- The **version & dependency policy** — runtimes, frameworks, libraries.
- **Compliance** as an engineered capability.
- **Security governance** — posture, the threat-model cadence, the scanner suite.
- **Canon stewardship** — keeping the Product Canon coherent as the system evolves.

Governance operates on a **cadence**, not per-change; per-change concerns are handled by the gates.

---

## 2. Standards governance

Standards are living. Governance keeps them honest:

- **A standard exists only if it is enforced.** A standard the OS cannot gate is downgraded to a
  guideline ([00 §5](00-first-principles.md)). Every standard in [05](05-engineering-standards.md)
  maps to a gate in [06](06-quality-gates-and-metrics.md).
- **Promotion and retirement.** A pattern that proves itself across requirements is promoted to a
  standard (with a gate). A standard that no longer serves is retired with an ADR — silently-ignored
  standards corrode trust in all of them.
- **Exceptions are explicit and time-boxed.** A waiver from a standard is recorded (who, why, until
  when), never a quiet bypass.

---

## 3. The tech radar

A periodically-reviewed map of technologies and techniques in four rings:

| Ring | Meaning | Consequence |
|---|---|---|
| **Adopt** | Proven here; the default choice. | Use without an ADR. |
| **Trial** | Promising; use in a bounded, reversible context. | Allowed with an ADR + a kill path. |
| **Assess** | Worth understanding; not yet for production. | Spikes only. |
| **Hold** | Avoid for new work (legacy, risky, or superseded). | New use requires escalation. |

The radar prevents two failure modes: **uncontrolled novelty** (every team picks a different new
thing) and **ossification** (nothing new is ever tried). New technology enters production through
**Trial → Adopt**, gated by an ADR and the stack-decision framework ([09](09-reference-architecture.md)).

---

## 4. Version & dependency policy

**Intent.** Dependencies and runtimes are current enough to be secure and supported, stable enough to
be trusted, and upgraded deliberately.

- **LTS baseline.** Runtimes and core frameworks track a supported (LTS) baseline; running on
  end-of-life versions is a tracked risk with a remediation plan.
- **Upgrade cadence by change size.** Patch updates land promptly (security first); minor updates on
  a regular cadence; **major upgrades require an ADR** (breaking-change assessment + migration plan).
- **EOL watch.** Upcoming end-of-life and end-of-support dates are tracked ahead of time, not
  discovered at the deadline.
- **Automated dependency triage.** An update bot (e.g. Dependabot/Renovate-style) raises updates;
  they are triaged — security patches expedited, others batched — never auto-merged blindly into
  high-stakes paths.
- **Supply-chain integrity.** Dependencies are pinned and lock-filed; provenance and licenses are
  checked; the dependency scanner ([05 §3](05-engineering-standards.md)) gates known-vulnerable
  versions.

Ownership: Platform/SRE + Architect, on a governance cadence.

---

## 5. Compliance as an engineered capability

The OS carries **no specific regulatory knowledge** — compliance regimes are domain- and
jurisdiction-specific and are defined in the Product Canon ([10](10-adoption-and-product-canon.md)).
What the OS provides is the **machinery to enforce whatever regime the Canon declares**:

- **Compliance is a trigger surface.** Any change touching the compliance boundary routes to
  high-stakes rigor ([03 §3](03-delivery-lifecycle.md)).
- **The Security Reviewer VETOes violations** of the declared regime ([02](02-engineering-roles.md)).
- **Evidence-as-you-build.** Where a regime requires attestation (audits, certifications), the
  evidence is produced *as part of the work*, not reconstructed before an audit — controls map to
  gates, and the gate's record is the evidence.
- **Audit-trail integrity.** Where a regime requires tamper-evidence, the OS supports an immutable,
  append-only, integrity-verifiable record (hash-chaining / write-once storage) so integrity can be
  *proven*, not asserted.
- **Data-handling controls** (residency, retention, consent, minimization, deletion) are expressed as
  enforceable rules in the Canon and gated like any other standard.

> The OS makes compliance *enforceable and provable*; the Canon makes it *specific*. This split is
> what lets the same OS serve a regime in one jurisdiction and a different regime in another without
> changing the OS.

---

## 6. Security governance

Beyond the per-change Security gate ([06](06-quality-gates-and-metrics.md)), governance maintains the
security posture over time:

- **Threat-model cadence** — high-risk systems are re-threat-modeled on a schedule and on
  significant change, not only at birth.
- **The scanner suite** (SAST, dependency audit, secret scan, IaC scan, container scan) is maintained,
  tuned to reduce false-negatives, and its findings are triaged on a cadence.
- **Access reviews** — privileged access and access-control policies are reviewed periodically;
  least-privilege drift is corrected.
- **Secret hygiene** — secret-scanning gates cannot be silently bypassed; rotation policies exist and
  are tested.
- **Incident lessons feed posture** — security-relevant postmortems update the threat models and the
  standards.

---

## 7. Canon stewardship

The Product Canon ([10](10-adoption-and-product-canon.md)) is the ground truth every role reads. As
the system evolves, the Canon must evolve with it or it becomes a lie roles act on.

- **Drift detection.** Governance watches for divergence between the Canon (design, invariants,
  standards) and the running reality; detected drift becomes a requirement to reconcile.
- **Amendment discipline.** A change to an invariant or a foundational decision is a **Foundation
  amendment** — it re-enters the Foundation flow and is re-approved, not edited in passing.
- **Single source of truth.** Where a fact lives in exactly one place (a metric definition, a
  contract, a config), governance ensures it is not silently duplicated; duplication that drifts is a
  defect.

---

## 8. The governance cadence

```
 Per change ─────────────▶ the gates ([06]) handle it.
 Per cadence (governance) ─▶ radar review · version/EOL triage · threat-model refresh ·
                            standards promote/retire · access review · Canon drift reconcile.
 Per Foundation amendment ▶ invariant/architecture changes re-enter the Foundation flow.
```

Governance is deliberately **slow and rare** relative to delivery. Its job is to keep the fast path
(the pipeline) trustworthy — by ensuring the standards it enforces, the stack it builds on, and the
Canon it reads are current, coherent, and defensible.
