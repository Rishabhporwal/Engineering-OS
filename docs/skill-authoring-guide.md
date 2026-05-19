# Skill Authoring Guide

> How to extend the Brain Engineering OS without bloating it. Read this before adding a new skill, a command, or an inline rule. The governing principle is the same one the team enforces in product code: **don't over-engineer** — the smallest thing that covers the need wins.

## First decision: inline a rule, or author a full skill?

Most of the time you do NOT need a new skill. Decide in this order:

| If the guidance is… | Put it… |
|---|---|
| One or two sentences that apply to everyone, always | In `prompts/system-prompt.md` (universal) — inline rule |
| Specific to one agent's stage/lane | In that agent's `.md` (operating loop / "Don't" section) |
| A reusable, multi-section discipline an agent must *load* when doing a kind of work | A full `skills/<name>/SKILL.md` |
| A human-or-agent-triggered action (`/something`) | A command skill (`disable-model-invocation: true`) |
| Maintainer/process guidance (like this file) | A `docs/*.md` |

**STOP signals — you do NOT need a new skill:**
- It duplicates an existing skill (check the [skill-mapping-matrix](skill-mapping-matrix.md) first — many concepts already exist).
- It's a single rule (inline it instead).
- It's a one-off for a single requirement (it belongs in the run, not the plugin).
- You can't name three distinct situations where an agent would load it.

Authoring a duplicate or a one-rule skill IS the over-engineering the team's own durable rule forbids.

## Two kinds of skill

| Kind | Frontmatter | Invoked by | Examples |
|---|---|---|---|
| **Domain/discipline skill** | `name` + `description` (no `disable-model-invocation`) | Auto-loaded by an agent (model-invocable) | `testing-tdd`, `agentic-actions-auditor`, `verification-before-completion` |
| **Command skill** | `name` + `description` + `disable-model-invocation: true` (+ optional `argument-hint`) | A human typing `/brain-engineering-os:<name>` | `requirement`, `approve`, `deploy`, `eos-init`, `adopt-rule` |

Command skills are deliberate actions a person triggers; domain skills are knowledge an agent pulls in. Don't add `disable-model-invocation` to a domain skill — it makes it un-loadable by agents.

## House style for a domain skill

Match the existing skills (see `skills/verification-before-completion/SKILL.md` as the canonical example):

1. **Frontmatter** — `name` (kebab-case, matches folder) + a `description` that says *what it is* AND *when to auto-load it* (the description is how agents decide relevance, so be specific).
2. **Title + one-line tagline** (blockquote) — the punchy "why this matters".
3. **The Iron Law** — the one non-negotiable, in a code block.
4. **A process/gate** — the steps to actually do the thing.
5. **Tables** — classification tables and an Excuse→Reality rationalization table.
6. **Red flags — STOP** — the signals to bounce.
7. **Brain wiring** — owner + reference table tying it to roles/agents.
8. **The bottom line** + **Related** links.

Keep it grounded in Brain's locked stack (pnpm/uv/buf/dbt/Cypress/Detox/Expo/k6, ClickHouse, Supabase, India compliance) — generic advice that ignores the stack is low-value.

## Registration checklist (a new domain skill isn't done until)

- [ ] `skills/<name>/SKILL.md` written in house style.
- [ ] Added to the table in [skill-mapping-matrix.md](skill-mapping-matrix.md) (domain, primary owner, shared-with).
- [ ] Added to the owning agent's **Owned skills** list in `agents/<role>.md`.
- [ ] Added to the matrix's per-role "Skills by role" list.
- [ ] If it changes an agent's behavior, referenced in that agent's operating loop.
- [ ] Cross-linked from related skills' "Related" lines.

A command skill skips the matrix but must be namespaced correctly and documented in the README's command list.

## The bottom line

Prefer an inline rule over a skill, and an existing skill over a new one. When you do author a skill, make it a reusable discipline in house style, ground it in the Brain stack, and register it in the matrix. Fewer, sharper skills beat a sprawling library no agent can navigate.
