# Changelog

All notable changes to Audiobookify will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
