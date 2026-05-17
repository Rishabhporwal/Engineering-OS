---
name: push-notification-setup
description: Push notification wiring for Brain's mobile app via Expo Push Service (APNS + FCM under the hood) + notifications-service producer. Morning Brief delivery (06:55–09:00 IST), permission request UX, token storage in core-service, receipt + error handling, deep linking, channels (Android). Use when wiring a new push category, when push delivery fails, when adding a deep link from a push, when permission UX needs review.
---

# Push Notification Setup

Brain's mobile app uses **Expo Push Service** — Expo signs/dispatches to APNS (iOS) + FCM (Android) on Brain's behalf. The producer side lives in `notifications-service` (Vikram). The Morning Brief is the most important push payload: delivered into the 07:00–09:00 IST coffee window, every single morning, every single workspace.

## Why this matters for Brain

| Surface | Push concern |
|---|---|
| **Morning Brief** | 06:55–07:15 IST synthesis window → push at 07:00; must arrive; deep link to today's brief |
| **Alert push** (anomaly, RTO spike) | Severity-aware; respect Do-Not-Disturb; rate-limit per workspace |
| **Lifecycle events** (Phase 3 — inbound inbox new message) | Per-user, real-time |
| **System** (auth changes, integration disconnect) | Critical; deep link to fix |

A Morning Brief that fails to arrive is **the** product failure: the Founder built the product around that 7:00 IST moment, and the daily heartbeat depends on it.

## The Brain stack (Expo + notifications-service)

```
   Brain notifications-service  →  Expo Push Service  →  APNS  →  iPhone
        (Vikram, Node)                                  →  FCM   →  Android
        Fastify + Kafka consumer                                     (Karan's app)
```

Brain does NOT use raw Firebase SDK or APNS APIs directly. Expo's managed workflow is the locked stack (TECH/10) — easier OTA updates, single dispatch API, free for Brain's volume.

## Client side (Karan — Expo)

### Permission + token registration

```typescript
// apps/mobile/src/notifications/register.ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { trpc } from '@/lib/trpc';

export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) return null;  // Simulator can't receive push

  const { status: existing } = await Notifications.getPermissionsAsync();
  let status = existing;
  if (existing !== 'granted') {
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
  }
  if (status !== 'granted') return null;

  // Android — channels must be set up before getting the token
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('morning-brief', {
      name: 'Morning Brief',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
      vibrationPattern: [0, 250, 250, 250],
    });
    await Notifications.setNotificationChannelAsync('alerts', {
      name: 'Alerts',
      importance: Notifications.AndroidImportance.MAX,
      sound: 'default',
    });
  }

  const token = (await Notifications.getExpoPushTokenAsync({
    projectId: Constants.expoConfig?.extra?.eas?.projectId,
  })).data;

  // Register token with Brain's core-service against workspace_id + user_id
  await trpc.notifications.registerToken.mutate({
    token,
    platform: Platform.OS,
    device_id: await Application.getAndroidId() ?? await Application.getIosIdForVendorAsync(),
  });
  return token;
}
```

**Permission UX rule** (Karan): never request push permission at app launch. Request it after the user has experienced the value (e.g., right after they see their first Morning Brief in the app, or right after they configure their workspace). The OS only lets you ask once on iOS — burn the request strategically.

### Foreground + background handlers

```typescript
// apps/mobile/src/notifications/handlers.ts
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { z } from 'zod';

// Foreground — show banner even when app is open
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

// Response handler — deep link routing
const PayloadSchema = z.object({
  kind:         z.enum(['morning_brief', 'alert', 'lifecycle', 'system']),
  workspace_id: z.string().uuid(),
  deep_link:    z.string().optional(),
});

Notifications.addNotificationResponseReceivedListener(({ notification }) => {
  // ALWAYS Zod-validate the payload before routing (defense-in-depth-validation)
  const parsed = PayloadSchema.safeParse(notification.request.content.data);
  if (!parsed.success) {
    Sentry.captureMessage('push.payload.invalid', { extra: { data: notification.request.content.data } });
    return;
  }

  // Route by kind
  switch (parsed.data.kind) {
    case 'morning_brief':
      router.push(`/(brief)/${parsed.data.workspace_id}`);
      break;
    case 'alert':
      router.push(parsed.data.deep_link ?? '/alerts');
      break;
    // ...
  }
});
```

**Brain rule:** **never trust the push payload.** Validate with Zod before using any field for navigation. A malicious push (or a misconfigured server-side template) can otherwise navigate the user into an unexpected screen.

## Producer side (Vikram — notifications-service)

