# 11 — Runtime & Cost Doctrine

> The OS's roles can be staffed by humans or by AI agents. When they are staffed by AI agents, the OS
> applies its own engineering discipline **to its own operation**: it tiers compute to the task,
> caches aggressively, bounds fan-out, enforces verification validity, and measures its own spend.
> This document is the operating doctrine for the agentic instantiation. (A purely human
> instantiation reads this as "match effort to risk" — the same principle, fewer mechanics.)

---

## 1. Principle: cheapest sufficient effort, always

Every role spends the **least effort that meets the bar** for its task. Effort is matched to risk and
to the kind of reasoning required — not applied uniformly. This mirrors the OS's stance toward the
products it builds ([09](09-reference-architecture.md)): use the cheapest method (a query, a rule, a
small model, a large model) that solves the problem.

A useful ordering of compute cost, cheapest first: **deterministic logic ≪ statistical/ML ≪ small
model ≪ large model**. A role reaches up the ladder only when the rung below cannot meet the bar — and
records why when it does.

---

## 2. Tiering the roles

Capability tiers are abstract so the OS is vendor-neutral; the Canon maps each to a concrete
model/effort. The default mapping:

| Tier | Used for | Why |
|---|---|---|
| **mechanical** | Deterministic classification — lane assignment, dependency detection, persona count, telemetry logging. | No judgment; a rule or the cheapest model. |
| **standard** | The bulk of building, the security checklist + scanner sweep, QA, routine intake framing. | Competent judgment at moderate cost. |
| **deep** | Architecture (runs once per requirement), final go/no-go review, Foundation synthesis, evaluation design, a genuine critical/ambiguous security finding. | Decisions that are expensive to get wrong justify the most capable tier. |
| **delta** | Re-verifying an already-passed surface after a scoped fix. | Bounded scope → a cheaper tier at low effort. |

Two rules keep this honest:

- **Run the expensive tier once, not per bounce.** Architecture and final judgment are the costly
  tiers; structure the pipeline so they are not re-run wholesale on every fix (see delta re-review,
  [06 §4](06-quality-gates-and-metrics.md)).
- **Escalate the tier on a trigger, not on nerves.** A security review escalates to `deep` only on an
  actual critical/compliance ambiguity — not reflexively.

---

## 3. Caching — the highest-ROI lever

A multi-stage, multi-role pipeline calls the same large shared context (the system prompt, the Canon
section, tool definitions) over and over. Caching that shared prefix is the single biggest cost lever
in an agentic instantiation; real systems cut 70–90% of input cost this way.

The doctrine — **stabilize the shared prefix, isolate the variable part after it**:

- **The stable prefix is byte-stable and ordered:** system prompt → tool definitions → the specific
  Canon section the task needs → role boilerplate. Nothing per-run goes here.
- **The cache breakpoint sits on the last shared block** (Canon / tool defs), never on the per-task
  message.
- **Everything dynamic goes after the breakpoint:** the requirement id, run-folder paths, the diff,
  per-task input, and any lazily-loaded skill body. *A lazily-loaded skill that lands inside the
  prefix busts the cache for everything after it* — so variable content is always appended.
- **Forbidden in the prefix:** timestamps, per-run IDs, random values, live state. These bust the
  cache on every spawn (this is *why* IDs and timestamps are appended, never prefixed).
- **Use a long cache TTL** for the shared prefix so a busy multi-role run does not cold-start
  repeatedly.
- **Measure it:** log cache-hit tokens; target a high hit-rate on the long-context stages before
  declaring a caching win.

---

## 4. Bounded fan-out

Parallelism is a tool, not a reflex. Spawning more agents is sometimes right (independent reviews,
parallel builder tracks, diverse stress-test angles) and often wasteful.

- **Persona count is capped (0–2).** More adversaries is rarely more signal.
- **Reviews that are genuinely independent run in parallel** (security ∥ QA); work with dependencies
  runs in sequence.
- **A pipeline-stage pattern, not a swarm.** Each stage plans → executes → self-reviews → verifies →
  hands off. Fan-out happens *within* a stage when the work is genuinely parallel, not as a default.
- **A lane-aware safety bound** caps total spawns per requirement; at the cap the OS **pauses and
  surfaces the full history** so a runaway loop is distinguishable from legitimate large work
  ([03 §8](03-delivery-lifecycle.md)) — it does not hard-stop blindly.

---

## 5. Verification validity (the doctrine that makes cheapness safe)

Cheap effort is only safe if "pass" means something. The verification-validity rules
([06 §3](06-quality-gates-and-metrics.md)) are part of the runtime doctrine precisely because they
are what let the OS run cheaply without shipping false confidence:

- Tests run **under real conditions**, never with protection bypassed.
- Every test has a **negative control** — it fails when its guard is removed.
- Parity is checked against an **independent oracle**, never itself.
- A green test under bypassed protection is a **defect**, not a pass.

Without this, tiering down would trade cost for risk. With it, the cheap tier is cheap *and* trusted.

---

## 6. Telemetry — enforced, not narrated

The OS measures its own operation as rigorously as it measures the products it builds. Telemetry is a
**gate**, not prose:

- **After every spawn,** the orchestrator logs the call's usage, the actual tier/model used, and the
  review scope.
- **Before advancing a stage,** the presence of that telemetry row is asserted — a missing row is a
  *defect* that must be corrected before routing on.
- **A liveness heartbeat** distinguishes "idle" from "stuck": silence is flagged, not assumed to mean
  progress.
- This feeds the efficiency metrics in [06 §5](06-quality-gates-and-metrics.md) — cost per change,
  cache-hit rate, lane distribution — from recorded reality, not self-report.

---

## 7. The cost frontier (adopt-next levers)

Further levers the doctrine reaches for as they prove out, cheapest-impact first:

- **Batch/asynchronous execution** for non-interactive stages (full security/QA sweeps, evaluation
  runs, nightly reports) — stacks with caching for compounding savings.
- **Confidence-gated escalation** — run the cheap tier plus a verifier; escalate to the deep tier
  *only* on low confidence, so even some judgment stages skip the expensive tier per bounce.
- **Typed structured hand-offs** between stages — a bounce carries a structured delta, not
  re-explained prose, killing re-explanation cost.
- **Effort tiering within a tier** — low effort for delta re-review, high effort for architecture.
- **Forked workers that inherit the cached prefix** for parallel re-review — far cheaper than fresh
  spawns.

---

## 8. The doctrine in one sentence

**Spend the least effort that meets the bar, cache everything shared, fan out only when the work is
truly parallel, never trust an unverified pass, and measure your own spend as strictly as you measure
the product** — so the Engineering OS is not only effective but *economical*, at any scale, on any
stack.
