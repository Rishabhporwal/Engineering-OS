# TECH/10 — Mobile Architecture (Android + iOS)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E5 (Mobile Engineer) | **Reviewers:** E1, E2
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/06_api_contracts.md](06_api_contracts.md), [TECH/07_frontend_architecture.md](07_frontend_architecture.md), [TECH/08_alerts_reporting.md](08_alerts_reporting.md)

This document specifies:
- React Native + Expo architecture for both Android and iOS
- The **Morning Brief** as the product's defining surface
- Code / logic reuse with the web frontend
- Authentication, secure token storage, certificate pinning
- Push notifications (APNS + FCM via Expo)
- App Store / Play Store submission and CI/CD via EAS
- Feature scope per phase

**Mandate revision (per AI-native commerce OS brief):**

Mobile is **THE primary surface for the product's defining workflow** — the Morning Brief. Three signals per morning, approve / reject / edit, three-minute commitment. Web is the workbench used for Monday review + on-demand depth. Phone is the daily heartbeat.

This is a meaningful re-prioritisation from the earlier "mobile is complementary" framing. The Morning Brief experience must be the **highest-quality piece of UI in all of Brain** — phone-first, thumb-first, designed for 06:55-09:00 IST coffee-in-hand workflow.

The rest of mobile (dashboards, alerts feed, AI Chat) remains complementary. But the Morning Brief is the product.

---

## 1. Tech Stack

