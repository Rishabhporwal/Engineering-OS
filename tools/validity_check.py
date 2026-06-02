# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""validity_check — make "your verification can actually fail" mechanical (O11).

O11 was the #1 recurring bounce: green tests under BYPASSRLS/superuser, inert
security probes, tautological parity asserts. v2 stated the rule in prose across
five files but NOTHING checked it — a builder could claim a negative control with
none existing and no tool could tell. This is that tool.

Two checks:
  1. ANTI-PATTERN scan (always): flag bypass-green tests on tenancy/auth paths —
     BYPASSRLS, SET ROLE postgres / superuser DSNs, disabled RLS, tautological
     asserts (assertEqual(x, x)), and parity asserted against itself.
  2. NEGATIVE-CONTROL presence (--require-negative-control): on a high-stakes path,
     the QA/security artifact MUST carry a non-empty negative_control (a probe that
     removes the guard and captures the RED failure). Empty → defect.

Usage:
  uv run validity_check.py --paths <test dirs/files> [--artifacts qa-review.* security-review.*] [--require-negative-control]

Exit 0 = valid. Exit 3 = a validity defect (same severity as a missing usage row).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Bypass / inert / tautology anti-patterns (the O11 failure classes).
ANTIPATTERNS = [
    (r"\bBYPASSRLS\b", "test runs under BYPASSRLS — RLS is never exercised"),
    (r"SET\s+ROLE\s+(postgres|rds_superuser|supabase_admin)", "test sets a superuser role — tenancy bypassed"),
    (r"ALTER\s+TABLE\s+\w+\s+DISABLE\s+ROW\s+LEVEL\s+SECURITY", "RLS disabled in a test path"),
    (r"postgres(ql)?://(postgres|admin|root|supabase_admin):", "superuser DSN in a test — not the app's real context"),
    (r"assert\w*\(\s*([A-Za-z_][\w.]*)\s*,\s*\1\s*\)", "tautological assert (x == x) — cannot fail"),
    (r"role\s*=\s*['\"]service_role['\"]", "service_role key in a tenancy test — bypasses RLS"),
]
# A negative control proves the test fails when the guard is gone.
NEG_CONTROL_MARKERS = [
    r"negative[_\s-]?control", r"guard\s+removed", r"protection\s+removed",
    r"expect[s]?\s+(it\s+)?to\s+fail\s+(when|without)", r"fails?\s+without\s+(the\s+)?(rls|guard|requirerole)",
]
HIGH_STAKES_HINT = re.compile(r"(rls|workspace_id|requireRole|requireWorkspaceMember|tenant|auth|"
                              r"decision_log|gmv|billing|minor_units|consent|dlt|ncpr)", re.I)


def iter_files(paths: list[Path]):
    for p in paths:
        if p.is_dir():
            yield from (f for f in p.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".ts", ".tsx", ".sql", ".md", ".json")
                        and ".git/" not in str(f))
        elif p.is_file():
            yield p


_CODE_SUFFIXES = {".py", ".ts", ".tsx", ".sql", ".js", ".tsx"}


def scan_antipatterns(files) -> list[str]:
    viol = []
    for f in files:
        # anti-patterns live in CODE; .md/.json prose that mentions BYPASSRLS as an
        # example (docs, this tool, the schemas) must not false-positive.
        if f.suffix not in _CODE_SUFFIXES:
            continue
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat, why in ANTIPATTERNS:
                if re.search(pat, line):
                    viol.append(f"  VALIDITY  {f}:{i}  {why}")
    return viol


def has_negative_control(artifacts) -> bool:
    for f in artifacts:
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        # structured JSON artifact: judge SOLELY on the parsed array (don't text-match
        # the literal field name, which would always "match").
        if f.suffix == ".json":
            try:
                obj = json.loads(text)
                if isinstance(obj.get("negative_control"), list) and obj["negative_control"]:
                    return True
            except (json.JSONDecodeError, AttributeError):
                pass
            continue
        # markdown/other artifact: require a real negative-control section + evidence
        if any(re.search(m, text, re.I) for m in NEG_CONTROL_MARKERS):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(prog="validity_check")
    ap.add_argument("--paths", nargs="*", default=[], help="test dirs/files to scan for anti-patterns")
    ap.add_argument("--artifacts", nargs="*", default=[], help="qa-review / security-review artifacts")
    ap.add_argument("--require-negative-control", action="store_true",
                    help="fail if no non-empty negative control is present (use on high-stakes paths)")
    args = ap.parse_args()

    problems = 0
    files = list(iter_files([Path(p) for p in args.paths]))
    viol = scan_antipatterns(files)
    if viol:
        print("BYPASS/INERT/TAUTOLOGY anti-patterns (O11 — a green test here is false confidence):", file=sys.stderr)
        for v in viol:
            print(v, file=sys.stderr)
        problems += len(viol)

    if args.require_negative_control:
        artifacts = [Path(a) for a in args.artifacts if Path(a).exists()]
        if not has_negative_control(artifacts):
            print("MISSING NEGATIVE CONTROL: this is a high-stakes (tenancy/auth/money) change, but no probe "
                  "proves the test FAILS when the protection is removed. 'Your verification must be able to "
                  "fail.' Add a negative_control entry (guard removed + captured red output) before PASS.",
                  file=sys.stderr)
            problems += 1

    if problems == 0:
        print(f"validity_check: clean ({len(files)} files scanned)")
        return 0
    print(f"\nDEFECT: {problems} verification-validity issue(s) — VETO. Fix before handoff (O11).", file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
