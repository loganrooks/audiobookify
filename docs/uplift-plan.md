# Audiobookify Uplift Plan

**Companion to:** [`project-review-2026-07.md`](./project-review-2026-07.md) ·
[`dependency-reduction-plan.md`](./dependency-reduction-plan.md)
**Horizon:** ~6 months, five milestones
**Status:** M0 and M1 complete (v2.6.0 shipped 2026-07-24); M2–M4 proposed

This plan covers four tracks that need to move together:

| Track | What it means |
|-------|---------------|
| 🏗️ **Product** | The tool itself — correctness, performance, architecture |
| 🔧 **Development infrastructure** | What makes changing the code safe and fast |
| 🤝 **Contribution** | What makes it possible for someone other than the maintainer to help |
| 🚀 **Deployment** | How working software reaches users |

## Guiding principles

Three rules that fall directly out of the review's findings. If nothing else
survives from this plan, these should.

1. **Documentation asserts only what CI verifies.** Every one of the four critical
   defects was a gap between what a document promised and what the artifact did.
   When you write a claim in the README, add the check that keeps it true.
2. **Gates that do not run are not gates.** mypy was installed for months without
   ever being invoked; `ruff format` was `continue-on-error`; `docker build` never
   ran the image. A configured tool that never fails the build is worse than no
   tool, because it reads as coverage.
3. **Ship the smallest thing that reaches a user.** Two minor releases of good work
   sat unreleased. Prefer a tagged 2.6.0 that users can install over a perfect
   2.7.0 that stays in git.

---

## M0 — Stop the bleeding ✅ *(complete)*

Everything in this milestone is implemented and verified in this branch.

### 🚀 Deployment
- [x] Fix the Docker image — copy `pyproject.toml` so the entrypoint exists
- [x] Add tag-driven `release.yml` — PyPI via Trusted Publishing, GHCR multi-arch, GitHub Release
- [x] Gate releases on tag ↔ `pyproject.toml` ↔ `CHANGELOG.md` agreement
- [x] Add `--version` and `__version__`
- [x] Backfill missing 2.4.0 / 2.5.0 changelog entries

### 🏗️ Product
- [x] Fix `--test-mode` `ModuleNotFoundError` — ship the mock as `epub2tts_edge.testing`
- [x] Fix `IndexError` on chapters with no readable content
- [x] Declare `usedforsecurity=False` on the two non-cryptographic MD5 helpers

### 🔧 Development infrastructure
- [x] Smoke-test built artifacts in CI (run the wheel, run the image)
- [x] Stop CI calling Microsoft's TTS service; move it to a weekly canary that files an issue
- [x] Actually run mypy (non-blocking) and bandit
- [x] Enforce `ruff format`, scoped to Python sources
- [x] Least-privilege `permissions`, `concurrency`, `workflow_dispatch`, Python 3.13, NLTK caching
- [x] Dependabot for pip / Actions / Docker, with `edge-tts` excluded
- [x] `scripts/check_requirements_sync.py` to prevent dependency drift

### 🤝 Contribution
- [x] `requires_ffmpeg` marker — clean checkout now gives `542 passed, 16 skipped`
- [x] Issue templates, PR template, `SECURITY.md`
- [x] Correct the stale project structure and setup steps in `CONTRIBUTING.md`
- [x] Document the release process
- [x] Move internal docs to `docs/`, archive completed working documents

### Verification still outstanding

See [`handoff.md`](./handoff.md) for the full list. The two that matter:
- [ ] Build and **run** the Docker image (blocked in the review environment by
      Docker Hub egress denial — the fix is verified at the packaging layer only)
- [ ] One real end-to-end conversion with live Edge TTS (blocked by gateway policy
      denial on `speech.platform.bing.com`); everything so far ran on mock TTS

### Remaining manual step

- [ ] **Configure PyPI Trusted Publishing** and create the `pypi` environment
      (owner `loganrooks`, repo `audiobookify`, workflow `release.yml`).
      Nothing can be published until this is done — steps are in `CONTRIBUTING.md`.

