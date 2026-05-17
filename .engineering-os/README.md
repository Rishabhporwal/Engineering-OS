# `.engineering-os/` — Shared Memory

> **DO NOT** add this directory to `.gitignore`. It is intentionally committed.

This directory is the shared, git-synced memory of the Brain Engineering OS. Every teammate who clones the repo and runs `git pull` receives the full state of every prior run, every decision, and every per-agent journal.

See [`docs/memory-and-git-sync.md`](../docs/memory-and-git-sync.md) for the full model.

## Layout

```
.engineering-os/
├── memory/
│   ├── agents/          per-agent append-only journals
│   └── features/        per-feature append-only journals
├── state/
│   ├── active.json      in-flight requirements (last-write-wins; auto-backed-up)
│   └── registry.json    canonical list of every req_id ever seen (append-only)
├── decision-log/        YYYY/MM/YYYY-MM-DD.jsonl — immutable line-per-event stream
├── artifacts/           optional per-req cross-links / large artifacts
└── runs/                per-run timestamped folders — no collisions possible
```

## Conventions

- **Append-only:** `memory/*.md`, `decision-log/*.jsonl`, `state/registry.json`. Merged with `merge=union` (see `.gitattributes`).
- **Last-write-wins:** `state/active.json` only. Backed up to `.bak.<ts>` on every write.
- **Per-run isolation:** every run is its own folder under `runs/<ts>__<req-id>__<operator>/`. Two operators never collide.

## Touch policy

- Agents append to journals via Write tool.
- Decision log appended by agents OR by hook on every meaningful action.
- State updated only by agents (`/requirement`, `/approve`, etc.) — never by hand.
- Runs are append-only artifact bundles per requirement-run.
