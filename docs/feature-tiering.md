# Feature Tiering — risk-based lanes (Speed & Cost track)

> **Why this exists.** The 8-stage pipeline is correct, but running *every* requirement through all 8 stages, 11 agents, 2 personas, and the full numbered-artifact set is slow and token-heavy. Most work doesn't need it. Tiering routes each requirement into the lightest lane that's still safe. A copy change should not cost the same as a payment integration.
>
> **The principle.** Risk-aware task routing, with the audit trail preserved: the human Stakeholder gate, append-only memory, and the anti-blind-agreement rule survive in every lane. We take the speed, not the loss of control.

---

## The three lanes

The Engineering Advisor assigns `feature_class` at **Stage 1**, before persona count. The lane decides **which stages run**.

| | **Express** | **Standard** | **High-stakes** |
|---|---|---|---|
| **When** | Trivial + zero trigger-surface | Normal feature, no trigger-surface | Touches ≥1 trigger surface |
| **Stages** | 1 → 3 → 5 → 7 → 8 | 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 | 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 |
| **Skips** | Architect (2), Security (4), Final-review (6) | — | — |
| **Personas** | 0 | 0–1 | 2 |
| **Stage 3** | 1 builder | builders as needed | builders as needed |
| **Security VETO** | n/a (skipped) | runs, rarely blocks | **mandatory** |
| **Mutation tests** | no | no | **required** |
| **Artifacts** | 1 combined (`08-express-report.md`) | key artifacts | full numbered set |
| **Top-tier-model stages invoked** | none (only the Advisor's short triage) | Architect + Final-review | Architect + Security + Final-review |

Express skips the three top-tier-model stage owners (Architect, Security, the Advisor's Stage-6 final review), which is where most of the cost lives. The Stakeholder gate (Stage 7) and Stage 8 deploy run in **every** lane — the human gate and the post-deploy monitor are never skipped.

---

## The classifier (how the Advisor decides)

Two ordered tests at Stage 1:

**1. Trigger-surface scan.** Does the requirement touch any of these? (The product's *concrete* high-stakes surfaces + thresholds are declared in its `TRIGGER-SURFACES.md`; the categories below are the generic taxonomy.)

| Trigger surface | Examples |
|---|---|
| `auth` | login, session/token, RBAC, password/OTP |
| `multi-tenancy` | anything reading/writing the tenant-isolation key, row-level isolation, cross-tenant access |
| `tool-contracts` | new/changed agent-facing or service-facing tool, agent-to-agent contract |
| `connectors` | any external-system integration / vendor connector |
| `outbound-channels` | any outbound message/notification channel (call, chat, email, SMS, push, audience export) |
| `pii` | personal data — phone/email/address, account or transaction records |
| `schema-contract` | data-store migration, internal contract/schema change, event-topic change. *(Creating the EMPTY contract HOME — scaffolding config / migration-dir structure / placeholder with **no live consumers, no business logic, no migration on existing data, no runtime** — is foundational structure, NOT a contract change → that is `standard`. A real message/field definition consumed by a service, or a migration touching existing data, stays `high-stakes`.)* |
| `money` | **moving/charging money** — pricing, billing/metering, invoices, refunds, payouts, settlement. *(Computing a money-DERIVED number — e.g. a financial metric over minor-units inputs — is NOT a money trigger; nearly every metric consumes money, so a money-side-effect, not money-math, is what escalates. A new metric helper is `standard`.)* |
| `compliance` | anything the product's `COMPLIANCE.md` regime governs — data-protection, residency, retention, consent, channel/contact rules |

→ **Any hit ⇒ `high-stakes`.** Record the hits in `trigger_surfaces_touched`. Stop.

> **Foundational-scaffolding carve-out (narrow).** When the surfaces touched are **only** structural (`schema-contract` / `multi-tenancy` / `tool-contracts`) **and** they are touched *only* by creating empty homes / toolchain config / directory structure — **no live contract or consumers, no business logic, no migration on existing data, no runtime, and no `money`/`pii`/`outbound-channels`/`connectors`/`compliance` surface** — classify `standard`, not high-stakes. The Architect, **Security, QA, and final-review gates all still run** (they catch the real defects — e.g. a QA gate catching a bad codegen version pin); only the **persona escalation + mutation-test mandate** drop. **On any doubt, stay high-stakes** (the conservative tie-break below is unchanged). This narrows the trigger to *real* contract/behaviour changes; it never lets a live-surface change escape high-stakes.

> **No-code spike / design-only depth modifier.** A *spike* — a research / architecture / planning requirement that produces a design artifact and ships **zero product code** (the Advisor sets the `no-prod-code` guardrail at intake) — stays at its risk-appropriate **lane** (a migration-architecture spike is `high-stakes`), but the **review depth right-sizes to the artifact**: Security + QA review the **design** (soundness; compliance / PII / residency / tenancy / money-handling decisions; whether the plan is concrete + testable) and mark the **code-level machinery N/A** (vuln scans, real-network smoke, contract + mutation tests) — *declared, never silently skipped*, because no code exists yet. This preserves the high-value design + compliance vetting (where a spike's review earns its keep) while removing full code-review depth from an artifact that has no code. Full depth returns on the actual build slices. (Implemented in `agents/security-reviewer.md` + `agents/qa-agent.md` change-class scope.)

**2. Triviality test** (only if zero trigger surfaces). Is the change purely: copy/content · docs · config tweak · dependency bump · styling · refactor with zero behavior change · a clear repeat of a lessons-registry pattern?

→ **Yes ⇒ `express`. No ⇒ `standard`.**

### The conservative tie-break (non-negotiable)

> On **any** doubt between two lanes, pick the **higher-rigor** lane.

A high-stakes change misclassified as express is a production incident. An express change misclassified as standard just costs a few extra agent passes. The asymmetry is the whole point. Never downgrade to express on ambiguity.

---

## What gets recorded

The Advisor writes a **"Lane decision"** section in `02-cto-advisor-review.md` and sets three fields on the requirement entry in `state/active.json`:

- `feature_class` — `express` | `standard` | `high-stakes`
- `feature_class_rationale` — one line: which rule fired + any surfaces
- `trigger_surfaces_touched` — array (must be empty for express)

See [schemas/requirement.schema.json](../schemas/requirement.schema.json) and the `lanes:` block in [workflows/requirement-to-release.yaml](../workflows/requirement-to-release.yaml).

---

## Model routing (Lever 2)

The lane determines model spend *indirectly* — by deciding which agents run. Per-agent model tier (set in each agent's frontmatter):

| Model tier | Agents | Rationale |
|---|---|---|
| **Top tier** | Architect, Engineering Advisor, Security Reviewer | Deep reasoning, VETO authority, hardest trade-offs |
| **Mid tier** | All builders (Backend/Frontend/Mobile/AI-ML), QA, Platform/SRE, Delivery Coordinator, persona generator | Real implementation + review work |
| **Small tier** | *(reserved for the background workers)* | Bounded, scheduled scans |

Because Express skips the Architect, Security, and the Advisor's Stage-6 final review, **an Express feature never invokes a top-tier-model stage** beyond the Advisor's short Stage-1 triage. That is the cost win, made structural rather than hoped-for.

> **Optional further saving (not yet applied):** the Delivery Coordinator is pure coordination/sync/release-notes and could move to a smaller tier. Left on the mid tier for now to protect stakeholder-facing release-note quality. Flip if cost pressure rises.

---

## Express lane — end-to-end flow

```
/requirement "fix typo on the KPI card subtitle"
   │
   ▼ Stage 1  Advisor: trigger-scan → none. triviality → copy. feature_class=express. 0 personas.
   │          Records Lane decision. Invokes ONE builder directly (skips the Architect).
   ▼ Stage 3  Frontend Engineer: minimal edit + real-network smoke. Writes 08-express-report.md.
   │          Invokes QA directly (skips Security).
   ▼ Stage 5  QA: smoke + lint + minimal secrets-grep. PASS.
   │          Sets awaiting-founder (skips the Advisor's Stage 6).
   ▼ Stage 7  Stakeholder: /approve
   ▼ Stage 8  Platform/SRE: deploy + post-deploy monitor.
```

Five agent touches instead of ten-plus. No top-tier-model stage beyond a short triage. Same audit trail (journals + audit log + run folder), same human gate, same deploy safety.

---

## Guardrails (so speed never costs safety)

1. **The conservative tie-break** routes ambiguity *up*, never down.
2. **Trigger surfaces force high-stakes mechanically** — they can't be argued away into express.
3. **QA still re-runs a minimal Stage 4 secrets-grep on express** (inherited from the existing "Security skipped" protocol) — so even the skipped-Security lane has a thin safety net.
4. **The Stakeholder gate (Stage 7) and post-deploy monitor (Stage 8) run in every lane.**
5. **Anything that bounces** (a builder discovers a trigger surface mid-build) re-routes the requirement to the correct higher lane — the Advisor re-classifies; the express path is abandoned.

---

## Artifact levels (Lever 5 — lean artifacts)

The numbered run-folder artifacts are partly audit record, partly ceremony. The journal + audit log are the *durable* record and are written in **every** lane. The numbered files scale with the lane:

| Artifact | Express | Standard | High-stakes |
|---|:---:|:---:|:---:|
| `01-requirement.md` | ✅ | ✅ | ✅ |
| `02-cto-advisor-review.md` | stub¹ | lean | full |
| `03/04-persona-*.md` | — | 0–1 | 2 |
| `06-architecture-plan.md` | — | ✅ | ✅ |
| `07-handoff-to-developer.md` | — | fold into 06² | ✅ separate |
| `08-developer-report-*.md` | `08-express-report.md` (1 combined) | per builder | per builder |
| `09-security-review.md` | — | ✅ | ✅ |
| `10-qa-review.md` | brief (smoke) | ✅ | ✅ |
| `11-final-review.md` | — | lean | full |
| `12-founder-decision.json` | ✅ | ✅ | ✅ |
| `13-deployment-report.md` | ✅ | ✅ | ✅ |
| `14-retro.md` | — | terse | full |

*(Artifact filenames retain their canonical `cto-advisor` / `founder` tokens to match the run-folder schema; they denote the Engineering-Advisor and Stakeholder roles respectively.)*

¹ Express `02` is a short stub: the Lane decision + ADVANCE, not the full template.
² Standard folds the handoff into the architecture plan (no separate `07`); high-stakes keeps `07` separate at calibrated depth.

**Terseness directive (all lanes):** artifacts state *decisions + evidence*, not prose. Don't restate the template's prompts; cite file paths and captured command output; don't narrate the pipeline. A reviewable artifact is short and dense.

---

## Parallel review (Lever 4 — Security ∥ QA)

For **standard** and **high-stakes**, the Security Reviewer and QA Engineer review the same staged code and don't mutate it — so they run **concurrently**, not in sequence. The **builder** is the single reconciliation owner:

```
builder (Stage 3 done)
   │  ── ONE message, TWO Agent calls (PARALLEL REVIEW MODE) ──
   ├──▶ security-reviewer  → returns SECURITY: PASS|BOUNCE  (writes 09)
   └──▶ qa-agent           → returns QA: PASS|FAIL          (writes 10)
   │
   ▼ builder reconciles
   both PASS ──▶ final-reviewer (Stage 6)
   either fails ──▶ fix all findings, restage, re-run parallel review
```

In `PARALLEL REVIEW MODE`, Security and QA **return their verdict and do NOT advance** — only the builder invokes the next stage. That single-owner rule is what prevents a double-invoke of Stage 6. Express never parallelizes (it skips Security entirely → builder → QA → Stakeholder).

> **Verification note:** Lever 4 changes multi-agent orchestration, which can only be exercised by a real subagent run (not a unit test). Run one standard-lane `/requirement` end-to-end and confirm exactly one Stage-6 invocation before relying on it at volume.

---

## What this does NOT change

- The full 8-stage pipeline is still the path for standard and high-stakes work.
- Memory, audit log, journals, run folders — identical in every lane.
- VETO authority (Security, QA, the Engineering Advisor) is unchanged where those stages run.
- The anti-blind-agreement rule applies in every lane.

Tiering removes *ceremony for trivial work*. It removes nothing from the work that actually carries risk.
