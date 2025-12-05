# Architecture Refactoring Plan

## Overview

This document outlines the refactoring needed to make the codebase maintainable and extensible for future features.

## Current State

### Problem: tui.py Monolith (3,372 lines)

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

## Phase 1: Module Extraction (v2.5.0)

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

### Phase 1: Module Extraction
- [ ] Create tui/models/ directory
- [ ] Extract PreviewChapter, ChapterPreviewState
- [ ] Extract VoicePreviewStatus
- [ ] Create tui/panels/ directory
- [ ] Extract FilePanel (with EPUBFileItem)
- [ ] Extract SettingsPanel
- [ ] Extract PreviewPanel (with ChapterPreviewItem)
- [ ] Extract ProgressPanel
- [ ] Extract QueuePanel
- [ ] Extract JobsPanel (with JobItem)
- [ ] Extract LogPanel
- [ ] Create tui/screens/ directory
- [ ] Extract HelpScreen
- [ ] Extract processing logic to tui/processing.py
- [ ] Update all imports
- [ ] Verify all tests pass

### Phase 2: Unified Pipeline
- [ ] Create core/ directory
- [ ] Implement EventBus
- [ ] Implement ProcessingJob
- [ ] Implement ProcessingPipeline
- [ ] Integrate with TUI
- [ ] Integrate with CLI
- [ ] Deprecate old processing functions
- [ ] Remove deprecated code

### Phase 3: Configuration
- [ ] Implement ProcessingProfile
- [ ] Add profile selection to UI
- [ ] Implement OutputNaming
- [ ] Add template editor to settings

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
