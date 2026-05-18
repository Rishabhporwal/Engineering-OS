# Field Notes — Round 2 (Mid-Execution Snapshot, v0.3.0)

> **Source observation:** Brain product repo at `~/Desktop/Brain` running v0.3.0 plugin.
> **Window observed:** continuation past Round 1 (see [field-notes-2026-05-19-first-real-run.md](field-notes-2026-05-19-first-real-run.md)).
> **What's new:** Architect (Aryan) emitted a 27KB handoff brief; Vikram (Stage 3) executed Track 1 (commit `9a70b1b` — canon mirror); Track 2 files exist uncommitted; Track 3 not started.
> **Snapshot timestamp:** mid-execution, child #1 ~33% done.

---

## TL;DR Round 2

Round 1 missed five real issues that only show up *during* execution:

1. **D12 — Vikram is silent during execution.** Aryan handed off at 23:00:41Z. C1 committed at 03:12:02 local. No journal entry. No decision-log entry. The pipeline is technically "active" but observably indistinguishable from "stuck."
2. **D13 — Decision log is decoupled from git activity.** Real commits land without any `type: commit` event. Future audits will have to cross-reference git log + decision log to reconstruct what actually happened.
3. **D14 — Handoff doc is 500 lines for a 3-hour task.** Brilliant for child #1 (scope-creep risk). Will be a problem at scale (children #8/#9 with real refactor risk need different shape).
4. **D15 — Track 4 verification assumes the full 3-commit chain exists.** `git diff HEAD~3..HEAD` errors when only 1 commit has landed. Verification can't run incrementally.
5. **D16 — Aryan pre-computed SHA-256 values in the handoff.** This is *brilliant* (W9 below) but creates a race: if the plugin updates between Aryan's plan and Vikram's execution, Vikram will detect drift and stop. Need to lock the plugin version at plan time.

Plus three more things working better than expected (W8/W9/W10 below).

---

## New things working brilliantly (additions to Round 1)

### W8 — Aryan's handoff brief is operationally exemplary

