# TUI Comprehensive Review

## Issue 1: Log Tab Not Anchored to Bottom

### Current Layout Structure
```
AudiobookifyApp
├── Header
├── #app-container (Horizontal)
│   ├── #left-column (Vertical)
│   │   ├── FilePanel (height: 1fr, min-height: 10)
│   │   └── #bottom-tabs TabbedContent (height: 1fr, min-height: 15)
│   │       ├── TabPane "Progress" → ProgressPanel
│   │       ├── TabPane "Queue" → QueuePanel
│   │       ├── TabPane "Jobs" → JobsPanel
│   │       └── TabPane "Log" → LogPanel
│   └── #right-column (Vertical)
│       └── SettingsPanel (VerticalScroll, height: 100%)
└── Footer
```

### Problem Analysis
The `TabbedContent` widget wraps each `TabPane` in its own container. The inner panels have `height: 100%` but the TabPane container itself may not be filling the TabbedContent properly.

### Root Cause
Looking at the screenshot, the Log panel appears inside the TabbedContent but doesn't fill vertically. The issue is that:
1. `TabbedContent` reserves space for tabs at the top
2. The `TabPane` content area uses remaining space
3. Each panel inside has `height: 100%` but the parent chain isn't enforcing full height

### Recommended Fix
```css
/* In AudiobookifyApp.CSS */
#bottom-tabs {
    height: 1fr;
    min-height: 15;
}

#bottom-tabs > ContentSwitcher {
    height: 1fr;
}

#bottom-tabs > ContentSwitcher > TabPane {
    height: 100%;
}
```

Or simpler approach - target the TabbedContent's internal structure:
```css
TabPane {
    height: 100%;
}

TabPane > * {
    height: 100%;
}
```

---

## Issue 2: FilePanel Button Placement

### Current Layout (top to bottom)
1. Title label ("📁 Select Files")
2. Mode toggle (Books | Text buttons) - 3 lines
3. File count label ("0 files found")
4. Path input field
5. File list (ListView) - **this should be maximized**
6. Action buttons (All | None | Refresh) - 3 lines

### Space Consumption
- Fixed elements: ~10-12 lines (title, mode toggle, count, path, buttons)
- File list: Gets whatever remains

### Recommendations

**Option A: Merge mode toggle with title row**
```
📁 Select Books  [📚 Books] [📝 Text]   0 files found
```
Saves: 2 lines

**Option B: Move action buttons to title row**
```
📁 Select Files                    [✓] [✗] [🔄]
```
Saves: 3 lines

**Option C: Use compact inline buttons**
Replace the 3-line button row with inline icon buttons:
```css
FilePanel > #file-actions {
    height: 1;  /* Instead of 3 */
}
FilePanel > #file-actions > Button {
    min-width: 3;  /* Compact */
    padding: 0;
}
```

**Option D: Move buttons to keyboard shortcuts only**
- `a` = Select All (already exists)
- `d` = Deselect All (already exists)
- `r` = Refresh (already exists)

Remove the button row entirely, add tooltip or help text.

### Recommended: Option A + C combined
```
📁 Books ▾  (12 files)              [✓] [✗] [🔄]
[path input..................................]
[file list fills remaining space.............]
```

---

## Issue 3: Directory Selection UX

### Current Implementation
- Manual text input for path
- No autocomplete
- No visual browser
- No parent directory navigation

### Textual Capabilities Available

1. **DirectoryTree widget** - Full tree browser
2. **Input with suggestions** - Autocomplete capability
3. **Custom completion** - Can implement path completion

### Recommended Solutions

**Option A: DirectoryTree Browser (Modal)**
Add a "Browse" button that opens a modal with DirectoryTree:
```python
class DirectoryBrowserScreen(ModalScreen):
    def compose(self):
        yield DirectoryTree(".")
        yield Button("Select", id="select-dir")
```

**Option B: Path Autocomplete**
Implement path completion on the Input widget:
```python
def on_input_changed(self, event):
    path = Path(event.value)
    if path.parent.exists():
        suggestions = [p.name for p in path.parent.iterdir() if p.is_dir()]
        # Show suggestions dropdown
```

**Option C: Parent Navigation Button**
Add `[↑ Parent]` button next to path input:
```python
yield Button("↑", id="parent-dir")  # Navigate to parent
```

**Option D: Path History/Bookmarks**
- Remember recently used paths
- Allow bookmarking favorite directories

### Recommended: Option A + C
- Add `[📂 Browse]` button → opens DirectoryTree modal
- Add `[↑]` button → quick parent navigation
- Keep manual input for power users

---

## Issue 4: Export Text vs Export Only - Clarification

### Current Behavior

| Feature | Location | What it does |
|---------|----------|--------------|
| **Export Text** button | SettingsPanel | Exports ONE selected EPUB to .txt immediately, shows editing instructions |
| **Export Only** switch | SettingsPanel | When ON, batch conversion exports text but skips audio generation |

### The Confusion
These are different workflows but:
1. Names are too similar ("Export Text" vs "Export Only")
2. "Export Text" is an ACTION, not a setting
3. "Export Only" is a MODE, not an action
4. Both are in the "Settings" panel

### Recommendations

**Rename for clarity:**
- "Export Text" → **"Export & Edit"** (describes the workflow)
- "Export Only" → **"Text Only Mode"** or **"Skip Audio"**

**Relocate actions:**
- Move "Export & Edit" button OUT of Settings panel
- It's an action, belongs with "Preview Chapters" in a separate "Actions" section

