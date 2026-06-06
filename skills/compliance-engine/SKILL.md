---
name: compliance-engine
description: The generic compliance-enforcement machinery — enforces whatever regulatory regime the Product Canon's COMPLIANCE.md declares (data protection, residency, retention, consent, channel rules). Security Reviewer VETO.
---

# Compliance Engine — the machinery that enforces the declared regime

The OS carries **no specific regulatory knowledge** — regimes are domain- and jurisdiction-specific and live in the Product Canon (`COMPLIANCE.md`). This skill is the **machinery to enforce whatever regime the Canon declares**, as an engineered, gated capability. **Any breach blocks a release — a Security Reviewer VETO surface.** Where the product is a processor and a customer is the controller, the product supplies the tools + defaults that make the customer compliant by default. Every other security skill references THIS for the enforcement mechanics; the specific regime lives only in the Canon.

> The OS makes compliance *enforceable and provable*; the Canon makes it *specific*. This split is what lets the same OS serve one regime in one jurisdiction and a different regime in another without changing the OS. (`engineering-os-blueprint/08-technical-governance.md §5`.)

## How the regime is declared (read it from the Canon)

`COMPLIANCE.md` declares the obligations this product is held to. The OS treats each as an enforceable rule gated like any other standard. Generic examples of the kinds of obligation a regime may carry:

| Obligation class | Example shape (the Canon supplies specifics) |
|---|---|
| **Data-protection law** | lawful basis / consent for processing, purpose limitation, minimization, retention limits, right to erasure, breach notification within a window |
| **Channel / outreach rules** | registered sender identity, do-not-contact suppression lists, permitted-hours windows, per-channel opt-in + approved-template requirements |
| **Cross-border / residency** | data of a given population stays in a named region; transfers need approved safeguards |
| **Sector controls** | sensitive-data handling prohibitions, attestation/audit requirements (→ `compliance-attestation`) |

The OS does not hardcode any of these — it provides the enforcement points below and reads the parameters from the Canon.

## The compliance engine (outbound gating — NOT feature-flaggable)

Where the regime governs outbound contact, the check is hard-coded into **every** outbound path so a send/call cannot bypass it. The specific channels, windows, and suppression sources come from `COMPLIANCE.md`; the *structure* is generic:

```python
def can_contact(self, tenant_id, subject_id, channel, segment, purpose) -> ComplianceResult:
    # 1. Consent / lawful basis (per channel + purpose) — re-checked before EVERY send
    if purpose == 'marketing' and c.consent(channel) != 'opted_in':
        return ComplianceResult.blocked('consent_missing')
    if c.consent(channel) in ('opted_out','withdrawn'):
        return ComplianceResult.blocked('consent_revoked')
    # 2. Channel-specific rules (parameters from COMPLIANCE.md)
    if channel in self.windowed_channels:
        if not self.within_permitted_window(now, channel):
            return ComplianceResult.deferred('outside_permitted_window')  # held, flushed when window opens
        if c.do_not_contact or self.suppression_list.is_listed(c.address):  # two-layer suppression
            return ComplianceResult.blocked('suppressed')
        if not self.sender_registered(tenant_id, channel):
            return ComplianceResult.blocked('sender_not_registered')
    if channel in self.templated_channels and not self.template_approved(tenant_id, purpose):
        return ComplianceResult.blocked('template_not_approved')
    # 3. Frequency cap — across ALL flows
    if self.last_contact_within(tenant_id, subject_id, self.cap_hours) and not vip_override:
        return ComplianceResult.blocked('frequency_cap')
    return ComplianceResult.ok()
```

### Channel rules (generic shape; Canon fills the specifics)
| Channel class | Enforced (parameters from COMPLIANCE.md) |
|---|---|
| **Templated messaging** | opt-in; approved template per purpose; free/service window for replies; frequency cap. |
| **SMS / registered messaging** | registered sender identity + template on the **customer's own** entity (never commingled); suppression-list scrub; permitted-hours window; cap. |
| **Voice / automated calls** | two-layer suppression (own list + regulator list); permitted-hours gated **at the queue, not the dialer**; automated-agent disclosure at call open; recording consent (proceed without retention if declined); human handoff; cap. |
| **Email** | opt-in/unsubscribe honored; suppression on withdrawal; lawful-footer requirement. |
| **Ad custom audiences** | consent state + suppression applied before push to the ad platform. |

**Permitted-hours gating is at the queue:** out-of-window contacts sit in a `pending_window` queue and flush when the window opens — "0 out-of-window attempts" is a structural guarantee, not a runtime hope.

## The consent primitive (one model, all channels)

Built once and consumed by every outbound path (Single-Primitive Rule). Tracked by **subject × channel × purpose × source × timestamp × region × withdrawal**, append-only:
```sql
consent_event(                          -- append-only ledger
  tenant_id, subject_id, channel,       -- e.g. email/sms/messaging/call/ads_custom_audience/all
  old_status, new_status,               -- opted_in/opted_out/withdrawn/unknown
  purpose, source, region, recorded_at) -- purpose = marketing | transactional
subject_consent_current(...)            -- materialized; PK (tenant_id, subject_id, channel, purpose)
```
**Transactional vs marketing:** support replies may continue where legally transactional even if marketing consent is withdrawn; marketing upsells cannot. **Opt-out overrides all marketing.** Keep the `source` field forward-compatible with external consent managers (`source = 'consent_manager'`) where the regime defines them.

