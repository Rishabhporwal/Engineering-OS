---
name: testing-tdd
description: Brain's testing discipline — Vitest (Node + Web + RNTL), pytest (Python), Cypress (web E2E), Detox (mobile E2E), k6 (load — Phase 3+ 5K RPS target), real-network smoke tests (mandatory for PASS), metric registry parity (TS↔Python), cost-routing paradigm audit verification, India compliance test matrix. Auto-load whenever Tanvi or any builder is writing tests.
---

# Testing — Brain's TDD Discipline

## TDD by Mode

| Mode | Rule |
|---|---|
| SCALE | Failing test before code (Iron Law TDD). Real-network smoke before PASS. Cost-routing paradigm audit verified. India compliance matrix runs. |
| SPEED | Tests on critical business logic only. Real-network smoke still required for PASS. |

## Testing pyramid (Brain)

```
                    ▲
                    │
            E2E (Cypress + Detox)
            critical journeys only
                    │
        Integration (Supertest + pytest)
        against real Postgres + ClickHouse + Kafka (docker compose)
                    │
                Unit (Vitest + pytest)
                business logic + utilities
                    │
                    ▼
```

Plus, for any user-facing service: **real-network smoke test** (the PASS gate).

## Node unit — Vitest

```typescript
// apps/api-gateway/src/trpc/routers/store.test.ts
import { describe, it, expect, vi } from 'vitest';
import { createCaller } from './store';

describe('store.kpis', () => {
  it('returns KPIs scoped to the requested workspace', async () => {
    const caller = createCaller({
      workspaceId: 'ws-1',
      grpc: { analytics: { getDailyMetrics: vi.fn().mockResolvedValue({ rows: [...] }) } },
    });
    const result = await caller.store.kpis({ from, to });
    expect(result.rows).toHaveLength(3);
    expect(caller.grpc.analytics.getDailyMetrics).toHaveBeenCalledWith(
      expect.objectContaining({ workspace_id: 'ws-1' })
    );
  });
});
```

## Node integration — Supertest against real server

```typescript
// apps/api-gateway/test/integration/trpc.test.ts
import request from 'supertest';
import { buildServer } from '../src/main';

describe('POST /trpc/store.kpis', () => {
  let server;
  beforeAll(async () => { server = await buildServer(); await server.listen({ port: 0 }); });
  afterAll(async () => { await server.close(); });

  it('returns KPIs for valid JWT', async () => {
    const response = await request(server.server)
      .post('/trpc/store.kpis')
      .set('Authorization', `Bearer ${VALID_JWT}`)
      .send({ from: '2026-04-01', to: '2026-04-30' });
    expect(response.status).toBe(200);
    expect(response.body.result.data.rows).toBeDefined();
  });

  it('rejects cross-workspace queries', async () => {
    const response = await request(server.server)
      .post('/trpc/store.kpis')
      .set('Authorization', `Bearer ${WORKSPACE_A_JWT}`)
      .send({ workspace_id: 'workspace-b', from, to });
    expect(response.status).toBe(403);
  });
});
```

## Python unit — pytest

```python
# apps/analytics-service/tests/unit/test_metric_engine.py
import pytest
from analytics_service.metrics.amer import compute_amer

def test_amer_zero_when_no_acquisition_spend():
    rows = [{"customer_order_number": 1, "revenue_minor": 100000, "campaign_classification": "acquisition", "ad_spend_minor": 0}]
    result = compute_amer(rows)
    assert result is None  # division by zero → None

def test_amer_correct_ratio():
    rows = [
        {"customer_order_number": 1, "revenue_minor": 200000, "ad_spend_minor": 100000, "campaign_classification": "acquisition"},
    ]
    assert compute_amer(rows) == 2.0
```

## Python integration — pytest + docker compose

```python
# apps/analytics-service/tests/integration/test_daily_metrics_mv.py
import pytest
from brain_clickhouse import query

@pytest.mark.integration
async def test_daily_metrics_aggregates_orders_by_workspace(ch_client):
    await ch_client.execute("INSERT INTO orders_local VALUES (...)")  # fixture
    await asyncio.sleep(2)  # MV propagation
    result = await query(
        "SELECT sum(revenue_net_minor) FROM daily_metrics_local WHERE workspace_id = ? AND date = ?",
        ("ws-1", "2026-04-15"),
    )
    assert result[0][0] == 482000
```

