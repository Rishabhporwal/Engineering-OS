---
name: data-privacy-dpdp
description: Brain's full Compliance Engine (canon/TECH/16) — data privacy + telecom. India DPDP Act 2023 + Rules 2025 (consent-based, minimization, retention, right-to-erasure, breach notice, Consent-Manager-ready); India TCCCPR/DLT (A2P SMS/voice), NCPR/DND two-layer scrub, 9am–9pm window; WhatsApp Meta opt-in + approved templates + 24h service window; AI-voice disclosure + recording consent + human handoff; UAE/KSA PDPL; India data in-region (ap-south-1) by default; PII never stored (cards/CVV/UPI/bank/Aadhaar/passwords; addresses default pincode/city); consent primitive per customer/channel/purpose/source/timestamp/region/withdrawal; Compliance SLO 0 violations. A Shreya VETO surface. Use when handling PII, wiring outbound, or building erasure.
---

# Compliance Engine — DPDP · PDPL · DLT/TCCCPR · consent · residency

Brain processes large volumes of customer PII and does outbound voice/messaging in a heavily regulated market. This is the single, named, **enforceable** spec (canon/TECH/16). **Any breach of these rules blocks a release — this is a Shreya VETO surface** alongside [`security-baseline`](../security-baseline/SKILL.md). Brain is a **processor**; the brand is the controller/data-fiduciary — Brain provides the tools + defaults that make the brand compliant by default.

**Canonical sources:** `canon/TECH/16_compliance_engine.md` · technical-requirements §21 · `canon/TECH/11` §6.

## Applicable regimes (named, current 2026)

| Regime | Scope | Brain's obligations |
|---|---|---|
| **India DPDP Act 2023 + Rules 2025** (phased → Consent Managers ~Nov 2026 → core duties ~May 2027) | all Indian customer PII | consent-based processing, purpose limitation, minimization, retention limits, **right to erasure**, breach notification, Consent-Manager compatibility |
| **India TCCCPR 2018 (amended 12 Feb 2025)** | A2P SMS + voice | **DLT** registration of headers + templates, **NCPR/DND** scrubbing, **9am–9pm** promotional window |
| **UAE PDPL** (45/2021) | UAE PII | explicit revocable opt-in for marketing; erasure; cross-border transfer controls |
| **KSA PDPL** (enforced 14 Sep 2024) | KSA PII | opt-in consent; sensitive-data prohibition for marketing; transfer restrictions; penalties to SAR 5M |
| **Meta WhatsApp policy** | WhatsApp sends | user opt-in, approved templates, free 24h service window, quality-rating |

## The compliance engine (outbound gating — NOT feature-flaggable)

Hard-coded into **every** outbound path in `lifecycle-service/compliance/engine.py`. A send/call cannot bypass it:

```python
def can_contact(self, brand_id, customer_id, channel, segment, purpose) -> ComplianceResult:
    # 1. Consent (per channel + purpose) — re-checked before EVERY send
    if purpose == 'marketing' and c.consent(channel) != 'opted_in':
        return ComplianceResult.blocked('consent_missing')
    if c.consent(channel) in ('opted_out', 'withdrawn'):
        return ComplianceResult.blocked('consent_revoked')
    # 2. Channel-specific
    if channel in ('call', 'sms') and region == 'IN':
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
| **WhatsApp** | Meta opt-in; approved template per purpose; **free 24h service window** for replies; frequency cap. (NOT DLT.) |
| **SMS** | DLT header + template on the **brand's** DLT entity (never commingled); NCPR/DND; 9am–9pm; cap. |
| **Voice / AI calls** | **two-layer DND** (brand list + NCPR); 9am–9pm gated **at the queue, not the dialer**; **automated-agent disclosure** at call open; **recording consent** (proceed without retention if declined); **human handoff** path; cap. |
| **Email** | opt-in/unsubscribe honored; suppression on withdrawal; CAN-SPAM-equivalent footer. |
| **Ad custom audiences** | consent state + suppression applied before push to Meta/Google. |

**Calling-hours gating is at the queue:** out-of-window calls/SMS sit in `pending_window` and flush at 09:00 — so "0 out-of-window attempts" is a *structural guarantee*, not a runtime hope.

## The consent primitive (one model, all channels)

Built once in `core-service` (`consent/`), consumed by every outbound path (Single-Primitive Rule). Tracked by **customer × channel × purpose × source × timestamp × region × withdrawal**, append-only:

```sql
lifecycle.consent_event(             -- append-only ledger
  workspace_id, customer_id, channel,   -- email/sms/whatsapp/call/ads_custom_audience/all
  old_status, new_status,                -- opted_in/opted_out/withdrawn/unknown
  purpose, source, region, recorded_at)  -- purpose = marketing | transactional