```typescript
// services/notifications/src/expo-push.ts
import { Expo, ExpoPushMessage, ExpoPushTicket } from 'expo-server-sdk';

const expo = new Expo({ accessToken: process.env.EXPO_PUSH_TOKEN });

export async function sendBatch(messages: ExpoPushMessage[]) {
  // Expo accepts batches up to 100; split larger
  const chunks = expo.chunkPushNotifications(messages);
  const tickets: ExpoPushTicket[] = [];

  for (const chunk of chunks) {
    try {
      const chunkTickets = await expo.sendPushNotificationsAsync(chunk);
      tickets.push(...chunkTickets);
    } catch (err) {
      log().error({ err }, 'expo.send.failed');
      throw err;
    }
  }

  // Process receipts after a short delay — Expo provides them async
  const receiptIds = tickets
    .filter((t): t is { status: 'ok'; id: string } => t.status === 'ok')
    .map(t => t.id);

  // Defer to a BullMQ job to read receipts in 15 min
  await scheduleReceiptCheck(receiptIds);

  // Log + dead-letter any tickets that errored upfront
  for (const t of tickets) {
    if (t.status === 'error') {
      log().warn({ ticket: t }, 'expo.ticket.error');
      if (t.details?.error === 'DeviceNotRegistered') {
        // Token is dead — purge from core-service
        await trpc.notifications.purgeToken.mutate({ token: t.details.expoPushToken });
      }
    }
  }
}
```

### Morning Brief delivery — the canonical Brain push

```typescript
// services/notifications/src/morning-brief.ts
// Triggered by EventBridge at 07:00 IST after Maya's synthesis completes
export async function dispatchMorningBrief(workspaceId: string, briefId: string) {
  const tokens = await tokensRepo.listForWorkspace(workspaceId);
  if (tokens.length === 0) return;

  const message: ExpoPushMessage = {
    to: tokens.map(t => t.token),
    title: 'Brain · Morning Brief',
    body:  await briefSnippetForPush(briefId),                  // Haiku-generated 1-line snippet
    data:  { kind: 'morning_brief', workspace_id: workspaceId, brief_id: briefId },
    channelId: 'morning-brief',                                 // Android
    sound: 'default',
    priority: 'high',
    badge: 1,
    // Categorize for iOS rich notification (Phase 3 — quick actions)
    categoryIdentifier: 'morning_brief',
  };

  await sendBatch([message]);
}
```

## Receipts + error handling

Expo returns "tickets" synchronously and "receipts" asynchronously (~15 min later). The receipts are where you find out if APNS/FCM actually accepted the push.

```typescript
// services/notifications/src/receipts.ts
export async function checkReceipts(receiptIds: string[]) {
  const chunks = expo.chunkPushNotificationReceiptIds(receiptIds);
  for (const chunk of chunks) {
    const receipts = await expo.getPushNotificationReceiptsAsync(chunk);
    for (const [id, receipt] of Object.entries(receipts)) {
      if (receipt.status === 'error') {
        log().warn({ id, receipt }, 'expo.receipt.error');
        switch (receipt.details?.error) {
          case 'DeviceNotRegistered':
            await tokensRepo.purge(receipt.details.expoPushToken);
            break;
          case 'MessageTooBig':
            // app bug — log to Sentry
            Sentry.captureMessage('push.payload.too_big', { extra: { id } });
            break;
          case 'MessageRateExceeded':
            // Vendor (APNS/FCM) throttled us — alert Aarav
            break;
        }
      }
    }
  }
}
```

## Channels (Android only — but plan for them)

Brain defines channels per push category so users can mute "Alerts" without muting "Morning Brief":

| Channel ID | Name | Importance |
|---|---|---|
| `morning-brief` | Morning Brief | HIGH (sound, vibrate, banner) |
| `alerts` | Alerts | MAX (sound, vibrate, full-screen) |
| `lifecycle` | Inbox messages (Phase 3) | DEFAULT |
| `system` | Account & integrations | LOW |

## Best Practices

- **Use Expo Push Service** (locked stack); don't reach for raw Firebase / APNS
- **Request permission strategically** — after the user sees value, never at app launch
- **Validate every push payload with Zod** before routing — see `defense-in-depth-validation`
- **Use channels** on Android — let users mute categories independently
- **Implement deep linking** — every push should land somewhere meaningful, not just open the app
- **Never send PII or secrets** in the payload — push payloads are visible in the OS notification log
- **Token refresh handling** — `onTokenRefresh` analogue is built into Expo; re-register on every app launch (idempotent on the server)
- **Test on real devices** (simulator can't receive APNS)
- **Receipt checking is non-optional** — without it, dead tokens accumulate and dispatch latency grows
- **Idempotency** — Morning Brief dispatch deduped by `(workspace_id, brief_id, date)` — see `idempotency-handling`

## Never Do

- Send sensitive data in payload (PII, financial numbers, tokens)
- Request permission at app launch
- Trust the payload for navigation without Zod validation
- Skip receipt checking
- Send the same push from multiple producers without dedup
- Use Expo's `sound: 'sounds/custom.wav'` (managed-workflow constraint — use 'default')

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Mobile client (permission, channels, handlers) | **Karan** | TECH/10 §"Push" |
| Producer (notifications-service) | **Vikram** | TECH/08 §"Push" |
| Morning Brief snippet (Haiku) | **Maya** | TECH/05 §"Synthesis" |
| Schedule (EventBridge → trigger) | **Jatin** | TECH/09 §"Scheduling" |
| Receipt monitoring + dead-token cleanup | **Vikram** | BullMQ job |
| PII redaction in payloads | **Shreya** | `logging-best-practices` + `security-baseline` |

Related Brain skills: `morning-brief-mobile` (the surface deep design), `frontend-mobile`, `defense-in-depth-validation` (push payload validation), `idempotency-handling` (dispatch dedup), `mobile-offline-support` (handle push received while offline).
