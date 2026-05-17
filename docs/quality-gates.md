# Section 3.3 — Quality Gates

Every transition between stages is guarded. A requirement cannot advance unless **all** gate conditions are true. Gates are owned, evidence-based, and auditable.

This document defines each gate's:
- **Owner** (who decides).
- **Condition** (what must be true).
- **Evidence** (what artifact + journal entry proves it).
- **Bounce target** (where it goes if it fails).

---

## G1 — Intake → Architecture

**Owner:** CTO Advisor.

**Condition:**
- [ ] Requirement has a clear **problem statement** (what is broken / missing).
- [ ] Requirement has a clear **target user** (persona + tier).
- [ ] Requirement has a **success metric** (how do we know it worked).
- [ ] Requirement has at least one stated **constraint** (cost, time, regulatory, technical).
- [ ] 3 dynamic personas have weighed in; each surfaced at least one concern.
- [ ] CTO Advisor decision is one of: ADVANCE, CHALLENGE-BACK, KILL.

**Evidence:**
- `cto-advisor-review.md` artifact in the run folder.
- 3 `dynamic-persona-review.md` artifacts.
- Decision log entry.

**Bounce target on fail:** Back to Founder (`challenged-back` status) with structured challenge.

---

## G2 — Architecture → Development

**Owner:** Architect (with CTO Advisor sign-off on paradigm).

**Condition:**
- [ ] `architecture-plan.md` has **every section filled** (no `TBD`).
- [ ] **`@paradigm`** declared and justified (SQL / ML / Haiku / Sonnet).
- [ ] **Cost estimate** in tokens-per-day (or rupees-per-month) at expected load.
- [ ] **Single-Primitive sweep** done — no duplicated audience builder / consent flow / decision log / notification / attribution / identity.
- [ ] **DB schema additions** have a migration plan + RLS policy + index plan.
- [ ] **Event topics** named per convention `<domain>.<entity>.<event_type>.v<version>`; partition key is `workspace_id`.
- [ ] **API surfaces** (gRPC / tRPC / MCP) have proto sketches; breaking-change implications considered (`api-versioning-strategy`).
- [ ] **Observability plan** lists metrics, logs, traces, alarms, dashboards.
- [ ] **Test strategy** lists unit + integration + contract + (E2E / load if applicable) + real-network smoke.
- [ ] **4 multi-tenancy layers** addressed (JWT, service, DB, Kafka).
- [ ] **Risks + alternatives** listed; alternatives that were rejected include the reason.
- [ ] Track lists tagged per builder (`@vikram`, `@ananya`, `@karan`, `@maya`).

**Evidence:**
- `architecture-plan.md`.
- CTO Advisor's one-line paradigm sign-off in the architect's journal.

**Bounce target on fail:** Back to Stage 2 (Architect re-works) or Stage 1 (back to CTOA if requirement is now unworkable).

---

## G3 — Development → Security Review

**Owner:** Implementing developer (per-builder gate). All builders tagged in the track list must hit this gate before Stage 4 starts.

**Condition (per builder):**

**Code & paradigm**
- [ ] `@paradigm` decorator on every new code path.
- [ ] Per-feature LLM token budget set.
- [ ] Idempotency keys cached for all write operations.
- [ ] Zod schemas on every API input; server-side re-validation.
- [ ] All timestamps UTC or `Asia/Kolkata` — never ambiguous.
- [ ] `workspace_id` assertion in every gRPC handler.
- [ ] `requireRole(...)` on every mutation endpoint.
- [ ] CloudWatch custom metrics + Sentry instrumentation present.

**Tests (in-lane)**
- [ ] Unit tests for new functions.
- [ ] Integration tests where the change crosses a boundary.
- [ ] **Real-network smoke** ran locally and captured output.
- [ ] Coverage ≥70% on new code in this lane.

