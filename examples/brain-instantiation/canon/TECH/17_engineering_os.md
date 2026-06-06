# TECH/17 — Engineering Operating Model (the AI team that builds Brain)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. This deep-dive documents the **engineering operating model** (how Brain is built), not the product architecture.
> **Source:** the founder's *Engineering OS — Rebuild Prompt v0.8.0* (pasted into this project; authored into Brain-docs as the single source — not the external `Brain/.engineering-os/` folder).
> **Provenance note:** the founder's paste was truncated at "§3 Phase 0 flow"; **§3 flow detail, §4 the 8-stage pipeline, and §5 PLAN-phase research below are reconstructed from the spec's own cues** (the touchpoints table, the agent roster, the plan-binding model, the VETO authorities). They are marked *(reconstructed)*. Treat them as a faithful draft to confirm/amend, not verbatim founder text.
> **Claude Code mechanics** were verified against current (2026) official docs; corrections to the spec's assumptions are flagged in §12.

---

## 0. What this is — and what it is NOT

The **Engineering OS** is a Claude Code **plugin** that delivers an *AI engineering team* which builds Brain. It takes a founder requirement from intake to release through a **two-phase operating model**:

1. **Phase 0 — Foundation (one-time):** the founder hands over the BRD + TRD; the team synthesizes the `knowledge-base/`; the founder approves; the recurring pipeline unlocks.
2. **Recurring pipeline (per requirement):** an **8-stage** requirement-to-release flow (§4), mostly autonomous, touching the founder at exactly **four** points (§6).

> **Critical distinction (no discrepancy):** the **11 agents here build Brain**. They are NOT the **15 product agents** (AICMO / AICOO / AICFO) that run *inside* Brain for customers — those are `../technical-requirements.md` §16.4 and `TECH/14`. "Rohan/Aryan/security-reviewer/…" assemble the product; "AICMO-Meta/AICOO-Logistics/…" are features of the product. Both use Claude models; they are different rosters with different jobs.

The plugin is **product-agnostic**. Stack, architecture, baselines, compliance specifics, and the moat are NOT hard-coded in the OS — they are derived in Phase 0 from Brain's BRD + TRD and live in the `knowledge-base/`. For Brain, **Phase 0's outputs are these very Brain-docs** (§9 mapping). Build the minimum that fulfils the spec — do not over-engineer.

---

## 1. Distribution & Memory Model

- **Ships as a Claude Code plugin.** Manifest at `.claude-plugin/plugin.json` (required field `name`; optional `version`, `description`, component paths). The plugin is **installed** to `~/.claude/plugins/cache/{plugin-id}/`, never cloned into the product repo.
- **Marketplace registration** is separate from the plugin: a marketplace repo carries `.claude-plugin/marketplace.json` listing the plugin's `source` (git/sha-pinned for reproducible installs). *(Correction to the spec, which implied marketplace.json ships in the plugin — see §12.)*
- **Path resolution:**
  - Plugin-shipped files → `${CLAUDE_PLUGIN_ROOT}`
  - Product repo's shared memory → `${CLAUDE_PROJECT_DIR}/.engineering-os/` — **committed to git** so it survives `git pull` for every teammate. **Memory is the moat.**
  - Optional persistent plugin data → `${CLAUDE_PLUGIN_DATA}`.
- **Slash commands are implemented as SKILLS** (`skills/<name>/SKILL.md`) with `disable-model-invocation: true` so they run only when explicitly invoked, never auto-triggered. No `commands/` folder. *(Caveat for plugin skills — §12.)*
- **Domain skills:** `skills/<name>/SKILL.md` with `name` + `description` frontmatter.
- **Namespacing:** plugin skills/agents are invoked as `/engineering-os:<name>`.
- **Phase-0 gating:** a `PreToolUse`/`UserPromptSubmit` hook (and a self-check inside the intake skill) refuses any Stage-1 intake until the sentinel `${CLAUDE_PROJECT_DIR}/.engineering-os/foundation-approved.json` exists; without it, intake directs the founder to `/foundation-kickoff`. (Hooks can block by exiting code 2 — §12.)

