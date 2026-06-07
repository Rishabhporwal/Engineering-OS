---
name: finops-cost
description: Cloud + infrastructure cost as an engineering discipline — the FOCUS spec, OpenCost/Kubecost allocation, tenant/feature cost attribution, cost as an SLO with budgets + alerts, and rightsizing. The infra-cost counterpart to cost-routing-paradigms (model cost). Owner Platform/SRE.
---

# FinOps — Cloud Cost Engineering (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **cloud-cost seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to OpenCost/Kubecost, the cloud's native cost tooling, CloudHealth, or Vantage, normalized via the **FOCUS** spec. The *patterns* — normalized cost data, allocation to tenant/team/feature, cost as a budgeted SLO, and rightsizing — transfer; the tools are examples.

`cost-routing-paradigms` governs **model/inference** cost (the cheapest-sufficient-effort tier). This skill governs the **infrastructure** cost — compute, storage, data transfer, the streaming/OLAP/lakehouse footprint — so a feature's total unit economics (model + infra) are visible. **Owner:** Platform/SRE; the Architect designs for cost; the Stakeholder owns the per-tenant cap. Canon: `STACK.md` + the cost caps in the Product Canon.

## Invariants (NON-NEGOTIABLE)
1. **Cost is allocated, not just totaled.** Every cost maps to a **tenant / team / feature / environment** via mandatory tags + Kubernetes allocation (OpenCost). An unallocatable "miscellaneous 40%" means the tagging is broken — fix it before optimizing.
2. **Normalize to FOCUS.** Use the **FinOps Open Cost & Usage Spec** so multi-cloud/multi-source cost is one schema — comparisons and dashboards don't break per provider.
3. **Cost is an SLO with a budget + alert.** Each service/tenant has a cost budget; crossing a threshold **alerts before** the bill arrives (ties to `ai-observability-tracing`'s per-tenant token cost for the full picture). Surprise bills are an incident-class failure (`incident-response`).
4. **Per-tenant unit economics are known.** Cost-to-serve a tenant (infra + model) is computable, so the per-tenant cost cap (Canon) is enforceable and pricing is grounded. A tenant that costs more than it pays is a flagged exception, not a silent loss.
5. **Rightsizing is continuous, evidence-based.** Idle/over-provisioned resources are surfaced and reclaimed from utilization data — not guessed. Autoscaling (Karpenter — `devops-aws`) + spot/savings-plan strategy are part of the design, not a cleanup afterthought.

## What to instrument
```
Cloud billing (CUR/exports) + K8s allocation (OpenCost) → FOCUS-normalized store
  → allocate by tag: tenant_id, team, feature, env
  → dashboards: cost/tenant/day, cost/feature, unit cost (per request / per active tenant)
  → budgets + anomaly alerts (a sudden 3x is a page, like any SLO breach)
  → rightsizing report: idle, over-provisioned, no-savings-plan
```
Mandatory tags (enforced by `policy-as-code`): `tenant_id`, `team`, `feature`, `env`, `cost-center`. An untagged resource is a CI/admission failure — untagged spend is unmanageable.

## The big infra-cost levers (for this stack)
- **Compute:** autoscale to zero where possible; spot for batch (`batch-processing-spark`); savings plans for steady baseline; rightsize pods (requests/limits from real usage).
- **Storage:** lifecycle raw events to cheap object storage (`lakehouse-iceberg`); compaction + snapshot expiry bound cost; tier cold data.
- **Streaming:** the diskless/S3-direct Kafka model (`event-driven-kafka`) targets exactly the cross-AZ + storage cost that dominates high-volume topics.
- **Data transfer:** cross-AZ/cross-region egress is a silent top cost — keep traffic in-AZ/in-region (also a `region-and-locale` residency win).
- **Caching:** every cache hit (`caching-strategy`) is an OLAP/model call not paid — a cost lever, not just latency.

## Operability + governance
- A lightweight **FinOps review** in the delivery loop: a feature's plan includes an infra-cost estimate (the Architect's cost estimate already covers model tokens — extend it to infra).
- Showback/chargeback per team/tenant makes cost a shared concern, not just the platform team's.
- Don't over-rotate: optimize the top cost drivers (usually compute + egress + storage), not a $5/mo line item. Engineering time has a cost too.

## Anti-patterns
Cost totaled but not allocated (the "miscellaneous 40%") · untagged resources · no per-tenant unit economics (can't enforce the cap or price) · finding out about overspend on the invoice · rightsizing by guesswork · ignoring cross-AZ/region egress · treating FinOps as a quarterly cleanup instead of a continuous budget+alert · optimizing pennies while compute/egress bleed.
