---
name: mobile-surface
description: Reference mobile stack (React Native + Expo) — invariants, offline-first, push, deep links, OTA-vs-native, cert pinning, MASVS. Product-specific screen UX lives in the Canon.
---

# Mobile Surface — Reference Implementation (React Native + Expo, managed)

> **Reference implementation.** This skill documents one concrete binding of the mobile client seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to a different framework (native, Flutter, etc.). The *patterns* here
> (offline-first, idempotent queued mutations, OTA-vs-native discipline, cert pinning, MASVS) are what
> transfer, not the specific framework.

This skill is the **stack + plumbing** (state, offline, push, OTA, security). The product's screen-level UX/contracts live in the Product Canon — reference them, don't restate them.

## Stack invariants (example binding)

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
| Auth | the product's auth provider RN client + `expo-auth-session`; biometric `expo-local-authentication` |
| Builds / OTA | **EAS Build** + **EAS Update**; E2E (Detox/Maestro), unit Vitest + RNTL |
| Crash/analytics | an error tracker RN SDK + a product-analytics RN SDK |

Release pipeline + EAS profiles + store hazards live in [`app-store-deployment`]. Locale-aware number/currency formatting goes through a shared formatter from a `lib-formatters` package, honoring the active locale (see `region-and-locale`) — never hand-format.

## Auth token storage

```typescript
await SecureStore.setItemAsync('app.refresh_token', token, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
```
Refresh token → secure-store; access token → in-memory only (lost on kill → forces refresh); refresh on foreground + 5-min idle; biometric re-prompt before sensitive views.

## Offline-first (degraded-network reality)

Cellular drops to slow/no signal in elevators/tunnels/transit; the app MUST render last-known state, never a bare spinner. Storage routing: tokens→secure-store, UI state→redux-persist, API cache→AsyncStorage persistor, sync queue→AsyncStorage (capped), large assets→`expo-file-system`.

**Queued mutations** — ULID-keyed for idempotency, persisted immediately, flushed on reconnect:

```typescript
const SYNC_QUEUE_KEY = 'app:sync-queue:v1'; const MAX_QUEUE = 1000;
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

**Conflict resolution:** mutations are server-authoritative. On 409, **never client-resolve** audit-log / consent / money-moving writes — surface "this changed, reload?" and keep the user's pending intent retryable. Last-write-wins only for non-critical UI state (last filter, draft notes). The offline-first cached-render pattern for a specific screen belongs in the Product Canon.

**Offline UI:** show a `NetInfo`-driven banner ("You're offline — changes will sync"); disclose staleness honestly ("Stale since 06:55"), never an unmarked spinner-into-old-data.

## Push notifications (Expo Push)

`notifications-service` → Expo Push Service → APNS/FCM. Prefer the managed push service over raw Firebase/APNS.

**Client:** request permission **after first value, never at launch** (iOS lets you ask once; a `push_permission_denied` rate >60% = asked too early). Android channels must exist before `getExpoPushTokenAsync`. Re-register token on every launch (idempotent server-side). Simulator can't receive APNS — test on a real device.

```typescript
Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldShowBanner: true, shouldPlaySound: true, shouldSetBadge: true }) });

const PayloadSchema = z.object({ kind: z.enum(['digest','alert','lifecycle','system']), tenant_id: z.string().uuid(), deep_link: z.string().optional() });
Notifications.addNotificationResponseReceivedListener(({ notification }) => {
  const parsed = PayloadSchema.safeParse(notification.request.content.data);   // NEVER trust the payload — validate first
  if (!parsed.success) return errorTracker.captureMessage('push.payload.invalid');
  switch (parsed.data.kind) { case 'digest': router.push(`/(digest)/${parsed.data.tenant_id}`); break; /* ... */ }
});
```

**Android channels:** define one per notification category (e.g. `digest` HIGH, `alerts` MAX, `lifecycle` DEFAULT, `system` LOW) so users mute categories independently.

**Producer:** `expo-server-sdk`, batches ≤100 (`chunkPushNotifications`). Tickets are synchronous, **receipts ~15min async** — schedule a receipt check; on `DeviceNotRegistered` purge the token, on `MessageTooBig`/`MessageRateExceeded` log/alert. Dedup each dispatch by a stable `(tenant_id, item_id, date)` key. **Never put PII/secrets in a payload** (visible in the OS notification log). A specific notification's delivery chain + SLO belongs in the Canon.

## Deep links + simulator inner loop

Deep links use the product's scheme, e.g. `app://<route>/{id}`, `app://auth/callback`. Test without a real push:
```bash
xcrun simctl openurl booted "app://<route>"                 # deep link
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

## Cert pinning rotation (CRITICAL — Product Canon `STACK.md`)

Pin **both** current + rotation cert. Sequence: (1) add new pin to `PINS`; (2) OTA the new pin set **one week before** server rotation; (3) rotate server cert; (4) remove old pin in next OTA. Keep an unpinned HTTP kill-switch endpoint as the recovery path.

```typescript
const PINS = ['sha256/AAAA...current', 'sha256/BBBB...rotation'];
```

## Desktop-only views (mobile fallback)

Dense data-grid / bulk-editor / large-chart / export views → link out, don't cram:
```tsx
<EmptyState title="This view works best on desktop" cta={<Link href={`${WEB_URL}/...`}>Open in browser →</Link>} />
```

## MASVS security

MASVS L1 + key L2: refresh token in secure-store / access token in memory; magic-link via universal/app links; cert pinning (above); no PII in logs (error-tracker breadcrumbs rate-limited); biometric before sensitive/financial views. See [`security-baseline`] §MASVS.

## Anti-patterns

- OTA on a native change (silent break); cert-pin rotation without the OTA-before-rotate sequence (bricks app); push permission at launch; token in DOM during magic-link callback (XSS); a web-only chart lib on RN (use a native chart lib like `victory-native`); hand-formatted numbers/currency (use the locale-aware shared formatter).
- Tokens/PII in AsyncStorage (use secure-store); last-write-wins on audit-log/consent/money writes; unbounded sync queue (AsyncStorage throws ~5MB on Android); trusting `NetInfo.isConnected===true` as working network; queueing auth-mutating actions (run synchronously).
- Trusting a push payload for navigation without schema validation; skipping receipt checking (dead tokens accumulate); PII/secrets in a payload; `sound: 'custom.wav'` (managed-workflow — use `'default'`).

## Verify

- Real device, airplane mode: the primary screen renders from cache with a staleness banner; a queued mutation survives an app kill and flushes on reconnect with its idempotency key.
- `xcrun simctl openurl booted "app://<route>"` opens the right screen; a `simctl push` routes by validated `kind`.
- OTA-channel test build pulls a preview update; a native-touching dep change triggers a native bump in CI.

## References

- Product Canon (`STACK.md`) — the bound mobile stack, push, secure-store, cert pinning, MASVS
- the Canon's screen specs — screen UX, contracts, delivery SLO, offline-render pattern
- [`app-store-deployment`] — EAS Build/Update, profiles, OTA-vs-store, store hazards
- [`idempotency-handling`] — server dedup for queued mutations · [`security-baseline`] §MASVS · [`region-and-locale`] — RN RTL + locale formatting

## 2026 market update

- **Styling:** **NativeWind** (Tailwind-for-RN) and **Unistyles** are now mainstream picks alongside Tamagui — match `STACK.md`.
- **KMP / Compose Multiplatform** (stable May 2025) is the rising "share logic, optionally share UI, native rendering" alternative for regulated/native-heavy products (mirrors the existing Flutter mention). New Architecture (Fabric/TurboModules, Hermes) + Expo Router are already the assumed defaults here.
