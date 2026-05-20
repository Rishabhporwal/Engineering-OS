---
name: finishing-a-development-branch
description: The end-of-work discipline for Brain — commit boundaries (product code vs `.engineering-os/` audit trail), explicit-path staging (never `git add -A`), the no-history-rewrite rule, the push-success gate, and the reversibility recipe. Consolidates the scattered commit-discipline rules into one place. Adapted from the superpowers finishing-a-development-branch pattern. Auto-load when Jatin runs Stage 8, or any time an agent is about to stage/commit/push.
---

# Finishing a Development Branch

> The last mile is where work gets lost. A careless `git add -A`, an `--amend` on a pushed commit, or a `reset --hard` over uncommitted work destroys more than a bug ever does.

This is the operational depth behind the **Commit discipline durable rule (2026-05-19)** and Jatin's Stage 8. It exists because the team once wiped real work with a stray `git reset` — never again.

## The Iron Laws

```
1. AGENTS DO NOT COMMIT PRODUCT CODE. You stage it; the Founder commits it.
2. AGENTS DO COMMIT THE `.engineering-os/` AUDIT TRAIL — as a chore(eos) commit, no approval needed.
3. NEVER REWRITE HISTORY: no reset --hard, rebase, commit --amend, push --force. Ever.
4. STAGE EXPLICIT PATHS. Never `git add -A` or `git add .`.
5. STATE MOVES TO `shipped` ONLY AFTER PUSH SUCCEEDS.
```

Violating any of these is violating the spirit of the rule, not a clever shortcut.

## Why the product/audit-trail split

| What | Who commits | Why |
|---|---|---|
| Product code (everything outside `.engineering-os/`) | **Founder** | Founder owns what ships; agents propose, the human decides. |
| `.engineering-os/` audit trail (run folder, journals, decision log, state) | **Agent (Jatin)** as `chore(eos):` | It's the record of what the team did; it must flow automatically or `/status` goes stale. |

Two commits, never one mixed commit. (See the Brain recovery on 2026-05-20: `feat(monorepo)` for product, `chore(eos)` for the audit trail — separate commits.)

## The finishing sequence

```
1. STAGE (product) — explicit paths only:
   git status                       # confirm tree matches the dev report's file list
   git add <path1> <path2> ...      # NEVER -A / . ; exclude .engineering-os
   git diff --cached --stat         # verify the staged set is exactly what you intend

2. INTEGRITY GATES — run + capture output (per verification-before-completion):
   build, typecheck, lint, app-code-diff sentinel. No green claim without evidence.

3. WRITE the deployment report (STAGE-ONLY mode):
   - list staged files explicitly
   - propose commit message(s) for the Founder (split per dev report, or single squash)
   - document the reversibility recipe

4. COMMIT (audit trail only — you do this):
   git add .engineering-os/
   git commit -m "chore(eos): pipeline state for <req-id>"
   # do NOT push yet

5. HAND OFF to Founder: status `awaiting-founder-commit`, current_owner `founder`.

6. AFTER Founder commits + pushes:
   git push --dry-run               # verify remote is current
   - verified  → state `shipped`
   - push fails (e.g. 403) → state `awaiting-push-fix`, surface the failure mode explicitly
```

## Staging discipline — why explicit paths

`git add -A` sweeps in whatever happens to be in the tree: build caches (`.turbo/`, `dist/`), editor settings, secrets, half-finished files. Stage the exact paths from the dev report. If a cache dir keeps showing as untracked, gitignore it — don't sweep it in. (Brain recovery example: `.turbo/` was not gitignored and would have been committed by a blind `add -A`.)

## The reversibility recipe (put it in every deployment report)

Before anything risky, document how to undo it:

- **Un-commit (keep changes):** `git reset --soft HEAD~1` (soft — never `--hard`).
- **Roll back a deploy:** ArgoCD rollback to the previous synced revision.
- **Revert a merged change:** `git revert <sha>` (a new commit; never rewrite).

If you can't write the undo step, you don't understand the change well enough to ship it.

## Push-success gate

`shipped` is a claim that the code is on the remote. You cannot claim it from a local commit. Run `git push` (Founder) then `git push --dry-run` (verify "up to date"). If the push 403s or fails, the state is `awaiting-push-fix`, not `shipped` — surface the exact failure so the Founder can fix access. (Brain: pushes 403 because the account lacks org write access — that's `awaiting-push-fix`, never silently `shipped`.)

## Red flags — STOP

- About to run `git add -A` / `git add .` — stop, list explicit paths.
- About to `git reset --hard`, `rebase`, `commit --amend`, or `push --force` — stop, you don't rewrite history.
- About to commit product code as an agent — stop, you stage; Founder commits.
- About to mark `shipped` from a local commit — stop, push must succeed first.
- A mixed commit with product code AND `.engineering-os/` in it — split it.
- Uncommitted work in the tree before a risky op — commit/stash to lock it in first.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "`git add -A` is faster" | It's faster until it commits a secret or a 200MB cache. Explicit paths. |
| "`--amend` keeps history clean" | On a pushed commit it rewrites shared history and can destroy a teammate's pull. New commit instead. |
| "I'll just `reset --hard` to clean up" | `--hard` discards uncommitted work with no undo. Use `--soft`, or `git revert`. |
| "It's committed locally, so it shipped" | Local ≠ remote. `shipped` requires a successful push. |
| "One commit is simpler than two" | Mixing product + audit trail makes the Founder review the wrong diff and breaks the chore(eos) convention. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Stage 8 finishing sequence | **Jatin** (platform-devops) | his operating loop |
| The commit-discipline rule | universal (all agents) | `prompts/system-prompt.md` §Commit discipline |
| Verification before the green claim | the finishing agent | `verification-before-completion` |
| Deploy rollback | Jatin | `devops-aws`, `operational-readiness` |

## The bottom line

Stage explicit product paths for the Founder; commit only the `.engineering-os/` audit trail yourself; never rewrite history; and don't say `shipped` until the push succeeds. The last mile is where discipline matters most.

Related: `verification-before-completion` (the green-claim gate), `subagent-orchestration` (this is the final stage), `operational-readiness` (pre-ship checklist), `devops-aws` (deploy + rollback).
