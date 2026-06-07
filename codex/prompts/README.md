# Codex command prompts — Engineering OS

These are **thin wrappers** that let Codex invoke the Engineering OS command-skills. Each one tells the single Codex agent to read the canonical `skills/<name>/SKILL.md` (the same instructions the Claude Code plugin runs) and execute it, honoring the cross-runtime contract in [`../../AGENTS.md`](../../AGENTS.md). **No command logic is duplicated here** — the SKILL.md is the single source of truth, so the two runtimes can't drift.

## Install
```bash
mkdir -p ~/.codex/prompts && cp *.md ~/.codex/prompts/
```
(Skip this README — Codex would expose it as `/README`.)

## Full coverage — all 29 command-skills mirrored

Every command-skill in [`../../skills/`](../../skills/) carrying `disable-model-invocation: true` has a `/eos-<name>` mirror here, so Codex has parity with the Claude Code plugin commands. The six pipeline-spine prompts (`eos-init`, `eos-requirement`, `eos-status`, `eos-handoff`, `eos-decide`, `eos-deploy`) are hand-tuned with extra stage guidance; the rest are thin wrappers that delegate to their `SKILL.md`.

| Group | Codex prompts |
|---|---|
| **Lifecycle** | `/eos-init` · `/eos-requirement` · `/eos-status` · `/eos-handoff` · `/eos-decide` |
| **Gates / release** | `/eos-approve` · `/eos-reject` · `/eos-deploy` · `/eos-rollback` |
| **Memory / recall** | `/eos-recall` · `/eos-recall-similar` · `/eos-reindex` · `/eos-resume` |
| **Self-improvement** | `/eos-new-skill` · `/eos-propose-rule` · `/eos-adopt-rule` · `/eos-reject-rule` |
| **Review / QA** | `/eos-design-review` · `/eos-qa-browser` · `/eos-test-pipeline` |
| **Ops / reporting** | `/eos-monitor` · `/eos-watch` · `/eos-dashboard` · `/eos-team-digest` |
| **Audits** | `/eos-worker-canon-drift` · `/eos-worker-compliance-drift` · `/eos-worker-test-gap` |
| **Misc** | `/eos-persona` · `/eos-invoke-skill` |

> When a new command-skill is added to `skills/`, mirror it with one wrapper file (same body, swap the name). The wrapper holds **no logic** — the `SKILL.md` is the single source of truth, so the runtimes can't drift.
