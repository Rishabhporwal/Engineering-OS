---
name: requirement
description: Submit a new requirement to the Engineering OS pipeline (Stage 1).
disable-model-invocation: true
---

You are processing a new requirement submission from the Stakeholder.

The Stakeholder's requirement text is:

> $ARGUMENTS

Steps:

1. **Check for duplicates.** Read `.engineering-os/state/registry.json` and `.engineering-os/state/active.json`. If a similar requirement already exists, surface it and ask the Stakeholder whether to merge or proceed as new.

2. **Generate a `req_id`.** Pattern: `<kind>-<kebab-slug>` where kind ∈ `{feat, fix, chore, spike, exp}`. Slug is the kebab-cased core of the requirement (max ~6 words).

3. **Create the run folder:**
   `.engineering-os/runs/<ISO-8601-UTC-no-colons>__<hex6>__<req-id>__<operator>/`
   - `<ISO-8601-UTC-no-colons>` — fresh from `date -u +%Y-%m-%dT%H-%M-%SZ` (colons → hyphens). Per the UTC timestamp durable rule, derive at action time; do NOT infer from prior artifacts.
   - `<hex6>` — 6 random hex chars from `openssl rand -hex 3` (prevents same-second collisions).
   - `<req-id>` — the kebab-cased requirement ID.
   - `<operator>` — current OS user (or `<actor>-via-cto-advisor` when the Engineering Advisor intakes a child on the Stakeholder's behalf under delegation).
   Example: `.engineering-os/runs/2026-05-17T14-22-31Z__a3f201__feat-abandoned-cart-recovery__<operator>/`

4. **Write `01-requirement.md`** using [templates/requirement-template.md](../../templates/requirement-template.md). Fill in `raw_text`, `submitted_by` (current operator), `submitted_at` (now). Other fields can be filled by the Engineering Advisor in Stage 1.

5. **Update `.engineering-os/state/active.json`:** append the new entry with `status: cto-review`, `stage: 1`, `current_owner: cto-advisor`. Write a `.bak.<ts>` first.

6. **Update `.engineering-os/state/registry.json`:** append the new req_id + title + first_seen timestamp.

7. **Append a decision-log entry** in `.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl`:
   ```json
   {"ts":"...","actor":"system","type":"intake","req_id":"...","title":"...","submitted_by":"..."}
   ```

   The lane this requirement runs (express / standard / high-stakes) is driven by whether it touches a high-stakes surface declared in the Product Canon's `TRIGGER-SURFACES.md` — the Engineering Advisor and the lane scan (`tools/classify_lane.py`) resolve this in Stage 1.

8. **ORCHESTRATE the pipeline end-to-end.** The full orchestration logic now lives in **[pipeline/orchestrator.md](../../pipeline/orchestrator.md)** + **[pipeline/pipeline.yaml](../../pipeline/pipeline.yaml)** — follow `pipeline/orchestrator.md`. It defines the spawn loop, the stage transitions and lanes (express / standard / high-stakes), persona fan-out + model tiering, parallel review reconciliation, terminal narration, usage logging, and the safety bound. YOU (this top-level session) are the orchestrator — you have the `Agent` tool; spawned agents do NOT.

9. **At the Stakeholder gate (Stage 7), STOP.** Print a concise summary: req_id, lane, stages run, any bounces, and: *"Pipeline reached the Stakeholder gate. Run `/approve <req-id>` to ship (Stage 8) or `/reject <req-id> <reason>`."* Do NOT run Stage 8 — deploy happens only after `/approve`.

If anything fails (state corrupted, an agent errors, no write permission), surface it clearly, leave state consistent for `/resume`, and do not silently proceed.
