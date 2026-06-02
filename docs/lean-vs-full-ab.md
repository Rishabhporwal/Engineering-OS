# Lean-vs-Full A/B — prove (or kill) the multi-agent pipeline's value

> Strategic-review finding: Opus is ~68% of pipeline spend, concentrated in the *ceremony* stages (intake/architect/security×rounds/final), and we have **never proven the 11-agent pipeline beats a lean single session** on the same work. This doc is the experiment that decides it. Until it runs, the pipeline's value over a lean session is **asserted, not measured.**

## The hypothesis
For a **no-trigger-surface** requirement (no compliance/tenancy/metric/decision-log/money/outbound/auth), **one disciplined Sonnet session** — carrying the canon + `challenge-framework` + the negative-control DoD + memory recall, doing build *and* structured self-review against the security/QA/compliance checklists — produces **equivalent quality at a fraction of the cost** versus the full multi-agent pipeline.

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

## Honesty note
The static footprint cuts (−71% prompt, −74% descriptions) are **not** the cost story — against an Opus-dominated bill they're ~2–5% of dollars. The real levers are **model tier × review rounds** (now addressed by the P0-2 cto-advisor split + Security-on-Sonnet) and **whether the ceremony runs at all** (this A/B). Run the meter before claiming a number.
</content>
