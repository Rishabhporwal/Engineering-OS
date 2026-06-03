# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""cache_lint — protect the prompt-caching stable prefix (the #1 LLM cost lever).

Caching cuts 70-90% on repeated calls that SHARE a byte-stable prefix. In this plugin
the prefix is naturally stable (the system-prompt + agent files + canon are static
files the harness caches automatically). The way you LOSE that win is by letting
per-run/volatile content leak into the cached region — a shell-interpolated timestamp,
a random hex, a req-specific value baked into a file every spawn re-reads. Any of those
changes the prefix bytes → cache miss → the calls become expensive WRITES.

This lints the files that form the cached prefix for high-confidence cache-busters.
The real ordering lever (stable-prefix-then-variable per spawn) lives in
pipeline/orchestrator.md; this catches the static-file regressions.

Usage:  uv run cache_lint.py        (from the plugin root)
Exit 0 = clean. Exit 1 = a cache-buster in the stable prefix.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that form the cache-stable prefix loaded on (nearly) every agent spawn.
PREFIX_GLOBS = ["prompts/*.md", "agents/*.md"]

# Static .md files are byte-stable by nature, so they can only bust the cache if a
# tool TEMPLATES them per run (string-substituting a live value into a file the prefix
# re-reads). The honest, narrow check: a literal `${...}`-style template placeholder for
# a per-run value sitting in PROSE (outside code fences AND inline code, where such tokens
# are just documentation). An instruction *to run* `date -u` is stable text — not flagged.
BUSTERS = [
    (r"\$\{\{?\s*(NOW|TODAY|TIMESTAMP|RANDOM|UUID|RUN_ID)\b", "per-run template placeholder in the cached prefix"),
    (r"<<\s*INJECT", "explicit per-run injection marker in the cached prefix"),
]
FENCE = re.compile(r"```.*?```", re.S)        # fenced code = stable examples/instructions
INLINE = re.compile(r"`[^`\n]*`")             # inline code = stable instruction text


def main() -> int:
    problems = []
    for g in PREFIX_GLOBS:
        for f in sorted(ROOT.glob(g)):
            text = f.read_text(errors="ignore")
            stripped = INLINE.sub("", FENCE.sub("", text))  # only PROSE remains
            for pat, why in BUSTERS:
                for m in re.finditer(pat, stripped):
                    line = stripped[:m.start()].count("\n") + 1
                    problems.append(f"  CACHE-BUSTER  {f.relative_to(ROOT)}:{line}  {why}")

    if problems:
        print("PROMPT-CACHE prefix has per-run interpolation (busts the cache for every agent):",
              file=sys.stderr)
        for p in problems:
            print(p, file=sys.stderr)
        print("\nKeep per-run values (req_id, timestamps, diff) OUT of the cached prefix — the "
              "orchestrator injects them in the VARIABLE suffix of the spawn prompt, not the static files.",
              file=sys.stderr)
        return 1
    print(f"cache_lint: clean — the stable prefix ({', '.join(PREFIX_GLOBS)}) has no per-run cache-busters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
