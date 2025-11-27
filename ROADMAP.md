# Audiobookify Roadmap

## Current Version: 2.3.0

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

#### Phase 6: Format Support & Docker (v2.3.0)
- [x] **MOBI/AZW support** - Amazon Kindle formats (MOBI, AZW, AZW3)
- [x] **Chapter detection for MOBI** - Extract chapters from Kindle books
- [x] **Cover extraction** - Extract cover images from MOBI files
- [x] **Metadata parsing** - Extract title, author from MOBI metadata
- [x] **Docker support** - Dockerfile and docker-compose.yml for containerized usage

---

## Planned Features

### v2.4.0 - Additional Formats & Advanced Features

#### Format Support
- [ ] **PDF support** - Extract text from PDF files
- [ ] **HTML/Markdown** - Direct conversion from web content
- [ ] **Output formats** - MP3, OPUS, AAC options (not just M4B)
- [ ] **Chapter images** - Embed chapter artwork if available

#### Advanced Features
- [ ] **Local TTS engines** - Offline conversion (Piper, Coqui)
- [ ] **GPU acceleration** - Faster processing with CUDA
- [ ] **Streaming mode** - Start playback while converting
- [ ] **Cloud sync** - Sync audiobook library across devices
- [ ] **Audiobook metadata** - Enhanced ID3/M4B tags

### v3.0.0 - Platform Expansion

- [ ] **Web UI** - Browser-based interface (optional)
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
| 2.3.0 | 2025-11 | MOBI/AZW format support, Docker image |
| 2.2.0 | 2025-11 | Audio normalization, silence trimming, custom pronunciation, multi-voice |
| 2.1.0 | 2025-11 | Voice preview, rate/volume control, chapter selection, pause/resume |
| 2.0.0 | 2025-11 | Enhanced chapter detection, batch processing, TUI |
| 1.2.7 | 2024 | Original epub2tts-edge features (forked) |