| Concern | Choice | Why |
|---------|--------|-----|
| **Framework** | **React Native + Expo (managed workflow)** | Single TS codebase for iOS + Android; reuses tRPC + Redux + TypeScript from web; one engineer ships both platforms |
| **SDK version** | Expo SDK 51+ (or latest stable) | New Architecture (Fabric + TurboModules) enabled |
| **Workflow** | Managed → eject only if necessary | Avoid native code; Expo modules cover 95%+ of needs |
| **Language** | TypeScript (strict) | Parity with web codebase |
| **Navigation** | Expo Router (file-based) | Mirrors Next.js App Router mental model |
| **State** | Redux Toolkit + redux-persist | Shared store schema with web; persist UI prefs to AsyncStorage |
| **Server state** | TanStack Query + tRPC React Native client | Same hooks pattern as web; type-safe |
| **Forms** | React Hook Form + Zod | Same as web |
| **UI primitives** | `tamagui` or `@tamagui/core` (mobile-tuned) | Native-feel components; theme tokens parity with shadcn web tokens |
| **Charts** | `victory-native` (D3-based; works on RN's Skia renderer) | Recharts/Visx don't work on RN; Victory does |
| **Forms / inputs** | RN built-ins + Tamagui wrappers | |
| **Local storage** | `expo-secure-store` (sensitive) + AsyncStorage (everything else) | Keychain (iOS) / Keystore (Android) for tokens |
| **HTTP** | tRPC client over fetch | Same as web |
| **WebSocket / SSE** | tRPC subscription with `event-source-polyfill` | For AI Chat streaming and live dashboard refresh |
| **Push notifications** | `expo-notifications` + APNS + FCM | Tokens registered to notifications-service; channel `push` added |
| **Auth** | Supabase Auth React Native SDK + `expo-auth-session` | OAuth (Google) handled by `expo-auth-session`; magic link deep-link via `expo-linking` |
| **Biometric** | `expo-local-authentication` (Phase 2) | Face ID / fingerprint to re-open app after backgrounding |
| **Crash reporting** | Sentry React Native SDK | Same Sentry org as web + backend |
| **Analytics** | PostHog React Native SDK | Same project as web |
| **Builds + CI** | **EAS Build** (Expo's cloud build service) | Avoids maintaining Mac runners; OTA updates via EAS Update |
| **Distribution** | App Store (iOS) + Google Play (Android) + TestFlight (iOS beta) + Play Internal Track (Android beta) | Standard |
| **Versioning** | Semantic versioning; OTA-only for JS-only patches | Native version bump only when native modules change |
| **E2E testing** | Detox (iOS + Android) | Industry standard for RN |
| **Unit tests** | Vitest + React Native Testing Library | |

### Why React Native + Expo (Not Native, Not Flutter)

- **Native Swift + Kotlin:** doubles engineering effort. Two codebases, two skill sets, two release cycles. Out of scope for a 2-4 person engineering team.
- **Flutter:** strong technical choice, but adds a third language (Dart). Loses shared TS types with backend gRPC clients. The team's TypeScript investment doesn't carry.
- **PWA (Progressive Web App):** insufficient. No push notification reliability on iOS, no App Store presence, limited home-screen presence, no Face ID, no native widgets.
- **Capacitor / Ionic wrapper:** acceptable Phase 0 stopgap if mobile launch must beat React Native development time; rejected because UX quality matters for an analytics product operators check daily.

React Native + Expo gives us 80% of native quality at 30% of native effort, in the same TypeScript stack as web. Standard for fintech and analytics startups at our stage.

---

## 2. Monorepo Layout (Additive)

```
brain/
├── apps/
│   ├── frontend/                  # Next.js web (existing)
│   ├── mobile/                    # NEW: Expo app
│   │   ├── app/                   # Expo Router file-based routes
│   │   │   ├── (auth)/
│   │   │   │   ├── login.tsx
│   │   │   │   └── magic-link.tsx
│   │   │   ├── (workspace)/       # Auth-required group
│   │   │   │   ├── _layout.tsx    # Tab navigator
│   │   │   │   ├── index.tsx      # Home dashboard
│   │   │   │   ├── insights.tsx
│   │   │   │   ├── alerts.tsx
│   │   │   │   ├── chat.tsx
│   │   │   │   └── settings.tsx
│   │   │   └── _layout.tsx        # Root: providers
│   │   ├── components/
│   │   ├── lib/
│   │   ├── assets/
│   │   ├── app.json               # Expo config
│   │   ├── eas.json               # EAS Build profiles
│   │   └── package.json
│   └── ...
│
├── packages/
│   ├── ui/                        # Web shadcn — desktop-only
│   ├── ui-mobile/                 # NEW: Tamagui-based mobile primitives
│   ├── lib-metrics/               # Shared (used by web + mobile)
│   ├── lib-grpc-clients/          # Shared (web uses; mobile uses too via tRPC)
│   ├── lib-formatters/            # NEW: extracted currency / date formatters from packages/ui (web + mobile share)
│   ├── trpc-client/               # NEW: shared tRPC client + types (web + mobile)
│   └── ...
```

### Code Reuse Across Web + Mobile

- **Shared:** types (`packages/lib-metrics`, gRPC client types), formatters (`packages/lib-formatters`), tRPC client setup, Redux slices (`apps/web/lib/store/slices/*` → moved to `packages/state` and imported by both)
- **Platform-specific:** UI components (web uses shadcn, mobile uses Tamagui — same design tokens), routing, navigation, native modules

Target: ~40% code share across web + mobile (mostly business logic, types, formatters, validation schemas).

---

## 3. Feature Scope by Phase

The mobile app does not aim for feature parity day-1. Each phase progressively expands.

### Phase 1 — Mobile MVP (Read-Only, ships W12–14)

| Screen | Functionality |
|--------|---------------|
| Login | Email/password + magic link + Google OAuth |
| Workspace switcher | If user belongs to multiple workspaces |
| Home / Dashboard | KPI cards: Revenue, MER, aMER, CAC, New Customers (today + WoW change) + RAG status |
| Acquisition | MER/aMER + per-platform spend; goal vs actual; weekly trend |
| Calendar Summary | Last 14 days; single metric per screen with swipe between metrics |
| AI Insights | Inbox of unacked insights; tap to read full body; acknowledge |
| Alerts | Feed of fired alerts; acknowledge / snooze |
| Settings | Profile, notifications preferences, sign out |
| Push notifications | Critical alerts + new daily digest summary |

### Phase 2 — Interaction Layer (W14–22)

| Addition | |
|----------|-|
| AI Chat | Full streaming chat experience; tool indicators; action links open relevant deep screens |
| Goal editing | Inline goal updates per metric |
| Marketing action quick-add | "Email sent today" — one-tap log |
| Drill-downs | Tap a KPI → see contributing orders / campaigns |
| Biometric unlock | Face ID / fingerprint for app re-open |

### Phase 3 — Intelligence + Power Features (W23–36)

| Addition | |
|----------|-|
| Plan Module overview | Forecast charts (read-only); spend plan view (not edit) |
| Pincode/RTO summary | India workspaces: top problem pincodes; quick block recommendations |
| Notification rich actions | Acknowledge alert from notification without opening app |
| App badges | Unread insight count |
| Tablet layout | iPad/Android tablet 2-column layout |

### Phase 4 — Parity + Native Affordances

| Addition | |
|----------|-|
| Home screen widget | iOS WidgetKit + Android App Widgets — show today's revenue/MER glance |
| Apple Watch companion | Daily KPI glance complication |
| Voice queries via Siri Shortcuts / Google Assistant | "Hey Siri, ask Brain what's my MER today" |
| Multi-workspace at-a-glance | For agency users |

### Never on Mobile

These features stay desktop-only because the UX doesn't translate:

- Cohort heatmap (24×36 matrix; unreadable on phone)
- CM Waterfall (filter dimensions, drill cells)
- First Product Cascade table (column-heavy)
- Settings → Costs / Product COGS bulk editor
- Settings → Campaign Classifications bulk view
- Plan Module spend plan editor
- CSV / XLSX export downloads (linkable from app, but downloaded on desktop)

If an operator opens these on mobile, we show: *"This view works best on desktop — [Open in browser →](https://{BRAIN_DOMAIN}/...)"*

---

## 4. Authentication

### Flow

```
1. User opens app → Login screen
2. Email magic link OR Google OAuth via expo-auth-session
3. Supabase JWT received
4. Refresh token stored in expo-secure-store (Keychain / Keystore)
5. Access token kept in memory (never persisted)
6. Background: refresh-token-rotation on app foreground or 5-min idle
7. Biometric unlock (Phase 2): re-prompt before sensitive actions
```

### Token Storage

```typescript
// apps/mobile/lib/auth/storage.ts
import * as SecureStore from 'expo-secure-store';

const REFRESH_TOKEN_KEY = 'brain.refresh_token';

export async function storeRefreshToken(token: string) {
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function clearRefreshToken() {
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}
```

- **iOS:** Keychain with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`
- **Android:** Keystore-backed encrypted shared preferences
- **Access token:** in-memory only; lost on app kill (forces re-auth via refresh token)

### Deep Linking (for Magic Link Auth + Notifications)

```json
// apps/mobile/app.json
{
  "expo": {
    "scheme": "brain",
    "ios": {
      "associatedDomains": ["applinks:{BRAIN_DOMAIN}"]
    },
    "android": {
      "intentFilters": [{
        "action": "VIEW",
        "autoVerify": true,
        "data": [{ "scheme": "https", "host": "{BRAIN_DOMAIN}" }],
        "category": ["BROWSABLE", "DEFAULT"]
      }]
    }
  }
}
```

Universal links via Apple App Site Association (AASA) and Android App Links (assetlinks.json). Required for magic link auth flow.

### Sign-Out

- Clear refresh token from secure store
- Clear in-memory access token
- Clear Redux store (call `persistor.purge()`)
- Unregister push token from notifications-service
- Navigate to login

---

## 5. API Communication

Mobile uses the **same api-gateway** as web. Same tRPC contracts. Same auth headers.

```typescript
// apps/mobile/lib/trpc.ts
import { createTRPCReact, httpBatchLink, splitLink, httpSubscriptionLink } from '@trpc/react-query';
import type { AppRouter } from 'brain-api-gateway';   // shared types

export const trpc = createTRPCReact<AppRouter>();

export const trpcClient = trpc.createClient({
  links: [
    splitLink({
      condition: (op) => op.type === 'subscription',
      true: httpSubscriptionLink({ url: 'https://api.{BRAIN_DOMAIN}/trpc' }),
      false: httpBatchLink({
        url: 'https://api.{BRAIN_DOMAIN}/trpc',
        headers: async () => {
          const token = await getAccessToken();
          return token ? { Authorization: `Bearer ${token}` } : {};
        },
      }),
    }),
  ],
});
```

### Certificate Pinning

For production builds, pin the api-gateway TLS certificate to prevent MITM attacks on hostile networks (operator on café WiFi):

```typescript
// apps/mobile/lib/network/pinning.ts
import { Platform } from 'react-native';

// Public key SHA-256 pinning via expo-ssl-pinning (or react-native-cert-pinner)
// Configured at app.json level for managed Expo workflow
```

Pin both current cert and rotation cert (avoid bricking app on cert renewal). Rotate pins via OTA update before cert expires.

### Token Refresh

Token refresh interceptor:

```typescript
async function refreshAccessTokenIfNeeded() {
  const accessToken = getAccessTokenInMemory();
  if (accessToken && !isExpired(accessToken)) return accessToken;

  const refreshToken = await getRefreshToken();
  if (!refreshToken) {
    redirectToLogin();
    throw new Error('No refresh token');
  }

  try {
    const { access_token, refresh_token } = await supabase.auth.refreshSession(refreshToken);
    setAccessTokenInMemory(access_token);
    await storeRefreshToken(refresh_token);
    return access_token;
  } catch (err) {
    await clearRefreshToken();
    redirectToLogin();
    throw err;
  }
}
```

---

## 6. State Management

Same Redux Toolkit setup as web (TECH/07 §4). Shared slices via `packages/state`.

### Mobile-Specific Slices

```typescript
// packages/state/slices/mobileSlice.ts
import { createSlice } from '@reduxjs/toolkit';

interface MobileState {
  pushToken: string | null;          // Expo push token
  pushPermissionStatus: 'granted' | 'denied' | 'undetermined';
  biometricEnabled: boolean;
  lastBackgroundedAt: number | null;
  appStateForeground: boolean;
}

const mobileSlice = createSlice({
  name: 'mobile',
  initialState: {
    pushToken: null,
    pushPermissionStatus: 'undetermined' as const,
    biometricEnabled: false,
    lastBackgroundedAt: null,
    appStateForeground: true,
  },
  reducers: {
    setPushToken: (state, action) => { state.pushToken = action.payload; },
    setPushPermission: (state, action) => { state.pushPermissionStatus = action.payload; },
    setBiometric: (state, action) => { state.biometricEnabled = action.payload; },
    appBackgrounded: (state) => {
      state.appStateForeground = false;
      state.lastBackgroundedAt = Date.now();
    },
    appForegrounded: (state) => { state.appStateForeground = true; },
  },
});
```

### redux-persist on Mobile

Same pattern as web, but using AsyncStorage:

```typescript
// apps/mobile/lib/store/index.ts
import AsyncStorage from '@react-native-async-storage/async-storage';
import { persistReducer, persistStore } from 'redux-persist';

const persistedReducer = persistReducer(
  { key: 'brain-mobile', storage: AsyncStorage, whitelist: ['ui', 'mobile'] },
  rootReducer
);
```

---

## 7. Push Notifications

### Architecture

```
notifications-service
    │
    │ (1) When firing critical alert
    │      OR generating daily digest summary
    ▼
Expo Push API (https://exp.host/--/api/v2/push/send)
    │
    ├──► APNS (iOS device)
    └──► FCM (Android device)
         │
         ▼
   Device receives notification
         │
         ▼
   User taps → deep link → app opens to specific screen
```

### Token Registration

On app first run (after login):

```typescript
// apps/mobile/lib/push/register.ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

export async function registerForPushNotifications() {
  if (!Device.isDevice) return null;

  const { status: existing } = await Notifications.getPermissionsAsync();
  let final = existing;
  if (existing !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    final = status;
  }
  if (final !== 'granted') return null;

  const { data: pushToken } = await Notifications.getExpoPushTokenAsync({
    projectId: EXPO_PROJECT_ID,
  });

  await trpcClient.notifications.registerPushToken.mutate({
    pushToken,
    platform: Platform.OS,
    deviceId: await getDeviceId(),
  });

  return pushToken;
}
```

The push token is sent to notifications-service, stored in `mobile_push_tokens` table:

```sql
CREATE TABLE mobile_push_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  push_token TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
  device_id TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, device_id)
);
```

### Push Delivery (notifications-service)

```typescript
// apps/notifications-service/src/delivery/push.ts
import { Expo } from 'expo-server-sdk';

const expo = new Expo({ accessToken: process.env.EXPO_ACCESS_TOKEN });

export async function sendPushAlert(event: AlertEvent, recipients: PushRecipient[]) {
  const messages = recipients
    .filter(r => Expo.isExpoPushToken(r.pushToken))
    .map(r => ({
      to: r.pushToken,
      sound: event.severity === 'critical' ? 'default' : null,
      title: `${event.severity.toUpperCase()}: ${event.title}`,
      body: event.message.slice(0, 200),
      data: {
        type: 'alert',
        alertId: event.id,
        deepLink: `brain://alerts/${event.id}`,
      },
      priority: event.severity === 'critical' ? 'high' : 'default',
      channelId: 'alerts',                 // Android notification channel
    }));

  const chunks = expo.chunkPushNotifications(messages);
  for (const chunk of chunks) {
    try {
      const tickets = await expo.sendPushNotificationsAsync(chunk);
      await persistDeliveryTickets(event.id, tickets);
    } catch (err) {
      Sentry.captureException(err);
    }
  }
}
```

### Token Hygiene

- Push tickets are checked 30 min later for delivery receipts
- `DeviceNotRegistered` errors → mark `active = false` in `mobile_push_tokens`
- Tokens not seen in 30 days → auto-deactivate

### Notification Channels (Android)

Channels let users granularly opt-out via system settings:

| Channel ID | Importance | Sound |
|-----------|-----------|-------|
| `alerts.critical` | High | Default |
| `alerts.warning` | Default | Default |
| `digests` | Low | None |
| `insights` | Default | None |

Created on first launch via `Notifications.setNotificationChannelAsync()`.

### Quiet Hours Integration

notifications-service already respects workspace quiet hours (TECH/08 §10). Push delivery follows the same gate: non-critical events queued for end-of-quiet-hours.

---

## 8. Offline Behavior

Phase 1 MVP: **online-only**. App requires connectivity. Show "Offline — last updated 5 min ago" banner if NetInfo reports disconnected.

Phase 2: cached read view. TanStack Query's `persistQueryClient` plugin serializes cache to AsyncStorage; on cold start, hydrate from cache before network fetch.

Phase 3: optimistic mutation queue. Goal edits, marketing action quick-adds queue while offline; flush on reconnect.

Phase 4 (if demand): full offline mode with ClickHouse delta sync. **Probably never needed** — operators need fresh metrics; stale offline data is misleading.

---

## 9. Build & Release Pipeline

### EAS (Expo Application Services)

```json
// apps/mobile/eas.json
{
  "cli": { "version": ">= 11.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "channel": "development"
    },
    "preview": {
      "distribution": "internal",
      "channel": "preview",
      "ios": { "simulator": false },
      "android": { "buildType": "apk" }
    },
    "production": {
      "channel": "production",
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "team@{BRAIN_DOMAIN}",
        "ascAppId": "...",
        "appleTeamId": "..."
      },
      "android": {
        "serviceAccountKeyPath": "./play-store-service-account.json",
        "track": "production"
      }
    }
  }
}
```

### CI/CD Flow

```
PR merged to main
    │
    ▼
