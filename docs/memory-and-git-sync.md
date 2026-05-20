# Section 4.3 — Memory & Git Sync (the "agents never forget" guarantee)

> How shared agent memory survives `git pull`, multi-operator parallelism, and time. Read this if you ever need to debug a memory inconsistency or onboard a teammate.

> **v0.2.0 location.** Shared memory lives at `${CLAUDE_PROJECT_DIR}/.engineering-os/` — i.e., inside **the Brain product repo**, not inside the plugin. The plugin (installed at `~/.claude/plugins/brain-engineering-os/`) reads and writes to that location. Teammates `git push/pull` the Brain product repo to share memory. Scaffolded once via `/eos-init`.

---

## The guarantee

When **Teammate A** finishes working on a feature, pushes to git, and **Teammate B** runs `git pull` and opens Claude Code:

- B sees every decision A made.
- B sees every artifact A produced.
- Every agent on B's machine has continuity of memory: the architect knows what the architect did last week, the security reviewer knows the past findings on this codebase, the founder approval log is the same on both machines.

This is delivered by **three primitives** working together:
1. **Append-only journals** (per-agent + per-feature) in `.engineering-os/memory/`.
2. **An immutable JSONL decision log** in `.engineering-os/decision-log/`.
3. **A small, last-write-wins state file** at `.engineering-os/state/active.json`.

All committed to git. All read on session start.

---

## What "memory" means here

| Memory class | Location | Append-only? | Conflict-resistant? |
|--------------|----------|--------------|---------------------|
| **Per-agent journal** — what *this agent* did, across all features | `.engineering-os/memory/agents/<role>.journal.md` | YES | Trivial (line-level union resolves) |
| **Per-feature journal** — everything every agent did on *this feature* | `.engineering-os/memory/features/feat-<slug>.md` | YES | Trivial |
| **Decision log** — structured, queryable event stream | `.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl` | YES | Trivial (one-event-per-line; day-bucketed files) |
| **Run artifacts** — full per-run output bundle | `.engineering-os/runs/<ts>__<req>__<operator>/*` | Per-folder; folder names collision-proof | Impossible to collide |
| **State** — currently active requirements + statuses | `.engineering-os/state/active.json` | NO (last-write-wins) | Designed for trivial JSON merge; agents always re-read before acting |
| **Registry** — canonical list of all req-ids ever | `.engineering-os/state/registry.json` | YES (append-only by convention) | Trivial |

---

## Why append-only is the right shape

Brain's own canon already establishes this principle: the **Decision Log** for the AICMO/AICOO/AICFO agents is append-only, and "Memory is the moat." The plugin applies the same pattern to itself.

**Properties this gives us:**

- **Merge conflicts are rare and shallow.** Two agents appending to the same file at the same place produce a textual conflict at most a few lines wide.
- **History is permanent.** No agent can rewrite history (even by accident). `git revert` exists if needed.
- **Trivially diffable.** `git log -p .engineering-os/memory/agents/architect.journal.md` reads like a story.
- **Trivially searchable.** `grep` over markdown and JSONL is fast.
- **Time-travel-able.** Any historical state can be reconstructed by `git checkout <sha>`.

---

## Conflict scenarios and how they're handled

### Scenario 1 — Two operators submit different requirements simultaneously

**Setup:** Alice and Bob both pull at commit C. Alice runs `/requirement A`; Bob runs `/requirement B`. Both push.

**What happens:**

| File | Alice's change | Bob's change | Merge result |
|------|----------------|--------------|--------------|
| `runs/<tsA>__feat-A__alice/01-requirement.md` | created | — | no conflict |
| `runs/<tsB>__feat-B__bob/01-requirement.md` | — | created | no conflict |
| `memory/features/feat-A.md` | created (1 entry) | — | no conflict |
| `memory/features/feat-B.md` | — | created (1 entry) | no conflict |
| `memory/agents/cto-advisor.journal.md` | appended A's entry | appended B's entry | **trivial 2-way append** — git auto-resolves with `merge=union` attribute |
| `decision-log/2026/05/2026-05-17.jsonl` | appended 1 line | appended 1 line | **trivial 2-way append** — same |
| `state/active.json` | added req-A | added req-B | **JSON merge** — usually trivially resolvable; manual if not |
| `state/registry.json` | appended req-A | appended req-B | **trivial 2-way append** — same |

Whoever pushes second gets a tiny conflict on `state/active.json`. Git's built-in 3-way merge usually resolves the JSON correctly when both adds are to the same array; otherwise the operator resolves manually in 30 seconds.

