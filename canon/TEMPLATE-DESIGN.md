# HLD / LLD — design (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/HLD.md` (+ `LLD-<context>.md` per bounded context). Organize
> by **bounded context / domain**, never by technical layer. See
> `engineering-os-blueprint/04-architecture-and-decisions.md`.

## High-level design
- **System context:** `<what the system is, its external actors and systems>`
- **Bounded contexts:** `<list each domain context and what it owns>`
- **Sync vs async seams:** `<which interactions are request/response, which are event-driven, and why (ADR)>`
- **Data ownership:** `<which context owns which data; OLTP vs OLAP split>`
- **Cross-cutting concerns:** `<tenant isolation, idempotency, traceability — where each is enforced>`

## Low-level design (per context)
For each bounded context, a `LLD-<context>.md`:
- **Responsibilities & boundaries** — what it owns; what it must not reach into.
- **Contracts** — APIs / events / shared schemas it exposes (the source of truth; versioned).
- **Data model** — entities, the tenant-isolation primitive leading the schema, indexes, partitioning.
- **Key flows** — the important request/event paths, end to end, with the correlation identity.
- **Failure modes** — timeouts, retries, degradation, rollback.
