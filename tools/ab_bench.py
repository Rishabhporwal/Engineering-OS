# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""ab_bench — per-stage token A/B between two pipeline runs (v1 vs v2).

The harness surfaces total-only tokens for subagent spawns (O10), so the only
reliable per-stage measurement is an identical-task A/B: run the SAME trivial
requirement on v1 and on v2, then diff usage.jsonl per stage. This tool does
the diff + reports the savings the optimization program is built to prove.

Usage:
  uv run ab_bench.py --v1 path/to/v1-usage.jsonl --v2 path/to/v2-usage.jsonl [--req REQ]

Reads two usage.jsonl files (the format tools/usage_logger.py writes), groups by
stage, and prints a per-stage + total comparison with delta + %.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(path: str, req: str | None) -> dict[int, dict]:
    by_stage: dict[int, dict] = defaultdict(lambda: {"total": 0, "spawns": 0, "models": set(), "scopes": set()})
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"not found: {path}")
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if req and r.get("req_id") != req:
            continue
        st = int(r.get("stage", -1))
        by_stage[st]["total"] += int(r.get("total_tokens", 0) or 0)
        by_stage[st]["spawns"] += 1
        by_stage[st]["models"].add(r.get("model", "?"))
        by_stage[st]["scopes"].add(r.get("review_scope", "?"))
    return by_stage


def main() -> int:
    ap = argparse.ArgumentParser(prog="ab_bench")
    ap.add_argument("--v1", required=True)
    ap.add_argument("--v2", required=True)
    ap.add_argument("--req", default=None, help="filter to one req_id (recommended for an identical-task A/B)")
    args = ap.parse_args()

    a = load(args.v1, args.req)
    b = load(args.v2, args.req)
    stages = sorted(set(a) | set(b))

    print(f"{'stage':>5} | {'v1 tok':>10} {'v1 (model/scope)':>22} | {'v2 tok':>10} {'v2 (model/scope)':>22} | {'delta':>10} {'%':>7}")
    print("-" * 104)
    tot1 = tot2 = 0
    for s in stages:
        t1 = a.get(s, {}).get("total", 0)
        t2 = b.get(s, {}).get("total", 0)
        tot1 += t1
        tot2 += t2
        m1 = ",".join(sorted(a.get(s, {}).get("models", set()) or {"-"})) + "/" + ",".join(sorted(a.get(s, {}).get("scopes", set()) or {"-"}))
        m2 = ",".join(sorted(b.get(s, {}).get("models", set()) or {"-"})) + "/" + ",".join(sorted(b.get(s, {}).get("scopes", set()) or {"-"}))
        d = t2 - t1
        pct = (d / t1 * 100) if t1 else 0.0
        print(f"{s:>5} | {t1:>10} {m1:>22} | {t2:>10} {m2:>22} | {d:>+10} {pct:>+6.1f}%")
    print("-" * 104)
    dtot = tot2 - tot1
    ptot = (dtot / tot1 * 100) if tot1 else 0.0
    print(f"{'TOTAL':>5} | {tot1:>10} {'':>22} | {tot2:>10} {'':>22} | {dtot:>+10} {ptot:>+6.1f}%")
    if tot1:
        print(f"\nv2 is {abs(ptot):.1f}% {'cheaper' if dtot < 0 else 'more expensive'} than v1 on this task.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
