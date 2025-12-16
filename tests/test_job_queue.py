"""Tests for parallel job queue functionality."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from epub2tts_edge.core.job_queue import (
    JobQueue,
    QueuedJob,
    QueuedJobStatus,
    create_job_queue,
)
from epub2tts_edge.job_manager import Job, JobStatus


@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    return Job(
        job_id="test_job_1",
        source_file="/books/test.epub",
        job_dir="/tmp/jobs/test_job_1",
        title="Test Book",
        author="Test Author",
        status=JobStatus.PENDING,
        total_chapters=5,
    )


@pytest.fixture
def sample_jobs():
    """Create multiple sample jobs for testing."""
    return [
        Job(
            job_id=f"test_job_{i}",
            source_file=f"/books/test{i}.epub",
            job_dir=f"/tmp/jobs/test_job_{i}",
            title=f"Test Book {i}",
            status=JobStatus.PENDING,
            total_chapters=3,
        )
        for i in range(1, 4)
    ]


class TestQueuedJob:
    """Tests for QueuedJob dataclass."""

    def test_init(self, sample_job):
        """QueuedJob initializes with defaults."""
        qj = QueuedJob(job=sample_job)
        assert qj.job == sample_job
        assert qj.status == QueuedJobStatus.QUEUED
        assert qj.future is None
        assert qj.cancel_requested is False
        assert qj.error_message is None

    def test_job_id_property(self, sample_job):
        """job_id returns underlying job ID."""
        qj = QueuedJob(job=sample_job)
        assert qj.job_id == "test_job_1"

    def test_is_running(self, sample_job):
        """is_running checks status correctly."""
        qj = QueuedJob(job=sample_job)
        assert qj.is_running is False

        qj.status = QueuedJobStatus.RUNNING
        assert qj.is_running is True

    def test_is_done(self, sample_job):
        """is_done returns True for terminal states."""
        qj = QueuedJob(job=sample_job)
        assert qj.is_done is False

        qj.status = QueuedJobStatus.COMPLETED
        assert qj.is_done is True

        qj.status = QueuedJobStatus.FAILED
        assert qj.is_done is True

        qj.status = QueuedJobStatus.CANCELLED
        assert qj.is_done is True

    def test_request_cancel(self, sample_job):
        """request_cancel sets flag."""
        qj = QueuedJob(job=sample_job)
        assert qj.cancel_requested is False

        qj.request_cancel()
        assert qj.cancel_requested is True


class TestJobQueueBasic:
    """Basic tests for JobQueue."""

    def test_create_job_queue(self):
        """create_job_queue creates configured queue."""
        queue = create_job_queue(max_workers=5)
        assert queue.max_workers == 5
        queue.shutdown(wait=False)

    def test_default_max_workers(self):
        """Default max_workers is 3."""
        queue = JobQueue()
        assert queue.max_workers == 3
        queue.shutdown(wait=False)

    def test_initial_counts(self):
        """New queue has zero counts."""
        queue = JobQueue()
        assert queue.running_count == 0
        assert queue.queued_count == 0
        assert queue.completed_count == 0
        assert queue.failed_count == 0
        assert queue.total_count == 0
        queue.shutdown(wait=False)


class TestJobQueueSubmit:
    """Tests for job submission."""

    def test_submit_requires_executor(self, sample_job):
        """Submit raises without executor function."""
        queue = JobQueue()
        with pytest.raises(RuntimeError, match="No executor function"):
            queue.submit(sample_job)
        queue.shutdown(wait=False)

    def test_submit_job(self, sample_job):
        """Can submit a job to the queue."""
        queue = JobQueue()
        execution_started = threading.Event()

        def slow_executor(job, check_cancelled):
            execution_started.set()
            while not check_cancelled():
                time.sleep(0.01)
            return True

        queue.set_executor(slow_executor)
        result = queue.submit(sample_job)

        assert result is True
        assert queue.total_count == 1

        # Wait for job to start running
        execution_started.wait(timeout=2)
        assert queue.running_count == 1

        queue.cancel(sample_job.job_id)
        queue.shutdown(wait=True)

    def test_submit_duplicate_fails(self, sample_job):
        """Cannot submit same job twice."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            time.sleep(0.5)
            return True

        queue.set_executor(executor)
        queue.submit(sample_job)
        result = queue.submit(sample_job)

        assert result is False
        assert queue.total_count == 1
        queue.shutdown(wait=False)

    def test_submit_many(self, sample_jobs):
        """submit_many adds multiple jobs."""
        queue = JobQueue()
        submitted_jobs = []

        def executor(job, check_cancelled):
            submitted_jobs.append(job.job_id)
            time.sleep(0.1)
            return True

        queue.set_executor(executor)
        count = queue.submit_many(sample_jobs)

        assert count == 3
        assert queue.total_count == 3
        queue.shutdown(wait=True)


