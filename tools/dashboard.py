#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Engineering OS — progress dashboard generator.

Renders a SELF-CONTAINED `.engineering-os/dashboard.html` (no server, no external
deps, works offline on file://) from the git-committed memory: a pipeline board
of every requirement by stage, lane breakdown, throughput, challenges, per-engineer
work, lessons, and a recent-activity feed. Open it in a browser; regenerate any
time with `/dashboard`. Reuses the team_digest aggregation.

Usage:  uv run tools/dashboard.py [--open]
"""
from __future__ import annotations

import html
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import team_digest  # noqa: E402

STAGES = {1: "Intake", 2: "Architect", 3: "Build", 4: "Security",
          5: "QA", 6: "Final review", 7: "Founder gate", 8: "Deploy"}
LANE_COLOR = {"express": "#3fb950", "standard": "#58a6ff", "high-stakes": "#f85149", "—": "#8b949e"}


def _esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def _feature_classes(eos: Path) -> dict:
    out = {}
    p = eos / "state" / "active.json"
    if p.exists():
        try:
            for r in json.loads(p.read_text()).get("active_requirements", []):
                out[r.get("req_id")] = r.get("feature_class") or "—"
        except Exception:
            pass
    return out


def _recent_events(eos: Path, n: int = 25) -> list[dict]:
    evs = []
    dl = eos / "decision-log"
    if dl.is_dir():
        for f in sorted(dl.rglob("*.jsonl")):
            for line in f.read_text(errors="replace").splitlines():
                line = line.strip()
                if line:
                    try:
                        evs.append(json.loads(line))
                    except Exception:
                        pass
    evs.sort(key=lambda e: str(e.get("ts", "")))
    return evs[-n:][::-1]


def _kpi(label, value, sub=""):
    return (f'<div class="kpi"><div class="kpi-v">{_esc(value)}</div>'
            f'<div class="kpi-l">{_esc(label)}</div>'
            f'{f"<div class=kpi-s>{_esc(sub)}</div>" if sub else ""}</div>')


def render(eos: Path, d: dict) -> str:
    fclass = _feature_classes(eos)
    # group in-flight by stage
    cols = defaultdict(list)
    for r in d["in_flight"]:
        try:
            st = int(r.get("stage") or 0)
        except Exception:
            st = 0
        cols[st].append(r)

    # board columns
    board = ""
    for st in sorted(STAGES):
        cards = ""
        for r in cols.get(st, []):
            lane = fclass.get(r["req_id"], "—")
            engs = ", ".join(d["feature_engineers"].get(r["req_id"], [])) or "—"
            cards += (
                f'<div class="card" style="border-left:3px solid {LANE_COLOR.get(lane, "#8b949e")}">'
                f'<div class="card-id">{_esc(r["req_id"])}</div>'
                f'<div class="card-meta">{_esc(r.get("status"))}</div>'
                f'<div class="card-meta">👤 {_esc(r.get("owner"))} · 🧑‍💻 {_esc(engs)} · <span class="lane">{_esc(lane)}</span></div>'
                f'</div>')
        board += (f'<div class="col"><div class="col-h">{st}. {STAGES[st]} '
                  f'<span class="count">{len(cols.get(st, []))}</span></div>{cards or "<div class=empty>—</div>"}</div>')

    # throughput (shipped per day)
    by_day = Counter(str(s.get("ts", ""))[:10] for s in d["shipped"] if s.get("ts"))
    tmax = max(by_day.values(), default=1)
    bars = "".join(
        f'<div class="bar" title="{_esc(day)}: {n}"><div class="bar-fill" style="height:{int(n / tmax * 60) + 4}px"></div>'
        f'<div class="bar-x">{_esc(day[5:])}</div></div>'
        for day, n in sorted(by_day.items())) or '<div class="empty">no ships yet</div>'

    # lane breakdown
    lane_counts = Counter(fclass.get(r["req_id"], "—") for r in d["in_flight"])
    lanes = "".join(
        f'<span class="pill" style="background:{LANE_COLOR.get(l, "#8b949e")}22;color:{LANE_COLOR.get(l, "#8b949e")}">{_esc(l)}: {c}</span>'
        for l, c in lane_counts.items()) or '<span class="empty">—</span>'

    # challenges grouped
    ch = defaultdict(list)
    for c in d["challenges"]:
        ch[c["req_id"]].append(c["type"])
    chrows = "".join(
        f'<li><b>{_esc(req)}</b> <span class="muted">{_esc(", ".join(sorted(set(t))))}</span></li>'
        for req, t in list(ch.items())[:15]) or '<li class="empty">none — clean</li>'

    # engineers
    engrows = "".join(
        f'<li><b>{_esc(e)}</b> <span class="muted">{_esc(", ".join(reqs))}</span></li>'
        for e, reqs in sorted(d["by_engineer"].items())) or '<li class="empty">no run folders</li>'

    # shipped list
    shiprows = "".join(
        f'<li><b>{_esc(s["req_id"])}</b> <span class="muted">{_esc(s.get("type"))} · {_esc(s.get("ts"))}</span></li>'
        for s in d["shipped"][-10:][::-1]) or '<li class="empty">none yet</li>'

    # recent activity
    actrows = "".join(
        f'<li><span class="muted">{_esc(str(e.get("ts", ""))[11:19])}</span> '
        f'<b>{_esc(e.get("actor", "?"))}</b> {_esc(e.get("type", ""))} '
        f'<span class="muted">{_esc(e.get("req_id", ""))}</span></li>'
        for e in _recent_events(eos)) or '<li class="empty">no events</li>'

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kpis = (_kpi("In flight", len(d["in_flight"]))
            + _kpi("Shipped", len(d["shipped"]))
            + _kpi("Challenges", len(d["challenges"]), f'{len(ch)} features')
            + _kpi("Engineers", len(d["by_engineer"]))
            + _kpi("Lessons", d["lessons"])
            + _kpi("Decision events", d["event_count"]))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brain — Engineering Progress</title>
<style>
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:#0d1117;color:#e6edf3}}
header{{padding:18px 24px;border-bottom:1px solid #21262d;display:flex;justify-content:space-between;align-items:baseline}}
h1{{font-size:18px;margin:0}} .sub{{color:#8b949e;font-size:12px}}
.wrap{{padding:20px 24px;max-width:1400px;margin:0 auto}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}}
.kpi{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px}}
.kpi-v{{font-size:26px;font-weight:700}} .kpi-l{{color:#8b949e;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
.kpi-s{{color:#8b949e;font-size:11px;margin-top:2px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:#8b949e;margin:26px 0 10px}}
.board{{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}}
.col{{flex:0 0 200px;background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:8px}}
.col-h{{font-size:12px;font-weight:600;color:#c9d1d9;margin-bottom:8px;display:flex;justify-content:space-between}}
.count{{background:#21262d;border-radius:10px;padding:0 7px;color:#8b949e;font-size:11px}}
.card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:8px;margin-bottom:8px}}
.card-id{{font-weight:600;font-size:12px;word-break:break-all}} .card-meta{{color:#8b949e;font-size:11px;margin-top:3px}}
.lane{{font-weight:600}} .empty{{color:#484f58;font-size:12px;font-style:italic}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.panel{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px}}
ul{{list-style:none;margin:0;padding:0}} li{{padding:4px 0;border-bottom:1px solid #21262d;font-size:13px}}
li:last-child{{border:0}} .muted{{color:#8b949e;font-size:12px}}
.pill{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-right:6px}}
.bars{{display:flex;gap:6px;align-items:flex-end;height:90px}}
.bar{{display:flex;flex-direction:column;align-items:center;justify-content:flex-end}}
.bar-fill{{width:22px;background:#3fb950;border-radius:3px 3px 0 0}} .bar-x{{font-size:9px;color:#8b949e;margin-top:3px}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>🧠 Brain — Engineering Progress</h1><span class="sub">generated {now} · regenerate with <code>/dashboard</code></span></header>
<div class="wrap">
  <div class="kpis">{kpis}</div>
  <h2>Pipeline board</h2><div class="board">{board}</div>
  <h2>Lanes (in flight)</h2><div>{lanes}</div>
  <div class="grid" style="margin-top:8px">
    <div class="panel"><h2 style="margin-top:0">Throughput (shipped/day)</h2><div class="bars">{bars}</div></div>
    <div class="panel"><h2 style="margin-top:0">Challenges &amp; bounces</h2><ul>{chrows}</ul></div>
    <div class="panel"><h2 style="margin-top:0">Who's working on what</h2><ul>{engrows}</ul></div>
    <div class="panel"><h2 style="margin-top:0">Recently shipped</h2><ul>{shiprows}</ul></div>
  </div>
  <h2>Recent activity</h2><div class="panel"><ul>{actrows}</ul></div>
</div></body></html>"""


def main() -> int:
    eos = team_digest.eos_root()
    if not eos.is_dir():
        print("[dashboard] no .engineering-os/ found — run /eos-init first.")
        return 1
    d = team_digest.collect(eos, None)
    out = eos / "dashboard.html"
    out.write_text(render(eos, d))
    print(f"[dashboard] wrote {out}")
    print(f"[dashboard] in-flight={len(d['in_flight'])} shipped={len(d['shipped'])} "
          f"challenges={len(d['challenges'])} engineers={len(d['by_engineer'])}")
    print(f"[dashboard] open it:  open {out}")
    if "--open" in sys.argv:
        import subprocess
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.run([opener, str(out)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
