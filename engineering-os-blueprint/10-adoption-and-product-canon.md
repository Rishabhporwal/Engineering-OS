# 10 — Adoption & the Product Canon

> How to instantiate the OS for a real product. The OS carries no domain knowledge; a product is made
> concrete through the **Foundation phase**, which produces the **Product Canon** — the
> `knowledge-base/` every role reads. This document is the template and the procedure.

---

## 1. The principle: the OS is empty until grounded

Everything domain-specific lives in the Product Canon, never in the OS:

| The OS supplies (fixed) | The Canon supplies (per product) |
|---|---|
| Roles, pipeline, lanes, gates, governance | What is being built (requirements) |
| Standards' *intents* | The chosen stack (seam bindings) |
| Trigger-surface *categories* | The specific trigger surfaces & thresholds |
| Compliance *machinery* | The actual regulatory regime |
| Metric *definitions of health* | The product's own metrics & invariants |
| The escalation *rubric structure* | The escalation thresholds |

Adopting the OS = **running the Foundation once** to fill the right column, then filing requirements.

---

## 2. The Foundation phase (one-time, gates everything)

```
 Stakeholder supplies:           Foundation team (Advisor + Architect) produces:
   • Requirements (the BRD)   ──▶   the Product Canon (knowledge-base/)
   • Constraints (the TRD)    ──▶   reconciled, coherent, internally consistent
                                ──▶ Stakeholder approves ──▶ sentinel written ──▶ pipeline unlocks
```

### 2.1 Trigger

The stakeholder kicks off Foundation and supplies two raw inputs:

- **A requirements document** — what the product must do, end to end. May be rough, incomplete, or
  contradictory.
- **A technical-constraints document** — known constraints, preferences, regulatory context, scale
  expectations. Also raw.

### 2.2 Flow

1. **Ingest & interrogate.** The Architect and Engineering Advisor read both inputs and build a
   gap/contradiction list. Research is permitted (it is a planning phase).
2. **Reconcile with the stakeholder.** Open contradictions and gaps are surfaced — batched and
   decision-shaped, not a stream of questions — and the answers fold back in.
3. **Stress-test.** 0–2 personas pressure-test the foundation from product-derived risk angles; each
   surfaces ≥1 concern; concerns are resolved into the Canon.
4. **Synthesize the Canon.** The team authors the `knowledge-base/` (§3) — stack, design, playbooks,
   invariants, the escalation rubric, the moat, the trigger surfaces.
5. **Approve & gate.** The Canon is presented; the stakeholder approves it; an approval **sentinel**
   is written to the repo. The recurring pipeline unlocks.

The Foundation runs **once per product**, and again only on an explicit **Foundation amendment**
(a change to an invariant or a foundational decision — [08 §7](08-technical-governance.md)).

---

## 3. The Product Canon template (`knowledge-base/`)

The minimum contents. Names are conventions; the *slots* are what matter. Each slot is the
product-specific answer to a fixed OS question.

| Canon artifact | The OS question it answers |
|---|---|
| **`STACK.md`** | Which technology binds each seam ([09 §2](09-reference-architecture.md)), and why (ADRs). |
| **`HLD.md` / `LLD-*.md`** | The high- and low-level design — bounded contexts, contracts, data model. |
| **`INVARIANTS.md`** | The non-negotiables: rules that must always hold (the "never" list). |
| **`TRIGGER-SURFACES.md`** | The product's concrete high-stakes surfaces + thresholds ([03 §3](03-delivery-lifecycle.md)). |
| **`COMPLIANCE.md`** | The regulatory regime to enforce (jurisdictions, controls, data rules). |
| **`METRICS.md`** | The product's source-of-truth metric/contract definitions (the single-definition registry). |
| **`PLAYBOOK-deploy.md`** | Rollout strategy, bake window, rollback thresholds ([07](07-operations-and-reliability.md)). |
| **`PLAYBOOK-incident.md`** | The severity ladder, paging, kill switches. |
| **`ESCALATION-RUBRIC.md`** | When a role must escalate to the stakeholder ([01 §5](01-organization-structure.md)). |
| **`THE-MOAT.md`** | The asset that compounds and must be protected (what the product's durability rests on). |
| **`team-roster.md`** | Optional human/team identities attached to the OS roles. |

> **A Canon slot left empty is a known gap, stated as such** — never silently treated as "no
> constraint." An empty `COMPLIANCE.md` means "no regulatory regime applies," recorded explicitly, not
> omitted.

---

## 4. The adoption checklist

```
[ ] 1. Place the OS where roles can read it (the framework) and create the repo's .engineering-os/.
[ ] 2. Run the Foundation phase: supply requirements + constraints.
[ ] 3. Reconcile gaps/contradictions with the stakeholder.
[ ] 4. Bind every needed seam in STACK.md (ADR each non-trivial choice).
[ ] 5. Declare INVARIANTS, TRIGGER-SURFACES, COMPLIANCE, METRICS.
[ ] 6. Write the deploy + incident PLAYBOOKs and the ESCALATION-RUBRIC.
[ ] 7. Approve the Canon → sentinel written → pipeline unlocked.
[ ] 8. File the first requirement. The OS delivers it end-to-end and records everything.
[ ] 9. Memory (.engineering-os/) is committed to git — it is the moat, never ignored.
```

---

## 5. Worked instantiation pattern (how a domain maps in)

The mapping is mechanical — every product fills the *same slots* with *different content*. Three
illustrative product types, same OS:

| Canon slot | A SaaS web app | A data platform | A mobile-first consumer app |
|---|---|---|---|
| Stack (seams) | Web + API + OLTP + cache + auth | Ingestion + OLAP + object store + orchestrator | Mobile + BFF + OLTP + push |
| Trigger surfaces | Auth, tenancy, billing | Data contracts, PII, lineage | Auth, payments, store policy |
| Compliance | The applicable data-protection regime | Data-residency + retention | App-store + data-protection |
| Moat | Customer data + workflow lock-in | Data quality + lineage trust | Engagement + offline UX |
| Metrics registry | Usage/billing definitions | Freshness/quality SLAs | Engagement/retention defs |

In every case the **roles, pipeline, lanes, gates, and governance are identical**. Only the Canon
differs. That invariance is the proof the OS is universal.

---

## 6. The state the OS creates in the consuming repo

After adoption, the consuming repo contains the memory layout from
[01 §6](01-organization-structure.md): the approved Canon, the lessons-learned log, the pending
attention queue, and a per-requirement working set + state. This directory is **committed to git** so
the organization's memory survives every pull, every teammate, and every run — it is the compounding
asset the OS exists to grow.

---

## 7. Re-adoption and portability

Because the OS holds no product state, the same OS framework serves any number of products
simultaneously — each with its own Canon in its own repo. Upgrading the OS (new standards, new gate
logic) upgrades every product at once; changing a product changes only its Canon. The OS and the
products it builds evolve on independent clocks — which is exactly what a universal Engineering OS
must guarantee.
