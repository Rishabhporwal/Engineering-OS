#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Engineering OS — interactive progress dashboard generator (PM-grade).

Renders a SELF-CONTAINED, INTERACTIVE `.engineering-os/dashboard.html` (no server,
no external deps/CDN, works offline on file://) from the git-committed memory:
tabs for Overview, Agents (performance), Bugs, Features (sortable/filterable),
Tokens & cost, and Activity — with inline-SVG charts. Data is embedded as JSON
and rendered client-side (vanilla JS) so tables sort/filter live.

Sources: state/active.json · registry.json · decision-log/**/*.jsonl · runs/ ·
findings/*.md · usage.jsonl (token logging) · lessons-learned.md.

Usage:  uv run tools/dashboard.py [--open]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import team_digest  # noqa: E402

STAGES = {1: "Intake", 2: "Architect", 3: "Build", 4: "Security",
          5: "QA", 6: "Final", 7: "Founder", 8: "Deploy"}
# rough blended $ per 1M tokens (input+output) — estimate only
MODEL_RATE = {"opus": 30.0, "sonnet": 6.0, "haiku": 1.5}
DEFAULT_RATE = 8.0
BUG_HINT = ("bounce", "bounced", "veto", "violation", "rollback", "reject", "remediation", "fail")
TERMINAL = ("shipped", "rejected", "killed", "done")


def _all_events(eos: Path) -> list[dict]:
    out = []
    dl = eos / "decision-log"
    if dl.is_dir():
        for f in sorted(dl.rglob("*.jsonl")):
            for line in f.read_text(errors="replace").splitlines():
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    out.sort(key=lambda e: str(e.get("ts", "")))
    return out


def _requirements(eos: Path) -> list[dict]:
    reqs = {}
    reg = eos / "state" / "registry.json"
    if reg.exists():
        try:
            for r in json.loads(reg.read_text()).get("requirements", []):
                reqs[r.get("req_id")] = {"req_id": r.get("req_id"), "title": r.get("title", ""),
                                         "stage": None, "status": "", "owner": "", "feature_class": "—",
                                         "submitted": r.get("first_seen", "")}
        except Exception:
            pass
    act = eos / "state" / "active.json"
    if act.exists():
        try:
            for r in json.loads(act.read_text()).get("active_requirements", []):
                rid = r.get("req_id")
                reqs.setdefault(rid, {"req_id": rid, "title": r.get("title", "")})
                reqs[rid].update({
                    "title": r.get("title", reqs[rid].get("title", "")),
                    "stage": r.get("stage"), "status": r.get("status", ""),
                    "owner": r.get("current_owner_persona") or r.get("current_owner", ""),
                    "feature_class": r.get("feature_class") or "—",
                    "submitted": r.get("submitted_at") or reqs[rid].get("submitted", ""),
                })
        except Exception:
            pass
    return list(reqs.values())


def _findings(eos: Path) -> list[dict]:
    out = []
    d = eos / "findings"
    if d.is_dir():
        for f in sorted(d.glob("*.md")):
            src = f.stem
            for block in re.split(r"^##\s", f.read_text(errors="replace"), flags=re.M)[1:]:
                head = block.splitlines()[0] if block.splitlines() else ""
                sev = "MED"
                for s in ("P0", "HIGH", "MED", "LOW"):
                    if s in head.upper():
                        sev = s
                        break
                ts = (re.search(r"\d{4}-\d{2}-\d{2}[T \d:Z-]*", head) or [None])
                out.append({"source": src, "severity": sev, "text": head[:160],
                            "ts": ts.group(0).strip() if hasattr(ts, "group") else ""})
    return out


def _usage(eos: Path) -> list[dict]:
    out = []
    u = eos / "usage.jsonl"
    if u.exists():
        for line in u.read_text(errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def build(eos: Path) -> dict:
    base = team_digest.collect(eos, None)
    events = _all_events(eos)
    reqs = _requirements(eos)
    findings = _findings(eos)
    usage = _usage(eos)

    shipped_ids = {s["req_id"] for s in base["shipped"]}
    feng = base["feature_engineers"]

    # tokens
    tok_by_agent, tok_by_feat, tok_by_stage, tok_by_day = Counter(), Counter(), Counter(), Counter()
    tok_total = 0
    est_cost = 0.0
    for u in usage:
        n = int(u.get("total_tokens") or 0)
        tok_total += n
        tok_by_agent[u.get("agent", "?")] += n
        tok_by_feat[u.get("req_id", "?")] += n
        tok_by_stage[f'S{u.get("stage", "?")}'] += n
        tok_by_day[str(u.get("ts", ""))[:10]] += n
        est_cost += n / 1e6 * MODEL_RATE.get(str(u.get("model", "")).lower(), DEFAULT_RATE)

    # agent performance
    actors = defaultdict(lambda: {"events": 0, "stages": 0, "vetos": 0, "bounces": 0, "last": ""})
    for e in events:
        a = e.get("actor", "?")
        t = str(e.get("type", "")).lower()
        ar = actors[a]
        ar["events"] += 1
        if t.startswith("stage") or any(k in t for k in ("plan", "build", "review", "qa", "advance")):
            ar["stages"] += 1
        if "veto" in t:
            ar["vetos"] += 1
        if any(k in t for k in ("bounce", "remediation")):
            ar["bounces"] += 1
        ar["last"] = max(ar["last"], str(e.get("ts", "")))
    agents = []
    for a, r in actors.items():
        if a in ("system",):
            continue
        agents.append({"name": a, **r, "tokens": tok_by_agent.get(a, 0)})
    agents.sort(key=lambda x: -x["events"])

    # bugs = gate bounces/vetos (from events) + findings
    bugs = []
    for e in events:
        t = str(e.get("type", "")).lower()
        if any(h in t for h in BUG_HINT):
            rid = e.get("req_id", "")
            bugs.append({"ts": str(e.get("ts", "")), "type": e.get("type", ""),
                         "feature": rid, "source": "gate:" + (e.get("actor", "") or "?"),
                         "severity": "HIGH" if "veto" in t else "MED",
                         "status": "resolved" if rid in shipped_ids else "open"})
    for f in findings:
        bugs.append({"ts": f["ts"], "type": "finding:" + f["source"], "feature": "",
                     "source": f["source"], "severity": f["severity"], "status": "open",
                     "text": f["text"]})
    bugs.sort(key=lambda b: b["ts"], reverse=True)

    # features table
    bounce_by_req = Counter(b["feature"] for b in bugs if b["feature"])
    ship_ts = {s["req_id"]: s.get("ts", "") for s in base["shipped"]}
    features = []
    for r in reqs:
        rid = r["req_id"]
        features.append({
            "req": rid, "title": r.get("title", ""), "lane": r.get("feature_class", "—"),
            "stage": r.get("stage"), "status": r.get("status", ""),
            "owner": r.get("owner", ""), "engineers": ", ".join(feng.get(rid, [])) or "—",
            "bounces": bounce_by_req.get(rid, 0), "tokens": tok_by_feat.get(rid, 0),
            "submitted": r.get("submitted", ""), "shipped": ship_ts.get(rid, ""),
            "done": rid in shipped_ids,
        })
    features.sort(key=lambda x: (x["done"], str(x.get("submitted") or "")))

    # board (in-flight by stage)
    board = defaultdict(list)
    for f in features:
        if f["done"]:
            continue
        try:
            st = int(f["stage"] or 0)
        except Exception:
            st = 0
        if st:
            board[st].append(f)

    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "kpis": {
            "in_flight": len([f for f in features if not f["done"]]),
            "shipped": len(shipped_ids), "features": len(features),
            "bugs_open": len([b for b in bugs if b["status"] == "open"]),
            "bugs_total": len(bugs), "engineers": len(base["by_engineer"]),
            "tokens": tok_total, "cost": round(est_cost, 2),
            "lessons": base["lessons"], "events": base["event_count"],
        },
        "stages": STAGES,
        "board": {str(k): v for k, v in board.items()},
        "lanes": dict(Counter(f["lane"] for f in features if not f["done"])),
        "throughput": dict(Counter(s["ts"][:10] for s in base["shipped"] if s.get("ts"))),
        "agents": agents,
        "bugs": bugs,
        "features": features,
        "tokens": {"total": tok_total, "cost": round(est_cost, 2),
                   "by_agent": dict(tok_by_agent), "by_feature": dict(tok_by_feat),
                   "by_stage": dict(tok_by_stage), "by_day": dict(tok_by_day),
                   "has_data": bool(usage)},
        "activity": [{"ts": str(e.get("ts", "")), "actor": e.get("actor", "?"),
                      "type": e.get("type", ""), "req": e.get("req_id", "")}
                     for e in events[-40:][::-1]],
        "by_engineer": base["by_engineer"],
    }


SHELL = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Brain — Engineering Dashboard</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:#0d1117;color:#e6edf3}
header{padding:16px 24px;border-bottom:1px solid #21262d;display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px}
h1{font-size:17px;margin:0}.sub{color:#8b949e;font-size:12px}
nav{display:flex;gap:4px;padding:0 16px;border-bottom:1px solid #21262d;flex-wrap:wrap}
nav button{background:none;border:0;color:#8b949e;padding:11px 14px;cursor:pointer;font-size:13px;border-bottom:2px solid transparent}
nav button.on{color:#e6edf3;border-bottom-color:#58a6ff;font-weight:600}
.wrap{padding:20px 24px;max-width:1500px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:13px}
.kpi-v{font-size:24px;font-weight:700}.kpi-l{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#8b949e;margin:24px 0 10px}
.board{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px}
.col{flex:0 0 180px;background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:8px}
.col-h{font-size:12px;font-weight:600;margin-bottom:8px;display:flex;justify-content:space-between}
.count{background:#21262d;border-radius:10px;padding:0 7px;color:#8b949e;font-size:11px}
.card{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:8px;margin-bottom:8px;border-left:3px solid #8b949e}
.card-id{font-weight:600;font-size:12px;word-break:break-all}.card-meta{color:#8b949e;font-size:11px;margin-top:3px}
.panel{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px;margin-bottom:16px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #21262d;white-space:nowrap}
th{color:#8b949e;font-size:11px;text-transform:uppercase;cursor:pointer;user-select:none}
th:hover{color:#e6edf3}td.wrap{white-space:normal}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}
.muted{color:#8b949e}.empty{color:#484f58;font-style:italic;padding:10px}
input.filter{background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:7px;padding:7px 10px;width:260px;margin-bottom:10px}
.bars{display:flex;gap:8px;align-items:flex-end;height:130px;overflow-x:auto}
.bar{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:36px}
.bar .v{font-size:10px;color:#8b949e}.bar .b{width:26px;background:#58a6ff;border-radius:3px 3px 0 0;min-height:2px}
.bar .x{font-size:9px;color:#8b949e;margin-top:4px;max-width:54px;overflow:hidden;text-overflow:ellipsis}
.hidden{display:none}
</style></head><body>
<header><h1>🧠 Brain — Engineering Dashboard</h1><span class="sub" id="gen"></span></header>
<nav id="nav"></nav>
<div class="wrap" id="app"></div>
<script>const D=__DATA__;
const LANE={express:"#3fb950",standard:"#58a6ff","high-stakes":"#f85149","—":"#8b949e"};
const SEV={P0:"#f85149",HIGH:"#f85149",MED:"#d29922",LOW:"#8b949e"};
const $=h=>{const d=document.createElement('div');d.innerHTML=h;return d.firstChild};
const esc=s=>String(s==null?"":s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt=n=>n>=1e6?(n/1e6).toFixed(2)+'M':n>=1e3?(n/1e3).toFixed(1)+'k':String(n);
function bars(obj,color){const ks=Object.keys(obj).sort();const mx=Math.max(1,...Object.values(obj));
 if(!ks.length)return '<div class=empty>no data</div>';
 return '<div class=bars>'+ks.map(k=>{const v=obj[k];const h=Math.round(v/mx*100)+6;
  return `<div class=bar title="${esc(k)}: ${v}"><div class=v>${fmt(v)}</div><div class=b style="height:${h}px;background:${color||'#58a6ff'}"></div><div class=x>${esc(k)}</div></div>`}).join('')+'</div>'}
function kpi(l,v){return `<div class=kpi><div class=kpi-v>${esc(v)}</div><div class=kpi-l>${esc(l)}</div></div>`}
function table(rows,cols,id){
 if(!rows.length)return '<div class=empty>none</div>';
 const head='<tr>'+cols.map(c=>`<th data-k="${c.k}">${c.t}</th>`).join('')+'</tr>';
 const body=rows.map(r=>'<tr>'+cols.map(c=>`<td class="${c.wrap?'wrap':''}">${c.r?c.r(r):esc(r[c.k])}</td>`).join('')+'</tr>').join('');
 return `<table id="${id}"><thead>${head}</thead><tbody>${body}</tbody></table>`}
function sortable(id,rows,cols,render){
 let cur=null,asc=true;const host=document.getElementById(id);
 const draw=()=>{host.innerHTML=table(rows,cols,id+'_t');
  host.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;asc=cur===k?!asc:true;cur=k;
   rows.sort((a,b)=>{let x=a[k],y=b[k];if(typeof x==='number'){return asc?x-y:y-x}return asc?String(x).localeCompare(String(y)):String(y).localeCompare(String(x))});draw()})};
 draw();return draw}
const TABS={
 Overview(){let h=`<div class=kpis>${kpi('In flight',D.kpis.in_flight)}${kpi('Shipped',D.kpis.shipped)}${kpi('Open bugs',D.kpis.bugs_open)}${kpi('Engineers',D.kpis.engineers)}${kpi('Tokens',fmt(D.kpis.tokens))}${kpi('Est. cost','$'+D.kpis.cost)}${kpi('Lessons',D.kpis.lessons)}${kpi('Events',D.kpis.events)}</div>`;
  h+='<h2>Pipeline board</h2><div class=board>';
  for(const s of Object.keys(D.stages)){const cards=(D.board[s]||[]);
   h+=`<div class=col><div class=col-h><span>${s}. ${D.stages[s]}</span><span class=count>${cards.length}</span></div>`;
   h+=cards.map(c=>`<div class=card style="border-left-color:${LANE[c.lane]||'#8b949e'}"><div class=card-id>${esc(c.req)}</div><div class=card-meta>${esc(c.status)}</div><div class=card-meta>👤 ${esc(c.owner)} · ${esc(c.lane)}</div></div>`).join('')||'<div class=empty>—</div>';
   h+='</div>'}
  h+='</div><div class=grid2><div class=panel><h2>Lanes (in flight)</h2>'+bars(D.lanes,'#58a6ff')+'</div><div class=panel><h2>Throughput (shipped/day)</h2>'+bars(D.throughput,'#3fb950')+'</div></div>';
  return h},
 Agents(){let h='<h2>Agent performance</h2><div class=panel id=agt></div><div class=grid2><div class=panel><h2>Events by agent</h2>'+bars(Object.fromEntries(D.agents.map(a=>[a.name,a.events])))+'</div><div class=panel><h2>Tokens by agent</h2>'+bars(D.tokens.by_agent,'#a371f7')+'</div></div>';
  setTimeout(()=>sortable('agt',D.agents.slice(),[{k:'name',t:'Agent'},{k:'events',t:'Events'},{k:'stages',t:'Stages'},{k:'vetos',t:'VETOs'},{k:'bounces',t:'Bounces'},{k:'tokens',t:'Tokens',r:a=>fmt(a.tokens)},{k:'last',t:'Last active',r:a=>esc(String(a.last).slice(0,16))}]),0);
  return h},
 Bugs(){let h=`<div class=kpis>${kpi('Total',D.kpis.bugs_total)}${kpi('Open',D.kpis.bugs_open)}${kpi('Resolved',D.kpis.bugs_total-D.kpis.bugs_open)}</div>`;
  h+='<input class=filter id=bf placeholder="filter bugs…"><div class=panel id=bug></div>';
  const cols=[{k:'severity',t:'Sev',r:b=>`<span class=pill style="background:${(SEV[b.severity]||'#8b949e')}22;color:${SEV[b.severity]||'#8b949e'}">${esc(b.severity)}</span>`},{k:'type',t:'Type'},{k:'feature',t:'Feature'},{k:'source',t:'Source'},{k:'status',t:'Status',r:b=>`<span class=pill style="background:${b.status==='open'?'#f8514922':'#3fb95022'};color:${b.status==='open'?'#f85149':'#3fb950'}">${esc(b.status)}</span>`},{k:'ts',t:'When',r:b=>esc(String(b.ts).slice(0,16))},{k:'text',t:'Detail',wrap:1,r:b=>esc(b.text||'')}];
  setTimeout(()=>{const dr=sortable('bug',D.bugs.slice(),cols);document.getElementById('bf').oninput=e=>{const q=e.target.value.toLowerCase();const f=D.bugs.filter(b=>JSON.stringify(b).toLowerCase().includes(q));document.getElementById('bug').innerHTML=table(f,cols,'bug_t')}},0);
  return h},
 Features(){let h='<input class=filter id=ff placeholder="filter features…"><div class=panel id=feat></div>';
  const cols=[{k:'req',t:'Requirement'},{k:'lane',t:'Lane',r:f=>`<span class=pill style="background:${(LANE[f.lane]||'#8b949e')}22;color:${LANE[f.lane]||'#8b949e'}">${esc(f.lane)}</span>`},{k:'stage',t:'Stage'},{k:'status',t:'Status'},{k:'owner',t:'Owner'},{k:'engineers',t:'Engineer(s)'},{k:'bounces',t:'Bugs'},{k:'tokens',t:'Tokens',r:f=>fmt(f.tokens)},{k:'submitted',t:'Started',r:f=>esc(String(f.submitted).slice(0,10))},{k:'shipped',t:'Shipped',r:f=>esc(String(f.shipped).slice(0,10))}];
  setTimeout(()=>{sortable('feat',D.features.slice(),cols);document.getElementById('ff').oninput=e=>{const q=e.target.value.toLowerCase();const f=D.features.filter(x=>JSON.stringify(x).toLowerCase().includes(q));document.getElementById('feat').innerHTML=table(f,cols,'feat_t')}},0);
  return h},
 Tokens(){if(!D.tokens.has_data)return '<div class=panel><h2>Tokens &amp; cost</h2><div class=empty>No token usage logged yet. Runs after v0.14.0 record per-stage usage to <code>.engineering-os/usage.jsonl</code> (the orchestrator logs each spawn). This view fills in as the pipeline runs.</div></div>';
  let h=`<div class=kpis>${kpi('Total tokens',fmt(D.tokens.total))}${kpi('Est. cost','$'+D.tokens.cost)}</div>`;
  h+='<div class=grid2><div class=panel><h2>Tokens by agent</h2>'+bars(D.tokens.by_agent,'#a371f7')+'</div><div class=panel><h2>Tokens by feature</h2>'+bars(D.tokens.by_feature,'#58a6ff')+'</div><div class=panel><h2>Tokens by stage</h2>'+bars(D.tokens.by_stage,'#3fb950')+'</div><div class=panel><h2>Tokens by day</h2>'+bars(D.tokens.by_day,'#d29922')+'</div></div>';
  h+='<div class=sub style="margin-top:8px">Cost is a rough estimate (blended $/1M: opus 30 · sonnet 6 · haiku 1.5).</div>';
  return h},
 Activity(){return '<h2>Recent activity</h2><div class=panel>'+(D.activity.map(e=>`<div style="padding:4px 0;border-bottom:1px solid #21262d"><span class=muted>${esc(String(e.ts).slice(11,19))}</span> <b>${esc(e.actor)}</b> ${esc(e.type)} <span class=muted>${esc(e.req)}</span></div>`).join('')||'<div class=empty>no events</div>')+'</div>'},
};
document.getElementById('gen').textContent='generated '+D.generated+' · regenerate with /dashboard';
const nav=document.getElementById('nav'),app=document.getElementById('app');
Object.keys(TABS).forEach((name,i)=>{const b=document.createElement('button');b.textContent=name;b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));b.classList.add('on');app.innerHTML='';const out=TABS[name]();if(typeof out==='string')app.innerHTML=out};nav.appendChild(b);if(i===0)b.click()});
</script></body></html>"""


def main() -> int:
    eos = team_digest.eos_root()
    if not eos.is_dir():
        print("[dashboard] no .engineering-os/ found — run /eos-init first.")
        return 1
    data = build(eos)
    out = eos / "dashboard.html"
    out.write_text(SHELL.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    k = data["kpis"]
    print(f"[dashboard] wrote {out}")
    print(f"[dashboard] features={k['features']} in-flight={k['in_flight']} shipped={k['shipped']} "
          f"bugs={k['bugs_total']}(open {k['bugs_open']}) agents={len(data['agents'])} tokens={k['tokens']}")
    print(f"[dashboard] open it:  open {out}")
    if "--open" in sys.argv:
        import subprocess
        subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(out)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
