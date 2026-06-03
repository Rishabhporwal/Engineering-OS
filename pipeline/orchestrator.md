# Orchestrator — the pipeline driver (v2)

> The top-level `/requirement` session is the ONLY actor with the `Agent` tool. Spawned agents have no `Agent` tool (a subagent cannot spawn a subagent). The orchestrator drives every stage: spawn → read the returned `HANDOFF` block + re-read `state/active.json` (source of truth) → route per `pipeline.yaml` → repeat, until the Founder gate (Stage 7) or a terminal state.
>
> All routing, lanes, model tiers, and delta-review rules come from [`pipeline.yaml`](pipeline.yaml). Lane assignment uses [`lane-classifier.md`](lane-classifier.md). This file is the *procedure*; the YAML is the *data*. They must agree (validated by `tools/pipeline_doctor.py`).

## Per-spawn contract (every Agent call)

**Order the spawn prompt CACHE-STABLE-FIRST (the #1 cost lever — `pipeline.yaml §caching`):** build every spawn prompt as a **stable prefix** then a **variable suffix**, never interleaved. Stable prefix (byte-identical across spawns → the harness caches it): the role/stage framing + the fixed plugin paths + which canon/skills to consult. Variable suffix (the only changing bytes, placed LAST after a clear `--- TASK ---` delimiter): `req_id`, run-folder path, the diff, the specific task + findings. Putting per-run data first would bust the cache for every call; keeping it last maximizes the cached prefix.

Every spawn prompt MUST include (stable prefix unless noted):
- the absolute `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PROJECT_DIR}`;
- the model tier from `pipeline.yaml.stages.<stage>.model` (override per persona / delta as noted);
- the note: *"you are a subagent with no Agent tool — do your stage, persist artifacts + journals, declare your intended state in the HANDOFF `state` fields (do NOT write `state/active.json` yourself — the orchestrator is the sole writer), END with a HANDOFF block; do NOT attempt to spawn anything";*
- *"append a live progress line to `.engineering-os/live.log` at each meaningful step";*
- **VARIABLE suffix (last):** the `req_id`, the run-folder path, the diff, and the task specifics + any bounce findings.

## State is written by the orchestrator only (fixes the parallel-write race)

You spawn builders and reviewers **in parallel**; if each wrote `active.json` directly, concurrent read-modify-writes would clobber the source-of-truth file. So subagents NEVER write it — they return their intended `state` in the HANDOFF block, and **you apply it serially + atomically** after each spawn returns:
```sh
uv run ${CLAUDE_PLUGIN_ROOT}/tools/state_update.py --project-dir ${CLAUDE_PROJECT_DIR} \
  --req <req_id> --status <handoff.state.status> --stage <handoff.state.stage> --owner <handoff.state.owner>
```
Apply each parallel agent's delta one at a time (you are single-threaded — that's the guarantee). `state_update.py` writes atomically (`os.replace`) so a crash never leaves invalid JSON live.

## Persist your OWN loop state (crash recovery)

