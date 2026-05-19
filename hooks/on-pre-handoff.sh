#!/usr/bin/env bash
# Engineering OS — handoff-event LOGGER (observability, not enforcement)
# Triggered on Write tool use. When a write looks like a handoff-signal artifact
# (developer-report with READY-FOR-SECURITY, a review with verdict PASS, etc.),
# this hook appends a timestamped line to handoff-attempts.log so the pipeline's
# stage transitions are observable.
#
# It deliberately does NOT block writes. Gate ENFORCEMENT is the agents' job —
# each stage self-reviews, QA (Tanvi) re-runs skipped gates, and CTOA (Rohan)
# spot-re-runs QA's gates at Stage 6. Those agents have the context to judge a
# gate; a stdin heuristic does not, and a false block would stall the pipeline.
# Keep enforcement in the agents; keep this hook for the audit trail only.

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

# Record the handoff event for the audit trail (observability only — never blocks)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG="$EOS_DIR/memory/handoff-attempts.log"
echo "$TS  HANDOFF-EVENT  write to $FILE_PATH  (logged; enforcement is the agents' job)" >> "$LOG"

exit 0
