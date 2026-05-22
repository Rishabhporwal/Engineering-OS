---
name: multi-tenancy-isolation
description: Brain's tenant-isolation contract (technical-requirements §6 + canon/TECH/09 + TECH/01) — workspace_id = tenant = brand = billing unit, enforced at FOUR layers (JWT claim → api-gateway service-side assertion + requireRole on every mutation → Postgres RLS via SET LOCAL app.workspace_id → ClickHouse query-gateway rejecting un-scoped queries). Redis keys + S3 paths workspace-scoped; Kafka partition key = workspace_id + consumer asserts it; cross-brand benchmarks aggregate-only k≥5; the 5-role model; org→workspace→integration hierarchy + Models A/B/C/D. A single missed layer is a cross-brand data leak — P0, Shreya VETO, SLO 0 leaks. Use on ANY endpoint, query, event, MCP tool, or cache key that touches tenant data.
---

# Multi-Tenancy & Data Isolation

**Tenant = `workspace_id` = brand = billing unit** (technical-requirements §6). A cross-brand leak is the single worst thing Brain can do — **P0, a Shreya VETO surface, SLO = 0 leaks.** Isolation is **defense in depth: four layers, all required.** A single missed layer is a leak.

**Canonical sources:** `canon/technical-requirements.md` §6 · `canon/TECH/09_security_observability.md` · `canon/TECH/01_data_architecture.md` §5.

## The hierarchy

```
Organisation → Brand/Workspace → Store/Channel/Integration → records
```

Workspace = tenant = brand = billing unit. **Account models** (business §3.4): **A** single brand = single workspace (default); **B** one org owns many brands (each isolated); **C** agency-managed (scoped per-brand grant, every action tagged + audited); **D** enterprise overlay (residency, stricter isolation). Portfolio/benchmark views aggregate workspaces only via explicit permission + anonymized/scoped queries.

## The four enforcement layers (all required)

| # | Layer | Enforcement | Where |
|---|---|---|---|
| 1 | **JWT claim** | Supabase token carries `active_workspace_id`, `role`, accessible-workspace list | [`auth-and-access`](../auth-and-access/SKILL.md) |
| 2 | **api-gateway service-side assertion** | validates JWT; asserts `active_workspace_id` matches the requested workspace; propagates `workspace_id`/`user_id`/`request_id` via gRPC metadata; **`requireRole(ctx, ws, minRole)` on every mutation** | api-gateway (Vikram) |
| 3 | **Postgres RLS** | `SET LOCAL app.workspace_id = ?` at txn start; policy on every workspace-scoped table | [`database-design`](../database-design/SKILL.md) |
| 4 | **ClickHouse query gateway** | `pylibs/brain_clickhouse` rejects any query lacking a `workspace_id` predicate (CH has **no RLS**) | [`clickhouse-olap`](../clickhouse-olap/SKILL.md) |

### Layer 3 — Postgres RLS

```sql
ALTER TABLE orders_recent ENABLE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON orders_recent
  USING       (workspace_id = current_setting('app.workspace_id', true)::uuid)
  WITH CHECK  (workspace_id = current_setting('app.workspace_id', true)::uuid);
```

The service sets `SET LOCAL app.workspace_id = ?` at transaction start — the JWT claim alone never reaches the DB. (Brain Admin `/admin/*` uses a separate `app_admin` role with `BYPASSRLS`; **every BYPASSRLS query is logged to `audit_log`**.)

### Layer 4 — ClickHouse query gateway

ClickHouse has no Postgres-style RLS. Two protections: `ORDER BY (workspace_id, ...)` leads every table (makes the filter O(log n)), and **all access goes through the gateway**:

```python
class ClickHouseClient:
    def query(self, sql, workspace_id, params=None):
        if not self._has_workspace_filter(sql, workspace_id):
            raise QueryWithoutTenantFilter(f"Query missing workspace_id={workspace_id} filter")
        return self._raw_client.execute(sql, params or {})
```

Direct `clickhouse_driver` calls that bypass the gateway are a security incident.

## Beyond the four layers — same key everywhere

- **Redis keys** are `workspace_id`-prefixed; **S3 paths** are workspace-scoped ([`caching-strategy`](../caching-strategy/SKILL.md)).
- **Kafka:** every event envelope carries `workspace_id`; **partition key IS `workspace_id`** (per-workspace ordering, required for version dedup); consumers **assert** `workspace_id` from the envelope ([`event-driven-kafka`](../event-driven-kafka/SKILL.md)).
- **MCP tools** share api-gateway auth/tenancy and do a tenant check; **gRPC** `TenancyInterceptor` rejects requests missing `x-workspace-id`.
- **Logs/metrics/traces** carry `workspace_id` in the correlation ID.
- **Memory Layer** vectors filter `workspace_id` on every retrieval ([`memory-layer-pgvector`](../memory-layer-pgvector/SKILL.md)).

## The 5-role model (RBAC — canonical R2)

`viewer (1)` < `analyst (2)` < `agency (3, scoped + tagged)` < `operator (4)` < `owner (5)`. Owner: billing/integrations/auto-execute/delete. Operator: operational write, approve/reject, lifecycle, inbox (no billing/delete). Analyst: read + comment + goals/alerts (no approvals/execution). Agency: scoped per-brand grant, every action tagged + audited. Viewer: read-only, no PII, no exports, no actions. The per-action-class approval matrix is enforced in `application/` use-cases — never in an in-process map.

## Cross-brand benchmarks + agency access

- **Agency cross-brand access is an explicit, role-gated grant — never implicit.** An agency user sees brand X only if Owner granted it; enforced at all four layers; every action tagged.
- **Cross-brand portfolio queries + benchmarks** run through a dedicated aggregation pipeline that anonymizes/aggregates with **k-anonymity k≥5** (`ai.cross_brand_pattern.brand_count CHECK (>= 5)`). A benchmark must **never** expose another brand's raw row ([`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md)).

## Anti-patterns (each is a potential P0 leak)

- Trusting the JWT claim without the service-side assertion (layer 2 skipped).
- A Postgres query/table without an RLS policy, or forgetting `SET LOCAL app.workspace_id`.
- A ClickHouse query that bypasses the gateway or omits the `workspace_id` predicate.
- A Kafka event without `workspace_id` in the envelope, or a consumer that doesn't assert it.
- A cache key, S3 path, log line, or metric without `workspace_id` scoping.
- A cross-brand benchmark that returns a competitor's raw values, or a pattern below k=5.
- A mutation without `requireRole`; an implicit (un-granted) agency cross-brand view.
- BYPASSRLS used outside `/admin/*` or without an audit entry.

## Verify

- For a new tenant endpoint: a token for workspace A **cannot** read/write workspace B's data (fails closed) — at the service layer AND via RLS AND via the CH gateway.
- New ClickHouse calls go through `brain_clickhouse.query`; new events include `workspace_id`; new mutations call `requireRole`.
- A benchmark query never returns a single-brand row; `cross_brand_pattern` rejects `brand_count < 5`.

## References

- `canon/technical-requirements.md` §6 — hierarchy, roles, four-layer enforcement
- `canon/TECH/09_security_observability.md` — auth, roles, defense-in-depth, admin BYPASSRLS + impersonation
- `canon/TECH/01_data_architecture.md` §5 — Postgres RLS + ClickHouse gateway code
- [`security-baseline`](../security-baseline/SKILL.md) · [`database-design`](../database-design/SKILL.md) · [`clickhouse-olap`](../clickhouse-olap/SKILL.md) · [`event-driven-kafka`](../event-driven-kafka/SKILL.md)
