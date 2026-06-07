# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""secret_scan — the commit-gate half of the O1 fix (the hook is the write-gate half).

Scans files for secret VALUES using the SAME pattern file as the PreToolUse hook
(hooks/secret-patterns.txt), so the two never drift. Run it before the
`.engineering-os/` auto-commit (skills/finishing-a-development-branch) so a secret
can never reach a committed file even if the live-write hook was bypassed.

Usage:
  uv run secret_scan.py --staged                 # scan files git has staged (the commit gate)
  uv run secret_scan.py path/ [path2 ...]        # scan explicit paths
  uv run secret_scan.py --patterns FILE ...      # override the pattern file

Exit 0 = clean. Exit 1 = secret found (prints file:line with the value redacted).
No deps; works with or without gitleaks installed (gitleaks config is shipped
separately for teams that have it).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PATTERNS = _PLUGIN_ROOT / "hooks" / "secret-patterns.txt"
_REDACT = re.compile(r"(GOCSPX-|shp[a-z]+_|EAA|sk-|AKIA|ASIA|AIza|ya29\.|gh[pousr]_|"
                     r"glpat-|xox[baprs]-|sk_live_|rk_live_|rzp_live_|eyJ)[A-Za-z0-9_./+-]+")
# redact the password in a credentialed URL (scheme://user:pw@host) — keep scheme/user/@,
# hide the secret. Without this, a DSN hit would print the password in cleartext.
_REDACT_URLPW = re.compile(r"(://[^:@/ ]+:)[^@/ ]{3,}(@)")


def load_patterns(path: Path) -> list[re.Pattern]:
    pats = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            pats.append(re.compile(line))
        except re.error:
            pass
    return pats


def staged_files() -> list[Path]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True)
    return [Path(p) for p in out.stdout.splitlines() if p.strip()]


def iter_files(paths: list[Path]):
    for p in paths:
        if p.is_dir():
            yield from (f for f in p.rglob("*") if f.is_file() and ".git/" not in str(f)
                        and "__pycache__" not in str(f) and f.suffix != ".pyc")
        elif p.is_file():
            yield p


def scan(files, pats: list[re.Pattern]) -> int:
    hits = 0
    for f in files:
        try:
            text = f.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat in pats:
                if pat.search(line):
                    red = _REDACT.sub(lambda m: m.group(1) + "***REDACTED***", line)
                    red = _REDACT_URLPW.sub(r"\1***REDACTED***\2", red).strip()[:160]
                    print(f"  SECRET  {f}:{i}  {red}", file=sys.stderr)
                    hits += 1
                    break
    return hits


def selftest(patterns_path: Path) -> int:
    """Guard the patterns against silent regressions (e.g. the POSIX-class bug that made the
    connection-string pattern match NOTHING). Secret-shaped strings are BUILT AT RUNTIME so no
    literal secret value is committed in this file. Exit 0 = all patterns behave; 1 = a gap."""
    pats = load_patterns(patterns_path)
    def hit(s: str) -> bool:
        return any(p.search(s) for p in pats)
    A16, H40, Z32 = "A" * 16, "b" * 40, "c" * 32
    must_match = {
        "dsn-password":      "postgres://u:" + ("x" * 10) + "@h:5432/d",   # the regression this guards
        "credentialed-url":  "https://user:" + ("y" * 12) + "@example.com",
        "aws-akia":          "AKIA" + A16,
        "anthropic":         "sk-ant-" + ("z" * 28),
        "gh-pat":            "ghp_" + ("d" * 36),
        "jwt":               "eyJ" + ("e" * 12) + ".eyJ" + ("f" * 12) + "." + ("g" * 12),
        "private-key":       "-----BEGIN " + "RSA PRIVATE KEY-----",   # split so this file is self-clean
    }
    must_not_match = {
        "no-cred-url":       "https://example.com/path",
        "dsn-no-cred":       "postgres://localhost:5432/store",
        "ssh-remote":        "git@github.com:org/repo.git",
        "placeholder":       "DATABASE_URL=<your-connection-string>",
        "prose":             "set the api key via the secrets manager at deploy time",
    }
    fails = []
    for name, s in must_match.items():
        if not hit(s):
            fails.append(f"  ✗ FALSE-NEGATIVE [{name}] — a secret-shaped value is NOT caught")
    for name, s in must_not_match.items():
        if hit(s):
            fails.append(f"  ✗ FALSE-POSITIVE [{name}] — a non-secret IS flagged")
    if fails:
        print("secret_scan --selftest FAILED (the pattern file regressed):", file=sys.stderr)
        for f in fails:
            print(f, file=sys.stderr)
        return 1
    print(f"secret_scan --selftest: OK ({len(must_match)} caught, {len(must_not_match)} correctly ignored)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="secret_scan")
    ap.add_argument("paths", nargs="*", help="files/dirs to scan")
    ap.add_argument("--staged", action="store_true", help="scan git-staged files (the commit gate)")
    ap.add_argument("--selftest", action="store_true", help="verify the patterns catch/ignore the right shapes (CI regression guard)")
    ap.add_argument("--patterns", default=str(_DEFAULT_PATTERNS))
    args = ap.parse_args()

    if args.selftest:
        return selftest(Path(args.patterns))

    pats = load_patterns(Path(args.patterns))
    if not pats:
        print("secret_scan: no patterns loaded", file=sys.stderr)
        return 0  # fail-open on config error, like the hook
    files = staged_files() if args.staged else list(iter_files([Path(p) for p in args.paths]))
    if not files:
        print("secret_scan: nothing to scan")
        return 0
    hits = scan(files, pats)
    if hits:
        print(f"\nDEFECT: {hits} secret value(s) found — do NOT commit. Replace with ***REDACTED*** "
              f"or a Secrets-Manager ARN. (O1 prevention; patterns: {args.patterns})", file=sys.stderr)
        return 1
    print(f"secret_scan: clean ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
