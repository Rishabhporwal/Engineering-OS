---
name: new-skill
description: Scaffold a new Engineering OS domain skill consistently (ECC-inspired Skill Creator). Creates skills/<name>/SKILL.md in the canonical format, then registers it in the skill-mapping-matrix and the owning agent's owned-skill list. Use when a REAL, recurring gap surfaces during work — author the skill on-demand instead of by hand, and keep the library consistent. A skill must earn its place; do not pad the library.
disable-model-invocation: true
---

Scaffold a new domain skill. Skill name (kebab-case) + one-line intent:

> $ARGUMENTS

## Steps

1. **Parse** the kebab-case `name` and a one-line intent from `$ARGUMENTS`. If missing, ask for them.
2. **Prove the gap is real (anti-bloat gate).** Run `/recall-similar "<intent>"` and scan `docs/skill-mapping-matrix.md`. If an existing skill already covers it → **extend that skill, do NOT create a new one** (Single-Primitive for skills; recall v0.7.1 consolidated 59→49 deliberately). Only proceed if no existing skill fits.
3. **Ground it in canon.** Identify the `canon/technical-requirements.md` / `business-requirements.md` section it derives from — a domain skill cites real Brain architecture, not generic advice.
4. **Create `skills/<name>/SKILL.md`** in the house format (match an existing domain skill like `caching-strategy`): frontmatter (`name`, `description` — the description must say *when to auto-load*), then `# Title`, a one-paragraph intro, a key-patterns table, "rules" (non-negotiables, cross-linked to related skills via `[[name]]`-style markdown links), "anti-patterns", and "verify". Keep it ~50–70 lines, dense and Brain-specific.
5. **Register it (3 places, or the doctor will not flag it but the matrix drifts):**
   - Add a row to the matrix table in `docs/skill-mapping-matrix.md` (domain category, primary owner, shared-with, exposed-as-command).
   - Add it to the **owning agent's owned-skill list** — both in `docs/skill-mapping-matrix.md` §"Skills by role" AND in `agents/<owner>.md`.
   - Bump the domain-skill count wherever it appears (matrix header, `README.md`).
6. **Validate:** run `uv run "${CLAUDE_PLUGIN_ROOT}/tools/pipeline_doctor.py"` — C6 confirms the folder is well-formed (`name:` matches folder).

## Don't
- Don't create a skill that duplicates or overlaps an existing one — consolidate instead.
- Don't write generic best-practice; a Brain skill is grounded in Brain's stack, canon, and economics.
- Don't forget the matrix + owner registration — an unmapped skill is invisible to the agents that need it.
