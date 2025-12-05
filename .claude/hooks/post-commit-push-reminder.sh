#!/bin/bash
# Claude Code Post-Commit Push Reminder Hook
# Reminds to push after successful commits
#
# This hook intercepts successful `git commit` commands and:
# 1. Checks if the branch has unpushed commits
# 2. Outputs a reminder to push if commits are unpushed

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the tool name and input
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")

# Only intercept Bash tool with git commit commands
if [[ "$TOOL_NAME" != "Bash" ]]; then
    exit 0
fi

if [[ "$TOOL_INPUT" != *"git commit"* ]]; then
    exit 0
fi

# Navigate to repo root
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# Check if there are unpushed commits
UNPUSHED=$(git log @{u}.. --oneline 2>/dev/null | wc -l || echo "0")

if [[ "$UNPUSHED" -gt 0 ]]; then
    echo ""
    echo "⚠️  REMINDER: You have $UNPUSHED unpushed commit(s)!"
    echo "   Run: git push"
    echo ""
fi

exit 0