GitHub Actions:
  - lint, typecheck, unit tests (Vitest)
  - E2E tests (Detox on macOS runner)
  - If passing → EAS build (production channel)
    │
    ├──► Build iOS .ipa
    ├──► Build Android .aab
    │
    ▼
Manual approval → EAS submit
    │
    ├──► Apple App Store Connect → TestFlight (7-day soak) → App Store review (1-3 days) → Production
    └──► Google Play Console → Internal Track → Closed Beta → Production (rolling 24h release)
```

### OTA Updates (EAS Update)

For JS-only changes (no native module updates), push updates without App Store / Play Store re-review:

```bash
eas update --channel production --message "Fix calendar report rendering"
```

OTA updates roll out within minutes. Users get update on next app open.

### When OTA is NOT Possible (Native Bump Required)

- Adding native modules (e.g., new RN library with iOS/Android native code)
- Bumping Expo SDK version
- Permission changes (e.g., adding camera access)
- Bundle identifier / app icon changes

Native bumps go through full App Store review.

---

## 10. App Store / Play Store Submission

### Initial Submission Timeline (Plan Carefully)

| Step | Duration |
|------|----------|
| Apple Developer Program enrollment | 1–2 days (if D-U-N-S verification needed: +5 days) |
| Google Play Developer enrollment | 1 day + identity verification (5–7 days) |
| App Store Connect setup | 1 day |
| App icon, screenshots, descriptions, privacy policy | 3–5 days work |
| TestFlight first build approval | 1 day |
| App Store review (first submission) | **2–7 days** — slowest for new apps |
| Play Store internal testing → production | Same day rollout once approved |

**Critical-path implication:** **start App Store registration in Week 0**, not Week 12. Identity verification can take 1-2 weeks.

### Required Assets

- App icon: 1024×1024 + adaptive icon for Android
- iPhone screenshots: 6.7" (1290×2796) + 6.5" + 5.5"
- iPad screenshots (Phase 3+)
- Android screenshots: phone + 7" tablet + 10" tablet
- Feature graphic (Play Store)
- App preview videos (optional but helpful)
- Privacy policy URL (Brain has one — link from app)
- Marketing URL
- Support URL + email

### Privacy Disclosures

#### iOS App Privacy "Nutrition Label"

Mandatory disclosure on data collection. Brain's:

| Data Type | Collected | Linked to User | Used for Tracking |
|-----------|-----------|----------------|-------------------|
| Contact info (email) | Yes | Yes | No |
| User content (chat messages) | Yes | Yes | No |
| Identifiers (user ID) | Yes | Yes | No |
| Usage data (app activity) | Yes | Yes | No |
| Diagnostics (crashes, performance) | Yes | Yes | No |

#### Android Data Safety Section (Play Console)

Equivalent disclosure. Same answers.

#### App Tracking Transparency (iOS 14.5+)

Brain doesn't track users across apps. ATT prompt **not required**. We show no ad SDKs; PostHog runs in product-analytics-only mode.

---

## 11. Security

### OWASP MASVS (Mobile Application Security Verification Standard)

Brain targets MASVS Level 1 + key Level 2 controls.

| Control | Implementation |
|---------|----------------|
| Sensitive data in secure storage | Refresh tokens in Keychain/Keystore via `expo-secure-store` |
| No sensitive data in logs | Same redaction rules as backend (TECH/09 §10.12) |
| TLS certificate pinning | Production builds only; pin api-gateway + Supabase |
| Anti-tampering (jailbreak/root detection) | `expo-device.isRootedExperimentalAsync()` + warning banner (don't block — too aggressive) |
| Code obfuscation | Hermes engine + Metro minification (default) |
| Biometric auth for sensitive actions | Phase 2 — Face ID / fingerprint before viewing financial data after backgrounding |
| App attestation | Apple DeviceCheck / Google Play Integrity API (Phase 3) — api-gateway validates attestation token on critical endpoints |
| Screen recording / screenshot prevention | iOS: `FLAG_SECURE` equivalent on sensitive screens (financial summary). Android: same. Phase 2. |
| Deep link validation | Validate `scheme://` URLs before navigation; reject unknown hosts |

