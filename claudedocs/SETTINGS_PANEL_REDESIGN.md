# Settings Panel Redesign

## Overview

Redesign the current monolithic SettingsPanel into a more organized, tabbed interface with clear separation between configuration (settings) and operations (actions).

## Current State

### Problems

1. **Mixed Concerns**: Settings and action buttons are combined in one scrolling panel
2. **Overwhelming Options**: All settings visible at once, regardless of relevance
3. **No Logical Grouping**: Voice settings mixed with detection settings mixed with output options
4. **Poor Discoverability**: Advanced options hidden among common ones

### Current Layout (SettingsPanel)

```
┌─────────────────────────────┐
│ Voice Selection             │
│ Rate                        │
│ Volume                      │
│ Detection Method            │
│ Hierarchy Style             │
│ Paragraph Pause             │
│ Sentence Pause              │
│ Normalize Audio             │
│ Trim Silence                │
│ ... more settings ...       │
│                             │
│ [Preview Chapters]          │
│ [Process Selected]          │
│ [Clear Selection]           │
└─────────────────────────────┘
```

---

## Proposed Design

### Structure: Split Panel + Tabbed Settings

```
┌─────────────────────────────┐
│ ═══ SETTINGS ═══            │
│ ┌─────────────────────────┐ │
│ │ Voice │ Timing │ Output │ │  ← Tab bar
│ ├─────────────────────────┤ │
│ │                         │ │
│ │   (Tab Content)         │ │  ← Settings for selected tab
│ │                         │ │
│ │                         │ │
│ └─────────────────────────┘ │
│                             │
│ ═══ ACTIONS ═══             │
│ ┌─────────────────────────┐ │
│ │ [Preview Chapters]      │ │
│ │ [Process Selected]      │ │
│ │ [Clear Selection]       │ │
│ │ [Export to Text]        │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

---

## Tab Organization

### Tab 1: Voice

Primary voice and speech settings.

```python
# Contents
- Voice Selection (dropdown with search)
- Speech Rate (-50% to +50%)
- Volume (-50% to +50%)
- Voice Preview button (inline sample)
```

### Tab 2: Timing

Pause and silence settings.

```python
# Contents
- Paragraph Pause (ms)
- Sentence Pause (ms)
- Trim Silence (checkbox)
- Silence Threshold (dBFS, shown if Trim enabled)
- Max Silence Duration (ms, shown if Trim enabled)
```

### Tab 3: Output

Output format and quality settings.

```python
# Contents
- Normalize Audio (checkbox)
- Normalization Target (dBFS, shown if Normalize enabled)
- Normalization Method (peak/rms, shown if Normalize enabled)
- Output Format (future: m4b/mp3/opus)
- Output Naming Template (future)
```

### Tab 4: Detection (Context-Sensitive)

Chapter detection settings. Only shown when relevant.

```python
# Contents
- Detection Method (toc/headings/combined/auto)
- Hierarchy Style (flat/numbered/arrow/breadcrumb/indented)
- Include Empty Chapters (checkbox)
```

### Tab 5: Advanced (Optional)

Power user settings.

```python
# Contents
- Pronunciation Dictionary
- Voice Mapping (multi-voice)
- Narrator Voice
- Processing Concurrency (future)
```

---

## Actions Panel

Separate, always-visible section for operations.

### Primary Actions

```python
# File context (files selected in FilePanel)
- "Preview Chapters" - Load chapters for editing
- "Process Selected" - Start processing selected files

# Preview context (chapters loaded in PreviewPanel)
- "Start All" - Process all remaining chapters
- "Export Text" - Export to text file only

# Common
- "Clear Selection" - Clear file selection
```

### Contextual Visibility

Actions should enable/disable based on context:

```python
class ActionsPanel(Widget):
    def update_context(self, context: str):
        """Update button states based on current context."""
        if context == "file_selection":
            self.preview_btn.disabled = not self.has_files_selected
            self.process_btn.disabled = not self.has_files_selected
            self.start_all_btn.disabled = True

        elif context == "preview_editing":
            self.preview_btn.disabled = True
            self.process_btn.disabled = True
            self.start_all_btn.disabled = not self.has_chapters
```

---

## Implementation

### Component Structure

```python
# New files in tui/panels/
├── settings/
│   ├── __init__.py
│   ├── settings_panel.py      # Main tabbed container
│   ├── voice_tab.py           # Voice settings
│   ├── timing_tab.py          # Timing settings
│   ├── output_tab.py          # Output settings
│   ├── detection_tab.py       # Detection settings
│   └── advanced_tab.py        # Advanced settings
├── actions_panel.py           # Actions section
```

### Textual Implementation

```python
# settings_panel.py
from textual.widgets import TabbedContent, TabPane

class SettingsPanel(Widget):
    """Tabbed settings panel."""

    def compose(self) -> ComposeResult:
        yield Static("═══ SETTINGS ═══", classes="section-header")

        with TabbedContent():
            with TabPane("Voice", id="voice-tab"):
                yield VoiceTab()
            with TabPane("Timing", id="timing-tab"):
                yield TimingTab()
            with TabPane("Output", id="output-tab"):
                yield OutputTab()
            with TabPane("Detection", id="detection-tab"):
                yield DetectionTab()


