# Changelog — Engineering OS

## 2.0.0 — Generalized to a universal, domain-agnostic Engineering OS

The OS was lifted out of its original product binding and turned into a **universal,
domain-agnostic AI engineering organization** that takes any requirement from intake to
production, on any stack, for any product. No business, product, or domain knowledge remains
in the OS itself.

### The two-layer split
- **The Engineering OS** (this plugin) — roles, pipeline, standards, gates, governance —
  is now stable, reusable, and domain-free.
- **The Product Canon** (per adoption) — the *thing being built*: requirements, chosen
  stack, architecture, compliance regime, invariants, metrics, the moat — is supplied **once**
  in a **Foundation phase** and lives in the consuming repo's `.engineering-os/knowledge-base/`.

### What changed
- **Roles, not personas.** The roster is now defined by role (Engineering Advisor, Architect,
  Backend / Frontend-Web / Mobile / AI-ML Engineer, Security Reviewer, QA Engineer, Platform/SRE,
  Delivery Coordinator, the stress-test persona, + the Stakeholder human). Human/team names are
  optional and assigned per adoption in `team-roster.md`.
- **Product Canon template.** A new canon template (`canon/`, indexed by `canon/INDEX.md`)
  describes the per-adoption slots: `STACK.md`, `HLD/LLD`, `INVARIANTS.md`, `TRIGGER-SURFACES.md`,
  `COMPLIANCE.md`, `METRICS.md`, `PLAYBOOK-*.md`, `ESCALATION-RUBRIC.md`, `THE-MOAT.md`.
- **The framework, as docs.** The full organization — first principles, structure, roles,
  delivery lifecycle, standards, quality gates, operations, governance, the stack-agnostic
  reference architecture, the adoption guide, and the runtime/cost doctrine — is documented in
  `engineering-os-blueprint/`.
- **Standards & pipeline are domain-free.** Tenant isolation is a generic isolation key
  (declared in the Canon); compliance is whatever `COMPLIANCE.md` declares; money is integer
  minor units + a `currency_code`; metrics come from a single-source registry (`METRICS.md`)
  with cross-runtime parity; cost routing is "cheapest sufficient effort" (deterministic ≫
  statistical/ML ≫ small model ≫ large model). The OS supplies the enforcement machinery; the
  Canon supplies the specifics.