class TestJobQueueExecution:
    """Tests for job execution."""

    def test_job_executes_successfully(self, sample_job):
        """Job executor is called and completes."""
        queue = JobQueue()
        executed = threading.Event()

        def executor(job, check_cancelled):
            executed.set()
            return True

        queue.set_executor(executor)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        assert executed.is_set()
        qj = queue.get_job(sample_job.job_id)
        assert qj.status == QueuedJobStatus.COMPLETED

    def test_job_failure(self, sample_job):
        """Failed job is marked as failed."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            return False

        queue.set_executor(executor)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        qj = queue.get_job(sample_job.job_id)
        assert qj.status == QueuedJobStatus.FAILED

    def test_job_exception(self, sample_job):
        """Exception in executor marks job failed."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            raise ValueError("Test error")

        queue.set_executor(executor)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        qj = queue.get_job(sample_job.job_id)
        assert qj.status == QueuedJobStatus.FAILED
        assert "Test error" in qj.error_message

    def test_completion_callback(self, sample_job):
        """Completion callback is called."""
        queue = JobQueue()
        callback_args = []

        def executor(job, check_cancelled):
            return True

        def on_complete(job_id, success, error):
            callback_args.append((job_id, success, error))

        queue.set_executor(executor)
        queue.set_completion_callback(on_complete)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        assert len(callback_args) == 1
        assert callback_args[0] == (sample_job.job_id, True, None)