## Data lifecycle (per the declared regime)

- **Never store** what the regime forbids — typically: card numbers, CVV, full payment-instrument identifiers, full bank accounts, plaintext passwords, national IDs, special-category data, more PII than needed (e.g. coarse-grained location rather than full address), PII in logs. (Payment-scope boundary: `compliance-attestation`.)
- **PII at rest/in transit:** hash high-cardinality identifiers by default (`email_hash`/`phone_hash`); keep plaintext contact only where outreach is enabled + a consent/legal basis exists, encrypted via a managed KMS. Redact at the logger AND at the log-shipping layer before it reaches the log store. TLS everywhere; mobile cert-pinning.
- **Residency (where the regime requires it):** data of a named population stays in its required region by default — every data store (OLTP, OLAP, object storage, message bus) provisioned in-region. Other regions follow that regime's transfer rules. Structural enforcement lives behind the region seam (`region-and-locale`).
- **Right to erasure:** subject-initiated → tombstone in the OLTP store (tenant-scoped) + hard-delete plaintext PII → delete from the OLAP store (`ALTER TABLE ... DELETE WHERE tenant_id=? AND subject_id=?`) → purge raw object-storage payloads → suppress in all audiences + set consent → `withdrawn` → write the PII-free audit-log entry (retained). Export = signed machine-readable bundle.
- **Retention:** apply the regime's retention class per dataset (raw payloads, recent windows, de-identified canonical aggregates, audit log, soft-deleted-tenant purge horizon) — enforced by scheduled jobs.
- **Breach:** alerting fires → on-call → scoped impact → notify affected parties within the regime's window → post-mortem.

## Cross-tenant benchmark privacy (where the product aggregates across tenants)
Raw data never leaves a tenant partition. Benchmarks are aggregate + anonymized, **k-anonymity (k≥ the Canon's threshold)** enforced in schema (`CHECK (tenant_count >= N)`). Opt-in to contribute (DPA); receive patterns regardless.

## Compliance SLOs (all = 0)
Suppression-list-blocked attempts that **leaked** · out-of-window send attempts · cross-tenant data leaks · PII-in-logs incidents — each must be 0; non-zero is a rule violation.

## PII data-catalog & lineage
Erasure + breach-scope are only as fast as your knowledge of where PII lives. Maintain a **field-level PII catalog** (versioned in repo, asserted in CI) + a **lineage map** so a data-subject request is a lookup, not archaeology.

| Field | Class | Default handling |
|---|---|---|
| `phone` | direct | `phone_hash`; plaintext only w/ outreach consent (KMS) |
| `email` | direct | `email_hash`; plaintext only w/ consent (KMS) |
| `location` | direct | coarse-grained (region/area) only; full precise address never |
| `order_id` / record facts | linked | retained; tombstoned on erasure |
| name + value combo | quasi | never co-logged |

Lineage — every copy a PII field makes:
```
connector ingest → raw object storage (KMS) → OLAP raw_* → OLAP canonical
  → derived stores (e.g. vector embeddings)
  → logs (redacted at logger + log shipper) → exports (signed bundle)
```
The lineage map drives BOTH workflows: an **erasure** walks every node (OLTP tombstone + plaintext hard-delete → OLAP `DELETE` → object-storage purge → re-embed/evict derived rows → suppress in audiences/consent → keep the PII-free audit entry); a **breach** uses the same map to compute notification scope (fields × stores × tenants) within the window. A new connector or derived table is **not done** until its PII fields are in the catalog + lineage.

## Anti-patterns
- A send/call that bypasses the engine, or checks consent once instead of before every send; gating permitted hours at the dialer not the queue.
- Commingling tenants' sender registrations; sending an unapproved template; ignoring the free/service-window distinction.
- Marketing to `opted_out`/`withdrawn`; storing a forbidden data class; PII reaching logs.
- Writing residency-restricted data outside its required region; erasure that misses the OLAP store / object storage / audiences; a cross-tenant benchmark below the k-anonymity threshold.

## Verify
- An out-of-window send sits in `pending_window` and flushes when the window opens; a suppression-listed/opted-out address is blocked.
- A marketing send to a `withdrawn` consent fails; a transactional reply within the service window proceeds.
- An erasure removes plaintext PII across OLTP + OLAP + object storage + audiences; the audit entry remains.
- Grep new code paths + sample log lines for direct identifiers — none present.

## References
`engineering-os-blueprint/08-technical-governance.md §5` (compliance as an engineered capability) · the Product Canon's `COMPLIANCE.md` (the specific regime + its parameters, SLOs, test matrix) · `security-baseline` · `multi-tenancy-isolation` · `region-and-locale` (residency enforcement) · `compliance-attestation` (payment scope + audit immutability + attestation evidence). For one concrete instantiation of a regime, see `examples/brain-instantiation/`.
