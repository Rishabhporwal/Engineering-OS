---
name: frontend-mobile
description: Brain's React Native + Expo stack (Expo SDK 56, RN 0.85, React 19.2, Hermes v1) — Expo Router + Tamagui + tRPC client + Redux Toolkit + TanStack Query + redux-persist (AsyncStorage) + expo-secure-store + expo-notifications + victory-native + EAS Build/Update. Use whenever Karan is building mobile screens, the Morning Brief surface, push notification handling, deep linking, cert pinning, MASVS controls, or anything in apps/mobile/. Covers the THREE-signal Morning Brief rule, OTA-vs-native bump policy, and the desktop-fallback pattern for views that don't translate.
---

# Frontend Mobile — React Native + Expo (managed)

The mobile stack for Brain's **primary product surface**. The Morning Brief is THE product workflow — three signals at 06:55–09:00 IST, approve / reject / edit, three-minute commitment, thumb-first.

## Stack invariants (LOCKED — canon/technical-requirements.md §1)

| Layer | Choice | Reason |
|---|---|---|
| Framework | **React Native + Expo SDK 56** managed workflow (RN 0.85, React 19.2) | One TS codebase ships iOS + Android |
| Architecture | **New Architecture (Fabric + TurboModules) is MANDATORY** — non-disableable since SDK 55 | The legacy architecture is gone; nothing to opt into |
| JS engine | **Hermes v1** (default since SDK 56) | Faster startup + lower memory |
| Styling | **Tamagui** stays Brain's choice; **NativeWind / Unistyles are now valid co-leads** if a screen prefers Tailwind-class or atomic styling | Tokens parity with web shadcn either way |
| Navigation | **Expo Router** (file-based) | Mirrors Next.js App Router mental model |
| Server state | **TanStack Query** via tRPC RN client | Same hooks pattern as web |
| Client state | **Redux Toolkit + redux-persist** (AsyncStorage; whitelist `ui` + `mobile`) | Shared slices with web |
| UI primitives | **Tamagui** (`@tamagui/core`) | Native-feel; tokens parity with shadcn web |
| Charts | **`victory-native`** (D3 on Skia) | Recharts/Visx don't work on RN |
| Forms | React Hook Form + Zod | Same as web |
| Secure storage | **`expo-secure-store`** (Keychain iOS / Keystore Android) | Refresh tokens only |
| Other storage | AsyncStorage | Non-sensitive prefs |
| HTTP | tRPC client over fetch | |
| Subscriptions | tRPC subscription + `event-source-polyfill` | AI Chat streaming, live refresh |
| Push | **`expo-notifications`** + APNS + FCM via Expo Push API | |
| Auth | Supabase Auth RN SDK + `expo-auth-session` | Google OAuth |
| Biometric | `expo-local-authentication` | Phase 2 |
| Crash | Sentry RN SDK | |
| Analytics | PostHog RN SDK | Same project as web |
| Builds | **EAS Build** (production tier $99/mo) | Cloud builds; no Mac runners |
| Distribution | App Store + Google Play | TestFlight beta + Play Internal Track |
| OTA | **EAS Update** | JS-only patches; rolling release in minutes |
| E2E | **Detox** (macOS iOS sim + Linux Android emu) | |
| Unit | Vitest + React Native Testing Library | |

## Morning Brief — the three-signal rule

The Morning Brief is the highest-quality UI in all of Brain (canon/technical-requirements.md mandate). Get it right:

- **Three signals max** — not five, not seven. The Synthesizer (Maya) picks top three by priority score.
- **One-thumb operation** — swipe between cards; tap approve/reject; long-press to edit.
- **Three-minute total commitment** — if reading takes longer, the Synthesizer output is too verbose; flag for Maya.
- **Action + magnitude + outcome + safety** in one sentence per signal:
  > "Pause campaign X creative; reallocate ₹50K/day from Meta to Google; expected to recover ₹2.8L over 30 days; cashflow neutral."
- **Approval flow:**
  - Approve → MCP write-back fires (`integrations.meta.pause_ad_set` etc.) → Decision Log entry → confirmation toast
  - Reject → logged with reason → Decision Log entry (state: rejected) → next signal
  - Edit → magnitude slider modal → save returns to approve flow
