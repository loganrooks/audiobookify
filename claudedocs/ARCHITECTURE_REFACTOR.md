# Architecture Refactoring Plan

## Overview

This document outlines the refactoring needed to make the codebase maintainable and extensible for future features.

## Current State

### What's Already Clean ✅

| Module | Purpose | Status |
|--------|---------|--------|
| `audio_generator.py` | TTS generation, M4B creation | ✅ Clean - core TTS logic |
| `chapter_detector.py` | Chapter detection from EPUB | ✅ Clean - pure detection |
| `content_filter.py` | Front/back matter filtering | ✅ Clean - pure filtering |
| `job_manager.py` | Job state persistence | ✅ Clean - pure state management |
| `config.py` | App configuration | ✅ Clean - pure config |

### Problem: epub2tts_edge.py Mixed Concerns

```
epub2tts_edge.py (1,200+ lines):
├── CLI argument parsing (main())
├── Export logic (export(), export_legacy(), export_mobi())
├── Cover extraction (get_epub_cover())
└── Legacy book processing (chap2text_epub())
```

The CLI code mixes UI concerns (arg parsing) with business logic (export).

### Problem: tui.py Monolith (4,500+ lines)

```
tui.py contains:
├── Data models (PreviewChapter, ChapterPreviewState, VoicePreviewStatus)
├── 7 Panel widgets (FilePanel, SettingsPanel, PreviewPanel, etc.)
├── 2 Item widgets (EPUBFileItem, ChapterPreviewItem)
├── 1 Modal screen (HelpScreen)
├── Main app (AudiobookifyApp) with processing logic embedded
└── Processing logic scattered throughout
```

### Problem: Dual Job Tracking Systems

```
System A: QueuePanel + BookTask
- Short-term, UI-only
- No persistence
- Used by process_text_files()

System B: JobsPanel + JobManager
- Persistent, resume-capable
- Used by resume_job_async()
- NOT connected to Preview workflow
```

### Problem: Processing Logic Scattered

| Location | Function | Purpose |
|----------|----------|---------|
| tui.py | process_text_files() | Process from Preview |
| tui.py | process_files() | Process selected files |
| batch_processor.py | process_book() | Batch processing |
| audio_generator.py | read_book() | Core TTS generation |

---

## Phase 0: Core Backend Extraction (v2.4.x) - ✅ COMPLETED

### Goal
Create a unified `core/` module that both CLI and TUI can use. Bug fixes in one place affect both interfaces.

### Decision Record (2024-12-10)

**Problem**: TUI and CLI have separate implementations for:
- Job creation (different slug generation)
- Text export (different code paths)
- Conversion orchestration (duplicated logic)

**Decision**: Create `core/pipeline.py` with `ConversionPipeline` class that:
1. Orchestrates the full workflow: detect → filter → export → generate → package
2. Accepts callbacks for progress reporting (UI-agnostic)
3. Uses existing clean modules (audio_generator, chapter_detector, etc.)

**Rationale**:
- Single source of truth for business logic
- Easier testing (test core without UI)
- New interfaces (API, GUI) just call core
- Bug fixes propagate to all interfaces

### Target Structure

```
epub2tts_edge/
├── core/                       # Pure business logic - NO UI dependencies
│   ├── __init__.py
│   ├── pipeline.py             # ConversionPipeline - orchestrates workflow
│   └── text_exporter.py        # Extract from epub2tts_edge.py
│
├── audio_generator.py          # Already clean ✅
├── chapter_detector.py         # Already clean ✅
├── content_filter.py           # Already clean ✅
├── job_manager.py              # Already clean ✅
│
├── cli.py                      # Thin CLI - just arg parsing + calls core
├── tui.py                      # TUI - UI + calls core (later split further)
```

### ConversionPipeline Interface

