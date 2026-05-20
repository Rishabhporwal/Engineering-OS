---
name: recall-similar
description: Semantic search over Engineering OS memory — find past decisions, journal entries, and features by MEANING, not keyword. Use before designing anything ("have we solved something like this before?"). Complements /recall (which fetches one feature's full history by exact slug).
disable-model-invocation: true
---

Find the most semantically similar entries in the Engineering OS memory (Point A / Lever 3).

> Self-refreshing: this incrementally re-indexes inline before searching, so results are always fresh after a `git pull` — no manual `/reindex` needed.

The Founder's query is:

> $ARGUMENTS

## Run

```sh
UV_PYTHON_PREFERENCE=only-managed uv run --python 3.12 "${CLAUDE_PLUGIN_ROOT}/tools/memory_search.py" -k 8 "$ARGUMENTS"
```

## Present the results

The script prints a ranked list (similarity %, req_id, timestamp, source path, snippet). Render each hit's `source` as a **clickable markdown link** into the git file so the operator can jump to the full entry. Lead with the single most relevant hit and a one-line "what this means for the current question".

## Fallbacks

- If output is `index not found` → tell the operator to run `/reindex` first, then retry.
- If results look weak/empty but you expect matches → the index may be stale; suggest `/reindex`.

## When to use which recall

- **`/recall-similar <description>`** (this) — semantic, fuzzy, cross-feature: "anything like X?"
- **`/recall <feat-slug>`** — exact, full chronological history of ONE known feature.