### Scenario 2 — Two operators pick up the same requirement simultaneously

**Setup:** Both pull. Both see `feat-X` in `state/active.json` ready for QA. Both run agents.

**What happens (intended):**

1. Each agent **re-reads `state/active.json` before acting**. It sees `feat-X.current_owner = qa-agent`.
2. Each agent **attempts to update `state/active.json`** to set `current_owner_persona = tanvi-alice` or `tanvi-bob` (machine-tagged).
3. **First push wins.** Second push sees the conflict on `state/active.json` and exits gracefully ("Tanvi was already picked up by alice@10:00; your work has been preserved in `runs/<tsB>__feat-X__bob/` for reference; not advancing canonical status.").
4. The "loser" run folder is preserved (zero collision) but does not advance status.

**Defensive layer:** Before any agent writes a final artifact (e.g., `qa-review.md`), it pulls again and checks `state/active.json`. If the status moved on, it bails with a clear message.

> **V2 improvement — optimistic concurrency:** To make the defensive layer mechanical rather than convention-based, V2 will add a `version` (or `last_modified_sha`) field to `active.json`. Agents compare the version before writing; if it changed since their last read, the write is rejected with a clear message. This prevents silent overwrites without requiring locking.

### Scenario 3 — Two operators append to the same journal at the same place

**Setup:** Both pull. Both make Vikram append an entry to `memory/agents/backend.journal.md` at the same time.

**What happens:**

The `.gitattributes` file at the repo root sets:
```gitattributes
.engineering-os/memory/agents/*.journal.md merge=union
.engineering-os/memory/features/*.md merge=union
.engineering-os/decision-log/**/*.jsonl merge=union
.engineering-os/state/registry.json merge=union
```

`merge=union` tells git to take **both** sides when a conflict occurs on different lines of an append-only file. The merged file preserves both entries. **No human intervention needed.**

> If two operators happen to append the **same** line at the same time (true content collision), git keeps one. The journal is human-readable; redundancy is obvious and rare.

### Scenario 4 — `state/active.json` corruption

If the JSON file is corrupted (rare — most likely a malformed manual edit):

1. Plugin refuses to start (parse error).
2. `hooks/on-session-start.sh` surfaces: "state file corrupt; restore from `.engineering-os/state/active.json.bak.<ts>`".
3. The `.bak.<ts>` file is written **on every save** by the plugin, so an unbroken backup is always one revision behind.

### Scenario 5 — Force-push (DON'T) or history rewrite

This is the only thing that *can* corrupt the memory irretrievably.

**Policy:** Force-push to `main` is forbidden. CI rejects it. (V2: pre-receive hook on the upstream forbids it.)

---

## What gets read on session start

`hooks/on-session-start.sh` is the rehydration mechanism. Implementation:

```sh
#!/usr/bin/env bash
# hooks/on-session-start.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
STATE="$ROOT/.engineering-os/state/active.json"

if [ ! -f "$STATE" ]; then
  cat <<EOF
[engineering-os] No active.json found. Starting fresh.
EOF
  exit 0
fi

cat <<EOF
[engineering-os] Active requirements:
EOF
jq -r '.active_requirements[] | "  - \(.req_id) — Stage \(.stage) (\(.status)) — owner: \(.current_owner_persona)"' "$STATE"

cat <<EOF

[engineering-os] Recent journal activity (last 5 per agent):
EOF
for j in "$ROOT/.engineering-os/memory/agents/"*.journal.md; do
  agent=$(basename "$j" .journal.md)
  echo "  -- $agent --"
  tail -n 60 "$j" | head -n 30  # crude; V2 parses sections
  echo
done
```

This output is surfaced via Claude Code's session-start hook mechanism and becomes part of the conversation's opening context. The user sees a concise digest; agents, when invoked, can ask to read the full files.

> **Token discipline:** the digest is short (under 1k tokens). Agents load the full journal only when needed.

---

## What gets read by each agent on invocation

When a subagent (e.g., `architect`) is invoked, its system prompt instructs it to first:

1. **Read [`docs/business-context.md`](business-context.md) and [`docs/technical-context.md`](technical-context.md)** — the canon primers.
2. **Read its own journal:** `.engineering-os/memory/agents/architect.journal.md` (last 20 entries by default).
3. **Read the per-feature journal** for the feature it's about to work on: `.engineering-os/memory/features/feat-<slug>.md` (full).
4. **Read `.engineering-os/state/active.json`** to see status of the requirement.

These reads are **cheap** in plain markdown / JSON. They take a few hundred tokens unless the feature is unusually mature.

---