---

## 2. The Team (11 agents)

Each agent: `agents/<name>.md` with frontmatter `name`, `description`, `tools`, `model`. **Every agent additionally gets `WebSearch` + `WebFetch`** — used strictly during PLAN-phase research (§5). Agents that need to spawn others keep `Agent`.

| # | Agent (file) | Person | Model | Role & authority |
|---|---|---|---|---|
| 1 | `cto-advisor` | **Rohan** | opus | Phase 0 foundation co-lead · Stage 1 intake + brainstorm co-lead · Stage 6 final review. **VETO at Stage 6.** **Sole authority to `/escalate`** to the founder mid-pipeline against `knowledge-base/DECISIONS-escalation-rubric.md`. Picks persona count 0/1/2 (cap 2). Has `Agent`. |
| 2 | `dynamic-persona-generator` | — | sonnet | Spawned by Rohan to inhabit ONE stress-test persona (e.g. compliance-officer, ai-cost-realist, regional-expansion-officer — personas derived in Phase 0). Must surface ≥1 concern. |
| 3 | `architect` | **Aryan** | opus | Phase 0 foundation co-lead · Stage 1 brainstorm co-lead · **Stage 2 binding plan** (`06-architecture-plan.md`). Owns the plan-amendment loop for Stage 3+. Raises concerns to Rohan (who decides whether to `/escalate`). Has `Agent`. |
| 4 | `backend-developer` | *(Phase 0 `team-roster.md`)* | sonnet | Backend services in the Phase-0 stack. Executes the plan; deviations route through Aryan. Trace-instruments every endpoint + message consumer. |
| 5 | `frontend-web-developer` | *(Phase 0)* | sonnet | Web frontend. Executes the plan; propagates trace context; surfaces request IDs on error UI. |
| 6 | `mobile-developer` | *(Phase 0)* | sonnet | Mobile app. Executes the plan; trace-context propagation. |
| 7 | `intelligence-engineer` | *(Phase 0)* | sonnet | AI/ML services. Executes the plan; agent invocations trace-instrumented end-to-end incl. LLM calls. |
| 8 | `security-reviewer` | *(Phase 0)* | opus | **Stage 4. VETO on CRITICAL/HIGH** + compliance gaps (regime set by Phase 0) + **missing traceability.** Surfaces rubric-matching findings to Rohan. |
| 9 | `qa-agent` | *(Phase 0)* | sonnet | **Stage 5. VETO on missing real-network verification.** Verifies trace IDs appear end-to-end in test runs. |
| 10 | `platform-devops` | *(Phase 0)* | sonnet | **Stage 8** deploy + monitor + rollback. Reads `knowledge-base/PLAYBOOK-*`. Verifies trace pipeline healthy post-deploy. |
| 11 | `product-manager` | *(Phase 0)* | sonnet | Cross-cuts (not a stage): release notes, tracker sync, surfaces escalations in `pending-founder-attention.md`. |

**Model pins (2026):** `opus` → `claude-opus-4-7`; `sonnet` → `claude-sonnet-4-6`; `haiku` → `claude-haiku-4-5-20251001` (aliases acceptable in frontmatter). (Mirrors `TECH/00`.)

**Naming convention.** Rohan (CTO Advisor) and Aryan (Architect) are pre-named (universally understood role names; they co-lead Phase 0 and so cannot be derived from Phase-0 outputs). Roles 4–11 are scaffolded with **role-based filenames** (`backend-developer.md`, …); their **human names** (brand/team-voice aligned) are assigned by Phase 0's `team-roster.md` and live in the agent frontmatter `description` + system prompt.

**Escalation authority (not democratic).** Any agent hitting a rubric-matching condition raises it to **Rohan**. Rohan alone decides whether to `/escalate`. If he can answer in good conscience from `knowledge-base/` + `lessons-learned.md`, he answers — escalation is a last resort.

