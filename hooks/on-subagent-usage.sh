#!/usr/bin/env bash
# Engineering OS — spawn heartbeat. PostToolUse hook on Task|Agent.
# Fixes O13/O14 at the root: in v1 BOTH usage logging and live.log narration were
# the orchestrator LLM "remembering" to echo — and both silently died. This hook
# fires on the HARNESS event loop every time a spawned subagent RETURNS, so it
# records ground truth the model cannot skip:
#   1) appends a row to .engineering-os/spawn-heartbeat.jsonl  (proves the spawn happened)
#   2) appends a line to .engineering-os/live.log                (liveness can't go silent)
#
# It deliberately does NOT write usage.jsonl (the orchestrator's usage_logger owns the
# token NUMBERS, to avoid double-counting). Instead, heartbeat_check.py reconciles the
# two: a spawn with a heartbeat but no usage row = the O14 silent-stop, now DETECTABLE.
# Fails open (exit 0) so it never wedges the pipeline.

set -euo pipefail

PAYLOAD="$(cat 2>/dev/null || true)"
[ -n "$PAYLOAD" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL=$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // .toolName // empty' 2>/dev/null || true)
case "$TOOL" in
  Task|Agent) ;;
  *) exit 0 ;;
esac

PROJ="${CLAUDE_PROJECT_DIR:-.}"
EOS="$PROJ/.engineering-os"
[ -d "$EOS" ] || exit 0

# subagent type is the agent id; req_id / stage / model are embedded in the spawn prompt
AGENT=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.subagent_type // .tool_input.subagentType // empty' 2>/dev/null || true)
PROMPT=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.prompt // .tool_input.description // empty' 2>/dev/null || true)
REQ=$(printf '%s' "$PROMPT" | grep -oiE 'req[_-]?id[":= ]+[a-z0-9-]+' | head -1 | grep -oiE '(feat|fix|chore|spike|exp)-[a-z0-9-]+' | head -1 || true)
STAGE=$(printf '%s' "$PROMPT" | grep -oiE 'stage[ _:#-]*[0-9]' | head -1 | grep -oE '[0-9]' | head -1 || true)
MODEL=$(printf '%s' "$PROMPT" | grep -oiE '\b(opus|sonnet|haiku)\b' | head -1 || true)
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

printf '{"ts":"%s","agent":"%s","stage":"%s","req_id":"%s","model":"%s","event":"spawn_returned"}\n' \
  "$TS" "${AGENT:-unknown}" "${STAGE:-?}" "${REQ:-?}" "${MODEL:-?}" >> "$EOS/spawn-heartbeat.jsonl" 2>/dev/null || true

printf '%s [heartbeat] %s S%s %s returned\n' \
  "$(date -u +%H:%M:%SZ)" "${AGENT:-subagent}" "${STAGE:-?}" "${REQ:-?}" >> "$EOS/live.log" 2>/dev/null || true

exit 0
