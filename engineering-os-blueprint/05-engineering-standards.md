# 05 — Engineering Standards

> The standards every change is held to, regardless of stack or domain. These are the *content* of
> the quality gates in [06](06-quality-gates-and-metrics.md): code, testing, security, observability,
> API, data, infrastructure, and documentation. Each standard states the **intent** (which is fixed)
> separately from any **implementation** (which is the Canon's stack choice).

---

## 1. Coding & code review

**Intent.** Code is correct, readable, and consistent with its surroundings; defects are caught by a
second perspective before merge.

- **Read like the neighborhood.** New code matches the surrounding file's naming, idiom, structure,
  and comment density. Consistency beats personal preference.
- **Small, reversible changes.** Vertical slices; one logical change per commit; explicit-path commits.
- **No reinvented primitives.** Reusing an existing capability is required; re-implementing one is a
  review finding.
- **Code review is technical, evidence-based, and adversarial-but-fair.** A reviewer either points to
  a concrete concern (with file:line and a suggested fix) or approves. Performative agreement and
  vague objection are both rejected. Rigor over politeness.
- **Review checklist:** correctness, security posture, test validity, observability, contract impact,
  reuse/simplicity, and adherence to the binding plan.

---

## 2. Testing strategy

**Intent.** Behavior is proven against an independent source of truth, under realistic conditions,
and stays proven as the system changes. *False confidence is worse than no test* ([00 §3](00-first-principles.md)).

The strategy is a pyramid plus mandatory real-environment verification:

| Layer | Purpose | Required |
|---|---|---|
| **Unit** | Logic correctness in isolation | Always |
| **Integration / contract** | Seams between modules/services honor their contracts | When a contract exists |
| **End-to-end / real-network smoke** | The change works against a *real* environment, not mocks | **Always, before "done"** |
| **Regression suite** | Previously-passing behavior still passes | Run in full on every bounce-fix |
| **Mutation** | The tests actually detect breakage | On high-stakes paths |
| **Load / performance** | Latency, throughput, cost budgets hold under load | When a budget exists |

**Verification validity (non-negotiable).** A test only counts if:

- It runs **under the real security context** — never with isolation/authorization bypassed.
- It has a **negative control** — the test fails when the protection it guards is removed. A test that
  cannot fail proves nothing.
- Parity/equality is asserted against an **independent** source of truth, never against itself
  (no tautological assertions).

Invalid tests are a **QA VETO** surface, treated as more dangerous than missing tests because they
manufacture false confidence.

---

## 3. Security standards

**Intent.** The system resists the threats in its model; sensitive data and access are controlled;
compliance obligations are met. Security is **shifted left** (every builder owns posture) and **gated**
(the Security Reviewer holds a VETO).

- **Threat modeling** for any change touching a trust boundary (a structured method such as STRIDE).
- **Input validation at every boundary**, output encoding against injection/XSS, parameterized data
  access.
- **Least privilege everywhere** — access control enforced at the data layer, not just the app layer;
  tenant isolation as a primitive at multiple layers.
- **Secrets are managed, never embedded** — a managed secret store / KMS; no secrets in code, logs, or
  config; an automated secret-scanner gate that cannot be silently bypassed.
- **Compliance is a capability, not a checkbox** — the product's regulatory regime is defined in the
  Canon; the Security Reviewer enforces it and VETOes violations ([08 §Compliance](08-technical-governance.md)).
- **Supply chain** — dependencies are pinned, scanned, and updated deliberately ([08 §Versioning](08-technical-governance.md)).
- **A standard scanner suite** runs in CI (SAST, dependency audit, secret scan, IaC scan); findings
  are triaged, not ignored.

---

## 4. Observability & traceability standards

**Intent.** Any request can be followed end-to-end; operators can answer "what happened" without
guessing. Un-traceable code does not ship (Iron Law 6).

- **One correlation identity** propagates through *every* hop — inbound request → internal calls →
  async messages → downstream/model calls. The identity carries at minimum a request id, a trace id,
  and the relevant scope (tenant/user) keys.
- **Structured logging** — machine-parseable, with the correlation identity on every line; **no
  sensitive data in logs** (redaction is enforced, not hoped for).
- **The three pillars** — distributed **traces**, **metrics**, and **logs** — plus error tracking,
  wired into the platform's observability backend.
- **Surfaced to humans** — error states in UI and API responses carry the request id so a user report
  is traceable to a trace.
- **Gated** — the Security Reviewer VETOes missing traceability; QA verifies trace IDs appear
  end-to-end in real-network runs; Platform/SRE verifies the observability pipeline is healthy after
  deploy.

---

## 5. API & contract standards

**Intent.** Interfaces are explicit, evolvable, and safe to depend on.

- **Contracts are first-class** — every API/event/shared schema has a written contract that is the
  source of truth, with generated types where possible.
- **Contract tests** verify provider and consumer agree; breaking changes are detected automatically
  (a breaking-change check in CI), not discovered in production.
- **Versioning & deprecation** — backward-incompatible changes are versioned; deprecations carry a
  sunset timeline; consumers are given a migration path.
- **Pagination** uses stable cursors/keysets, not offsets, for any list that can grow.
- **Rate limiting & quotas** protect every public surface.
- **Idempotency** — every mutating endpoint and external side-effect accepts an idempotency key and
  de-duplicates; no duplicate effects on retry.

---

## 6. Data standards

**Intent.** Data is correct, fresh, isolated, and performant for its access pattern.

- **Right store for the access pattern** — transactional (OLTP) and analytical (OLAP) workloads are
  separated; the schema serves the query, not the other way around.
- **Tenant isolation in the data layer** — the isolation primitive (e.g. a tenant key) leads the
  schema and is enforced by the datastore (row-level policies / scoped access), not only by app code.
- **Migrations are reversible** and run as a deliberate, observable step; destructive migrations are
  staged and gated.
- **Data contracts at ingestion** — incoming data is validated against a contract; violations are
  quarantined, not silently absorbed.
- **Data quality is gated** — freshness SLAs and correctness assertions; data that fails quality is
  marked *estimated/untrusted* until the gate passes, never presented as authoritative.
- **Indexing & partitioning** are part of the design ([04](04-architecture-and-decisions.md)), not a
  reaction to a slow query in production.

---

## 7. Infrastructure standards

**Intent.** Infrastructure is reproducible, observable, secure, and recoverable.

- **Everything as code** — all infrastructure is declared in version-controlled IaC; no click-ops in
  production.
- **Immutable, reproducible builds** — artifacts are built once and promoted across environments;
  environments are paved roads, not snowflakes.
- **Least-privilege & network segmentation** by default; secrets via the managed store; encryption in
  transit and at rest.
- **Health & readiness signals** on every deployable unit so the platform can route, restart, and
  drain safely.
- **Capacity & cost are budgeted** and observable; autoscaling is bounded; cost is a first-class
  signal ([11](11-runtime-and-cost-doctrine.md)).
- **Recovery is designed and rehearsed** — backups, restore drills, and a tested rollback path.

---

## 8. Documentation standards

**Intent.** The system can be understood, operated, and changed by someone who did not build it.
Documentation is a **deliverable**, not an afterthought.

- **ADRs** for consequential decisions ([04](04-architecture-and-decisions.md)).
- **Runbooks** for every operational procedure and known failure mode ([07](07-operations-and-reliability.md)).
- **API references** generated from the contract, kept in sync.
- **Architecture docs** (HLD/LLD) maintained in the Canon as the system evolves.
- **Onboarding material** so a new engineer (human or agent) can reach productivity from the docs.
- **Release notes** for every shipped requirement, traceable to its origin.
- **Docs live with the code** and change in the same review; stale docs are a defect.

---

## 9. The accessibility & user-facing quality bar

For any human-facing surface (web or mobile), accessibility is an **enforced gate**, not a
preference: keyboard and focus operability, state never conveyed by color alone, non-visual
alternatives for visual data, reduced-motion support, and platform accessibility APIs honored. The
bar is checked in CI and is a release gate ([06](06-quality-gates-and-metrics.md)).

---

> **How the intent/implementation split keeps this reusable:** each standard above states a fixed
> *intent* (idempotency, traceability, negative controls, isolation) and leaves the *implementation*
> (which library, which datastore, which scanner) to the Canon's stack decision ([09](09-reference-architecture.md)).
> The gate checks the intent; the stack supplies the means.
