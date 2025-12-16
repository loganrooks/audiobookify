"""Parallel job queue for concurrent audiobook conversion.

Provides a ThreadPoolExecutor-based queue for running multiple conversion
jobs simultaneously with progress tracking and cancellation support.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from epub2tts_edge.job_manager import Job, JobManager, JobStatus

if TYPE_CHECKING:
    from epub2tts_edge.core.events import EventBus


class QueuedJobStatus(Enum):
    """Status of a job within the queue."""

    QUEUED = "queued"  # Waiting in queue
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # User cancelled


@dataclass
class QueuedJob:
    """A job in the processing queue with execution state."""

    job: Job
    status: QueuedJobStatus = QueuedJobStatus.QUEUED
    future: Future | None = None
    cancel_requested: bool = False
    error_message: str | None = None

    @property
    def job_id(self) -> str:
        """Get the underlying job ID."""
        return self.job.job_id

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == QueuedJobStatus.RUNNING

    @property
    def is_done(self) -> bool:
        """Check if job has finished (completed, failed, or cancelled)."""
        return self.status in (
            QueuedJobStatus.COMPLETED,
            QueuedJobStatus.FAILED,
            QueuedJobStatus.CANCELLED,
        )

    def request_cancel(self) -> None:
        """Request cancellation of this job."""
        self.cancel_requested = True


# Type for job execution function
JobExecutor = Callable[[Job, Callable[[], bool]], bool]


@dataclass
class JobQueue:
    """Manages parallel execution of conversion jobs.

    Provides a queue with configurable concurrency for running multiple
    audiobook conversions simultaneously.

    Attributes:
        max_workers: Maximum concurrent jobs (default 3)
        event_bus: Optional event bus for progress notifications
    """

    max_workers: int = 3
    event_bus: EventBus | None = None

    # Internal state
    _executor: ThreadPoolExecutor | None = field(default=None, init=False, repr=False)
    _queued_jobs: dict[str, QueuedJob] = field(default_factory=dict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _job_manager: JobManager | None = field(default=None, init=False)
    _executor_fn: JobExecutor | None = field(default=None, init=False)
    _on_job_complete: Callable[[str, bool, str | None], None] | None = field(
        default=None, init=False
    )

    def __post_init__(self) -> None:
        """Initialize the thread pool executor."""
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="job_worker"
        )

    def set_job_manager(self, job_manager: JobManager) -> None:
        """Set the job manager for status updates."""
        self._job_manager = job_manager

    def set_executor(self, executor_fn: JobExecutor) -> None:
        """Set the function that executes a job.

        Args:
            executor_fn: Function taking (job, cancellation_check) -> success
        """
        self._executor_fn = executor_fn

    def set_completion_callback(self, callback: Callable[[str, bool, str | None], None]) -> None:
        """Set callback for job completion.

        Args:
            callback: Function called with (job_id, success, error_message)
        """
        self._on_job_complete = callback

    @property
    def running_count(self) -> int:
        """Get number of currently running jobs."""
        with self._lock:
            return sum(1 for qj in self._queued_jobs.values() if qj.is_running)

    @property
    def queued_count(self) -> int:
        """Get number of jobs waiting in queue."""
        with self._lock:
            return sum(
                1 for qj in self._queued_jobs.values() if qj.status == QueuedJobStatus.QUEUED
            )

    @property
    def completed_count(self) -> int:
        """Get number of completed jobs."""
        with self._lock:
            return sum(
                1 for qj in self._queued_jobs.values() if qj.status == QueuedJobStatus.COMPLETED
            )

    @property
    def failed_count(self) -> int:
        """Get number of failed jobs."""
        with self._lock:
            return sum(
                1 for qj in self._queued_jobs.values() if qj.status == QueuedJobStatus.FAILED
            )

    @property
    def total_count(self) -> int:
        """Get total number of jobs in queue."""
        with self._lock:
            return len(self._queued_jobs)

    def get_jobs(self) -> list[QueuedJob]:
        """Get all jobs in the queue."""
        with self._lock:
            return list(self._queued_jobs.values())

    def get_running_jobs(self) -> list[QueuedJob]:
        """Get currently running jobs."""
        with self._lock:
            return [qj for qj in self._queued_jobs.values() if qj.is_running]

    def get_job(self, job_id: str) -> QueuedJob | None:
        """Get a specific job by ID."""
        with self._lock:
            return self._queued_jobs.get(job_id)

    def submit(self, job: Job) -> bool:
        """Submit a job to the queue.

        Args:
            job: The job to execute

        Returns:
            True if job was submitted, False if already in queue
        """
        if self._executor_fn is None:
            raise RuntimeError("No executor function set. Call set_executor() first.")

        with self._lock:
            if job.job_id in self._queued_jobs:
                return False

            queued_job = QueuedJob(job=job)
            self._queued_jobs[job.job_id] = queued_job

            # Submit to thread pool
            future = self._executor.submit(self._run_job, queued_job)
            queued_job.future = future

        return True

    def submit_many(self, jobs: list[Job]) -> int:
        """Submit multiple jobs to the queue.

        Args:
            jobs: List of jobs to execute

        Returns:
            Number of jobs actually submitted (excludes duplicates)
        """
        submitted = 0
        for job in jobs:
            if self.submit(job):
                submitted += 1
        return submitted

    def cancel(self, job_id: str) -> bool:
        """Request cancellation of a job.

        Args:
            job_id: ID of job to cancel

        Returns:
            True if cancellation requested, False if job not found
        """
        with self._lock:
            queued_job = self._queued_jobs.get(job_id)
            if queued_job is None:
                return False

            queued_job.request_cancel()

            # If still queued (not started), cancel the future
            if queued_job.status == QueuedJobStatus.QUEUED and queued_job.future:
                cancelled = queued_job.future.cancel()
                if cancelled:
                    queued_job.status = QueuedJobStatus.CANCELLED
                    if self._job_manager:
                        self._job_manager.update_status(job_id, JobStatus.CANCELLED)

        return True

    def cancel_all(self) -> int:
        """Request cancellation of all jobs.

        Returns:
            Number of jobs cancelled
        """
        cancelled = 0
        with self._lock:
            job_ids = list(self._queued_jobs.keys())

        for job_id in job_ids:
            if self.cancel(job_id):
                cancelled += 1

        return cancelled

    def remove_completed(self) -> int:
        """Remove completed/failed/cancelled jobs from queue.

        Returns:
            Number of jobs removed
        """
        with self._lock:
            to_remove = [job_id for job_id, qj in self._queued_jobs.items() if qj.is_done]
            for job_id in to_remove:
                del self._queued_jobs[job_id]
            return len(to_remove)

    def clear(self) -> None:
        """Clear the queue, cancelling all pending jobs."""
        self.cancel_all()
        with self._lock:
            self._queued_jobs.clear()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if not wait:
            self.cancel_all()

        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def _run_job(self, queued_job: QueuedJob) -> None:
        """Execute a job in a worker thread."""
        job = queued_job.job
        job_id = job.job_id

        # Check if cancelled before starting
        if queued_job.cancel_requested:
            with self._lock:
                queued_job.status = QueuedJobStatus.CANCELLED
            if self._job_manager:
                self._job_manager.update_status(job_id, JobStatus.CANCELLED)
            self._notify_complete(job_id, False, "Cancelled before start")
            return

        # Mark as running
        with self._lock:
            queued_job.status = QueuedJobStatus.RUNNING

        if self._job_manager:
            self._job_manager.update_status(job_id, JobStatus.CONVERTING)

        # Create cancellation checker
        def check_cancelled() -> bool:
            return queued_job.cancel_requested

        # Execute the job
        try:
            success = self._executor_fn(job, check_cancelled)

            with self._lock:
                if queued_job.cancel_requested:
                    queued_job.status = QueuedJobStatus.CANCELLED
                    if self._job_manager:
                        self._job_manager.update_status(job_id, JobStatus.CANCELLED)
                    self._notify_complete(job_id, False, "Cancelled")
                elif success:
                    queued_job.status = QueuedJobStatus.COMPLETED
                    if self._job_manager:
                        self._job_manager.complete_job(job_id)
                    self._notify_complete(job_id, True, None)
                else:
                    queued_job.status = QueuedJobStatus.FAILED
                    queued_job.error_message = "Job returned failure"
                    if self._job_manager:
                        self._job_manager.set_error(job_id, "Job returned failure")
                    self._notify_complete(job_id, False, "Job returned failure")

        except Exception as e:
            error_msg = str(e)
            with self._lock:
                queued_job.status = QueuedJobStatus.FAILED
                queued_job.error_message = error_msg

            if self._job_manager:
                self._job_manager.set_error(job_id, error_msg)

            self._notify_complete(job_id, False, error_msg)

    def _notify_complete(self, job_id: str, success: bool, error_message: str | None) -> None:
        """Notify completion callback if set."""
        if self._on_job_complete:
            try:
                self._on_job_complete(job_id, success, error_message)
            except Exception:
                pass  # Don't let callback errors crash the worker


def create_job_queue(max_workers: int = 3, event_bus: EventBus | None = None) -> JobQueue:
    """Create a new job queue with the specified configuration.

    Args:
        max_workers: Maximum concurrent jobs (default 3)
        event_bus: Optional event bus for progress notifications

    Returns:
        Configured JobQueue instance
    """
    return JobQueue(max_workers=max_workers, event_bus=event_bus)
