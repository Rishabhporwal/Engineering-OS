---
name: dynamic-persona-spawning
description: The discipline for choosing and inhabiting the 0–2 Stage-1 stress-test personas — count by intersecting risk dimensions, type by surface, depth tier by stakes, ≥1 concrete concern each, and how the Advisor weighs the inputs. Owner dynamic-persona-generator + Engineering Advisor.
---

# Dynamic Persona Spawning (Stage-1 Stress-Test Discipline)

Personas exist to surface the concern the standing team would miss — **not** to add ceremony. This skill governs both sides: the **Engineering Advisor** (who decides the count + types; the orchestrator spawns) and the **persona agent** (who must inhabit one lens honestly).

## Count rule (hard cap: 2)
| Count | When |
|---|---|
| **0** | Pure docs, zero-behavior refactor, config tweak, clear repeat of a pattern in memory. Don't pay for theater. |
| **1** | ONE risk dimension dominates (compliance-only, cost-only, scale-only, parity-only). |
| **2** | Two **distinct, intersecting** risk dimensions (cost × compliance, parity × interface-stability). |
| 3+ | **Never.** Needing 3 means the requirement is too broad → bounce for decomposition (`requirement-intake`). |

Rationale (validated by the multi-agent failure literature): extra agents multiply tokens 7–15× and add conflicting implicit decisions; bounded, read-only personas contribute *intelligence* without becoming parallel *writers*. Personas read and judge — they never edit.

## Type selection (match the lens to the surface)
Pick from the catalog (`docs/role-empowerment-model.md §2`): `security-stress-tester` (PII/auth/tenancy/payments) · `compliance-officer` (regime in `COMPLIANCE.md`) · `ai-cost-realist` (new model calls) · `scalability-architect` (10× load / new data shape) · `data-quality-skeptic` (metric correctness) · `ops-on-call` (new failure modes) · `economic-skeptic` (cost vs payback) · `regional-expansion-officer` · `partner-integration` · `enterprise-buyer` · `customer-success` · `competitive-analyst` · `engineering-debt-realist` · `business-strategist` · `product-marketing`.

**Depth tier per persona:** tag `:haiku` (mechanical — bounded checklist lens) or `:sonnet` (standard — open-ended reasoning lens). Pay the standard tier only when the lens genuinely needs reasoning, not enumeration (`cost-routing-paradigms`).

## Inhabiting the persona (the agent side)
1. Read the Advisor's intake summary + the ONE persona type assigned. Read the one skill your lens anchors on (e.g. `compliance-officer` → `compliance-engine`; `ai-cost-realist` → `cost-routing-paradigms`).
2. Stay in-lens: you are not a general reviewer; surface what THIS persona would fight for.
3. **Produce ≥1 concrete, falsifiable concern** with: the risk, the evidence/trigger, severity, and a proposed mitigation. "Looks good, no concerns" = you failed the job and the Advisor must reject your review.
4. Write `templates/dynamic-persona-review.md`; you advise — you have **no veto** and no edit rights.

## Synthesis (the Advisor side)
Weigh persona inputs as **signals, not votes**: a concern is adopted if it names a real trigger surface, cost, or invariant — not because a persona said it forcefully. Fold adopted concerns into the intake review as must-address items for the Architect; record rejected concerns with one line of why (the audit trail of roads not taken).

## Anti-patterns
Spawning 2 personas on a no-risk change (theater) · 3+ personas instead of decomposing · a persona reviewing everything instead of its lens · "no concerns" returns · treating persona output as a veto · paying the standard tier for a checklist lens · personas editing artifacts (they read + judge only).
