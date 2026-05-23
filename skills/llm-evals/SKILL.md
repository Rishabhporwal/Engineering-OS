---
name: llm-evals
description: Brain's eval discipline for every LLM surface — the gate that lets a prompt or model change ship. Golden-set + regression evals; faithfulness/groundedness scoring (the 07:15 Sonnet Morning Brief synthesis must NEVER contradict the deterministic numbers — "LLMs never invent numbers" stops metric *hallucination* structurally, but NOT synthesis *un*faithfulness, which this gates); RAG eval (recall@k + context-groundedness over Brand Fingerprint / Decision-Log retrieval); agent-step evals (tool-call correctness, plan adherence) for the 15 AICMO/AICOO/AICFO agents; the three-point CI release gate (offline golden-set → pre-merge CI → online prod sampling, ship only if eval ≥ baseline); the model-migration policy on Anthropic EOL/upgrade. Owner Maya; Tanvi gates at Stage 5. Use when changing any prompt, model, RAG retriever, or agent tool-set.
---

# LLM Evals — the gate behind Brain's LLM surfaces

Brain's cost-routing keeps the LLM footprint tiny (target 0.5% Sonnet / 2.5% Haiku), but the few surfaces that *are* LLM are load-bearing: the **07:15 IST Morning Brief synthesis** (Sonnet 4.6 — the product's defining surface), AI Chat, anomaly explanation, ticket classification (Haiku 4.5), and template personalisation. A prompt tweak or an Anthropic model bump can silently regress quality. **Evals are how a prompt/model change earns the right to ship.** No eval, no merge.

> **The faithfulness gap this skill closes.** The Iron Rule "LLMs never invent numbers" is enforced *structurally*: every metric comes from the registry (SQL paradigm), never from a model — see [`metric-engine`](../metric-engine/SKILL.md), [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md). That stops the LLM from *computing* a wrong number. It does **not** stop the synthesis step from *narrating* the right numbers unfaithfully — e.g. the deterministic CM2 fell but the Brief says "margin held," or it claims a courier switch "recovered ₹X" the Decision Log never recorded. **Faithfulness/groundedness evals gate exactly that.**

**Canonical doc:** `canon/TECH/05_intelligence_layer.md` (synthesis, daily tick) + `canon/technical-requirements.md` §14 (SLOs). Owner: **Maya** (intelligence-service). **Tanvi gates at Stage 5** (a prompt/model PR with no eval ≥ baseline is a QA VETO).

## The four eval families

| Family | What it scores | Surfaces it gates | Paradigm of the *scorer* |
|---|---|---|---|
| **1. Golden-set + regression** | output vs a frozen, human-curated reference set | every LLM surface | exact/structural match = SQL; LLM-as-judge = Haiku |
| **2. Faithfulness / groundedness** | does the prose contradict the deterministic numbers / Decision Log? | Morning Brief synthesis, anomaly explanation, AI Chat, ticket replies | claim-extraction + numeric check (SQL) + LLM-judge (Haiku) |
| **3. RAG eval** | recall@k + context-groundedness of retrieved context | anything that retrieves Brand Fingerprint / Decision-Log / policy | recall@k = SQL; groundedness = Haiku judge |
| **4. Agent-step eval** | tool-call correctness, arg validity, plan adherence | the 15 product agents' tool-use loops | schema check (SQL) + trajectory diff |

