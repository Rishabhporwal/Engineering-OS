---
name: data-privacy-dpdp
description: India's Digital Personal Data Protection Act (DPDP 2023) + PII lifecycle for Brain — lawful consent, purpose limitation, data minimization, retention limits, right-to-erasure, breach response, and PII redaction everywhere (logs, journals, caches, embeddings). Distinct from telecom compliance (DLT/NCPR/DND). Use when handling customer PII (phone/email/address/order data), wiring a connector that ingests customers, building erasure, or reviewing where PII flows. Shreya VETO surface alongside security-baseline.
---

# Data Privacy — India DPDP Act + PII lifecycle

Brain ingests real customer PII (phones, emails, addresses, order history) from connectors. India's **DPDP Act 2023** governs this — separate from the **telecom** compliance (DLT/NCPR/DND) covered in [`india-commerce-economics`](../india-commerce-economics/SKILL.md). Both apply; this skill is the *data-protection* half. Shreya gates on it.

## DPDP obligations (engineering-relevant)

| Principle | What it means in Brain |
|---|---|
| **Lawful consent** | Customer PII is processed for a stated purpose; the brand is the Data Fiduciary, Brain a Processor. Consent state is recorded (`consent_event`). |
| **Purpose limitation** | Use PII only for the purpose collected (e.g., order fulfilment, opted-in lifecycle messaging) — not arbitrary new uses. |
| **Data minimization** | Ingest/store only the PII a feature needs. Don't hoard fields "just in case." |
| **Retention limits** | PII has a retention window; expired PII is deleted/anonymized (pairs with raw-archive TTL). |
| **Right to erasure** | A customer (via the brand) can request deletion — there must be a path to erase across Postgres, ClickHouse, S3 raw archive, caches, and the Memory Layer. |
| **Breach response** | A suspected leak is a P0 page (cross-tenant leak path in [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)). |

## Engineering rules

1. **PII never in logs/journals/decision-log.** Redact at the logger + Fluent Bit ([`observability`](../observability/SKILL.md)) and in the Engineering OS journals (the hook redacts secrets; PII discipline is on you).
2. **PII encrypted at rest**; OAuth tokens AES-256-GCM with per-brand KMS ([`security-baseline`](../security-baseline/SKILL.md)).
3. **PII never in cache keys; encrypted if cached as values** ([`caching-strategy`](../caching-strategy/SKILL.md)).
4. **Embeddings of PII** in the Memory Layer must be `workspace_id`-scoped and within retention ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md)).
5. **Erasure is a first-class path**, not an afterthought — design new PII-touching tables knowing they must be erasable.
6. **Cross-border**: keep India customer PII in-region unless a lawful transfer basis exists ([`region-adapter`](../region-adapter/SKILL.md)).

## Anti-patterns

- Logging a customer phone/email/address anywhere.
- Storing PII with no retention/erasure plan.
- Reusing PII for a purpose the customer didn't consent to.
- Embedding raw PII into the Memory Layer with no scoping or expiry.

## Verify

- Grep new code paths + sample log lines for PII leakage (phone/email/address patterns) — none present.
- A new PII-touching table has a documented retention + erasure path. Erasure test: a deletion request removes the row from Postgres + CH + S3 raw + cache + embeddings.
