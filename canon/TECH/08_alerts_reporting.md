# TECH/08 — Alerts, Reporting & Notifications (notifications-service)

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E4 (Analytics/ML) + E1 (Tech Lead) | **Reviewers:** All
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/05_intelligence_layer.md](05_intelligence_layer.md)

This document specifies:
- notifications-service architecture (Kafka consumer)
- Threshold-based alert evaluation
- Daily/weekly digest composition
- Multi-channel dispatch: SES, Slack, WhatsApp, in-app
- Export jobs (CSV, XLSX, PDF) via S3
- Outbound webhooks (Phase 4)

---

## 1. notifications-service Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  notifications-service (Node/TypeScript)              │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ gRPC Server                                                     ││
│  │  • ListAlertRules / UpsertAlertRule / DeleteAlertRule           ││
│  │  • ListAlertEvents / AcknowledgeAlert                           ││
│  │  • EnqueueExport / GetExportStatus                              ││
│  │  • ConfigureWebhook                                             ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Kafka Consumers (multiple consumer groups)                      ││
│  │                                                                 ││
│  │  • analytics.metrics.daily_materialized.v1                      ││
│  │    → evaluate threshold rules; fire alerts                      ││
│  │                                                                 ││
│  │  • intelligence.anomaly.detected.v1                             ││
│  │    → wrap as alert; deliver                                     ││
│  │                                                                 ││
│  │  • intelligence.insight.generated.v1                            ││
│  │    → enqueue for digest; surface critical immediately           ││
│  │                                                                 ││
│  │  • operations.export.requested.v1                               ││
│  │    → run export job                                             ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Scheduled Jobs (EventBridge → SQS → service)                    ││
│  │  • Daily 06:00 IST: digest composition + dispatch               ││
│  │  • Weekly Monday 08:00 IST: weekly digest                       ││
│  │  • Monthly 1st: monthly PDF report                              ││
│  └────────────────────────────────┬────────────────────────────────┘│
│                                   │                                   │
│  ┌────────────────────────────────▼────────────────────────────────┐│
│  │ Delivery Workers                                                ││
│  │  • EmailWorker (AWS SES via SDK)                                ││
│  │  • SlackWorker (incoming webhook URLs)                          ││
│  │  • WhatsAppWorker (Gupshup API)                                 ││
│  │  • InAppWorker (Postgres in_app_notifications)                  ││
│  │  • WebhookWorker (HMAC-signed HTTPS POST)                       ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Export Workers                                                  ││
│  │  • CSV/XLSX renderer                                            ││
│  │  • PDF renderer (headless Chromium / Puppeteer)                 ││
│  │  • S3 upload + signed URL generation                            ││
│  └─────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Scaling

- 2–8 pods of the main service
- 2–10 pods of delivery workers (separate deployment)
- Each delivery channel has its own worker pool (independent scaling)

---

## 2. Alert Architecture

### Sources of Alerts

1. **User-defined rules** in `alert_rules` (TECH/01)
2. **System-default rules** seeded on workspace creation (per-region from `RegionAdapter`)
3. **Anomaly-detected** events from intelligence-service

### Kafka-Driven Evaluation

Every time daily_metrics are materialized for a workspace, an event is published. notifications-service consumes it and evaluates all rules for that workspace:

```typescript
// apps/notifications-service/src/consumers/metricsMaterializedConsumer.ts

import { Kafka } from "kafkajs"; // MIGRATE: kafkajs is abandoned (broken under Kafka 4.0) -> use /kafka-javascript (KafkaJS-compatible API)

async function onMetricsMaterialized(event: MetricsMaterializedEvent) {
  const { workspaceId, date } = event;

  const rules = await db.alertRules.findMany({
    where: { workspaceId, enabled: true },
  });

  for (const rule of rules) {
    const result = await evaluateRule(workspaceId, rule, date);
    if (result.triggered) {
      const signature = computeFireSignature(rule, result);
      if (!await isRecentlyFired(workspaceId, rule.id, signature)) {
        await fireAlert(workspaceId, rule, result);
      }
    }
  }
}

async function evaluateRule(workspaceId: string, rule: AlertRule, date: Date): Promise<EvaluationResult> {
  if (rule.condition === 'above') {
    const current = await fetchCurrentMetricValue(workspaceId, rule.metricName, date);
    return { triggered: current > rule.threshold, observed: current, expected: rule.threshold };
  } else if (rule.condition === 'below') {
    const current = await fetchCurrentMetricValue(workspaceId, rule.metricName, date);
    return { triggered: current < rule.threshold, observed: current, expected: rule.threshold };
  } else if (rule.condition === 'change_pct_above') {
    const current = await fetchCurrentMetricValue(workspaceId, rule.metricName, date);
    const prior = await fetchPriorMetricValue(workspaceId, rule.metricName, rule.comparisonWindow);
    const changePct = prior ? (current - prior) / prior : 0;
    return { triggered: changePct > rule.threshold, observed: changePct, expected: rule.threshold };
  }
  // ... other conditions
}
```

