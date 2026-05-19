# Brain Engineering OS — Improvement Plan v0.3.1 → v0.5.0

> **Goal:** Transform the team from *"high-quality work, weak process glue"* to *"high-quality work, self-improving operating system."*
>
> Source observations: [field-notes-2026-05-19-first-real-run.md](field-notes-2026-05-19-first-real-run.md) (Round 1), [field-notes-2026-05-19-round-2-mid-execution.md](field-notes-2026-05-19-round-2-mid-execution.md) (Round 2), and [brain-monitoring/2026-05-19-live-monitor-log.md](brain-monitoring/2026-05-19-live-monitor-log.md) (live monitoring of children #1–#4).

---

## Three principles guiding every change

1. **Don't break what's working.** Agent quality, anti-blind-agreement, structured journaling, and review rigor are already excellent. Preserve them.
2. **Codify the patterns the team already exhibits informally.** Most fixes turn implicit good behavior into explicit required protocol. Tanvi re-ran Shreya's skipped gates; codify that. CTOA re-ran Tanvi's gates; codify that. The team self-corrected on `.engineering-os/` un-committed; codify that.
3. **Build self-improvement substrate, not just bug fixes.** Every fix should leave the team better-equipped to find its own next defect. Memory IS the moat; the moat must include lessons learned.

---

## Where we are vs where we're going

### Current state (v0.3.0)
- ✅ Agents do thoughtful, code-grounded work.
- ✅ Reviews are rigorous and independent (Tanvi re-runs Shreya, Rohan re-runs Tanvi).
- ✅ Anti-blind-agreement actually fires (4 deviations with written justification on child #1; 2 more on child #2).
- ✅ Team self-corrects organically (D2 noise + D17 audit trail both fixed without prompting).
- ⚠️ Pipeline doesn't flow autonomously (every stage transition needs human prompting — D1).
- ⚠️ Dependency violations can pass silently (child #4 shipped while child #3 orphaned).
- ⚠️ Commit discipline confused (no-auto-commit rule overshot; reset wiped 10 commits).
- ⚠️ Stage gates can be skipped without codified exception.
- ⚠️ Audit trail gets stuck in working tree, never reaches remote (GitHub 403 not gating Stage 8).

### Target state (v0.5.0)
- All current ✅ items preserved.
- Pipeline runs autonomously end-to-end — only Founder gates require Founder.
- Dependency violations are caught mechanically before children can advance.
- Commit discipline is explicit and well-scoped: code commits gate on Founder, audit-trail commits flow automatically.
- Push failures are first-class state (`awaiting-push-fix`), not silent.
- Every child ends with a retro that feeds the next child's intake (compounding learning).
- Team can propose changes to its own operating rules through a formal channel (Founder approves).
- Three children's worth of operational lessons compound into v0.5.0's release readiness.

---

## Phasing overview

| Phase | Owner | Effort | What ships |
|---|---|:---:|---|
| **Phase 0** | Founder | 30 min | Brain repo unblocked: commits recovered, child #3/#4 disposition, GitHub 403 fixed, "no commits" rule clarified |
| **Phase 1** | Plugin (me) | 3–4 h | Pipeline mechanics: subagent spawning, dep-check gate, push-success gate, decision-log commit events, audit-trail commit protocol |
| **Phase 2** | Plugin (me) | 4–5 h | Self-improvement substrate: retros, lessons-learned registry, rule-proposal mechanism, Founder visibility for proposed changes |
| **Phase 3** | Plugin (me) | 2–3 h | Process codification: gate skip rules, re-run protocols (W13/W14), pre-flight check at intake |
| **Phase 4** | Plugin (me) | 1–2 h | Infrastructure hygiene: UTC timestamps, unique run folders, agent attribution fix, Sonnet/Opus investigation |
| **Phase 5** | Founder + Plugin | 1–2 h | Validation: run one real requirement through Brain end-to-end; capture observations; iterate |

**Total plugin work:** ~10–14 hours.
**Total Founder time:** ~1 hour + the validation run.

---

## Phase 0 — Brain repo unblock (Founder side, today)

**Why first:** nothing else matters if the Brain repo has lost commits and uncommitted working trees. Stabilize ground truth before fixing the system that sits on top.

### Actions

| # | Action | Owner | How |
|---|---|---|---|
| 0.1 | Recover the 10 lost commits | Founder | `cd ~/Desktop/Brain && git reflog \| head -20` → identify last good SHA (likely `530926a`) → `git reset --hard 530926a` |
| 0.2 | Decide child #3 disposition | Founder + me | Either (a) restart child #3 cleanly with a fresh intake; or (b) accept skip + update meta-tracker; or (c) merge into child #4's scope retroactively |
| 0.3 | Decide child #4 disposition | Founder + me | Either (a) accept the out-of-order ship with a logged "Founder override of dependency rule"; or (b) revert child #4's work (working tree only — no commits to revert) |
| 0.4 | Fix GitHub 403 | Founder | Likely cause: SSH/HTTPS auth mismatch, expired PAT, or org-permission change. Diagnose with `git remote -v` + `git push --dry-run` + check `~/.ssh/` keys |
| 0.5 | "No auto-commit" rule scope (Founder clarified 2026-05-19) | Founder + me | Rule: agents may NOT `git commit` product code; agents MUST `git commit` `.engineering-os/` audit trail; agents may NEVER rewrite git history. Codified in `prompts/system-prompt.md` § "Commit discipline" and `agents/platform-devops.md` § "Operating loop" — already shipped in v0.3.1-dev |

### Verification
- `git log --oneline -15` shows the recovered commits.
- `git push origin master --dry-run` returns success (or a precise error we can fix).
- `state/active.json` reflects child #3 + #4's chosen disposition.
- `.engineering-os/durable-rules/2026-05-19-commit-approval.md` exists with clarified scope.

---

## Phase 1 — Pipeline mechanics (plugin, 3–4 hours)

**Why second:** the biggest throughput multiplier. With autonomous pipeline flow, every other improvement becomes more visible.

### Phase 1.1 — Subagent spawning (fixes D1)

**Problem:** When CTOA finishes Stage 1, it can't programmatically invoke the Architect. It writes `HANDOFF-TO-ARCHITECT.md` and waits for the user to manually run `/brain-engineering-os:architect`. Same at every stage transition.

**Root cause:** CTOA's agent file has `tools: [..., Agent]` but the `Agent` tool isn't being plumbed through to nested subagent threads in Claude Code v2.1.143.

**Fix candidates** (try in order until one works):
- **F1.1a**: Explicitly demonstrate `Agent(subagent_type=..., prompt=...)` usage in the CTOA operating loop. Right now the prompt says "spawn 3 personas in parallel" without showing the literal call shape.
- **F1.1b**: If nested subagents genuinely can't spawn other subagents in this Claude Code version, fall back to a *handoff file* pattern that the operator's session reads and routes — i.e., codify the current workaround as the official protocol.
- **F1.1c**: Investigate `Task` tool variations and Claude Code 2.x subagent docs for the right invocation idiom.

**Verification:** After CTOA completes Stage 1 on a test requirement, the Architect subagent auto-starts without manual prompting.

### Phase 1.2 — Dependency-check gate at intake (fixes process violation observed in monitor)

**Problem:** Child #4 shipped through Stage 7 while child #3 (its declared blocker per the meta-tracker's `proposed_children[].blocks`) sat orphaned at Stage 1.

**Fix:** Add a "pre-flight check" at the start of every child intake:
```pseudo
for blocker in self.proposed_children[i].blocks:
  if state[blocker].status != "shipped":
    REFUSE to advance this child past Stage 1.
    Emit decision-log event type: "dependency-violation-blocked".
    Notify Founder with explicit list of unshipped blockers.
```

**Where it lives:** `agents/cto-advisor.md` Stage 1 operating loop, with the rule codified in `docs/workflow.md` § "Pre-flight dependency check."

**Verification:** Attempt to intake a child whose blocker is unshipped → CTOA refuses and surfaces the unshipped blocker.

### Phase 1.3 — Push-success gate at Stage 8 (fixes D22)

**Problem:** Child #1 was marked `status: shipped` even though `git push origin master` returned 403. State lied relative to git.

**Fix:** Jatin's Stage 8 protocol gains two new sub-stages:
- **Stage 8a (push attempt):** `git push origin master`. If success → `status: shipped`. If failure → `status: awaiting-push-fix`, owner: Founder.
- **Stage 8b (push verify):** `git ls-remote origin HEAD` matches local HEAD → genuinely shipped.

**Decision-log event:** `type: push-result` with `success | failure` + error message + remote SHA.

**Verification:** Simulate a push failure (e.g., bad remote URL); state must move to `awaiting-push-fix` and surface to Founder, NOT show `shipped`.

### Phase 1.4 — Commit events in decision log (fixes D13)

**Problem:** Real commits land in git but the decision log has no `type: commit` event. Reconstructing "what shipped for this req" requires cross-referencing.

**Fix:** Add to every dev agent's protocol (Vikram/Ananya/Karan/Maya): after every commit, append a decision-log event:
```json
{"ts":"...","actor":"<persona>","type":"commit","req_id":"...","commit_sha":"<sha>","subject":"<subject>","track":"N"}
```

**Backstop (V2):** post-commit git hook in the Brain project that does this automatically.

### Phase 1.5 — Audit trail commit protocol (codifies the team's D17 self-correction)

**Problem:** The team caught the `.engineering-os/`-uncommitted defect organically and made a `chore(eos):` commit. But that fix isn't codified — the next teammate may not repeat it.

**Fix:** Add to Jatin's Stage 8 protocol (final step): `git add .engineering-os/ && git commit -m "chore(eos): pipeline state for <req-id>"` BEFORE the push. Documented in `agents/platform-devops.md` and `docs/workflow.md` § Stage 8.

**Important:** This must NOT be blocked by the "no auto-commit" rule. The rule applies to PRODUCT CODE commits; audit-trail commits flow always. This needs to be explicit in the durable-rule clarification (Phase 0.5).

---

## Phase 2 — Self-improvement substrate (plugin, 4–5 hours)

**Why third:** with the pipeline flowing and dependencies enforced, the team can start *getting better at being a team* — the recursive payoff.

### Phase 2.1 — Per-child retros

**Pattern observed:** CTOA's intake of child #2 reflected on child #1 ("Why 3 personas, not 1 as in child #1: ...") — informal but valuable. Children #3+ should have this formalized.

**Fix:** Add a new artifact `14-retro.md` to the run folder template (Section 5 of plugin). Filled by CTOA at the close of every child, NOT by the implementing developer. Three sections:
1. **What worked** — concrete patterns from this child to replicate.
2. **What didn't work** — concrete patterns to avoid.
3. **What surprised us** — emergent learning the planning didn't anticipate.

**Where it goes:** `templates/retro.md` (new template) + `schemas/retro.schema.json` (new schema) + addition to `agents/cto-advisor.md` Stage 6 operating loop.

### Phase 2.2 — Lessons-learned registry

**Problem:** Retros are per-child. Without aggregation, each next child re-discovers the same lessons.

**Fix:** A single `.engineering-os/lessons-learned.md` file at the Brain project root (committed). Append-only. Each entry:
- Sourced from a `14-retro.md`
- Three fields: `lesson`, `evidence` (which req surfaced it), `applies_to` (categories: process, code, security, etc.)
- Tagged so next intake can filter relevantly.

**Where it goes:** template + schema + addition to CTOA Stage 1 operating loop: *"Before drafting the new requirement, read `lessons-learned.md` and cite any lessons that apply."*

### Phase 2.3 — Rule-proposal mechanism

**Pattern observed:** Founder said "no commits without approval" in chat; team adopted as "durable rule" but interpreted too broadly. No way to propose-then-confirm before durable-fying.

**Fix:** Two artifacts:
- `.engineering-os/rule-proposals/<ts>__<slug>.md` — agent or operator writes a proposed rule. Header has `proposed_by`, `target_scope`, `proposed_text`, `rationale`, `evidence`.
- `.engineering-os/durable-rules/<adopted-ts>__<slug>.md` — formal durable rule, with `adopted_by: founder`, `adopted_at`, `text`, and explicit `scope`.

A proposal can only become durable when Founder runs `/brain-engineering-os:adopt-rule <proposal-path>`. **Agents cannot self-promote a proposal to durable.**

**Where it goes:** new slash command `adopt-rule`, new templates, new section in `docs/escalation-rules.md` for governance changes.

### Phase 2.4 — Founder visibility for proposed changes

**Pattern observed:** CTOA approved child #4 on Founder's behalf without acknowledging the dependency violation; the violation is now baked into the decision log as an approved outcome.

**Fix:** Whenever an agent makes a decision that violates a previously-documented rule (dependency check, Single-Primitive Rule, India compliance, etc.), it must:
1. Emit `type: rule-deviation` decision-log event with `rule`, `evidence-of-violation`, `justification`.
2. Surface to Founder in a `pending-founder-attention.md` file at the Brain repo root.
3. NOT proceed past the gate without explicit Founder response.

This is anti-blind-agreement applied to the DELEGATION itself — even under Rohan's full approval authority, rule-deviations remain Founder-visible.

---

## Phase 3 — Process codification (plugin, 2–3 hours)

### Phase 3.1 — Gate skip rules (fixes D3)

**Problem:** Aryan skipped Stage 4 (Shreya) on child #1 with judgment but no codified exception process. Future agents will copy the pattern.

**Fix:** Add to `docs/quality-gates.md` § "Stage 4 skip exception":
- Skipping Stage 4 is permitted IF AND ONLY IF the change touches only `.md`/`.txt`/`.json` files AND no `.env`/lockfile/auth/secret-relevant content AND a `Stage 4 skip rationale` field is filled in the architecture plan.
- The skip emits a `type: gate-skip` decision-log event.
- Tanvi (Stage 5) re-runs the skipped gate's verification — codified per Phase 3.2.

### Phase 3.2 — QA re-runs skipped gates (codifies W13)

**Pattern observed:** Tanvi at Stage 5 re-ran Shreya's secrets-grep even though Stage 4 was skipped.

**Fix:** Add to `agents/qa-agent.md` operating loop: *"For every gate marked SKIPPED in the prior stages, re-run a minimal version of that gate's verification yourself. Record output in the QA review."*

Tanvi's QA gates checklist gains a `skipped-gates-re-verified` field.

### Phase 3.3 — Final review re-runs QA gates (codifies W14)

**Pattern observed:** Rohan independently re-ran 3 of Tanvi's gates rather than rubber-stamp.

**Fix:** Add to `agents/cto-advisor.md` Stage 6 operating loop: *"Spot-re-run at least 3 of Stage 5's verification gates. Record output in the final review. Match Tanvi's PASS with your own captured output."*

### Phase 3.4 — Pre-flight check at intake

**Already covered in Phase 1.2 (dependency check).** Codified protocol — no separate work.

---

## Phase 4 — Infrastructure hygiene (plugin, 1–2 hours)

### Phase 4.1 — UTC timestamp discipline (fixes D7 + D26)

**Problem:** Agents drift between UTC, IST, and logical-clock guesses. Audit trail readability suffers.

**Fix:** Add to system prompt (`prompts/system-prompt.md`):
> "All timestamps in journal entries, decision-log events, run folder names, state files, and artifact metadata MUST be derived from `date -u +%Y-%m-%dT%H:%M:%SZ` at the time of action. Do not infer timestamps from prior artifacts. Do not use IST. Always UTC, always Z-suffix."

Add a CI gate (v0.4.0): regex-check timestamp format on every committed artifact.

### Phase 4.2 — Unique run folder names (fixes the same-timestamp bug)

**Problem:** Children #3 and #4 had run folders with identical timestamp prefix `2026-05-19T14-30-00Z`. Naming collision possible.

**Fix:** Run folder format becomes:
```
runs/<ISO-ts>__<random-6-hex>__<req-id>__<operator>/
```
Adding 6 hex chars (e.g., `a3f201`) makes collisions essentially impossible. Documented in `docs/plugin-architecture.md` § "Run folder layout."

### Phase 4.3 — Auto-journal hook agent attribution (fixes D2 root cause)

**Problem:** The hook defaults `CLAUDE_AGENT_NAME=unknown` when env var unset. Team gitignored the resulting file; better fix is to attribute correctly.

**Fix:** Hook script reads the active subagent name from Claude Code's task metadata if available; falls back to parsing the call stack; only writes to `unknown.journal.md` as last resort. Investigate what env var or hook context Claude Code 2.1.143 actually exposes.

### Phase 4.4 — Sonnet vs Opus investigation (D21)

**Problem:** Subagents appear to default to Sonnet 4.6 despite Founder session being Opus 4.7. Quality has been excellent on Sonnet but may degrade on complex children.

**Action:** Read Claude Code subagent docs; check if `model: inherit` in agent frontmatter changes this; experiment with `model: opus` declaration on the Architect (highest-stakes agent); compare plan quality. Report findings.

---

## Phase 5 — Validation (Founder + me, 1–2 hours)

**Why last:** every prior phase claims to fix something. Validation proves it.

### Test requirement to submit
Run `/brain-engineering-os:requirement Add a small health-check endpoint to the backend API` (the original suggested first requirement). Low-stakes; tests the pipeline end-to-end.

### Expected pipeline behavior (with v0.3.1 fixes)
1. CTOA intakes, reads lessons-learned, spawns 3 personas, synthesizes, **auto-invokes Architect.**
2. Aryan plans, **auto-invokes Builder.**
3. Vikram builds, emits commit events to decision log, **auto-invokes Security.**
4. Shreya passes; Tanvi re-runs Shreya's gates; **auto-invokes CTOA.**
5. Rohan re-runs 3 of Tanvi's gates, emits retro, **surfaces to Founder.**
6. Founder approves (or delegates) → Jatin pushes → `status: shipped` only after push verified.
7. Retro file landed; lesson appended to lessons-learned registry.

### Failure modes to test
- Dependency violation: try to intake child #3 again (with #2 still uncommitted) — must be refused.
- Push failure: simulate via bad remote — state must move to `awaiting-push-fix`, not `shipped`.
- Stage 4 skip: try on a code-touching change — must be refused; only docs/json/md changes allowed to skip.

### Capture
- Field notes Round 3 (`docs/field-notes-2026-05-DD-validation.md`) covering what worked, what regressed.
- Any new lessons feed back into the registry.

---

## Risks & mitigations

| Risk | Likelihood | Severity | Mitigation |
|---|:---:|:---:|---|
| Subagent spawning fix can't actually be made to work in Claude Code 2.1.143 | Medium | High | Fall back to handoff-file pattern (F1.1b); codify as official protocol; pipeline still requires user prompting between stages but with clear next-action prompt |
| Phase 2 (self-improvement) adds bureaucracy that slows the team | Low | Medium | Each artifact is small (≤200 lines); retro is a 5-min CTOA action; lessons registry is consulted (not edited) by next CTOA intake. Costs are bounded; benefits compound |
| Founder doesn't actually want self-improvement substrate (Phase 2) | Medium | Low | Phase 2 is optional. Phase 1 + Phase 3 + Phase 4 alone deliver the throughput gains. Phase 2 is a bigger investment for compounding payoff |
| Plugin changes destabilize current Brain pipeline | Low | High | All changes go in via numbered v0.3.1, v0.3.2 releases. Brain repo can pin to v0.3.0 if needed. Rollback is `git revert` |
| Phase 0 actions get postponed indefinitely (GitHub 403, commit recovery) | Medium | High | Phase 0 IS the bottleneck. Without it, Phase 5 validation can't run. Make this Founder's first action when ready |

---

## Sequencing decision (which phases to ship in which release)

| Release | Includes | Why |
|---|---|---|
| **v0.3.1** | Phase 1 + Phase 3 + Phase 4 | Fixes the critical mechanics + codifies process patterns the team already exhibits. ~7 hours of work. Safe to ship without Phase 2. |
| **v0.3.2** | Phase 2 | Self-improvement substrate. ~5 hours. Ships after Phase 5 validation confirms v0.3.1 doesn't regress |
| **v0.4.0** | (future) | CI gates for timestamp regex, agent-model selection, archive policy for old runs, `/digest` weekly summary |
| **v0.5.0** | (future) | True multi-team scale: per-project `.engineering-os/`, cross-team handoffs, on-call/incident pipeline |

---

## Stop-and-ask points (where Founder must weigh in)

Before any plugin work starts:
- **Phase 0** complete? Confirm child #3/#4 disposition + GitHub auth + "no commits" rule clarification.

Mid-flight:
- After Phase 1.1 (subagent spawning): if all three fix candidates fail, pause and discuss fallback before continuing.
- After Phase 1: pause and validate that pipeline auto-flow actually works on a simple test before proceeding to Phase 3.
- After Phase 3: pause for Founder to decide whether to ship v0.3.1 immediately or continue with Phase 2.

---

## Reading order

For this plan:
1. Read this document end-to-end (you're doing it now).
2. Skim the three field notes if not already read.
3. Decide cutoffs (v0.3.1 only? or include Phase 2 in v0.3.1?).
4. Confirm Phase 0 timing — when will you do the Brain-side unblocks?
5. Greenlight Phase 1 start.

For the team (once Phase 2 ships):
- Every CTOA Stage 1 intake reads `lessons-learned.md` first.
- Every Stage 6 final review writes a retro entry.
- Every rule-deviation surfaces to Founder before proceeding.

---

## Net assessment

The team is two short structural fixes away from running autonomously at high quality. The biggest leverage is **Phase 1.1 (subagent spawning)** — without it, every other improvement is gated on human prompting between stages. The second-biggest is **Phase 2.3 (rule-proposal mechanism)** — without it, Founder feedback becomes overshooting durable rules with no propose-then-confirm channel.

Everything else is polish (Phase 3, 4) or compounding-value-over-time (Phase 2.1, 2.2, 2.4).

**Recommended cutoff:** ship Phase 0 → 1 → 3 → 4 as v0.3.1. Validate (Phase 5). Then ship Phase 2 as v0.3.2 if validation shows the substrate is working.

---

*Plan author: Engineering OS development (plugin maintainer).*
*Plan reviewer (pending): Founder (Rishabh).*
*Status: DRAFT — awaiting Founder cutoff decision.*
