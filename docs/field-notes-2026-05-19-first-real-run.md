# Field Notes — First Real Production Run (v0.3.0)

> **Source observation:** Brain product repo at `~/Desktop/Brain` (Looqus codebase) running v0.3.0 of `brain-engineering-os` plugin.
> **Window observed:** 2026-05-18T22:45 → 23:03 (Z) — Stage 1 (parent) + Stage 1 (child #1) + Stage 2 (child #1, Aryan).
> **Read on disk:** `.engineering-os/runs/`, `.engineering-os/memory/`, `.engineering-os/decision-log/`, `.engineering-os/state/`.
> **Author:** plugin-side analysis from the Engineering OS repo, not from inside the Brain Claude Code session.

---

## TL;DR

The agents are working **better than I expected** on quality — the CTO Advisor's decomposition into 11 ordered child reqs is genuinely excellent operator-grade thinking, and Aryan's Stage-2 plan for child #1 is rigorous enough to satisfy a senior staff review. But three real defects are showing in production:

1. **CTO Advisor can't spawn subagents** — `Agent` tool isn't in its tools list, so it manually writes a `HANDOFF-TO-ARCHITECT.md` and prays the next turn picks it up. This breaks pipeline automation.
2. **Auto-journal hook is firing on every Bash call** — `unknown.journal.md` has 80+ entries documenting `ls`, `date`, `grep`. Pure noise. Hook needs filtering + agent attribution.
3. **Skipping Shreya silently became a precedent** — Aryan exercised judgment to skip Stage 4 on a paper-only change. Defensible call, but no codified exception in the workflow doc; future agents will copy the pattern indiscriminately.

Plus 8 smaller items below.

---

## What's working brilliantly (don't break these)

### W1 — "Less dumb first" pass is doing real work

CTOA explicitly killed the "rewrite everything at once" framing in its first review:
> "Deleting the all-at-once framing is the single biggest derisking move available. Treat the parent as a *meta-tracker*; reject any child req that tries to swap more than one component at a time."

This is the `engineering-discipline` skill doing exactly what it's designed for. **Keep.**

### W2 — Decomposition order is sound

The 11-child sequence is genuinely well-ordered:
1. Canon into repo (zero risk; unblocks everyone)
2. RegionAdapter interface (interface refactor, no behavior change)
3. Metric registry (paisa parity gate)
4. Monorepo split (after the moat is hardened)
5. tRPC at gateway (additive; REST still works)
6. RLS hardening (separate child with dedicated backfill harness)
7. Observability (cheap; before service carves)
8. Carve ingestion-service (first real carve, shadow-then-cutover)
9. Carve analytics-service (only stand up ClickHouse if a surface exceeds 500ms p95)
10. Kafka MSK *only if* a second consumer materializes
11. CI gates (last — ratifies the new shape)

RegionAdapter before monorepo split is the **right** call — the persona work surfaced this and CTOA listened. Architect would normally jump to monorepo first because it's the "architectural" move; CTOA correctly identified that the moat must harden first.

### W3 — Anti-blind-agreement applied to the agent's OWN rules

Both CTOA and Aryan explicitly defended deviations:
- CTOA spawned **1 persona instead of 3** for child #1 (pure docs) with a written justification ("parent absorbed full 3-persona brainstorm").
- Aryan **skipped Shreya** (Stage 4) with a written justification ("zero attack surface added").
- Aryan **mirrored 12 docs instead of the 4 the requirement named** with a written justification ("cross-link graph would break with only 4").

Each deviation is recorded in the journal *and* in the artifact. This is exactly the discipline we want — agents that bend rules with cited reasoning, not silently.

### W4 — Hard constraints flow downstream cleanly

The parent's `hard_constraints_carried_to_every_child` list (7 items: pixel-diff=0, paisa parity, 7-day shadow, $ cost, no new features, no EKS migration, no MCP/Memory Layer content) is being applied verbatim in every child's Stage-2 plan as a **compliance checklist** with PASS/FAIL per row. Aryan's child #1 plan has all 7 marked PASS with one-line justifications. Future audits can scan one table per child.

### W5 — Single-Primitive sweep is being honored

Aryan's Section 7 explicitly noted: "Decision Log extended — this child appends two entries to the existing `decision-log/2026/05/2026-05-18.jsonl`; no new log surface created." Single-Primitive Rule applied to the EOS's own infrastructure. **Good recursion.**

### W6 — Decision log shape is excellent

The JSONL events are well-typed:
```json
{"ts":"...","actor":"cto-advisor","type":"stage-1-review","req_id":"...","decision":"approve","rationale":"...","personas_spawned":[...],"paradigm_recommendation":"sql","next_owner":"architect","next_stage":2}
```
Greppable, queryable, machine-readable. This is the moat-of-the-moat working as designed.

### W7 — State file atomicity

`active.json.bak.<ts>` written before every save (4 backups in 15 minutes — that's the right cadence). Bootstrap entries say "system → bootstrap" with no req_id. Real entries follow the schema. **Good discipline; preserve.**

---

## Real defects — fix these in v0.3.1

### D1 — CTO Advisor cannot spawn subagents *(BLOCKER for full automation)*

**Evidence:** CTOA wrote `HANDOFF-TO-ARCHITECT.md` with the explicit note:
> "The `Agent` tool was not available in the CTO Advisor's invoking thread; this handoff manifest + the `state/active.json` mutation + the `type: handoff` decision-log entry serve as the durable invocation record. **The next orchestrator turn (or a direct human invocation of the `architect` subagent) picks this up.**"

This means the Founder has to manually re-invoke `/brain-engineering-os:architect` after every CTOA stage-1 completion. The 8-stage pipeline is supposed to flow agent-to-agent. Right now it's flowing through the human.

**Root cause:** `agents/cto-advisor.md` frontmatter lists `tools: [Read, Write, Edit, Bash, Grep, Glob, TodoWrite, Agent]` — but when CTOA is itself invoked as a subagent, the `Agent` tool likely isn't being plumbed through the sub-conversation. Either:
- (a) The `Agent` tool entry is being silently dropped by Claude Code for nested subagents (architectural limit).
- (b) The tool is present but the agent prompt doesn't *use* it correctly.
- (c) There's a permissions/scope thing we missed.

**Fix candidates:**
- **F1a:** Explicitly demonstrate Agent-tool usage in CTOA's `agents/cto-advisor.md` operating loop (right now it says "spawn 3 personas in parallel" without showing the literal `Agent(...)` call). Make the prompt show the tool call shape.
- **F1b:** If nested subagents can't spawn subagents, switch to a flat orchestration model: CTOA writes a "next-action" file, and the user's next slash-command invocation reads it and routes. Less elegant but works in current Claude Code.
- **F1c:** Investigate whether `--max-turns` or session-level config affects subagent tool availability.

**Workaround for now:** Founder manually runs `/brain-engineering-os:architect` after CTOA completes each Stage 1. Document this in the operating manual.

**Severity:** HIGH (every stage transition currently requires human intervention).

---

### D2 — Auto-journal hook is generating noise, not signal

**Evidence:** `memory/agents/unknown.journal.md` has 100+ entries like:
```markdown
## 2026-05-18T22:50:00Z — auto — unknown
**Auto-entry from post-tool-use hook.** Bash: grep -n "^#" /Users/rishabhporwal/Desktop/Brain/docs/BRAIN_TECHNICAL_DOCUMENTATION.md 2>&1 | head -80
```

Every bash call by every agent is being captured. The hook's intent was "auto-journal meaningful actions" but the filter is "any Edit / Write / Bash" with no signal threshold.

**Two problems:**
1. **`unknown` as agent name** — the hook can't determine which agent is running (the `CLAUDE_AGENT_NAME` env var isn't being set by Claude Code, or my hook script's fallback is wrong). All entries go to `unknown.journal.md`.
2. **Every Bash is being logged** — even trivial inspection commands (`ls`, `grep`, `date`). This dilutes the journal until the real entries (made by agents themselves via Write) are buried.

**Fix candidates:**
- **F2a:** Stop auto-journaling Bash entirely. Bash calls are too noisy. Only auto-journal Edit/Write on files inside `.engineering-os/runs/` (i.e., artifact production).
- **F2b:** Drop the entire auto-journal hook. Agents are already journaling explicitly (well — CTOA wrote ~5 explicit entries to `cto-advisor.journal.md`). The hook's value is marginal and its noise is high.
- **F2c:** Keep the hook but invert the filter — log to a single shared `memory/auto-trace.log` (single file, not a journal) for forensic debugging, and rely on agent-authored journal entries for the canonical record.

**Recommendation:** F2b (drop the hook). Agents are journaling correctly without it. The hook is solving a problem that doesn't exist.

**Severity:** MEDIUM (noise, not failure — but the noise *masks* real signal).

---

### D3 — Stage skips are happening without codified exception process

**Evidence:** Aryan's plan §11:
> "**Shreya (security) is explicitly skipped for this child** (deviation from default 8-stage pipeline; flagged for Founder visibility). Justification: zero attack surface added — no input parsing, no auth path, no secret handling, no dependency added, no script executed."

This is defensible reasoning. But:
- The plugin's `docs/workflow.md` says all 8 stages run on every requirement.
- The plugin's `docs/quality-gates.md` says Shreya has VETO authority.
- There is no documented "Stage 4 can be skipped when X" exception.

If we leave this implicit, every Aryan-equivalent agent in every Brain repo will start skipping stages whenever they feel the change is small. The discipline rots.

**Fix candidates:**
- **F3a:** Codify a "Stage 4 fast-pass" rule in `docs/quality-gates.md`: for changes that touch only `.md`/`.txt` files outside `apps/` and `services/`, Shreya runs a 60-second scoped scan instead of full review.
- **F3b:** Require Stage 4 always — Shreya can pass in 60 seconds, fine, but the gate event must be logged. No silent skips.
- **F3c:** Add a `paper_only: true` flag to the requirement schema. When set + verified (sentinel: zero diff outside docs/), Stage 4 routes to a "paper-only" mini-template instead of full security review.

**Recommendation:** F3b — require the gate, allow it to be trivial. Discipline > convenience.

**Severity:** MEDIUM (today only this child skipped; next month, dozens will).

---

### D4 — Architecture plan filename violates template numbering

**Evidence:** Aryan wrote `03-architecture-plan.md` instead of `06-architecture-plan.md` (per template). His own preamble:
> "Numbered `03-` per Founder/CTOA convention in this run folder (Stage 1 personas are `03-…` only because there was a single persona; the convention here is sequential, not template-section-numbered)."

Two competing conventions in the same run folder:
- Template: `01-requirement`, `02-cto-advisor-review`, `03/04/05-persona-*`, `06-architecture-plan`, `07/08-dev-report`, ...
- This run folder: `01-requirement`, `02-cto-advisor-review`, `03-persona-doc-completeness-officer`, `03-architecture-plan`(!), `HANDOFF-TO-ARCHITECT.md`

This creates ambiguity for the QA agent (Tanvi) when she reads the run folder. Did Aryan replace `03-persona-...`? Is `03-architecture-plan` the Stage-2 deliverable or a renamed persona?

**Fix candidates:**
- **F4a:** Enforce strict template numbering — Aryan must write `06-architecture-plan.md` regardless of how many persona files exist (slots 03/04/05 stay reserved).
- **F4b:** Switch to fully descriptive filenames — `requirement.md`, `cto-advisor-review.md`, `persona-<type>.md`, `architecture-plan.md`, `dev-report-<persona>.md`. Drop numeric prefixes entirely; rely on git/file mtime for ordering.

**Recommendation:** F4b — descriptive names. Numeric prefixes break exactly when the run is non-standard (which is most runs).

**Severity:** LOW (audit confusion, not failure).

---

### D5 — Per-feature journal filename has redundant prefix

**Evidence:** Files exist:
- `memory/features/feat-chore-revamp-to-eos-standards.md`
- `memory/features/feat-chore-eos-canon-into-repo.md`

The `feat-` prefix is hardcoded in `eos-init`'s scaffolder, but the requirement is actually `chore-revamp-...` (kind prefix already present). So the filename is double-prefixed: `feat-chore-...`.

**Fix:** Change the template guidance to `<kind>-<slug>.md` (the kind comes from the requirement ID's own prefix). Drop the `feat-` hardcode.

**Severity:** LOW (cosmetic; no functional impact).

---

### D6 — Architecture plan deviates significantly from template

**Evidence:** Aryan's plan adds sections not in `templates/architecture-plan.md`:
- "Smallest shippable slice" (good addition)
- "Three-commit plan" (good)
- "Hard-constraint compliance checklist" (excellent — should be standard)
- "Out of scope" block (excellent)
- "Definition of Done" with 13 testable conditions (excellent)
- "Reversibility recipe" (excellent)
- "Architect sign-off" footer (good)

These additions are **better than the template**. The template is currently inferior to what the agents produce in practice.

**Fix:** Roll these additions back into `templates/architecture-plan.md` so they become the default expected shape.

**Severity:** OPPORTUNITY (template is a floor, not a ceiling — but raising the floor pulls everyone up).

---

### D7 — Timestamp inconsistency across the audit trail

**Evidence:** Mix of timestamps in journals:
- Bootstrap (mine): `2026-05-19T08:30:00Z` (probably wall-clock today)
- CTOA Stage 1 review: `2026-05-19T08:35:40Z` (5 minutes later — plausible)
- CTOA fan-out + child #1 intake: `2026-05-18T22:48:40Z`, `22:54:00Z`, `22:56:57Z` (yesterday!)
- Aryan's plan: `2026-05-18T23:00:41Z`

Looks like the agents are using their best guess at "now" but inconsistent reference time (UTC vs local IST?). The bootstrap entry I wrote is in the *future* relative to the agents' real activity timestamps.

**Fix candidates:**
- **F7a:** Add a system-prompt rule: "Always use UTC. Always use the current date provided by `date -u +%Y-%m-%dT%H:%M:%SZ`."
- **F7b:** Make the bootstrap journal entries timestamp-less ("bootstrap — date TBD on first real activity").

**Severity:** MEDIUM (audit trail readability is degraded; not a correctness bug).

---

### D8 — Founder-approval protocol drift

**Evidence:** `12-founder-decision.json` was written by the CTO Advisor agent (per the decision-log event `actor: rishabh, type: founder-decision`). This is the agent *recording* the founder's decision after the founder spoke it in chat.

The intended protocol (per my `/approve` skill design) is:
- Founder runs `/brain-engineering-os:approve <req-id>` slash command.
- The skill writes `12-founder-decision.json` itself.
- The skill records the decision-log event.

Current observed flow:
- Founder typed "/approve... Option A" in chat (informally).
- CTOA caught the intent and wrote both files on the Founder's behalf.

This works but it's brittle:
- No invocation by the Founder means no audit trail showing the Founder actually saw the artifacts before approving.
- Agent could fake an approval (in principle).
- `/approve` skill exists but isn't being used.

**Fix:** Add to the system prompt for CTOA: "Never write a `12-founder-decision.json` yourself. If the Founder approves informally in chat, tell them: 'Please run `/brain-engineering-os:approve <req-id>` to record this formally.' Wait for the slash command before advancing state."

**Severity:** MEDIUM (process discipline; not a present-tense bug because the Founder is also the operator).

---

### D9 — Single-persona deviation needs an explicit rule, not judgment

**Evidence:** CTOA spawned 1 persona for child #1 (not 3). Justification was correct — "parent meta-tracker already executed full 3-persona brainstorm whose conclusions are absorbed into this child's Constraints." But this is a judgment call that the system prompt currently calls "rejected" — see `prompts/anti-blind-agreement.md`:
> "Every persona must produce at least one concern. A persona that returns 'looks good, no concerns' is rejected by the CTOA — that persona didn't do its job."

And `docs/role-empowerment-model.md` §Dynamic Persona Generator says "Pick 3 personas". Hard count.

If the rule is "always 3", Aryan/CTOA shouldn't have done 1.
If the rule is "default 3, deviate with justification", that should be codified.

**Fix:** Update `docs/role-empowerment-model.md` and `docs/workflow.md`: "Spawn 3 personas by default. For child requirements where the parent already executed a 3-persona brainstorm and the child is bounded in scope (paper-only, single-track, zero-runtime-risk), spawn 1 scoped persona with a written deviation note recorded in the journal."

**Severity:** MEDIUM (rule ambiguity creates inconsistent agent behavior).

---

### D10 — `HANDOFF-TO-ARCHITECT.md` is a custom artifact not in the template set

**Evidence:** CTOA wrote `HANDOFF-TO-ARCHITECT.md` (caps + dashes) outside the numbered convention. There's no template for it. It's well-structured but ad-hoc.

This file exists *because* of D1 (Agent tool unavailable). Once D1 is fixed (agent auto-invocation works), this file becomes redundant.

**Fix:** Either:
- (a) Fix D1 → handoff file disappears.
- (b) If we keep handoff files as a permanent pattern, add `templates/handoff-manifest.md` to the templates set and document numbering.

**Recommendation:** Fix D1; let the handoff file vanish.

**Severity:** LOW (consequence of D1).

---

### D11 — Plan length will set bad precedent

**Evidence:** Aryan's `03-architecture-plan.md` is **385 lines** for a 3-commit pure-docs change. The plan is *excellent* — every section is justified — but the length-per-impact ratio is high. Future runs on similar trivial changes will produce 400-line plans because "Aryan did it this way."

For non-trivial work (a Python service carve), 400 lines might be right. For a docs mirror, 100 lines is plenty.

**Fix:** Add to `docs/role-empowerment-model.md` §Architect: "Plan length should scale with risk. Paper-only / pixel-diff=0 changes: 60–120 lines. Single-component refactor: 200–300 lines. Service carve / new managed service: 400–600 lines. Document the calibration band you're targeting at the top of the plan."

**Severity:** LOW (over-engineering risk; doesn't break anything today).

---

## Recommended fix order (by impact ÷ effort)

| Priority | Fix | Effort | Why |
|---|---|---|---|
| **P0** | F2b — drop the auto-journal hook | 10 min | Highest noise reduction; no risk |
| **P0** | F3b — codify gate-runs-always-but-can-be-trivial | 30 min | Prevents discipline rot |
| **P1** | F1a — show Agent tool usage explicitly in CTOA prompt | 1–2 h | Restores pipeline auto-flow |
| **P1** | F1b — fallback flat orchestration if F1a doesn't unblock | 2–4 h | Pragmatic compromise |
| **P2** | F4b — descriptive filenames (drop numeric prefixes) | 1 h | Removes audit ambiguity |
| **P2** | F6 — roll Aryan's additions into the template | 1 h | Raise the floor |
| **P3** | F7a — UTC timestamp discipline in system prompt | 15 min | Audit trail clarity |
| **P3** | F8 — codify `/approve` discipline | 15 min | Process tightening |
| **P3** | F9 — codify single-persona deviation rule | 30 min | Rule consistency |
| **P3** | F5 — drop `feat-` hardcode in journal filenames | 10 min | Cosmetic |
| **P4** | F11 — plan-length calibration bands | 15 min | Risk-proportionality |
| **(deferred)** | F10 — handoff template (only if F1 can't be fixed) | 1 h | Conditional |

Total: ~10 hours of work to ship v0.3.1 with all these addressed.

---

## What the agents got *exactly right* and should be cited in future training/prompt tuning

- **CTOA's "Could delete / Could simplify / Could defer" pass** is rich, specific, and operationally actionable. Use it as the canonical example in the system prompt.
- **Aryan's "Out of scope" block** is the single best anti-scope-creep tool I've seen produced by an agent. Make it mandatory in the template.
- **Aryan's "Hard-constraint compliance checklist"** with PASS/FAIL per row is the right shape for parent→child constraint inheritance.
- **The decision log's structured JSONL events** are exactly the right grain — one event per state transition, type-discriminated.
- **The reversibility recipe** ("`git revert HEAD~2..HEAD` reverts all three commits") at the bottom of the plan is the kind of operational humility we want everywhere.

---

## What to NOT change (to avoid breaking what works)

- Don't shorten the persona reviews. Their depth is what makes the synthesis useful.
- Don't auto-generate the `Hard-constraint compliance checklist`. The explicit human-readable PASS/FAIL is the contract.
- Don't centralize the run folder layout into a database. The flat git-tracked file structure is *why* this is auditable.
- Don't try to enforce strict 3-persona spawning when a child req is bounded. The deviation discipline (with written justification) is the right pattern.

---

## Next action for the Founder

Pick a priority cutoff and tell me which fixes to ship in v0.3.1. Suggested cutoff: **P0 + P1** (15 min + 3–6 hours). That gets you:
- No more `unknown.journal.md` noise.
- Stage 4 gate-skipping codified properly.
- CTO Advisor → Architect pipeline runs without manual re-invocation.

Lower-priority fixes can roll into v0.3.2 after we see how the team evolves on the next 1–2 child reqs.
