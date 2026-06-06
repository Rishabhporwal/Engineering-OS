# Engineering OS — Roadmap

> This roadmap is the **framework's own evolution** — how the Engineering OS itself gets better at taking any requirement from intake to production, on any stack, for any product. It is *not* a product, business, or domain roadmap (that belongs in a consuming repo's Product Canon). Items are marked **Built** (shipped and enforced today) or **Proposed** (research-backed, not yet built). The "adopt-next" ideas are drawn from [`pipeline/pipeline.yaml`](pipeline/pipeline.yaml) `§adopt_next` and [`engineering-os-blueprint/11-runtime-and-cost-doctrine.md`](engineering-os-blueprint/11-runtime-and-cost-doctrine.md) `§7`.

---

## Design rule for this roadmap

The OS changes **almost never**; the Product Canon changes per product. So every item here must make the *organization* better without baking in any domain. If a proposal needs a business assumption, it belongs in a Canon, not here. We also hold ourselves to the OS's own doctrine: ship the minimum that meets the bar, prove a lever binds on real telemetry before declaring a win, and prefer the next real problem from a real run over a speculative feature.

---

## 1. Pipeline & lanes

**Built**
- Risk-based lanes (lean / express / standard / high-stakes) that scale rigor to risk; ambiguity routes *up* (conservative tie-break).
- Deterministic lane classifier (`tools/classify_lane.py`) — a model miss can't strip Security off a trigger-surface change.
- Post-build reclassification gate — re-scans the actual staged diff against the intake surfaces; a change that grows into a trigger surface mid-build is upgraded (express → high-stakes) automatically.
- Experimental `--lean` one-session lane + the lean-vs-full A/B harness.

**Proposed**
- **Broaden lane A/B validation** — settle lean-vs-full with live runs across more requirement shapes, not just trivial ones; promote the winning default per surface class.
- **Confidence-gated tier escalation** — run the cheap model + a confidence/verifier check, and escalate to the deep tier *only* on low confidence, so even some judgment stages skip the expensive tier per bounce (the eval-gated cascade; FrugalGPT-style savings).
- **Batch / async stages** — run non-interactive stages (full security/QA sweeps, eval runs, nightly reports) on the Batch path; stacks with prompt-caching for a large unit-cost reduction.

## 2. Hand-offs & orchestration

**Built**
- `HANDOFF`-block protocol — every stage plans → executes → self-reviews → verifies → returns a structured handoff; the top-level orchestrator is the sole writer of `state/active.json` (atomic `os.replace`), killing the parallel-builder lost-update race.
- Crash-recoverable orchestrator (`tools/orchestrator_cursor.py`) — in-flight plan persisted; `/resume` rebuilds the scheduler.
- Hook-enforced spawn telemetry + heartbeat — every spawn return recorded deterministically; `/watch` surfaces a STALE banner.

**Proposed**
- **Typed structured hand-offs** — a bounce carries a structured delta (machine-readable) rather than re-explained prose, cutting retries and re-explanation between stages.
- **Per-stage effort tiering** — bind the runtime effort level per role (e.g. delta-reviewer low, architect high) instead of one tier per model.
- **Forked subagents for parallel re-review** — inherit the parent's cached prefix for cheaper fan-out re-reviews than fresh spawns.

## 3. Quality gates & verification

**Built**
- VETO gates as deterministic tools (`tools/gate_check.py`) — fail-closed; can't advance past an open CRITICAL/HIGH or a non-PASS review, even on a Stakeholder "approve".
- Verification-validity gate (`tools/validity_check.py`) — negative-control schema field; rejects tests that pass under security-bypass, inert probes, or tautological parity.
- Full prior-passing suite re-run on every bounce-fix (decoupled from delta scope) so regression auto-block can actually fire.
- CI self-gate — the OS gates itself (pipeline_doctor, secret_scan, validity_check, cache_lint, knowledge_lint, agent-frontmatter).

**Proposed**
- **Richer engineering-KPI gates** — wire more of the engineering metrics in [`engineering-os-blueprint/06-quality-gates-and-metrics.md`](engineering-os-blueprint/06-quality-gates-and-metrics.md) (delta re-review coverage, escape rate, gate-fire ledger) into the dashboard and the self-gate.
- **Mutation-testing as a standard high-stakes gate** across more reference-stack bindings.

