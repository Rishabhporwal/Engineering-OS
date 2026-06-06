# TECH/07 — Web Frontend Architecture

> **v2.0 reconciliation — authority:** `00_tech_stack_decision.md` + `../technical-requirements.md`. Canonical: money = integer **minor units**; roles = Owner/Operator/Analyst/Agency/Viewer; bill on **realized GMV**; India **GST 2.0 = 0/5/18/40** per-SKU; **GCC VAT per-country** (KSA 15 / UAE 5 / BH 10 / OM 5); **India-first** (UAE/GCC Phase 4); compliance → `16_compliance_engine.md`; billing → `15_billing_metering.md`.

**Owner:** E2 (Web Frontend) | **Reviewers:** E1, E5
**Companion:** [technical-requirements.md](../technical-requirements.md), [TECH/06_api_contracts.md](06_api_contracts.md), [TECH/10_mobile_architecture.md](10_mobile_architecture.md) (mobile is a separate codebase)

This document specifies the **web (Next.js)** frontend. Mobile (React Native + Expo) is covered in [TECH/10](10_mobile_architecture.md). Shared code lives in `packages/` and is consumed by both surfaces.

Scope:
- Next.js App Router structure
- BFF pattern via api-gateway (frontend never talks directly to backend services)
- Data fetching: Server Components + tRPC
- State management
- Charts and design system
- Multi-currency, multi-region UI
- AWS hosting via CloudFront + Amplify (or self-hosted on EKS)
- Performance budget at scale

**Mandate:** Brain's web UI is the wedge against incumbent dashboards. Notion-level polish, Linear-level speed. The primary surface for deep analytics work — mobile is complementary, not a replacement.

**Shared with mobile (in `packages/`):** types, Redux slices, formatters (`packages/lib-formatters`), tRPC client setup, validation schemas. NOT shared: UI primitives (shadcn for web vs Tamagui for mobile), routing (App Router vs Expo Router), charts (Recharts/Visx vs Victory Native).

---

## 1. Framework: Next.js 16+ App Router

Hosted as a containerized app on EKS (with Karpenter for auto-scaling), fronted by CloudFront. Static assets and images cached at edge.

Alternative: AWS Amplify Hosting for the frontend if EKS feels like overkill. CloudFront-backed; auto-deploys from main. Lower ops cost; less control. Phase 0 = Amplify; migrate to EKS at scale if needed.

### Why App Router

- Server Components for fast initial paint on data-heavy dashboards
- Streaming SSR — show shell + skeletons immediately
- Nested layouts (workspace shell wraps every dashboard route)
- Per-route loading.tsx + error.tsx

### File Tree

```
apps/web/
├── app/
│   ├── layout.tsx                    # Root: providers, fonts, theme
│   ├── page.tsx                      # / → redirect based on auth state
│   ├── globals.css                   # Tailwind + design tokens
│   │
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── invite/[token]/page.tsx
│   │
│   ├── (onboarding)/
│   │   ├── create-workspace/page.tsx
│   │   └── connect/[integration]/page.tsx
│   │
│   ├── (workspace)/                  # Workspace-scoped routes
│   │   ├── layout.tsx                # Shell with sidebar + topbar
│   │   ├── loading.tsx
│   │   │
│   │   ├── page.tsx                  # Dashboard
│   │   │
│   │   ├── analytics/
│   │   │   ├── store/page.tsx
│   │   │   ├── pnl/page.tsx
│   │   │   ├── products/
│   │   │   ├── ltv/page.tsx
│   │   │   ├── cohorts/page.tsx
│   │   │   ├── acquisition/page.tsx
│   │   │   ├── distributions/page.tsx
│   │   │   ├── timing/page.tsx
│   │   │   └── inventory/page.tsx
│   │   │
│   │   ├── calendar/page.tsx
│   │   ├── waterfall/page.tsx
│   │   ├── customers/
│   │   │   ├── page.tsx              # NAC report
│   │   │   └── [customerId]/page.tsx
│   │   │
│   │   ├── regional/                 # Region-specific tabs (India + future US)
│   │   │   ├── pincodes/page.tsx     # IN only
│   │   │   ├── rto/page.tsx          # IN only
│   │   │   ├── ndr/page.tsx          # IN only
│   │   │   ├── cod-economics/page.tsx # IN only
│   │   │   ├── chargebacks/page.tsx  # US only
│   │   │   └── states-tax/page.tsx   # US only
│   │   │
│   │   ├── ai/
│   │   │   ├── insights/page.tsx
│   │   │   └── chat/page.tsx
│   │   │
│   │   ├── plan/page.tsx
│   │   ├── alerts/page.tsx
│   │   │
│   │   └── settings/
│   │       ├── general/page.tsx
│   │       ├── team/page.tsx
│   │       ├── integrations/
│   │       ├── costs/page.tsx
│   │       ├── product-cogs/page.tsx
│   │       ├── campaign-classifications/page.tsx
│   │       ├── goals/page.tsx
│   │       └── alerts/page.tsx
│   │
│   ├── (admin)/                      # Brain team
│   │   └── admin/
│   │
│   └── api/                          # Route handlers (proxies to api-gateway)
│       ├── trpc/[trpc]/route.ts      # tRPC client → api-gateway HTTPS
│       ├── webhooks/[...path]/route.ts
│       └── auth/callback/route.ts
│
├── components/                        # App-specific components
├── lib/                              # Frontend utilities (not in packages/)
├── public/
└── next.config.js
```

