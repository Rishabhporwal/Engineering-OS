---
name: tech-stack-evaluation
description: Brain's stack is LOCKED (see canon/technical-requirements.md). Use this skill ONLY when adding a new layer not in the stack — e.g., picking the AI calling vendor (Path A/B/C), choosing a new BSP, or proposing a layer swap that needs an explicit architecture decision. For routine work, Aryan skips this skill entirely and references the locked stack.
---

# Tech Stack Evaluation — Stack Is Locked

## Brain's stack is locked

Brain's tech stack is the locked decision in `canon/technical-requirements.md`. The full table is also reflected in `prompts/system-prompt.md` and the project's `memory/business-context.md`. **For routine work, don't re-run evaluation — reference the canon.**

| Layer | Choice |
|---|---|
| Frontend (web) | Next.js 14+ App Router, shadcn/ui, Tailwind, Recharts + Visx, Redux Toolkit + TanStack Query + nuqs |
| Frontend (mobile, PRIMARY for Morning Brief) | React Native + Expo SDK 51+, Tamagui, Expo Router, redux-persist on AsyncStorage, victory-native, EAS Build |
| Edge API | Fastify + tRPC (typed end-to-end) |
| Internal API | gRPC over HTTP/2 via Protocol Buffers; `buf` for codegen (TS + Python) |
| Agent surface | MCP server inside api-gateway |
| OLTP | Supabase Postgres + RLS + Auth |
| OLAP | ClickHouse Cloud (workspace_id-sharded; query gateway in `pylibs/brain_clickhouse`) |
| Cache | ElastiCache Redis (cluster mode) |
| Vector | pgvector in Postgres (Memory Layer) |
| Async | Amazon MSK + AWS Glue Schema Registry + Avro |
| CDC | Debezium on MSK Connect |
| Search / Logs | AWS OpenSearch (Fluent Bit log spine + Phase 3 product search) |
| Object | S3 |
| CDN + DNS | CloudFront + Route 53 |
| Orchestration | EKS + Karpenter + ArgoCD |
| IaC | AWS CDK (TypeScript) |
| Secrets | AWS Secrets Manager + per-pod IRSA |
| CI/CD | GitHub Actions with OIDC → ECR → ArgoCD; EAS Build + EAS Update for mobile |
| LLM | Anthropic Claude Sonnet 4.6 + Haiku 4.5 with prompt caching |
| Email / SMS / WhatsApp | AWS SES; Gupshup or Kaleyra (DLT); WhatsApp Cloud API (Gupshup BSP) |
| AI Calling | Pilot Path A (Bolna / Smallest.ai) or Path B (Vapi / Retell); parallel-build Path C (native) at ~5K calls/day |
| Observability | Fluent Bit → OpenSearch + CloudWatch + X-Ray + Sentry + PostHog |

## When to use this skill (RARELY)

Only when:

1. **Adding a new layer not in the stack** — e.g., picking the AI calling vendor (see canon/technical-requirements.md)
2. **Proposing a layer swap** — write an explicit architecture decision with: failure mode of current choice, swap cost, migration path, security review (Shreya)
3. **Phase 4 expansion** — choosing the US region, multi-3PL providers (Delhivery, Bluedart direct), new payment processors

Otherwise: **skip this skill.** Reference `canon/technical-requirements.md`.

## The evaluation principle (when you ARE evaluating)

> **The simplest tool that meets the requirement over the project's expected lifetime wins.**

Rules:
- Don't add complexity for hypothetical future scale
- Don't add complexity for one-off needs
- Lifetime-weight the choice — if you'll need it in 6 months, build it now (the cost of "Kafka in slice 3" is 3-5× the cost of "Kafka in slice 1, even with one consumer")
- Document every choice in an ADR

## ADR template for stack additions / swaps

```markdown
---
adr: NNN
title: <Layer> — <Choice>
status: proposed | accepted | superseded
date: YYYY-MM-DD
---

# Context
Why are we evaluating this? What constraint forced the conversation?

# Options Considered

## Option A: <choice>
- Pros: <list>
- Cons: <list>
- Cost: <monthly $>
- Migration cost from current: <effort>

## Option B: <choice>
- ...

# Decision

We chose **<X>** because:
- <reason 1>
- <reason 2>

# Consequences

- What does this enable?
- What does this lock us into?
- What new failure modes does it introduce?

# Rejected alternatives

Why each rejected option is wrong for Brain at this Phase.
```

## AI calling vendor — the live decision (see canon/technical-requirements.md)

Brain has an OPEN evaluation for AI calling:

| Path | Strengths | Weaknesses | Time to market |
|---|---|---|---|
| A — India vendor (Bolna, Smallest.ai) | Hindi/Hinglish accents; STD trunking ₹0.30-0.60/min; vendor handles DLT/DND | Vendor dependency; less control | 4-6 weeks |
| B — Global vendor (Vapi, Retell, ElevenLabs, Bland) | Best voice quality + latency; mature SDKs | $0.05-0.15/min; SIP plumbing for India compliance | 4-6 weeks + SIP trunk |
| C — Native build (Deepgram/Whisper + Haiku + ElevenLabs/Cartesia + Plivo/Exotel) | Full control; long-term margin | 4-6 month build; voice-agent engineer needed | 4-6 months |

**Heuristic:** Months 1-6 partner (A or B); months 6-12 parallel-build C if volume > 5K calls/day; months 12+ migrate primary to C; keep partner as overflow + regional-language hedge.

Vendor abstraction in `lifecycle-service/call_router.py` makes swaps a config change. Production can run multiple providers concurrently.

## Common failure modes

- **Re-evaluating a locked stack** — the stack ADR is written. Reference it; don't redo evaluation. Detection: a new "stack evaluation" section appears when prior ADR already locked decisions.
- **Choosing on hype, not Brain fit** — "everyone uses Pulsar now" doesn't matter if MSK is locked. New ADR required for swap.
- **Forgetting Phase context** — Phase 1 doesn't justify Phase 4 infrastructure. Lifetime-weight at the project level, but stage spend per Phase.

## References

- `canon/technical-requirements.md` — the canonical stack table + AI calling vendor decision (the locked stack)
- `skills/architecture-patterns/SKILL.md` — when a pattern change implies a stack change
