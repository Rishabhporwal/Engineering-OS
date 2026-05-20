# Orchestration Model (how the pipeline runs end-to-end)

> **The platform constraint that shapes everything:** a spawned subagent does **not** have the `Agent` tool — a subagent cannot spawn another subagent. Only the **top-level session** can spawn. (Verified directly: even `cto-advisor`, which declares `Agent` in its frontmatter, has no `Agent` tool when spawned.) So the pipeline cannot self-drive by "each agent spawning the next." Orchestration must live at the top level.

## The model

```
Founder runs /requirement <text>
        │
        ▼
TOP-LEVEL ORCHESTRATOR  (the /requirement flow — HAS the Agent tool)
        │  spawn agent → read its HANDOFF block + re-read state/active.json → advance
        ├─▶ cto-advisor (Stage 1)              ──returns HANDOFF──┐
        │      (needs_personas? → orchestrator spawns personas ∥, re-invokes Rohan)
        ├─▶ architect (Stage 2)                ──returns HANDOFF──┤
        ├─▶ builder(s) (Stage 3, ∥ if multi)   ──returns HANDOFF──┤
        ├─▶ security ∥ qa (Stage 4∥5)          ──return verdicts──┤
        ├─▶ cto-advisor (Stage 6 final)        ──returns HANDOFF──┘
        ▼
   awaiting-founder  ── STOP ── Founder runs /approve
        ▼
   /approve drives Stage 8 (spawns platform-devops)
```

The agents do their stage and **return**; the orchestrator (top level) does all spawning. This is the only arrangement that works on this platform — and it's what makes "submit one `/requirement` and the team runs end-to-end" real.

## Contract between orchestrator and agents

**Each agent (subagent):**
- Has NO `Agent` tool. Must NOT try to spawn. Must NOT write `HANDOFF-TO-*.md` files.
- Does its stage, persists artifacts + journals + decision-log, and **updates `state/active.json`** (status/stage/owner → next, using exact `state-machine.yaml` values).
- **Ends its response with a `HANDOFF:` block** (decision / next_stage / next_agent / bounce_target / needs_personas / reason). Defined in [system-prompt §3](../prompts/system-prompt.md).

**The orchestrator (top level — the `/requirement` flow):**
- Spawns the right agent for the current stage, always passing `req_id`, run folder, absolute `${CLAUDE_PLUGIN_ROOT}` + `${CLAUDE_PROJECT_DIR}`, and "you have no Agent tool — return a HANDOFF block."
- Reads the returned HANDOFF + re-reads `state/active.json` (source of truth) and routes per the lane (see [feature-tiering.md](feature-tiering.md)).
- Does the special spawns agents can't: **personas in parallel** (Stage 1 high-stakes), **Security ∥ QA in parallel** (Stage 4∥5), **multiple builders in parallel** (Stage 3).
- STOPS at the Founder gate (Stage 7). `/approve` resumes the drive into Stage 8.
- Safety-bounds the loop (~20 spawns) and always leaves `state/active.json` consistent so [`/resume`](../skills/resume/SKILL.md) can pick up an interrupted run.

## Routing table (status → next spawn)

| After | Lane | Orchestrator spawns next |
|---|---|---|
| Stage 1 ADVANCE | express | the one builder (Stage 3) |
| Stage 1 ADVANCE | standard / high-stakes | architect (Stage 2) |
| Stage 1 needs_personas | high-stakes | personas ∥, then cto-advisor (synthesis) |
| Stage 2 ADVANCE | std / high | tagged builder(s) (Stage 3, ∥) |
| Stage 3 done | express | qa-agent (Stage 5) |
| Stage 3 done | std / high | security ∥ qa (Stage 4∥5) |
| Stage 4∥5 PASS | std / high | cto-advisor (Stage 6) |
| Stage 4∥5 PASS | express | Founder gate (STOP) |
| any BOUNCE/FAIL | — | the bounce_target builder, then re-review |
| Stage 6 PASS | — | Founder gate (STOP) |
| /approve | — | platform-devops (Stage 8) |

## Why not nested spawning / handoff files

- **Nested spawning** isn't available on the platform (the whole reason for this model).
- **`HANDOFF-TO-*.md` files** (the old fallback) are retired — they required a human to run the next command, which defeats autonomy. The HANDOFF block + state update let the top-level orchestrator continue automatically.

## Verification boundary

The orchestrator loop is driven by the top-level session following the `/requirement` protocol. It was verified end-to-end on a sandbox (express: Rohan → builder → QA → Founder gate, each agent returning a clean HANDOFF, no spawn attempts). Run the full `docs/v0.8.0-validation.md` in a real Brain session to confirm standard + high-stakes (personas, parallel review) behave the same.
