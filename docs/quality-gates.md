# Section 3.3 — Quality Gates

Every transition between stages is guarded. A requirement cannot advance unless **all** gate conditions are true. Gates are owned, evidence-based, and auditable.

This document defines each gate's:
- **Owner** (who decides).
- **Condition** (what must be true).
- **Evidence** (what artifact + journal entry proves it).
- **Bounce target** (where it goes if it fails).

---

## G0 — Pre-flight dependency check

**Owner:** Engineering Advisor (Stage 1 — runs BEFORE any persona spawn or "less dumb first" pass).

**Condition:**
- [ ] If this requirement is a child of a meta-tracker, its `blocks` field has been read from the parent's `proposed_children[]`.
- [ ] Every blocker in `blocks` has `status == "shipped"` OR `status == "founder-override-of-dependency-rule"` in `state/active.json`.
- [ ] If any blocker is unshipped: the Advisor REFUSES to proceed past G0 and surfaces to the Stakeholder.

**Evidence:**
- Audit-log event: `{"actor":"cto-advisor","type":"dependency-precheck","req_id":"...","blockers":[...],"all_blockers_shipped":<bool>}`.
- On violation: a `pending-stakeholder-attention.md` artifact in the run folder explaining the unshipped blocker(s).

**Bounce target on fail:** No bounce — work is REFUSED, not bounced. State becomes `blocked-on-dependency` with `current_owner=founder`. The Stakeholder either waits for the blocker to ship or invokes `/engineering-os:override-dependency-rule` with a written rationale (which becomes a logged audit-trail entry).

**Why this exists:** a child requirement can ship while a declared blocker is still orphaned at Stage 1, and the Advisor can approve it on the Stakeholder's behalf without flagging the violation. G0 makes the check mechanical.

---

## Stage 4 skip exception

**Default:** Stage 4 (Security) runs on every requirement.

**Exception — "Stage 4 fast-pass":** Skipping Stage 4 is permitted IF AND ONLY IF **all** of these are true:

- [ ] The staged file set contains ONLY files with these extensions: `.md`, `.txt`, `.json`, `.yaml`, `.yml`.
- [ ] NO file under a source/service/package directory (e.g. `apps/`, `src/`, `services/`, `packages/`, `protos/`, migrations dir, mobile app dir) is touched.
- [ ] NO `.env`, `.env.example`, dependency lockfile, or root manifest is touched.
- [ ] NO file in the auth/secret-relevant set is touched (any file matching the regex `secret|password|token|key|credential|auth` in path).
- [ ] An explicit `stage_4_skip_rationale` field is filled in `06-architecture-plan.md` § "Security considerations".

**On qualified skip:**
- Architect (Stage 2) writes the `stage_4_skip_rationale` and routes the handoff to dev with `next_after_dev = qa-agent` (not `security-reviewer`).
- The Security agent, when invoked anyway, may emit a `type: stage-4-fast-pass` audit-log event with a one-line confirmation and advance immediately.
- QA agent (Stage 5) MUST re-run a minimal version of the skipped Stage 4 verification itself (per the W13 protocol below).

**On unqualified skip attempt:** Stage 4 runs full review. The mere presence of a `.env`, lockfile, code file, or auth-relevant file in the staged set is enough to disqualify fast-pass — no human judgment needed.

**Why this exists:** an agent skipping Stage 4 on a pure-docs change by judgment alone would rot into "skip whenever convenient." This rule lets the skip happen safely AND mechanically.

---

## W13 — Mandatory upstream-skip re-run

**Owner:** QA Agent at Stage 5.

**Condition:**
- [ ] If Stage 4 was marked SKIPPED or FAST-PASS, the QA agent MUST re-run a minimal version of the Stage 4 verification itself.
- [ ] At minimum: `git diff --cached | grep -iE 'password|secret|api[_-]?key|bearer|aws_|sk-[a-zA-Z0-9]+|ghp_'` on the staged diff. Capture output.
- [ ] Result is recorded in `10-qa-review.md` under a new "Stage 4 skip acknowledgment" section.

**Why this exists:** anti-blind-agreement applied across stage boundaries. The QA agent doesn't trust upstream skips blindly; it re-verifies.

---

## W14 — Mandatory Stage-5 gate re-run at final review

