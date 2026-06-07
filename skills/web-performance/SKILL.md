---
name: web-performance
description: Web dashboard performance — Server Components/code-splitting/chart-rendering, Core Web Vitals targets, the pre-deploy Lighthouse+budget CI gate, RUM. Tools (Next.js, Visx, PostHog) are examples; bind them via STACK.md.
---

# Web Performance — The Web Dashboard

> **Reference implementation.** This skill documents one concrete binding of the web-frontend seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to different technology. The *patterns* (Server Components by default, code-splitting, Core Web Vitals budgets, a PR-time perf gate, RUM) transfer; the named libraries (Next.js, Visx, PostHog) are examples.

A data-heavy web dashboard is a workbench operators use for periodic review + on-demand depth. It MUST stay snappy and cannot regress silently. This covers both **optimization techniques** and the **pre-deploy audit gate**.

> **Modern compilers auto-memoize** (e.g. the React Compiler) — most hand-written `useMemo`/`useCallback` is now optional. Reach for them only where the compiler provably can't (profiler-confirmed hot path); don't add manual memoization reflexively.

## Core Web Vitals targets (the one canonical table)

| Metric | Good | Needs work | Poor (alert) |
|---|---|---|---|
| LCP p75 | <2.0s | 2.0–2.5s | >2.5s for 24h |
| INP p75 | <200ms | 200–300ms | >300ms for 24h |
| CLS p75 | <0.05 | 0.05–0.1 | >0.1 ever |
| TTFB (BFF p95) | <200ms | 200–400ms | >400ms for 1h |
| FCP | <1.5s | 1.5–2.0s | >2.0s |
| Initial JS (any route) | <100 KB gz | 100–150 KB gz | >150 KB gz at deploy |

INP replaced FID in March 2024 — measure **INP, not FID**. Per-surface: dashboard landing (LCP<2.0s, INP<200ms, CLS<0.05); heavy charts like a heatmap + waterfall (first paint <500ms after data; hover <16ms = 60fps); BFF (TTFB <200ms p95 — the Backend Engineer owns API-surface latency).

# Part 1 — Optimization techniques

## Default to Server Components

Use Client Components (`'use client'`) **only** for browser APIs, hooks, event handlers, interactivity. Server Components ship zero JS for static parts — the biggest single lever.

```tsx
export default async function OrdersPage({ searchParams }) {
  const orders = await trpcServer.orders.list.query({ /* from searchParams */ });
  return (<><DateRangeFilter />{/* only 'use client' boundary */}<OrdersTable rows={orders.data} /></>);
}
```

## Code splitting (route + dynamic component)

```tsx
const CohortHeatmap = dynamic(() => import('@/components/cohort-heatmap'), {
  ssr: false,                                // canvas/SVG-heavy; render on client
  loading: () => <ChartSkeleton h={300} />,  // fixed height avoids CLS
});
```
`ssr: false` prevents the server spending CPU on a chart the user might never scroll to.

## Image optimization (`<Image>` + CDN)

Always set `width`/`height` (eliminates CLS); mark the LCP candidate `priority`. A modern image component emits AVIF/WebP at the CDN edge.
```tsx
<Image src="/logos/{slug}.png" alt="{label}" width={120} height={40} priority sizes="(max-width: 600px) 100vw, 120px" />
```

## Low-level SVG charts — perf gotchas (e.g. Visx)

| Gotcha | Fix |
|---|---|
| Re-render on every parent state change | `React.memo`; pass only used props |
| Tooltips firing on every mousemove | `throttle: 16` (60fps) |
| Recomputing scales every render | `useMemo` `scaleBand`/`scaleLinear`; depend only on data + dimensions |
| >5k points blocking main thread | pre-aggregate server-side; never ship raw points |
| SVG rendering 50k+ DOM nodes | switch to `<canvas>` above ~2k marks |

## Bundle size discipline

