# Technical Context — primer TEMPLATE (author per adoption)

> **This file is a TEMPLATE, not content.** In a generic Engineering OS, the technical context is
> **product-specific** and authored **per adoption**. The OS is stack-agnostic and carries no product
> architecture. This file explains *what a product's technical-context primer should contain* and
> *where the authoritative answers live* — the **Product Canon** in
> `${CLAUDE_PROJECT_DIR}/.engineering-os/knowledge-base/` (template index: `canon/INDEX.md`; seam model:
> `engineering-os-blueprint/09-reference-architecture.md`).
>
> **What this primer is.** A short, agent-loadable **condensation** of the product's technical
> requirements, read before writing code, designing a service, or reviewing a PR. It **summarizes and
> references** the Canon — never re-owns a fact. **When this primer and the Canon disagree, the Canon
> wins; re-read it.** Keep it tight.
>
> A worked, fully-populated example lives under `examples/` (a concrete stack instantiation) — read it
> to see what a completed technical primer looks like in practice.

---

## How to author this file (delete this block once filled)

1. Fill each section from the product's technical requirements; point each fact to its **one owning
   Canon file** rather than restating it.
2. Name the **technology that binds each seam** in `STACK.md`; this primer references those choices, it
   doesn't re-decide them.
3. Keep money as **integer minor units + a `currency_code`** everywhere.
4. State unknowns explicitly. An empty slot is a known gap.

---

## 0. The obligations (everything serves these)

> The 3–5 non-negotiable system obligations the product is built to honor (e.g. truth/auditability,
> compounding memory, safe execution, the product's quality bar). The most important cross-cutting
> invariant for most products: **the cheapest sufficient effort runs each decision** — deterministic
> logic ≫ statistical/ML ≫ small model ≫ large model; reach up a tier only when the one below can't meet
> the bar. → Canon: `INVARIANTS.md`; doctrine: `engineering-os-blueprint/11-runtime-and-cost-doctrine.md`.

## 1. Build the contracts from day one; run the infra at the smallest footprint

> The mature target architecture is the destination — **do not build all of it on day one.** Build the
> *invariants/contracts* now; graduate each heavy infra layer only when its trigger fires.
>
> **Non-negotiable-from-day-one list (retrofitting these is brutal)** — author the product's version,
> e.g.: the **tenant-isolation key** on every row/event/cache-key/log + isolation enforced at every
> layer · **integer minor-units money** + `currency_code` (never float for money) · the **system-of-record
> audit log** (where the Canon requires one) · the **region/locale adapter** seam · the **single-source
> metric registry** with cross-runtime parity · **cheapest-sufficient-effort** discipline + per-tenant
> model caps · **contract-defined internal APIs** for every bounded context · **idempotency** on every
> connector write + mutating endpoint. → Canon: `INVARIANTS.md`, `STACK.md`, `HLD.md`.

## 2. Stack snapshot

> A table of the locked technology bound to each seam (runtimes, web, mobile, edge/API, internal API,
> OLTP, OLAP, cache, object store, events, intelligence/LLM gateway, infra, observability, secrets).
> **The stack is LOCKED** — use `tech-stack-evaluation` only when adding a layer not in the stack or
> proposing a swap (needs an ADR). The vendor-named reference-implementation skills
> (`backend-fastify-trpc-grpc`, `clickhouse-olap`, `frontend-web`, `mobile-surface`, `devops-aws`, etc.)
> show one concrete binding of a seam; the *patterns* transfer, the vendor does not. → Canon: `STACK.md`.

## 3. Bounded contexts / services

> The product's backend bounded contexts (each a DDD context with its own internal contract from day
> one), and how many deployables they run as per phase (*logical separation now, physical separation
> later*). Frontend/presentation surfaces listed separately. → Canon: `HLD.md`, `LLD-*.md`.
>
> **Communication (contract-first):** frontend → the API gateway only · gateway → services via the
> internal-RPC seam · service ↔ service via async events (versioned + DLQ + retries). Services never
> call each other via ad-hoc REST and never share a database.

