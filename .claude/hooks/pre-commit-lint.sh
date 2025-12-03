#!/bin/bash
# Claude Code Pre-Commit Lint Hook
# Runs linting checks before git commits to prevent CI failures
#
# This hook intercepts `git commit` commands and runs:
# 1. ruff check - Python linting
# 2. ruff format --check - Code formatting verification
#
# Exit codes:
#   0 - Success, allow the commit
#   2 - Failure, block the commit

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command - look for git commit patterns
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

echo "🔍 Running pre-commit lint checks..."

# Check if ruff is available
if ! command -v ruff &> /dev/null; then
    echo "⚠️  ruff not found, skipping lint check"
    exit 0
fi

# Run ruff linter
echo "  • Running ruff check..."
if ! ruff check . 2>&1; then
    echo ""
    echo "❌ Linting failed!"
    echo "   Fix with: ruff check . --fix"
    echo ""
    # Return JSON to block the operation
    echo '{"decision": "block", "reason": "Linting failed. Run: ruff check . --fix"}'
    exit 2
fi

# Run ruff formatter check
echo "  • Checking code formatting..."
if ! ruff format --check . 2>&1; then
    echo ""
    echo "❌ Formatting check failed!"
    echo "   Fix with: ruff format ."
    echo ""
    echo '{"decision": "block", "reason": "Formatting failed. Run: ruff format ."}'
    exit 2
fi

echo "✅ All lint checks passed!"
exit 0
