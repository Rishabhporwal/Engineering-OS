# Lane Classifier — deterministic risk tiering

> In v1 this decision tree lived inside the deep-tier `cto-advisor` prompt (steps 7a/9/10) and was re-reasoned on every intake — costly and drift-prone. In v2 it is a **deterministic procedure** the intake stage applies mechanically (runnable on `intake_mechanical`, the mechanical tier). cto-advisor spends its judgment on requirement quality + challenge, not on running this table.

The output: `feature_class ∈ {express, standard, high_stakes}` + `trigger_surfaces_touched[]` + one-line rationale. Recorded on the requirement in `state/active.json` and in the intake review.

## Step 1 — Trigger-surface scan (decides high-stakes) — DETERMINISTIC

> Run by a **tool, not a model judgment** (the high-blast-radius part must not depend on the cheapest model spotting a surface in prose):
> ```sh
> uv run ${CLAUDE_PLUGIN_ROOT}/tools/classify_lane.py --text "<requirement>" [--diff <staged-diff>]
> ```
> It emits `trigger_surfaces_touched[]`. The intake agent may **ADD** a surface the scan missed; it may **NEVER silently REMOVE** one the scan flagged. ≥1 surface ⇒ `high_stakes`. This closes the "a cheapest-tier model miss strips Security off a compliance change" gap.

Surfaces the scan checks (and the intake agent cross-checks):

> The surface KEYS below are the cross-file interface (emitted by `tools/classify_lane.py`,
> consumed by the orchestrator + pipeline) — preserved verbatim. The Examples are generic
> illustrations; a product binds each surface to its own concrete signals via its Canon
> (`TRIGGER-SURFACES.md` / `COMPLIANCE.md`).
>
| Surface | Examples |
|---|---|
| `auth` | login, JWT, session, role, permission |
| `multi_tenancy` | anything keyed on the tenant-isolation key, RLS, an OLAP query-gateway |
| `mcp_tools` | new/changed agent/tool surface (e.g. an MCP tool) |
| `connectors` | any external connector OAuth or ingestion path |
| `outbound_channel` | any outbound message/channel (call / messaging / SMS / email / audience push) |
| `pii` | customer PII read/write/store |
| `schema_proto` | DB migration or a contract/schema (`.proto`) change |
| `money` | money math (minor units) — billing, metering, fees |
| `compliance` | the product's compliance regime (per `COMPLIANCE.md`) — data-protection law, residency, retention, consent, channel rules |

- **≥1 surface → `high_stakes`.** Record the surfaces. Stop — express/standard are off the table.
- **0 surfaces → go to Step 2.**

### Foundational-scaffolding carve-out (narrow; Stakeholder-ratified)
If the ONLY surfaces are structural (`schema_proto` / `multi_tenancy` / `mcp_tools`) **and** touched *only* by creating empty homes / toolchain config / structure — **no live contract or consumers, no business logic, no migration on existing data, no runtime, and no `money`/`pii`/`outbound_channel`/`connectors`/`compliance` surface** — classify **`standard`** (architect + security + qa + final still run; only persona escalation + mutation tests drop). **On ANY doubt, stay `high_stakes`.**

## Step 2 — Triviality test (only if zero trigger surfaces)

Is the change purely one of: copy/content · docs · config tweak · dependency bump · styling · refactor with zero behavior change · a clear repeat of a lessons-registry pattern (confirm via semantic recall)?

- **YES → `express`.**
- **NO → `standard`.**

## Step 3 — Conservative tie-break (Stakeholder rule)

On any doubt between two lanes, pick the **higher-rigor** lane. A misclassified high-stakes change is a production incident; a misclassified express change costs only a few extra agent passes. **NEVER downgrade to express on ambiguity.**

## Step 4 — Persona count (capped by lane)

| Lane | Personas |
|---|---|
| express | **0** (no brainstorm) |
| standard | **0–1** (1 when a single risk dimension dominates) |
| high_stakes | **2** (when two distinct risk dimensions intersect; this is the hard cap) |

3+ personas are never permitted — if you want 3+, the requirement is too broad: bounce to the Stakeholder to decompose. Tag each persona's depth: `:haiku` (the mechanical tier — bounded: checklist/toolchain/naming/single-rule) or `:sonnet` (the standard tier — reasoning-heavy: migration method, compliance trade-offs, numeric parity). Pick the cheapest tier that still surfaces a real concern.
</content>
