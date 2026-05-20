---
name: eos-init
description: One-time scaffold of the Brain Engineering OS shared memory into the current Brain product repo. Run once per Brain project.
disable-model-invocation: true
---

Initialize the Brain Engineering OS shared memory in the current project.

This command writes `.engineering-os/` + `.gitattributes` into `${CLAUDE_PROJECT_DIR}`. Run it once per Brain product repo. Subsequent teammates who clone the repo will already have the scaffold — they only need to install the plugin (`/plugin install brain-engineering-os`).

## What this command does

1. **Detect** `${CLAUDE_PROJECT_DIR}` (the Brain product repo root).
2. **Refuse** if `${CLAUDE_PROJECT_DIR}/.engineering-os/` already exists — that means the project was already initialized. Print "already initialized; nothing to do" and exit.
3. **Refuse** if `${CLAUDE_PROJECT_DIR}/.git` does not exist — the Engineering OS depends on git for shared memory. Print "no git repo found; run `git init` first" and exit.
4. **Confirm with the operator** (unless `$ARGUMENTS == "yes"`) — show what will be written and ask for confirmation. Files to write:
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/README.md`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/state/active.json`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/state/registry.json`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/agents/{cto-advisor,architect,backend,frontend-web,frontend-mobile,intelligence,security,qa,platform,product}.journal.md` (10 starter journals)
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/features/.gitkeep`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/decision-log/.gitkeep`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/runs/.gitkeep`
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/artifacts/.gitkeep`
   - `${CLAUDE_PROJECT_DIR}/.gitattributes` (or append if exists) with the `merge=union` rules for append-only files.
5. **Also create v0.4.0+ directories + files** for the self-improvement substrate:
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/rule-proposals/.gitkeep` (rule proposals land here)
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/durable-rules/.gitkeep` (adopted rules land here)
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/lessons-learned.md` with header:
     ```
     # Brain Engineering OS — Lessons Learned

     > Append-only registry. Each entry sourced from a per-child retro (`14-retro.md`).
     > CTOA reads relevant entries at every Stage 1 intake.
     > Mutation rule: append only.

     No lessons filed yet. First entry will come from the first child's retro.
     ```
   - `${CLAUDE_PROJECT_DIR}/.engineering-os/pending-founder-attention.md` with header:
     ```
     # Pending Founder Attention

     > Items here require Founder review. Agents add lines; Founder acts and strikes them through.
     > Each line names the issue, the artifact path, and the slash command to act.

     (no items)
     ```

5a2. **Also (v0.8.0) create the background-worker findings dir:** `${CLAUDE_PROJECT_DIR}/.engineering-os/findings/.gitkeep`. Background workers (Point C) append findings here; it stays committed (findings are part of the audit trail). The `.last-*-scan` marker files inside are written by the workers at runtime.

5b. **Also (v0.8.0+) gitignore the derived/runtime files.** Add these lines to `${CLAUDE_PROJECT_DIR}/.gitignore` (create or append; avoid duplicates):
   - `.engineering-os/index/` — the **derived** semantic vector index (`memory.db`), rebuilt by `/reindex`. Never commit it.
   - `.engineering-os/live.log` — the **live pipeline activity stream** agents append to while working (watch it with `/watch` / `tail -f`). Ephemeral runtime narration; the durable record is the journals + decision-log.
   - `.engineering-os/dashboard.html` — the **generated** progress dashboard (rebuilt by `/dashboard`). Derived/rebuildable; never commit it.
   Everything ELSE under `.engineering-os/` stays committed.

6. **Write each scaffolded file** using the canonical templates below. Use the Write tool one file at a time.
6. **Stage and commit** (with operator confirmation) — `git add .engineering-os/ .gitattributes && git commit -m "Wire up Engineering OS shared memory"`. Do NOT push — that's the operator's decision.
7. **Print a summary** of what was created and the suggested next steps:
   - "Push when ready: `git push`"
   - "Try the team: `/requirement <something simple to start>`"

## Templates to write

### `.engineering-os/README.md`

```markdown
# `.engineering-os/` — Shared Memory (Brain product repo)

This directory holds the Brain Engineering OS shared agent memory. It is **committed to git**. Every teammate who clones the repo and runs `git pull` receives the full state of every prior run.

Do NOT add this directory to `.gitignore`. Do NOT remove `.gitattributes`.

## Layout
- `memory/agents/` — per-agent append-only journals
- `memory/features/` — per-feature append-only journals
- `state/` — active.json (last-write-wins), registry.json (append-only)
- `decision-log/` — YYYY/MM/YYYY-MM-DD.jsonl (immutable line-per-event stream)
- `runs/` — per-run timestamped artifact bundles (no collisions possible)
- `artifacts/` — optional per-req cross-links / large artifacts
- `index/` — **derived** semantic vector index (`memory.db`). Gitignored + rebuildable from the above via `/reindex`. NOT a source of truth.

The plugin agents read/write here automatically. You typically don't touch these files by hand. Use `/status` and `/recall <feat-slug>` to inspect state.
```

### `.engineering-os/state/active.json`

```json
{
  "schema_version": 1,
  "updated_at": "<NOW_ISO>",
  "updated_by": "system",
  "active_requirements": []
}
```

(Replace `<NOW_ISO>` with the current UTC ISO 8601 timestamp.)

### `.engineering-os/state/registry.json`

```json
{
  "schema_version": 1,
  "requirements": []
}
```

### Each `.engineering-os/memory/agents/<role>.journal.md`

```markdown
# <Role Title> — Journal

> Append-only. See ${CLAUDE_PLUGIN_ROOT}/docs/role-empowerment-model.md for entry shape.

## <NOW_ISO> — system — bootstrap
**Action:** Journal initialized by /eos init on <NOW_ISO>.
```

Create one file per role:
- `cto-advisor.journal.md`
- `architect.journal.md` (Aryan)
- `backend.journal.md` (Vikram)
- `frontend-web.journal.md` (Ananya)
- `frontend-mobile.journal.md` (Karan)
- `intelligence.journal.md` (Maya)
- `security.journal.md` (Shreya)
- `qa.journal.md` (Tanvi)
- `platform.journal.md` (Jatin)
- `product.journal.md` (Priya)

### `.gitattributes` (append to existing or create)

```gitattributes
# Brain Engineering OS — merge rules for append-only shared memory
.engineering-os/memory/agents/*.journal.md merge=union
.engineering-os/memory/features/*.md merge=union
.engineering-os/decision-log/**/*.jsonl merge=union
.engineering-os/state/registry.json merge=union
```

If `.gitattributes` already exists, append these lines (avoid duplicating). Print a note if you appended vs. created.

## Don't

- Don't overwrite an existing `.engineering-os/` — refuse and exit instead.
- Don't push automatically — operator chooses when to push.
- Don't commit without operator confirmation.
- Don't write more than the listed files — keep the scaffold minimal.