### App Attestation (Phase 3)

Verify requests come from the legitimate Brain app, not a tampered build or script:

```typescript
// On app launch
const attestationToken = await DeviceCheck.generateAttestationToken();    // iOS
// or Play Integrity equivalent for Android

// Include in every API request
headers['X-App-Attestation'] = attestationToken;
```

api-gateway validates the attestation token against Apple/Google APIs. Critical-rate-limited endpoints (auth, mutations) gate on attestation.

### Certificate Pinning Specifics

Pin SHA-256 hashes of api-gateway's TLS certificate **and** the rotation certificate (avoid bricking the app when cert rotates):

```typescript
// apps/mobile/lib/network/pinning.ts
const PINS = [
  'sha256/AAAA...current-cert-pin',
  'sha256/BBBB...rotation-cert-pin',
];
```

When rotating certs:
1. Add new cert pin to the array
2. OTA update with new pin (one week before rotation)
3. Rotate cert on server
4. Remove old pin in next OTA

If we forget: app loses connectivity until users update. There's a "kill switch" endpoint (HTTP, no pinning) the app calls on cert errors to fetch updated pin set.

---

## 12. Observability

### Crash Reporting

Sentry React Native SDK in every app launch:

```typescript
import * as Sentry from '@sentry/react-native';

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
  release: `brain-mobile@${Application.nativeApplicationVersion}+${Application.nativeBuildVersion}`,
  tracesSampleRate: 0.05,
  enableNative: true,
  enableNativeCrashHandling: true,
});
```

