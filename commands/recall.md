---
name: recall
description: Print the full per-feature journal so a teammate gets caught up instantly.
argument-hint: "<feature-slug>"
---

Print everything every agent has done on feature `$ARGUMENTS`.

Steps:

1. Locate `.engineering-os/memory/features/$ARGUMENTS.md`. If missing, try the `feat-` prefix or `fix-` prefix.

2. Read the full journal. Print it verbatim.

3. After the journal, print a one-paragraph summary:
   - Current stage / status
   - Owner
   - Outstanding blockers
   - Last verification result
   - When the next action is due

4. Read the corresponding run folder(s) from `.engineering-os/runs/` (filter by req_id suffix in folder name). List the artifact files present.

5. Read recent decision-log entries for this req_id: `grep -r '"req_id":"<feature>"' .engineering-os/decision-log/`. Print the last 10.

This command is the single best onboarding tool for a teammate who just ran `git pull`.
