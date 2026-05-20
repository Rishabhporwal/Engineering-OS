---
name: reindex
description: Rebuild/refresh the semantic memory index over .engineering-os/ (decision log + journals). Incremental and cheap. Run after a feature ships or whenever /recall-similar feels stale.
disable-model-invocation: true
---

Refresh the Engineering OS semantic memory index (Point A / Lever 3).

The index is a **derived, rebuildable cache** over the git-committed memory. Git markdown/JSONL stays the source of truth; this just makes it searchable by meaning.

## Run

Execute (the env var + managed python are required so SQLite can load the `sqlite-vec` extension — the macOS python.org build cannot):

```sh
UV_PYTHON_PREFERENCE=only-managed uv run --python 3.12 "${CLAUDE_PLUGIN_ROOT}/tools/memory_index.py" $ARGUMENTS
```

- Pass `--rebuild` to drop and fully rebuild (otherwise it is incremental — unchanged chunks are skipped).
- First run on a machine downloads a managed CPython (~16 MB) + the `BAAI/bge-small-en-v1.5` embedding model (~50 MB), once. Subsequent runs are fast.
- To verify plumbing without the model download, prefix `EOS_EMBED_BACKEND=hash` (semantics-free; self-test only — re-run without it for real search).

## After running

Report the printed summary line: `total / added / updated / unchanged / removed`, and the index path. If `.engineering-os/` is missing, tell the operator to run `/eos-init` first.

## Notes

- The index lives at `.engineering-os/index/memory.db` — gitignored, never committed.
- If `/recall-similar` ever returns "index not found", run this command.