You are the SPOF: your in-flight plan (which parallel spawns are outstanding, what's awaiting reconcile, the spawn count) lives only in your context — a mid-pipeline compaction/crash loses it. After **every routing decision** (every spawn issued or returned), write your cursor:
```sh
uv run ${CLAUDE_PLUGIN_ROOT}/tools/orchestrator_cursor.py set --project-dir ${CLAUDE_PROJECT_DIR} \
  --req <req_id> --stage <N> --outstanding <agents-spawned-not-yet-returned> --last-route "<one line>" --bump-spawns
```
On a clean Founder-gate/terminal, `clear` it. `/resume` rebuilds the *scheduler* from this cursor — not just the requirement status — so it re-awaits the exact outstanding spawns instead of guessing.

## Per-spawn telemetry — ENFORCED (not prose; fixes O14/O13)

Immediately after each spawn returns:
1. **Log** — call:
   ```sh
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/usage_logger.py log \
     --project-dir ${CLAUDE_PROJECT_DIR} --req <req_id> --agent <agent> --stage <N> \
     --model <actual-model> --review-scope <full|delta|none> \
     --total <t> [--input <i> --output <o> --cache-read <cr> --cache-creation <cc>]
   ```
   Pull the usage from the Agent result's `usage` object; omit any field the harness doesn't surface (never fabricate). For personas, log the model the orchestrator actually used (Haiku/Sonnet), not the generator default.
2. **Assert** — before routing on, call:
   ```sh
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/usage_logger.py assert \
     --project-dir ${CLAUDE_PROJECT_DIR} --req <req_id> --agent <agent> --stage <N>
   ```
   Exit 3 = the row is missing = a DEFECT. Re-log it before advancing. A missing usage row is treated like a skipped required check — never silently passed.

## Terminal narration (the Founder is watching)

At start: `Pipeline started for <req_id>. Follow with /watch or tail -f .engineering-os/live.log`.
Around each spawn:
- before: `▶ Stage <N> — spawning <agent> (<persona>) [<model>]…`
- after: `✓ <persona>: <2–3 line summary> → handing to <next>` or `✗ <persona>: BOUNCE — <reason> → re-spawning <target> [<review_scope>]`.

## The loop (routes per `pipeline.yaml.routing`)

1. **Intake (S1)** — first run the **deterministic lane scan**, then spawn `cto-advisor` (model `intake_judgment`, Sonnet) with the result:
   ```sh
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/classify_lane.py --text "<requirement>"
   ```
   Pass `feature_class` + `trigger_surfaces_touched` into the spawn prompt; the agent validates (may ADD a surface, never REMOVE one). This is what makes the lane robust to a model miss.
   - `CHALLENGE-BACK` / `KILL` → STOP, surface to Founder.
   - `needs_personas` non-empty → spawn each persona via `dynamic-persona-generator` **IN PARALLEL** (one message, multiple Agent calls), each at its tagged model (`:haiku`→`persona_bounded`, `:sonnet`→`persona_deep`). Then **re-spawn `cto-advisor`** to synthesize; re-read.
   - `ADVANCE` → `express`: next = the one builder (S3); `standard`/`high_stakes`: next = `architect` (S2).
2. **Architect (S2)** → on ADVANCE spawn the tagged builder(s). Multiple tracks (`@vikram`/`@ananya`/`@karan`/`@maya`) → spawn **IN PARALLEL**.
3. **Builders (S3) return** → `express`: spawn `qa-agent` only. `standard`/`high_stakes`: spawn `security-reviewer` AND `qa-agent` **IN PARALLEL** (PARALLEL REVIEW MODE: review, write artifact, return verdict, do not advance).
4. **Reconcile reviews** (use `docs/finding-severity-rubric.md` so Security/QA converge, not bounce each other):
   - both `PASS` → `express` → **run the VETO gate before the Founder gate** (below); else → `final` (S6).
   - any `BOUNCE`/`FAIL` → re-spawn the responsible **builder** with the findings, then **DELTA RE-REVIEW** (next section).
5. **Final (S6) — `final-reviewer`** (model `final_judgment`). `PASS` → **run the VETO gate**, then ensure `awaiting-founder` → STOP at Founder gate. `BOUNCE` → spawn `bounce_target`, continue.

   **VETO gate (non-LLM, before ANY Founder-gate transition):** a VETO must be a state-machine invariant, not your good behavior. Before setting `awaiting-founder`, run:
   ```sh
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/gate_check.py --run-dir <run-folder> --to founder_gate
   ```
   Exit 2 = an unresolved CRITICAL/HIGH or a non-PASS review exists → do NOT advance; route back to the responsible stage. You cannot reach the Founder gate past this check.
6. **Safety bound (lane-aware, pause-and-confirm):** cap at `pipeline.yaml.safety_bound.max_spawns_by_lane` (express 8 / standard 14 / high_stakes 28). On exceed, **PAUSE** and surface to the Founder **with the spawn history** (from the orchestrator cursor: stage, outstanding, spawns, last_route) so loop-vs-legit is distinguishable — the Founder confirms a one-time bump (`/resume`) or kills it. Never assume "loop"; never hard-stop without showing the history. Leave state + cursor consistent for `/resume`.

## Delta re-review (the dominant cost lever; fixes O12)

When a review BOUNCES and the builder has re-fixed, the orchestrator decides `review_scope` per `pipeline.yaml.delta_review`:
- **`full`** if the fix touches a `high_stakes_path` (compliance/tenancy/metric/decision-log/money/outbound/auth) OR the diff exceeds the bounced finding's blast radius → re-spawn the reviewer normally (`security_default`/`qa`).
- **`delta`** otherwise → re-spawn the reviewer at `delta_reverify` (Sonnet) with: *"DELTA RE-REVIEW. Your REASONING is delta-scoped — read your prior PASS/BOUNCE artifact + the diff-since-last-review and focus on the bounced finding(s) + relevant slices. But RUN THE FULL prior-passing test suite (the same command that last PASSed — it's cheap CI); any test green-before/red-now is an AUTO-BLOCK. Don't re-REASON the whole surface; do re-RUN the whole suite."*

Pass `--review-scope delta` to `usage_logger.py` so the savings are measurable on the dashboard.

## Founder gate (S7) — STOP

Print: req_id, lane, stages run, bounces (+ how many were delta vs full), then: *"Pipeline reached the Founder gate. Run `/approve <req-id>` to ship (Stage 8) or `/reject <req-id> <reason>`."* Do NOT run Stage 8 — deploy happens only after `/approve`.

## Failure handling

Any failure (state corrupted, agent error, no write permission) → surface clearly, leave `state/active.json` consistent for `/resume`, never silently proceed.
</content>