### Alert Events Schema

```sql
CREATE TABLE alert_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  rule_id UUID REFERENCES alert_rules(id) ON DELETE SET NULL,
  insight_id UUID REFERENCES ai.insights(id),

  metric_name TEXT NOT NULL,
  severity TEXT NOT NULL,
  signature TEXT NOT NULL,                         -- dedup key

  observed_value NUMERIC(20, 6),
  expected_value NUMERIC(20, 6),
  message TEXT NOT NULL,
  context JSONB,

  fired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID REFERENCES auth.users(id),

  delivered_channels TEXT[] NOT NULL DEFAULT '{}',
  delivery_log JSONB
);

CREATE INDEX idx_alert_events_workspace_fired ON alert_events(workspace_id, fired_at DESC);
CREATE INDEX idx_alert_events_workspace_unacked ON alert_events(workspace_id) WHERE acknowledged_at IS NULL;
```

### Firing an Alert

```typescript
async function fireAlert(workspaceId, rule, result) {
  // 1. Generate narrative via Claude Haiku (cheap, fast)
  const insight = await generateAlertInsight(workspaceId, rule, result);

  // 2. Persist event
  const event = await createAlertEvent(workspaceId, rule, result, insight);

  // 3. Publish to Kafka for delivery workers
  await kafkaProducer.send({
    topic: 'notifications.alert.fired.v1',
    messages: [{
      key: workspaceId,
      value: serializeAvro({ event_id: event.id, workspace_id: workspaceId, channels: rule.channels, ... }),
    }],
  });
}
```

Delivery workers consume `notifications.alert.fired.v1` and dispatch per channel.

---

## 3. Notification Channels

### 3.1 Email (AWS SES)

```typescript
// apps/notifications-service/src/delivery/email.ts
import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";

const ses = new SESClient({ region: 'ap-south-1' });

async function sendAlertEmail(event: AlertEvent, recipients: User[]) {
  const html = renderAlertEmailHtml(event);
  const text = renderAlertEmailText(event);

  for (const recipient of recipients) {
    await ses.send(new SendEmailCommand({
      Source: 'alerts@{BRAIN_DOMAIN}',
      Destination: { ToAddresses: [recipient.email] },
      Message: {
        Subject: { Data: `${event.severity.toUpperCase()}: ${event.title}` },
        Body: {
          Html: { Data: html },
          Text: { Data: text },
        },
      },
      ConfigurationSetName: 'brain-alerts',                // tracks open/click via SES
      Tags: [
        { Name: 'workspace_id', Value: event.workspaceId },
        { Name: 'event_id', Value: event.id },
        { Name: 'severity', Value: event.severity },
      ],
    }));
  }
}
```

**SES Setup:**
- Verified sending domains (DKIM, SPF, DMARC)
- Configuration set with CloudWatch event publishing (opens, clicks, bounces, complaints)
- Suppression list for bounced/complained addresses
- Dedicated IP pool (Phase 3) for reputation control
- Bounce/complaint webhook → notifications-service updates user opt-in state

**Cost:** $0.10/1000 emails. At 1000 workspaces × 30 emails/month = 30k emails = $3/month.

### 3.2 Slack

