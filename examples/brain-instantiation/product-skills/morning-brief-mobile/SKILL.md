---
name: morning-brief-mobile
description: Brain's Morning Brief (canon/TECH/10) — THE product surface. Thumb-first, ≤3 ranked actions, approve-reject-edit→Decision Log, Sonnet 07:15 IST, push by 07:20.
---

# Morning Brief — the product

Mobile is **THE primary surface for the product's defining workflow.** Web is the workbench; the phone is the daily heartbeat. The Morning Brief screen **must be the highest-quality UI in all of Brain** — designed for the **06:55–09:00 IST coffee-in-hand, one-handed, three-minute** flow.

**Canon:** `canon/TECH/10_mobile_architecture.md` · `canon/business-requirements.md` §8.2. Stack: RN + **Expo SDK 56** (managed; **Hermes v1**), Expo Router, Tamagui, `victory-native`, `expo-secure-store`, `expo-notifications`. Stack/offline/push plumbing lives in [`mobile-surface`].

> **Hermes v1 directly serves this surface:** ~29% faster cold start + ~38% less memory means the brief renders sooner from a cold launch — load-bearing for the **<100ms-from-cache** open and the 3-minute SLO when a founder taps the 07:00 push after an overnight app kill.

## The contract (business-requirements §8.2)

**At most three ranked actions — not a dump of charts.** Each action, in order:

1. **Problem** — what's wrong / the opportunity, plain language.
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

**Every approve/reject/edit writes the user's response into `ai.decision_log`** (status, `user_response`) — a Morning Brief action that cannot write here is not a Brain action ([`metric-engine`] supplies the numbers; LLMs never invent them).

## The three-signal rule

Exactly **≤3 actions**, ranked by expected CM2 impact × urgency × confidence × reversibility. If the daily tick produces more candidates, the synthesizer selects the top 3 — *fewer, decisive* signals over a feed. More than three breaks the three-minute promise.

## How the brief is produced — the Daily Intelligence Loop (IST)

The brief is the **only frontier-LLM step** in the pipeline (canon/TECH/05; [`cost-routing-paradigms`]):

```
06:55  freshness gate (P0 integrations < 1h, else label "estimated")
07:00  Brand Fingerprint refresh        (SQL + numpy — paradigm 1)
07:05  Memory query                     (pgvector — paradigm 2)
07:10  15 agents run in parallel        (SQL/ML, each writes Decision Log candidates)
07:15  Morning Brief SYNTHESIZED        (Claude Sonnet — paradigm 4, the ONE LLM step)
       → publish intelligence.morning_brief.generated.v1
07:00–09:00  notifications-service delivers via Expo Push
```

The Sonnet synthesizer **narrates** the agents' deterministic outputs into ≤3 ranked actions — it does not compute the numbers ([`memory-layer-pgvector`], [`claude-api`] for prompt-caching the Brand Fingerprint + Decision Log context).

## Delivery (Expo Push)

`notifications-service` consumes `intelligence.morning_brief.generated.v1` → Expo Push → APNS/FCM. Deep-links straight to the brief (`brain://morning-brief/{id}`). Push token registered post-login (`registerPushToken` tRPC), stored in `mobile_push_tokens`; `DeviceNotRegistered` receipts deactivate dead tokens. The brief is a normal (not critical-alert) push. Push wiring detail in [`mobile-surface`] / [`app-store-deployment`].

## Offline-first render

The brief MUST render in <100ms from cache; the network refresh is decoration. Use TanStack Query with `placeholderData` from the persisted last-known brief; show a stale banner; only show the skeleton if there is no cached version at all:

```tsx
const { data, isStale, dataUpdatedAt } = useQuery({
  queryKey: ['morning-brief', workspaceId, today],
  queryFn: () => trpc.morningBrief.get.query({ workspaceId, date: today }),
  staleTime: 1000*60*60*4, gcTime: 1000*60*60*24,
  placeholderData: () => getPersistedBrief(workspaceId, today),
});
if (!data) return <BriefSkeleton />;
return <View>{isStale && <StaleBanner since={dataUpdatedAt} />}<BriefBody data={data} /></View>;
```
Offline queue semantics (server-authoritative, 409 handling) live in [`mobile-surface`].

## SLO + quality bar

- **Delivered by 07:20 IST on > 99.5% of days** (canon §14). Monitor end-to-end latency of the 06:55→delivery chain.
- Thumb-first: primary actions one-handed; approve/reject large tap targets; no horizontal scroll for the core flow.
- Currency-aware via shared formatters (₹ lakh/crore for INR; locale otherwise) — [`region-and-locale`].
- Every evidence number drills to source rows.

## Security (MASVS L1 + key L2)

Refresh token in `expo-secure-store`, access token in memory; magic-link via universal/app links; cert pinning (pin current **and** rotation cert; rotate the pin via OTA a week before cert renewal; unpinned kill-switch endpoint); no PII in logs; biometric before financial views (Phase 2). Detail in [`mobile-surface`] / [`compliance-engine`].

## Phasing

- **Phase 1 (W12–14):** read-only brief + approve/reject + push; online-only ("Offline — last updated Nm ago" via NetInfo).
- **Phase 2:** edit + AI chat + biometric; cached reads.
- **Phase 3:** plan/pincode summaries + notification rich-actions + optimistic offline queue.

Desktop-only views (cohort heatmap, CM waterfall, First Product Cascade, COGS bulk editor) link out gracefully — never crammed onto the phone.

## Anti-patterns

- More than three actions / a chart dump; an action without expected revenue + CM2 or without confidence/risk; approve/reject that doesn't write the response to the Decision Log; the Sonnet synthesizer computing a metric instead of narrating registry numbers; shipping from stale data without the freshness gate / "estimated" label; Recharts/Visx on RN (use `victory-native`); refresh token in AsyncStorage instead of secure-store.

## Verify

- A simulated daily tick produces ≤3 ranked actions, each with all six fields; tapping Approve writes a `decision_log` row with the user_response.
- Push arrives before 07:20 IST in a delivery test; deep link opens the correct brief.
- Evidence numbers match the metric engine and drill to source rows.

## References

- canon/TECH/10 — RN/Expo stack, push, secure-store, cert pinning, MASVS, phasing
- canon/business-requirements.md §8.2 — Morning Brief contract · canon/TECH/05 — the daily tick + Sonnet synthesis
- [`mobile-surface`] · [`push: see mobile-surface`] · [`memory-layer-pgvector`] · [`metric-engine`] · [`region-and-locale`]
