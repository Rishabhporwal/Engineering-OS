---
name: tech-stack-evaluation
description: Brain's stack is LOCKED — use ONLY when adding a layer not in the stack (e.g. the AI calling vendor) or proposing a layer swap needing an ADR. For routine work, skip and reference canon.
---

# Tech Stack Evaluation — Stack Is Locked

## Brain's stack is locked

The full table is the locked decision in `canon/technical-requirements.md`, reflected in `prompts/system-prompt.md` and `memory/business-context.md`. **For routine work, don't re-run evaluation — reference the canon.**

| Layer | Choice |
|---|---|
| Frontend (web) | Next.js 16 App Router, shadcn/ui, Tailwind, Recharts + Visx, Redux Toolkit + TanStack Query + nuqs |
| Frontend (mobile, PRIMARY) | React Native + Expo SDK 56, Tamagui, Expo Router, redux-persist on AsyncStorage, victory-native, EAS Build |
| Edge API | Fastify + tRPC (typed end-to-end) |
| Internal API | gRPC over HTTP/2 via Protobuf; `buf` codegen (TS + Python) |
| Agent surface | MCP server inside api-gateway |
| OLTP | Supabase Postgres + RLS + Auth |
| OLAP | ClickHouse Cloud (workspace_id-sharded; query gateway in `pylibs/brain_clickhouse`) |
| Cache | ElastiCache Redis (cluster mode) |
| Vector | pgvector in Postgres (Memory Layer) |
| Async | Amazon MSK + AWS Glue Schema Registry + Avro |
| CDC | Debezium on MSK Connect |
| Search / Logs | AWS OpenSearch (Fluent Bit log spine + Phase 3 search) |
| Object | S3 |
| CDN + DNS | CloudFront + Route 53 |
| Orchestration | EKS + Karpenter + ArgoCD |
| IaC | AWS CDK (TypeScript) |
| Secrets | AWS Secrets Manager + per-pod IRSA |
| CI/CD | GitHub Actions OIDC → ECR → ArgoCD; EAS Build + Update for mobile |
| LLM | LiteLLM gateway (self-hosted on EKS, ap-south-1) → Claude default (Sonnet 4.6 synthesis + Haiku 4.5 bounded NL) with prompt caching |
| Email / SMS / WhatsApp | AWS SES; Gupshup or Kaleyra (DLT); WhatsApp Cloud API (Gupshup BSP) |
| AI Calling | Pilot Path A (Bolna/Smallest.ai) or Path B (Vapi/Retell); parallel-build Path C (native) at ~5K calls/day |
| Observability | Fluent Bit → OpenSearch + CloudWatch + X-Ray + Sentry + PostHog |

## When to use this skill (RARELY)

1. **Adding a new layer not in the stack** — e.g., the AI calling vendor.
2. **Proposing a layer swap** — write an explicit ADR with: failure mode of current choice, swap cost, migration path, security review (Shreya).
3. **Phase 4 expansion** — US region, multi-3PL (Delhivery, Bluedart direct), new payment processors.

Otherwise: **skip this skill.**

## The evaluation principle (when you ARE evaluating)

> **The simplest tool that meets the requirement over the project's expected lifetime wins.**

Don't add complexity for hypothetical scale or one-off needs. Lifetime-weight the choice — if you'll need it in 6 months, build it now ("Kafka in slice 3" costs 3-5× "Kafka in slice 1, even with one consumer"). Document every choice in an ADR.

## ADR template for stack additions / swaps

```markdown
---
adr: NNN
title: <Layer> — <Choice>
status: proposed | accepted | superseded
date: YYYY-MM-DD
---
# Context — Why are we evaluating this? What constraint forced it?
# Options Considered — per option: Pros / Cons / Cost ($/mo) / Migration cost from current
# Decision — We chose **<X>** because: <reasons>
# Consequences — What it enables / locks us into / new failure modes
# Rejected alternatives — Why each is wrong for Brain at this Phase
```

## AI calling vendor — the live decision

Brain has an OPEN evaluation:

| Path | Strengths | Weaknesses | TTM |
|---|---|---|---|
| A — India vendor (Bolna, Smallest.ai) | Hindi/Hinglish accents; STD trunking ₹0.30-0.60/min; vendor handles DLT/DND | Vendor dependency; less control | 4-6 wk |
| B — Global vendor (Vapi, Retell, ElevenLabs, Bland) | Best voice quality + latency; mature SDKs | $0.05-0.15/min; SIP plumbing for India compliance | 4-6 wk + SIP trunk |
| C — Native (Deepgram/Whisper + Haiku + ElevenLabs/Cartesia + Plivo/Exotel) | Full control; long-term margin | 4-6 mo build; voice-agent engineer | 4-6 mo |

**Heuristic:** Months 1-6 partner (A or B); 6-12 parallel-build C if volume > 5K calls/day; 12+ migrate primary to C, keep partner as overflow + regional-language hedge. Vendor abstraction in `lifecycle-service/call_router.py` makes swaps a config change; production can run multiple providers concurrently.

## Common failure modes

- **Re-evaluating a locked stack** — the ADR is written; reference it.
- **Choosing on hype, not Brain fit** — "everyone uses Pulsar now" doesn't matter if MSK is locked.
- **Forgetting Phase context** — lifetime-weight at the project level, but stage spend per Phase.

## References

- `canon/technical-requirements.md` — canonical stack table + AI calling vendor decision
- Related: `architecture-patterns` (when a pattern change implies a stack change), `version-upgrade-policy` (version cadence within the locked stack)
