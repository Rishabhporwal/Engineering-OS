---
name: llm-evals
description: The ship gate for any prompt/model/RAG/agent change — golden-set, faithfulness/groundedness, RAG recall@k, agent-step; three-point CI gate, ship only if ≥ baseline.
---

# LLM Evals — the gate behind every LLM surface

Cost-routing keeps the LLM footprint small, but the few surfaces that *are* LLM are load-bearing: a synthesis/summary surface, conversational query, anomaly explanation, classification, and template personalisation. A prompt tweak or model bump can silently regress quality. **Evals are how a prompt/model change earns the right to ship.** No eval, no merge.

> **The faithfulness gap this skill closes.** "Models never invent numbers" is enforced *structurally* — every metric comes from the registry (deterministic), never from a model ([`metric-engine`](../metric-engine/SKILL.md), [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)). That stops the model *computing* a wrong number. It does **not** stop a narration step *describing* the right numbers unfaithfully — e.g. the metric fell but the summary says "it held." **Faithfulness/groundedness evals gate exactly that.**

**Canonical doc:** the Product Canon's intelligence section (`STACK.md`, the synthesis/agent surfaces) + the defining-surface SLOs in `TRIGGER-SURFACES.md`. Owner: **AI/ML Engineer**. **The QA Engineer gates at Stage 5** (a prompt/model PR with no eval ≥ baseline is a QA VETO).

## The four eval families

| Family | What it scores | Surfaces it gates | Effort tier of the *scorer* |
|---|---|---|---|
| **1. Golden-set + regression** | output vs a frozen, human-curated reference set | every LLM surface | exact/structural match = deterministic; LLM-as-judge = a small model |
| **2. Faithfulness / groundedness** | does the prose contradict the deterministic numbers / audit log? | synthesis, anomaly explanation, conversational replies | claim-extraction + numeric check (deterministic) + LLM-judge (small model) |
| **3. RAG eval** | recall@k + context-groundedness of retrieved context | anything that retrieves context (memory / policy / docs) | recall@k = deterministic; groundedness = small-model judge |
| **4. Agent-step eval** | tool-call correctness, arg validity, plan adherence | tool-using agents' loops | schema check (deterministic) + trajectory diff |

**Scorers obey the same cost gate as everything else** ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)): prefer deterministic checks over an LLM judge; reach for an LLM judge only for genuinely fuzzy quality (tone, helpfulness). LLM-judge scores are themselves evaluated against human labels so the judge doesn't drift.

## 1. Golden-set + regression evals

