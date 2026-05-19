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

8. **Invoke the `cto-advisor` subagent** with the req_id and run folder path. Rohan (CTO Advisor) runs Stage 1 (intake + 0–2 personas by complexity).

9. **Print to the user:**
   - Generated req_id
   - Run folder path
   - "Handed off to CTO Advisor (Stage 1)"

If anything fails (state file corrupted, no write permission, etc.), surface the error clearly and do not silently proceed.