## 4. Reference-stack bindings (seam adapters)

**Built**
- Stack-agnostic reference architecture ([`engineering-os-blueprint/09-reference-architecture.md`](engineering-os-blueprint/09-reference-architecture.md)) + reference-implementation skills (one concrete binding per seam: backend, data store, async backbone, frontend, mobile, model gateway, infra, region/locale).
- `STACK.md` in the Product Canon binds each seam per adoption.

**Proposed**
- **More reference-stack bindings** — additional adapters per seam (e.g. alternate languages/runtimes, message buses, datastores, model providers) so a new adoption finds a closer starting binding.
- **Seam conformance checks** — a per-seam contract that any binding must satisfy, so swapping a binding is mechanically verifiable.

## 5. Cost & runtime doctrine

**Built**
- Cheapest-sufficient-effort routing (deterministic ≫ statistical/ML ≫ small model ≫ large model) applied to the OS's own operation; per-path cost-routing gate.
- Model-tier split (standard intake / deep final review) — the headline cost lever.
- Prompt-caching discipline (cache-stable-first spawn prefixes) + `tools/cache_lint.py`; cache-hit % surfaced in the dashboard.

**Proposed**
- **Batch API + cascade compounding** — combine batch, caching, and the confidence-gated cascade for the largest unit-cost reduction on non-interactive work.
- **Spend telemetry → automatic tier feedback** — let observed per-stage cost and pass-rate tune lane/tier defaults over time.

## 6. Governance & the learning loop

**Built**
- Rule governance — any agent `/propose-rule`; the Stakeholder `/adopt-rule` / `/reject-rule`; adopted rules indexed in `.engineering-os/durable-rules/INDEX.md` and read by every agent at session start.
- Retro → `lessons-learned.md` → read at every intake (the compounding learning loop).
- Knowledge-drift lint (`tools/knowledge_lint.py`) — self-enforces the single-source claim.

**Proposed**
- **Richer governance cadence** — a periodic, structured review of durable rules, tech-radar movement, and version/dependency policy (see [`engineering-os-blueprint/08-technical-governance.md`](engineering-os-blueprint/08-technical-governance.md)), with stale-rule retirement.
- **Cross-adoption lesson sharing** — an opt-in mechanism to lift domain-free lessons from one adoption into the OS's own defaults.
- **Incident pipeline** as a first-class vertical alongside the feature pipeline (`/incident` → triage → mitigate → resolve → blameless postmortem → lessons-learned).

## 7. Integrations & DX

**Built**
- Tool-agnostic task-tracker integration (opt-in per env var; falls back to a pending log).
- Live observability commands (`/watch`, `/monitor`, `/dashboard`) + the cost/risk decision card on `/approve`.
- Real-browser + visual QA (`/qa-browser`, `/design-review`).

**Proposed**
- **Gate-transition notifications** (opt-in: Slack/Discord/email at awaiting-Stakeholder, rollback, digest).
- **Stakeholder approval out-of-band** (approve/reject without CLI access).
- **Weekly digest** aggregating the audit log: features shipped, gates fired, time-in-stage, top bounce causes.

---

## How we decide what's next

1. **Bind the cost levers live first.** Confirm the model-tier split and caching wins hold on real telemetry before adding more.
2. **Then: run → observe → fix.** The next real problem from a real run is worth more than any speculative feature.
3. **Domain-free or it doesn't ship here.** Anything that needs a business assumption goes in a Product Canon, never in the OS.

## Where to start

- New teammate: read [README.md](README.md), then [`engineering-os-blueprint/`](engineering-os-blueprint/) in order, then run `/status`.
- New role owner: read [agents/](agents/) for your role.
- New skill author: copy a similar skill folder under `skills/`, then update [docs/skill-mapping-matrix.md](docs/skill-mapping-matrix.md) and the owning agent's owned-skill list.
- Framework contributor: read [`engineering-os-blueprint/11-runtime-and-cost-doctrine.md`](engineering-os-blueprint/11-runtime-and-cost-doctrine.md) and [`pipeline/pipeline.yaml`](pipeline/pipeline.yaml), then this roadmap.
</content>