**Proposed Settings Panel reorganization:**
```
⚙️ Settings

── Voice ──
Voice: [Select...]
Rate: [Normal ▾]
Volume: [Normal ▾]
[🔊 Preview Voice]

── Timing ──
Sentence Pause: [1.2s ▾]
Paragraph Pause: [1.2s ▾]

── Chapter Detection ──
Method: [Combined ▾]
Hierarchy: [Flat ▾]
Chapters: [e.g., 1-5, 1,3,7]

── Processing Mode ──
☐ Text Only (skip audio)
☑ Skip Existing
☐ Recursive Scan

── Audio Quality ──
☐ Normalize Volume
☐ Trim Silence

── Advanced ──
Pronunciation: [path...]
Voice Mapping: [path...]
```

**Move these buttons to FilePanel or a new Actions section:**
- Preview Chapters
- Export & Edit

---

## Issue 5: Settings Panel Audit

### Current Settings (22 options!)

| Setting | Purpose | Verdict |
|---------|---------|---------|
| Voice | TTS voice selection | ✅ Essential |
| Preview Voice | Test voice | ✅ Keep (but it's an action) |
| Rate | Speech speed | ✅ Keep |
| Volume | Speech volume | ✅ Keep |
| Sentence Pause | Pause timing | ⚠️ Advanced - collapse |
| Paragraph Pause | Pause timing | ⚠️ Advanced - collapse |
| Detection | Chapter detection method | ✅ Keep |
| Hierarchy | Title formatting | ⚠️ Could default to "auto" |
| Preview Chapters | Show chapter list | ❌ Move - it's an action |
| Export Text | Export for editing | ❌ Move - it's an action |
| Chapters | Chapter selection | ✅ Keep |
| Export Only | Skip audio generation | ✅ Keep (rename) |
| Skip Existing | Skip completed files | ✅ Keep |
| Recursive | Scan subdirs | ✅ Keep |
| Normalize | Audio normalization | ⚠️ Advanced - collapse |
| Trim Silence | Remove long pauses | ⚠️ Advanced - collapse |
| Pronunciation | Custom pronunciations | ⚠️ Advanced - collapse |
| Voice Mapping | Multi-voice support | ⚠️ Advanced - collapse |

### Recommendation: Collapsible Sections

```
⚙️ Settings

▼ Voice [expanded by default]
  Voice: [en-US-Andrew ▾]
  Rate: [Normal ▾]  Volume: [Normal ▾]
  [🔊 Preview]

▼ Chapters [expanded by default]
  Detection: [Combined ▾]
  Select: [e.g., 1-5]

▼ Processing [expanded by default]
  ☐ Text Only  ☑ Skip Existing  ☐ Recursive

▶ Timing [collapsed]
▶ Audio Quality [collapsed]
▶ Advanced [collapsed]
```

---

## Issue 6: Chapter/Structure Preview

### Current "Preview Chapters" Feature
- Shows chapter titles in Log panel
- Shows word count per chapter
- Just a list, no structure visualization

### Enhanced Preview Concept

**Option A: Dedicated Preview Panel**
Replace one of the bottom tabs with "Preview":
```
[Progress] [Queue] [Jobs] [Preview] [Log]
```

Preview tab contents:
```
📖 Book Preview: MyBook.epub
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Structure:
├── Part I: The Beginning
│   ├── Chapter 1: Origins (2,450 words, ~15 min)
│   ├── Chapter 2: Discovery (3,100 words, ~19 min)
│   └── Chapter 3: Journey (2,800 words, ~17 min)
├── Part II: The Middle
│   └── ...
└── Appendix (skipped)

Total: 45,000 words | ~4.5 hours estimated
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sample Text (Chapter 1):
"It was a dark and stormy night when the
protagonist first discovered the ancient..."

[◀ Prev Chapter] [▶ Next Chapter] [📋 Full Text]
```

**Option B: Modal Preview Screen**
Full-screen modal with:
- Tree view of chapters
- Text preview pane
- Estimated duration
- Option to edit chapter selection

**Option C: Enhanced Log Output**
Keep current approach but add:
- Tree-style indentation for hierarchy
- Estimated audio duration per chapter
- First sentence preview for each chapter
- Summary statistics

### Recommended: Option A (Preview Tab)
- Most discoverable
- Doesn't interrupt workflow
- Can show live updates as detection runs
- Natural place for "what will be processed" info

---

## Summary of Recommended Changes

### High Priority
1. **Fix Log anchoring** - CSS fix for TabbedContent height
2. **Rename Export options** - "Export & Edit" and "Text Only Mode"
3. **Add directory browser** - DirectoryTree modal + parent nav button

### Medium Priority
4. **Compact FilePanel** - Merge title row with mode toggle and file count
5. **Move action buttons** - Preview Chapters and Export & Edit out of Settings
6. **Add Preview tab** - Replace or add to bottom tabs

### Low Priority (Nice to have)
7. **Collapsible settings sections** - Group advanced options
8. **Path autocomplete** - Tab completion for directory input
9. **Estimated duration** - Show per-chapter and total time estimates

---

## Implementation Order

1. CSS fix for Log anchoring (quick fix)
2. Rename Export Text → "Export & Edit", Export Only → "Text Only"
3. Compact FilePanel layout
4. Add Browse button with DirectoryTree modal
5. Add Preview tab with enhanced chapter visualization
6. Reorganize Settings panel with collapsible sections
