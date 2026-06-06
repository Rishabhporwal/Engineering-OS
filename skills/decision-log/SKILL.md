---
name: decision-log
description: The system-of-record audit-log discipline (where the product's Canon requires one) — append-then-update ledger of consequential actions and their outcomes. Create-before-display; write tools auto-log. Distinct from the OS's own .engineering-os/ trail.
---

# System-of-Record Audit Log — the consequential-action ledger

Where the Product Canon requires a **system-of-record audit log** (declared in `THE-MOAT.md` / `COMPLIANCE.md` / the data architecture), it is **mandatory infrastructure, not a reporting add-on**. It is the append-then-update ledger of every consequential action the product takes: the condition that was true, what was recommended, what the operator did, what executed, whether it was reversed, and what happened later (e.g. 7 and 30 days on). For products whose moat is accumulated condition→outcome experience, this ledger is *where the moat is written* — a competitor with the same dashboards and integrations still can't match a tenant's accumulated history.

> **This is the product's own audit log — not the OS's.** The Engineering OS keeps its *own* operational audit trail under `.engineering-os/` (journals + audit-log lines; principle 1 in the system prompt). This skill is about the **product feature** the Canon may require. Don't conflate the two.

> **The one rule (where the Canon requires this log):** *A workflow that cannot write here is not complete.* No recommendation, approval, send, resolution, auto-execution, change, refund, guardrail block, or reversal exists unless it is logged.

**Canon:** the Product Canon's `THE-MOAT.md` (whether this log exists and why) + the data architecture HLD/LLD + `COMPLIANCE.md` (retention/immutability requirements). Owned by whichever service the Canon assigns; written *through* the API gateway's write-tool middleware.

## The schema (representative shape)

```sql
decision_log(
  id, tenant_id, actor_group, actor_name,
  decision_type, action_type, status,            -- proposed/approved/rejected/edited/queued/auto_executed/blocked/executed/reversed/failed/observed
  priority_score, confidence, risk_level, reversibility,
  channel,
  title, explanation, input_snapshot JSONB, evidence_refs JSONB,
  proposed_action JSONB, expected_impact JSONB, actor_response JSONB, executed_action JSONB, reversal JSONB,
  outcome_short JSONB, outcome_long JSONB,        -- e.g. 7d / 30d windows
  attributed_value_minor BIGINT, recovered_value_short_minor BIGINT, recovered_value_long_minor BIGINT,
  learning_note TEXT, created_by, created_at, updated_at)
-- indexes: (tenant_id, created_at DESC), (tenant_id, actor_name, status), (tenant_id, action_type)
```

The **tenant-isolation key leads every index** (multi-tenant; RLS-scoped — see `multi-tenancy-isolation`). **All money is integer minor units + a `currency_code` (BIGINT, never float/NUMERIC).** JSONB columns carry the structured envelopes; promote a frequently-queried field to a generated column + index rather than scanning JSONB.

## Every field, and what it carries

| Field (contract) | column | Meaning |
|---|---|---|
| **decision_id** | `id` | Unique immutable ID for the decision. |
| **tenant_id** | `tenant_id` | Tenant isolation key (RLS leads on it). |
| **actor** | `created_by` + `actor_group`/`actor_name` | Who acted: an automated agent, a user, an automation, an external API, or a system guardrail. |
| **domain** | `decision_type` | The business domain the decision belongs to. |
| **trigger** | (in `input_snapshot`) | anomaly / schedule / user_query / event / manual_log. |
| **condition_snapshot** | `input_snapshot` JSONB | Structured metrics true at decision time (the *condition*). |
| **recommendation** | `title` + `explanation` | Human-readable summary shown to the operator. |
| **action_payload** | `proposed_action` JSONB | Structured, executable action (e.g. `{tool, args}` for the write-back). |
| **expected_impact** | `expected_impact` JSONB | Projected value / cost / time / risk. |
| **confidence** | `confidence` | Numeric score + reason. |
| **risk** | `risk_level` | low / medium / high / critical. |
| **reversibility** | `reversibility` | reversible / partially_reversible / irreversible (irreversible → operator-only). |
| **approval_state** | `status` | proposed → approved/rejected/edited → queued → auto_executed/blocked → executed → reversed/failed → observed. |
| **execution_state** | (in `status` + `executed_action`) | not_started / queued / sent / executed / failed / reversed. |
| **channel** | `channel` + `evidence_refs` | Where the action happened + provider refs. |
| **cost** | (in `executed_action`/`expected_impact`) | Cost of the action (minor units). |
| **value_attributed** | `attributed_value_minor` | Realized value tied to this decision. |
| **outcome_short / outcome_long** | `outcome_short` / `outcome_long` JSONB + the `recovered_value_*_minor` columns | Structured outcome at the maturity windows. |
| **learning_note** | `learning_note` | Short note: what should change next time (feeds future recommendations). |

`actor_response` (approve/reject/edit payload) and `reversal` (what was undone, when) round out the lifecycle of a row.

## The write lifecycle — create-before-display, then update

```
trigger (tick / query / event / anomaly)
   ▼
INSERT row  status='proposed'              ◀── BEFORE the recommendation is ever displayed
   ▼
operator sees it
   ├─ approve → UPDATE status='approved',  actor_response={...}
   ├─ edit    → UPDATE status='edited',    actor_response={edited_action}
   ├─ reject  → UPDATE status='rejected',  actor_response={reason}   (no write fires)
   └─ (auto-execute, where allowed) → status='auto_executed'
   ▼
write tool fires → UPDATE executed_action={...}, status='executed'  (or 'blocked'/'failed')
   ▼  (if undone)
reversal → UPDATE reversal={...}, status='reversed'
   ▼  later (scheduled, off-peak)
short-window job → UPDATE outcome_short, attributed_value_minor, recovered_value_short_minor
long-window job  → UPDATE outcome_long,  recovered_value_long_minor, learning_note
```

**The row is created before anything is shown to a human.** A recommendation that reaches the UI without a `proposed` row already in the log is a bug. Subsequent state changes **update the same row** — append-with-status-transitions, not delete-and-rewrite.

## Write tools auto-write via middleware

Every **write** tool (an outbound send, a refund, a config/budget change, an external-system write) auto-writes/updates the audit log **through gateway middleware** — the handler never has to remember. Tool schemas generate from the same contracts as the RPC layer, so the action payload logged matches the action executed (cannot drift). Writing to an external API directly — bypassing the write-tool path — skips the audit log and is a code-review blocker. See `mcp-protocol`.

```python
# What the middleware does on every write-tool invocation (conceptual)
async def audit_log_middleware(tool, args, ctx, next_):
    row = await audit_log.upsert_proposed(tenant_id=ctx.tenant_id, action_type=tool.name,
                                          proposed_action=args, created_by=ctx.actor)   # before execute
    try:
        result = await next_(args, ctx)
        await audit_log.mark_executed(row.id, executed_action=result)
        return result
    except GuardrailBlocked as e:
        await audit_log.mark(row.id, status="blocked", reversal={"reason": str(e)}); raise
    except Exception:
        await audit_log.mark(row.id, status="failed"); raise
```

## Outcome attribution (maturity windows)

A scheduled, off-peak attribution job (tier 1 — deterministic; near-zero model cost) walks decisions whose outcome window has matured and backfills `outcome_short` / `outcome_long` and the `attributed_value_minor` / `recovered_value_*_minor` columns from realized facts in the OLAP store. **Attribution is on realized value, never projected.**

## The event topic (retained per the Canon)

Every audit-log write can emit an event (envelope keyed by the tenant key) so downstream consumers (attribution, digests, audit) stay decoupled. Where the Canon makes this log the moat, its topic is in the **retain-forever** class so any downstream materialization can be rebuilt from scratch.

## How it can feed a learning loop (where the product has one)

When a decision's outcome matures, it can become a row in a condition-outcome store (e.g. Postgres + a vector index), linked by `decision_log_id`, carrying the condition at decision time, the recommendation, whether it was approved/auto-executed, and the matured outcome. A recommender can then run a vector similarity query: *"find the most similar past conditions and what happened."*

```
condition = what was true   →  recommendation = what was suggested
action    = what was done   →  outcome = what happened later  →  learning = what to change next
```

This is the engine of compounding learning, at deterministic/ML economics. Retrieval mechanics and agent wiring are product features — see `examples/brain-instantiation/` for one concrete instantiation.

## Verification / anti-patterns (code-review blockers)

- **A recommendation with no `proposed` log row** → blocker. Every path that emits a recommendation MUST insert a `proposed` row before it can surface.
- **An external write that bypasses the write-tool middleware** → blocker. Calling a provider SDK directly skips the auto-write. Always go through the write-tool path.
- **Float / NUMERIC money** on any `*_minor` column → blocker. Integer minor units + `currency_code` only.
- **Attribution on projected (not realized) value** → wrong number; outcome jobs read realized facts.
- **Missing tenant key** on a row or the event envelope → cross-tenant leak risk (P0).
- **Delete-then-reinsert on status change** → breaks the immutable `id` + any downstream FK. Update the existing row.
- **Audit-log write availability is an SLO** (the Canon sets the target, e.g. > 99.99%). A dropped write is lost record — alert, retry via a transactional outbox, never silently swallow.
- **Reversal with no logged `reversal` payload** → an un-auditable undo; auto-execute reversals MUST update the row.

## References

- The Product Canon's `THE-MOAT.md` (whether this log exists + why) + the data-architecture HLD/LLD + `COMPLIANCE.md` (retention/immutability)
- `mcp-protocol` · `multi-tenancy-isolation` · `agentic-safety` (auditing agent-emitted write-backs)
- For one concrete instantiation of this log as a product moat, see `examples/brain-instantiation/`
