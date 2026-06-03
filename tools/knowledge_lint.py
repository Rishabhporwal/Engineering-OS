# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""knowledge_lint — make the single-source / no-drift claim self-enforcing (Knowledge-F4).

v2 claims "each fact has one owner; primers + skills cite, don't restate" and "every
referenced file exists" — but nothing checked it, so cites silently became copies and
pointers silently went dead (the deleted BLUEPRINT was still referenced by both primers).
This linter is the gate.

Checks:
  1. DEAD POINTERS: every `canon/...`, `docs/...`, `skills/<x>/`, `prompts/...` path referenced
     from the primers + canon/INDEX.md + the skill-mapping-matrix actually exists on disk.
  2. MATRIX COUNT: the skill-mapping-matrix's stated skill count equals `ls skills/`.
  3. NO DELETED-BLUEPRINT references anywhere.

Usage:  uv run knowledge_lint.py        (run from the plugin root)
Exit 0 = clean. Exit 1 = drift (CI fails the merge).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH_RE = re.compile(r'`((?:canon|docs|skills|prompts|pipeline|schemas|templates|tools|workflows)/[A-Za-z0-9_./-]+?)`')


def check_dead_pointers() -> list[str]:
    problems = []
    sources = [ROOT / "docs/business-context.md", ROOT / "docs/technical-context.md",
               ROOT / "canon/INDEX.md", ROOT / "docs/skill-mapping-matrix.md"]
    for src in sources:
        if not src.exists():
            continue
        for m in PATH_RE.finditer(src.read_text()):
            ref = m.group(1).rstrip("/")
            # tolerate a trailing "§…" or glob and section anchors
            ref = re.sub(r'\s*§.*$', '', ref).split("#")[0].strip()
            # skip template placeholders (TECH/NN, <slug>, *.md globs, {{X}})
            if re.search(r'NN|<|>|\*|\{\{|\bN\b', ref):
                continue
            p = ROOT / ref
            # a skills/<x> ref resolves to the dir; a file ref to the file
            if not p.exists() and not (ROOT / ref).with_suffix(".md").exists():
                problems.append(f"  DEAD POINTER  {src.name} → `{ref}` does not exist")
    return problems


def check_matrix_count() -> list[str]:
    matrix = ROOT / "docs/skill-mapping-matrix.md"
    if not matrix.exists():
        return []
    actual = len([d for d in (ROOT / "skills").iterdir() if d.is_dir()])
    text = matrix.read_text()
    m = re.search(r'=\s*(\d+)\s+skill folders', text)
    if m and int(m.group(1)) != actual:
        return [f"  MATRIX COUNT  matrix says {m.group(1)} skill folders; disk has {actual}"]
    return []


def check_no_blueprint() -> list[str]:
    problems = []
    if (ROOT / "canon/IMPLEMENTATION-BLUEPRINT.md").exists():
        return []  # if it exists, refs are fine
    for f in ROOT.rglob("*.md"):
        if ".git/" in str(f):
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            # a live "use the BLUEPRINT" pointer (not a historical "replaced the BLUEPRINT" note)
            if "IMPLEMENTATION-BLUEPRINT" in line and not re.search(r"replac|delet|former|was |old |removed", line, re.I):
                problems.append(f"  DEAD BLUEPRINT REF  {f.relative_to(ROOT)}:{i}")
    return problems


def main() -> int:
    problems = check_dead_pointers() + check_matrix_count() + check_no_blueprint()
    if problems:
        print("KNOWLEDGE DRIFT (the single-source / no-dead-pointer claim is violated):", file=sys.stderr)
        for p in problems:
            print(p, file=sys.stderr)
        print(f"\n{len(problems)} issue(s). Fix the pointer/count, or update the owner.", file=sys.stderr)
        return 1
    print("knowledge_lint: clean (pointers resolve, matrix count matches, no dead BLUEPRINT refs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