**Specifics per lane**
- **BE (Vikram):** Cursor pagination on any new list endpoint. No offset. No sequential DB queries in a layout (use `Promise.all`).
- **FE-W (Ananya):** Server Component by default. Lighthouse run; Core Web Vitals targets met.
- **FE-M (Karan):** Morning Brief three-signal rule honored. `expo-secure-store` for tokens. Offline behavior tested.
- **AI (Maya):** Prompt caching applied where possible. `@mcp_tool` + Decision Log middleware on any new MCP tool. Daily-tick simulation passes locally.

**Evidence:**
- `developer-report.md` per builder.
- Test command outputs captured in journal.
- Handoff signal `READY-FOR-SECURITY` posted.

**Bounce target on fail:** Self (developer reworks). If the failure traces to a plan defect, bounce to Stage 2.

---

## G4 — Security Review → QA

**Owner:** Shreya — **VETO** authority.

**Condition:**
- [ ] **Zero CRITICAL findings.** No exceptions.
- [ ] **Zero HIGH findings.** No exceptions.
- [ ] **Zero India compliance violations** — DLT, NCPR, DND, calling hours, recording consent, 48h cap.
- [ ] Every mutation endpoint: `requireRole` + `requireWorkspaceMember` + Zod input + `workspace_id` assertion present and tested.
- [ ] Every new MCP tool: auth scope + tenant check + Decision Log middleware.
- [ ] Every new connector: OAuth AES-256-GCM + webhook signature + per-brand KMS key.
- [ ] Vulnerability scans run: pnpm audit, Snyk, Bandit, safety, pip-audit, Trivy, OWASP Dep-Check. No CRITICAL/HIGH.
- [ ] No PII in logs (sample log lines reviewed).
- [ ] No plaintext OAuth tokens anywhere.

**Evidence:**
- `security-review.md` with gate-by-gate PASS/FAIL + finding evidence.
- Scan output captured in journal.