## What gets written by each agent on every action

The `hooks/on-post-tool-use.sh` hook (Claude Code post-tool-use event) auto-appends a journal entry after every meaningful tool use (Edit / Write / Bash with side effect). The agent can also write its own structured entries (preferred, because narrative is richer).

**Required fields on every entry:**
- ISO timestamp.
- Agent name + persona.
- `req_id` or `feat-slug` it's about.
- Stage.
- Action one-liner.
- Skills loaded.
- Decisions made.
- Verification commands + output.
- Handoff signal (if applicable).

> **Known limitation — auto-journal agent routing:** The `on-post-tool-use.sh` hook tries several env vars (`CLAUDE_AGENT_NAME`, `CLAUDE_SUBAGENT_TYPE`, `CLAUDE_CONTEXT_AGENT`) to determine which agent is running. If none are set (which is common in current Claude Code versions), entries are filed under `auto.journal.md`. This is a known safety-net limitation — **agents must still write their own structured journal entries** in their named file (e.g., `architect.journal.md`). Auto-journal entries are supplementary, not authoritative.

---

## Migration from "no memory" to "shared memory"

For a teammate joining mid-flight (say, joining when `feat-X` is in Stage 3):

1. **`git pull`** — receives every prior journal entry, every artifact, every decision log line.
2. **Open Claude Code** — session-start hook prints active digest.
3. **Run `/recall feat-X`** — prints the full per-feature journal.
4. **Run `/status`** — prints current stage + owner.
5. Begin work — agents the teammate invokes are *the same agents* with continuity.

No setup. No external sync.

---

## What about secrets?

Memory and decision log are **plain text in git**. **Secrets must never be committed.**

Discipline:
- The `on-post-tool-use.sh` hook redacts known token patterns (`sk-`, `xoxb-`, `AKIA…`, etc.) before writing journal entries.
- Agents are instructed (via system prompt) to never write secrets to artifacts.
- The pre-commit hook (V2) scans for common secret patterns and fails the commit if found.

OAuth tokens, API keys, and customer data live in environment variables and managed-secrets services — never in the engineering-os memory.

---

## What about size?

| Component | Growth rate | 1-year size |
|-----------|-------------|-------------|
| Journals | ~10 KB/feature | ~5 MB at 50 features/month |
| Decision log | ~1 KB/event, ~50 events/feature | ~1 MB |
| Run folder artifacts (markdown) | ~50 KB/feature | ~30 MB at 50 features/month |
| Run folder artifacts (large — perf reports, screenshots) | variable | git LFS recommended at >1 MB/file |

Total git-friendly footprint over a year: ~50 MB plain + LFS for big artifacts. Comfortable indefinitely.

**Archival policy (V2):**
- After 12 months, `runs/` older than 365 days move to `.engineering-os/archive/runs/<YYYY>/`.
- Journals and decision log stay forever (the moat).
- An `/archive` slash command runs the move + a CI check ensures no link rot.

---

## Disaster scenarios

| Scenario | Recovery |
|----------|----------|
| Repo deleted on remote | Any local clone has the full history. `git push` from a healthy clone restores it. |
| Local `.engineering-os/` deleted | `git checkout -- .engineering-os/` restores from the last commit. |
| One bad commit corrupts state | `git revert <sha>`; state restored. |
| `merge=union` produces a duplicate-line journal entry | Hand-edit; commit; move on. The duplication is human-readable. |
| State file backups all clobbered | Recreate `active.json` from `decision-log/` events (V2 helper). |

---

## How this differs from `~/.claude/memory/`

Claude Code's per-user memory system (`~/.claude/projects/.../memory/`) is **per-machine**. It does not survive `git pull` and is invisible to teammates.

The Brain Engineering OS uses **`.engineering-os/` in the repo** instead:
- Survives `git pull`.
- Visible to teammates.
- Auditable in git history.
- Multi-operator safe.

Per-user memory (`~/.claude/...`) is still useful for **personal preferences** ("Vikram prefers verbose journal entries"). The shared memory (`.engineering-os/...`) is for **work product**.

---

## Summary

- Memory = plain files in git.
- Append-only by default; the only mutable file is small and JSON.
- Git is the sync mechanism — no external service.
- Conflicts are rare, shallow, and (for journals + decision log) auto-resolved by `merge=union`.
- Every agent reads its journal at session start and on every invocation.
- The decision log is the queryable source of truth.

That's the entire model. Simple, durable, audit-friendly. It is exactly the same pattern Brain itself uses for the Decision Log + Brand Fingerprint — applied to the engineering team.
