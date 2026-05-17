---
name: web-performance-audit
description: Pre-deploy performance audit — Lighthouse run, Core Web Vitals snapshot, performance budget gate, RUM check. Use as a release gate before Ananya's web changes merge to main, when investigating a customer-reported "the dashboard is slow", or when LCP/INP/CLS alerts fire in PostHog/CloudWatch.
---

# Web Performance Audit

Brain's web dashboard cannot regress on perf silently. This skill is the **pre-deploy audit** for Ananya's PRs and the **incident-time triage** when PostHog alerts on a Core Web Vitals regression.

## When to run

- Before merging any PR that touches `apps/web/app/`, `apps/web/components/`, or chart code
- Before deploying a new dashboard route
- When PostHog alerts: LCP p75 > 2.5s for 24h, INP p75 > 300ms, CLS > 0.1
- When a customer says "the dashboard is slow" — start here, not in DevTools

## Core Web Vitals targets (Brain)

| Metric | Good | Needs work | Poor (alert) |
|---|---|---|---|
| LCP (Largest Contentful Paint) | <2.0s | 2.0–2.5s | >2.5s |
| INP (Interaction to Next Paint) | <200ms | 200–300ms | >300ms |
| CLS (Cumulative Layout Shift) | <0.05 | 0.05–0.1 | >0.1 |
| TTFB (BFF p95) | <200ms | 200–400ms | >400ms |
| FCP | <1.5s | 1.5–2.0s | >2.0s |

INP replaced FID as a Core Web Vital in March 2024. Brain measures INP, not FID.

## Audit pipeline

### 1. Lighthouse CI (gate on PR)

```yaml
# .github/workflows/lighthouse.yml — runs on PR to apps/web/**
- uses: treosh/lighthouse-ci-action@v11
  with:
    urls: |
      https://staging.brain.pipadacapital.com/dashboard
      https://staging.brain.pipadacapital.com/orders
      https://staging.brain.pipadacapital.com/cohorts
    budgetPath: ./apps/web/lighthouse-budget.json
    uploadArtifacts: true
```

```json
// apps/web/lighthouse-budget.json
{
  "timings": [
    { "metric": "first-contentful-paint",     "budget": 1500 },
    { "metric": "largest-contentful-paint",   "budget": 2000 },
    { "metric": "speed-index",                "budget": 2500 },
    { "metric": "interactive",                "budget": 3000 }
  ],
  "resourceSizes": [
    { "resourceType": "script",     "budget": 200 },
    { "resourceType": "stylesheet", "budget":  50 },
    { "resourceType": "image",      "budget": 300 },
    { "resourceType": "total",      "budget": 600 }
  ]
}
```

PR fails if budget is exceeded. Fix the regression or bump the budget with reviewer approval.

### 2. Real-user metrics (RUM) via web-vitals + PostHog

```typescript
// apps/web/app/layout.tsx
import { useReportWebVitals } from 'next/web-vitals';

useReportWebVitals((m) => {
  posthog.capture('web_vital', {
    name: m.name,
    value: m.value,
    rating: m.rating,           // good | needs-improvement | poor
    route: window.location.pathname,
    workspace_id: getWorkspaceId(),
  });
});
```

PostHog dashboard: **"Web Vitals by route"** — p50/p75/p95 grouped by route segment. Alert configured per the targets table above.

### 3. On-incident manual audit

```bash
# Local repro — Lighthouse mobile profile
pnpm dlx lighthouse https://staging.brain.pipadacapital.com/dashboard \
  --preset=desktop \
  --only-categories=performance \
  --output html --output-path /tmp/lhci.html

# Open the report
open /tmp/lhci.html
```

Look for:
- **Largest Contentful Paint element** — is it an image (mark `priority`)? A chart waiting on a slow tRPC call (sql-query-optimization)? A web font (preload it)?
- **Total Blocking Time** — large JS chunks blocking the main thread. Run `pnpm dlx @next/bundle-analyzer`.
- **Cumulative Layout Shift** — find which element jumps; usually images without `width`/`height` or async-loaded charts without skeleton.

## Optimization tiers

### Quick wins (hours)

- Add `priority` to LCP images
- Add `width`/`height` to all `<Image>` and `<img>`
- Convert heavy components to `dynamic()` with `ssr: false`
- Preload critical fonts in `app/layout.tsx`
- Defer PostHog / Sentry replay scripts (`strategy="lazyOnload"`)

### Medium (days)

- Code-split per route segment (already free in App Router — verify chunks)
- Replace any client-side aggregation with a tRPC procedure that returns pre-aggregated data
- Reduce hover-tooltip recomputes on Visx (memoize scales, throttle handlers)
- Tune CloudFront cache headers per route

### Large (weeks)

- Move static dashboard cells to ISR (Incremental Static Regeneration) where the data is per-brand-cached
- Replace SVG chart with `<canvas>` above 2k marks
- Split the dashboard route into parallel routes with `loading.tsx` boundaries
- Server-side waterfall pre-computation (Kabir + Aryan — that's a TECH/03 conversation)

## Audit checklist

- [ ] Baseline measured (Lighthouse CI + PostHog RUM)
- [ ] LCP element identified (image / chart / hero text)
- [ ] Bundle analyzer run; no chunk > 500 KB gz; total initial < 200 KB gz
- [ ] No `<img>` / `<Image>` without explicit width/height
- [ ] CLS sources reviewed (fonts, ads if any, charts)
- [ ] Tested on slow 3G connection (DevTools throttling — India-realistic)
- [ ] Tested on a real mid-tier Android device, not just iPhone
- [ ] Budget updated (or PR fixes the regression)
- [ ] PostHog alert thresholds reviewed for the affected route

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| PR-time Lighthouse gate | **Ananya** + **Jatin** | CI config |
| RUM dashboards + alerts | **Ananya** + **Jatin** | `observability` |
| BFF-side optimisations (TTFB) | **Vikram** | TECH/06 |
| ClickHouse query speed (often the LCP bottleneck) | **Kabir** | `sql-query-optimization` |

Related Brain skills: `web-performance-optimization` (the optimizations themselves), `observability` (alerts + RUM), `frontend-web`, `sql-query-optimization` (slow tRPC backend = slow LCP).