lifecycle.customer_consent_current(...)  -- materialized current state, PK (workspace_id, customer_id, channel, purpose)
```

**Transactional vs marketing:** support replies may continue where legally transactional even if marketing consent is withdrawn; marketing upsells cannot. **Opt-out overrides all marketing.** Forward-compatible with DPDP Consent Managers via `source = 'consent_manager'`.

## Data lifecycle (DPDP / PDPL)

- **Never store:** card numbers, CVV, full UPI IDs, full bank accounts, plaintext passwords, national IDs (Aadhaar), special-category data, **full addresses** (default **pincode/city-level**), PII in logs.
- **PII at rest/in transit:** hash email/phone by default (`email_hash`/`phone_hash`); plaintext contact only where outreach is enabled + consent/legal basis exists, KMS-encrypted. **Redaction at the logger (`pylibs/brain_logger`) AND at Fluent Bit (Lua scrub)** before OpenSearch ([`observability`](../observability/SKILL.md)). TLS everywhere; mobile cert-pinning.
- **Residency (default, not enterprise-only):** **Indian customer data stored in-region (ap-south-1) by default** — Supabase, MSK, ClickHouse, S3 all in-region. UAE/KSA (Phase 4) per PDPL transfer rules.
- **Right to erasure:** brand-initiated → tombstone in Postgres (RLS-scoped) + hard-delete plaintext PII → ClickHouse `ALTER TABLE ... DELETE WHERE workspace_id=? AND customer_id=?` → purge S3 raw payloads → suppress in all audiences + consent → `withdrawn` → write `audit.audit_log` (the audit entry itself is PII-free and retained). Export = signed-S3 machine-readable bundle.
- **Retention:** raw 5y, `*_recent` 90d, canonical/daily-metrics forever (de-identified where required), `audit_log` 7y, soft-deleted workspaces hard-deleted at 90d — enforced by scheduled jobs.
- **Breach:** Sentry P1 → on-call → scoped impact → notify affected brand(s) within the regime's window → post-mortem.

## Cross-brand benchmark privacy

Raw data never leaves a workspace partition. Benchmarks are aggregate + anonymized, **k-anonymity k≥5** enforced in schema (`ai.cross_brand_pattern.brand_count CHECK (>=5)`). Opt-in to contribute (DPA); receive patterns regardless ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md), [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md)).

## Compliance SLOs (all = 0)

DND/NCPR-blocked attempts that **leaked** · out-of-window send attempts · cross-brand data leaks · PII-in-logs incidents — **each must be 0**; non-zero is a rule violation.

## Anti-patterns

- A send/call that bypasses the engine, or checks consent once instead of before every send.
- Gating calling hours at the dialer instead of the queue.
- Commingling brands' DLT registrations; sending an unapproved WhatsApp template.
- Marketing to `opted_out`/`withdrawn`; ignoring the 24h service-window distinction.
- Storing a full address/card/UPI/Aadhaar; PII reaching logs.
- Writing Indian customer data outside ap-south-1.
- Erasure that misses ClickHouse, S3, or audiences (must remove everywhere it propagated; keep the audit entry).
- A cross-brand pattern below k=5.

## Verify

- A pre-09:00 IST SMS/call sits in `pending_window` and flushes at 09:00; a NCPR-listed or opted-out number is blocked.
- A marketing send to a `withdrawn` consent fails the test; a transactional support reply within the window proceeds.
- An erasure removes plaintext PII across PG + CH + S3 + audiences; the audit entry remains.
- Grep new code paths + sample OpenSearch lines for phone/email/address — none present (redaction at logger + Fluent Bit).

## References

- `canon/TECH/16_compliance_engine.md` — the full enforceable spec + test matrix + SLOs
- `canon/technical-requirements.md` §21 · `canon/TECH/11_lifecycle_revenue_layer.md` §6
- [`lifecycle-revenue-layer`](../lifecycle-revenue-layer/SKILL.md) · [`security-baseline`](../security-baseline/SKILL.md) · [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md) · [`region-adapter`](../region-adapter/SKILL.md)
