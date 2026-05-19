---
name: morning-brief-mobile
description: Brain's Morning Brief — THE primary product surface. Three signals per morning, 06:55–07:15 IST agent fan-out → 07:15 Sonnet synthesis → push delivered 07:00–09:00 IST. Thumb-first one-handed operation, three-minute total commitment. Auto-load whenever modifying the Morning Brief screen, the daily-tick orchestrator, the Synthesizer Sonnet prompt, or push delivery for the morning digest. The Morning Brief screen must be the highest-quality piece of UI in all of Brain.
---

# Morning Brief — Brain's Defining Surface

The Morning Brief **is** the product (canon/BRAIN_TECHNICAL.md mandate revision). Three signals at coffee time, approve / reject / edit, three-minute commitment. Mobile-first; web has a parallel "Daily" view but mobile leads.

**Canonical docs:** `canon/BRAIN_TECHNICAL.md` §morning-brief, `canon/BRAIN_TECHNICAL.md` §morning-brief-synthesizer.

## Operational SLO (non-negotiable — from architecture review 2026-05-16)

The Brief synthesis window is **06:55–07:15 IST**. Push delivers into the **07:00–09:00 IST coffee window**. The window has **zero slack** — if any phase blows past its budget, the Brief misses coffee, and the Brief IS the product.

**SLO**: Brief delivered by 07:20 IST > **99.5% of days** per workspace.

**Mandatory operational control: synthetic Brief canary at 06:50 IST in staging.**

- A scheduled job runs in staging at 06:50 IST every day that exercises the full daily-tick pipeline against a synthetic workspace (`workspace_id=__canary__`): ingestion sync → fingerprint build → memory query → agent fan-out → Sonnet synthesis → notifications-service → Expo push receipt.
- The canary asserts each phase completes within its 5-min budget AND the final push receipt is acknowledged by Expo within 60s of synthesis completion.
- Any phase missing its budget pages **Jatin (P2)** AND **Maya** within 60 seconds — we want to know at 06:52 that prod is broken, not at 07:25 from a missed-coffee operator.
- If three canaries miss in 7 days, the next morning's prod Brief auto-fails-over to the previous day's Brief with a "stale since <date>" banner (mobile-offline-support pattern) rather than ship no Brief at all.

See `memory/decisions/ADR-DRAFT-2026-05-16-stack-review.md` §Recommendations #3, and `skills/health-check-endpoints/SKILL.md` for the canary primitive.

## The shape (NON-NEGOTIABLE)

- **Three signals max.** Synthesizer picks top three by priority score across all 15 agents (see canon/BRAIN_TECHNICAL.md). Not five, not seven.
- **One-thumb operation.** Swipe between cards. Tap approve / reject. Long-press to edit (magnitude slider).
- **Three-minute total commitment.** If reading takes longer, the Synthesizer output is too verbose — flag for Maya.
- **Each signal is ONE sentence:** action + magnitude + outcome + safety check.
  > "Pause campaign X creative; reallocate ₹50K/day from Meta to Google; expected to recover ₹2.8L over 30 days; cashflow neutral."
- **Approve → MCP write-back fires** (e.g., `integrations.meta.pause_ad_set`) → Decision Log entry → confirmation toast.
- **Reject → logged** (Decision Log state `rejected`) → next signal.
- **Edit → magnitude slider modal** → save returns to approve flow → Decision Log captures both original and edited values.

## The daily tick (canon/BRAIN_TECHNICAL.md)

```
06:55 IST — orchestration/daily_tick.py
   ▼
For each workspace × each agent (parallel; 5-min budget each):
   1. Memory query: Brand Fingerprint k=5 similar past states (paradigm 2)
   2. Run paradigm models (mostly ML — EWMA, XGBoost, Prophet, pgvector, isotonic, BG/NBD)
   3. Generate ranked recommendations
   4. Persist to Decision Log (state: pending if agent not graduated)
   ▼
07:15 IST — orchestration/morning_brief.py
   ▼
Pull top-3 priority-scored across all agents per workspace
   ▼
@paradigm("frontier_llm", model="claude-sonnet-4-6", token_budget=2000)
   Sonnet synthesizes plain-English: action + magnitude + outcome + safety
   ↳ prompt caching ALWAYS on
   ↳ fallback: template brief if budget breached
   ▼
notifications-service → push delivered 07:00–09:00 IST (varies by individual quiet hours)
```

The Synthesizer is the **only** Frontier-LLM call in the daily loop. Everything upstream is paradigm 1 or 2. This is the cost-routing invariant in action.

## The Synthesizer prompt structure

```
You are the Morning Brief synthesizer for {brand_name}. Below are three recommendations from specialist agents.

For each, produce one sentence in this exact shape:
  <Action> <magnitude>; expected to <outcome with magnitude> over <horizon>; <safety check>.

Use plain English, no jargon. Show numbers in Indian numbering (₹4,82,000). Use the brand's voice: {brand_voice_descriptor}.

Recommendations (already prioritised; do not reorder):
1. {agent_1.action_payload}
2. {agent_2.action_payload}
3. {agent_3.action_payload}

Constraints:
- Each item ONE sentence
- Total reading time < 60 seconds
- No preamble, no closing
```

System prompt cached. Per-brand context cached separately. Token budget 2000 (canon/BRAIN_TECHNICAL.md Layer 2).

## Token budget enforcement

