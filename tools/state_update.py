# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""state_update — the ONLY writer of state/active.json (fixes the lost-update race).

v1/v2 had every spawned subagent do an unguarded read-modify-write on active.json,
and the pipeline spawns builders + reviewers IN PARALLEL — so two near-simultaneous
writes silently clobbered each other on the source-of-truth file (the spec promised
a lock that never existed). Fix: subagents NEVER write active.json. They return their
intended state in the HANDOFF block; the single-threaded orchestrator applies it here,
one requirement at a time, with an ATOMIC write (tmp + os.replace) so a crash mid-write
can never leave invalid JSON live.

Usage (orchestrator only, after a spawn returns):
  uv run state_update.py --project-dir DIR --req REQ \
      [--status S] [--stage N] [--owner A] [--set key=value ...] [--remove key ...]

Creates the requirement entry if absent (intake). Writes a capped .bak first.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)  # atomic on POSIX — no torn/invalid live file on crash


def _coerce(v: str):
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.lstrip("-").isdigit():
        return int(v)
    return v


def main() -> int:
    ap = argparse.ArgumentParser(prog="state_update")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--req", required=True)
    ap.add_argument("--status")
    ap.add_argument("--stage", type=int)
    ap.add_argument("--owner")
    ap.add_argument("--set", action="append", default=[], metavar="key=value")
    ap.add_argument("--remove", action="append", default=[])
    ap.add_argument("--keep-baks", type=int, default=5)
    args = ap.parse_args()

    state_dir = Path(args.project_dir) / ".engineering-os" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    active_p = state_dir / "active.json"

    data = {"active_requirements": []}
    if active_p.exists():
        try:
            data = json.loads(active_p.read_text())
        except json.JSONDecodeError:
            # corrupt live file — fall back to newest schema-parseable backup
            baks = sorted(state_dir.glob("active.json.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            for b in baks:
                try:
                    data = json.loads(b.read_text())
                    break
                except json.JSONDecodeError:
                    continue
        # backup the current good file before mutating
        bak = state_dir / f"active.json.bak.{_now().replace(':', '-')}"
        bak.write_text(active_p.read_text())
        olds = sorted(state_dir.glob("active.json.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in olds[args.keep_baks:]:
            old.unlink()

    reqs = data.setdefault("active_requirements", [])
    entry = next((r for r in reqs if r.get("req_id") == args.req), None)
    if entry is None:
        entry = {"req_id": args.req}
        reqs.append(entry)

    if args.status is not None:
        entry["status"] = args.status
    if args.stage is not None:
        entry["stage"] = args.stage
    if args.owner is not None:
        entry["current_owner"] = args.owner
    for kv in args.set:
        if "=" in kv:
            k, v = kv.split("=", 1)
            entry[k.strip()] = _coerce(v.strip())
    for k in args.remove:
        entry.pop(k, None)
    entry["last_journal_entry_at"] = _now()

    _atomic_write(active_p, data)
    print(f"state_update: {args.req} → status={entry.get('status')} stage={entry.get('stage')} "
          f"owner={entry.get('current_owner')} (atomic; sole writer)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
