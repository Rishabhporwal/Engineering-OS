---
name: audit-log-immutability
description: Tamper-evidence for Brain's audit trail + Decision Log (the moat). WORM via S3 Object Lock (compliance mode); hash-chaining / append-only enforcement at the DB layer; why the Decision Log's append-then-update (status transitions only — never silent edit/delete) must be provably tamper-evident; 7-year audit retention integrity; and how you PROVE integrity to a SOC 2 / ISO 27001 auditor. Use when designing audit/Decision-Log persistence, wiring the S3 mirror, reviewing any code that touches audit_log or ai.decision_log, or prepping evidence for an auditor. Owner: Shreya + Vikram.
---

# Audit-log immutability — make the trail tamper-evident

Two ledgers carry Brain's integrity story: `audit_log` (who did what — TECH/09 §6) and `ai.decision_log` (the moat: every condition→recommendation→outcome — `decision-log`). Both are written append-style today, but "append-only by convention" is not the same as "provably unaltered." An enterprise buyer's security team — and a SOC 2 / ISO 27001 auditor — will ask: *can a Brain engineer with DB access silently rewrite a decision or delete an audit row, and would anyone know?* This skill makes the answer demonstrably **no**.

> **The one rule:** *the audit trail and the Decision Log are append-only and tamper-evident — any alteration is either physically prevented (WORM) or cryptographically detectable (hash chain), and we can prove it on demand.*

**Canonical source:** TECH/09 §6 (audit_log + S3 mirror, 7-year retention) + §17 open-Q "Audit log to immutable S3 (Object Lock)? Phase 3", TECH/16 §4.4–4.5 (erasure retains the audit entry; retention windows). Owned by **Shreya** (security/compliance VETO) + **Vikram** (data layer). The Decision Log's write-availability SLO is **>99.99%** — a dropped or altered write is lost moat.

## Three layers of tamper-evidence

### 1. WORM at the object store — S3 Object Lock (compliance mode)

The audit mirror + Decision Log topic archive land in S3 buckets with **Object Lock in COMPLIANCE mode** + a retention period — write-once-read-many. Under compliance mode **no one — not the root account, not an admin — can delete or overwrite an object before its retention expires.** This is the hard physical guarantee; everything else is defense in depth.

```
audit_log (Postgres, hot)  ──Kinesis Firehose──▶  s3://brain-audit/  (Object Lock COMPLIANCE, 7y)
ai.decision_log writes  ──intelligence.decision.logged.v1──▶  MSK tiered storage ▶ s3 archive
                                                            (Decision Log topic = infinite retention)
```

