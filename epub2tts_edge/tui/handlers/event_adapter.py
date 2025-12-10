"""Event adapter for connecting EventBus to TUI updates.

This module bridges the core EventBus system to the Textual TUI,
translating processing events into UI updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ...core.events import Event, EventBus, EventType

if TYPE_CHECKING:
    from ..app import AudiobookifyApp


class UIUpdater(Protocol):
    """Protocol for UI update methods.

    This allows the event adapter to work with any object that provides
    these UI update methods, making it testable without the full TUI.
    """

    def log_message(self, message: str) -> None:
        """Log a message to the log panel."""
        ...

    def update_progress(self, current: int, total: int, chapter_title: str = "") -> None:
        """Update the progress display."""
        ...

    def set_processing_state(self, running: bool) -> None:
        """Update the processing state (buttons, etc.)."""
        ...

    def refresh_jobs(self) -> None:
        """Refresh the jobs list."""
        ...


class TUIEventAdapter:
    """Adapts EventBus events to TUI UI updates.

    This class subscribes to EventBus events and translates them into
    appropriate TUI method calls. It handles thread-safety by using
    Textual's call_from_thread when needed.

    Usage:
        adapter = TUIEventAdapter(app, event_bus)
        adapter.connect()  # Subscribe to all events
        # ... run pipeline ...
        adapter.disconnect()  # Clean up subscriptions
    """

    def __init__(self, app: AudiobookifyApp, event_bus: EventBus) -> None:
        """Initialize the adapter.

        Args:
            app: The Textual app instance
            event_bus: The EventBus to subscribe to
        """
        self.app = app
        self.event_bus = event_bus
        self._unsubscribers: list[callable] = []

    def connect(self) -> None:
        """Subscribe to all relevant events."""
        # Job lifecycle events
        self._unsubscribers.append(self.event_bus.on(EventType.JOB_CREATED, self._on_job_created))
        self._unsubscribers.append(self.event_bus.on(EventType.JOB_STARTED, self._on_job_started))
        self._unsubscribers.append(
            self.event_bus.on(EventType.JOB_COMPLETED, self._on_job_completed)
        )
        self._unsubscribers.append(self.event_bus.on(EventType.JOB_FAILED, self._on_job_failed))
        self._unsubscribers.append(
            self.event_bus.on(EventType.JOB_CANCELLED, self._on_job_cancelled)
        )

        # Processing stage events
        self._unsubscribers.append(
            self.event_bus.on(EventType.DETECTION_STARTED, self._on_detection_started)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.DETECTION_COMPLETED, self._on_detection_completed)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.EXPORT_STARTED, self._on_export_started)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.EXPORT_COMPLETED, self._on_export_completed)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.CONVERSION_STARTED, self._on_conversion_started)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.CONVERSION_COMPLETED, self._on_conversion_completed)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.PACKAGING_STARTED, self._on_packaging_started)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.PACKAGING_COMPLETED, self._on_packaging_completed)
        )

        # Progress events
        self._unsubscribers.append(
            self.event_bus.on(EventType.CHAPTER_STARTED, self._on_chapter_started)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.CHAPTER_COMPLETED, self._on_chapter_completed)
        )
        self._unsubscribers.append(
            self.event_bus.on(EventType.PROGRESS_UPDATE, self._on_progress_update)
        )

        # Log events
        self._unsubscribers.append(self.event_bus.on(EventType.LOG_INFO, self._on_log_info))
        self._unsubscribers.append(self.event_bus.on(EventType.LOG_WARNING, self._on_log_warning))
        self._unsubscribers.append(self.event_bus.on(EventType.LOG_ERROR, self._on_log_error))

    def disconnect(self) -> None:
        """Unsubscribe from all events."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    def _safe_log(self, message: str) -> None:
        """Log a message safely from any thread."""
        self.app.call_from_thread(self.app.log_message, message)

    def _safe_update_progress(self, current: int, total: int, title: str = "") -> None:
        """Update progress safely from any thread."""

        # The app's progress panel update method
        def update():
            try:
                from ..panels import ProgressPanel

                panel = self.app.query_one(ProgressPanel)
                panel.update_progress(current, total, title)
            except Exception:
                pass  # Panel might not exist

        self.app.call_from_thread(update)

    # Job lifecycle handlers

    def _on_job_created(self, event: Event) -> None:
        """Handle job created event."""
        job = event.job
        if job:
            self._safe_log(f"📝 Job created: {job.title or job.job_id}")

    def _on_job_started(self, event: Event) -> None:
        """Handle job started event."""
        job = event.job
        if job:
            self._safe_log(f"▶️ Starting: {job.title or job.job_id}")

    def _on_job_completed(self, event: Event) -> None:
        """Handle job completed event."""
        job = event.job
        output = event.data.get("output_path", "")
        if job:
            self._safe_log(f"✅ Completed: {job.title or job.job_id}")
            if output:
                self._safe_log(f"   Output: {output}")
        self.app.call_from_thread(self._refresh_jobs)

    def _on_job_failed(self, event: Event) -> None:
        """Handle job failed event."""
        job = event.job
        error = event.data.get("error", "Unknown error")
        if job:
            self._safe_log(f"❌ Failed: {job.title or job.job_id}")
            self._safe_log(f"   Error: {error}")
        self.app.call_from_thread(self._refresh_jobs)

    def _on_job_cancelled(self, event: Event) -> None:
        """Handle job cancelled event."""
        job = event.job
        if job:
            self._safe_log(f"🚫 Cancelled: {job.title or job.job_id}")
        self.app.call_from_thread(self._refresh_jobs)

    # Processing stage handlers

    def _on_detection_started(self, event: Event) -> None:
        """Handle detection started event."""
        self._safe_log("🔍 Detecting chapters...")

    def _on_detection_completed(self, event: Event) -> None:
        """Handle detection completed event."""
        count = event.data.get("chapter_count", 0)
        filtered = event.data.get("filtered_count", 0)
        msg = f"📖 Found {count} chapters"
        if filtered:
            msg += f" ({filtered} filtered)"
        self._safe_log(msg)

    def _on_export_started(self, event: Event) -> None:
        """Handle export started event."""
        self._safe_log("📝 Exporting text...")

    def _on_export_completed(self, event: Event) -> None:
        """Handle export completed event."""
        self._safe_log("📝 Text export complete")

    def _on_conversion_started(self, event: Event) -> None:
        """Handle conversion started event."""
        total = event.data.get("total_chapters", 0)
        self._safe_log(f"🔊 Converting {total} chapters to audio...")

    def _on_conversion_completed(self, event: Event) -> None:
        """Handle conversion completed event."""
        count = event.data.get("chapters_converted", 0)
        self._safe_log(f"🔊 Audio conversion complete ({count} chapters)")

    def _on_packaging_started(self, event: Event) -> None:
        """Handle packaging started event."""
        self._safe_log("📦 Creating audiobook...")

    def _on_packaging_completed(self, event: Event) -> None:
        """Handle packaging completed event."""
        output = event.data.get("output_path", "")
        self._safe_log(f"📦 Audiobook created: {output}")

    # Progress handlers

    def _on_chapter_started(self, event: Event) -> None:
        """Handle chapter started event."""
        index = event.data.get("chapter_index", 0)
        total = event.data.get("total_chapters", 0)
        title = event.data.get("chapter_title", "")
        self._safe_update_progress(index, total, title)
        # Also log to log panel (1-indexed for display)
        title_preview = title[:50] if title else "Untitled"
        self._safe_log(f"  📖 Chapter {index + 1}/{total}: {title_preview}")

    def _on_chapter_completed(self, event: Event) -> None:
        """Handle chapter completed event."""
        index = event.data.get("chapter_index", 0)
        total = event.data.get("total_chapters", 0)
        title = event.data.get("chapter_title", "")
        self._safe_update_progress(index + 1, total, title)  # +1 because completed

    def _on_progress_update(self, event: Event) -> None:
        """Handle generic progress update event."""
        current = event.data.get("current", 0)
        total = event.data.get("total", 0)
        message = event.data.get("message", "")
        self._safe_update_progress(current, total, message)

    # Log handlers

    def _on_log_info(self, event: Event) -> None:
        """Handle info log event."""
        message = event.data.get("message", "")
        self._safe_log(message)

    def _on_log_warning(self, event: Event) -> None:
        """Handle warning log event."""
        message = event.data.get("message", "")
        self._safe_log(f"⚠️ {message}")

    def _on_log_error(self, event: Event) -> None:
        """Handle error log event."""
        message = event.data.get("message", "")
        self._safe_log(f"❌ {message}")

    # Helper methods

    def _refresh_jobs(self) -> None:
        """Refresh the jobs panel."""
        try:
            from ..panels import JobsPanel

            panel = self.app.query_one(JobsPanel)
            panel.refresh_jobs()
        except Exception:
            pass  # Panel might not exist