## 4. DDD by bounded context (mandatory — code-review blocker if violated)

> Every backend service is organized **by domain**, never by technical layers
> (`bootstrap/`/`domain/`/`application/`/`infrastructure/`/`interfaces/`). A `controllers/`-style
> technical-layer folder is a blocker. → skill `domain-driven-design`.

## 5. Multi-tenancy & RBAC — the isolation key is law (enforced at every layer)

> The product's tenant hierarchy, the isolation key, and how it's enforced at **every** layer
> (identity/JWT → API gateway role check on every mutation → data-store row-level isolation → async
> backbone asserts the key from the envelope; cache keys + object-store paths scoped). The product's
> role model (with the approval matrix per action class). → Canon: `INVARIANTS.md`; skills
> `multi-tenancy-isolation`, `auth-and-access`.

## 6. Data model

> The OLTP/OLAP split, the schemas per bounded context, money as **integer minor units +
> `currency_code`** everywhere, PII handling, and credential storage (encrypted at rest; plaintext
> never logged). Where a system-of-record audit log is required, describe its append-only schema and
> the rule that **a workflow that cannot write its audit record is not complete.** → Canon: `LLD-*.md`,
> `INVARIANTS.md`; skills `data-layer`, `clickhouse-olap`, `decision-log`.

## 7. Event spine

> Topic naming convention; **partition key = the tenant-isolation key**; schema registry + envelope
> shape (carrying the correlation identity); retention tiers; idempotent consumers + DLQ + replay;
> versioning rules. → Canon: `LLD-*.md`; skill `event-driven-kafka`.

## 8. Metric engine & region adapters

> The **single-source metric registry** (`METRICS.md`) — one definition computed identically across
> runtimes, **CI-enforced parity**; models never produce metric numbers. The **RegionAdapter** seam for
> region/locale-varying behavior (tax, formats, calendars, etc.) — adding a region is a new adapter +
> tests; the metric engine/frontend/intelligence need zero changes. → Canon: `METRICS.md`, `STACK.md`;
> skills `metric-engine`, `region-and-locale`.

## 9. AI / LLM layer & cost-routing (the engineering invariant)

> The effort-tier ladder and its relative cost — **deterministic logic ≫ statistical/ML ≫ small model ≫
> large model.** Every endpoint/agent declares its tier; CI/PR blocks if a cheaper tier would suffice.
> Routing goes through a model-agnostic gateway that picks the cheapest model passing that tier's eval
> bar; per-feature token budgets + per-tenant caps; caching as the biggest cost lever; model swaps are
> eval-gated. → Canon: `STACK.md`, `INVARIANTS.md`; skills `cost-routing-paradigms`, `llm-gateway`,
> `llm-evals`, `claude-api`.

## 10. API contracts

> The external API surface (typed client for web/mobile; tiered procedures `public → authed → tenant →
> privileged`; **keyset/cursor pagination — OFFSET banned in prod**; money fields as minor units +
> `currency_code`); the internal RPC surface (contract is the single source of truth, also feeds tool
> schemas so they can't drift; correlation metadata on every call; an interceptor rejects a missing
> tenant key). Every write tool auto-writes the audit record where the Canon requires one. → Canon:
> `LLD-*.md`; skills `api-discipline`, `grpc-buf`, `mcp-protocol`.

## 11. Integrations

> One connector interface (**backfill == live; only the window changes**): authenticate / refresh /
> sync(window) / receive_webhook / canonicalize / health_check. Idempotent writes (UPSERT on payload
> hash). Connector health = data freshness, not just "auth works." Stale data is labelled, agents
> degrade gracefully. → Canon: `HLD.md`; skill `integration-connectors`.

## 12. Frontend & mobile

