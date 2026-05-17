# Brain Engineering OS — Implementation Roadmap

> Section 8 of the build prompt. Scope by version + developer task breakdown + suggested tech stack + build sequence + risks/mitigations + rollout plan + one full end-to-end feature walkthrough.

---

## Versions

### V1 — MVP (this checkout)

**Goal:** the team works. A teammate can clone, open Claude Code, run `/requirement`, and get a feature through to Founder approval with full audit trail.

**In scope:**
- 10 agents (CTO Advisor, Architect, Backend, Web, Mobile, Intelligence, Security, QA, DevOps, PM) + Dynamic Persona Generator (runtime).
- 10 slash commands (`/requirement`, `/status`, `/recall`, `/handoff`, `/approve`, `/reject`, `/deploy`, `/rollback`, `/skill`, `/persona`).
- 54 mirrored skills auto-loaded per agent's owned-skill list.
- 8-stage pipeline (Stage 1 intake → Stage 8 deploy + 48h monitor).
- Shared, git-committed memory in `.engineering-os/` with append-only journals + decision log.
- 3 hooks (session-start, post-tool-use, pre-handoff) — pre-handoff is best-effort logging in MVP.
- 11 JSON schemas + 9 markdown templates.
- All 12 docs (operating manual, workflow, gates, escalation, plugin architecture, etc.).
- Conflict-resistant multi-operator sync via git + `merge=union`.

**Explicitly out of MVP** (deferred to V2):
- Auto-merge PRs after Founder approval.
- Active gate enforcement in pre-handoff hook (V2 makes it actually block).
- Automated mirror script for `Requirements/skills/` → `skills/` (MVP refreshes manually).
- `/digest` weekly summary slash command.
- Per-feature graphs of stage-time and bounce-count.
- Slack/Discord/email notifications at gate transitions.
- Auto-archive of run folders older than 365 days.
- Pre-commit secret-scanning hook.

### V2 — Production-ready (4–8 weeks after MVP)

**Goal:** the plugin operates safely at multi-operator scale without manual reconciliation.

- **Hook hardening:**
  - `pre-handoff` actually blocks on gate failures (reads `quality-gates.md` and verifies evidence).
  - `pre-commit` secret-scanning hook.
  - `on-session-start` surfaces stuck items (>2 days in same stage) with recommended action.
- **Mirror automation:**
  - Hook runs `rsync --delete Requirements/skills/ skills/` on session start.
  - CI fails if any skill is in one place but not the other.
- **`/digest` slash command:** weekly Friday summary aggregating decision log: features shipped, gates fired (PASS/FAIL), average time-in-stage, top bounce causes.
- **External integrations** (opt-in via env vars):
  - GitHub: Jatin opens PRs; Tanvi attaches test output as PR comments.
  - Slack: notification on Stage 7 awaiting-founder, rollback, daily digest.
  - ClickUp / Linear / Jira: Priya syncs req-ids to tracker.
