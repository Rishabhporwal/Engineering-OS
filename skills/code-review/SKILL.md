---
name: code-review
description: Code review discipline — technical rigor over performative agreement, evidence-based feedback, verification gates. Use before approving a PR, invoking /review, or handing off.
---

# Code Review

Code review in Brain is one of three places where quality is structurally enforced (the others: Shreya's threat-model VETO, Tanvi's PASS/FAIL gate). This skill keeps reviews technically rigorous, evidence-based, and out of social comfort.

## Three distinct practices

1. **Receiving feedback** — technical evaluation over performative agreement
2. **Requesting review** — invoking `/review` (Shreya + Tanvi parallel) at the right time
3. **Verification gates** — evidence before any completion claim (owner skill: `verification-before-completion`)

## Core principle

**Technical correctness over social comfort.** Verify before implementing. Ask before assuming. Evidence before claims.

## When to use

**Receiving feedback** — review comments from any source; feedback unclear/questionable; multiple items to prioritise; external reviewer lacks Brain context; suggestion conflicts with an ADR or Iron Law.

**Requesting review** — completing a builder task before handoff to Tanvi; before merging to main; stuck; after fixing a complex bug (confirm root-cause per `systematic-debugging`); any change touching auth/PII/payments/India compliance/MCP scopes/mobile cert pinning → **must** route through Shreya (VETO).

**Verification gates** — see `verification-before-completion` for the full gate protocol (triggers + red flags live there).

## Quick decision tree

```
SITUATION?
├─ Received feedback
│  ├─ Unclear items?      → STOP, ask for clarification first
│  ├─ From Founder?       → Understand, push back if technically wrong (Iron Law #7), then implement
│  ├─ From Shreya (VETO)? → CRITICAL/HIGH must be fixed; LOW/MEDIUM defensible
│  ├─ From Tanvi?         → PASS/FAIL non-negotiable; CONDITIONAL PASS has conditions to close
│  └─ From external?      → Verify technically first; reject if it contradicts Brain canon
├─ Completed builder task
│  ├─ Touches auth/PII/India?  → /review with Shreya BLOCKING
│  └─ Otherwise             → /review (Shreya + Tanvi parallel)
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
| **Founder (Rishabh)** | Trusted; understand intent, then implement | When technically wrong — Iron Law #7, dissent required |
| **Shreya (Security)** | VETO on CRITICAL/HIGH | Only with evidence; LOW/MEDIUM negotiable with rationale |
| **Tanvi (QA)** | PASS/FAIL gates deploy | CONDITIONAL PASS lets you close conditions over time; don't argue verdict |
| **Aryan (Architect)** | Trusted on architecture | Only with a competing ADR or TECH-doc citation |
| **Rohan (CTO Advisor)** | Strategic | Tactical specifics only; respect strategic calls |
| **External (ultrareview, sub-agent)** | Verify technically | Reject anything contradicting a Brain ADR, TECH doc, or Iron Law |

## Requesting review — Brain pattern

`/review` runs Shreya + Tanvi in parallel.

```bash
/review            # current branch
/review 1234       # PR #1234
```

For Medium/Large tier, run `/review` **after** the builder completes and **before** the deploy handoff. For Trivial/Small (one-file change, bug fix), `/review` is optional — builder owns judgement.

Request specifically: after every builder task in a Medium+ feature; after fixing any CVE-class bug; before merging to main; after 3+ failed fixes (architectural question — `systematic-debugging` Phase 4.5); when the change touches the Decision Log row spec, Single-Primitive territory, or the cost-routing audit.

### Acting on feedback

| Severity | Action |
|---|---|
| **CRITICAL** (Shreya) | Block merge. Fix before any other work. |
| **HIGH** (Shreya) | Block merge. Fix or formally defer with Shreya's written approval. |
| **MEDIUM** | Fix in this PR if cheap; else backlog `slice-X.Y`. |
| **LOW** | Note in PR description; backlog. |
| **Tanvi FAIL** | Block deploy. Fix what failed, re-run /qa. |
| **Tanvi CONDITIONAL PASS** | Close conditions in next slice. Track in `memory/qa/<slug>.md`. |
| **Tanvi PASS** | Proceed to deploy. |

## Verification gates

The Iron Law and its full red-flag inventory + per-claim evidence table live in `verification-before-completion`. In short: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE. Mutation score, smoke result, and paradigm-audit presence are verified inputs to `/review`, not trusted.

## Integration with the Brain pipeline

- **Builder flow:** builder completes → run verification → /review → emit handoff to Tanvi
- **/review flow:** Shreya + Tanvi parallel → CRITICAL/HIGH block → fixes → re-run → APPROVED → deploy
- **/qa flow:** Tanvi runs full suite + smoke + paradigm audit + metric parity → PASS/CONDITIONAL/FAIL
- **/deploy flow:** Jatin runs CI/CD; auto-rollback on composite alarm (see `operational-readiness`)
- **Incident:** Jatin recalls a PR's review trail in postmortem — verifications are part of the record

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| code-review (this skill) | **Rohan** (Stage 6) + Shreya + Tanvi | this SKILL.md |
| QA PASS/FAIL gate | **Tanvi** | canon/technical-requirements.md |
| Security VETO | **Shreya** | prompts/system-prompt.md (Iron Laws) |
| Architectural pushback | **Aryan** | the ADR for the change |
| Strategic pushback | **Rohan** | when ADR needs non-engineering perspective |

Related: `verification-before-completion`, `engineering-discipline`, `systematic-debugging`, `defense-in-depth-validation`.

**Verify. Question. Then implement. Evidence. Then claim.**
