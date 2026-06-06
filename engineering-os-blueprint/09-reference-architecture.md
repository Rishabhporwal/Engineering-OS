# 09 — Reference Architecture (stack-agnostic, with one worked example)

> The OS mandates **patterns and intents**, never a specific technology. This document gives the
> capability map every product architecture must satisfy, the adapter seams that make any concrete
> stack pluggable, the framework for choosing a stack, and **one fully worked reference stack** as an
> illustration — explicitly an example, not a requirement.

---

## 1. The capability map (what every architecture must provide)

A product architecture is judged by whether it provides these **capabilities**, regardless of which
technology implements each. This is the contract the OS designs against.

| Capability | Intent | Common implementations (examples only) |
|---|---|---|
| **Edge / API surface** | A controlled entry point; auth, rate limiting, routing. | API gateway, BFF, reverse proxy |
| **Synchronous services** | Request/response business logic, organized by bounded context. | Any service framework, any language |
| **Asynchronous backbone** | Decoupled, replayable, ordered-where-needed eventing. | Log-based broker, queue, stream |
| **Transactional store (OLTP)** | Strong-consistency system of record. | Relational DB, document store |
| **Analytical store (OLAP)** | High-volume aggregate/analytical queries. | Columnar warehouse / analytics DB |
| **Cache / low-latency store** | Hot-path reads, dedup, rate-limit state. | In-memory cache/KV |
| **Object / blob storage** | Large/immutable artifacts, raw archives. | Object store |
| **Search / retrieval** | Text/semantic lookup. | Search engine, vector index |
| **Compute platform** | Where services run; scheduling, scaling, isolation. | Containers + orchestrator, serverless |
| **Identity & access** | AuthN, AuthZ, session lifecycle, RBAC. | Managed auth, IdP, policy engine |
| **Secrets & keys** | Managed secrets, encryption keys. | Secret manager + KMS |
| **Observability** | Traces, metrics, logs, error tracking. | OTel + a backend |
| **CI/CD & IaC** | Reproducible build, test, deploy; infra as code. | Pipeline runner + IaC tool |
| **Client surfaces** | Web and/or mobile UIs. | Web framework, mobile framework |
| **AI/ML serving** *(if applicable)* | Model inference, evaluation, gateway/routing. | Model gateway, inference service |

An architecture review ([04](04-architecture-and-decisions.md)) checks that each *needed* capability
is present and that the **intents** of [05](05-engineering-standards.md) (isolation, idempotency,
traceability, contract safety) are met by the chosen implementations.

---

## 2. The adapter seams (what makes the stack pluggable)

The OS stays stack-agnostic by talking to **seams**, not products. Each seam has a stable intent; the
Canon binds it to a concrete technology. Swapping a technology means re-binding a seam, not rewriting
the OS.

| Seam | Stable intent the OS depends on | Bound in the Canon to |
|---|---|---|
| **PersistenceAdapter** | Read/write the system of record with tenant isolation + reversible migrations. | the chosen OLTP store |
| **AnalyticsAdapter** | Run aggregate queries over high-volume facts. | the chosen OLAP store |
| **EventAdapter** | Publish/consume events idempotently, replayably. | the chosen broker/stream |
| **CacheAdapter** | Get/set hot data with TTL + scoped keys. | the chosen cache |
| **BlobAdapter** | Put/get large immutable objects. | the chosen object store |
| **IdentityAdapter** | Authenticate, authorize, manage sessions/roles. | the chosen auth/IdP |
| **SecretsAdapter** | Fetch secrets / use keys without embedding them. | the chosen secret manager/KMS |
| **ObservabilityAdapter** | Emit the correlation identity across traces/metrics/logs. | the chosen telemetry backend |
| **DeployAdapter** | Progressive rollout + bake + auto-rollback. | the chosen CI/CD + orchestrator |
| **ModelAdapter** *(AI)* | Route an inference request to the cheapest sufficient model, with caching + fallback. | the chosen model gateway |
| **RegionAdapter** | Vary region-specific behavior (residency, locale, formats). | the chosen region/locale rules |

> The seams are where the OS's reusability lives. A startup binds `PersistenceAdapter` to a single
> managed database; an enterprise binds it to a sharded cluster. The pipeline, gates, and roles are
> identical — only the binding differs.

---

## 3. Choosing a stack — the decision, not the default

The OS does not pick the stack. The **Architect** picks it in the Foundation phase (or via an ADR for
a new layer), using the decision framework in [04 §5](04-architecture-and-decisions.md). The
stack-decision rubric for each capability:

1. **Does an existing binding already cover this?** Don't add a layer the Canon already provides.
2. **What access pattern / scale / consistency does the requirement actually need?** Choose to the
   need, not the trend.
3. **What's the operational cost?** Who runs it, how is it observed, how does it fail, how is it
   recovered.
4. **How reversible is the choice?** Prefer managed + standard over bespoke + exotic unless the
   requirement forces it.
5. **Record it as an ADR** — context, options, decision, consequences, status.

A stack, once chosen, is **locked in the Canon** for the product — routine work references the Canon
and does not re-litigate the choice. Adding a *new* layer or swapping one requires a fresh ADR.

---

## 4. One worked reference stack (illustration only)

To make the abstract concrete, here is **one** coherent cloud-native binding of the seams. It is a
worked example to reason from — **not** a recommendation to copy. A different product would bind the
same seams to entirely different technologies and travel the identical pipeline.

```
                          ┌──────────────────────── Clients ────────────────────────┐
                          │   Web app (SSR/SPA)            Mobile app (native/cross)  │
                          └───────────────┬───────────────────────┬──────────────────┘
                                          │  (correlation identity propagated)        
                                  ┌───────▼────────────────────────▼───────┐
                                  │  Edge: API gateway / BFF  (authN, rate  │
                                  │  limiting, routing, request-id minting) │
                                  └───────┬─────────────────────────────────┘
                  ┌───────────────────────┼───────────────────────────────┐
          ┌───────▼───────┐       ┌───────▼───────┐               ┌────────▼────────┐
          │ Service A     │       │ Service B     │   …per bounded │ AI/ML service   │
          │ (bounded ctx) │       │ (bounded ctx) │     context    │ (+ model gw)    │
          └───┬───────┬───┘       └───┬───────┬───┘               └───┬─────────────┘
              │       │ events        │       │ events                │ inference
       ┌──────▼──┐ ┌──▼──────────────▼───┐ ┌──▼─────────┐      ┌──────▼─────────┐
       │ OLTP    │ │  Async backbone     │ │ Cache/KV   │      │ Model gateway   │
       │ (system │ │  (log-based broker, │ │ (hot reads,│      │ (cheapest-      │
       │ of      │ │   replayable)       │ │  dedup)    │      │  sufficient     │
       │ record) │ └──────────┬──────────┘ └────────────┘      │  routing+cache) │
       └────┬────┘            │  CDC / fact stream             └─────────────────┘
            │            ┌────▼─────┐   ┌───────────┐   ┌──────────────┐
            └───────────▶│ OLAP /   │   │ Object    │   │ Search /     │
                         │ warehouse│   │ store     │   │ vector index │
                         └──────────┘   └───────────┘   └──────────────┘

  Cross-cutting (every box): Identity & access · Secrets/KMS · Observability (traces/metrics/logs)
  Platform: containers + orchestrator · IaC · CI/CD with progressive delivery + auto-rollback
```

**Properties of the reference** (the things any good binding should share, not the specific products):

- **Cloud-native & containerized** — services are stateless, horizontally scalable, health-probed,
  and scheduled by an orchestrator.
- **Distributed & event-driven** where decoupling/replay matter; synchronous where consistency
  matters — each choice an ADR.
- **OLTP/OLAP split** — the system of record is not the analytics engine.
- **Tenant isolation at multiple layers** — edge → service → data store.
- **One correlation identity** flowing through every box.
- **Everything reproducible** — IaC + immutable artifacts + progressive delivery.

---

## 5. Distributed-systems defaults the OS assumes

Whatever the binding, the OS assumes these are honored (they are gated by [05](05-engineering-standards.md)):

- **Idempotency** on every mutating operation and external side-effect.
- **At-least-once delivery** assumed on the async backbone → consumers are idempotent and dedup.
- **Backward/forward-compatible contracts** with explicit versioning at every seam.
- **Partitioning from day one** — data and event streams keyed by the isolation/scaling primitive.
- **Graceful degradation** — a dependency's failure degrades a feature, it does not collapse the
  system.
- **No distributed transaction where a saga/outbox will do** — consistency patterns chosen to the
  need.

---

## 6. Why this stays reusable

The OS's pipeline, roles, gates, and governance never reference a product or a vendor — only the
**seams** and **intents** above. A new adoption writes its stack into the Canon by binding the seams;
everything else in this blueprint applies unchanged. That is the whole point: **the architecture is
pluggable; the engineering organization is constant.**
