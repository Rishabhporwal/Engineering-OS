#!/usr/bin/env bash
# Engineering OS — session-start hook
# Surfaces the current state of in-flight requirements + recent journal activity
# so every session starts with full continuity. Output is consumed by Claude
# Code as session-start context.

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE="$ROOT/.engineering-os/state/active.json"
MEM="$ROOT/.engineering-os/memory/agents"

if [ ! -d "$ROOT/.engineering-os" ]; then
  cat <<EOF
[engineering-os] No .engineering-os/ directory found at $ROOT. Plugin not initialized.
EOF
  exit 0
fi

echo "[engineering-os] === Session start ==="

# 1) In-flight requirements
if [ -f "$STATE" ] && command -v jq >/dev/null 2>&1; then
  COUNT=$(jq '.active_requirements | length' "$STATE" 2>/dev/null || echo "0")
  echo "[engineering-os] In-flight requirements: $COUNT"
  if [ "$COUNT" != "0" ]; then
    jq -r '.active_requirements[] |
      "  - \(.req_id) — Stage \(.stage) (\(.status)) — owner: \(.current_owner_persona // .current_owner) — last journal: \(.last_journal_entry_at // "n/a")"' "$STATE" 2>/dev/null || true
  fi
else
  echo "[engineering-os] active.json missing or jq unavailable — skipping in-flight summary."
fi

echo

# 2) Recent journal activity per agent (last entry of each)
if [ -d "$MEM" ]; then
  echo "[engineering-os] Recent journal entries (most recent per agent):"
  for j in "$MEM"/*.journal.md; do
    [ -f "$j" ] || continue
    agent=$(basename "$j" .journal.md)
    # Find the last "## " heading line
    last_heading=$(grep -n '^## ' "$j" 2>/dev/null | tail -n 1 || true)
    if [ -n "$last_heading" ]; then
      line_num=$(echo "$last_heading" | cut -d: -f1)
      heading_text=$(echo "$last_heading" | cut -d: -f2-)
      echo "  - $agent: $heading_text"
    fi
  done
fi

echo

# 3) Pre-flight Agent tool check
# The pipeline relies on the Agent tool for autonomous stage-to-stage handoffs.
# If it's unavailable (older Claude Code versions or certain plans), warn the operator.
if [ -n "${CLAUDE_SUPPORTS_SUBAGENTS:-}" ] && [ "$CLAUDE_SUPPORTS_SUBAGENTS" = "false" ]; then
  cat <<EOF
[engineering-os] ⚠️  WARNING: Subagent support not detected.
  The pipeline will require manual /handoff between stages.
  Agents cannot invoke each other automatically.
  To proceed: after each stage completes, run the next agent manually.
  Consider upgrading your Claude Code version for autonomous flow.
EOF
fi

echo

# 4) Reminders
cat <<EOF
[engineering-os] Reminders:
  • Read docs/business-context.md + docs/technical-context.md before non-trivial work.
  • Memory is git-committed — your decisions persist for teammates.
  • Use /status for the full pipeline view, /recall <feat-slug> for one feature.
  • Use /resume <req-id> to recover an interrupted pipeline.
  • Use /test-pipeline --dry-run to validate plugin health.
  • Anti-blind-agreement: challenge weak requirements (see prompts/challenge-framework.md).
[engineering-os] === Ready ===
EOF
