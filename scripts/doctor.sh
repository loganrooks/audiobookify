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

# macOS has no `timeout` -- it ships as `gtimeout` with coreutils, and often not
# at all. Without this shim the Docker probe below fails with "command not
# found" and gets misreported as blocked registry egress.
if command -v timeout >/dev/null 2>&1; then
  timeout_() { timeout "$@"; }
elif command -v gtimeout >/dev/null 2>&1; then
  timeout_() { gtimeout "$@"; }
else
  timeout_() { shift; "$@"; }  # no timeout available; run unbounded
fi

CAN_TEST=1
CAN_FFMPEG=0
CAN_DOCKER_BUILD=0
CAN_TTS=0
DOCKER_DAEMON_DOWN=0

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
else
  # A stopped daemon is not the same as a missing capability. Try to start it
  # before concluding anything, or the summary below blames the network for
  # what is really just an unstarted service.
  if ! docker info >/dev/null 2>&1 && command -v dockerd >/dev/null 2>&1; then
    dockerd >/tmp/dockerd.log 2>&1 &
    for _ in $(seq 1 15); do
      docker info >/dev/null 2>&1 && break
      sleep 1
    done
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  :
elif ! docker info >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    warn "docker daemon" "not running -- start Docker Desktop: open -a Docker"
  else
    warn "docker daemon" "not running -- try: dockerd >/tmp/dockerd.log 2>&1 &"
  fi
  DOCKER_DAEMON_DOWN=1
else
  pass "docker daemon" "$(docker version --format '{{.Server.Version}}' 2>/dev/null)"
  # A running daemon is not enough: pulling the base image needs egress to
  # Docker Hub, which restricted networks commonly deny.
  if timeout_ 90 docker pull -q python:3.11-slim >/dev/null 2>&1; then
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

# Listing voices is a plain HTTPS GET; synthesis is a WebSocket upgrade that
# Microsoft can reject on its own terms even when the host is perfectly
# reachable. Only the second one tells you whether real conversions work, so
# probe that, and report the two separately when they disagree.
TTS_PROBE=""
if [[ -x "$VENV/bin/python" ]]; then
  TTS_PROBE="$("$VENV/bin/python" - <<'PY' 2>/dev/null
import asyncio

async def probe():
    import edge_tts
    try:
        voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=25)
    except Exception as exc:
        return f"list-failed:{type(exc).__name__}"
    if not voices:
        return "list-failed:empty"
    try:
        comm = edge_tts.Communicate("Test.", "en-US-AndrewNeural")
        async for chunk in comm.stream():
            if chunk["type"] == "audio" and chunk["data"]:
                return "ok"
        return "synth-failed:no-audio"
    except Exception as exc:
        name = type(exc).__name__
        # A certificate error is a local trust problem (e.g. a TLS-terminating
        # egress proxy whose CA is not in certifi), not the service saying no.
        if "Certificate" in name or "SSL" in name or "CERTIFICATE_VERIFY" in str(exc):
            return f"tls-failed:{name}"
        status = getattr(exc, "status", None)
        return f"synth-refused:{name}" + (f":{status}" if status else "")

try:
    print(asyncio.run(asyncio.wait_for(probe(), timeout=60)))
except Exception as exc:
    print(f"probe-failed:{type(exc).__name__}")
PY
)"
fi

case "$TTS_PROBE" in
  ok)
    pass "Edge TTS synthesis" "reachable -- real conversions work"
    CAN_TTS=1
    ;;
  synth-refused:*)
    fail "Edge TTS synthesis" "host reachable but synthesis refused (${TTS_PROBE#synth-refused:})"
    warn "  -> " "not a network block: the service rejected this edge-tts client"
    ;;
  tls-failed:*)
    fail "Edge TTS synthesis" "TLS verification failed (${TTS_PROBE#tls-failed:})"
    warn "  -> " "local trust issue, not an egress block: edge-tts pins certifi's"
    warn "  -> " "CA bundle, so a TLS-terminating proxy's CA is not trusted"
    ;;
  synth-failed:*)
    fail "Edge TTS synthesis" "no audio returned (${TTS_PROBE#synth-failed:})"
    ;;
  *)
    fail "Edge TTS (speech.platform...)" "unreachable/blocked -- no real TTS verification here"
    ;;
esac

# ---------------------------------------------------------------- verdict

head_ "What you can verify here"

# These counts double as a stale-clone tripwire: a mismatch usually means the
# checkout is behind, not that the suite broke. Update them when tests change.
if [[ $CAN_TEST -eq 1 ]]; then
  if [[ $CAN_FFMPEG -eq 1 ]]; then
    pass "full test suite" "expect 567 passed, 5 skipped (TTS)"
  else
    warn "test suite (partial)" "expect 552 passed, 20 skipped (ffmpeg + TTS)"
  fi
  pass "lint / format / types / security" "ruff, mypy, bandit"
  pass "wheel build + smoke test" "python -m build; install into a clean venv"
else
  fail "test suite" "environment not provisioned"
fi

[[ $CAN_FFMPEG -eq 1 ]]      && pass "audio pipeline (mock TTS)" "read_book, make_m4b, normalization" \
                             || fail "audio pipeline" "needs ffmpeg"
if [[ $CAN_DOCKER_BUILD -eq 1 ]]; then
  pass "Docker image build + run" "docker build . && docker run --rm <img> --version"
elif [[ $DOCKER_DAEMON_DOWN -eq 1 ]]; then
  fail "Docker image build + run" "daemon not running -- start it, this is not a network limit"
else
  fail "Docker image build + run" "needs registry egress"
fi

if [[ $CAN_TTS -eq 1 ]]; then
  pass "real end-to-end conversion" "EPUB -> M4B with live TTS"
elif [[ "$TTS_PROBE" == synth-refused:* ]]; then
  fail "real end-to-end conversion" "Edge TTS reachable but refusing synthesis"
elif [[ "$TTS_PROBE" == tls-failed:* ]]; then
  fail "real end-to-end conversion" "Edge TTS blocked by local TLS trust, not egress"
else
  fail "real end-to-end conversion" "needs Edge TTS access"
fi

if [[ $CAN_DOCKER_BUILD -eq 0 || $CAN_TTS -eq 0 ]]; then
  printf '\n\033[1;33mSome verification requires a more permissive environment.\033[0m\n'
  printf 'See docs/handoff.md for the exact outstanding checks and commands.\n'
fi

echo
[[ $CAN_TEST -eq 1 ]] && exit 0 || exit 1