---

## 3. Phase 0 — Foundation (one-time; gates the pipeline)

Produces the `knowledge-base/` from the founder's BRD + TRD. Runs once per product, and again only on an explicit foundation amendment. The recurring pipeline is gated until Phase 0 passes.

### 3.1 Trigger
Founder runs `/foundation-kickoff` and attaches:
- `inputs/founder-BRD.md` — end-to-end Business Requirements (for Brain: `business-requirements.md`).
- `inputs/founder-TRD.md` — end-to-end Technical Requirements (for Brain: `technical-requirements.md` + `TECH/`).

These are *raw* — possibly rough, incomplete, contradictory. Aryan + Rohan interrogate them, fill gaps, surface contradictions back to the founder, and produce a coherent, internally consistent foundation.

### 3.2 Flow *(reconstructed)*
1. **Ingest & interrogate** — Aryan + Rohan read BRD + TRD; build a gap/contradiction list. (PLAN-phase research allowed: WebSearch/WebFetch to validate market/stack/compliance facts — §5.)
2. **Founder reconciliation** — open contradictions/gaps are surfaced to the founder (batched, decision-shaped); answers fold back in.
3. **Persona stress-test** — Rohan optionally spawns 0–2 `dynamic-persona-generator`s (count by complexity, cap 2) to pressure-test from derived angles (e.g. compliance-officer, ai-cost-realist); each surfaces ≥1 concern; concerns resolve into the foundation.
4. **Synthesis** — Aryan + Rohan author the `knowledge-base/` (§3.3) — stack, HLD, LLD, playbooks, escalation rubric, non-negotiables, the moat, team roster.
5. **Draft review & gate** — the foundation draft is presented; the founder runs **`/approve-foundation`**, which writes `.engineering-os/foundation-approved.json` (the sentinel). The pipeline unlocks.

### 3.3 Outputs — the `knowledge-base/`
At minimum (contents are product-set, not OS-fixed):
- `knowledge-base/STACK.md` — chosen stack + justification → for Brain = `TECH/00`.
- `knowledge-base/HLD.md`, `knowledge-base/LLD-*.md` — high/low-level design → for Brain = `technical-requirements.md` + `TECH/01–16`.
- `knowledge-base/PLAYBOOK-*.md` — deploy/rollback/incident playbooks → for Brain = `TECH/09` + `TECH/08`.
- `knowledge-base/DECISIONS-escalation-rubric.md` — when an agent must escalate to the founder (§7).
- `knowledge-base/NON-NEGOTIABLES.md` — the invariants → for Brain = `technical-requirements.md` §2 + §26.
- `knowledge-base/THE-MOAT.md` — what compounds → for Brain = the Decision Log + Memory Layer (`TECH/05`).
- `team-roster.md` — names roles 4–11.

---

## 4. The 8-Stage Recurring Pipeline *(reconstructed)*

Per requirement, after foundation is approved. Pattern (from the subagent-orchestration discipline): **each stage plans → executes → self-reviews → verifies → hands off to the next stage via an `Agent()` invocation.** Deviations from the binding plan trigger the plan-amendment loop (§5), never freelancing.

