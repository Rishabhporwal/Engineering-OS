---
name: frontend-web
description: Brain's Next.js 14 web stack — App Router + tRPC client + Redux Toolkit + TanStack Query + nuqs + shadcn/ui + Tailwind + Recharts + Visx. Use whenever Ananya is building the web workbench: dashboard pages, KPI cards with RAG, CM Waterfall (Visx), Cohort heatmap (Visx), First Product Cascade table, Calendar Report with marketing-action overlays, drill-down drawers. Covers state ownership split (Redux / URL state / TanStack / Auth / Forms), Server Components, Indian numbering format, accessibility, Core Web Vitals.
---

# Frontend Web — Next.js 14 + tRPC + Redux + TanStack + nuqs + shadcn + Visx

The web stack for Brain's **workbench surface** — Ananya's domain. Web is the desktop surface operators use for Monday review + on-demand depth. Mobile is the daily heartbeat (Karan owns it).

## Stack invariants (LOCKED — TECH/07)

| Layer | Choice | Reason |
|---|---|---|
| Framework | **Next.js 14+ App Router**, TypeScript strict | Server Components for heavy dashboards |
| Edge API | **tRPC client** via `@trpc/react-query` | Typed end-to-end with api-gateway |
| Server state | **TanStack Query** (via tRPC) | Cache + staleness + invalidation |
| Client state | **Redux Toolkit** + redux-persist (whitelist `workspace` + `ui`) | UI prefs + active workspace persistence |
| URL state | **nuqs** | Filters, date ranges (shareable links + back-button) |
| Auth | Supabase Auth (httpOnly cookie) | Never in JS |
| Forms | **React Hook Form + Zod** | Same validation as backend |
| UI | **shadcn/ui + Tailwind** | Owned primitives; design tokens shared with mobile Tamagui |
| Charts (90%) | **Recharts** | Easy axes, time-series, bar/line/area |
| Charts (specialty) | **Visx** | CM Waterfall, Cohort heatmap, custom drill layouts |
| Icons | Lucide | |
| Font | Inter; dark-mode-first | |
| Date | date-fns + date-fns-tz (`Asia/Kolkata`) | IST handling for India workspaces |
| Currency | `packages/lib-formatters` — Indian numbering (`₹4,82,000`) | NEVER `₹482,000` |
| Unit tests | Vitest + RTL | |
| E2E | **Cypress** (critical journeys) | |
| Deploy | AWS Amplify or EKS (SSR) — Jatin owns | |

## State ownership rules (NON-NEGOTIABLE)

| What | Where | Why |
|---|---|---|
| Active `workspace_id` | Redux `workspace.activeId` (persisted) | Cross-page; survives reload |
| Date range, filters | URL via nuqs | Shareable + back-button-friendly |
| Sidebar / theme / drawer open | Redux `ui.*` (persisted) | UI prefs |
| Server data | TanStack Query | Caching + invalidation |
| Auth session | httpOnly cookie | XSS-safe |
| Form state | React Hook Form (local) | Don't pollute Redux |

If you reach for Zustand or Jotai — stop. Brain doesn't use them.

## Server Component pattern (default for heavy reads)

```tsx
// app/(dashboard)/[workspace]/store/page.tsx
import { trpcServer } from '@/lib/trpc/server';

export default async function StorePage({ params }: { params: { workspace: string } }) {
  // Server-side fetch — no client JS for initial paint
  const kpis = await trpcServer.store.kpis({
    from: subDays(new Date(), 30),
    to: new Date(),
  });
  return <StoreKpis initialData={kpis} />;  // hydrate into client component
}
```

```tsx
// components/StoreKpis.tsx  (client component)
'use client';
import { trpc } from '@/lib/trpc/client';

export function StoreKpis({ initialData }: Props) {
  const { data } = trpc.store.kpis.useQuery(
    { from, to },
    { initialData, staleTime: 60_000 }
  );
  // ...
}
```

## Empty / loading / error pattern (mandatory)

