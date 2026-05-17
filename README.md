# Brain Engineering Operating System

An **AI engineering team** delivered as a Claude Code plugin. Orchestrates a 10-role agent pipeline that takes a requirement from intake to production for **[Brain](https://brain.pipadacapital.com)** — Pipada Capital's AI-native commerce operating system for D2C brands.

This is not a generic "AI assistant." Every agent is grounded in the Brain canon — `Requirements/BRAIN_BUSINESS.md`, `Requirements/BRAIN_TECHNICAL.md`, and 54 curated skills that define exactly how Brain thinks about commerce, India-native economics, agentic design, and engineering discipline.

---

## Quick start

1. **Clone the repo.** Everyone on the team works in the same git repo. The plugin code, the Brain canon, and the shared agent memory all live here.
   ```sh
   git clone <your-repo-url> brain-engineering-os
   cd brain-engineering-os
   ```

2. **Open in Claude Code.** The plugin is auto-detected at the repo root (`.claude-plugin/plugin.json`).

3. **Submit a requirement.** Use one of the entry commands (see *Commands* below) and the team takes over from there:
   ```
   /requirement Add abandoned-cart recovery for COD orders in the GCC region
   ```

4. **Approve at the gate.** You (the Founder/CTO) are Stage 7 — final approval before deployment. Everything before that is fully agentic with audit trails.

---

## The 10-role team

| # | Role | Persona | Stage in pipeline |
|---|------|---------|-------------------|
| 1 | CTO Advisor (shadow CTO) | *Rishabh's shadow* | 1, 6 |
| 2 | Dynamic Persona Generator | *Runtime-spawned* | 1 |
| 3 | Architect | **Aryan** | 2 |
| 4 | Backend Developer | **Vikram** | 3 |
| 5 | Frontend (Web) Developer | **Ananya** | 3 |
| 6 | Mobile Developer | **Karan** | 3 |
| 7 | Intelligence Engineer (AI/ML/Agents) | **Maya** | 3 |
| 8 | Security Reviewer | **Shreya** | 4 |
| 9 | QA Agent | **Tanvi** | 5 |
| 10 | Platform/DevOps | **Jatin** | 8 |
| — | Founder/CTO (you) | **Rishabh** | 7 |

> Names match the personas referenced throughout the 53 curated skills in `Requirements/skills/`. They are continuous across runs and across teammates — Vikram is always Vikram, with the same memory, no matter who is operating the plugin.

---

## The 8-stage pipeline

```
1. CTO Advisor (intake) ──┐
   + 3 dynamic personas   │
2. Architect (Aryan)      │
3. Parallel Development   │   Vikram (BE) ∥ Ananya (FE) ∥ Karan (Mobile) ∥ Maya (AI)
4. Security (Shreya)      │── on fail, bounces back to responsible dev
5. QA (Tanvi)             │── on fail, bounces back to responsible dev
6. CTO Advisor (final)    │
7. Founder Approval (you) │── HUMAN GATE
8. Platform/DevOps (Jatin)│
```

Quality gates between every stage. Anti-blind-agreement enforced — every agent can (and must) push back when the requirement is unclear, risky, low-value, or technically expensive. See [docs/operating-system.md](docs/operating-system.md) for the full operating manual.

---

## Shared, git-synced memory (the "agents never forget" guarantee)

All agent memory lives in [.engineering-os/](.engineering-os/) at the repo root. **It is committed to git.** When a teammate runs `git pull`, they receive the full state of every prior run: decisions, reviews, artifacts, journal entries — everything.

```
.engineering-os/
├── memory/
│   ├── agents/          # per-agent append-only journal (architect.journal.md, etc.)
│   └── features/        # per-feature append-only journal (feat-<slug>.md)
├── state/               # current workflow state per active requirement
├── decision-log/        # immutable per-day JSONL log of every decision/recommendation
├── artifacts/           # generated plans, reviews, schemas, code stubs
└── runs/                # full timestamped run logs (one folder per run, no collisions)
```

**Conflict-resistant by design:**
- Per-run folders use `YYYY-MM-DDTHH-MM-SSZ__<feature-slug>__<operator>` → no two operators ever write to the same path.
- Journals are append-only. Merge-conflict surface is essentially zero.
- State files (the small "what is in flight right now" set) use last-write-wins; agents always re-read before acting.

See [docs/memory-and-git-sync.md](docs/memory-and-git-sync.md) for the full model.

---

## Commands

| Command | What it does |
|---------|--------------|
| `/requirement <text>` | Submit a new requirement → kicks off Stage 1 (CTO Advisor + 3 personas) |
| `/status [<req-id>]` | Show the state of all in-flight requirements (or one specific) |
| `/recall <feature-slug>` | Print everything every agent has done on a feature so far |
| `/handoff <req-id> <stage>` | Manually move a requirement to a stage (escape hatch) |
| `/approve <req-id>` | Founder approval (Stage 7 → Stage 8) |
| `/reject <req-id> <reason>` | Founder rejection — bounces back with reason |
| `/deploy <req-id>` | Run Stage 8 (Platform/DevOps) — staging deploy + production with auto-rollback |
| `/rollback <req-id>` | Trigger rollback of a deployed change |
| `/skill <skill-name>` | Manually invoke a curated skill (e.g. `/skill security-baseline`) |
| `/persona <topic>` | Manually spawn a dynamic persona (e.g. `/persona regulatory`) |

---

## Repository layout

```
.
├── .claude-plugin/
│   └── plugin.json                # plugin manifest
├── agents/                        # 10 subagent definitions (md + frontmatter)
├── plugin-skills/                 # 54 curated skills (mirrored from Requirements/skills/)
├── commands/                      # slash commands listed above
├── hooks/                         # plugin hooks (memory rehydration on session start, etc.)
├── docs/                          # operating manual + architecture docs
├── prompts/                       # system prompt + anti-blind-agreement + challenge framework
├── workflows/                     # state machine + approval flow (YAML)
├── schemas/                       # JSON schemas for every artifact type
├── templates/                     # markdown templates for every artifact type
├── Requirements/                  # SOURCE OF TRUTH — Brain canon
│   ├── BRAIN_BUSINESS.md
│   ├── BRAIN_TECHNICAL.md
│   └── skills/                    # 53 curated skill folders
├── .engineering-os/               # SHARED STATE (git-committed)
└── claude_prompt.md               # original team-build prompt (preserved for reference)
```

---

## Documents to read next

- [docs/operating-system.md](docs/operating-system.md) — the complete operating manual
- [docs/folder-context-summary.md](docs/folder-context-summary.md) — what was discovered in `Requirements/`
- [docs/business-context.md](docs/business-context.md) — Brain business primer for every agent
- [docs/technical-context.md](docs/technical-context.md) — Brain technical primer for every agent
- [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md) — which skill belongs to which role
- [docs/role-empowerment-model.md](docs/role-empowerment-model.md) — how each agent uses its skills
- [docs/workflow.md](docs/workflow.md) — the 8-stage pipeline stage-by-stage
- [docs/quality-gates.md](docs/quality-gates.md) — what must be true to advance each stage
- [docs/escalation-rules.md](docs/escalation-rules.md) — when to bounce back, when to escalate to Founder
- [docs/plugin-architecture.md](docs/plugin-architecture.md) — how the plugin itself is built
- [docs/memory-and-git-sync.md](docs/memory-and-git-sync.md) — shared-memory model details
- [ROADMAP.md](ROADMAP.md) — MVP / V2 / V3 build sequence with one end-to-end walkthrough

---

## Principles (non-negotiable)

1. **No blind agreement.** Every agent must respectfully challenge a weak requirement.
2. **Memory is the moat.** Decision Log and per-feature journals are append-only forever.
3. **Cost-routed paradigms.** SQL > ML > Haiku > Sonnet. Every feature passes the Q1–Q4 cost-routing audit.
4. **Single-Primitive Rule.** Every cross-cutting concern (audiences, consent, decision log, attribution, identity, notifications) is built once and consumed N times.
5. **Multi-tenant `workspace_id` discipline.** Enforced at 4 layers (JWT → service-side → DB RLS → Kafka envelope).
6. **India compliance is P0.** DND, NCPR, DLT, calling hours, GST — zero violations.
7. **Goal-driven verification.** Every "done" claim runs a verification command and captures real output.

---

*This plugin is the engineering team. Use it like one.*
