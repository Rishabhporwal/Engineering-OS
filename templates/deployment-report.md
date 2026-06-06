# Deployment Report — {{REQ_ID}}

> Filled by the Platform/SRE Engineer in Stage 8.
> Validates against [schemas/deployment.schema.json](../schemas/deployment.schema.json).
> Updated at three checkpoints: after CI, after staging, after the 48h monitor.

| Field | Value |
|-------|-------|
| **req_id** | `{{REQ_ID}}` |
| **Actor** | platform-devops |
| **Timestamp (latest update)** | {{TS}} |
| **Deploy class** | **{{DEPLOY_CLASS}}**  *(service / library / mobile / infra / docs-config)* |

---

## 0. Deploy class (fast-path)

Declare the **deploy class first** — it determines which sections apply. Sections that don't apply to the class are legitimately **N/A — out of scope** with a one-line reason (don't fabricate continuous-delivery/canary detail for a change that has none). The concrete deploy tooling for each seam is bound in the Product Canon's STACK.md.

| Class | What ships | Sections that apply | Sections N/A |
|---|---|---|---|
| **service** | a backend/edge service (per the service map in STACK.md) | §1 CI · §2 staging · §3 prod (continuous-delivery sync + canary) · §4 monitor · §5 dashboards | — |
| **library** | a shared package (per the package layout in STACK.md — e.g. the metric registry) consumed by services | §1 CI (lint/typecheck/test/build + **metric-parity if the registry changed**) · §4 monitor of the **consuming services** · §5 only if a new metric/panel is emitted | §2/§3 deploy sync + canary — **no independent deploy; ships with the next build of its consuming service(s) — name them in §3** |
| **mobile** | the mobile app (per STACK.md) | §1 CI · mobile build/submit + OTA-vs-native decision (note in §3) · §4 monitor (crash-free rate) | continuous-delivery/canary (mobile uses its own release pipeline) |
| **infra** | infrastructure-as-code (per STACK.md) | §1 CI · infra plan/apply (note in §3) · §4 monitor | app canary; dashboards unless infra adds them |
| **docs-config** | docs / config only | §1 CI (lint) | §2–§5 — no runtime deploy |

> **Library fast-path:** a shared-package change has **no deploy sync of its own**. Verify CI green (incl. metric-parity if the registry changed), record which **consuming services** will pick it up on their next deploy (§3), point the 48h monitor at those services, and mark §2 + §3-canary **N/A — ships with consuming service**.

> **New-service + affected-scope gate (service class):** if this is a **NEW service**, confirm its CI/CD pipeline + its **own deploy unit** were created with it (the day-one rule — never retrofitted). Confirm the deploy was **affected-scoped**: only the changed service + its transitive dependents were built/pushed/synced (via the build graph's affected-detection), **not a deploy-all** of the repo.

---

## 1. CI run

| Field | Value |
|-------|-------|
| **Pipeline** | {{CI_PIPELINE}} |
| **URL** | {{CI_URL}} |
| **Outcome** | **{{CI_OUTCOME}}** |
| Lint | {{CI_LINT}} |
| Typecheck | {{CI_TYPECHECK}} |
| Test | {{CI_TEST}} |
| Build | {{CI_BUILD}} |
| Artifact/image push to registry | {{CI_IMAGE_PUSH}} |

---

## 2. Staging deploy

| Field | Value |
|-------|-------|
| **Deploy sync** | {{ARGO_STAGING_SYNC}} |
| **Smoke** | {{STAGING_SMOKE}} |
| **Metric parity** | {{STAGING_METRIC_PARITY}} |
| **Dashboard sanity** | {{STAGING_DASHBOARD_SANITY}} |
| **Alarm wiring sanity** | {{STAGING_ALARM_SANITY}} |

### Staging verification commands
- `{{STAGING_VERIFY_CMD_1}}`
  → {{STAGING_VERIFY_OUT_1}}
- `{{STAGING_VERIFY_CMD_2}}`
  → {{STAGING_VERIFY_OUT_2}}

---

## 3. Production deploy

| Field | Value |
|-------|-------|
| **Deploy sync** | {{ARGO_PROD_SYNC}} |
| **Strategy** | {{DEPLOY_STRATEGY}}  *(all-at-once / canary-10 / canary-25 / canary-50)* |
| **Canary started at** | {{CANARY_START}} |
| **Canary promoted at** | {{CANARY_PROMOTE}} |

### Rollback plan (pre-recorded)
{{ROLLBACK_PLAN}}

---

## 4. 48h post-deploy monitor

| Field | Value |
|-------|-------|
| **Status** | **{{MONITOR_STATUS}}**  *(clean / alarm-fired / rolled-back / in-progress)* |
| **Rollback triggered?** | {{ROLLBACK_TRIGGERED}} |
| **Rollback reason** | {{ROLLBACK_REASON}} |
| **p95 latency observed (ms)** | {{P95_LATENCY}} |
| **Error rate observed (%)** | {{ERROR_RATE}} |

### Auto-rollback triggers (active)
- p95 latency > 2s for 5 min → roll back
- Error rate > 1% for 5 min → roll back
- Health check failing 2 consecutive probes → roll back

---

## 5. Dashboard + alarms

- **Dashboard URL:** {{DASHBOARD_URL}}
- **New panels added:** {{DASHBOARD_PANELS_ADDED}}
- **New alarms registered:** {{ALARMS_REGISTERED}}

---

## 6. Release notes

> Human-readable summary suitable for the Stakeholder + a user-facing changelog (auto-generated).

{{RELEASE_NOTES}}

---

## 7. Runbook

> Operational runbook for this change. What to do if it breaks.

{{RUNBOOK_LINK_OR_INLINE}}

---

## 8. Final journal entry (Platform/SRE)

> Posted to `.engineering-os/memory/agents/platform.journal.md`.

```markdown
## {{TS}} — platform-devops — {{REQ_ID}} — SHIPPED
**Stage:** 8 (deploy + monitor)
**Action:** Production deploy completed via the deploy pipeline (strategy: {{DEPLOY_STRATEGY}}). 48h monitor: {{MONITOR_STATUS}}.
**Dashboards:** {{DASHBOARD_URL}}
**Release notes:** see deployment-report.md §6.
```
