---
name: i18n-rtl
description: Build the localization SEAM now — like region-adapter does for economics — so India-only UI strings don't force a Phase-4 retrofit when UAE/GCC goes live. String externalization (next-intl on web, equivalent on RN — zero hardcoded UI copy), RTL layout for Arabic (logical CSS properties + mirroring, Phase 4), locale-aware formatting beyond ₹ (numbers/dates/currency keyed off the workspace RegionAdapter), Hindi UI (Phase 3), font fallback. The seam ships now; Arabic/RTL activates in Phase 4. Use when adding any user-facing string, any layout that assumes LTR, or any locale-dependent format. Owner: Ananya + Karan.
---

# i18n & RTL — build the seam now, activate Arabic in Phase 4

`region-adapter` keeps region-varying *economics* behind an interface even when only India is implemented. This skill is the same discipline for the *presentation layer*: externalize every UI string and use logical (direction-agnostic) layout **now**, so that when the first UAE/GCC brand goes live in Phase 4 we add a locale bundle + flip `dir`, not retrofit thousands of hardcoded `<div>Revenue</div>` and `marginLeft` rules. Today the seam is missing — TECH/07 §16 plans `next-intl` for Phase 3 Hindi but Phase-1 copy is being hardcoded in English. That is the exact retrofit trap the adapter pattern exists to prevent.

> **The one rule:** *no user-facing string is hardcoded and no layout hardcodes left/right — copy comes from a message catalogue, direction comes from the locale.* Adding a market is a new bundle + adapter, never a fork.

**Canonical source:** TECH/07 §16 (i18n roadmap), TECH/04 (RegionAdapter currency/timezone). Owned by **Ananya** (web) + **Karan** (mobile). Phasing: **Phase 1** English (en-IN/en-US/en-GB) + the seam itself; **Phase 3** Hindi UI; **Phase 4** Arabic + RTL for AE/SA.

## 1. String externalization (do this from Phase 1)

Web uses **next-intl** (App Router-native, Server-Component-friendly). No literal user-facing copy in JSX — ever.

```tsx
// ❌ retrofit trap — hardcoded copy, can never be translated without code edits
<h2>Store Analytics</h2><button>Approve</button>

// ✅ seam — copy from the catalogue
import { useTranslations } from 'next-intl';
const t = useTranslations('analytics');
<h2>{t('store.title')}</h2><button>{t('actions.approve')}</button>
```

```jsonc
// apps/web/messages/en.json  (Phase 1)            apps/web/messages/ar.json (Phase 4)
{ "analytics": { "store": { "title": "Store Analytics" },
                 "actions": { "approve": "Approve" } } }
```

Mobile uses the equivalent (`react-intl` / `i18next` with `expo-localization` for the device locale) and **shares the same message keys** where copy is identical, so web and mobile never drift apart. Catalogues live in `packages/` so both surfaces consume one source.

**Keep metric labels in English on purpose.** TECH/07 §16: operators expect "Revenue", "CM2", "aMER", "MER" — not transliterations (not "आय"). Translate chrome (nav, buttons, empty states, errors), not the canonical metric vocabulary. Pluralization + interpolation go through ICU MessageFormat (`{count, plural, one {# order} other {# orders}}`), never string concatenation — concatenation is untranslatable and an anti-pattern.

## 2. RTL layout — logical properties now, mirror in Phase 4

Arabic (UAE/GCC) is right-to-left. The cost of RTL is near-zero **if you never hardcode physical direction**. Use CSS **logical properties** everywhere from Phase 1:

```css
/* ❌ breaks under RTL — sidebar pins to the wrong edge for an Arabic operator */
.sidebar { margin-left: 16px; border-right: 1px solid; }
/* ✅ direction-agnostic — flips automatically when dir="rtl" */
.sidebar { margin-inline-start: 16px; border-inline-end: 1px solid; }
```

Tailwind: use the logical utilities (`ms-4`, `me-4`, `ps-2`, `pe-2`, `start-0`, `end-0`, `text-start`, `border-e`) — not `ml-4`/`pr-2`/`left-0`/`text-left`. Set direction at the root from the workspace locale:

```tsx
// app/layout.tsx — dir comes from locale, not hardcoded "ltr"
<html lang={locale} dir={localeDir(locale) /* 'rtl' for ar, else 'ltr' */}>
```