```tsx
if (isLoading) return <Skeleton variant="kpi-card" />;
if (error)    return <ErrorCard message={error.message} retry={refetch} />;
if (!data?.metrics?.length) return <EmptyState title="No data yet" />;
return <KpiCard {...data.metrics[0]} />;
```

Every interactive element gets `data-testid` for Cypress.

## RAG (Red/Amber/Green) on every metric card

Per `docs/TECH/03_metrics_engine.md` §goals:

```tsx
<RagCell
  metric="mer"
  actual={3.2}
  goal={3.5}
  goalType="minimum"  // higher = better
  // thresholds: green ≥ goal*0.95, amber ≥ goal*0.80, red < goal*0.80
/>
```

Calendar Report (TECH/03) renders every cell with RAG. CSV exports preserve raw values + RAG metadata.

## CM Waterfall — Visx

```tsx
// components/charts/Waterfall.tsx
import { BarStack } from '@visx/shape';
import { Group } from '@visx/group';
// ... layered horizontal step-down per the spec in BRAIN_REQUIREMENTS.md §P2.5
```

Filter: `[All | New Customers | Returning Customers]`. The "wow" demo moment is showing the loss-making-new vs profitable-returning pattern.

## Indian numbering format (Brain invariant)

```tsx
import { formatINR } from '@brain/formatters';

formatINR(482000n)   // → "₹4,82,000"   ✓
formatINR(48200000n) // → "₹4,82,00,000" ✓
// Never use Intl.NumberFormat('en-IN') directly — it returns "₹4,82,000" but not consistent across Node versions for big-int.
```

## Desktop-only territory (mobile shows "Open in browser →")

These views don't translate to mobile:
- Cohort heatmap (24×36 matrix)
- CM Waterfall (filter dimensions + drill cells)
- First Product Cascade table
- Settings → Costs / COGS bulk editor
- Settings → Campaign Classifications bulk view
- Plan Module spend plan editor
- CSV / XLSX exports

```tsx
// components/MobileFallback.tsx
<EmptyState
  title="This view works best on desktop"
  cta={<Link href="https://brain.pipadacapital.com/...">Open in browser →</Link>}
/>
```

## Performance targets (TECH/07)

- Lighthouse > 80 on every dashboard route
- p95 < 500ms server-rendered initial paint
- First Contentful Paint < 1s on Wi-Fi
- Skeleton placeholders for any query > 200ms

## Path layout

```
apps/frontend/
  app/(dashboard)/[workspace]/<route>/page.tsx
  components/charts/{Waterfall,CohortHeatmap,KpiCard,TimeSeriesChart}.tsx
  components/drilldown/{OrdersDrawer,CampaignsDrawer}.tsx
  components/rag/{RagCell,RagBadge}.tsx
  lib/trpc/{client,server}.ts
  lib/store/slices/{workspace,ui}.ts
```

## Common pitfalls

- **Arbitrary exports from `route.ts`**: App Router HTTP-verb handlers only. Constants and helpers MUST live in `lib/`. Detection: `next build` fails with `"<NAME>" is not a valid Route export field`.
- **Token in DOM / non-httpOnly cookie**: XSS exfiltration. Always `httpOnly + sameSite=lax + secure`.
- **Indian numbering format mismatch**: `₹482,000` (wrong) vs `₹4,82,000` (right). Use the formatter.
- **Recharts on waterfall / heatmap**: doesn't bend that way. Use Visx.
- **State scope violation**: filters in Redux → broken back button; filters in URL → broken cross-page persistence. Follow the table.

## References

- `docs/TECH/07_frontend_architecture.md` — design system + BFF + multi-currency
- `docs/TECH/03_metrics_engine.md` — KPI definitions + RAG + Calendar Report
- `docs/BRAIN_REQUIREMENTS.md` §P2 — every wedge feature's UI spec
- `skills/india-commerce-economics/SKILL.md` §currency-format — numbering + GST display
- `skills/testing-tdd/SKILL.md` — Vitest + RTL + Cypress patterns
