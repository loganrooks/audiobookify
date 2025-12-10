"""Event system for decoupled processing updates.

This module provides a publish-subscribe event system that allows
processing logic to emit events without knowing about the UI.
The TUI (or any other interface) subscribes to events and updates accordingly.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ..job_manager import Job, JobStatus


class EventType(Enum):
    """Types of events emitted during processing."""

    # Job lifecycle events
    JOB_CREATED = "job_created"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"

    # Processing stage events
    DETECTION_STARTED = "detection_started"
    DETECTION_COMPLETED = "detection_completed"
    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"
    CONVERSION_STARTED = "conversion_started"
    CONVERSION_COMPLETED = "conversion_completed"
    PACKAGING_STARTED = "packaging_started"
    PACKAGING_COMPLETED = "packaging_completed"

    # Progress events
    CHAPTER_STARTED = "chapter_started"
    CHAPTER_COMPLETED = "chapter_completed"
    PROGRESS_UPDATE = "progress_update"

    # Log events
    LOG_INFO = "log_info"
    LOG_WARNING = "log_warning"
    LOG_ERROR = "log_error"


@dataclass
class Event:
    """An event emitted during processing.

    Attributes:
        event_type: The type of event
        job: The job this event relates to (optional)
        data: Additional event-specific data
    """

    event_type: EventType
    job: Job | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def job_id(self) -> str | None:
        """Get job ID if job is present."""
        return self.job.job_id if self.job else None


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Publish-subscribe event system for processing updates.

    This allows processing logic to emit events without coupling to the UI.
    Any number of handlers can subscribe to events.

    Example:
        >>> bus = EventBus()
        >>> bus.on(EventType.CHAPTER_COMPLETED, lambda e: print(f"Chapter done: {e.data}"))
        >>> bus.emit(EventType.CHAPTER_COMPLETED, job=my_job, data={"chapter": 1, "total": 10})
    """

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def on(self, event_type: EventType, handler: EventHandler) -> Callable[[], None]:
        """Subscribe to a specific event type.

        Args:
            event_type: The event type to listen for
            handler: Callback function receiving the Event

        Returns:
            Unsubscribe function that removes this handler
        """
        self._handlers[event_type].append(handler)

        def unsubscribe() -> None:
            self._handlers[event_type].remove(handler)

        return unsubscribe

    def on_all(self, handler: EventHandler) -> Callable[[], None]:
        """Subscribe to all events.

        Args:
            handler: Callback function receiving all Events

        Returns:
            Unsubscribe function that removes this handler
        """
        self._global_handlers.append(handler)

        def unsubscribe() -> None:
            self._global_handlers.remove(handler)

        return unsubscribe

    def emit(
        self,
        event_type: EventType,
        job: Job | None = None,
        **data: Any,
    ) -> None:
        """Emit an event to all subscribed handlers.

        Args:
            event_type: The type of event to emit
            job: Optional job this event relates to
            **data: Additional data to include in the event
        """
        event = Event(event_type=event_type, job=job, data=data)

        # Call type-specific handlers
        for handler in self._handlers[event_type]:
            try:
                handler(event)
            except Exception as e:
                # Log but don't crash on handler errors
                import logging

                logging.getLogger(__name__).warning("Event handler error for %s: %s", event_type, e)

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    "Global event handler error for %s: %s", event_type, e
                )

    def clear(self, event_type: EventType | None = None) -> None:
        """Remove all handlers for an event type, or all handlers if None.

        Args:
            event_type: Specific event type to clear, or None for all
        """
        if event_type is None:
            self._handlers.clear()
            self._global_handlers.clear()
        else:
            self._handlers[event_type].clear()


# Convenience functions for creating common events


def job_started_event(job: Job) -> Event:
    """Create a job started event."""
    return Event(
        event_type=EventType.JOB_STARTED,
        job=job,
        data={"status": JobStatus.PENDING},
    )


def chapter_progress_event(
    job: Job,
    chapter_index: int,
    total_chapters: int,
    chapter_title: str = "",
) -> Event:
    """Create a chapter progress event."""
    return Event(
        event_type=EventType.CHAPTER_COMPLETED,
        job=job,
        data={
            "chapter_index": chapter_index,
            "total_chapters": total_chapters,
            "chapter_title": chapter_title,
            "percentage": (chapter_index / total_chapters * 100) if total_chapters else 0,
        },
    )


def job_completed_event(job: Job, output_path: Path | None = None) -> Event:
    """Create a job completed event."""
    return Event(
        event_type=EventType.JOB_COMPLETED,
        job=job,
        data={"output_path": str(output_path) if output_path else None},
    )


def job_failed_event(job: Job, error: str) -> Event:
    """Create a job failed event."""
    return Event(
        event_type=EventType.JOB_FAILED,
        job=job,
        data={"error": error},
    )


def log_event(message: str, level: str = "info") -> Event:
    """Create a log event."""
    event_type = {
        "info": EventType.LOG_INFO,
        "warning": EventType.LOG_WARNING,
        "error": EventType.LOG_ERROR,
    }.get(level, EventType.LOG_INFO)

    return Event(event_type=event_type, data={"message": message})
