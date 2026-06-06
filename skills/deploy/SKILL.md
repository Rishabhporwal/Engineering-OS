---
name: deploy
description: Run Stage 8 (Platform/SRE) — CI + staging + production with auto-rollback.
disable-model-invocation: true
---

Run Stage 8 for `$ARGUMENTS`. Normally invoked automatically after `/approve`, but available manually as an escape hatch.

Steps:

1. Read `.engineering-os/state/active.json`. Verify status == `approved`. If not, refuse: "Cannot deploy — requirement is not approved yet."
2. **Invoke the `platform-devops` subagent.**

The Platform/SRE role then runs (binding the concrete tooling from the Product Canon's `STACK.md` + the deploy playbook):
- CI: lint → typecheck → test → build → image push
- Staging deploy
- Staging verification: real-network smoke, metric parity, dashboard sanity, alarm sanity
- Production deploy (canary if applicable)
- Post-deploy monitor window with auto-rollback triggers active

Print the role's progress as it goes. The final `deployment-report.md` will be in the run folder.

If any gate fails, the Platform/SRE role bounces back to Stage 4 (security/QA triage) and updates state.
