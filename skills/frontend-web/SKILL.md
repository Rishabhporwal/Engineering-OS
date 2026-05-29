---
name: frontend-web
description: Brain's Next.js 16 web workbench — App Router, tRPC, Redux/TanStack/nuqs split, shadcn/Tailwind, Recharts+Visx, Server Components/Actions, Indian numbering.
---

# Frontend Web — Next.js 16 + tRPC + Redux + TanStack + nuqs + shadcn + Visx

The web stack for Brain's workbench surface — Ananya's domain. Web is the desktop surface operators use for Monday review + on-demand depth; mobile is the daily heartbeat ([`mobile-surface`] / [`morning-brief-mobile`]).

## Stack invariants (LOCKED — canon/TECH/07)

| Layer | Choice | Reason |
|---|---|---|
| Framework | **Next.js 16 App Router**, TS strict (React 19) | Server Components for heavy dashboards; **Turbopack default + React Compiler stable** (auto-memoization — most manual `useMemo`/`useCallback` optional) |
| Edge API | **tRPC client** via `@trpc/react-query` | Typed end-to-end with api-gateway |
| Server state | **TanStack Query** (via tRPC) | Cache + staleness + invalidation |
| Client state | **Redux Toolkit** + redux-persist (whitelist `workspace`+`ui`) | UI prefs + active workspace |
| URL state | **nuqs** | Filters, date ranges (shareable + back-button) |
| Auth | Supabase Auth (httpOnly cookie) | Never in JS |
| Forms | **React Hook Form + Zod** | Same validation as backend |
| UI | **shadcn/ui + Tailwind** | Owned primitives; tokens shared with mobile Tamagui |
| Charts (90%) | **Recharts** | Time-series, bar/line/area |
| Charts (specialty) | **Visx** | CM Waterfall, cohort heatmap, custom drill |
| Date | date-fns + date-fns-tz (`Asia/Kolkata`) | IST for India workspaces |
| Currency | `packages/lib-formatters` — Indian numbering (`₹4,82,000`) | NEVER `₹482,000` |
| E2E | **Playwright** (critical journeys) | Cross-browser, auto-wait, trace viewer |
| Unit | Vitest + RTL | |

## State ownership rules (NON-NEGOTIABLE)

| What | Where | Why |
|---|---|---|
| Active `workspace_id` | Redux `workspace.activeId` (persisted) | Cross-page; survives reload |
| Date range, filters | URL via nuqs | Shareable + back-button |
| Sidebar / theme / drawer | Redux `ui.*` (persisted) | UI prefs |
| Server data | TanStack Query | Caching + invalidation |
| Auth session | httpOnly cookie | XSS-safe |
| Form state | React Hook Form (local) | Don't pollute Redux |

Reaching for Zustand or Jotai — stop. Brain doesn't use them.

## Magic UI (scoped)

Magic UI = animated React components, **copy-paste like shadcn** (own the code in `packages/ui`; zero runtime dep; same Tailwind tokens). **Scoped-use rule (NON-NEGOTIABLE):** adopt only on **marketing / onboarding / login / empty-state / "delight"** surfaces — **NOT the dense operator workbench** (P&L, CM Waterfall, cohort heatmap, Calendar Report, KPI grids, drill drawers stay shadcn + Visx/Recharts under the perf budget). Animation on a 2,250-cell Calendar Report or a cohort heatmap is a perf regression, not delight. Guardrails: copy into `packages/ui`; respect `prefers-reduced-motion`; stay within the perf budget (lazy-load heavy animated components via `next/dynamic`); WCAG AA.

## Server Component pattern (default for heavy reads)

```tsx
// app/(dashboard)/[workspace]/store/page.tsx
export default async function StorePage({ params }) {
  const kpis = await trpcServer.store.kpis({ from: subDays(new Date(), 30), to: new Date() });
  return <StoreKpis initialData={kpis} />;   // hydrate into client component
}
```
```tsx
'use client';
export function StoreKpis({ initialData }) {
  const { data } = trpc.store.kpis.useQuery({ from, to }, { initialData, staleTime: 60_000 });
}
```

