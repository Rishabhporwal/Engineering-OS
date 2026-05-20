#!/usr/bin/env bash
# Engineering OS — /careful guard (gstack-inspired). PreToolUse hook on Bash.
# BLOCKS a tight, high-signal set of catastrophic / almost-never-intended
# commands so an agent (or human) can't fat-finger an irreversible action.
# Exit 2 = block + reason fed back to the model. Exit 0 = allow.
#
# Design: HIGH SIGNAL, LOW FRICTION. We block only things that are essentially
# never legitimate in this pipeline (rm -rf of / ~ $HOME or a bare wildcard;
# force-push; DROP/TRUNCATE; raw disk writes; recursive chmod 777). Ordinary
# destructive-but-normal ops (rm -rf ./build, git reset --hard) are ALLOWED so
# the guard never cries wolf. Override any block by adding `#careful-ok` to the
# command or prefixing `EOS_ALLOW_DESTRUCTIVE=1`.

set -euo pipefail

PAYLOAD="$(cat 2>/dev/null || true)"
[ -n "$PAYLOAD" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // .toolName // empty' 2>/dev/null || true)
[ "$TOOL" = "Bash" ] || exit 0
CMD=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
[ -n "$CMD" ] || exit 0

# Explicit override — deliberate destructive ops just opt out.
if printf '%s' "$CMD" | grep -qiE 'EOS_ALLOW_DESTRUCTIVE|#careful-ok'; then
  exit 0
fi

block=""

# 1) rm -rf targeting / ~ $HOME or a bare wildcard (NOT ordinary ./paths)
if printf '%s' "$CMD" | grep -qiE '\brm\b[^|;&]*-[a-z]*r' \
   && printf '%s' "$CMD" | grep -qiE '\brm\b[^|;&]*-[a-z]*f'; then
  if printf '%s' "$CMD" | grep -qiE 'rm[^|;&]*[[:space:]](/|~|\$HOME|/\*|\*)([[:space:]]|/|$)' \
     || printf '%s' "$CMD" | grep -qi 'no-preserve-root'; then
    block="recursive force-delete targeting / ~ \$HOME or a bare wildcard"
  fi
fi

# 2) git force-push (force-with-lease is allowed)
if [ -z "$block" ] && printf '%s' "$CMD" | grep -qiE 'git[[:space:]]+push'; then
  if printf '%s' "$CMD" | grep -qiE '(--force([^-]|$)|[[:space:]]-f([[:space:]]|$))' \
     && ! printf '%s' "$CMD" | grep -qi 'force-with-lease'; then
    block="git force-push (forbidden to shared branches; use --force-with-lease on a feature branch if you must)"
  fi
fi

# 3) destructive SQL
if [ -z "$block" ] && printf '%s' "$CMD" | grep -qiE '\b(DROP[[:space:]]+(TABLE|DATABASE|SCHEMA)|TRUNCATE([[:space:]]+TABLE)?)\b'; then
  block="destructive SQL (DROP/TRUNCATE)"
fi

# 4) raw disk writes
if [ -z "$block" ] && printf '%s' "$CMD" | grep -qiE '\bmkfs\b|\bdd[[:space:]][^|;&]*of=/dev/|>[[:space:]]*/dev/(sd|disk|nvme)'; then
  block="raw disk write (mkfs / dd to device / redirect to /dev)"
fi

# 5) recursive chmod 777
if [ -z "$block" ] && printf '%s' "$CMD" | grep -qiE '\bchmod\b' \
   && printf '%s' "$CMD" | grep -qiE '\-[a-z]*R' \
   && printf '%s' "$CMD" | grep -qE '0?777'; then
  block="recursive chmod 777 (over-permissive)"
fi

if [ -n "$block" ]; then
  cat >&2 <<EOF
[careful] BLOCKED — $block.
Command: $(printf '%s' "$CMD" | head -c 200)
This is almost never intended. If you genuinely mean it, re-run with an override:
  • prefix:  EOS_ALLOW_DESTRUCTIVE=1 <command>
  • or append a marker:  <command>  #careful-ok
Otherwise, choose a narrower, reversible command.
EOF
  exit 2
fi

exit 0
