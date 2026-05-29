---
name: region-and-locale
description: The region seam — RegionAdapter for region-varying economics, structural ap-south-1 + KSA/UAE residency, and the i18n/RTL/locale-format seam, India-first.
---

# Region & Locale — multi-region from day one, India-first by sequencing

One seam, three layers: **behaviour** (RegionAdapter), **data plane** (residency enforcement), **presentation** (i18n/RTL/formatting). Rule for all three: *region/locale-varying concerns go behind an interface even when only India is implemented* — so Phase-4 UAE/GCC is additive (new adapter + bundle + region), never a retrofit. Reference [`compliance-engine`] for DPDP/PDPL/transfer law; this skill is the engineering seam, not the legal canon.

**Canon:** TECH/04 (RegionAdapter) · TECH/16 §4.3/§6 (residency) · TECH/09 §5 (per-region infra) · TECH/07 §16/§5 (i18n/fonts). Owners: Jatin+Shreya (residency), Ananya+Karan (i18n). Phasing: Phase 0–1 ap-south-1 only + all three seams; Phase 3 Hindi UI; Phase 4 GCC region + Arabic/RTL.

## 1. RegionAdapter — the behaviour seam (`pylibs/brain_regional`)

`RegionAdapter` (ABC) hides every region-varying concern. Resolve per-workspace from a read-only `home_region`; **never assume IN**.

```python
class RegionAdapter(ABC):
    region_code: str; default_currency: str; default_timezone: str; fiscal_year_start_month: int
    def extract_net_revenue(self, order) -> tuple[int,int]      # (net_minor, tax_minor) — per-SKU
    def classify_payment_method(self, order) -> str             # card|wallet|upi|cod|bnpl|other
    def is_high_risk_payment(self, order, region_data) -> bool  # IN: COD on high-RTO pincode
    def map_shipment_status(self, source, status) -> str        # → canonical states (incl. rto)
    def compute_logistics_cost(self, shipment, settings) -> dict[str,int]
    def normalize_postal_code(self, raw) -> Optional[str]       # IN: 6-digit pincode
    def postal_code_metadata(self, code) -> dict                # {city,state,tier,serviceable_by}
    def get_seasonal_events(self, year) -> list[dict]
    def tax_reconciliation_report(self, ws, period) -> dict

# __init__.py
ADAPTERS = {'IN': IndiaAdapter(), 'US': USAdapter(), 'GB': UKAdapter(), 'AE': UAEAdapter()}
def get_adapter(ws_region: str) -> RegionAdapter: return ADAPTERS.get(ws_region, IndiaAdapter())
```

Ingestion/analytics/intelligence all resolve via `get_adapter(workspace.home_region)`. `IN` is the full implementation — GST 2.0 per-SKU (0/5/18/40), COD/RTO model + pincode reliability + NDR + festival calendar, `Asia/Kolkata`, fiscal month 4 (see [`india-commerce-economics`]). UAE/GCC (Phase 4): per-country VAT (KSA 15/UAE 5/BH 10/OM 5; QA/KW none), AED/SAR, Ramadan/Eid, Tabby/Tamara, **no RTO concept**, Salla/Zid/Noon connectors.

**Add-a-region (TECH/04 §4):** new adapter + `seasonal_events_<cc>` seed + `<CC>_DEFAULT_ALERTS` + translation bundle + CI snapshot walking an order through it. The metric engine, frontend, intelligence, and notifications need **zero changes** — if adding a region forces a change outside the adapter, the region path leaked.

## 2. Data residency — the data-plane seam (structural, not a config flag)

Residency that is merely *configured* breaks silently the day someone adds cross-region replication. Make it physically impossible + continuously tested. Residency is the **default for every workspace** (DPDP/PDPL transfer law), not an enterprise upsell.

**Guardrails (Jatin):** SCP on the prod OU denies `s3:PutObject`/`rds:CreateDBInstance`/`dynamodb:CreateTable`/`kafka:CreateCluster`/`es:CreateDomain` where `aws:RequestedRegion ∉ allowed-set`; a CDK `ResidencyAspect` fails `cdk synth` if any data store lands off-region; `cdk-nag` carries the rule. Also guarded: S3 cross-region replication, RDS/Aurora cross-region snapshots, DynamoDB global tables, AMI/EBS snapshot copies, and CloudWatch/OpenSearch log shipping cross-region (logs carry `workspace_id`+PII — in scope).

**Routing:** storage targets resolve from `home_region`, never hardcoded — `RESIDENCY_REGION[home_region]` → per-region Supabase/ClickHouse/MSK/S3 (IN→ap-south-1, AE→me-central-1, SA→KSA). Data-plane mirror of adapter resolution; the seam exists now so Phase-4 GCC is additive.

**The proof (TECH/16 §6 — QA VETO gate):** a real test, failing-if-violated:

