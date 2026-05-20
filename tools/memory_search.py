#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["fastembed>=0.3", "sqlite-vec>=0.1.6", "numpy"]
# ///
"""
Engineering OS — semantic memory SEARCH (Point A / Lever 3).

Embeds a query and returns the top-k most semantically similar entries from the
index built by memory_index.py. Used by:
  - the /recall-similar command-skill (human, markdown output)
  - agents during their loop (--json), e.g. Rohan at Stage 1 / Aryan at Stage 2,
    so they retrieve the relevant slices instead of re-reading whole journals.

Usage:
  uv run tools/memory_search.py "abandoned cart recovery for COD"
  uv run tools/memory_search.py -k 5 --json "RFM segment reuse"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DIM = 384


def eos_root() -> Path:
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    cands = []
    if base:
        cands.append(Path(base))
    try:
        import subprocess

        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if top:
            cands.append(Path(top))
    except Exception:
        pass
    cands.append(Path.cwd())
    for c in cands:
        if (c / ".engineering-os").is_dir():
            return c / ".engineering-os"
    return Path.cwd() / ".engineering-os"


def hash_embed(texts):
    import hashlib

    import numpy as np

    out = []
    for t in texts:
        v = np.zeros(DIM, dtype="float32")
        for tok in t.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % DIM] += 1.0
        n = float(np.linalg.norm(v))
        out.append((v / n if n else v).tolist())
    return out


def embed_query(text: str, backend: str):
    if backend == "hash":
        return hash_embed([text])[0]
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return list(map(float, next(iter(model.embed([text])))))


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS semantic memory search")
    ap.add_argument("query", nargs="+", help="natural-language query")
    ap.add_argument("-k", "--limit", type=int, default=8, help="results to return")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    query = " ".join(args.query)

    eos = eos_root()
    db_path = eos / "index" / "memory.db"
    if not db_path.exists():
        msg = "index not found — run /reindex (or: uv run tools/memory_index.py) first."
        print(json.dumps({"error": msg}) if args.json else f"[recall] {msg}")
        return 1

    import sqlite3

    import sqlite_vec

    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    row = db.execute("SELECT v FROM meta WHERE k='backend'").fetchone()
    backend = row[0] if row else "fastembed"

    qvec = embed_query(query, backend)
    rows = db.execute(
        "SELECT c.id, c.source, c.req_id, c.ts, c.heading, c.text, m.distance "
        "FROM (SELECT rowid, distance FROM vec_chunks "
        "      WHERE embedding MATCH ? ORDER BY distance LIMIT ?) m "
        "JOIN chunks c ON c.rowid = m.rowid ORDER BY m.distance",
        (sqlite_vec.serialize_float32(qvec), args.limit),
    ).fetchall()

    results = []
    for cid, source, req_id, ts, heading, text, dist in rows:
        sim = max(0.0, 1.0 - float(dist))  # cosine distance -> similarity
        results.append(
            {
                "similarity": round(sim, 3),
                "req_id": req_id,
                "ts": ts,
                "source": source,
                "heading": heading,
                "snippet": (text[:280] + ("…" if len(text) > 280 else "")),
                "id": cid,
            }
        )

    if args.json:
        print(json.dumps({"query": query, "backend": backend, "results": results}, ensure_ascii=False))
        return 0

    if not results:
        print(f'[recall] No matches for "{query}". Index may be empty — run /reindex.')
        return 0
    print(f'### Semantic recall: "{query}"  ·  backend={backend}  ·  {len(results)} hits\n')
    for i, r in enumerate(results, 1):
        tag = f"{int(r['similarity'] * 100)}%"
        meta = " · ".join(x for x in [r["req_id"], r["ts"]] if x)
        print(f"{i}. **[{tag}]** {meta}  —  `{r['source']}`")
        if r["heading"]:
            print(f"   _{r['heading']}_")
        print(f"   > {r['snippet']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
