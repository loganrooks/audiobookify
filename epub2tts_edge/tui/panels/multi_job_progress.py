"""Multi-job progress panel for displaying parallel conversion progress."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Label, ProgressBar, Static

if TYPE_CHECKING:
    pass


@dataclass
class JobProgressInfo:
    """Progress information for a single job."""

    job_id: str
    title: str
    status: str
    chapter_num: int = 0
    total_chapters: int = 0
    chapter_title: str = ""
    paragraph_num: int = 0
    total_paragraphs: int = 0

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress as percentage."""
        if self.total_chapters == 0:
            return 0.0
        chapter_progress = (self.chapter_num - 1) / self.total_chapters
        if self.total_paragraphs > 0:
            para_progress = self.paragraph_num / self.total_paragraphs
            return (chapter_progress + (para_progress / self.total_chapters)) * 100
        return chapter_progress * 100

    @property
    def status_text(self) -> str:
        """Get formatted status text."""
        if self.total_chapters == 0:
            return self.status
        if self.chapter_title:
            return f"Ch {self.chapter_num}/{self.total_chapters}: {self.chapter_title[:25]}"
        return f"Chapter {self.chapter_num}/{self.total_chapters}"


class JobProgressItem(Static):
    """Widget showing progress for a single job."""

    DEFAULT_CSS = """
    JobProgressItem {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
        border: solid $primary-darken-2;
    }

    JobProgressItem.completed {
        border: solid $success-darken-2;
    }

    JobProgressItem.failed {
        border: solid $error-darken-2;
    }

    JobProgressItem.cancelled {
        border: solid $warning-darken-2;
    }

    JobProgressItem > #job-title {
        text-style: bold;
        margin-bottom: 0;
    }

    JobProgressItem > #job-status {
        color: $text-muted;
        margin-bottom: 0;
    }

    JobProgressItem > #job-progress {
        margin: 0;
    }

    JobProgressItem > Horizontal {
        height: auto;
    }

    JobProgressItem > Horizontal > Button {
        min-width: 6;
        margin-left: 1;
    }
    """

    def __init__(self, job_id: str, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.job_id = job_id
        self._title = title
        self._status = "Queued"
        self._progress = 0.0

    def compose(self) -> ComposeResult:
        yield Label(f"📖 {self._title[:35]}", id="job-title")
        yield Label(self._status, id="job-status")
        yield ProgressBar(total=100, show_eta=False, id="job-progress")
        with Horizontal():
            yield Button("✕", id="cancel-job-btn", variant="error")

    def update_progress(self, info: JobProgressInfo) -> None:
        """Update the job progress display."""
        self._status = info.status_text
        self._progress = info.progress_percentage

        self.query_one("#job-status", Label).update(self._status)
        self.query_one("#job-progress", ProgressBar).update(progress=self._progress)

    def set_status(self, status: str) -> None:
        """Set simple status text."""
        self._status = status
        self.query_one("#job-status", Label).update(status)

    def set_completed(self, success: bool, error: str | None = None) -> None:
        """Mark job as completed."""
        self.remove_class("failed", "cancelled")
        if success:
            self.add_class("completed")
            self._status = "✅ Completed"
            self.query_one("#job-progress", ProgressBar).update(progress=100)
        else:
            if error and "cancel" in error.lower():
                self.add_class("cancelled")
                self._status = "⚠️ Cancelled"
            else:
                self.add_class("failed")
                self._status = f"❌ {error[:30]}" if error else "❌ Failed"

        self.query_one("#job-status", Label).update(self._status)
        self.query_one("#cancel-job-btn", Button).disabled = True


class MultiJobProgress(Vertical):
    """Panel for displaying multiple job progress simultaneously."""

    DEFAULT_CSS = """
    MultiJobProgress {
        height: auto;
        min-height: 8;
        max-height: 24;
        border: round $primary;
        border-title-color: $primary;
        padding: 1;
        background: $surface;
    }

    MultiJobProgress > #queue-stats {
        height: auto;
        margin-bottom: 1;
    }

    MultiJobProgress > #queue-stats > Label {
        margin-right: 2;
    }

    MultiJobProgress > #queue-stats > .stat-running {
        color: $success;
    }

    MultiJobProgress > #queue-stats > .stat-queued {
        color: $primary;
    }

    MultiJobProgress > #queue-stats > .stat-done {
        color: $text-muted;
    }

    MultiJobProgress > #jobs-container {
        height: auto;
        max-height: 18;
    }

    MultiJobProgress > #no-jobs {
        color: $text-muted;
        text-align: center;
        padding: 1;
    }

    MultiJobProgress > #queue-controls {
        height: auto;
        dock: bottom;
        margin-top: 1;
    }

    MultiJobProgress > #queue-controls > Button {
        min-width: 10;
        margin-right: 1;
    }
    """

    running_count: reactive[int] = reactive(0)
    queued_count: reactive[int] = reactive(0)
    completed_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._job_widgets: dict[str, JobProgressItem] = {}
        self.border_title = "Queue Progress"

    def compose(self) -> ComposeResult:
        with Horizontal(id="queue-stats"):
            yield Label("Running: 0", id="stat-running", classes="stat-running")
            yield Label("Queued: 0", id="stat-queued", classes="stat-queued")
            yield Label("Done: 0", id="stat-done", classes="stat-done")
        yield VerticalScroll(id="jobs-container")
        yield Label("No jobs in queue", id="no-jobs")
        with Horizontal(id="queue-controls"):
            yield Button("▶ Start All", id="start-queue-btn", variant="success")
            yield Button("⏹ Cancel All", id="cancel-all-btn", variant="error", disabled=True)
            yield Button("Clear Done", id="clear-done-btn", variant="default", disabled=True)

    def watch_running_count(self, count: int) -> None:
        """Update running count display."""
        self.query_one("#stat-running", Label).update(f"Running: {count}")
        self.query_one("#cancel-all-btn", Button).disabled = count == 0

    def watch_queued_count(self, count: int) -> None:
        """Update queued count display."""
        self.query_one("#stat-queued", Label).update(f"Queued: {count}")

    def watch_completed_count(self, count: int) -> None:
        """Update completed count display."""
        self.query_one("#stat-done", Label).update(f"Done: {count}")
        self.query_one("#clear-done-btn", Button).disabled = count == 0

    def add_job(self, job_id: str, title: str) -> None:
        """Add a job to the progress display."""
        if job_id in self._job_widgets:
            return

        widget = JobProgressItem(job_id, title)
        self._job_widgets[job_id] = widget

        container = self.query_one("#jobs-container", VerticalScroll)
        container.mount(widget)

        self._update_empty_state()

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the progress display."""
        if job_id not in self._job_widgets:
            return

        widget = self._job_widgets.pop(job_id)
        widget.remove()

        self._update_empty_state()

    def update_job_progress(self, job_id: str, info: JobProgressInfo) -> None:
        """Update progress for a specific job."""
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.update_progress(info)

    def set_job_status(self, job_id: str, status: str) -> None:
        """Set status text for a job."""
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.set_status(status)

    def mark_job_complete(self, job_id: str, success: bool, error: str | None = None) -> None:
        """Mark a job as completed."""
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.set_completed(success, error)

    def update_stats(self, running: int, queued: int, completed: int) -> None:
        """Update queue statistics."""
        self.running_count = running
        self.queued_count = queued
        self.completed_count = completed

    def clear_completed(self) -> list[str]:
        """Remove completed/failed jobs from display.

        Returns:
            List of removed job IDs
        """
        to_remove = []
        for job_id, widget in self._job_widgets.items():
            if widget.has_class("completed", "failed", "cancelled"):
                to_remove.append(job_id)

        for job_id in to_remove:
            self.remove_job(job_id)

        return to_remove

    def clear_all(self) -> None:
        """Remove all jobs from display."""
        for widget in list(self._job_widgets.values()):
            widget.remove()
        self._job_widgets.clear()
        self._update_empty_state()

    def set_running(self, running: bool) -> None:
        """Update button states based on running status."""
        self.query_one("#start-queue-btn", Button).disabled = running
        self.query_one("#cancel-all-btn", Button).disabled = not running

    def _update_empty_state(self) -> None:
        """Show/hide empty state message."""
        no_jobs = self.query_one("#no-jobs", Label)
        container = self.query_one("#jobs-container", VerticalScroll)

        if self._job_widgets:
            no_jobs.display = False
            container.display = True
        else:
            no_jobs.display = True
            container.display = False

    def get_job_ids(self) -> list[str]:
        """Get all job IDs in the panel."""
        return list(self._job_widgets.keys())