**Owner:** Engineering Advisor at Stage 6.

**Condition:**
- [ ] The Advisor spot-re-runs at least 3 of the QA agent's Stage 5 verification gates with captured output.
- [ ] Common picks: G1 app-code-diff sentinel, G3 provenance/discipline gate, G4 parity round-trip.
- [ ] Result is recorded in `11-final-review.md` under "Re-verified Stage 5 gates" section, with the exact command + actual output.
- [ ] If the Advisor cannot replicate the QA agent's PASS: BOUNCE to Stage 5 with the finding.

**Why this exists:** Stage 6 must not rubber-stamp. The final reviewer independently re-runs a sample of the prior stage's gates.

---

---

## G1 — Intake → Architecture

**Owner:** Engineering Advisor.

**Condition:**
- [ ] Requirement has a clear **problem statement** (what is broken / missing).
- [ ] Requirement has a clear **target user** (persona + tier).
- [ ] Requirement has a **success metric** (how do we know it worked).
- [ ] Requirement has at least one stated **constraint** (cost, time, regulatory, technical).
- [ ] G0 (pre-flight dependency check) PASSED — if this is a child req, all declared blockers are `shipped` or `founder-override-of-dependency-rule`.
- [ ] Persona count (0, 1, or 2) recorded with rationale per the complexity classifier in `agents/cto-advisor.md`. If 1 or 2 personas spawned, each surfaced at least one concern. If 0 personas, the Advisor's own analysis stands as the synthesis.
- [ ] Engineering Advisor decision is one of: ADVANCE, CHALLENGE-BACK, KILL.

**Evidence:**
- `cto-advisor-review.md` artifact in the run folder.
- 0-2 `dynamic-persona-review.md` artifacts (one per spawned persona).
- Audit-log entry.

**Bounce target on fail:** Back to the Stakeholder (`challenged-back` status) with structured challenge.

---

## G2 — Architecture → Development

**Owner:** Architect (with Engineering Advisor sign-off on the effort tier).

**Condition:**
- [ ] `architecture-plan.md` has **every section filled** (no `TBD`).
- [ ] **Effort tier** declared and justified (deterministic logic / statistical-ML / small model / large model — cheapest sufficient).
- [ ] **Cost estimate** (tokens-per-day, or monthly cost) at expected load.
- [ ] **Single-Primitive sweep** done — no duplicated cross-cutting concern (shared builder / consent flow / audit log / notification / attribution / identity).
- [ ] **Data-store schema additions** have a migration plan + isolation policy + index plan.
- [ ] **Event topics** named per the product's convention; partition key is the tenant-isolation key.
- [ ] **API/contract surfaces** have contract sketches; breaking-change implications considered (`api-discipline`).
- [ ] **Observability plan** lists metrics, logs, traces, alarms, dashboards.
- [ ] **Test strategy** lists unit + integration + contract + (E2E / load if applicable) + real-network smoke.
- [ ] **All tenant-isolation layers** addressed (identity → service → data store → async backbone).
- [ ] **Risks + alternatives** listed; alternatives that were rejected include the reason.
- [ ] Track lists tagged per builder role (backend / frontend-web / mobile / ai-ml).

**Evidence:**
- `architecture-plan.md`.
- The Engineering Advisor's one-line effort-tier sign-off in the architect's journal.

**Bounce target on fail:** Back to Stage 2 (Architect re-works) or Stage 1 (back to the Advisor if requirement is now unworkable).

---

## G3 — Development → Security Review

**Owner:** Implementing developer (per-builder gate). All builders tagged in the track list must hit this gate before Stage 4 starts.

**Condition (per builder):**

**Code & effort tier**
- [ ] Effort-tier declaration on every new code path (cheapest sufficient).
- [ ] Per-feature model/LLM token budget set.
- [ ] Idempotency keys cached for all write operations.
- [ ] Schema validation on every API input; server-side re-validation.
- [ ] All timestamps UTC (or an explicit, unambiguous zone) — never ambiguous.
- [ ] Tenant-isolation-key assertion in every service handler.
- [ ] Role check (`requireRole(...)`-equivalent) on every mutation endpoint.
- [ ] Custom metrics + error-tracking instrumentation present.

