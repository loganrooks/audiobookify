# Changelog

All notable changes to Audiobookify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Docker image was unusable.** `pyproject.toml` was never copied into the build
  context, so `pip install -e .` fell back to the minimal `setup.py`, which
  declares no `[project.scripts]`. The `audiobookify` console script was never
  created and `ENTRYPOINT ["audiobookify"]` could not resolve. CI only ran
  `docker build`, never `docker run`, so this was never caught.
- **`--test-mode` crashed for installed users.** `audio_generator.enable_test_mode()`
  imported `MockTTSEngine` from the `tests` package, which is not distributed in
  the wheel, raising `ModuleNotFoundError: No module named 'tests'`. The mock now
  ships as `epub2tts_edge.testing`.
- **`IndexError` on chapters with no readable content.** `read_book()` indexed
  `files[-1]` / `filenames[-1]` without checking for empty lists, so a chapter
  with no paragraphs (or a whitespace-only paragraph) crashed the conversion.
  Empty chapters now emit a silent placeholder segment, which also keeps segment
  count aligned with `chapter_titles` in `generate_metadata()`.
- Documented `pip install ".[tui]"` and `pip install -e ".[all]"` referenced
  extras that did not exist. Both are now defined in `pyproject.toml`.

### Added
- `--version` flag and `epub2tts_edge.__version__`, both sourced from installed
  package metadata.
- Tag-driven release pipeline (`.github/workflows/release.yml`): publishes to
  PyPI via Trusted Publishing, pushes multi-arch images to GHCR, and creates a
  GitHub Release with notes extracted from this changelog. Verifies the tag
  matches `pyproject.toml` and that a changelog entry exists before publishing.
- Weekly TTS canary (`.github/workflows/tts-canary.yml`) that exercises the live
  Edge TTS service and opens an issue when the integration breaks.
- `requires_ffmpeg` pytest marker; those tests now skip with a clear reason
  instead of failing with `FileNotFoundError` when ffmpeg is absent.
- `scripts/check_requirements_sync.py`, enforced in CI, to stop `requirements.txt`
  drifting from `[project.dependencies]`.
- Dependabot config, issue/PR templates, and `SECURITY.md`.
- Wheel and Docker smoke tests in CI that actually execute the built artifacts.

### Changed
- CI no longer calls Microsoft's TTS service. `SKIP_TTS_TESTS=1` is set for the
  whole workflow, so a Microsoft outage can no longer turn a contributor's PR red.
- CI runs `mypy` (non-blocking, pending backlog cleanup) and `bandit`, which were
  previously installed or configured but never executed.
- `ruff format --check` is now enforced instead of `continue-on-error`, scoped to
  Python sources (ruff >=0.16 also reformats Markdown code blocks).
- Added Python 3.13 to the test matrix, least-privilege `permissions`,
  `concurrency` cancellation, and `workflow_dispatch` to CI.
- Docker image now runs as a non-root user and uses OCI-standard labels with a
  build-arg version instead of a hardcoded, stale `2.3.0`.
- Internal design docs moved from `claudedocs/` to `docs/`; completed working
  documents archived under `docs/archive/`.

## [2.5.0] - 2025-12

### Added
- **Unified conversion pipeline** - `core/pipeline.py` with `ConversionPipeline`
  shared by both CLI and TUI
- **EventBus** - Decoupled pub-sub communication with 17 event types, plus
  `TUIEventAdapter` for thread-safe UI updates
- **Processing profiles** - 5 built-in presets (Quick Draft, High Quality,
  Audiobook, Accessibility) selectable from the Settings panel
- **Output naming templates** - Configurable `{author} - {title}.m4b` patterns
  with 6 presets plus custom templates
- **Job management** - `job_manager.py` for job tracking, persistence, and
  per-job directory isolation
- **Testing infrastructure** - 558 tests total
  - Mock TTS engine for fast, offline testing (no network calls)
  - `--test-mode` CLI flag for development/CI testing
  - Test mode APIs: `enable_test_mode()`, `disable_test_mode()`, `is_test_mode()`,
    `get_mock_engine()`
  - E2E workflow tests covering EPUB → text → audio → M4B (14 tests)
  - Core pipeline tests for `ConversionPipeline`, `PipelineConfig`,
    `PipelineResult` (29 tests)
  - Error handling tests for file errors, invalid formats, TTS failures (15 tests)
  - Test fixtures in `tests/fixtures/` for creating test EPUBs

### Fixed
- Type mismatch in `ConversionPipeline.export_text()`, which expected
  `ChapterNode` objects but received dicts from `detect_chapters()`
- Incorrect relative imports in the TUI app module

### Changed
- CI workflow gained coverage reporting (Codecov integration)
- Pipeline coverage improved from 22% to 60%

## [2.4.0] - 2025-12

### Added
- **TUI module extraction** - Split the `tui.py` monolith (4,277 → 1,995 lines,
  53% reduction) into `tui/panels/`, `tui/models/`, and `tui/screens/`
- **Range/batch selection** - Anchor-based range selection (Enter) and toggle
  mode (V)
- **Directory browser** - `DirectoryTree` modal for folder selection (📂, `b`)
- **Path autocomplete** - Tab completion in the directory input field
- **Settings panel redesign** - Tabbed settings (Voice, Audio, Chapters, Advanced)
- **Job queue improvements** - Multi-select, reordering, and batch operations
- **Preview chapter editing** - Merge/delete chapters with undo, inline title
  editing (`E`)

