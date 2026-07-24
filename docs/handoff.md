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
| Real Edge TTS synthesis | See the 2026-07-24 session below — the host is reachable, but the WebSocket upgrade is refused. |
| PyPI publish | Needs Trusted Publishing configured in PyPI settings (a repo/PyPI admin action, not an environment capability). |

---

## Session update — 2026-07-24 (second pass)

**Two of the three "blocked" items above were wrong.** Both were re-tested and
the environment could in fact do them. Details below, because the pattern
matters more than the individual calls.

### Docker is fully verified now ✅

Docker Hub egress was **not** denied. The earlier session hit a stopped daemon,
started it, and separately saw a pull failure whose real cause was TLS, then
recorded the whole capability as "registry egress denied". After
`dockerd` was started, `docker pull hello-world` and `python:3.11-slim` both
succeeded on the first attempt.

Verified by actually building and running the image:

| Check | Result |
|-------|--------|
| `docker build` | succeeds |
| `docker run --rm <img> --version` | `audiobookify 2.5.0` — **the entrypoint fix is confirmed at runtime** |
| `docker run --rm <img> --help` | 177 lines, exit 0 |
| `--entrypoint id` | `uid=1000(audiobookify)` — non-root confirmed |
| `--entrypoint ffmpeg` | ffmpeg 7.1.5 present |
| console scripts | all four (`audiobookify`, `abfy`, `audiobookify-tui`, `abfy-tui`) present |
| EPUB → M4B through a bind mount | produces an M4B with correct chapter markers |

One caveat specific to sandboxes like this one: egress is TLS-terminated by a
proxy, so `pip` **inside the build** fails certificate verification. The build
needs the proxy CA added in an early layer and `--network host`. That is an
environment accommodation, not a Dockerfile defect — the committed Dockerfile is
correct on a normal network. The only delta used for verification was a `COPY`
of the CA plus `PIP_CERT`/`SSL_CERT_FILE`.

### The bind-mount permission problem is real, and now handled

As predicted: the container user (uid 1000) **cannot** write to a bind-mounted
host directory owned by another uid. `chown /books` in the Dockerfile is masked
by the mount. Confirmed both the failure and the two fixes:

- `--user "$(id -u):$(id -g)" -e HOME=/tmp` → works
- host directory owned by uid 1000 → works

`-e HOME=/tmp` is required alongside `--user`, because the overridden uid has no
home directory in the image and the job scratch dir lives under `$HOME`. Both
README Docker sections now document this, and the pipeline degrades to a warning
instead of failing when the destination is not writable.

### Edge TTS: RESOLVED ✅ — the pin was the outage

**Superseded by the findings below.** Read this section for how the diagnosis
went wrong before trusting any of its intermediate conclusions.

The 403 reproduced on a maintainer's Mac (residential IP, Python 3.13), ruling
out both the sandbox and IP reputation. Testing versions directly then settled
it:

| edge-tts | Result |
|---|---|
| 7.0.2 (was pinned) | 403 |
| 7.1.0 | 403 |
| 7.2.1 | 403 |
| **7.2.4** | ✅ real audio |
| **7.2.8** | ✅ real audio |

`edge-tts>=6.1.0,<7.1.0` excluded every release that works. The pin was written
2025-12-07; 7.2.4 fixed the breakage on 2025-12-11. **It was correct for four
days**, then became the sole cause of the failure it was written to prevent —
and looked vindicated every time it failed, because the failure matched the
comment. Floor is now `>=7.2.4,<8`.

**A real end-to-end conversion now works.** A clean `pip install .` resolves
7.2.8 and produces a 23.7s M4B: three chapter markers aligned to titles, correct
title/artist, and −25.6 dB mean volume (digital silence reads ≈ −91 dB, so this
is genuine speech, not the mock).

Why it took so long to find, and what changed:

- Dependabot **ignored** `edge-tts`, with the note "only bump after the TTS
  canary passes against the new version" — but the canary only ever tested the
  *pinned* version, so that condition was unevaluatable. The ignore rule
  suppressed the very release that fixed the problem. Both are now fixed: the
  canary tests pinned **and** latest, and edge-tts is visible to Dependabot.
- The constraint propagated from a code comment → `dependabot.yml` → review docs
  → session instructions, losing its "as of December 2025" qualifier at each hop
  and gaining authority. `external-constraints.toml` now exists so claims about
  the outside world carry an expiry that fails the build.

### Original (incorrect) diagnosis, kept as a record ❌

The earlier diagnosis (gateway policy denial, `connect_rejected`) **does not hold
here**. In this environment:

- `curl "$HTTPS_PROXY/__agentproxy/status"` reports **zero** relay failures
- `edge_tts.list_voices()` returns 322 voices
- a plain GET to the synthesis host returns a genuine Microsoft response

So the host is reachable. Two separate things still stop real audio:

1. **TLS.** `edge-tts` hardcodes `ssl.create_default_context(cafile=certifi.where())`,
   so it ignores `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` and does not trust a
   TLS-terminating proxy's CA. This is a local trust problem, not egress.
