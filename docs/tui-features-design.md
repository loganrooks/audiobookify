# TUI Features Design Document

This document provides detailed architectural designs for planned TUI features and identifies refactoring opportunities in the existing codebase.

---

## Table of Contents
1. [Codebase Analysis](#codebase-analysis)
2. [Path History](#path-history)
3. [Path Autocomplete](#path-autocomplete)
4. [Keyboard Navigation](#keyboard-navigation)
5. [Job Status Legend](#job-status-legend)
6. [Refactoring Recommendations](#refactoring-recommendations)
7. [Preview Tab & Chapter Approval Workflow](#preview-tab--chapter-approval-workflow)

---

## Codebase Analysis

### Current Architecture

```
epub2tts_edge/
├── tui.py                 # 2041 lines - TUI application (NEEDS SPLITTING)
├── job_manager.py         # 456 lines - Job persistence & management
├── batch_processor.py     # 786 lines - Batch processing logic
├── chapter_detector.py    # 914 lines - Chapter detection
├── epub2tts_edge.py       # 1102 lines - CLI & core logic
└── [feature modules]      # 200-500 lines each
```

### Established Patterns

| Pattern | Example | Used For |
|---------|---------|----------|
| **Config Dataclasses** | `BatchConfig`, `VoicePreviewConfig` | Feature configuration |
| **Manager Classes** | `JobManager`, `BatchProcessor` | Resource management |
| **JSON Persistence** | `~/.audiobookify/jobs/` | State & data storage |
| **Textual Widgets** | `FilePanel`, `JobsPanel` | UI components |

### Storage Locations
- **Jobs**: `~/.audiobookify/jobs/[job_id]/job.json`
- **Batch State**: `.audiobookify_state.json` (in working dir)
- **Config**: Not yet centralized (opportunity!)

---

## Path History

### Purpose
Remember recently used directories across sessions to speed up navigation.

### Design

#### Data Model
```python
# New file: epub2tts_edge/user_preferences.py

from dataclasses import dataclass, field
from pathlib import Path
import json
from datetime import datetime

@dataclass
class PathHistoryEntry:
    """A single entry in path history."""
    path: str
    last_used: float  # timestamp
    use_count: int = 1

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "last_used": self.last_used,
            "use_count": self.use_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PathHistoryEntry":
        return cls(**data)


@dataclass
class UserPreferences:
    """User preferences and history storage."""

    path_history: list[PathHistoryEntry] = field(default_factory=list)
    max_history_entries: int = 20

    # Future: other preferences
    # default_voice: str = "en-US-AndrewNeural"
    # default_rate: str | None = None
    # theme: str = "dark"

    CONFIG_DIR = Path.home() / ".audiobookify"
    CONFIG_FILE = "preferences.json"

    @classmethod
    def load(cls) -> "UserPreferences":
        """Load preferences from disk."""
        config_path = cls.CONFIG_DIR / cls.CONFIG_FILE
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                prefs = cls()
                prefs.path_history = [
                    PathHistoryEntry.from_dict(e)
                    for e in data.get("path_history", [])
                ]
                prefs.max_history_entries = data.get("max_history_entries", 20)
                return prefs
            except (json.JSONDecodeError, OSError):
                pass
        return cls()

    def save(self) -> None:
        """Save preferences to disk."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_path = self.CONFIG_DIR / self.CONFIG_FILE
        data = {
            "path_history": [e.to_dict() for e in self.path_history],
            "max_history_entries": self.max_history_entries,
        }
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_path(self, path: str) -> None:
        """Add or update a path in history."""
        path = str(Path(path).resolve())

        # Check if path already exists
        for entry in self.path_history:
            if entry.path == path:
                entry.last_used = datetime.now().timestamp()
                entry.use_count += 1
                break
        else:
            # New entry
            self.path_history.append(PathHistoryEntry(
                path=path,
                last_used=datetime.now().timestamp()
            ))

        # Sort by last_used (most recent first)
        self.path_history.sort(key=lambda e: e.last_used, reverse=True)

        # Trim to max entries
        self.path_history = self.path_history[:self.max_history_entries]

        self.save()

    def get_recent_paths(self, limit: int = 10) -> list[str]:
        """Get most recently used paths."""
        return [e.path for e in self.path_history[:limit]]

    def get_frequent_paths(self, limit: int = 10) -> list[str]:
        """Get most frequently used paths."""
        sorted_by_count = sorted(
            self.path_history,
            key=lambda e: e.use_count,
            reverse=True
        )
        return [e.path for e in sorted_by_count[:limit]]
```

#### TUI Integration

```python
# In tui.py - FilePanel modifications

class FilePanel(Vertical):
    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.current_path = Path(initial_path).resolve()
        self.files: list[Path] = []
        self.file_mode = "books"
        self.preferences = UserPreferences.load()  # NEW

    def compose(self) -> ComposeResult:
        with Horizontal(id="file-header"):
            yield Label("📁", classes="title")
            yield Label("(0)", classes="file-count", id="file-count")
            yield Button("📚", id="mode-books", classes="active")
            yield Button("📝", id="mode-text")
            yield Button("📜", id="show-history")  # NEW: History button
        # ... rest of compose

    def action_show_history(self) -> None:
        """Show path history dropdown or modal."""
        recent = self.preferences.get_recent_paths(10)
        if recent:
            # Option 1: Push a selection screen
            self.app.push_screen(PathHistoryScreen(recent), self._on_path_selected)

    def _on_path_selected(self, path: str | None) -> None:
        """Handle path selection from history."""
        if path:
            self.current_path = Path(path)
            self.query_one("#path-input", Input).value = path
            self.scan_directory()

    def scan_directory(self) -> None:
        # Existing code...
        # ADD: Record path usage
        self.preferences.add_path(str(self.current_path))


class PathHistoryScreen(ModalScreen):
    """Modal screen for selecting from path history."""

    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.paths = paths

    def compose(self) -> ComposeResult:
        with Vertical(id="history-container"):
            yield Label("📜 Recent Directories", id="history-title")
            yield ListView(id="history-list")
            yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        history_list = self.query_one("#history-list", ListView)
        for path in self.paths:
            history_list.append(ListItem(Label(path)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        label = event.item.query_one(Label)
        self.dismiss(label.renderable)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
```

#### File Storage
```
~/.audiobookify/
├── jobs/                    # Existing
├── preferences.json         # NEW: User preferences including path history
```

#### preferences.json Example
```json
{
  "path_history": [
    {"path": "/home/user/Books/SciFi", "last_used": 1733356800.0, "use_count": 15},
    {"path": "/home/user/Downloads", "last_used": 1733270400.0, "use_count": 3},
    {"path": "/mnt/library/Audiobooks", "last_used": 1733184000.0, "use_count": 8}
  ],
  "max_history_entries": 20
}
```

---

## Path Autocomplete

### Purpose
Tab completion for directory paths while typing, similar to shell behavior.

### Design

#### Approach: Custom Input with Suggestions

```python
# New file: epub2tts_edge/tui_widgets.py

from pathlib import Path
from textual.widgets import Input, Static
from textual.containers import Vertical
from textual.message import Message

class PathInput(Input):
    """Input widget with path autocomplete support."""

    class SuggestionsChanged(Message):
        """Message sent when suggestions change."""
        def __init__(self, suggestions: list[str]) -> None:
            self.suggestions = suggestions
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.suggestions: list[str] = []
        self._suggestion_index = -1

    def on_key(self, event) -> None:
        """Handle Tab key for autocomplete."""
        if event.key == "tab":
            event.prevent_default()
            self._complete()
        elif event.key == "shift+tab":
            event.prevent_default()
            self._complete(reverse=True)

    def watch_value(self, value: str) -> None:
        """Update suggestions when value changes."""
        self._update_suggestions(value)

    def _update_suggestions(self, value: str) -> None:
        """Generate path suggestions based on current input."""
        if not value:
            self.suggestions = []
            self._suggestion_index = -1
            return

        path = Path(value)

        # If the path ends with separator, list contents
        if value.endswith("/") or value.endswith("\\"):
            if path.is_dir():
                self.suggestions = self._get_directory_contents(path)
            else:
                self.suggestions = []
        else:
            # Complete the current path component
            parent = path.parent
            partial = path.name

            if parent.exists() and parent.is_dir():
                self.suggestions = [
                    str(p) for p in parent.iterdir()
                    if p.is_dir() and p.name.lower().startswith(partial.lower())
                ]
            else:
                self.suggestions = []

        self._suggestion_index = -1
        self.post_message(self.SuggestionsChanged(self.suggestions))

    def _get_directory_contents(self, path: Path) -> list[str]:
        """Get list of subdirectories in a path."""
        try:
            return sorted([
                str(p) for p in path.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ])
        except PermissionError:
            return []

    def _complete(self, reverse: bool = False) -> None:
        """Apply next/previous suggestion."""
        if not self.suggestions:
            return

        if reverse:
            self._suggestion_index -= 1
            if self._suggestion_index < 0:
                self._suggestion_index = len(self.suggestions) - 1
        else:
            self._suggestion_index += 1
            if self._suggestion_index >= len(self.suggestions):
                self._suggestion_index = 0

        self.value = self.suggestions[self._suggestion_index]
        self.cursor_position = len(self.value)


class PathInputWithSuggestions(Vertical):
    """Path input with visible suggestion dropdown."""

    DEFAULT_CSS = """
    PathInputWithSuggestions {
        height: auto;
    }

    PathInputWithSuggestions > #suggestions {
        height: auto;
        max-height: 5;
        background: $surface-darken-2;
        display: none;
    }

    PathInputWithSuggestions > #suggestions.visible {
        display: block;
    }

    PathInputWithSuggestions > #suggestions > Static {
        height: 1;
        padding: 0 1;
    }

    PathInputWithSuggestions > #suggestions > Static.selected {
        background: $primary;
    }
    """

    def __init__(self, placeholder: str = "", value: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.initial_value = value
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield PathInput(
            placeholder=self.placeholder,
            value=self.initial_value,
            id="path-input"
        )
        yield Vertical(id="suggestions")

    def on_path_input_suggestions_changed(
        self, event: PathInput.SuggestionsChanged
    ) -> None:
        """Update suggestion display."""
        suggestions_container = self.query_one("#suggestions", Vertical)
        suggestions_container.remove_children()

        if event.suggestions:
            suggestions_container.add_class("visible")
            for i, suggestion in enumerate(event.suggestions[:5]):
                display_path = Path(suggestion).name
                suggestions_container.mount(
                    Static(f"  {display_path}", classes=f"suggestion-{i}")
                )
        else:
            suggestions_container.remove_class("visible")
```

#### Integration with FilePanel

```python
# In FilePanel.compose():
def compose(self) -> ComposeResult:
    with Horizontal(id="file-header"):
        # ... existing header
    yield PathInputWithSuggestions(
        placeholder="Enter folder path...",
        value=str(self.current_path),
        id="path-container"
    )
    yield ListView(id="file-list")
    # ... rest
```

---

## Keyboard Navigation

### Purpose
Comprehensive keyboard control for the entire TUI without requiring a mouse.

### Current State

```python
BINDINGS = [
    Binding("q", "quit", "Quit"),
    Binding("s", "start", "Start"),
    Binding("escape", "stop", "Stop"),
    Binding("r", "refresh", "Refresh"),
    Binding("a", "select_all", "Select All"),
    Binding("d", "deselect_all", "Deselect All"),
    Binding("p", "preview_voice", "Preview Voice"),
    Binding("?", "help", "Help"),
    Binding("ctrl+d", "toggle_debug", "Debug"),
]
```

### Proposed Additions

#### Global Navigation
| Key | Action | Description |
|-----|--------|-------------|
| `Tab` | `focus_next` | Move to next panel |
| `Shift+Tab` | `focus_prev` | Move to previous panel |
| `1` | `tab_progress` | Switch to Progress tab |
| `2` | `tab_queue` | Switch to Queue tab |
| `3` | `tab_jobs` | Switch to Jobs tab |
| `4` | `tab_log` | Switch to Log tab |
| `F1` | `show_help` | Show help modal |

#### File Panel
| Key | Action | Description |
|-----|--------|-------------|
| `Enter` | `toggle_selected` | Toggle current file selection |
| `Space` | `toggle_selected` | Toggle current file selection |
| `/` | `focus_path` | Focus path input |
| `Backspace` | `parent_dir` | Go to parent directory |
| `h` | `show_history` | Show path history |

#### Jobs Panel
| Key | Action | Description |
|-----|--------|-------------|
| `Enter` | `toggle_job` | Toggle job selection |
| `R` | `resume_jobs` | Resume selected jobs |
| `X` | `delete_jobs` | Delete selected jobs |

### Implementation

```python
# In AudiobookifyApp

BINDINGS = [
    # Existing
    Binding("q", "quit", "Quit"),
    Binding("s", "start", "Start"),
    Binding("escape", "stop", "Stop"),
    Binding("r", "refresh", "Refresh"),
    Binding("a", "select_all", "Select All"),
    Binding("d", "deselect_all", "Deselect All"),
    Binding("p", "preview_voice", "Preview Voice"),
    Binding("?", "help", "Help"),
    Binding("ctrl+d", "toggle_debug", "Debug"),

    # NEW: Tab switching
    Binding("1", "tab_progress", "Progress", show=False),
    Binding("2", "tab_queue", "Queue", show=False),
    Binding("3", "tab_jobs", "Jobs", show=False),
    Binding("4", "tab_log", "Log", show=False),

    # NEW: Navigation
    Binding("tab", "focus_next", "Next Panel", show=False),
    Binding("shift+tab", "focus_prev", "Prev Panel", show=False),
    Binding("/", "focus_path", "Go to Path", show=False),
    Binding("backspace", "parent_dir", "Parent Dir", show=False),
    Binding("h", "show_history", "History", show=False),

    # NEW: Job operations
    Binding("R", "resume_jobs", "Resume Jobs", show=False),
    Binding("X", "delete_jobs", "Delete Jobs", show=False),

    # NEW: Help
    Binding("f1", "show_help_modal", "Help", show=False),
]

def action_tab_progress(self) -> None:
    """Switch to Progress tab."""
    self.query_one("#bottom-tabs", TabbedContent).active = "progress-tab"

def action_tab_queue(self) -> None:
    """Switch to Queue tab."""
    self.query_one("#bottom-tabs", TabbedContent).active = "queue-tab"

def action_tab_jobs(self) -> None:
    """Switch to Jobs tab."""
    self.query_one("#bottom-tabs", TabbedContent).active = "jobs-tab"

def action_tab_log(self) -> None:
    """Switch to Log tab."""
    self.query_one("#bottom-tabs", TabbedContent).active = "log-tab"

def action_focus_path(self) -> None:
    """Focus the path input field."""
    self.query_one("#path-input", Input).focus()

def action_parent_dir(self) -> None:
    """Navigate to parent directory."""
    file_panel = self.query_one(FilePanel)
    parent = file_panel.current_path.parent
    if parent.exists():
        file_panel.current_path = parent
        file_panel.query_one("#path-input", Input).value = str(parent)
        file_panel.scan_directory()

def action_show_history(self) -> None:
    """Show path history modal."""
    file_panel = self.query_one(FilePanel)
    file_panel.action_show_history()

def action_resume_jobs(self) -> None:
    """Resume selected jobs (capital R for safety)."""
    self.action_resume_job()

def action_delete_jobs(self) -> None:
    """Delete selected jobs (capital X for safety)."""
    self.action_delete_job()

def action_show_help_modal(self) -> None:
    """Show comprehensive help modal."""
    self.push_screen(HelpScreen())
```

### Help Screen

```python
class HelpScreen(ModalScreen):
    """Modal showing all keyboard shortcuts."""

    BINDINGS = [("escape", "dismiss", "Close"), ("?", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }

    #help-container > Label.title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #help-container > Label.section {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("⌨️  Keyboard Shortcuts", classes="title")

            yield Label("── Global ──", classes="section")
            yield Static("  q          Quit")
            yield Static("  s          Start conversion")
            yield Static("  Esc        Stop conversion")
            yield Static("  r          Refresh")
            yield Static("  Tab        Next panel")
            yield Static("  Shift+Tab  Previous panel")
            yield Static("  1-4        Switch bottom tabs")
            yield Static("  ?/F1       This help")

            yield Label("── File Selection ──", classes="section")
            yield Static("  a          Select all files")
            yield Static("  d          Deselect all")
            yield Static("  /          Focus path input")
            yield Static("  Backspace  Parent directory")
            yield Static("  h          Path history")

            yield Label("── Jobs ──", classes="section")
            yield Static("  R          Resume selected")
            yield Static("  X          Delete selected")
            yield Static("  ↑/↓        Move in queue")

            yield Label("── Voice ──", classes="section")
            yield Static("  p          Preview voice")

            yield Static("")
            yield Static("  Press Esc or ? to close", classes="hint")
```

---

## Job Status Legend

### Purpose
Help users understand what each job status icon means.

### Design Options

#### Option A: Tooltip on Hover (Limited in TUI)
Textual has limited tooltip support. Not recommended.

#### Option B: Legend Button in JobsPanel

```python
# In JobsPanel

def compose(self) -> ComposeResult:
    with Horizontal(id="jobs-header"):
        yield Label("💼 Jobs", classes="title")
        yield Label("(0)", id="job-count", classes="count")
        yield Button("❓", id="job-legend")  # NEW: Legend button
    yield ListView(id="jobs-list")
    # ... buttons


class JobStatusLegendScreen(ModalScreen):
    """Modal explaining job status icons."""

    BINDINGS = [("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    JobStatusLegendScreen {
        align: center middle;
    }

    #legend-container {
        width: 50;
        height: auto;
        background: $surface;
        border: round $secondary;
        padding: 1 2;
    }

    #legend-container > Label.title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="legend-container"):
            yield Label("📊 Job Status Icons", classes="title")
            yield Static("")
            yield Static("  ⏳  Pending      - Waiting to start")
            yield Static("  📝  Extracting   - Extracting text from book")
            yield Static("  🔊  Converting   - Generating audio")
            yield Static("  📦  Finalizing   - Creating M4B file")
            yield Static("  ✅  Completed    - Done successfully")
            yield Static("  ❌  Failed       - Error occurred")
            yield Static("  🚫  Cancelled    - Stopped by user")
            yield Static("")
            yield Static("  🔄  Resumable    - Can be resumed")
            yield Static("")
            yield Button("Close", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
```

#### Option C: Inline Legend in JobsPanel Header

```python
# Compact legend shown in header when panel is focused

JobsPanel > #jobs-legend {
    display: none;
    height: 1;
    color: $text-muted;
}

JobsPanel:focus-within > #jobs-legend {
    display: block;
}
```

### Recommended: Option B
A button that opens a modal is the clearest UX and follows established patterns (like the `?` help).

---

## Refactoring Recommendations

### 1. Split tui.py (HIGH PRIORITY)

**Current**: 2041 lines in single file
**Problem**: Hard to navigate, test, and maintain

**Proposed Structure**:
```
epub2tts_edge/
├── tui/
│   ├── __init__.py          # Exports AudiobookifyApp
│   ├── app.py               # Main AudiobookifyApp class
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── file_panel.py    # FilePanel, EPUBFileItem
│   │   ├── settings_panel.py
│   │   ├── progress_panel.py
│   │   ├── queue_panel.py
│   │   ├── jobs_panel.py    # JobsPanel, JobItem
│   │   └── log_panel.py
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── help_screen.py
│   │   ├── history_screen.py
│   │   └── legend_screen.py
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── path_input.py    # PathInput, PathInputWithSuggestions
│   │   └── voice_status.py  # VoicePreviewStatus
│   └── styles.py            # Centralized CSS
```

**Migration Strategy**:
1. Create `tui/` directory structure
2. Extract one panel at a time, starting with smallest (LogPanel)
3. Update imports incrementally
4. Maintain backward compatibility with `from epub2tts_edge.tui import AudiobookifyApp`

### 2. Centralize User Preferences (MEDIUM PRIORITY)

**Current**: No centralized user preferences
**Proposed**: `UserPreferences` class (as designed above)

**Benefits**:
- Path history (designed above)
- Future: Default voice, theme, window size
- Future: Per-project settings

### 3. Extract Configuration Management (MEDIUM PRIORITY)

**Current**: Various `*Config` dataclasses scattered across modules
**Proposed**: Central config registry

```python
# epub2tts_edge/config.py

from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class AppConfig:
    """Central application configuration."""

    # Storage
    config_dir: Path = Path.home() / ".audiobookify"
    jobs_dir: Path = config_dir / "jobs"

    # Defaults
    default_voice: str = "en-US-AndrewNeural"
    default_detection: str = "combined"
    default_hierarchy: str = "flat"

    # TUI
    max_path_history: int = 20
    debug_mode: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from disk."""
        # Implementation
        pass

    def save(self) -> None:
        """Save config to disk."""
        pass
```

### 4. Improve Error Handling (LOW PRIORITY)

**Current**: Mix of try/except patterns, some silent failures
**Issue Found**: DataTable `get_row_at()` bug was silent due to broad `except Exception`

**Recommendation**:
- Use specific exception types
- Log errors even when handling gracefully
- Consider custom exception hierarchy (already exists in `errors.py`)

### 5. Add Type Hints Throughout (LOW PRIORITY)

**Current**: Partial type hints
**Recommendation**: Full type hints for better IDE support and documentation

---

## Preview Tab & Chapter Approval Workflow

### Purpose
Transform the chapter preview from log output to an interactive Preview tab where users can review, approve, edit, remove, and merge chapters before processing.

### Current State
- Chapter preview outputs to Log panel
- No interactive editing
- Users must export to text file, edit externally, then reimport

### Proposed Workflow

```
1. User selects EPUB file(s)
2. User clicks "Preview Chapters" or presses designated key
3. Preview tab opens automatically showing:
   - Chapter tree with checkboxes
   - Paragraph count per chapter
   - Word count per chapter
   - Expandable content preview
4. User can:
   - ✅ Approve chapters (check/uncheck to include/exclude)
   - 🔀 Merge chapters (select multiple → merge button)
   - ✂️ Split chapters (coming later)
   - 👁️ Preview content (expand to see first N paragraphs)
5. User clicks "Start" to process approved chapters only
```

### Data Model

```python
from dataclasses import dataclass, field
from enum import Enum

class ChapterAction(Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    MERGE_WITH_PREVIOUS = "merge_prev"
    MERGE_WITH_NEXT = "merge_next"

@dataclass
class PreviewChapter:
    """A chapter in the preview with editing state."""
    original_node: "ChapterNode"  # Reference to original
    title: str
    word_count: int
    paragraph_count: int
    content_preview: str  # First 500 chars or 3 paragraphs
    included: bool = True
    merged_into: int | None = None  # Index of chapter this merges into
    children: list["PreviewChapter"] = field(default_factory=list)

@dataclass
class ChapterPreviewState:
    """State for the preview workflow."""
    source_file: Path
    detection_method: str
    chapters: list[PreviewChapter]
    modified: bool = False

    def get_included_chapters(self) -> list[PreviewChapter]:
        """Get chapters that are included (not excluded or merged)."""
        return [c for c in self.chapters if c.included and c.merged_into is None]

    def merge_chapters(self, indices: list[int]) -> None:
        """Merge selected chapters into the first one."""
        if len(indices) < 2:
            return
        primary = indices[0]
        for idx in indices[1:]:
            self.chapters[idx].merged_into = primary
        self.modified = True
```

### UI Components

#### PreviewTab (New TabPane)

```python
class PreviewTab(TabPane):
    """Tab for interactive chapter preview and editing."""

    DEFAULT_CSS = '''
    PreviewTab {
        height: 100%;
    }

    #preview-header {
        height: auto;
        padding: 0 1;
        background: $surface-darken-1;
    }

    #chapter-tree {
        height: 1fr;
    }

    #preview-actions {
        height: auto;
        dock: bottom;
        padding: 1;
    }

    .chapter-item {
        height: auto;
        padding: 0 1;
    }

    .chapter-item.excluded {
        color: $text-muted;
        text-style: strike;
    }

    .chapter-item.merged {
        color: $warning;
        text-style: italic;
    }

    #content-preview {
        height: auto;
        max-height: 10;
        background: $surface-darken-2;
        padding: 1;
        display: none;
    }

    #content-preview.visible {
        display: block;
    }
    '''

    def compose(self) -> ComposeResult:
        with Vertical():
            # Header with book info
            with Horizontal(id="preview-header"):
                yield Label("📖 ", id="book-icon")
                yield Label("No book selected", id="book-title")
                yield Label("", id="chapter-stats")

            # Chapter tree with checkboxes
            yield ListView(id="chapter-tree")

            # Content preview pane (expandable)
            yield Static("", id="content-preview")

            # Action buttons
            with Horizontal(id="preview-actions"):
                yield Button("☑ All", id="preview-select-all")
                yield Button("☐ None", id="preview-select-none")
                yield Button("🔀 Merge", id="preview-merge", disabled=True)
                yield Button("👁️ Preview", id="preview-content")
                yield Button("✅ Approve & Start", id="preview-approve", variant="success")
```

#### ChapterPreviewItem (ListItem widget)

```python
class ChapterPreviewItem(ListItem):
    """Interactive chapter item with checkbox."""

    def __init__(self, chapter: PreviewChapter, index: int) -> None:
        super().__init__()
        self.chapter = chapter
        self.index = index
        self.is_selected = False  # For multi-select merge operations

    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.chapter.included else "☐"
        indent = "  " * (self.chapter.original_node.level - 1)
        stats = f"({self.chapter.word_count:,}w, {self.chapter.paragraph_count}¶)"

        status = ""
        if self.chapter.merged_into is not None:
            status = " [merged]"

        yield Label(f"{checkbox} {indent}{self.chapter.title} {stats}{status}")

    def toggle_include(self) -> None:
        """Toggle chapter inclusion."""
        self.chapter.included = not self.chapter.included
        self.refresh()

    def toggle_select(self) -> None:
        """Toggle selection for merge operations."""
        self.is_selected = not self.is_selected
        self.refresh()
```

### Integration Points

#### 1. Bottom Tabs Update

```python
# In AudiobookifyApp.compose()
with TabbedContent(id="bottom-tabs"):
    with TabPane("Progress", id="progress-tab"):
        yield ProgressPanel()
    with TabPane("Preview", id="preview-tab"):  # NEW
        yield PreviewTab()
    with TabPane("Queue", id="queue-tab"):
        yield QueuePanel()
    with TabPane("Jobs", id="jobs-tab"):
        yield JobsPanel(job_manager=self.job_manager)
    with TabPane("Log", id="log-tab"):
        yield LogPanel()
```

#### 2. Preview Workflow

```python
def action_preview_chapters(self) -> None:
    """Preview chapters in the Preview tab instead of log."""
    selected = [item.path for item in self.query(EPUBFileItem) if item.is_selected]

    if not selected:
        self.notify("Select a file to preview", severity="warning")
        return

    if len(selected) > 1:
        self.notify("Select only one file for preview", severity="warning")
        return

    epub_path = selected[0]

    # Switch to Preview tab
    self.query_one("#bottom-tabs", TabbedContent).active = "preview-tab"

    # Load chapters into preview
    preview_tab = self.query_one(PreviewTab)
    preview_tab.load_chapters(epub_path, self.get_settings())
```

#### 3. Processing Approved Chapters

```python
def process_with_preview(self) -> None:
    """Process only approved chapters from preview."""
    preview_tab = self.query_one(PreviewTab)

    if not preview_tab.has_chapters():
        self.notify("No chapters to process", severity="warning")
        return

    approved = preview_tab.get_approved_chapters()

    if not approved:
        self.notify("No chapters selected", severity="warning")
        return

    # Create modified chapter list for processing
    # Pass to existing processing pipeline with filtered chapters
    self.process_approved_chapters(
        preview_tab.source_file,
        approved,
        self.get_settings()
    )
```

### Keyboard Shortcuts

| Key | Action | Context |
|-----|--------|---------|
| `5` | Switch to Preview tab | Global |
| `Space` | Toggle chapter inclusion | Preview tab focused |
| `Enter` | Expand/collapse content preview | Preview tab focused |
| `m` | Merge selected chapters | Preview tab, multiple selected |
| `u` | Unmerge chapter | Preview tab, merged chapter selected |

### Implementation Phases

**Phase 1: Basic Preview Tab**
- Create PreviewTab widget
- Move chapter preview from log to tab
- Add chapter tree with stats
- Keyboard shortcut to switch to tab

**Phase 2: Interactive Selection**
- Add checkboxes for include/exclude
- Select all / Select none buttons
- Chapter exclusion affects processing

**Phase 3: Chapter Merging**
- Multi-select for merge operations
- Merge button combines chapters
- Visual indication of merged chapters
- Unmerge capability

**Phase 4: Content Preview**
- Expandable content preview pane
- Show first N paragraphs
- Highlight potential issues (very short chapters, etc.)

### Visual Mockup

```
┌─ Preview ─────────────────────────────────────────┐
│ 📖 Writing and Difference              46 ch, 120k words │
├───────────────────────────────────────────────────┤
│ ☑ 1. Force and Signification        (12,340w, 45¶) │
│ ☑ 2. Cogito and History of Madness  (8,210w, 32¶)  │
│ ☐ 3. Edmond Jabès and the Question  (5,670w, 22¶)  │
│ ☑ 4. Violence and Metaphysics       (15,890w, 58¶) │
│   └─ [merged with 5]                               │
│ ☑ 5. "Genesis and Structure"        (9,450w, 38¶)  │
│ ...                                                │
├───────────────────────────────────────────────────┤
│ Content Preview:                                   │
│ "The concept of force is central to Derrida's     │
│  critique of structuralism. He argues that..."    │
├───────────────────────────────────────────────────┤
│ [☑ All] [☐ None] [🔀 Merge] [👁️ Preview] [✅ Approve & Start] │
└───────────────────────────────────────────────────┘
```

---

## Implementation Priority

| Feature | Priority | Effort | Dependencies |
|---------|----------|--------|--------------|
| **Preview Tab (Phase 1)** | HIGH | Medium | None ✅ DONE |
| **Preview Tab (Phase 2)** | HIGH | Medium | Phase 1 ✅ DONE |
| **Preview Tab (Phase 3)** | HIGH | Medium | Phase 2 ✅ DONE |
| **Keyboard Navigation** | HIGH | Small | None ✅ DONE |
| **Job Status Legend** | HIGH | Small | None |
| **Preview Tab (Phase 4)** | MEDIUM | Medium | Phase 3 |
| **tui.py split** | MEDIUM | Large | None |
| **Path History** | MEDIUM | Medium | UserPreferences class |
| **Path Autocomplete** | MEDIUM | Medium | PathInput widget |
| **User Preferences** | MEDIUM | Medium | None |

### Recommended Order
1. ✅ **Keyboard Navigation** - DONE
2. ✅ **Preview Tab Phase 1** - Basic interactive preview - DONE
3. ✅ **Preview Tab Phase 2** - Include/exclude affects processing - DONE
4. ✅ **Preview Tab Phase 3** - Chapter merging and deletion - DONE
5. **Job Status Legend** - Quick win, helps users
6. **Preview Tab Phase 4** - Content preview pane
7. **Split tui.py** - Foundational for future work
8. **User Preferences** - Enables path history
9. **Path History** - Depends on UserPreferences
10. **Path Autocomplete** - Most complex, do last

---

## Change History

| Date | Author | Description |
|------|--------|-------------|
| 2024-12-04 | Claude | Initial design document |
| 2024-12-05 | Claude | Added Preview Tab & Chapter Approval Workflow design |
| 2024-12-05 | Claude | Marked Preview Tab Phases 1 & 2 as complete |
| 2024-12-05 | Claude | Added Phase 3: merge/delete functionality with keyboard shortcuts |
| 2024-12-05 | Claude | Enhanced merge: exports merged content directly to text file for processing |
