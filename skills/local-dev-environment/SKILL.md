---
name: local-dev-environment
description: Dev/prod parity locally — a Docker Compose stack of the REAL backing services (Postgres, Redis, IdP, a Kafka-API broker, schema registry, MinIO/S3, an Iceberg REST catalog, OLAP, the LLM gateway, Grafana), health-gated startup, LocalStack for AWS APIs, and Testcontainers for CI. Owner Platform/SRE + all builders.
---

# Local Development Environment (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **dev-experience / parity seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — `STACK.md` names the actual services. The *patterns* — run the *real* backing services locally, health-gate startup, config-from-env, Compose vs Testcontainers vs LocalStack by job — are what transfer. **Anchor: Compose Spec v2.25+, LocalStack 2026.03, Kafka 4.0 (KRaft-only).**

A developer who can't run the system locally writes code that "passed on my machine" and breaks in prod. **Owner:** Platform/SRE (owns the stack + parity discipline); every builder uses it. Pairs with `platform-engineering-idp` (the IDP scaffolds this) and `operational-readiness`. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Dev/prod parity is a discipline (12-factor X).** Use the **same TYPE of backing service** dev↔prod — the local impl may differ only where the **API contract is identical** (MinIO↔S3, Redpanda↔MSK, Keycloak/Authentik↔the prod IdP). **Never fake a backing service** (SQLite-for-Postgres, in-memory-for-Kafka) — "tiny incompatibilities crop up and fail in production." Modern packaging makes running the *real* service cheap; do that.
2. **Health-gate startup — never bare `depends_on`.** Bare `depends_on` waits for container *start*, not *ready*. Use long-form `depends_on: { dep: { condition: service_healthy } }` backed by a real `healthcheck`. This one line is load-bearing.
3. **Config comes from the environment, not the image.** Same image dev→prod; behaviour differs only by env/secrets. **No `if (env === 'dev')` in code** — the seam is endpoint URLs + flags (S3 endpoint + path-style, gateway base URL, IdP issuer).
4. **Three tools, three jobs — don't conflate:** **Compose** = the dev inner loop / run the whole app (long-lived); **Testcontainers** = CI integration tests against *ephemeral real* services (random ports, auto-torn-down); **LocalStack** = AWS-API emulation only.
5. **Green local ≠ prod-correct for cloud magic.** LocalStack defaults to **permit-all IAM** (enforcement is paid) — a passing local run says nothing about IAM/VPC/KMS correctness. Validate those against a real ephemeral cloud account.

## The Compose stack (map each to its prod analogue)
| Local | Prod | Note |
|---|---|---|
| **Postgres** | RDS/Aurora | same engine — run the real one |
| **Redis** | ElastiCache | same engine |
| **Authentik / Keycloak** (IdP) | the prod IdP | real OIDC/OAuth2 locally; backed by its own Postgres (`auth-and-access`) |
| **Redpanda** (Kafka API) | Redpanda/MSK | single binary, no ZooKeeper/KRaft, **built-in schema registry + Console** (`event-driven-kafka`) |
| **MinIO** | S3 | S3-compatible; swap only endpoint + path-style |
| **Iceberg REST catalog** (Lakekeeper or Nessie) | Glue/Polaris | real Iceberg REST over MinIO (`lakehouse-iceberg`) |
| **StarRocks / DuckDB / Trino** | the prod OLAP | match the prod role (`starrocks-olap`) |
| **LiteLLM proxy** | the same gateway | one OpenAI-format endpoint; **same gateway local + prod** (`llm-gateway`) |
| **Grafana + Loki (+ Alloy)** | the LGTM stack | local logs/traces (`observability`) |

### Health-gated startup (the pattern)
```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]   # READY, not just started
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
  seed:                                                # one-shot migrate/seed, gated on db
    image: app/migrate:dev
    depends_on: { db: { condition: service_healthy } }
  api:
    image: app/api:dev
    depends_on:
      seed: { condition: service_completed_successfully }   # app never starts on an unmigrated DB
    develop:
      watch:                                           # live reload (Compose v2.25+ multi-service safe)
        - { action: sync, path: ./src, target: /app/src }
        - { action: rebuild, path: package.json }
```
- `depends_on` conditions: `service_started` (weak default), **`service_healthy`**, `service_completed_successfully` (init/seed/migrate).
- Put heavy optional services (Trino/StarRocks/Tempo) behind **`profiles`** so they're off unless `--profile`/`COMPOSE_PROFILES` asks for them.
- Pre-create MinIO buckets / Iceberg namespaces with a gated `mc`/init container; Postgres auto-runs `/docker-entrypoint-initdb.d/*.sql` on first init.

## LocalStack (AWS APIs locally)
- **Emulates well:** S3, SQS, SNS, DynamoDB, Secrets Manager, Lambda, Kinesis — the core inner-loop set. Use for fast/offline dev, deterministic CI, cost avoidance.
- **Emulates poorly:** IAM authorization fidelity (permit-all by default; enforcement is paid), performance characteristics, new-service lag, per-service quirks. **Verify against the live Feature Coverage page** for anything load-bearing.
- **2026 packaging change:** the standalone free Community image was deprecated (2026-03-23); a single image now needs `LOCALSTACK_AUTH_TOKEN`; the free **Hobby** tier is **non-commercial only**. Budget a license (or pick an alternative) before standardizing it in commercial CI.

## Testcontainers vs Compose vs LocalStack
**Compose** when a human runs the whole app. **Testcontainers** when an automated test needs a *real* Postgres/Kafka isolated + disposable — especially CI (random ports avoid clashes; auto-teardown; `withReuse(true)` for fast local loops). **LocalStack** when the thing under test is AWS-API-specific — and **Testcontainers can run LocalStack**, so it's often "Testcontainers driving LocalStack." Complementary, not exclusive.

## Local Kubernetes
**k3d** (k3s-in-Docker — light, built-in LB + registry) for everyday convenience; **kind** (upstream kubeadm — conformant) for "closest to real" CI when admission controllers/CRDs/operators matter. Neither replaces a real ephemeral staging cluster for cloud networking/IAM.

## Anti-patterns
Bare `depends_on` (app races the DB) · a healthcheck that lies (`CMD true` / port-open-before-ready) · faking a backing service locally · `if(env==='dev')` branching in code instead of env config · trusting green LocalStack as an IAM/security test · the free LocalStack image in commercial CI post-2026.03 (token + license) · hardcoded host ports clashing in CI (use Testcontainers' random ports) · version skew vs prod (pin to prod's major/minor — local Redpanda vs prod Kafka 4.0 KRaft) · running every heavy service on every `up` (use `profiles`) · treating k3d/kind/LocalStack as a staging replacement.

## References
`platform-engineering-idp` (scaffolds + owns this) · `operational-readiness` · `event-driven-kafka` · `lakehouse-iceberg` · `starrocks-olap` · `auth-and-access` · `llm-gateway` · `observability` · `testing-tdd` (Testcontainers in the integration suite).