**Tests (in-lane)**
- [ ] Unit tests for new functions.
- [ ] Integration tests where the change crosses a boundary.
- [ ] **Real-network smoke** ran locally and captured output.
- [ ] Coverage ≥70% on new code in this lane.

**Specifics per lane**
- **Backend:** Keyset/cursor pagination on any new list endpoint. No offset. No sequential queries where a batch/parallel fetch is correct.
- **Frontend (web):** Server-rendered by default where the stack supports it. Performance budget (e.g. Core Web Vitals) checked.
- **Mobile:** Platform UX invariants honored. Secure storage for tokens. Offline behavior tested.
- **AI/ML:** Prompt/result caching applied where possible. Audit-log middleware on any new write tool. A representative run passes locally.

**Evidence:**
- `developer-report.md` per builder.
- Test command outputs captured in journal.
- Handoff signal `READY-FOR-SECURITY` posted.

**Bounce target on fail:** Self (developer reworks). If the failure traces to a plan defect, bounce to Stage 2.

---

## G4 — Security Review → QA

**Owner:** Security Reviewer — **VETO** authority.

**Condition:**
- [ ] **Zero CRITICAL findings.** No exceptions.
- [ ] **Zero HIGH findings.** No exceptions.
- [ ] **Zero violations of the product's compliance regime** (whatever `COMPLIANCE.md` declares — consent, channel/contact rules, retention, residency, etc.).
- [ ] Every mutation endpoint: role check + tenant-membership check + input validation + tenant-isolation-key assertion present and tested.
- [ ] Every new agent/service tool: auth scope + tenant check + audit-log middleware.
- [ ] Every new connector: encrypted-at-rest credentials + webhook signature verification + per-tenant key.
- [ ] Vulnerability scans run (dependency audit, SAST, container scan, etc.). No CRITICAL/HIGH.
- [ ] No PII in logs (sample log lines reviewed).
- [ ] No plaintext credentials/tokens anywhere.

**Evidence:**
- `security-review.md` with gate-by-gate PASS/FAIL + finding evidence.
- Scan output captured in journal.