```python
# core/pipeline.py

@dataclass
class PipelineConfig:
    """Configuration for conversion pipeline."""
    speaker: str = "en-US-AndrewNeural"
    rate: str | None = None
    volume: str | None = None
    detection_method: str = "combined"
    hierarchy_style: str = "flat"
    filter_config: FilterConfig | None = None
    normalize_audio: bool = False
    trim_silence: bool = False
    sentence_pause: int = 1200
    paragraph_pause: int = 1200
    max_concurrent: int = 5

class ConversionPipeline:
    """Single source of truth for the conversion workflow.

    Used by both CLI and TUI for consistent behavior.
    """

    def __init__(self, job_manager: JobManager, config: PipelineConfig):
        self.job_manager = job_manager
        self.config = config

    def create_job(self, source_file: Path, title: str = None,
                   author: str = None) -> Job:
        """Create job - unified for CLI and TUI."""

    def detect_chapters(self, source_file: Path) -> tuple[list[ChapterNode], FilterResult]:
        """Detect and filter chapters."""

    def export_text(self, job: Job, chapters: list[ChapterNode]) -> Path:
        """Export chapters to text file in job directory."""

    def generate_audio(self, job: Job, text_file: Path,
                       progress_callback=None,
                       cancellation_check=None) -> list[Path]:
        """Generate audio - with optional progress callback for UI."""

    def package_audiobook(self, job: Job, audio_files: list[Path],
                          cover_image: Path = None) -> Path:
        """Create final M4B audiobook."""

    def run(self, source_file: Path,
            progress_callback=None,
            cancellation_check=None) -> Job:
        """Full pipeline: detect → export → generate → package."""
```

### Migration Steps

1. ✅ **Create `core/pipeline.py`** with `ConversionPipeline` - Done (2024-12-10)
2. ⏸️ **Extract `text_exporter.py`** - Deferred (export logic in pipeline.export_text())
3. ✅ **Update CLI** to use `ConversionPipeline` - Done (EPUB → audiobook via pipeline)
4. ✅ **Update TUI** - Import added; TUI uses same underlying audio_generator.py
5. 🔄 **Remove duplicate code** - Partial (ongoing as needed)

### Implementation Notes (2024-12-10)

**CLI Integration**:
- EPUB files now use `ConversionPipeline.run()` for full conversion
- `--export-only` flag preserves legacy export-to-text behavior
- All CLI args mapped to `PipelineConfig`

**TUI Architecture**:
- TUI imports `ConversionPipeline` for future use
- TUI continues to use `BatchProcessor` + `process_text_files` workflow
- Both TUI and CLI share `audio_generator.py` functions (read_book, make_m4b)
- This ensures bug fixes in audio generation apply to both interfaces

**Shared Foundation**:
```
CLI (EPUB)  →  ConversionPipeline  →  audio_generator.py
TUI (EPUB)  →  BatchProcessor       →  audio_generator.py
TUI (TXT)   →  process_text_files   →  audio_generator.py
```

All paths converge on `audio_generator.py`, achieving the "fix bugs once" goal.

### Benefits

| Benefit | Impact |
|---------|--------|
| Fix bugs once | High - no more duplicate fixes |
| Consistent behavior | High - CLI and TUI work identically |
| Easier testing | High - core can be unit tested without UI |
| Add new interfaces | Medium - API, GUI just call core |

---

## Phase 1: TUI Module Extraction (v2.5.0)

### Target Structure

```
epub2tts_edge/
├── tui/
│   ├── __init__.py           # Re-export main components
│   ├── app.py                # AudiobookifyApp (slimmed down)
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── file_panel.py     # FilePanel, EPUBFileItem
│   │   ├── settings_panel.py # SettingsPanel (settings only)
│   │   ├── actions_panel.py  # NEW: Action buttons
│   │   ├── preview_panel.py  # PreviewPanel, ChapterPreviewItem
│   │   ├── progress_panel.py # ProgressPanel
│   │   ├── queue_panel.py    # QueuePanel (merge with Jobs?)
│   │   ├── jobs_panel.py     # JobsPanel, JobItem
│   │   └── log_panel.py      # LogPanel
│   ├── models/
│   │   ├── __init__.py
│   │   ├── preview_state.py  # PreviewChapter, ChapterPreviewState
│   │   └── voice_status.py   # VoicePreviewStatus
│   ├── screens/
│   │   ├── __init__.py
│   │   └── help_screen.py    # HelpScreen
│   └── processing.py         # Processing logic extracted from app
├── core/
│   ├── __init__.py
│   ├── pipeline.py           # NEW: Unified ProcessingPipeline
│   ├── events.py             # NEW: Event system
│   └── config.py             # NEW: Configuration management
```

### Extraction Order

