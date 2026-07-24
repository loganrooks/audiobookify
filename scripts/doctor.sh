#!/usr/bin/env bash
#
# Report what this environment can actually do.
#
# Audiobookify's verification surface depends on things setup cannot control:
# whether ffmpeg installed, whether the Docker daemon is up, and whether
# network policy permits reaching Microsoft's speech endpoint and Docker Hub.
# Run this FIRST in a new environment so you know what is verifiable before
# you start, instead of discovering it from a confusing failure later.
#
# Exit code: 0 if the test suite can run, 1 if it cannot.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"
PY="$VENV/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3 || true)"

pass() { printf '  \033[1;32m✓\033[0m %-30s %s\n' "$1" "${2:-}"; }
fail() { printf '  \033[1;31m✗\033[0m %-30s %s\n' "$1" "${2:-}"; }
warn() { printf '  \033[1;33m!\033[0m %-30s %s\n' "$1" "${2:-}"; }
head_() { printf '\n\033[1;34m%s\033[0m\n' "$1"; }

CAN_TEST=1
CAN_FFMPEG=0
CAN_DOCKER_BUILD=0
CAN_TTS=0

# ------------------------------------------------------------------ toolchain

head_ "Toolchain"

if [[ -x "$VENV/bin/python" ]]; then
  pass "virtualenv" ".venv ($("$VENV/bin/python" -V 2>&1))"
else
  fail "virtualenv" "missing -- run ./scripts/setup-dev.sh"
  CAN_TEST=0
fi

if [[ -n "$PY" ]] && "$PY" -c "import epub2tts_edge" >/dev/null 2>&1; then
  pass "epub2tts_edge importable" "$("$PY" -c 'import epub2tts_edge;print(epub2tts_edge.__version__)')"
else
  fail "epub2tts_edge importable" "run ./scripts/setup-dev.sh"
  CAN_TEST=0
fi

for tool in pytest ruff mypy bandit pre-commit; do
  if [[ -x "$VENV/bin/$tool" ]]; then
    pass "$tool" "$("$VENV/bin/$tool" --version 2>&1 | head -1)"
  else
    warn "$tool" "not installed"
    [[ "$tool" == "pytest" ]] && CAN_TEST=0
  fi
done

# ------------------------------------------------------------- system deps

head_ "System dependencies"

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  pass "ffmpeg / ffprobe" "$(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"
  CAN_FFMPEG=1
else
  fail "ffmpeg / ffprobe" "audio tests will SKIP; no conversion possible"
fi

command -v espeak-ng >/dev/null 2>&1 && pass "espeak-ng" || warn "espeak-ng" "optional"

if [[ -n "$PY" ]] && "$PY" - <<'PY' >/dev/null 2>&1
import nltk
nltk.data.find("tokenizers/punkt"); nltk.data.find("tokenizers/punkt_tab")
PY
then
  pass "nltk punkt data" "cached"
else
  warn "nltk punkt data" "missing -- will be downloaded on first use (needs network)"
fi

# ------------------------------------------------------------------- docker

head_ "Docker"

if ! command -v docker >/dev/null 2>&1; then
  warn "docker CLI" "not installed -- cannot verify the image"
elif ! docker info >/dev/null 2>&1; then
  warn "docker daemon" "not running -- try: dockerd >/tmp/dockerd.log 2>&1 &"
else
  pass "docker daemon" "$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  # A running daemon is not enough: pulling the base image needs egress to
  # Docker Hub, which restricted networks commonly deny.
  if timeout 90 docker pull -q python:3.11-slim >/dev/null 2>&1; then
    pass "docker base image pull" "python:3.11-slim available"
    CAN_DOCKER_BUILD=1
  else
    fail "docker base image pull" "registry egress blocked -- cannot build the image here"
  fi
fi

# ---------------------------------------------------------------- network

head_ "Network"

if [[ -n "$PY" ]] && "$PY" - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("https://pypi.org/simple/", timeout=10)
PY
then
  pass "PyPI" "reachable"
else
  warn "PyPI" "unreachable -- pip installs will fail"
fi

if [[ -x "$VENV/bin/python" ]] && "$VENV/bin/python" - <<'PY' >/dev/null 2>&1
import asyncio, edge_tts
voices = asyncio.run(asyncio.wait_for(edge_tts.list_voices(), timeout=25))
raise SystemExit(0 if voices else 1)
PY
then
  pass "Edge TTS (speech.platform...)" "reachable -- real conversions work"
  CAN_TTS=1
else
  fail "Edge TTS (speech.platform...)" "unreachable/blocked -- no real TTS verification here"
fi

# ---------------------------------------------------------------- verdict

head_ "What you can verify here"

if [[ $CAN_TEST -eq 1 ]]; then
  if [[ $CAN_FFMPEG -eq 1 ]]; then
    pass "full test suite" "expect 553 passed, 5 skipped (TTS)"
  else
    warn "test suite (partial)" "expect ~544 passed, ~14 skipped (ffmpeg + TTS)"
  fi
  pass "lint / format / types / security" "ruff, mypy, bandit"
  pass "wheel build + smoke test" "python -m build; install into a clean venv"
else
  fail "test suite" "environment not provisioned"
fi

[[ $CAN_FFMPEG -eq 1 ]]      && pass "audio pipeline (mock TTS)" "read_book, make_m4b, normalization" \
                             || fail "audio pipeline" "needs ffmpeg"
[[ $CAN_DOCKER_BUILD -eq 1 ]] && pass "Docker image build + run" "docker build . && docker run --rm <img> --version" \
                             || fail "Docker image build + run" "needs registry egress"
[[ $CAN_TTS -eq 1 ]]          && pass "real end-to-end conversion" "EPUB -> M4B with live TTS" \
                             || fail "real end-to-end conversion" "needs Edge TTS access"

if [[ $CAN_DOCKER_BUILD -eq 0 || $CAN_TTS -eq 0 ]]; then
  printf '\n\033[1;33mSome verification requires a more permissive environment.\033[0m\n'
  printf 'See docs/handoff.md for the exact outstanding checks and commands.\n'
fi

echo
[[ $CAN_TEST -eq 1 ]] && exit 0 || exit 1
