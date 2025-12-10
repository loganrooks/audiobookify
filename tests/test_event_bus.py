"""Tests for the EventBus event system."""

from epub2tts_edge.core.events import (
    Event,
    EventBus,
    EventType,
    chapter_progress_event,
    job_completed_event,
    job_failed_event,
    job_started_event,
    log_event,
)
from epub2tts_edge.job_manager import Job, JobStatus


class TestEventType:
    """Tests for EventType enum."""

    def test_job_lifecycle_events_exist(self):
        """EventType should have job lifecycle events."""
        assert EventType.JOB_CREATED
        assert EventType.JOB_STARTED
        assert EventType.JOB_COMPLETED
        assert EventType.JOB_FAILED
        assert EventType.JOB_CANCELLED

    def test_processing_stage_events_exist(self):
        """EventType should have processing stage events."""
        assert EventType.DETECTION_STARTED
        assert EventType.DETECTION_COMPLETED
        assert EventType.CONVERSION_STARTED
        assert EventType.CONVERSION_COMPLETED

    def test_progress_events_exist(self):
        """EventType should have progress events."""
        assert EventType.CHAPTER_STARTED
        assert EventType.CHAPTER_COMPLETED
        assert EventType.PROGRESS_UPDATE

    def test_log_events_exist(self):
        """EventType should have log events."""
        assert EventType.LOG_INFO
        assert EventType.LOG_WARNING
        assert EventType.LOG_ERROR


class TestEvent:
    """Tests for Event dataclass."""

    def test_create_event_with_type_only(self):
        """Event can be created with just event_type."""
        event = Event(event_type=EventType.JOB_STARTED)
        assert event.event_type == EventType.JOB_STARTED
        assert event.job is None
        assert event.data == {}

    def test_create_event_with_job(self):
        """Event can include a job reference."""
        job = Job(
            job_id="test-123",
            source_file="/path/to/book.epub",
            job_dir="/tmp/jobs/test-123",
            title="Test Book",
        )
        event = Event(event_type=EventType.JOB_STARTED, job=job)
        assert event.job == job
        assert event.job_id == "test-123"

    def test_create_event_with_data(self):
        """Event can include additional data."""
        event = Event(
            event_type=EventType.CHAPTER_COMPLETED,
            data={"chapter_index": 5, "total_chapters": 10},
        )
        assert event.data["chapter_index"] == 5
        assert event.data["total_chapters"] == 10

    def test_job_id_property_without_job(self):
        """job_id property returns None when no job."""
        event = Event(event_type=EventType.LOG_INFO)
        assert event.job_id is None


class TestEventBus:
    """Tests for EventBus pub-sub system."""

    def test_create_event_bus(self):
        """EventBus can be instantiated."""
        bus = EventBus()
        assert bus is not None

    def test_subscribe_to_event(self):
        """Can subscribe to specific event type."""
        bus = EventBus()
        received = []

        bus.on(EventType.JOB_STARTED, lambda e: received.append(e))
        bus.emit(EventType.JOB_STARTED)

        assert len(received) == 1
        assert received[0].event_type == EventType.JOB_STARTED

    def test_multiple_handlers_for_same_event(self):
        """Multiple handlers can subscribe to same event."""
        bus = EventBus()
        received1 = []
        received2 = []

        bus.on(EventType.JOB_STARTED, lambda e: received1.append(e))
        bus.on(EventType.JOB_STARTED, lambda e: received2.append(e))
        bus.emit(EventType.JOB_STARTED)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_handlers_only_receive_subscribed_events(self):
        """Handlers only receive events they subscribed to."""
        bus = EventBus()
        received = []

        bus.on(EventType.JOB_STARTED, lambda e: received.append(e))
        bus.emit(EventType.JOB_COMPLETED)  # Different event type

        assert len(received) == 0

    def test_emit_with_job_and_data(self):
        """emit() can pass job and additional data."""
        bus = EventBus()
        received = []

        bus.on(EventType.CHAPTER_COMPLETED, lambda e: received.append(e))

        job = Job(
            job_id="test-456", source_file="/path.epub", job_dir="/tmp/jobs/test-456", title="Test"
        )
        bus.emit(
            EventType.CHAPTER_COMPLETED,
            job=job,
            chapter_index=3,
            total_chapters=10,
        )

        assert len(received) == 1
        event = received[0]
        assert event.job == job
        assert event.data["chapter_index"] == 3
        assert event.data["total_chapters"] == 10

    def test_unsubscribe_from_event(self):
        """on() returns unsubscribe function."""
        bus = EventBus()
        received = []

        unsubscribe = bus.on(EventType.JOB_STARTED, lambda e: received.append(e))
        bus.emit(EventType.JOB_STARTED)
        assert len(received) == 1

        unsubscribe()
        bus.emit(EventType.JOB_STARTED)
        assert len(received) == 1  # No new events

    def test_on_all_receives_all_events(self):
        """on_all() subscribes to all event types."""
        bus = EventBus()
        received = []

        bus.on_all(lambda e: received.append(e))

        bus.emit(EventType.JOB_STARTED)
        bus.emit(EventType.CHAPTER_COMPLETED)
        bus.emit(EventType.LOG_INFO)

        assert len(received) == 3

    def test_unsubscribe_from_all(self):
        """on_all() returns unsubscribe function."""
        bus = EventBus()
        received = []

        unsubscribe = bus.on_all(lambda e: received.append(e))
        bus.emit(EventType.JOB_STARTED)
        assert len(received) == 1

        unsubscribe()
        bus.emit(EventType.JOB_COMPLETED)
        assert len(received) == 1  # No new events

    def test_clear_specific_event_handlers(self):
        """clear() can remove handlers for specific event type."""
        bus = EventBus()
        started_count = []
        completed_count = []

        bus.on(EventType.JOB_STARTED, lambda e: started_count.append(1))
        bus.on(EventType.JOB_COMPLETED, lambda e: completed_count.append(1))

        bus.clear(EventType.JOB_STARTED)

        bus.emit(EventType.JOB_STARTED)
        bus.emit(EventType.JOB_COMPLETED)

        assert len(started_count) == 0
        assert len(completed_count) == 1

    def test_clear_all_handlers(self):
        """clear() with no args removes all handlers."""
        bus = EventBus()
        received = []

        bus.on(EventType.JOB_STARTED, lambda e: received.append(e))
        bus.on_all(lambda e: received.append(e))

        bus.clear()

        bus.emit(EventType.JOB_STARTED)
        assert len(received) == 0

    def test_handler_error_does_not_crash(self):
        """Handler errors are caught and don't affect other handlers."""
        bus = EventBus()
        received = []

        def bad_handler(e):
            raise ValueError("Handler error")

        def good_handler(e):
            received.append(e)

        bus.on(EventType.JOB_STARTED, bad_handler)
        bus.on(EventType.JOB_STARTED, good_handler)

        # Should not raise, and good_handler should still be called
        bus.emit(EventType.JOB_STARTED)
        assert len(received) == 1