**Scorers obey the same cost gate as everything else** ([`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)): prefer deterministic checks (exact-match, JSON-schema, numeric-equality) over an LLM judge; reach for a Haiku judge only for genuinely fuzzy quality (tone, helpfulness). LLM-judge scores are themselves evaluated against human labels so the judge doesn't drift.

## 1. Golden-set + regression evals

A **golden set** is a frozen, versioned table of `(input_snapshot, expected_output, rubric)` per surface, curated by Maya from real (PII-redacted, `workspace_id`-stripped) production cases — including the hard ones: a margin-trap day, a stale-connector morning, a zero-action day, a festival spike. Store in the repo (`evals/golden/<surface>/`), version it, and **never edit a case to make a failing model pass** (that's gaming the gate). On any prompt/model change, replay the whole set and compare to the **baseline** score recorded for the currently-shipped version. **Ship only if every metric ≥ baseline** (regression guard) within tolerance.

## 2. Faithfulness / groundedness (the Morning Brief gate)

The synthesis Sonnet receives ML/SQL outputs (the deterministic signals) and writes prose. Faithfulness eval verifies the prose is **entailed by** those inputs and the `ai.decision_log` rows it summarises:

```python
@paradigm("small_llm", model="claude-haiku-4-5")  # claim extraction; numeric check is pure SQL
async def faithfulness_score(brief_text, signals, decision_rows) -> FaithfulnessReport:
    claims = extract_claims(brief_text)              # numeric + directional claims
    numeric = check_numbers_match(claims, signals)   # SQL: every ₹/% must equal a registry value
    grounded = judge_entailment(claims, signals, decision_rows)  # Haiku: each claim entailed?
    return FaithfulnessReport(unsupported=[c for c in claims if not numeric or not grounded])
```

Hard rules a brief must pass: **(a)** every number it states equals a metric-registry value (no fabricated/rounded-wrong figures), **(b)** every directional claim ("CM2 improved") matches the sign of the deterministic delta, **(c)** every recovered-revenue / action claim maps to a real Decision-Log row, **(d)** no recommendation outside the agents' actual `proposed_action` set. Any unsupported claim **fails the gate** — synthesis is high-stakes, so this set also gets mutation-tested (see [`testing-tdd`](../testing-tdd/SKILL.md)).

## 3. RAG eval (Brand Fingerprint + Decision-Log retrieval)

Agents retrieve the 5 most-similar past conditions (pgvector cosine on the 16-dim Brand Fingerprint) and relevant Decision-Log/policy context before reasoning ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md), [`decision-log`](../decision-log/SKILL.md)). Two metrics, both `workspace_id`-scoped:

- **recall@k** — of the known-relevant past conditions for a labelled query, how many appear in the top-k? Catches a broken embedding/index before it starves an agent of context.
- **context-groundedness** — is the answer actually supported by the retrieved context (vs the model's parametric memory)? Plus a **no-context-leak** check: retrieval must never surface another brand's rows (cross-brand leak = P0; see [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)).

## 4. Agent-step evals (the 15 AICMO/AICOO/AICFO agents)

For tool-using agents, the *trajectory* matters as much as the final text:

- **Tool-call correctness** — right MCP tool for the intent, args validate against the proto-generated schema (schemas can't drift — [`mcp-protocol`](../mcp-protocol/SKILL.md)), `@paradigm`/`@mcp_tool` present.
- **Plan adherence** — the agent followed its declared plan; no skipped freshness/consent/policy check; no tool fired before the Decision-Log `proposed` row exists.
- **Guardrail honouring** — never proposes an action above its confidence threshold or outside calling hours/consent. Overlaps the pre-execution [`agentic-actions-auditor`](../agentic-actions-auditor/SKILL.md): evals catch it *offline against the golden set*; the auditor catches it *at run time*.

## The three-point release gate (ship only if eval ≥ baseline)

Same eval suite, three points — a prompt/model/retriever/tool-set change must clear **all three**:

```
1. Offline golden-set  — Maya runs locally; full golden set; must be ≥ baseline before opening the PR
2. Pre-merge CI        — CI replays the golden set on the diff; fails the build on any regression
                         (this is also a @paradigm + faithfulness gate — Tanvi's Stage-5 VETO surface)
3. Online prod sampling— sample N live briefs/chats/day, score faithfulness + groundedness async
                         (Batch API, 50% off, non-latency-path); dashboard + alert on drift below baseline
```

Online sampling is the safety net for distribution shift the golden set didn't cover; a sustained dip pages Maya and can trigger a rollback. **Never** put the eval scorer on the latency path of the 07:15 synthesis itself — that risks the **07:20 IST / 99.5%** SLO. Score asynchronously.

## Per-tier model-swap gate (the model-agnostic gateway world)

Brain routes LLM calls through a **model-agnostic LiteLLM gateway** ([`llm-gateway`](../llm-gateway/SKILL.md)): `@paradigm("small_llm"|"frontier_llm")` names a **routed policy tier**, and the gateway routes each call to the cheapest model that **passes that tier's eval bar**. The eval suite is therefore the **production gate for which models may serve a tier**:

- **No model serves a paradigm tier in production until it passes that tier's eval suite.** Adding **Amazon Nova Micro / Gemini 2.5 Flash-Lite** to `small_llm`, or swapping the `frontier_llm` default off **Claude Sonnet 4.6**, requires a full golden-set + faithfulness + agent-step pass at that tier ≥ baseline. A model wired into a routing policy with no eval pass is a blocker.
- **Re-baseline on any routed-model version bump.** A version bump of *any* model the gateway can route to (Nova, Gemini, Haiku, Sonnet, Opus) invalidates that tier's baseline — replay the suite before the new version serves traffic. Re-confirm cost + latency (the tier's per-brand cap + the **07:20 IST synthesis budget**) and prompt-cache hit rate on the Claude path.
- **Claude stays the frontier fallback.** Keep Claude Sonnet 4.6 pinned in the `frontier_llm` fallback chain so a **failed swap degrades to a known-good model**, never to "no answer" — the gateway advances down the chain on a regression or stall (protecting the Morning Brief SLO).
- The frontier default being Claude is itself **eval-justified, not assumed** — it keeps the default only while it clears the bar at its cost; the gate is what makes "model-agnostic = right model on cost, not avoid Claude" enforceable.

## Model-migration policy (Anthropic EOL / upgrade)

Models are pinned to canon (Sonnet 4.6 the frontier default, Haiku 4.5 a small-tier fallback). When a provider ships a successor or announces an EOL for a routed model, migration is an **evidence-gated ADR**, coordinated with [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) (this is a deliberate, cadenced change — never a reactive same-day swap), the routing policy in [`llm-gateway`](../llm-gateway/SKILL.md), and the model pins in [`claude-api`](../claude-api/SKILL.md):

1. **Re-baseline** the golden set on the new model (a model bump invalidates the old baseline).
2. **A/B old-vs-new** on online prod sampling — faithfulness, groundedness, agent-step, human spot-check.
3. **Cost + latency re-check** — new model must hold the per-brand LLM cap and the 07:20 synthesis budget; re-confirm prompt-cache hit rate (the biggest lever).
4. **Rollback plan** — keep the old model pinned and one flag-flip away until the new one beats baseline on the live sample for a defined window.
5. **Decision Log + ADR** — record the migration decision and its eval evidence.

## Anti-patterns (code-review / Stage-5 blockers)

- Prompt or model change merged with **no eval run** or a score **below baseline** → blocker.
- **Editing a golden case to make a failing model pass** → gaming the gate; blocker.
- **Faithfulness eval skipped** on a synthesis/explanation change → an unfaithful Brief can ship even though every number is "real."
- **LLM judge with no human-label calibration** → the judge silently drifts.
- Eval scorer **on the 07:15 latency path** → SLO risk; score async.
- Model swapped **without re-baselining + A/B + cost/latency re-check** → silent regression.
- A model **wired into a gateway routing tier with no eval pass at that tier** → an unproven model serves production traffic; blocker (see the per-tier model-swap gate above).

## References

- `canon/TECH/05_intelligence_layer.md` — daily tick, Sonnet synthesis, the 06:55→07:15 window
- `canon/technical-requirements.md` §14 — Morning Brief 07:20 IST >99.5% SLO
- [`llm-gateway`](../llm-gateway/SKILL.md) · [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md) · [`claude-api`](../claude-api/SKILL.md) · [`agentic-design`](../agentic-design/SKILL.md) · [`decision-log`](../decision-log/SKILL.md) · [`version-upgrade-policy`](../version-upgrade-policy/SKILL.md) · [`metric-engine`](../metric-engine/SKILL.md) · [`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md) · [`agentic-actions-auditor`](../agentic-actions-auditor/SKILL.md)