- **Push:** 07:00 IST digest push; deep link `brain://morning-brief` opens directly to it.

```tsx
// apps/mobile/components/morning-brief/SignalCard.tsx
import { Stack, Text, Button, XStack } from 'tamagui';
import { trpc } from '@/lib/trpc';

export function SignalCard({ signal }: { signal: Recommendation }) {
  const approve = trpc.lifecycle.approveRecommendation.useMutation();
  return (
    <Stack padding="$4">
      <Text fontSize="$6">{signal.headline}</Text>
      <Text>{signal.rationale_short}</Text>
      <XStack gap="$2">
        <Button onPress={() => approve.mutate({ id: signal.id, action: 'approve' })}>Approve</Button>
        <Button onPress={() => approve.mutate({ id: signal.id, action: 'reject' })}>Reject</Button>
        <Button onPress={() => openEditDrawer(signal)}>Edit</Button>
      </XStack>
    </Stack>
  );
}
```

## Auth flow (canon/technical-requirements.md §4)

```typescript
// apps/mobile/lib/auth/storage.ts
import * as SecureStore from 'expo-secure-store';

export async function storeRefreshToken(token: string) {
  await SecureStore.setItemAsync('brain.refresh_token', token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}
```

- Refresh token → `expo-secure-store` (Keychain `WHEN_UNLOCKED_THIS_DEVICE_ONLY`)
- Access token → in-memory only (lost on app kill → forces refresh)
- Refresh on app foreground + 5-min idle
- Biometric re-prompt before sensitive views (Phase 2)

## Push notifications (canon/technical-requirements.md §7)

```typescript
// apps/mobile/lib/push/register.ts
import * as Notifications from 'expo-notifications';

export async function registerForPush() {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return null;
  const { data: pushToken } = await Notifications.getExpoPushTokenAsync({ projectId: EXPO_PROJECT_ID });
  await trpcClient.notifications.registerPushToken.mutate({ pushToken, platform: Platform.OS, deviceId: await getDeviceId() });
  return pushToken;
}
```

**Don't ask for permission on first launch.** Ask after first useful interaction (PostHog `push_permission_denied` > 60% = you asked too early).

Android channels: `alerts.critical` (high), `alerts.warning` (default), `digests` (low), `insights` (default).

## OTA vs native bump policy (canon/technical-requirements.md §9)

| Change | Path |
|---|---|
| JS bugfix | EAS Update OTA (`eas update --channel production --message "..."`) |
| New Expo SDK | Native bump → App Store / Play Store review |
| New native module | Native bump |
| Permission change | Native bump |
| Bundle ID / icon | Native bump |

**Anti-pattern:** pushing OTA when a native module was added → silently breaks for users. Discipline: any `package.json` change to a native-touching dep → native bump.

## Cert pinning rotation (CRITICAL — canon/technical-requirements.md §11)

Pin BOTH current + rotation cert. Rotation sequence:

1. Add new cert pin to `PINS` array
2. OTA-update new pin set **ONE WEEK BEFORE** server rotation
3. Rotate cert on server
4. Remove old pin in next OTA

Kill-switch endpoint (HTTP, no pinning) as emergency escape.

```typescript
// apps/mobile/lib/pinning.ts
const PINS = [
  'sha256/AAAA...current-cert-pin',
  'sha256/BBBB...rotation-cert-pin',
];
```

## Desktop-only views (mobile fallback)

```tsx
// Mobile shows this instead of trying to render:
<EmptyState
  title="This view works best on desktop"
  description="Cohort heatmap, CM Waterfall, First Product Cascade, settings bulk editors, exports"
  cta={<Link href={`https://brain.pipadacapital.com/${workspaceId}/...`}>Open in browser →</Link>}