```python
@paradigm("frontier_llm", model="claude-sonnet-4-6", token_budget=2000)
async def synthesize_morning_brief(workspace_id, signals):
    response = await sonnet_client.synthesize(
        ...,
        max_tokens=2000,
        cache_control={"type": "ephemeral"},
        on_budget_warning=lambda: log_event("token_budget_80", workspace_id),
        on_budget_exceeded=lambda: fallback_to_template_brief(workspace_id, signals),
    )
    return response
```

Fallback: template brief (paradigm 1) — concatenates `agent.rationale_short` per signal. Less polished but ships.

## Mobile screen (Karan owns)

```tsx
// apps/mobile/app/(workspace)/morning-brief.tsx
import { Stack, ScrollView } from 'tamagui';
import { trpc } from '@/lib/trpc';
import { SignalCard } from '@/components/morning-brief/SignalCard';

export default function MorningBriefScreen() {
  const { data, isLoading } = trpc.morningBrief.today.useQuery();
  if (isLoading) return <Skeleton />;
  if (!data?.signals?.length) return <EmptyState title="No signals today" />;

  return (
    <ScrollView horizontal pagingEnabled>
      {data.signals.map(signal => <SignalCard key={signal.id} signal={signal} />)}
    </ScrollView>
  );
}
```

Each `SignalCard` exposes `data-testid` for Detox flows.

## Push delivery (canon/BRAIN_TECHNICAL.md)

- Channel: `digests` (Android); priority default
- Title: `"☀️ Today's Brief — {brand_name}"`
- Body: count + headline of top signal ("3 recommendations · Pause campaign X...")
- Deep link: `brain://morning-brief`
- Respects per-workspace quiet hours (notifications-service gate)

## Detox flow (mandatory per release)

```javascript
describe('Morning Brief', () => {
  it('renders three signals, approve writes Decision Log', async () => {
    await device.launchApp();
    await element(by.id('login-email')).typeText('test@brand.com');
    await element(by.id('send-link-button')).tap();
    await device.openURL({ url: 'brain://auth/callback?token=...' });
    await device.openURL({ url: 'brain://morning-brief' });

    await expect(element(by.id('signal-card-0'))).toBeVisible();
    await expect(element(by.id('signal-card-1'))).toBeVisible();
    await expect(element(by.id('signal-card-2'))).toBeVisible();

    await element(by.id('signal-card-0')).swipe('right');
    await element(by.id('approve-button')).tap();
    await expect(element(by.id('approved-toast'))).toBeVisible();
    // Backend assertion: ai.decision_log has new row with state='approved'
  });
});
```

## Edit flow

```
User long-presses signal → EditDrawer opens
   ▼
Magnitude slider (e.g., budget shift: ₹30K / ₹50K / ₹80K)
   ▼
Slider value bounded by agent's recommended range
   ▼
Save → original + edited values both logged to Decision Log
   ▼
MCP write-back fires with edited magnitude
   ▼
Confirmation toast → next signal
```

If the user moves the slider outside the agent's recommended range, show a warning + require an additional tap to confirm.

## Web parallel "Daily" view (Ananya)

Web doesn't compete with mobile here — it's a *Monday review* surface, not a daily ritual. Layout: same three signals + drill-down to underlying data (orders, campaigns, customers). Operator can approve from web too, but the push notification goes to mobile.

## Success metrics

- **Mobile DAU / brand:** > 60% by month 3 (Sugandh Lok + 3+ paying brands)
- **Median time-to-first-action:** < 90 seconds
- **Approve rate** across all agents over rolling 30 days (feeds graduation)
- **Reading time** (PostHog `morning_brief.signal_viewed_at` → `signal_actioned_at`): median < 60s per signal
- **Push open rate** (canon/BRAIN_TECHNICAL.md): > 40%

## Common failure modes

- **Synthesizer too verbose** — three signals turn into 800 words. Detection: reading-time PostHog median > 90s/signal. Mitigation: prompt tweak; constrain max_tokens.
- **Wrong paradigm in daily tick** — an agent uses Sonnet where EWMA would have answered. Detection: paradigm-distribution dashboard. Maya audits prompts.
- **Push at the wrong hour** — workspace quiet hours not respected. Detection: PostHog `push_received_at` shows < 06:00 or > 21:00 local.
- **Approve doesn't fire MCP write-back** — silently broken. Detection: Decision Log shows state='approved' but no `mcp_writeback_completed_at`. Mitigation: Detox flow asserts toast + DB write.
- **Magnitude edit silently out of range** — agent's recommendation said ±₹50K but user edited to ±₹500K. Mitigation: bounded slider + confirm tap if outside.
- **Per-tenant signal leak** — workspace A sees workspace B's signal. Mitigation: `requireTenant` middleware on tRPC; Detox flow verifies.

## References

- `canon/BRAIN_TECHNICAL.md` §morning-brief — UX spec
- `canon/BRAIN_TECHNICAL.md` §morning-brief-synthesizer — orchestration
- `canon/BRAIN_TECHNICAL.md` — token budget + fallback
- `canon/BRAIN_TECHNICAL.md` — write-back tools fired on approve
- `skills/frontend-mobile/SKILL.md` — RN + Tamagui implementation
- `skills/agentic-design/SKILL.md` — daily-tick orchestration
- `skills/cost-routing-paradigms/SKILL.md` — Synthesizer is the only paradigm-4 call