class ActionsPanel(Widget):
    """Always-visible actions section."""

    def compose(self) -> ComposeResult:
        yield Static("═══ ACTIONS ═══", classes="section-header")

        with Container(id="actions-container"):
            yield Button("Preview Chapters", id="preview-btn")
            yield Button("Process Selected", id="process-btn")
            yield Button("Start All", id="start-all-btn", disabled=True)
            yield Button("Export Text", id="export-btn", disabled=True)
            yield Button("Clear Selection", id="clear-btn")
```

### CSS Styling

```css
/* Settings tabs */
SettingsPanel TabbedContent {
    height: auto;
    max-height: 60%;
}

SettingsPanel TabPane {
    padding: 1;
}

/* Actions section */
ActionsPanel {
    height: auto;
    dock: bottom;
    padding: 1;
}

ActionsPanel Button {
    width: 100%;
    margin-bottom: 1;
}

ActionsPanel Button.primary {
    background: $primary;
}
```

---

## Progressive Disclosure

### Conditional Visibility

Show advanced options only when relevant:

```python
class TimingTab(Widget):
    def on_checkbox_changed(self, event: Checkbox.Changed):
        if event.checkbox.id == "trim-silence":
            # Show/hide silence threshold controls
            self.query_one("#silence-options").display = event.value
```

### Tooltips / Help

Add inline help for complex settings:

```python
yield Static("Normalization Target", classes="label")
yield Input(id="norm-target", value="-16.0")
yield Static("(dBFS, -20 to -10 typical)", classes="help-text")
```

---

## Settings Profiles (Future)

### Profile System

```python
@dataclass
class SettingsProfile:
    name: str
    voice: str
    rate: str | None
    volume: str | None
    paragraph_pause: int
    sentence_pause: int
    normalize: bool
    trim_silence: bool
    # ... other settings

# Built-in profiles
PROFILES = {
    "default": SettingsProfile(...),
    "quick_draft": SettingsProfile(rate="+20%", ...),
    "high_quality": SettingsProfile(normalize=True, trim_silence=True, ...),
}
```

### Profile Selector

```python
class SettingsPanel(Widget):
    def compose(self) -> ComposeResult:
        yield Static("═══ SETTINGS ═══", classes="section-header")

        # Profile selector at top
        yield Select(
            options=[(name, name) for name in PROFILES.keys()],
            id="profile-selector",
            prompt="Profile: Custom",
        )

        # Tabs below
        with TabbedContent():
            # ...
```

---

## Migration Strategy

### Phase 1: Structural Split

1. Create ActionsPanel as separate widget
2. Move action buttons from SettingsPanel to ActionsPanel
3. Update layout in AudiobookifyApp
4. Test all action functionality

### Phase 2: Tab Implementation

1. Add TabbedContent to SettingsPanel
2. Group existing settings into tabs
3. Update CSS for new layout
4. Test settings persistence

### Phase 3: Progressive Disclosure

1. Add conditional visibility
2. Implement context-sensitive actions
3. Add help text / tooltips
4. User testing and refinement

### Phase 4: Profiles (v2.5.0+)

1. Implement SettingsProfile dataclass
2. Create profile management
3. Add profile selector UI
4. Enable save/load custom profiles

---

## Implementation Checklist

### Phase 1: Structural Split
- [ ] Create ActionsPanel widget
- [ ] Move action buttons
- [ ] Update AudiobookifyApp.compose()
- [ ] Wire up action handlers
- [ ] Test all buttons work

### Phase 2: Tab Implementation
- [ ] Add TabbedContent to SettingsPanel
- [ ] Create VoiceTab
- [ ] Create TimingTab
- [ ] Create OutputTab
- [ ] Create DetectionTab
- [ ] Update CSS
- [ ] Test settings changes apply

### Phase 3: Enhancements
- [ ] Conditional visibility for dependent settings
- [ ] Context-sensitive action enabling
- [ ] Help text / tooltips
- [ ] Keyboard shortcuts for tabs

### Phase 4: Profiles
- [ ] SettingsProfile dataclass
- [ ] Built-in profiles
- [ ] Profile selector UI
- [ ] Custom profile save/load

---

## Dependencies

```
Phase 1 (Structural Split) - Can start immediately
    ↓
Phase 2 (Tabs) - Requires Phase 1
    ↓
Phase 3 (Enhancements) - Requires Phase 2
    ↓
Phase 4 (Profiles) - Requires Phase 3
```

## Benefits

1. **Clearer Organization**: Related settings grouped together
2. **Reduced Cognitive Load**: See only relevant options
3. **Better Discoverability**: Tabs make sections obvious
4. **Separation of Concerns**: Settings vs Actions clearly distinct
5. **Future Extensibility**: Easy to add new tabs or profile system
