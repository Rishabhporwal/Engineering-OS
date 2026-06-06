---
name: region-and-locale
description: The region/locale seam — a RegionAdapter for region-varying behaviour, a structural data-residency seam, and the i18n/RTL/locale-format seam. Build all three behind interfaces from day one so a new region is additive, not a retrofit.
---

# Region & Locale — multi-region from day one, behind one seam

> **Reference patterns, generic examples.** The *patterns* below (adapter for region-varying behaviour,
> structural residency, externalized i18n) transfer to any product. The specific regions, currencies, tax
> regimes, and providers named here are **illustrative examples only** — your product's actual regions,
> residency obligations, and locales are declared in the Product Canon (`COMPLIANCE.md` for the regulatory
> regime, `STACK.md` for which infra/region a seam binds to).

One seam, three layers: **behaviour** (RegionAdapter), **data plane** (residency enforcement), **presentation** (i18n/RTL/formatting). Rule for all three: *region/locale-varying concerns go behind an interface even when only one region is implemented* — so adding a second region later is additive (new adapter + bundle + region), never a retrofit. Reference [`compliance-engine`] for the data-protection / transfer regime; this skill is the engineering seam, not the legal canon.

**Canon:** the residency obligations and supported regions live in the Product Canon (`COMPLIANCE.md` + `STACK.md`); the formula/locale rules in `METRICS.md`. Owners: Platform/SRE + Security Reviewer (residency), Frontend/Web + Mobile (i18n). Phase the rollout however the Canon sequences it — but build all three seams in the first region.

## 1. RegionAdapter — the behaviour seam

A `RegionAdapter` (abstract base) hides every region-varying concern. Resolve it per-tenant from a read-only `home_region`; **never assume a default region in business logic**.

```python
class RegionAdapter(ABC):
    region_code: str; default_currency: str; default_timezone: str; fiscal_year_start_month: int
    def extract_net_amount(self, txn) -> tuple[int,int]         # (net_minor, tax_minor) — integer minor units
    def classify_payment_method(self, txn) -> str              # card|wallet|bank|cash|bnpl|other
    def is_high_risk_transaction(self, txn, region_data) -> bool
    def map_fulfilment_status(self, source, status) -> str     # → canonical states
    def compute_logistics_cost(self, shipment, settings) -> dict[str,int]
    def normalize_postal_code(self, raw) -> Optional[str]
    def postal_code_metadata(self, code) -> dict               # {city, region, tier, serviceable_by}
    def get_seasonal_events(self, year) -> list[dict]
    def tax_reconciliation_report(self, tenant, period) -> dict

# __init__.py — register one adapter per supported region; the set comes from the Canon
ADAPTERS = {'<RA>': RegionAAdapter(), '<RB>': RegionBAdapter()}
def get_adapter(region: str) -> RegionAdapter: return ADAPTERS.get(region, ADAPTERS[DEFAULT_REGION])
```

Every consumer (ingestion, analytics, intelligence, notifications) resolves via `get_adapter(tenant.home_region)`. Each adapter is a full implementation of its region's rules — tax model (e.g. per-line tax slabs vs a flat VAT), payment mix, fulfilment/returns concept, postal-code system, fiscal calendar, seasonal/holiday calendar, currency, and timezone. Regions differ structurally (e.g. one region may have a delivery-returns concept the other lacks, or a different tax rate per category or per country) — that difference belongs **inside the adapter**, never in a branch in shared code.

**Add-a-region:** new adapter + seasonal-events seed + per-region default alerts + translation bundle + a CI snapshot that walks a transaction through it. The metric engine, frontend, intelligence, and notifications need **zero changes** — if adding a region forces a change outside the adapter, the region path leaked.

## 2. Data residency — the data-plane seam (structural, not a config flag)

Residency that is merely *configured* breaks silently the day someone adds cross-region replication. Make it physically impossible + continuously tested. Where the Canon's regime requires it, residency is the **default for every tenant**, not an enterprise upsell.

**Guardrails (Platform/SRE):** at the cloud-org level, deny the create/write operations for every data store (object storage, managed DB, table/stream/search-cluster creation) when the requested region is outside the allowed set; an infra-as-code policy aspect fails the synth/plan step if any data store lands off-region; a policy linter carries the rule. Also guarded: cross-region replication, cross-region snapshots/copies, global tables, image/volume snapshot copies, and cross-region log shipping (logs carry the tenant key + PII — in scope).

**Routing:** storage targets resolve from `home_region`, never hardcoded — a `RESIDENCY_REGION[home_region]` map → the per-region datastore/bus/object-store endpoints. This is the data-plane mirror of adapter resolution; the seam exists now so a second region is additive.

**The proof (QA VETO gate):** a real test, failing-if-violated:

```python
def test_tenant_data_never_leaves_its_home_region():
    t = make_tenant(home_region='<RA>'); write_record(t, sample_record())
    stores = stores_for(t)
    assert all(region_of(e) == EXPECTED_REGION['<RA>'] for e in (stores.db, stores.olap, stores.bus, stores.objects))
    with pytest.raises(AccessDenied):                                    # off-region write denied
        object_client(OTHER_REGION).put(bucket=stores.objects_in(OTHER_REGION), ...)
    assert no_cross_region_replication(stores.objects) and no_global_tables_touching(t)  # no copy path exists
```

Run in CI + as a periodic prod conformance check; pair with a cloud-config drift rule. **Cross-border transfers:** where the Canon's regime restricts transfer, data leaves a region only via an approved legal basis (adequacy / standard contractual clauses / binding corporate rules) logged in the data-processing record. Residency runs **both ways** — region A's guardrail never permits region B's stores, and vice-versa. Sub-processors need per-region presence or an approved transfer basis before a tenant in that region goes live.

## 3. i18n / RTL — the presentation seam

Same discipline for copy + layout: externalize every string, use logical (direction-agnostic) layout now; adding a locale later = add a bundle + flip `dir`, not retrofit thousands of hardcoded strings.

- **Strings:** an i18n library on web + mobile, shared keys in a common package. No literal user-facing copy in markup. Use ICU MessageFormat for plurals/interpolation — never string concat. **Keep canonical metric labels in one source language** — translate the chrome (nav/buttons/empty states/errors), not the metric vocabulary, so a metric name means the same thing everywhere.
- **RTL:** CSS **logical properties** everywhere from the first locale (`margin-inline-start`, `border-inline-end`; framework equivalents like `ms-/me-/ps-/pe-/start-/end-/text-start` — never `ml-/pr-/left-/text-left`). Set `dir` from the locale at the root. RTL checklist: mirror directional icons (gate on `dir`); **numbers, charts, and tabular grids stay LTR** even on an RTL page (`dir="ltr"` / `unicode-bidi:isolate`); on mobile use the platform's RTL manager + `start`/`end` props, and verify the primary flow mirrors correctly.
- **Formatting:** currency via a single `formatMoney` helper + the adapter (locale-specific grouping such as lakh/crore only where that locale uses it; otherwise the platform `Intl.NumberFormat` per locale); number grouping, dates/times (`Intl.DateTimeFormat` + the tenant tz), percent/status formatting via `Intl`, and any locale-specific calendar context for seasonal events. Locale derives from `home_region` with an optional per-user override.
- **Fonts:** declare a font stack with the needed script fallbacks now (e.g. a Latin face + a tabular-nums monospace + script-specific fallbacks) so a new script renders the day its bundle lands; verify shaping + tabular-nums under each target locale.

## Anti-patterns (code-review blockers / Security VETO on residency)

- `if region == '<X>'` branches in business logic; hardcoded currency/tax/timezone/returns logic outside an adapter; a region-specific **fork** of a primitive instead of a new adapter; a single blended tax rate where the regime is per-line.
- Cross-region replication / snapshot / global table / image copy / cross-region logs moving a tenant's data off its region; hardcoded storage endpoints instead of `home_region` routing; residency offered only to enterprise; a residency claim with no org-level guardrail + no test; a cross-border transfer with no logged legal basis.
- Hardcoded user-facing string; physical CSS direction (`ml-/left/text-left`); string concat for sentences; hardcoded currency/date/number format outside `formatMoney`/the adapter; translating canonical metric names; assuming a new region/locale "just works".

## Verify

- Grep shared code for hardcoded region codes / currency symbols / tax names / fixed hours / hardcoded copy / physical-direction classes (`ml-`/`text-left`) outside the adapter + formatter modules — none in shared primitives.
- A stub adapter + locale (an RTL bundle, `dir="rtl"`): a transaction flows through it untouched; the shell mirrors, numbers/charts stay LTR; a second-language stub shows chrome translated, metrics in the source language.
- The infra synth/plan fails off-region; `test_tenant_data_never_leaves_its_home_region` passes; cloud-config reports zero off-region data resources; a stub second-region tenant routes to its region and its guardrail refuses the first region.

## References

- Product Canon: `COMPLIANCE.md` (regime + supported regions + transfer basis) · `STACK.md` (per-region infra binding) · `METRICS.md` (region-agnostic formulas)
- [`compliance-engine`] — data-protection / transfer law + erasure · [`metric-engine`] — region-agnostic formulas
- [`multi-tenancy-isolation`] — the tenant key carries `home_region` · [`frontend-web`] · [`mobile-surface`] · [`accessibility`] — the render-layer surfaces the locale seam feeds
- A concrete, fully-bound instantiation of this seam lives under `examples/brain-instantiation/`.
