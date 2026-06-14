---
name: multi-tenancy-isolation
description: Tenant isolation enforced at EVERY layer — identity → service → data store → async backbone. The tenant key is carried on every row/event/cache-key/log; a cross-tenant leak is a P0, Security-VETO surface, SLO = 0 leaks.
---

# Multi-Tenancy & Data Isolation

**Tenant = the product's isolation unit** (whatever the Canon declares — `tenant_id`, account, organisation, brand). A cross-tenant leak is among the worst things the product can do — **P0, a Security-Reviewer VETO surface, SLO = 0 leaks.** Isolation is **defense in depth: every layer enforces it, all are required.** A single missed layer is a leak.

**Canonical sources:** the Product Canon — `INVARIANTS.md` (the isolation invariant), `STACK.md` (which mechanism binds each layer), `COMPLIANCE.md` (residency/segregation requirements). See `engineering-os-blueprint/05-engineering-standards.md` (isolation) and `08-technical-governance.md`.

## The hierarchy

```
Organisation → Tenant → Account/Channel/Integration → records
```

The tenant is the billing + isolation unit. **Account models** vary by product: single tenant = single account (default); one org owns many tenants (each isolated); partner/agency-managed (scoped per-tenant grant, every action tagged + audited); enterprise overlay (residency, stricter isolation). Portfolio/benchmark views aggregate across tenants **only** via explicit permission + anonymized/scoped queries.

## Enforce at every layer (all required)

Isolation is not one check — it is the **same tenant key asserted independently at each layer**, so no single bug or bypass leaks data. Bind each layer to your stack's mechanism in `STACK.md`:

| # | Layer | Intent | Example mechanism |
|---|---|---|---|
| 1 | **Identity / token** | The caller's token carries the active tenant + role + accessible-tenant list | a JWT claim from the IdP/auth provider → `auth-and-access` |
| 2 | **Service boundary** | The edge/gateway validates the token, **asserts** the requested tenant matches the token's tenant, and propagates `tenant_id`/`user_id`/`request_id` on every internal hop; **enforce role on every mutation** | gateway assertion + a `requireRole(ctx, tenant, minRole)` check |
| 3 | **Transactional store** | Every tenant-scoped row read/write is filtered by tenant in the engine, not just app code | **Postgres RLS** (`SET LOCAL` the tenant GUC per txn) → `data-layer` |
| 4 | **Analytical / OLAP store** | A store without engine-level row security gets a **query gateway** that rejects any query lacking a tenant predicate | a thin client wrapper that asserts the `tenant_id =` filter → `clickhouse-olap` |
| 5 | **Async backbone** | Every event carries the tenant on its envelope; the **partition key is the tenant** (per-tenant ordering); consumers **assert** the tenant from the envelope | Kafka/queue envelope + partition key → `event-driven-kafka` |

### Example — Layer 3 (Postgres RLS)

```sql
ALTER TABLE records ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON records
  USING       (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK  (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

The service sets `SET LOCAL app.tenant_id = ?` at transaction start — the token claim alone never reaches the DB. An admin bypass (e.g. a `BYPASSRLS` role for `/admin/*`) must be a **separate, narrowly-scoped role**, and **every bypassed query is logged to the audit log**.

### Example — Layer 4 (OLAP query gateway)

A columnar/analytical store often has no row-level security. Two protections: lead the table's sort key with the tenant (`ORDER BY (tenant_id, ...)`, making the filter cheap), and route **all access through a gateway** that fails closed:

```python
class AnalyticsClient:
    def query(self, sql, tenant_id, params=None):
        if not self._has_tenant_filter(sql, tenant_id):
            raise QueryWithoutTenantFilter(f"Query missing tenant_id={tenant_id} filter")
        return self._raw_client.execute(sql, params or {})
```

Direct driver calls that bypass the gateway are a security incident.

## Beyond the data path — same key everywhere

- **Cache keys** are tenant-prefixed; **object-store paths** are tenant-/brand-scoped — a per-tenant prefix (`s3://bucket/<brand>/…`) **plus, where the regime requires hard cryptographic separation, a per-tenant/per-brand KMS key** so one tenant's data is unreadable with another's key (and a leaked key blasts one tenant, not all). Bucket policies + IAM scope access to the prefix (`caching-strategy`, `security-baseline`).
- **Lakehouse + warehouse governance:** on an Iceberg/Glue lakehouse, enforce row/column policies at the catalog with **AWS Lake Formation** (FGAC) so the *same* policy holds across every engine (Spark/Trino/Athena/StarRocks). On the OLAP serving engine, use its row-filter mechanism where it has one (**StarRocks via Apache Ranger / catalog-centric Lake Formation** — it has **no native row-policy DDL**), and make the **Analytics API the sole tenant path** (no tenant gets direct warehouse credentials; the API injects the tenant predicate, the catalog/Ranger filter is the backstop). See `starrocks-olap`, `lakehouse-iceberg`.
- **Logs / metrics / traces** carry the tenant in the correlation ID (`observability`).
- **Tool / RPC interceptors** reject requests missing the tenant header.
- **Any semantic-retrieval / vector store** filters by tenant on every retrieval (see `examples/brain-instantiation/` for a worked example).

## Roles (RBAC)

Define a small, ordered role hierarchy in the Canon (e.g. `viewer < analyst < partner(scoped) < operator < owner`) where each role's allowed action-classes are explicit. Enforce the per-action-class approval matrix in the **application use-case layer**, never an ad-hoc in-process map. See `auth-and-access`.

## Cross-tenant benchmarks + partner access

- **Partner/agency cross-tenant access is an explicit, role-gated grant — never implicit.** A partner user sees tenant X only if its owner granted it; enforced at every layer; every action tagged.
- **Cross-tenant portfolio queries + benchmarks** run through a dedicated aggregation pipeline that anonymizes/aggregates with a **minimum-cohort threshold (k-anonymity, k ≥ the Canon's floor)**, enforced as a `CHECK`/guard so a benchmark can **never** expose another tenant's raw row (`compliance-engine`).

## Anti-patterns (each is a potential P0 leak)

- Trusting the token claim without the service-side assertion (the service-boundary layer skipped).
- A transactional query/table without a row-security policy, or forgetting to set the tenant GUC.
- An analytical query that bypasses the gateway or omits the tenant predicate.
- An event without the tenant on its envelope, or a consumer that doesn't assert it.
- A cache key, object-store path, log line, or metric without tenant scoping.
- A cross-tenant benchmark that returns a competitor's raw values, or a cohort below the k floor.
- A mutation without the role check; an implicit (un-granted) partner cross-tenant view.
- An admin/bypass role used outside its narrow scope or without an audit entry.

## Verify

- For a new tenant endpoint: a token for tenant A **cannot** read/write tenant B's data (fails closed) — at the service layer AND via row security AND via the analytical gateway. The test runs under the **real** security context (not bypassed) and fails when the protection is removed.
- New analytical calls go through the gateway; new events include the tenant; new mutations call the role check.
- A benchmark query never returns a single-tenant row; the cohort guard rejects counts below the k floor.

## References

- Product Canon — `INVARIANTS.md` (isolation invariant), `STACK.md` (per-layer mechanism), `COMPLIANCE.md` (residency/segregation)
- `engineering-os-blueprint/05-engineering-standards.md` — isolation as a cross-cutting standard
- `auth-and-access` · `data-layer` · `clickhouse-olap` · `event-driven-kafka` · `security-baseline` · `compliance-engine`
