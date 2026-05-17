---
name: web-performance-optimization
description: Next.js 14 App Router performance — Server Components, route segments, dynamic imports, image optimization, Visx chart perf, Core Web Vitals (LCP, INP, CLS) targets for Brain's dashboard. Use when the dashboard slows on cohort heatmaps or waterfall charts, when LCP > 2.5s on the workspace landing, when bundle size grows, when adding a new dashboard route.
---

# Web Performance Optimization

Brain's web dashboard (Next.js 14 App Router, shadcn, Visx) is the workbench operators use for Monday review + on-demand depth. Mobile is the daily heartbeat (Morning Brief); web is where they spend 5–30 minutes diving in. That diving-in experience MUST stay snappy: LCP <2s on the landing, INP <200ms on chart hover, CLS ≈0 on dashboard re-renders.

## Why this matters for Brain

| Surface | Budget | Owner |
|---|---|---|
| Workspace landing / dashboard | LCP < 2.0s, INP < 200ms, CLS < 0.05 | Ananya |
| Cohort heatmap (Visx) | First paint < 500ms after data arrives; smooth pan/zoom | Ananya |
| CM Waterfall (Visx) | First paint < 500ms; legend hover < 16ms | Ananya |
| BFF route handlers | TTFB < 200ms p95 (Vikram is on hook for the api-gateway latency) | Ananya + Vikram |

## Default to Server Components

Next.js App Router renders Server Components on the server by default. Use Client Components (`'use client'`) **only** when you need browser APIs, hooks (useState/useEffect), event handlers, or interactivity. Server Components ship zero JS for static parts of the page — biggest single lever for Brain's dashboard.

```tsx
// app/(dashboard)/orders/page.tsx — Server Component
import { OrdersTable } from '@/components/orders-table'; // also Server, renders rows
import { DateRangeFilter } from '@/components/date-range-filter'; // Client (uses nuqs)

export default async function OrdersPage({ searchParams }: Props) {
  const orders = await trpcServer.orders.list.query({ /* from searchParams */ });
  return (
    <>
      <DateRangeFilter />
      <OrdersTable rows={orders.data} />
    </>
  );
}
```

The `DateRangeFilter` is the only `'use client'` boundary on this page. The orders table is fully server-rendered.

## Code splitting (route + dynamic component)

App Router splits per route segment automatically. For heavy components inside a route — Visx charts, recharts, the cohort heatmap — use `next/dynamic`:

```tsx
import dynamic from 'next/dynamic';

const CohortHeatmap = dynamic(() => import('@/components/cohort-heatmap'), {
  ssr: false,                          // canvas/SVG-heavy; render on client
  loading: () => <ChartSkeleton h={300} />, // fixed-height to avoid CLS
});
```

`ssr: false` prevents the server from spending CPU on a chart that the user might not scroll to.

## Image optimization (Next.js `<Image>` + CloudFront)

```tsx
import Image from 'next/image';

<Image
  src="/brand-logos/sugandh-lok.png"
  alt="Sugandh Lok"
  width={120}
  height={40}
  priority           // LCP candidate? mark priority
  sizes="(max-width: 600px) 100vw, 120px"
/>;
```

Next.js Image emits AVIF/WebP via the image optimizer at the CloudFront edge. Always set `width`/`height` to reserve layout — eliminates CLS.

## Visx charts — perf gotchas

| Gotcha | Fix |
|---|---|
| Re-rendering on every parent state change | Wrap chart in `React.memo`; pass only the data props it actually uses |
| Tooltips firing on every mousemove | Use `LocalizedTooltip` with `throttle: 16` (60fps) |
| Recomputing scales on every render | `useMemo` the `scaleBand`/`scaleLinear`; depend only on data + dimensions |
| Big datasets (>5k points) blocking the main thread | Pre-aggregate server-side; never ship raw points to the client |
| SVG rendering 50k+ DOM nodes | Switch to `<canvas>` (Visx supports both) above ~2k marks |

## Bundle size discipline

```bash
# After every PR touching app/ or components/
pnpm dlx @next/bundle-analyzer
```

Brain's targets:
- Initial JS for `/dashboard` route: **< 200 KB gz** (currently uses tRPC + nuqs + minimal client work)
- No single chunk > 500 KB gz
- Visx + Recharts both = no. Pick one (Brain uses **Visx** per the locked stack).

Watch list: lodash → use named imports; date-fns → use `date-fns/{fn}` direct paths; heavy SDKs (Sentry full vs Sentry browser) → use the minimal entry.

## Core Web Vitals — instrument with web-vitals

```typescript
// app/layout.tsx — root, runs once per visit
import { useReportWebVitals } from 'next/web-vitals';

useReportWebVitals((metric) => {
  // Brain ships these to PostHog (product) + CloudWatch via the BFF
  fetch('/api/internal/wv', {
    method: 'POST',
    body: JSON.stringify({ name: metric.name, value: metric.value, id: metric.id, workspaceId }),
    keepalive: true,
  });
});
```

PostHog dashboards show p50/p75/p95 by route segment. Alert if any segment's p75 LCP > 2.5s for 24h.

## Performance targets (Brain)

| Metric | Target | Alert |
|---|---|---|
| LCP (p75) | < 2.0s | > 2.5s for 24h |
| INP (p75) | < 200ms | > 300ms for 24h |
| CLS (p75) | < 0.05 | > 0.1 ever |
| TTFB (BFF p95) | < 200ms | > 400ms for 1h |
| Initial JS (any route) | < 200 KB gz | > 250 KB gz at deploy |

## Quick wins (always-on)

- [ ] Static assets cached at CloudFront edge with `Cache-Control: public, max-age=31536000, immutable` on hashed filenames
- [ ] tRPC responses: `s-maxage=10` for slow-changing dashboard data; `no-store` for live data
- [ ] Brotli on the BFF — on EKS, NGINX ingress handles compression (Brain's locked stack)
- [ ] Preload critical fonts in `app/layout.tsx`
- [ ] Defer non-critical scripts (PostHog, Sentry replay) via `next/script` with `strategy="lazyOnload"`

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Dashboard performance | **Ananya** | TECH/07 §"Next.js BFF + design system" |
| Visx chart rendering | **Ananya** | TECH/07 §"Charts" |
| BFF route handler latency | **Ananya** + **Vikram** | TECH/06 |
| CloudFront cache config | **Jatin** | TECH/09 |
| RUM dashboards + alerts | **Jatin** + Ananya | `observability` |

Related Brain skills: `web-performance-audit` (Lighthouse + budget gates), `frontend-web` (broader Ananya playbook), `sql-query-optimization` (slow BFF queries often = slow Postgres).