| Stage | Owner | Input → Output | Gate / VETO | Founder? |
|---|---|---|---|---|
| **1 — Intake & Brainstorm** | Rohan (+ Aryan, 0–2 personas) | Founder requirement → joint brainstorm (`01-brainstorm.md`); Rohan sets persona count; personas each surface ≥1 concern | Phase-0 sentinel must exist (hook-gated) | **Files the requirement** |
| **2 — Binding Implementation Plan** | Aryan | Brainstorm → `06-architecture-plan.md` (binding for stages 3–8); 2–5-min tasks, concrete file paths, verification steps; auto-loads on schema/proto/MCP/event-topic changes | Plan is the contract | — |
| **3 — Build** | backend / frontend-web / mobile / intelligence devs | Plan → code (vertical slices) + per-feature journal; trace-instrumented per §8; deviations → Aryan amendment loop | Self-review + verification-before-completion | — |
| **4 — Security Review** | security-reviewer | Code → findings | **VETO on CRITICAL/HIGH, compliance gaps (DPDP/PDPL/DLT — `TECH/16`), missing traceability**; rubric matches → Rohan | — |
| **5 — QA** | qa-agent | Code → test results | **VETO on missing real-network verification**, contract tests, metric-registry parity (TS↔Python), mutation gaps on high-stakes paths; **verifies trace IDs end-to-end** | — |
| **6 — Final Review** | Rohan | Reconciles cross-team; confirms plan adherence → mechanical commit command | **VETO**; commit-boundary discipline (product code vs `.engineering-os/` audit trail; explicit-path staging; no history rewrite; push-success gate) | **Runs the commit command** |
| **7 — Deploy Gate** | Founder | Reviewed change → decision | `/approve` or `/reject` | **`/approve` or `/reject`** |
| **8 — Deploy + Monitor + Rollback** | platform-devops | Approved change → release | Reads `PLAYBOOK-*`; CI/CD → ArgoCD (services) + EAS (mobile); **48h monitor + auto-rollback**; verifies trace pipeline healthy; PM emits release notes + tracker sync | — |

On any VETO (Stage 4/5/6), the work routes back to Stage 3 (or Stage 2 if the plan itself is wrong) — never overridden silently.

---

## 5. Plan-Binding & PLAN-Phase Research *(reconstructed)*

