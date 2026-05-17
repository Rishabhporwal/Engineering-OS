# The Brain Engineering Operating System

> The complete internal operating manual. If you read only one document, read this one.

---

## Executive Summary

The Brain Engineering Operating System (Engineering OS) is an **AI engineering team delivered as a Claude Code plugin**. It takes a Founder's requirement and runs it through an 8-stage pipeline — CTO Advisor → Architect → Parallel Development → Security → QA → Final Review → Founder Approval → DevOps — producing production-grade code, audited and journaled, every time.

It exists so that **Brain (Pipada Capital)** can ship the AI-native commerce OS for D2C brands **without hiring a large engineering team early**. The plugin is the team: 10 named agents grounded in the Brain canon (`Requirements/BRAIN_BUSINESS.md`, `Requirements/BRAIN_TECHNICAL.md`, 53 curated skills).

Multiple teammates can use the plugin simultaneously. **All agent memory lives in `.engineering-os/` at the repo root and is committed to git.** When a teammate runs `git pull`, they receive the full state of every prior run.

---

## Core Philosophy

1. **Memory is the moat.** The Decision Log and per-feature journals are append-only forever. Agents never forget.
2. **No blind agreement.** Every agent must respectfully challenge a weak requirement using the [challenge framework](../prompts/challenge-framework.md).
3. **Cost-routed paradigms.** SQL > ML > Haiku > Sonnet. Every feature passes the Q1–Q4 cost-routing audit. (See [skill: cost-routing-paradigms](../skills/cost-routing-paradigms/SKILL.md).)
4. **Single-Primitive Rule.** Every cross-cutting concern is built once and consumed N times. (See [business-context.md §Single-Primitive Rule](business-context.md#the-single-primitive-rule-from-brain_businessmd-165).)
5. **Multi-tenant `workspace_id` discipline.** Enforced at 4 layers (JWT → service-side → DB RLS → Kafka envelope).
6. **India compliance is P0.** DND, NCPR, DLT, calling hours, GST — zero violations.
7. **Goal-driven verification.** Every "done" claim runs a verification command and captures real output. (See [skill: verification-before-completion](../skills/verification-before-completion/SKILL.md).)

---

## Operating Principles (the day-to-day rules)

1. **Make requirements less dumb first.** Before any plan, the CTO Advisor and Architect ask: *Can we delete? Simplify? Defer?*
2. **Vertical slices over horizontal layers.** Ship one user-visible feature end-to-end before broadening.
3. **Small commits.** A commit must be reviewable in <10 minutes.
4. **Real-network smoke tests beat in-memory mocks.** Every PASS verdict requires real-network smoke output.
5. **Append-only journals, never overwrite.** Memory is the moat; mutation of memory is corruption.
6. **One paradigm per code path.** No "try LLM, fallback to ML." Declare the paradigm; commit to it.
7. **Multi-region from day one, India-first by sequencing.** Every primitive uses a `RegionAdapter` interface even when only India is implemented today.
8. **Challenge respectfully, always with a path forward.** "No" is allowed; "no, and here's what I recommend instead" is required.
9. **Verify before claiming success.** "Should work," "I think it's done," "tests should pass" — all rejected by QA.

---

## Team Structure

10 agents + 1 human (Founder/CTO). Names match the personas already used in the curated skills in `Requirements/skills/`.

| # | Role | Persona | Pipeline stage(s) |
|---|------|---------|-------------------|
| 1 | CTO Advisor (shadow CTO) | *(unnamed — Rishabh's shadow)* | Stage 1, Stage 6 |
| 2 | Dynamic Persona Generator | runtime-spawned (3 personas) | Stage 1 |
| 3 | Architect | **Aryan** | Stage 2 |
| 4 | Backend Developer | **Vikram** | Stage 3 |
| 5 | Frontend Web Developer | **Ananya** | Stage 3 |
| 6 | Mobile Developer | **Karan** | Stage 3 |
| 7 | Intelligence Engineer (AI/ML/agents) | **Maya** | Stage 3 |
| 8 | Security Reviewer | **Shreya** | Stage 4 |
| 9 | QA Agent | **Tanvi** | Stage 5 |
| 10 | Platform / DevOps | **Jatin** | Stage 8 |
| — | Founder / CTO | **Rishabh** (you) | Stage 7 |
| (+ Product Manager) | **Priya** | not a pipeline stage; cross-cuts |

Detailed missions, authority, operating loops, and skill bindings are in [role-empowerment-model.md](role-empowerment-model.md).

---

## Responsibility Matrix (RACI)

A condensed RACI for the most common activities. **R**esponsible / **A**ccountable / **C**onsulted / **I**nformed.

| Activity | CTOA | Aryan | Vikram | Ananya | Karan | Maya | Shreya | Tanvi | Jatin | Priya | Rishabh |
|----------|:----:|:-----:|:------:|:------:|:-----:|:----:|:------:|:-----:|:-----:|:-----:|:-------:|
| Intake & scope requirement | A | C | I | I | I | I | I | I | I | C | C |
| Spawn dynamic personas | A,R | I | — | — | — | — | I | — | — | C | I |
| Technical plan | C | A,R | C | C | C | C | C | I | C | I | I |
| Backend implementation | I | C | A,R | — | — | — | C | I | I | — | — |
| Web frontend implementation | I | C | I | A,R | — | — | C | I | I | — | — |
| Mobile implementation | I | C | — | C | A,R | — | C | I | I | — | — |
| AI/agent implementation | I | C | — | — | — | A,R | C | I | I | — | — |
| Security review | I | C | I | I | I | I | A,R | I | I | — | I |
| QA / test verification | I | C | I | I | I | I | C | A,R | I | — | I |
| Final review | A,R | C | I | I | I | I | C | C | C | I | I |
| Founder approval | I | I | I | I | I | I | I | I | I | I | A,R |
| Deploy (staging → prod) | I | I | I | I | I | I | C | C | A,R | I | I |
| Rollback decision | C | C | C | C | C | C | C | C | A,R | I | C |
| Schema/proto changes | C | A,R | C | I | I | C | C | I | I | I | I |
| Cost cap breach response | A | C | C | — | — | A,R | I | I | I | I | C |
| India compliance gate | C | C | C | C | C | C | A,R | C | C | C | I |

---

## Decision Rights

Decisions are categorized by where they sit on the autonomy axis.

| Level | Who decides | Examples |
|-------|------------|----------|
| **L1 — Inside-plan tactical** | Implementing agent (Vikram/Ananya/Karan/Maya) | Component composition, helper functions, test layout, internal naming, where to put a TypeScript type |
| **L2 — Architectural choice within stack** | Architect (Aryan) | API design, schema additions, event topic, paradigm choice, service boundary |
| **L3 — Security or compliance gate** | Security Reviewer (Shreya) — VETO | CRITICAL/HIGH finding, India telecom violation, MASVS L2 gap |
| **L4 — Process / quality gate** | QA (Tanvi) — VETO on missing verification | PASS / FAIL / NEEDS-MORE-INFO |
| **L5 — Final technical review** | CTO Advisor — VETO | Stage 6 final review; reject back to any earlier stage |
| **L6 — Strategic / Founder** | Rishabh | Stack changes, region additions, partner commits, pricing changes, deploy approval |

**The team can challenge any level (including L6).** See [Anti-Blind-Agreement Rule](#anti-blind-agreement-rule-non-negotiable) below.

---

## The 8-Stage Workflow

```
                Founder (Rishabh)
                       │
                       ▼ /requirement <text>
            ┌──────────────────────┐
            │ Stage 1: CTO Advisor │  intake + brainstorm
            │   + 3 dynamic        │  (challenge weak reqs)
            │     personas         │
            └──────────┬───────────┘
                       │ ADVANCE  │  CHALLENGE → back to Founder
                       ▼          │  KILL → archived
            ┌──────────────────────┐
            │ Stage 2: Architect   │  technical plan, paradigm, schema, observability,
            │   (Aryan)            │  test strategy, risks, alternatives
            └──────────┬───────────┘
                       │ ADVANCE
                       ▼
            ┌─────────────────────────────────────────────┐
            │ Stage 3: Parallel Development               │
            │  Vikram (BE) ∥ Ananya (FE-W) ∥              │
            │  Karan (FE-M) ∥ Maya (AI)                    │
            └──────────┬──────────────────────────────────┘
                       │ All "ready for QA"
                       ▼
            ┌──────────────────────┐
            │ Stage 4: Security    │  Shreya — VETO on CRITICAL/HIGH or India compliance
            │   (Shreya)           │  ── on fail, bounce to responsible dev
            └──────────┬───────────┘
                       │ PASS
                       ▼
            ┌──────────────────────┐
            │ Stage 5: QA          │  Tanvi — VETO on missing real-network smoke
            │   (Tanvi)            │  ── on fail, bounce to responsible dev
            └──────────┬───────────┘
                       │ PASS
                       ▼
            ┌──────────────────────┐
            │ Stage 6: Final       │  CTO Advisor — VETO; can bounce to any earlier stage
            │   CTO Advisor        │
            └──────────┬───────────┘
                       │ ADVANCE
                       ▼
            ┌──────────────────────┐
            │ Stage 7: Founder     │  ★ HUMAN GATE ★ /approve or /reject
            │   (Rishabh)          │
            └──────────┬───────────┘
                       │ APPROVED
                       ▼
            ┌──────────────────────┐
            │ Stage 8: Platform /  │  CI → ECR → ArgoCD → staging → verify →
            │   DevOps (Jatin)     │  production → 48h monitor → auto-rollback ready
            └──────────────────────┘
                       │
                       ▼
                Deployment Report
```

### Stage-by-stage detail

Each stage is its own document — see [workflow.md](workflow.md) for stage-by-stage execution detail (inputs, outputs, expected duration, escalation triggers, artifact templates).

---

## Quality Gates

A change advances stage-N → stage-N+1 only if **all** gate conditions are true. The full gate definitions are in [quality-gates.md](quality-gates.md). Summary:

| Gate | Owner | Cannot advance if … |
|------|-------|--------------------|
| **G1: Intake → Architecture** | CTOA | Requirement lacks a problem statement, target user, success metric, or constraints. |
| **G2: Architecture → Dev** | Aryan + CTOA | Paradigm not declared, single-primitive violated, observability plan missing, schema change not migration-planned. |
| **G3: Dev → Security** | Implementing dev | Definition-of-Done items in the dev's lane not all green. |
| **G4: Security → QA** | Shreya | Any CRITICAL/HIGH; any India compliance gap; any missing standard guard. |
| **G5: QA → Final review** | Tanvi | <70% coverage; missing real-network smoke; contract test absent on contract change; mutation test missing on high-stakes path; metric registry parity failure. |
| **G6: Final → Founder** | CTOA | Cost paradigm audit failed; observability incomplete; risk not documented; alternatives not surfaced. |
| **G7: Founder → Deploy** | Founder | Founder hasn't approved. |
| **G8: Staging → Production** | Jatin | Staging smoke failed; auto-rollback not wired; dashboard or alarm missing for new metric. |
| **G9: 48h post-deploy** | Jatin | Any alarm fired; auto-rollback triggered → re-enter Stage 4. |

---

## Escalation Rules

Detailed in [escalation-rules.md](escalation-rules.md). Summary:

- **Bounce-back** (within pipeline): G4 fails → back to responsible dev. G5 fails → back to responsible dev. G6 fails → back to whoever owns the broken artifact (could be Architect, dev, Shreya, or Tanvi).
- **Escalate to CTO Advisor**: Architectural ambiguity; cross-team conflict; cost paradigm dispute; gate interpretation question.
- **Escalate to Founder/Rishabh**: Tech stack change, region addition, partner commitment, pricing impact, compliance scope change, anything implying ADR-001 update.
- **Page (P0) immediately**:
  - DND violation in production calling.
  - Cross-brand data leak suspected.
  - Auth bypass / multi-tenancy break.
  - Auto-execute action with financial impact and no rollback.
  - LLM cost >1.5× monthly cap / 30 in a day.
  - Memory layer corruption.

---

## Anti-Blind-Agreement Rule (non-negotiable)

Even though Rishabh is Founder/CTO and source of truth, **every agent must respectfully challenge** when a requirement is:

- unclear
- risky
- insecure
- low value
- technically expensive
- overcomplicated
- unscalable
- misaligned with the product
- bad for customers
- bad for enterprise readiness
- bad for long-term maintainability

When challenging, agents use the [challenge framework](../prompts/challenge-framework.md):

1. **What I understood.**
2. **What concern I have.**
3. **What risk exists.**
4. **What alternative I recommend.**
5. **What decision I need from you.**

**Tone is constructive, never combative.** The team can say no — but always with a path forward.

This rule is **embedded in the system prompt** (see [prompts/system-prompt.md](../prompts/system-prompt.md)), so every agent inherits it.

---

## Communication Rules

1. **Single-thread per requirement.** A requirement gets one `req-<slug>` ID; every artifact is tagged with it.
2. **Append-only journaling.** Per-agent journal + per-feature journal entry on every meaningful action (see [role-empowerment-model.md §Cross-cutting](role-empowerment-model.md#cross-cutting-how-every-agent-journals)).
3. **Handoff signals are explicit.** No vague "I'm done." The dev posts `READY-FOR-QA` (or `READY-FOR-SECURITY` if Shreya wasn't pre-consulted) with the artifact list.
4. **Disagreement is logged.** Every challenge produces an artifact (`templates/challenge-record.md` — V2 addition; for now, append to the relevant journal).
5. **Cross-agent questions go through the CTO Advisor by default.** Avoid pairwise side-channels that bypass the audit trail.
6. **Founder asks** carry the most weight, but Founder **answers to questions** (especially "are you sure?") are also logged.

---

## Definition of Done (composite)

A change is **Done** only when **all** of these are true. See [technical-context.md §Definition of Done](technical-context.md#definition-of-done-composite--tanvi-and-cto-advisor-both-gate-on-this) for the long form. The headline checklist:

### Code & paradigm
- [ ] `@paradigm` decorator on every new code path.
- [ ] Per-feature LLM token budget set; soft 80%, hard fail 100%.
- [ ] Idempotency keys cached for all writes.
- [ ] Zod schemas on every API input; server-side re-validation.
- [ ] All timestamps UTC or `Asia/Kolkata` — never ambiguous.
- [ ] `workspace_id` assertion in every gRPC handler.
- [ ] `requireRole(...)` on every mutation endpoint.
- [ ] CloudWatch metrics + Sentry instrumentation present.

### Tests
- [ ] >70% coverage on new code.
- [ ] Real-network smoke test passes.
- [ ] Contract tests (`buf breaking` for proto; Pact for services; Zod diff for tRPC; MCP schema diff).
- [ ] Mutation tests for high-stakes paths.

### Security & compliance
- [ ] No CRITICAL/HIGH from vulnerability scan.
- [ ] No India compliance violation.
- [ ] PII never in logs.
- [ ] OAuth tokens AES-256-GCM with per-brand KMS key.

### Ops
- [ ] Health endpoints respond.
- [ ] Operational-readiness checklist all green.
- [ ] Dashboard added/updated if new metric.
- [ ] Alarm registered if new SLO implied.

### Process
- [ ] Decision Log entry written.
- [ ] Per-feature journal updated.
- [ ] CTO Advisor final review attached.
- [ ] Founder approval recorded.

---

## Production Readiness Checklist

For Stage 8 → production:

- [ ] Staging deploy succeeded.
- [ ] Real-network smoke on staging passed.
- [ ] Auto-rollback triggers wired:
  - p95 latency >2 s for 5 min → roll back
  - Error rate >1% for 5 min → roll back
  - Health check failing for 2 consecutive probes → roll back
- [ ] CloudWatch dashboard updated for any new metric.
- [ ] CloudWatch alarm registered for any new SLO.
- [ ] Runbook in `.engineering-os/runbooks/` (V2) or in journal addendum (MVP).
- [ ] Release note appended to `.engineering-os/decision-log/<YYYY>/<MM>/<DD>.jsonl`.
- [ ] On-call rotation acknowledged (V2; MVP: Jatin holds).
- [ ] Founder informed.

---

## Status Lifecycle

A requirement moves through these statuses. (See [workflows/state-machine.yaml](../workflows/state-machine.yaml) for the formal state machine.)

| Status | Stage | Meaning |
|--------|-------|---------|
| `intake` | pre-1 | Founder submitted; not yet picked up. |
| `cto-review` | 1 | CTOA + 3 personas active. |
| `challenged-back` | 1 (terminal until Founder responds) | CTOA pushed back to Founder. |
| `architect` | 2 | Aryan designing. |
| `dev-parallel` | 3 | Builders active. |
| `dev-blocked` | 3 | A builder is blocked; surfaces in `/status`. |
| `security-review` | 4 | Shreya reviewing. |
| `security-bounced` | 4 → back to 3 | Shreya found CRITICAL/HIGH or compliance gap. |
| `qa-review` | 5 | Tanvi running tests + verification. |
| `qa-bounced` | 5 → back to 3 | Coverage gap, smoke failed, parity broken. |
| `final-review` | 6 | CTOA final pass. |
| `final-bounced` | 6 → back to N | CTOA bouncing to specific earlier stage. |
| `awaiting-founder` | 7 | Founder gate. |
| `rejected` | 7 (terminal) | Founder rejected; archived with reason. |
| `approved` | 7 → 8 | Founder approved; DevOps takes over. |
| `deploying-staging` | 8a | CI passed; staging deploy in flight. |
| `staging-failed` | 8a → back to 3 | Staging verification failed. |
| `awaiting-prod-deploy` | 8b | Staging green; ready for production push. |
| `deploying-prod` | 8c | Production deploy in flight. |
| `monitoring` | 8d (48h) | Production live; under watch. |
| `rolled-back` | 8d → back to 4 | Auto-rollback fired. |
| `shipped` | 9 (terminal happy path) | 48h post-deploy with no incidents. |

---

## Plugin Architecture (one-paragraph summary; full design in `plugin-architecture.md`)

The plugin lives at the repo root (`.claude-plugin/plugin.json`). It exposes **10 agents** (via `agents/`), **53 skills** (mirrored from `Requirements/skills/` into `skills/`), ~**10 slash commands** (via `commands/`), and **hooks** that on session start auto-rehydrate the agent personas + load the current state of all active requirements from `.engineering-os/state/`. All persistent memory — journals, state, decision log, run artifacts — lives in `.engineering-os/` at the repo root, committed to git. Append-only conventions and per-run timestamped folders make merge conflicts nearly impossible.

See [plugin-architecture.md](plugin-architecture.md) for the full design.

---

## Reading order for a new operator

If you're a new teammate just cloning the repo, read these in this order:

1. [README.md](../README.md) — what this is.
2. [docs/operating-system.md](operating-system.md) — *this file*.
3. [docs/business-context.md](business-context.md) — Brain primer.
4. [docs/technical-context.md](technical-context.md) — stack primer.
5. [docs/workflow.md](workflow.md) — stage-by-stage.
6. [docs/quality-gates.md](quality-gates.md) — what to expect at every gate.
7. [docs/escalation-rules.md](escalation-rules.md) — when to bounce, when to escalate.
8. [docs/memory-and-git-sync.md](memory-and-git-sync.md) — how shared memory works.
9. [docs/plugin-architecture.md](plugin-architecture.md) — under the hood.
10. [ROADMAP.md](../ROADMAP.md) — MVP/V2/V3 + end-to-end walkthrough.

Then in Claude Code, run `/status` to see what's in flight, and `/recall <feature-slug>` to read the history of any past feature.
