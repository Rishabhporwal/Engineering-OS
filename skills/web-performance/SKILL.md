---
name: web-performance
description: Brain's web dashboard performance — Next.js 14 App Router (Server Components, route splitting, dynamic imports, image optimization, Visx chart perf), Core Web Vitals (LCP/INP/CLS) targets, the pre-deploy Lighthouse + budget audit gate, and RUM via web-vitals + PostHog. Use before merging Ananya's web changes, when the dashboard slows on cohort heatmaps or waterfalls, when LCP/INP/CLS alerts fire, or when a customer reports "the dashboard is slow".
---

# Web Performance — Brain's Dashboard

Brain's web dashboard (Next.js 14 App Router, shadcn, Visx) is the workbench operators use for Monday review + on-demand depth. Mobile is the daily heartbeat (Morning Brief); web is where they spend 5–30 minutes diving in. That experience MUST stay snappy — and it cannot regress silently. This skill covers both the **optimization techniques** and the **pre-deploy audit gate**.

## Core Web Vitals targets (Brain) — the one canonical table

| Metric | Good | Needs work | Poor (alert) |
|---|---|---|---|
| LCP (Largest Contentful Paint), p75 | <2.0s | 2.0–2.5s | >2.5s for 24h |
| INP (Interaction to Next Paint), p75 | <200ms | 200–300ms | >300ms for 24h |
| CLS (Cumulative Layout Shift), p75 | <0.05 | 0.05–0.1 | >0.1 ever |
| TTFB (BFF p95) | <200ms | 200–400ms | >400ms for 1h |
| FCP | <1.5s | 1.5–2.0s | >2.0s |
| Initial JS (any route) | <100 KB gz | 100–150 KB gz | >150 KB gz at deploy |

INP replaced FID as a Core Web Vital in March 2024. Brain measures **INP, not FID**.

Per-surface budgets: dashboard landing (LCP <2.0s, INP <200ms, CLS <0.05); Visx cohort heatmap + CM waterfall (first paint <500ms after data arrives; legend/tooltip hover <16ms = 60fps); BFF route handlers (TTFB <200ms p95 — Vikram owns api-gateway latency).

---

# Part 1 — Optimization techniques

## Default to Server Components

App Router renders Server Components on the server by default. Use Client Components (`'use client'`) **only** for browser APIs, hooks, event handlers, or interactivity. Server Components ship zero JS for static parts — the biggest single lever for Brain's dashboard.

```tsx
// app/(dashboard)/orders/page.tsx — Server Component
export default async function OrdersPage({ searchParams }: Props) {
  const orders = await trpcServer.orders.list.query({ /* from searchParams */ });
  return (
    <>
      <DateRangeFilter />          {/* the only 'use client' boundary (uses nuqs) */}
      <OrdersTable rows={orders.data} />  {/* fully server-rendered */}
    </>
  );
}
```

## Code splitting (route + dynamic component)

App Router splits per route segment automatically. For heavy components inside a route — Visx charts, the cohort heatmap — use `next/dynamic`:

```tsx
const CohortHeatmap = dynamic(() => import('@/components/cohort-heatmap'), {
  ssr: false,                                // canvas/SVG-heavy; render on client
  loading: () => <ChartSkeleton h={300} />,  // fixed height to avoid CLS
});
```

`ssr: false` prevents the server spending CPU on a chart the user might never scroll to.

## Image optimization (`<Image>` + CloudFront)

Always set `width`/`height` to reserve layout (eliminates CLS); mark the LCP candidate `priority`. Next.js Image emits AVIF/WebP via the optimizer at the CloudFront edge.

```tsx
<Image src="/brand-logos/sugandh-lok.png" alt="Sugandh Lok"
  width={120} height={40} priority sizes="(max-width: 600px) 100vw, 120px" />
```

## Visx charts — perf gotchas

| Gotcha | Fix |
|---|---|
| Re-rendering on every parent state change | Wrap in `React.memo`; pass only the data props it uses |
| Tooltips firing on every mousemove | `LocalizedTooltip` with `throttle: 16` (60fps) |
| Recomputing scales on every render | `useMemo` the `scaleBand`/`scaleLinear`; depend only on data + dimensions |
| Big datasets (>5k points) blocking main thread | Pre-aggregate server-side; never ship raw points to the client |
| SVG rendering 50k+ DOM nodes | Switch to `<canvas>` (Visx supports both) above ~2k marks |

## Bundle size discipline

```bash
pnpm dlx @next/bundle-analyzer   # after every PR touching app/ or components/
```

