"""File panel for browsing and selecting files."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, ListItem, ListView

from ..screens import DirectoryBrowserScreen


class EPUBFileItem(ListItem):
    """A list item representing an EPUB file."""

    def __init__(
        self, path: Path, selected: bool = False, has_resumable_session: bool = False
    ) -> None:
        super().__init__()
        self.path = path
        self.is_selected = selected
        self.has_resumable_session = has_resumable_session

    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.is_selected else "☐"
        resume_indicator = " 🔄" if self.has_resumable_session else ""
        yield Label(f"{checkbox} {self.path.name}{resume_indicator}")

    def toggle(self) -> None:
        self.is_selected = not self.is_selected
        checkbox = "☑" if self.is_selected else "☐"
        resume_indicator = " 🔄" if self.has_resumable_session else ""
        self.query_one(Label).update(f"{checkbox} {self.path.name}{resume_indicator}")


class PathInput(Input):
    """Input widget with Tab completion for file paths."""

    class PathCompleted(Message):
        """Message sent when path completion occurs."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._completion_matches: list[Path] = []
        self._completion_index: int = 0

    def _get_completions(self, partial_path: str) -> list[Path]:
        """Get matching paths for the given partial path."""
        if not partial_path:
            return []

        path = Path(partial_path).expanduser()

        # Handle absolute vs relative paths
        if partial_path.startswith("/") or partial_path.startswith("~"):
            # Absolute path
            if path.exists() and path.is_dir():
                # If path is a complete directory, list its contents
                if partial_path.endswith("/"):
                    parent = path
                    prefix = ""
                else:
                    parent = path.parent
                    prefix = path.name.lower()
            else:
                parent = path.parent
                prefix = path.name.lower()
        else:
            # Relative path - treat as relative to current value's parent
            parent = path.parent if path.parent != path else Path(".")
            prefix = path.name.lower() if str(path) != "." else ""

        if not parent.exists():
            return []

        # Find matching entries
        try:
            matches = []
            for entry in parent.iterdir():
                # Skip hidden files unless user is explicitly typing a dot
                if entry.name.startswith(".") and not prefix.startswith("."):
                    continue
                if entry.name.lower().startswith(prefix):
                    matches.append(entry)
            # Sort: directories first, then alphabetically
            return sorted(matches, key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return []

    def _find_common_prefix(self, paths: list[Path]) -> str:
        """Find the longest common prefix among path names."""
        if not paths:
            return ""
        if len(paths) == 1:
            return paths[0].name

        names = [p.name for p in paths]
        min_len = min(len(n) for n in names)

        common = ""
        for i in range(min_len):
            char = names[0][i].lower()
            if all(n[i].lower() == char for n in names):
                common += names[0][i]  # Preserve original case
            else:
                break
        return common

    def _apply_completion(self, completed_path: Path) -> None:
        """Apply the completed path to the input."""
        result = str(completed_path)
        # Add trailing slash for directories to continue completion
        if completed_path.is_dir():
            result = result.rstrip("/") + "/"
        self.value = result
        self.cursor_position = len(result)
        self.post_message(self.PathCompleted(completed_path))

    def _key_tab(self, event) -> None:
        """Handle Tab key for path completion."""
        event.prevent_default()
        event.stop()

        current = self.value.strip()
        if not current:
            current = "."

        # Get fresh completions
        matches = self._get_completions(current)

        if not matches:
            self.app.bell()
            return

        if len(matches) == 1:
            # Single match - complete it
            self._apply_completion(matches[0])
            self._completion_matches = []
            self._completion_index = 0
        else:
            # Multiple matches
            # Check if we're cycling through previous matches
            if self._completion_matches and matches == self._completion_matches:
                # Cycle to next match
                self._completion_index = (self._completion_index + 1) % len(matches)
                self._apply_completion(matches[self._completion_index])
            else:
                # New completion - try common prefix first
                path = Path(current).expanduser()
                parent = path.parent if not current.endswith("/") else path
                common = self._find_common_prefix(matches)

                if common and len(common) > (len(path.name) if not current.endswith("/") else 0):
                    # Complete to common prefix
                    completed = parent / common
                    self.value = str(completed)
                    self.cursor_position = len(self.value)
                    self._completion_matches = matches
                    self._completion_index = 0
                else:
                    # No common prefix longer than current - start cycling
                    self._completion_matches = matches
                    self._completion_index = 0
                    self._apply_completion(matches[0])

    async def _on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "tab":
            self._key_tab(event)
        else:
            # Reset completion state on other keys
            self._completion_matches = []
            self._completion_index = 0


class FilePanel(Vertical):
    """Panel for browsing and selecting files (EPUB/MOBI or TXT)."""

    DEFAULT_CSS = """
    FilePanel {
        width: 1fr;
        height: 100%;
        border: round $primary;
        border-title-color: $primary;
        padding: 0 1;
        background: $surface;
    }

    FilePanel > #file-header {
        height: auto;
        margin-bottom: 0;
    }

    FilePanel > #file-header > Label.title {
        text-style: bold;
        color: $primary-lighten-2;
        width: auto;
    }

    FilePanel > #file-header > Label.file-count {
        color: $text-muted;
        margin-left: 1;
    }

    FilePanel > #file-header > Button {
        min-width: 6;
        height: auto;
        padding: 0;
        margin: 0 0 0 1;
    }

    FilePanel > #file-header > Button.active {
        background: $primary;
        color: $text;
    }

    FilePanel > #path-row {
        height: auto;
        margin-bottom: 0;
    }

    FilePanel > #path-row > #path-input {
        width: 1fr;
        margin-bottom: 0;
        border: round $primary-darken-1;
    }

    FilePanel > #path-row > .browse-btn {
        min-width: 4;
        width: auto;
        height: auto;
        padding: 0;
        margin-left: 1;
    }

    FilePanel > #file-list {
        height: 1fr;
        min-height: 3;
        border: round $primary-darken-2;
        background: $surface-darken-1;
    }

    FilePanel > #file-list > EPUBFileItem {
        height: 1;
        padding: 0;
    }

    FilePanel > #file-list > EPUBFileItem > Label {
        width: 100%;
        padding: 0 1;
    }

    FilePanel > #file-actions {
        height: auto;
        margin-top: 0;
        width: 100%;
    }

    FilePanel > #file-actions > Button {
        min-width: 4;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }

    FilePanel > #file-actions > Button.sel-btn {
        min-width: 6;
    }
    """

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.current_path = Path(initial_path).resolve()
        self.files: list[Path] = []
        self.file_mode = "books"  # "books" or "text"

    def compose(self) -> ComposeResult:
        with Horizontal(id="file-header"):
            yield Label("📁", classes="title", id="panel-title")
            yield Label("(0)", classes="file-count", id="file-count")
            yield Button("📚", id="mode-books", classes="active")
            yield Button("📝", id="mode-text")
        with Horizontal(id="path-row"):
            yield PathInput(
                placeholder="Enter folder path (Tab to complete)...",
                value=str(self.current_path),
                id="path-input",
            )
            yield Button("📂", id="browse-btn", classes="browse-btn")
        yield ListView(id="file-list")
        with Horizontal(id="file-actions"):
            yield Button("All", id="select-all", classes="sel-btn")
            yield Button("None", id="deselect-all", classes="sel-btn")
            yield Button("⟳", id="refresh")
            yield Button("Preview", id="preview-chapters-btn", classes="action-btn")
            yield Button("Export", id="export-text-btn", classes="action-btn")

    def on_mount(self) -> None:
        self.scan_directory()

    def set_mode(self, mode: str) -> None:
        """Set the file selection mode."""
        if mode == self.file_mode:
            return

        self.file_mode = mode

        # Update button states
        books_btn = self.query_one("#mode-books", Button)
        text_btn = self.query_one("#mode-text", Button)

        if mode == "books":
            books_btn.add_class("active")
            text_btn.remove_class("active")
        else:
            books_btn.remove_class("active")
            text_btn.add_class("active")

        # Update title
        title = self.query_one("#panel-title", Label)
        if mode == "books":
            title.update("📁 Select Books (EPUB/MOBI/AZW)")
        else:
            title.update("📁 Select Text Files")

        # Rescan directory
        self.scan_directory()

    def scan_directory(self) -> None:
        """Scan current directory for files based on current mode."""
        file_list = self.query_one("#file-list", ListView)
        file_list.clear()

        self.files = []
        resumable_count = 0

        # Get job manager from app if available
        job_manager = getattr(self.app, "job_manager", None)

        if self.current_path.exists() and self.current_path.is_dir():
            # Scan for files based on mode
            if self.file_mode == "books":
                patterns = ["*.epub", "*.mobi", "*.azw", "*.azw3"]
            else:
                patterns = ["*.txt"]

            all_files = []
            for pattern in patterns:
                all_files.extend(self.current_path.glob(pattern))

            for file_path in sorted(set(all_files)):
                self.files.append(file_path)

                # Check for resumable job via JobManager (only for books)
                has_resumable = False
                if self.file_mode == "books" and job_manager:
                    resumable_job = job_manager.find_job_for_source(str(file_path))
                    has_resumable = resumable_job is not None

                if has_resumable:
                    resumable_count += 1

                file_list.append(EPUBFileItem(file_path, has_resumable_session=has_resumable))

        # Update file count with resumable indicator
        count_label = self.query_one("#file-count", Label)
        count = len(self.files)
        resume_text = f"+🔄{resumable_count}" if resumable_count > 0 else ""
        count_label.update(f"({count}{resume_text})")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path-input":
            new_path = Path(event.value).resolve()
            if new_path.exists() and new_path.is_dir():
                self.current_path = new_path
                self.scan_directory()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mode-books":
            self.set_mode("books")
        elif event.button.id == "mode-text":
            self.set_mode("text")
        elif event.button.id == "select-all":
            for item in self.query(EPUBFileItem):
                if not item.is_selected:
                    item.toggle()
        elif event.button.id == "deselect-all":
            for item in self.query(EPUBFileItem):
                if item.is_selected:
                    item.toggle()
        elif event.button.id == "refresh":
            path_input = self.query_one("#path-input", PathInput)
            self.current_path = Path(path_input.value).resolve()
            self.scan_directory()
        elif event.button.id == "browse-btn":
            self.app.push_screen(
                DirectoryBrowserScreen(self.current_path),
                self._on_directory_selected,
            )

    def _on_directory_selected(self, path: Path | None) -> None:
        """Handle directory selection from browser modal."""
        if path is not None:
            self.current_path = path
            path_input = self.query_one("#path-input", PathInput)
            path_input.value = str(path)
            self.scan_directory()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, EPUBFileItem):
            event.item.toggle()

    def get_selected_files(self) -> list[Path]:
        """Get list of selected EPUB files."""
        return [item.path for item in self.query(EPUBFileItem) if item.is_selected]