### Region-Aware Routing

Regional pages conditionally render based on `workspace.home_region`:

```typescript
// app/(workspace)/regional/pincodes/page.tsx
import { redirect } from "next/navigation";
import { createCaller } from "@/server/trpc";

export default async function PincodesPage() {
  const caller = await createCaller();
  const workspace = await caller.workspace.current();

  if (workspace.home_region !== 'IN') {
    redirect('/regional');  // generic regional landing page
  }

  return <PincodeView workspaceId={workspace.id} />;
}
```

Sidebar dynamically filters region-specific links based on current workspace's region.

---

## 2. Hosting on AWS

### Option A: AWS Amplify (Phase 0–2)

- Auto-deploy from `main`
- CloudFront-backed; SSR via Lambda@Edge
- Minimal ops overhead
- $0.01/build-minute; $0.15/GB-served (CloudFront pricing)
- Sufficient up to ~100k req/min

### Option B: EKS Container (Phase 3+)

- Next.js standalone build in a container
- Deployed to EKS alongside backend services
- ALB-fronted; CloudFront in front of ALB for caching
- Better cost control + same infra as backend
- Migration: containerize, deploy, switch DNS

We start with **Amplify Hosting** for speed. Migrate to EKS when:
- Build minutes exceed budget
- We need fine-grained ISR / edge config
- Bundle / SSR latency becomes a concern

### CloudFront Config

- **Static assets** (`/_next/static/*`): `Cache-Control: public, max-age=31536000, immutable`
- **Images** (`/_next/image/*`): cached based on transformation key
- **HTML routes:** dynamic; no caching at edge (auth-aware)
- **API proxy** (`/api/trpc/*`): no caching; pass-through to backend
- **Behaviors:** WAF rate-limit + bot protection enabled

---

## 3. Data Fetching Pattern

### Server Components: Default Path

```typescript
// app/(workspace)/analytics/store/page.tsx (Server Component)
import { createCaller } from "@/server/trpc";

export default async function StorePage({ searchParams }: PageProps) {
  const caller = await createCaller();
  const { from, to } = parseDateRange(searchParams);

  const kpis = await caller.store.kpis({ from, to, compareTo: 'previous_period' });

  return (
    <PageShell title="Store Analytics">
      <StoreKpiGrid kpis={kpis} />
      <StoreTrendChart from={from} to={to} />
    </PageShell>
  );
}
```

`createCaller()` instantiates a server-side tRPC client that calls api-gateway over HTTPS — same path the browser uses, but with auth context from cookies. No internal "shortcut" — keeps behavior identical between SSR and CSR.

### Client Components: For Interactive Charts/Filters

```typescript
'use client';
import { trpc } from "@/lib/trpc/client";

export function StoreTrendChart({ from, to }) {
  const { data, isLoading } = trpc.store.timeSeries.useQuery({
    from, to,
    metrics: ['revenue_net_minor', 'mer', 'amer'],
  });

  if (isLoading) return <ChartSkeleton />;
  return <LineChart data={data} />;
}
```

### Streaming for AI Chat

