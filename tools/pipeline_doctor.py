#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Engineering OS — pipeline doctor (Goal 2: smooth, flawless, autonomous execution).

Statically validates the orchestration graph so a broken handoff chain is caught
BEFORE a run, not during one. Checks:

  C1 state-machine integrity — every transition target is a real state;
     terminals have no transitions; every non-terminal is reachable from `intake`.
  C2 lane integrity — each lane's stage list references defined stage ids.
  C3 personas resolve — every persona in the workflow has an agents/<name>.md.
  C4 agent handoffs resolve — every `subagent_type="X"` in an agent points at a
     real agent (catches a handoff into the void).
  C5 advertised commands exist — every `/command` the session-start hook tells
     users about exists as a skill folder (catches broken UX promises).
  C6 skill-matrix sanity — every skills/<x>/ has a SKILL.md whose `name:` matches.

Exit 0 if all pass; 1 if any check fails. Run before relying on autonomous flow,
and after any change to states/lanes/agents/skills.

Usage:  uv run tools/pipeline_doctor.py [--quiet]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AGENTS = {p.stem for p in (ROOT / "agents").glob("*.md")}
SKILLS = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def c1_state_machine() -> tuple[str, bool, list[str]]:
    issues = []
    sm = _load_yaml("workflows/state-machine.yaml")
    states = sm.get("states", {})
    names = set(states)
    terminal = set()
    for name, body in states.items():
        tos = body.get("transitions_to", []) or []
        if not tos:
            terminal.add(name)
        for t in tos:
            if t not in names:
                issues.append(f"state '{name}' → unknown state '{t}'")
    # reachability from intake
    start = "intake" if "intake" in names else next(iter(names), None)
    seen, stack = set(), [start] if start else []
    while stack:
        s = stack.pop()
        if s in seen:
            continue
        seen.add(s)
        stack += (states.get(s, {}).get("transitions_to", []) or [])
    manual_entry = {"paused"}  # entered via /pause from any state, not a graph edge
    for n in names:
        if n not in seen and n not in terminal and n not in manual_entry:
            issues.append(f"state '{n}' is unreachable from '{start}'")
    return ("C1 state-machine integrity", not issues, issues)


def c2_lanes() -> tuple[str, bool, list[str]]:
    issues = []
    wf = _load_yaml("workflows/requirement-to-release.yaml")
    stage_ids = {s["id"] for s in wf.get("stages", [])}
    lanes = wf.get("lanes", {})
    if not lanes:
        issues.append("no `lanes:` block found (tiering missing)")
    for lane, body in lanes.items():
        for sid in body.get("stages", []):
            if sid not in stage_ids:
                issues.append(f"lane '{lane}' references undefined stage {sid}")
    return ("C2 lane integrity", not issues, issues)


def c3_personas() -> tuple[str, bool, list[str]]:
    issues = []
    wf = _load_yaml("workflows/requirement-to-release.yaml")
    for key, body in (wf.get("personas", {}) or {}).items():
        agent = body.get("agent")
        if agent and agent not in AGENTS:
            issues.append(f"persona '{key}' → missing agents/{agent}.md")
    return ("C3 personas resolve to agent files", not issues, issues)


def c4_handoffs() -> tuple[str, bool, list[str]]:
    issues = []
    pat = re.compile(r'subagent_type\s*=\s*"([a-z0-9-]+)"')
    for af in (ROOT / "agents").glob("*.md"):
        for m in pat.finditer(af.read_text()):
            target = m.group(1)
            if target not in AGENTS and not target.startswith("<"):
                issues.append(f"{af.name} hands off to unknown agent '{target}'")
    return ("C4 agent handoffs resolve", not issues, issues)


def c5_advertised_commands() -> tuple[str, bool, list[str]]:
    issues = []
    hook = (ROOT / "hooks" / "on-session-start.sh").read_text()
    # A command is a /token followed by an arg marker (` <`, ` --`, ` for`) — this
    # excludes path fragments like ${ROOT}/tools or 2>/dev/null.
    advertised = set(re.findall(r"/([a-z][a-z-]+)(?=\s+(?:<|--|for\b))", hook))
    for cmd in sorted(advertised):
        if cmd not in SKILLS:
            issues.append(f"hook advertises /{cmd} but skills/{cmd}/ does not exist")
    return ("C5 advertised commands exist", not issues, issues)


def c6_skill_matrix() -> tuple[str, bool, list[str]]:
    issues = []
    for d in (ROOT / "skills").iterdir():
        if not d.is_dir():
            continue
        sk = d / "SKILL.md"
        if not sk.exists():
            issues.append(f"skills/{d.name}/ has no SKILL.md")
            continue
        m = re.search(r"^name:\s*(\S+)", sk.read_text(), re.M)
        if not m:
            issues.append(f"skills/{d.name}/SKILL.md missing `name:` frontmatter")
        elif m.group(1) != d.name:
            issues.append(f"skills/{d.name}/ name '{m.group(1)}' != folder")
    return ("C6 skill folders well-formed", not issues, issues)


def main() -> int:
    quiet = "--quiet" in sys.argv
    checks = [c1_state_machine, c2_lanes, c3_personas, c4_handoffs,
              c5_advertised_commands, c6_skill_matrix]
    all_ok = True
    print("=== pipeline-doctor ===")
    for fn in checks:
        name, ok, issues = fn()
        all_ok = all_ok and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok or not quiet:
            for i in issues:
                print(f"        - {i}")
    print("=======================")
    print("OK — orchestration graph is consistent." if all_ok
          else "FAIL — fix the above before relying on autonomous flow.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
