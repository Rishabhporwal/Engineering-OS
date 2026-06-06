# Threat Model — {{FEATURE_OR_SURFACE}}

> STRIDE threat model. Filled by the Security Reviewer (or the builder, reviewed by the Security Reviewer) per the `security-baseline` skill — required for any change touching auth, multi-tenancy, MCP tools, connectors, outbound channels, money movement, or PII. Save the filled copy to `${CLAUDE_PROJECT_DIR}/.engineering-os/memory/security/<slug>-threat-model.md`.

| Field | Value |
|---|---|
| **Surface / feature** | {{FEATURE}} |
| **req_id** | `{{REQ_ID}}` |
| **Author / reviewer** | {{AUTHOR}} / the Security Reviewer |
| **Date** | {{TS}} |
| **Data sensitivity** | {{none / internal / PII / payment-adjacent / compliance-regulated}} |
| **Trust boundary crossed?** | {{which: client→gateway, gateway→service, service→external-API, agent→MCP-tool, …}} |

## 1. Asset & entry-point inventory
- **Assets at risk:** {{e.g. tenant data, audit log, vendor OAuth tokens, customer PII, billing/financial figures}}
- **Entry points:** {{tRPC procedures, gRPC methods, MCP tools, Kafka topics, webhooks, the UI}}
- **Actors:** {{role(s) — viewer/analyst/agency/operator/owner — + external partners + the product agents}}

## 2. STRIDE analysis
For each, state whether it applies, the specific threat, and the mitigation (or N/A with reason).

| STRIDE | Applies? | Threat | Mitigation (must map to a real control) |
|---|:---:|---|---|
| **S**poofing (identity) | | | the identity provider JWT verify; `tenant_id`+`role` from `app_metadata` only (never request body); MCP scope check |
| **T**ampering (data/integrity) | | | Postgres RLS; ClickHouse query-gateway; idempotency keys; audit log append-then-update (no silent edit); minor-units money |
| **R**epudiation (deniability) | | | Audit log (7y); audit log actor + timestamp; correlation ID end-to-end |
| **I**nformation disclosure | | | 4-layer `tenant_id` isolation; no cross-tenant reads; PII hashed by default + redacted in logs; k≥5 benchmarks; least-privilege OAuth scopes |
| **D**enial of service | | | Per-tier rate limits; per-vendor outbound throttle; per-workspace LLM caps; cursor pagination (no OFFSET); query timeouts |
| **E**levation of privilege | | | `requireRole` on every mutation; no BYPASSRLS in request path; agent action blast-radius gate + human-gate on irreversible/financial |

## 3. AI-surface threats (if the change adds/changes an agent action or LLM call)
- **Prompt injection:** untrusted commerce text (ticket/inbox/ad-copy/brand notes) reaching an LLM that drives a write tool → see `prompt-injection-defense`. Mitigation: {{input isolation, output-schema validation, tool-call monitoring, args validated before the tool runs}}.
- **Action blast radius:** {{read / reversible / irreversible / financial / compliance-gated}} → per `agentic-actions-auditor`; human gate + magnitude cap + kill switch + audit log + idempotency.
- **Compliance gate before the action fires:** {{the controls the Canon's COMPLIANCE.md declares — e.g. channel send-window, opt-out/consent check, required disclosure, frequency cap}}.

## 4. Residual risk & decision
- **Residual risk after mitigations:** {{low / medium / high}} — {{description}}
- **Verdict:** {{accept (Owner/CTOA-logged) / mitigate-before-ship / VETO}}
- **Follow-ups (tracked):** {{tech-debt items with owner + date}}
