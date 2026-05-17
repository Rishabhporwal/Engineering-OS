# Prompt: Build the Brain Engineering Operating System

## 1. Your Role

You are simultaneously acting as: world-class CTO, startup engineering operator, AI agent architect, product strategist, security reviewer, QA lead, DevOps architect, and implementation architect.

You are designing a complete **Engineering Operating System (Engineering OS)** for my startup **Brain** — delivered as a **plugin** that functions as a lean AI engineering team. Multiple people on my team will use this plugin to build Brain without hiring a large engineering team early. The plugin must analyze, design, build, review, test, approve, and deploy features through a structured, auditable workflow.

I am the **Founder/CTO** and the only source of truth for business and product requirements.

---

## 2. Source of Truth: The `requirements/` Folder

Before producing anything, you must scan, read, and analyze every relevant file in the current folder — especially the `requirements/` subfolder, which contains:

1. Business requirements
2. Technical requirements
3. Product requirements
4. Architecture notes
5. Supporting documents
6. **Curated skill definitions** (highest importance — these define how each agent thinks and acts)

**Rules for reading the folder:**

- Inspect the folder structure first; list every file you considered.
- Identify files relevant to: business, technical, product, architecture, workflows, user journeys, APIs, data models, security, compliance, infrastructure, deployment, roadmap, product strategy, AI engineering skills.
- Extract business context, technical context, product goals, users, workflows, constraints, integrations, data flows, risks, non-functional requirements, and all curated skills.
- Treat existing files as authoritative. If similar files already exist in the folder, **extend and improve them** rather than duplicating.
- If requirements conflict, document the conflict and recommend a resolution.
- If information is missing, document the gap and create a clear, labeled assumption — **do not block the work** and do not ask me to paste content unless files are physically inaccessible.
- Do **not** invent generic skills. Use curated skills from the folder. Only add new ones under a clearly-marked "Recommended Additional Skills" section.

---

## 3. Operating Model (The Workflow)

The plugin orchestrates this exact pipeline. Every requirement I submit flows through these stages in order:

**Stage 1 — CTO Advisor (intake & brainstorm)**
Acts as my shadow CTO. Responsible for technical/business brainstorming, technical decisions, architecture review, engineering quality, resolving doubts from agents, final code review, production-readiness calls, and challenging weak requirements.
At runtime, the CTO Advisor spawns **3 dynamic personas** chosen based on the requirement (e.g. business, product, security, scalability, customer, compliance, data, AI, cost, ops) to brainstorm from multiple angles.

**Stage 2 — Architect**
Analyzes the requirement, asks clarifying questions, produces: technical architecture, implementation plan, API design, database design, data flow, edge cases, security considerations, observability plan, test strategy, impacted systems, risks, and tradeoffs.

**Stage 3 — Parallel Development**
Backend, Frontend, and Mobile developer agents work in parallel wherever possible to maximize throughput.

**Stage 4 — Security Review**
Reviews authentication, authorization, PII handling, compliance impact, input validation, API security, secrets management, logging safety, dependency risks, rate limiting, abuse cases, data retention, tenant isolation, and enterprise security expectations. Failures bounce back to the responsible developer agent.

**Stage 5 — QA**
Verifies requirement completeness, acceptance criteria, unit/integration/smoke/regression tests, impacted scenarios, edge cases, platform-specific behavior, and existing product behavior. Failures bounce back to the responsible developer agent.

**Stage 6 — CTO Advisor Final Review**
Reviews requirement alignment, architecture quality, code quality, security review, QA review, risks, production readiness, and business/technical tradeoffs.

**Stage 7 — Founder/CTO Approval (me)**
I am the final gate before deployment.

**Stage 8 — Platform/DevOps**
Handles CI/CD, staging deploy, staging verification, production deploy, monitoring, auto-rollback, release notes, and deployment reporting.

---

## 4. Core Principle: No Blind Agreement

Even though I am the Founder/CTO and source of truth, every agent must respectfully challenge me when a requirement is unclear, risky, insecure, low-value, technically expensive, overcomplicated, unscalable, misaligned with the product, bad for customers, bad for enterprise readiness, or bad for long-term maintainability.

When challenging, agents must state:
1. What they understood
2. What concern they have
3. What risk exists
4. What alternative they recommend
5. What decision is needed from me

The tone is constructive, never combative. The team can say no — but always with a path forward.

---

## 5. Skill Handling (Mandatory)

The curated skills in `requirements/` are the foundation of agent behavior.

You must:

1. Extract every curated skill from the folder.
2. Categorize them by domain.
3. Map them to roles: CTO Advisor, Architect, Backend Developer, Frontend Developer, Mobile Developer, Security Reviewer, QA Agent, Platform/DevOps Agent.
4. Mark shared ownership where a skill applies to multiple roles.
5. Mark any gaps under **Recommended Additional Skills** (clearly labeled as not sourced from the folder).
6. Use skills to define each role's responsibilities, review criteria, quality gates, prompts, and decision-making behavior.
7. Produce a dedicated **Skill Mapping Matrix**, a **Role Empowerment Model**, and a **Skills Registry** design that the plugin consumes at runtime.

---

## 6. Required Deliverables

Produce one complete end-to-end implementation package, structured as the following **eight sections**. Do not summarize if the output gets long — continue section by section until complete.

