# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""heartbeat_check — make silence detectable (fixes O13) + reconcile telemetry (fixes O14).

Two checks, both answering "is the pipeline actually alive / is it logging?":

  1. STALENESS (O13): compare mtime(live.log) vs mtime(active.json) and mtime(usage.jsonl).
     If state/usage moved but live.log is older by > --lag-min minutes, the narration is
     DEAD while work continues — the exact "silence looks like idle" incident. Loud banner.

  2. RECONCILE (O14): every spawn the harness recorded in spawn-heartbeat.jsonl (ground truth,
     written by the PostToolUse hook) MUST have a matching usage.jsonl row (the token numbers,
     written by the orchestrator). A heartbeat with no usage row = the silent-stop, now visible.

Usage:
  uv run heartbeat_check.py --project-dir DIR [--lag-min 15]

Exit 0 = healthy. Exit 1 = stale or unreconciled (so /watch and CI can gate on it).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


def _load(p: Path) -> list[dict]:
    if not p.exists():
        return []
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(prog="heartbeat_check")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--lag-min", type=float, default=15.0)
    args = ap.parse_args()

    eos = Path(args.project_dir) / ".engineering-os"
    live = eos / "live.log"
    active = eos / "state" / "active.json"
    usage = eos / "usage.jsonl"
    heartbeat = eos / "spawn-heartbeat.jsonl"

    problems = 0

    # 1. staleness
    live_m = _mtime(live)
    newest_state = max(_mtime(active), _mtime(usage))
    if newest_state > 0 and live_m > 0:
        lag_min = (newest_state - live_m) / 60.0
        if lag_min > args.lag_min:
            print(f"  STALE: live.log is {lag_min:.0f} min behind state/usage — narration may be DEAD "
                  f"while work continues (O13). Check whether the pipeline is actually progressing.")
            problems += 1
    elif newest_state > 0 and live_m == 0:
        print("  WARN: state/usage exist but live.log is missing — no narration at all.")
        problems += 1

    # 2. reconcile heartbeat (spawns that happened) vs usage (spawns that logged tokens)
    hb = _load(heartbeat)
    us = _load(usage)
    if hb:
        usage_keys = {(r.get("req_id"), str(r.get("agent")), str(r.get("stage"))) for r in us}
        gaps = [r for r in hb
                if (r.get("req_id"), str(r.get("agent")), str(r.get("stage"))) not in usage_keys
                and r.get("req_id") not in (None, "?")]
        if gaps:
            print(f"  UNRECONCILED: {len(gaps)} spawn(s) returned (heartbeat) with NO usage.jsonl row — "
                  f"the O14 silent-stop. The orchestrator stopped logging tokens. Examples:")
            for g in gaps[:5]:
                print(f"      {g.get('agent')} S{g.get('stage')} {g.get('req_id')} @ {g.get('ts')}")
            problems += 1

    if problems == 0:
        print(f"heartbeat_check: healthy (live.log fresh; {len(hb)} spawns reconciled vs {len(us)} usage rows)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