1. **models/** - No dependencies, extract first
2. **screens/** - Minimal dependencies
3. **panels/** - One at a time, test after each
4. **processing.py** - Extract from app.py last
5. **core/pipeline.py** - New unified system

### Migration Strategy

```python
# Step 1: Create new module with re-export
# epub2tts_edge/tui/models/__init__.py
from .preview_state import PreviewChapter, ChapterPreviewState
from .voice_status import VoicePreviewStatus

# Step 2: Update imports in tui.py
# OLD: class PreviewChapter defined here
# NEW: from .tui.models import PreviewChapter

# Step 3: Move class to new file
# Step 4: Run tests, verify nothing broke
# Step 5: Repeat for next class
```

---

## Phase 2: Unified Processing Pipeline (v2.5.0)

### Design

```python
# core/pipeline.py

class ProcessingJob:
    """Unified job representation."""
    job_id: str
    source_file: Path
    chapters: list[ChapterSpec]  # What to process
    config: ProcessingConfig     # Voice, rate, etc.
    status: JobStatus
    progress: JobProgress

class ProcessingPipeline:
    """Single entry point for all processing."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.job_manager = JobManager()

    def submit(self, job: ProcessingJob) -> str:
        """Submit job for processing. Returns job_id."""
        self.job_manager.register(job)
        self.event_bus.emit("job_submitted", job)
        return job.job_id

    def process(self, job_id: str) -> None:
        """Process a job."""
        job = self.job_manager.get(job_id)
        self.event_bus.emit("job_started", job)

        for i, chapter in enumerate(job.chapters):
            if job.cancelled:
                self.event_bus.emit("job_cancelled", job)
                return

            self.event_bus.emit("chapter_started", job, chapter, i)
            audio = self._generate_chapter(chapter, job.config)
            self.event_bus.emit("chapter_completed", job, chapter, i, audio)

        output = self._package_audiobook(job)
        self.event_bus.emit("job_completed", job, output)
```

### Event System

```python
# core/events.py

class EventBus:
    """Publish-subscribe event system."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        for handler in self._handlers[event]:
            handler(*args, **kwargs)

# Usage in TUI:
pipeline = ProcessingPipeline(event_bus)
event_bus.on("chapter_completed", lambda j, c, i, a: update_progress(i))
event_bus.on("job_completed", lambda j, o: show_notification(o))
```

### Benefits

1. **Single source of truth** for job state
2. **UI-agnostic** - CLI and TUI use same pipeline
3. **Testable** - Can test pipeline without UI
4. **Extensible** - Add hooks, plugins, parallel processing

---

## Phase 3: Configuration Management (v2.6.0)

### Processing Profiles

```python
# core/config.py

@dataclass
class ProcessingProfile:
    name: str
    voice: str
    rate: str | None
    volume: str | None
    paragraph_pause: int
    sentence_pause: int
    normalize_audio: bool
    trim_silence: bool

# Built-in profiles
PROFILES = {
    "default": ProcessingProfile(
        name="Default",
        voice="en-US-AndrewNeural",
        rate=None,
        volume=None,
        paragraph_pause=1200,
        sentence_pause=1200,
        normalize_audio=False,
        trim_silence=False,
    ),
    "quick_draft": ProcessingProfile(
        name="Quick Draft",
        voice="en-US-GuyNeural",
        rate="+20%",
        ...
    ),
    "high_quality": ProcessingProfile(
        name="High Quality",
        voice="en-US-AndrewNeural",
        rate="-10%",
        normalize_audio=True,
        trim_silence=True,
        ...
    ),
}
```

### Output Naming Templates

```python
class OutputNaming:
    """Template-based output naming."""

    template: str = "{author} - {title}.m4b"

    def format(self, metadata: BookMetadata) -> str:
        return self.template.format(
            author=metadata.author,
            title=metadata.title,
            year=metadata.year or "Unknown",
        )
```

---

## Implementation Checklist

### Phase 1: Module Extraction ✅ COMPLETED (2024-12-10)
- [x] Create tui/models/ directory
- [x] Extract PreviewChapter, ChapterPreviewState
- [x] Extract VoicePreviewStatus
- [x] Create tui/panels/ directory
- [x] Extract FilePanel (with EPUBFileItem, PathInput)
- [x] Extract SettingsPanel
- [x] Extract PreviewPanel (with ChapterPreviewItem)
- [x] Extract ProgressPanel
- [x] Extract QueuePanel
- [x] Extract JobsPanel (with JobItem)
- [x] Extract LogPanel
- [x] Create tui/screens/ directory
- [x] Extract HelpScreen
- [x] Extract DirectoryBrowserScreen (bonus)
- [ ] Extract processing logic to tui/processing.py (deferred to Phase 2 - tightly coupled to UI)
- [x] Update all imports
- [x] Verify all tests pass (393 tests pass)

**Results**: app.py reduced from 4277 lines → 1995 lines (53% reduction)

### Phase 2: Unified Pipeline ✅ COMPLETED (2024-12-10)
- [x] EventBus implemented (core/events.py)
  - EventType enum with 17 event types (job lifecycle, stages, progress, logs)
  - Event dataclass with job reference and data payload
  - EventBus pub-sub class with on(), emit(), on_all(), clear()
  - Helper functions for creating common events
- [x] ConversionPipeline extended with EventBus support
  - Optional event_bus parameter (backward compatible)
  - _emit() helper for safe event emission
  - Events emitted at all key pipeline stages
- [x] TUIEventAdapter created (tui/handlers/event_adapter.py)
  - Bridges EventBus to TUI UI updates
  - Thread-safe updates via call_from_thread
  - Handles all event types with appropriate logging
  - Chapter progress logged to log panel (not just progress bar)
- [x] 28 tests for EventBus (tests/test_event_bus.py)
- [x] Integrate TUIEventAdapter with TUI processing workflows
  - EventBus initialized in AudiobookifyApp.__init__
  - TUIEventAdapter connected in on_mount, disconnected in on_unmount
- [x] Wire up events in TUI's process_files and process_text_files
  - process_text_files: JOB_CREATED, CONVERSION_STARTED, CHAPTER_STARTED/COMPLETED, PACKAGING_STARTED, JOB_COMPLETED/FAILED
  - process_files: CHAPTER_STARTED/COMPLETED (no Job object in batch mode)
- [x] Deprecate old callback-based processing
  - Removed redundant direct logging covered by EventBus events
  - Kept essential context logging not covered by events (traceback, cover image, etc.)
- [x] Remove deprecated code
  - Duplicate log messages removed from process_text_files and process_files
  - EventBus is now the single source of truth for processing status logging

**Results**: EventBus fully integrated, 421 tests pass

**Architecture Achieved**:
- Single source of truth: EventBus handles all processing status logging
- UI decoupled: Processing methods emit events, TUIEventAdapter handles UI updates
- Thread-safe: All UI updates go through call_from_thread via TUIEventAdapter
- Extensible: New interfaces (API, CLI) can subscribe to same events

### Phase 3: Configuration ✅ COMPLETED (2024-12-10)
- [x] Implement ProcessingProfile (core/profiles.py)
  - ProcessingProfile dataclass with all conversion settings
  - Built-in profiles: default, quick_draft, high_quality, audiobook, accessibility
  - Helper functions: get_profile(), list_profiles(), get_profile_names()
  - Serialization: to_dict() and from_dict() methods
- [x] Add profile selection to UI (tui/panels/settings_panel.py)
  - Profile dropdown in Voice tab
  - _apply_profile() method applies settings to all controls
  - Profile changes update voice, rate, volume, pauses, normalize, trim, detection, hierarchy
- [x] Implement OutputNaming (core/output_naming.py)
  - OutputNaming class with template-based naming
  - BookMetadata dataclass for book information
  - Template variables: {title}, {author}, {year}, {series}, {series_index}, {language}, {publisher}
  - sanitize_filename() for safe file names
  - Validation and help text for templates
  - Presets: author_title, title_only, title_author, series, year, full
- [x] Add template editor to settings
  - Output naming dropdown in Advanced tab
  - get_config() returns output_naming_template and profile
- [x] Tests for profiles and output naming (54 tests)
  - tests/test_profiles.py: 19 tests for ProcessingProfile
  - tests/test_output_naming.py: 35 tests for OutputNaming

**Results**: 475 tests pass, Phase 3 complete

---

## Dependencies

```
Phase 1 (Module Extraction)
    ↓
Phase 2 (Unified Pipeline) ← Requires Phase 1
    ↓
Phase 3 (Configuration) ← Requires Phase 2
    ↓
Future Features (Parallel processing, plugins, etc.)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Comprehensive test suite before starting |
| Import cycle issues | Careful dependency ordering |
| Performance regression | Profile before/after each phase |
| User confusion during transition | Feature flags, gradual rollout |
