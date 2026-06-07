---
name: supply-chain-security
description: Software supply-chain integrity — SBOM generation, dependency + container vuln scanning, SLSA provenance, keyless artifact signing (Sigstore/cosign), and OIDC-keyless CI. Prove what you shipped, from source to running artifact. Owner Platform/SRE; Security Reviewer gate.
---

# Supply-Chain Security (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **artifact-integrity seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to different tools (GitHub Actions vs GitLab CI; Syft/Trivy vs Snyk; cosign vs notation). The *patterns* — an SBOM per artifact, scan-and-block in CI, build provenance, signed-and-verified artifacts, and no long-lived cloud keys — are what transfer; the named tools are examples.

The single largest AppSec shift of 2024–2026: knowing **what** you ship and **proving** it wasn't tampered with between commit and run. Complements `security-baseline` (which covers app-level OWASP/SAST/secrets) with the **artifact + dependency + CI** layer. **Owner:** Platform/SRE (wires the pipeline); **Security Reviewer** gates on findings + missing provenance. Canon: `STACK.md` + `COMPLIANCE.md`.

## Invariants (NON-NEGOTIABLE)
1. **An SBOM is produced for every shippable artifact** (image, package) and stored as a build attestation — not regenerated later from guesswork. Format: SPDX or CycloneDX.
2. **CI blocks on CRITICAL/HIGH vulnerabilities** in dependencies and base images (the same severity bar as `security-baseline`). A scan that only warns is not a gate.
3. **No long-lived cloud credentials in CI.** Use **OIDC federation** (GitHub Actions → cloud role) for short-lived tokens. A static `AWS_SECRET_ACCESS_KEY` in CI secrets is a finding.
4. **Artifacts are signed and verified.** Sign images/artifacts with keyless **Sigstore/cosign** (OIDC identity, transparency log); the deploy step **verifies** the signature + provenance before rollout. Unsigned → does not deploy.
5. **Build provenance to SLSA Level 2+.** The CI emits a provenance attestation (who/what/which source built this artifact); consumers verify it. Untraceable artifacts don't ship.

## The pipeline (where each control sits)
```
commit → [secrets scan: gitleaks/trufflehog]   ← pre-merge, blocks
       → build
       → [SBOM: syft → SPDX/CycloneDX]          ← attach as attestation
       → [vuln scan: trivy/grype on deps+image] ← block CRITICAL/HIGH
       → [IaC scan: trivy/checkov]              ← block on misconfig (ties to policy-as-code)
       → sign: cosign (keyless, OIDC) + provenance (SLSA L2: attest-build-provenance)
       → push to registry
deploy → cosign verify (signature + provenance + SBOM present) → admit  ← else reject
```

## SBOM + scan
```bash
syft packages dir:. -o spdx-json > sbom.spdx.json          # what's inside
grype sbom:sbom.spdx.json --fail-on high                   # known CVEs → fail CI
trivy image --severity CRITICAL,HIGH --exit-code 1 $IMAGE  # image + OS packages
osv-scanner --lockfile package-lock.json                   # malicious-package / OSV feed
```
- Scan **lockfiles** (exact resolved versions), not ranges. Pin/lock dependencies; a floating range is an unreviewed supply-chain entry point.
- Maintain an auditable **allowlist with expiry** for accepted/un-fixable findings — never a blanket ignore.

## Sign + provenance (keyless)
```yaml
# GitHub Actions — OIDC identity, no stored keys
permissions: { id-token: write, contents: read, attestations: write }
- uses: actions/attest-build-provenance@v1     # SLSA provenance attestation
  with: { subject-path: ${IMAGE} }
- run: cosign sign --yes $IMAGE_DIGEST          # keyless: identity from the OIDC token
```
Verify at admission (and ideally via `policy-as-code` admission control):
```bash
cosign verify --certificate-identity-regexp '^https://github.com/<org>/' \
              --certificate-oidc-issuer https://token.actions.githubusercontent.com $IMAGE
```

## Operability + audit
- Provenance + SBOM attestations are **auditor-grade evidence** — feed them to `compliance-attestation` (SLSA attestations literally satisfy "show me what produced this artifact").
- Track: % artifacts signed, mean time-to-patch a CRITICAL CVE, count of unsigned/unverified deploys blocked.
- GitHub Actions itself is a top attack surface — pin third-party actions to a **commit SHA**, not a moving tag; least-privilege `permissions:` per job.

## Anti-patterns
No SBOM (you can't answer "are we affected by CVE-X?") · scan that warns but doesn't block · long-lived cloud keys in CI · unsigned artifacts / no admission verification · provenance missing (untraceable build) · third-party actions pinned to a mutable tag · blanket vuln ignores with no expiry · floating dependency ranges.