---

## M1 — Ship a release ~2 weeks

**Goal: a user can `pip install audiobookifier` and get the 2.5.0 work.** This is the
highest-value milestone in the plan and the cheapest. Everything since 2.3.0 is
already written; it just needs to reach people.

### 🚀 Deployment
- [ ] Complete Trusted Publishing setup
- [ ] Tag `v2.6.0` and let the pipeline run end to end
  - *2.6.0 rather than 2.5.0: the M0 fixes are user-visible behaviour changes, and
    2.5.0 is already claimed by the ROADMAP's history table.*
- [ ] Verify the published artifacts by installing from PyPI and pulling from GHCR
      in a clean environment — do not trust the pipeline's own smoke tests for the
      first run
- [ ] Add the GHCR image to the README's Docker section

### 🏗️ Product
- [ ] Restructure the README's feature sections **by capability, not by version**.
      "New in v2.1.0 / v2.2.0 / v2.3.0" is changelog structure leaking into
      documentation, and it has already gone stale — v2.4.0 and v2.5.0 features are
      absent, so the README describes an older product than the one shipped.
- [ ] Document v2.4.0/v2.5.0 features that the README never covered (processing
      profiles, output naming templates, job management, the tabbed settings panel)

### 🔧 Development infrastructure
- [ ] Pin `release.yml`'s actions by commit SHA — it is the workflow with
      publish permissions and deserves the strongest supply-chain posture

**Exit criteria:** `pipx install audiobookifier` yields the current feature set;
`docker run ghcr.io/loganrooks/audiobookify --version` works; README describes what
users actually get.

---

## M2 — Make the critical path safe to change ~6 weeks

**Goal: invert the coverage/risk inversion, and get the type baseline clean.**
Every item after this milestone depends on being able to change
`audio_generator.py` and `epub2tts_edge.py` without fear.

### 🔧 Development infrastructure
- [ ] **Raise CLI (`epub2tts_edge.py`) coverage from 14% → 60%+.** 472 of its 553
      statements are uncovered — the single biggest gap in the project. Argument
      parsing and dispatch are highly testable and almost entirely untested.
- [ ] **Raise `tui/app.py` coverage from 9%.** 887 uncovered statements in a
      1,000-statement class. Even 40% would materially de-risk changes here.
- [ ] Cover the remaining gaps in `audio_generator.py` (68.61%) — mainly the
      `run_edgespeak()` retry/cooldown paths and `make_m4b()` error handling.
      *Note: an earlier review pass reported this module at 22%; that was measured
      without ffmpeg, which skips the tests that exercise it.*
- [ ] Add coverage floors to CI (`--cov-fail-under`), ratcheting upward — set the
      initial floor at the current number so it can only improve
- [ ] Drop the vestigial `setuptools` runtime dependency (nothing imports it)
- [ ] Replace `nltk` (154k LOC for one function) with an internal sentence splitter,
      behind a golden corpus — also removes the runtime `punkt` download from the
      Dockerfile, CI, and first-run UX. See
      [dependency-reduction-plan.md](./dependency-reduction-plan.md)
- [ ] Replace `EbookLib` with an internal EPUB reader — removes AGPL-3.0 code from a
      GPL-3.0 project; ~60% of the parsing already exists in `TOCParser` and
      `get_epub_cover()`
- [ ] Clear the **53 mypy errors**, then flip the mypy step to blocking
- [ ] Create `epub2tts_edge/py.typed` — *only after* the baseline is green, since
      `pyproject.toml` already declares it and shipping it early would export
      broken types to consumers

### 🏗️ Product
Fix the real defects that mypy is already pointing at:
- [ ] `core/pipeline.py:469` — `Job | None` passed where `Job` is required
- [ ] `epub2tts_edge.py:262` — iterating a value that may be `None`
- [ ] `tui/app.py:670` — `ChapterPreviewState` has no attribute `epub_path`
- [ ] **Wire up `clean_intermediate_files()`** — it is dead code that was written
      to prevent stale-audio reuse, and the bug it guards against is still live