**Bounce target on fail:** Responsible developer (the finding's owner). The Security Reviewer tags the owning builder role in the bounce note.

**MED / LOW findings:** logged but do not block. Tracked as tech debt in journal.

---

## G5 — QA → Final Review

**Owner:** QA Engineer — **VETO** on missing verification.

**Condition:**
- [ ] All unit tests green.
- [ ] All integration tests green.
- [ ] All contract tests green (breaking-change check, consumer contracts, schema diff).
- [ ] All E2E green (web + mobile, where applicable).
- [ ] Load tests pass (where in scope).
- [ ] **Real-network smoke output captured**. No "should work" — actual output.
- [ ] **Cross-runtime metric parity** confirmed against the single-source metric registry (`METRICS.md`).
- [ ] **Operational-readiness checklist** all green: root handler, health endpoint, port selection, env var validation, native-dep gotchas.
- [ ] Mutation tests pass on **high-stakes paths**: the metric registry, the compliance enforcement code, the system-of-record audit log.
- [ ] Coverage ≥70% on the change set (composite — re-validated post-builder claim).
- [ ] No flaky tests introduced (re-run 3× confirms).

**Evidence:**
- `qa-review.md` with command + output for every claim.
- All test output captured in journal.

**Bounce target on fail:** Responsible developer per finding.

---

## G6 — Final Review → Stakeholder

**Owner:** Engineering Advisor — **VETO** authority.

**Condition:**
- [ ] **Requirement alignment** — does the shipped change still solve the original requirement? (Drift check.)
- [ ] **Effort-tier audit** — every effort-tier declaration matches the declared plan; no expensive tier snuck in where a cheaper one was promised.
- [ ] **Architecture quality** — Single-Primitive Rule held; no anti-pattern drift.
- [ ] **Code quality** — sampled 3–5 files; no obvious smells; comments only where the *why* is non-obvious.
- [ ] **Security review** — Security Reviewer PASS.
- [ ] **QA review** — QA Engineer PASS.
- [ ] **Observability complete** — metrics emitted, dashboards updated, alarms wired.
- [ ] **Cost estimate held** — actual tokens/day from a representative run within ±20% of plan.
- [ ] **Risks acknowledged** — `final-review.md` lists any remaining risks.
- [ ] **Production-readiness assessment** — Platform/SRE pre-deploy checks would pass.
- [ ] **Recommendation to the Stakeholder** — explicit APPROVE / APPROVE-WITH-CAVEATS / REJECT.

**Evidence:**
- `final-review.md`.
- The Advisor's effort-tier audit notes in `cto-advisor.journal.md`.

**Bounce target on fail:** Specific earlier stage (the Advisor chooses based on the failure's root cause — often Stage 2 or Stage 3).

---

## G7 — Stakeholder → Deploy

**Owner:** Stakeholder — **HUMAN GATE**.

**Condition:**
- [ ] Stakeholder ran `/approve <req-id>`.

**Evidence:**
- Audit-log entry: `{"actor": "stakeholder", "decision": "approved", "req_id": "...", "timestamp": "..."}`.

**Bounce target on rejection:** the Advisor reads the rejection reason and re-routes to the appropriate stage.

---

## G8 — Staging → Production

**Owner:** Platform/SRE.

**Condition:**
- [ ] CI green: lint → typecheck → test → build → artifact push.
- [ ] Staging sync succeeded.
- [ ] Staging real-network smoke passed (the QA test scripts re-run on staging).
- [ ] Staging metric parity verified.
- [ ] Dashboard panels render with non-zero data on staging.
- [ ] Alarms wired and verified (synthetic trigger fires the alarm).
- [ ] Rollback plan documented in `deployment-report.md`.

**Evidence:**
- `deployment-report.md` Section "Staging verification".

**Bounce target on fail:** Stage 4 triage (Security/QA/Platform-SRE decide whether it's a code defect, test gap, or infra issue).

---

## G9 — Post-Deploy Monitor (bake window)

**Owner:** Platform/SRE (with auto-rollback automation). Bake-window length comes from the product's `PLAYBOOK-deploy.md`.

**Condition (over the bake window):**
- [ ] p95 latency stays within target.
- [ ] Error rate stays <1%.
- [ ] Health check probes pass.
- [ ] No alarms fired.
- [ ] No auto-rollback triggered.

**Evidence:**
- Monitoring dashboard snapshots across the bake window.
- `deployment-report.md` Section "Post-deploy monitor".

**Bounce target on fail:** Auto-rollback fires → status → `rolled-back` → back to Stage 4 for triage.

---

## How agents check gates

1. **Static check (precondition):** Before declaring "ready," the responsible agent reads this file and self-checks the gate it's about to hand off across.
2. **Reviewer check (postcondition):** The next-stage owner reads this file and verifies each condition against the evidence.
3. **CI check (mechanical, non-LLM — fails the merge before any agent gate runs):**
   - **The OS itself** is gated by `.github/workflows/eos-self-gate.yml` — `pipeline_doctor` (graph consistency), `secret_scan`, `validity_check` (verification-validity anti-patterns), agent-frontmatter + JSON validity, tools-compile. This runs on every plugin PR.
   - **The consuming PRODUCT repo** instantiates its own gate from that template + an effort-tier check (the cheapest-sufficient-effort declaration is present and honest), a test-coverage threshold, the security-scanner suite exit codes, and a contract-diff check. A red gate fails the merge — even before any agent gate runs. *(If the product CI is not yet wired, that is itself a gap to close — do not rely on the agent gates alone for the mechanical checks.)*

> **No gate can be "waived" silently.** If the team needs to ship despite a gate failure, the Engineering Advisor must escalate to the Stakeholder for an explicit, logged waiver — which becomes a tech-debt item with an owner and a date.

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

A weekly digest (run by the `/team-digest` slash command) aggregates from the audit log:
- How often each gate fired (PASS / FAIL ratio).
- Average time spent in each stage.
- Top 5 root causes of bounce-backs.

This data feeds back into making the operating system itself smarter: e.g., if Stage 4 bounces on a missing role check 5+ times in a month, the Architect's Stage 2 checklist gets an explicit "verify the role check on every mutation" item.

---

## Related

- [`engineering-os-blueprint/06-quality-gates-and-metrics.md`](../engineering-os-blueprint/06-quality-gates-and-metrics.md) — overall philosophy & RACI.
- [workflow.md](workflow.md) — stage-by-stage detail.
- [escalation-rules.md](escalation-rules.md) — what to do when a gate fail can't be resolved at this layer.
