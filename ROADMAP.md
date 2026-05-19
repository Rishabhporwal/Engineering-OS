# Brain Engineering OS — Implementation Roadmap

> Section 8 of the build prompt. Scope by version + developer task breakdown + suggested tech stack + build sequence + risks/mitigations + rollout plan + one full end-to-end feature walkthrough.

---

## Versions

### V1 — MVP (this checkout)

**Goal:** the team works. A teammate can clone, open Claude Code, run `/requirement`, and get a feature through to Founder approval with full audit trail.

**In scope:**
- 10 agents (CTO Advisor, Architect, Backend, Web, Mobile, Intelligence, Security, QA, DevOps, PM) + Dynamic Persona Generator (runtime).
- Slash commands (`/requirement`, `/status`, `/recall`, `/handoff`, `/approve`, `/reject`, `/deploy`, `/rollback`, `/persona`, `/invoke-skill`, `/eos-init`, `/propose-rule`, `/adopt-rule`, `/reject-rule`) — implemented as command-skills.
- The curated skill library, auto-loaded per agent's owned-skill list (domain skills) + human-triggered command-skills.
- 8-stage pipeline (Stage 1 intake → Stage 8 deploy + 48h monitor).
- Shared, git-committed memory in `.engineering-os/` with append-only journals + decision log.
- 3 hooks (session-start, post-tool-use, pre-handoff) — pre-handoff is handoff-event logging; gate enforcement lives in the agents.
- 11 JSON schemas + 9 markdown templates.
- All 12 docs (operating manual, workflow, gates, escalation, plugin architecture, etc.).
- Conflict-resistant multi-operator sync via git + `merge=union`.

**Explicitly out of MVP** (deferred to V2):
- Auto-merge PRs after Founder approval.
- `/digest` weekly summary slash command.
- Per-feature graphs of stage-time and bounce-count.
- Slack/Discord/email notifications at gate transitions.
- Auto-archive of run folders older than 365 days.
- Pre-commit secret-scanning hook.

### V2 — Production-ready (4–8 weeks after MVP)

**Goal:** the plugin operates safely at multi-operator scale without manual reconciliation.

- **Hook hardening:**
  - `pre-commit` secret-scanning hook.
  - `on-session-start` surfaces stuck items (>2 days in same stage) with recommended action.
- **Skill-library CI check:** fail CI if a skill folder isn't mapped in `skill-mapping-matrix.md` (catches drift between the library and the matrix).
- **`/digest` slash command:** weekly Friday summary aggregating decision log: features shipped, gates fired (PASS/FAIL), average time-in-stage, top bounce causes.
- **External integrations** (opt-in via env vars):
  - GitHub: Jatin opens PRs; Tanvi attaches test output as PR comments.
  - Slack: notification on Stage 7 awaiting-founder, rollback, daily digest.
  - ClickUp / Linear / Jira: Priya syncs req-ids to tracker.
- **Recommended additional skills** (4 candidates flagged for a future build):
  - `requirement-intake`
  - `dynamic-persona-spawning`
  - `production-readiness-checklist`
  - `release-notes-and-changelog`
- **Archive policy:** runs/ older than 365 days move to `.engineering-os/archive/runs/<YYYY>/`.
- **Founder Slack approval** as an alternate to `/approve`.
- **Cost dashboards** showing per-feature LLM token consumption (rolling 30d).

### V3 — Multi-team scale (post-Phase 2 of Brain itself)

**Goal:** the plugin works for multiple parallel Brain projects, multi-team handoffs, and serves as the template for the AICMO/AICOO/AICFO agent pattern Brain uses internally.

- **Team contexts:** support multiple Brain projects (e.g., main app + retail-OS spin-off) in the same plugin install, with per-project `.engineering-os/`.
- **Cross-agent escalation routing:** structured "I need Maya's input" → automatic peer-review side thread.
- **Incident response pipeline** (new vertical alongside the feature pipeline): `/incident <text>` → on-call → triage → mitigation → postmortem.
- **On-call rotation** management.
- **Founder Slack workflow** for approve/reject without CLI access.
- **Runbook generation** from per-feature journals + ops decisions.
- **Open-source release** of the plugin shell (without Brain-specific canon) for external D2C teams to adapt.

---

## Suggested tech stack for the plugin itself

The plugin uses what Claude Code provides; very little new tech needed.

