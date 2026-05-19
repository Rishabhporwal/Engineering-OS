# Phase 5 — Validation Checklist

> Run this when you're ready to validate v0.3.1 → v0.4.0 against a real requirement. Each step has a PASS/FAIL outcome; capture results in `docs/field-notes-2026-05-DD-validation.md` (replace DD with actual date).

---

## Pre-validation (Founder side — Phase 0)

Complete BEFORE running validation. Without these, validation can't measure what we shipped.

- [ ] **0.1 Recover lost commits.** `cd ~/Desktop/Brain && git reflog | head -30` → find last good SHA (likely `530926a`). `git reset --hard <sha>` to restore. Or commit working tree manually. Verify with `git log --oneline -15` showing the recovered work.
- [ ] **0.2 Decide child #3 disposition.** Either restart cleanly (recommended — preserves dependency chain), accept skip + update meta-tracker, or merge into child #4 scope retroactively.
- [ ] **0.3 Decide child #4 disposition.** Either accept the out-of-order ship (with logged Founder-override-of-dependency-rule), or revert child #4's work (working tree only).
- [ ] **0.4 Fix GitHub 403.** Diagnose: `git remote -v`, `git push --dry-run`, check SSH keys / PAT scopes. Push succeeds.
- [ ] **0.5 Update plugin in your Claude Code session.** `/plugin marketplace update brain-engineering-os-marketplace` → `/plugin update brain-engineering-os` → confirm `0.4.0` in `/plugin` Installed tab. Then `/reload-plugins`.
- [ ] **0.6 Verify `.engineering-os/` scaffold includes the v0.4.0+ pieces.** Check that `.engineering-os/durable-rules/`, `.engineering-os/rule-proposals/`, `.engineering-os/lessons-learned.md`, `.engineering-os/pending-founder-attention.md` all exist. If missing, run `/brain-engineering-os:eos-init` again (it's idempotent for these v0.4.0 paths).

## Validation requirement

Use this exact test requirement (low-stakes, validates the full pipeline):

```
/brain-engineering-os:requirement Add a simple health-check endpoint at GET /health that returns {status:"ok", time:<UTC>} from the existing Express backend. Single endpoint, no auth, no DB call. Wire to existing Express app in backend/src/.
```

## Expected behaviors (each should PASS)

### Pre-flight gates

- [ ] **G0 dependency check** runs. CTOA reads `proposed_children` block in parent if applicable; this is a standalone req so it has no blockers.
- [ ] **Persona count decision** is RECORDED in `02-cto-advisor-review.md` under "Persona-count decision" section. For this requirement (trivial new endpoint), expected count is **0 or 1**. If CTOA spawns 3 or more, v0.3.2 didn't land.
- [ ] **Lessons-learned read** at Stage 1. CTOA cites any applicable lessons in `02-cto-advisor-review.md` under "Lessons applied" section.
- [ ] **Durable rules read** at Stage 1. CTOA's review references commit-discipline rule + plan-first/self-review rule + no-over-engineering rule.

### Autonomous flow

- [ ] **CTOA auto-invokes Architect** via `Agent(subagent_type="architect", ...)`. No `HANDOFF-TO-ARCHITECT.md` file written (unless Agent call fails — record fallback).
- [ ] **Architect auto-invokes Backend Developer** via `Agent(subagent_type="backend-developer", ...)`.
- [ ] **Backend Developer auto-invokes Security Reviewer** OR (since this is .ts code) Stage 4 runs fully (not skipped — code touches `backend/src/`).
- [ ] **Security auto-invokes QA.**
- [ ] **QA auto-invokes CTOA Stage 6.**
- [ ] **CTOA Stage 6 auto-invokes Platform-DevOps OR surfaces to Founder** (depends on delegation status).
- [ ] You (Founder) only intervene at Stage 7 (approval) and at Stage 8d (after Jatin stages, you commit + push).

### Plan-first + self-review

- [ ] **Every agent's primary artifact has a "Plan" section** (TodoWrite snapshot or `<stage>-plan.md` referenced).
- [ ] **Every agent's primary artifact has a "Self-review" section** with in-lane DoD line-by-line and captured command output.

### Commit discipline

- [ ] **No agent runs `git commit` on product code.** Verify with `git log --oneline -20` after the run — only the `chore(eos):` audit-trail commit by Jatin should be agent-attributed.
- [ ] **No `git reset`, `git rebase`, `git commit --amend`, or `git push --force`** appears in `unknown.journal.md` or any agent's command history.
- [ ] **`.engineering-os/` audit trail IS committed** by Jatin at Stage 8b.
- [ ] **Product code is staged for you** with `git add <explicit paths>`. `git diff --cached --stat` shows the staged set after Stage 8a.

### Gate codification

- [ ] **Stage 4 runs full review** (because this requirement touches `backend/src/` — a code file, not a doc). Tanvi's QA does NOT skip-acknowledgment-only.
- [ ] **Tanvi's QA review has a "Skipped-gates re-verified" section** even if empty.
- [ ] **CTOA Stage 6 has a "Re-verified Stage 5 gates" section** with at least 3 gates re-run + captured output.
- [ ] **CTOA Stage 6 has an "Over-engineering audit" section** (per v0.3.3 rule).

### Infra hygiene

- [ ] **Run folder name has `<hex6>` suffix.** Pattern: `runs/<ts>__<hex6>__feat-...__rishabh/`.
- [ ] **All timestamps in journals + decision-log are UTC + Z-suffix.** No IST. No timezone-less.
- [ ] **Push-success gate fires.** State moves to `shipped` ONLY after `git push --dry-run` succeeds. If push gate fails (e.g., another auth issue surfaces), state should be `awaiting-push-fix`, NOT `shipped`.

### Self-improvement substrate (v0.4.0)

- [ ] **`14-retro.md` exists** in the run folder after Stage 6. Written by CTOA. Has all 5 sections (what worked / didn't work / surprised / lessons / action items / calibration).
- [ ] **At least one lesson appended to `.engineering-os/lessons-learned.md`** sourced from this retro.
- [ ] **No spurious rule proposals filed** (this is a small requirement; team shouldn't be proposing rules for it).

## What to capture in Field Notes Round 3

In `docs/field-notes-2026-05-DD-validation.md`:

1. **PASS/FAIL per check** above with one-line evidence each.
2. **Any new defects observed** — name + severity + recommendation (D27, D28, etc. continuing the field-notes numbering).
3. **Any new strengths observed** — codify next time (W18, W19, etc.).
4. **Any rule proposals that emerged.**
5. **Throughput measurement** — handoff → C1 time, total Stage 3 time, total pipeline time. Compare to children #1/#2/#4.
6. **Token cost measurement** if available — should be lower per the persona calibration (0/1/2 vs 3).
7. **Overall verdict** — does v0.4.0 ship cleanly, or do we need a v0.4.1?

## If something regresses

If any expected behavior PASS fails: do not rush to fix. Capture evidence first. The regression is more useful as data than as a fire to put out — it tells you whether the codified rule is being followed correctly by the agents (interpretation problem) or whether the rule itself was wrong (design problem). Bring the field-notes findings back and we ship v0.4.1 with the targeted fix.