Native crashes (iOS + Android) reported to same Sentry project as backend services.

### Performance

Sentry React Native Performance tracks:
- App cold start time
- Screen render times
- Network call latency (linked to backend trace_id via request_id header)

### Logging

Same centralized logging spine as backend (TECH/09 §10). Mobile logs flow to Sentry breadcrumbs (not OpenSearch directly — too chatty). Critical events explicitly logged to a `mobile_events` endpoint that proxies into OpenSearch with proper enrichment:

```typescript
import { log } from './lib/logger';

log.info('order_drilldown.opened', { orderId });           // breadcrumb only
log.warn('push_token_refresh_failed', { error });          // breadcrumb + Sentry message
log.error('biometric_unlock_failed', { error });           // breadcrumb + Sentry + remote event
```

The remote event path is rate-limited (max 10 events/minute per device) to prevent log floods.

### Product Analytics

PostHog React Native SDK:

```typescript
import PostHog from 'posthog-react-native';

const posthog = await PostHog.init(process.env.EXPO_PUBLIC_POSTHOG_KEY, {
  host: 'https://app.posthog.com',
  captureNativeAppLifecycleEvents: true,
});

posthog.capture('insight.acknowledged', { insight_id, severity });
```

Same project as web — funnel analysis works across surfaces.

