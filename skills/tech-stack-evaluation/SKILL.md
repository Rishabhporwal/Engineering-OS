---
name: tech-stack-evaluation
description: The stack-DECISION framework. The OS is stack-agnostic — each seam is bound in the product's STACK.md via an ADR during Foundation. Use when adding a layer not yet in the Canon, or proposing a layer swap that needs an ADR. For routine work, skip and reference the Canon.
---

# Tech Stack Evaluation — Decide Deliberately, Then Lock

## The OS is stack-agnostic; the product's stack is decided in the Canon

The Engineering OS does not prescribe a technology. **Each architectural seam is bound to a concrete technology in the product's `STACK.md`** (in `.engineering-os/knowledge-base/`), produced during the Foundation phase via an ADR (see `engineering-os-blueprint/09-reference-architecture.md` and `engineering-os-blueprint/04-architecture-and-decisions.md`). **Once a seam is chosen and recorded in `STACK.md`, it is locked** — for routine work, don't re-run evaluation; reference the Canon.

The seams a `STACK.md` typically binds (the technology in each cell is the *product's* choice, not a mandate):

| Seam | What `STACK.md` binds it to |
|---|---|
| Web frontend | a web framework + UI/charting libs + state strategy |
| Mobile frontend (if any) | a mobile framework + build/release pipeline |
| Edge / public API | an HTTP framework + typed contract layer |
| Internal API | an internal RPC/contract layer with codegen across runtimes |
| Agent / tool surface | how models/tools are exposed (e.g. an MCP server) |
| OLTP store | a transactional database + row-level isolation |
| OLAP store | an analytical store (with the tenant key leading the sort order) |
| Cache | a caching layer + invalidation discipline |
| Vector / similarity | a vector index appropriate to the workload |
| Async backbone | a message bus + schema registry |
| Search / Logs | a log/search spine |
| Object storage | a blob store |
| CDN + DNS | edge delivery + DNS |
| Orchestration | a container/scheduler platform |
| IaC | an infrastructure-as-code tool |
| Secrets | a managed secret store + per-workload identity |
| CI/CD | a pipeline + artifact registry + deploy mechanism |
| Model gateway | a single entry point routing to the chosen model(s) |
| Outbound channels | email/SMS/chat/voice providers (per `COMPLIANCE.md`) |
| Observability | logs + metrics + traces + error tracking |

## When to use this skill (RARELY)

1. **Adding a new seam/layer not yet bound in `STACK.md`** — e.g. a new outbound-channel vendor.
2. **Proposing a layer swap** — write an explicit ADR with: failure mode of the current choice, swap cost, migration path, Security Reviewer sign-off.
3. **A scope expansion that forces a new technology** — a new region, a new integration class, a new payment/processor surface.

Otherwise: **skip this skill** and reference the Canon.

## The evaluation principle (when you ARE evaluating)

> **The simplest tool that meets the requirement over the project's expected lifetime wins.**

Don't add complexity for hypothetical scale or one-off needs. Lifetime-weight the choice — if you'll need it in 6 months, build it now (introducing a message bus in slice 3 costs 3-5× introducing it in slice 1, even with one consumer). Document every choice in an ADR.

## ADR template for stack additions / swaps

```markdown
---
adr: NNN
title: <Seam> — <Choice>
status: proposed | accepted | superseded
date: YYYY-MM-DD
---
# Context — Why are we evaluating this? What constraint forced it?
# Options Considered — per option: Pros / Cons / Cost (per month) / Migration cost from current
# Decision — We chose **<X>** because: <reasons>
# Consequences — What it enables / locks us into / new failure modes
# Rejected alternatives — Why each is wrong for THIS product at this stage
```

## Worked example — choosing an outbound-voice/channel vendor

A typical "buy vs. partner vs. build" evaluation for a regulated outbound channel (the specific vendors are illustrative):

| Path | Strengths | Weaknesses | TTM |
|---|---|---|---|
| A — Regional vendor | Local accents/numbers; vendor handles regional channel-compliance registration | Vendor dependency; less control | 4-6 wk |
| B — Global vendor | Best quality + latency; mature SDKs | Higher per-unit cost; extra plumbing for regional compliance | 4-6 wk + integration |
| C — Build native | Full control; long-term margin | Multi-month build; specialist engineer | 4-6 mo |

**Heuristic:** early on, partner (A or B); once volume justifies it, parallel-build C; later, migrate primary to C and keep a partner as overflow + a regional hedge. Put the vendor behind an adapter (e.g. a `channel_router`) so swaps are a config change and production can run multiple providers concurrently. The specific compliance obligations come from `COMPLIANCE.md`.

## Common failure modes

- **Re-evaluating an already-locked seam** — the ADR is written; reference it.
- **Choosing on hype, not product fit** — "everyone uses X now" doesn't matter if `STACK.md` already binds the seam well.
- **Forgetting stage context** — lifetime-weight at the project level, but stage the spend per phase.

## References

- The product's `STACK.md` (in `.engineering-os/knowledge-base/`) — the canonical seam→technology bindings + their ADRs
- `engineering-os-blueprint/04-architecture-and-decisions.md` (ADR discipline) · `engineering-os-blueprint/09-reference-architecture.md` (seam catalogue)
- Related: `architecture-patterns` (when a pattern change implies a stack change), `version-upgrade-policy` (version cadence within the locked stack)
