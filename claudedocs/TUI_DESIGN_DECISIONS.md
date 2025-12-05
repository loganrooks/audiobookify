# TUI Design Decisions

This document captures key design decisions for the Audiobookify TUI, intended for future review and revision.

## Layout Architecture

### Overall Structure
```
+---------------------------------------------------+
|                    Header                          |
+----------------------------+----------------------+
|        Left Column         |    Right Column      |
|          (2fr)             |       (1fr)          |
+----------------------------+----------------------+
|        FilePanel           |    SettingsPanel     |
|    (1fr, max-height: 40%)  |    (full height)     |
+----------------------------+                      |
|       Bottom Tabs          |                      |
|   (3fr, min-height: 25)    |                      |
|  [Progress|Queue|Jobs|Log] |                      |
+----------------------------+----------------------+
|                    Footer                          |
+---------------------------------------------------+
```

### Column Proportions
- **Left column**: `width: 2fr` (2/3 of space), `min-width: 30`
- **Right column**: `width: 1fr` (1/3 of space), `min-width: 35`, `max-width: 50`

**Rationale**: Settings panel needs fixed width for readability. File panel and logs need more space for paths and messages.

**Consideration for Review**: The `max-width: 50` on settings panel may feel cramped with all v2.2.0 options. May need wider panel or scrollable sections.

### Vertical Distribution (Left Column)
- **FilePanel**: `height: 1fr`, `min-height: 10`, `margin-bottom: 1`
- **Bottom tabs**: `height: 1fr`, `min-height: 15`

**Rationale**: 50/50 split with both panels anchored to the middle. Equal space for file selection and bottom tabs (Progress, Queue, Jobs, Log).

**Fix Applied (v2)**: The `max-height: 40%` constraint combined with the new mode toggle buttons squeezed the file list to nothing. Changed to equal `1fr` heights for a clean 50/50 split.

## Panel Designs

### FilePanel
- **Dual-mode design**: Toggle between Books (EPUB/MOBI/AZW) and Text (.txt) modes
- Mode toggle buttons at top: `📚 Books` | `📝 Text`
- DataTable for file selection with checkboxes
- Columns: checkbox, filename, status
- Press `s` to start or use Start button

**Design Decision**: Text file conversion was moved from SettingsPanel to FilePanel as a mode toggle. This improves separation of concerns:
- **Before**: "Convert from Text" was a workflow action awkwardly placed in settings
- **After**: FilePanel handles ALL file selection, regardless of type

**Mode Toggle CSS**:
```css
FilePanel > #mode-toggle {
    height: 3;
    margin-bottom: 1;
}
FilePanel > #mode-toggle > Button {
    min-width: 12;
    margin: 0 1 0 0;
}
FilePanel > #mode-toggle > Button.active {
    background: $primary;
    color: $text;
}
```

**Workflow**:
1. **Books mode** (default): Select EPUB/MOBI/AZW files → Start → Full conversion
2. **Text mode**: Select .txt files → Start → Convert edited text to audiobook

**Export & Edit Flow**:
1. Select EPUB in Books mode
2. Click "📝 Export Text" in settings
3. Edit the .txt file externally
4. Switch to Text mode in FilePanel
5. Select the edited .txt file
6. Click Start to convert

### SettingsPanel
Contains all conversion options:
- Voice selection (dropdown)
- Rate adjustment (input)
- Volume adjustment (input)
- Chapter detection method (dropdown)
- Hierarchy style (dropdown)

**Removed**: "Convert from Text" section was relocated to FilePanel as a mode toggle.

**Concern**: Settings panel is getting dense with v2.2.0 options (normalization, silence detection, pronunciation, multi-voice). May need reorganization.

### JobsPanel
Shows saved jobs from `~/.audiobookify/jobs/`:
- DataTable showing job_id, status, progress, source file
- Resume/Delete buttons

**Button CSS Fix Applied**:
```css
JobsPanel Button {
    min-width: 10;
    height: 3;       /* Was: height: 1; max-height: 1 - too small! */
    padding: 0 1;
    margin: 0 1 0 0;
}
```

**Issue**: With `height: 1`, button text was invisible. Changed to `height: 3` for proper text display.

### LogPanel
RichLog widget for conversion output:
- Shows progress messages, chapter completions, errors
- Auto-scrolls to latest message

## Job Isolation Architecture

### Purpose
Each conversion job gets an isolated folder in `~/.audiobookify/jobs/` to prevent file collisions between concurrent or sequential conversions.

