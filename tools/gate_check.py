# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""gate_check — make the VETO a state-machine invariant, not a model's good behavior.

A VETO (Security Reviewer / QA Engineer / Engineering Advisor) is otherwise just an agent
RETURNING a BOUNCE that the orchestrator (also a model) is trusted to honor. Nothing in
code stops a Stage-7/8 transition while an unresolved CRITICAL/HIGH sits in the run folder.
This tool is that stop: before advancing to the Stakeholder gate or deploy, it reads the
review artifacts and REFUSES (exit 2) if any review isn't PASS or any unresolved
CRITICAL/HIGH finding exists — regardless of what the model decided.

Usage:
  uv run gate_check.py --run-dir <run folder> --to stakeholder_gate   # before Stage 7
  uv run gate_check.py --run-dir <run folder> --to deploy             # before Stage 8 (/approve)

Exit 0 = clear to advance. Exit 2 = BLOCKED (prints the blocking findings).
Reads JSON artifacts structurally; falls back to scanning the .md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# which review artifacts gate which transition.
GATES = {
    "stakeholder_gate": ["security-review", "qa-review"],
    "deploy":           ["security-review", "qa-review", "final-review"],
}
PASS_RE = re.compile(r"\b(verdict|recommendation|decision)\b[:\s*]*\**\s*(PASS|APPROVE)\b", re.I)
FAIL_RE = re.compile(r"\b(verdict|recommendation|decision)\b[:\s*]*\**\s*(FAIL|BOUNCE|REJECT|VETO)\b", re.I)
SEV_RE = re.compile(r"\b(severity[:\s*]*\**\s*)?(critical|high)\b", re.I)
# ONLY an explicit resolution clears a CRITICAL/HIGH. "mitigated"/"deferred"/"accepted"
# do NOT clear it (a CRITICAL tagged 'mitigated' without being mitigated would otherwise walk
# through). You cannot ship past a CRITICAL by deferring it — only a Stakeholder-logged waiver can.
RESOLVED_RE = re.compile(r"\b(resolved|fixed in [0-9a-f]{6,}|stakeholder.?waiver|waiver.?logged)\b", re.I)
# Deferring security/compliance work to a follow-up is the evasion that has NO severity keyword
# ("enforcement deferred to a follow-up"). If defer-language sits near a security/compliance
# keyword, BLOCK regardless of whether 'critical/high' was written.
DEFER_RE = re.compile(r"\b(deferred?|follow.?up|next.?sprint|tech.?debt|backlog|TODO|later|punt(ed)?)\b", re.I)
# GENERIC security/compliance keyword set — the compliance terms (consent, retention,
# residency, contact-window, …) are regime-agnostic markers; a product can extend them
# from its COMPLIANCE.md regime.
SECKW_RE = re.compile(r"\b(window|contact.?hours|consent|retention|residency|rls|requirerole|requiretenantmember|"
                      r"secret|pii|cross.?tenant|tenant_id|bypassrls|plaintext|encrypt|kms|"
                      r"compliance|data.?protection|privacy|traceab|tenant)\b", re.I)


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
        # (1) a CRITICAL/HIGH finding line that isn't explicitly resolved → block (a bare
        #     'mitigated'/'deferred' no longer clears it — only resolved/fixed-in-<sha>/waiver does).
        if SEV_RE.search(line) and not RESOLVED_RE.search(line) and re.search(r"finding|issue|vuln|severity", line, re.I):
            reasons.append(f"{p.name}: unresolved CRITICAL/HIGH → {line.strip()[:90]}")
        # (2) the no-severity-keyword evasion: security/compliance work deferred to a follow-up.
        #     defer-language NEAR a security keyword blocks regardless of whether 'critical' was written.
        elif DEFER_RE.search(line) and SECKW_RE.search(line) and not RESOLVED_RE.search(line):
            reasons.append(f"{p.name}: security/compliance work deferred to a follow-up (cannot advance past it) → {line.strip()[:90]}")
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
        print("\nResolve the finding(s) / re-run the review to PASS, or get a Stakeholder-logged waiver via the Engineering Advisor.", file=sys.stderr)
        return 2
    print(f"gate_check: clear to advance to {args.to} (all reviews PASS, no unresolved CRITICAL/HIGH)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