/>
```

List in canon/technical-requirements.md §3.

## Versioning (canon/technical-requirements.md §14)

```json
{
  "expo": {
    "version": "1.2.0",
    "ios":     { "buildNumber": "47" },
    "android": { "versionCode": 47 }
  }
}
```

`min_supported_version` lives in `app_versions` table — force-update only for security-critical fixes.

## Indian numbering (mobile)

```tsx
import { formatINR } from '@brain/formatters';
formatINR(482000n)  // "₹4,82,000"
```

Same formatter as web (shared `packages/lib-formatters`).

## Path layout

```
apps/mobile/
  app/(workspace)/<route>.tsx
  components/morning-brief/{SignalCard,ApprovalButtons,EditDrawer}.tsx
  lib/{trpc,auth,push,pinning,logger}.ts
  app.json    eas.json
packages/ui-mobile/<Component>.tsx
packages/state/slices/<slice>.ts
```

## Local dev loop — simulator + Expo (the inner loop)

Before EAS cloud builds and Detox, this is the fast iteration loop Karan lives in. EAS Build is for releases; the simulator is for development. Don't wait on a 15-min cloud build to test a layout change.

```bash
# Start Metro + dev server (from apps/mobile)
pnpm --filter mobile start            # or: npx expo start
#   press i → open iOS Simulator   |  press a → open Android emulator
#   press r → reload               |  press m → toggle dev menu
#   press shift+i → pick a specific iOS simulator device

# Custom dev client (needed once you add any native module — Expo Go won't load it)
npx expo run:ios                      # builds + installs the dev client on the sim
npx expo run:android
```

**Expo Go vs dev client:** Expo Go runs JS-only against the Expo SDK. The moment you add a native module (cert pinning, a custom native dep), Expo Go can't load it — you must use a **dev client** (`expo run:ios`/`run:android`). Symptom of getting this wrong: "module not found" / native crash only in Expo Go.

### Driving the simulator directly (`simctl`)

```bash
xcrun simctl list devices                              # find booted/available sims
xcrun simctl boot "iPhone 15 Pro"                      # boot a specific device
xcrun simctl openurl booted "brain://morning-brief"    # test a deep link without a push
xcrun simctl push booted <bundle-id> payload.apns.json # test a push notification locally
xcrun simctl io booted screenshot brief.png            # capture a screenshot for the PR
```

Deep-link + push testing on the simulator is the fast way to verify the Morning Brief entry points (`brain://morning-brief`, `brain://auth/callback`) before wiring real APNS/FCM.

### When the simulator misbehaves

- **Stale JS / weird state** → press `r` to reload, or shake (dev menu) → Reload. If still wrong, `npx expo start -c` (clears Metro cache).
- **Native change not reflected** → Expo Go can't show it; rebuild the dev client (`expo run:ios`).
- **Sim won't boot / black screen** → `xcrun simctl erase all` (wipes all sims — resets to clean state).
- **Push not arriving** → simulators need `simctl push` (real APNS doesn't reach the sim); test the real path on a device.

The simulator is the inner loop; a real device + EAS build is still required before a PASS (per `verification-before-completion` — sim behavior ≠ device behavior for push, biometrics, and performance).

## Detox flow (mandatory for Morning Brief PR)

```javascript
describe('Morning Brief approve flow', () => {
  it('approves a signal and writes Decision Log', async () => {
    await element(by.id('signal-card-0')).swipe('left');
    await element(by.id('approve-button')).tap();
    await expect(element(by.id('approved-toast'))).toBeVisible();
  });
});
```

## Common pitfalls

- **OTA on native change** — silent break. Always native bump.
- **Cert pinning rotation footgun** — bricks app. New pin OTA *before* server cert rotation.
- **Push permission asked too early** — denied forever. Ask after first useful interaction.
- **Token rendered in DOM** during magic-link callback — XSS. Process server-side.
- **Recharts on RN** — doesn't render. Use `victory-native`.
- **Indian numbering** — `₹482,000` is wrong. Use `formatINR`.

## References

- `canon/technical-requirements.md` — the entire mobile spec
- `canon/technical-requirements.md` §push — notifications-service path
- `skills/morning-brief-mobile/SKILL.md` — the Morning Brief UX rules in depth
- `skills/security-baseline/SKILL.md` §MASVS
- `skills/india-commerce-economics/SKILL.md` §currency-format
