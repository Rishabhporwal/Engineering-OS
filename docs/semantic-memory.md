# Semantic Memory (Point A / Lever 3)

> Retrieval by **meaning**, layered on top of the git-committed memory — so agents (and you) can ask *"have we solved something like this before?"* and get hits a keyword `grep` would miss. It is also the biggest **token-per-invocation** reducer: agents retrieve the relevant slices instead of re-reading whole journals.

---

## The principle: derived cache, never a source of truth

```
SOURCE OF TRUTH (committed to git, append-only, auditable)
  .engineering-os/decision-log/**/*.jsonl
  .engineering-os/memory/agents/*.journal.md
  .engineering-os/memory/features/*.md
        │
        │  /reindex  (tools/memory_index.py)
        ▼
DERIVED INDEX (gitignored, rebuildable, machine-local)
  .engineering-os/index/memory.db   ← sqlite-vec, 384-d embeddings
        │
        │  /recall-similar  (tools/memory_search.py)
        ▼
RANKED HITS → linked back to the git source files
```

The index adds **zero** new source of truth. Delete `memory.db` and `/reindex` rebuilds it from git. This is what keeps the audit moat intact while adding semantic recall.

---

## Why this stack

| Choice | Tool | Why |
|---|---|---|
| Vector store | **sqlite-vec** | Single file, zero external service, rebuildable — fits the "no database, no external service" principle. |
| Embeddings | **fastembed** (`BAAI/bge-small-en-v1.5`, 384-d) | Local ONNX, no torch, free, no API key. Consistent with the Python/uv stack. **Not** a hosted embeddings API. |
| Runtime | **`uv run` + PEP 723** | Inline deps auto-resolve into an ephemeral env — no global install, no `requirements.txt` to maintain. |

---

## Commands

| Command | Does |
|---|---|
| `/reindex` | Refresh the index (incremental; `--rebuild` for full). Run after a feature ships or when recall feels stale. |
| `/recall-similar <description>` | Semantic top-k over all memory. Returns ranked hits linked to source. |
| `/recall <feat-slug>` | (existing) Exact, full chronological history of ONE known feature. |

`/recall-similar` is fuzzy and cross-feature; `/recall` is exact and single-feature. Use recall-similar to *discover*, recall to *read the whole story*.

---

## Automatic freshness (no manual reindex)

`/recall-similar` (and every agent search) **self-refreshes inline**: before searching, it checks whether any source file is newer than the index and, if so, runs an incremental re-index *as part of the search command* — which always completes (no fragile background job to get killed).

Consequence for teams: after a teammate ships a feature and you `git pull`, your very next `/recall-similar` automatically sees their new decisions. You do **not** run `/reindex`. The cost is near-zero when nothing changed (the embedding model only loads when there are genuinely new entries to embed).

`/reindex` remains for two cases only: a forced full rebuild (`--rebuild`), or pre-warming the index so the first search after a big pull has no latency (optional; e.g. via a scheduled `/schedule` job).

> We deliberately do **not** reindex from the session-start hook: a background job spawned by a hook isn't guaranteed to survive after the hook returns (verified — it gets killed mid-build). Inline self-refresh is the robust mechanism.

---

## How agents use it (the token win)

Rohan (Stage 1) and Aryan (Stage 2) run `memory_search.py --json` early in their loop:

- **Rohan** — catches near-duplicate requirements, and a close match to a prior *shipped* pattern supports an `express` lane classification ("clear repeat of a registry pattern").
- **Aryan** — pulls the prior paradigm/primitive/schema decisions for similar features and **reuses** them instead of re-deriving, citing the matched `req_id`.

Both prefer these targeted hits over re-reading entire journals — which is where the per-invocation token reduction comes from. It compounds with the [feature-tiering](feature-tiering.md) savings.

---

## The macOS native-dep gotcha (important)

The python.org macOS build of CPython is compiled **without** loadable-SQLite-extension support, so `sqlite-vec` can't load under it. The fix is baked into every invocation:

```sh
UV_PYTHON_PREFERENCE=only-managed uv run --python 3.12 <script>
```

This forces uv to use its own managed CPython (python-build-standalone), which **does** enable extensions. First run downloads a managed Python (~16 MB) + the embedding model (~50 MB), once. Verified working on macOS (Darwin, Apple Silicon).

> Self-test without the model download: prefix `EOS_EMBED_BACKEND=hash` (deterministic, semantics-free — proves plumbing only; re-run without it for real search).

---

## Operational notes

- **Index location:** `.engineering-os/index/memory.db` — gitignored by `/eos-init`, never committed.
- **What's indexed:** decision log (one event per line) + agent/feature journals (split on `## ` sections). `runs/` artifacts are excluded to keep the index lean.
- **Incremental:** chunks are content-hashed; unchanged chunks are skipped, changed ones re-embedded, deleted ones pruned. Re-running is cheap.
- **Backend safety:** the index records its embedding backend; querying with a mismatched backend triggers an automatic rebuild (a `hash` index and a `fastembed` index are not comparable).
- **Staleness:** handled automatically — see "Automatic freshness" below. You almost never run `/reindex` by hand.

---

## What this is NOT

- Not a replacement for the git memory — it's a lens over it.
- Not committed — it's a local cache.
- Not a hosted vector DB — no service, no API key, no egress.