## Web E2E — Cypress

```typescript
// apps/frontend/cypress/e2e/store-dashboard.cy.ts
describe('Store dashboard', () => {
  beforeEach(() => { cy.loginAsTestUser(); });

  it('loads KPIs with RAG coloring', () => {
    cy.visit('/store');
    cy.get('[data-testid="kpi-mer"]').should('be.visible');
    cy.get('[data-testid="kpi-mer-rag"]').should('have.class', 'rag-green').or('have.class', 'rag-amber').or('have.class', 'rag-red');
  });

  it('drills down on a campaign row', () => {
    cy.visit('/acquisition');
    cy.get('[data-testid="campaign-row-0"]').click();
    cy.get('[data-testid="campaign-drilldown-drawer"]').should('be.visible');
  });
});
```

## Mobile E2E — Detox (TECH/10)

```javascript
// apps/mobile/e2e/morning-brief.test.js
describe('Morning Brief', () => {
  beforeAll(async () => { await device.launchApp(); });

  it('login → push deep link → Morning Brief renders three signals', async () => {
    await element(by.id('email-input')).typeText('test@brand.com');
    await element(by.id('send-link-button')).tap();
    await device.openURL({ url: 'brain://auth/callback?token=<test>' });
    await device.openURL({ url: 'brain://morning-brief' });
    await expect(element(by.id('signal-card-0'))).toBeVisible();
    await expect(element(by.id('signal-card-1'))).toBeVisible();
    await expect(element(by.id('signal-card-2'))).toBeVisible();
  });

  it('approve writes Decision Log', async () => {
    await element(by.id('signal-card-0')).swipe('right');
    await element(by.id('approve-button')).tap();
    await expect(element(by.id('approved-toast'))).toBeVisible();
    // Backend assertion: ai.decision_log has new row with state='approved'
  });
});
```

## Load — k6 (Phase 3+ 5K RPS target)

```javascript
// load-tests/dashboard-read.k6.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    sustained: {
      executor: 'constant-arrival-rate',
      rate: 5000,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 200,
      maxVUs: 500,
    },
  },
  thresholds: {
    'http_req_duration{name:trpc.store.kpis}': ['p(95)<500'],
    'http_req_failed': ['rate<0.01'],
  },
};

export default function () {
  const token = __ENV.JWT;
  const response = http.post(
    `${__ENV.API}/trpc/store.kpis`,
    JSON.stringify({ from: '2026-04-01', to: '2026-04-30' }),
    { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, tags: { name: 'trpc.store.kpis' } },
  );
  check(response, { 'status is 200': r => r.status === 200 });
}
```

## Real-network smoke test — PASS gate (NON-NEGOTIABLE)

In-process request mocks (`fastify.inject()`, FastAPI `TestClient`, NestJS `Test.createTestingModule`) **skip the network stack.** They miss:
- Port binding failures
- TLS / reverse-proxy quirks
- Missing root handlers
- EADDRINUSE diagnostics
- Real connection-pool behavior

**PASS verdict requires** a smoke test that spawns the server on a real port and curls it:

```bash
#!/usr/bin/env bash
# apps/api-gateway/scripts/smoke.sh
set -euo pipefail

PORT=3001 node dist/main.js &
SERVER_PID=$!
trap "kill $SERVER_PID" EXIT

# Wait for bind
for i in {1..30}; do
  curl -fs http://localhost:3001/health && break || sleep 1
done

# Identity check
curl -fs http://localhost:3001/ | grep -q "api-gateway" || { echo "GET / missing service identity"; exit 1; }

# Health check
curl -fs http://localhost:3001/health | jq -e '.status == "ok"' > /dev/null

# Happy path (with test JWT)
curl -fs -X POST http://localhost:3001/trpc/store.kpis \
  -H "Authorization: Bearer $TEST_JWT" \
  -H "Content-Type: application/json" \
  -d '{"from":"2026-04-01","to":"2026-04-30"}' \
  | jq -e '.result.data.rows' > /dev/null

echo "SMOKE PASS"
```