### Section 1 — Folder Analysis & Context Extraction
- Folder/files discovered
- Files reviewed and selected as relevant
- Extracted business, technical, product, and architecture context
- Extracted curated skills and their categories
- Conflicts found, missing information, assumptions made

### Section 2 — Skill Mapping & Role Empowerment
- Full list of curated skills with categories
- **Skill Mapping Matrix** (skill × role)
- Shared skills
- Recommended additional skills (labeled)
- **Role Empowerment Model**: how each agent uses its skills during execution
- How skills influence agent behavior, quality gates, prompts, reviews, and decisions

### Section 3 — Engineering Operating System
Executive summary; core philosophy; operating principles; team structure; role definitions; responsibility matrix; decision rights; full requirement-to-production workflow with stage-by-stage process; dynamic persona creation; processes for CTO Advisor, Architect, Backend, Frontend, Mobile, Security, QA, final CTO Advisor review, Founder approval, and Platform/DevOps; quality gates; escalation rules; anti-blind-agreement rule; challenge framework; communication rules; Definition of Done; production readiness checklist; status lifecycle.

### Section 4 — Plugin Architecture & Technical Design
Plugin architecture and modules; backend architecture; API endpoints; database schema; workflow orchestration logic; Agent Registry; Skills Registry; skill-to-role mapping model; state machine implementation; artifact storage; approval flow; authN/authZ; integrations (GitHub, CI/CD, Slack, Jira/Linear, monitoring); event model; error handling; audit logging; security model; deployment architecture; example API requests/responses; example DB tables; example workflow execution payload; how the plugin reads requirement files and curated skills; how it keeps business/technical/skill context updated over time.

### Section 5 — Templates & Schemas
Markdown templates AND JSON schemas for: requirement, CTO Advisor review, dynamic persona, architecture, development report, security review, QA review, final review, deployment, skill registry, agent registry.

### Section 6 — Agent Prompts (directly usable)
Full Brain Engineering OS system prompt, plus individual prompts for: CTO Advisor, Dynamic Persona Generator, Architect, Backend Developer, Frontend Developer, Mobile Developer, Security Reviewer, QA Agent, Platform/DevOps Agent, Founder Approval Assistant, and a Challenge & Disagreement behavior prompt.

Every agent prompt must include: role mission, responsibilities, assigned curated skills (from folder), shared skills, decision rights, inputs, outputs, quality checklist, escalation rules, prompt instructions, and anti-blind-agreement behavior.

### Section 7 — File-by-File Implementation Package
Generate the complete folder structure and the full content of every file below. For each file: file path, purpose, and complete content. Use clear `TODO:` placeholders where folder content is missing.

```
README.md
docs/
  operating-system.md
  folder-context-summary.md
  business-context.md
  technical-context.md
  skill-mapping-matrix.md
  role-empowerment-model.md
  workflow.md
  quality-gates.md
  escalation-rules.md
  plugin-architecture.md
  technical-implementation.md
agents/
  cto-advisor.md
  architect.md
  backend-developer.md
  frontend-developer.md
  mobile-developer.md
  security-reviewer.md
  qa-agent.md
  platform-devops.md
  dynamic-persona-generator.md
prompts/
  system-prompt.md
  anti-blind-agreement.md
  challenge-framework.md
workflows/
  requirement-to-release.yaml
  state-machine.yaml
  approval-flow.yaml
schemas/
  requirement.schema.json
  cto-advisor-review.schema.json
  dynamic-persona.schema.json
  architecture.schema.json
  development-report.schema.json
  security-review.schema.json
  qa-review.schema.json
  final-review.schema.json
  deployment.schema.json
  skill-registry.schema.json
  agent-registry.schema.json
templates/
  requirement-template.md
  cto-advisor-review.md
  dynamic-persona-review.md
  architecture-plan.md
  developer-report.md
  security-review.md
  qa-review.md
  final-review.md
  deployment-report.md
```

### Section 8 — Implementation Roadmap
MVP / V2 / V3 scope; developer task breakdown; suggested tech stack; build sequence; risks and mitigations; rollout plan; and one **end-to-end example feature walkthrough** using an actual feature from the existing requirement files (requirement → CTO Advisor → personas → architecture → dev → security → QA → final review → my approval → deployment).

---

## 7. Output Rules

- **Start by showing your work**: list folder/files discovered, files considered relevant, business/technical context extracted, curated skills extracted, skill-to-role mapping, and any missing or conflicting information — *before* producing the full package.
- Use clear headings and a consistent structure.
- Keep language simple and practical. Be detailed without being bloated.
- Make it **startup-friendly** (lean, fast, low overhead) and **enterprise-ready** (security, compliance, scale, auditability).
- Heavily ground everything in the actual folder contents and curated skills. **Do not give generic advice** — produce the real, working Engineering OS.
- Use YAML or JSON where it adds clarity; use checklists where they help.
- Include state machine statuses, role prompts ready to paste into an agent system, and concrete examples throughout.
- Production-ready and directly usable by the developers who will build the plugin.
- If the output becomes long, **do not summarize** — continue section by section until complete.

The final deliverable should read like a complete internal operating manual *plus* an implementation specification for the Brain Engineering OS plugin.check 