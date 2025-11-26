# Audiobookify - Development Context

This file provides context for Claude Code when working on this project.

## Project Overview

**Audiobookify** is a Python tool that converts EPUB files to M4B audiobooks using Microsoft Edge's cloud-based text-to-speech. It was forked from [epub2tts-edge](https://github.com/aedocw/epub2tts-edge) and enhanced with better chapter detection, batch processing, and a terminal UI.

## Architecture

```
epub2tts_edge/
├── __init__.py           # Package exports
├── epub2tts_edge.py      # Main CLI and audio generation logic
├── chapter_detector.py   # Enhanced chapter detection (TOC + headings)
├── batch_processor.py    # Batch processing for multiple EPUBs
└── tui.py               # Terminal UI (Textual-based)

tests/
├── test_chapter_detector.py
└── test_batch_processor.py
```

## Key Components

### 1. Chapter Detection (`chapter_detector.py`)
- **TOCParser**: Parses EPUB2 NCX and EPUB3 NAV table of contents
- **HeadingDetector**: Extracts h1-h6 headings from HTML content
- **ChapterDetector**: Combines multiple detection methods
- **ChapterNode**: Tree structure for hierarchical chapters

Detection methods:
- `toc` - Table of Contents only
- `headings` - HTML headings only
- `combined` - Merge TOC with headings (default)
- `auto` - Automatically choose best method

### 2. Batch Processing (`batch_processor.py`)
- **BatchProcessor**: Processes multiple EPUBs
- **BatchConfig**: Configuration options
- **BatchResult**: Results and reporting
- **BookTask**: Individual book status tracking

Features:
- Folder scanning (recursive optional)
- Skip already-processed files
- Resume interrupted batches
- JSON report generation

### 3. Terminal UI (`tui.py`)
Built with [Textual](https://textual.textualize.io/):
- **FilePanel**: EPUB file browser and selection
- **SettingsPanel**: Voice, detection, hierarchy options
- **ProgressPanel**: Real-time conversion progress
- **QueuePanel**: Processing queue with status
- **LogPanel**: Detailed log output

### 4. Audio Generation (`epub2tts_edge.py`)
- Uses `edge-tts` for Microsoft Edge TTS
- Parallel sentence processing (10 concurrent)
- FLAC intermediate format
- FFmpeg for M4B creation with chapter markers

## CLI Commands

```bash
# Main commands
audiobookify <file|folder> [options]
abfy <file|folder> [options]          # Short alias

# TUI
audiobookify-tui [folder]
abfy-tui [folder]                      # Short alias
```

## Key Options

| Option | Description |
|--------|-------------|
| `--detect` | Chapter detection method (toc/headings/combined/auto) |
| `--hierarchy` | Title format (flat/numbered/arrow/breadcrumb/indented) |
| `--batch` | Enable batch processing |
| `--recursive` | Scan subdirectories |
| `--export-only` | Only export to TXT, skip audio |
| `--tui` | Launch terminal UI |
| `--preview` | Preview chapters without exporting |

## Development

### Running Tests
```bash
python -m pytest tests/ -v
```

### Testing CLI
```bash
# Without installing
PYTHONPATH=. python -m epub2tts_edge.epub2tts_edge --help

# Test TUI
PYTHONPATH=. python -m epub2tts_edge.tui
```

### Dependencies
- `ebooklib` - EPUB parsing
- `beautifulsoup4` - HTML parsing
- `edge-tts` - Microsoft Edge TTS
- `pydub` - Audio manipulation
- `mutagen` - M4B metadata
- `textual` - Terminal UI
- `nltk` - Sentence tokenization
- `ffmpeg` - Audio processing (external)

## File Formats

### Intermediate Text Format
```
Title: Book Title
Author: Author Name

# Chapter 1
Paragraph text here...

## Section 1.1
More text...
```

### M4B Chapter Metadata
Uses FFmpeg metadata format with chapter markers including start/end times in milliseconds.

## Related Documentation

- [ROADMAP.md](./ROADMAP.md) - Future plans and features
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [README.md](./README.md) - User documentation

## Common Tasks

### Adding a new detection method
1. Add to `DetectionMethod` enum in `chapter_detector.py`
2. Implement in `ChapterDetector._detect_*` method
3. Add to CLI choices in `epub2tts_edge.py`
4. Update tests

### Adding a new TUI panel
1. Create widget class in `tui.py`
2. Add to `AudiobookifyApp.compose()`
3. Wire up event handlers
4. Update CSS if needed

### Adding a CLI option
1. Add `parser.add_argument()` in `main()`
2. Pass to appropriate processor/function
3. Update help text examples
4. Document in README
