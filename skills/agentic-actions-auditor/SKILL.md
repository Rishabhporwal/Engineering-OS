---
name: agentic-actions-auditor
description: Audit agent-emitted actions BEFORE they execute — MCP write-backs (pause_ad_set, reallocate budget), AI calls under DLT/NCPR, shell/SQL the agent generates, and any tool that mutates the outside world. Adapted from the Trail of Bits agentic-actions-auditor pattern. Auto-load whenever Shreya reviews an AI surface, Maya builds an MCP write tool or lifecycle action, or Aryan designs an autonomous loop. Distinct from `vulnerability-scanning` (CVE/dependency scanning) — this audits the ACTIONS the agent takes, not the libraries it imports.
---

# Agentic Actions Auditor

> An agent that can *act* is an agent that can do harm. The blast radius of a Brain agent is real money and a regulated phone line — audit every action it can emit before it ships.

Brain's agents don't just answer — they **act**: the Morning Brief approve flow fires `integrations.meta.pause_ad_set`, reallocates ad budget, and the lifecycle-service places AI calls to real customers under DLT/NCPR. A wrong action isn't a wrong answer the Founder can ignore; it's ₹50K/day moved to the wrong channel, or a call placed at 21:30 IST that triggers a TRAI complaint. This skill audits the **action surface** of any agentic feature.

This is the operational depth behind `agentic-design` (how to build the loop) and `security-baseline` (the gate). It is **distinct from `vulnerability-scanning`** — that scans dependencies for CVEs; this scans the *actions the agent can take* for blast radius, reversibility, authorization, and compliance.

## The Iron Law

```
EVERY AGENT-EMITTED ACTION MUST BE CLASSIFIED, AUTHORIZED, REVERSIBLE-OR-GATED, AND LOGGED — BEFORE IT SHIPS.
```

If an agent can emit an action you have not classified, you have not finished the audit.

## What counts as an "agent-emitted action"

Anything where the model's output causes a side effect in the world or the system:

- **MCP write tools** — `integrations.meta.pause_ad_set`, `integrations.google.update_budget`, any `*.write`/`*.mutate` tool exposed to an agent.
- **Outbound channels** — AI calls (lifecycle-service), WhatsApp/SMS/email sends.
- **Generated-and-executed code** — shell commands, SQL, migrations, or scripts the agent writes AND something runs.
- **State mutations** — DB writes, Kafka produces, cache invalidations triggered by an agent decision.
- **Spend** — anything that costs money: ad budget, LLM tokens at scale, paid API calls.
- **Privilege use** — anything using a connector's OAuth token or a service's KMS key.

If the agent only *reads* and *recommends*, and a human approves before any write, the write is the audited action — not the recommendation.

## The audit (run for EVERY action the agent can emit)

```
FOR EACH action the agent can emit:

1. CLASSIFY blast radius:
   - READ-ONLY        → low risk, note and move on
   - REVERSIBLE WRITE → e.g. pause campaign (can un-pause). Requires log + idempotency.
   - IRREVERSIBLE     → e.g. send a call/message, delete data, charge money. Requires HUMAN GATE.
   - FINANCIAL        → moves money/budget. Requires HUMAN GATE + magnitude cap + log.
   - COMPLIANCE-GATED → AI call, marketing send. Requires the full India matrix to pass FIRST.

2. AUTHORIZE:
   - Is the tool scoped to the caller's workspace_id? (multi-tenant isolation)
   - Is the OAuth scope / KMS key the minimum needed? (no "manage everything" token)
   - Is there a requireRole / requireWorkspaceMember check on the path that emits it?

3. GATE (for IRREVERSIBLE / FINANCIAL / COMPLIANCE):
   - Is there a human-in-the-loop approval before the action fires? (Morning Brief approve)
   - Is there a magnitude cap? (can the agent move ₹50K but not ₹50L without escalation?)
   - Is there a kill-switch / circuit breaker if the action loop misbehaves?

4. REVERSIBILITY:
   - Reversible: is the inverse action wired and tested? (pause ↔ resume)
   - Irreversible: is the gate sufficient given it can't be undone?

5. IDEMPOTENCY:
   - If the action fires twice (retry, double-tap, replay) does it double-charge / double-send?
   - Is there an idempotency key? (see `idempotency-handling`)

6. INJECTION SURFACE:
   - Can untrusted input (a customer name, an ad-copy field, a connector payload) reach the
     action's arguments? Could a crafted value turn a "pause campaign X" into "pause all"?
   - Are arguments validated with Zod/schema BEFORE the tool runs, not after?

7. LOG:
   - Does the action write a Decision Log entry (actor, action, args, workspace_id, ts, outcome)?
   - Without this, you cannot answer "why did CM2 drop ₹2L?" two weeks later.

8. DECIDE: PASS (all gates green) | BOUNCE (name the missing gate per action).
```