### Notes
- Neither 2.4.0 nor 2.5.0 was published to PyPI or tagged at the time. These
  entries were reconstructed from the git history and ROADMAP when the release
  pipeline was introduced.

## [2.3.0] - 2025-11-27

### Added
- **MOBI/AZW format support** - Parse Amazon Kindle ebook formats
  - MOBI, AZW, and AZW3 file support
  - Chapter detection from HTML headings in Kindle books
  - Metadata extraction (title, author, language, publisher)
  - Cover image extraction
  - `--preview` mode for MOBI/AZW files
- **New module** - `epub2tts_edge/mobi_parser.py`
  - `MobiParser` class for parsing Kindle files
  - `MobiBook` and `MobiChapter` dataclasses
  - `is_kindle_file()`, `is_mobi_file()`, `is_azw_file()` helper functions
- **Docker support** - Containerized deployment
  - `Dockerfile` for building the image
  - `docker-compose.yml` for easy usage
  - `.dockerignore` for optimized builds
- **Calibre plugin** - Integration with Calibre library
  - Convert books directly from Calibre
  - Preview chapters before conversion
  - Configurable voice, rate, and volume settings
  - Audio normalization and silence trimming options

### Dependencies
- Added `mobi` library for Kindle format parsing

## [2.2.0] - 2025-11-27

### Added
- **Audio normalization** - Consistent volume levels across all chapters
  - `--normalize` flag to enable normalization
  - `--normalize-target` to set target loudness (default: -16 dBFS)
  - `--normalize-method` to choose peak or RMS normalization
- **Silence detection and trimming** - Remove excessive pauses
  - `--trim-silence` flag to enable silence trimming
  - `--silence-thresh` to set silence threshold (default: -40 dBFS)
  - `--max-silence` to set maximum silence duration (default: 2000ms)
- **Custom pronunciation dictionary** - Correct mispronounced words
  - `--pronunciation` to specify dictionary file (JSON or text format)
  - `--pronunciation-case-sensitive` for case-sensitive matching
  - Support for word-boundary aware replacements
- **Multiple voice support** - Different voices for characters and narration
  - `--voice-mapping` to specify voice mapping JSON file
  - `--narrator-voice` to set narrator voice separately
  - Automatic dialogue detection and speaker attribution
- **Example configuration files** in `examples/` directory
  - `pronunciation.json` and `pronunciation.txt` templates
  - `voice_mapping.json` template
- **TUI integration** for all v2.2.0 features
  - Audio quality switches (normalize, trim silence)
  - Pronunciation and voice mapping file inputs

### Changed
- Updated documentation with v2.2.0 features

## [2.1.0] - 2025-11-27

### Added
- **Voice preview** - Listen to voice samples before converting
  - `--list-voices` to display all available voices
  - `--preview-voice VOICE` to generate a sample
- **Speech rate and volume control**
  - `--rate` to adjust speech speed (e.g., "+20%", "-10%")
  - `--volume` to adjust volume (e.g., "+50%", "-20%")
- **Chapter selection** - Convert only specific chapters
  - `--chapters` with flexible syntax: "3", "1-5", "1,3,5-7", "5-"
- **Pause/resume support** - Resume interrupted conversions
  - `--resume` to continue from saved state
  - `--no-resume` to start fresh
  - Automatic state saving on interruption (Ctrl+C)
- **TUI integration** for all v2.1.0 features
  - Voice selector with preview button
  - Rate and volume sliders
  - Chapter range input
  - Resume option

## [2.0.0] - 2025-11-27

### Added
- **Enhanced chapter detection**
  - EPUB2 NCX Table of Contents parsing
  - EPUB3 NAV document parsing
  - Multi-level heading detection (h1-h6)
  - `--detect` option with methods: toc, headings, combined, auto
  - Hierarchical chapter structure with ChapterNode tree
  - `--hierarchy` option with styles: flat, numbered, arrow, breadcrumb, indented
  - `--preview` mode to inspect chapters without converting
- **Batch processing**
  - Process entire folders of EPUB files
  - `--recursive` for subfolder scanning
  - Skip already-processed files
  - Resume interrupted batches
  - JSON report generation
  - `--output-dir` for custom output location
  - `--export-only` mode for text extraction only
- **Terminal UI (TUI)**
  - Interactive file browser
  - Settings panel for voice and detection options
  - Real-time progress display
  - Processing queue with status tracking
  - Log panel for detailed output
  - Keyboard shortcuts

### Changed
- Renamed CLI from `epub2tts-edge` to `audiobookify` (with `abfy` alias)
- Reorganized codebase into modular components

## [1.2.7] - 2024

### Notes
- Original epub2tts-edge features (forked from aedocw/epub2tts-edge)
- Basic EPUB to M4B conversion
- Microsoft Edge TTS integration
- Chapter markers in output

---

[Unreleased]: https://github.com/loganrooks/audiobookify/compare/v2.5.0...HEAD
[2.5.0]: https://github.com/loganrooks/audiobookify/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/loganrooks/audiobookify/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/loganrooks/audiobookify/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/loganrooks/audiobookify/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/loganrooks/audiobookify/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/loganrooks/audiobookify/releases/tag/v2.0.0