- **Compliance mode, not Governance mode** — Governance can be bypassed by a privileged user with `BypassGovernanceRetention`; compliance cannot. For a legal/audit record, use compliance.
- **Retention = 7 years** for `audit_log` (matches §6 + TECH/16 §4.5); the Decision Log archive is effectively permanent (MSK tiered storage → S3, one of Brain's two never-expiring topic classes).
- **Versioning ON** + MFA-delete on the bucket as belt-and-braces. SSE-KMS with the per-environment key.

### 2. Append-only enforcement at the DB layer

Postgres `audit_log` and `ai.decision_log` must reject `DELETE` and reject the *wrong kind* of `UPDATE` structurally, not by hoping the app behaves:

- **No `DELETE`** for any role except the scheduled retention job (and that only past the legal window). Revoke `DELETE` from every service role; the only deletion is the time-boxed retention job (TECH/16 §4.5), and **erasure tombstones PII without deleting the audit row** (the audit entry is PII-free and legally retained — TECH/16 §4.4).
- **`audit_log` is insert-only** — revoke `UPDATE` entirely. An audit row is never edited.
- **`ai.decision_log` allows status-transition UPDATEs only** — see below. A `BEFORE UPDATE` trigger rejects any change to immutable columns (`id`, `workspace_id`, `created_at`, `input_snapshot`, `proposed_action`, `agent_name`) and validates the `status` transition is legal (e.g. `executed → reversed` ok; `executed → proposed` rejected). Delete-then-reinsert is blocked (it would break the immutable `id` + the `condition_outcome` FK).

### 3. Hash-chaining (append-then-verify)

Each appended row carries a hash of its own canonical content **plus the prior row's hash**, per partition (`workspace_id`). Altering any historical row breaks every subsequent hash — detectable by re-walking the chain.

```
row_n.row_hash = SHA256( canonical(row_n.payload) || row_{n-1}.row_hash )    -- prev_hash chained
```

- Store `row_hash` + `prev_hash` columns; the genesis row chains from a constant seed per `(workspace_id, ledger)`.
- A nightly **integrity verifier** (paradigm 1 — SQL/CPU, no LLM) re-walks each chain and compares against periodic **anchor hashes** written to the Object-Lock bucket (so even a full-table rewrite is caught against the WORM anchor). Mismatch → Sentry P1 + Shreya page.
- For the Decision Log specifically, the chain covers the row's **terminal** content snapshot at each status transition, so the *history of transitions* (proposed → approved → executed → reversed) is itself tamper-evident, not just the final state.

## Why append-then-update (Decision Log) still must be tamper-evident

The Decision Log is deliberately **append-with-status-transitions**, not append-only-immutable (`decision-log`): one row's `status` legitimately moves proposed → approved/edited → executed → reversed → observed, and nightly jobs backfill `outcome_7d`/`outcome_30d`. That mutability is the point — but it is exactly why it needs tamper-evidence:

- **Legal/observed updates** (status transition, outcome backfill, user_response) are allowed and chained — each transition extends the hash chain.
- **Illegal updates** (rewriting `input_snapshot` to change what condition was "true," editing `proposed_action` after the fact, deleting a rejected rec) are **blocked by the trigger and would break the chain** if forced via direct SQL. The distinction — *transition, not silent edit* — is enforced, not trusted. This is what lets Brain claim the moat is real: a competitor can't fake their condition→outcome history because Brain's own engineers structurally can't either.

## Proving integrity to a SOC 2 / ISO 27001 auditor

The evidence package (collect as-you-build, per `soc2-readiness`):

| Auditor question | Evidence artifact |
|---|---|
| "Can audit records be deleted/altered?" | S3 Object Lock **compliance-mode** config + retention; revoked `DELETE`/`UPDATE` grants on `audit_log` |
| "How do you detect tampering?" | Hash-chain schema + the nightly verifier's run logs + anchor hashes in WORM |
| "Show an integrity check passing" | Verifier output: every chain walks clean to its WORM anchor for the period |
| "Retention meets policy?" | Object Lock 7y + retention-job schedule + TECH/16 §4.5 mapping |
| "Erasure vs audit retention conflict?" | TECH/16 §4.4: PII tombstoned, PII-free audit row retained — documented + tested |

Maps to SOC 2 TSC **CC7.x** (monitoring), **PI1.x** (processing integrity), **C1.x** (confidentiality) and ISO 27001 **A.8.15 (logging)** + **A.8.16 (monitoring)**.

## Anti-patterns (code-review blockers / Shreya VETO)

- **`DELETE` granted** on `audit_log` / `ai.decision_log` to a service role (only the time-boxed retention job, past the window).
- **Delete-then-reinsert** on a Decision Log status change (breaks `id` + the `condition_outcome` FK + the chain).
- **Editing an immutable Decision Log column** (`input_snapshot`, `proposed_action`, `created_at`) — that's falsifying history, not a status transition.
- **S3 Object Lock in Governance mode** (bypassable) for a legal audit record — use Compliance mode.
- **No integrity verifier** / no WORM anchor — a hash chain you never check is decoration.
- **Erasure that deletes the audit row** instead of tombstoning PII and keeping the row.
- Treating "Object Lock to immutable S3" as a Phase-3 nice-to-have when an enterprise deal needs it — bring it forward when the deal does.

## Verify

- Attempt `DELETE FROM audit_log` / `UPDATE ai.decision_log SET input_snapshot=...` as a service role → rejected by grants/trigger.
- Attempt to delete an object in the audit bucket before retention expiry → denied by Object Lock.
- Tamper with a historical row in a staging copy → the nightly verifier flags the broken chain against the WORM anchor.
- Run an erasure → plaintext PII gone across PG/CH/S3/audiences, the `audit_log` entry remains, chain still walks clean.

## References
- TECH/09 §6 (audit_log, S3 Firehose mirror, 7y) + §17 (Object Lock open question)
- TECH/16 §4.4 (erasure retains audit entry) + §4.5 (retention windows)
- [`decision-log`](../decision-log/SKILL.md) — the append-then-update lifecycle this protects
- [`security-baseline`](../security-baseline/SKILL.md) — Shreya VETO + A09 logging integrity
- [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md) — `workspace_id` partitions the chains
- [`soc2-readiness`](../soc2-readiness/SKILL.md) — where this becomes CC7/PI1/C1 evidence
- [`database-design`](../database-design/SKILL.md) — triggers, grants, retention jobs at the data layer