```bash
pnpm dlx @next/bundle-analyzer   # after every PR touching app/ or components/
```
Targets: initial JS for `/dashboard` < 100 KB gz; no single chunk > 500 KB gz; if two charting libs coexist, keep the heavy one (e.g. a low-level lib for waterfall/cohort heatmap) `dynamic`-imported and confined to those surfaces. Watch: `lodash`→named imports; `date-fns`→`date-fns/{fn}`; heavy SDKs→minimal entry.

## Quick wins (always-on)

- `priority` on LCP images; `width`/`height` on every image; `dynamic(..., { ssr: false })` for below-the-fold heavy components.
- Preload critical fonts; defer analytics/error-replay SDKs (`strategy="lazyOnload"`).
- CDN `max-age=31536000, immutable` on hashed files; `s-maxage=10` for slow-changing API data; `no-store` for live.
- Replace client-side aggregation with a pre-aggregated API procedure; Brotli at the ingress.

## Larger levers (days–weeks)

- Tune CDN cache per route; ISR for per-tenant-cached static cells; split dashboard into parallel routes with `loading.tsx`; server-side waterfall pre-computation (AI/ML + Architect).

# Part 2 — Pre-deploy audit gate

Run before merging any PR touching `apps/web/app/`, `apps/web/components/`, or chart code; before deploying a new route; when alerts fire; or when a customer says "the dashboard is slow" (start here, not in DevTools).

### 1. Lighthouse CI (gate on PR)

`treosh/lighthouse-ci-action` on PR to `apps/web/**` against staging URLs with `lighthouse-budget.json` (FCP 1500ms, LCP 2000ms, speed-index 2500ms, interactive 3000ms; script 100KB, total 600KB). **PR fails if budget exceeded** — fix or bump with reviewer approval.

### 2. RUM via `web-vitals` + your analytics tool

```typescript
useReportWebVitals((m) => {
  analytics.capture('web_vital', { name: m.name, value: m.value, rating: m.rating, route: location.pathname, tenant_id: getTenantId() });
});
```
"Web Vitals by route" in your analytics tool — p50/p75/p95 by route segment; alerts per the targets table (mirrored to your metrics backend via the BFF).

### 3. On-incident manual audit

```bash
pnpm dlx lighthouse https://staging.<product-domain>/dashboard --preset=desktop --only-categories=performance --output html --output-path /tmp/lhci.html
```
Look for: the **LCP element** (image→`priority`? chart on slow tRPC→`sql-query-optimization`? font→preload?); **TBT** (large chunks→bundle-analyzer); **CLS** source (images without dimensions, async charts without skeleton).

### Audit checklist

- [ ] Baseline measured (Lighthouse CI + RUM) · [ ] LCP element identified · [ ] Bundle analyzer run (no chunk >500 KB gz, route JS <100 KB gz) · [ ] No image without explicit width/height · [ ] CLS sources reviewed · [ ] Tested on slow-3G throttling AND a real mid-tier Android · [ ] Budget updated or PR fixes the regression.

## Wiring

| Concern | Owner |
|---|---|
| Dashboard perf + chart rendering | **Frontend Engineer** |
| PR-time Lighthouse gate / RUM | **Frontend Engineer** + **Platform/SRE** |
| BFF route latency (TTFB) | **Frontend Engineer** + **Backend Engineer** |
| CDN cache config | **Platform/SRE** |
| Analytical query speed (often the LCP bottleneck) | **AI/ML Engineer** |

Related: [`observability`] (alerts + RUM), [`frontend-web`] (broader playbook), [`sql-query-optimization`] (slow backend = slow LCP).

## 2026 market update

- **Partial Prerendering (PPR) + streaming Suspense** is a first-class lever — static shell delivered instantly, dynamic content streamed in (verify GA status in your Next version before treating as default-on).
- **Rust bundlers** (Vite/Rolldown, Turbopack default in Next) for build-time budgets; the **React Compiler** removes most manual memoization. INP-not-FID already covered here.
