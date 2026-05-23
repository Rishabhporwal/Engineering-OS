# Feature Tiering — risk-based lanes (Speed & Cost track)

> **Why this exists.** The 8-stage pipeline is correct, but running *every* requirement through all 8 stages, 11 agents, 2 personas, and the full numbered-artifact set is slow and token-heavy. Most work doesn't need it. Tiering routes each requirement into the lightest lane that's still safe. A copy change should not cost the same as a payment integration.
>
> **Source of the idea.** Borrowed from ruflo's risk-aware task routing, adapted to keep Brain's audit moat: the human Founder gate, append-only memory, and the anti-blind-agreement rule survive in every lane. We took the speed, not the loss of control.

---

## The three lanes

Rohan (CTO Advisor) assigns `feature_class` at **Stage 1**, before persona count. The lane decides **which stages run**.

| | **Express** | **Standard** | **High-stakes** |
|---|---|---|---|
| **When** | Trivial + zero trigger-surface | Normal feature, no trigger-surface | Touches ≥1 trigger surface |
| **Stages** | 1 → 3 → 5 → 7 → 8 | 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 | 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 |
| **Skips** | Architect (2), Security (4), Final-review (6) | — | — |
| **Personas** | 0 | 0–1 | 2 |
| **Stage 3** | 1 builder | builders as needed | builders as needed |
| **Mutation tests** | no | no | **required** |
| **Shreya VETO** | n/a (skipped) | runs, rarely blocks | **mandatory** |
| **Artifacts** | 1 combined (`08-express-report.md`) | key artifacts | full numbered set |
| **Opus-heavy stages invoked** | none (only Rohan's short triage) | Architect + Final-review | Architect + Security + Final-review |

Express skips the three Opus-stage owners (Aryan, Shreya, Rohan-Stage-6), which is where most of the cost lives. The Founder gate (Stage 7) and Stage 8 deploy run in **every** lane — the human gate and the 48h monitor are never skipped.

---

## The classifier (how Rohan decides)

Two ordered tests at Stage 1:

**1. Trigger-surface scan.** Does the requirement touch any of these?

| Trigger surface | Examples |
|---|---|
| `auth` | login, JWT, session, RBAC, password/OTP |
| `multi-tenancy` | anything reading/writing `workspace_id`, RLS, cross-brand |
| `mcp-tools` | new/changed MCP tool, agent-to-agent contract |
| `connectors` | Shopify, Meta, Google, Shiprocket, Klaviyo, TikTok, Snap |
| `outbound-channels` | call, WhatsApp, email, SMS, ad-audience push |
| `pii` | customer phone/email/address, order data |
| `schema-proto` | Postgres/ClickHouse migration, `.proto` change, Kafka topic |
| `money` | **moving/charging money** — pricing, billing/metering, GMV-% fee, invoices, refunds, payouts, settlement. *(Computing a money-DERIVED number — e.g. a CM/RTO/break-even metric over minor-units inputs — is NOT a money trigger; nearly every metric consumes money, so a money-side-effect, not money-math, is what escalates. A new metric helper is `standard`.)* |
| `india-compliance` | DPDP / UAE-KSA PDPL data-protection; DLT, NCPR, DND, calling hours (9am–9pm), recording consent; WhatsApp opt-in/template approval; GST per-SKU; India in-region data residency |

→ **Any hit ⇒ `high-stakes`.** Record the hits in `trigger_surfaces_touched`. Stop.

**2. Triviality test** (only if zero trigger surfaces). Is the change purely: copy/content · docs · config tweak · dependency bump · styling · refactor with zero behavior change · a clear repeat of a lessons-registry pattern?

→ **Yes ⇒ `express`. No ⇒ `standard`.**

### The conservative tie-break (non-negotiable)

> On **any** doubt between two lanes, pick the **higher-rigor** lane.

A high-stakes change misclassified as express is a production incident. An express change misclassified as standard just costs a few extra agent passes. The asymmetry is the whole point. Never downgrade to express on ambiguity. This is a Founder rule (2026-05-20).

---

## What gets recorded

Rohan writes a **"Lane decision"** section in `02-cto-advisor-review.md` and sets three fields on the requirement entry in `state/active.json`:

- `feature_class` — `express` | `standard` | `high-stakes`
- `feature_class_rationale` — one line: which rule fired + any surfaces
- `trigger_surfaces_touched` — array (must be empty for express)

See [schemas/requirement.schema.json](../schemas/requirement.schema.json) and the `lanes:` block in [workflows/requirement-to-release.yaml](../workflows/requirement-to-release.yaml).

---

## Model routing (Lever 2)

The lane determines model spend *indirectly* — by deciding which agents run. Per-agent model assignments (already set in each agent's frontmatter):

| Model | Agents | Rationale |
|---|---|---|
| **Opus** | Architect (Aryan), CTO Advisor (Rohan), Security (Shreya) | Deep reasoning, VETO authority, hardest trade-offs |
| **Sonnet** | All builders (Vikram/Ananya/Karan/Maya), QA (Tanvi), DevOps (Jatin), PM (Priya), persona generator | Real implementation + review work |
| **Haiku** | *(reserved for the background workers — Track C)* | Bounded, scheduled scans |

Because Express skips Aryan, Shreya, and Rohan-Stage-6, **an Express feature never invokes an Opus stage** beyond Rohan's short Stage-1 triage. That is the cost win, made structural rather than hoped-for.

> **Optional further saving (not yet applied):** Priya (PM) is pure coordination/sync/release-notes and could move to Haiku. Left on Sonnet for now to protect Founder-facing release-note quality. Flip if cost pressure rises.

---

## Express lane — end-to-end flow

```
/requirement "fix typo on the KPI card subtitle"
   │
   ▼ Stage 1  Rohan: trigger-scan → none. triviality → copy. feature_class=express. 0 personas.
   │          Records Lane decision. Invokes ONE builder directly (skips Aryan).
   ▼ Stage 3  Ananya: minimal edit + real-network smoke. Writes 08-express-report.md.
   │          Invokes Tanvi directly (skips Shreya).
   ▼ Stage 5  Tanvi: smoke + lint + minimal secrets-grep. PASS.
   │          Sets awaiting-founder (skips Rohan Stage 6).
   ▼ Stage 7  Founder: /approve
   ▼ Stage 8  Jatin: deploy + 48h monitor.
```

Five agent touches instead of ten-plus. No Opus stage beyond a short triage. Same audit trail (journals + decision log + run folder), same human gate, same deploy safety.

---

## Guardrails (so speed never costs safety)

1. **The conservative tie-break** routes ambiguity *up*, never down.
2. **Trigger surfaces force high-stakes mechanically** — they can't be argued away into express.
3. **Tanvi still re-runs a minimal Stage 4 secrets-grep on express** (inherited from the existing "Security skipped" protocol) — so even the skipped-Security lane has a thin safety net.
4. **The Founder gate (Stage 7) and 48h monitor (Stage 8) run in every lane.**
5. **Anything that bounces** (a builder discovers a trigger surface mid-build) re-routes the requirement to the correct higher lane — Rohan re-classifies; the express path is abandoned.

---

## Artifact levels (Lever 5 — lean artifacts)

The numbered run-folder artifacts are partly audit record, partly ceremony. The journal + decision log are the *durable* record and are written in **every** lane. The numbered files scale with the lane:

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

¹ Express `02` is a short stub: the Lane decision + ADVANCE, not the full template.
² Standard folds the handoff into the architecture plan (no separate `07`); high-stakes keeps `07` separate at calibrated depth.

**Terseness directive (all lanes):** artifacts state *decisions + evidence*, not prose. Don't restate the template's prompts; cite file paths and captured command output; don't narrate the pipeline. A reviewable artifact is short and dense.

---

## Parallel review (Lever 4 — Security ∥ QA)

For **standard** and **high-stakes**, Security (Shreya) and QA (Tanvi) review the same staged code and don't mutate it — so they run **concurrently**, not in sequence. The **builder** is the single reconciliation owner:

```
builder (Stage 3 done)
   │  ── ONE message, TWO Agent calls (PARALLEL REVIEW MODE) ──
   ├──▶ security-reviewer  → returns SECURITY: PASS|BOUNCE  (writes 09)
   └──▶ qa-agent           → returns QA: PASS|FAIL          (writes 10)
   │
   ▼ builder reconciles
   both PASS ──▶ cto-advisor (Stage 6)
   either fails ──▶ fix all findings, restage, re-run parallel review
```

In `PARALLEL REVIEW MODE`, Shreya and Tanvi **return their verdict and do NOT advance** — only the builder invokes the next stage. That single-owner rule is what prevents a double-invoke of Stage 6. Express never parallelizes (it skips Security entirely → builder → Tanvi → Founder).

> **Verification note:** Lever 4 changes multi-agent orchestration, which can only be exercised by a real subagent run (not a unit test). Run one standard-lane `/requirement` end-to-end and confirm exactly one Stage-6 invocation before relying on it at volume.

---

## What this does NOT change

- The full 8-stage pipeline is still the path for standard and high-stakes work.
- Memory, decision log, journals, run folders — identical in every lane.
- VETO authority (Shreya, Tanvi, Rohan) is unchanged where those stages run.
- The anti-blind-agreement rule applies in every lane.

Tiering removes *ceremony for trivial work*. It removes nothing from the work that actually carries risk.
