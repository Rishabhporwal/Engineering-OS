---
name: compliance-engine
description: Owner of the compliance regime — DPDP+Rules 2025, TCCCPR-DLT, NCPR-DND, 9am-9pm, WhatsApp, PDPL, in-region data, consent primitive, PII-not-stored. Shreya VETO.
---

# Compliance Engine — the single owner of the regime

Brain processes large volumes of customer PII and does outbound voice/messaging in a heavily regulated market. This is the single, named, **enforceable** spec (`canon/TECH/16_compliance_engine.md`). **Any breach blocks a release — a Shreya VETO surface.** Brain is a **processor**; the brand is the controller/data-fiduciary — Brain provides the tools + defaults that make the brand compliant by default. Every other security skill references THIS for the regime; don't restate it elsewhere.

## Applicable regimes (named, current 2026)

| Regime | Scope | Obligations |
|---|---|---|
| **India DPDP Act 2023 + Rules 2025** (phased → **13 Nov 2026** Consent Manager registration → **13 May 2027** substantive duties) | all Indian PII | consent-based processing, purpose limitation, minimization, retention limits, **right to erasure**, breach notification, Consent-Manager compatibility |
| **India TCCCPR 2018 (amended 12 Feb 2025)** | A2P SMS + voice | **DLT** registration of headers + templates, **NCPR/DND** scrubbing, **9am–9pm** promotional window |
| **UAE PDPL** (45/2021) | UAE PII | explicit revocable marketing opt-in; erasure; cross-border transfer controls |
| **KSA PDPL** (full SDAIA enforcement since 14 Sep 2024) | KSA PII | opt-in; sensitive-data marketing prohibition; cross-border needs SDAIA-approved SCCs/BCRs; penalties to SAR 5M |
| **Meta WhatsApp policy** | WhatsApp sends | user opt-in, approved templates, free service window (**24h customer-service reply; 72h ad-click entry-point**), quality-rating |

## The compliance engine (outbound gating — NOT feature-flaggable)

Hard-coded into **every** outbound path in `lifecycle-service/compliance/engine.py`. A send/call cannot bypass it:
```python
def can_contact(self, brand_id, customer_id, channel, segment, purpose) -> ComplianceResult:
    # 1. Consent (per channel + purpose) — re-checked before EVERY send
    if purpose == 'marketing' and c.consent(channel) != 'opted_in':
        return ComplianceResult.blocked('consent_missing')
    if c.consent(channel) in ('opted_out','withdrawn'):
        return ComplianceResult.blocked('consent_revoked')
    # 2. Channel-specific
    if channel in ('call','sms') and region == 'IN':
        if not (9 <= now.hour < 21):
            return ComplianceResult.deferred('outside_calling_hours')   # held, flushed at 09:00
        if c.do_not_call or self.ncpr.is_listed(c.phone):              # two-layer DND
            return ComplianceResult.blocked('dnd_or_ncpr')
        if not self.dlt_registered(brand_id):
            return ComplianceResult.blocked('dlt_not_registered')
    if channel == 'whatsapp' and not self.template_approved(brand_id, purpose):
        return ComplianceResult.blocked('template_not_approved')
    # 3. Frequency cap — 48h per customer across ALL Brain flows
    if self.last_contact_within(brand_id, customer_id, hours=48) and not vip_override:
        return ComplianceResult.blocked('frequency_cap')
    return ComplianceResult.ok()
```

### Channel rules (canonical)
| Channel | Enforced |
|---|---|
| **WhatsApp** | Meta opt-in; approved template per purpose; free service window (24h customer-service reply; 72h ad-click entry-point) for replies; frequency cap. India marketing per-message rate ≈ **₹0.86** since 1 Jan 2026. (NOT DLT.) |
| **SMS** | DLT header + template on the **brand's** DLT entity (never commingled); NCPR/DND; 9am–9pm; cap. |
| **Voice / AI calls** | two-layer DND (brand list + NCPR); 9am–9pm gated **at the queue, not the dialer**; automated-agent disclosure at call open; recording consent (proceed without retention if declined); human handoff; cap. |
| **Email** | opt-in/unsubscribe honored; suppression on withdrawal; CAN-SPAM-equivalent footer. |
| **Ad custom audiences** | consent state + suppression applied before push to Meta/Google. |

**Calling-hours gating is at the queue:** out-of-window calls/SMS sit in `pending_window`, flush at 09:00 — "0 out-of-window attempts" is a structural guarantee, not a runtime hope.

## The consent primitive (one model, all channels)

Built once in `core-service` (`consent/`), consumed by every outbound path (Single-Primitive Rule). Tracked by **customer × channel × purpose × source × timestamp × region × withdrawal**, append-only:
```sql
lifecycle.consent_event(             -- append-only ledger
  workspace_id, customer_id, channel,   -- email/sms/whatsapp/call/ads_custom_audience/all
  old_status, new_status,                -- opted_in/opted_out/withdrawn/unknown
  purpose, source, region, recorded_at)  -- purpose = marketing | transactional
lifecycle.customer_consent_current(...)  -- materialized; PK (workspace_id, customer_id, channel, purpose)
```
**Transactional vs marketing:** support replies may continue where legally transactional even if marketing consent is withdrawn; marketing upsells cannot. **Opt-out overrides all marketing.** Forward-compatible with DPDP Consent Managers via `source = 'consent_manager'`.

