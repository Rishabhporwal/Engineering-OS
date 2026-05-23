---
name: morning-brief-mobile
description: Brain's Morning Brief (canon/TECH/10) — THE primary product surface. Mobile-first, thumb-first, 3-minute commitment, ≤3 ranked actions each with problem/evidence/recommended-action/expected-impact(revenue+CM2)/risk/confidence and approve-reject-edit buttons that write the user's response to the Decision Log. Synthesized by the daily tick (Sonnet at 07:15 IST) and delivered by Expo Push 07:00–09:00 IST. Stack: RN + Expo, Tamagui, victory-native, expo-secure-store, deep links, cert pinning, MASVS. SLO: delivered by 07:20 IST on >99.5% of days. Auto-load when modifying the Morning Brief screen, the daily-tick orchestrator, the Synthesizer prompt, or morning push.
---

# Morning Brief — the product

Mobile is **THE primary surface for the product's defining workflow.** Web is the workbench (Monday review + on-demand depth); the phone is the daily heartbeat. The Morning Brief screen **must be the highest-quality piece of UI in all of Brain** — designed for the **06:55–09:00 IST coffee-in-hand, one-handed, three-minute** flow.

**Canonical sources:** `canon/TECH/10_mobile_architecture.md` · `canon/business-requirements.md` §8.2. Tech stack: React Native + **Expo SDK 56** (managed; **Hermes v1** default), Expo Router, Tamagui (tokens parity with web shadcn), `victory-native` (Recharts/Visx don't run on RN), `expo-secure-store`, `expo-notifications` (Expo Push → APNS + FCM).

> **Hermes v1 (SDK 56) directly serves this surface:** ~29% faster cold startup + ~38% less memory means the brief renders sooner from a cold launch — load-bearing for the **<100ms-from-cache** open and the 3-minute SLO when a founder taps the 07:00 push and the app was killed overnight.

## The contract (business-requirements §8.2)

The Morning Brief is **at most three ranked actions — not a dump of charts.** Each action includes, in this order:

1. **Problem** — what's wrong / the opportunity, in plain language.
2. **Evidence** — specific numbers (drillable to source).
3. **Recommended action** — the concrete next step.
4. **Expected impact** — **revenue + CM2** (and time/risk where relevant), never vanity ROAS.
5. **Risk** + **Confidence**.
6. **Approve / Reject / Edit** buttons.

```
Brain | {Brand} | {Date}
Yesterday: {Revenue} | CM2 {CM2%} | MER {MER} | RTO Risk {RTO%}

1. {Highest-priority action}
   Evidence: {specific numbers}
   Expected impact: {revenue / CM2 / time / risk}    Confidence: {0–1}
   [ Approve ]  [ Edit ]  [ Reject ]

2. {Second action}     3. {Third action}

This month: {recovered realized revenue} | {recovered CM2} | {fee coverage}× Brain fee
```

**Every approve/reject/edit writes the user's response into `ai.decision_log`** (status, `user_response`) — a Morning Brief action that cannot write here is not a Brain action ([`metric-engine`](../metric-engine/SKILL.md) supplies the numbers; LLMs never invent them).

## The three-signal rule

Exactly **≤3 actions**, ranked by expected CM2 impact × urgency × confidence × reversibility. If the daily tick produces more candidates, the synthesizer selects the top 3 — the discipline is *fewer, decisive* signals over a feed. More than three breaks the three-minute promise.

## How the brief is produced — the Daily Intelligence Loop (IST)

The brief is the **only frontier-LLM step** in the pipeline (canon/TECH/05; [`cost-routing-paradigms`](../cost-routing-paradigms/SKILL.md)):

```
06:55  freshness gate (P0 integrations < 1h, else label "estimated")
07:00  Brand Fingerprint refresh        (SQL + numpy — paradigm 1)
07:05  Memory query                     (pgvector — paradigm 2)
07:10  15 agents run in parallel        (SQL/ML, each writes Decision Log candidates)
07:15  Morning Brief SYNTHESIZED        (Claude Sonnet — paradigm 4, the ONE LLM step)
       → publish intelligence.morning_brief.generated.v1
07:00–09:00  notifications-service delivers via Expo Push
```

The Sonnet synthesizer **narrates** the agents' deterministic outputs into ≤3 ranked human-readable actions — it does not compute the numbers ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md), [`claude-api`](../claude-api/SKILL.md) for prompt caching the Brand Fingerprint + Decision Log context).

## Delivery (Expo Push)

`notifications-service` consumes `intelligence.morning_brief.generated.v1` and sends via the Expo Push API → APNS (iOS) / FCM (Android). The notification deep-links straight to the brief (`brain://morning-brief/{id}`). Push token registered post-login (`registerPushToken` tRPC), stored in `mobile_push_tokens`; `DeviceNotRegistered` receipts deactivate dead tokens. Android channel for digests is low-importance; the brief itself is not a critical-alert blast.

## SLO + quality bar

- **Morning Brief delivered by 07:20 IST on > 99.5% of days** (technical-context §14). Monitor end-to-end latency of the 06:55→delivery chain.
- Thumb-first: primary actions reachable one-handed; approve/reject are large tap targets; no horizontal scrolling for the core flow.
- Currency-aware rendering via shared formatters (₹ lakh/crore for INR; locale otherwise) — [`region-adapter`](../region-adapter/SKILL.md).
- Drill-down: every evidence number links to its source rows.

## Security (MASVS L1 + key L2)

Refresh token in `expo-secure-store` (Keychain/Keystore), access token in memory only; magic-link via universal/app links (`expo-linking`); **certificate pinning** (pin current **and** rotation cert — rotate the pin via OTA a week before cert renewal, with an unpinned kill-switch endpoint as the recovery path); no PII in logs (Sentry breadcrumbs, rate-limited remote events). Biometric unlock before financial views is Phase 2 ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)).

