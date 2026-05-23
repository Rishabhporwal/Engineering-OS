# Lessons-Learned Registry — Format Specification

> The append-only registry of lessons distilled from per-child retros. Lives at `${CLAUDE_PROJECT_DIR}/.engineering-os/lessons-learned.md` in the consuming Brain product repo.
>
> **Read by:** CTOA at every Stage 1 intake (mandatory step 3a in `agents/cto-advisor.md`).
> **Written by:** CTOA at every Stage 6 retro (mandatory step 8 in `agents/cto-advisor.md`).
> **Mutation rule:** APPEND ONLY. Never edit prior entries. Never reorder. Outdated lessons are *superseded*, not deleted.

---

## File header

The file begins with:

```markdown
# Brain Engineering OS — Lessons Learned

> Append-only registry. Each entry sourced from a per-child retro (`14-retro.md`).
> CTOA reads relevant entries at every Stage 1 intake.
> Mutation rule: append only. Outdated lessons are SUPERSEDED, not deleted.

---
```

## Entry format

Each lesson is one section:

```markdown
## L-<NNN> — <one-line lesson>

| Field | Value |
|---|---|
| **Filed** | <ISO timestamp> |
| **Sourced from** | <req_id> retro |
| **Applies to** | <comma-separated tags> |
| **Status** | active | superseded-by-L-<NNN> |

**Lesson:** <2-4 sentence elaboration>

**Evidence:** <one-paragraph cite of the artifact / observation that surfaced this lesson>

**How CTOA should apply at intake:**
- <one or two concrete bullets — what to check, what to bias toward, what to bounce on>
```

Tags (`applies_to`) — pick all that apply:

- `process` — operating model / handoff / journaling
- `code` — implementation patterns
- `security` — auth / secrets / multi-tenancy
- `india-compliance` — DLT / NCPR / DND / GST / RTO
- `numeric-parity` — paisa-level parity vs an external/reference dashboard
- `cost-routing` — paradigm choice (SQL/ML/Haiku/Sonnet)
- `single-primitive` — Single-Primitive Rule violations or near-misses
- `migration` — legacy → Brain shape changes
- `agent-discipline` — agents over-engineering / under-engineering / silently skipping gates
- `pipeline-mechanics` — handoff / state / decision-log / git
- `infra` — AWS / hooks / observability

## Superseding

When a lesson becomes incorrect or is replaced by a better lesson:

1. Add a NEW lesson `L-<NNN>` (next sequential number).
2. In the new lesson's body, note "Supersedes L-<OOO> because <reason>."
3. In the prior lesson, change `Status: active` to `Status: superseded-by-L-<NNN>`. **This is the ONLY allowed mutation to a prior entry.** No content edits to prior lessons; the supersession line is sufficient.

## Example entries

These would be the first few entries if generated from the Brain repo's first 4 children:

### L-001 — Subagents must journal mid-execution, not only at handoff

| Field | Value |
|---|---|
| **Filed** | 2026-05-19T11:30:00Z |
| **Sourced from** | chore-eos-canon-into-repo retro |
| **Applies to** | process, agent-discipline |
| **Status** | active |

**Lesson:** Developer agents (Vikram et al.) defaulted to journaling only at handoff time. For Stage 3 work >2 hours, this creates a silent execution window where observers (other agents, Founder, `/status`) can't tell whether work is progressing or stuck. Codified in v0.3.1 as mid-execution journaling protocol (every ~30 min or per track boundary).

**Evidence:** Child #1's Vikram journal had only one entry (bootstrap) until the final handoff signal hours later. The team monitored child #1 via the auto-journal hook noise file because real journals were silent.

**How CTOA should apply at intake:**
- For estimated multi-hour stages, remind agents to journal per track boundary in the handoff brief.
- If a builder goes >2 hours without a journal entry, surface as a stuck-state in `/status`.

### L-002 — Same-second run folder collisions are real

| Field | Value |
|---|---|
| **Filed** | 2026-05-19T11:30:00Z |
| **Sourced from** | chore-turborepo-monorepo retro |
| **Applies to** | infra, pipeline-mechanics |
| **Status** | active |

**Lesson:** Children #3 and #4 were intaken close enough in time that both run folders used the same `2026-05-19T14-30-00Z` timestamp prefix; the only differentiator was the req_id segment. v0.3.1 added a `<hex6>` random suffix to mechanically prevent this.

**Evidence:** `ls -la .engineering-os/runs/` after children #3 and #4 showed two folders identical except for the req-id segment.

**How CTOA should apply at intake:**
- Verify `<hex6>` is present in the new run folder name before proceeding to step 4.
- If the format check fails, the v0.3.1 upgrade isn't fully picked up — `/reload-plugins` and retry.

---

## Bootstrap by /eos-init

The `/brain-engineering-os:eos-init` skill writes an initial empty `.engineering-os/lessons-learned.md` with just the header so the file exists for the first CTOA intake to read. Initial body says "No lessons filed yet. First entry will come from the first child's retro."
