---
name: task-tracker-integration
description: Tool-agnostic task tracker patterns (ClickUp/Linear/GitHub Projects/Jira) — every spec maps 1:1 to tasks; opt-in per env var; if none configured, log to memory/tasks-pending.log and continue.
---

# Task Tracker Integration

Pick one tracker. The OS works with any. **No tracker is required.**

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
        └── Subtasks (2-5 min each, per writing-plans)
            status: BACKLOG → IN_BUILD → IN_REVIEW → IN_QA → READY → DEPLOYED → DONE
```

Map onto your tracker: ClickUp (Space→Folder→List→Task→Subtask); Linear (Team→Project→Issue→Sub-issue); GitHub Projects (Project→Item status column); Jira (Project→Epic→Story→Sub-task).

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
| Shreya | APPROVED / NEEDS FIXES | IN_SECURITY → IN_QA / → IN_BUILD |
| Tanvi | PASS / FAIL | IN_QA → READY / → IN_BUILD |
| Jatin | Deploy complete | READY → DEPLOYED |
| Any | Unresolvable | * → BLOCKED |

## Custom fields (set on every task)

| Field | What |
|---|---|
| `feature_slug` | Links task ↔ `memory/specs/<slug>.md` |
| `spec_path` / `design_path` / `adr_link` | `memory/specs|designs|decisions/...` |
| `platform` | `web` \| `mobile` \| `api-gateway` \| `core-service` \| `notifications-service` \| `ingestion-service` \| `analytics-service` \| `intelligence-service` \| `lifecycle-service` \| `infra` |
| `owner_agent` | `priya` \| `rohan` \| `aryan` \| `vikram` \| `ananya` \| `karan` \| `maya` \| `shreya` \| `tanvi` \| `jatin` \| `learning-retro` |
| `mode` | `SPEED` \| `SCALE` |
| `sev` | `P0` \| `P1` \| `P2` \| `P3` |

## Task Title Convention

```
[<AGENT>][<platform>] <verb> <object> in <file>
```

Examples: `[VIKRAM][api-gateway] Add 'ads.spend.adjust' tRPC mutation in apps/api-gateway/src/trpc/routers/ads.ts` · `[ANANYA][web] Wire <CohortHeatmap/> in apps/web/components/charts/cohort-heatmap.tsx` · `[MAYA][analytics-service] Add mer_daily_mv MV in apps/analytics-service/src/materializations/mer_daily_mv.sql` · `[MAYA][lifecycle-service] Add 09:00–21:00 IST calling-hours guard in apps/lifecycle-service/src/compliance/calling_hours.py`

## Idempotency

Match by `feature_slug`. If a task with the same slug exists, update fields rather than create a duplicate.

## Graceful degradation (no tracker configured — the DEFAULT state)

If no tracker env vars are set, agents proceed without blocking; each intended call → one line in `memory/tasks-pending.log`:
```
2026-05-12T10:00:00Z create_task list=specs slug=<feature-slug> title="..." owner=priya
2026-05-12T10:02:00Z update_status task=<slug> from=BACKLOG to=IN_BUILD
```
`/sync-tracker` replays the log when connectivity returns. The plugin does NOT require any tracker.

## Anti-patterns

- ❌ Creating tasks without `feature_slug` (can't trace to spec)
- ❌ Big "Implement X" tasks (split per `writing-plans`)
- ❌ Hardcoding one tracker's name in agent prose — use generic "tracker"
- ❌ Blocking the pipeline when the tracker is unreachable — log and continue
