#!/usr/bin/env bash
# Engineering OS — post-tool-use hook
# Best-effort journal-append. Reads the tool input from stdin (JSON) and, if
# the call looks "meaningful" (Edit / Write / Bash with side effect on Brain
# files), appends a one-liner to the appropriate agent journal.
#
# This is a safety net for forgetful agents. Agents are still expected to
# author rich, structured journal entries themselves.

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
EOS_DIR="$ROOT/.engineering-os"
[ -d "$EOS_DIR" ] || exit 0

# Read stdin (Claude Code passes hook context as JSON on stdin)
PAYLOAD="$(cat 2>/dev/null || true)"
[ -n "$PAYLOAD" ] || exit 0

# Pull tool name and a short summary; if jq missing, skip silently
command -v jq >/dev/null 2>&1 || exit 0
TOOL=$(echo "$PAYLOAD" | jq -r '.tool_name // .toolName // empty' 2>/dev/null || true)
[ -n "$TOOL" ] || exit 0

# Only care about side-effect tools
case "$TOOL" in
  Edit|Write|Bash) ;;
  *) exit 0 ;;
esac

# Redact known secret patterns from the payload before journaling
SAFE=$(echo "$PAYLOAD" | sed -E \
  -e 's/sk-[A-Za-z0-9_-]{20,}/[REDACTED-anthropic-key]/g' \
  -e 's/sk_(test|live)_[A-Za-z0-9]{20,}/[REDACTED-stripe-key]/g' \
  -e 's/xoxb-[A-Za-z0-9-]{20,}/[REDACTED-slack-bot]/g' \
  -e 's/AKIA[0-9A-Z]{16}/[REDACTED-aws-access-key]/g' \
  -e 's/ghp_[A-Za-z0-9]{36}/[REDACTED-github-token]/g')

# Surmise the active agent from env (if Claude Code sets it) — else "unknown"
AGENT="${CLAUDE_AGENT_NAME:-unknown}"
JOURNAL_FILE="$EOS_DIR/memory/agents/${AGENT}.journal.md"
[ -d "$EOS_DIR/memory/agents" ] || mkdir -p "$EOS_DIR/memory/agents"

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# One-line auto-entry; agents author richer entries themselves
SUMMARY=$(echo "$SAFE" | jq -r --arg tool "$TOOL" '
  if .tool_input.file_path then "\($tool) on \(.tool_input.file_path)"
  elif .tool_input.command then "\($tool): \(.tool_input.command | .[0:120])"
  else "\($tool)"
  end' 2>/dev/null || echo "$TOOL")

echo "" >> "$JOURNAL_FILE"
echo "## $TS — auto — $AGENT" >> "$JOURNAL_FILE"
echo "**Auto-entry from post-tool-use hook.** $SUMMARY" >> "$JOURNAL_FILE"

exit 0
