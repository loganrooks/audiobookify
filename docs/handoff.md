# Session Handoff

**From:** Claude Code on the web session, 2026-07-24
**Branch:** `claude/devops-infrastructure-review-2lwaaj`
**For:** the next session, in an environment with fewer network restrictions

---

## Start here

```bash
./scripts/setup-dev.sh     # provision: ffmpeg, .venv, deps, nltk data, pre-commit hooks
./scripts/doctor.sh        # report what this environment can actually verify
```

`doctor.sh` is the important one. **Run it before anything else and believe what it
says.** It probes ffmpeg, the Docker daemon, Docker Hub egress, and Edge TTS
reachability, then tells you which of the outstanding checks below are possible here.

In Claude Code on the web this is automatic — `.claude/hooks/session-start.sh` runs
`setup-dev.sh` at session start and puts `.venv/bin` on `PATH` with
`SKIP_TTS_TESTS=1` set. That takes effect for all future sessions **once this branch
is merged to the default branch.**

---

## What this branch contains

Three commits, in order:

1. **`5c09e2b`** — fixes four defects that broke documented functionality, plus the
   release pipeline and CI hardening
2. **`fd1fce0`** — [`project-review-2026-07.md`](./project-review-2026-07.md) and
   [`uplift-plan.md`](./uplift-plan.md)
3. **`5f7f7c0`** — [`dependency-reduction-plan.md`](./dependency-reduction-plan.md)

Plus this handoff and the setup tooling. Read the review first; it explains why
everything else looks the way it does.

---

## Verification status

### Verified in this environment ✅

| What | Evidence |
|------|----------|
| Full test suite | **556 passed, 5 skipped** (ffmpeg present, TTS skipped) |
| Bare-environment suite | 545 passed, 16 skipped — no ffmpeg, no network, zero failures |
| Empty-chapter fix | 3 regression tests added, each **proven to fail when the fix is reverted** |
| `--test-mode` fix | `enable_test_mode()` called from a wheel installed in a clean venv, outside the source tree |
| Docker entrypoint fix | Build context replicated exactly; console scripts now created (was: none) |
| `--version` / extras | `audiobookify --version` → `2.5.0`; `.[tui]` and `.[all]` resolve without warnings |
| Lint / format / security | ruff clean, `bandit -ll` clean (0 high, 0 medium) |
| Coverage | 47.88% overall; CLI 13.88%, `tui/app.py` 9.20%, `audio_generator.py` 68.61% |
| ffmpeg cover-art substitution | `-disposition:v attached_pic` → `covr` atom present, 386 bytes, JPEG |
| Setup script | Runs green from a deleted `.venv` on a bare container |
| SessionStart hook | Provisions correctly with `CLAUDE_CODE_REMOTE=true`; no-ops without it |

### Blocked here — needs a permissive environment ❌

| What | Why it's blocked |
|------|------------------|
| Docker image build + run | Daemon runs, but Docker Hub egress is denied: `403 Forbidden` from `production.cloudfront.docker.com` when pulling `python:3.11-slim`. `--network host` does not help — the *daemon* does the pull. |
| Real Edge TTS anything | Gateway policy-denies `speech.platform.bing.com:443` (`connect_rejected`, 403 to CONNECT). Not a TLS problem — a policy denial. |
| PyPI publish | Needs Trusted Publishing configured in PyPI settings (a repo/PyPI admin action, not an environment capability). |

---

## Outstanding checks, with commands

### 1. Docker image end-to-end 🔴 highest priority

The image entrypoint fix is verified at the packaging layer but **the image has never
been built or run.** This is the one fix where the original bug was invisible to
everything except actually running the container, so verify it that way.

```bash
docker build -t audiobookify:verify .
docker run --rm audiobookify:verify --version          # must print "audiobookify 2.5.0"
docker run --rm audiobookify:verify --help             # must not error
docker run --rm --entrypoint id audiobookify:verify    # must NOT be uid=0
docker run --rm --entrypoint ffmpeg audiobookify:verify -version

# And a real conversion through the mounted volume:
mkdir -p books && cp /path/to/some.epub books/
docker run --rm -v "$PWD/books:/books" audiobookify:verify /books/some.epub
ls -l books/                                            # expect some.txt written as uid 1000
```

Watch for: the non-root user needing write access to `/books`. The Dockerfile chowns
`/books` at build time, but a bind-mounted host directory keeps its **host**
ownership, so writes may fail depending on the host uid. If they do, document
`--user "$(id -u):$(id -g)"` in the README, or reconsider the non-root default.

### 2. Real end-to-end conversion with live TTS 🔴

Nothing in this branch has ever produced a real audiobook — everything ran on
`MockTTSEngine`, which emits silence.