The 27KB / ~500-line [`04-handoff-to-developer.md`](https://github.com/Rishabhporwal/Engineering-OS/blob/master/...) for child #1 contains:

- **Copy-paste-ready bash** for every track (mkdir, cp, sha256 loop, commit with full conventional message body).
- **Pre-filled ADR-001 scaffold** — Vikram doesn't author the ADR; he transcribes from CLAUDE.md tables and the canon's stack snapshot. Zero room for "creative" ADR drafting.
- **Pre-filled `docs/canon/README.md` scaffold** with all 12 SHA-256 values and the expected-broken-link baseline.
- **Pre-filled CLAUDE.md edit text** — exactly the markdown line to add, exactly where to add it.
- **"What you MUST NOT do" list** — 11 specific forbidden actions. No room for scope creep.
- **Time estimates per track** (45 min / 75 min / 30 min / 30 min = ~3 hours total). If anything exceeds 1.5× estimate → ping Aryan via decision log.
- **Escape hatches**: `type: clarification-needed` if blocked, `type: stop-and-ping-architect` if drifting.

This is how a staff engineer writes a brief for a junior. **Make this the default handoff pattern for high-risk-of-misinterpretation work.** Codify the structure (copy-paste bash, pre-filled scaffolds, MUST NOT lists, time estimates, escape hatches) in `templates/developer-handoff.md` (V2 addition).

### W9 — Upstream SHA-256 pre-computation in the handoff is a defensive masterpiece

From `04-handoff-to-developer.md`:
> "Authoritative reference: upstream SHA-256 values you must record in the Track 3 README table. These were computed by Aryan from the plugin cache at PoR time and are reproduced here so Vikram has a fixed expected baseline (your `/tmp/canon-upstream-shas.txt` from step 4 above must match these byte-for-byte)."
>
> [Table of 12 file → SHA-256 hashes]
>
> "If `/tmp/canon-upstream-shas.txt` does not match this table, **STOP and ping Aryan via the decision log** — the upstream plugin may have changed mid-flight and the version-pin of `0.3.0` is no longer accurate."

This is **brilliant** defensive engineering. Aryan locked the version at plan time, recorded the cryptographic fingerprints, and gave Vikram a literal STOP condition. Mid-flight plugin upgrades would otherwise be a silent contamination of the mirror. **This pattern should be a discipline for every cross-artifact transfer.**

### W10 — C1 commit + provenance headers landed cleanly

Sample mirrored file (`docs/canon/business-context.md`):
```html
<!-- MIRROR: do not edit in place. Source: brain-engineering-os@0.3.0 :: docs/business-context.md -->
<!-- Upstream SHA-256: 5475f877ec440ce38663bff062b36c138d2c79970ec8a8dccae12377defe3605 -->
<!-- Re-mirror recipe: see docs/canon/README.md -->

# Brain — Business Context (Agent Primer)
...
```

Vikram followed the provenance-header recipe byte-for-byte. The 4-line block is correct (3 HTML comments + 1 blank line). Future drift will be mechanically detectable. Discipline preserved.

### W11 — Aryan's deviations from the requirement are all journaled with reasoning

Aryan made 4 deviations from the requirement's literal text:
1. Mirrored 12 files (not 4) — cross-link graph
2. Used `docs/canon/` subtree (not flat `docs/*.md`) — namespace discipline
3. Two-axis Locked split (Today + Target) — genuine stack tension
4. Skipped Shreya Stage 4 — zero attack surface

**Every deviation is documented in `architect.journal.md` AND in `02-cto-advisor-review.md`-of-child AND flagged for "Founder visibility via Stage-2 return summary."** This is the anti-blind-agreement pattern applied to architectural deviations — *exactly* the discipline we want.

The deviation list also tells Founder: "here's what I changed about your ask, here's why, here's the surface for objection." If Founder disagrees with deviation #4 (skipped Shreya), one slash command bounces it back.

---

## New defects (additions to Round 1)

### D12 — Vikram (and any builder) is silent during execution

**Evidence:**
- Aryan's handoff: 23:00:41Z (clear `Next: Vikram begins Stage 3, ~3 hours`).
- C1 commit lands at 03:12:02 +0400 local (= 23:12:02 UTC) — **11 minutes after handoff**.
- `memory/agents/backend.journal.md` has **only the bootstrap entry** as of snapshot time. No Vikram entries.
- `decision-log/2026/05/2026-05-18.jsonl` has **no `actor: backend-developer` entries**.
- C2 files (`docs/adr/ADR-001-locked-stack.md`, `docs/adr/README.md`) exist in the working tree but are **uncommitted**.
- C3 files (`docs/canon/README.md`, CLAUDE.md edit) don't exist yet.

So Vikram has done one of:
- Done C1, written C2 files, not committed yet, is working on C3 → fine but silent.
- Done C1, written C2 files, then stopped → orphaned in-flight work, no signal.
- Done C1, then context lost → no way to know without asking Founder.

The handoff brief says journal *at handoff signal time* (after all 13 DoD pass). That means during multi-hour execution, the audit trail goes silent. For a 3-hour task that's tolerable; for a 3-day task (children #8 or #9) it's a real visibility hole.

**Fix candidates:**
- **F12a:** Per-commit journal protocol — after every commit, append a 5-line journal entry: `## <ts> — Vikram — <req_id> — C1 LANDED. Commit <sha>. Track 1 done. Track 2 starting.`
- **F12b:** Per-30-min "I'm still working" heartbeat — append `## <ts> — Vikram — <req_id> — IN-FLIGHT. Currently on Track 2 step 4. ETA: 30 min.`
- **F12c:** Pre-commit git hook auto-journals the commit (decoupled from agent attention).
- **F12d:** All of the above, in order of preference (F12a is the minimum bar; F12c is the safety net).

**Recommendation:** F12a as protocol (cheap discipline), F12c as backstop (no agent forgetfulness).

**Severity:** MEDIUM — works fine in a single-operator setup; breaks the moment two teammates share a repo and one tries to read `/status` while the other is executing.

---

### D13 — Decision log is decoupled from git activity

**Evidence:**
- Git log shows commit `9a70b1b docs(canon): mirror plugin canon docs from brain-engineering-os@0.3.0`.
- Decision log has 8 events: intake, stage-1-review, founder-decision, intake (child), stage-1-review (child), handoff (CTOA→architect), stage-2-plan, handoff (architect→backend-developer).
- **No `type: commit` event** anywhere in the decision log.
- **No correlation between the C1 commit SHA and any decision-log entry.**

This breaks "single source of truth" for the audit trail. Reconstruct "what code shipped for this requirement?" requires:
- Read decision log for `req_id`
- Read journals for `req_id`
- Cross-reference git log on date/time
- Manually map commits to stages

At 11 children × multiple commits each, this gets painful. The decision log was supposed to be the queryable index.

**Fix candidates:**
- **F13a:** Add `type: commit` to the decision-log schema. Vikram appends one per commit (with the SHA).
- **F13b:** Post-commit git hook auto-appends to decision-log with commit metadata.
- **F13c:** Both — agent appends rich entry on intentional commits; hook is backstop for forgetfulness.

**Severity:** LOW (audit cost; doesn't break anything operationally).

---

### D14 — Handoff doc verbosity is uncalibrated to risk

**Evidence:** 27KB / 500 lines of handoff for a 3-hour pure-docs task. Includes:
- 12-row pre-computed SHA-256 table (justified — defensive).
- 130-line ADR-001 scaffold (Vikram doesn't author it — he transcribes).
- 80-line `docs/canon/README.md` scaffold (similarly transcribe-only).
- 30-line CLAUDE.md edit text.

For child #1: this verbosity *is* the value. The work is "type carefully without thinking" — exactly the case where Aryan should pre-think everything.

But this creates a precedent risk. Children #8 and #9 are real refactors (carve Python ingestion service, carve Python analytics service). If Aryan emits 500-line briefs for those, two failure modes:
1. The brief is wrong in details Aryan couldn't anticipate (because real refactors discover things), and Vikram blindly follows it → bad code.
2. The brief is so prescriptive that Vikram becomes a typist and never builds the judgment to do the next service carve unsupervised.

**Fix:** Codify a "handoff depth" calibration in the architect's prompt. Add to `agents/architect.md`:

> **Handoff depth calibration.** Match handoff verbosity to risk profile:
> - **Pure docs / scope-creep-prone work** (canon mirrors, ADR drafts, naming conventions): write a *prescriptive* handoff (~400+ lines). Copy-paste bash, pre-filled scaffolds, MUST NOT lists. Block scope creep mechanically.
> - **Bounded refactor / well-understood pattern** (RegionAdapter interface, metric registry layout): write a *guided* handoff (~150-250 lines). Architecture sketch, file targets, key interfaces. Builder fills in implementation details with judgment.
> - **Real refactor / discovery-heavy work** (service carves, dual-write windows, shadow validations): write a *terse* handoff (~80-150 lines). Goal, success criteria, hard constraints, escape hatches. Builder owns the implementation discovery.
>
> Anti-pattern: emitting a 500-line brief for discovery-heavy work because that's what you did last time. The brief is wrong in details you couldn't anticipate, and the builder loses the judgment to navigate the unknowns.

**Severity:** MEDIUM (won't bite child #1; will bite child #8 silently — the wrong handoff will produce wrong code and nobody will notice the brief was the source).

---

### D15 — Track 4 verification not idempotent

**Evidence:** Aryan's Track 4 step 3:
```bash
git diff --stat HEAD~3..HEAD -- frontend/app frontend/components frontend/lib frontend/hooks backend/src backend/prisma
```

This errors when only 1 commit has landed (HEAD~3 doesn't exist). It assumes the full 3-commit chain is present.

For child #1 it's fine — Track 4 is the final gate. But:
- It can't be run incrementally to check work-in-progress.
- It hardcodes the commit count (3). If Vikram needs 4 commits (e.g., a fixup), the diff command needs editing.
- If anyone amends a commit (despite the brief saying don't), the SHA chain breaks and `HEAD~3..HEAD` doesn't span what Aryan thought.

**Fix:** Use a baseline branch reference instead of commit count:
```bash
git diff --stat HEAD..main -- frontend/app ...    # or origin/master..HEAD
```

Or compute against the commit that started the run (recorded in the run folder metadata).

**Severity:** LOW (cosmetic; the verification still works at the end of the chain).

---

### D16 — Plugin-version race during execution

**Evidence:** Aryan's handoff pre-computed 12 SHA-256 values from the plugin at *plan time* (23:00:41Z). Vikram executes hours later. If the plugin is updated mid-flight (e.g., I push v0.3.1 to fix the bugs in Round 1), Vikram's `cp -R ~/.claude/plugins/cache/.../0.3.0/docs/*.md` either:
- Still works if the marketplace cache hasn't pulled the update (likely — manual `/plugin update` is required).
- Or fails if Vikram ran `/plugin marketplace update` between Aryan's plan and his own execution.

Aryan's defensive STOP condition catches this — Vikram's `shasum` will diverge from the table and he'll halt. But it's a halt, not a graceful "use the new version." The whole plan is invalidated.

**Fix candidates:**
- **F16a:** Lock the plugin cache directory pin at plan time. Aryan records `~/.claude/plugins/cache/brain-engineering-os-marketplace/brain-engineering-os/0.3.0` (literal version path) so even if `0.3.1` is installed alongside, Vikram reads from `0.3.0`.
- **F16b:** Have the agent prompt forbid `/plugin update` while a requirement is in `stage 3` (dev-active) for any child.

**Recommendation:** F16a (path-pinning is the cleaner fix; F16b requires user discipline).

**Severity:** MEDIUM (could silently corrupt the mirror if Vikram doesn't notice the divergence; the STOP catches it but is a hard halt).

---

## Re-confirmed from Round 1 (still true after re-observation)

- **D1 (CTO Advisor can't spawn subagents)** confirmed: Aryan was invoked manually by Founder after CTOA emitted `HANDOFF-TO-ARCHITECT.md`. Same pattern repeats for Vikram (Aryan's handoff → Founder manually invokes `/brain-engineering-os:backend-developer`). The pipeline is bouncing through Founder at every stage transition.
- **D2 (unknown.journal.md noise)** confirmed: file continues to grow with auto-trace bash calls; agent attribution still broken.
- **D3 (Stage skips without codified exception)** confirmed: Aryan's handoff to Vikram now also encodes "Stage 4 skipped → go directly to Tanvi." The pattern is now embedded in 2 artifacts.

---

## Updated fix priority (Round 1 + Round 2)

| Priority | Fix | Effort | Why |
|---|---|---|---|
| **P0** | F2b — drop the auto-journal hook | 10 min | Highest noise reduction; no risk |
| **P0** | F12a + F13a — per-commit journal + decision-log protocol | 30 min | Closes mid-execution visibility hole + audit gap |
| **P0** | F3b — codify gate-runs-always-but-can-be-trivial | 30 min | Prevents discipline rot |
| **P1** | F1a — show Agent tool usage explicitly in CTOA prompt | 1–2 h | Restores pipeline auto-flow |
| **P1** | F14 — handoff-depth calibration in architect prompt | 30 min | Prevents future-child failure mode |
| **P1** | F16a — plugin-cache path pinning at plan time | 30 min | Prevents silent mirror corruption |
| **P2** | F4b — descriptive filenames | 1 h | Removes audit ambiguity |
| **P2** | F6 — roll Aryan's additions into the template | 1 h | Raise the floor |
| **P3** | F12c — post-commit git hook backstop | 1 h | Safety net for forgetfulness |
| **P3** | F15 — Track 4 idempotent verification | 20 min | Cosmetic |
| **P3** | F7a, F8, F9, F5, F11 — small items from Round 1 | ~1.5 h total | Polish |

Total v0.3.1 scope (P0 + P1): ~5 hours.
Total v0.3.2 scope (P2 + P3): ~5 hours.

---

## What to specifically codify into `agents/architect.md` for v0.3.1

Based on what Aryan did right and what he over-did:

```markdown
## Handoff brief calibration (NEW for v0.3.1)

Match handoff brief depth to risk profile of the work:

| Work type | Brief shape | Length |
|---|---|---|
| Pure docs / scope-creep-prone (ADRs, canon mirrors, naming) | Prescriptive — copy-paste bash, pre-filled scaffolds, MUST NOT lists | ~400+ lines |
| Bounded refactor (interfaces, registry layouts) | Guided — architecture sketch, file targets, key interfaces | ~150-250 lines |
| Discovery refactor (service carves, dual-writes) | Terse — goal, success criteria, hard constraints, escape hatches | ~80-150 lines |

**Always include in any handoff** (regardless of length):
1. Reproducible reference values for any cross-artifact transfer (file SHAs, schema hashes, contract checksums).
2. Explicit STOP conditions ("if X diverges, ping me via decision log; don't guess").
3. Escape hatches (`type: clarification-needed`, `type: stop-and-ping-architect`).
4. Time estimate per track + ping-threshold ("if anything exceeds 1.5× estimate, ping").
5. The handoff signal protocol the next agent uses at completion.
```

And to `agents/backend-developer.md` (and the other dev agents):

```markdown
## Mid-execution journaling protocol (NEW for v0.3.1)

You are NOT allowed to go silent during multi-track execution. Required signals:

1. **At track start:** append a journal entry (`## <ts> — <persona> — <req_id> — Track N STARTING. ETA: <time>.`).
2. **After every commit:** append a journal entry AND a decision-log event:
   ```json
   {"ts":"...","actor":"<persona>","type":"commit","req_id":"...","commit_sha":"<sha>","track":"N","subject":"<commit subject>"}
   ```
3. **If blocked for >30 min:** append `## <ts> — <persona> — <req_id> — BLOCKED on <specific question>. Pinging <architect|cto-advisor> via decision log.`
4. **At handoff:** append a structured journal entry + decision-log event per the template in your role doc.

The decision log + journal together must let any teammate run `/status` mid-execution and learn:
- Which track you're on.
- Last commit SHA.
- Estimated time remaining.
- Whether you're blocked.
```

These two additions, plus the P0 noise reduction, would cleanly close the gaps observed in Round 2.

---

## Reading order for Round 2 → v0.3.1 fix sprint

1. Read [field-notes-2026-05-19-first-real-run.md](field-notes-2026-05-19-first-real-run.md) — Round 1 findings.
2. Read this file — Round 2 mid-execution findings.
3. Decide priority cutoff with Founder.
4. Ship v0.3.1 with at least P0 items.
5. Re-observe Brain repo on next child (child #2, RegionAdapter) — that one has real refactor risk and will surface different defects.
