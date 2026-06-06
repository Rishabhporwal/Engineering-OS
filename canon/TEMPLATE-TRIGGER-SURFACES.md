# TRIGGER SURFACES — what forces high-stakes rigor (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/TRIGGER-SURFACES.md`. The OS supplies the **categories**; you
> supply the **concrete surfaces and thresholds** for this product. Any change touching a trigger
> surface is routed to the **high-stakes lane** (architecture + security + QA + final review + 2
> personas + mutation tests). See `engineering-os-blueprint/03-delivery-lifecycle.md §3`.
>
> These also drive the **post-build reclassification gate**: the actual staged diff is re-scanned, so a
> change that grows into a trigger surface mid-build is upgraded automatically.

| Category (OS-fixed) | Concrete surface in this product (you fill) | Threshold / notes |
|---|---|---|
| Compliance / regulatory boundary | `<files/modules touching the regime in COMPLIANCE.md>` | any change |
| Multi-tenancy / isolation boundary | `<the tenant-key enforcement points>` | any change |
| Authentication / authorization | `<auth/session/role code>` | any change |
| Money / financial calculation | `<billing/pricing/amount math>` | any change |
| Shared-contract parity | `<a calc/schema defined in >1 runtime/language>` | any change |
| System-of-record / audit-log writes | `<the audit/decision log writer>` | any change |
| Outbound side-effects | `<external API calls, user-facing sends>` | any change |
| `<product-specific category, if any>` | `<…>` | |
