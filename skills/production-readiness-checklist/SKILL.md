---
name: production-readiness-checklist
description: The composed Stage-6 go/no-go checklist — aggregates operational-readiness, observability, security/supply-chain, docs/runbook, rollback, and cost into ONE pass the final reviewer (and Platform/SRE at Stage 8) walks before anything reaches the Stakeholder. Owner Engineering Advisor (final) + Platform/SRE.
---

# Production-Readiness Checklist (the Composed Stage-6 Gate)

Individual gates each check their slice; this skill is the **composition** — the one walk the `final-reviewer` does at Stage 6 (and Platform/SRE re-confirms at Stage 8) so nothing ships with a slice missing. Each line cites its owning skill; this checklist **aggregates, never restates** (single-source rule). Evidence = the actual artifact/command output in the run folder, per `verification-before-completion`.

## The checklist (every line needs evidence, not assertion)

**Runs + survives** (`operational-readiness`)
- [ ] Root handler + the four health probes; correct port + env validation; real-network smoke output captured.
- [ ] Graceful degradation paths exercised (cost-cap, dependency-down) where the change adds one.

**Observable** (`observability`, `ai-observability-tracing`)
- [ ] Metrics/logs/traces emitted on every new path; correlation/trace ID propagates end-to-end (Stage-4 VETO surface).
- [ ] A dashboard + at least one alarm exists for any new service/surface; model/agent paths emit `gen_ai.*` spans.

**Reviewed + clean** (`security-baseline`, `supply-chain-security`, `gate_check`)
- [ ] Security + QA artifacts = PASS; `tools/gate_check.py --to stakeholder_gate` exits 0 (mechanical — run it, paste output).
- [ ] Scanner suite clean; artifact signed + SBOM attached where the pipeline produces images.

**Verifiable + valid** (`testing-tdd`, `pipeline.yaml §verification_validity`)
- [ ] Full suite green under the REAL security context; negative controls present on high-stakes paths (`validity_check` output).
- [ ] Metric parity vs the registry where metrics changed; mutation tests on high-stakes paths (lane requirement).

**Reversible** (`progressive-delivery`, `incident-response`, `workflow-engine-temporal`)
- [ ] A rollback path exists and is STATED in the deploy plan (flag flip / registry stage / `PLAYBOOK-deploy.md` recipe) — and takes minutes, not a rebuild.
- [ ] Kill switch identified for any new outbound/consequential action.

**Operated** (`incident-response`, the Canon's playbooks)
- [ ] `PLAYBOOK-incident.md` covers the new failure modes (or the delta is appended); on-call knows it exists (journal note).
- [ ] Migration/backfill steps idempotent + re-runnable, with an abort path.

**Costed** (`cost-routing-paradigms`, `finops-cost`)
- [ ] Effort tier declared + justified on every model path; expected per-tenant cost delta stated and within cap.

**Documented**
- [ ] The run folder tells the story end-to-end (intake → plan → reports → reviews); release notes drafted (`release-notes-and-changelog`).

## Verdict discipline
ALL boxes checked-with-evidence → ADVANCE to the Stakeholder gate. ANY box unevidenced → that's not a note, it's a **BOUNCE to the owning stage** — an unchecked readiness box at Stage 6 is cheaper than the same gap discovered in production. A box that *cannot* apply (e.g. no UI changed) is marked N/A with one line of why — never silently skipped (`no-SKIP` rule).

## Anti-patterns
Checking boxes from memory instead of artifacts · "dashboard will be added later" (later = never; it ships with the change) · a rollback plan that's "revert the commit" for a stateful migration · readiness asserted by the builder instead of walked by the reviewer · skipping the walk on express lane (express still gets the `operational-readiness` + `gate_check` subset).