```bash
unset SKIP_TTS_TESTS
pytest tests/test_tts_connectivity.py -v         # 4 live tests, currently never run in CI
audiobookify --list-voices
audiobookify --preview-voice --speaker en-US-AndrewNeural

# Full path on a real DRM-free EPUB:
audiobookify book.epub                            # → book.txt
audiobookify book.txt --cover cover.png           # → book (en-US-AndrewNeural).m4b
```

Then check the output in a real player: chapter markers land on the right titles,
cover art displays, no truncation at chapter boundaries.

**Specifically confirm the empty-chapter fix on real input.** The silent-placeholder
path is only covered by mock tests. Find or construct an EPUB with a TOC entry
pointing at a title page or section divider, and confirm chapter markers stay
aligned with titles through it.

### 3. Cover art in real players 🟡

`attached_pic` produces a correct `covr` atom (verified). What's unverified is
whether **Apple Books, Audiobookshelf, and Smart AudioBook Player** display it. This
gates the `mutagen` → ffmpeg substitution in the
[dependency plan](./dependency-reduction-plan.md).

```bash
ffmpeg -i in.m4b -i cover.png -map 0:a -map 1:v -c:a copy -c:v mjpeg \
       -disposition:v attached_pic out.m4b
```

Compare side by side against a mutagen-embedded file in each player.

### 4. Performance baseline before M3 🟡

The review found an event loop *and* thread pool created per paragraph, with each
`asyncio.run()` acting as a hard barrier. **Measure the current cost before
optimising**, so the M3 work has a number to beat:

```bash
time audiobookify book.txt          # a real multi-chapter book, live TTS
```

Record wall clock, and note the ratio of time in TTS versus ffmpeg. Without a
baseline there is no way to tell whether the M3 rework helped.

### 5. First release 🔴

Blocked on a one-time setup step, not on code:

1. Configure [PyPI Trusted Publishing](https://pypi.org/manage/project/audiobookify/settings/publishing/)
   — owner `loganrooks`, repo `audiobookify`, workflow `release.yml`, environment `pypi`
2. Create the `pypi` environment in repository settings
3. Add a `## [2.6.0] - YYYY-MM-DD` section to `CHANGELOG.md` and set the version in
   `pyproject.toml` to match — **`release.yml` refuses to publish if these disagree**
4. `git tag v2.6.0 && git push origin main --tags`
5. Verify independently: `pipx install audiobookify` and
   `docker pull ghcr.io/loganrooks/audiobookify:v2.6.0` from a clean machine. Do not
   trust the pipeline's own smoke tests for the first run.

---

## Environment notes worth carrying forward

Things that cost me time here, so they don't cost you time:

- **`apt-get update` before `apt-get install`, always.** Container images ship with
  package lists pinned to versions since superseded in the archive, so `install`
  alone fails with 404s on `.deb` files rather than a useful message. My first
  attempt at installing ffmpeg failed this way and I wrongly concluded ffmpeg was
  unavailable. `setup-dev.sh` handles it.
- **Use `--no-install-recommends` for ffmpeg**, or it drags in the X11/mesa/VA driver
  tree that a headless box cannot use.
- **The Docker daemon may need starting manually:** `dockerd >/tmp/dockerd.log 2>&1 &`.
  It is not running by default. I initially reported Docker as "unavailable" when it
  merely wasn't started.
- **`curl -sS "$HTTPS_PROXY/__agentproxy/status"`** lists recent relay failures with
  the exact denied hosts. That is how the `speech.platform.bing.com` and Docker Hub
  denials were identified. Check it before theorising about network problems.
- **Tool versions must be pinned in lockstep.** `.pre-commit-config.yaml` and
  `pyproject.toml` each pin ruff and bandit; if they drift, pre-commit and CI
  reformat each other's work forever, and bandit's findings change with the rev.
  Both files carry comments saying so — keep them in sync when Dependabot bumps one.
- **Coverage numbers depend on provisioning.** `audio_generator.py` reads as 21.77%
  without ffmpeg and 68.61% with it, because the tests that exercise it skip. An
  under-provisioned environment understates well-tested modules and makes the
  coverage distribution look worse than it is. Run `doctor.sh` before trusting a
  coverage figure.

---

## Next actions, in order

1. Merge this branch (the SessionStart hook only takes effect from the default branch)
2. Run checks **1** and **2** above — they close the last gaps on the four fixes
3. Configure Trusted Publishing and cut `v2.6.0` — [uplift plan M1](./uplift-plan.md#m1--ship-a-release-2-weeks)
4. Then M2: CLI and TUI coverage, and the mypy baseline

Open questions for the maintainer, none blocking:

- Should `.serena/memories/` stay in version control? They're AI session notes.
- Is the `epub2tts_edge` → `audiobookify` rename worth the breaking change? It's
  bundled with the CLI subcommand restructure in
  [M4](./uplift-plan.md#m4--grow-the-project-12-weeks).
- Non-root Docker default: keep it, or revert if bind-mount permissions prove
  annoying in practice? Check **1** will tell you.