class TestEventHelpers:
    """Tests for event helper functions."""

    def test_job_started_event(self):
        """job_started_event creates correct event."""
        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        event = job_started_event(job)

        assert event.event_type == EventType.JOB_STARTED
        assert event.job == job
        assert event.data["status"] == JobStatus.PENDING

    def test_chapter_progress_event(self):
        """chapter_progress_event creates correct event."""
        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        event = chapter_progress_event(
            job=job,
            chapter_index=5,
            total_chapters=10,
            chapter_title="Chapter 5",
        )

        assert event.event_type == EventType.CHAPTER_COMPLETED
        assert event.job == job
        assert event.data["chapter_index"] == 5
        assert event.data["total_chapters"] == 10
        assert event.data["chapter_title"] == "Chapter 5"
        assert event.data["percentage"] == 50.0

    def test_chapter_progress_event_zero_chapters(self):
        """chapter_progress_event handles zero total chapters."""
        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        event = chapter_progress_event(job=job, chapter_index=0, total_chapters=0)

        assert event.data["percentage"] == 0

    def test_job_completed_event(self):
        """job_completed_event creates correct event."""
        from pathlib import Path

        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        output_path = Path("/output/book.m4b")
        event = job_completed_event(job, output_path=output_path)

        assert event.event_type == EventType.JOB_COMPLETED
        assert event.job == job
        # Use str(Path(...)) for platform-independent comparison
        assert event.data["output_path"] == str(output_path)

    def test_job_completed_event_no_output(self):
        """job_completed_event handles missing output path."""
        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        event = job_completed_event(job)

        assert event.data["output_path"] is None

    def test_job_failed_event(self):
        """job_failed_event creates correct event."""
        job = Job(
            job_id="test-789", source_file="/path.epub", job_dir="/tmp/jobs/test-789", title="Test"
        )
        event = job_failed_event(job, error="Something went wrong")

        assert event.event_type == EventType.JOB_FAILED
        assert event.job == job
        assert event.data["error"] == "Something went wrong"

    def test_log_event_info(self):
        """log_event creates info event by default."""
        event = log_event("Test message")

        assert event.event_type == EventType.LOG_INFO
        assert event.data["message"] == "Test message"

    def test_log_event_warning(self):
        """log_event can create warning event."""
        event = log_event("Warning message", level="warning")

        assert event.event_type == EventType.LOG_WARNING
        assert event.data["message"] == "Warning message"

    def test_log_event_error(self):
        """log_event can create error event."""
        event = log_event("Error message", level="error")

        assert event.event_type == EventType.LOG_ERROR
        assert event.data["message"] == "Error message"