```typescript
// apps/notifications-service/src/delivery/slack.ts
import { request } from "undici";

async function sendSlackAlert(event: AlertEvent, webhookUrl: string) {
  const color = { info: '#3B82F6', warning: '#F59E0B', critical: '#EF4444' }[event.severity];

  const payload = {
    attachments: [{
      color,
      title: `${event.severity.toUpperCase()}: ${event.title}`,
      title_link: `https://{BRAIN_DOMAIN}/alerts/${event.id}`,
      text: event.message,
      fields: [
        { title: 'Metric', value: event.metricName, short: true },
        { title: 'Observed', value: formatValue(event.observedValue, event.metricName), short: true },
        { title: 'Expected', value: formatValue(event.expectedValue, event.metricName), short: true },
      ],
      footer: 'Brain',
      footer_icon: 'https://{BRAIN_DOMAIN}/icon.png',
      ts: Math.floor(event.firedAt.getTime() / 1000),
    }],
  };

  await request(webhookUrl, {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' },
  });
}
```

**Setup:** workspace creates a Slack incoming webhook in their workspace; pastes into Brain Settings → Integrations → Slack.

### 3.3 WhatsApp (Gupshup)

```typescript
// apps/notifications-service/src/delivery/whatsapp.ts

async function sendWhatsAppAlert(event: AlertEvent, phone: string) {
  // Pre-approved template: "brain_alert_v1"
  const payload = {
    channel: 'whatsapp',
    source: GUPSHUP_SOURCE_NUMBER,
    destination: phone,
    template: {
      id: 'brain_alert_v1',
      params: [
        event.severity.toUpperCase(),
        event.title,
        event.message.slice(0, 300),
        `https://{BRAIN_DOMAIN}/alerts/${event.id}`,
      ],
    },
  };

  await request('https://api.gupshup.io/wa/api/v1/template/msg', {
    method: 'POST',
    headers: { apikey: GUPSHUP_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**Constraints:** templates must be pre-approved by WhatsApp (Brain submits via Gupshup). India-region default; expand to other regions via local providers (Phase 4).

### 3.4 Push Notifications (Mobile — APNS + FCM via Expo)

For Brain's React Native mobile app (see [TECH/10_mobile_architecture.md](10_mobile_architecture.md)), push is the primary "you need to know now" channel — operators see them on lock screen + app icon badge. Available from Phase 1 W11 (mobile MVP includes push).

**Token registration:** mobile app calls `trpc.notifications.registerPushToken` on auth.

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

**Delivery via Expo Push API** (fans out to APNS for iOS, FCM for Android):

```typescript
// apps/notifications-service/src/delivery/push.ts
import { Expo } from 'expo-server-sdk';

const expo = new Expo({ accessToken: process.env.EXPO_ACCESS_TOKEN });

async function sendPushAlert(event: AlertEvent, recipients: PushRecipient[]) {
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
      channelId: event.severity === 'critical' ? 'alerts.critical' : 'alerts.warning',
    }));

  for (const chunk of expo.chunkPushNotifications(messages)) {
    try {
      const tickets = await expo.sendPushNotificationsAsync(chunk);
      await persistDeliveryTickets(event.id, tickets);
    } catch (err) {
      Sentry.captureException(err);
    }
  }
}
```

**Receipt checking** (30 minutes after send):

```typescript
async function checkDeliveryReceipts(ticketIds: string[]) {
  const receipts = await expo.getPushNotificationReceiptsAsync(
    expo.chunkPushNotificationReceiptIds(ticketIds).flat()
  );
  for (const [id, receipt] of Object.entries(receipts)) {
    if (receipt.status === 'error' && receipt.details?.error === 'DeviceNotRegistered') {
      await deactivatePushToken(id);
    }
  }
}
```

**Android Notification Channels** (set on first app launch):

| Channel ID | Importance | Sound |
|-----------|-----------|-------|
| `alerts.critical` | High | Default |
| `alerts.warning` | Default | Default |
| `digests` | Low | None |
| `insights` | Default | None |

Channels let users granularly opt-out via system settings.

**Deep links:** every push includes a `deepLink` field (e.g., `brain://alerts/{id}`) that opens the specific screen in the mobile app on tap.

**Quiet-hours integration:** notifications-service already respects workspace quiet hours. Push follows the same rule — non-critical events queue for end-of-quiet-hours.

**Cost:** Expo Push API is free for our send volume. APNS + FCM are free. Total push cost: ~$0/month even at 1M sends/month.

### 3.5 In-App

```sql
CREATE TABLE in_app_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),               -- NULL = all members
  type TEXT NOT NULL,                                   -- 'alert', 'insight', 'export_ready', 'integration_status'
  severity TEXT,
  title TEXT NOT NULL,
  body TEXT,
  link_url TEXT,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_in_app_notifications_unread ON in_app_notifications(workspace_id, user_id) WHERE read_at IS NULL;
```

Frontend (web + mobile) polls `trpc.notifications.unread.useQuery({ refetchInterval: 30000 })` for the bell badge, or subscribes via tRPC subscription for real-time (Phase 3).

---

## 3a. Morning Brief — The Product's Defining Surface

Per the brief and [TECH/05 §0.7](05_intelligence_layer.md), the **Morning Brief** is the heart of the product. It is not a "daily digest" — it is three approve-or-reject signals on the founder's phone every morning.

**Daily Intelligence Loop ownership:** notifications-service owns the **assembly + delivery** step (07:15 IST). The upstream steps (data pull, vector generation, memory query, agent processing) are owned by intelligence-service.

### 3a.1 Morning Brief Composition

```
intelligence-service publishes: intelligence.daily_recommendations.ready.v1
   {
     "brand_id": "...",
     "as_of": "2026-05-13",
     "recommendations": [
       { "agent": "aicmo-meta", "priority_score": 0.91, "type": "creative_fatigue", ... },
       { "agent": "aicfo-conversion", "priority_score": 0.78, "type": "cod_block_pincode", ... },
       { "agent": "aicoo-logistics", "priority_score": 0.65, "type": "courier_swap", ... },
       ...
     ],
     "morning_brief_text": "...",   // Pre-synthesised by Claude Sonnet at 07:15
     "brand_fingerprint_summary": "..."
   }

notifications-service consumes the event:
1. Selects top 3 by priority_score
2. Composes phone-optimised payload:
   - One-line summary per signal
   - Approve / Reject / Edit buttons (deep-link to mobile app)
   - Optional "see why" link → web app drill-down
3. Pushes to mobile app via expo-notifications (07:15 IST)
4. Falls back to email + WhatsApp if push fails or user opts in to additional channels
5. Records delivery + (later) Owner response back to Decision Log
```

### 3a.2 Phone-First Push Payload

```typescript
const morningBriefPush = {
  to: ownerPushToken,
  title: "Brain — your 3 things today",
  body: "1. Pause campaign X (-18% CTR). 2. Block COD for pincode 110001. 3. Switch courier for South region.",
  sound: 'default',
  channelId: 'morning_brief',     // dedicated channel; never throttled
  priority: 'high',
  data: {
    type: 'morning_brief',
    brand_id: brandId,
    as_of: today,
    deep_link: `brain://morning-brief/${today}`,
  },
};
```

The mobile app deep-link opens the 3-signal interactive screen (see [TECH/10](10_mobile_architecture.md)).

### 3a.3 Email Fallback

If push delivery fails OR Owner opts in to email-also (some founders prefer both):

```
Subject: Brain — 3 things to look at today
From: brain@brand-owner-domain  (white-labelled? Phase 4)
Body (HTML + plain text):
  - One-line for each of 3 actions
  - "Open in Brain →" deep link (universal link → mobile app or web)
  - Footer: "Approve / Reject / Discuss" buttons linked to web
```

### 3a.4 SLO

| Metric | Target |
|--------|--------|
| Morning Brief delivered by 07:20 IST | > 99.5% of brand-days |
| Delivery latency (intelligence event → push received) | p95 < 30 seconds |
| Push delivery success rate | > 98% (excluding device-not-registered) |
| Owner read rate within 90 min of delivery | > 80% target (this is the Daily Active Founders metric) |

### 3a.5 The Evening Pulse (18:00 IST)

A lighter-weight version of the Morning Brief — only exceptions vs forecast. Push + in-app, no email by default.

Same composition pattern; different topic (`intelligence.evening_pulse.v1`).

---

## 4. Daily Digest (Detailed Web Brief — Optional)

The Morning Brief is the heart. The **Daily Digest** is the longer-form version some operators prefer as a Monday review primer. Delivered 06:00 IST (per workspace timezone) to all opted-in members.

### Composition Flow

Triggered after insight generation completes (05:30 IST):

```typescript
// apps/notifications-service/src/jobs/dailyDigest.ts

async function generateDailyDigest(workspaceId: string) {
  const workspace = await coreClient.getWorkspace({ workspaceId });
  const yesterday = subDays(new Date(), 1);

  const digest = {
    workspace,
    yesterday: yesterday,
    headline: await buildHeadlineKpis(workspaceId, yesterday),
    deltas: await buildDeltaSection(workspaceId, yesterday),
    insights: prioritize(await fetchUnackedInsights(workspaceId, sinceHoursAgo: 24), max: 5),
    openAlerts: await fetchOpenAlerts(workspaceId),
    todayPlan: await fetchTodayPlan(workspaceId),
  };

  const html = renderDigestHtml(digest, workspace.home_region);    // region-aware formatting
  const text = renderDigestText(digest, workspace.home_region);

  const recipients = await getDigestRecipients(workspaceId, 'daily');
  for (const recipient of recipients) {
    await ses.send(new SendEmailCommand({
      Source: 'digest@{BRAIN_DOMAIN}',
      Destination: { ToAddresses: [recipient.email] },
      Message: {
        Subject: { Data: `Brain Daily — ${workspace.name} — ${format(yesterday, 'EEE, MMM d')}` },
        Body: { Html: { Data: html }, Text: { Data: text } },
      },
      ConfigurationSetName: 'brain-digests',
      Tags: [
        { Name: 'workspace_id', Value: workspaceId },
        { Name: 'frequency', Value: 'daily' },
      ],
    }));
  }
}
```

### Email Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  Brain Daily — the pilot brand                              Tue, May 13   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Yesterday at a glance                                          │  │
│  │                                                                 │  │
│  │  Revenue   ₹4,82,000  ↑8% vs Mon  • 108% of ₹3.5L goal  🟢    │  │
│  │  MER       3.4x       ↓0.1x       • 97% of 3.5x goal   🟢    │  │
│  │  aMER      1.7x       ↓22% (7d)   • 74% of 2.3x goal   🔴    │  │
│  │  CAC       ₹920       ↑16% (7d)   • Above ₹800 goal    🔴    │  │
│  │  Orders    186        ↑12% vs Mon                              │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ⚠️ 2 things to look at today                                          │
│  ────────────────────────────                                         │
│                                                                       │
│  1. aMER dropped to 1.7x — acquisition engine weakening              │
│     Your aMER fell 22% over the last 7 days...                        │
│     [View full insight →]                                             │
│                                                                       │
│  2. 4 new pincodes recommended for COD restriction                   │
│     ...                                                               │
│     [Review pincodes →]                                               │
│                                                                       │
│  📅 Today's plan                                                      │
│  ───────────────                                                      │
│  Planned ad spend: ₹1.2L (₹85K Meta acquisition, ₹35K Google)        │
│  Forecast revenue: ₹4.1L–₹5.3L (base ₹4.6L)                          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  [Open Brain →]                                                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Manage preferences | Unsubscribe                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### Region-Aware Formatting

- INR workspaces: ₹4,82,000 (Indian grouping), lakh/crore
- USD workspaces: $4,820 (US grouping)
- Each region's "yesterday" computed in workspace timezone

### Frequency Options

Recipients choose:
- Daily (06:00 local) — owner default
- Weekly (Mon 08:00 local) — analyst/viewer default
- Critical-only
- None

### First-Day Stub

For new workspaces:
> "Brain is still gathering data. We need ~7 days of orders + ad spend to generate meaningful insights. We'll start sending real digests once we're ready."

---

## 5. Weekly Digest

Monday 08:00 IST (workspace local). Wider lens:

- Week-over-week comparison of all KPIs
- Customer lifecycle changes
- Top campaigns this week
- Top first products driving repeat
- Cumulative MTD spend vs goal
- Forecast for next week

Same delivery channels.

---

## 6. Monthly Report (PDF)

Sent on the 1st of each month. The "investor report."

```typescript
// apps/notifications-service/src/jobs/monthlyReport.ts
import { launch } from "puppeteer-core";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

async function generateMonthlyPdf(workspaceId: string, month: Date) {
  const html = await renderMonthlyReportHtml(workspaceId, month);
  const browser = await launch({ executablePath: CHROME_PATH, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setContent(html);
  const pdf = await page.pdf({ format: 'A4', printBackground: true });
  await browser.close();

  const key = `reports/${workspaceId}/${format(month, 'yyyy-MM')}.pdf`;
  await s3.send(new PutObjectCommand({
    Bucket: 'brain-exports',
    Key: key,
    Body: pdf,
    ContentType: 'application/pdf',
  }));

  const signedUrl = await getSignedUrl(s3, new GetObjectCommand({ Bucket: 'brain-exports', Key: key }), { expiresIn: 7 * 24 * 3600 });

  await sendEmailWithLink(workspaceId, signedUrl, 'Monthly Report');
}
```

Headless Chromium runs in a sidecar pod (separate from main service, larger memory footprint).

**Contents:**
- Full P&L for the month
- CM Waterfall
- Channel performance breakdown
- Cohort summary
- Top products
- Region-specific section (India: RTO costs + pincode performance; US: chargebacks + state sales tax)
- Forecast next month

---

## 7. Export Jobs

Triggered by user clicking "Export" on any page.

### Flow

```
User clicks Export
    │
    ▼
api-gateway → notifications-service.EnqueueExport (gRPC)
    │
    ▼
notifications-service inserts row in `export_jobs` (status='queued')
    │
    ▼
Publishes operations.export.requested.v1
    │
    ▼
Export worker consumes; runs the export (CSV/XLSX via streams; PDF via Chromium)
    │
    ▼
Uploads to S3 (bucket: brain-exports)
    │
    ▼
Generates signed URL (24h expiry)
    │
    ▼
Updates export_jobs.status='completed', signed_url=...
    │
    ▼
Publishes notifications.export.ready.v1 → email + in-app
```

### `export_jobs` Schema

```sql
CREATE TABLE export_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  requested_by UUID NOT NULL REFERENCES auth.users(id),
  export_type TEXT NOT NULL,                            -- 'pnl', 'products', 'calendar', 'cm_waterfall', ...
  format TEXT NOT NULL,                                 -- 'csv', 'xlsx', 'pdf'
  params JSONB NOT NULL,                                -- date_range + filters
  status TEXT NOT NULL DEFAULT 'queued',                -- queued, running, completed, failed
  s3_key TEXT,
  signed_url TEXT,
  signed_url_expires_at TIMESTAMPTZ,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);
```

### Supported Exports

| Module | Formats |
|--------|---------|
| P&L Table | CSV, XLSX |
| Products | CSV, XLSX |
| Calendar Report | CSV, XLSX, PDF |
| CM Waterfall | XLSX, PDF |
| First Product Cascade | CSV, XLSX |
| Cohorts | XLSX |
| LTV Curves | XLSX (with chart) |
| Customer List | CSV |
| Monthly Report | PDF (auto + on-demand) |
| Pincode Reliability (IN) | CSV, XLSX |

### Large Export Streaming

For large exports (e.g., 50k customers), stream rows to S3 via multipart upload to avoid OOM:

```typescript
import { Upload } from "@aws-sdk/lib-storage";

const upload = new Upload({
  client: s3,
  params: { Bucket: 'brain-exports', Key: key, Body: passThrough, ContentType: 'text/csv' },
});

const passThrough = new PassThrough();
upload.done();

const queryStream = await ch.queryStream(largeQuery);
queryStream.pipe(csvFormatter()).pipe(passThrough);
```

---

## 8. Outbound Webhooks (Phase 4)

For brands integrating Brain into their own systems.

```sql
CREATE TABLE outbound_webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  secret TEXT NOT NULL,
  events TEXT[] NOT NULL,                              -- ['alert.fired', 'insight.generated', 'export.ready']
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  webhook_id UUID NOT NULL REFERENCES outbound_webhooks(id) ON DELETE CASCADE,
  event_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',              -- pending, succeeded, failed
  attempts INT NOT NULL DEFAULT 0,
  last_response_code INT,
  last_response_body TEXT,
  last_attempt_at TIMESTAMPTZ,
  next_retry_at TIMESTAMPTZ
);
```

### Delivery

```typescript
async function deliverWebhook(webhook: OutboundWebhook, event: any) {
  const payload = JSON.stringify(event);
  const signature = crypto.createHmac('sha256', webhook.secret).update(payload).digest('hex');

  const response = await request(webhook.url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Brain-Signature': signature,
      'X-Brain-Event': event.type,
      'X-Brain-Delivery-Id': delivery.id,
    },
    body: payload,
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    await markDeliverySucceeded(delivery.id);
  } else {
    await scheduleRetry(delivery.id, attempts);  // exponential backoff, max 5 attempts
  }
}
```

---

## 9. Alert UI

### `/alerts` Page

**Tab 1: Feed**
Chronological list. Filterable by severity / status. Each row:
- Severity badge
- Title
- Time
- Metric chip
- Acknowledge button
- "Snooze for 24h" option

**Tab 2: Rules**
CRUD UI for `alert_rules`.

### Alert Detail Drawer

Opens on row click:
- Full AI-generated narrative
- Metric chart for the relevant window
- Recommended actions (linked to Brain pages)
- "Mark resolved" with optional note
- Related insights (Phase 3 — semantic search via embeddings)

---

## 10. Anti-Spam / Quiet Hours

### Per-Workspace Rate Limits

- Max 10 alert notifications per channel per hour
- Max 30 alert notifications per channel per day
- Beyond: queued + delivered as end-of-hour digest

### Quiet Hours

```sql
ALTER TABLE workspaces ADD COLUMN quiet_hours_start TIME DEFAULT '22:00';
ALTER TABLE workspaces ADD COLUMN quiet_hours_end TIME DEFAULT '07:00';
```

During quiet hours:
- Only `critical` severity delivers via WhatsApp/Slack
- Non-critical queued; delivered at end of quiet hours
- In-app notifications always silent (badge updates regardless)

```typescript
async function shouldDeliverNow(workspaceId, event): Promise<boolean> {
  const ws = await coreClient.getWorkspace({ workspaceId });
  const now = utcToZonedTime(new Date(), ws.default_timezone);
  if (isInQuietHours(ws.quiet_hours_start, ws.quiet_hours_end, now) && event.severity !== 'critical') {
    await queueForMorning(event);
    return false;
  }
  return true;
}
```

---

## 11. Observability

CloudWatch metric namespace `Brain/Notifications`:

- `alerts.evaluated_total{workspace_id}` — counter
- `alerts.fired_total{severity, workspace_id}` — counter
- `alerts.delivered_total{channel, success}` — counter
- `alerts.delivery_duration_seconds{channel}` — histogram
- `digest.generated_total{frequency, workspace_id}` — counter
- `digest.email_sent_total{success}` — counter
- `export.jobs_total{type, format, success}` — counter
- `export.job_duration_seconds{type}` — histogram
- `webhook.delivered_total{success}` — counter

CloudWatch alarms (meta-monitoring — if alerting breaks, who alerts us?):
- 0 daily digests sent for 2+ days → page on-call
- SES bounce rate > 5% over 1h → page on-call
- Gupshup error rate > 5% over 1h → P2 alert
- Workspace with 0 alert evaluations for 24h → admin email

---

## 12. Cost Model

| Channel | Cost per message | Volume @ 1000 workspaces | Monthly |
|---------|------------------|--------------------------|---------|
| Email (SES) | $0.0001 | ~30K/day = ~900K/mo | **$90** |
| Slack | Free | — | $0 |
| WhatsApp (Gupshup) | ₹0.32 (utility) | ~300/day = ~9K/mo | **~₹2,900 ($35)** |
| **Push (Expo → APNS/FCM)** | Free | ~10K/day = ~300K/mo | **$0** |
| In-app | Free | — | $0 |
| LLM (Haiku for narratives) | ~$0.0005/alert | ~3K/day = ~90K/mo | **~$45** |
| PDF generation | Compute-only | ~1K/mo | **~$10** |

**Total alerts/digests cost at 1000 workspaces: ~$180/month.** Scales linearly.

---

## 13. Scale Design at 100k Events/Min

At Phase 4 with 1000 workspaces:
- Materialization events: 1000/day = trivial
- Alert evaluation: 1000 × ~10 rules avg = 10K evaluations/day
- Insights: 1000 × 5 insights/day = 5K insights
- Digests: 1000 × daily = 1000 emails at 06:00 local
- Exports: ~100/day

Notifications-service load is **bursty**:
- 06:00 IST burst: 600 daily digests in 10 minutes = 1 digest/sec
- Distributed across timezones: smoother for global expansion

Worker pods scale 2 → 10 via SQS queue depth.

---

## 14. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Per-recipient alert preferences? | E1 | Workspace-wide Phase 1; per-recipient Phase 2. |
| SMS as a channel? | E4 | Skip — WhatsApp + email dominate India; US uses email + Slack. |
| Holiday-aware delivery (don't send on Diwali)? | E4 | Phase 3. Festival-aware quiet hours per workspace. |
| AI-generated alert message vs templated? | E4 | AI for warning/critical (Claude Haiku); templates for info. |
| Push notifications (browser)? | E2 + E4 | Phase 3. Standard Web Push API. |
| Email from regional sender (alerts@.in vs .com)? | E1 | Single global sender Phase 1; regional Phase 4 if deliverability requires. |