What still needs explicit handling under RTL (Phase-4 checklist, but design for it now):
- **Directional icons** mirror (back/forward chevrons, the sidebar collapse `‹›`, trend arrows) — gate on `dir`.
- **Numbers, charts, the CM Waterfall, and the Calendar grid stay LTR** even in an RTL page — financial figures and time axes are read left-to-right in Arabic-locale finance. Wrap numeric cells with `dir="ltr"`/`unicode-bidi: isolate`.
- **Mobile:** React Native `I18nManager.isRTL` mirrors flex automatically; use `start`/`end` props (not `left`/`right`) and test that the thumb-first Morning Brief flow still reads correctly mirrored.

## 3. Locale-aware formatting beyond ₹

Currency already routes through `region-adapter` + `packages/lib-formatters formatMoney` (₹ lakh/crore for INR; `Intl.NumberFormat` per-locale otherwise — crore/lakh appear ONLY for INR). Extend the same discipline to everything locale-dependent:

| Concern | Source of truth | Never |
|---|---|---|
| Currency display | `formatMoney(minor, currency, format)` via RegionAdapter | hardcode `₹` or a symbol in JSX |
| Number grouping | `Intl.NumberFormat(locale)` (Indian 12,34,567 vs Western 1,234,567 vs Arabic digits) | manual `toLocaleString()` with a fixed locale |
| Dates / times | `Intl.DateTimeFormat(locale, { timeZone: workspace tz })` | a global date library with a fixed format |
| Calendars | Gregorian default; surface Hijri month context for GCC seasonal events (Ramadan/Eid) | assume Gregorian-only |
| Percent / RAG thresholds | `Intl.NumberFormat(locale, {style:'percent'})` | `${v*100}%` string concat |

Locale resolution mirrors adapter resolution: a workspace has a locale derived from its `home_region` (with a Phase-4 user-level override, TECH/07 §20). Daily aggregates already use workspace-local time via `default_timezone` — formatting reads the same tz so the dashboard and the data agree.

## 4. Fonts

Brain ships **Inter** (Latin) + **JetBrains Mono** (tabular numerals) + **Noto Sans** as the multi-script fallback (TECH/07 §5 — Hindi/Devanagari Phase 3, Arabic Phase 4). Declare the fallback stack now so Devanagari/Arabic glyphs render the moment a bundle lands; verify Arabic shaping (ligatures, contextual forms) and that tabular-nums still applies to numeric columns under an Arabic locale.

## Anti-patterns (code-review blockers)

- **Hardcoded user-facing string** in JSX/TSX/RN instead of a catalogue key — the retrofit trap.
- **Physical CSS direction** (`ml-`/`mr-`/`left`/`right`/`text-left`/`pl-`) in shared UI instead of logical properties — breaks RTL silently.
- **String concatenation for sentences** with interpolated values/plurals instead of ICU MessageFormat.
- **Hardcoded `₹`, a date format, or a number grouping** outside `lib-formatters`/RegionAdapter — same leak `region-adapter` forbids for economics.
- **Translating canonical metric names** (Revenue/CM2/aMER) — keep them English by policy.
- Assuming a new locale "just works" without a bundle + `dir` + font + format pass.

## Verify

- Grep shared web/mobile code for hardcoded copy + `ml-`/`mr-`/`text-left`/literal `₹` outside `lib-formatters` — none in shared components.
- Switch the active locale to a stub `ar` bundle + `dir="rtl"`: the shell mirrors, numbers/charts stay LTR, no layout breaks. (Pseudo-locale `en-XA` is a fast Phase-1 smoke test for missing keys + truncation.)
- A Hindi stub bundle renders chrome in Hindi while metric labels stay English.

## References
- TECH/07 §16 (i18n roadmap) + §5 (fonts) — canonical
- TECH/04 — RegionAdapter currency + timezone (formatting source of truth)
- [`region-adapter`](../region-adapter/SKILL.md) — the economics seam this mirrors for presentation
- [`frontend-web`](../frontend-web/SKILL.md) — Next.js + Indian number formatting + a11y
- [`frontend-mobile`](../frontend-mobile/SKILL.md) — RN `I18nManager` RTL + `expo-localization`
- [`accessibility`](../accessibility/SKILL.md) — language attributes + dir feed screen-reader correctness
