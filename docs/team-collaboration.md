# Multi-Engineer Collaboration (Goal 3)

> When several product engineers build Brain with the team simultaneously, the engineering team must behave as **one shared brain** — every engineer's features and challenges visible to every engineer's agents. This is delivered by the git-synced memory + two complementary surfaces: **semantic pull** (`/recall-similar`) and **team-wide push** (`/team-digest`).

---

## The guarantee

> The team knows about all features developed and challenges faced by all other product engineers.

This holds because **all memory is committed to git in the Brain repo's `.engineering-os/`** (see [memory-and-git-sync.md](memory-and-git-sync.md)). When engineer B runs `git pull`, B's agents inherit A's decisions, journals, challenges, and lessons — there is no per-machine silo. Append-only journals + `merge=union` make concurrent work conflict-resistant.

---

## Two surfaces over the shared memory

| Surface | Direction | Use |
|---|---|---|
| **`/recall-similar <topic>`** | semantic **pull** | "Has anyone solved something like this?" Returns ranked hits by meaning. Agents run it automatically in their pre-flight (system-prompt), so reuse is automatic. Self-refreshes after a pull. |
| **`/team-digest`** | team-wide **push** | "What has everyone built, and what challenges did they hit?" One view: in-flight + owner + **engineer attribution**, recently shipped, **challenges/bounces grouped per feature**, who's-working-on-what, lessons count. |

Engineer attribution comes from run-folder operators (`runs/<ts>__<hex>__<req>__<operator>/`); challenges from the decision log (bounces, violations, rollbacks).

---

## How an engineer should work (the loop)

1. `git pull` → `/team-digest` — situational awareness across the whole team.
2. `/recall-similar "<my idea>"` — reuse prior decisions; avoid re-deriving or colliding.
3. `/requirement <ask>` — the team runs autonomously; lane chosen by risk.
4. `/approve` / `/reject` at Stage 7.
5. On finish, the audit trail (journals + decision log) is committed (`chore(eos):`) and pushed — so the next engineer's `git pull` + `/team-digest` sees it.

See [ONBOARDING.md §12](../ONBOARDING.md) for the product-engineer enablement version of this.

---

## Why not a coordination *service* (the ruflo path, declined)

ruflo offers zero-trust agent federation (mTLS, trust scoring) for cross-org coordination. Brain is **one team, one repo** — git *is* the coordination substrate, and it's auditable, conflict-resistant, and free. A coordination service would add infra and split the source of truth for no benefit at this scale. The git-native model is the right fit; `/team-digest` + `/recall-similar` are the synthesis layer on top.

---

## Collision handling

Two engineers picking up the same requirement is handled by the state model (last-write-wins on `state/active.json`, re-read before acting, per-run folders never collide) — see [memory-and-git-sync.md §Conflict scenarios](memory-and-git-sync.md). `/team-digest`'s "who's working on what" makes collisions visible *before* they happen.