> The web surface (server-rendered by default where the stack supports it; typed API client; the state
> split; the chart primitives; a performance budget + WCAG AA) and the mobile surface (offline
> behavior, secure token storage, OTA-vs-native-bump policy, cert pinning, mobile MASVS). → Canon:
> `STACK.md`, `LLD-*.md`; skills `frontend-web`, `mobile-surface`, `web-performance`, `accessibility`.

## 13. Security, privacy & compliance

> What the product must **never store**; PII handling (hash/redact by default; data residency per the
> regime); and the **applicable compliance regime** — whatever `COMPLIANCE.md` declares (data
> protection, residency, retention, consent, channel/contact rules), or "none" stated explicitly. The
> consent primitive, if any (append-only; opt-out overrides all marketing). → Canon: `COMPLIANCE.md`,
> `INVARIANTS.md`; skills `security-baseline`, `compliance-engine`, `compliance-attestation`.
>
> **Security VETO** on any CRITICAL/HIGH finding, any compliance-regime violation, or **missing
> traceability.**

## 14. Observability & SLOs

> One correlation identity (`request_id` + `trace_id` + the tenant/user keys) propagating across every
> hop (inbound → internal calls → async messages → model calls). The observability stack (PII-redacted)
> and the product's SLO table. → Canon: `LLD-*.md`, `PLAYBOOK-incident.md`; skill `observability`.

## 15. Definition of Done

> A task is **done** only when it: carries tenant isolation (every layer) · reuses shared primitives
> (no per-channel forks) · writes the system-of-record audit record where required · has role checks on
> mutations · declares its **effort tier** · uses **minor-units money** · handles region/locale via the
> **adapter** · has tests for success + permission-failure + stale-data + provider-failure + idempotency
> · emits structured logs + metrics with the **correlation identity** · degrades gracefully on
> missing/stale data · has reversal/rollback where possible · is documented for the next builder.
> Real-network smoke is mandatory for PASS; cross-runtime metric parity preserved; mutation tests on
> high-stakes paths (the metric registry, the compliance enforcement code, the audit log).

## 16. Anti-patterns to reject (code-review blockers)

> Author the product's blocker list. Generic backbone: per-channel audience/consent/attribution forks ·
> agent actions without the required audit record · **model-generated metric numbers** · region-specific
> forks of metric code · **float money** · **OFFSET pagination in prod** · cross-tenant data visible to
> another tenant · sequential queries where a batch fetch is correct · service-to-service ad-hoc REST ·
> **an expensive model tier where deterministic logic/ML suffices** · `controllers/`-style folders ·
> a credential/token stored or logged in plaintext.

## 17. How the product is built — the Engineering OS

> You are the **Engineering OS** — the AI team that builds this product. The recurring **8-stage
> pipeline**: 1 intake+brainstorm (Engineering Advisor + 0–2 personas) → 2 binding plan (Architect) →
> 3 build (builders, trace-instrumented) → 4 security review (Security VETO on CRITICAL/HIGH +
> compliance + missing traceability) → 5 QA (QA VETO on missing real-network verification + metric
> parity + end-to-end trace IDs) → 6 final review (Engineering Advisor VETO) → 7 deploy gate
> (Stakeholder `/approve`) → 8 deploy + bake-window monitor + auto-rollback (Platform/SRE).
> **Plan-binding:** stages 3–8 execute the Stage-2 plan; deviations route through the Architect's
> amendment loop. **Escalation is Advisor-gated, last-resort** (`/escalate` → Stakeholder `/decide`).

## 18. When in doubt

> 1. Re-read this primer. 2. Open the relevant Canon owner file via `canon/INDEX.md` (the source of
> truth). 3. Open the relevant skill (see `docs/skill-mapping-matrix.md`). 4. PLAN-phase only:
> `WebSearch`/`WebFetch` to validate a stack/compliance fact. 5. Escalate to the **Architect**
> (architecture), the **Security Reviewer** (security/compliance), the **Engineering Advisor**
> (priorities/cross-team), or the **Stakeholder** (changing the stack or a non-negotiable).
