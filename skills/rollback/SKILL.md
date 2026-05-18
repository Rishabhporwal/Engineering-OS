---
name: rollback
description: Manually trigger rollback of a deployed change.
disable-model-invocation: true
---

Manually trigger rollback. Use when the auto-rollback didn't fire (slow regression, customer-reported issue, security flag) but human judgment says revert.

Steps:

1. Parse `$ARGUMENTS` into `req_id` and `reason`.
2. **Confirm intent** — rollback is destructive in the sense that it reverts the deployed change. Surface what's being reverted (commit SHA, image tag, services affected).
3. **Invoke the `platform-devops` subagent** with directive `manual-rollback`. Jatin uses ArgoCD to revert to the previous synced revision.
4. Append a decision-log entry: type `rollback`, actor `<operator>`, reason, blast radius.
5. Update `state/active.json`: status → `rolled-back`, stage → 4 (re-triage).
6. **Invoke the `security-reviewer` and `qa-agent` subagents** to triage what went wrong.
7. Print: "Rollback initiated. State → rolled-back. Shreya + Tanvi triaging."

For P0 (auth bypass, data leak, DND violation): also page the Founder via the configured alerting channel.