---

## 13. Testing

### Unit / Component

Vitest + React Native Testing Library:

```typescript
// __tests__/components/KpiCard.test.tsx
import { render, screen } from '@testing-library/react-native';
import { KpiCard } from '../components/KpiCard';

test('renders revenue with INR formatting', () => {
  render(<KpiCard label="Revenue" valueMinor={48200000n} currency="INR" />);
  expect(screen.getByText('₹4,82,000')).toBeOnTheScreen();
});
```

### E2E (Detox)

```javascript
// e2e/login.test.js
describe('Login flow', () => {
  beforeAll(async () => { await device.launchApp(); });

  it('logs in with magic link and shows dashboard', async () => {
    await element(by.id('email-input')).typeText('test@brand.com');
    await element(by.id('send-link-button')).tap();
    await expect(element(by.text('Check your email'))).toBeVisible();
    // Simulate deep link
    await device.openURL({ url: 'brain://auth/callback?token=...' });
    await expect(element(by.id('dashboard-title'))).toBeVisible();
  });
});
```

Detox runs on:
- macOS runner with iOS simulator (App Store target)
- Linux runner with Android emulator

Both in GitHub Actions, blocking merge on E2E fail (critical flows only — login, view dashboard, acknowledge insight).

### Device Testing

- Internal team: TestFlight + Play Internal Track from W11 onward
- Beta brands: invited to TestFlight + Play Closed Testing in W12-13
- Production launch: W14-15 (the pilot brand migration window)

