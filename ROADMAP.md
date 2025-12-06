# Audiobookify Roadmap

## Current Version: 2.3.0

### Design Documents

The following design documents detail implementation plans for major features:

| Document | Description | Status |
|----------|-------------|--------|
| [Architecture Refactor](./claudedocs/ARCHITECTURE_REFACTOR.md) | Module extraction, unified pipeline | Planning |
| [Settings Panel Redesign](./claudedocs/SETTINGS_PANEL_REDESIGN.md) | Tabbed settings, actions separation | Planning |
| [Testing Strategy](./claudedocs/TESTING_STRATEGY.md) | TUI tests, fixtures, CI integration | Planning |

---

### Completed Features

#### Phase 1: Enhanced Chapter Detection (v2.0.0)
- [x] EPUB2 NCX Table of Contents parsing
- [x] EPUB3 NAV document parsing
- [x] Multi-level heading detection (h1-h6)
- [x] Multiple detection methods (toc, headings, combined, auto)
- [x] Hierarchical chapter structure (ChapterNode tree)
- [x] Multiple hierarchy display styles (flat, numbered, arrow, breadcrumb, indented)
- [x] Chapter preview mode (`--preview`)
- [x] Legacy mode for backward compatibility (`--legacy`)

#### Phase 2: Batch Processing (v2.0.0)
- [x] Folder scanning for EPUB files
- [x] Recursive subfolder scanning (`--recursive`)
- [x] Skip already-processed files
- [x] Resume interrupted batches
- [x] JSON report generation
- [x] Progress tracking per book
- [x] Custom output directory (`--output-dir`)
- [x] Export-only mode (`--export-only`)

#### Phase 3: Terminal UI (v2.0.0)
- [x] File browser panel
- [x] Settings panel (voice, detection, hierarchy)
- [x] Real-time progress display
- [x] Processing queue with status icons
- [x] Log panel
- [x] Keyboard shortcuts

#### Phase 4: Quality of Life (v2.1.0)
- [x] **Voice preview** - Listen to voice samples before converting (`--preview-voice`, `--list-voices`)
- [x] **Speed/volume control** - Adjust TTS rate and volume (`--rate`, `--volume`)
- [x] **Chapter selection** - Convert only specific chapters (`--chapters "1-5"`)
- [x] **Pause/resume** - Resume interrupted conversions (`--resume`, `--no-resume`)
- [x] **TUI integration** - All v2.1.0 features available in Terminal UI

#### Phase 5: Enhanced Audio Quality (v2.2.0)
- [x] **Audio normalization** - Consistent volume across chapters (`--normalize`)
- [x] **Silence detection** - Trim excessive pauses (`--trim-silence`)
- [x] **Custom pronunciation** - Dictionary for proper nouns, technical terms (`--pronunciation`)
- [x] **Multiple voice support** - Different voices for different characters (`--voice-mapping`, `--narrator-voice`)
- [x] **TUI integration** - All v2.2.0 features available in Terminal UI

#### Phase 6: Format Support & Platform Integration (v2.3.0)
- [x] **MOBI/AZW support** - Amazon Kindle formats (MOBI, AZW, AZW3)
- [x] **Chapter detection for MOBI** - Extract chapters from Kindle books
- [x] **Cover extraction** - Extract cover images from MOBI files
- [x] **Metadata parsing** - Extract title, author from MOBI metadata
- [x] **Docker support** - Dockerfile and docker-compose.yml for containerized usage
- [x] **Calibre plugin** - Integration with Calibre library management

---

## Planned Features

### v2.4.0 - TUI Improvements & Additional Formats

#### TUI Improvements (Completed)
- [x] **Compact FilePanel layout** - Merge title/mode/count into single row to maximize file list
- [x] **Multi-select jobs** - Select multiple jobs for batch operations (delete, resume)
- [x] **Job queue reordering** - Move jobs up/down in queue priority
- [x] **Preview chapter editing** - Merge/delete chapters with undo, batch operations
- [x] **Chapter title editing** - Inline title editing with E key
- [x] **Parent navigation** - Backspace key navigates to parent directory
- [x] **Keyboard navigation** - More shortcuts for common operations (1-4 tabs, /, Backspace, R, X, F1)

#### TUI Improvements (Next)
- [x] **Range/batch selection** - Enter key for anchor-based range, V key for toggle mode
- [x] **Directory browser** - Add DirectoryTree modal for easier folder selection (📂 button, `b` key)
- [x] **Path autocomplete** - Tab completion for directory input (Tab key in path field)
- [ ] **Settings panel redesign** - Tabbed settings with actions separation (see [design doc](./claudedocs/SETTINGS_PANEL_REDESIGN.md))

