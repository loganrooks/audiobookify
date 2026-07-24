# Audiobookify — Code, Infrastructure & Project Review

**Date:** 2026-07-24
**Version reviewed:** 2.5.0 (commit `53a8daf`)
**Scope:** Codebase, CI/CD, packaging, release & deployment, public-facing surfaces,
contributor experience, and strategic direction.

This supersedes [`archive/code-review-2.3.0.md`](./archive/code-review-2.3.0.md).

---

## Executive summary

Audiobookify is a genuinely capable tool with a well-modularised codebase, a real
test suite, and a feature set well beyond its upstream fork. The engineering
*inside* the package is in decent shape.

The problem is everything around it. **The project has been shipping features
faster than it has been shipping software.** Three of its four advertised
distribution and development surfaces were broken or misleading at the time of
this review:

- The **Docker image could not start at all** — and had been that way since Docker
  support was introduced in 2.3.0.
- **`--test-mode` crashed** for every user who installed from PyPI.
- **PyPI has been stuck at 2.3.0** since 2025-12-03 while the repository advanced
  through 2.4.0 and 2.5.0. There are no git tags and no GitHub Releases.
- Documented install commands referenced **extras that did not exist**.

None of these were caught, because CI validated that artifacts *build*, never that
they *work*. A `docker build` step that never runs the image cannot detect a
missing entrypoint; a `python -m build` step that never installs the wheel cannot
detect a missing module.