| Concern | Tool |
|---------|------|
| Plugin runtime | Claude Code |
| Agent system prompts | Markdown + YAML frontmatter |
| State persistence | Plain JSON + JSONL in git |
| Memory persistence | Plain Markdown in git |
| Hooks | Bash + `jq` |
| Templates | Markdown |
| Schemas | JSON Schema Draft-07 |
| Workflow definition | YAML |
| Integrations (V2+) | `gh` (GitHub), `curl` (Slack webhook), `clickup-cli` / `linear` |

> **Deliberately minimal.** No database. No external service. The plugin's source of truth is the git repo. Brain's own engineering principles ("Make requirements less dumb first") apply to the plugin's own implementation.

---

## Build sequence (suggested)

Follow this order to derisk the dependency graph.

### Phase 0 — Hours 0–4 (scaffold + docs)
1. Plugin manifest + README.
2. `.engineering-os/` layout + `.gitattributes` + `.gitignore`.
3. Section 1 docs (folder-context, business-context, technical-context).
4. Section 2 docs (skill mapping, role empowerment).

### Phase 1 — Hours 4–8 (operating manual)
5. Operating manual (Section 3) + workflow + quality gates + escalation rules.
6. Plugin architecture + technical implementation + memory & git sync (Section 4).

### Phase 2 — Hours 8–16 (templates + schemas + prompts)
7. 11 JSON schemas + 9 Markdown templates (Section 5).
8. Shared prompts (system-prompt, anti-blind-agreement, challenge-framework).
9. 11 agent files (Section 6).

### Phase 3 — Hours 16–24 (plugin scaffold)
10. Author the curated skill library (domain skills + command-skills).
11. 3 hooks (`hooks.json` + 3 scripts).
12. 3 workflow YAMLs.
13. Seed `.engineering-os/` starter content.

### Phase 4 — Hours 24+ (operate)
15. **Run a test requirement end-to-end** (see walkthrough below).
16. Iterate based on what hurt.

### Phase 5 — V2 work (later)
17. Hook hardening.
18. Skill-library ↔ matrix CI check.
19. External integrations.

---

## Risks & mitigations

