# Section 3.2 — The 8-Stage Workflow (Stage-by-Stage)

Each stage below specifies: **owner**, **inputs**, **what happens**, **outputs**, **artifacts**, **expected duration**, **typical bounce triggers**, **exit gate**.

---

## Universal protocol (every stage, every agent)

Per the `Plan-first + Self-review discipline` durable rule (2026-05-19), every stage's owner observes the same three responsibilities:

### 1. Plan-first (at start of every stage)

The owning agent writes its plan-of-work within the first 2–5 minutes of invocation:
- TodoWrite list (preferred for in-flight tracking), or
- `<stage-N>-plan.md` file in the run folder (preferred when plan exceeds 10 tasks)

Each plan task has: **what** (1-line action) + **why** (which DoD item it satisfies) + **verification** (how the agent knows it's done).

### 2. Self-review (before handoff)

The owning agent re-reads its own output and walks the in-lane Definition of Done line-by-line before handing off. Captured under a "Self-review" section in the stage's primary artifact. Anything failing must be FIXED before handoff, not deferred to the next agent.

### 3. Hand off by RETURNING a structured HANDOFF block — NOT by spawning

**Platform reality:** every stage owner runs as a *spawned subagent* and does **NOT** have the `Agent` tool — on this platform a subagent cannot spawn another subagent. So an agent **cannot** invoke the next stage itself. The pipeline is driven by a **top-level orchestrator** (the `/requirement` flow, which does have the `Agent` tool). See [orchestration.md](orchestration.md) for the full model and [system-prompt.md §3](../prompts/system-prompt.md) for the canonical contract — that section SUPERSEDES any older "invoke the next agent via the Agent tool" wording.

When the stage is genuinely complete and self-reviewed, the agent:

- **Persists everything first:** writes its stage artifact(s); appends per-agent + per-feature journals + a decision-log line; and **updates `state/active.json`** (status / stage / owner → next, using the EXACT status values from [`state-machine.yaml`](../workflows/state-machine.yaml)).
- **Ends its response with a machine-readable HANDOFF block:**

```
HANDOFF:
  decision: ADVANCE | BOUNCE | CHALLENGE-BACK | KILL | PASS | FAIL
  next_stage: <stage number/name, or "founder">
  next_agent: <agent-id | founder | none>
  bounce_target: <agent-id | none>      # only when decision is BOUNCE/FAIL
  needs_personas: [<persona-type>, ...]  # Stage 1 only; else []
  reason: <one line>
```

Do **NOT** call the `Agent` tool (you don't have it). Do **NOT** write `HANDOFF-TO-*.md` files (that legacy fallback is retired — it required a human to run the next command, defeating autonomy). The top-level orchestrator reads the `state/active.json` update + the HANDOFF block and spawns the next stage; it also does the special spawns agents can't (personas in parallel at Stage 1, Security ∥ QA at Stage 4∥5, multiple builders in parallel at Stage 3).

These three responsibilities together = **smooth autonomous flow**. The orchestrator moves the pipeline stage-to-stage without Founder prompting between stages. Founder gates remain only at requirement submission and Stage 7 (approval, unless delegated).

---

## Stage 1 — CTO Advisor (intake & brainstorm)

**Owner:** Rohan (CTO Advisor).
**Dynamic personas spawned:** 0–2, by complexity (chosen from the catalog in [role-empowerment-model.md §Dynamic Persona Generator](role-empowerment-model.md#2-dynamic-persona-generator--dynamic-persona-generator)).

### Inputs
- Founder's `/requirement <text>` invocation.
- Optional Founder-attached context (links, prior artifacts, anything in [.engineering-os/](../.engineering-os/)).

### What happens
1. Generate `req-<slug>` ID — kebab-cased from a short summary of the requirement.
2. Create the run folder: `.engineering-os/runs/<ISO-timestamp>__req-<slug>__<operator>/`.
3. Load `docs/business-context.md` + `docs/technical-context.md` + the CTO Advisor's owned skills.
4. Read the raw requirement.
5. **Run "Make requirements less dumb first"** (from `engineering-discipline`): Can we delete? Simplify? Defer?
6. Decide the persona count (0/1/2 by complexity) — but do NOT spawn them (Rohan is a subagent with no `Agent` tool). Record the chosen persona type(s) and RETURN them in the HANDOFF `needs_personas` list; the **top-level orchestrator** spawns that many in parallel (each writing a [`templates/dynamic-persona-review.md`](../templates/dynamic-persona-review.md) artifact) and then re-invokes Rohan to synthesize. For count=0, skip the persona round-trip.
7. Synthesize persona inputs + own analysis into a [`templates/cto-advisor-review.md`](../templates/cto-advisor-review.md) artifact (on the synthesis pass, after the orchestrator has produced the persona artifacts).
8. Decide: **ADVANCE** (Stage 2), **CHALLENGE-BACK** (to Founder with structured challenge), or **KILL** (archive with reason).
9. Append entry to:
   - `.engineering-os/decision-log/<YYYY>/<MM>/<YYYY-MM-DD>.jsonl`
   - `.engineering-os/memory/agents/cto-advisor.journal.md`
   - `.engineering-os/memory/features/feat-<slug>.md`
10. Update `.engineering-os/state/active.json` with the new `req-<slug>` and its current status.

### Outputs
- `cto-advisor-review.md` artifact in the run folder.
- 0-2 `dynamic-persona-review.md` artifacts.
- Status: `cto-review` → `architect` (ADVANCE) | `challenged-back` (CHALLENGE) | terminal `killed`.

### Expected duration
- 5–15 minutes of agent work for typical requirements.

### Typical bounce triggers (challenge-back)
- Requirement lacks a problem statement, target user, success metric, or constraint.
- Requirement violates the Single-Primitive Rule.
- Requirement assumes Sonnet when SQL/ML/Haiku would do.
- Requirement skips a region adapter step for non-India work.

### Exit gate (G1)
- All 5 sections of `cto-advisor-review.md` are filled.
- The persona-count decision (0/1/2) is recorded, and every spawned persona review includes at least one concern (a "looks good, no concerns" persona is rejected).
- Decision is recorded in the decision log.

---

## Stage 2 — Architect (Aryan)

**Owner:** Aryan.

### Inputs
- `cto-advisor-review.md` + 0-2 `dynamic-persona-review.md` (one per spawned persona).
- The raw requirement (for original-context reference).
- Relevant skill files (auto-loaded from his owned-skill list).
- Prior architecture decisions in `.engineering-os/memory/agents/architect.journal.md` (Aryan reads his own prior journal for continuity).

### What happens
1. Re-read the canon primers + `architecture-patterns` + `database-design` + `api-versioning-strategy` + domain-relevant skills.
2. Identify all *affected* services, schemas, topics, and primitives.
3. Run a Single-Primitive sweep: *does this duplicate anything?*
4. Declare the **paradigm** (SQL / ML / Haiku / Sonnet) and **justify** it.
5. Produce [`templates/architecture-plan.md`](../templates/architecture-plan.md), covering:
   - Context, problem, proposed solution
   - Architecture diagram (mermaid)
   - API design — gRPC proto sketch + tRPC procedure shape + MCP tool shape (if external)
   - DB schema additions/changes + migration plan + RLS policies
   - Event model — which topics, partition key `workspace_id` always
   - Paradigm declaration + justification
   - Data flow (mermaid)
   - Edge cases + failure modes
   - Security considerations (forwarded to Shreya)
   - Observability plan (metrics, logs, traces, alarms, dashboards)
   - Test strategy (unit / integration / contract / E2E / load / real-network smoke)
   - Impacted systems
   - Risks + tradeoffs + alternatives considered + why rejected
   - Cost estimate (LLM tokens/day at expected load)
6. Decompose the plan into per-builder track lists. Tag each track with `@vikram`, `@ananya`, `@karan`, `@maya` (multiple per task is fine).
7. Append journal.

### Outputs
- `architecture-plan.md` artifact.
- Track lists ready for Stage 3.

### Expected duration
- 30–90 minutes of agent work.

### Typical bounce triggers (back to CTOA)
- Requirement is ambiguous after attempting the plan.
- Requirement implies a new tech-stack layer (escalate via `tech-stack-evaluation`).
- Requirement would force a Single-Primitive violation no matter how creative the design.

### Exit gate (G2)
- All sections of `architecture-plan.md` filled.
- `@paradigm` declared and justified.
- Observability plan present.
- Test strategy present.
- Risks + alternatives documented.
- All 4 multi-tenancy enforcement layers addressed (JWT, service, DB, Kafka).
- CTO Advisor signs off on the paradigm choice (one-line note in the journal).

---

## Stage 3 — Parallel Development

**Owners:** Vikram (BE), Ananya (FE-W), Karan (FE-M), Maya (AI) — only those tagged in the track list.

### Inputs
- `architecture-plan.md` + the builder's per-track list.
- The builder's owned skills.
- The relevant per-feature journal entries from prior runs of the same feature (if any).

### What happens (per builder)
1. Read the architecture plan and the prior feature journal.
2. Load owned skills relevant to the track.
3. Decompose the track into 2–5 minute tasks (writing-plans discipline).
4. For each task:
   - Implement.
   - Write tests inline.
   - Run real-network smoke locally.
   - Run verification command and capture output.
   - Commit (small, focused).
5. When all in-lane Definition-of-Done items are green, post `READY-FOR-SECURITY` (or `READY-FOR-QA` if Shreya wasn't pre-consulted) in [`templates/developer-report.md`](../templates/developer-report.md).
6. Append journal entry per task and a final entry summarizing the track.

### Outputs
- Code, tests, migration files (if any), proto changes (if any), dashboard updates (if any).
- `developer-report.md` per builder.

### Expected duration
- Highly variable — a few hours to a few days for a meaningful feature.

### Typical bounce triggers (back to Architect)
- Architecture plan implies an anti-pattern (offset pagination, plaintext OAuth, missing `requireRole`, etc.).
- Plan doesn't account for a real-world edge case discovered in implementation.
- Plan misses a downstream consumer.

### Exit gate (G3) — per builder
- All in-lane Definition-of-Done checks pass.
- `developer-report.md` complete.
- Handoff signal posted.

> **Stage 3 advances to Stage 4 only when *all* tagged builders have posted READY**. The QA agent watches for this and gates the move.

---

## Stage 4 — Security Review (Shreya)

**Owner:** Shreya — **VETO** authority.

### Inputs
- All Stage 3 artifacts + code diffs + proto changes + schema changes + new MCP tools (if any) + new outbound channels (if any).

### What happens
1. Load `security-baseline`, `auth-and-access`, `defense-in-depth-validation` (incl. XSS), `vulnerability-scanning`, `oauth-implementation`, `india-commerce-economics` (compliance side).
2. For every mutation endpoint: verify `requireRole` + `requireWorkspaceMember` + Zod input + `workspace_id` assertion.
3. For every new MCP tool: verify auth scope + tenant check + Decision Log middleware.
4. For every new connector: verify OAuth AES-256-GCM + webhook signature + per-brand KMS key.
5. For every new outbound channel: verify DLT / NCPR / DND / calling hours / recording consent / 48h cap.
6. Run vulnerability scans (pnpm audit, Snyk, Bandit, safety, Trivy, OWASP DC).
7. Produce [`templates/security-review.md`](../templates/security-review.md) with:
   - Each gate, PASS/FAIL with evidence.
   - List of CRITICAL/HIGH/MED/LOW findings.
   - Recommended remediation for each finding.
   - Overall verdict.

### Outputs
- `security-review.md`.
- Status: `security-review` → `qa-review` (PASS) | `security-bounced` (FAIL).

### Expected duration
- 15–60 minutes.

### Typical bounce triggers (back to responsible dev)
- Any CRITICAL or HIGH finding.
- Any India compliance gap.
- Missing standard guard on a mutation endpoint.
- Plaintext OAuth in storage.
- New code path with PII in logs.

### Exit gate (G4)
- Zero CRITICAL / HIGH findings.
- Zero India compliance violations.
- All standard guards present and tested.
- All MCP tools tenant-checked.
- All connectors token-encrypted.

---

## Stage 5 — QA (Tanvi)

**Owner:** Tanvi — **VETO** on missing verification.

### Inputs
- Stage 3 + Stage 4 artifacts + all code diffs.

### What happens
1. Load `testing-tdd` (incl. mutation testing), `api-contract-testing`, `operational-readiness`, `verification-before-completion`.
2. Run:
   - Unit tests (`pnpm vitest`, `pytest`).
   - Integration tests (services + connectors with synthetic + live credentials).
   - Contract tests (`buf breaking`, Pact, tRPC schema diff, MCP schema diff).
   - E2E (Playwright for web, Detox for mobile).
   - Load (k6 — Phase 3+).
   - **Real-network smoke tests (mandatory for PASS).**
3. Verify **metric registry parity** (TS ↔ Python).
4. Run **operational-readiness checklist**: root handler, health, port, env vars, native deps.
5. Run mutation tests on high-stakes paths (metric registry, India compliance engine, Decision Log).
6. Capture *actual* command output for every claim.
7. Produce [`templates/qa-review.md`](../templates/qa-review.md) with PASS/FAIL + evidence.

### Outputs
- `qa-review.md`.
- Status: `qa-review` → `final-review` (PASS) | `qa-bounced` (FAIL).

### Expected duration
- 30–120 minutes (longer if E2E or load is in scope).

### Typical bounce triggers (back to responsible dev)
- <70% coverage on new code.
- Missing real-network smoke.
- Contract test missing on contract change.
- Mutation test missing on high-stakes path.
- Metric registry parity failure.
- Operational-readiness checklist red.

### Exit gate (G5)
- All test categories green.
- Coverage ≥70% on new code.
- Real-network smoke output captured.
- Metric parity confirmed.
- Operational-readiness checklist all green.

---

## Stage 6 — CTO Advisor Final Review

**Owner:** CTO Advisor — **VETO** authority.

### Inputs
- Every artifact from this run: CTOA intake, the 0–2 persona reviews, architecture plan, developer reports, security review, QA review.

### What happens
1. Re-read the original requirement (verify alignment).
2. Re-read the architecture plan (verify it still maps to the requirement after dev pivots).
3. Verify cost paradigm choice held through implementation (audit `@paradigm` decorators).
4. Verify all 4 multi-tenancy layers are present.
5. Verify observability plan was actually implemented.
6. Spot-check the code (sample 3–5 files).
7. Synthesize into [`templates/final-review.md`](../templates/final-review.md):
   - Requirement alignment (PASS/FAIL).
   - Architecture quality.
   - Code quality.
   - Security review summary.
   - QA review summary.
   - Risks remaining.
   - Production-readiness assessment.
   - Recommendation to Founder.

### Outputs
- `final-review.md`.
- Status: `final-review` → `awaiting-founder` (PASS) | `final-bounced` (FAIL).

### Expected duration
- 20–60 minutes.

### Typical bounce triggers (back to specific earlier stage)
- Paradigm audit failed → back to Stage 3 (or Stage 2 if the plan was wrong).
- Observability incomplete → back to Stage 3 (dev) or Stage 2 (plan).
- Requirement misalignment → back to Stage 2 (Architect) for re-plan.
- Cost estimate breached → back to Stage 2 (re-plan with cheaper paradigm).

### Exit gate (G6)
- All sub-reviews PASS.
- Paradigm audit clean.
- Observability complete.
- Risks acknowledged.

---

## Stage 7 — Founder Approval (Rishabh)

**Owner:** Rishabh — **HUMAN GATE**.

### Inputs
- `final-review.md` + every prior artifact (read on demand).
- The decision log's last 30 days for trend context.

### What happens
1. Read final review.
2. Apply strategic judgment (does this advance Brain's roadmap? does the cost make sense? is the risk acceptable now?).
3. Run `/approve <req-id>` or `/reject <req-id> <reason>`.

### Outputs
- Approval or rejection in `.engineering-os/decision-log/`.
- Status: `awaiting-founder` → `approved` (Stage 8) | `rejected` (terminal).

### Expected duration
- Up to Rishabh. Pipeline waits.

### Bounce behavior
- Rejection includes a reason. CTOA reads the reason and decides where to bounce (typically back to Stage 2 with a re-scoping note).

### Exit gate (G7)
- Founder's recorded decision is in the decision log.

---

## Stage 8 — Platform / DevOps (Jatin)

**Owner:** Jatin.

### Inputs
- Approved Stage 7 artifacts.

### What happens
1. Run CI: lint → typecheck → test → build → push to ECR.
2. ArgoCD syncs staging.
3. Run staging verification: real-network smoke, metric parity, dashboard sanity, alarm wiring sanity.
4. If staging fails: bounce to Stage 4 (could be code OR infra issue — let Shreya/Tanvi/Jatin triage).
5. If staging passes: deploy to production via ArgoCD (canary if applicable).
6. Watch for 48 hours. Auto-rollback if:
   - p95 latency >2 s for 5 min
   - Error rate >1% for 5 min
   - Health check failing 2 consecutive probes
7. Produce [`templates/deployment-report.md`](../templates/deployment-report.md).
8. Append final journal entry.

### Outputs
- Deployment report.
- Status: `deploying-staging` → `awaiting-prod-deploy` → `deploying-prod` → `monitoring` → `shipped` (48h clean) | `rolled-back` (auto-rollback fired).

### Expected duration
- 30 min to 2 hours for CI + staging + production push. 48h monitor afterwards.

### Typical bounce triggers
- Staging verification failure → Stage 4 triage.
- Production rollback → back to Stage 4.

### Exit gate (G8 + G9)
- Staging smoke passed.
- Production deploy completed.
- 48h post-deploy monitoring clean.

---

## What happens on session restart / git pull

When a teammate runs `git pull` then re-opens Claude Code:

1. **Session-start hook** (`hooks/on-session-start.sh`) reads `.engineering-os/state/active.json` and prints the list of in-flight requirements.
2. Each agent, on first invocation, **reads its own journal** (`.engineering-os/memory/agents/<role>.journal.md`) for continuity. Last-N entries are surfaced into context.
3. For any specific feature work, the agent **reads the per-feature journal** (`.engineering-os/memory/features/feat-<slug>.md`) before doing anything.

This is how "agents never forget." See [memory-and-git-sync.md](memory-and-git-sync.md) for the full mechanism.

---

## Manual escape hatches

Slash commands let a human operator override the pipeline when needed:

- `/handoff <req-id> <stage>` — manually move a requirement to a stage (e.g., when an emergency requires skipping Stage 4 — but Shreya's veto still applies on the next normal review).
- `/recall <feature-slug>` — print the full per-feature journal so a teammate gets caught up instantly.
- `/invoke-skill <skill-name>` — manually invoke a skill outside the pipeline.
- `/persona <topic>` — spawn an extra persona for an open question.

See the command-skills in [`skills/`](../skills/) (those with `disable-model-invocation: true`) for the full list.