```typescript
'use client';
import { trpc } from "@/lib/trpc/client";

export function ChatUI() {
  const [conversationId, setConversationId] = useState<string>();
  const [streaming, setStreaming] = useState(false);

  trpc.ai.chatStream.useSubscription(
    { conversationId, message: pendingMessage },
    {
      enabled: streaming,
      onData(chunk) {
        if (chunk.type === 'content_chunk') appendToCurrentAssistantMessage(chunk.data);
        if (chunk.type === 'tool_call') showToolCallIndicator(chunk.data);
        if (chunk.type === 'done') setStreaming(false);
      },
    }
  );

  return <ChatPanel />;
}
```

Transport: WebSocket. api-gateway upgrades and bridges to intelligence-service gRPC bidi stream.

### Rule of Thumb

- **KPI cards, static tables:** Server Component
- **Interactive charts, filterable tables, forms:** Client Component
- **AI Chat:** Client Component with subscription
- **Calendar Report:** Server shell + Client cells (for click-to-drill)

---

## 4. State Management

### Server State: TanStack Query (via tRPC)

```typescript
const { data, isLoading } = trpc.products.firstProductCascade.useQuery({
  from: '2026-04-01', to: '2026-04-30', minCohortSize: 10,
});

const setClassification = trpc.settings.campaignClassifications.set.useMutation({
  onSuccess: () => utils.acquisition.kpis.invalidate(),
});
```

Defaults:
- `staleTime`: 60 seconds
- `gcTime`: 5 minutes
- Auto-refetch on window focus: ON for dashboards

### URL State: nuqs

Date range, filters, comparison period live in URL params:

```typescript
import { useQueryStates } from "nuqs";

const [filters, setFilters] = useQueryStates({
  from: { defaultValue: '2026-04-01' },
  to: { defaultValue: '2026-04-30' },
  customerType: { defaultValue: 'all' },
});
```

### Local / App State: Redux Toolkit

Redux Toolkit (RTK) is the canonical Redux pattern: `createSlice` removes boilerplate, the store is fully type-safe, and Redux DevTools (time-travel debugging, action replay) come free. Used for UI state, AI chat session state, multi-step form state, optimistic update tracking, and any cross-component state that doesn't belong in the URL or server cache.

**Three-layer state separation:**

| Layer | Tool | Examples |
|-------|------|----------|
| Server state | TanStack Query (via tRPC) | Daily metrics, products, customers, alerts feed |
| URL state | nuqs | Date range, filters, comparison period, active tab |
| Client/app state | **Redux Toolkit** | Sidebar collapsed, theme, density, AI panel toggle, current chat conversation, optimistic updates, drill-down drawer state |

**Why this split (not RTK Query for server state):** tRPC's auto-generated `useQuery()` / `useMutation()` hooks give us end-to-end type inference for every API call without writing endpoint definitions twice. Replacing TanStack Query with RTK Query would either lose tRPC's type inference or require maintaining parallel definitions. Three layers, three best-fit tools.

#### Store Setup

```typescript
// lib/store/index.ts
import { configureStore, combineReducers } from "@reduxjs/toolkit";
import { persistReducer, persistStore } from "redux-persist";
import storage from "redux-persist/lib/storage";

import uiReducer from "./slices/uiSlice";
import chatReducer from "./slices/chatSlice";
import drilldownReducer from "./slices/drilldownSlice";

const rootReducer = combineReducers({
  ui: uiReducer,
  chat: chatReducer,
  drilldown: drilldownReducer,
});

// Persist only UI preferences (theme, density, sidebar). Chat + drill-down are ephemeral.
const persistedReducer = persistReducer(
  { key: "brain", storage, whitelist: ["ui"] },
  rootReducer
);

export const makeStore = () =>
  configureStore({
    reducer: persistedReducer,
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: {
          // redux-persist + RTK streaming actions emit non-serializable internals
          ignoredActions: ["persist/PERSIST", "persist/REHYDRATE", "chat/streamChunkReceived"],
        },
      }),
    devTools: process.env.NODE_ENV !== "production",
  });

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
```

#### Typed Hooks

```typescript
// lib/store/hooks.ts
import { useDispatch, useSelector, type TypedUseSelectorHook } from "react-redux";
import type { RootState, AppDispatch } from "./index";

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
```

#### Example Slice

