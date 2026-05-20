#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["fastembed>=0.3", "sqlite-vec>=0.1.6", "numpy"]
# ///
"""
Engineering OS — semantic memory INDEXER (Point A / Lever 3).

Builds a *derived, rebuildable* vector index over the git-committed memory in
`.engineering-os/` so agents can retrieve past decisions/journal entries by
MEANING instead of re-reading whole files. Git markdown/JSONL stays the source
of truth; this index is a cache (gitignored, rebuildable from git at any time).

Sources indexed (the durable moat):
  - .engineering-os/decision-log/**/*.jsonl   (one line = one chunk)
  - .engineering-os/memory/agents/*.journal.md  (split on '## ' headings)
  - .engineering-os/memory/features/*.md        (split on '## ' headings)
run/ artifacts are intentionally excluded to keep the index lean.

Incremental: each chunk is content-hashed; unchanged chunks are skipped, changed
chunks re-embedded, deleted chunks pruned. Re-running is cheap.

Embedding backend (env EOS_EMBED_BACKEND):
  - "fastembed" (default) — BAAI/bge-small-en-v1.5, 384-dim, local ONNX, free.
  - "hash"               — deterministic hashing, NO semantics. Self-test only.

Usage:
  uv run tools/memory_index.py            # incremental reindex
  uv run tools/memory_index.py --rebuild  # drop + full rebuild
  EOS_EMBED_BACKEND=hash uv run tools/memory_index.py   # plumbing self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

DIM = 384  # bge-small-en-v1.5 and the hash backend both produce 384-d vectors.


def eos_root() -> Path:
    """Locate the .engineering-os directory."""
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    candidates = []
    if base:
        candidates.append(Path(base))
    # git toplevel
    try:
        import subprocess

        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if top:
            candidates.append(Path(top))
    except Exception:
        pass
    candidates.append(Path.cwd())
    for c in candidates:
        if (c / ".engineering-os").is_dir():
            return c / ".engineering-os"
    # default to cwd even if missing (caller handles)
    return Path.cwd() / ".engineering-os"


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
def _norm_text(s: str, limit: int = 4000) -> str:
    s = s.strip()
    return s[:limit]


def iter_chunks(eos: Path):
    """Yield dicts: {id, source, req_id, ts, heading, text}."""
    # 1) decision log JSONL — one event per line
    dl = eos / "decision-log"
    if dl.is_dir():
        for f in sorted(dl.rglob("*.jsonl")):
            rel = f.relative_to(eos).as_posix()
            for i, line in enumerate(f.read_text(errors="replace").splitlines()):
                line = line.strip()
                if not line:
                    continue
                req_id = ts = heading = ""
                try:
                    obj = json.loads(line)
                    req_id = str(obj.get("req_id", "") or "")
                    ts = str(obj.get("ts", "") or "")
                    heading = str(obj.get("type", "") or "")
                except Exception:
                    pass
                yield {
                    "id": f"{rel}:{i}",
                    "source": rel,
                    "req_id": req_id,
                    "ts": ts,
                    "heading": heading,
                    "text": _norm_text(line),
                }

    # 2) markdown journals + feature journals — split on '## ' sections
    for sub in ("memory/agents", "memory/features"):
        d = eos / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            rel = f.relative_to(eos).as_posix()
            raw = f.read_text(errors="replace")
            sections = _split_sections(raw)
            for idx, (heading, body) in enumerate(sections):
                text = _norm_text((heading + "\n" + body).strip())
                if not text:
                    continue
                yield {
                    "id": f"{rel}#{idx}",
                    "source": rel,
                    "req_id": _guess_req_id(heading + " " + body),
                    "ts": _guess_ts(heading),
                    "heading": heading.lstrip("# ").strip()[:200],
                    "text": text,
                }


def _split_sections(raw: str):
    """Split markdown into (heading_line, body) on '## ' boundaries."""
    lines = raw.splitlines()
    sections = []
    cur_head = ""
    cur_body: list[str] = []
    have = False
    for ln in lines:
        if ln.startswith("## "):
            if have:
                sections.append((cur_head, "\n".join(cur_body)))
            cur_head, cur_body, have = ln, [], True
        else:
            cur_body.append(ln)
    if have:
        sections.append((cur_head, "\n".join(cur_body)))
    if not sections:  # no headings — index whole file as one chunk
        sections = [("", raw)]
    return sections


import re

_REQ_RE = re.compile(r"\b((?:feat|fix|chore|spike|exp)-[a-z0-9-]+)\b")
_TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2}(?:T[\d:Z\-]+)?)")


def _guess_req_id(s: str) -> str:
    m = _REQ_RE.search(s)
    return m.group(1) if m else ""


def _guess_ts(s: str) -> str:
    m = _TS_RE.search(s)
    return m.group(1) if m else ""


def chunk_hash(c: dict) -> str:
    return hashlib.sha256(c["text"].encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #
def hash_embed(texts):
    """Deterministic, semantics-free embedding for plumbing self-tests."""
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


def get_embedder(backend: str):
    if backend == "hash":
        return hash_embed
    from fastembed import TextEmbedding  # lazy: only when actually used

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    def embed(texts):
        return [list(map(float, v)) for v in model.embed(list(texts))]

    return embed


# --------------------------------------------------------------------------- #
# DB
# --------------------------------------------------------------------------- #
def open_db(eos: Path):
    import sqlite3
    import sqlite_vec

    (eos / "index").mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(eos / "index" / "memory.db")
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute(
        "CREATE TABLE IF NOT EXISTS chunks("
        "id TEXT PRIMARY KEY, source TEXT, req_id TEXT, ts TEXT, "
        "heading TEXT, hash TEXT, text TEXT)"
    )
    db.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks "
        f"USING vec0(embedding float[{DIM}] distance_metric=cosine)"
    )
    db.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    return db, sqlite_vec


def main() -> int:
    ap = argparse.ArgumentParser(description="Engineering OS semantic memory indexer")
    ap.add_argument("--rebuild", action="store_true", help="drop and fully rebuild")
    args = ap.parse_args()

    eos = eos_root()
    if not eos.is_dir():
        print(f"[reindex] No .engineering-os/ found near {eos.parent}. Nothing to index.")
        return 0

    backend = os.environ.get("EOS_EMBED_BACKEND", "fastembed")
    db, sqlite_vec = open_db(eos)

    if args.rebuild:
        db.execute("DELETE FROM chunks")
        db.execute("DELETE FROM vec_chunks")

    # backend consistency: if the index was built with a different backend, force rebuild
    prev = db.execute("SELECT v FROM meta WHERE k='backend'").fetchone()
    if prev and prev[0] != backend:
        print(f"[reindex] backend changed ({prev[0]} -> {backend}); rebuilding.")
        db.execute("DELETE FROM chunks")
        db.execute("DELETE FROM vec_chunks")
    db.execute(
        "INSERT INTO meta(k,v) VALUES('backend',?) "
        "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
        (backend,),
    )

    existing = {
        row[0]: (row[1], row[2])  # id -> (rowid, hash)
        for row in db.execute("SELECT id, rowid, hash FROM chunks")
    }
    seen: set[str] = set()
    to_embed: list[tuple[int, str]] = []  # (rowid, text)
    added = updated = unchanged = 0

    for c in iter_chunks(eos):
        cid = c["id"]
        seen.add(cid)
        h = chunk_hash(c)
        if cid not in existing:
            cur = db.execute(
                "INSERT INTO chunks(id,source,req_id,ts,heading,hash,text) "
                "VALUES(?,?,?,?,?,?,?)",
                (cid, c["source"], c["req_id"], c["ts"], c["heading"], h, c["text"]),
            )
            to_embed.append((cur.lastrowid, c["text"]))
            added += 1
        elif existing[cid][1] != h:
            rowid = existing[cid][0]
            db.execute(
                "UPDATE chunks SET source=?,req_id=?,ts=?,heading=?,hash=?,text=? WHERE id=?",
                (c["source"], c["req_id"], c["ts"], c["heading"], h, c["text"], cid),
            )
            db.execute("DELETE FROM vec_chunks WHERE rowid=?", (rowid,))
            to_embed.append((rowid, c["text"]))
            updated += 1
        else:
            unchanged += 1

    # prune deleted
    removed = 0
    for cid, (rowid, _h) in existing.items():
        if cid not in seen:
            db.execute("DELETE FROM chunks WHERE id=?", (cid,))
            db.execute("DELETE FROM vec_chunks WHERE rowid=?", (rowid,))
            removed += 1

    # embed in one batch, insert vec rows
    if to_embed:
        embed = get_embedder(backend)
        vectors = embed([t for _r, t in to_embed])
        for (rowid, _t), vec in zip(to_embed, vectors):
            db.execute(
                "INSERT INTO vec_chunks(rowid, embedding) VALUES(?, ?)",
                (rowid, sqlite_vec.serialize_float32(vec)),
            )

    db.commit()
    total = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(
        f"[reindex] backend={backend} total={total} "
        f"added={added} updated={updated} unchanged={unchanged} removed={removed}"
    )
    print(f"[reindex] index at {eos / 'index' / 'memory.db'} (gitignored, rebuildable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
