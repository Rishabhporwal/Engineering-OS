# Section 4.1 — Plugin Architecture

> How the Brain Engineering OS plugin itself is built. Read this if you need to extend the plugin, debug a behaviour, or hand it off to a teammate.

> **v0.2.0 model (current).** The plugin is **installable via Claude Code marketplace**, not cloned into a project. It lives in `~/.claude/plugins/brain-engineering-os/`. Brain product repos receive only a `.engineering-os/` scaffold (via `/eos-init`) for shared memory. See [README.md](../README.md) for distribution + setup. The historical "single repo" layout described below was used during the green-field build and reorganised in v0.2.0.

---

## Architectural choice: it is a Claude Code plugin

The Brain Engineering OS is delivered as a **Claude Code plugin**, not a separate web service. Reasons:

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Claude Code plugin (chosen)** | Lives where work happens (the repo); shares git for sync; no extra infra; subagents + skills + commands + hooks are native primitives; works with any Claude Code workspace | Coupled to Claude Code's runtime; less flexibility for non-CLI users | **YES** |
| Standalone web service | Multi-channel access (Slack, web); central state | Needs hosting; auth/multi-tenant; sync infrastructure; UX work; out of scope for this build | NO |
| GitHub Action only | Free, runs on PRs | No interactive intake; no dev-time loop | NO (could augment plugin later) |
| Slack bot | Conversational | Needs hosting; no code context | NO |

A future companion (Slack notifier, GitHub Action) can be added later — the plugin's source of truth (`.engineering-os/`) is in git, so any companion just reads from git.

---

## Components (mapped to Claude Code primitives)

| Plugin primitive | Brain use | Lives in |
|------------------|-----------|----------|
| **Subagents** | The 10 named agents (Rohan, Aryan, Vikram, Ananya, Karan, Maya, Shreya, Tanvi, Jatin, Priya) + the runtime dynamic-persona-generator | [`agents/`](../agents/) |
| **Skills** | The Brain skill library (71 domain skills + 28 command-skills = 99) | [`skills/`](../skills/) |
| **Slash commands** | `/requirement`, `/status`, `/recall`, `/handoff`, `/approve`, `/reject`, `/deploy`, `/rollback`, `/persona`, `/invoke-skill`, `/eos-init`, `/propose-rule`, `/adopt-rule`, `/reject-rule` | command-skills in [`skills/`](../skills/) (`disable-model-invocation: true`) |
| **Hooks** | Session-start memory rehydration; post-tool-use journal append; pre-handoff handoff-event logging; on-careful PreToolUse catastrophic-command guard | [`hooks/`](../hooks/) |
| **Plugin manifest** | Declares everything above | [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) |
| **Persistent state** | Shared memory, decision log, run artifacts — git-committed | [`.engineering-os/`](../.engineering-os/) |
| **Reference docs** | Operating manual, business/technical primer, skill matrix, role empowerment, this file | [`docs/`](../docs/) |
| **Templates + schemas** | Artifact shapes (CTOA review, plan, dev report, security review, etc.) | [`templates/`](../templates/), [`schemas/`](../schemas/) |
| **Workflows** | State machine YAML, approval flow, requirement-to-release | [`workflows/`](../workflows/) |
| **System prompts** | The shared system prompt, the anti-blind-agreement prompt, the challenge framework | [`prompts/`](../prompts/) |

---

## File layout

### Plugin files (shipped in `~/.claude/plugins/brain-engineering-os/`)

