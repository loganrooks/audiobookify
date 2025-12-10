"""Queue panel for displaying the processing queue."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Label

from ...batch_processor import BookTask, ProcessingStatus


class QueuePanel(Vertical):
    """Panel showing the processing queue and results."""

    DEFAULT_CSS = """
    QueuePanel {
        height: 1fr;
        border: round $warning;
        border-title-color: $warning;
        padding: 1;
        background: $surface;
    }

    QueuePanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $warning-lighten-2;
    }

    QueuePanel > #queue-table {
        height: 1fr;
        background: $surface-darken-1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📋 Queue", classes="title")
        yield DataTable(id="queue-table")

    def on_mount(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.add_columns("Status", "Book", "Chapters", "Time")

    def add_task(self, task: BookTask) -> None:
        """Add a task to the queue display."""
        table = self.query_one("#queue-table", DataTable)
        status_icon = self._get_status_icon(task.status)
        table.add_row(
            status_icon,
            task.basename[:30],
            str(task.chapter_count) if task.chapter_count else "-",
            self._format_duration(task.duration),
            key=task.epub_path,
        )

    def update_task(self, task: BookTask) -> None:
        """Update a task in the queue display."""
        table = self.query_one("#queue-table", DataTable)
        try:
            row_key = table.get_row_index(task.epub_path)
            status_icon = self._get_status_icon(task.status)
            table.update_cell_at((row_key, 0), status_icon)
            table.update_cell_at(
                (row_key, 2), str(task.chapter_count) if task.chapter_count else "-"
            )
            table.update_cell_at((row_key, 3), self._format_duration(task.duration))
        except Exception:
            pass

    def clear_queue(self) -> None:
        """Clear the queue display."""
        table = self.query_one("#queue-table", DataTable)
        table.clear()

    def _get_status_icon(self, status: ProcessingStatus) -> str:
        icons = {
            ProcessingStatus.PENDING: "⏳",
            ProcessingStatus.EXPORTING: "📝",
            ProcessingStatus.CONVERTING: "🔊",
            ProcessingStatus.COMPLETED: "✅",
            ProcessingStatus.FAILED: "❌",
            ProcessingStatus.SKIPPED: "⏭️",
        }
        return icons.get(status, "?")

    def _format_duration(self, duration: float | None) -> str:
        if duration is None:
            return "-"
        mins = int(duration // 60)
        secs = int(duration % 60)
        return f"{mins}m {secs}s"
