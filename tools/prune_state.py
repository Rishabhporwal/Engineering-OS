# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""prune_state — keep active.json an IN-FLIGHT-ONLY hot file (fixes O9).

v1's state/active.json was read into context after every spawn but grew ~236
lines/requirement and NEVER pruned terminal reqs — ~3MB read-per-action at 200
reqs. v2 moves terminal reqs (shipped/rejected/killed) to a compact registry
line and keeps active.json small. Also caps the unbounded .bak.<ts> backups.

Run at stage completion (orchestrator) or manually:
  uv run prune_state.py --project-dir DIR [--keep-baks 5]

- Moves entries whose status is terminal out of active.json into registry.json
  (one compact line each: req_id, title, status, shipped/closed ts).
- Detail stays in the run folder (untouched).
- Caps state/*.bak.* to the most recent N.
- Writes a fresh .bak before mutating active.json.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

TERMINAL = {"shipped", "rejected", "killed"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)  # atomic — never leave a torn/invalid live file (SRE F4)


def main() -> int:
    ap = argparse.ArgumentParser(prog="prune_state")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--keep-baks", type=int, default=5)
    args = ap.parse_args()

    state_dir = Path(args.project_dir) / ".engineering-os" / "state"
    active_p = state_dir / "active.json"
    registry_p = state_dir / "registry.json"
    if not active_p.exists():
        print("no active.json — nothing to prune")
        return 0

    active = json.loads(active_p.read_text())
    reqs = active.get("active_requirements", [])
    keep, moved = [], []
    for r in reqs:
        (moved if r.get("status") in TERMINAL else keep).append(r)

    if moved:
        registry = {"requirements": []}
        if registry_p.exists():
            registry = json.loads(registry_p.read_text())
        seen = {x.get("req_id") for x in registry.get("requirements", [])}
        for r in moved:
            if r.get("req_id") in seen:
                continue
            registry["requirements"].append({
                "req_id": r.get("req_id"),
                "title": r.get("title"),
                "status": r.get("status"),
                "feature_class": r.get("feature_class"),
                "closed_at": _now(),
            })
        registry_p.write_text(json.dumps(registry, indent=2) + "\n")

        # backup then shrink active.json (atomic)
        bak = active_p.with_suffix(f".json.bak.{_now().replace(':', '-')}")
        bak.write_text(active_p.read_text())
        active["active_requirements"] = keep
        _atomic_write(active_p, active)
        print(f"pruned {len(moved)} terminal req(s) → registry.json; active.json now holds {len(keep)} in-flight")
    else:
        print(f"no terminal reqs to prune; active.json holds {len(keep)} in-flight")

    # cap .bak backups
    baks = sorted(state_dir.glob("active.json.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in baks[args.keep_baks:]:
        old.unlink()
    if len(baks) > args.keep_baks:
        print(f"capped backups: removed {len(baks) - args.keep_baks}, kept {args.keep_baks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
