---
name: decision-log
description: Brain's Decision Log (`ai.decision_log`) — THE MOAT. The append-update ledger that records every condition → recommendation → approval/edit/execution/reversal → 7d/30d outcome. Auto-load whenever an agent emits a recommendation, an MCP write tool fires, a lifecycle send / support resolution / auto-execute / reversal happens, or you wire the nightly outcome-attribution jobs. Every recommendation creates a row BEFORE display; MCP write tools auto-write via middleware; a workflow that cannot write here is not a Brain action. Money fields are minor units. Feeds Condition-Outcome memory (the learning loop).
---

# Decision Log — Brain's Moat

The Decision Log is **mandatory infrastructure, not a reporting add-on** (business §7.1). It is the append-then-update ledger of every decision Brain touches: the condition that was true, what Brain recommended, what the Owner did, what executed, whether it was reversed, and what happened 7 and 30 days later. After 12 months a competitor with the same dashboards and integrations still cannot match a brand's Brain — because they don't have its accumulated condition→outcome pairs. **Memory is the moat; the Decision Log is where it is written.**

> **The one rule:** *A workflow that cannot write here is not a Brain action.* No recommendation, approval, lifecycle send, support resolution, auto-execution, courier change, refund, guardrail block, or reversal exists unless it is logged (technical-requirements Iron Rule #9).

**Canonical doc:** `canon/technical-requirements.md` §9.3 + `canon/business-requirements.md` §7 + `canon/TECH/05_intelligence_layer.md`. Owned by **analytics-service** (Decision Log writes + outcome backfills); written *through* api-gateway MCP middleware and intelligence-service agents.

## The schema — `ai.decision_log` (technical-requirements §9.3)

```sql
ai.decision_log(
  id, workspace_id, agent_group, agent_name,
  decision_type, action_type, status,            -- proposed/approved/rejected/edited/queued/auto_executed/blocked/executed/reversed/failed/observed
  priority_score, confidence, risk_level, reversibility,
  channel,                                        -- call/whatsapp/email/sms/ad_audience/no_action
  title, explanation, input_snapshot JSONB, evidence_refs JSONB,
  proposed_action JSONB, expected_impact JSONB, user_response JSONB, executed_action JSONB, reversal JSONB,
  outcome_7d JSONB, outcome_30d JSONB,
  attributed_revenue_minor BIGINT, attributed_cm2_minor BIGINT,
  recovered_revenue_7d_minor BIGINT, recovered_revenue_30d_minor BIGINT,
  learning_note TEXT, created_by DEFAULT 'brain', created_at, updated_at)
-- indexes: (workspace_id, created_at DESC), (workspace_id, agent_name, status), (workspace_id, action_type)
```

`workspace_id` leads every index (multi-tenant; RLS-scoped). **All money is integer minor units + currency (BIGINT, never float/NUMERIC)** — `attributed_revenue_minor`, `attributed_cm2_minor`, `recovered_revenue_7d_minor`, `recovered_revenue_30d_minor`. JSONB columns carry the structured envelopes; promote a frequently-queried field to a generated column + index rather than scanning JSONB.

## Every field, and what it carries (business §7.2 contract ↔ schema column)

| Field (business contract) | `ai.decision_log` column | Meaning |
|---|---|---|
| **decision_id** | `id` | Unique immutable ID for the decision. |
| **workspace_id** | `workspace_id` | Brand/workspace isolation key (RLS leads on it). |
| **actor** | `created_by` + `agent_group`/`agent_name` | Who acted: `brain_agent` (e.g. `aicmo-meta`), `user`, `automation`, `external_api`, `system_guardrail`. |
| **domain** | `decision_type` | marketing / lifecycle / support / logistics / inventory / finance / pricing / compliance / product. |
| **trigger** | (in `input_snapshot`) | anomaly / schedule / user_query / ticket / campaign_event / stock_event / integration_event / manual_log. |
| **condition_snapshot** | `input_snapshot` JSONB | Structured metrics true at decision time (the *condition*). |
| **recommendation** | `title` + `explanation` | Human-readable summary shown to the Owner. |
| **action_payload** | `proposed_action` JSONB | Structured, executable action (e.g. `{tool, args}` for the MCP write-back). |
| **expected_impact** | `expected_impact` JSONB | Projected revenue / CM2 / cost / time / risk. |
| **confidence** | `confidence` | Numeric score + reason. |
| **risk** | `risk_level` | low / medium / high / critical. |
| **reversibility** | `reversibility` | reversible / partially_reversible / irreversible (irreversible → Owner-only). |
| **approval_state** | `status` | proposed → approved/rejected/edited → queued → auto_executed/blocked → executed → reversed/failed → observed. |
| **execution_state** | (in `status` + `executed_action`) | not_started / queued / sent / executed / failed / reversed. |
| **channel** | `channel` + `evidence_refs` | Where the action happened (call/whatsapp/email/sms/ad_audience/no_action) + provider refs. |
| **cost** | (in `executed_action`/`expected_impact`) | Message, call, discount, ad spend, or refund cost (minor units). |
| **revenue_attributed** | `attributed_revenue_minor` + `attributed_cm2_minor` | Placed / realized / CM2 revenue tied to this decision. |
| **outcome_7d** | `outcome_7d` JSONB + `recovered_revenue_7d_minor` | Structured outcome 7 days later. |
| **outcome_30d** | `outcome_30d` JSONB + `recovered_revenue_30d_minor` | Structured outcome 30 days later. |
| **learning_note** | `learning_note` | Short note: what should change next time (feeds future recs). |

`user_response` (approve/reject/edit payload) and `reversal` (what was undone, when) round out the lifecycle of a row.

## The write lifecycle — create-before-display, then update

```
agent daily tick / NL query / ticket / anomaly
   ▼
INSERT row  status='proposed'              ◀── BEFORE the recommendation is ever displayed
   ▼
Owner sees it (Morning Brief / Home / web)
   ├─ approve → UPDATE status='approved',  user_response={...}
   ├─ edit    → UPDATE status='edited',    user_response={edited_action}
   ├─ reject  → UPDATE status='rejected',  user_response={reason}   (no write fires)
   └─ (graduated agent) → status='auto_executed'
   ▼
MCP write tool fires → UPDATE executed_action={...}, status='executed'  (or 'blocked'/'failed')
   ▼  (if undone)
reversal → UPDATE reversal={...}, status='reversed'
   ▼  nightly (23:55 IST, analytics-service)
7d job  → UPDATE outcome_7d,  attributed_*_minor, recovered_revenue_7d_minor
30d job → UPDATE outcome_30d, recovered_revenue_30d_minor, learning_note
```

**The row is created before anything is shown to a human.** A recommendation that reaches the UI without a `proposed` row already in `ai.decision_log` is a bug. Subsequent state changes (approve / edit / execute / reverse) **update the same row** — the Decision Log is append-with-status-transitions, not delete-and-rewrite.

## MCP write tools auto-write via middleware

Every MCP **write** tool (`integrations.*.write`, `lifecycle.outreach.*`, `lifecycle.call.place`, `core.consent.update`, `core.goal.set`, refunds/replacements, budget changes) auto-writes/updates the Decision Log **through gateway middleware** — the handler never has to remember (technical-requirements §10, MCP contract). Tool schemas generate from the same protos as gRPC, so the action payload logged matches the action executed (cannot drift). Writing to an external API directly — bypassing the `mcpTool({...})` path — skips the Decision Log and is a code-review blocker.

```python
# What the middleware does on every write-tool invocation (conceptual)
async def decision_log_middleware(tool, args, ctx, next_):
    row = await decision_log.upsert_proposed(workspace_id=ctx.workspace_id, action_type=tool.name,
                                             proposed_action=args, created_by=ctx.actor)   # before execute
    try:
        result = await next_(args, ctx)
        await decision_log.mark_executed(row.id, executed_action=result)
        return result
    except GuardrailBlocked as e:
        await decision_log.mark(row.id, status="blocked", reversal={"reason": str(e)}); raise
    except Exception as e:
        await decision_log.mark(row.id, status="failed"); raise
```

## Nightly outcome attribution (7d / 30d) — analytics-service

The **23:55 IST** attribution job (paradigm 1 — SQL; almost-zero LLM cost) walks decisions whose outcome window has matured and backfills `outcome_7d` / `outcome_30d`, `attributed_revenue_minor`, `attributed_cm2_minor`, and `recovered_revenue_*_minor` from realized order/shipment/refund facts in ClickHouse. **Attribution is on realized revenue + CM2, never placed.** Recovered-revenue attribution from `lifecycle.recovered_revenue.attributed.v1` flows back into the same rows. This is also when each matured decision becomes a **Condition-Outcome pair** (below).

## The Kafka topic — `intelligence.decision.logged.v1` (retained forever)

Every Decision Log write emits `intelligence.decision.logged.v1` (envelope keyed by `workspace_id`). **Retention is infinite** (MSK tiered storage → S3) — the Decision Log topic is one of the two never-expiring topic classes (the other is raw integrations). Downstream consumers: analytics (attribution), notifications (digests/audit), audit. Because the topic is replayable forever, any downstream materialization of decisions can be rebuilt from scratch.

## How it feeds Condition-Outcome memory — the learning loop

When a decision's outcome matures, it becomes a row in `ai.condition_outcome` (Postgres + pgvector), linked by `decision_log_id`, carrying the **16-dim Brand Fingerprint at decision time** (`brand_fingerprint_at_decision vector(16)`), the recommendation, whether it was approved/auto-executed, and the 7d/30d outcome + recovered revenue. Every agent, on every daily tick, runs a pgvector cosine k-NN: *"find the 5 most similar past conditions for this brand and what happened."*

```
condition = what was true   →  recommendation = what Brain suggested
action    = what was done   →  outcome = what happened at 7d/30d  →  learning = what to change next
```

This is the engine of compounding learning (business §7.4; TECH/05 §0.3): Brain gets measurably better at decisions for *that specific brand* because every prior decision + outcome lives here. It runs at SQL economics, so agents query it constantly — see `memory-layer-pgvector` and `agentic-design`.

## Verification / anti-patterns (code-review blockers)

- **Agent recommendation with no `ai.decision_log` row** → blocker. Every agent method that emits a `Recommendation` MUST insert a `proposed` row before the rec can surface. Detection: a Morning Brief / Insights item with no `decision_log_id`.
- **External write that bypasses the MCP middleware** → blocker. Calling Meta/Google/Shopify/Razorpay/Shiprocket/BSP SDKs directly skips the auto-write. Always go through `mcpTool({...})`.
- **Float / NUMERIC money** on `attributed_revenue_minor` / `attributed_cm2_minor` / `recovered_revenue_*_minor` → blocker. Integer minor units + `currency_code` only.
- **Attribution on placed (not realized) revenue** → wrong number; outcome jobs read realized facts.
- **Missing `workspace_id`** on a row or the topic envelope → cross-brand leak risk (P0).
- **Delete-then-reinsert on status change** → breaks the immutable `id` + the `condition_outcome` FK. Update the existing row.
- **Decision Log write availability** is an SLO: **> 99.99%** (technical-requirements §14). A dropped write is lost moat — alert, retry via transactional outbox, never silently swallow.
- **Reversal with no logged `reversal` payload** → an un-auditable undo; auto-execute reversals MUST update the row.

## References

- `canon/technical-requirements.md` §9.3 — `ai.decision_log` schema + the create-before-display rule
- `canon/business-requirements.md` §7 — Decision Log principle, fields (§7.2), Condition-Outcome memory (§7.4)
- `canon/TECH/05_intelligence_layer.md` §0.3 — Condition-Outcome Pair Log + the daily learning-loop query
- `skills/mcp-protocol/SKILL.md` — write tools auto-write Decision Log via middleware
- `skills/agentic-design/SKILL.md` — agents emit recommendations as `proposed` rows
- `skills/memory-layer-pgvector/SKILL.md` — Brand Fingerprint + Condition-Outcome retrieval
- `skills/agentic-actions-auditor/SKILL.md` — auditing agent-emitted actions before they execute
- `skills/multi-tenancy-isolation/SKILL.md` — `workspace_id` enforcement on the row + topic envelope
