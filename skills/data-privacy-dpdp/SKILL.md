---
name: data-privacy-dpdp
description: Data-privacy & PII engineering discipline — consent capture, purpose limitation, data minimization, retention limits, right-to-erasure paths, breach response, and PII redaction everywhere (logs, journals, caches, embeddings). Business-agnostic engineering practice. NOTE — the specific regulatory regime (was India DPDP Act + telecom) is RESET; bind the concrete obligations to the new business canon when re-fed.
---

# Data Privacy & PII Handling (engineering discipline)

The reusable **engineering** practice for handling personal data is intact; the **specific regulatory regime was reset** (the prior business was India: DPDP Act 2023 + telecom). Bind concrete obligations (which laws, retention windows, consent semantics, cross-border rules) to the new business canon once re-fed. Until then, treat PII conservatively and escalate regime-specific questions to the Founder.

## Business-agnostic rules (always apply)
1. **PII never in logs/journals/decision-log.** Redact at the logger + log pipeline ([`observability`](../observability/SKILL.md)) and in the Engineering OS journals.
2. **PII encrypted at rest**; secrets/tokens via a managed KMS ([`security-baseline`](../security-baseline/SKILL.md)).
3. **PII never in cache keys; encrypted if cached as values** ([`caching-strategy`](../caching-strategy/SKILL.md)).
4. **Data minimization** — collect/store only what a feature needs.
5. **Retention + erasure are first-class** — every PII-touching table has a documented retention window + an erasure path (Postgres + OLAP + object storage + caches + any embeddings).
6. **Consent is recorded** where the domain requires it; purpose-limit usage to what was consented.
7. **Breach = P0** — a suspected leak (incl. cross-tenant, see [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)) is a page.

## To bind to the new business (when re-fed)
> _(define: which regulations apply, lawful bases, retention windows, cross-border transfer rules, any sector-specific obligations)_

## Verify
- Grep new code paths + sample log lines for PII leakage (phone/email/address patterns) — none present.
- A new PII-touching table has a documented retention + erasure path; an erasure request removes the row everywhere it propagated.

*Prior India-DPDP-specific content retained in git history.*
