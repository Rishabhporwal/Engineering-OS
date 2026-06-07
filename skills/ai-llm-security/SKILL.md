---
name: ai-llm-security
description: Security for LLM/agent applications mapped to OWASP Top 10 for LLM Apps (2025) + OWASP Agentic Top 10 — prompt injection, excessive agency, sensitive-info disclosure, insecure output handling, system-prompt leakage. The framework anchor for agentic-safety. Security Reviewer VETO.
---

# AI / LLM Application Security (Reference Patterns)

> **Reference implementation.** This skill anchors the **LLM/agent security seam** to the now-canonical frameworks — **OWASP Top 10 for LLM Applications (2025)** and **OWASP Top 10 for Agentic AI (2025)** — the way `security-baseline` anchors app-sec to the classic OWASP Top 10. The OS is stack-agnostic; controls bind to your `STACK.md`/`COMPLIANCE.md`. It pairs with `agentic-safety` (action blast-radius + input hardening): this skill is the *threat framework*, `agentic-safety` is the *action-control mechanism*. **Owner:** Security Reviewer (VETO); AI/ML + ML Platform Engineers implement the controls.

## The threats that matter most (OWASP LLM/Agentic)
| # | Risk | Defense-in-depth |
|---|------|------------------|
| LLM01 | **Prompt injection** (direct + indirect via retrieved/tool content) | Treat ALL non-system text as untrusted data, never instructions; structure prompts so retrieved/tool output can't escalate; constrain tools (`agentic-safety`); never let model output trigger a privileged action without a gate. |
| LLM02 | **Sensitive-info disclosure** | Redact PII into prompts; tenant-scope retrieval (`rag-retrieval`, `multi-tenancy-isolation`); output filters; don't put secrets in the system prompt. |
| LLM05 | **Insecure output handling** | Treat model output as untrusted input to the *next* system — validate/encode before it hits a shell, SQL, browser (XSS), or another tool. |
| LLM06 | **Excessive agency** | Least-privilege tools, scoped + audited (`agentic-safety`); human-in-the-loop gate on consequential actions (`workflow-engine-temporal`); cap blast radius. |
| LLM07 | **System-prompt leakage** | Assume the system prompt is public — put no secrets/credentials/authz logic in it; enforce authz in code, not in the prompt. |
| LLM08 | **Vector/embedding weaknesses** | Tenant-isolate the vector store; validate ingested docs (poisoning); access-control retrieval. |
| LLM04/09 | **Data/model poisoning, misinformation** | Provenance on training/RAG data; groundedness evals (`llm-evals`); guardrails on output. |
| Agentic | **Tool misuse, identity/permission, cascading multi-agent failures** | Per-agent identity + scope; bound autonomy; trajectory evals (`agent-evaluation`); kill switch (`incident-response`). |

## Invariants (NON-NEGOTIABLE)
1. **Untrusted text is data, never instructions.** Retrieved documents, tool outputs, user messages, and web content can all carry injected instructions. The agent's **edges/code** decide what runs next — never the model's interpretation of untrusted text. This is the #1 LLM risk; design for it, don't hope.
2. **No privileged action without a gate.** A model/agent cannot, on its own say-so, execute a consequential or irreversible action — it proposes; a scoped tool + (for high-stakes) a human/policy gate disposes (`agentic-safety`, `workflow-engine-temporal`).
3. **Model output is untrusted input downstream.** Validate/encode before it reaches SQL, a shell, the DOM (XSS — `security-baseline`), or another tool. Insecure output handling is how injection becomes RCE/leakage.
4. **The system prompt is public.** Authz, tenancy, and secrets live in code + infra, never in the prompt. Assume leakage.
5. **Adversarial testing is a CI gate.** Red-team the prompts/agents (promptfoo-style injection + jailbreak suites) and gate on it — pair with `agent-evaluation`'s guardrail metrics. Map each control to an OWASP item for auditor evidence (`compliance-attestation`).

## Mapping to the rest of the OS
- **Action controls + input hardening:** `agentic-safety` (the mechanism for LLM01/LLM06/Agentic).
- **Tenant isolation of context/vectors:** `multi-tenancy-isolation`, `rag-retrieval`.
- **Output encoding / classic web-sec:** `security-baseline` (LLM05).
- **Adversarial + trajectory testing:** `agent-evaluation`.
- **Supply chain of models/datasets:** `supply-chain-security` (provenance of weights + RAG data).
- **Audit of agent actions:** `decision-log`.

## Anti-patterns
Trusting retrieved/tool text as instructions · letting model output trigger a privileged action with no gate · piping model output into SQL/shell/DOM unvalidated · secrets or authz rules in the system prompt · no red-team/injection suite in CI · giving an agent broad standing permissions "for convenience" · treating LLM security as a prompt tweak rather than defense-in-depth · no per-agent identity in a multi-agent system.
