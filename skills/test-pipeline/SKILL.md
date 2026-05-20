---
name: test-pipeline
description: Validate Engineering OS plugin health before relying on autonomous flow. Runs the pipeline doctor — orchestration graph, lane integrity, agent handoff targets, advertised-command existence, and skill-matrix sanity. Run after editing any state/lane/agent/skill, and as a pre-flight when onboarding a repo.
disable-model-invocation: true
---

Run the pipeline doctor — a static validation of the whole orchestration graph, so a broken handoff chain is caught BEFORE a run, not during one.

## Run

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/tools/pipeline_doctor.py" $ARGUMENTS
```

(`--dry-run` and `--quiet` are accepted; the doctor is inherently static/dry.)

## Report

Show each check's PASS/FAIL:
- **C1** state-machine integrity (valid transitions, reachability, terminals)
- **C2** lane integrity (express/standard/high-stakes stage lists valid)
- **C3** personas resolve to `agents/<name>.md`
- **C4** agent handoffs (`subagent_type`) point at real agents
- **C5** every `/command` the session-start hook advertises exists as a skill
- **C6** every `skills/<x>/` has a well-formed `SKILL.md`

If **any** check FAILs, surface the specific issues and do NOT start a real pipeline run until they're fixed (exit code is non-zero, so CI can gate on it too).
