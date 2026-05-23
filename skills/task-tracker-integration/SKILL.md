---
name: task-tracker-integration
description: Task tracker integration patterns — works with ClickUp, Linear, GitHub Projects, or Jira. Every feature spec maps 1:1 to tasks in whichever tracker the project uses. Opt-in via env var per tracker; if none configured, agents log intended actions to memory/tasks-pending.log and continue without blocking. Tool-agnostic by design.
---

# Task Tracker Integration

Pick one tracker. The OS works with any of them. **No tracker is required.**

| Tracker | Env vars | MCP package |
|---|---|---|
| ClickUp | `CLICKUP_API_KEY`, `CLICKUP_TEAM_ID` | `@taazkareem/clickup-mcp-server` |
| Linear | `LINEAR_API_KEY` | `@tacticlaunch/mcp-linear` |
| GitHub Projects | `GITHUB_TOKEN` with `project` scope | `@modelcontextprotocol/server-github` |
| Jira | `JIRA_HOST`, `JIRA_API_TOKEN`, `JIRA_EMAIL` | `@aaronsb/mcp-jira` (or similar) |

MCPs are declared in `.mcp.json` and auto-load when env vars are present. **If no tracker is configured, agents skip tracker calls silently** and log intended actions to `memory/tasks-pending.log`. Run `/sync-tracker` to drain when connectivity returns.

## Canonical Hierarchy (vendor-agnostic)

```
Workspace / Team
└── Project / Folder: Engineering
    └── Epic = one feature (created by Priya at /spec)
        └── Subtasks (2-5 min each, per writing-plans skill)
            status flow: BACKLOG → IN_BUILD → IN_REVIEW → IN_QA → READY → DEPLOYED → DONE
```

Map onto your tracker's primitives:
- ClickUp: Space → Folder → List → Task → Subtask
- Linear: Team → Project → Issue → Sub-issue
- GitHub Projects: Project → Item (status column)
- Jira: Project → Epic → Story → Sub-task

## Status flow (universal)

```
BACKLOG → IN_BUILD → IN_SECURITY (if auth/PII) → IN_QA → READY → DEPLOYED → DONE
                                                       ↓
                                                  FAILED_QA → IN_BUILD (loop)
                                                       ↓
                                                  BLOCKED (any status → BLOCKED)
```

| Agent | Action | Transition |
|---|---|---|
| Priya | Creates Epic + subtasks | → BACKLOG |
| Aryan | Hands off to builders | → IN_BUILD |
| Builders | Starts/finishes subtask | BACKLOG → IN_BUILD → IN_QA (or IN_SECURITY) |
| Shreya | APPROVED | IN_SECURITY → IN_QA |
| Shreya | NEEDS FIXES | IN_SECURITY → IN_BUILD (loop) |
| Tanvi | PASS | IN_QA → READY |
| Tanvi | FAIL | IN_QA → IN_BUILD (loop) |
| Jatin | Deploy complete | READY → DEPLOYED |
| Any | Unresolvable | * → BLOCKED |

## Custom fields (set on every task)

| Field | What |
|---|---|
| `feature_slug` | Links task ↔ `memory/specs/<slug>.md` |
| `spec_path` | `memory/specs/<slug>.md` |
| `design_path` | `memory/designs/<slug>.md` |
| `adr_link` | `memory/decisions/ADR-NNN-<slug>.md` |
| `platform` | `web` \| `mobile` \| `api-gateway` \| `core-service` \| `notifications-service` \| `ingestion-service` \| `analytics-service` \| `intelligence-service` \| `lifecycle-service` \| `infra` |
| `owner_agent` | `priya` \| `rohan` \| `aryan` \| `vikram` \| `ananya` \| `karan` \| `maya` \| `shreya` \| `tanvi` \| `jatin` \| `learning-retro` |
| `mode` | `SPEED` \| `SCALE` |
| `sev` | `P0` \| `P1` \| `P2` \| `P3` |

## Task Title Convention

```
[<AGENT>][<platform>] <verb> <object> in <file>
```

Examples (Brain canon):
- `[VIKRAM][api-gateway] Add 'ads.spend.adjust' tRPC mutation in services/api-gateway/src/trpc/routers/ads.ts`
- `[ANANYA][web] Wire <CohortHeatmap/> in apps/web/components/charts/cohort-heatmap.tsx`
- `[MAYA][analytics-service] Add mer_daily_mv materialized view in services/analytics-service/src/materializations/mer_daily_mv.sql`
- `[MAYA][ingestion-service] Add Shopify orders webhook in services/ingestion-service/src/routers/webhooks.py — Verify: uv run pytest tests/test_shopify_webhook.py`
- `[MAYA][intelligence-service] Add Morning Brief synthesis with cached system prompt in services/intelligence-service/src/synthesis/morning_brief.py`
- `[MAYA][lifecycle-service] Add 09:00–21:00 IST calling-hours guard in services/lifecycle-service/src/compliance/calling_hours.py`

## Idempotency

Match by `feature_slug`. If a task with the same slug exists, update fields rather than create a duplicate.

## Graceful degradation (no tracker configured)

If no tracker env vars are set:
- Agents proceed without blocking
- Each intended tracker call → `memory/tasks-pending.log` one line:
  ```
  2026-05-12T10:00:00Z create_task list=specs slug=<feature-slug> title="..." owner=priya
  2026-05-12T10:02:00Z update_status task=<slug> from=BACKLOG to=IN_BUILD
  ```
- `/sync-tracker` replays the log when connectivity returns

This is the **default state**. The plugin does NOT require any tracker.

## Anti-patterns

- ❌ Creating tasks without `feature_slug` (can't trace to spec)
- ❌ Big "Implement X" tasks (must split per writing-plans skill)
- ❌ Hardcoding one tracker's name in agent prose — use generic "tracker"
- ❌ Blocking the pipeline when tracker is unreachable — log and continue
