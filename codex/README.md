# Engineering OS under OpenAI Codex

The Engineering OS ships as a **Claude Code plugin**, but the organization it encodes — the roster, the pipeline, the gates, the Iron Laws, the shared memory — is **runtime-agnostic**. This directory makes the same OS usable from **OpenAI Codex**.

> **Read [`../AGENTS.md`](../AGENTS.md) first.** It is the cross-runtime operating contract and Codex loads it automatically. This README only covers Codex-specific install + the runtime differences.

---

## How the runtimes differ

| | Claude Code (plugin) | Codex |
|---|---|---|
| Roster execution | each role is a dispatched **subagent** | **one agent** rotates through the roles in pipeline order |
| Skill loading | `Skill` tool + frontmatter auto-load | the agent **`Read`s** `skills/<name>/SKILL.md` when the task matches its trigger |
| Gate enforcement | Security/QA **subagents** + **hooks** | the agent plays the reviewer hat honestly and **blocks itself** on a failing gate |
| Commands | `/engineering-os:<name>` plugin commands | Codex custom prompts in `~/.codex/prompts/` (mirrored here) |
| Shared memory | `.engineering-os/` (git) | **identical** `.engineering-os/` (git) |

The **process, gates, journals, Canon, and Iron Laws are identical.** The only thing that changes is *who* executes a role (N subagents vs. one agent wearing hats) and *how* a command is invoked.

---

## Install (Codex)

1. **Point Codex at this repo's contract.** Codex auto-loads `AGENTS.md` from the repo root — nothing to do beyond having `../AGENTS.md` present (it is). For a consuming product repo, copy `../AGENTS.md` to that repo's root (or add an `AGENTS.md` that links to the installed OS).

2. **Install the command prompts.** Copy the prompt mirrors into your Codex prompts dir:
   ```bash
   mkdir -p ~/.codex/prompts
   cp codex/prompts/*.md ~/.codex/prompts/
   ```
   They then appear in Codex as `/eos-requirement`, `/eos-status`, `/eos-handoff`, `/eos-deploy`, `/eos-decide`, `/eos-init` (namespaced with an `eos-` prefix to avoid clashing with built-ins).

3. **Scaffold shared memory** (once per product repo): run `/eos-init` in Codex, or follow [`../skills/eos-init/SKILL.md`](../skills/eos-init/SKILL.md) — it writes the same `.engineering-os/` substrate the plugin uses. (Substitute `${CLAUDE_PROJECT_DIR}` → your repo root; the layout is identical.)

4. **(Optional) MCP servers** — if your adoption exposes an MCP surface (see [`../mcp/`](../mcp/)), register it in `~/.codex/config.toml` under `[mcp_servers]`. The same server definition works for both runtimes.

---

## Operating the pipeline as one agent

When you run a requirement under Codex you are **all twelve roles in turn**. Walk the stages in [`../AGENTS.md`](../AGENTS.md) §"The pipeline", and at each one:

1. `Read` the owning role's file in [`../agents/`](../agents/) and the skills it triggers (per [`../docs/skill-mapping-matrix.md`](../docs/skill-mapping-matrix.md)).
2. Do that role's work; **verify with real command output**; append the role's journal entry.
3. **Switch hats to the next gate and review your own output as that reviewer would.** A VETO gate (Security CRITICAL/HIGH, QA missing smoke/parity) blocks *you* — you do not advance past a gate you would have failed. This is the discipline that replaces the separate enforcing subagent.

The full proficiency / ownership / backup model for the roster is in [`../docs/engineering-skills-matrix.md`](../docs/engineering-skills-matrix.md).

---

## Keeping the two runtimes in sync

Both runtimes describe **one** organization. When a role, skill, or gate changes, update it once in the canonical files ([`../agents/`](../agents/), [`../skills/`](../skills/), [`../docs/`](../docs/)) — `AGENTS.md` and these prompts **cite** those files, they don't fork the logic. The prompt mirrors here are deliberately thin wrappers that delegate to the same `SKILL.md` instructions the plugin uses, so there is no second copy to drift.
