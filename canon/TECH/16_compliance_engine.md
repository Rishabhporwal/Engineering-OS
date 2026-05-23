# TECH/16 — Compliance Engine (DPDP · PDPL · DLT/TCCCPR · consent · residency)

> **Status:** New deep-dive (created with consolidated v2.0).
> **Owner:** `lifecycle-service` (`compliance/` — outbound gating) + `core-service` (`consent/`, residency, erasure) + Founder/Legal (DPA).
> **Companion:** `../technical-requirements.md` §21, `../business-requirements.md` §19, `11_lifecycle_revenue_layer.md` §6, `09_security_observability.md`.
> **Why this exists:** the prior docs treated compliance generically and scattered across §11/§09. Brain processes large volumes of customer PII and does outbound voice/messaging in a heavily regulated market. This is the single, named, enforceable spec. **VETO surface:** any breach of these rules blocks a release.

---

## 1. Applicable regimes (named, current 2026)

| Regime | Scope | Brain's obligations |
|---|---|---|
| **India — DPDP Act 2023 + DPDP Rules 2025** (notified 13 Nov 2025; phased: procedural now → Consent Managers ~Nov 2026 → core duties ~May 2027) | All Indian customer PII | Consent-based processing, purpose limitation, data minimization, retention limits, **right to erasure**, breach notification, Significant-Data-Fiduciary readiness, Consent-Manager compatibility |
| **India — TCCCPR 2018 (amended 12 Feb 2025)** | A2P SMS + voice | **DLT** registration of sender headers + templates, **NCPR/DND** scrubbing, **9am–9pm** promotional window, tightened complaint thresholds (5/10 days) |
| **UAE — PDPL** (Federal Decree-Law 45/2021, in force Jan 2022) | UAE customer PII | Explicit, revocable opt-in for direct marketing; erasure; cross-border transfer controls |
| **KSA — PDPL** (in force; enforcement 14 Sep 2024) | KSA customer PII | Opt-in marketing consent; sensitive-data prohibition for marketing; transfer restrictions; penalties up to SAR 5M |
| **Meta WhatsApp Business policy** | WhatsApp sends | User opt-in, approved templates, free service window (24h customer-service reply; 72h ad-click entry-point), quality-rating compliance |

Brain is a **processor/service provider**; the brand is the controller/data-fiduciary. Brain provides the tools + defaults that make the brand compliant by default.

---

## 2. The compliance engine (outbound gating)

Hard-coded into **every** outbound path in `lifecycle-service` — not feature-flaggable policy. A send/call cannot bypass it.

```python
# lifecycle-service/compliance/engine.py
class ComplianceEngine:
    def can_contact(self, brand_id, customer_id, channel, segment, purpose) -> ComplianceResult:
        c = self.customer(brand_id, customer_id)
        region = self.workspace_region(brand_id)
        now = datetime.now(self.tz_for(region))

        # 1. Consent (per channel + purpose) — must be opted_in for marketing purpose
        if purpose == 'marketing' and c.consent(channel) not in ('opted_in',):
            return ComplianceResult.blocked('consent_missing')
        if c.consent(channel) in ('opted_out', 'withdrawn'):
            return ComplianceResult.blocked('consent_revoked')

        # 2. Channel-specific
        if channel in ('call', 'sms'):
            if region == 'IN':
                if not (9 <= now.hour < 21):
                    return ComplianceResult.deferred('outside_calling_hours')   # held, flushed at 09:00
                if c.do_not_call or self.ncpr.is_listed(c.phone):
                    return ComplianceResult.blocked('dnd_or_ncpr')
                if not self.dlt_registered(brand_id):
                    return ComplianceResult.blocked('dlt_not_registered')
        if channel == 'whatsapp':
            if not self.template_approved(brand_id, purpose):
                return ComplianceResult.blocked('template_not_approved')

        # 3. Frequency cap (48h per customer across all Brain flows)
        if self.last_contact_within(brand_id, customer_id, hours=48):
            if not (segment == 'champions' and c.vip_override_approved):
                return ComplianceResult.blocked('frequency_cap')

        return ComplianceResult.ok()
```

