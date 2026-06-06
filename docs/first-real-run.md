# First real run — the one sequence that matters next

> After this hardening release (v1.1.0), the highest-value action is a single real run that
> (a) confirms the mechanics fire, (b) confirms the model-tiering cost cut binds live, and (c) settles
> lean-vs-full. This is that sequence — copy-paste after `/plugin update` + **restart**.

## 0. Apply (the #1 gotcha)
```
git push origin master        # if not already
# in the consuming product repo session:
/plugin update engineering-os
# >>> RESTART the Claude Code session <<<  (plugin loads only on restart)
/status                        # confirms version 1.1.0 is loaded
```

## 1. Health (10 seconds, from the plugin root)
```sh
python3 tools/pipeline_doctor.py    # OK — 6 checks
python3 tools/cache_lint.py         # clean
python3 tools/knowledge_lint.py     # clean
```

## 2. One trivial requirement — proves the mechanics fire
```
/requirement Update the dashboard empty-state copy to "No data yet for this period."
```
Watch for: lane classified (deterministic), a mid-tier-model builder, a usage row per spawn
(`spawn-heartbeat.jsonl` written by the hook), `/approve` shows the **decision card**.

## 3. Confirm the cost cut bound — the headroom KPI
```sh
uv run tools/dashboard.py    # (CLAUDE_PROJECT_DIR=<product repo>); open .engineering-os/dashboard.html
```
- **"tier headroom" KPI** on the Tokens tab should now read **~0%** for the new run
  (everything already logged at the right tier). If it still shows headroom, an agent got
  pinned back to a top-tier model — check that spawn's `model` in `usage.jsonl`.

## 4. Settle lean-vs-full (2 trivial reqs)
```
/requirement <trivial ask>            # full pipeline → cp usage.jsonl /tmp/full.jsonl
/requirement --lean <same-class ask>  # lean lane    → cp usage.jsonl /tmp/lean.jsonl
uv run tools/ab_bench.py --v1 /tmp/lean.jsonl --v2 /tmp/full.jsonl --req <id>
```
Decision rule in `docs/lean-vs-full-ab.md`: if lean ≈ full quality and materially cheaper
and escalates correctly → flip `lean` to default; else keep full and lean stays opt-in.

## 5. Then — the actual point
**Put a real product feature through the team and watch what breaks.** The OS that's worth
having is improved by reacting to real-run observations, not by pre-building features.
Bring the next *specific* signal — a flaky gate, a cost spike the headroom KPI flags, a bounce
that shouldn't have happened — and it gets fixed fast. That loop (run → observe → fix) is the
roadmap from here.

## Rollback (if needed)
```sh
git checkout v1-0.26.0-archive    # or: git revert <commit>
# /plugin update + restart
```