Tanvi's PASS gate: smoke test ran AND returned non-zero exit code zero. Otherwise FAIL.

## Brain-specific verifications

### Cost-routing paradigm audit (TECH/12 — mandatory on every PR)

```typescript
// tools/check-paradigm-audit.ts
// Parses @paradigm(...) decorators across apps/ and asserts every endpoint / agent action has one.
// CI gate: PRs without paradigm declarations or with paradigm declared but Sonnet routed where ML suffices → FAIL.
```

### Metric registry parity (TS ↔ Python — mandatory on every PR)

```python
# tools/check-metrics-parity.py
import json
from brain_metrics import registry as py_registry

with open("packages/lib-metrics/registry-export.json") as f:
    ts_registry = json.load(f)

ts_names = set(m["name"] for m in ts_registry)
py_names = set(py_registry.list_names())
assert ts_names == py_names, f"Drift: TS-only={ts_names - py_names} | Py-only={py_names - ts_names}"
```

### Multi-tenant isolation test

```typescript
describe('multi-tenant isolation', () => {
  it('workspace A cannot read workspace B data via tRPC', async () => {
    const response = await request.post('/trpc/orders.list')
      .set('Authorization', `Bearer ${WORKSPACE_A_JWT}`)
      .send({ workspace_id: 'workspace-b' });
    expect(response.status).toBe(403);
  });

  it('ClickHouse query gateway rejects unscoped queries', async () => {
    await expect(query("SELECT * FROM orders_local", {})).rejects.toThrow(/workspace_id/);
  });
});
```

### India compliance matrix (for any lifecycle-service touch)

```python
@pytest.mark.parametrize("hour,expected", [(8, "outside_calling_hours"), (9, "ok"), (20, "ok"), (21, "outside_calling_hours")])
def test_calling_hours(hour, expected):
    with freeze_time(f"2026-05-13 {hour:02d}:00:00", tz_offset=5.5):
        result = compliance.can_call(workspace_id="ws-1", customer_id="c-1", segment="loyal")
        if expected == "ok":
            assert result.is_ok
        else:
            assert result.blocked_reason == expected

def test_frequency_cap_48h():
    # Call at T → second call at T+24h blocked
    compliance.log_call(workspace_id="ws-1", customer_id="c-1", at=now)
    result = compliance.can_call(workspace_id="ws-1", customer_id="c-1", segment="loyal", at=now + timedelta(hours=24))
    assert result.blocked_reason == "frequency_cap"

def test_dlt_unregistered_blocked():
    result = compliance.can_call(workspace_id="ws-unregistered", customer_id="c-1", segment="loyal")
    assert result.blocked_reason == "dlt_not_registered"
```

## Coverage targets

| Layer | Target |
|---|---|
| Services (business logic) | > 80% line coverage |
| Controllers / tRPC procedures | > 60% |
| Utils + formatters | > 90% |
| Critical paths (auth, payment, India compliance) | > 95% |
| Overall (excluding generated code + third-party) | > 70% |

## Naming convention

```typescript
describe('<ClassUnderTest>', () => {
  it('should <behavior> when <condition>', () => { ... });
});
```

```python
class TestClassUnderTest:
    def test_<behavior>_when_<condition>(self):
        ...
```

## Common failure modes

- **`fastify.inject()` for smoke** — doesn't bind a real port. PASS requires real network.
- **Tests dropped under session truncation** — write tests alongside production code, not as phase-4 polish.
- **Coverage theater** — 90% line coverage on no-op getters/setters. Cover the critical paths.
- **Mocking ClickHouse + Postgres** — integration tests run against real (docker compose) instances. Mocking masks RLS + query gateway bugs.
- **Forgetting India compliance matrix** — every lifecycle change needs the full matrix. Detection: lifecycle PR without `tests/compliance/` updates.

## References

- `docs/BRAIN_IMPLEMENTATION_PLAN.md` §10 — Definition of Done per layer
- `skills/operational-readiness/SKILL.md` — pre-handoff checklist + real-network smoke
- `skills/cost-routing-paradigms/SKILL.md` — paradigm audit verification
- `skills/india-commerce-economics/SKILL.md` — compliance test matrix
- `skills/clickhouse-olap/SKILL.md` — query gateway test patterns
