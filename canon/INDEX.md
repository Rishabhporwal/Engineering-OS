# Product Canon — Index & Template

> This is the **template** for a product's Canon. The Engineering OS ships it empty-but-structured; a
> consuming product fills it in **once**, during the Foundation phase, and the filled copy lives in the
> consuming repo at `${CLAUDE_PROJECT_DIR}/.engineering-os/knowledge-base/`. **That filled copy is the
> single source of truth** every agent reads — not this template.
>
> The OS itself carries **no** product, business, or domain knowledge. Everything domain-specific is
> declared here, per adoption. See `engineering-os-blueprint/10-adoption-and-product-canon.md` for the
> Foundation procedure, and `engineering-os-blueprint/09-reference-architecture.md` for the seam model.
>
> A worked, fully-populated example Canon (the "Brain" commerce-OS instantiation) lives under
> `examples/brain-instantiation/canon/` — read it to see what a completed Canon looks like.

## Layers

- **Daily reading (optional primers):** `docs/business-context.md` + `docs/technical-context.md` —
  condensed primers a product may author for session-start reading.
- **The Canon (the owners):** the slot files below, in `.engineering-os/knowledge-base/`.

## The slots — topic → owner file (each fact has exactly ONE home; cite, don't restate)

| Slot (owner file) | The OS question it answers | Template |
|---|---|---|
| `STACK.md` | Which technology binds each architecture seam, and why (ADRs). | [TEMPLATE-STACK.md](TEMPLATE-STACK.md) |
| `HLD.md` / `LLD-*.md` | High/low-level design — bounded contexts, contracts, data model. | [TEMPLATE-DESIGN.md](TEMPLATE-DESIGN.md) |
| `INVARIANTS.md` | The non-negotiables — rules that must always hold (the "never" list). | [TEMPLATE-INVARIANTS.md](TEMPLATE-INVARIANTS.md) |
| `TRIGGER-SURFACES.md` | The product's concrete high-stakes surfaces + thresholds (drives lane = high-stakes). | [TEMPLATE-TRIGGER-SURFACES.md](TEMPLATE-TRIGGER-SURFACES.md) |
| `COMPLIANCE.md` | The regulatory regime to enforce (jurisdictions, controls, data rules) — or "none". | [TEMPLATE-COMPLIANCE.md](TEMPLATE-COMPLIANCE.md) |
| `METRICS.md` | The single-source metric/contract definitions (identical across runtimes). | [TEMPLATE-METRICS.md](TEMPLATE-METRICS.md) |
| `PLAYBOOK-deploy.md` | Rollout strategy, bake window, rollback thresholds. | [TEMPLATE-PLAYBOOK-deploy.md](TEMPLATE-PLAYBOOK-deploy.md) |
| `PLAYBOOK-incident.md` | Severity ladder, paging, kill switches. | [TEMPLATE-PLAYBOOK-incident.md](TEMPLATE-PLAYBOOK-incident.md) |
| `ESCALATION-RUBRIC.md` | When a role must escalate to the Stakeholder. | [TEMPLATE-ESCALATION-RUBRIC.md](TEMPLATE-ESCALATION-RUBRIC.md) |
| `THE-MOAT.md` | The asset that compounds and must be protected. | [TEMPLATE-MOAT.md](TEMPLATE-MOAT.md) |
| `team-roster.md` | Optional human/team identities attached to the OS roles. | [TEMPLATE-team-roster.md](TEMPLATE-team-roster.md) |

## Rules of the Canon

- **Single-owner rule:** every fact has exactly ONE home file above. Primers and skills *summarize and
  reference* — they never re-own. When a primer and the Canon disagree, the Canon wins.
- **A slot left empty is a known gap, stated as such** — never silently treated as "no constraint." An
  empty `COMPLIANCE.md` means "no regulatory regime applies," recorded explicitly.
- **Never load the Canon whole** — find your topic above, open the **one** owning file, read the
  relevant section.
- **Amendments to an invariant or a foundational decision are a Foundation amendment** — they re-enter
  the Foundation flow and are re-approved, not edited in passing
  (`engineering-os-blueprint/08-technical-governance.md §7`).
