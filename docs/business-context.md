# Business Context — primer TEMPLATE (author per adoption)

> **This file is a TEMPLATE, not content.** In a generic Engineering OS, the business context is
> **product-specific** and authored **per adoption**. The OS itself carries no product, business, or
> domain knowledge. This file explains *what a product's business-context primer should contain* and
> *where the authoritative answers live* — the **Product Canon** in
> `${CLAUDE_PROJECT_DIR}/.engineering-os/knowledge-base/` (template index: `canon/INDEX.md`).
>
> **What this primer is.** A short, agent-loadable **condensation** of the product's business
> requirements, read at session start so every agent shares the same intent. It **summarizes and
> references** the Canon — it never re-owns a fact. **When this primer and the Canon disagree, the
> Canon wins; re-read it.** Keep it tight (one screen of prose, plus the section stubs below).
>
> A worked, fully-populated example lives under `examples/` (a commerce-OS instantiation) — read it to
> see what a completed business primer looks like in practice.

---

## How to author this file (delete this block once filled)

1. Fill each section below from the product's business requirements.
2. For every fact, point to its **one owning Canon file** (don't restate it here at length).
3. Keep money as **integer minor units + a `currency_code`** in every example you give.
4. Express roles as the OS roles (the human who files requirements and holds the deploy gate is the
   **Stakeholder**); attach human names, if any, in `.engineering-os/knowledge-base/team-roster.md`.
5. State unknowns explicitly. A blank section is a known gap, never "no constraint."

---

## 1. What the product is (prime directive)

> One or two sentences: what the product does, for whom, and the single outcome it exists to move.
> What the product is **not** (the anti-scope) is as useful as what it is.
>
> **A feature ships only if it ties to a stated outcome** — list the product's value axes here (e.g.
> value created, risk reduced, time saved, a compliance obligation met, decision quality compounded).
> If a feature can't tie to one, it doesn't ship. → Canon: `THE-MOAT.md`, `INVARIANTS.md`.

## 2. The user problem

> The concrete pain the product removes, and the failure modes it fixes. Frame it as the question the
> user is actually trying to answer — not the surface metric they currently stare at.

## 3. Users (ICP) & scope

> Who the customers/users are, any volume/segment floor, and the tiers/segments. The
> **region/locale footprint** (which markets are first-class now vs activated later via the
> RegionAdapter seam) goes here. → Canon: `HLD.md` (scope), `STACK.md` (region seam).

## 4. Roles & access

> The product's role model (RBAC) and the approval matrix per consequential action class. Express in
> the OS role vocabulary; map product-specific personas to those roles. → Canon: `INVARIANTS.md`
> (tenant isolation + role rules), `ESCALATION-RUBRIC.md` (when a role escalates to the Stakeholder).

## 5. The product pillars

> The 4–8 capability areas the product is built around, each in one line. Each pillar should name the
> outcome it serves (from §1). → Canon: `HLD.md`.

## 6. Metrics that matter

> The product's key business metrics, **defined once** in the single-source registry — never restated
> in prose or computed by a model. Money = integer minor units + `currency_code`; every metric is
> identical across runtimes (parity is CI-checked). Models classify/explain/draft; they **never invent
> numbers.** → Canon: `METRICS.md`.

## 7. Product surfaces

> The screens/endpoints/channels where the product meets the user, and which one is the primary
> high-stakes surface. The product's *concrete* high-stakes surfaces + thresholds (what forces the
> high-stakes lane) are declared in `TRIGGER-SURFACES.md`.

## 8. Outbound / channels (if any)

> If the product sends outbound messages or takes consequential external actions: the channels, the
> consent model, the frequency/cost rules. All channel and consent rules are governed by the product's
> compliance regime. → Canon: `COMPLIANCE.md`, `TRIGGER-SURFACES.md`.

## 9. Automated / agentic actions (if any)

> If the product takes actions on the user's behalf: the guardrails (caps, reversibility, confidence
> thresholds, a kill switch, an audit entry per action), and the graduation path from "recommend" to
> "act". → Canon: `INVARIANTS.md`, `THE-MOAT.md` (where a system-of-record audit log is required).

## 10. Pricing, compliance, the moat

> - **Pricing model** (how the product charges), if relevant to engineering decisions (e.g. a cost
>   ceiling a feature must respect). → Canon: `METRICS.md`, `ESCALATION-RUBRIC.md`.
> - **Compliance regime (P0):** whatever `COMPLIANCE.md` declares — data protection, residency,
>   retention, consent, channel/contact rules — has **zero violations** (Security VETO). The OS
>   supplies the enforcement machinery; the Canon supplies the specific regime. If no regime applies,
>   `COMPLIANCE.md` says so explicitly.
> - **The moat:** the asset that compounds and must be protected. → Canon: `THE-MOAT.md`.

## 11. Roadmap (phases)

> The phased delivery plan, if one exists — what is foundational (build now) vs what graduates later
> when its trigger fires. → Canon: `HLD.md`.

## 12. Acceptance bar (every implementation)

> The product's "definition of done" at the business level — the checklist every shipped change must
> satisfy. Generic backbone every product inherits: tenant-safe + role-aware · ties to a stated
> outcome (§1) · deterministic metrics from the registry (models never invent numbers) · exposes data
> freshness/caveats · region/locale via **adapters** (no forks) · writes the system-of-record audit
> record where the Canon requires one · auditability/export/deletion/consent/PII-minimization.
>
> **Top risks to defend against:** list the product's specific failure modes here, each with its
> mitigation pointer into the Canon.