## Action classification table (Brain canon)

| Action | Class | Required controls |
|---|---|---|
| `integrations.meta.pause_ad_set` | REVERSIBLE WRITE | human approve + Decision Log + idempotency key + resume wired |
| `integrations.*.update_budget` | FINANCIAL | human approve + magnitude cap + Decision Log + idempotency |
| lifecycle AI call | COMPLIANCE-GATED + IRREVERSIBLE | India matrix PASS (hours/DLT/NCPR/DND/consent/48h cap) **before** dial + Decision Log + recording-consent path |
| WhatsApp/SMS/email send | COMPLIANCE-GATED + IRREVERSIBLE | opt-in check + DLT template (SMS) + Decision Log + idempotency |
| agent-generated SQL on OLAP | REVERSIBLE-ish | workspace_id scoping enforced by query gateway; read-only role; no DDL |
| agent-generated migration | IRREVERSIBLE | human review + reversible-down + run in staging first |
| token-spend (LLM batch) | FINANCIAL (soft) | paradigm audit (SQL>ML>Haiku>Sonnet) + budget alarm |

## Red flags — STOP and BOUNCE

- An MCP write tool with **no Decision Log middleware** — you lose the audit trail the whole MER dashboard depends on.
- An **irreversible or financial action with no human gate** — the agent can spend/send autonomously.
- A tool scoped to **"all workspaces"** or using a **god-mode OAuth token**.
- Untrusted input flowing into action args **without schema validation first** (prompt-injection → action-injection).
- A **magnitude with no cap** — "reallocate budget" that can move the entire account.
- **No idempotency key** on a write that can retry — double-spend / double-send.
- A compliance-gated action where the **gate runs after** (or in parallel with) the action instead of strictly before.
- "We'll add the kill-switch later" on an autonomous loop.

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "It only ever pauses campaigns, that's safe" | Reversible ≠ free. A wrong pause still costs revenue and needs a log + the resume path tested. |
| "The model won't generate a bad action" | The model will generate whatever a crafted input steers it to. Validate args; don't trust the prompt. |
| "There's a human in the Morning Brief" | Only if THIS action routes through it. Confirm the path; background/cron actions often don't. |
| "The OAuth token is encrypted" | Encryption protects the token at rest; scope protects you when the agent misuses it. Both required. |
| "Decision Log is a nice-to-have" | It's the only thing that maps a metric swing back to the action that caused it. Non-negotiable. |
| "Idempotency is over-engineering here" | Retries and double-taps happen in production. One double-send to a customer is a compliance incident. |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Action audit at Stage 4 | **Shreya** (security-reviewer) | this skill + `security-baseline` |
| Building the action safely | **Maya** (intelligence-engineer) | `agentic-design`, `mcp-protocol`, `idempotency-handling` |
| Designing the human gate | **Aryan** (architect) + **Karan** (Morning Brief approve flow) | `morning-brief-mobile` |
| India compliance gate | **Shreya** | `india-commerce-economics` (DLT/NCPR/DND/hours/consent) |
| Decision Log middleware | Maya + Vikram | `mcp-protocol` §Decision Log |

## When to apply

- Stage 4, on **any PR that adds or changes an MCP write tool, an outbound channel, or an autonomous loop**.
- Architecture review (Stage 2) when a new agentic surface is proposed — gate the design before code exists.
- Any time the Morning Brief gains a new approve-able action type.

## The bottom line

Recommendations are cheap to get wrong; actions are not. Classify the blast radius, require a human gate on anything irreversible or financial, validate the arguments, and log every action. An agent that acts without these isn't autonomous — it's unsupervised.

Related: `agentic-design` (build the loop), `mcp-protocol` (Decision Log + tool auth), `security-baseline` (the gate), `idempotency-handling` (no double-fire), `india-commerce-economics` (the compliance matrix).
