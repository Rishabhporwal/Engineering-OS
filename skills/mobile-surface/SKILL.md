---
name: mobile-surface
description: Brain's RN + Expo (SDK 56) mobile stack — invariants, offline-first, Expo Push, deep links, OTA-vs-native, cert pinning, MASVS. Morning Brief UX is separate.
---

# Mobile Surface — React Native + Expo (managed)

The mobile stack for Brain's primary product surface. This skill is the **stack + plumbing** (state, offline, push, OTA, security). The Morning Brief UX/contract lives in [`morning-brief-mobile`] — reference it, don't restate it.

## Stack invariants (LOCKED — canon/TECH/10)

| Layer | Choice |
|---|---|
| Framework | **RN + Expo SDK 56** managed (RN 0.85, React 19.2); **New Arch (Fabric+TurboModules) mandatory**; **Hermes v1** |
| Navigation | **Expo Router** (file-based) |
| Styling | **Tamagui** (tokens parity with web shadcn); NativeWind/Unistyles valid co-leads |
| Server state | **TanStack Query** via tRPC RN client |
| Client state | **Redux Toolkit + redux-persist** (AsyncStorage; whitelist `ui`+`mobile`) |
| Charts | **`victory-native`** (Recharts/Visx don't run on RN) |
| Forms | React Hook Form + Zod |
| Secure storage | **`expo-secure-store`** (Keychain/Keystore) — refresh tokens only |
| Other storage | AsyncStorage (non-sensitive) · `expo-file-system` (large assets) |
| Push | **`expo-notifications`** + Expo Push → APNS/FCM |
| Auth | Supabase Auth RN + `expo-auth-session`; biometric `expo-local-authentication` (Phase 2) |
| Builds / OTA | **EAS Build** + **EAS Update**; **E2E Detox**, unit Vitest + RNTL |
| Crash/analytics | Sentry RN + PostHog RN |

Release pipeline + EAS profiles + store hazards live in [`app-store-deployment`]. Indian numbering: shared `formatINR` from `packages/lib-formatters` (`₹4,82,000`, never `₹482,000`).

## Auth token storage

```typescript
await SecureStore.setItemAsync('brain.refresh_token', token, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
```
Refresh token → secure-store; access token → in-memory only (lost on kill → forces refresh); refresh on foreground + 5-min idle; biometric re-prompt before sensitive views (Phase 2).

## Offline-first (Indian metro network reality)

4G drops to Edge in elevators/tunnels; the app MUST render last-known state, never a bare spinner. Storage routing: tokens→secure-store, UI state→redux-persist, API cache→AsyncStorage persistor, sync queue→AsyncStorage (capped), large assets→`expo-file-system`.

**Queued mutations** — ULID-keyed for idempotency, persisted immediately, flushed on reconnect:

```typescript
const SYNC_QUEUE_KEY = 'brain:sync-queue:v1'; const MAX_QUEUE = 1000;
async enqueue(m) {
  const item = { ...m, id: ulid(), timestamp: Date.now() };
  this.queue.push(item);
  if (this.queue.length > MAX_QUEUE) this.queue.shift();              // drop oldest
  await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(this.queue));
  if (this.isOnline) this.flush();
}
async flush() {
  const remaining = [];
  for (const item of this.queue) {
    try { await trpcClient.request({ ...item, headers: { 'Idempotency-Key': item.id } }); }  // server dedups
    catch (err) { if (isRetriableError(err)) remaining.push(item); /* else drop + Sentry */ }
  }
  this.queue = remaining; await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(this.queue));
}
```

`NetInfo` listener flushes on offline→online transition. **Reads** can be hours stale (with a banner); **writes** must be idempotent + retried. Server (`idempotency-handling`) deduplicates by the ULID.

**Conflict resolution:** mutations are server-authoritative. On 409, **never client-resolve** Decision Log / consent / ad-spend writes — surface "this changed, reload?" and keep the user's pending intent retryable. Last-write-wins only for non-critical UI state (last filter, draft notes). The offline-first cached render pattern for the brief itself lives in [`morning-brief-mobile`].

**Offline UI:** show a `NetInfo`-driven banner ("You're offline — changes will sync"); disclose staleness honestly ("Stale since 06:55 IST"), never an unmarked spinner-into-old-data.

## Push notifications (Expo Push)

`notifications-service` (Vikram, Node) → Expo Push Service → APNS/FCM. Brain does **not** use raw Firebase/APNS.

**Client (Karan):** request permission **after first value, never at launch** (iOS lets you ask once; PostHog `push_permission_denied` >60% = asked too early). Android channels must exist before `getExpoPushTokenAsync`. Re-register token on every launch (idempotent server-side). Simulator can't receive APNS — test on a real device.

```typescript
Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldShowBanner: true, shouldPlaySound: true, shouldSetBadge: true }) });

const PayloadSchema = z.object({ kind: z.enum(['morning_brief','alert','lifecycle','system']), workspace_id: z.string().uuid(), deep_link: z.string().optional() });
Notifications.addNotificationResponseReceivedListener(({ notification }) => {
  const parsed = PayloadSchema.safeParse(notification.request.content.data);   // NEVER trust the payload — Zod first
  if (!parsed.success) return Sentry.captureMessage('push.payload.invalid');
  switch (parsed.data.kind) { case 'morning_brief': router.push(`/(brief)/${parsed.data.workspace_id}`); break; /* ... */ }
});
```

**Android channels:** `morning-brief` (HIGH), `alerts` (MAX), `lifecycle` (DEFAULT, Phase 3), `system` (LOW) — so users mute categories independently.

**Producer (Vikram):** `expo-server-sdk`, batches ≤100 (`chunkPushNotifications`). Tickets are synchronous, **receipts ~15min async** — schedule a BullMQ receipt check; on `DeviceNotRegistered` purge the token, on `MessageTooBig`/`MessageRateExceeded` log/alert. Morning Brief dispatch deduped by `(workspace_id, brief_id, date)`. **Never put PII/secrets in a payload** (visible in the OS notification log). The Morning Brief delivery chain + SLO is owned by [`morning-brief-mobile`].

## Deep links + simulator inner loop

Deep links: `brain://morning-brief/{id}`, `brain://auth/callback`. Test without a real push:
```bash
xcrun simctl openurl booted "brain://morning-brief"          # deep link
xcrun simctl push booted <bundle-id> payload.apns.json       # local push
npx expo start                                               # i=iOS, a=Android, r=reload, m=dev menu
```
**Expo Go vs dev client:** the moment you add a native module (cert pinning, custom dep), Expo Go can't load it — use a dev client (`expo run:ios`/`run:android`). Sim is the inner loop, but a real device + EAS build is required before PASS (push/biometric/perf differ).

## OTA vs native bump

| Change | Path |
|---|---|
| JS bugfix / asset | EAS Update OTA (`eas update --branch production`) |
| New Expo SDK / native module / permission / bundle-id / icon | Native bump → store review |

**Anti-pattern:** OTA when a native module was added → silent break for users. Any `package.json` change to a native-touching dep → native bump; `runtimeVersion` discipline (see [`app-store-deployment`]).

## Cert pinning rotation (CRITICAL — canon/TECH/10)

Pin **both** current + rotation cert. Sequence: (1) add new pin to `PINS`; (2) OTA the new pin set **one week before** server rotation; (3) rotate server cert; (4) remove old pin in next OTA. Keep an unpinned HTTP kill-switch endpoint as the recovery path.

```typescript
const PINS = ['sha256/AAAA...current', 'sha256/BBBB...rotation'];
```

## Desktop-only views (mobile fallback)

Cohort heatmap, CM Waterfall, First Product Cascade, COGS/classification bulk editors, exports → link out, don't cram:
```tsx
<EmptyState title="This view works best on desktop" cta={<Link href="https://brain.pipadacapital.com/...">Open in browser →</Link>} />
```

## MASVS security

MASVS L1 + key L2: refresh token in secure-store / access token in memory; magic-link via universal/app links; cert pinning (above); no PII in logs (Sentry breadcrumbs rate-limited); biometric before financial views (Phase 2). See [`security-baseline`] §MASVS.

## Anti-patterns

- OTA on a native change (silent break); cert-pin rotation without the OTA-before-rotate sequence (bricks app); push permission at launch; token in DOM during magic-link callback (XSS); Recharts on RN (use `victory-native`); `₹482,000` (use `formatINR`).
- Tokens/PII in AsyncStorage (use secure-store); last-write-wins on Decision Log/consent/ad-spend; unbounded sync queue (AsyncStorage throws ~5MB on Android); trusting `NetInfo.isConnected===true` as working network; queueing auth-mutating actions (run synchronously).
- Trusting a push payload for navigation without Zod; skipping receipt checking (dead tokens accumulate); PII/secrets in a payload; `sound: 'custom.wav'` (managed-workflow — use `'default'`).

## Verify

- Real device, airplane mode: brief renders from cache with staleness banner; a queued mutation survives an app kill and flushes on reconnect with its idempotency key.
- `xcrun simctl openurl booted "brain://morning-brief"` opens the right screen; a `simctl push` routes by validated `kind`.
- OTA-channel test build pulls a preview update; a native-touching dep change triggers a native bump in CI.

## References

- canon/TECH/10 — RN/Expo stack, push, secure-store, cert pinning, MASVS
- [`morning-brief-mobile`] — the brief UX, contract, delivery SLO, offline-render pattern
- [`app-store-deployment`] — EAS Build/Update, profiles, OTA-vs-store, store hazards
- [`idempotency-handling`] — server dedup for queued mutations · [`defense-in-depth-validation`] — push payload validation
- [`security-baseline`] §MASVS · [`region-and-locale`] — RN RTL + Indian numbering