## Data lifecycle (DPDP / PDPL)

- **Never store:** card numbers, CVV, full UPI IDs, full bank accounts, plaintext passwords, national IDs (Aadhaar), special-category data, **full addresses** (default **pincode/city-level**), PII in logs. (PCI scope boundary: `compliance-attestation`.)
- **PII at rest/in transit:** hash email/phone by default (`email_hash`/`phone_hash`); plaintext contact only where outreach is enabled + consent/legal basis exists, KMS-encrypted. Redaction at the logger (`pylibs/brain_logger`) AND at Fluent Bit (Lua scrub) before OpenSearch. TLS everywhere; mobile cert-pinning.
- **Residency (default, not enterprise-only):** Indian customer data in-region (**ap-south-1**) by default — Supabase, MSK, ClickHouse, S3 all in-region. UAE/KSA (Phase 4) per PDPL transfer rules. (Structural enforcement: `data-residency-enforcement`.)
- **Right to erasure:** brand-initiated → tombstone in Postgres (RLS-scoped) + hard-delete plaintext PII → ClickHouse `ALTER TABLE ... DELETE WHERE workspace_id=? AND customer_id=?` → purge S3 raw payloads → suppress in all audiences + consent → `withdrawn` → write `audit.audit_log` (PII-free, retained). Export = signed-S3 machine-readable bundle.
- **Retention:** raw 5y, `*_recent` 90d, canonical/daily-metrics forever (de-identified where required), `audit_log` 7y, soft-deleted workspaces hard-deleted at 90d — enforced by scheduled jobs.
- **Breach:** Sentry P1 → on-call → scoped impact → notify affected brand(s) within the regime's window → post-mortem.

## Cross-brand benchmark privacy
Raw data never leaves a workspace partition. Benchmarks are aggregate + anonymized, **k-anonymity k≥5** enforced in schema (`ai.cross_brand_pattern.brand_count CHECK (>=5)`). Opt-in to contribute (DPA); receive patterns regardless.

## Compliance SLOs (all = 0)
DND/NCPR-blocked attempts that **leaked** · out-of-window send attempts · cross-brand data leaks · PII-in-logs incidents — each must be 0; non-zero is a rule violation.

## PII data-catalog & lineage
Erasure + breach-scope are only as fast as your knowledge of where PII lives. Maintain a **field-level PII catalog** (versioned in repo, asserted in CI) + a **lineage map** so a DPDP request is a lookup, not archaeology.

| Field | Class | Default handling |
|---|---|---|
| `phone` | direct | `phone_hash`; plaintext only w/ outreach consent (KMS) |
| `email` | direct | `email_hash`; plaintext only w/ consent (KMS) |
| `address` | direct | pincode/city-level only; full address never |
| `order_id` / order facts | linked | retained; tombstoned on erasure |
| name + order-total combo | quasi | never co-logged |

Lineage — every copy a PII field makes:
```
connector ingest → S3 raw (KMS) → CH raw_* → CH canonical (orders, customers)
  → pgvector embeddings (Brand Fingerprint / condition_outcome)
  → logs (redacted at logger + Fluent Bit) → exports (signed S3 bundle)
```
The lineage map drives BOTH workflows: an **erasure** walks every node (PG tombstone + plaintext hard-delete → CH `ALTER … DELETE` → S3 purge → re-embed/evict derived pgvector rows → suppress in audiences/consent → keep the PII-free audit entry); a **breach** uses the same map to compute notification scope (fields × stores × brands) within the window. A new connector or derived table is **not done** until its PII fields are in the catalog + lineage.

## Anti-patterns
- A send/call that bypasses the engine, or checks consent once instead of before every send; gating calling hours at the dialer not the queue.
- Commingling brands' DLT registrations; sending an unapproved WhatsApp template; ignoring the free-service-window distinction.
- Marketing to `opted_out`/`withdrawn`; storing a full address/card/UPI/Aadhaar; PII reaching logs.
- Writing Indian customer data outside ap-south-1; erasure that misses ClickHouse/S3/audiences; a cross-brand pattern below k=5.

## Verify
- A pre-09:00 IST SMS/call sits in `pending_window` and flushes at 09:00; an NCPR-listed/opted-out number is blocked.
- A marketing send to a `withdrawn` consent fails; a transactional support reply within the window proceeds.
- An erasure removes plaintext PII across PG + CH + S3 + audiences; the audit entry remains.
- Grep new code paths + sample OpenSearch lines for phone/email/address — none present.

## References
`canon/TECH/16_compliance_engine.md` (full spec + test matrix + SLOs) · `canon/technical-requirements.md` §21 · `canon/TECH/11_lifecycle_revenue_layer.md` §6 · `lifecycle-revenue-layer` · `security-baseline` · `multi-tenancy-isolation` · `region-adapter` · `data-residency-enforcement` (residency enforcement) · `compliance-attestation` (PCI scope + audit immutability + SOC2).
