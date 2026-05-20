#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Engineering OS — team digest (Goal 3: cross-engineer awareness).

When multiple product engineers use the team on one Brain repo, each operates
their own sessions — but the memory is git-shared. This synthesizes that shared
memory into ONE view so any engineer instantly sees what the WHOLE team has
built and the challenges everyone hit — not just their own work.

Reads (all from the git-committed .engineering-os/):
  - state/active.json        → in-flight requirements (stage/status/owner)
  - runs/<ts>__<hex>__<req>__<operator>/  → which ENGINEER worked on which feature
  - decision-log/**/*.jsonl  → events; challenges = bounces / violations / rollbacks
  - lessons-learned.md       → accumulated lessons count

Pairs with /recall-similar (semantic pull) — this is the push/overview side.

Usage:
  uv run tools/team_digest.py [--days N] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

CHALLENGE_HINTS = ("bounce", "bounced", "veto", "violation", "rollback", "reject",
                   "challenge", "blocked", "fail", "remediation")
TERMINAL_STATUS = ("shipped", "rejected", "killed", "done")


def eos_root() -> Path:
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    for c in ([Path(base)] if base else []) + [Path.cwd()]:
        if (c / ".engineering-os").is_dir():
            return c / ".engineering-os"
    # git toplevel
    try:
        import subprocess
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=False).stdout.strip()
        if top and (Path(top) / ".engineering-os").is_dir():
            return Path(top) / ".engineering-os"
    except Exception:
        pass
    return Path.cwd() / ".engineering-os"


def _within(ts: str, cutoff: datetime | None) -> bool:
    if not cutoff:
        return True
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff
    except Exception:
        return True


def collect(eos: Path, days: int | None) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)) if days else None

    # in-flight (terminal/shipped statuses are split out, not counted as in-flight)
    in_flight, completed_state = [], []
    state = eos / "state" / "active.json"
    if state.exists():
        try:
            data = json.loads(state.read_text())
            for r in data.get("active_requirements", []):
                status = (r.get("status") or "").lower()
                row = {
                    "req_id": r.get("req_id"), "stage": r.get("stage"),
                    "status": r.get("status"),
                    "owner": r.get("current_owner_persona") or r.get("current_owner"),
                    "last": r.get("last_journal_entry_at") or r.get("last_journal_at"),
                }
                if any(t in status for t in TERMINAL_STATUS):
                    completed_state.append(row)
                else:
                    in_flight.append(row)
        except Exception:
            pass

    # engineer → features, from run-folder names: <ts>__<hex>__<req-id>__<operator>
    by_engineer: dict[str, set] = defaultdict(set)
    feature_engineers: dict[str, set] = defaultdict(set)
    runs = eos / "runs"
    if runs.is_dir():
        for d in runs.iterdir():
            if not d.is_dir():
                continue
            # tolerate both 3-part (ts__req__operator) and 4-part (ts__hex__req__operator)
            parts = d.name.split("__")
            if len(parts) >= 3:
                req_id, operator = parts[-2], parts[-1]
                operator = operator.split("-via-")[0]  # normalize delegated form
                by_engineer[operator].add(req_id)
                feature_engineers[req_id].add(operator)

    # events + challenges from the decision log
    shipped, challenges = [], []
    event_count = 0
    dl = eos / "decision-log"
    if dl.is_dir():
        for f in sorted(dl.rglob("*.jsonl")):
            for line in f.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ts = str(e.get("ts", ""))
                if not _within(ts, cutoff):
                    continue
                event_count += 1
                etype = str(e.get("type", "")).lower()
                req = e.get("req_id", "")
                if etype in ("shipped", "approved", "deployed"):
                    shipped.append({"req_id": req, "type": etype, "ts": ts})
                if any(h in etype for h in CHALLENGE_HINTS):
                    challenges.append({"req_id": req, "type": etype, "ts": ts,
                                       "actor": e.get("actor", "")})

    # lessons
    lessons = 0
    ll = eos / "lessons-learned.md"
    if ll.exists():
        lessons = len(re.findall(r"^##\s", ll.read_text(), re.M))

    # fold state-derived completions (status terminal) into shipped, dedupe by req_id
    seen_ship = {s["req_id"] for s in shipped}
    for r in completed_state:
        if r["req_id"] not in seen_ship:
            shipped.append({"req_id": r["req_id"], "type": r["status"], "ts": r.get("last") or ""})
            seen_ship.add(r["req_id"])

    return {"in_flight": in_flight, "by_engineer": {k: sorted(v) for k, v in by_engineer.items()},
            "feature_engineers": {k: sorted(v) for k, v in feature_engineers.items()},
            "shipped": shipped, "challenges": challenges,
            "lessons": lessons, "event_count": event_count}


def render(d: dict, days: int | None) -> str:
    out = []
    window = f" (last {days}d)" if days else ""
    out.append(f"# Team Digest{window} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    out.append(f"## In flight ({len(d['in_flight'])})")
    if d["in_flight"]:
        for r in d["in_flight"]:
            eng = ", ".join(d["feature_engineers"].get(r["req_id"], [])) or "—"
            out.append(f"- **{r['req_id']}** — Stage {r['stage']} ({r['status']}) — owner: {r['owner']} — engineer(s): {eng}")
    else:
        out.append("- (nothing in flight)")
    out.append("")

    out.append(f"## Recently shipped ({len(d['shipped'])})")
    for s in d["shipped"][-10:]:
        out.append(f"- {s['req_id']} — {s['type']} @ {s['ts']}")
    if not d["shipped"]:
        out.append("- (none in window)")
    out.append("")

    feats = {c["req_id"] for c in d["challenges"]}
    out.append(f"## Challenges & bounces ({len(d['challenges'])} across {len(feats)} features)")
    grouped = defaultdict(list)
    for c in d["challenges"]:
        grouped[c["req_id"]].append(c)
    for req, cs in list(grouped.items())[:20]:
        kinds = ", ".join(sorted({c["type"] for c in cs}))
        out.append(f"- **{req}**: {len(cs)}× — {kinds}")
    if not d["challenges"]:
        out.append("- (none recorded — clean window)")
    out.append("")

    out.append(f"## Who's working on what ({len(d['by_engineer'])} engineers)")
    for eng, reqs in sorted(d["by_engineer"].items()):
        out.append(f"- **{eng}**: {', '.join(reqs)}")
    if not d["by_engineer"]:
        out.append("- (no run folders yet)")
    out.append("")

    out.append(f"## Lessons learned: {d['lessons']} entries  ·  decision-log events scanned: {d['event_count']}")
    out.append("\n> Pair this overview with `/recall-similar <topic>` to pull the detail on any feature or challenge.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS cross-engineer team digest")
    ap.add_argument("--days", type=int, help="only events within the last N days")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    eos = eos_root()
    if not eos.is_dir():
        msg = "no .engineering-os/ found — run /eos-init first."
        print(json.dumps({"error": msg}) if args.json else f"[team-digest] {msg}")
        return 1
    d = collect(eos, args.days)
    print(json.dumps(d, ensure_ascii=False, indent=2) if args.json else render(d, args.days))
    return 0


if __name__ == "__main__":
    main()
    raise SystemExit(0)
