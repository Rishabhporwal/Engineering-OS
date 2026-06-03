# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""ab_project — projected v1→v2 cost from REAL v1 telemetry (not a live A/B, but real numbers).

A live lean-vs-full A/B needs interactive pipeline runs. This is the honest interim: take the
ACTUAL per-spawn token counts from a v1 usage.jsonl and re-price each spawn at its v2 model
tier (the dominant lever) + optionally model the delta-review discount on bounce re-reviews.

It does NOT measure v2; it projects what the SAME work would have cost under v2's tiering.
Conservative: token COUNTS are held constant (same work); only the per-token RATE changes with
the model. Delta-review is shown as a separate, clearly-labelled optimistic scenario.

Usage:  uv run ab_project.py --usage <v1 usage.jsonl> [--rates opus=30,sonnet=6,haiku=1.5]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# v2 model tier by (stage, agent) — from pipeline.yaml + the cto-advisor split.
def v2_model(stage: int, agent: str, v1_model: str) -> str:
    if stage == 1 and agent == "cto-advisor":          return "sonnet"   # intake split off Opus
    if stage == 1 and "persona" in agent:               return v1_model   # personas already tiered
    if stage == 2:                                       return "opus"     # architect (unchanged)
    if stage == 3:                                       return "sonnet"   # builders
    if stage == 4:                                       return "sonnet"   # security default (escalate=opus rare)
    if stage == 5:                                       return "sonnet"   # qa
    if stage == 6:                                       return "opus"     # final-reviewer (judgment, kept)
    if stage == 8:                                       return "sonnet"   # devops
    return v1_model


def main() -> int:
    ap = argparse.ArgumentParser(prog="ab_project")
    ap.add_argument("--usage", required=True)
    ap.add_argument("--rates", default="opus=30,sonnet=6,haiku=1.5", help="blended $/1M tokens")
    ap.add_argument("--delta-factor", type=float, default=0.4,
                    help="tokens a delta re-review uses vs a full one (2nd+ security/qa spawn per req)")
    args = ap.parse_args()

    rate = {}
    for kv in args.rates.split(","):
        k, v = kv.split("="); rate[k.strip()] = float(v)

    rows = [json.loads(l) for l in Path(args.usage).read_text().splitlines() if l.strip()]

    # detect bounce re-reviews: the 2nd+ security/qa spawn on the same req is a re-review
    seen_review = defaultdict(int)
    by_stage = defaultdict(lambda: {"v1": 0.0, "v2": 0.0, "v2d": 0.0, "tok": 0})
    tot = {"v1": 0.0, "v2": 0.0, "v2d": 0.0, "tok": 0}

    for r in rows:
        stage = int(r.get("stage", -1)); agent = r.get("agent", "?")
        m1 = r.get("model", "sonnet"); tok = int(r.get("total_tokens", 0) or 0)
        m2 = v2_model(stage, agent, m1)
        c1 = tok / 1e6 * rate.get(m1, 6)
        c2 = tok / 1e6 * rate.get(m2, 6)

        # delta-review scenario: a re-review (not the first) on a non-high-stakes path uses less
        c2d = c2
        if agent in ("security-reviewer", "qa-agent"):
            seen_review[(r.get("req_id"), agent)] += 1
            if seen_review[(r.get("req_id"), agent)] > 1:   # a bounce re-review
                c2d = tok * args.delta_factor / 1e6 * rate.get(m2, 6)

        s = by_stage[stage]
        s["v1"] += c1; s["v2"] += c2; s["v2d"] += c2d; s["tok"] += tok
        tot["v1"] += c1; tot["v2"] += c2; tot["v2d"] += c2d; tot["tok"] += tok

    print(f"\nProjected v1 → v2 cost from {len(rows)} REAL v1 spawns "
          f"(rates $/1M: {args.rates}). Token counts held constant; only model tier re-priced.\n")
    print(f"{'stage':>5} | {'tokens':>10} | {'v1 $':>8} | {'v2 $ (tier)':>12} | {'v2 $ (tier+delta)':>18}")
    print("-" * 66)
    for st in sorted(by_stage):
        s = by_stage[st]
        print(f"{st:>5} | {s['tok']:>10,} | {s['v1']:>8.2f} | {s['v2']:>12.2f} | {s['v2d']:>18.2f}")
    print("-" * 66)
    print(f"{'TOTAL':>5} | {tot['tok']:>10,} | {tot['v1']:>8.2f} | {tot['v2']:>12.2f} | {tot['v2d']:>18.2f}")

    def pct(a, b): return (b - a) / a * 100 if a else 0.0
    print(f"\n  v2 model-tiering alone:      ${tot['v1']:.2f} → ${tot['v2']:.2f}   "
          f"({pct(tot['v1'], tot['v2']):+.0f}%, saves ${tot['v1']-tot['v2']:.2f})")
    print(f"  v2 tiering + delta-review:   ${tot['v1']:.2f} → ${tot['v2d']:.2f}   "
          f"({pct(tot['v1'], tot['v2d']):+.0f}%, saves ${tot['v1']-tot['v2d']:.2f})")
    print(f"\n  NOTE: projection from real per-spawn tokens, not a live v2 run. Does NOT credit prompt")
    print(f"  caching (the biggest untested lever) or context-trim. Confirm with a live A/B (ab_bench.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