These four have been fixed and verified in this branch (see
[Part 1](#part-1-critical-defects-found-and-fixed)). What remains is a set of
structural issues that need a deliberate plan, laid out in
[`uplift-plan.md`](./uplift-plan.md).

**The single largest strategic risk is not in this list at all:** the entire
product rests on an unofficial client for an undocumented Microsoft endpoint,
with no abstraction layer and no second implementation. That is discussed in
[Part 6](#part-6-strategic-assessment).

### Assessment at a glance

| Dimension | Rating | Note |
|-----------|--------|------|
| Module structure & separation | 🟢 Good | Clean boundaries, dataclass configs, sensible `core/` extraction |
| Test suite breadth | 🟡 Mixed | 558 tests, but 45% coverage concentrated away from the critical path |
| Critical-path test coverage | 🔴 Poor | CLI 14%, TUI app 9%, audio generation 22% |
| Type safety | 🔴 Poor | 53 mypy errors; `py.typed` declared but missing |
| CI correctness | 🟡 Improving | Was building without verifying; called a live 3rd-party API on every PR |
| Release & deployment | 🔴 Was absent | No tags, releases, or automation; now implemented |
| Public docs accuracy | 🟡 Mixed | Good coverage, but documented commands that could not work |
| Contributor onboarding | 🟡 Mixed | Good CONTRIBUTING, but stale structure and confusing local failures |
| Dependency risk posture | 🔴 High | Single undocumented upstream, no abstraction, no fallback |

---

## Method

Everything asserted here was verified by execution, not by reading alone. Where a
claim rests on static reading, it says so.

- Full test suite run under three configurations (with/without network,
  with/without ffmpeg)
- Wheel built and installed into clean virtualenvs; CLI and API exercised from
  outside the source tree
- The Dockerfile's `COPY` set replicated exactly into a scratch directory and
  installed, to isolate the entrypoint failure (the Docker daemon was unavailable
  in the review environment, so the image itself was not built — the failure was
  reproduced at the packaging layer, which is where it originates)
- `ruff`, `mypy`, and `bandit` run across the package
- Coverage measured per module
- PyPI release history and GitHub tags/releases/workflow history queried directly

---

## Part 1: Critical defects (found and fixed)

### 1.1 The Docker image could never run — `Dockerfile`

**Severity: Critical.** Shipped broken in 2.3.0 and never detected.

The Dockerfile copied `setup.py` but **not `pyproject.toml`**:

```dockerfile
COPY epub2tts_edge/ ./epub2tts_edge/
COPY setup.py .
COPY README.md .
RUN pip install --no-cache-dir -e .
```

With `pyproject.toml` absent from the build context, setuptools falls back to
`setup.py`, which declares only a name and packages:

```python
setup(name="audiobookify", packages=find_packages())
```

No `entry_points`. So `pip install -e .` created **no console scripts**, and the
image's final instruction — `ENTRYPOINT ["audiobookify"]` — referenced a binary
that did not exist. Every documented `docker run` invocation in the README would
fail immediately.

Reproduced by replicating the exact `COPY` set and installing into a clean venv:

```
=== console scripts from DOCKER context (setup.py only) ===
>>> NONE — ENTRYPOINT ["audiobookify"] WILL FAIL <<<

=== control: same install from repo root (has pyproject.toml) ===
abfy  abfy-tui  audiobookify  audiobookify-tui
```

**Why CI missed it:** the `docker` job ran `docker build` with `push: false` and
stopped there. Building an image proves the Dockerfile parses; it proves nothing
about whether the resulting image works.

**Fixed:** copy `pyproject.toml`, install non-editable, run as non-root, replace
the hardcoded `LABEL version="2.3.0"` with a build-arg OCI label. CI now runs
`docker run --rm audiobookify:ci --version` as a gate.

### 1.2 `--test-mode` crashed for installed users — `audio_generator.py`

**Severity: High.** Production code imported from the test suite.

```python
def enable_test_mode() -> None:
    from tests.mocks.tts_mock import MockTTSEngine   # not shipped in the wheel
```

The `tests` package is deliberately excluded from the wheel
(`[tool.setuptools.packages.find] include = ["epub2tts_edge*"]`). Verified against
an installed wheel from a directory outside the source tree:

```
FAILS: ModuleNotFoundError: No module named 'tests'
```

This worked in development only because the repository root happened to be on
`sys.path`. The advertised `--test-mode` flag was unusable for anyone who
installed the package — the exact audience it was documented for.

**Fixed:** the mock now ships as `epub2tts_edge.testing`, with backwards-compatible
shims left in `tests/mocks/` so existing test imports still work. CI's wheel smoke
test now calls `enable_test_mode()` from a clean venv.

### 1.3 `IndexError` on chapters with no readable content — `audio_generator.py`

**Severity: Medium.** Latent crash on real-world input.

`read_book()` indexed the last element of two lists without checking emptiness:

```python
append_silence(filenames[-1], paragraphpause)   # empty if sent_tokenize() → []
...
append_silence(files[-1], 2000)                 # empty if chapter has no paragraphs
```

A whitespace-only paragraph tokenizes to an empty list; a chapter with no
paragraphs leaves `files` empty. Either crashes the conversion outright.

This is not hypothetical: `ROADMAP.md` lists "Empty chapter detection — flag /
auto-remove chapters with no meaningful content" as *unimplemented*, so empty
chapters reach `read_book()` by design. Chapter detection over TOC entries that
point at title pages or section dividers produces exactly this shape.

**Fixed:** empty paragraphs are skipped; empty chapters emit a short silent
placeholder segment. The placeholder matters beyond avoiding the crash —
`generate_metadata()` pairs `files[i]` with `chapter_titles[i]` positionally, so
silently *dropping* a segment would shift every subsequent chapter marker onto the
wrong title.

### 1.4 Documented install commands referenced non-existent extras — `README.md`

**Severity: Medium.** Every platform install path was affected.

The README instructed `pip install ".[tui]"` (three times, once per platform) and
`pip install -e ".[all]"`. Only a `dev` extra was defined. pip treats unknown
extras as a warning rather than an error, so users got a silently degraded install
plus a confusing message.

**Fixed:** `tui` and `all` extras are now defined in `pyproject.toml`, so the
documented commands resolve cleanly.

---

## Part 2: Code review — open findings

These are not fixed in this branch. They need design decisions, and several are
better done as focused follow-ups. Sequenced in [`uplift-plan.md`](./uplift-plan.md).

### 2.1 An event loop and thread pool are created per paragraph 🔴

**Impact: significant, on the hottest path in the product.**

`read_book()` calls, once per paragraph:

```python
asyncio.run(parallel_edgespeak(sentences, speakers, filenames, ...))
```

and `parallel_edgespeak()` in turn does:

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
```

So for a 300-paragraph book, audiobookify creates and tears down **300 event loops
and 300 thread pools**. Worse, each `asyncio.run()` is a hard synchronisation
barrier: all sentences in paragraph *N* must finish before paragraph *N+1* starts.

The practical effect is that the advertised parallelism is bounded by *sentences
per paragraph*, not by `max_concurrent`. A paragraph with two sentences gets
two-way concurrency and then stalls the pipeline while the slowest of the two
completes. Typical prose gives you far less throughput than the configured limit
of 5 suggests.

**Direction:** hoist the event loop and executor to the top of `read_book()` and
feed a single work queue spanning the whole chapter (or book), with the semaphore
providing the only concurrency limit. This is the highest-value performance change
available and is largely mechanical.

### 2.2 `clean_intermediate_files()` is dead code — and it is the fix for a known bug 🟠

`audio_generator.py:382` defines `clean_intermediate_files()`, with a docstring
stating it exists so "no stale files from previous jobs can be accidentally
reused." **Nothing calls it.** Verified across the whole repository.

This matters because the resume logic it was written to protect is still live:

```python
ptemp = str(out_path / f"pgraphs{pindex}.flac")
if os.path.isfile(ptemp):
    logger.debug("%s exists, skipping to next paragraph", ptemp)   # trusts the file
```

Paragraph audio is keyed only by index within a chapter. The documented workflow is
*export to text → **edit the text** → convert*. If a user interrupts a conversion,
edits the `.txt`, and re-runs, leftover `pgraphs{N}.flac` files are reused for
paragraphs whose content has changed — producing an audiobook with stale content
and no error.

This is the same class of bug as the one documented in
[`archive/job-isolation-plan.md`](./archive/job-isolation-plan.md); the guard was
written and then never wired up.

**Direction:** call it at the start of a non-resume run, and key intermediate files
by a content hash rather than a bare index.

### 2.3 `make_m4b()` transcodes the entire audiobook twice 🟠

Two sequential full passes over the audio:

1. Concatenate all chapters → **FLAC inside an MP4 container** (`outputm4a`)
2. Read that back → transcode to AAC with metadata (`outputm4b`)

For a 10-hour audiobook the intermediate is multi-gigabyte, and the wall-clock cost
is roughly double what a single pass would take. FFmpeg can concat, apply the
metadata file, and encode to AAC in one invocation.

### 2.4 `make_m4b()` writes scratch files to the current working directory 🟠

When `output_dir` is `None`:

```python
filelist = "filelist.txt"
metadata_file = "FFMETADATAFILE"
```

Two consequences: it litters whatever directory the user happened to run from, and
two concurrent conversions started from the same directory will overwrite each
other's manifests — silently producing a corrupted audiobook rather than an error.
Parallel job processing is on the roadmap, which makes this a latent blocker.

Relatedly, `make_m4b()` unconditionally `os.remove()`s all input segments at the
end. If the second ffmpeg pass fails, the user loses hours of generated audio with
no recovery path.

### 2.5 Importing the library eagerly loads the entire TUI 🟡

`__init__.py` does `from .tui import AudiobookifyApp` at module scope, so
`import epub2tts_edge` — and therefore every CLI invocation, including
`audiobookify --version` — imports Textual and builds the whole TUI app class.

Measured: ~608 ms to import the package, of which the TUI subtree is ~154 ms.

This also forces `textual` to be a hard runtime dependency for users who only ever
touch the CLI. Making it a lazy import (with `tui` becoming a genuine optional
extra) would cut startup meaningfully and shrink the default install.

### 2.6 53 mypy errors; `py.typed` declared but absent 🟡

`mypy` has been configured and installed in CI since coverage was added, but the
lint job **never invoked it**. Current state:

| File | Errors |
|------|--------|
| `chapter_detector.py` | 11 |
| `epub2tts_edge.py` | 8 |
| `core/pipeline.py` | 7 |
| `audio_generator.py` | 7 |
| *(11 more files)* | 20 |

By category: `arg-type` (14), `attr-defined` (10), `union-attr` (5), `call-arg` (5).

Several look like real defects rather than annotation noise, e.g.:

- `core/pipeline.py:469` — `Argument "job" to "PipelineResult" has incompatible
  type "Job | None"; expected "Job"`
- `epub2tts_edge.py:262` — `Item "None" of "list[str] | str | None" has no
  attribute "__iter__"`
- `tui/app.py:670` — `"ChapterPreviewState" has no attribute "epub_path"`

The last one in particular is an attribute access that cannot succeed.

Separately, `pyproject.toml` declares `package-data = {epub2tts_edge = ["py.typed"]}`
but **the file does not exist**, so the marker is absent from the wheel and
downstream consumers get no type information regardless. Create it only once the
baseline is clean — shipping `py.typed` while 53 errors stand would export broken
types to consumers.

CI now runs mypy as non-blocking. It should become blocking once the baseline is
green.

### 2.7 Test coverage is inverted relative to risk 🟠

558 tests sounds strong. Coverage tells a different story: **44.93% overall**, and
the distribution is the problem.

| Module | Statements | Coverage |
|--------|-----------:|---------:|
| `tui/app.py` | 1003 | **9.20%** |
| `epub2tts_edge.py` (CLI) | 553 | **13.88%** |
| `audio_generator.py` | 303 | **21.77%** |
| `tui/panels/file_panel.py` | 215 | 25.08% |
| `tui/panels/preview_panel.py` | 463 | 28.82% |
| `chapter_detector.py` | 671 | 49.95% |
| `core/pipeline.py` | 205 | 55.02% |
| `config.py` | 104 | 95.31% |
| `core/profiles.py` | 28 | 100.00% |

*(Measured without ffmpeg present, which suppresses `audio_generator.py` somewhat;
with ffmpeg it is higher, but the CLI and TUI figures are unaffected.)*

The three largest and most user-facing modules are the three least tested. Tests
have accumulated where they are easy to write — pure functions with dataclass
configs — and thinned out exactly where behaviour is complex and regressions are
expensive.

`CONTRIBUTING.md` describes this as "558 tests, good coverage" and marks test
coverage as a *completed* high-priority item. That should be corrected; it
discourages precisely the contributions the project most needs.

### 2.8 Two modules are large enough to resist change 🟡

`tui/app.py` (2,055 lines) and `chapter_detector.py` (1,384 lines) are the two
biggest units. The v2.5.0 refactor did excellent work bringing `tui.py` down from
4,277 lines, but `app.py` remains a 1,000-statement class at 9% coverage —
the combination that makes changes risky. `chapter_detector.py` bundles NCX
parsing, NAV parsing, heading extraction, merge strategy, and five hierarchy
renderers in one file; those are separable along clean seams.

### 2.9 Smaller items

- **Fixed-name intermediates** (`sntnc0.mp3`, `pgraphs{N}.flac`) are only safe
  because of job-directory isolation. That invariant is documented in a docstring
  but not enforced anywhere in code.
- **`_is_auth_or_ssl_error()` matches on substrings** of stringified exceptions
  (`"401"`, `"ssl"`). Fragile: a sentence containing "401" in an unrelated error
  message would trigger the auth-error path and a 30-second cooldown.
- **pydub emits a `RuntimeWarning` on every invocation** when ffmpeg is missing,
  including for `--version` and `--help`. A preflight check with an actionable
  message would be a better first-run experience; `errors.py` already defines
  `DependencyError` for exactly this and it is underused.

---

## Part 3: DevOps, release & deployment review

This was the weakest area of the project and received the most attention.

### 3.1 There was no release process at all 🔴

Verified directly against GitHub and PyPI:

| Signal | State before this review |
|--------|--------------------------|
| Git tags | **none** |
| GitHub Releases | **none** |
| Latest PyPI version | **2.3.0**, published 2025-12-03 |
| Repository version | 2.5.0 |
| Release automation | **none** |

Two full minor releases of work — the entire v2.5.0 architecture refactor, the TUI
module extraction, processing profiles, output naming, job management, and the
whole testing infrastructure — **exist only in git**. Every user who followed the
README's `pipx install audiobookify` got 2.3.0.

Version identity was scattered and inconsistent: `pyproject.toml` said 2.5.0, the
Dockerfile label said 2.3.0, `CHANGELOG.md`'s last released section was 2.3.0 (with
2.4.0 and 2.5.0 missing entirely), and `ROADMAP.md` listed 2.4.0 and 2.5.0 in a
"Version History" table with release dates for releases that never happened. There
was no `__version__` attribute and no `--version` flag, so a user could not
determine what they were running.

**Implemented:** `release.yml`, driven by `v*` tags. It refuses to publish unless
the tag matches `pyproject.toml` *and* `CHANGELOG.md` has a matching section, then
builds, smoke-tests the wheel in a clean venv, publishes to PyPI via **Trusted
Publishing** (OIDC — no long-lived token in repository secrets), pushes multi-arch
images to GHCR, and cuts a GitHub Release with notes extracted from the changelog.
`--version` and `__version__` now exist, sourced from installed metadata.

> **Action required before the first automated release:** configure PyPI Trusted
> Publishing and create the `pypi` environment. Steps are in `CONTRIBUTING.md`.

### 3.2 CI called a live third-party API on every push 🔴

`tests/test_tts_connectivity.py` makes real network requests to
`speech.platform.bing.com`. It is skippable via `SKIP_TTS_TESTS`, but **CI never
set it**. Every push and PR hit Microsoft's production speech endpoint across all
six matrix jobs.

Two problems. Contributors' PRs would go red for reasons entirely outside their
control — a Microsoft outage, a DRM handshake change, rate limiting. And the
project was issuing unauthenticated automated traffic to an undocumented endpoint
on every commit.

The `integration` and `slow` markers were applied but do nothing on their own;
markers only filter when selected with `-m`.

**Implemented:** `SKIP_TTS_TESTS=1` is set workflow-wide. The live checks moved to
`tts-canary.yml`, which runs weekly, and **opens a GitHub issue when it fails** —
turning the project's single biggest external dependency from an invisible risk
into a monitored one.

### 3.3 CI validated that artifacts build, never that they work 🔴

This is the root cause of both §1.1 and §1.2, and the most important structural
lesson in this review.

- `docker build` ran; `docker run` never did → a broken entrypoint shipped for two
  minor versions
- `python -m build` and `twine check` ran; the wheel was never installed → a
  `ModuleNotFoundError` shipped in the advertised test-mode flag

**Implemented:** both jobs now execute their artifacts. The Docker job runs
`--version` and `--help` against the built image; the build job installs the wheel
into a clean venv, runs the CLI, and calls `enable_test_mode()`. Each of these
gates would have caught its corresponding bug on the commit that introduced it.

### 3.4 Configured quality gates that never ran 🟠

| Gate | Configured? | Ran? |
|------|-------------|------|
| ruff check | ✅ | ✅ |
| ruff format | ✅ | ⚠️ `continue-on-error: true` |
| mypy | installed in the lint job | ❌ never invoked |
| bandit | in `.pre-commit-config.yaml` and `pyproject.toml` | ❌ not in CI |

The `continue-on-error` on formatting is worth a note, because the reason it was
there turned out to be benign: **all 75 Python files are correctly formatted.** The
8 files that `ruff format --check .` flagged are all *Markdown* — ruff ≥0.16
reformats fenced code blocks in docs. The fix is to scope the check to Python
sources, which is now done, and drop `continue-on-error`.

Bandit surfaced two high-severity findings, both MD5 used for short-ID generation
rather than security. Fixed by declaring `usedforsecurity=False`, which is both
accurate and clears the gate. CI now runs bandit at medium-and-above.

### 3.5 Supply chain & workflow hygiene 🟡

Addressed in this branch:

- No `permissions:` block → workflows ran with the default token scope. Now
  `contents: read` by default, elevated per-job only where needed.
- No `concurrency:` group → superseded pushes kept running. Now cancels in-flight.
- No `workflow_dispatch` → no way to trigger a run manually.
- CI triggered on a `develop` branch that does not exist.
- Codecov v4 without a token (rate-limited/flaky for private uploads).
- No NLTK data caching — re-downloaded on every job.
- Python 3.13 absent from the matrix despite `audioop-lts` being declared
  specifically for it, so the 3.13 code path was never exercised.
- No dependency update automation. Dependabot now configured for pip, Actions, and
  Docker, with `edge-tts` explicitly excluded — it is deliberately pinned `<7.1.0`
  and must only be bumped after the canary passes.

Still open: **GitHub Actions are referenced by mutable tags** (`@v4`, `@v5`) rather
than commit SHAs. For a project that publishes to PyPI, pinning the release
workflow's actions by SHA is worth doing.

### 3.6 Dependency declarations had three sources of truth 🟡

`pyproject.toml`, `requirements.txt`, and `requirements-dev.txt` all declared
dependencies, and they had already drifted: `requirements-dev.txt` was missing
`pre-commit` and `bandit`, and pinned `ruff>=0.1.0` against `pyproject`'s
`>=0.8.0`.

`requirements-dev.txt` now delegates to `-e .[dev]`. `requirements.txt` must stay
(the Dockerfile installs it as a separate layer for build caching), so
`scripts/check_requirements_sync.py` enforces that it matches
`[project.dependencies]`, and CI runs it.

---

## Part 4: Public-facing surfaces

### 4.1 README

Good in substance — thorough option tables, per-platform install sections, worked
examples for every feature. The issues were accuracy and framing:

- Documented extras that did not exist (§1.4) — **fixed**
- No status badges (CI, PyPI, Python versions, licence) — **added**
- The cloud dependency was mentioned only obliquely. For a tool that transmits the
  **full text of every book you convert** to Microsoft, that belongs above the
  fold, not implied by "cloud-based TTS" — **added as a callout**
- The "Documentation" section led with `CLAUDE.md`, an AI-assistant context file,
  as the first item a user sees — **split into user-facing and contributor-facing**
- Feature sections are organised by *version introduced* ("New in v2.3.0", "New in
  v2.2.0", "New in v2.1.0"). This is changelog structure, not documentation
  structure — a new user does not care which release added silence trimming. It
  also decays: the v2.4.0 and v2.5.0 features are absent entirely, so the README
  silently describes an older product. **Still open** — see the uplift plan.

### 4.2 Repository root

The root presented as a workspace rather than a product. `PLAN.md` (an internal
debugging plan for a fixed bug), `CODE_REVIEW.md` (a stale 2.3.0 review),
`CLAUDE.md`, `claudedocs/`, and `.serena/` were all top-level.

Design docs moved to `docs/`; completed working documents archived under
`docs/archive/`. `CLAUDE.md` stays at the root by convention.

`.serena/memories/` remains tracked. Those are AI session notes — worth deciding
deliberately whether they belong in version control.

### 4.3 Missing community health files

No `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue templates, PR template, or
`CODEOWNERS`. Issue and PR templates and `SECURITY.md` have been added. The bug
template requires version, OS, Python, ffmpeg and `edge-tts` versions up front —
the four things nearly every real issue here will hinge on.

### 4.4 Package naming and identity 🟡

The distribution is `audiobookify`; the import package is `epub2tts_edge`. Every
programmatic user writes `from epub2tts_edge import ...`, and every internal
module path carries the name of the upstream fork.

Beyond the confusion, the name encodes two things that are no longer true: the
tool handles MOBI/AZW as well as EPUB, and the roadmap explicitly plans non-Edge
TTS engines. This is a real public-API decision with a breaking-change cost, and
it gets harder the longer it waits. Discussed in the uplift plan.

---

## Part 5: Contributor experience

**A new contributor's first `pytest` run produced 13 failures.** Nine from missing
ffmpeg (with a raw `FileNotFoundError: 'ffprobe'` and no explanation), four from
live network calls. Meanwhile `CONTRIBUTING.md` promised tests "use mock TTS
automatically - no network calls."

Fixed: ffmpeg-dependent tests carry a `requires_ffmpeg` marker and skip with an
explanatory reason; the TTS tests are opt-in. A clean checkout with no ffmpeg and
no network now yields:

```
542 passed, 16 skipped
```

Also corrected in `CONTRIBUTING.md`: the documented project structure still
described a `tui.py` that has not existed since v2.4.0 and omitted `core/`,
`job_manager.py`, `config.py`, and `errors.py`; setup instructions did not mention
the `[dev]` extra or pre-commit; and there was no documented release process.

Still open: **there is no `CODE_OF_CONDUCT.md`**, and no `good first issue`
labelling — the issue tracker is currently empty, which is itself a signal that the
project has not yet invited outside contribution.

---

## Part 6: Strategic assessment

### 6.1 The dependency risk is the whole ballgame 🔴

Audiobookify's core value — free, high-quality neural TTS — comes entirely from
`edge-tts`, an **unofficial client for an undocumented Microsoft endpoint that is
not a public API**. Microsoft offers no compatibility guarantee, no deprecation
policy, and no obligation to keep serving unauthenticated clients.

The project already has direct evidence of this fragility. From `pyproject.toml`:

```toml
"edge-tts>=6.1.0,<7.1.0",  # Pin below 7.1.0 due to SSL fingerprinting issues
```

and from `audio_generator.py`, a dedicated code path for auth failures with a
30-second cooldown and a user-facing message explaining the version incompatibility.
Significant engineering has already gone into working around upstream instability.

**If Microsoft changes that endpoint, every version of audiobookify ever shipped
stops working simultaneously.** There is no abstraction layer, no second backend,
and no graceful degradation. `run_edgespeak()` is called directly from
`read_book()`.

The mitigating asset is already in the codebase: `MockTTSEngine` is a working
second implementation of the synthesis interface. It demonstrates that the seam
exists — it just has not been named. Formalising a `TTSEngine` protocol
(`generate`/`generate_sync`, already the mock's shape) and adding one local backend
(Piper is the obvious candidate — small, fast, permissively licensed, no network)
would convert an existential single point of failure into a configuration choice.
This is the single highest-leverage architectural change available, and it also
unlocks the "offline mode" that heads the roadmap's Known Limitations.

The weekly TTS canary added in this branch does not fix the risk, but it does mean
the project finds out from a GitHub issue rather than from user bug reports.

### 6.2 Feature velocity has outrun delivery capability 🟠

The changelog shows v2.0.0 through v2.3.0 shipped within a single month, and
v2.4.0/v2.5.0 shortly after — an enormous amount of functionality. In the same
period, the release pipeline, the Docker image, and the packaging correctness all
went unmaintained, and the last thing users could actually install was 2.3.0.

This is a recognisable and correctable pattern: the work that is visible and
satisfying (features) crowded out the work that is invisible until it fails
(delivery). The imbalance shows up quantitatively too — 558 tests, but 9% coverage
on the largest module.

**The recommendation is to spend one full cycle adding no user-facing features**,
and instead: get a release out, fix the type baseline, invert the coverage
distribution, and land the TTS abstraction. The uplift plan sequences this.

### 6.3 Documentation claims exceed reality 🟠

A pattern worth naming on its own, because it compounds:

- `ROADMAP.md` lists 2.4.0 and 2.5.0 in a Version History table with dates —
  neither was ever tagged or published
- `CONTRIBUTING.md` marks test coverage as complete with "good coverage" — 45%,
  with the critical path in the teens
- `CONTRIBUTING.md` and `CLAUDE.md` promised no network calls in tests — four made
  live API calls
- README documented install commands that could not work, and `docker run`
  invocations against an image that could not start

Individually minor. Together they mean **a reader cannot trust the project's own
description of itself** — which is the single most expensive thing to lose when
trying to attract users or contributors. Worth adopting as a working principle:
documentation asserts only what CI verifies. The wheel smoke test, image smoke
test, and requirements-sync check added here are the first instances of that.

### 6.4 The CLI's core interaction model is surprising 🟡

The primary workflow overloads one command on file extension:

```bash
audiobookify mybook.epub    # → writes mybook.txt
audiobookify mybook.txt     # → writes mybook.m4b
```

Same command, entirely different operation, distinguished only by the input's
extension. There is no way to express "export and convert in one go," and the
two-step nature is easy to miss. Layered on this is a single flat argparse
namespace with roughly 50 flags, many mutually exclusive or only meaningful in
combination.

The intent behind two steps is sound and worth keeping — letting users edit chapter
text before spending an hour of synthesis is a genuine feature. But it should be
explicit rather than inferred. Subcommands (`abfy export`, `abfy convert`,
`abfy run`, `abfy tui`, `abfy voices`) would make the model self-describing and
let each subcommand carry only its own flags. This is a breaking change and should
ride along with the naming decision in §4.4.

### 6.5 What the project has going for it

Worth stating plainly, because the above is heavily weighted toward problems:

- **The module decomposition is genuinely good.** Config dataclasses with
  validation, an enum-based detection strategy, clean `core/` extraction, an
  EventBus decoupling processing from UI. The v2.5.0 refactor was real work,
  well executed.
- **The test suite, whatever its distribution, exists and is fast** — 542 tests in
  ~15 seconds, fully offline. That is a strong foundation to build coverage on.
- **`MockTTSEngine` was the right idea**, and is the seam the whole engine
  abstraction can be built on.
- **Feature depth is a real moat.** Chapter detection across NCX/NAV/headings,
  multi-voice dialogue attribution, pronunciation dictionaries, normalisation, and
  a TUI is well beyond what comparable tools offer.
- **The problems found here are almost entirely in the delivery layer, not the
  product.** That is the cheaper kind of problem to have, and most of it is now
  fixed.

---

## Appendix: metrics

```
Package source             15,424 lines across 43 modules
Test suite                  9,051 lines across 30 files, 558 tests
Test result (clean env)    542 passed, 16 skipped, 0 failed  (no network, no ffmpeg)
Test wall time             ~15 s
Coverage                   44.93% overall (branch coverage enabled)
ruff check                 clean
ruff format                clean (75 Python files)
mypy                       53 errors across 15 files
bandit                     0 high, 0 medium, 37 low (subprocess notices)
Package import time        ~608 ms (~154 ms of it the eagerly-imported TUI)
Largest modules            tui/app.py 2055 · chapter_detector.py 1384 · epub2tts_edge.py 1303
```

---

## Where to go next

See [`uplift-plan.md`](./uplift-plan.md) for the sequenced execution plan covering
the product, the development infrastructure, the contribution pipeline, and
deployment.

See [`dependency-reduction-plan.md`](./dependency-reduction-plan.md) for the
per-dependency analysis of what can be brought in-house — ~56% of the third-party
code is removable, but vendoring is the wrong mechanism for almost all of it.