| Risk | Likelihood | Severity | Mitigation |
|------|:----------:|:--------:|------------|
| Two teammates collide on same requirement | Medium | Low | Per-run folders never collide; `state/active.json` last-write-wins with surfaced conflict; agents re-read state before acting |
| `state/active.json` corruption | Low | High | `.bak.<ts>` written on every save; plugin refuses to start if corrupt and surfaces recovery |
| A gate failure slips through a handoff | Medium | Medium | Enforcement lives in the agents (each stage self-reviews, Tanvi re-runs skipped gates, Rohan spot-re-runs Tanvi's gates at Stage 6); the pre-handoff hook logs the event for the audit trail; a downstream gate catches what an upstream one missed |
| Founder forgets to `/approve` or `/reject`, work stalls | Medium | Low | `/status` surfaces stuck items; V2 sends Slack reminder after 24h |
| Memory file balloons over years | Low | Low | Plain markdown + JSONL is cheap; V2 archive at 365 days |
| Secrets accidentally committed in journals | Medium | High | `on-post-tool-use.sh` redacts known patterns; V2 pre-commit hook scans |
| Agent misreads canon and ships wrong assumption | Medium | High | CTOA Stage 6 review catches drift; Decision Log surfaces past similar decisions; canon primer is concise and read on every task |
| Founder over-approves to "be helpful" | Medium | Medium | Anti-blind-agreement embedded in system prompt; CTOA still gets Stage 6 VETO even if Founder says yes; logged waivers for overrides |
| Auto-rollback fires on benign noise | Low | Low | Thresholds tuned (5-min sustained, not transient); rollback always re-enters Stage 4 triage rather than silent revert |

---

## Rollout plan (for the plugin itself)

1. **Day 0:** Build the MVP (this checkout).
2. **Day 1:** Rishabh runs ONE end-to-end requirement himself ("the walkthrough") to validate the loop.
3. **Day 2:** Open the repo to ONE teammate. They `git pull` and run `/status` + `/recall` to confirm continuity works.
4. **Week 1:** Run 3–5 real Brain features through the pipeline. Iterate hooks + templates based on friction.
5. **Week 2:** Open to the rest of the team. Daily standups review `/status` output.
6. **Week 4:** First V2 hardening (pre-commit secret-scanning hook; session-start stuck-item surfacing).
7. **Month 2+:** Recommended additional skills + external integrations as needed.

---

## End-to-end feature walkthrough

> One concrete feature through all 8 stages, at a glance. For the per-stage execution detail see [docs/workflow.md](docs/workflow.md); for the machine-readable definition see [workflows/requirement-to-release.yaml](workflows/requirement-to-release.yaml). This is the summary, not the source of truth — don't re-narrate the pipeline here.

**Feature:** *"Add abandoned cart recovery for COD orders in GCC. Reuse the existing RFM segment. Don't break the India path."* Founder runs `/brain-engineering-os:requirement <text>`.

| Stage | Owner | What happens | Key artifact(s) | Outcome |
|---|---|---|---|---|
| 0 intake | `/requirement` | Dedup check; mint `req_id=feat-abandoned-cart-recovery-gcc`; create run folder; write `01-requirement.md`; invoke Rohan | `01-requirement.md` | → Stage 1 |
| 1 intake | **Rohan** | "Make it less dumb first" (UAE-first, defer KSA); persona count = **2** (compliance + regional-expansion); recommend SQL paradigm | `02-cto-advisor-review.md`, `03/04-persona-*.md` | ADVANCE |
| 2 plan | **Aryan** | Extend lifecycle-service `region=ae` (reuse Audience Builder — Single-Primitive); new `gcc.recovery_windows` table w/ RLS; SQL paradigm; observability + tests | `06-architecture-plan.md`, `07-handoff-to-developer.md` | → Stage 3 |
| 3 build | **Vikram** ∥ **Maya** | BE route + calling-window assertion (Vikram challenges a missing agency-JWT guard, Aryan agrees); Python RFM lookup w/ short-history fallback. Both capture real-network smoke | `08-developer-report-vikram.md`, `08-developer-report-maya.md` | READY-FOR-SECURITY |
| 4 security | **Shreya** | Finds HIGH: UAE DLT registration not wired → **BOUNCE** to Vikram; he fixes (UAE TRA vs India TRAI); re-review PASS | `09-security-review.md` | BOUNCE → PASS |
| 5 QA | **Tanvi** | Unit + integration + Cypress E2E + real-network smoke + metric-registry parity + ops-readiness, all green | `10-qa-review.md` | PASS |
| 6 final | **Rohan** | Paradigm audit (no Sonnet snuck in); over-engineering audit; spot-re-run 3 of Tanvi's gates; write retro | `11-final-review.md`, `14-retro.md` | APPROVE |
| 7 gate | **Founder** | Reads `/status` + final review; `/approve` | `12-founder-decision.json` | APPROVED |
| 8 ship | **Jatin** | Stage product code for Founder; commit `.engineering-os/` (chore-eos); CI → ArgoCD staging → canary → prod; 48h monitor + auto-rollback armed | `13-deployment-report.md` | shipped (after push verified) |

**Economics:** ~40h of agent work over ~3 working days; ~10 minutes of real Founder time (one `/requirement`, one `/approve`). ~15–18 decision-log lines — every step searchable and git-blameable. The security bounce at Stage 4 (not in production) is the system working as designed.

---

## Open questions for V2

1. **Auto-merge after Founder approval?** Currently Jatin opens the PR; humans merge. Should Stage 7 also gate the merge?
2. **How rich should `/digest` be?** Weekly stage-time, bounce-causes, decision-log search — but also probably a "what shipped, in plain English" section.
3. **External persona inputs?** Should the dynamic-persona-generator be able to call out to a customer-success Slack channel for the `customer-success` persona's actual voice?
4. **Per-brand context vector?** Should the plugin maintain a Brain-specific brand fingerprint that the AICMO/AICOO/AICFO agents reference at design time (e.g., "Sugandh Lok would be affected by this — how?")?
5. **Pause/resume mid-pipeline?** Should `/pause <req-id>` exist for "we're not going to do this for 2 weeks"?

Defer answers until V2 build kicks off.

---

## Where to start

- New teammate: read [README.md](README.md), then [docs/operating-system.md](docs/operating-system.md), then run `/status`.
- New agent owner: read [agents/](agents/) for your role.
- New skill author: copy a similar skill folder under `skills/`, then update [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md) and the owning agent's owned-skill list. See [docs/skill-authoring-guide.md](docs/skill-authoring-guide.md).
- Plugin developer (you): read [docs/plugin-architecture.md](docs/plugin-architecture.md), then this roadmap.

Build. Operate. Iterate. Brain.