```
brain-engineering-os/                        # THE PLUGIN
├── .claude-plugin/
│   └── plugin.json                          # plugin manifest (with components block)
├── agents/                                  # 11 subagent files (10 named + dynamic-persona-generator; md + frontmatter)
│   ├── cto-advisor.md
│   ├── dynamic-persona-generator.md
│   ├── architect.md                         (Aryan)
│   ├── backend-developer.md                 (Vikram)
│   ├── frontend-web-developer.md            (Ananya)
│   ├── mobile-developer.md                  (Karan)
│   ├── intelligence-engineer.md             (Maya)
│   ├── security-reviewer.md                 (Shreya)
│   ├── qa-agent.md                          (Tanvi)
│   ├── platform-devops.md                   (Jatin)
│   └── product-manager.md                   (Priya)
│
├── skills/                                  # all skills: domain skills + command-skills
│   ├── agentic-design/                      # domain skill (model-auto-loaded)
│   ├── domain-driven-design/
│   ├── requirement/                         # command-skill (disable-model-invocation: true)
│   ├── approve/                             # command-skill
│   └── ...
│
├── hooks/
│   ├── hooks.json                           # hook registry
│   ├── on-session-start.sh                  # rehydrate state on session start
│   ├── on-pre-handoff.sh                    # handoff event logger (observability only)
│   ├── on-post-tool-use.sh                  # auto-append to journal
│   └── on-careful.sh                        # PreToolUse guard — blocks catastrophic Bash
│
├── docs/                                    # operating manual
│   ├── operating-system.md
│   ├── business-context.md
│   ├── technical-context.md
│   ├── skill-mapping-matrix.md
│   ├── role-empowerment-model.md
│   ├── workflow.md
│   ├── quality-gates.md
│   ├── escalation-rules.md
│   ├── plugin-architecture.md               # ← this file
│   ├── technical-implementation.md
│   └── memory-and-git-sync.md
│
├── prompts/
│   ├── system-prompt.md                     # shared system prompt
│   ├── anti-blind-agreement.md
│   └── challenge-framework.md
│
├── workflows/
│   ├── requirement-to-release.yaml          # the 8-stage pipeline as data
│   ├── state-machine.yaml                   # status transitions
│   └── approval-flow.yaml                   # founder approval mechanics
│
├── schemas/                                 # JSON Schemas (Draft-07) for every artifact
│   ├── requirement.schema.json
│   ├── cto-advisor-review.schema.json
│   ├── dynamic-persona.schema.json
│   ├── architecture.schema.json
│   ├── development-report.schema.json
│   ├── security-review.schema.json
│   ├── qa-review.schema.json
│   ├── final-review.schema.json
│   ├── deployment.schema.json
│   ├── retro.schema.json
│   ├── skill-registry.schema.json
│   └── agent-registry.schema.json          # 12 schemas total
│
├── templates/                               # markdown templates
│   ├── requirement-template.md
│   ├── cto-advisor-review.md
│   ├── dynamic-persona-review.md
│   ├── architecture-plan.md
│   ├── developer-report.md
│   ├── security-review.md
│   ├── qa-review.md
│   ├── final-review.md
│   ├── deployment-report.md
│   ├── retro.md
│   ├── rule-proposal.md
│   └── durable-rule.md                      # 12 templates total
│
├── canon/                                   # SOURCE OF TRUTH — Brain canon (ships with plugin)
│   ├── business-requirements.md
│   └── technical-requirements.md
│
├── ROADMAP.md
└── README.md
```

### Consumer repo files (scaffolded by `/eos-init` in the Brain product repo)

```
<brain-product-repo>/
├── .engineering-os/                         # SHARED STATE — git-committed in the PRODUCT repo
│   ├── memory/
│   │   ├── agents/                          # per-agent journals (append-only)
│   │   │   ├── cto-advisor.journal.md
│   │   │   ├── architect.journal.md
│   │   │   ├── backend.journal.md
│   │   │   ├── frontend-web.journal.md
│   │   │   ├── frontend-mobile.journal.md
│   │   │   ├── intelligence.journal.md
│   │   │   ├── security.journal.md
│   │   │   ├── qa.journal.md
│   │   │   ├── platform.journal.md
│   │   │   └── product.journal.md
│   │   └── features/                        # per-feature journals (append-only)
│   │       └── feat-<slug>.md
│   ├── state/
│   │   ├── active.json                      # currently in-flight requirements + statuses
│   │   └── registry.json                    # canonical list of all req-ids ever seen
│   ├── decision-log/                        # YYYY/MM/YYYY-MM-DD.jsonl
│   │   └── 2026/05/2026-05-17.jsonl
│   ├── artifacts/                           # per-req artifact bundles (optional cross-link)
│   │   └── <req-id>/
│   ├── runs/                                # full per-run logs (timestamped, collision-free)
│   │   └── 2026-05-17T14-22-31Z__a3f201__feat-<slug>__<operator>/
│   ├── rule-proposals/                      # self-improvement substrate (v0.4.0+)
│   ├── durable-rules/
│   ├── lessons-learned.md
│   └── pending-founder-attention.md
│
└── .gitattributes                           # merge=union rules for append-only files
```

---

## Plugin manifest ([`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json))

Already created. Key fields:

