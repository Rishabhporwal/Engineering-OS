---
name: <agent-id>
description: <persona> — <one-line role>. <When the orchestrator/PROACTIVE trigger uses it>.
tools: [Read, Write, Edit, Bash, Grep, Glob, TodoWrite, WebSearch, WebFetch]   # NO Agent tool — subagents never spawn
model: <haiku|sonnet|opus|inherit>  # REAL Claude Code field — sets this agent's model; orchestrator can override per-spawn
skills: [<skill-a>, <skill-b>]      # REAL field — PRELOADS 1–2 always-needed skills' bodies at startup (keep tiny)
effort: <low|medium|high>           # optional REAL field — low for bounded/delta work, high for deep reasoning
---

# <Persona> — <Role>

> Inherits `prompts/system-prompt.md` (universal rules — paths, principles, HANDOFF, commit, token discipline, redaction). This file carries ONLY what is unique to this role. Do not restate inherited rules; cite the section.

> **Skills you reach for (auto-discovered by task match — see `docs/skill-mapping-matrix.md`):** <list>. These are NOT preloaded — the model invokes a skill's body on demand when the task surface matches (Anthropic's just-in-time pattern). Only the 1–2 truly-always skills go in `skills:` above.

## Mission
<2–3 lines: the one thing this role guarantees.>

## Authority
- **Decide alone:** <…>
- **Cannot decide alone:** <…>
- **VETO:** <surface, if any>

## In-lane Definition of Done
- [ ] <gated checklist item with one-line evidence requirement>
- [ ] <…>
- [ ] Journal + decision-log + `state/active.json` updated; HANDOFF block returned.

## Anti-blind triggers (you MUST challenge)
- <role-specific triggers; the generic ones are inherited from system-prompt §2>

## Journal stub
```markdown
## {{ISO_TS}} — {{PERSONA}} ({{agent-id}}) — {{REQ_ID}}
**Stage:** {{STAGE}} · **Action:** {{ACTION}} · **Decision:** {{DECISION}}
**Skills loaded:** {{SKILLS}} · **Verification:** {{CMD_+_OUTPUT}}
**Next:** {{NEXT}}
```
</content>
