# Orchestrator — the pipeline driver (v2)

> The top-level `/requirement` session is the ONLY actor with the `Agent` tool. Spawned agents have no `Agent` tool (a subagent cannot spawn a subagent). The orchestrator drives every stage: spawn → read the returned `HANDOFF` block + re-read `state/active.json` (source of truth) → route per `pipeline.yaml` → repeat, until the Founder gate (Stage 7) or a terminal state.
>
> All routing, lanes, model tiers, and delta-review rules come from [`pipeline.yaml`](pipeline.yaml). Lane assignment uses [`lane-classifier.md`](lane-classifier.md). This file is the *procedure*; the YAML is the *data*. They must agree (validated by `tools/pipeline_doctor.py`).

## Per-spawn contract (every Agent call)

Every spawn prompt MUST include:
- the `req_id`, the run-folder path, the absolute `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PROJECT_DIR}`;
- the model tier from `pipeline.yaml.stages.<stage>.model` (override per persona / delta as noted);
- the note: *"you are a subagent with no Agent tool — do your stage, persist artifacts + update `state/active.json` + journals, END with a HANDOFF block; do NOT attempt to spawn anything";*
- *"append a live progress line to `.engineering-os/live.log` at each meaningful step."*

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

1. **Intake (S1) — spawn `cto-advisor`** (model `intake_judgment`).
   - `CHALLENGE-BACK` / `KILL` → STOP, surface to Founder.
   - `needs_personas` non-empty → spawn each persona via `dynamic-persona-generator` **IN PARALLEL** (one message, multiple Agent calls), each at its tagged model (`:haiku`→`persona_bounded`, `:sonnet`→`persona_deep`). Then **re-spawn `cto-advisor`** to synthesize; re-read.
   - `ADVANCE` → `express`: next = the one builder (S3); `standard`/`high_stakes`: next = `architect` (S2).
2. **Architect (S2)** → on ADVANCE spawn the tagged builder(s). Multiple tracks (`@vikram`/`@ananya`/`@karan`/`@maya`) → spawn **IN PARALLEL**.
3. **Builders (S3) return** → `express`: spawn `qa-agent` only. `standard`/`high_stakes`: spawn `security-reviewer` AND `qa-agent` **IN PARALLEL** (PARALLEL REVIEW MODE: review, write artifact, return verdict, do not advance).
4. **Reconcile reviews** (use `docs/finding-severity-rubric.md` so Security/QA converge, not bounce each other):
   - both `PASS` → `express` → Founder gate; else → `final` (S6).
   - any `BOUNCE`/`FAIL` → re-spawn the responsible **builder** with the findings, then **DELTA RE-REVIEW** (next section).
5. **Final (S6) — `cto-advisor`** (model `final_judgment`). `PASS` → ensure `awaiting-founder` → STOP at Founder gate. `BOUNCE` → spawn `bounce_target`, continue.
6. **Safety bound:** cap at 20 spawns. On exceed, STOP, leave state consistent for `/resume`, surface to Founder.

## Delta re-review (the dominant cost lever; fixes O12)

When a review BOUNCES and the builder has re-fixed, the orchestrator decides `review_scope` per `pipeline.yaml.delta_review`:
- **`full`** if the fix touches a `high_stakes_path` (compliance/tenancy/metric/decision-log/money/outbound/auth) OR the diff exceeds the bounced finding's blast radius → re-spawn the reviewer normally (`security_default`/`qa`).
- **`delta`** otherwise → re-spawn the reviewer at `delta_reverify` (Sonnet) with: *"DELTA RE-REVIEW. Read your prior PASS/BOUNCE artifact + the diff-since-last-review. Re-verify ONLY the bounced finding(s) + a regression check on the changed lines. Do NOT re-run the full surface."*

Pass `--review-scope delta` to `usage_logger.py` so the savings are measurable on the dashboard.

## Founder gate (S7) — STOP

Print: req_id, lane, stages run, bounces (+ how many were delta vs full), then: *"Pipeline reached the Founder gate. Run `/approve <req-id>` to ship (Stage 8) or `/reject <req-id> <reason>`."* Do NOT run Stage 8 — deploy happens only after `/approve`.

## Failure handling

Any failure (state corrupted, agent error, no write permission) → surface clearly, leave `state/active.json` consistent for `/resume`, never silently proceed.
</content>