A **golden set** is a frozen, versioned table of `(input_snapshot, expected_output, rubric)` per surface, curated from real (PII-redacted, tenant-stripped) production cases — including the hard ones: an edge-case day, a stale-data input, an empty/zero result, a spike. Store in the repo (`evals/golden/<surface>/`), version it, and **never edit a case to make a failing model pass** (that's gaming the gate). On any prompt/model change, replay the whole set and compare to the **baseline** for the currently-shipped version. **Ship only if every metric ≥ baseline** within tolerance.

## 2. Faithfulness / groundedness (the synthesis gate)

A synthesis model receives deterministic signals (the computed numbers) and writes prose. Faithfulness eval verifies the prose is **entailed by** those inputs and the audit-log rows it summarises ([`decision-log`](../decision-log/SKILL.md)):

```python
# claim extraction by a small model; the numeric check is deterministic
async def faithfulness_score(text, signals, audit_rows) -> FaithfulnessReport:
    claims = extract_claims(text)                    # numeric + directional claims
    numeric = check_numbers_match(claims, signals)   # deterministic: every figure must equal a registry value
    grounded = judge_entailment(claims, signals, audit_rows)  # small-model judge: each claim entailed?
    return FaithfulnessReport(unsupported=[c for c in claims if not numeric or not grounded])
```

Hard rules the prose must pass: **(a)** every number equals a metric-registry value (no fabricated/rounded-wrong figures), **(b)** every directional claim matches the sign of the deterministic delta, **(c)** every action/impact claim maps to a real audit-log row, **(d)** no recommendation outside the agents' actual `proposed_action` set. Any unsupported claim **fails the gate** — synthesis is high-stakes, so this set also gets mutation-tested ([`testing-tdd`](../testing-tdd/SKILL.md)).

## 3. RAG eval (retrieval quality)

When agents retrieve context (similar past conditions, relevant policy/docs) before reasoning, score two things, both tenant-scoped:

- **recall@k** — of the known-relevant items for a labelled query, how many appear in the top-k? Catches a broken embedding/index before it starves an agent of context.
- **context-groundedness** — is the answer supported by the retrieved context (vs parametric memory)? Plus a **no-context-leak** check: retrieval must never surface another tenant's rows (cross-tenant leak = P0; [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)).

## 4. Agent-step evals

For tool-using agents, the *trajectory* matters as much as the final text:

- **Tool-call correctness** — right tool for the intent, args validate against the contract-generated schema ([`mcp-protocol`](../mcp-protocol/SKILL.md)), the cost-tier annotation present.
- **Plan adherence** — the agent followed its declared plan; no skipped freshness/consent/policy check; no tool fired before the audit-log `proposed` row exists.
- **Guardrail honouring** — never proposes an action above its confidence threshold or outside policy. Overlaps the pre-execution audit ([`agentic-safety`](../agentic-safety/SKILL.md)): evals catch it *offline against the golden set*; the auditor catches it *at run time*.

## The three-point release gate (ship only if eval ≥ baseline)

Same eval suite, three points — a change must clear **all three**:

```
1. Offline golden-set  — run locally; full golden set; ≥ baseline before opening the PR
2. Pre-merge CI        — CI replays the golden set on the diff; fails the build on any regression
                         (also a cost-tier + faithfulness gate — the QA Stage-5 VETO surface)
3. Online prod sampling— sample N live outputs/day, score faithfulness + groundedness async
                         (a batch/off-peak path, off the latency path); dashboard + alert on drift below baseline
```

Online sampling is the safety net for distribution shift the golden set didn't cover; a sustained dip pages the owner and can trigger rollback. **Never** put the eval scorer on the latency path of a defining surface's synthesis — that risks its SLO. Score asynchronously.

## Per-tier model-swap gate (the model-agnostic gateway world)

When LLM calls route through a **model-agnostic gateway** ([`llm-gateway`](../llm-gateway/SKILL.md)), a cost tier names a **routed policy tier**, and the gateway routes each call to the cheapest model that **passes that tier's eval bar**. The eval suite is therefore the **production gate for which models may serve a tier**:

- **No model serves a tier in production until it passes that tier's eval suite.** Adding a model to the small tier, or swapping the frontier-tier default, requires a full golden-set + faithfulness + agent-step pass ≥ baseline. A model wired into a routing policy with no eval pass is a blocker.
- **Re-baseline on any routed-model version bump.** A bump of *any* routable model invalidates that tier's baseline — replay before it serves traffic. Re-confirm cost + latency (per-tenant cap + any defining-surface budget) and prompt-cache hit rate.
- **Keep a known-good model in the fallback chain** so a **failed swap degrades to a known-good model**, never to "no answer".
- Each tier's default being what it is should be **eval-justified, not assumed** — the gate is what makes "right model on cost" enforceable.

## Model-migration policy (provider EOL / upgrade)

Migration is an **evidence-gated ADR**, coordinated with [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) (deliberate, cadenced — never a reactive same-day swap), the routing policy in [`llm-gateway`](../llm-gateway/SKILL.md), and any provider-specific pins ([`claude-api`](../claude-api/SKILL.md)):

1. **Re-baseline** the golden set on the new model.
2. **A/B old-vs-new** on online prod sampling — faithfulness, groundedness, agent-step, human spot-check.
3. **Cost + latency re-check** — must hold the per-tenant cap and any defining-surface budget; re-confirm prompt-cache hit rate.
4. **Rollback plan** — keep the old model pinned and one flag-flip away until the new one beats baseline on the live sample for a defined window.
5. **Audit log + ADR** — record the migration decision and its eval evidence.

## Tooling + eval-driven development (2026)

Eval-driven development is now standard practice, not optional — a CI quality gate **plus** a platform for human annotation + regression dashboards:

- **The trace store is the substrate.** Online sampling (point 3) and the golden set both read from the **OpenTelemetry GenAI** spans captured by [`ai-observability-tracing`](../ai-observability-tracing/SKILL.md) — a failing eval links straight to the offending trace. Instrument once (OTel `gen_ai.*`), swap the backend freely.
- **Named reference tooling** (bind in `STACK.md`): **DeepEval / Ragas / promptfoo** for the CI scorers (pytest-integrated, RAG metrics, red-teaming); **Langfuse / Arize Phoenix** as the OTLP eval/annotation backend. All are examples of the seam — the patterns here transfer.
- **Multi-step agents → `agent-evaluation`.** This skill's "agent-step eval" family is the entry point; deep **trajectory / tool-call / multi-turn** evaluation of durable agents lives in [`agent-evaluation`](../agent-evaluation/SKILL.md). RAG recall@k tuning lives in [`rag-retrieval`](../rag-retrieval/SKILL.md). This skill remains the gate for prompt/model/single-shot RAG changes.
- **Every production failure becomes a golden case** — the suite grows from real incidents, not only curated examples.

## Anti-patterns (code-review / Stage-5 blockers)

- Prompt or model change merged with **no eval run** or a score **below baseline** → blocker.
- **Editing a golden case to make a failing model pass** → gaming the gate; blocker.
- **Faithfulness eval skipped** on a synthesis/explanation change → unfaithful prose can ship even though every number is "real."
- **LLM judge with no human-label calibration** → the judge silently drifts.
- Eval scorer **on a defining surface's latency path** → SLO risk; score async.
- Model swapped **without re-baselining + A/B + cost/latency re-check** → silent regression.
- A model **wired into a gateway routing tier with no eval pass at that tier** → an unproven model serves production traffic; blocker.

## References

- Product Canon intelligence section — the synthesis/agent surfaces and their windows
- `TRIGGER-SURFACES.md` — defining-surface SLOs
- [`llm-gateway`](../llm-gateway/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`claude-api`](../claude-api/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) · [`metric-engine`](../metric-engine/SKILL.md) · [`agentic-safety`](../agentic-safety/SKILL.md)