---

## 14. Versioning Strategy

```json
// apps/mobile/app.json
{
  "expo": {
    "version": "1.0.0",        // shown to users + App Store version
    "ios": { "buildNumber": "42" },
    "android": { "versionCode": 42 }
  }
}
```

- **Semantic version (`1.0.0`)** — user-visible; bumped on feature release
- **Build number / versionCode (`42`)** — internal; auto-incremented per EAS build
- **Native version bump (e.g., `1.1.0`)** — only when native modules change

### Release Cadence

- **Bug fixes via OTA:** any time; rolling release in minutes
- **Feature releases via App Store / Play Store:** every 2–3 weeks (aligned with sprint cadence)
- **Major versions (1.x → 2.x):** roughly per phase boundary

### Force-Update Policy

```typescript
// On app launch
const minSupportedVersion = await trpcClient.app.minVersion.query();
if (currentVersion < minSupportedVersion) {
  // Block app; show "Please update Brain to continue"
}
```

`min_supported_version` lives in a config table (`app_versions`); operators can force-update when security-sensitive bugs are fixed. Rare — try to keep N-3 versions supported.

---

## 15. Cost

| Item | Cost | When |
|------|------|------|
| Apple Developer Program | $99/year | Week 0 |
| Google Play Developer | $25 one-time | Week 0 |
| EAS (Production tier) | $99/month | From W7 (first build) |
| Sentry React Native (already on Sentry team plan) | $0 incremental | Existing |
| PostHog mobile events | scales with volume | Phase 2+ |
| App Store + Play Store fees on revenue | 15-30% commission **only if selling in-app** | Brain charges B2B SaaS — billed via Stripe outside app; no commission |

Total monthly: **~$110/month** for mobile-specific infra. Negligible at our scale.

---

## 16. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Tablet layout — when? | E5 | Phase 3 — once we know enough operators use tablets (likely 5-10%) |
| Apple Watch / Wear OS apps? | E5 | Phase 4 if demand. Niche but high-delight. |
| iPad Pencil support? | E5 | Not relevant for analytics app. Skip. |
| Custom domain / branded build for enterprise (white-label app)? | E1 | Phase 5+. Multi-tenant single app is fine until there's a $50K+ ARR customer asking. |
| Submit to other stores (Amazon App Store, Huawei AppGallery)? | E1 | Skip Amazon. Huawei evaluation Phase 4 if Indian Android users heavily on Huawei. |
| Notification rich actions (acknowledge from notification)? | E5 | Phase 3 via Notification Service Extension (iOS) + custom notification (Android). |
| App distribution via MDM (for enterprise IT)? | E1 | Phase 5+. Apple Business Manager + Google Workspace. |
| Hot reload for OTA on production? | E5 | Yes — Expo Update silent download + apply on next open. Saves manual update friction. |
| Should there be an "office desktop only" gate for new users? | Founder | Yes — onboarding flow requires desktop to connect Shopify. Mobile post-onboarding. |