### Job Folder Structure
```
~/.audiobookify/jobs/
  BookName_20241203_143022_abc123/
    job.json           # Job metadata and state
    BookName.txt       # Extracted text
    chapter_001.flac   # Audio segments
    chapter_002.flac
    ...
```

### Job States
- `PENDING` - Job created, not started
- `EXTRACTING` - Extracting text from EPUB
- `CONVERTING` - Converting to audio (main work)
- `FINALIZING` - Creating M4B
- `COMPLETED` - Done successfully
- `FAILED` - Error occurred
- `CANCELLED` - User stopped

### Resume Logic
`Job.is_resumable` returns True when:
- Status is `EXTRACTING` or `CONVERTING`
- `0 < completed_chapters < total_chapters`

**Key Fix Applied**: When user cancels, job must NOT be marked as FAILED:
```python
# batch_processor.py - cancellation handling
if cancellation_check and cancellation_check():
    task.status = ProcessingStatus.FAILED
    task.error_message = "Cancelled by user"
    task.end_time = time.time()
    # DON'T call set_error() - keep job in CONVERTING state for resume
    return False
```

### Resume Flow in TUI
1. User clicks "Resume" on a job in JobsPanel
2. `action_resume_job()` gets selected job
3. `resume_job_async()` runs in background thread
4. Creates `BookTask` with job_id and job_dir already set
5. Creates `BatchProcessor` but does NOT call `prepare()`
6. Calls `processor.process_book(task)` directly

**Key Fix Applied**: Originally `resume_job_async()` was calling `prepare()` which created a NEW task without job info, losing the resume context:
```python
# WRONG - creates fresh task without job info:
processor.prepare()
book_task = processor.result.tasks[0]  # Lost job_id/job_dir!

# CORRECT - use pre-configured task directly:
processor = BatchProcessor(config)
success = processor.process_book(task, ...)  # task has job_id/job_dir
```

## CSS Quirks and Gotchas

### Button Height
Textual buttons need explicit height for text visibility:
- `height: 1` - Too small, text clips
- `height: 3` - Appropriate for single-line buttons

### TabbedContent Height
Tab panels inherit from their container. To give tabs more space:
```css
#bottom-tabs {
    height: 3fr;      /* Relative to FilePanel's 1fr */
    min-height: 25;   /* Minimum lines for log readability */
}
```

### Fractional Units vs Percentages
- `fr` units for flexible layouts within containers
- `%` for hard limits relative to parent (like `max-height: 40%`)

## Future Considerations

### Settings Panel Organization
With v2.2.0 features, the settings panel has many options:
- Basic: Voice, Rate, Volume
- Detection: Method, Hierarchy, Max Depth
- Audio Processing: Normalize, Trim Silence
- Advanced: Pronunciation dict, Multi-voice mapping

**Suggestion**: Consider grouping into collapsible sections or tabs within settings panel.

### Job Management UX
Current: Select job in table, click button
**Alternative**: Right-click context menu or inline buttons per row

### Progress Display
Current: Chapter-level progress in Progress tab
**Enhancement**: Consider adding overall batch progress, estimated time remaining

## Change History

| Date | Change | Files |
|------|--------|-------|
| 2024-12-04 | Fixed Jobs buttons text visibility (height: 1 → 3) | tui.py |
| 2024-12-04 | Fixed Log panel height (added max-height: 40% to FilePanel, bottom-tabs min-height: 25) | tui.py |
| 2024-12-04 | Fixed resume button (removed prepare() call, keep job in CONVERTING on cancel) | tui.py, batch_processor.py |
| 2024-12-04 | Refactored text conversion: Added dual-mode FilePanel (Books/Text toggle), removed "Convert from Text" from SettingsPanel, cleaned up old action_convert_text/convert_text_async methods | tui.py |
| 2024-12-04 | Fixed FilePanel/bottom-tabs layout: Removed max-height: 40% constraint, changed to 50/50 split (1fr each), removed internal max-height constraints, compacted margins | tui.py |
| 2024-12-04 | Fixed Log tab height: Added CSS for TabbedContent internal height propagation (ContentSwitcher, TabPane) | tui.py |
| 2024-12-04 | Renamed exports: "Export Text" → "Export & Edit", "Export Only:" → "Text Only:" for clarity | tui.py |
| 2024-12-04 | Fixed job resume: BatchProcessor now respects task's existing job_id instead of overwriting; is_resumable allows completed_chapters=0 | batch_processor.py, job_manager.py |
| 2024-12-04 | Added verbose resume logging: Job details now logged when resuming (ID, dir, status, progress, voice) | tui.py |