## Server Actions pattern (default for writes — React 19)

For mutations, React 19 Server Actions + `useActionState`/`useOptimistic` are the idiomatic write path — the action runs server-side and calls the tRPC server caller (api-gateway BFF stays the contract).

```tsx
'use server';
export async function updateCogs(prev, formData) {
  const res = await trpcServer.costs.updateCogs({ /* Zod-validated */ });
  return { ok: true, value: res };
}
```
```tsx
'use client';
export function CogsForm({ initial }) {
  const [state, formAction, pending] = useActionState(updateCogs, { ok: false });
  const [optimistic, setOptimistic] = useOptimistic(initial);
}
```
Mutations still write the Decision Log + `requireRole` server-side — a Server Action is transport, not a bypass.

## Empty / loading / error pattern (mandatory)

```tsx
if (isLoading) return <Skeleton variant="kpi-card" />;
if (error)    return <ErrorCard message={error.message} retry={refetch} />;
if (!data?.metrics?.length) return <EmptyState title="No data yet" />;
return <KpiCard {...data.metrics[0]} />;
```
Every interactive element gets `data-testid` for Playwright.

## RAG on every metric card

```tsx
<RagCell metric="mer" actual={3.2} goal={3.5} goalType="minimum"
  // green ≥ goal*0.95, amber ≥ goal*0.80, red < goal*0.80
/>
```
Calendar Report renders every cell with RAG; CSV exports preserve raw values + RAG metadata. (Detail in [`kpi-dashboard-design`].)

## CM Waterfall — Visx

```tsx
import { BarStack } from '@visx/shape'; import { Group } from '@visx/group';
// layered horizontal step-down per canon/business-requirements.md
```
Filter `[All | New | Returning]`. The "wow" demo: loss-making-new vs profitable-returning.

## Indian numbering format (Brain invariant)

```tsx
formatINR(482000n)   // "₹4,82,000"  ✓
formatINR(48200000n) // "₹4,82,00,000" ✓
// Never Intl.NumberFormat('en-IN') directly — inconsistent for bigint across Node versions.
```

## Desktop-only territory (mobile shows "Open in browser →")

Cohort heatmap (24×36), CM Waterfall, First Product Cascade, Costs/COGS bulk editor, Campaign Classifications bulk view, Plan spend editor, CSV/XLSX exports.
```tsx
<EmptyState title="This view works best on desktop" cta={<Link href="https://brain.pipadacapital.com/...">Open in browser →</Link>} />
```

## Performance targets (perf budget — CI-gated, see [`web-performance`])

- **LCP < 2s · INP < 200ms · CLS < 0.1 · route JS < 100KB gz**
- Cached dashboard p95 < 500ms SSR initial paint; FCP < 1s on Wi-Fi; WCAG AA every route; skeletons for any query > 200ms.

## Path layout

```
apps/frontend/app/(dashboard)/[workspace]/<route>/page.tsx
  components/charts/{Waterfall,CohortHeatmap,KpiCard,TimeSeriesChart}.tsx
  components/drilldown/{OrdersDrawer,CampaignsDrawer}.tsx · components/rag/{RagCell,RagBadge}.tsx
  lib/trpc/{client,server}.ts · lib/store/slices/{workspace,ui}.ts
```

## Common pitfalls

- Arbitrary exports from `route.ts` (HTTP-verb handlers only; helpers in `lib/`) → `next build` fails.
- Token in DOM / non-httpOnly cookie → XSS. Always `httpOnly + sameSite=lax + secure`.
- `₹482,000` vs `₹4,82,000` — use the formatter; Recharts on waterfall/heatmap (use Visx); state-scope violation (filters in Redux breaks back-button; in URL breaks cross-page persistence).

## References

- canon/TECH/07 — design system + BFF + multi-currency + KPI/RAG/Calendar Report
- canon/business-requirements.md — each wedge feature's UI spec
- [`india-commerce-economics`] §currency-format · [`testing-tdd`] · [`kpi-dashboard-design`] · [`web-performance`] · [`accessibility`]
