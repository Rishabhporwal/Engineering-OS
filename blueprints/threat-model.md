# Threat Model — {{FEATURE_OR_SURFACE}}

> STRIDE threat model. Filled by Shreya (or the builder, reviewed by Shreya) per the `security-baseline` skill — required for any change touching auth, multi-tenancy, MCP tools, connectors, outbound channels, money movement, or PII. Save the filled copy to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/security/<slug>-threat-model.md`.

| Field | Value |
|---|---|
| **Surface / feature** | {{FEATURE}} |
| **req_id** | `{{REQ_ID}}` |
| **Author / reviewer** | {{AUTHOR}} / Shreya |
| **Date** | {{TS}} |
| **Data sensitivity** | {{none / internal / PII / payment-adjacent / compliance-regulated}} |
| **Trust boundary crossed?** | {{which: client→gateway, gateway→service, service→external-API, agent→MCP-tool, …}} |

## 1. Asset & entry-point inventory
- **Assets at risk:** {{e.g. workspace data, Decision Log, vendor OAuth tokens, customer PII, billing/GMV figures}}
- **Entry points:** {{tRPC procedures, gRPC methods, MCP tools, Kafka topics, webhooks, the UI}}
- **Actors:** {{role(s) — viewer/analyst/agency/operator/owner — + external partners + the product agents}}

## 2. STRIDE analysis
For each, state whether it applies, the specific threat, and the mitigation (or N/A with reason).

| STRIDE | Applies? | Threat | Mitigation (must map to a real control) |
|---|:---:|---|---|
| **S**poofing (identity) | | | Supabase JWT verify; `workspace_id`+`role` from `app_metadata` only (never request body); MCP scope check |
| **T**ampering (data/integrity) | | | Postgres RLS; ClickHouse query-gateway; idempotency keys; Decision Log append-then-update (no silent edit); minor-units money |
| **R**epudiation (deniability) | | | Audit log (7y); Decision Log actor + timestamp; correlation ID end-to-end |
| **I**nformation disclosure | | | 4-layer `workspace_id` isolation; no cross-brand reads; PII hashed by default + redacted in logs; k≥5 benchmarks; least-privilege OAuth scopes |
| **D**enial of service | | | Per-tier rate limits; per-vendor outbound throttle; per-workspace LLM caps; cursor pagination (no OFFSET); query timeouts |
| **E**levation of privilege | | | `requireRole` on every mutation; no BYPASSRLS in request path; agent action blast-radius gate + human-gate on irreversible/financial |

## 3. AI-surface threats (if the change adds/changes an agent action or LLM call)
- **Prompt injection:** untrusted commerce text (ticket/inbox/ad-copy/brand notes) reaching an LLM that drives a write tool → see `prompt-injection-defense`. Mitigation: {{input isolation, output-schema validation, tool-call monitoring, args validated before the tool runs}}.
- **Action blast radius:** {{read / reversible / irreversible / financial / compliance-gated}} → per `agentic-actions-auditor`; human gate + magnitude cap + kill switch + Decision Log + idempotency.
- **Compliance gate before the action fires:** {{DLT/NCPR/DND/9am–9pm for SMS-voice; WhatsApp opt-in+template; AI-call disclosure+human-handoff; consent re-check}}.

## 4. Residual risk & decision
- **Residual risk after mitigations:** {{low / medium / high}} — {{description}}
- **Verdict:** {{accept (Owner/CTOA-logged) / mitigate-before-ship / VETO}}
- **Follow-ups (tracked):** {{tech-debt items with owner + date}}
