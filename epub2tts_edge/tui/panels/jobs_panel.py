"""Jobs panel for managing saved jobs."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, ListItem, ListView

from ...job_manager import Job, JobManager, JobStatus


class JobItem(ListItem):
    """A list item representing a saved job with checkbox selection."""

    STATUS_DISPLAY = {
        JobStatus.PREVIEW: ("📋", "Preview"),
        JobStatus.PENDING: ("⏳", "Pending"),
        JobStatus.EXTRACTING: ("📝", "Extracting"),
        JobStatus.CONVERTING: ("🔊", "Converting"),
        JobStatus.PAUSED: ("⏸️", "Paused"),
        JobStatus.FINALIZING: ("📦", "Finalizing"),
        JobStatus.COMPLETED: ("✅", "Completed"),
        JobStatus.FAILED: ("❌", "Failed"),
        JobStatus.CANCELLED: ("🚫", "Cancelled"),
    }

    def __init__(self, job: Job, selected: bool = False) -> None:
        super().__init__()
        self.job = job
        self.is_selected = selected

    def compose(self) -> ComposeResult:
        yield Label(self._build_label())

    def _progress_bar(self, percentage: float, width: int = 8) -> str:
        """Generate a text progress bar."""
        filled = int(width * percentage / 100)
        empty = width - filled
        return "█" * filled + "░" * empty

    def _build_label(self) -> str:
        """Build the display label for this job item."""
        checkbox = "☑" if self.is_selected else "☐"
        icon, status_text = self.STATUS_DISPLAY.get(self.job.status, ("?", "Unknown"))
        book_name = Path(self.job.source_file).stem[:25]

        # Progress display varies by status
        if self.job.status in (JobStatus.CONVERTING, JobStatus.PAUSED):
            pct = self.job.progress_percentage
            bar = self._progress_bar(pct)
            progress = f"{bar} {pct:.0f}%"
        elif self.job.status == JobStatus.COMPLETED:
            progress = f"{self.job.completed_chapters}/{self.job.total_chapters}"
        elif self.job.total_chapters > 0:
            progress = f"{self.job.completed_chapters}/{self.job.total_chapters}"
        else:
            progress = ""

        # Format: checkbox icon book_name | status_text progress
        if progress:
            return f"{checkbox} {icon} {book_name} | {status_text} {progress}"
        else:
            return f"{checkbox} {icon} {book_name} | {status_text}"

    def toggle(self) -> None:
        """Toggle selection state."""
        self.is_selected = not self.is_selected
        self.query_one(Label).update(self._build_label())

    def refresh_display(self) -> None:
        """Refresh the display label (e.g., after job update)."""
        self.query_one(Label).update(self._build_label())


class JobsPanel(Vertical):
    """Panel showing saved jobs with checkbox selection for multi-select operations."""

    DEFAULT_CSS = """
    JobsPanel {
        height: 1fr;
        border: round $secondary;
        border-title-color: $secondary;
        padding: 0 1;
        background: $surface;
    }

    JobsPanel > #jobs-header {
        height: auto;
        margin-bottom: 0;
    }

    JobsPanel > #jobs-header > Label.title {
        text-style: bold;
        color: $secondary-lighten-2;
        width: auto;
    }

    JobsPanel > #jobs-header > Label.count {
        color: $text-muted;
        margin-left: 1;
    }

    JobsPanel > #jobs-list {
        height: 1fr;
        background: $surface-darken-1;
    }

    JobsPanel > #jobs-buttons {
        height: auto;
        margin-top: 0;
    }

    JobsPanel > #jobs-buttons > Button {
        min-width: 6;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }
    """

    def __init__(self, job_manager: JobManager | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.job_manager = job_manager or JobManager()
        self._auto_refresh_timer = None  # Timer for auto-refresh during processing

    def compose(self) -> ComposeResult:
        with Horizontal(id="jobs-header"):
            yield Label("💼 Jobs", classes="title")
            yield Label("(0)", id="job-count", classes="count")

        # Instructions like Preview panel has
        yield Label(
            "📋 Space=select, R=resume, X=delete, ⟳=refresh",
            id="jobs-instructions",
        )

        yield ListView(id="jobs-list")

        # Combined selection + transport + job actions in single row
        # Make labels more consistent with Preview panel
        with Horizontal(id="jobs-buttons"):
            yield Button("Select All", id="job-select-all")
            yield Button("Select None", id="job-deselect-all")
            yield Button("▶ Resume", id="jobs-play-btn", variant="success", disabled=True)
            yield Button("⏸ Pause", id="jobs-pause-btn", variant="warning", disabled=True)
            yield Button("⏹ Stop", id="jobs-stop-btn", variant="error", disabled=True)
            yield Button("🗑️ Delete", id="job-delete", variant="error")
            yield Button("⟳ Refresh", id="job-refresh")

    def on_mount(self) -> None:
        self.refresh_jobs()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection (toggle checkbox)."""
        if isinstance(event.item, JobItem):
            event.item.toggle()
            self.update_play_button()

    def refresh_jobs(self) -> None:
        """Refresh the job list from disk."""
        jobs_list = self.query_one("#jobs-list", ListView)
        jobs_list.clear()

        jobs = self.job_manager.list_jobs(include_completed=True)
        for job in jobs:
            jobs_list.append(JobItem(job))

        # Update count label
        count_label = self.query_one("#job-count", Label)
        job_count = len(jobs)
        count_label.update(f"({job_count})")

    def get_selected_jobs(self) -> list[Job]:
        """Get all selected jobs."""
        return [item.job for item in self.query(JobItem) if item.is_selected]

    def get_selected_job(self) -> Job | None:
        """Get the first selected job (for backward compatibility)."""
        selected = self.get_selected_jobs()
        return selected[0] if selected else None

    def get_resumable_selected_jobs(self) -> list[Job]:
        """Get selected jobs that can be resumed."""
        return [job for job in self.get_selected_jobs() if job.is_resumable]

    def delete_selected_jobs(self) -> int:
        """Delete all selected jobs. Returns count of deleted jobs."""
        deleted = 0
        for job in self.get_selected_jobs():
            if self.job_manager.delete_job(job.job_id):
                deleted += 1
        self.refresh_jobs()
        return deleted

    def select_all(self) -> None:
        """Select all jobs."""
        for item in self.query(JobItem):
            if not item.is_selected:
                item.toggle()

    def deselect_all(self) -> None:
        """Deselect all jobs."""
        for item in self.query(JobItem):
            if item.is_selected:
                item.toggle()

    def move_selected_up(self) -> None:
        """Move selected jobs up in the list (for queue priority)."""
        jobs_list = self.query_one("#jobs-list", ListView)
        items = list(self.query(JobItem))

        # Find indices of selected items
        selected_indices = [i for i, item in enumerate(items) if item.is_selected]

        if not selected_indices or selected_indices[0] == 0:
            return  # Can't move up if already at top or nothing selected

        # Move each selected item up by one position
        for idx in selected_indices:
            if idx > 0:
                # Swap with previous item
                items[idx], items[idx - 1] = items[idx - 1], items[idx]

        # Rebuild the list
        jobs_list.clear()
        for item in items:
            jobs_list.append(JobItem(item.job, selected=item.is_selected))

    def move_selected_down(self) -> None:
        """Move selected jobs down in the list (for queue priority)."""
        jobs_list = self.query_one("#jobs-list", ListView)
        items = list(self.query(JobItem))

        # Find indices of selected items (in reverse order for proper movement)
        selected_indices = [i for i, item in enumerate(items) if item.is_selected]

        if not selected_indices or selected_indices[-1] == len(items) - 1:
            return  # Can't move down if already at bottom or nothing selected

        # Move each selected item down by one position (process in reverse)
        for idx in reversed(selected_indices):
            if idx < len(items) - 1:
                # Swap with next item
                items[idx], items[idx + 1] = items[idx + 1], items[idx]

        # Rebuild the list
        jobs_list.clear()
        for item in items:
            jobs_list.append(JobItem(item.job, selected=item.is_selected))

    def set_running(self, running: bool) -> None:
        """Update transport button states based on running status."""
        play_btn = self.query_one("#jobs-play-btn", Button)
        play_btn.disabled = running
        self.query_one("#jobs-pause-btn", Button).disabled = not running
        self.query_one("#jobs-stop-btn", Button).disabled = not running

        # Start/stop auto-refresh based on processing state
        if running:
            self.start_auto_refresh(interval=1.0)  # Refresh every second
        else:
            self.stop_auto_refresh()
            self.refresh_jobs()  # Final refresh when stopped

    def set_paused(self, paused: bool) -> None:
        """Update pause button state."""
        pause_btn = self.query_one("#jobs-pause-btn", Button)
        if paused:
            pause_btn.label = "▶ Resume"
        else:
            pause_btn.label = "⏸ Pause"

    def start_auto_refresh(self, interval: float = 1.0) -> None:
        """Start auto-refreshing the jobs list periodically."""
        self.stop_auto_refresh()  # Cancel any existing timer
        self._auto_refresh_timer = self.set_interval(interval, self._auto_refresh_jobs)

    def stop_auto_refresh(self) -> None:
        """Stop auto-refreshing the jobs list."""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()
            self._auto_refresh_timer = None

    def _auto_refresh_jobs(self) -> None:
        """Auto-refresh callback - updates job displays without full refresh."""
        jobs_list = self.query_one("#jobs-list", ListView)
        # Update each job item's display from disk
        for item in jobs_list.children:
            if isinstance(item, JobItem):
                # Reload job data from disk
                updated_job = self.job_manager.load_job(item.job.job_id)
                if updated_job:
                    item.job = updated_job
                    item.refresh_display()

    def update_play_button(self) -> None:
        """Update play button label and state based on selected jobs."""
        play_btn = self.query_one("#jobs-play-btn", Button)
        selected = self.get_selected_jobs()

        if not selected:
            play_btn.label = "▶ Play"
            play_btn.disabled = True
            return

        # Check first selected job's status to determine button label
        first_job = selected[0]
        if first_job.status == JobStatus.PREVIEW:
            play_btn.label = "▶ Start"
            play_btn.disabled = False
        elif first_job.status == JobStatus.PAUSED:
            play_btn.label = "▶ Resume"
            play_btn.disabled = False
        elif first_job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            play_btn.label = "▶ Restart"
            play_btn.disabled = False
        elif first_job.status in (JobStatus.CONVERTING, JobStatus.EXTRACTING, JobStatus.FINALIZING):
            play_btn.label = "▶ Play"
            play_btn.disabled = True  # Already running
        elif first_job.status == JobStatus.PENDING:
            play_btn.label = "▶ Start"
            play_btn.disabled = False
        else:
            play_btn.label = "▶ Play"
            play_btn.disabled = False