```python
def test_indian_workspace_data_never_leaves_ap_south_1():
    ws = make_workspace(home_region='IN'); write_order(ws, sample_order())
    t = stores_for(ws)
    assert all(region_of(e) == 'ap-south-1' for e in (t.pg, t.ch, t.msk, t.s3))   # routing
    with pytest.raises(AccessDenied):                                              # off-region write denied
        s3_client('us-east-1').put_object(Bucket=t.s3.replace('ap-south-1','us-east-1'), ...)
    assert no_cross_region_replication(t.s3) and no_global_tables_touching(ws)     # no copy path exists
```

Run in CI + as a periodic prod conformance check; pair with an AWS Config rule for drift. **GCC transfers** (Phase 4): KSA PDPL (SDAIA) and UAE PDPL restrict cross-border transfer — out only via adequacy/SCCs/BCRs logged in the DPA. A KSA workspace's SCP never permits ap-south-1, and vice-versa — isolation runs both ways. Sub-processors need per-region presence or an approved transfer basis before a GCC brand goes live.

## 3. i18n / RTL — the presentation seam

Same discipline for copy + layout: externalize every string, use logical (direction-agnostic) layout now; Phase 4 = add a bundle + flip `dir`, not retrofit thousands of hardcoded strings.

- **Strings:** web `next-intl`, mobile `i18next`/`react-intl` + `expo-localization`, shared keys in `packages/`. No literal user-facing copy in JSX. ICU MessageFormat for plurals/interpolation — never string concat. **Keep canonical metric labels English** (Revenue/CM2/aMER/MER) — translate chrome (nav/buttons/empty states/errors), not the metric vocabulary (TECH/07 §16).
- **RTL:** CSS **logical properties** everywhere from Phase 1 (`margin-inline-start`, `border-inline-end`; Tailwind `ms-/me-/ps-/pe-/start-/end-/text-start/border-e` — never `ml-/pr-/left-/text-left`). Set `dir` from locale at root. Phase-4 checklist: mirror directional icons (gate on `dir`); **numbers, charts, CM Waterfall, Calendar grid stay LTR** even on an RTL page (`dir="ltr"`/`unicode-bidi:isolate`); RN `I18nManager.isRTL` + `start`/`end` props, verify thumb-first Morning Brief mirrors correctly.
- **Formatting (beyond ₹):** currency via `formatMoney` + adapter (₹ lakh/crore ONLY for INR; else `Intl.NumberFormat` per locale); number grouping, dates/times (`Intl.DateTimeFormat` + workspace tz), percent/RAG via `Intl`, Hijri month context for GCC seasonal events. Locale derives from `home_region` (Phase-4 user override).
- **Fonts:** Inter (Latin) + JetBrains Mono (tabular nums) + Noto Sans fallback — declare the stack now so Devanagari (Phase 3) / Arabic (Phase 4) render when a bundle lands; verify Arabic shaping + tabular-nums under Arabic locale.

## Anti-patterns (code-review blockers / Shreya VETO on residency)

- `if region == 'IN'` branches in business logic; hardcoded ₹/GST/VAT/IST hours/RTO logic outside an adapter; a region-specific **fork** of a primitive instead of a new adapter; a single blended tax rate.
- S3 cross-region replication / cross-region snapshot / global table / AMI copy / cross-region logs moving an IN/KSA/UAE workspace's data off its region; hardcoded storage endpoints instead of `home_region` routing; residency offered only to enterprise; a residency claim with no SCP + no test; a GCC transfer with no SCC/BCR/SDAIA basis logged.
- Hardcoded user-facing string; physical CSS direction (`ml-/left/text-left`); string concat for sentences; hardcoded ₹/date/number-format outside `formatMoney`/adapter; translating canonical metric names; assuming a new region/locale "just works".

## Verify

- Grep shared code for `'IN'`/`₹`/`GST`/`09:00–21:00`/hardcoded copy/`ml-`/`text-left` outside `pylibs/brain_regional` + `lib-formatters` — none in shared primitives.
- A stub adapter + locale (`ar` bundle, `dir="rtl"`): order flows through it untouched; shell mirrors, numbers/charts stay LTR; Hindi stub shows chrome in Hindi, metrics English.
- `cdk synth` fails off-region; `test_indian_workspace_data_never_leaves_ap_south_1` passes; AWS Config reports zero off-region data resources; a stub KSA workspace routes to KSA and its SCP refuses ap-south-1.

## References

- TECH/04 (RegionAdapter) · TECH/16 §4.3/§6/§8 Q5 (residency + sub-processors) · TECH/09 §5 · TECH/07 §16/§5
- [`india-commerce-economics`] — the IN economics behind the adapter · [`compliance-engine`] — DPDP/PDPL/transfer law + erasure
- [`metric-engine`] — region-agnostic formulas · [`devops-aws`] — CDK/SCPs/cdk-nag · [`multi-tenancy-isolation`] — `workspace_id` carries `home_region`
- [`frontend-web`] · [`mobile-surface`] · [`accessibility`] — render-layer the locale seam feeds
