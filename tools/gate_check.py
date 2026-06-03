# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""gate_check — make the VETO a state-machine invariant, not a model's good behavior.

Security-F3: the Shreya/Tanvi/Rohan VETO is just an agent RETURNING a BOUNCE that the
orchestrator (also a model) is trusted to honor. Nothing in code stops a Stage-7/8
transition while an unresolved CRITICAL/HIGH sits in the run folder. This tool is that
stop: before advancing to the Founder gate or deploy, it reads the review artifacts and
REFUSES (exit 2) if any review isn't PASS or any unresolved CRITICAL/HIGH finding exists —
regardless of what the model decided.

Usage:
  uv run gate_check.py --run-dir <run folder> --to founder_gate   # before Stage 7
  uv run gate_check.py --run-dir <run folder> --to deploy          # before Stage 8 (/approve)

Exit 0 = clear to advance. Exit 2 = BLOCKED (prints the blocking findings).
Reads JSON artifacts structurally; falls back to scanning the .md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# which review artifacts gate which transition
GATES = {
    "founder_gate": ["security-review", "qa-review"],
    "deploy":       ["security-review", "qa-review", "final-review"],
}
PASS_RE = re.compile(r"\b(verdict|recommendation|decision)\b[:\s*]*\**\s*(PASS|APPROVE)\b", re.I)
FAIL_RE = re.compile(r"\b(verdict|recommendation|decision)\b[:\s*]*\**\s*(FAIL|BOUNCE|REJECT|VETO)\b", re.I)
# a CRITICAL/HIGH finding line not marked resolved/deferred/accepted
SEV_RE = re.compile(r"\b(severity[:\s*]*\**\s*)?(critical|high)\b", re.I)
RESOLVED_RE = re.compile(r"\b(resolved|fixed|deferred|defer|accepted|waived|n/?a|mitigated)\b", re.I)


def find_artifact(run_dir: Path, stem: str) -> Path | None:
    for ext in (".json", ".md"):
        for p in run_dir.glob(f"*{stem}*{ext}"):
            return p
    return None


def check_artifact(p: Path) -> list[str]:
    """Return a list of blocking reasons for this artifact (empty = clear)."""
    text = p.read_text(errors="ignore")
    reasons = []

    if p.suffix == ".json":
        try:
            obj = json.loads(text)
            verdict = str(obj.get("verdict") or obj.get("recommendation") or "").upper()
            if verdict and verdict not in ("PASS", "APPROVE"):
                reasons.append(f"{p.name}: verdict is {verdict} (not PASS)")
            gates = obj.get("gates", {})
            if gates.get("no_critical") is False:
                reasons.append(f"{p.name}: gates.no_critical = false (a CRITICAL is open)")
            if gates.get("no_high") is False:
                reasons.append(f"{p.name}: gates.no_high = false (a HIGH is open)")
            for f in obj.get("findings", []):
                sev = str(f.get("severity", "")).lower()
                status = str(f.get("status", "")).lower()
                if sev in ("critical", "high", "block") and status not in ("resolved", "deferred", "accepted", "waived"):
                    reasons.append(f"{p.name}: unresolved {sev.upper()} — {f.get('title', '?')}")
            return reasons
        except json.JSONDecodeError:
            pass  # fall through to markdown scan

    # markdown fallback: verdict + unresolved CRITICAL/HIGH lines
    if FAIL_RE.search(text) and not PASS_RE.search(text):
        reasons.append(f"{p.name}: verdict is FAIL/BOUNCE (not PASS)")
    elif not PASS_RE.search(text):
        reasons.append(f"{p.name}: no explicit PASS verdict found")
    for line in text.splitlines():
        if SEV_RE.search(line) and not RESOLVED_RE.search(line) and re.search(r"finding|issue|vuln|severity", line, re.I):
            reasons.append(f"{p.name}: possible unresolved CRITICAL/HIGH → {line.strip()[:90]}")
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser(prog="gate_check")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--to", required=True, choices=list(GATES))
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"gate_check: run dir not found: {run_dir}", file=sys.stderr)
        return 2  # fail CLOSED — a missing run folder must not advance

    blocking = []
    missing = []
    for stem in GATES[args.to]:
        art = find_artifact(run_dir, stem)
        if art is None:
            missing.append(stem)
            continue
        blocking += check_artifact(art)

    if missing:
        blocking.append(f"required review artifact(s) missing: {', '.join(missing)} — the gate never ran")

    if blocking:
        print(f"BLOCKED: cannot advance to {args.to} — VETO is a state-machine invariant, not a suggestion:", file=sys.stderr)
        for b in blocking:
            print(f"  ✗ {b}", file=sys.stderr)
        print("\nResolve the finding(s) / re-run the review to PASS, or get a Founder-logged waiver via Rohan.", file=sys.stderr)
        return 2
    print(f"gate_check: clear to advance to {args.to} (all reviews PASS, no unresolved CRITICAL/HIGH)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
