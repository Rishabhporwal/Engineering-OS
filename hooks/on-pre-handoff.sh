#!/usr/bin/env bash
# Engineering OS — pre-handoff hook
# Triggered on Write tool use. If the write looks like a handoff-signal artifact
# (developer-report.md with READY-FOR-SECURITY, security-review.md with PASS,
# etc.), this hook verifies the corresponding quality gate before allowing it.
#
# If a gate fails, returns non-zero to block the write and surfaces the missing
# evidence to the operator.
#
# MVP: minimal implementation; logs intent. V2: rich gate-check logic.

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
EOS_DIR="$ROOT/.engineering-os"
[ -d "$EOS_DIR" ] || exit 0

PAYLOAD="$(cat 2>/dev/null || true)"
[ -n "$PAYLOAD" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

FILE_PATH=$(echo "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
CONTENT_SNIPPET=$(echo "$PAYLOAD" | jq -r '.tool_input.content // empty | .[0:2000]' 2>/dev/null || true)

# Heuristic: handoff artifacts live in runs/ folders
case "$FILE_PATH" in
  *"/runs/"*) ;;
  *) exit 0 ;;
esac

# Heuristic: handoff signal keywords
case "$CONTENT_SNIPPET" in
  *"READY-FOR-SECURITY"*|*"READY-FOR-QA"*|*"verdict\": \"PASS\""*|*"verdict\":\"PASS\""*) ;;
  *) exit 0 ;;
esac

# Log the intent (V2: run actual gate checks)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG="$EOS_DIR/memory/handoff-attempts.log"
echo "$TS  PRE-HANDOFF write to $FILE_PATH  (gate-check stub: ALLOWED in MVP)" >> "$LOG"

# MVP: don't block. V2: actually verify gates.
exit 0