Targets: initial JS for `/dashboard` < 100 KB gz (canon route-JS budget); no single chunk > 500 KB gz; **Visx + Recharts coexist** — Recharts for ~90% of time-series/bar/line, Visx only for the specialty charts (CM waterfall, cohort heatmap) per the locked stack, and `dynamic`-import the Visx-heavy routes so the budget holds. Watch list: `lodash` → named imports; `date-fns` → `date-fns/{fn}` direct paths; heavy SDKs → minimal entry (Sentry browser, not full).

## Quick wins (always-on)

- Add `priority` to LCP images; `width`/`height` on every `<Image>`/`<img>`
- `dynamic(..., { ssr: false })` for below-the-fold heavy components
- Preload critical fonts in `app/layout.tsx`; defer PostHog/Sentry replay (`strategy="lazyOnload"`)
- CloudFront: `Cache-Control: public, max-age=31536000, immutable` on hashed filenames; `s-maxage=10` for slow-changing tRPC dashboard data, `no-store` for live
- Replace client-side aggregation with a tRPC procedure returning pre-aggregated data
- Brotli at the EKS NGINX ingress (Brain's locked stack)

## Larger levers (days–weeks)

- Tune CloudFront cache headers per route; ISR for per-brand-cached static dashboard cells
- Split the dashboard route into parallel routes with `loading.tsx` boundaries
- Server-side waterfall pre-computation (Maya + Aryan — see canon/technical-requirements.md)

---

# Part 2 — Pre-deploy audit gate

Run before merging any PR that touches `apps/web/app/`, `apps/web/components/`, or chart code; before deploying a new dashboard route; when alerts fire; or when a customer says "the dashboard is slow" (start here, not in DevTools).

### 1. Lighthouse CI (gate on PR)

`treosh/lighthouse-ci-action` runs on PR to `apps/web/**` against the staging dashboard/orders/cohorts URLs with a `lighthouse-budget.json` (FCP 1500ms, LCP 2000ms, speed-index 2500ms, interactive 3000ms; script 100KB per the canon route-JS budget, total 600KB). **PR fails if the budget is exceeded** — fix the regression or bump the budget with reviewer approval.

### 2. Real-user metrics (RUM) via `web-vitals` + PostHog

```typescript
// app/layout.tsx — root, runs once per visit
useReportWebVitals((m) => {
  posthog.capture('web_vital', {
    name: m.name, value: m.value, rating: m.rating,  // good | needs-improvement | poor
    route: window.location.pathname, workspace_id: getWorkspaceId(),
  });
});
```

PostHog dashboard **"Web Vitals by route"** — p50/p75/p95 by route segment; alerts configured per the targets table above (also mirrored to CloudWatch via the BFF).

### 3. On-incident manual audit

```bash
pnpm dlx lighthouse https://staging.brain.pipadacapital.com/dashboard \
  --preset=desktop --only-categories=performance --output html --output-path /tmp/lhci.html
```

Look for: the **LCP element** (image → `priority`? chart waiting on a slow tRPC call → `sql-query-optimization`? web font → preload?); **Total Blocking Time** (large JS chunks → `@next/bundle-analyzer`); **CLS** source (images without dimensions, async charts without a skeleton).

### Audit checklist

- [ ] Baseline measured (Lighthouse CI + PostHog RUM)
- [ ] LCP element identified (image / chart / hero text)
- [ ] Bundle analyzer run; no chunk > 500 KB gz; total initial route JS < 100 KB gz (canon budget)
- [ ] No `<img>`/`<Image>` without explicit width/height
- [ ] CLS sources reviewed (fonts, charts)
- [ ] Tested on slow 3G throttling (India-realistic) AND a real mid-tier Android device, not just iPhone
- [ ] Budget updated (or PR fixes the regression); PostHog alert thresholds reviewed for the route

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Dashboard performance + Visx rendering | **Ananya** | canon/technical-requirements.md (Next.js BFF, design system, charts) |
| PR-time Lighthouse gate | **Ananya** + **Jatin** | CI config |
| RUM dashboards + alerts | **Ananya** + **Jatin** | `observability` |
| BFF route handler latency (TTFB) | **Ananya** + **Vikram** | canon/technical-requirements.md |
| CloudFront cache config | **Jatin** | canon/technical-requirements.md |
| ClickHouse query speed (often the LCP bottleneck) | **Maya** | `sql-query-optimization` |

Related Brain skills: `observability` (alerts + RUM), `frontend-web` (broader Ananya playbook), `sql-query-optimization` (slow tRPC/Postgres/ClickHouse backend = slow LCP).
