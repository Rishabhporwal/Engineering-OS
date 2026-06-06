# Canon Index — the pointer map (read this, open ONE target)

> Replaces v1's 924-line `IMPLEMENTATION-BLUEPRINT.md`, which was a 4th full restatement (only 82 of its lines were pointers) and the single largest avoidable load in the pipeline. This index is **pointers only** — find your topic, open the **one** owning file, read the relevant `§`. Never load canon whole.
>
> **Single-owner rule:** every fact has exactly ONE home file (below). Primers (`docs/business-context.md`, `docs/technical-context.md`) and skills *summarize and reference* — they never re-own. When a primer and the canon disagree, the canon wins.

## Layers
- **Daily reading:** `docs/business-context.md` (89 ln) + `docs/technical-context.md` (188 ln) — condensed primers, read at session start.
- **Full requirements:** `canon/business-requirements.md` (BRD) · `canon/technical-requirements.md` (TRD).
- **Deep dives (the owners):** `canon/TECH/00–18` — open targeted.

## Topic → owner file

| Topic | Owner |
|---|---|
| Tech-stack choices, phased adoption, graduation triggers | `TECH/00` |
| Data architecture, Postgres/ClickHouse split, RLS, partitioning, CDC | `TECH/01` |
| Connectors, ETL, Kafka ingestion, OAuth, idempotent upsert | `TECH/02` |
| **Metrics engine, the Formula Book, CM waterfall, RAG bands, TS↔Python parity** | `TECH/03` |
| **RegionAdapter, India-first, residency, GST/VAT slabs, locale** | `TECH/04` |
| Intelligence layer, 15 product agents, Memory Layer (pgvector), daily tick | `TECH/05` |
| API contracts (tRPC / gRPC / MCP), pagination, versioning | `TECH/06` |
| Web frontend architecture, state ownership, charts | `TECH/07` |
| Alerts, reporting, notifications, Morning Brief assembly | `TECH/08` |
| Security & observability, traceability, secrets, RLS enforcement | `TECH/09` |
| Mobile architecture, the Morning Brief surface, MASVS | `TECH/10` |
| Lifecycle & revenue execution layer (lifecycle-service) | `TECH/11` |
| **Cost-routed compute paradigm (SQL≫ML≫Haiku≫Sonnet), `@paradigm`, caps** | `TECH/12` |
| MCP protocol, tool schemas (generated from protos) | `TECH/13` |
| Agent roster (AICMO/AICOO/AICFO), graduation tracker | `TECH/14` |
| **Billing & metering, realized-GMV pricing, fee clamp, tier %s, minor units** | `TECH/15` |
| **Compliance engine — DPDP/PDPL/DLT-TCCCPR/NCPR-DND/9–9 window/WhatsApp/consent/residency** | `TECH/16` |
| Engineering operating model (this team) | `TECH/17` |
| Per-service operational spec, comms matrix, failure/retry contracts, E2E flows | `TECH/18` |

## Key economic facts — owner file (do NOT restate elsewhere; cite this)
- **COD-RTO break-even** `r* = M/(M+C)` → `TECH/04` (India economics) + BRD.
- **CM waterfall / CM2 / CM3**, Goal RAG (Green ≥95% / Amber 80–95% / Red <80%) → `TECH/03`.
- **GST 2.0 per-SKU slabs (0/5/18/40)** → `TECH/04`.
- **Fee** `clamp(gmv_pct × billable_gmv, min_fee, cm2_cap_pct × CM2)`; tiers Launch ~1.0 / Growth ~0.75 / Scale ~0.5 / Enterprise custom → `TECH/15`.
- **Cost ratio** SQL:ML:Haiku:Sonnet ≈ 1:100:1,000:10,000 → `TECH/12`.
- **7 services** (api-gateway, core, ingestion, analytics, intelligence, notifications, lifecycle) → `TECH/18`.

## How agents use this
1. Need a fact? Find the topic above → open that ONE file → read the `§` (grep the heading).
2. Writing an artifact? Cite the owner (`per TECH/15 §fee`), don't paste the formula.
3. Primer and canon disagree? Canon wins — re-read the owner file and flag the primer drift.
</content>
