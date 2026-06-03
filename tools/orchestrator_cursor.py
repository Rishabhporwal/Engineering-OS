# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""orchestrator_cursor — make the orchestrator crash-recoverable (Architect F2 / SRE).

The top-level orchestrator is the SPOF: its in-flight loop state (which parallel
spawns are outstanding, what's awaiting reconcile, the last route, the spawn count)
lives ONLY in its context. A mid-pipeline compaction/crash loses it, and /resume can
only infer requirement *status* from active.json — not the orchestrator's own plan
(e.g. "I spawned 3 builders in parallel and am waiting on all 3"). This persists that
plan to a tiny cursor file after each routing decision so /resume rebuilds the
SCHEDULER, not just the requirement.

Usage:
  uv run orchestrator_cursor.py set   --project-dir DIR --req REQ --stage N \
        [--outstanding a,b,c] [--awaiting-reconcile a,b] [--last-route TEXT] [--bump-spawns]
  uv run orchestrator_cursor.py get   --project-dir DIR --req REQ
  uv run orchestrator_cursor.py clear --project-dir DIR --req REQ

Atomic writes (tmp + os.replace). One cursor file per project: state/orchestrator-cursor.json,
keyed by req_id (the orchestrator may interleave a few requirements).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(project_dir: str) -> Path:
    return Path(project_dir) / ".engineering-os" / "state" / "orchestrator-cursor.json"


def _load(p: Path) -> dict:
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {"requirements": {}}


def _atomic(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, p)


def _split(s: str | None) -> list[str]:
    return [x.strip() for x in s.split(",")] if s else []


def main() -> int:
    ap = argparse.ArgumentParser(prog="orchestrator_cursor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("set", "get", "clear"):
        s = sub.add_parser(name)
        s.add_argument("--project-dir", required=True)
        s.add_argument("--req", required=True)
        if name == "set":
            s.add_argument("--stage", type=int)
            s.add_argument("--outstanding", help="comma list of agents spawned, not yet returned")
            s.add_argument("--awaiting-reconcile", help="comma list of reviews awaiting reconciliation")
            s.add_argument("--last-route", help="one-line description of the last routing decision")
            s.add_argument("--bump-spawns", action="store_true", help="increment the spawn counter")
    args = ap.parse_args()

    p = _path(args.project_dir)
    data = _load(p)
    reqs = data.setdefault("requirements", {})

    if args.cmd == "get":
        cur = reqs.get(args.req)
        print(json.dumps(cur, indent=2) if cur else "{}  (no cursor — fresh or completed)")
        return 0

    if args.cmd == "clear":
        reqs.pop(args.req, None)
        _atomic(p, data)
        print(f"orchestrator_cursor: cleared {args.req}")
        return 0

    # set (merge)
    cur = reqs.setdefault(args.req, {"spawns": 0})
    if args.stage is not None:
        cur["stage"] = args.stage
    if args.outstanding is not None:
        cur["outstanding"] = _split(args.outstanding)
    if args.awaiting_reconcile is not None:
        cur["awaiting_reconcile"] = _split(args.awaiting_reconcile)
    if args.last_route is not None:
        cur["last_route"] = args.last_route
    if args.bump_spawns:
        cur["spawns"] = int(cur.get("spawns", 0)) + 1
    cur["updated_at"] = _now()
    _atomic(p, data)
    print(f"orchestrator_cursor: {args.req} → stage={cur.get('stage')} "
          f"outstanding={cur.get('outstanding', [])} spawns={cur.get('spawns', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
