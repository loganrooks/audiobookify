"""Log panel for displaying log output."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Log


class LogPanel(Vertical):
    """Panel for displaying log output."""

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        min-height: 10;
        border: round $primary-darken-1;
        border-title-color: $primary-darken-1;
        padding: 1;
        background: $surface;
    }

    LogPanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary-lighten-1;
    }

    LogPanel > #log-output {
        height: 1fr;
        min-height: 8;
        background: $surface-darken-1;
        border: round $primary-darken-2;
        scrollbar-gutter: stable;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📜 Log", classes="title")
        yield Log(id="log-output", auto_scroll=True, max_lines=1000)

    def write(self, message: str) -> None:
        """Write a message to the log."""
        self.query_one("#log-output", Log).write_line(message)

    def clear(self) -> None:
        """Clear the log."""
        self.query_one("#log-output", Log).clear()
