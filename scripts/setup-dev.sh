#!/usr/bin/env bash
#
# Provision a complete audiobookify development environment.
#
# Idempotent and non-interactive: safe to run repeatedly, safe to run from a
# SessionStart hook, safe to run on a fresh container or an existing checkout.
#
#   ./scripts/setup-dev.sh              # full setup
#   ./scripts/setup-dev.sh --no-system  # skip system packages (no root needed)
#
# After it finishes, run ./scripts/doctor.sh to see what the environment can
# actually do -- some capabilities depend on network policy, not on setup.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"
SKIP_SYSTEM=0
[[ "${1:-}" == "--no-system" ]] && SKIP_SYSTEM=1

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m warn\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  ok\033[0m %s\n' "$*"; }

# Use sudo only when we need it and it exists.
SUDO=""
if [[ "$(id -u)" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 && SUDO="sudo" || SUDO=""
fi

# ---------------------------------------------------------------- system deps

install_system_deps() {
  if [[ $SKIP_SYSTEM -eq 1 ]]; then
    warn "skipping system packages (--no-system)"
    return 0
  fi

  if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
    ok "ffmpeg and ffprobe already present"
    return 0
  fi

  if command -v apt-get >/dev/null 2>&1; then
    log "installing ffmpeg and espeak-ng via apt"
    # `apt-get update` FIRST is not optional. A container image ships with
    # package lists pinned to versions that have since been superseded in the
    # archive, so `apt-get install` without it fails with 404s on the .deb
    # files rather than a useful error.
    $SUDO apt-get update -q || warn "apt-get update reported errors (blocked PPAs are usually harmless)"
    # --no-install-recommends keeps ffmpeg from dragging in the X11/mesa/VA
    # driver tree, which is a few hundred MB of packages a headless box
    # cannot use.
    $SUDO apt-get install -y -q --no-install-recommends ffmpeg espeak-ng \
      || warn "apt install failed -- see doctor.sh output for what this disables"

  elif command -v brew >/dev/null 2>&1; then
    log "installing ffmpeg and espeak via brew"
    brew install ffmpeg espeak || warn "brew install failed"

  elif command -v choco >/dev/null 2>&1; then
    log "installing ffmpeg via choco"
    choco install ffmpeg -y || warn "choco install failed"

  else
    warn "no supported package manager found; install ffmpeg and espeak-ng manually"
    return 0
  fi

  command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg installed" || warn "ffmpeg still missing"
}

# ---------------------------------------------------------------- python env

setup_python() {
  if [[ ! -d "$VENV" ]]; then
    log "creating virtualenv at .venv"
    python3 -m venv "$VENV"
  else
    ok "virtualenv already exists"
  fi

  log "installing audiobookify with dev extras"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  # Editable install so source edits take effect without reinstalling.
  "$VENV/bin/python" -m pip install --quiet -e "$REPO_ROOT[dev]"
  ok "python dependencies installed"
}

# ---------------------------------------------------------------- nltk data

setup_nltk() {
  # audiobookify calls nltk.download() lazily at runtime; pre-seeding it here
  # keeps the first conversion from needing network access.
  if "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import nltk
nltk.data.find("tokenizers/punkt")
nltk.data.find("tokenizers/punkt_tab")
PY
  then
    ok "nltk punkt data already present"
    return 0
  fi

  log "downloading nltk punkt data"
  "$VENV/bin/python" -c \
    "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)" \
    || warn "nltk download failed -- sentence tokenization will fail until this succeeds"
}

# ---------------------------------------------------------------- pre-commit

setup_precommit() {
  if [[ ! -f "$REPO_ROOT/.pre-commit-config.yaml" ]]; then
    return 0
  fi
  # Only install the git hook in a real checkout, and never clobber an
  # existing hook the developer put there deliberately.
  if [[ ! -d "$REPO_ROOT/.git" ]]; then
    warn "not a git checkout; skipping pre-commit hook install"
    return 0
  fi
  if [[ -f "$REPO_ROOT/.git/hooks/pre-commit" ]]; then
    ok "pre-commit hook already installed"
    return 0
  fi
  log "installing pre-commit hooks"
  (cd "$REPO_ROOT" && "$VENV/bin/pre-commit" install) || warn "pre-commit install failed"
}

# ---------------------------------------------------------------- verify

verify() {
  log "verifying the install"
  "$VENV/bin/python" -c "import epub2tts_edge; print('  epub2tts_edge', epub2tts_edge.__version__)"
  "$VENV/bin/audiobookify" --version 2>/dev/null | sed 's/^/  cli: /' || warn "CLI entry point failed"
  "$VENV/bin/ruff" --version | sed 's/^/  /'
  "$VENV/bin/python" -m pytest --version 2>&1 | head -1 | sed 's/^/  /'
}

main() {
  log "audiobookify dev setup ($REPO_ROOT)"
  install_system_deps
  setup_python
  setup_nltk
  setup_precommit
  verify

  cat <<EOF

$(ok "setup complete")

  Activate:      source .venv/bin/activate
  Run tests:     SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/
  Lint:          .venv/bin/ruff check . && .venv/bin/ruff format --check epub2tts_edge tests
  Capabilities:  ./scripts/doctor.sh

EOF
}

main "$@"