```typescript
// lib/store/slices/uiSlice.ts
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface UiState {
  sidebarCollapsed: boolean;
  density: "comfortable" | "compact";
  theme: "light" | "dark" | "system";
  aiPanelOpen: boolean;
}

const initialState: UiState = {
  sidebarCollapsed: false,
  density: "comfortable",
  theme: "system",
  aiPanelOpen: false,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },
    setDensity: (state, action: PayloadAction<UiState["density"]>) => {
      state.density = action.payload;
    },
    setTheme: (state, action: PayloadAction<UiState["theme"]>) => {
      state.theme = action.payload;
    },
    toggleAiPanel: (state) => {
      state.aiPanelOpen = !state.aiPanelOpen;
    },
  },
});

export const { toggleSidebar, setDensity, setTheme, toggleAiPanel } = uiSlice.actions;
export default uiSlice.reducer;
```

#### SSR-Safe Provider (Next.js App Router)

A fresh store is created per request on the server; the client rehydrates into its own instance. Avoids cross-request state leakage.

```typescript
// lib/store/StoreProvider.tsx
"use client";
import { useRef } from "react";
import { Provider } from "react-redux";
import { makeStore, type AppStore } from "./index";

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const storeRef = useRef<AppStore | null>(null);
  if (!storeRef.current) storeRef.current = makeStore();
  return <Provider store={storeRef.current}>{children}</Provider>;
}
```

Wired in the root layout:

```typescript
// app/layout.tsx
import { StoreProvider } from "@/lib/store/StoreProvider";
import { TrpcProvider } from "@/lib/trpc/Provider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <StoreProvider>
          <TrpcProvider>{children}</TrpcProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
```

#### Usage in Components

```typescript
"use client";
import { useAppSelector, useAppDispatch } from "@/lib/store/hooks";
import { toggleSidebar } from "@/lib/store/slices/uiSlice";

export function SidebarToggle() {
  const collapsed = useAppSelector((s) => s.ui.sidebarCollapsed);
  const dispatch = useAppDispatch();
  return (
    <button onClick={() => dispatch(toggleSidebar())} aria-label={collapsed ? "Expand" : "Collapse"}>
      {collapsed ? "›" : "‹"}
    </button>
  );
}
```

#### Slice Inventory (Phase 1)

| Slice | Persisted | Purpose |
|-------|-----------|---------|
| `ui` | yes | Sidebar, theme, density, AI panel |
| `chat` | no | Active conversation id, streaming buffer, tool-call indicators |
| `drilldown` | no | Open drawer state — which metric, which date, page in result set |
| `optimistic` | no | Pending mutations awaiting server confirmation (e.g., goal edits) |
| `workspace` | no | Selected workspace context cached client-side for sub-ms reads |

New slices added as features land. Rule: a slice exists when ≥2 components share state; otherwise use `useState`.

#### Async Logic: createAsyncThunk

For non-server-cache async work that benefits from being in Redux (e.g., posting to a third-party non-tRPC endpoint, or orchestrating multi-step optimistic flows), use `createAsyncThunk`. For straightforward server reads/writes, prefer tRPC — don't duplicate into thunks.

#### Testing

- Slice unit tests via Vitest — pure reducer functions, easy to test
- Selector tests for memoized selectors (`createSelector` from Reselect when needed)
- Component tests use a custom `renderWithStore()` helper that wraps in `<Provider>` with a fresh test store

#### What Doesn't Go in Redux