## Phasing

- **Phase 1 (W12–14):** read-only brief + approve/reject + push.
- **Phase 2:** edit + AI chat + biometric.
- **Phase 3:** plan/pincode summaries + notification rich-actions + optimistic offline queue.
- Offline: **online-only** Phase 1 (show "Offline — last updated Nm ago" via NetInfo) → cached reads Phase 2 ([`mobile-offline-support`](../mobile-offline-support/SKILL.md)).

Desktop-only views (cohort heatmap, CM waterfall, First Product Cascade, COGS bulk editor) link out gracefully — *"This view works best on desktop"* — never crammed onto the phone.

## Anti-patterns

- More than three actions / a chart dump (breaks the 3-minute, three-signal contract).
- An action without expected revenue + CM2, or without confidence/risk.
- Approve/reject that doesn't write the response to the Decision Log.
- The Sonnet synthesizer computing a metric instead of narrating registry numbers.
- Shipping the brief from stale data without the freshness gate / "estimated" label.
- Recharts/Visx on RN (use `victory-native`); refresh token in AsyncStorage instead of secure-store.

## Verify

- A simulated daily tick produces ≤3 ranked actions, each with all six fields; tapping Approve writes a `decision_log` row with the user_response.
- Push arrives before 07:20 IST in a delivery test; deep link opens the correct brief.
- Evidence numbers match the metric engine and drill to source rows.

## References

- `canon/TECH/10_mobile_architecture.md` — RN/Expo stack, push, secure-store, cert pinning, MASVS, phasing
- `canon/business-requirements.md` §8.2 — Morning Brief contract
- `canon/TECH/05_intelligence_layer.md` — the daily tick + Sonnet synthesis (07:15 IST)
- [`push-notification-setup`](../push-notification-setup/SKILL.md) · [`frontend-mobile`](../frontend-mobile/SKILL.md) · [`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md) · [`metric-engine`](../metric-engine/SKILL.md)
