# Session: TUI Improvements & Chapter Detection Fix

## Date: 2025-12-05 (continued from 2025-12-04)

## Summary
Major improvements to the Audiobookify TUI including an Export & Edit workflow, mid-chapter stop capability, and critical chapter detection duplicate content fix.

## Key Changes

### 1. Export & Edit Workflow (tui.py)
- Added "📝 Export Text" button in SettingsPanel after "Preview Chapters"
- Added "Convert from Text" section with text file input and "🔊 Convert Text to Audio" button
- New methods:
  - `action_export_text()` - Exports EPUB to text with editing instructions
  - `export_text_async()` - Background worker for export
  - `action_convert_text()` - Converts edited text file to audiobook  
  - `convert_text_async()` - Background worker for text-to-audio conversion
  - `_set_text_file_input()` - Auto-fills text path after export
  - `_text_convert_complete()` - Cleanup after conversion

### 2. Mid-Chapter Stop Capability
- Added `cancellation_check: Callable | None = None` parameter to `read_book()` in audio_generator.py:238
- Cancellation checks added at:
  - Chapter start (line ~265)
  - Paragraph start (line ~317)
- Updated `BatchProcessor.process_book()` to accept and pass `cancellation_check`
- Updated TUI `process_files()` to create `check_cancelled()` callback
- Changed stop message from "will finish current book" to "will stop after current paragraph"

### 3. Log Panel Height Fix (tui.py CSS)
- Changed `#bottom-tabs` from `height: 1fr` to `height: 2fr`
- Changed `min-height` from 15 to 20
- Result: Bottom tabs (including log) get twice the vertical space

### 4. Chapter Detection Duplicate Content Fix (chapter_detector.py:682)
**Problem**: When multiple chapters pointed to same HTML file without anchors, ALL chapters got ALL paragraphs (duplicating content massively).

**Solution in `_populate_content()`**:
- Track files already fully processed with `files_fully_processed: set[str]`
- Before falling back to "get all paragraphs", try to match chapter title to heading in file
- If file already processed and no anchor/title match, skip (don't duplicate)

**Code pattern**:
```python
# If no anchor, try to find a heading that matches the chapter title
if not start_elem and chapter.title:
    for heading in soup.find_all(HeadingDetector.HEADING_TAGS):
        heading_text = heading.get_text(strip=True)
        if heading_text and (
            heading_text.lower() == chapter.title.lower()
            or chapter.title.lower() in heading_text.lower()
            or heading_text.lower() in chapter.title.lower()
        ):
            start_elem = heading
            break
```

## Files Modified
- `epub2tts_edge/tui.py` - Export/Edit workflow, stop capability, CSS height
- `epub2tts_edge/audio_generator.py` - cancellation_check parameter in read_book()
- `epub2tts_edge/batch_processor.py` - cancellation_check passthrough in process_book()
- `epub2tts_edge/chapter_detector.py` - Duplicate content prevention in _populate_content()

## Testing
- All tests pass: 17 chapter detector, 32 job manager, 19 batch processor
- Imports verified working

## Known Issues to Watch
- Chapter detection for "Writing and Difference" had split titles ("Two" and "Cogito and the History of Madness")
- Fix should prevent duplicate content, but user should verify with Preview Chapters
- If still wrong, use Export Text → Edit → Convert workflow

## Session 2025-12-05 Changes

### 5. Toggle Mode for Batch Chapter Selection (tui.py)
- Added `_toggle_mode: bool` flag for visual selection
- V key enters toggle mode - navigating with arrow keys toggles each item's selection state
- Escape or V again exits toggle mode
- Methods: `_enter_toggle_mode()`, `_exit_toggle_mode()`, `_update_toggle_mode_instructions()`
- Instructions update dynamically: "🔵 TOGGLE MODE: ↑↓=toggle items, V/Esc=exit"

### Recent Commits (feature/tui-improvements-v2)
- 1799aec: Rename visual mode to toggle mode for clarity
- 131d91a: Simplify visual mode to single toggle behavior
- 5401dbc: Add visual deselect mode with D key (later simplified)
- 864e729: Implement visual selection mode with V key
- 5afaf1f: Change range selection from Shift+Space to Enter key

## Architecture Notes
- TUI uses `@work(exclusive=True, thread=True)` for background processing
- Progress updates use `call_from_thread()` for thread-safe UI updates
- Cancellation is cooperative - checked at natural boundaries (chapters/paragraphs)