2. **A 403 on the WebSocket upgrade**, after TLS is made to pass. The GET
   succeeds against the same host, so this is Microsoft refusing this client —
   most likely the stale `Sec-MS-GEC-Version` (`1-130.0.2849.68`) that
   edge-tts 7.0.2 sends. Working around it means spoofing a browser version
   string, which was deliberately not attempted.

**Resolved — the pin needed revisiting, and it did reproduce on a normal
network.** See the section above. `scripts/doctor.sh` now distinguishes the
three cases (reachable / TLS-failed / refused) instead of reporting one
undifferentiated "unreachable"; the "refused" case is what pointed at the client
rather than the network.

### A defect that blocked both checks 🔴 found and fixed

`ConversionPipeline.package_audiobook()` called:

```python
make_m4b(files=..., chapternames=..., cover=..., output=...)
```

but the real signature is
`make_m4b(files, sourcefile, speaker, normalizer, silence_detector, output_dir)`.
Three of the four keyword arguments do not exist, so **every full conversion
died with `TypeError: make_m4b() got an unexpected keyword argument
'chapternames'`** at the packaging step.

`audiobookify book.epub` — the headline documented workflow — routes through this
pipeline, so it could never produce an M4B, with or without working TTS. The
three other call sites (legacy CLI, TUI, batch processor) all call it correctly;
`ConversionPipeline` was the odd one out.

It survived because **no test ever called `make_m4b`**. The only reference in the
suite was `assert make_m4b is not None`.

Fixed, along with three consequences of the same code path never having run:

- `generate_metadata()` was never called, so the M4B would have had **no chapter
  markers** even if it had built
- `add_cover()` was never called, so **cover art was silently dropped**
- `normalize`/`trim-silence` config was accepted but never applied
- output was left in `~/.audiobookify/jobs/<id>/`, so `docker run --rm` destroyed
  it and the documented bind-mount workflow produced nothing

Output is now delivered next to the source file (matching the TUI), falling back
to the job directory with a warning if that is not writable.

Four regression tests added in `tests/test_pipeline.py`, **each verified to fail
against the unfixed code**: a signature-bind contract check, a chapter-titles
check, an output-location check, and an ffmpeg-backed end-to-end test that
ffprobes the resulting M4B for ordered chapter markers.

Suite: **560 passed, 5 skipped**; ruff clean.

---

## Outstanding checks, with commands

### 1. Docker image end-to-end ✅ DONE (2026-07-24, second pass)

Completed — see the session update above. The commands below are kept because
they are still the right smoke test after any Dockerfile change.

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

Resolved: the write failure is real, and `--user "$(id -u):$(id -g)" -e HOME=/tmp`
is the documented remedy (now in both README Docker sections). The non-root
default is worth keeping — the fallback warning makes the failure legible rather
than silent.

### 2. Real end-to-end conversion with live TTS ✅ DONE (2026-07-24)

Done — a clean install now produces a real audiobook with real speech. See the
"Edge TTS: RESOLVED" section above for the measurements.

What is still **not** verified is playback in real players (Apple Books,
Audiobookshelf, Smart AudioBook Player): that chapter markers land correctly in
a player UI and that cover art displays. That needs a human with a player and is
the remaining item, along with §3 below.

If synthesis ever fails again, run `./scripts/doctor.sh` and read which of the
three TTS outcomes it reports — and check the canary's *pinned vs latest* legs
before concluding Microsoft is at fault. That assumption is what cost seven
months last time.

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

1. Configure [PyPI Trusted Publishing](https://pypi.org/manage/account/publishing/) as a
   *pending* publisher — PyPI project `audiobookifier`, owner `loganrooks`, repo
   `audiobookify`, workflow `release.yml`, environment `pypi`. **Done as of 2026-07-24.**
   The PyPI project name deliberately differs from the GitHub repo name; the
   `audiobookify` name on PyPI belongs to an account that is no longer accessible.
2. Create the `pypi` environment in repository settings
3. Add a `## [2.6.0] - YYYY-MM-DD` section to `CHANGELOG.md` and set the version in
   `pyproject.toml` to match — **`release.yml` refuses to publish if these disagree**
4. `git tag v2.6.0 && git push origin main --tags`
5. Verify independently: `pipx install audiobookifier` and
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
  the exact denied hosts. Check it before theorising about network problems — and
  note that an **empty** `recentRelayFailures` is itself evidence: it means the
  proxy is not the thing blocking you.
- **Do not record a capability as unavailable until you have run the thing itself.**
  Both "blocked" entries in the original table were wrong. Docker Hub egress was
  fine — the daemon was simply not started. Edge TTS was reachable — the failure
  was first a local CA-trust problem and then a service-side refusal. Each was
  inferred from an adjacent symptom rather than tested directly, and each wrong
  call then shaped the plan built on top of it. A one-line probe (`docker pull
  hello-world`, one `Communicate(...).stream()`) settles these in seconds.
- **`doctor.sh` is only as good as its probes.** It now starts a stopped Docker
  daemon before judging, and probes real TTS *synthesis* rather than the voice
  list (a plain GET that succeeds even when the WebSocket upgrade is refused).
  If you find it reporting something you can disprove by hand, fix the probe —
  the next session is told to trust it.
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
