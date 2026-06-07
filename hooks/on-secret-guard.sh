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
# Loud-warn instead of silent-fail-open: a SECRET GUARD that can't run must SAY so, not vanish.
if ! command -v jq >/dev/null 2>&1; then
  echo "WARNING: secret-guard cannot run (jq not installed) — secret-blocking is DISABLED for this write. Install jq." >&2
  exit 0
fi

PATTERNS="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")}/secret-patterns.txt"
if [ ! -f "$PATTERNS" ]; then
  echo "WARNING: secret-guard pattern file missing ($PATTERNS) — secret-blocking is DISABLED for this write." >&2
  exit 0
fi

# Tool name varies by harness/tool: Write|Edit (Claude), Bash (heredoc `cat > f <<EOF`),
# apply_patch|shell (Codex). The Bash case closes the heredoc-bypass the war-game found.
TOOL=$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // .toolName // .tool // empty' 2>/dev/null || true)
case "$TOOL" in
  Write|Edit|Bash|apply_patch|shell) ;;
  "") ;;                                # unknown shape — still scan the raw payload below
  *) exit 0 ;;
esac

# Pull the written content across tool/harness payload shapes (Write content / Edit new_string /
# Bash command / Codex fields). For Bash this catches a secret in a heredoc redirect.
CONTENT=$(printf '%s' "$PAYLOAD" | jq -r '
  .tool_input.content // .tool_input.new_string // .tool_input.command //
  .tool_input.changes // .input.content // .arguments.content // .arguments.input // empty' 2>/dev/null || true)
FILE=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // .tool_input.path // .arguments.path // empty' 2>/dev/null || true)
# Cross-tool robustness: if no structured content field matched, scan the WHOLE raw payload —
# a live secret value anywhere in the tool input blocks regardless of field name. A false block
# is recoverable; a leaked secret on a remote is not.
[ -n "$CONTENT" ] || CONTENT="$PAYLOAD"

# Build the active (non-comment) pattern set.
HITS=$(printf '%s' "$CONTENT" | grep -nE -f <(grep -vE '^\s*#|^\s*$' "$PATTERNS") 2>/dev/null || true)
[ -n "$HITS" ] || exit 0

# Redact the matched value before echoing it back (never print the secret).
SAMPLE=$(printf '%s' "$HITS" | head -1 \
  | sed -E 's#(GOCSPX-|shp[a-z]+_|EAA|sk-|AKIA|gh[pousr]_|xox[baprs]-|eyJ)[A-Za-z0-9_./+-]+#\1***REDACTED***#g' \
  | sed -E 's#(://[^:@/ ]+:)[^@/ ]{3,}@#\1***REDACTED***@#g')

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
