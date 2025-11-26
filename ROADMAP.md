# Audiobookify Roadmap

## Current Version: 2.0.0

### Completed Features

#### Phase 1: Enhanced Chapter Detection
- [x] EPUB2 NCX Table of Contents parsing
- [x] EPUB3 NAV document parsing
- [x] Multi-level heading detection (h1-h6)
- [x] Multiple detection methods (toc, headings, combined, auto)
- [x] Hierarchical chapter structure (ChapterNode tree)
- [x] Multiple hierarchy display styles (flat, numbered, arrow, breadcrumb, indented)
- [x] Chapter preview mode (`--preview`)
- [x] Legacy mode for backward compatibility (`--legacy`)

#### Phase 2: Batch Processing
- [x] Folder scanning for EPUB files
- [x] Recursive subfolder scanning (`--recursive`)
- [x] Skip already-processed files
- [x] Resume interrupted batches
- [x] JSON report generation
- [x] Progress tracking per book
- [x] Custom output directory (`--output-dir`)
- [x] Export-only mode (`--export-only`)

#### Phase 3: Terminal UI
- [x] File browser panel
- [x] Settings panel (voice, detection, hierarchy)
- [x] Real-time progress display
- [x] Processing queue with status icons
- [x] Log panel
- [x] Keyboard shortcuts

---

## Planned Features

### v2.1.0 - Quality of Life

#### High Priority
- [ ] **Voice preview** - Listen to voice samples before converting
- [ ] **Speed/pitch control** - Adjust TTS voice parameters
- [ ] **Chapter selection** - Convert only specific chapters
- [ ] **Pause/resume** - Pause mid-conversion and resume later

#### Medium Priority
- [ ] **Multiple voice support** - Different voices for different characters/sections
- [ ] **Custom pronunciation** - Dictionary for proper nouns, technical terms
- [ ] **Audio normalization** - Consistent volume across chapters
- [ ] **Silence detection** - Trim excessive pauses

### v2.2.0 - Format Support

- [ ] **PDF support** - Extract text from PDF files
- [ ] **MOBI/AZW support** - Amazon Kindle formats
- [ ] **HTML/Markdown** - Direct conversion from web content
- [ ] **Output formats** - MP3, OPUS, AAC options (not just M4B)
- [ ] **Chapter images** - Embed chapter artwork if available

### v2.3.0 - Advanced Features

- [ ] **Local TTS engines** - Offline conversion (Piper, Coqui)
- [ ] **GPU acceleration** - Faster processing with CUDA
- [ ] **Streaming mode** - Start playback while converting
- [ ] **Cloud sync** - Sync audiobook library across devices
- [ ] **Audiobook metadata** - Enhanced ID3/M4B tags

### v3.0.0 - Platform Expansion

- [ ] **Web UI** - Browser-based interface (optional)
- [ ] **Docker image** - Easy deployment
- [ ] **REST API** - Programmatic access
- [ ] **Mobile companion app** - Control from phone
- [ ] **Calibre plugin** - Integration with Calibre library

---

## Known Issues

### Current Limitations
1. **Edge TTS requires internet** - No offline mode currently
2. **Large files** - Memory usage for very large EPUBs
3. **Complex layouts** - Tables, sidebars may not extract well
4. **Non-English** - Some languages have limited voice options

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
| 2.0.0 | 2024 | Enhanced chapter detection, batch processing, TUI |
| 1.2.7 | 2024 | Original epub2tts-edge features |
