---
name: frontend-web
description: A web-stack reference implementation — Next.js App Router, typed edge API, server/client/URL state split, component library, Server Components/Actions, locale-aware formatting.
---

# Frontend Web — Next.js + typed edge API + Redux + TanStack + nuqs + shadcn + Visx

> **Reference implementation.** This skill documents one concrete binding of the web seam (see
> `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's
> `STACK.md` may bind this seam to different technology. The *patterns* here (state-ownership split,
> Server Components for heavy reads, locale-aware money, the perf budget) are what transfer.

A web stack for the workbench/desktop surface owned by the **Frontend/Web Engineer**. Web is the desktop surface for review + on-demand depth; a separate mobile surface ([`mobile-surface`]) carries the daily flow.

## Stack invariants (as bound in `STACK.md`)

| Layer | Choice | Reason |
|---|---|---|
| Framework | **Next.js App Router**, TS strict (React 19) | Server Components for heavy dashboards; **Turbopack + React Compiler** (auto-memoization — most manual `useMemo`/`useCallback` optional) |
| Edge API | **typed client** (e.g. tRPC via `@trpc/react-query`) | Typed end-to-end with the edge gateway |
| Server state | **TanStack Query** | Cache + staleness + invalidation |
| Client state | **Redux Toolkit** + redux-persist (whitelist `tenant`+`ui`) | UI prefs + active tenant |
| URL state | **nuqs** | Filters, date ranges (shareable + back-button) |
| Auth | provider session (httpOnly cookie) | Never in JS |
| Forms | **React Hook Form + Zod** | Same validation as backend |
| UI | **shadcn/ui + Tailwind** | Owned primitives; tokens shared with mobile |
| Charts (90%) | **Recharts** | Time-series, bar/line/area |
| Charts (specialty) | **Visx** | Waterfalls, heatmaps, custom drill |
| Date | date-fns + date-fns-tz | Locale/timezone via the region adapter |
| Currency | a shared formatter lib (locale-aware) | Format from minor units + `currency_code`; never hardcode a symbol/grouping |
| E2E | **Playwright** (critical journeys) | Cross-browser, auto-wait, trace viewer |
| Unit | Vitest + RTL | |

## State ownership rules (NON-NEGOTIABLE)

| What | Where | Why |
|---|---|---|
| Active tenant key | Redux `tenant.activeId` (persisted) | Cross-page; survives reload |
| Date range, filters | URL via nuqs | Shareable + back-button |
| Sidebar / theme / drawer | Redux `ui.*` (persisted) | UI prefs |
| Server data | TanStack Query | Caching + invalidation |
| Auth session | httpOnly cookie | XSS-safe |
| Form state | React Hook Form (local) | Don't pollute Redux |

Reaching for another global-state lib not in `STACK.md` — stop. Match what the product already uses.

## Animated-component libraries (scoped)

Animated React component kits are **copy-paste like shadcn** (own the code; zero runtime dep; same Tailwind tokens). **Scoped-use rule (NON-NEGOTIABLE):** adopt only on **marketing / onboarding / login / empty-state / "delight"** surfaces — **NOT the dense operator workbench** (data tables, waterfalls, heatmaps, KPI grids, drill drawers stay shadcn + Visx/Recharts under the perf budget). Animation on a large data grid or a heatmap is a perf regression, not delight. Guardrails: own the copied code in your UI package; respect `prefers-reduced-motion`; stay within the perf budget (lazy-load heavy animated components via `next/dynamic`); WCAG AA.

## Server Component pattern (default for heavy reads)

```tsx
// app/(dashboard)/[tenant]/store/page.tsx
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

For mutations, React 19 Server Actions + `useActionState`/`useOptimistic` are the idiomatic write path — the action runs server-side and calls the server-side caller (the edge gateway stays the contract).

```tsx
'use server';
export async function updateCosts(prev, formData) {
  const res = await trpcServer.costs.update({ /* Zod-validated */ });
  return { ok: true, value: res };
}
```
```tsx
'use client';
export function CostsForm({ initial }) {
  const [state, formAction, pending] = useActionState(updateCosts, { ok: false });
  const [optimistic, setOptimistic] = useOptimistic(initial);
}
```
Mutations still write the system-of-record audit entry + check the role server-side — a Server Action is transport, not a bypass.

## Empty / loading / error pattern (mandatory)

```tsx
if (isLoading) return <Skeleton variant="kpi-card" />;
if (error)    return <ErrorCard message={error.message} retry={refetch} />;
if (!data?.metrics?.length) return <EmptyState title="No data yet" />;
return <KpiCard {...data.metrics[0]} />;
```
Every interactive element gets `data-testid` for Playwright.

## RAG status on every metric card

```tsx
<RagCell metric="conversion" actual={3.2} goal={3.5} goalType="minimum"
  // green ≥ goal*0.95, amber ≥ goal*0.80, red < goal*0.80
/>
```
A status grid renders every cell with RAG; CSV exports preserve raw values + RAG metadata. RAG is never colour-only ([`accessibility`]). (Detail in [`kpi-dashboard-design`].)

## A step-down waterfall — Visx

```tsx
import { BarStack } from '@visx/shape'; import { Group } from '@visx/group';
// layered horizontal step-down driven by the metric registry
```
Filters drive the cut. The "wow" demo: surfacing a counter-intuitive breakdown.

## Locale-aware money & numbers

```tsx
formatMoney(482000n, currencyCode, locale)   // formatted from minor units + currency_code + locale
// Never hardcode a currency symbol or grouping; the region adapter supplies locale.
```
Money is integer **minor units** + a `currency_code`; the formatter renders per locale ([`region-and-locale`]).

## Desktop-only territory (mobile shows "Open in browser →")

Large heatmaps, multi-step waterfalls, bulk editors, bulk classification views, CSV/XLSX exports.
```tsx
<EmptyState title="This view works best on desktop" cta={<Link href="/...">Open in browser →</Link>} />
```

## Performance targets (perf budget — CI-gated, see [`web-performance`])

- **LCP < 2s · INP < 200ms · CLS < 0.1 · route JS < 100KB gz**
- Cached dashboard p95 < 500ms SSR initial paint; FCP < 1s; WCAG AA every route; skeletons for any query > 200ms.

## Path layout

```
apps/frontend/app/(dashboard)/[tenant]/<route>/page.tsx
  components/charts/{Waterfall,Heatmap,KpiCard,TimeSeriesChart}.tsx
  components/drilldown/{OrdersDrawer,CampaignsDrawer}.tsx · components/rag/{RagCell,RagBadge}.tsx
  lib/trpc/{client,server}.ts · lib/store/slices/{tenant,ui}.ts
```

## Common pitfalls

- Arbitrary exports from `route.ts` (HTTP-verb handlers only; helpers in `lib/`) → `next build` fails.
- Token in DOM / non-httpOnly cookie → XSS. Always `httpOnly + sameSite=lax + secure`.
- Hardcoding a currency symbol/grouping — use the locale-aware formatter; Recharts where Visx belongs (waterfall/heatmap); state-scope violation (filters in Redux breaks back-button; in URL breaks cross-page persistence).

## References

- Product Canon design-system + edge-API + KPI/RAG section
- [`region-and-locale`] §currency-format · [`testing-tdd`] · [`kpi-dashboard-design`] · [`web-performance`] · [`accessibility`]

## 2026 market update

- **Styling:** Tailwind **v4** (CSS-first config, no `tailwind.config.js`, Oxide engine) + **shadcn/ui** (own-the-code on Radix) is the de-facto standard; runtime CSS-in-JS (styled-components/Emotion) is in decline (RSC-incompatible).
- **Validation:** **Zod v4** + **Standard Schema** (Zod/Valibot/ArkType interop into React Hook Form / TanStack Form / tRPC). State: **TanStack Query** (server-state) + **Zustand** (the lighter client-state default many teams now pick over Redux Toolkit).
- **React Compiler 1.0** auto-memoizes — manual `useMemo`/`useCallback` is opt-in for profiler-confirmed hot paths.
- **Alternatives callout:** RSC is **Next-standard, not React-standard** — Vite + **TanStack Start** / **React Router v7** / **Astro** are valid non-Next bindings via `STACK.md`. Build tooling went Rust (Vite→Rolldown, Turbopack).
- **AI surfaces** → `ai-streaming-ui` (Vercel AI SDK + assistant-ui).
