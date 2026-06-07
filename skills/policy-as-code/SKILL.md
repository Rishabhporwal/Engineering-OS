---
name: policy-as-code
description: Enforce security/compliance/ops rules as version-controlled, testable policy — admission control (OPA/Gatekeeper, Kyverno), IaC policy gates, and CI guardrails. Rules become code with tests, not a wiki page nobody reads. Owner Security Reviewer + Platform/SRE.
---

# Policy-as-Code (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **policy-enforcement seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to OPA/Gatekeeper (Rego), Kyverno (YAML, Kubernetes-native), Kubewarden (WASM), or Cloud Custodian. The *patterns* — declarative rules in version control, tested like code, enforced at admission/plan/CI time, fail-closed on the critical ones — are what transfer; the engine is an example.

Policy-as-code is the **enforcement mechanism** behind `security-baseline`, `compliance-engine`, and `multi-tenancy-isolation`: instead of "the wiki says don't deploy privileged containers", a policy *rejects* one. **Owner:** Security Reviewer (authors the policy) + Platform/SRE (operates the engine). Canon: `COMPLIANCE.md` declares which rules are mandatory. VETO surface.

## Invariants (NON-NEGOTIABLE)
1. **Policies live in version control + have tests.** A policy is code: reviewed, unit-tested against allow/deny fixtures, and CI-gated. An untested policy is as untrustworthy as untested code.
2. **Critical policies fail closed.** Tenant-isolation, no-privileged-container, encrypted-storage, residency, and signed-image rules **deny by default** — an engine outage blocks the deploy, it doesn't wave it through.
3. **Enforce at the earliest gate that can catch it.** IaC/policy violations caught at **CI/plan time** (cheap) before admission time (late). Shift left; admission control is the backstop, not the only line.
4. **Audit mode before enforce mode.** New policies ship in `warn`/`audit`, the violation rate is measured, offenders are fixed, *then* flip to `enforce`. Flipping straight to deny breaks the fleet.
5. **Every policy maps to a real control.** Each rule cites the `COMPLIANCE.md` clause or security control it enforces — no orphan rules; auditors trace control → policy → enforcement evidence.

## Where policies run
```
CI / IaC plan   → terraform/k8s manifest scanned (trivy/checkov + custom Rego) → block PR
Admission (K8s) → Gatekeeper (Rego) or Kyverno (YAML) validates/mutates every apply → reject
Runtime         → continuous audit of live resources for drift → alert/remediate
Application      → OPA as an authz decision point for fine-grained access (optional)
```

## Example — Kyverno (YAML, no Rego) + OPA (Rego)
```yaml
# Kyverno: deny images that aren't signed by our pipeline (pairs with supply-chain-security)
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: require-signed-images }
spec:
  validationFailureAction: Enforce          # fail closed
  rules:
  - name: verify-cosign
    match: { any: [{resources: {kinds: [Pod]}}] }
    verifyImages:
    - imageReferences: ["registry.internal/*"]
      attestors: [{entries: [{keyless: {issuer: "https://token.actions.githubusercontent.com"}}]}]
```
```rego
# OPA/Gatekeeper: no privileged containers (a hard control)
package k8s.security
deny[msg] {
  c := input.review.object.spec.containers[_]
  c.securityContext.privileged == true
  msg := sprintf("privileged container not allowed: %v", [c.name])
}
```
Test the Rego (`opa test`) / Kyverno (`kyverno test`) against fixtures in CI — allow-cases pass, deny-cases reject.

## Common policy set for a multi-tenant SaaS
- No privileged / hostPath / hostNetwork pods; non-root; read-only rootfs.
- Images only from the trusted registry **and** signed (`supply-chain-security`).
- Required labels (tenant/owner/cost-centre — ties to `finops-cost`), resource limits set.
- Storage encrypted; no public S3/buckets; residency tag matches region (`region-and-locale`).
- IaC: no `0.0.0.0/0` ingress on sensitive ports; no plaintext secrets in manifests.

## Operability + audit
- Policy violations are observable (`observability`) and trend-tracked; a rising violation rate before an `enforce` flip is the signal to coach teams first.
- Export policy decisions as **compliance evidence** (`compliance-attestation`): "control X is enforced by policy Y, here are N blocked violations this quarter."

## Anti-patterns
Policy in a wiki instead of code · untested policy · critical rule that fails open · enforcing a brand-new policy without an audit-mode soak · admission-only (missing the cheap CI/plan gate) · orphan rules with no control mapping · mutating policies that silently change user intent without review.
