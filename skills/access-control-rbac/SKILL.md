---
name: access-control-rbac
description: Role-based access control for Brain — Owner/Admin/Analyst/Viewer per workspace + agency multi-workspace context. Enforce in Supabase Auth JWT claims + Postgres RLS, never in an in-process map. Use when adding a new permission, when designing an admin endpoint, when wiring an MCP tool's scope, when an agency user needs cross-brand access.
---

# Access Control (RBAC)

Brain has multiple authorization surfaces (Owner approves consent transitions; Analyst can read but not adjust ad-spend; Agency user manages N brands). This skill is the canonical pattern: **JWT claims + Postgres RLS + MCP tool scopes**, enforced structurally — never as application-level if-statements.

## Why this matters for Brain

| Surface | Authorization concern |
|---|---|
| Web dashboard (tRPC) | Analyst sees revenue but can't change campaign budget; Admin can; Owner can approve agency invitations |
| MCP write tools (TECH/13) | Each tool declares required scope; external partner keys are scoped (read-only by default) |
| Outbound writebacks (Sahil → vendor) | Some brands disable writebacks entirely; per-brand toggle |
| Decision Log "approver" field | Owner-only actions audit-logged with actor |
| Agency multi-workspace | One user → N workspaces with different roles in each |

## Brain role model (canonical)

