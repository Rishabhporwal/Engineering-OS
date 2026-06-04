---
name: resume
description: Recover an interrupted Engineering OS pipeline. Reads state + journals, finds the in-flight requirement and its current stage/owner, and re-invokes the responsible agent to continue from exactly where it stopped — no completed work redone, nothing lost.
disable-model-invocation: true
---

Resume an interrupted pipeline. Target requirement (a `req_id`; if empty, list all resumable in-flight requirements):

> $ARGUMENTS

## Steps

1. **Read `.engineering-os/state/active.json`.** Identify the requirement by the `req_id` argument; if no argument, list every requirement NOT in a terminal state (`shipped` / `rejected` / `killed`) with its stage + owner, and ask which to resume.
1a. **Establish the OUTSTANDING spawns from the harness (most reliable), then the cursor, then status.** The harness records spawn issuance + return mechanically (the `Task|Agent` hook), so this survives an orchestrator crash even if the prose cursor write didn't land:
    ```sh
    uv run ${CLAUDE_PLUGIN_ROOT}/tools/heartbeat_check.py --project-dir ${CLAUDE_PROJECT_DIR}   # prints OUTSTANDING: spawns issued-but-not-returned
    uv run ${CLAUDE_PLUGIN_ROOT}/tools/orchestrator_cursor.py get --project-dir ${CLAUDE_PROJECT_DIR} --req <req-id>   # the scheduler's own plan (awaiting_reconcile, last_route)
    ```
    **Re-await/re-spawn exactly the `OUTSTANDING` set** (a builder spawned just before a crash shows here even if the cursor is stale). Cross-check against the cursor's `awaiting_reconcile` + `last_route`; fall back to status + artifacts only if both are empty.
2. **Reconstruct context** (don't trust memory — read it): the requirement's run folder, its per-feature journal (`memory/features/feat-<slug>.md`), and the recent decision-log lines. Establish what's DONE and what's PENDING (cross-check against the cursor's `outstanding`).
3. **Determine the resume point** from `status` + the last journal entry + which numbered artifacts already exist in the run folder.
4. **Re-invoke the responsible agent** via the Agent tool with a `RESUME` prompt that states: the stage, the run folder, what was already completed (artifact list), and what remains. The agent re-reads its journal + canon + runs `/recall-similar`, then continues — it MUST NOT redo completed work.
5. **Guard against duplicate work:** if `status` is mid-parallel-review, check whether `09-security-review.md` / `10-qa-review.md` already exist before re-spawning Shreya / Tanvi. If express lane, resume at the single builder or Tanvi as appropriate.
6. **Append a decision-log entry** `type="resume"` noting the resume point.

If the requirement is already in a terminal state, report that and do nothing. If `active.json` is missing/corrupt, point the operator at the `.bak.<ts>` recovery (see memory-and-git-sync).