### 2.1 Channel-specific rules (canonical)

| Channel | Rules enforced |
|---|---|
| **WhatsApp** | Meta opt-in; approved template per purpose; free service window for replies (24h customer-service reply; 72h ad-click entry-point); frequency cap. (NOT DLT — that's SMS/voice.) |
| **SMS** | DLT-registered header + template (on the **brand's** DLT entity, never commingled); NCPR/DND; 9am–9pm; frequency cap. |
| **Voice / AI calls** | NCPR/DND (two-layer: brand list + NCPR); 9am–9pm window gated at **queue level** (pre-09:00 held in `pending_window`, flushed at 09:00; post-21:00 rescheduled); **automated-agent disclosure** at call open; **recording consent** (proceed without retention if declined); frequency cap. |
| **Email** | Opt-in/unsubscribe honored; suppression on withdrawal; CAN-SPAM-equivalent footer. |
| **Ad custom audiences** | Consent state + suppression list applied before push to Meta/Google. |

### 2.2 Calling-hours gating is at the queue, not the dialer
Calls/SMS scheduled outside 09:00–21:00 IST never reach the provider — they sit in `pending_window` and flush at the window open. This makes "0 out-of-window attempts" a structural guarantee, not a runtime hope.

---

## 3. Consent primitive (one model, all channels)

Built once in `core-service` (`consent/`), consumed by every outbound path (Single-Primitive Rule).

```sql
lifecycle.consent_event(                    -- append-only
  id, workspace_id, customer_id, channel,   -- email/sms/whatsapp/call/ads_custom_audience/all
  old_status, new_status,                    -- opted_in/opted_out/withdrawn/unknown
  purpose,                                   -- marketing/transactional
  source, region, recorded_at, metadata)
lifecycle.customer_consent_current(          -- materialized current state
  workspace_id, customer_id, channel, status, purpose, updated_at,
  PRIMARY KEY (workspace_id, customer_id, channel, purpose))
```

- Tracked by **customer × channel × purpose × source × timestamp × region × withdrawal**.
- **Transactional vs marketing:** support replies can continue where legally transactional even if marketing consent is withdrawn; marketing upsells cannot.
- **Consent Managers (DPDP, ~Nov 2026):** model is forward-compatible — a `source = 'consent_manager'` with the manager's reference lets Brain honor consent granted/withdrawn via a registered third-party Consent Manager.

---

## 4. Data lifecycle (DPDP/PDPL)

### 4.1 Minimization & what Brain never stores
Card numbers, CVV, full UPI IDs, full bank accounts, plaintext passwords, national IDs (Aadhaar), special-category data, full addresses unless explicitly required+approved (default **pincode/city-level**), PII in logs. (Mirrors §21.1.)

### 4.2 PII at rest & in transit
Hash email/phone by default (`email_hash`, `phone_hash` `FixedString(64)` in CH); plaintext contact only where outreach is enabled + consent/legal basis exists, encrypted via KMS. PII redaction at the logger (`pylibs/brain_logger`) **and** at Fluent Bit (Lua scrub) before OpenSearch. TLS everywhere; mobile cert-pinning.

### 4.3 Data residency (default, not enterprise-only)
**Indian customer data is stored in-region (ap-south-1) by default** — Supabase project, MSK cluster, ClickHouse, and S3 all in-region. UAE/KSA workspaces (Phase 4) store in the region matching PDPL transfer rules. Cross-region replication only where a workspace's `aws_primary_region` permits. (Resolution R8/R9.)

### 4.4 Right to erasure & export
```
Erasure request (brand-initiated, on behalf of a data principal)
  → core-service erasure orchestrator
  → tombstone customer in Postgres (RLS-scoped) + hard-delete plaintext PII
  → ClickHouse: delete-by-customer (ALTER TABLE ... DELETE WHERE workspace_id=? AND customer_id=?)
  → S3: purge raw payloads referencing the customer (lifecycle policy + targeted delete)
  → suppress in all audiences + consent set to 'withdrawn'
  → write audit.audit_log entry; do NOT delete the audit entry itself (legal record, PII-free)
```
Export: machine-readable bundle of the customer's stored data, workspace-scoped, signed-S3 delivered. Aggregated/anonymized analytics may be retained where legally permitted (DPDP allows de-identified retention).

### 4.5 Retention
Per `01_data_architecture.md` §11: raw 5y, `*_recent` 90d, canonical/daily-metrics forever (de-identified where required), `audit_log` 7y, soft-deleted workspaces hard-deleted at 90d. Retention windows are enforced by scheduled jobs, not manual cleanup.

### 4.6 Breach notification
On suspected breach: Sentry P1 → on-call → scoped impact assessment (which workspaces/data principals) → notify affected brand(s) (controllers) within the regime's window so they can fulfil their data-principal notice obligations → post-mortem in `audit`.

---

## 5. Cross-brand benchmark privacy
Raw data never leaves a workspace partition. Benchmarks are aggregate + anonymized, **k-anonymity k≥5** enforced in schema (`ai.cross_brand_pattern.brand_count CHECK (>=5)`). Brand opts in (via DPA) to contribute; receives patterns regardless. No single-brand model training without explicit written opt-in.

---

## 6. Compliance test matrix (Tanvi/QA VETO gates)

| Check | Assertion |
|---|---|
| Calling-hours | No SMS/voice send leaves the queue outside 09:00–21:00 IST (workspace tz) |
| DND/NCPR | Every dial/SMS checked against brand list **and** NCPR; blocked count surfaced |
| DLT | 100% of SMS/voice-follow-up templates registered on the brand's DLT entity |
| WhatsApp | No template send without Meta approval + opt-in; service-window replies free |
| Consent | Marketing send to `opted_out`/`withdrawn` = test failure |
| Frequency | No customer contacted >1×/48h (except approved VIP override, logged) |
| AI-call disclosure | Every AI call opens with automated-agent disclosure |
| Recording consent | Recording suppressed where declined |
| Residency | Indian workspace data never written outside ap-south-1 |
| Erasure | Erasure removes plaintext PII across PG + CH + S3 + audiences; audit entry retained |
| Logs | No PII in OpenSearch (redaction verified at logger + Fluent Bit) |

### Compliance SLOs
- DND/NCPR-blocked attempts that **leaked**: **0** (rule violation if non-zero).
- Out-of-window send attempts: **0**.
- Cross-brand data leaks: **0**.
- PII-in-logs incidents: **0**.

---

## 7. Phase mapping

| Phase | Compliance scope |
|---|---|
| 0–1 | Consent primitive + DPDP minimization + in-region residency + PII redaction + audit log (no outbound yet) |
| 2 | Full compliance engine live with first outbound (WhatsApp + COD-confirm calls): DLT, NCPR/DND, calling hours, frequency caps, recording consent |
| 3 | Inbound consent capture; erasure/export self-serve; Consent-Manager-ready hooks |
| 4 | UAE/KSA PDPL adapters (Arabic opt-out language, transfer controls); SOC 2 readiness; DPA + sub-processor list maturity |

---

## 8. Open questions

| # | Question | Resolution path |
|---|---|---|
| 1 | DLT entity sign-up at onboarding | Self-serve onboarding step triggering BSP (Gupshup) DLT registration; cached entity id |
| 2 | Consent-Manager integration timing | Build hooks Phase 3; activate when registered Consent Managers are operational (~Nov 2026+) |
| 3 | SOC 2 Type 1/2 | Phase 4 (enterprise demand); vulnerability-scanning + audit foundations laid earlier |
| 4 | Per-region NCPR-equivalents for GCC | Phase 4 with UAE/KSA adapters |
| 5 | DPA + sub-processor list publication | Founder/Legal before first paying brand |
