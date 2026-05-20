---
name: requirement
description: Submit a new requirement to the Engineering OS pipeline (Stage 1).
disable-model-invocation: true
---

You are processing a new requirement submission from the Founder.

The Founder's requirement text is:

> $ARGUMENTS

Steps:

1. **Check for duplicates.** Read `.engineering-os/state/registry.json` and `.engineering-os/state/active.json`. If a similar requirement already exists, surface it and ask the Founder whether to merge or proceed as a new requirement.

2. **Generate a `req_id`.** Pattern: `<kind>-<kebab-slug>` where kind ∈ `{feat, fix, chore, spike, exp}`. Slug is the kebab-cased core of the requirement (max ~6 words).

3. **Create the run folder.** Format (v0.3.1+):
   `.engineering-os/runs/<ISO-8601-UTC-no-colons>__<hex6>__<req-id>__<operator>/`
   
   Where:
   - `<ISO-8601-UTC-no-colons>` — fresh from `date -u +%Y-%m-%dT%H-%M-%SZ` (colons replaced with hyphens for filesystem-safety). Per the UTC timestamp discipline durable rule, derive at action time; do NOT infer from prior artifacts.
   - `<hex6>` — 6 random hex chars from `openssl rand -hex 3` (prevents same-second collisions when multiple intakes overlap).
   - `<req-id>` — the kebab-cased requirement ID.
   - `<operator>` — current OS user (or `<actor>-via-cto-advisor` when CTOA intakes a child on Founder's behalf under delegation).
   
   Example: `.engineering-os/runs/2026-05-17T14-22-31Z__a3f201__feat-abandoned-cart-recovery-gcc__rishabh/`
   
   The `<hex6>` suffix was added in v0.3.1 after the monitor caught children #3 and #4 in the Brain repo colliding on the same `2026-05-19T14-30-00Z` prefix. Collisions are now mechanically prevented.

4. **Write `01-requirement.md`** using [templates/requirement-template.md](../templates/requirement-template.md). Fill in `raw_text`, `submitted_by` (current operator), `submitted_at` (now). Other fields can be filled by CTO Advisor in Stage 1.

5. **Update `.engineering-os/state/active.json`:** append the new requirement entry with `status: cto-review`, `stage: 1`, `current_owner: cto-advisor`. Write a `.bak.<ts>` first.

6. **Update `.engineering-os/state/registry.json`:** append the new req_id + title + first_seen timestamp.

7. **Append a decision-log entry** in `.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl`:
   ```json
   {"ts":"...","actor":"system","type":"intake","req_id":"...","title":"...","submitted_by":"..."}
   ```

8. **ORCHESTRATE the pipeline end-to-end.** YOU (this top-level session) are the orchestrator — you have the `Agent` tool; the agents you spawn do NOT (a subagent cannot spawn a subagent). So you drive every stage: spawn the right agent, read its returned `HANDOFF` block + re-read `state/active.json` (source of truth), and advance — until the Founder gate (Stage 7) or a terminal state. See [docs/orchestration.md](../docs/orchestration.md) for the full model.

   **Every spawn prompt MUST include:** the `req_id`, the run folder path, the explicit note *"you are a subagent with no Agent tool — do your stage, persist artifacts + update state/active.json + journals, and END with a HANDOFF block; do NOT attempt to spawn anything,"* and (critical) the absolute plugin root for `${CLAUDE_PLUGIN_ROOT}` and project dir for `${CLAUDE_PROJECT_DIR}`.

   **Loop:**

   a. **Stage 1 — spawn `cto-advisor`.** Read its HANDOFF + state:
      - `CHALLENGE-BACK` / `KILL` → STOP. Surface to Founder. Done.
      - `needs_personas` non-empty → spawn each persona via `dynamic-persona-generator` **IN PARALLEL** (multiple Agent calls in ONE message), each writing its `0N-persona-*.md`; then **re-spawn `cto-advisor`** to synthesize the persona concerns + finalize ADVANCE/CHALLENGE; re-read.
      - `ADVANCE` + `feature_class=express` → next = the single relevant **builder** (Stage 3).
      - `ADVANCE` + `standard`/`high-stakes` → next = **architect** (Stage 2).

   b. **Stage 2 — spawn `architect`.** On ADVANCE → spawn the tagged **builder(s)** (Stage 3). If the plan tags multiple tracks (@vikram/@ananya/@karan/@maya), spawn them **IN PARALLEL** (one message, multiple Agent calls).

   c. **Stage 3 — builders return.** Then by lane:
      - `express` → spawn **`qa-agent`** only (Stage 5).
      - `standard`/`high-stakes` → spawn **`security-reviewer` AND `qa-agent` IN PARALLEL** (Stages 4∥5). Tell each it is in PARALLEL REVIEW MODE: review, write its artifact, return a verdict, do not advance.

   d. **Reconcile reviews:** both `PASS` → `express` goes to the Founder gate; `standard`/`high-stakes` → spawn **`cto-advisor`** (Stage 6 final review). Any `BOUNCE`/`FAIL` → spawn the responsible **builder** again (Stage 3) with the findings, then re-run the review.

   e. **Stage 6 — cto-advisor returns.** `PASS` → ensure state is `awaiting-founder` → **STOP at the Founder gate.** `BOUNCE` → spawn the `bounce_target` and continue the loop.

   f. **Safety bound:** cap at ~20 agent invocations per requirement. If exceeded, STOP, set state, and surface to Founder (likely a loop). Always leave `state/active.json` consistent so `/resume` can pick up.

9. **At the Founder gate (Stage 7), STOP.** Print a concise pipeline summary: req_id, lane, stages run, any bounces, and: *"Pipeline reached the Founder gate. Run `/approve <req-id>` to ship (Stage 8) or `/reject <req-id> <reason>`."* Do NOT run Stage 8 — deploy happens only after `/approve`.

If anything fails (state corrupted, an agent errors, no write permission), surface it clearly, leave state consistent for `/resume`, and do not silently proceed.