class TestJobQueueCancellation:
    """Tests for job cancellation."""

    def test_cancel_running_job(self, sample_job):
        """Can cancel a running job."""
        queue = JobQueue()
        started = threading.Event()
        cancelled_check = []

        def executor(job, check_cancelled):
            started.set()
            while not check_cancelled():
                time.sleep(0.01)
            cancelled_check.append(True)
            return False

        queue.set_executor(executor)
        queue.submit(sample_job)

        # Wait for job to start
        started.wait(timeout=2)

        result = queue.cancel(sample_job.job_id)
        assert result is True

        queue.shutdown(wait=True)

        # Verify cancellation was checked
        assert len(cancelled_check) == 1
        qj = queue.get_job(sample_job.job_id)
        assert qj.status == QueuedJobStatus.CANCELLED

    def test_cancel_nonexistent(self):
        """Cancel returns False for unknown job."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            return True

        queue.set_executor(executor)
        result = queue.cancel("nonexistent")
        assert result is False
        queue.shutdown(wait=False)

    def test_cancel_all(self, sample_jobs):
        """cancel_all cancels all jobs."""
        queue = JobQueue(max_workers=1)
        started_count = []

        def executor(job, check_cancelled):
            started_count.append(job.job_id)
            while not check_cancelled():
                time.sleep(0.01)
            return False

        queue.set_executor(executor)
        queue.submit_many(sample_jobs)

        # Wait a moment for first job to start
        time.sleep(0.1)

        cancelled = queue.cancel_all()
        assert cancelled >= 1

        queue.shutdown(wait=True)


class TestJobQueueManagement:
    """Tests for queue management."""

    def test_get_jobs(self, sample_jobs):
        """get_jobs returns all jobs."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            time.sleep(0.5)
            return True

        queue.set_executor(executor)
        queue.submit_many(sample_jobs)

        jobs = queue.get_jobs()
        assert len(jobs) == 3
        queue.shutdown(wait=False)

    def test_get_running_jobs(self, sample_job):
        """get_running_jobs returns running jobs only."""
        queue = JobQueue()
        started = threading.Event()

        def executor(job, check_cancelled):
            started.set()
            while not check_cancelled():
                time.sleep(0.01)
            return True

        queue.set_executor(executor)
        queue.submit(sample_job)

        started.wait(timeout=2)

        running = queue.get_running_jobs()
        assert len(running) == 1
        assert running[0].job_id == sample_job.job_id

        queue.cancel(sample_job.job_id)
        queue.shutdown(wait=True)

    def test_remove_completed(self, sample_jobs):
        """remove_completed removes done jobs."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            return True

        queue.set_executor(executor)
        queue.submit_many(sample_jobs)
        queue.shutdown(wait=True)

        assert queue.completed_count == 3

        removed = queue.remove_completed()
        assert removed == 3
        assert queue.total_count == 0

    def test_clear(self, sample_jobs):
        """clear removes all jobs."""
        queue = JobQueue()

        def executor(job, check_cancelled):
            time.sleep(1)
            return True

        queue.set_executor(executor)
        queue.submit_many(sample_jobs)
        queue.clear()

        assert queue.total_count == 0
        queue.shutdown(wait=False)


class TestJobQueueConcurrency:
    """Tests for concurrent execution."""

    def test_parallel_execution(self):
        """Jobs run in parallel up to max_workers."""
        queue = JobQueue(max_workers=3)
        running_at_once = []
        lock = threading.Lock()
        barrier = threading.Barrier(3, timeout=5)

        def executor(job, check_cancelled):
            with lock:
                running_at_once.append(time.time())
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            return True

        queue.set_executor(executor)

        jobs = [
            Job(
                job_id=f"parallel_{i}",
                source_file=f"/books/p{i}.epub",
                job_dir=f"/tmp/jobs/parallel_{i}",
            )
            for i in range(3)
        ]

        queue.submit_many(jobs)
        queue.shutdown(wait=True)

        # All 3 jobs should have started at roughly the same time
        assert len(running_at_once) == 3
        time_spread = max(running_at_once) - min(running_at_once)
        assert time_spread < 1.0  # All started within 1 second

    def test_max_workers_limit(self):
        """Only max_workers jobs run concurrently."""
        queue = JobQueue(max_workers=2)
        concurrent_count = []
        current_running = [0]
        lock = threading.Lock()

        def executor(job, check_cancelled):
            with lock:
                current_running[0] += 1
                concurrent_count.append(current_running[0])
            time.sleep(0.1)
            with lock:
                current_running[0] -= 1
            return True

        queue.set_executor(executor)

        jobs = [
            Job(
                job_id=f"limit_{i}",
                source_file=f"/books/l{i}.epub",
                job_dir=f"/tmp/jobs/limit_{i}",
            )
            for i in range(5)
        ]

        queue.submit_many(jobs)
        queue.shutdown(wait=True)

        # Never more than 2 concurrent
        assert max(concurrent_count) <= 2


class TestJobQueueWithJobManager:
    """Tests for JobQueue with JobManager integration."""

    def test_updates_job_manager_status(self, sample_job):
        """Queue updates JobManager on status changes."""
        queue = JobQueue()
        mock_manager = MagicMock()

        def executor(job, check_cancelled):
            return True

        queue.set_executor(executor)
        queue.set_job_manager(mock_manager)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        # Should have called update_status and complete_job
        mock_manager.update_status.assert_called()
        mock_manager.complete_job.assert_called_with(sample_job.job_id)

    def test_updates_job_manager_on_failure(self, sample_job):
        """Queue updates JobManager on failure."""
        queue = JobQueue()
        mock_manager = MagicMock()

        def executor(job, check_cancelled):
            raise ValueError("Test error")

        queue.set_executor(executor)
        queue.set_job_manager(mock_manager)
        queue.submit(sample_job)
        queue.shutdown(wait=True)

        mock_manager.set_error.assert_called_once()
        call_args = mock_manager.set_error.call_args
        assert call_args[0][0] == sample_job.job_id
        assert "Test error" in call_args[0][1]