#### TUI Architecture (v2.5.0) - See [Architecture Refactor](./claudedocs/ARCHITECTURE_REFACTOR.md)

**Phase 1: Module Extraction**
- [ ] Extract tui.py monolith (3,372 lines) into organized modules
- [ ] Create tui/panels/, tui/models/, tui/screens/ structure
- [ ] Maintain backward compatibility during migration

**Phase 2: Unified Processing Pipeline**
- [ ] Implement EventBus for decoupled communication
- [ ] Create unified ProcessingPipeline
- [ ] Connect Preview workflow to JobManager
- [ ] Single source of truth for all processing jobs

**Phase 3: Enhanced Features**
- [ ] Multi-file preview with tabbed interface
- [ ] Parallel job processing (configurable concurrency)
- [ ] Progress estimation based on word count
- [ ] Processing profiles (Quick Draft, High Quality, etc.)

#### Testing Infrastructure - See [Testing Strategy](./claudedocs/TESTING_STRATEGY.md)
- [ ] Set up TUI integration tests with Textual's AppTest
- [ ] Create test fixtures (create_test_epub helper)
- [ ] Implement MockTTSEngine for fast testing
- [ ] Add CI/CD workflow for automated testing

#### Content Intelligence
- [ ] **Empty chapter detection** - Flag/auto-remove chapters with no meaningful content
- [ ] **Duplicate content detection** - Identify repeated sections
- [ ] **ML-based chapter detection** - Learn patterns from book structure
- [ ] **Smart front/back matter** - Auto-identify title pages, copyright, indexes
- [ ] **Footnote handling** - Options to inline, append, or skip footnotes

#### Quality of Life
- [ ] **Output naming templates** - Configurable "{author} - {title}.m4b" patterns
- [ ] **Quick edit shortcuts** - Keyboard shortcuts for common edit patterns
- [ ] **Batch chapter operations** - Apply same edit across multiple books

#### Format Support
- [ ] **PDF support** - Extract text from PDF files
- [ ] **HTML/Markdown** - Direct conversion from web content
- [ ] **Output formats** - MP3, OPUS, AAC options (not just M4B)
- [ ] **Chapter images** - Embed chapter artwork if available

#### Advanced Features
- [ ] **Local TTS engines** - Offline conversion (Piper, Coqui)
- [ ] **GPU acceleration** - Faster processing with CUDA
- [ ] **Streaming mode** - Start playback while converting
- [ ] **Audiobook metadata** - Enhanced ID3/M4B tags

### v3.0.0 - Platform Expansion

- [ ] **Web UI** - Browser-based interface (optional)
- [ ] **REST API** - Programmatic access
- [ ] **Mobile companion app** - Control from phone

---

## Known Issues

### Current Limitations
1. **Edge TTS requires internet** - No offline mode currently
2. **Large files** - Memory usage for very large EPUBs
3. **Complex layouts** - Tables, sidebars may not extract well
4. **Non-English** - Some languages have limited voice options

### TUI Architecture Limitations (Addressed in v2.5.0)

These are documented in [Architecture Refactor](./claudedocs/ARCHITECTURE_REFACTOR.md):

1. **tui.py monolith** - 3,372 lines mixing models, panels, and processing logic
2. **Preview is single-file only** - Multi-file preview planned for unified pipeline
3. **Two tracking systems** - QueuePanel and JobsPanel will be unified
4. **Jobs panel disconnected from Preview** - Will be connected via EventBus

### Planned Fixes
- [ ] Better error handling for network issues
- [ ] Streaming processing for large files
- [ ] Improved HTML content filtering
- [ ] Language auto-detection

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to contribute.

### Priority Areas
1. Bug fixes and stability
2. Documentation improvements
3. Test coverage
4. New TTS engine integrations
5. Format support expansion

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 2.3.0 | 2025-11 | MOBI/AZW format support, Docker image, Calibre plugin |
| 2.2.0 | 2025-11 | Audio normalization, silence trimming, custom pronunciation, multi-voice |
| 2.1.0 | 2025-11 | Voice preview, rate/volume control, chapter selection, pause/resume |
| 2.0.0 | 2025-11 | Enhanced chapter detection, batch processing, TUI |
| 1.2.7 | 2024 | Original epub2tts-edge features (forked) |