- [ ] Key intermediate audio files by content hash rather than bare index, so
      editing the `.txt` between runs cannot silently reuse stale audio
- [ ] Give `make_m4b()` a real temp directory instead of writing `filelist.txt` and
      `FFMETADATAFILE` into the current working directory
- [ ] Stop `make_m4b()` deleting source segments before the output is confirmed good
- [ ] Harden XML parsing against entity expansion with a shared
      `etree.XMLParser(resolve_entities=False, no_network=True)`. XXE is already
      blocked by lxml defaults (verified), so this is defence in depth rather than
      an open hole — but it needs a corpus test first, since real EPUBs use XHTML
      entities like `&nbsp;`. See review §2.10.

**Exit criteria:** mypy blocking and green; coverage floor enforced; the resume
path cannot serve stale audio.

---

## M3 — Break the single point of failure ~8 weeks

**Goal: audiobookify survives Microsoft changing or withdrawing the Edge TTS
endpoint.** This is the most important architectural work in the plan — see
[review §6.1](./project-review-2026-07.md#61-the-dependency-risk-is-the-whole-ballgame).

### 🏗️ Product
- [ ] **Define a `TTSEngine` protocol.** The interface already exists implicitly —
      `MockTTSEngine.generate()` / `.generate_sync()` is a working second
      implementation. Name it, and make `run_edgespeak()` one conforming backend
      rather than a hardcoded call.
- [ ] **Add a local backend (Piper).** Small, fast, permissively licensed, fully
      offline. This simultaneously closes the top entry in the roadmap's Known
      Limitations ("Edge TTS requires internet — no offline mode currently").
- [ ] `--engine {edge,piper}` on the CLI and in the settings panel
- [ ] Fall back gracefully with a clear message when the selected engine is
      unavailable, rather than a raw exception
- [ ] Replace `_is_auth_or_ssl_error()`'s substring matching on stringified
      exceptions with typed exceptions from the engine layer

### 🔧 Dependency reduction *(detail in [dependency-reduction-plan.md](./dependency-reduction-plan.md))*
- [ ] Replace `pydub` + `mutagen` with direct ffmpeg calls — do this **with** the
      performance items below, since they touch the same code. Removes ~23k LOC and
      the `audioop-lts` backport that exists only because pydub imports the
      `audioop` module removed in Python 3.13.
- [ ] Move `mobi` to an optional `[kindle]` extra (its import is already guarded)

### 🏗️ Performance *(unblocked by the engine abstraction)*
- [ ] **Hoist the event loop and thread pool out of the per-paragraph loop.**
      Currently one `asyncio.run()` and one `ThreadPoolExecutor` are created *per
      paragraph*, and each acts as a full synchronisation barrier — so real
      concurrency is bounded by sentences-per-paragraph, not by `max_concurrent`.
      Feed a single queue for the whole chapter instead.
- [ ] **Collapse `make_m4b()`'s two full transcode passes into one.** Today it
      writes a multi-gigabyte FLAC-in-MP4 intermediate and then re-encodes it to
      AAC; ffmpeg can concat, apply metadata, and encode in a single invocation.
- [ ] Make the TUI import lazy so `audiobookify --version` does not load Textual
      (~154 ms of a ~608 ms import), and make `textual` a genuine optional extra

**Exit criteria:** a full conversion completes with no network access; measured
throughput improvement on a real multi-chapter book.

---

## M4 — Grow the project ~12 weeks

**Goal: audiobookify becomes something other people can contribute to and build on.**

### 🤝 Contribution
- [ ] Add `CODE_OF_CONDUCT.md` and `CODEOWNERS`
- [ ] File the open findings from the review as tracked issues, and label the
      approachable ones `good first issue` — the tracker is currently empty, which
      reads to a prospective contributor as "contributions not expected"
- [ ] Publish the architecture docs as a rendered site (MkDocs or similar) rather
      than raw Markdown in `docs/`
- [ ] Decide deliberately whether `.serena/memories/` belongs in version control

### 🏗️ Product — the two breaking changes, taken together
Both of these are public-API decisions that get more expensive the longer they
wait. Doing them in one major release (`3.0.0`) means users absorb one migration
rather than two.

- [ ] **Rename the import package `epub2tts_edge` → `audiobookify`.** The current
      name is the upstream fork's, and it encodes two things that are no longer
      true: the tool handles MOBI/AZW as well as EPUB, and after M3 it is no longer
      Edge-only. Ship a deprecation shim that re-exports from the old path with a
      `DeprecationWarning` for at least one minor cycle.
- [ ] **Move the CLI to subcommands** — `abfy export`, `abfy convert`, `abfy run`,
      `abfy tui`, `abfy voices`. The current model overloads a single command on
      file extension (`audiobookify book.epub` exports text; `audiobookify book.txt`
      synthesises audio), which is genuinely surprising, and it funnels ~50 flags
      through one flat namespace. Keep the two-step workflow — letting users edit
      chapter text before an hour of synthesis is a real feature — but make it
      explicit rather than inferred. Add `abfy run` for the one-shot path.
      Keep the current invocation working, with a deprecation warning.

### 🔧 Development infrastructure
- [ ] Split `chapter_detector.py` (1,384 lines) along its existing seams: NCX
      parsing, NAV parsing, heading extraction, merge strategy, hierarchy rendering
- [ ] Continue reducing `tui/app.py` (2,055 lines, 9% coverage) — the size and the
      coverage together are what make it risky
- [ ] Add golden-file regression tests for chapter detection across a corpus of
      real-world EPUB structures

---

## Sequencing rationale

**Why release before fixing anything else (M1 before M2).** The work is already
done and sitting in git. Every week it stays unreleased is a week users run 2.3.0
with a broken Docker image. It is also the cheapest possible validation that the
new pipeline works — better to discover a release bug now, on a release that is
mostly already-tested code, than during a release that also carries an
architectural change.

**Why coverage before the engine abstraction (M2 before M3).** M3 restructures the
hottest code in the project — `read_book()`, `run_edgespeak()`, `make_m4b()` — which
currently sits at 22% coverage. Refactoring that without tests is how you ship a
regression that only shows up three hours into someone's audiobook. Build the net
first.

**Why the breaking changes go last and go together.** Renaming the package and
restructuring the CLI are both one-time migration costs for users. Bundling them
into a single `3.0.0` halves the disruption. They also both depend on M3: the
rename is only fully justified once the tool is no longer Edge-specific.

**What is deliberately not here.** The feature roadmap in
[`../ROADMAP.md`](../ROADMAP.md) — PDF support, GPU acceleration, web UI, mobile
companion — is untouched by this plan. That is the point of
[review §6.2](./project-review-2026-07.md#62-feature-velocity-has-outrun-delivery-capability):
the project's constraint right now is not a shortage of features. Resuming feature
work before M2 lands would recreate exactly the imbalance that produced the four
critical defects.

---

## Tracking

| Milestone | Focus | Effort | Status |
|-----------|-------|--------|--------|
| M0 | Stop the bleeding | — | ✅ Complete |
| M1 | Ship a release | ~2 weeks | ✅ Complete 2026-07-24 — v2.6.0 on PyPI (as `audiobookifier`), GHCR and GitHub Releases; exit criteria verified from clean installs |
| M2 | Make the critical path safe | ~6 weeks | Not started |
| M3 | Break the single point of failure | ~8 weeks | Not started |
| M4 | Grow the project | ~12 weeks | Not started |

Effort estimates assume part-time solo maintenance and are ranges, not commitments.
