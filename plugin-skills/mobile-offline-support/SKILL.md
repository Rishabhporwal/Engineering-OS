---
name: mobile-offline-support
description: Offline-first patterns for the Brain mobile app (RN + Expo) — AsyncStorage cache, queued mutations, NetInfo transitions, conflict resolution. Use for the Morning Brief surface (must render last-known state when offline), audience-builder edits made on the metro, push-notification handlers fired while disconnected, or encountering sync conflicts, stale caches, queue growth, secure-storage misuse.
---

# Mobile Offline Support

Build the Brain mobile app to work on **Indian metro network reality**: 4G that drops to Edge inside elevators and trains, sub-second blackouts in tunnels, NDR pulses during festival traffic. The Morning Brief MUST render even when offline — last-known state with a clear "stale since 06:55 IST" stamp is infinitely better than a spinner.

## Why this matters for Brain

| Surface | Requirement |
|---|---|
| Morning Brief (Karan, TECH/10) | The push lands at 07:00 IST. The user opens it at 07:12 in a moving Ola. App MUST render the synthesized brief from cache while the freshness check happens in background. |
| Audience builder edits | Founder tweaks a segment in transit. The save MUST queue locally, sync when connectivity returns, and the queued state MUST survive an app kill. |
| Approve / reject / edit signals | These are Decision Log writes — server-authoritative. Conflict resolution is "server wins on conflict, but the user's intent survives as a pending action they can retry." |

## Storage layers (per Brain mobile architecture, TECH/10)

| What | Where | Why |
|---|---|---|
| Tokens, refresh tokens, brand API keys | **expo-secure-store** | Encrypted at OS level (Keychain / Keystore). NEVER AsyncStorage. |
| UI state (Redux) | **redux-persist on AsyncStorage** | Restored on app launch; survives kills. |
| Cached API responses (TanStack Query / SWR cache) | **AsyncStorage (via persistor)** | Cheap reads, eventual consistency. |
| Sync queue (pending mutations) | **AsyncStorage** with size cap | See queue patterns below. |
| Large binary assets (cached chart data) | **expo-file-system** | AsyncStorage row-limit is ~6MB on Android. |

## React Native Implementation

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';

const SYNC_QUEUE_KEY = 'brain:sync-queue:v1';
const MAX_QUEUE = 1000;

interface QueuedMutation {
  id: string;                    // ULID for idempotency
  endpoint: string;              // tRPC route name
  payload: unknown;
  timestamp: number;             // ms, for ordering and TTL
}

export class OfflineManager {
  private queue: QueuedMutation[] = [];
  private isOnline = true;

  async init() {
    const persisted = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
    if (persisted) this.queue = JSON.parse(persisted);

    const state = await NetInfo.fetch();
    this.isOnline = !!state.isConnected;

    NetInfo.addEventListener((s) => {
      const wasOnline = this.isOnline;
      this.isOnline = !!s.isConnected;
      if (!wasOnline && this.isOnline) this.flush();
    });
  }

  async enqueue(m: Omit<QueuedMutation, 'id' | 'timestamp'>) {
    const item: QueuedMutation = { ...m, id: ulid(), timestamp: Date.now() };
    this.queue.push(item);
    if (this.queue.length > MAX_QUEUE) this.queue.shift(); // drop oldest
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(this.queue));
    if (this.isOnline) this.flush();
  }

  async flush() {
    const remaining: QueuedMutation[] = [];
    for (const item of this.queue) {
      try {
        await trpcClient.request({
          ...item,
          headers: { 'Idempotency-Key': item.id }, // server-side dedup
        });
      } catch (err) {
        if (isRetriableError(err)) remaining.push(item);
        // non-retriable (4xx other than 409/429): drop and log to Sentry
      }
    }
    this.queue = remaining;
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(this.queue));
  }
}
```

## Morning Brief — offline-first render

The Morning Brief is the most-loaded screen. It MUST render in <100ms from cache; the network refresh is decoration.

```tsx
import { useQuery } from '@tanstack/react-query';

