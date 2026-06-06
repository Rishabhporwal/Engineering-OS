---
name: team-digest
description: Cross-engineer team awareness (Goal 3). One view of what the WHOLE team has built and the challenges everyone hit — in-flight requirements + who owns them, recently shipped, challenges/bounces grouped per feature, who's-working-on-what by engineer, and lessons learned. Built from the git-shared .engineering-os memory. Run when joining a repo, at standup, or before starting a feature so you don't repeat someone else's work or mistake.
disable-model-invocation: true
---

Show the team-wide digest — what everyone has built and the challenges they faced. This is the *push/overview* side of shared memory; `/recall-similar` is the *semantic pull* side. Use both.

## Run

```sh
uv run "${CLAUDE_PLUGIN_ROOT}/tools/team_digest.py" $ARGUMENTS
```

- `--days N` limits to recent activity; `--json` for machine output.

## What it shows (from the git-committed `.engineering-os/`)

- **In flight** — every active requirement, its stage/status/owner, and which **engineer(s)** worked it (attributed from run-folder operators).
- **Recently shipped** — completed features.
- **Challenges & bounces** — security/QA bounces, dependency violations, rollbacks, grouped per feature, so the team learns from everyone's friction, not just their own.
- **Who's working on what** — per-engineer feature list (avoid two engineers colliding on the same area).
- **Lessons learned** — count from the registry.

## When to use it
- **Joining a repo / a teammate's first session** — instant situational awareness after `git pull`.
- **Before starting a feature** — check nobody's already on it and see related challenges (then `/recall-similar` for detail).
- **Standup / weekly review** — `--days 7` for a shipping + challenge summary.

> Because `.engineering-os/` is committed and pulled, this digest reflects **all** engineers' work — not just yours. That is the multi-engineer guarantee: everyone's features and challenges are visible to everyone's agents.
