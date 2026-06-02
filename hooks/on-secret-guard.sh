#!/usr/bin/env bash
# Engineering OS — secret guard. PreToolUse hook on Write|Edit.
# BLOCKS (exit 2) any write whose content contains a secret VALUE (see
# hooks/secret-patterns.txt). This is the MECHANICAL fix for incident O1
# (live OAuth/Shopify/DB creds were written into committed .engineering-os
# artifacts). v2's prose "redact before writing" rule + the post-write journal
# sanitizer did NOT cover the O1 classes and never rewrote the artifact — this
# hook stops the secret BEFORE it hits disk, regardless of what the model remembers.
#
# Uses VALUE patterns (prefix + realistic length) so docs that mention a bare
# prefix as an example do not trip. Fails OPEN (exit 0) if jq/patterns missing,
# so it never wedges the pipeline — but when it can run, it is a hard deny.

set -euo pipefail

PAYLOAD="$(cat 2>/dev/null || true)"
[ -n "$PAYLOAD" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

PATTERNS="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")}/secret-patterns.txt"
[ -f "$PATTERNS" ] || exit 0

TOOL=$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // .toolName // empty' 2>/dev/null || true)
case "$TOOL" in
  Write|Edit) ;;
  *) exit 0 ;;
esac

# Pull the content being written (Write: content; Edit: new_string) + the path.
CONTENT=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null || true)
FILE=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -n "$CONTENT" ] || exit 0

# Build the active (non-comment) pattern set.
HITS=$(printf '%s' "$CONTENT" | grep -nE -f <(grep -vE '^\s*#|^\s*$' "$PATTERNS") 2>/dev/null || true)
[ -n "$HITS" ] || exit 0

# Redact the matched value before echoing it back (never print the secret).
SAMPLE=$(printf '%s' "$HITS" | head -1 | sed -E 's#(GOCSPX-|shp[a-z]+_|EAA|sk-|AKIA|gh[pousr]_|xox[baprs]-|eyJ)[A-Za-z0-9_./+-]+#\1***REDACTED***#g')

cat >&2 <<EOF
BLOCKED: this Write/Edit contains what looks like a live secret value — refusing to write it to disk.
  file: ${FILE:-<unknown>}
  match (redacted): ${SAMPLE}
This is the O1 prevention gate (hooks/secret-patterns.txt). A secret must NEVER land in an
artifact/journal/state/log — the repo has a remote. Replace the value with ***REDACTED*** (or a
Secrets-Manager ARN reference) and write again. If this is a genuine false positive on documentation,
shorten/placeholder the example so it is not a full-length token.
EOF
exit 2
