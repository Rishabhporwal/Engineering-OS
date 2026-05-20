#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Engineering OS — paradigm-drift gate (Point D).

Promotes the @paradigm convention (cost-routing-paradigms: SQL > ML > Haiku >
Sonnet) from "audited by Rohan" to "enforced in CI". HEURISTIC, line-based —
a fast signal, not a proof. It flags three drift classes:

  1. MISSING   — an LLM call (Anthropic SDK / claude-* model) with no @paradigm
                 marker within the window above it.
  2. NON_LLM   — an LLM call inside a path declared `sql` or `ml` (those
                 paradigms must not call an LLM at all).
  3. ESCALATED — a sonnet/opus model used under a path declared `haiku`.

Markers recognised (Python decorator or TS/JS comment):
  @paradigm("sonnet")        @paradigm(Paradigm.HAIKU)
  // @paradigm: sql          # @paradigm sonnet

Usage:
  uv run tools/paradigm_check.py                 # scan whole repo
  uv run tools/paradigm_check.py --changed       # only files changed vs origin/HEAD
  uv run tools/paradigm_check.py path/to/dir ...  # explicit paths
Exit code 1 if any violation is found (wire into CI).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

WINDOW = 40  # lines: how far above an LLM call we look for a @paradigm marker
EXTS = {".py", ".ts", ".tsx", ".js", ".mjs"}

PARADIGM_RE = re.compile(r"@paradigm[\"'(:\s]*\s*(?:Paradigm\.)?[\"']?(sql|ml|haiku|sonnet)\b", re.I)
# An LLM call: an Anthropic SDK call OR an explicit claude-* / model=...Sonnet/Opus/Haiku
LLM_CALL_RE = re.compile(
    r"(messages\.create|client\.messages|anthropic\.|\.messages\.stream"
    r"|claude-(?:sonnet|opus|haiku)|model\s*[=:]\s*[\"'].*?(?:sonnet|opus|haiku))",
    re.I,
)
MODEL_TIER_RE = re.compile(r"(sonnet|opus|haiku)", re.I)


def changed_files() -> list[Path]:
    base = os.environ.get("PARADIGM_BASE_REF", "origin/HEAD")
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, check=False,
        ).stdout
        if not out.strip():
            out = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, check=False,
            ).stdout
        return [Path(p) for p in out.split() if Path(p).suffix in EXTS and Path(p).exists()]
    except Exception:
        return []


def iter_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            files += [f for f in pp.rglob("*") if f.suffix in EXTS]
        elif pp.suffix in EXTS and pp.exists():
            files.append(pp)
    # skip vendored / generated
    skip = ("node_modules", "/.git/", "/dist/", "/build/", "/__pycache__/", ".gen.", "/gen/")
    return [f for f in files if not any(s in str(f) for s in skip)]


def nearest_paradigm(lines: list[str], idx: int) -> str | None:
    for j in range(idx, max(-1, idx - WINDOW), -1):
        m = PARADIGM_RE.search(lines[j])
        if m:
            return m.group(1).lower()
    return None


def scan_file(f: Path) -> list[tuple[int, str, str]]:
    """Return list of (lineno, kind, detail) violations."""
    try:
        lines = f.read_text(errors="replace").splitlines()
    except Exception:
        return []
    violations = []
    for i, line in enumerate(lines):
        if not LLM_CALL_RE.search(line):
            continue
        declared = nearest_paradigm(lines, i)
        tier_m = MODEL_TIER_RE.search(line)
        tier = tier_m.group(1).lower() if tier_m else ""
        if declared is None:
            violations.append((i + 1, "MISSING", "LLM call with no @paradigm marker above it"))
        elif declared in ("sql", "ml"):
            violations.append((i + 1, "NON_LLM", f"LLM call inside a `{declared}` path (must not call an LLM)"))
        elif declared == "haiku" and tier in ("sonnet", "opus"):
            violations.append((i + 1, "ESCALATED", f"`{tier}` model used under a `haiku` path"))
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS paradigm-drift gate")
    ap.add_argument("paths", nargs="*", help="files/dirs (default: repo root)")
    ap.add_argument("--changed", action="store_true", help="only files changed vs base ref")
    args = ap.parse_args()

    if args.changed:
        files = changed_files()
    elif args.paths:
        files = iter_files(args.paths)
    else:
        files = iter_files(["."])

    total = 0
    for f in sorted(files):
        for lineno, kind, detail in scan_file(f):
            total += 1
            print(f"::paradigm-drift:: {kind}  {f}:{lineno}  — {detail}")

    if total:
        print(f"\n[paradigm-check] {total} violation(s) across {len(files)} file(s). FAIL.")
        return 1
    print(f"[paradigm-check] OK — no paradigm drift in {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
