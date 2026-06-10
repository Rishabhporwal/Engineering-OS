---
name: foundation
description: Agentic Foundation phase — the team drafts the entire Product Canon (all 11 slots) from a product brief + a repo scan, then the Stakeholder reviews and approves per file. Converts the 8–15-hour manual Canon authoring into a ~1-hour guided review. Run once per product, after /eos-init.
disable-model-invocation: true
---

Run the **Foundation phase as a guided, agentic session** — the team drafts the Product Canon; the Stakeholder approves. This replaces nothing in `engineering-os-blueprint/10-adoption-and-product-canon.md` (the Canon's meaning is unchanged); it changes **who does the typing**.

The Stakeholder's product brief (may be empty — then interview first) is:

> $ARGUMENTS

## Preconditions
1. `.engineering-os/` exists (else: "run `/eos-init` first" and stop).
2. The Canon is NOT already approved (a foundation sentinel exists → "Foundation already approved; amendments go through a Foundation amendment, not a re-run" and stop).

## Procedure

**1. Gather (≤10 questions, batched — respect the Stakeholder's time).**
Read the brief. Scan the repo if code exists (`package.json`/`pyproject`/lockfiles/docker/IaC/CI → detect the de-facto stack; existing models/routes → detect the domain). Then ask ONLY what the brief + scan can't answer, batched in ONE message, multiple-choice where possible:
- What is the product, for whom, and what's the ONE thing it must never get wrong? (→ INVARIANTS, THE-MOAT)
- Single-tenant or multi-tenant? Which regions/data-residency? (→ TRIGGER-SURFACES, COMPLIANCE)
- Which regulatory regime applies, if any (data protection / payments / health / none)? (→ COMPLIANCE)
- Stack preferences, or "team's choice"? (→ STACK)
- The 3–5 metrics that define success? Money involved? (→ METRICS)
- Deploy target + risk appetite (canary? bake window? manual approve?)? (→ PLAYBOOK-deploy)

**2. Draft — spawn the team in parallel (you are the orchestrator; subagents have no Agent tool).**
Build spawn prompts cache-stable-first (`pipeline/orchestrator.md` per-spawn contract). Each agent drafts from the canon TEMPLATES (`${CLAUDE_PLUGIN_ROOT}/canon/`) into `${CLAUDE_PROJECT_DIR}/.engineering-os/knowledge-base/`:
- **architect** (deep tier — this is THE binding-decision session): `STACK.md` (every seam bound, one-line ADR each), `HLD.md`, `TRIGGER-SURFACES.md` (concrete surfaces + thresholds — this drives lane escalation forever).
- **security-reviewer**: `COMPLIANCE.md` (the declared regime mapped to enforceable rules; "none" is a valid, explicit answer) + the security slice of `INVARIANTS.md`.
- **intelligence-engineer**: `METRICS.md` (single-source registry; money = minor units + currency_code) + effort-tier defaults.
- **platform-devops**: `PLAYBOOK-deploy.md`, `PLAYBOOK-incident.md` (severity ladder, kill switches).
- **cto-advisor**: `INVARIANTS.md` (merged), `ESCALATION-RUBRIC.md`, `THE-MOAT.md`, `team-roster.md` (optional).
Each drafter marks every assumption it had to make with `> ASSUMPTION:` inline — assumptions are the review surface.

**3. Review gate — per file, with the Stakeholder (the human stays the author of record).**
Present each Canon file as: a 5-line summary + the full draft + its `ASSUMPTION:` list. The Stakeholder approves / edits / answers per file. **Do not batch-approve silently** — STACK.md and COMPLIANCE.md and TRIGGER-SURFACES.md each get an explicit yes. Apply edits, clear the assumption markers as confirmed/corrected.

**4. Seal.**
- Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/knowledge_lint.py` against the repo canon if applicable; verify every template slot is filled (no `<placeholder>` left).
- Write the foundation sentinel (`.engineering-os/foundation-approved.<ISO-date>`) recording: who approved, when, and the list of files at their approved hashes.
- Commit `.engineering-os/knowledge-base/` + the sentinel (`chore(eos): Foundation — Product Canon approved`), per commit discipline (explicit paths, no push).
- Print next step: *"Foundation approved — the pipeline is unlocked. File your first requirement: `/requirement <the smallest valuable slice>`. Tip: start with one express-lane item to see the loop end-to-end."*

## Rules
- **Drafts, not decisions:** every binding choice (stack seam, compliance posture, thresholds) is explicitly surfaced for approval — the team proposes; the Stakeholder disposes. An unconfirmed `ASSUMPTION:` never silently becomes Canon.
- **Brownfield beats greenfield guessing:** when code exists, the detected de-facto stack is the draft default (changing a working stack is an ADR, not a Foundation default).
- **Time-box:** this is a ~1-hour Stakeholder session, not a multi-day workshop. A slot that needs deep work (e.g. a complex compliance regime) gets a TODO-with-owner in the file + a follow-up requirement — Foundation approves the 80% so the pipeline unlocks.
- Standard failure handling: anything broken → surface clearly, leave state consistent, never silently proceed.
