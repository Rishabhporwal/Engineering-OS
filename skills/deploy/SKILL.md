---
name: deploy
description: Run Stage 8 (Platform/DevOps) — CI + staging + production with auto-rollback.
disable-model-invocation: true
---

Run Stage 8 for `$ARGUMENTS`. Normally invoked automatically after `/approve`, but available manually as an escape hatch.

Steps:

1. Read `.engineering-os/state/active.json`. Verify status == `approved`. If not, refuse: "Cannot deploy — requirement is not approved yet."
2. **Invoke the `platform-devops` subagent.**

The subagent (Jatin) then runs:
- CI (GitHub Actions): lint → typecheck → test → build → ECR push
- Staging deploy via ArgoCD
- Staging verification: real-network smoke, metric parity, dashboard sanity, alarm sanity
- Production deploy via ArgoCD (canary if applicable)
- 48h post-deploy monitor with auto-rollback triggers active

Print Jatin's progress as he goes. The final `deployment-report.md` will be in the run folder.

If any gate fails along the way, Jatin will bounce back to Stage 4 (security/QA triage) and update state.
