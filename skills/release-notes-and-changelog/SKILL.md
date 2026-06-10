---
name: release-notes-and-changelog
description: Derive honest, audience-split release notes + a maintained CHANGELOG from the run's own artifacts (journals, reviews, deployment report) at Stage 8 — user-facing notes, internal/ops notes, and the changelog entry, written from evidence, not memory. Owner Platform/SRE + Delivery Coordinator.
---

# Release Notes & Changelog (Stage-8 Output)

A shipped change nobody can describe is a support ticket waiting to happen. At Stage 8 the run folder already contains the truth — the requirement, the plan, the reviews, the deployment report. This skill turns that **evidence into communication**: a changelog entry plus audience-split release notes, derived (never invented) from the artifacts.

## Sources (in priority order — cite, don't recall)
1. `01-requirement.md` — what was asked, by whom, why.
2. `03-architecture-plan.md` — what was actually built + tradeoffs.
3. The developer reports + QA/security reviews — what changed, what was verified, anything deferred-with-waiver.
4. `13-deployment-report.md` — version, flags, canary outcome, bake result, rollback status.
5. The per-feature journal — the narrative (bounces, decisions, lessons).

## The three outputs
**1. CHANGELOG entry** (`CHANGELOG.md`, Keep-a-Changelog shape, newest first):
```markdown
## [<version>] — <YYYY-MM-DD>
### Added | Changed | Fixed | Security | Deprecated | Removed
- <one line per change, linking the req_id> (req: feat-<slug>)
```
Versioning: semver; the version bump class follows the change class (breaking → major per `api-discipline` deprecation rules; feature → minor; fix → patch). The plugin/product manifest version and the changelog must move together.

**2. User-facing release notes** — for the people who use the product: what's new *in their terms* (no internal jargon, no req_ids), what changed in behavior, any action required, any flag-gated rollout ("enabled for X% / your account on date"). If the change is invisible to users, say nothing publicly — silence beats noise.

**3. Internal/ops notes** — for the team + on-call: req_id, flags + kill switch, dashboards/alarms added, migration/backfill performed, rollback recipe (one command/flag), known limitations, the waiver list (anything shipped with a Stakeholder-logged waiver is **named here, never buried**).

## Honesty rules
- **Notes are derived from artifacts** — every claim traces to a run-folder file. A "faster dashboards" claim needs the perf evidence behind it.
- **Realized vs placed:** describe what is live NOW (post-canary/bake), not what the plan intended (`kpi-dashboard-design`'s realized-vs-placed honesty, applied to prose).
- **Security fixes** are disclosed per the product's policy — coordinate with the Security Reviewer; never leak exploit detail in public notes; never silently patch a user-impacting vulnerability.
- **Deprecations** state the sunset date + migration path (`api-discipline`).

## Cadence + automation
Generated per shipped requirement at Stage 8 (Platform/SRE writes; Delivery Coordinator edits for audience). Conventional-commit history can scaffold the changelog (`finishing-a-development-branch` commit discipline makes this mechanical), but the **release notes are written from the run artifacts**, not from commit subjects — commits say what moved; notes say what it means.

## Anti-patterns
Notes written from memory instead of artifacts · marketing language for an internal fix · "various improvements" (say it or skip it) · req_ids/jargon in user-facing notes · a waiver shipped but unmentioned in internal notes · changelog and manifest version drifting apart · publishing exploit detail in a security note · announcing the plan instead of the realized state.