- **Recommended additional skills** (4 new — see [folder-context-summary.md §6](docs/folder-context-summary.md#6-recommended-additional-skills-not-sourced-from-requirementsskills--clearly-labeled)):
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
| Mirror sync (V2+) | `rsync` |
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
10. Mirror 54 skills.
11. 10 slash commands.
12. 3 hooks (`hooks.json` + 3 scripts).
13. 3 workflow YAMLs.
14. Seed `.engineering-os/` starter content.

### Phase 4 — Hours 24+ (operate)
15. **Run a test requirement end-to-end** (see walkthrough below).
16. Iterate based on what hurt.

### Phase 5 — V2 work (later)
17. Hook hardening.
18. Automated mirror + CI check.
19. External integrations.

---

## Risks & mitigations

| Risk | Likelihood | Severity | Mitigation |
|------|:----------:|:--------:|------------|
| Two teammates collide on same requirement | Medium | Low | Per-run folders never collide; `state/active.json` last-write-wins with surfaced conflict; agents re-read state before acting |
| `state/active.json` corruption | Low | High | `.bak.<ts>` written on every save; plugin refuses to start if corrupt and surfaces recovery |
| Pre-handoff hook lets through a gate failure | Medium (MVP) | Medium | MVP best-effort; V2 makes it actually block; reviewers catch it at next gate anyway |
| Skill drift between `Requirements/skills/` and `skills/` | Medium | Low | V2 automated mirror + CI check; MVP manual refresh + matrix doc |
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
6. **Week 4:** First V2 hardening (pre-handoff gate enforcement; mirror automation).
7. **Month 2+:** Recommended additional skills + external integrations as needed.

---

## End-to-end feature walkthrough

> Concrete: a real Brain feature flowing through every stage. Tracks back to artifacts that would actually exist on disk after a successful run.

**Feature:** *"Add abandoned cart recovery for COD orders in GCC."*

### Hour 0 — Founder submits

Rishabh runs in Claude Code:
```
/requirement Add abandoned-cart recovery for COD orders in GCC. Use the existing RFM segment. Don't break the India path.
```

The `requirement.md` command:
- Reads `.engineering-os/state/active.json` and `registry.json` — no duplicate.
- Generates `req_id = feat-abandoned-cart-recovery-gcc`.
- Creates `.engineering-os/runs/2026-05-15T09-14-00Z__feat-abandoned-cart-recovery-gcc__rishabh/`.
- Writes `01-requirement.md` from `templates/requirement-template.md`.
- Updates state + registry.
- Appends decision log: `{"ts":"...","actor":"system","type":"intake","req_id":"...","title":"...","submitted_by":"rishabh"}`.
- **Invokes `cto-advisor` subagent.**

### Hours 0:04–0:18 — CTO Advisor (Stage 1)

The CTOA subagent (its system prompt = `agents/cto-advisor.md` body):
- Reads canon primers + own journal + run folder.
- Runs "Make requirements less dumb first":
  - Could delete: nothing.
  - Could simplify: yes — first cut may target UAE only (smaller market, sharper compliance), defer KSA-specific work.
  - Could defer: KSA can be a follow-up.
- Runs India context check — passes (existing India-specific work).
- Picks 3 dynamic personas based on the requirement:
  - `compliance-officer` (because outbound calling outside India).
  - `regional-expansion-officer` (because GCC RegionAdapter touched).
  - `data-quality-skeptic` (because reusing RFM segment — confirm parity).
- **Spawns the 3 personas in parallel via `Agent({subagent_type: "dynamic-persona-generator", ...})` × 3.**
- Each persona writes its review:
  - `03-persona-compliance-officer.md` — concern: UAE calling window is 09:00–22:00 GST, not India's 09:00–21:00 IST. Severity HIGH.
  - `04-persona-regional-expansion-officer.md` — concern: existing RegionAdapter has only `region=in`; need to add `region=ae` (and follow-up `region=sa`).
  - `05-persona-data-quality-skeptic.md` — concern: RFM thresholds (P40/P80) are computed per workspace from trailing 12 months of orders; in GCC brand cohorts may not have 12 months yet — flag fallback path.
- Synthesizes into `02-cto-advisor-review.md`:
  - Decision: **ADVANCE** (with caveats forwarded to Aryan).
  - Paradigm recommendation: SQL (RFM lookup + rule-based recovery).
  - India context check passed; UAE/GCC context flagged for Aryan.
- Appends own journal + decision log line `{type: "stage-advance", from: 1, to: 2}`.
- Updates state: status → `architect`.
- **Invokes `architect` subagent.**

### Hours 0:18–2:00 — Architect (Stage 2)

Aryan reads everything, then produces `06-architecture-plan.md` covering:
- Solution: extend `lifecycle-service` recover flow with `region=ae`. New small Postgres table `gcc.recovery_windows` (with RLS). New event `intelligence.recovery.recommended.v1` (partitioned by `workspace_id`). Reuse existing Audience Builder (single primitive — no fork).
- Paradigm: **SQL** (justified — rule-based with RFM lookup; no LLM/ML needed).
- Single-Primitive sweep: Audience Builder reused; Consent extended (+`region` filter); Decision Log reused; Notifications reused; Attribution reused; Identity reused.
- 4-layer multi-tenancy: addressed.
- Observability plan: metrics for `recover_attempts_total`, `recover_successful_total`, `gcc_call_attempts_total`; dashboard panel; alarm on `recover_failed > 5%`.
- Test strategy: unit (RFM lookup), integration (lifecycle-service end-to-end), contract (no proto change), real-network smoke against staging.
- Cost estimate: SQL paradigm — no LLM cost added.
- Risks: 1 HIGH (calling-window per region), 1 MEDIUM (RFM threshold fallback for short-history brands).
- Alternatives considered: (a) build new GCC-specific recover service — rejected (Single-Primitive); (b) defer until KSA + UAE both supported — rejected (UAE-first is acceptable).
- Tracks emitted:
  - Track BE: `@vikram` — Fastify route `POST /v1/lifecycle/recover-cod-uae`, lifecycle-service handler, calling-window assertion.
  - Track AI: `@maya` — RFM segment lookup function in Python with fallback for <12-month brands.

Aryan updates his journal + decision log + state (status → `dev-parallel`).
**Invokes `backend-developer` and `intelligence-engineer` subagents in parallel.**

### Hours 2:00–32:00 — Parallel Development (Stage 3)

Vikram + Maya work independently:

**Vikram (BE):**
- Implements the Fastify route + lifecycle-service handler.
- Wires `requireRole(operator)`, Zod input, idempotency key `(workspace_id, cart_id, attempt_n)`, calling-window assertion.
- **Catches Aryan's plan missing** the UAE-specific override of `requireWorkspaceMember()` for a new `agency` use case — uses challenge framework to push back: *"Plan doesn't address agency cross-workspace context for GCC. Recommend: extend `requireWorkspaceMember` to honor agency JWT claim. 1-hour change."*
- Aryan agrees in the journal; Vikram implements.
- Runs `pnpm vitest`, `pnpm tsx scripts/smoke/recover-real-network.ts --region=ae`. Captures actual output.
- Writes `07-dev-report-vikram.md` with all DoD checks ✓.
- Posts `READY-FOR-SECURITY`.

**Maya (AI):**
- Implements the Python RFM lookup with fallback (returns `segment="unscored-new-brand"` when <60 days data, with metric emit).
- `@paradigm("sql")` decorator. No LLM. No ML.
- Writes pytest tests with mock data.
- Real-network smoke against staging ClickHouse.
- Writes `08-dev-report-maya.md`.
- Posts `READY-FOR-SECURITY`.

### Hours 32:00–34:00 — Security Review (Stage 4)

Shreya picks up. Reads everything. Runs scans.

- Checks every mutation endpoint guard — Vikram's `POST /v1/lifecycle/recover-cod-uae` has them.
- Checks calling-window assertion — present (Vikram already caught and fixed during Stage 3).
- Checks RegionAdapter extension — handled by the new `gcc.recovery_windows` table.
- Checks DLT registration — **finds GAP**: per-template DLT registration check is on the India calling path but not yet wired for UAE. Severity: HIGH. Bounce.

Shreya writes `09-security-review.md` with verdict BOUNCE + structured finding. Tags `@vikram` for the fix.
Updates state → `security-bounced` (back to `dev-parallel`).

### Hour 34:00–35:30 — Vikram re-fix

Vikram receives the bounce in his journal. Reads Shreya's finding. Implements the UAE DLT registration check (different DLT regulator structure — UAE TRA, not India's TRAI; but `lifecycle-service` already had the abstraction).
Re-runs smoke. Re-handoffs READY-FOR-SECURITY.

### Hour 35:30–36:00 — Shreya re-review

Shreya re-reviews the fix. PASS. Appends new section to `09-security-review.md` with the PASS verdict. Updates state → `qa-review`.

### Hours 36:00–37:30 — QA (Stage 5)

Tanvi runs:
- Unit + integration tests across both lanes.
- Contract tests (none broken — no proto change).
- E2E (web) — Cypress test exercising the dashboard's "GCC recovery" panel.
- Real-network smoke — exercises the actual flow on staging.
- Metric registry parity check — confirms `recover_attempts_total` is defined identically in TS + Python.
- Operational-readiness checklist — green.
- Mutation tests on Decision Log path.

All green. Writes `10-qa-review.md` with all gate checks ✓ and full command outputs. State → `final-review`.

### Hour 37:30–38:00 — CTO Advisor Final Review (Stage 6)

CTOA reads every artifact. Audits `@paradigm` decorators — all match the SQL declaration. No Sonnet snuck in. Spot-checks 3 files. Confirms observability complete + dashboard panel updated + alarm registered.

Writes `11-final-review.md` with recommendation **APPROVE**. State → `awaiting-founder`.

### Hour 38:00 — Founder Approval (Stage 7)

Rishabh sees the new requirement in `/status`. Reads the final review. Notes the bounced security finding (impressive — caught at Stage 4 not in production). Runs `/approve feat-abandoned-cart-recovery-gcc`.

`12-founder-decision.json` written. State → `approved`. Jatin starts.

### Hours 38:00–40:00 — Platform/DevOps (Stage 8)

Jatin runs:
- CI: lint → typecheck → test → build → push to ECR.
- ArgoCD syncs staging.
- Staging verification: real-network smoke, dashboard panels show data, alarm fires on synthetic test.
- Production deploy via ArgoCD (canary 10% → 100%).
- 48h monitor begins. Auto-rollback triggers active.

`13-deployment-report.md` written. State → `monitoring`.

### Hour +48 — Shipped

48h passes with no alarms. State → `shipped`. Priya appends release note to `13-deployment-report.md` §6. Decision log entry. Done.

### Total wall-clock

~40 hours of agent work spread over 3 working days. Real human time on Rishabh: ~10 minutes total (one `/requirement`, one `/approve`).

### Total decision-log entries

- 1 intake
- 1 persona-spawn (3 personas)
- 1 stage-advance Stage 1→2
- 1 stage-advance Stage 2→3
- 2 ready-signals (Stage 3 → 4)
- 1 security-bounce
- 1 stage-advance Stage 4→5
- 1 stage-advance Stage 5→6
- 1 stage-advance Stage 6→7
- 1 founder decision (approved)
- 5 deployment ticks (staging, prod, +24h, +48h, shipped)

~15–18 decision-log lines. Every step searchable. Every step git-blameable.

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
- New skill author: copy a similar skill folder under `Requirements/skills/`, then update [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md) and re-mirror.
- Plugin developer (you): read [docs/plugin-architecture.md](docs/plugin-architecture.md), then this roadmap.

Build. Operate. Iterate. Brain.
