---
name: status
description: Show the state of every in-flight requirement (or one specific by req_id).
disable-model-invocation: true
---

Show the current state of the Brain Engineering OS pipeline.

If `$ARGUMENTS` is empty:

1. Read `.engineering-os/state/active.json`.
2. **Split by terminal status.** Entries whose `status` is terminal (contains `shipped` / `rejected` / `killed`) are DONE — exclude them from the in-flight table and list them in a one-line "Recently completed: …" note below. This avoids shipped items showing as in-flight (the same bug `/team-digest` had before v0.9.1; `active.json` retains terminal items until archived).
3. Print the in-flight table with columns: `req_id`, `stage`, `status`, `current_owner`, `time_in_stage`, `last_journal_at`.
4. Sort by `stage` ascending, then by `time_in_stage` descending (oldest stuck items first).
5. Below the table, print a one-line summary: "N in flight; M blocked; K completed (awaiting archive); oldest at stage X for D days."

If `$ARGUMENTS` is a req_id:

1. Read `.engineering-os/state/active.json` (or `registry.json` if the req_id has been shipped/rejected).
2. Print the requirement metadata.
3. Print the per-feature journal (`.engineering-os/memory/features/feat-<slug>.md`) entries — most recent first, last 10.
4. Print the most recent decision-log entries for this req_id (grep `.engineering-os/decision-log/`).
5. Print "Next action: <who> should <what>" based on the current status.

For any blocked / stuck requirement (>2 days in same stage), surface a recommendation:
- Bounce back? Escalate to CTOA? Page Founder?