```json
{
  "name": "brain-engineering-os",
  "version": "0.24.0",
  "components": {
    "agents": "./agents",
    "skills": "./skills",
    "hooks": "./hooks/hooks.json"
  },
  "engineering-os": {
    "shared-state-dir": ".engineering-os",
    "memory-model": "git-committed append-only journals",
    "canon-roots": [
      "canon/business-requirements.md",
      "canon/technical-requirements.md",
      "skills"
    ],
    "team": { ... 10 personas ... }
  }
}
```

The `components` block tells Claude Code where to find the agents, skills (including command-skills / slash commands), and hooks. The `engineering-os` block is a Brain-specific extension (Claude Code ignores fields it doesn't know). Future hooks read it to find the shared state dir, the canon roots, and the team naming.

---

## Subagent design (the 11 agents)

Each agent is a markdown file with YAML frontmatter, following Claude Code's subagent format:

```markdown
---
name: backend-developer
description: Vikram — Brain's Node-side backend developer. Owns api-gateway, core-service, notifications-service. Auto-load when work touches Fastify routes, tRPC procedures, gRPC servers/clients, Prisma migrations, KafkaJS, Zod schemas. PROACTIVELY use for any Stage 3 backend track.
tools: [Read, Edit, Write, Bash, Grep, Glob, TodoWrite]
model: sonnet
---

# Vikram — Backend Developer

[role mission + responsibilities + assigned skills + decision rights + inputs + outputs + quality checklist + escalation rules + prompt instructions + anti-blind-agreement behavior]
```

The body of each agent file embeds:
- The shared system prompt header (link to `prompts/system-prompt.md`).
- The agent's mission, authority, operating loop (from `role-empowerment-model.md`).
- The agent's owned-skill list (from `skill-mapping-matrix.md`).
- The anti-blind-agreement triggers specific to this role.
- The journal entry template.

Why this structure: Claude Code loads each subagent into its own sub-conversation with this exact body as its system prompt. Token-budget aware — each agent only loads what it needs.

---

## Skill design

Skills live in `skills/<name>/SKILL.md`. Claude Code auto-discovers them from the plugin — there is no mirror, copy, or build step. Two kinds:

- **Domain skills** (model-auto-loaded): frontmatter is `name` + `description`. An agent loads its owned domain skills (per [`skill-mapping-matrix.md`](skill-mapping-matrix.md)) plus any whose description matches the task at hand.
- **Command-skills** (human-triggered): frontmatter adds `disable-model-invocation: true` (+ optional `argument-hint`). These ARE the slash commands — they run only when a person types `/brain-engineering-os:<name>`.

See [`skill-authoring-guide.md`](skill-authoring-guide.md) for when to author a full skill vs. inline a rule.

---

## Slash command design

Each slash command is a command-skill: `skills/<name>/SKILL.md` with `disable-model-invocation: true`.

```markdown
---
name: requirement
description: Submit a new requirement to the Engineering OS pipeline (Stage 1)
disable-model-invocation: true
argument-hint: <requirement text in natural language>
---

[skill body: how to interpret $ARGUMENTS and route to the cto-advisor subagent]
```

When the user types `/brain-engineering-os:requirement <text>`, Claude Code:
1. Reads the skill body.
2. Substitutes `$ARGUMENTS` with the user's input.
3. Invokes the body as a prompt — typically delegating to the `cto-advisor` subagent.

---

## Hook design

Hooks are shell scripts (or any executable) registered in `hooks/hooks.json`. Four hooks:

### 1. `on-session-start.sh` (event: `SessionStart`)

Runs once when Claude Code opens. Steps:
1. Read `.engineering-os/state/active.json`.
2. Print a concise summary: "3 requirements in flight: feat-X (Stage 4 — Shreya), feat-Y (Stage 7 — awaiting Founder), feat-Z (Stage 8 — monitoring)."
3. For each agent, read the last 5 entries of its journal and stage them as context (via Claude Code's session-start hook mechanism — typically a `<system-reminder>` style injection).

This is **what makes the "agents never forget" guarantee real**.

### 2. `on-pre-handoff.sh` (event: `PreToolUse` matching `Write`)

Runs before a Write tool use is committed. **Observability only — does NOT block.** Steps:
1. Detect writes to `runs/` folders (handoff artifacts live there).
2. Check content for handoff-signal keywords (`READY-FOR-SECURITY`, `READY-FOR-QA`, `verdict: PASS`).
3. If detected, append a timestamped event to `.engineering-os/memory/handoff-attempts.log` for audit trail.

> **Why this hook doesn't enforce gates:** Gate enforcement is intentionally the agents' job — each stage owner self-reviews against [quality-gates.md](quality-gates.md), QA (Tanvi) re-runs skipped gates (W13), and CTOA (Rohan) spot-re-runs QA's gates at Stage 6 (W14). A stdin heuristic doesn't have the context to judge whether a gate is truly met; the agents do. Keep enforcement in agents; keep this hook for the audit trail.

### 3. `on-post-tool-use.sh` (event: `PostToolUse`)

Runs after any tool use by any agent. Steps:
1. Inspect the tool result.
2. If it's a meaningful action (Edit / Write / Bash with side effect), **auto-append a journal entry** to the active agent's journal with: timestamp, agent, action summary, files touched, command output snippet.

This makes journaling automatic — agents can't forget to journal because the hook does it.

### 4. `on-careful.sh` (event: `PreToolUse` matching `Bash`)

An always-on guard that **blocks a tight set of catastrophic Bash commands** before they run — `rm -rf /` (or `~`/`$HOME`/bare-wildcard/`--no-preserve-root`), `git push --force`/`-f` (force-with-lease allowed), destructive SQL (`DROP TABLE`/`DROP DATABASE`/`TRUNCATE`), raw disk writes (`mkfs`/`dd of=/dev/…`), and recursive `chmod 777`. High-signal, low-friction: routine destructive-but-safe ops (`rm -rf ./build`, feature-branch `git push`, `git reset --hard`) pass untouched. Override per-command with `EOS_ALLOW_DESTRUCTIVE=1` or a trailing `#careful-ok`. **Fails open** (allows) if `jq` is unavailable, so it can never wedge the pipeline. See [careful-guard.md](careful-guard.md).

---

## State persistence model

All state is **plain files in git**. No database. No external service. Three categories:

| Category | Format | Where | Conflict-resistance |
|----------|--------|-------|---------------------|
| **Journals** (memory) | Markdown, append-only | `.engineering-os/memory/{agents,features}/` | Append-only — merge conflicts only on simultaneous appends, easily resolved by accepting both |
| **Decision log** | JSONL, append-only, line-per-decision | `.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl` | Append-only — line-level merge always works |
| **State** (active requirements) | JSON | `.engineering-os/state/active.json` | Last-write-wins; agents always re-read before acting; conflicts caught and surfaced |
| **Per-run artifacts** | Markdown + JSON | `.engineering-os/runs/<ts>__<req>__<operator>/` | Per-folder timestamp + operator → zero collision possible |

Detailed mechanics in [memory-and-git-sync.md](memory-and-git-sync.md).

---

## Integration points

The plugin can integrate with external systems via opt-in env vars:

| System | Env var | What it enables |
|--------|---------|-----------------|
| GitHub | `GITHUB_TOKEN` | DevOps (Jatin) opens PRs; QA (Tanvi) attaches test output as PR comments |
| Slack | `SLACK_WEBHOOK_URL` | Stage 7 sends Founder a notification; rollback alerts; daily digest |
| ClickUp / Linear / Jira | `CLICKUP_TOKEN` / `LINEAR_API_KEY` / `JIRA_TOKEN` | Priya syncs the plan to tasks (see [`task-tracker-integration`](../skills/task-tracker-integration/SKILL.md)) |
| Anthropic API | `ANTHROPIC_API_KEY` | (Already required by Claude Code; agents inherit) |
| AWS CDK | `AWS_PROFILE` | Jatin runs `cdk diff` / `cdk deploy` (Stage 8) |
| Sentry | `SENTRY_AUTH_TOKEN` | Release tagging |

If a token is missing, the corresponding workflow gracefully degrades: actions are logged to `.engineering-os/memory/tasks-pending.log` and the pipeline continues. (Pattern from [`task-tracker-integration`](../skills/task-tracker-integration/SKILL.md).)

---

## Authentication & authorization (within the plugin)

The plugin runs in the local user's Claude Code session — no inbound auth surface to defend. Authorization concerns:

- **Founder gate (Stage 7):** Enforced by the `approve` / `reject` slash commands recording the actor (current local OS user). For stronger guarantees in V2, the gate could require a signed commit.
- **External integrations:** Tokens are read from env vars; never written to disk.
- **Secrets in memory:** Journals must not record secrets. The journaling hook redacts known token patterns (`sk-`, `xoxb-`, etc.) before writing.

---

## Event model (within the plugin)

The plugin treats agent handoffs as events. Event types:

| Event | Emitted by | Consumed by |
|-------|------------|-------------|
| `requirement.submitted` | `/requirement` command | CTOA |
| `intake.completed` | CTOA Stage 1 | Aryan |
| `intake.challenged` | CTOA Stage 1 | Founder (notification) |
| `plan.completed` | Aryan Stage 2 | Vikram / Ananya / Karan / Maya (whoever tagged) |
| `dev.ready` | Each dev when in-lane DoD green | (counter — when all green, → Shreya) |
| `security.passed` | Shreya | Tanvi |
| `security.failed` | Shreya | Responsible dev |
| `qa.passed` | Tanvi | CTOA |
| `qa.failed` | Tanvi | Responsible dev |
| `final-review.passed` | CTOA | Founder (Stage 7 notification) |
| `founder.approved` | Founder | Jatin |
| `founder.rejected` | Founder | CTOA (re-route) |
| `deploy.staging-passed` | Jatin | (gate to prod) |
| `deploy.prod-passed` | Jatin | (48h monitor begins) |
| `monitor.clean` | Jatin (after 48h) | (status → `shipped`) |
| `monitor.alarm` | Auto | Jatin + Founder |
| `rollback.triggered` | Auto | Jatin + Shreya + Tanvi (re-enter Stage 4) |

Events are realized as: an entry in the decision log + a status update in `state/active.json` + (optionally) a Slack notification.

---

## Error handling

| Error class | Plugin behaviour |
|-------------|------------------|
| Agent runs out of context | Falls back to "read journal first, then act" pattern; surfaces "I lost context — re-read journal" to user |
| Gate fails at a handoff | The receiving agent (Shreya / Tanvi / Rohan) bounces with a structured note naming the missing evidence; the pipeline pauses at that stage, not crashes. (Enforcement is in the agents; the pre-handoff hook only logs the event.) |
| External token missing | Logs to `tasks-pending.log`; pipeline continues; notifies Founder at next status check |
| Git merge conflict on a journal | Append-only conflicts are auto-resolved by `git merge -X ours` for whitespace; substantive conflicts surface to user with reconciliation steps |
| State JSON corrupted | Plugin refuses to start; surfaces backup recovery from `.engineering-os/state/active.json.bak.<ts>` (created on each write) |
| Skill missing | Agent surfaces the missing skill to the user and proceeds with its remaining owned skills + canon; no silent skip |

---

## Audit logging

Every meaningful action produces **two** audit trails:

1. **Decision log** (`.engineering-os/decision-log/*.jsonl`) — structured, line-per-event, immutable. Searchable by `req_id`, `actor`, `type`.
2. **Per-agent + per-feature journals** (`.engineering-os/memory/`) — narrative, human-readable, append-only.

A weekly digest job (V2, `/digest` command) aggregates these into a readable Friday summary: features shipped, gates hit, bounces, escalations, who did what.

---

## Security model (of the plugin itself)

- **No secrets in committed files.** Tokens read from env vars only. Pre-commit hook (V2) scans for accidental commits of secret-looking strings.
- **Hooks are shell scripts** — readable, auditable. No binary plugins.
- **All state in plain files** — `cat` any state file to inspect.
- **No outbound network unless explicitly integrated** (GitHub, Slack, task tracker). Default plugin run is fully local + git.
- **Founder gate is enforced** by the slash command requiring explicit `/approve` invocation; subagents cannot self-approve.

---

## Deployment of the plugin

For Brain's own team, the plugin is checked into the same repo as the project. Teammates clone, open in Claude Code, work. No separate install.

For other Brain-style teams (future), the plugin can be packaged as a standalone Claude Code plugin per the [Claude Code plugin distribution model](https://docs.claude.com/en/docs/claude-code/plugins) — published to a plugin marketplace, installed via `/plugin install`. The plugin's `.engineering-os/` is then created in the consumer repo.

---

## Why this architecture wins for Brain

- **No infra to maintain.** The plugin is the team; the repo is the database; git is the sync.
- **Multi-operator from day one.** Anyone with repo access has the same view of the team's state.
- **Audit by default.** Every decision is in git history forever.
- **Reversible.** A bad plugin update is `git revert`; bad agent behavior is `git revert` + journal note.
- **Aligned with Brain's principles.** Append-only journals = "Memory is the moat." Single-Primitive in plugin design (one Audience Builder analogue per concern).

---

## Next reads

- [technical-implementation.md](technical-implementation.md) — concrete pieces, example requests/responses, example DB tables, example workflow payload.
- [memory-and-git-sync.md](memory-and-git-sync.md) — shared memory in detail, conflict avoidance.
