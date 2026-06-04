---
name: finishing-a-development-branch
description: End-of-work discipline — commit boundaries (product vs `.engineering-os/` audit trail), explicit-path staging (never `git add -A`), no history rewrite, push-success gate, reversibility recipe.
---

# Finishing a Development Branch

> The last mile is where work gets lost. A careless `git add -A`, an `--amend` on a pushed commit, or a `reset --hard` over uncommitted work destroys more than a bug ever does.

Operational depth behind the **Commit discipline durable rule (2026-05-19)** and Jatin's Stage 8. It exists because the team once wiped real work with a stray `git reset`.

## The Iron Laws

```
1. AGENTS DO NOT COMMIT PRODUCT CODE. You stage it; the Founder commits it.
2. AGENTS DO COMMIT THE `.engineering-os/` AUDIT TRAIL — as a chore(eos) commit, no approval needed.
3. NEVER REWRITE HISTORY: no reset --hard, rebase, commit --amend, push --force. Ever.
4. STAGE EXPLICIT PATHS. Never `git add -A` or `git add .`.
5. STATE MOVES TO `shipped` ONLY AFTER PUSH SUCCEEDS.
```

## Why the product/audit-trail split

| What | Who commits | Why |
|---|---|---|
| Product code (outside `.engineering-os/`) | **Founder** | Founder owns what ships; agents propose, the human decides. |
| `.engineering-os/` audit trail (run folder, journals, decision log, state) | **Agent (Jatin)** as `chore(eos):` | The record of what the team did; must flow automatically or `/status` goes stale. |

Two commits, never one mixed commit. (2026-05-20 recovery: `feat(monorepo)` for product, `chore(eos)` for audit trail — separate.)

## The finishing sequence

```
1. STAGE (product) — explicit paths only:
   git status                       # confirm tree matches the dev report's file list
   git add <path1> <path2> ...      # NEVER -A / . ; exclude .engineering-os
   git diff --cached --stat         # verify the staged set is exactly intended
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/secret_scan.py --staged   # O1 GATE on PRODUCT code too — the Founder commits this later, so a secret must be caught HERE. Exit 1 → unstage, redact, retry. NEVER hand off past this.
2. INTEGRITY GATES — run + capture output (per verification-before-completion):
   build, typecheck, lint, app-code-diff sentinel. No green claim without evidence.
3. WRITE the deployment report (STAGE-ONLY mode): list staged files; propose commit
   message(s) for the Founder; document the reversibility recipe.
4. COMMIT (audit trail only — you do this):
   git add .engineering-os/
   uv run ${CLAUDE_PLUGIN_ROOT}/tools/secret_scan.py --staged   # O1 GATE — fail-closed; if exit 1, a secret is staged: unstage, redact, retry. NEVER commit past this.
   git commit -m "chore(eos): pipeline state for <req-id>"   # do NOT push yet
5. HAND OFF to Founder: status `awaiting-founder-commit`, current_owner `founder`.
6. AFTER Founder commits + pushes:
   git push --dry-run               # verify remote is current
   - verified  → state `shipped`
   - push fails (e.g. 403) → state `awaiting-push-fix`, surface the failure mode explicitly
```

## Staging discipline — why explicit paths

`git add -A` sweeps in build caches (`.turbo/`, `dist/`), editor settings, secrets, half-finished files. Stage the exact paths from the dev report. If a cache dir keeps showing as untracked, gitignore it — don't sweep it in. (Recovery example: `.turbo/` was not gitignored and would have been committed by a blind `add -A`.)

## The reversibility recipe (in every deployment report)

- **Un-commit (keep changes):** `git reset --soft HEAD~1` (soft — never `--hard`).
- **Roll back a deploy:** ArgoCD rollback to the previous synced revision.
- **Revert a merged change:** `git revert <sha>` (a new commit; never rewrite).

If you can't write the undo step, you don't understand the change well enough to ship it.

## Push-success gate

`shipped` is a claim that the code is on the remote — you can't claim it from a local commit. Run `git push` (Founder) then `git push --dry-run` (verify "up to date"). If the push 403s or fails, the state is `awaiting-push-fix`, not `shipped` — surface the exact failure so the Founder can fix access.

## Red flags — STOP

- About to run `git add -A` / `git add .` — list explicit paths.
- About to `reset --hard`, `rebase`, `commit --amend`, or `push --force` — you don't rewrite history.
- About to commit product code as an agent — you stage; Founder commits.
- About to mark `shipped` from a local commit — push must succeed first.
- A mixed commit with product code AND `.engineering-os/` — split it.
- Uncommitted work in the tree before a risky op — commit/stash to lock it in first.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "`git add -A` is faster" | Until it commits a secret or a 200MB cache. |
| "`--amend` keeps history clean" | On a pushed commit it rewrites shared history. New commit instead. |
| "I'll just `reset --hard`" | Discards uncommitted work with no undo. Use `--soft` or `git revert`. |
| "It's committed locally, so it shipped" | Local ≠ remote. `shipped` requires a successful push. |
| "One commit is simpler than two" | Mixing product + audit trail makes the Founder review the wrong diff. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Stage 8 finishing sequence | **Jatin** | his operating loop |
| The commit-discipline rule | universal | `prompts/system-prompt.md` §Commit discipline |
| Verification before the green claim | the finishing agent | `verification-before-completion` |
| Deploy rollback | Jatin | `devops-aws`, `operational-readiness` |

Related: `verification-before-completion`, `subagent-orchestration`, `operational-readiness`, `devops-aws`.