**Bounce target on fail:** Responsible developer (the finding's owner). Shreya tags `@vikram`, `@ananya`, `@karan`, or `@maya` in the bounce note.

**MED / LOW findings:** logged but do not block. Tracked as tech debt in journal.

---

## G5 — QA → Final Review

**Owner:** Tanvi — **VETO** on missing verification.

**Condition:**
- [ ] All unit tests green (`pnpm vitest`, `pytest`).
- [ ] All integration tests green.
- [ ] All contract tests green (`buf breaking`, Pact, tRPC schema diff, MCP schema diff).
- [ ] All E2E green (Cypress for web, Detox for mobile).
- [ ] Load tests pass (Phase 3+ at 5K RPS target).
- [ ] **Real-network smoke output captured**. No "should work" — actual output.
- [ ] **Metric registry parity** confirmed (TS ↔ Python).
- [ ] **Operational-readiness checklist** all green: root handler, health endpoint, port selection, env var validation, native-dep gotchas.
- [ ] Mutation tests pass on **high-stakes paths**: metric registry, India compliance engine, Decision Log.
- [ ] Coverage ≥70% on the change set (composite — re-validated post-builder claim).
- [ ] No flaky tests introduced (re-run 3× confirms).

**Evidence:**
- `qa-review.md` with command + output for every claim.
- All test output captured in journal.

**Bounce target on fail:** Responsible developer per finding.

---

## G6 — Final Review → Founder

**Owner:** CTO Advisor — **VETO** authority.

**Condition:**
- [ ] **Requirement alignment** — does the shipped change still solve the original requirement? (Drift check.)
- [ ] **Paradigm audit** — every `@paradigm` decorator matches the declared plan; no Sonnet snuck in where Haiku was promised.
- [ ] **Architecture quality** — Single-Primitive Rule held; no anti-pattern drift.
- [ ] **Code quality** — sampled 3–5 files; no obvious smells; comments only where the *why* is non-obvious.
- [ ] **Security review** — Shreya PASS.
- [ ] **QA review** — Tanvi PASS.
- [ ] **Observability complete** — metrics emitted, dashboards updated, alarms wired.
- [ ] **Cost estimate held** — actual tokens/day from a simulated daily tick within ±20% of plan.
- [ ] **Risks acknowledged** — `final-review.md` lists any remaining risks.
- [ ] **Production-readiness assessment** — Jatin's pre-deploy checks would pass.
- [ ] **Recommendation to Founder** — explicit APPROVE / APPROVE-WITH-CAVEATS / REJECT.

**Evidence:**
- `final-review.md`.
- CTOA paradigm audit notes in `cto-advisor.journal.md`.

**Bounce target on fail:** Specific earlier stage (CTOA chooses based on the failure's root cause — often Stage 2 or Stage 3).

---

## G7 — Founder → Deploy

**Owner:** Rishabh — **HUMAN GATE**.

**Condition:**
- [ ] Founder ran `/approve <req-id>`.

**Evidence:**
- Decision log entry: `{"actor": "rishabh", "decision": "approved", "req_id": "...", "timestamp": "..."}`.

**Bounce target on rejection:** CTOA reads the rejection reason and re-routes to the appropriate stage.

---

## G8 — Staging → Production

**Owner:** Jatin.

**Condition:**
- [ ] CI green: lint → typecheck → test → build → ECR push.
- [ ] ArgoCD staging sync succeeded.
- [ ] Staging real-network smoke passed (Tanvi's test scripts re-run on staging).
- [ ] Staging metric parity verified.
- [ ] Dashboard panels render with non-zero data on staging.
- [ ] Alarms wired and verified (synthetic trigger fires the alarm).
- [ ] Rollback plan documented in `deployment-report.md`.

**Evidence:**
- `deployment-report.md` Section "Staging verification".

**Bounce target on fail:** Stage 4 triage (Shreya/Tanvi/Jatin decide whether it's a code defect, test gap, or infra issue).

---

## G9 — Post-Deploy 48h Monitor

**Owner:** Jatin (with auto-rollback automation).

**Condition (over 48h):**
- [ ] p95 latency stays <2 s.
- [ ] Error rate stays <1%.
- [ ] Health check probes pass.
- [ ] No alarms fired.
- [ ] No auto-rollback triggered.

**Evidence:**
- CloudWatch dashboard snapshot at +24h and +48h.
- `deployment-report.md` Section "Post-deploy monitor".

**Bounce target on fail:** Auto-rollback fires → status → `rolled-back` → back to Stage 4 for triage.

---

## How agents check gates

1. **Static check (precondition):** Before declaring "ready," the responsible agent reads this file and self-checks the gate it's about to hand off across.
2. **Reviewer check (postcondition):** The next-stage owner reads this file and verifies each condition against the evidence.
3. **CI check:** A subset of gates are automated (paradigm decorator present, test coverage threshold, security scan exit code, contract test diff). CI fails the merge if these are not green — even before any agent gates run.

> **No gate can be "waived" silently.** If the team needs to ship despite a gate failure, the CTO Advisor must escalate to Founder for an explicit, logged waiver — which becomes a tech-debt item with an owner and a date.

---

## Gate failure → bounce conventions

When a gate fails, the responsible agent posts a structured bounce-note that becomes the next agent's input. Bounce-note shape:

```markdown
## BOUNCE — gate <G#> failed — <YYYY-MM-DDThh:mm:ssZ>
**From:** <agent>
**To:** <agent or stage>
**Reason:** <one-sentence summary>
**Evidence:**
- <link to file + line>
- <command run + output>
**Recommended action:** <specific>
**Blocks Stage N until:** <specific condition>
```

The bounce-note is appended to both the per-agent journal and the per-feature journal.

---

## Tracking gate health

A weekly digest (run by `/digest` slash command, V2) aggregates from the decision log:
- How often each gate fired (PASS / FAIL ratio).
- Average time spent in each stage.
- Top 5 root causes of bounce-backs.

This data feeds back into making the operating system itself smarter: e.g., if Stage 4 bounces on `requireRole` 5+ times in a month, the architect's Stage 2 checklist gets an explicit "verify `requireRole` on every mutation" item.

---

## Related

- [operating-system.md](operating-system.md) — overall philosophy & RACI.
- [workflow.md](workflow.md) — stage-by-stage detail.
- [escalation-rules.md](escalation-rules.md) — what to do when a gate fail can't be resolved at this layer.