function MorningBriefScreen() {
  const { data, isStale, dataUpdatedAt } = useQuery({
    queryKey: ['morning-brief', workspaceId, today],
    queryFn: () => trpc.morningBrief.get.query({ workspaceId, date: today }),
    staleTime: 1000 * 60 * 60 * 4, // 4 hours — synthesis runs once at 06:55 IST
    gcTime: 1000 * 60 * 60 * 24,   // keep in memory all day
    placeholderData: () => getPersistedBrief(workspaceId, today), // last-known
  });

  if (!data) return <BriefSkeleton />; // ONLY if no cached version at all
  return (
    <View>
      {isStale && <StaleBanner since={dataUpdatedAt} />}
      <BriefBody data={data} />
    </View>
  );
}
```

## Conflict resolution

Brain mutations are server-authoritative. **Never client-resolve a conflict** on user-facing state (Decision Log, ad-spend adjustments, customer consent). When the server returns 409 conflict:

```typescript
// In trpc client onError
if (err.data?.httpStatus === 409) {
  // Server says the resource changed underneath. Don't blindly retry.
  // Surface to the user: "This audience changed. Reload?"
  ui.showConflictDialog({
    serverState: err.data.serverState,
    yourPendingChange: payload,
  });
}
```

Last-write-wins is acceptable ONLY for non-critical UI state (last-selected filter, last-viewed brand for an agency user, draft notes). Decision Log entries, consent transitions, and ad-spend writebacks always reject the client copy.

## UI offline indicator (Tamagui)

```tsx
import { useNetInfo } from '@react-native-community/netinfo';
import { Stack, Text } from 'tamagui';

export function OfflineBanner() {
  const net = useNetInfo();
  if (net.isConnected) return null;
  return (
    <Stack bg="$yellow3" px="$3" py="$2">
      <Text size="$2" color="$yellow11">
        You're offline. Changes will sync when connected.
      </Text>
    </Stack>
  );
}
```

## Best Practices

- **Cache reads aggressively, queue writes carefully.** Reads can be hours stale (with a banner); writes must be idempotent + retried.
- **Cap queue length** to avoid runaway memory + AsyncStorage row size limits. 1000 items is a safe default.
- **Persist queue immediately** on enqueue. App can be killed at any moment in iOS background mode.
- **ULID-keyed idempotency** on every queued mutation. The server (Vikram + `idempotency-handling`) deduplicates.
- **Sentry-log non-retriable failures** — silent drops are how data quietly disappears.
- **Don't queue auth-mutating actions** (token refresh, logout). Run those synchronously and surface errors.
- **Test on real devices in airplane mode** — Detox's network throttling doesn't catch every iOS WKWebView quirk.
- **Disclose cached state.** "Stale since 06:55 IST" is honest UI; an unmarked spinner-into-old-data is lying to the user.

## Never Do

- Store tokens or PII in AsyncStorage. Always **expo-secure-store**.
- Last-write-wins on Decision Log / consent / ad-spend. Server is the source of truth.
- Sync sensitive customer data without re-encrypting at the device layer.
- Unbounded queue growth. The first time it crosses 5MB on Android, AsyncStorage throws and the queue is lost.
- Assume `NetInfo.isConnected === true` means working network. Add a heartbeat ping if you need certainty.

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Mobile app offline UX | **Karan** | TECH/10 §"Offline-first" |
| Server-side idempotency for queued mutations | **Vikram** | `idempotency-handling` |
| Decision Log conflict semantics | **Aryan** + **Vikram** | TECH/13 §"Decision Log discipline" |
| Detox tests for offline flows | **Tanvi** | |

Related Brain skills: `morning-brief-mobile`, `frontend-mobile`, `idempotency-handling`, `security-baseline` (token storage).