| Role | Within a workspace, can… |
|---|---|
| **Owner** | Everything. Approve consent transitions, approve agency invites, change billing, delete the workspace. (Usually = the brand's founder.) |
| **Admin** | Everything except billing + workspace deletion. Approve writebacks, change integration configs, manage members. |
| **Analyst** | Read all data. Trigger ad-hoc reports. Cannot mutate (no campaign budget changes, no audience triggers, no outbound). |
| **Viewer** | Read dashboards. No drill-down to PII. (Used for read-only stakeholder access.) |
| **Service Bot** (internal) | Per-task IAM via Supabase service role; bypasses RLS for backfills + scheduled jobs. |

**Agency context:** an agency user has rows in `workspace_members` for each brand they manage, with potentially-different roles. The JWT carries the **current** workspace_id + role for the active session; switching workspaces refreshes the session.

## Enforce in JWT + RLS — NOT in application code

```sql
-- The single source of truth for who-can-see-what
CREATE TABLE workspace_members (
  workspace_id UUID NOT NULL,
  user_id      UUID NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'analyst', 'viewer')),
  invited_by   UUID,
  joined_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);

ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY rls_members ON workspace_members
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

Supabase trigger writes `app_metadata.workspace_id` and `app_metadata.role` into the JWT when the user signs in or switches workspace. The api-gateway preHandler verifies the JWT and sets `app.workspace_id` + `app.role` as Postgres session GUCs (see `session-management`).

```typescript
// preHandler in api-gateway
await db.query("SELECT set_config('app.workspace_id', $1, true), set_config('app.role', $2, true)",
  [req.workspaceId, req.role]);
```

## Permission checks at the tRPC layer

Application code does NOT compute "can the user do this?" — it asserts the role and lets RLS or service logic enforce.

```typescript
// procedureFactory: createProcedure(requiredRole)
import { TRPCError, initTRPC } from '@trpc/server';

const t = initTRPC.context<Context>().create();

function requireRole(roles: Array<'owner'|'admin'|'analyst'|'viewer'>) {
  return t.middleware(({ ctx, next }) => {
    if (!roles.includes(ctx.role)) {
      throw new TRPCError({ code: 'FORBIDDEN', message: `Required role: ${roles.join('|')}` });
    }
    return next();
  });
}

export const ownerProcedure   = t.procedure.use(requireRole(['owner']));
export const adminProcedure   = t.procedure.use(requireRole(['owner', 'admin']));
export const analystProcedure = t.procedure.use(requireRole(['owner', 'admin', 'analyst']));
export const viewerProcedure  = t.procedure.use(requireRole(['owner', 'admin', 'analyst', 'viewer']));
```

```typescript
// Usage — the procedure declares the role; RLS is the structural bottom
export const adsRouter = router({
  spend: router({
    list:   analystProcedure.query(/* ... */),                  // analyst+ can read
    adjust: adminProcedure.input(adjustInput).mutation(/* ... */),  // admin+ can write
  }),
  consent: router({
    grant:  ownerProcedure.input(consentInput).mutation(/* ... */),  // owner-only
  }),
});
```

If a future bug skips the middleware, RLS + the Decision Log audit still catch it (`defense-in-depth-validation`).

## MCP tool scopes (TECH/13)

Each MCP write tool declares the role it requires; external partner API keys carry scopes (read-only by default; write scopes require Owner approval).

```typescript
mcp.registerTool({
  name: 'analytics.waterfall.compute.v2',
  description: '...',
  inputSchema: WaterfallV2Input,
  requiredScope: 'analytics:read',          // partner key needs this scope
  requiredRole: 'analyst',                  // internal call needs this role
  handler: async (input, ctx) => { /* ... */ },
});

mcp.registerTool({
  name: 'ads.spend.adjust',
  requiredScope: 'ads:write',
  requiredRole: 'admin',
  handler: async (input, ctx) => { /* ... */ },
});
```

The MCP server middleware rejects tool calls that don't satisfy both checks. Decision Log entries record who invoked which tool with what scope/role.

## Agency multi-workspace pattern

```sql
-- An agency user is just a user with rows in multiple workspaces
SELECT workspace_id, role
FROM workspace_members
WHERE user_id = current_user_id();

-- Returns:
-- workspace_id | role
-- w_sugandh    | admin
-- w_brand2     | analyst
-- w_brand3     | owner
```

Switching workspace in the UI hits `/api/auth/switch-workspace?id=...` which:
1. Verifies the user has a row in `workspace_members` for that workspace
2. Re-issues the JWT with the new `app_metadata.workspace_id` + `role`
3. Re-sets the auth cookies

The Supabase admin API + Brain's switch-workspace endpoint are the only places that mutate session workspace.

## Audit every change (Decision Log)

```sql
-- Every role change, member add/remove, scope grant goes to the Decision Log
INSERT INTO ai.decision_log (workspace_id, actor, action, target, payload, paradigm)
VALUES ($1, $2, 'workspace.member.role_change',
        $3,                                                  -- target user_id
        jsonb_build_object('from_role', $4, 'to_role', $5),
        'sql');
```

The audit is also what makes the system reviewable for SOC 2 T1 (Phase 4).

## Best Practices

**Do:**
- **Apply least privilege** — start every new role at Viewer, escalate only on need
- **Use role hierarchies** (`admin` ⊃ `analyst` ⊃ `viewer`) to reduce duplication in middleware
- **Audit every access change** — role grant, scope grant, member add — Decision Log row
- **Review quarterly** — list every role on every workspace; remove anyone who shouldn't be there
- **Cache role-check decisions per request** (in `ctx`), not across requests
- **Separate authentication from authorization** — Supabase Auth answers "who"; RBAC answers "can they"

**Don't:**
- **Hardcode permission checks deep in business logic** — they belong in tRPC middleware + RLS, not inside `adsRepository.adjust()`
- **Allow permission creep without review** — Owner gets everything by definition; everyone else needs an explicit grant
- **Use overly broad wildcards** like `permissions: ['*']` — only `Owner` is wildcard
- **Skip audit logging** for role changes — auditors will fail you on SOC 2 if it's missing
- **Trust the client about role** — always re-derive from the verified JWT server-side

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| Role taxonomy + middleware | **Vikram** + **Shreya** | TECH/06 §"Auth" + this skill |
| Postgres RLS policy review | **Shreya** + Aryan | TECH/09 §"Multi-tenancy" |
| MCP tool scope catalogue | **Vikram** + **Maya** | TECH/13 §"Scopes" |
| Agency multi-workspace flow | **Vikram** + **Ananya** | TECH/06 + TECH/07 |
| Audit + SOC 2 prep (Phase 4) | **Shreya** + Jatin | TECH/09 §"Audit" |

Related Brain skills: `session-management` (JWT + cookies), `defense-in-depth-validation` (layer 2 + 3), `security-baseline` (broader posture), `mcp-protocol` (tool scopes).
