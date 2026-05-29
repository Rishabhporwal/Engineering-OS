# Brain Engineering OS — v2 Clean-Room Rebuild Spec

> **Status:** authoritative design contract for the v2 rebuild. Built on branch `eos-v2-cleanroom`, under `v2/`, so v1 stays the live plugin until v2 passes validation (A/B). Promotion = move `v2/*` to repo root + bump `plugin.json`.
>
> **Mandate:** rebuild the team **leaner and cheaper** without changing **what it stands for**. Every core-vision invariant (below) is preserved verbatim. Every change targets *runtime efficiency, model tiering, and de-duplication*.

---

## 0. Why a rebuild (the diagnosis, one screen)

Four parallel subsystem audits + the live-monitoring log (`docs/eos-improvement-observations.md`, O1–O14) converge on **eight root causes**, ranked by leverage:

| # | Root cause | Evidence | v2 fix |
|---|---|---|---|
| 1 | **Full-scope re-review on every bounce** | O12; security/qa agents re-run their entire loop on a 1-char fix; system-prompt §11 *mandates* full re-run | **Delta re-review** (§6) |
| 2 | **Opus on the most-rerun gates** | Security (S4) + final (S6) on Opus; Security's loop is checklist+scanners | **Model tiering** (§7) |
| 3 | **Verification-validity gap** | O11; `BYPASSRLS` green tests, inert probes, tautological tests → late VETO bounces (#1 recurring) | **Negative-control DoD** (§6) |
| 4 | **Eager context loading** | ~10K tokens of skill *descriptions* every turn; builders bulk-load 13–23 skills | **Lazy skill loading + 1-line descriptions** (§4) |
| 5 | **Boilerplate duplication** | system-prompt (300 ln) re-stated 40–55% in each agent; compliance regime in ~6 places | **Single-source + slim agents** (§3, §5) |
| 6 | **Knowledge-layer redundancy** | BLUEPRINT 924 ln (82 real pointers); facts in 4 files; plan template 227 ln × 6 stages | **Real index + single-sourced canon + lean templates** (§8) |
| 7 | **Hot-path `active.json` growth** | O9; read after every spawn; 236 ln/req; never pruned; unbounded `.bak` | **In-flight-only state + registry** (§9) |
| 8 | **Unreliable telemetry** | O14/O13; usage+live.log are best-effort prose, silently stop; program is blind | **Enforced telemetry hook+tool** (§10) |

---

## 1. Core vision — invariants preserved verbatim (DO NOT change)

These are the product's identity. v2 carries every one of them unchanged:

1. **Cost-routed paradigms** — SQL ≫ ML ≫ Haiku ≫ Sonnet; every code path declares `@paradigm`.
2. **Decision Log = the moat** — append-only `ai.decision_log`; a workflow that can't write there is not a Brain action.
3. **India commerce economics** — RTO/COD, GST 2.0 (0/5/18/40), festival lift, pincode reliability, `r*=M/(M+C)`. THE MOAT.
4. **Compliance is P0** — DPDP 2023 + Rules 2025 / TCCCPR-DLT / NCPR-DND / 9am–9pm window / WhatsApp policy / PDPL / India in-region. **Zero violations.** Shreya VETO.
5. **Metric-engine truth** — LLMs never invent numbers; deterministic registry, TS↔Python parity; money in integer minor units + `currency_code`.
6. **Multi-tenant `workspace_id`** — on every row/event/cache-key/log; enforced at 4 layers (JWT → service → RLS/CH-gateway → Kafka).
7. **Morning Brief** = the primary product surface (mobile, 3 ranked actions, Decision-Log write-back).
8. **Anti-blind-agreement / challenge-back** — challenge weak/risky/misaligned requirements, even from the Founder.
9. **Memory is the moat** — git-synced journals + decision-log + semantic recall; agents never forget.
10. **Specialist team + VETO quality gates** — the 11 named personas; Shreya/Tanvi/Rohan vetoes.

> **Rule of the rebuild:** if a change would weaken any invariant above, it is out of scope. v2 changes *how the team runs*, never *what it guards*.

---

## 2. v2 target tree

```
v2/
├── .claude-plugin/plugin.json        # version 1.0.0; components → ./agents ./skills ./hooks
├── prompts/
│   ├── system-prompt.md              # ~120 ln (was 300) — universal rules only, no restatement
│   ├── anti-blind-agreement.md       # kept
│   └── challenge-framework.md        # kept
├── agents/                           # 11 slim files (~50–80 ln each) — ONLY real agents (anything here loads as an agent)
│   ├── cto-advisor.md ... (×11)
├── templates/agent-template.md       # the canonical slim shape (in templates/, NOT agents/)
├── pipeline/                         # NEW — control-flow lives here, not in prompts
│   ├── pipeline.yaml                 # declarative: lanes, stages, routing, model tiers, delta-review rules
│   ├── lane-classifier.md            # the trigger-surface → lane decision table (was buried in cto-advisor)
│   └── orchestrator.md               # the /requirement driver logic (single source)
├── skills/                           # ~50 consolidated skills (was 99) — operational playbooks, 1-line descriptions
│   ├── <command-skills>/             # /requirement /approve /reject /status ... (lazy, explicit)
│   └── <knowledge-skills>/           # loaded by trigger match, never bulk
├── canon/                            # single source of truth — UNCHANGED content, de-duplicated
│   ├── business-requirements.md      # BRD (the one owner of business facts)
│   ├── technical-requirements.md     # TRD
│   ├── TECH/00–18                    # deep dives (the one owner of each technical fact)
│   └── INDEX.md                      # ~80-line REAL pointer index (replaces 924-ln BLUEPRINT)
├── docs/
│   ├── business-context.md           # condensed primer (kept lean, ~89 ln)
│   ├── technical-context.md          # condensed primer (kept lean, ~188 ln)
│   ├── role-empowerment-model.md     # authority/handoff-depth bands
│   ├── quality-gates.md              # gate criteria + bounce conventions
│   ├── finding-severity-rubric.md    # shared Security↔QA must-fix-vs-defer
│   └── (human-only meta-docs archived to docs/_archive/)
├── templates/                        # lean artifact templates (scaled-depth allowed)
├── tools/                            # python tools (kept) + usage_logger.py (NEW, enforced telemetry)
├── hooks/                            # session-start, post-tool-use, careful-guard, + usage-assert (NEW)
└── schemas/                          # state/decision-log/usage schemas (+ active.json schema, NEW)
```

**What disappears vs v1:** the 4th canon layer (BLUEPRINT prose), 99→~50 skills, ~19 human-only docs out of the hot path, per-agent boilerplate, control-flow inside the Opus prompt, orphaned `references/`, the dead `Agent` tool on cto-advisor/architect.

---

## 3. Slim-agent model (root causes 4 & 5)

Every v2 agent file contains **only what is unique to that role**:

```
frontmatter: name, description (1 line), model (tier), primary_skills (1–2), trigger_skills (lazy)
## Mission        — 2–3 lines
## Authority      — can-decide-alone / cannot / VETO
## In-lane DoD    — the checklist that gates handoff
## Anti-blind triggers — what THIS role must challenge
## Journal stub   — one fenced block
```

**Everything else is inherited, not restated:** path conventions, HANDOFF protocol, commit discipline, traceability, compliance regime, journaling, token discipline → **all live once in the system-prompt**. Agents reference by section number, never copy. Target: each builder agent drops from ~120 ln to ~60 ln (~50% cut), most of it previously-duplicated boilerplate.

**Compliance regime stated ONCE** (in `skills/compliance/` + system-prompt principle), referenced everywhere. (Fixes the Single-Primitive violation in a system that preaches it.)

**`primary_skills` (always load, 1–2) vs `trigger_skills` (lazy, load only on task-surface match).** No agent bulk-loads 13–23 skills at session start. Pattern proven by v1's `dynamic-persona-generator` (loads exactly 1 by lookup).

---

## 4. Skill consolidation (root cause 4 & 6): 99 → ~50

**Principle:** skills are **operational playbooks** (how to *do* a thing), not knowledge dumps. Facts live in canon; skills reference canon, never restate it. Every description ≤ ~160 chars (was 600–930).

### Merge map (knowledge-skills)

| v2 skill | Absorbs (v1) | Rationale |
|---|---|---|
| `security-baseline` | security-baseline, defense-in-depth-validation, vulnerability-scanning | one app-sec playbook |
| `agentic-safety` | prompt-injection-defense, agentic-actions-auditor | AI-surface safety |
| `compliance-attestation` | soc2-readiness, pci-compliance-scope, audit-log-immutability | attestation cluster |
| `compliance-engine` | data-privacy-dpdp + the compliance regime (single source) | **the** compliance owner |
| `api-discipline` | api-contract-testing, api-versioning-strategy, api-traffic-patterns | the 3-surface API rules |
| `grpc-buf`, `mcp-protocol`, `backend-fastify-trpc-grpc` | kept (distinct mechanics) | — |
| `data-layer` | database-design, sql-query-optimization | store-agnostic data rules |
| `clickhouse-olap`, `metric-engine`, `data-quality` | kept | distinct + load-bearing |
| `region-and-locale` | region-adapter, data-residency-enforcement, i18n-rtl | the region seam |
| `mobile-surface` | frontend-mobile, mobile-offline-support, push-notification-setup | RN/Expo + morning-brief stays separate |
| `frontend-web`, `morning-brief-mobile` | kept | — |
| `india-commerce-economics`, `cost-routing-paradigms`, `decision-log`, `multi-tenancy-isolation`, `billing-metering`, `lifecycle-revenue-layer`, `agentic-design`, `claude-api`, `llm-gateway`, `llm-evals`, `memory-layer-pgvector`, `forecasting-prophet`, `experimentation-holdouts` | kept (core-vision load-bearing) | — |
| process skills | engineering-discipline, code-review, testing-tdd, systematic-debugging, writing-plans, verification-before-completion, operational-readiness, observability, finishing-a-development-branch, incident-response, idempotency-handling, caching-strategy, integration-connectors, oauth-implementation, auth-and-access, event-driven-kafka, devops-aws, architecture-patterns, domain-driven-design, turborepo, python-services, tech-stack-evaluation, progressive-delivery, version-upgrade-policy, accessibility, web-performance, app-store-deployment, kpi-dashboard-design, subagent-orchestration, task-tracker-integration | kept, descriptions trimmed | — |

**Command-skills (~28):** kept as-is (lazy by design, `disable-model-invocation: true`), descriptions trimmed. NEW: `/decide` (resolve a hard gate + resume — fixes O3).

**Delete:** orphaned `devops-aws/references/` + `security-baseline/references/` (1,384 ln, incl. the ECS file contradicting "EKS not ECS").

Net: ~50 skills, every description 1 line. Saves ~6K tokens off *every* agent turn + removes ~30–40 skill bodies from a typical run.

---

## 5. Lean system-prompt (~120 ln)

Keep, condensed: path conventions (table), the 10 non-negotiable principles (1 line each, link to the owning skill/canon for depth), session-start + token discipline, the HANDOFF protocol (stated ONCE — the canonical home), commit discipline, forbidden behaviors. **Drop:** the long "this supersedes spawn instructions" override paragraph (no longer needed once the dead `Agent` tool is removed from agents), the repeated anti-over-engineering table (→ `engineering-discipline` skill), restated examples. Net ~120 ln (was 300) — the single biggest fixed per-call cost, halved.

---

## 6. Pipeline: delta re-review + verification-validity (root causes 1 & 3)

Control-flow moves into `pipeline/pipeline.yaml` (declarative) + `pipeline/orchestrator.md` (the driver). Agents stop carrying routing logic.

**Delta re-review (the dominant $ lever):** on a BOUNCE, the orchestrator passes the reviewer a `review_scope`:
- `full` — first review of a surface, OR the fix touches a **high-stakes path** (compliance / tenancy / metric-engine / Decision-Log / money / outbound channel).
- `delta` — otherwise: re-verify **only the bounced finding(s) + a diff-vs-last-PASS regression check**. Reviewer reads the prior PASS artifact + the diff, not the whole surface.

System-prompt §11 is relaxed accordingly: *"bounce-fix re-runs the FULL contract only when the fix touches a high-stakes path; else delta-verify the bounced findings + regression diff."* Safety preserved where it matters; cost cut where it doesn't (~halves 2nd-round cost).

**Negative-control DoD (kills #1 recurring bounce, O11):** builder DoD + QA gate now require:
- security/tenancy/auth tests run under the **real (non-`BYPASSRLS`) security context**;
- every probe/test carries a **negative control** — it must *fail when the protection is removed* (proves it exercises the path);
- no tautological parity tests (parity asserted against an independent source of truth, not itself).
"Your verification must be able to fail" is an explicit, gated DoD item.

---

## 7. Model tiering (root cause 2)

Apply the OS's own cost-routing doctrine to itself, declared in `pipeline.yaml`:

| Stage / agent | v1 | v2 | Rationale |
|---|---|---|---|
| S1 cto-advisor intake | opus | **sonnet** for mechanical (lane/dep/persona-count now in classifier); **opus** only for the judgment synthesis | most of S1 is deterministic now |
| S2 architect | opus | **opus** (runs once, deep reasoning) | justified |
| S3 builders | sonnet | **sonnet** | unchanged |
| S4 security | opus | **sonnet** default; **opus escalation** only on CRITICAL/compliance ambiguity | loop is checklist+scanners |
| S5 qa | sonnet | **sonnet** | unchanged |
| S6 final review | opus | **opus** judgment; **delta** re-runs on a cheaper tier | judgment stays Opus, re-verify doesn't |
| personas | sonnet | **haiku** bounded / **sonnet** deep (kept) | already tiered in v1 |
| delta re-review | n/a | **sonnet/haiku** | routine re-verify of a passed surface |

Opus drops from "3 agents on the most-rerun stages" to "deep reasoning only" — the biggest concentrated-cost reduction.

---

## 8. Canon single-sourcing (root cause 6)

- **`canon/INDEX.md`** — a real ~80-line pointer table: topic → `canon/TECH/NN §X`. Replaces the 924-line BLUEPRINT. Agents read the index, open exactly the one `§` they need.
- **Each fact has ONE owner.** CM waterfall, `r*`, RAG bands, GST slabs, the 7-service table → live in their owning `TECH/NN` file only. Primers + skills *reference* them. Edit-once, no drift. (Fixes the quadruple-duplication.)
- **Primers stay** (`business-context` 89 ln, `technical-context` 188 ln) — they condense well and are the per-session reading. Untouched except removing any fact now owned by a TECH file.
- **Lean templates** — `architecture-plan.md` trimmed; scaled-depth rule: small task → short plan (the doc itself flagged 385–769-ln plans for small tasks).

---

## 9. State / memory hot-path (root cause 7)

- `state/active.json` holds **in-flight requirements only**. On terminal (`shipped`/`rejected`/`killed`), the orchestrator prunes the entry → a compact line in `state/registry.json`, detail archived to the run folder.
- `.bak` capped (keep last N) + gitignored; regenerated `dashboard.html` gitignored.
- Add `schemas/active-state.schema.json` (the hot, most-mutated file was unvalidated).
- Concurrency: parallel-builder writes to `active.json` get an advisory lock / orchestrator-serialized merge (was unguarded read-modify-write → clobber risk).
- Semantic index + journals + decision-log: **unchanged** (the moat; carried over wholesale).

---

## 10. Enforced telemetry (root cause 8 — do this FIRST)

The whole optimization is blind without this. Replace best-effort prose with enforcement:

- **`tools/usage_logger.py`** — orchestrator calls it after every spawn with the Agent result's usage; it writes the row (full breakdown when available, total-only otherwise) and returns. One code path, not prose.
- **`hooks/usage-assert`** (PostToolUse / stage boundary) — asserts a usage row exists for the just-completed spawn; a **missing row is a defect** surfaced to `/watch` (like the no-SKIP rule).
- **Backstop reconcile** — `dashboard.py` cross-checks `usage.jsonl` against run-folder artifacts; flags gaps instead of rendering silent zero.
- **`dashboard.py` consumes the breakdown** (input/cache/output), not `total_tokens`-only.
- **`live.log` heartbeat** — `/watch` warns when `live.log` mtime lags `active.json`/`usage.jsonl` (silence ≠ idle).
- **A/B harness** — `tools/ab_bench.py`: run one trivial requirement on v1 vs v2, diff total tokens per stage. The only reliable per-stage measurement given the harness surfaces total-only for subagents.

---

## 11. Build & migration sequence

| Phase | Deliverable | Gate |
|---|---|---|
| **B0** | This spec + branch + skeleton | ✅ done |
| **B1** | Enforced telemetry (`usage_logger.py`, assert hook, A/B harness, dashboard breakdown) | A/B numbers trustworthy |
| **B2** | `pipeline/` (pipeline.yaml, lane-classifier, orchestrator) with delta-review + model tiers + negative-control DoD | `pipeline_doctor` passes on v2 graph |
| **B3** | Lean system-prompt + `_agent-template` + 11 slim agents | agents ≤ target line counts; no boilerplate restatement |
| **B4** | ~50 consolidated skills (1-line descriptions) + delete orphaned references | skill count + description-length check |
| **B5** | `canon/INDEX.md` + single-sourced canon + lean templates | no fact owned by >1 file |
| **B6** | State hot-path (in-flight-only active.json, registry prune, schema, lock) | schema validates |
| **B7** | **Moat migration** — copy `.engineering-os/` (decision-log, journals, semantic index, lessons, durable rules, O1–O14) into v2's consuming-repo contract UNCHANGED | moat intact |
| **B8** | **Validation** — `pipeline_doctor` + A/B identical-task vs v1 + a real high-stakes requirement dry-run | v2 ≤ v1 tokens, same correctness, vision invariants present |
| **B9** | **Promote** — move `v2/*` to root, bump `plugin.json` to 1.0.0, `/plugin update` | Founder sign-off |

**Nothing in v1 is deleted until B8 passes.** v1 remains the live plugin throughout. Promotion is a deliberate, reversible move.

---

## 12. Success criteria

- **Token cost:** measurable reduction on the A/B identical-task bench (target: meaningful cut on bounce-heavy + high-stakes runs, driven by delta-review + Security-off-Opus + lazy skills). Reported with real numbers, not asserted.
- **Reliability:** usage + live.log logging never silently stops (enforced + asserted).
- **Vision:** all 10 invariants (§1) present and exercised in the dry-run.
- **Leanness:** system-prompt ~120 ln; agents ~60 ln; ~50 skills; 1 canon index; no duplicated facts; control-flow out of prompts.
- **Safety:** no destructive change to v1 or the moat until validated; fully reversible.

---

## 13. Research validation & corrections (applied after web/GitHub + Claude Code docs review)

Two parallel research passes (Claude Code official docs + Anthropic engineering posts + industry sources) **validated the core thesis** and forced **two real corrections**:

**Validated:** per-agent + per-invocation model tiering is real and is *Anthropic's own* architecture (Opus-lead + Sonnet-subagents beat single-Opus by 90.2%); `disable-model-invocation: true` truly removes a command skill's description from context (our ~29 command skills are zero always-on cost); subagents genuinely cannot spawn subagents (orchestrator design correct); lazy/just-in-time skill loading is Anthropic's *named* recommended pattern; delta review is sound.

**Correction 1 — skill frontmatter (correctness bug, FIXED).** `primary_skills`/`trigger_skills` are **not real Claude Code fields** — the runtime would ignore them. Fixed all 11 agents to use the real **`skills:`** field (preloads 1–2 always-needed bodies) + a body line for the rest (auto-discovered by description match — the actual lazy mechanism). Also surfaced the real **`effort:`** field (low/high) as a free tiering lever.
  - *Nuance:* skill **descriptions** are bounded by a context budget (~1% of window) with a per-skill cap, not strictly "all always resident" — so the description trim is good but bounded; the bigger always-on win is `disable-model-invocation` on command skills (confirmed zero-cost).

**Correction 2 — prompt caching is fix #0 (NEW, the highest-ROI lever).** Caching cuts 70–90% on repeated calls sharing a prefix; "not optional for agentic systems >3–5 steps." Critically, **"shrink the prompt" conflicts with caching** (caching rewards a *large stable* prefix). Resolution now encoded in `pipeline.yaml §caching`: **stabilize the shared prefix (system-prompt + canon + tool defs, frozen byte-order, no per-run IDs/timestamps), shrink only the variable part, breakpoint on the last shared block, put all dynamic content + lazily-loaded skills AFTER the breakpoint, use the 1-hour TTL.** This is *why* the timestamp-discipline rule (IDs/timestamps appended, never prefixed) matters for cost, and why single-sourced canon helps caching (one stable block) rather than hurting it.

**Delta-review guardrail (FIXED in pipeline.yaml):** delta scope is **diff + relevant slices** (changed code's callers/importers/tests), not diff-only (diff-only "risks missing global interactions"); plus a **regression AUTO-BLOCK** — any test that passed before the bounce and now fails blocks even in delta scope.

**Adopt-next (ranked, not yet built — `pipeline.yaml §adopt_next`):** Batch API (50% off, stacks with caching) for async security/QA sweeps · eval-gated cascades (escalate to Opus only on low confidence) · typed structured handoffs · `effort:` tiering · fork-subagents for cached parallel re-review.
</content>
</invoke>
