"""Directory browser modal screen."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label


class FilteredDirectoryTree(DirectoryTree):
    """DirectoryTree that filters out hidden files and shows only directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        """Filter out hidden files and non-directories."""
        return sorted(
            [p for p in paths if not p.name.startswith(".") and p.is_dir()],
            key=lambda p: p.name.lower(),
        )


class DirectoryBrowserScreen(ModalScreen[Path | None]):
    """Modal screen for browsing and selecting directories."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    DEFAULT_CSS = """
    DirectoryBrowserScreen {
        align: center middle;
    }

    #browser-container {
        width: 70;
        height: 80%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }

    #browser-container > Label.title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #browser-container > Label.path-label {
        color: $text-muted;
        margin-bottom: 1;
    }

    #browser-container FilteredDirectoryTree {
        height: 1fr;
        border: solid $primary-darken-2;
        margin-bottom: 1;
    }

    #browser-actions {
        height: auto;
        align: center middle;
    }

    #browser-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, start_path: Path | None = None) -> None:
        super().__init__()
        self.start_path = start_path or Path.home()
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="browser-container"):
            yield Label("📁 Select Directory", classes="title")
            yield Label(f"Current: {self.start_path}", id="current-path", classes="path-label")
            yield FilteredDirectoryTree(str(self.start_path))
            with Horizontal(id="browser-actions"):
                yield Button("Select", id="select-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Update selected path when directory is clicked."""
        self.selected_path = event.path
        path_label = self.query_one("#current-path", Label)
        path_label.update(f"Current: {event.path}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            self.action_select()
        elif event.button.id == "cancel-btn":
            self.action_cancel()

    def action_select(self) -> None:
        """Confirm selection and close."""
        if self.selected_path:
            self.dismiss(self.selected_path)
        else:
            # Use the start path if nothing explicitly selected
            self.dismiss(self.start_path)

    def action_cancel(self) -> None:
        """Cancel and close without selection."""
        self.dismiss(None)
