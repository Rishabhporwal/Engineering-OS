---
name: code-review
description: Code review discipline — technical rigor over performative agreement, evidence-based feedback, verification gates. Use before approving a PR, invoking /review, or handing off.
---

# Code Review

Code review is one of the places where quality is structurally enforced (the others: the Security Reviewer's threat-model VETO, the QA Engineer's PASS/FAIL gate). This skill keeps reviews technically rigorous, evidence-based, and out of social comfort.

## Three distinct practices

1. **Receiving feedback** — technical evaluation over performative agreement
2. **Requesting review** — invoking `/review` (Security Reviewer + QA Engineer in parallel) at the right time
3. **Verification gates** — evidence before any completion claim (owner skill: `verification-before-completion`)

## Core principle

**Technical correctness over social comfort.** Verify before implementing. Ask before assuming. Evidence before claims.

## When to use

**Receiving feedback** — review comments from any source; feedback unclear/questionable; multiple items to prioritise; an external reviewer lacks product context; a suggestion conflicts with an ADR or Iron Law.

**Requesting review** — completing a builder task before handoff to QA; before merging to main; stuck; after fixing a complex bug (confirm root-cause per `systematic-debugging`); any change touching auth/PII/payments/the compliance regime/MCP scopes/mobile cert pinning → **must** route through the Security Reviewer (VETO).

**Verification gates** — see `verification-before-completion` for the full gate protocol (triggers + red flags live there).

## Quick decision tree

```
SITUATION?
├─ Received feedback
│  ├─ Unclear items?              → STOP, ask for clarification first
│  ├─ From the Stakeholder?       → Understand, push back if technically wrong (Iron Law: no blind agreement), then implement
│  ├─ From Security (VETO)?       → CRITICAL/HIGH must be fixed; LOW/MEDIUM defensible
│  ├─ From QA?                    → PASS/FAIL non-negotiable; CONDITIONAL PASS has conditions to close
│  └─ From external?              → Verify technically first; reject if it contradicts the Canon
├─ Completed builder task
│  ├─ Touches auth/PII/compliance? → /review with Security BLOCKING
│  └─ Otherwise                     → /review (Security + QA parallel)
└─ About to claim status
   ├─ Fresh verification? → State claim WITH evidence
   └─ No verification?    → RUN the verification command first
```

## Receiving feedback — the protocol

Pattern: `READ → UNDERSTAND → VERIFY → EVALUATE → RESPOND → IMPLEMENT`

- ❌ **No performative agreement.** No "You're absolutely right!", "Great catch!", "Thanks for the feedback!"
- ❌ **No implementation before verification.** If a reviewer says "this query is slow," EXPLAIN it before agreeing.
- ✅ Restate the requirement in your own words.
- ✅ Ask specific clarifying questions; if unclear, STOP and ask on ALL unclear items first.
- ✅ Push back with technical reasoning when a suggestion is wrong or conflicts with an ADR / Iron Law.
- ✅ **YAGNI check:** grep for usage before implementing a suggested "proper" feature.

### Source handling

| Reviewer | Trust posture | When to push back |
|---|---|---|
| **Stakeholder** | Trusted; understand intent, then implement | When technically wrong — the no-blind-agreement law, dissent required |
| **Security Reviewer** | VETO on CRITICAL/HIGH | Only with evidence; LOW/MEDIUM negotiable with rationale |
| **QA Engineer** | PASS/FAIL gates deploy | CONDITIONAL PASS lets you close conditions over time; don't argue verdict |
| **Architect** | Trusted on architecture | Only with a competing ADR or HLD/LLD citation |
| **Engineering Advisor** | Strategic | Tactical specifics only; respect strategic calls |
| **External (deep review, sub-agent)** | Verify technically | Reject anything contradicting an ADR, the Canon, or an Iron Law |

## Requesting review — the pattern

`/review` runs the Security Reviewer + QA Engineer in parallel.

```bash
/review            # current branch
/review 1234       # PR #1234
```

For Medium/Large tier, run `/review` **after** the builder completes and **before** the deploy handoff. For Trivial/Small (one-file change, bug fix), `/review` is optional — builder owns judgement.

Request specifically: after every builder task in a Medium+ feature; after fixing any CVE-class bug; before merging to main; after 3+ failed fixes (architectural question — `systematic-debugging` Phase 4.5); when the change touches the audit-log row spec, Single-Primitive territory, or the cost-routing audit.

### Acting on feedback

| Severity | Action |
|---|---|
| **CRITICAL** (Security) | Block merge. Fix before any other work. |
| **HIGH** (Security) | Block merge. Fix or formally defer with the Security Reviewer's written approval. |
| **MEDIUM** | Fix in this PR if cheap; else backlog. |
| **LOW** | Note in PR description; backlog. |
| **QA FAIL** | Block deploy. Fix what failed, re-run /qa. |
| **QA CONDITIONAL PASS** | Close conditions in the next slice. Track in `memory/qa/<slug>.md`. |
| **QA PASS** | Proceed to deploy. |

## Verification gates

The Iron Law and its full red-flag inventory + per-claim evidence table live in `verification-before-completion`. In short: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. Mutation score, smoke result, and cost-audit presence are verified inputs to `/review`, not trusted.

## Integration with the pipeline

- **Builder flow:** builder completes → run verification → /review → emit handoff to QA
- **/review flow:** Security + QA parallel → CRITICAL/HIGH block → fixes → re-run → APPROVED → deploy
- **/qa flow:** QA runs full suite + smoke + cost audit + metric parity → PASS/CONDITIONAL/FAIL
- **/deploy flow:** Platform/SRE runs CI/CD; auto-rollback on composite alarm (see `operational-readiness`)
- **Incident:** Platform/SRE recalls a PR's review trail in postmortem — verifications are part of the record

## Wiring

| Concern | Role | Reference |
|---|---|---|
| code-review (this skill) | **Engineering Advisor** (final review) + Security Reviewer + QA Engineer | this SKILL.md |
| QA PASS/FAIL gate | **QA Engineer** | `engineering-os-blueprint/06-quality-gates-and-metrics.md` |
| Security VETO | **Security Reviewer** | `prompts/system-prompt.md` (Iron Laws) |
| Architectural pushback | **Architect** | the ADR for the change |
| Strategic pushback | **Engineering Advisor** | when an ADR needs a non-engineering perspective |

Related: `verification-before-completion`, `engineering-discipline`, `systematic-debugging`, `security-baseline`.

**Verify. Question. Then implement. Evidence. Then claim.**
