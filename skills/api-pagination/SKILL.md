---
name: api-pagination
description: Cursor pagination for every Brain list endpoint — tRPC, gRPC, MCP tools. Offset is banned in prod paths. Use when adding any new list endpoint (orders, customers, decision_log, audiences, integrations.list_orders), when an OFFSET-based endpoint slows down, when shipping infinite-scroll UI.
---

# API Pagination

Brain ships **cursor pagination** for every list endpoint. OFFSET is banned in production paths — it scans the rows it discards, so page 50 of a tenant's audit log is 50× slower than page 1.

## Strategies — pick by use case

| Strategy | Brain use | Performance | When |
|---|---|---|---|
| **Cursor (keyset)** | Default for every list endpoint | O(1) per page | Orders list, audit log, decision log, customers, audiences, integration data |
| **OFFSET / LIMIT** | Admin tooling only | O(n) | Internal admin pages with bounded data; never in tenant-facing endpoints |
| **Sliding window over time** | Time-series views | O(1) per window | Cohort heatmap, daily metrics; not really pagination — windowed reads |

## The Brain pattern (tRPC + cursor)

```typescript
import { z } from 'zod';
import { protectedProcedure, router } from '@/server/trpc';

const listInput = z.object({
  cursor: z.string().datetime().nullish(),  // ISO timestamp from previous page's last item
  limit:  z.number().min(1).max(200).default(50),
  // (filters, sorts, etc.)
});

export const ordersRouter = router({
  list: protectedProcedure.input(listInput).query(async ({ ctx, input }) => {
    const rows = await ctx.db.query(
      `SELECT id, gross_revenue, currency, created_at
       FROM orders
       WHERE workspace_id = current_setting('app.workspace_id')::uuid
         AND ($1::timestamptz IS NULL OR created_at < $1)
       ORDER BY created_at DESC, id DESC
       LIMIT $2`,
      [input.cursor ?? null, input.limit + 1],   // fetch +1 to detect hasMore
    );

    const hasMore = rows.length > input.limit;
    const data    = hasMore ? rows.slice(0, input.limit) : rows;
    const next    = hasMore ? data.at(-1)!.created_at.toISOString() : null;

    return { data, nextCursor: next };
  }),
});
```

The cursor is the **last item's sort key** — for `ORDER BY created_at DESC` it's the `created_at` of the last row. For ties (multiple rows with same `created_at`), use a compound cursor of `(created_at, id)`.

## Composite cursor (when timestamps tie)

```typescript
// Compound cursor encoded as base64 JSON
function encodeCursor(row: { created_at: Date; id: string }) {
  return Buffer.from(JSON.stringify({ t: row.created_at.toISOString(), i: row.id })).toString('base64url');
}
function decodeCursor(c: string) {
  return JSON.parse(Buffer.from(c, 'base64url').toString()) as { t: string; i: string };
}

// SQL: keyset condition handles ties
const q = `
  SELECT ... FROM orders
  WHERE workspace_id = current_setting('app.workspace_id')::uuid
    AND ($1::timestamptz IS NULL OR (created_at, id) < ($1, $2))
  ORDER BY created_at DESC, id DESC
  LIMIT $3
`;
```

Use this for high-write tables where multiple rows can share a `created_at` value (decision_log, raw events).

## ClickHouse pagination (Maya)

For ClickHouse, cursors are cheap when the `ORDER BY` matches the primary key.

```sql
SELECT event_id, event_ts, payload
FROM events
WHERE workspace_id = 'xxxx-...'
  AND (event_ts, event_id) < ({cursor_ts: DateTime64}, {cursor_id: String})
ORDER BY event_ts DESC, event_id DESC
LIMIT 50;
```

For drill-downs returning more than 5k rows, ClickHouse will read multiple parts — prefer **server-side aggregation** before paginating, never pull raw points to the client.

## MCP tool pagination

MCP tools (see canon/BRAIN_TECHNICAL.md) that return lists follow the same shape; the cursor is in the response envelope:

```typescript
// MCP tool: integrations.list_orders
return {
  data: [...orders],
  pagination: { nextCursor: '...' },   // null when no more
};
```

External MCP clients (Claude native, partner integrations) honor `nextCursor` the same way internal callers do.

## Response shape (canonical, applies to tRPC + MCP)

```json
{
  "data": [ {...}, {...} ],
  "nextCursor": "2026-05-15T12:34:56.789Z",
  "hasMore": true
}
```

For the BFF (Next.js Server Components), TanStack Query's `useInfiniteQuery` consumes `nextCursor` directly:

```tsx
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['orders', filters],
  queryFn: ({ pageParam }) => trpc.orders.list.query({ cursor: pageParam, ...filters }),
  getNextPageParam: (last) => last.nextCursor,
  initialPageParam: null,
});
```

## Best Practices

- **Cursor always**, OFFSET never (in prod tenant-facing endpoints).
- **Max limit 200**, default 50. Never accept "unlimited."
- **Sort column must be indexed** — and the index must include `workspace_id` first.
- **Stable ordering** — use a compound cursor `(timestamp, id)` for tables where ties are possible.
- **Don't return total count** unless the UI specifically needs it. `COUNT(*)` over a multi-million-row table is expensive; cursor pagination doesn't need it.
- **For the UI: "load more" or infinite scroll, not "page X of Y"**, because cursors don't have stable page numbers.

## Anti-patterns

| Anti-pattern | Why it fails in Brain |
|---|---|
| `OFFSET 5000 LIMIT 50` on decision_log | Scans 5050 rows for a tenant page-100 read; times out at scale |
| `SELECT COUNT(*)` for "show 2,341,892 results" | `COUNT(*)` over a multi-million-row table without a `WHERE` predicate is full-scan |
| Page numbers in URLs (`?page=5`) | Cursors aren't stable page numbers; bookmarked URLs break when data shifts |
| Returning row IDs as the only cursor | Ordering by `id` doesn't match the user's mental model (chronological); use `created_at` |
| Allowing `limit=10000` "because the customer asked" | One bad client request can blow the BFF budget for everyone in the cluster |

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| tRPC list endpoints | **Vikram** | canon/BRAIN_TECHNICAL.md (list endpoints) |
| MCP tool list responses | **Vikram** + **Maya** | canon/BRAIN_TECHNICAL.md |
| ClickHouse drill-down pagination | **Maya** | canon/BRAIN_TECHNICAL.md + `clickhouse-olap` |
| TanStack Query `useInfiniteQuery` consumption | **Ananya** | canon/BRAIN_TECHNICAL.md |
| Mobile infinite scroll | **Karan** | canon/BRAIN_TECHNICAL.md |

Related Brain skills: `sql-query-optimization` (cursor needs the right index), `database-design` (schema decisions), `mcp-protocol` (tool response envelopes).
