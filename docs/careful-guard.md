# The `/careful` Guard (gstack-inspired)

> An always-on PreToolUse hook ([hooks/on-careful.sh](../hooks/on-careful.sh)) that **blocks a tight, high-signal set of catastrophic Bash commands** before they run — so neither an agent nor a human can fat-finger an irreversible action. It mechanically enforces rules the OS already holds as convention (no force-push, narrow `git add`, append-only memory).

Design principle: **high signal, low friction.** It blocks only things that are essentially *never* intended in this pipeline. Normal destructive-but-routine ops pass untouched, so the guard never cries wolf (a guard that nags gets disabled).

## What it blocks

| Pattern | Example |
|---|---|
| `rm -rf` of `/`, `~`, `$HOME`, or a bare wildcard / `--no-preserve-root` | `rm -rf ~/Desktop`, `rm -rf /`, `rm -rf *` |
| `git push --force` / `-f` (force-with-lease is allowed) | `git push --force origin main` |
| Destructive SQL | `DROP TABLE`, `DROP DATABASE`, `TRUNCATE` |
| Raw disk writes | `mkfs`, `dd … of=/dev/…`, `> /dev/sd…` |
| Recursive `chmod 777` | `chmod -R 777 .` |

## What it allows (no false positives)

`rm -rf ./build`, `rm -rf node_modules`, `git push` to a feature branch, `--force-with-lease`, `git reset --hard`, ordinary SQL `SELECT`, every `uv run …` tool — all pass. (Verified with a 20-case matrix: 10 block, 8 allow, 2 override.)

## Override (deliberate destructive ops)

When you genuinely mean it, opt out per-command:

```sh
EOS_ALLOW_DESTRUCTIVE=1 rm -rf ~/scratch        # prefix
git push --force origin throwaway   #careful-ok   # or trailing marker
```

A blocked command returns the reason to the agent, which then either narrows the command or adds the override.

## Notes
- Fires on `Bash` only; fails open (allows) if `jq` is unavailable, so it can never wedge the pipeline.
- This is the safety half of gstack's `/careful` + `/freeze`. `/freeze` (edit-locking to one dir) was intentionally **not** ported — the lane system + Aryan's track-tagging already scope work.