- **Plan-binding model.** Stage 1 = joint brainstorm; Stage 2 = binding `06-architecture-plan.md`. Stages 3–8 **execute against that plan**. Any required deviation triggers a **plan-amendment loop**: the developer raises it to Aryan, Aryan revises `06-architecture-plan.md`, then build resumes. No freelancing.
- **PLAN-phase research discipline.** Every agent has `WebSearch` + `WebFetch`, used **only during PLAN phases** — Phase 0 synthesis, Stage 1 brainstorm, Stage 2 planning (and Aryan's amendment loop). During **BUILD (Stage 3+)**, agents implement the plan; a newly-discovered external fact that would change the design does **not** authorize ad-hoc deviation — it routes back through Aryan's amendment loop. This keeps research a planning input, never a build-time excuse to drift from the contract.

---

## 6. Founder Touchpoints — the entire surface area

| When | What | Frequency |
|---|---|---|
| Phase 0 kickoff | Files BRD + TRD | Once per product (or per foundation amendment) |
| Phase 0 gate | `/approve-foundation` | Once per product (or per amendment) |
| Stage 1 intake | Files a requirement | Per requirement |
| Mid-pipeline escalation | Responds to `/escalate` with `/decide` | Rare; rubric-gated |
| Post-Stage-6 commit | Runs the mechanical commit command Rohan provides | Per requirement |
| Stage 7 deploy gate | `/approve` or `/reject` | Per requirement |

**Nothing else.** No status pings, no mid-build check-ins, no per-PR review. The human founder is named in Phase 0.

---

## 7. Escalation Rubric (Rohan-gated)

`knowledge-base/DECISIONS-escalation-rubric.md` (produced in Phase 0) defines the conditions that *may* warrant founder escalation — e.g. irreversible/high-blast-radius decisions, compliance ambiguity (DPDP/PDPL/DLT — `TECH/16`), cost-model threats (cost-routing — `TECH/12`), cross-team paradigm conflicts, anything that would change the moat or a non-negotiable. Flow: any agent → Rohan → Rohan decides. Escalation is a last resort; Rohan answers from `knowledge-base/` + `lessons-learned.md` whenever he can in good conscience. `product-manager` mirrors any pending escalation into `pending-founder-attention.md`.

---

## 8. Traceability Contract (= Brain's observability spine)

The OS's "traceability" maps onto Brain's observability layer (`../technical-requirements.md` §22 + `TECH/09`). One correlation ID — `request_id` + `trace_id` + `workspace_id` + `user_id` — propagates **HTTP headers → gRPC metadata → Kafka envelope → LLM call**. Obligations enforced as VETO surfaces:
- **Developers (Stage 3):** every endpoint, message consumer, frontend request, mobile request, and agent/LLM invocation is trace-instrumented; request IDs surface on error UI.
- **security-reviewer (Stage 4):** VETO on **missing traceability**.
- **qa-agent (Stage 5):** verifies trace IDs appear **end-to-end** in real-network test runs.
- **platform-devops (Stage 8):** verifies the trace pipeline (OTel → CloudWatch/X-Ray, Sentry, OpenSearch) is healthy post-deploy.

---

## 9. Brain Instantiation (the mapping that removes ambiguity)

The product-agnostic OS, grounded in Brain:

| Engineering OS artifact | Brain-docs reality |
|---|---|
| `inputs/founder-BRD.md` | `business-requirements.md` (v1.1) |
| `inputs/founder-TRD.md` | `technical-requirements.md` (v2.0) + `TECH/00–16` |
| `knowledge-base/STACK.md` | `TECH/00` (stack decision + phasing) |
| `knowledge-base/HLD + LLD` | `technical-requirements.md` + `TECH/01–16` |
| `knowledge-base/PLAYBOOK-*` | `TECH/09` (security/observability/incident) + `TECH/08` (alerts) + `TECH/15` (billing ops) |
| `knowledge-base/NON-NEGOTIABLES.md` | `technical-requirements.md` §2 (principles) + §26 (anti-patterns) |
| `knowledge-base/DECISIONS-escalation-rubric.md` | derived in Phase 0; compliance references → `TECH/16`; cost references → `TECH/12` |
| `knowledge-base/THE-MOAT.md` | Decision Log + Memory Layer (`TECH/05`; business §5.3/§7) |
| compliance regime | DPDP / PDPL / TCCCPR-DLT / NCPR — `TECH/16` |
| traceability contract | observability spine — §22 + `TECH/09` |
| chosen stack the devs build in | `TECH/00` (TS/Python, Next.js/Expo, Fastify/tRPC/gRPC, Postgres/ClickHouse, MSK, Claude) |
| `06-architecture-plan.md` (per requirement) | a per-requirement plan that extends the above; lives in `.engineering-os/` |

> **Brain's Phase 0 is effectively already done:** these Brain-docs *are* the approved foundation. The OS, when installed on the Brain repo, treats them as the `knowledge-base/` and runs the recurring pipeline against them.

---

## 10. `.engineering-os/` File & State Layout (committed to the product repo)

```text
${CLAUDE_PROJECT_DIR}/.engineering-os/
├── foundation-approved.json        # Phase-0 gate sentinel (created by /approve-foundation)
├── knowledge-base/                 # the approved foundation (see §3.3 / §9)
│   ├── STACK.md  HLD.md  LLD-*.md
│   ├── PLAYBOOK-*.md
│   ├── DECISIONS-escalation-rubric.md
│   ├── NON-NEGOTIABLES.md  THE-MOAT.md
├── team-roster.md                  # names roles 4–11
├── lessons-learned.md              # compounding learnings (feeds escalation judgment)
├── pending-founder-attention.md    # PM-surfaced escalations awaiting /decide
├── requirements/<id>/              # per-requirement working set
│   ├── 01-brainstorm.md            # Stage 1 output
│   ├── 06-architecture-plan.md     # Stage 2 binding plan
│   ├── journal.md                  # per-feature build journal (Stage 3+)
│   └── decision-log.md             # stage decisions, VETOs, amendments, outcomes
└── state/                          # active.json / registry.json (pipeline state)
```

**Commit-boundary discipline (Stage 6 / `finishing-a-development-branch`):** product code and the `.engineering-os/` audit trail are committed as **separate, explicit-path** stages (never `git add -A`); no history rewrite; push must succeed (push-success gate) before a stage is "done".

---

## 11. Non-Negotiables / Anti-Patterns (OS-level)

- No Stage-1 intake before `foundation-approved.json` exists.
- No build-stage freelancing — deviations go through Aryan's plan-amendment loop.
- No stage advances past a VETO (Stage 4 security, Stage 5 QA, Stage 6 Rohan).
- Escalation is Rohan-gated and last-resort — not democratic, not a status ping.
- Memory (`.engineering-os/`) is committed to git — it is the moat; never gitignored.
- Founder is touched at the four+two points in §6 and nowhere else.
- The OS's agents (build team) are never conflated with Brain's product agents (`TECH/14`).
- Traceability is mandatory and VETO-enforced (§8).

---

## 12. Claude Code Implementation Notes (verified 2026)

| Spec assumption | Verified reality / correction |
|---|---|
| "`plugin.json` + `marketplace.json`" ship together | `plugin.json` lives in the plugin at `.claude-plugin/plugin.json`. **`marketplace.json` lives in the *marketplace repo*** at `.claude-plugin/marketplace.json` and lists the plugin via a (sha-pinned) `source`. They are separate concerns. |
| Installed to `~/.claude/plugins/` | More precisely `~/.claude/plugins/cache/{plugin-id}/`. |
| `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}` | ✅ correct. Bonus: `${CLAUDE_PLUGIN_DATA}` for persistent plugin data across updates. |
| Skills with `disable-model-invocation: true` as slash-commands; no `commands/` | ✅ valid pattern; `commands/` is legacy. **Caveat:** there are open issues (anthropics/claude-code #22345, #26251) about **plugin** skills not honoring `disable-model-invocation` exactly like user skills (a typed slash invocation can be refused). Mitigation: keep the gate logic inside the skill body + the hook, and track the upstream fix. |
| `agents/<name>.md` frontmatter `name/description/tools/model` | ✅ correct. `model` accepts aliases (`opus/sonnet/haiku`) or full IDs. **Plugin agents cannot set `hooks`, `mcpServers`, or `permissionMode`** (security restriction); `isolation: "worktree"` is allowed. |
| `/engineering-os:<name>` namespacing | ✅ correct. |
| Hooks gate Stage-1 intake on a sentinel | ✅ a `PreToolUse` (or `UserPromptSubmit`) hook can **block by exiting code 2** (stderr returned to Claude). Configure in `hooks/hooks.json` or inline in `plugin.json`. Use `${CLAUDE_PROJECT_DIR}/.engineering-os/foundation-approved.json` as the sentinel check. |
| Model IDs | `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` (pinned snapshots). |

Sources: Claude Code docs — [Plugins](https://code.claude.com/docs/en/plugins), [Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces), [Skills](https://code.claude.com/docs/en/skills), [Subagents](https://code.claude.com/docs/en/sub-agents), [Hooks](https://code.claude.com/docs/en/hooks); issues [#22345](https://github.com/anthropics/claude-code/issues/22345), [#26251](https://github.com/anthropics/claude-code/issues/26251).

---

## 13. Open Items (confirm against the full spec when available)

| # | Item | Note |
|---|---|---|
| 1 | §3 flow detail, §4 stage contracts, §5 research discipline | **Reconstructed** from cues — confirm/amend against the founder's full prompt. |
| 2 | Exact persona catalog | Derived in Phase 0; examples only above. |
| 3 | Escalation rubric specifics | Produced in Phase 0; `TECH/16`/`TECH/12` referenced for compliance/cost triggers. |
| 4 | Plugin-skill `disable-model-invocation` gap | Track upstream fix (#22345/#26251); gate also enforced in skill body + hook. |
| 5 | 48h monitor + auto-rollback thresholds | Set in `PLAYBOOK-deploy.md` (Phase 0); align with SLOs in §22. |
