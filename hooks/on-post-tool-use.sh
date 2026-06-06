#!/usr/bin/env bash
# Engineering OS — post-tool-use hook
# Best-effort journal-append. Reads the tool input from stdin (JSON) and, if
# the call looks "meaningful" (Edit / Write / Bash with side effect on product
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
  Edit|Write) ;;
  Bash)
    # Skip read-only Bash — journaling `ls`/`grep`/`date`/`git status` is pure noise
    # (the "80+ junk entries" problem). Only journal Bash that can mutate state.
    CMD=$(echo "$PAYLOAD" | jq -r '.tool_input.command // empty' 2>/dev/null | head -c 300)
    FIRST=$(printf '%s' "$CMD" | sed -E 's/^[[:space:]]*//' | awk '{print $1}')
    case "$FIRST" in
      ls|cat|grep|rg|find|head|tail|echo|pwd|which|date|wc|stat|tree|env|printenv|less|more|jq|sort|uniq|cut|diff|cd|export|true)
        exit 0 ;;
    esac
    # git read-only subcommands produce no state change worth journaling
    if printf '%s' "$CMD" | grep -qE '^[[:space:]]*git[[:space:]]+(status|diff|log|show|branch|remote|rev-parse|ls-files|ls-remote|config[[:space:]]+--get)'; then
      exit 0
    fi
    ;;
  *) exit 0 ;;
esac

# Redact known secret patterns from the payload before journaling
SAFE=$(echo "$PAYLOAD" | sed -E \
  -e 's/sk-[A-Za-z0-9_-]{20,}/[REDACTED-anthropic-key]/g' \
  -e 's/sk_(test|live)_[A-Za-z0-9]{20,}/[REDACTED-stripe-key]/g' \
  -e 's/xoxb-[A-Za-z0-9-]{20,}/[REDACTED-slack-bot]/g' \
  -e 's/AKIA[0-9A-Z]{16}/[REDACTED-aws-access-key]/g' \
  -e 's/ghp_[A-Za-z0-9]{36}/[REDACTED-github-token]/g')

# Surmise the active agent from env. Order of preference:
#   1. CLAUDE_AGENT_NAME — explicit subagent name (most reliable when set)
#   2. CLAUDE_SUBAGENT_TYPE — Claude Code 2.x may set this for nested agents
#   3. CLAUDE_CONTEXT_AGENT — alternative name some versions set
#   4. Parse subagent name from the JSON payload's 'agent' field if present
#   5. If unresolved, SKIP entirely — do not write an unattributed entry.
AGENT="${CLAUDE_AGENT_NAME:-${CLAUDE_SUBAGENT_TYPE:-${CLAUDE_CONTEXT_AGENT:-}}}"
if [ -z "$AGENT" ]; then
  # Try to extract from payload
  AGENT=$(echo "$SAFE" | jq -r '.context.agent // .agent // .subagent_type // empty' 2>/dev/null)
fi
# v0.9.1: when the agent name can't be resolved, do NOT write. The unattributed
# safety-net append produced ~1,439 noise entries (unknown/auto.journal.md) in
# a prior adoption and polluted semantic recall. Agents author their own
# structured journals by design; this net re-enables itself automatically once
# Claude Code provides the agent name (CLAUDE_AGENT_NAME / subagent_type).
case "$AGENT" in
  "" | auto | unknown) exit 0 ;;
esac

# IMPORTANT: this is a safety-net file. Real agents author their own structured
# journal entries in their named file (architect.journal.md, etc.). The file
# produced here is gitignored per .gitignore in the consuming product repo.
# If AGENT resolves to "auto" repeatedly, investigate Claude Code's subagent
# env-var convention for the current version.
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
