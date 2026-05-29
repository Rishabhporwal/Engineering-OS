# Lane Classifier — deterministic risk tiering

> In v1 this decision tree lived inside the Opus `cto-advisor` prompt (steps 7a/9/10) and was re-reasoned on every intake — costly and drift-prone. In v2 it is a **deterministic procedure** the intake stage applies mechanically (runnable on `intake_mechanical` = Haiku). cto-advisor spends its judgment on requirement quality + challenge, not on running this table.

The output: `feature_class ∈ {express, standard, high_stakes}` + `trigger_surfaces_touched[]` + one-line rationale. Recorded on the requirement in `state/active.json` and in the intake review.

## Step 1 — Trigger-surface scan (decides high-stakes)

Does the requirement touch ANY of these surfaces?

| Surface | Examples |
|---|---|
| `auth` | login, JWT, session, role, permission |
| `multi_tenancy` | anything keyed on `workspace_id`, RLS, CH query-gateway |
| `mcp_tools` | new/changed MCP tool |
| `connectors` | Shopify/Meta/Google/Shiprocket/Klaviyo/TikTok/Snap OAuth or ingestion |
| `outbound_channel` | call / WhatsApp / SMS / email / ad-audience push |
| `pii` | customer PII read/write/store |
| `schema_proto` | DB migration or `.proto` change |
| `money` | billing, GMV meter, fees, minor-units math |
| `compliance` | DPDP / PDPL / DLT / NCPR / calling-hours / recording-consent / WhatsApp policy |

- **≥1 surface → `high_stakes`.** Record the surfaces. Stop — express/standard are off the table.
- **0 surfaces → go to Step 2.**

### Foundational-scaffolding carve-out (narrow; Founder-ratified)
If the ONLY surfaces are structural (`schema_proto` / `multi_tenancy` / `mcp_tools`) **and** touched *only* by creating empty homes / toolchain config / structure — **no live contract or consumers, no business logic, no migration on existing data, no runtime, and no `money`/`pii`/`outbound_channel`/`connectors`/`compliance` surface** — classify **`standard`** (architect + security + qa + final still run; only persona escalation + mutation tests drop). **On ANY doubt, stay `high_stakes`.**

## Step 2 — Triviality test (only if zero trigger surfaces)

Is the change purely one of: copy/content · docs · config tweak · dependency bump · styling · refactor with zero behavior change · a clear repeat of a lessons-registry pattern (confirm via semantic recall)?

- **YES → `express`.**
- **NO → `standard`.**

## Step 3 — Conservative tie-break (Founder rule)

On any doubt between two lanes, pick the **higher-rigor** lane. A misclassified high-stakes change is a production incident; a misclassified express change costs only a few extra agent passes. **NEVER downgrade to express on ambiguity.**

## Step 4 — Persona count (capped by lane)

| Lane | Personas |
|---|---|
| express | **0** (no brainstorm) |
| standard | **0–1** (1 when a single risk dimension dominates) |
| high_stakes | **2** (when two distinct risk dimensions intersect; this is the hard cap) |

3+ personas are never permitted — if you want 3+, the requirement is too broad: bounce to Founder to decompose. Tag each persona's depth: `:haiku` (bounded — checklist/toolchain/naming/single-rule) or `:sonnet` (reasoning-heavy — migration method, compliance trade-offs, numeric parity). Pick the cheapest tier that still surfaces a real concern.
</content>
