# STACK — seam bindings (TEMPLATE)

> Fill in once during Foundation; copy to `.engineering-os/knowledge-base/STACK.md`. Bind each
> architecture **seam** to a concrete technology. The OS is stack-agnostic — it depends on the seam's
> intent, not the product. See `engineering-os-blueprint/09-reference-architecture.md §2`.
>
> Record every non-trivial choice as an ADR (context → options → decision → consequences → status).

| Seam | Intent the OS depends on | Bound to (this product) | ADR |
|---|---|---|---|
| PersistenceAdapter | System-of-record read/write, tenant isolation, reversible migrations | `<e.g. PostgreSQL>` | ADR-001 |
| AnalyticsAdapter | Aggregate queries over high-volume facts | `<e.g. columnar warehouse / none>` | |
| EventAdapter | Idempotent, replayable publish/consume | `<e.g. log-based broker / none>` | |
| CacheAdapter | Hot reads, dedup, rate-limit state, scoped keys + TTL | `<e.g. in-memory cache / none>` | |
| BlobAdapter | Large immutable object storage | `<e.g. object store / none>` | |
| IdentityAdapter | AuthN, AuthZ, sessions, roles | `<e.g. managed auth / IdP>` | |
| SecretsAdapter | Managed secrets / keys, never embedded | `<e.g. secret manager + KMS>` | |
| ObservabilityAdapter | Correlation identity across traces/metrics/logs | `<e.g. OTel + backend>` | |
| DeployAdapter | Progressive rollout + bake + auto-rollback | `<e.g. CI/CD + orchestrator>` | |
| ModelAdapter (AI) | Cheapest-sufficient inference routing, cache, fallback | `<e.g. model gateway / n/a>` | |
| RegionAdapter | Region/locale-varying behavior (residency, formats) | `<e.g. region rules / n/a>` | |
| Client surfaces | Web and/or mobile UIs | `<e.g. web framework / mobile framework>` | |

## Phasing (optional)
`<which seams ship in which phase; what is deferred>`

## Locked choices
`<the stack is LOCKED once approved; routine work references this file. A new layer or a swap needs a fresh ADR.>`
