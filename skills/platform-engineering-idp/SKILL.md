---
name: platform-engineering-idp
description: Build the Internal Developer Platform — golden paths, self-service scaffolding, a workload spec (Score), a service catalog/portal (Backstage), and ephemeral preview environments. Reduce developer cognitive load; make the right way the easy way. Owner Platform/SRE.
---

# Platform Engineering — Internal Developer Platform (Reference Patterns)

> **Reference implementation.** This skill documents one concrete binding of the **developer-platform seam** (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind it to Backstage, a custom portal, Port, or Cortex; to Score, Humanitec, or Crossplane for orchestration. The *patterns* — golden paths, self-service with guardrails, a workload abstraction that hides infra, a service catalog, and ephemeral environments — are what transfer; the tools are examples.

An IDP productizes infrastructure so a developer ships a service without a ticket to the platform team — and without bypassing the guardrails. It is the antidote to the "fake SRE / shadow ops" anti-pattern (Team Topologies). **Owner:** Platform/SRE; the Architect reviews the golden-path templates. Canon: `STACK.md`.

## Invariants (NON-NEGOTIABLE)
1. **Golden paths, not gold cages.** Provide a paved, supported way to do the common thing (new service, new endpoint, new job); allow an escape hatch for the exception. Mandating the path for everything kills it; having no path means everyone reinvents (and re-breaks) the wheel.
2. **Self-service with guardrails baked in.** Scaffolding a new service produces one that is *already* compliant: observability wired, health probes present, tenant-isolation defaults, `policy-as-code` satisfied, CI with `supply-chain-security`. The platform encodes `operational-readiness` so the developer can't forget it.
3. **A workload abstraction hides infra.** Developers declare *what* they need (a workload + dependencies) via a spec like **Score**; the platform maps it to the actual infra. They don't hand-write Kubernetes/Terraform for routine work.
4. **The catalog is the source of truth for ownership.** Every service, its owner, on-call, docs, dashboards, and dependencies are discoverable in the portal (Backstage). An un-cataloged service is invisible at 2 a.m. — not allowed.
5. **Backstage (a portal) is the frontend, not the platform.** A portal without an orchestration backend is a pretty catalog. The self-service actions must actually provision through an orchestrator, or it's theater.

## The pieces
```
Portal (Backstage)        → catalog + docs + scaffolder templates + scorecards
Workload spec (Score)     → developer declares the workload; portable across environments
Orchestrator              → maps the spec to real infra (K8s/Terraform/Crossplane)
Golden-path templates     → `new service` / `new job` scaffolds: compliant by construction
Ephemeral environments    → per-PR preview env, auto-torn-down
Scorecards                → automated maturity checks (has owner? SLO? on-call? signed images?)
```

## Golden-path scaffold (what `new service` should emit)
- Service skeleton in the standard structure (DDD bounded-context per `domain-driven-design`).
- CI pipeline with lint/typecheck/test/build + `supply-chain-security` (SBOM, scan, sign).
- K8s/workload manifest via Score with health probes, resource limits, tenant labels.
- Observability pre-wired (OTel traces/metrics/logs — `observability`, `ai-observability-tracing` if it calls models).
- Catalog entry (`catalog-info.yaml`) with owner + on-call.
- A dashboard + a default alert. (No service ships dashboard-less — `operational-readiness`.)

## Ephemeral / preview environments
- Each PR gets a disposable environment (the app + a branched database — see `database-branching-dev-data`) for review + e2e, torn down on merge/close.
- Same provisioning path as production (IaC), just scoped + short-lived — so "works in preview" means something.

## Operability + measuring the platform
- Treat the platform as a **product**: developers are users; measure adoption, lead-time-to-first-deploy, and golden-path coverage. A path nobody uses is a bug.
- **Scorecards** drive maturity (DORA-style + ownership/SLO/security checks) without manual audits.
- Don't over-build: start with the one or two highest-friction paths (new service, preview env); grow by demand, not speculation.

## Anti-patterns
A portal with no orchestration behind it (theater) · golden path mandated with no escape hatch (gold cage) · self-service that produces non-compliant services (guardrails bolted on later) · developers hand-writing K8s/Terraform for routine work · un-cataloged services · building a huge platform before any developer asked · treating the platform as a project to finish rather than a product to run.
