#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["fastembed>=0.3", "sqlite-vec>=0.1.6", "numpy"]
# ///
"""
Engineering OS — semantic memory SEARCH (Point A / Lever 3).

Embeds a query and returns the top-k most semantically similar entries.

SELF-REFRESHING: before searching, it incrementally re-indexes if any source
file is newer than the index (or the index is missing). This is what makes
recall feel "always fresh" with zero manual /reindex — the refresh runs inline,
as part of the command you invoked, so it always completes (no fragile
background job). Cost is near-zero when nothing changed; the embedding model is
only loaded when there are genuinely new entries. Use --no-refresh to skip.

Used by:
  - the /recall-similar command-skill (human, markdown output)
  - agents during their loop (--json), e.g. the Engineering Advisor at Stage 1 /
    the Architect at Stage 2.

Usage:
  uv run tools/memory_search.py "rate limiting on the public API"
  uv run tools/memory_search.py -k 5 --json "idempotent webhook handler"
  uv run tools/memory_search.py --no-refresh "fast read, skip the freshness check"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse the indexer's helpers (eos_root, get_embedder, build_index, staleness).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_index  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS semantic memory search")
    ap.add_argument("query", nargs="+", help="natural-language query")
    ap.add_argument("-k", "--limit", type=int, default=8, help="results to return")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--no-refresh", action="store_true", help="skip the inline freshness check")
    args = ap.parse_args()
    query = " ".join(args.query)

    eos = memory_index.eos_root()

    # --- Self-refresh (lazy, inline, always completes) ---
    if not args.no_refresh:
        try:
            if memory_index.index_is_stale(eos):
                s = memory_index.build_index()
                if s.get("ok") and (s["added"] or s["updated"] or s["removed"] or s.get("rebuilt_for_backend")):
                    # note to STDERR so --json stdout stays clean
                    print(
                        f"[recall] auto-refreshed index "
                        f"(added={s['added']} updated={s['updated']} removed={s['removed']})",
                        file=sys.stderr,
                    )
        except Exception as e:  # never let a refresh failure block a search
            print(f"[recall] auto-refresh skipped ({e})", file=sys.stderr)

    db_path = eos / "index" / "memory.db"
    if not db_path.exists():
        msg = "index not found and could not be built — run /reindex (or check uv/.engineering-os)."
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

    qvec = memory_index.get_embedder(backend)([query])[0]
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
