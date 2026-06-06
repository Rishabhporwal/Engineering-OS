# Lean-vs-Full A/B — prove (or kill) the multi-agent pipeline's value

> Strategic-review finding: the top model tier dominates pipeline spend, concentrated in the *ceremony* stages (intake/architect/security×rounds/final), and we have **never proven the full multi-agent pipeline beats a lean single session** on the same work. This doc is the experiment that decides it. Until it runs, the pipeline's value over a lean session is **asserted, not measured.**

## The hypothesis
For a **no-trigger-surface** requirement (no compliance/tenancy/metric/audit-log/money/outbound/auth), **one disciplined mid-tier-model session** — carrying the Canon + `challenge-framework` + the negative-control DoD + memory recall, doing build *and* structured self-review against the security/QA/compliance checklists — produces **equivalent quality at a fraction of the cost** versus the full multi-agent pipeline.

If true → flip `lean` to the default lane and demote the full pipeline to the `high_stakes` carve-out (you already have the trigger taxonomy in `pipeline.yaml`).

## The procedure
1. Pick **5 real, no-trigger requirements** from history (copy/UI/refactor/config — things that classify express or standard today).
2. For each, run it **twice on the same starting commit**:
   - **Full:** `/requirement "<text>"` (the normal pipeline).
   - **Lean:** `/requirement --lean "<text>"` (the experimental `lean` lane — one builder session that self-gates; escalates to high_stakes if it discovers a trigger surface).
   - Capture each run's `usage.jsonl` separately (copy it aside after each).
3. Diff cost per requirement:
   ```sh
   uv run tools/ab_bench.py --v1 lean-usage.jsonl --v2 full-usage.jsonl --req <req-id>
   ```
   (Label is cosmetic — put lean in `--v1`, full in `--v2`; the tool prints per-stage + total delta.)
4. Score **quality** independently (this is the part that matters — cost is easy, quality is the risk):
   - Did the lean run catch what the full run's Security/QA/final caught? Compare findings.
   - Did the lean run ship a defect the full pipeline would have blocked? (the real question)
   - Did lean correctly **escalate** when a hidden trigger surface appeared?

## The decision rule
| Outcome | Action |
|---|---|
| Lean ≈ full quality, materially cheaper, escalates correctly | **Flip `lean` to default**; full pipeline becomes the high_stakes-only path |
| Lean misses defects full caught | Keep full as default; lean stays opt-in for trivia only |
| Mixed | Tune the lean self-review checklist; re-run on 5 more |

## Tiering baseline (already measurable from real v1 data)

Before the lean question, the *model-tiering* lever (cto-advisor split + running Security on a cheaper tier) can be projected from your real telemetry NOW:
```sh
uv run tools/ab_project.py --usage <product-repo>/.engineering-os/usage.jsonl
```
Repricing each real spawn at its tuned model tier (token counts held constant) projects the cost win from tiering alone — that validates the *full-pipeline* cost fix. The lean-vs-full run below is the SEPARATE question of whether the pipeline should run at all on no-trigger work.

## Honesty note
The static footprint cuts (−71% prompt, −74% descriptions) are **not** the cost story — against a top-tier-model-dominated bill they're ~2–5% of dollars. The real levers are **model tier × review rounds** (addressed by the cto-advisor split + running Security on a cheaper tier) and **whether the ceremony runs at all** (this A/B). Run the meter before claiming a number.
