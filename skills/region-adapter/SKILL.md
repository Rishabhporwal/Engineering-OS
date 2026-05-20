---
name: region-adapter
description: Brain's multi-region abstraction — "multi-region from day one, India-first by sequencing." Every region-varying concern (currency, tax, telecom compliance, shipping carriers, calling hours, festival calendar, address/pincode format) goes behind a RegionAdapter interface, even when only India (`in`) is implemented today. Use when building ANY primitive that could differ by market, or when adding a new region (ae/sa/us/eu/…). Prevents the India path from being hardcoded into a global product.
---

# Region Adapter — multi-region from day one, India-first by sequencing

Brain is India-first but **multi-region by architecture** (operating-system.md principle #7). The rule: **every region-varying concern is accessed through a `RegionAdapter` interface, even when only the India implementation exists.** This makes adding `ae`/`sa`/`us` a new adapter, not a refactor of hardcoded India logic.

## What varies by region (must go behind the adapter)

| Concern | India (`in`) | Why it can't be hardcoded |
|---|---|---|
| Currency + numbering | ₹, Indian (lakh/crore) grouping | UAE = AED, US = $ with western grouping |
| Tax | GST (inclusive, RTO-adjusted) | UAE = VAT 5%, US = sales tax by state |
| Telecom compliance | DLT, NCPR, DND, calling hours 09:00–21:00 IST | UAE = TRA rules; US = TCPA; different hours/registries |
| Shipping / RTO | Shiprocket, multi-3PL, pincode reliability | GCC carriers differ; RTO economics differ |
| Festival calendar | Diwali/Holi/etc. demand multipliers | Ramadan/Eid in GCC |
| Address format | pincode (6-digit) | UAE has no postal codes in the same sense |

## The pattern

1. **Define the interface, not the India impl, first.** `RegionAdapter { currency(); tax(); complianceGate(); carriers(); festivals(); … }`.
2. **Implement `IndiaRegionAdapter` only** for now — but code calls the interface, never India constants directly.
3. **Resolve the adapter per `workspace_id`** (a workspace has a region). Never assume India in shared code.
4. **Compliance gates run through the adapter** — the India telecom gate ([`india-commerce-economics`](../india-commerce-economics/SKILL.md)) is `in`'s implementation of `complianceGate()`, not a global hardcode. Adding UAE = implement its `complianceGate()`, don't fork the channel router.
5. **Single-Primitive Rule still holds:** the Audience Builder, channel routers, metric engine consume the adapter; they are not duplicated per region.

## Anti-patterns

- `if (country === 'IN')` branches scattered through business logic → the thing the adapter exists to prevent.
- Hardcoding ₹, GST %, or IST calling hours outside the India adapter.
- Building a region-specific fork of a primitive instead of a new adapter (violates Single-Primitive).
- Assuming a new region "just works" without implementing its compliance + tax + carrier methods.

## Verify

- Grep for hardcoded `'IN'` / `₹` / `GST` / `09:00`–`21:00` outside the India adapter — there should be none in shared primitives.
- A second (even stub) adapter can be registered without touching any primitive's code.