- Server data — TanStack Query
- URL-bindable filters — nuqs
- Pure component state (input draft, hover state) — `useState`
- Theme provider state read by Tailwind dark mode — `<ThemeProvider>` from next-themes is OK (it's already a Redux-style atom internally)

---

## 5. Design System

### Tokens

```typescript
// tailwind.config.ts
const colors = {
  brand: { 50: '...', 500: '#0EA5E9', 900: '...' },

  bg: { primary: 'var(--bg-primary)', secondary: '...', tertiary: '...' },
  fg: { primary: '...', secondary: '...', muted: '...' },
  border: { subtle: '...', strong: '...' },

  status: {
    green: { 50: '...', 500: '#10B981', 600: '...' },
    amber: { 500: '#F59E0B' },
    red: { 500: '#EF4444' },
  },

  // Metric category accents
  revenue: '#10B981', margin: '#3B82F6', marketing: '#8B5CF6',
  customer: '#EC4899', regional: '#F97316', inventory: '#06B6D4',
};
```

### Components: shadcn/ui-derived

Component library in `packages/ui/`:

```
packages/ui/
├── primitives/        # shadcn-derived: Button, Dialog, DropdownMenu, ...
├── data/              # MetricCard, DataTable, RagBadge, Sparkline
├── charts/            # LineChart, BarChart, Waterfall, Heatmap, FunnelBars
├── form/              # Input, Select, DatePicker, FormMoneyInput (currency-aware)
└── layout/            # PageShell, Sidebar, KpiGrid
```

**Magic UI (scoped, copy-paste — no runtime dep):** Magic UI (150+ animated React components, TypeScript + Tailwind + Motion) is adopted **copy-paste like shadcn** — pasted into `packages/ui/`, owned in-repo, **zero runtime dependency**, same shadcn ecosystem (same Tailwind tokens). It **composes with shadcn; it does not replace it.** Scoped-use rule: use it **only** on **marketing / onboarding / login / empty-state / "delight" surfaces — NOT the dense operator workbench** (P&L, CM Waterfall, Cohort heatmap, Calendar Report, KPI grids stay shadcn + Visx/Recharts). Every Magic UI surface respects `prefers-reduced-motion`, stays within the performance budget (§14), and holds WCAG AA (§15).

### Typography

- **Sans-serif:** Inter
- **Monospace (for table numbers):** JetBrains Mono with `font-variant-numeric: tabular-nums`
- **Multi-language fallback:** Noto Sans (Hindi/Bengali/Arabic for region expansion)

### Density Modes

Two modes: comfortable (default) and compact (-30% padding). User-configurable in settings.

### Theme

Light + Dark. `prefers-color-scheme` respected on first visit. User can override.

---

## 6. Workspace Shell

```
┌────────────────────────────────────────────────────────────────────┐
│ ┌────────┐                                                  ┌─────┐│
│ │ Sidebar│   ┌──────────────────────────────────────────┐  │ AI  ││
│ │        │   │ Top bar: workspace switcher, date filter │  │ Side││
│ │ Nav    │   │           search, profile               │  │ Panel││
│ │        │   ├──────────────────────────────────────────┤  │     ││
│ │        │   │            Page content                  │  │     ││
│ │        │   │                                          │  │     ││
│ │        │   │                                          │  │     ││
│ └────────┘   └──────────────────────────────────────────┘  └─────┘│
└────────────────────────────────────────────────────────────────────┘
```

### Sidebar (Region-Aware)

```
DASHBOARD

ANALYTICS
  Store
  P&L
  Products
  Lifetime Value
  Cohorts
  Acquisition
  Distributions
  Timing
  Inventory

REPORTS
  Calendar Report
  Waterfall
  Customer Lifecycle (NAC)

REGIONAL                          (only if workspace.home_region in dedicated regions)
  Pincodes                        (IN only)
  RTO                             (IN only)
  NDR                             (IN only)
  COD Economics                   (IN only)
  Chargebacks                     (US only)
  State Sales Tax                 (US only)

INTELLIGENCE
  AI Insights        🔴 3 unacked
  AI Chat
  Plan
  Alerts             ⚠️ 1 critical

SETTINGS
```

### Top Bar

- Workspace switcher (multi-workspace users)
- Global date range filter (some pages override)
- Quick search (cmd+K) — products, campaigns, customers, settings
- AI button (right side, cmd+I) — toggles AI side panel
- Profile menu

### AI Side Panel

Toggled via top-bar button or `cmd+I`. Context-aware: when user is on Products page, chat opens with products context preloaded.

---

## 7. Charts

### Library Stack

| Use Case | Library |
|----------|---------|
| Line, bar, area, sparkline | **Recharts** |
| Waterfall, custom funnel, cohort heatmap | **Visx** |
| Tables (sortable, virtualized) | **TanStack Table** |
| Calendar grid | Custom (CSS Grid) |

### Currency-Aware Formatting

Every chart axis, tooltip, table cell uses `formatMoney(amount, currency, format)`:

```typescript
<YAxis tickFormatter={(v) => formatMoney(v, workspace.default_currency, 'compact')} />
```

For INR, this renders `₹4.8 L`. For USD, `$480K`. Etc.

### Performance

- **Virtualization:** cohort heatmap (864 cells), Calendar Report (2,250 cells). CSS Grid + `content-visibility: auto`.
- **Memoization:** chart configs and data transforms via `useMemo`.
- **Skeletons:** every chart has a matching-layout skeleton.

---

## 8. Calendar Report Implementation

```typescript
// app/(workspace)/calendar/page.tsx (Server Component)
export default async function CalendarPage({ searchParams }) {
  const caller = await createCaller();
  const { from, to } = parseDateRange(searchParams);
  const data = await caller.calendar.report({ from, to });

  return <CalendarTable data={data} />;
}

// components/calendar/CalendarTable.tsx (Client Component)
'use client';
export function CalendarTable({ data }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full tabular-nums">
        <thead className="sticky top-0 bg-bg-primary z-10">
          <tr>
            <th className="sticky left-0">Date</th>
            <th>Actions</th>
            <th>CM3 / Goal</th>
            <th>Revenue / Goal</th>
            <th>MER / Goal</th>
            <th>aMER / Goal</th>
            {/* ... */}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => <CalendarRow key={row.date} row={row} />)}
        </tbody>
      </table>
    </div>
  );
}

function CalendarRow({ row }) {
  const { workspace } = useWorkspaceContext();
  return (
    <tr>
      <td className="sticky left-0">{formatDate(row.date, workspace.default_timezone)}</td>
      <td><ActionIcons actions={row.actions} /></td>
      <RagCell value={row.cm3} goal={row.goals.cm3} currency={workspace.default_currency} />
      <RagCell value={row.revenue} goal={row.goals.revenue} currency={workspace.default_currency} />
      {/* ... */}
    </tr>
  );
}

function RagCell({ value, goal, currency }) {
  const status = ragStatus(value, goal.value, goal.type, 'higher_is_better');
  return (
    <td className={cn(
      status === 'green' && 'bg-status-green-50',
      status === 'amber' && 'bg-status-amber-50',
      status === 'red' && 'bg-status-red-50',
    )}>
      {formatMoney(value, currency)} <span className="text-fg-muted">/ {formatMoney(goal.value, currency)}</span>
    </td>
  );
}
```

### Drill-Down

Click any numeric cell → opens a drawer with underlying orders/campaigns/refunds powering that number.

```typescript
function RagCell({ value, ..., onClick }) {
  return <td onClick={() => openDrillDown(row.date, metric_name)}>...</td>
}

// Drill-down drawer
function DrillDownDrawer({ date, metricName }) {
  const { data } = trpc.drillDown.byMetric.useQuery({ date, metricName });
  return <DataTable columns={...} data={data.items} />;
}
```

---

## 9. Waterfall Chart

Custom Visx. Each bar = a step. Green for revenue/profit, red for deductions.

```typescript
'use client';
import { Group } from "@visx/group";
import { Bar } from "@visx/shape";

export function WaterfallChart({ steps, currency }) {
  let running = 0;
  const positioned = steps.map((s) => {
    const start = s.type === 'deduction' ? running - s.amountMinor : running;
    const end = s.type === 'deduction' ? running : running + s.amountMinor;
    if (s.type === 'deduction') running -= s.amountMinor;
    else running += s.amountMinor;
    return { ...s, start, end };
  });

  // Render bars + labels
}
```

Filter chips on top: `All | New Customers | Returning Customers`.

---

## 10. AI Chat UI

```
┌──────────────────────────────────────────────────────────┐
│  AI Chat                                       [×]        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  You: What's my CAC for new customers via Meta in March? │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 🤖 Brain                                            ││
│  │                                                      ││
│  │ 🔎 Querying metric...                               ││  ← tool indicator
│  │                                                      ││
│  │ Your March CAC for new customers acquired via Meta  ││
│  │ was ₹842. That's 14% above your goal of ₹740.      ││
│  │                                                      ││
│  │ Breaking it down:                                   ││
│  │ - Meta acquisition spend: ₹1,42,000                ││
│  │ - New customers from Meta: 169                      ││
│  │ - Up from ₹723 in February (+16% MoM)              ││
│  │                                                      ││
│  │ [View Meta campaigns →]                              ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
├──────────────────────────────────────────────────────────┤
│ [Ask about your data...]                          [Send] │
└──────────────────────────────────────────────────────────┘
```

### Action Links

Structured response field, not free-text parsing:

```json
{
  "content_blocks": [
    {"type": "text", "text": "Your March CAC..."},
    {"type": "action", "label": "View Meta campaigns", "href": "/analytics/acquisition?channel=meta&..."}
  ]
}
```

---

## 11. Forms

### Library: react-hook-form + zod

```typescript
const schema = z.object({
  name: z.string().min(2),
  metricName: z.string(),
  goalValue: z.number().positive(),
});

function GoalForm() {
  const form = useForm({ resolver: zodResolver(schema) });
  return <Form {...form}>...</Form>;
}
```

### Currency-Aware Inputs

```typescript
<FormMoneyInput
  name="goalValue"
  currency={workspace.default_currency}
  // Accepts "2L" (lakh shortcut for INR), "500K" (thousand shortcut), or raw "200000"
/>
```

---

## 12. Tables: TanStack Table

```typescript
<DataTable
  columns={[
    { key: 'productTitle', header: 'Product', sortable: true },
    { key: 'paretoGrade', header: 'Grade', render: (row) => <ParetoGradeBadge grade={row.paretoGrade} /> },
    { key: 'cm1Minor', header: 'CM1', render: (row) => formatMoney(row.cm1Minor, currency), align: 'right' },
    { key: 'cm1Pct', header: 'CM1 %', render: (row) => `${(row.cm1Pct * 100).toFixed(1)}%`, align: 'right' },
  ]}
  data={products}
  paginated
  pageSize={50}
  exportable
  searchable
  initialSort={{ column: 'cm1Minor', dir: 'desc' }}
/>
```

For >1k rows, virtualization via `@tanstack/react-virtual`.

---

## 13. Mobile Web vs Native Mobile App

Brain has a **native mobile app** (React Native + Expo) — see [TECH/10_mobile_architecture.md](10_mobile_architecture.md) for the dedicated mobile build. This section covers the web frontend's mobile-viewport behavior only.

### Web on Mobile Browsers (Tablet + Phone Browsers)

The Next.js web app is responsive, but mobile-browser usage is a **fallback** experience — the native app is the recommended surface for phone users. Detect mobile user agent on landing: show a banner "Use Brain on your phone? [Open in app →](deep link)" with App Store / Play Store fallback.

For users who continue in mobile browser:
- Sidebar → bottom tab bar on `<md`
- KPI grid: 4 cols → 2 cols → 1 col
- Wide tables: horizontal scroll + sticky first column
- Calendar Report: single-column-at-a-time + swipe
- AI Chat: full-screen modal

What's cut on mobile web (use native app or desktop):
- Cohort heatmap
- CM Waterfall filter view (linear stack only)
- Plan Module forecast charts (limited)
- Settings → Costs / COGS bulk editor

---

## 14. Performance Budget at Scale

| Metric | Target |
|--------|--------|
| LCP | <2.0s |
| FID | <100ms |
| CLS | <0.1 |
| Initial JS / route | <100KB gzipped |
| Total dashboard JS | <400KB gzipped |
| API roundtrip → render | <300ms p95 |
| Tail latency (p99) at 100k req/min sustained | <1.5s |

Monitored via PostHog Web Vitals + CloudFront RUM metrics.

### Tactics

- Route-level code splitting (App Router default)
- Server Components reduce client JS
- `next/dynamic` for heavy charts not above the fold
- `next/image` for image optimization (CloudFront-backed)
- Inter font subset; `font-display: swap`
- Avoid client-side date math libraries on initial render
- Sub-bundles per route via Turbopack

---

## 15. Accessibility

WCAG 2.1 Level AA target:
- Color contrast 4.5:1+ on all text; RAG colors verified
- Keyboard: every interactive element reachable; modals trap focus
- Screen readers: ARIA labels on icon-only buttons; chart `<table>` fallback
- Focus visible: never `outline: none` without replacement
- Reduced motion: respect `prefers-reduced-motion`

Tooling: `eslint-plugin-jsx-a11y` + manual QA on key flows.

---

## 16. Internationalization (i18n)

### Phase 1: English (en-IN, en-US, en-GB)

Number formatting differs by region (lakh/crore for INR, etc.) but UI strings are English.

### Phase 3: Hindi UI Option

`next-intl`. UI strings translated; metric labels stay English ("Revenue" not "आय") since operators expect them.

### Future

Bengali, Tamil (Phase 4), Arabic (Phase 4 for AE/SA), Spanish (Phase 5 for LATAM).

---

## 17. Error Handling

### Per-Route Error Boundaries

```typescript
// app/(workspace)/analytics/products/error.tsx
'use client';
import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function ProductsError({ error, reset }) {
  useEffect(() => { Sentry.captureException(error); }, [error]);
  return (
    <PageShell title="Products">
      <ErrorState
        title="Something went wrong loading products"
        message={error.message}
        action={<Button onClick={reset}>Try again</Button>}
      />
    </PageShell>
  );
}
```

### tRPC Error Handling

```typescript
function handleTrpcError(error: TRPCClientError) {
  const code = error.data?.code;
  switch (code) {
    case 'UNAUTHORIZED': router.push('/login'); break;
    case 'INTEGRATION_NOT_CONNECTED': toast('Connect Shopify first'); break;
    case 'RATE_LIMITED': toast('Slow down — you\'re moving fast'); break;
    case 'BACKEND_SERVICE_UNAVAILABLE': toast.error('Brain is temporarily degraded; please retry'); break;
    default: Sentry.captureException(error);
  }
}
```

### Empty States

Every view has a guided empty state:
- "No products yet — connect Shopify"
- "No insights yet — Brain generates insights nightly. First batch tomorrow."
- "No anomalies — your metrics are tracking expected ranges."

---

## 18. Component Library Inventory

Approximate to budget E2's work:

### Primitives (~15)
Button, IconButton, Input, NumberInput, Select, MultiSelect, Combobox, DatePicker, DateRangePicker, Dialog, Drawer, Popover, Tooltip, Toast, DropdownMenu

### Data Components (~14)
KpiCard, MetricCard (RAG), Sparkline, RagBadge, DataTable, ParetoGradeBadge, ChannelBadge, ClassificationPill, EmptyState, ErrorState, LoadingShell, FormError, CurrencyLabel, RegionBadge

### Charts (~12)
LineChart, BarChart, AreaChart, StackedAreaChart, WaterfallChart, FunnelBar, CohortHeatmap, OrderValueHistogram, CalendarCell, PincodeMap (IN), USStatesMap (US, Phase 4), ForecastChart

### Layouts (~6)
PageShell, KpiGrid, SidebarShell, AiSidePanel, FilterBar, SectionHeader

### Modals/Drawers (~10)
GoalEditorModal, MarketingActionModal, CampaignClassificationDrawer, CostSettingsDrawer, DrillDownDrawer, InsightDetailDrawer, BillingModal (Phase 4), HelpModal, RegionSwitcherModal, IntegrationConfigDrawer

**Total:** ~57 components. Estimated build at 1–2/day by E2 starting from shadcn: 8–11 weeks (Phase 1–2).

---

## 19. Testing

- **Unit:** Vitest for utils, formatters
- **Component:** React Testing Library for non-trivial components
- **E2E:** Playwright for critical flows (login → connect Shopify → view Store)
- **Visual regression:** Chromatic (Phase 3, after design system stabilizes)

CI runs unit + component on every PR; E2E on PR-to-main.

---

## 20. Open Questions

| Q | Owner | Resolution |
|---|-------|-----------|
| Amplify vs EKS for frontend hosting? | E1 + E2 | Amplify Phase 0–2; EKS Phase 3 if build minutes / customization warrants. |
| Static export of marketing pages? | E2 | Marketing site separate (Webflow / static). Brain app is fully dynamic. |
| PWA for offline mobile? | E2 | Defer. |
| Native mac/Windows app (Electron/Tauri)? | E2 | No — Phase 5+ if data scale demands. |
| Real-time live dashboards (WebSocket-pushed)? | E2 | Phase 3. Subscribe to Kafka `analytics.metrics.daily_materialized.v1`. |
| White-label custom themes? | E2 | Phase 4. Theme tokens already support. |
| Date picker — shared or per-context? | E2 | One shared with regional fiscal year option. |
| Where do exports get downloaded? | E2 | S3 signed URLs; email-delivered after generation. |
| Should Storybook be in the repo? | E2 | Not initially. Add at Phase 3 if E2 grows beyond 1 person. |
| Frontend i18n at workspace level or user level? | E2 | Workspace primary; user override Phase 4. |
