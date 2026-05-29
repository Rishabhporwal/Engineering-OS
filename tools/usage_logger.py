# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""usage_logger — enforced per-spawn token telemetry for the Engineering OS v2.

Replaces v1's best-effort prose ("the orchestrator echoes a JSON line") that
silently stopped (O14/O13/O4/O10). The orchestrator calls this after EVERY
agent spawn with the Agent result's usage. One code path, not a prose
instruction the model can skip.

Two subcommands:

  log     append one usage row to usage.jsonl (full breakdown when available,
          total-only otherwise — never fabricates a missing field).

  assert  verify a usage row exists for a (req_id, stage, agent) spawn. A
          missing row is a DEFECT (like the no-SKIP rule), exit 3. This is the
          enforcement the v1 system never had.

Usage:
  uv run usage_logger.py log  --project-dir DIR --req REQ --agent A --stage N \
        --model M --total T [--input I --output O --cache-read CR --cache-creation CC]
  uv run usage_logger.py assert --project-dir DIR --req REQ --agent A --stage N

Design notes:
- No deps; safe to run with `uv run` or plain `python3`.
- Append-only; never rewrites history.
- Timestamps are UTC Z per the timestamp-discipline rule.
- Omits any field not provided (never logs a fabricated 0).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _usage_path(project_dir: str) -> Path:
    return Path(project_dir) / ".engineering-os" / "usage.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_log(args: argparse.Namespace) -> int:
    row: dict = {
        "ts": _now(),
        "req_id": args.req,
        "agent": args.agent,
        "stage": args.stage,
        "model": args.model,
        "review_scope": args.review_scope,  # full | delta | none — powers the delta-review savings view
    }
    # Only include fields that were actually provided — never fabricate.
    if args.total is not None:
        row["total_tokens"] = args.total
    if args.input is not None:
        row["input_tokens"] = args.input
    if args.output is not None:
        row["output_tokens"] = args.output
    if args.cache_read is not None:
        row["cache_read_tokens"] = args.cache_read
    if args.cache_creation is not None:
        row["cache_creation_tokens"] = args.cache_creation

    path = _usage_path(args.project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"usage logged: {row['agent']} S{row['stage']} {row['req_id']} "
          f"({row.get('total_tokens', '?')} tok, {row['model']}, {row['review_scope']})")
    return 0


def cmd_assert(args: argparse.Namespace) -> int:
    path = _usage_path(args.project_dir)
    if not path.exists():
        print(f"DEFECT: no usage.jsonl — spawn {args.agent} S{args.stage} {args.req} "
              f"was not logged. Telemetry is the optimization program's eyes (O14).",
              file=sys.stderr)
        return 3
    found = False
    with path.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r.get("req_id") == args.req and r.get("agent") == args.agent
                    and int(r.get("stage", -1)) == args.stage):
                found = True
                break
    if not found:
        print(f"DEFECT: usage row missing for {args.agent} S{args.stage} {args.req}. "
              f"Re-log it before advancing — a missing row is a defect, not a skip.",
              file=sys.stderr)
        return 3
    print(f"usage row present: {args.agent} S{args.stage} {args.req}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="usage_logger")
    sub = p.add_subparsers(dest="cmd", required=True)

    lg = sub.add_parser("log", help="append a usage row")
    lg.add_argument("--project-dir", required=True)
    lg.add_argument("--req", required=True)
    lg.add_argument("--agent", required=True)
    lg.add_argument("--stage", type=int, required=True)
    lg.add_argument("--model", required=True)
    lg.add_argument("--review-scope", default="full", choices=["full", "delta", "none"])
    lg.add_argument("--total", type=int, default=None)
    lg.add_argument("--input", type=int, default=None)
    lg.add_argument("--output", type=int, default=None)
    lg.add_argument("--cache-read", type=int, default=None)
    lg.add_argument("--cache-creation", type=int, default=None)
    lg.set_defaults(func=cmd_log)

    asrt = sub.add_parser("assert", help="verify a usage row exists for a spawn")
    asrt.add_argument("--project-dir", required=True)
    asrt.add_argument("--req", required=True)
    asrt.add_argument("--agent", required=True)
    asrt.add_argument("--stage", type=int, required=True)
    asrt.set_defaults(func=cmd_assert)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
