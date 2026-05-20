# Brain Engineering Operating System

An **AI engineering team** delivered as a Claude Code plugin. Orchestrates a 10-role agent pipeline that takes a requirement from intake to production for **[Brain](https://brain.pipadacapital.com)** — Pipada Capital's AI-native commerce operating system for D2C brands.

Every agent is grounded in the Brain canon — 55 domain skills + 26 command-skills + a business primer + a technical primer (all shipped inside the plugin). When you install the plugin in your Brain product repo, the agents come with you.

---

## Distribution model

| What | Where |
|---|---|
| The plugin itself (agents, skills, hooks, canon, prompts, workflows) | Lives in `~/.claude/plugins/brain-engineering-os/` after `/plugin install`. **Not in your Brain product repo.** |
| Your Brain product repo | You clone it from wherever Brain's source lives. Contains Brain's code + a `.engineering-os/` directory (shared agent memory). |
| Shared agent memory (`.engineering-os/`) | Committed to your **Brain product repo**, not the plugin. Every teammate who runs `git pull` receives the full memory of every prior run. |

The plugin is repo-decoupled. You install it once; you use it across any Brain product repo.

---

## Setup (per teammate, one-time)

### 1. Add the marketplace and install the plugin

In Claude Code:

```
/plugin marketplace add Rishabhporwal/Engineering-OS
/plugin install brain-engineering-os
```

The plugin lands in `~/.claude/plugins/brain-engineering-os/`. You will not need to look at it.

### 2. Open your Brain product repo in Claude Code

```sh
git clone <your-brain-product-repo>
code <your-brain-product-repo>  # or however you open it
```

### 3. (First-time setup of a Brain repo) Run `/brain-engineering-os:eos-init`

If this is the **first time** the Engineering OS is being used in this particular Brain repo, run:

```
/brain-engineering-os:eos-init
```

This scaffolds `.engineering-os/` and `.gitattributes` into the repo. Commit them. Push. Now every teammate who pulls this repo gets the shared memory baseline.

If you cloned an existing Brain repo that already has `.engineering-os/`, **skip this step** — it's already wired up.

---

## Daily use

All plugin-provided commands are invokable via Claude Code's plugin namespace:

```
/brain-engineering-os:requirement Add abandoned cart recovery for COD orders in GCC
/brain-engineering-os:status                              # what's in flight
/brain-engineering-os:recall feat-abandoned-cart-recovery-gcc   # full history of one feature
/brain-engineering-os:recall-similar re-engage customers who didn't check out   # semantic search across all memory
/brain-engineering-os:reindex                             # refresh the semantic memory index
/brain-engineering-os:watch                               # live stream: what every agent is thinking/doing right now
/brain-engineering-os:qa-browser                          # real-Chromium QA: walk flows, capture errors, gen regression test
/brain-engineering-os:design-review http://localhost:3000/dashboard   # screenshot + 0–10 scored visual audit
/brain-engineering-os:approve feat-abandoned-cart-recovery-gcc  # Founder gate (Stage 7)
/brain-engineering-os:reject feat-... <reason>            # Founder rejection
/brain-engineering-os:deploy feat-...                     # Stage 8 deploy
/brain-engineering-os:rollback feat-... <reason>          # manual rollback
/brain-engineering-os:invoke-skill <skill-name>           # invoke a curated skill ad-hoc
/brain-engineering-os:persona <persona-type> <question>   # spawn one persona for a quick check
/brain-engineering-os:handoff <req-id> <stage>            # manual stage move (escape hatch)
/brain-engineering-os:eos-init                            # one-time per Brain project scaffolder
```

> **Tip:** type `/` in Claude Code and start typing `brain` — autocomplete will surface every available command. You don't have to remember the exact names.

You never see the agent prompts, the Brain canon skills' internals, the workflow YAMLs, or the hook scripts. You see invokable skills, status, and rendered artifacts.

---

## The 10-role team

| Role | Persona | Pipeline stage(s) |
|------|---------|-------------------|
| CTO Advisor (shadow CTO) | **Rohan** | 1, 6 |
| Dynamic Persona Generator | *Runtime-spawned 0–2 in Stage 1* | 1 |
| Architect | **Aryan** | 2 |
| Backend Developer | **Vikram** | 3 |
| Frontend (Web) Developer | **Ananya** | 3 |
| Mobile Developer | **Karan** | 3 |
| Intelligence Engineer (AI/ML/Agents) | **Maya** | 3 |
| Security Reviewer (VETO) | **Shreya** | 4 |
| QA Agent (VETO) | **Tanvi** | 5 |
| Platform/DevOps | **Jatin** | 8 |
| Product Manager | **Priya** | cross-cuts |
| Founder/CTO (you) | **Rishabh** | 7 |

Names are continuous across runs and across teammates. Vikram is always Vikram, with the same memory, no matter who is operating the plugin.

---

## The 8-stage pipeline

```
1. Rohan (CTO Advisor, intake) + 0–2 dynamic personas (by complexity)
2. Architect (Aryan)
3. Parallel Development — Vikram (BE) ∥ Ananya (FE) ∥ Karan (Mobile) ∥ Maya (AI)
4. Security (Shreya) — VETO on CRITICAL/HIGH + India compliance
5. QA (Tanvi) — VETO on missing verification
6. CTO Advisor (final review)
7. Founder Approval (you) — HUMAN GATE
8. Platform/DevOps (Jatin) — CI → staging → prod → 48h auto-rollback
```

Bounces between stages happen automatically when gate conditions fail. Anti-blind-agreement is enforced — every agent must push back on weak requirements.

### Lanes (risk-based tiering)

Not every requirement runs all 8 stages. At Stage 1, Rohan assigns a **lane** by risk:

| Lane | When | Runs | Skips |
|------|------|------|-------|
| **Express** | trivial + zero trigger-surface (copy, docs, config, dep bump) | 1 → 3 → 5 → 7 → 8 | Architect, Security, Final-review |
| **Standard** | normal feature, no trigger-surface | full 8, lean | — |
| **High-stakes** | touches auth / money / multi-tenancy / PII / connectors / schema / India compliance | full 8 + mutation tests + 2 personas + mandatory Shreya VETO | — |

Express skips the three Opus-heavy stages, cutting most of the time and token cost for the long tail of small work. The Founder gate and 48h monitor run in **every** lane. Full rules: [docs/feature-tiering.md](docs/feature-tiering.md).

---

## Shared, git-synced memory (the "agents never forget" guarantee)

When a teammate finishes a feature and pushes, the next teammate who pulls receives the full state: decisions, reviews, artifacts, journal entries — everything. This is delivered by three primitives in your Brain product repo:

```
<your-brain-product-repo>/
├── (your Brain source code)
├── .engineering-os/                    # committed to git
│   ├── memory/
│   │   ├── agents/                     # per-agent append-only journals
│   │   └── features/                   # per-feature append-only journals
│   ├── state/
│   │   ├── active.json                 # currently in-flight requirements
│   │   └── registry.json               # canonical list of every req_id
│   ├── decision-log/                   # YYYY/MM/YYYY-MM-DD.jsonl
│   ├── artifacts/                      # optional per-req cross-links
│   └── runs/                           # per-run timestamped artifact bundles
└── .gitattributes                      # merge=union rules for append-only files
```

**Conflict-resistant by design.** Append-only files use `merge=union`, so simultaneous appends auto-merge. Per-run folders carry a timestamp + operator suffix → no two teammates ever collide on the same path. The only file with last-write-wins is `state/active.json`, which agents always re-read before acting.

---

## What's inside the plugin (you don't need to look)

If you're curious: `~/.claude/plugins/brain-engineering-os/` contains agents, skills, commands, hooks, the Brain canon, workflows, schemas, templates, and the operating manual. It's all plain markdown. Plugins distributed via Claude Code are not cryptographically protected — they're out of your daily workflow, but technically readable if you go looking.

For implementation details, see [docs/plugin-architecture.md](docs/plugin-architecture.md) and [docs/memory-and-git-sync.md](docs/memory-and-git-sync.md) (visible to plugin maintainers; teammates don't need them).

---

## Principles (non-negotiable)

1. **No blind agreement.** Every agent challenges weak requirements.
2. **Memory is the moat.** Decision Log and per-feature journals are append-only forever.
3. **Cost-routed paradigms.** SQL > ML > Haiku > Sonnet.
4. **Single-Primitive Rule.** Every cross-cutting concern is built once, consumed N times.
5. **Multi-tenant `workspace_id` discipline.** Enforced at 4 layers.
6. **India compliance is P0.** DND, NCPR, DLT, calling hours — zero violations.
7. **Goal-driven verification.** Every "done" claim runs a real command and captures real output.

---

## Versioning & updates

When the plugin updates, teammates run:

```
/plugin update brain-engineering-os
```

No code changes in their Brain product repo. The plugin in `~/.claude/plugins/` refreshes; the agents have new capabilities; their memory in `.engineering-os/` carries forward.

---

## Support

For the Founder: see [ROADMAP.md](ROADMAP.md) for V1/V2/V3 scope and the end-to-end walkthrough.
For maintainers: see [docs/](docs/) for the full operating manual.
For teammates: there is no support to ask for. Submit a `/requirement` and the team takes over.

*This plugin is the engineering team. Use it like one.*