- **Reference-implementation skills.** Stack-specific skills are reframed as one concrete
  binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`); the patterns
  transfer, the vendor is just the example. Skills that were product features were archived.
- **Original instantiation archived.** The original product binding — its Canon and
  product-specific skills — now lives under `examples/` as a fully-worked reference instantiation,
  so you can see what "filled in" looks like.
- **Namespace** is `engineering-os:` (commands invoke as `/engineering-os:<name>`).

---

> **Versions < 2.0.0 targeted a specific product instantiation (now under `examples/`).** The
> entries below are retained for history; their product/persona/domain specifics no longer
> describe the OS itself — they describe the original adoption. See git history for the full
> detail.

## 1.1.0 — Enforcement hardening (the 10-persona review)

A 10-expert adversarial review of the v1.0.0 clean-room rebuild found one systemic
flaw: **the design was excellent but the enforcement was prose** — nearly every
load-bearing guarantee (secrets, telemetry, state integrity, VETO, verification-validity,
lane classification, the spawn cap) depended on the model *remembering*. This release
moves every one of them **onto a hook, schema, or tool that fires regardless of model
behavior**, and makes the orchestrator crash-recoverable.

### Security
- **Secret guard actually fixed.** `hooks/on-secret-guard.sh` (PreToolUse Write|Edit) **blocks**
  any write containing a live secret value *before disk* — covering the classes that actually
  leaked (OAuth client secrets, provider access/personal-access tokens, long-lived API tokens,
  connection-string passwords). `tools/secret_scan.py` gates the `.engineering-os/` commit;
  `.gitleaks.toml` for the team. (v1.0.0's "fix" caught none of these and only sanitized its
  own journal line.)
- **Non-LLM VETO** (`tools/gate_check.py`): structurally refuses to advance to the Stakeholder
  gate / deploy on any unresolved CRITICAL/HIGH or non-PASS review — fail-closed. A model
  can no longer route past a VETO; a Stakeholder "approve" can't ship past an open CRITICAL.
- **Build-team prompt-injection defense:** the team's reads (legacy code, web, requirement
  text) are now treated as untrusted data; the deterministic gates hold regardless of what
  an injection makes an agent *say*.

### Reliability & telemetry
- **Hook-enforced heartbeat** (`hooks/on-subagent-usage.sh` + `tools/heartbeat_check.py`):
  every spawn return is recorded deterministically; `/watch` surfaces a STALE banner and
  reconciles spawns-vs-usage — silent stops are now *detectable*, not invisible.
- **Orchestrator is now crash-recoverable** (`tools/orchestrator_cursor.py`): its in-flight
  plan (outstanding spawns, count, last route) is persisted; `/resume` rebuilds the scheduler.
- **Orchestrator is the sole writer of `active.json`** (`tools/state_update.py`, atomic
  `os.replace`): kills the parallel-builder lost-update race; recovers from a corrupt live file.

### Quality
- **Verification-validity is now falsifiable:** `negative_control[]` schema field +
  `tools/validity_check.py` (catches security-bypass/superuser/tautology; rejects an empty
  control on high-stakes paths). The #1 recurring bounce has a mechanical gate.
- **Test suite decoupled from delta scope:** every bounce-fix re-runs the full prior-passing
  suite (cheap CI) so `regression_auto_block` can actually fire.
- **Learning loop closed:** adopted `durable-rules/INDEX.md` is read at session start.
- **CI self-gate** (`.github/workflows/eos-self-gate.yml`): pipeline_doctor, secret_scan,
  validity_check, cache_lint, knowledge_lint, agent-frontmatter — the OS gates itself.

### Cost
- **Advisor agent split** → standard-tier intake + deep-tier final review: the
  #1 unrealized lever. **Projected cost reduction on real telemetry** (`tools/ab_project.py`,
  surfaced in the dashboard's tier-headroom KPI).
- **Deterministic lane classifier** (`tools/classify_lane.py`): a model miss can no longer
  strip Security off a trigger-surface change.
- **Prompt-caching discipline:** cache-stable-first spawn prompts + `tools/cache_lint.py`.
- **Lane-aware pause-and-confirm spawn cap** (was a flat-20 footgun).
- **Experimental `lean` lane** + the lean-vs-full A/B (still pending a live run).

### DX & knowledge
- `/approve` renders a **cost/risk decision card** (was a rubber stamp).
- Onboarding fixed: dead doc links, `/eos init`→`/eos-init`, the restart-to-apply rule, the
  recovery commands (`/decide`, `/resume`, `/handoff`).
- Knowledge drift fixed + `tools/knowledge_lint.py` self-enforces the single-source claim.
- Skill-loading prose made mechanism-true (no more "auto-discovered" fiction).

### Still open (needs a live run — operator-side)
1. Confirm the projected cost reduction binds live (dashboard headroom → ~0 after restart).
2. Settle lean-vs-full (`/requirement` vs `/requirement --lean` on trivial reqs).
3. **Then: run → observe → fix.** The next real problem from a real run is worth more than
   any speculative feature. (Deliberately NOT built: Batch API — doesn't apply to interactive
   orchestration; eval-gated cascade — marginal until a run shows final-review cost is a problem.)

---

## 1.0.0 — Clean-room rebuild (promoted from v0.26.0)

Leaner runtime, same vision. Control-flow extracted from the deep-tier prompt into `pipeline/`;
delta re-review; model tiering; lazy skill loading; single-sourced canon (`canon/INDEX.md`
replaced the 924-line blueprint); enforced telemetry foundation. Static footprint cuts:
system-prompt 300→87 ln, always-on skill descriptions ~10k→2.6k tokens, 99→88 skills.
Prior runtime recoverable via tag `v1-0.26.0-archive`.
</content>
