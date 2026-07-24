#!/bin/bash
#
# SessionStart hook: provision the environment for Claude Code on the web.
#
# Without this, a fresh remote session starts with no ffmpeg, no virtualenv,
# and no NLTK data -- so `pytest` yields a wall of FileNotFoundError('ffprobe')
# and nothing is runnable until someone works out why.
#
# Runs synchronously so dependencies are guaranteed ready before the session
# begins. Local runs are skipped: developers manage their own environments via
# ./scripts/setup-dev.sh.

set -euo pipefail

# Only provision in the remote/web environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_ROOT"

echo "Provisioning audiobookify dev environment..."
./scripts/setup-dev.sh || {
  echo "setup-dev.sh reported errors; continuing so the session still starts."
  echo "Run ./scripts/doctor.sh to see what is available."
}

# Put the virtualenv first on PATH so `pytest`, `ruff`, and `audiobookify`
# resolve to the project's versions for the rest of the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$REPO_ROOT/.venv/bin:\$PATH\""
    echo "export VIRTUAL_ENV=\"$REPO_ROOT/.venv\""
    # The test suite must never call Microsoft's TTS service. Matches CI.
    echo 'export SKIP_TTS_TESTS=1'
  } >> "$CLAUDE_ENV_FILE"
fi

echo "Environment ready. Run ./scripts/doctor.sh for capability details."
