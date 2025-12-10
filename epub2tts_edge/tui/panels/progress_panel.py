"""Progress panel for displaying conversion progress."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, ProgressBar


class ProgressPanel(Vertical):
    """Panel for displaying current job progress."""

    DEFAULT_CSS = """
    ProgressPanel {
        height: auto;
        min-height: 14;
        border: round $success;
        border-title-color: $success;
        padding: 1;
        background: $surface;
    }

    ProgressPanel > #transport-controls {
        height: auto;
        margin-bottom: 1;
    }

    ProgressPanel > #transport-controls > Button {
        min-width: 8;
        margin-right: 1;
    }

    ProgressPanel > #current-book {
        margin-bottom: 1;
        text-style: bold;
    }

    ProgressPanel > #chapter-progress {
        color: $primary;
        margin-bottom: 0;
    }

    ProgressPanel > #paragraph-progress {
        color: $text-muted;
        margin-bottom: 1;
    }

    ProgressPanel > #progress-bar {
        margin-bottom: 1;
    }

    ProgressPanel > #status-text {
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="transport-controls"):
            yield Button("▶ Start", id="start-btn", variant="success")
            yield Button("⏸ Pause", id="pause-btn", variant="warning", disabled=True)
            yield Button("⏹ Stop", id="stop-btn", variant="error", disabled=True)
        yield Label("Ready to convert", id="current-book")
        yield Label("", id="chapter-progress")
        yield Label("", id="paragraph-progress")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Label("Select files and press Start", id="status-text")

    def set_progress(self, current: int, total: int, book_name: str = "", status: str = "") -> None:
        """Update progress display."""
        progress = (current / total * 100) if total > 0 else 0
        self.query_one("#progress-bar", ProgressBar).update(progress=progress)
        self.query_one("#current-book", Label).update(
            f"📖 {book_name}" if book_name else "Ready to convert"
        )
        self.query_one("#status-text", Label).update(status or f"{current}/{total} books processed")

    def set_chapter_progress(
        self,
        chapter_num: int,
        total_chapters: int,
        chapter_title: str,
        paragraph_num: int,
        total_paragraphs: int,
    ) -> None:
        """Update chapter/paragraph progress display."""
        # Calculate overall progress based on chapters and paragraphs
        chapter_progress = (chapter_num - 1) / total_chapters if total_chapters > 0 else 0
        paragraph_progress = paragraph_num / total_paragraphs if total_paragraphs > 0 else 0
        overall = (chapter_progress + (paragraph_progress / total_chapters)) * 100

        self.query_one("#progress-bar", ProgressBar).update(progress=overall)
        self.query_one("#chapter-progress", Label).update(
            f"Chapter {chapter_num}/{total_chapters}: {chapter_title[:40]}"
        )
        self.query_one("#paragraph-progress", Label).update(
            f"   Paragraph {paragraph_num}/{total_paragraphs}"
        )

    def clear_chapter_progress(self) -> None:
        """Clear chapter/paragraph progress display."""
        self.query_one("#chapter-progress", Label).update("")
        self.query_one("#paragraph-progress", Label).update("")

    def set_running(self, running: bool) -> None:
        """Update button states based on running status."""
        self.query_one("#start-btn", Button).disabled = running
        self.query_one("#pause-btn", Button).disabled = not running
        self.query_one("#stop-btn", Button).disabled = not running

    def set_paused(self, paused: bool) -> None:
        """Update pause button state."""
        pause_btn = self.query_one("#pause-btn", Button)
        if paused:
            pause_btn.label = "▶ Resume"
        else:
            pause_btn.label = "⏸ Pause"
