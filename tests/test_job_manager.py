"""Tests for the job_manager module."""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from epub2tts_edge.job_manager import Job, JobManager, JobStatus


class TestJob:
    """Tests for the Job class."""

    def test_job_creation(self):
        """Test creating a job with defaults."""
        job = Job(
            job_id="test_job_123",
            source_file="/path/to/book.epub",
            job_dir="/path/to/jobs/test_job_123",
        )

        assert job.job_id == "test_job_123"
        assert job.source_file == "/path/to/book.epub"
        assert job.job_dir == "/path/to/jobs/test_job_123"
        assert job.status == JobStatus.PENDING
        assert job.total_chapters == 0
        assert job.completed_chapters == 0

    def test_job_is_resumable_true(self):
        """Test is_resumable returns True when partially complete."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test",
            status=JobStatus.CONVERTING,
            total_chapters=10,
            completed_chapters=5,
        )

        assert job.is_resumable is True

    def test_job_is_resumable_false_completed(self):
        """Test is_resumable returns False when completed."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test",
            status=JobStatus.COMPLETED,
            total_chapters=10,
            completed_chapters=10,
        )

        assert job.is_resumable is False

    def test_job_is_resumable_false_not_started(self):
        """Test is_resumable returns False when not started."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test",
            status=JobStatus.PENDING,
            total_chapters=10,
            completed_chapters=0,
        )

        assert job.is_resumable is False

    def test_job_progress_percentage(self):
        """Test progress_percentage calculation."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test",
            total_chapters=10,
            completed_chapters=5,
        )

        assert job.progress_percentage == 50.0

    def test_job_progress_percentage_zero_chapters(self):
        """Test progress_percentage returns 0 when no chapters."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test",
            total_chapters=0,
            completed_chapters=0,
        )

        assert job.progress_percentage == 0.0

    def test_job_text_file_path(self):
        """Test text_file property returns correct path."""
        job = Job(
            job_id="test",
            source_file="/path/to/MyBook.epub",
            job_dir="/tmp/test_job",
        )

        assert job.text_file == Path("/tmp/test_job/MyBook.txt")

    def test_job_state_file_path(self):
        """Test state_file property returns correct path."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test_job",
        )

        assert job.state_file == Path("/tmp/test_job/job.json")

    def test_job_get_chapter_audio_path(self):
        """Test get_chapter_audio_path returns correct path in audio subdirectory."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test_job",
        )

        # Audio files now go in the audio/ subdirectory
        assert job.get_chapter_audio_path(1) == Path("/tmp/test_job/audio/chapter_001.flac")
        assert job.get_chapter_audio_path(42) == Path("/tmp/test_job/audio/chapter_042.flac")

    def test_job_get_chapter_audio_path_with_audio_dir(self):
        """Test get_chapter_audio_path with explicit audio_dir."""
        job = Job(
            job_id="test",
            source_file="/path/to/book.epub",
            job_dir="/tmp/test_job",
            audio_dir="/custom/audio/dir",
        )

        # Should use the explicit audio_dir
        assert job.get_chapter_audio_path(1) == Path("/custom/audio/dir/chapter_001.flac")

    def test_job_to_dict(self):
        """Test serialization to dictionary."""
        job = Job(
            job_id="test_123",
            source_file="/path/to/book.epub",
            job_dir="/tmp/job",
            status=JobStatus.CONVERTING,
            total_chapters=10,
            completed_chapters=3,
            speaker="en-US-JennyNeural",
        )

        data = job.to_dict()

        assert data["job_id"] == "test_123"
        assert data["source_file"] == "/path/to/book.epub"
        assert data["status"] == "converting"
        assert data["total_chapters"] == 10
        assert data["completed_chapters"] == 3
        assert data["speaker"] == "en-US-JennyNeural"

    def test_job_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "job_id": "test_456",
            "source_file": "/path/to/other.epub",
            "job_dir": "/tmp/other_job",
            "status": "completed",
            "total_chapters": 20,
            "completed_chapters": 20,
            "speaker": "en-GB-RyanNeural",
            "output_path": "/output/book.m4b",
        }

        job = Job.from_dict(data)

        assert job.job_id == "test_456"
        assert job.source_file == "/path/to/other.epub"
        assert job.status == JobStatus.COMPLETED
        assert job.total_chapters == 20
        assert job.output_path == "/output/book.m4b"


class TestJobManager:
    """Tests for the JobManager class."""

    @pytest.fixture
    def temp_jobs_dir(self):
        """Create a temporary jobs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_jobs_dir):
        """Create a JobManager with temporary directory."""
        return JobManager(temp_jobs_dir)

    @pytest.fixture
    def temp_source_file(self):
        """Create a temporary source file."""
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
            f.write(b"fake epub content")
            yield f.name
        os.unlink(f.name)

    def test_init_creates_directory(self, temp_jobs_dir):
        """Test that __init__ creates the jobs directory."""
        subdir = os.path.join(temp_jobs_dir, "nested", "jobs")
        manager = JobManager(subdir)

        assert os.path.isdir(subdir)
        assert manager.jobs_dir == Path(subdir)

    def test_create_job(self, manager, temp_source_file):
        """Test creating a new job."""
        job = manager.create_job(temp_source_file)

        assert job.job_id is not None
        assert job.source_file == str(Path(temp_source_file).resolve())
        assert os.path.isdir(job.job_dir)
        assert os.path.isfile(os.path.join(job.job_dir, "job.json"))

    def test_create_job_with_options(self, manager, temp_source_file):
        """Test creating a job with custom options."""
        job = manager.create_job(
            temp_source_file,
            speaker="en-US-JennyNeural",
            rate="+20%",
            volume="-10%",
        )

        assert job.speaker == "en-US-JennyNeural"
        assert job.rate == "+20%"
        assert job.volume == "-10%"

    def test_create_job_with_metadata(self, manager, temp_source_file):
        """Test creating a job with title and author generates a readable slug."""
        job = manager.create_job(
            temp_source_file,
            title="Writing and Difference",
            author="Jacques Derrida",
        )

        # Job ID should be a slug based on author and title
        assert "derrida" in job.job_id
        assert "writing" in job.job_id
        assert job.title == "Writing and Difference"
        assert job.author == "Jacques Derrida"

        # Audio directory should be created
        assert job.audio_dir is not None
        assert Path(job.audio_dir).name == "audio"

    def test_load_job(self, manager, temp_source_file):
        """Test loading a job by ID."""
        original = manager.create_job(temp_source_file)

        loaded = manager.load_job(original.job_id)

        assert loaded is not None
        assert loaded.job_id == original.job_id
        assert loaded.source_file == original.source_file

    def test_load_job_not_found(self, manager):
        """Test loading a non-existent job returns None."""
        result = manager.load_job("nonexistent_job_id")

        assert result is None

    def test_list_jobs(self, manager, temp_source_file):
        """Test listing jobs."""
        job1 = manager.create_job(temp_source_file)
        time.sleep(0.1)  # Ensure different timestamps
        job2 = manager.create_job(temp_source_file)

        jobs = manager.list_jobs()

        assert len(jobs) == 2
        # Most recent first
        assert jobs[0].job_id == job2.job_id
        assert jobs[1].job_id == job1.job_id

    def test_list_jobs_excludes_completed(self, manager, temp_source_file):
        """Test listing jobs excludes completed by default."""
        job1 = manager.create_job(temp_source_file)
        job2 = manager.create_job(temp_source_file)

        # Complete job2
        manager.update_status(job2.job_id, JobStatus.COMPLETED)

        jobs = manager.list_jobs()

        assert len(jobs) == 1
        assert jobs[0].job_id == job1.job_id

    def test_list_jobs_include_completed(self, manager, temp_source_file):
        """Test listing jobs includes completed when requested."""
        manager.create_job(temp_source_file)
        job2 = manager.create_job(temp_source_file)

        manager.update_status(job2.job_id, JobStatus.COMPLETED)

        jobs = manager.list_jobs(include_completed=True)

        assert len(jobs) == 2

    def test_find_job_for_source_found(self, manager, temp_source_file):
        """Test finding a resumable job for a source file."""
        job = manager.create_job(temp_source_file)
        manager.update_status(job.job_id, JobStatus.CONVERTING)
        manager.update_progress(job.job_id, completed_chapters=3, total_chapters=10)

        found = manager.find_job_for_source(temp_source_file)

        assert found is not None
        assert found.job_id == job.job_id

    def test_find_job_for_source_not_resumable(self, manager, temp_source_file):
        """Test finding job returns None when not resumable."""
        job = manager.create_job(temp_source_file)
        manager.update_status(job.job_id, JobStatus.COMPLETED)

        found = manager.find_job_for_source(temp_source_file)

        assert found is None

    def test_update_status(self, manager, temp_source_file):
        """Test updating job status."""
        job = manager.create_job(temp_source_file)

        manager.update_status(job.job_id, JobStatus.CONVERTING)

        loaded = manager.load_job(job.job_id)
        assert loaded.status == JobStatus.CONVERTING

    def test_update_progress(self, manager, temp_source_file):
        """Test updating job progress."""
        job = manager.create_job(temp_source_file)

        manager.update_progress(job.job_id, completed_chapters=5, total_chapters=10)

        loaded = manager.load_job(job.job_id)
        assert loaded.completed_chapters == 5
        assert loaded.total_chapters == 10

    def test_set_error(self, manager, temp_source_file):
        """Test marking job as failed."""
        job = manager.create_job(temp_source_file)

        manager.set_error(job.job_id, "Something went wrong")

        loaded = manager.load_job(job.job_id)
        assert loaded.status == JobStatus.FAILED
        assert loaded.error_message == "Something went wrong"

    def test_complete_job(self, manager, temp_source_file):
        """Test completing a job."""
        job = manager.create_job(temp_source_file)
        output_path = "/output/book.m4b"

        result = manager.complete_job(job.job_id, output_path, cleanup=False)

        assert result is True
        loaded = manager.load_job(job.job_id)
        assert loaded.status == JobStatus.COMPLETED
        assert loaded.output_path == output_path

    def test_complete_job_with_cleanup(self, manager, temp_source_file):
        """Test completing a job with cleanup removes intermediate files."""
        job = manager.create_job(temp_source_file)

        # Create some fake intermediate files
        Path(job.job_dir, "test.txt").write_text("test")
        Path(job.job_dir, "chapter_001.flac").write_bytes(b"fake audio")

        manager.complete_job(job.job_id, "/output/book.m4b", cleanup=True)

        # job.json should remain
        assert os.path.exists(os.path.join(job.job_dir, "job.json"))
        # Intermediate files should be removed
        assert not os.path.exists(os.path.join(job.job_dir, "test.txt"))
        assert not os.path.exists(os.path.join(job.job_dir, "chapter_001.flac"))

    def test_delete_job(self, manager, temp_source_file):
        """Test deleting a job."""
        job = manager.create_job(temp_source_file)
        job_dir = job.job_dir

        result = manager.delete_job(job.job_id)

        assert result is True
        assert not os.path.exists(job_dir)

    def test_delete_job_not_found(self, manager):
        """Test deleting non-existent job returns False."""
        result = manager.delete_job("nonexistent")

        assert result is False

    def test_cleanup_old_jobs(self, manager, temp_source_file):
        """Test cleaning up old completed jobs."""
        # Create an "old" completed job
        job = manager.create_job(temp_source_file)
        manager.update_status(job.job_id, JobStatus.COMPLETED)

        # Modify the updated_at to be old
        loaded = manager.load_job(job.job_id)
        loaded.updated_at = time.time() - (10 * 24 * 60 * 60)  # 10 days ago
        state_file = Path(loaded.job_dir) / "job.json"
        with open(state_file, "w") as f:
            json.dump(loaded.to_dict(), f)

        deleted = manager.cleanup_old_jobs(days=7)

        assert deleted == 1
        assert not os.path.exists(job.job_dir)

    def test_get_job_stats(self, manager, temp_source_file):
        """Test getting job statistics."""
        job1 = manager.create_job(temp_source_file)
        job2 = manager.create_job(temp_source_file)
        # Create a third job that stays pending
        manager.create_job(temp_source_file)

        manager.update_status(job1.job_id, JobStatus.COMPLETED)
        manager.update_status(job2.job_id, JobStatus.FAILED)

        stats = manager.get_job_stats()

        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1

    def test_sanitize_name(self, manager):
        """Test name sanitization for job IDs."""
        result = manager._sanitize_name("My Book: A Tale of <Adventure> & More!")

        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert len(result) <= 50


class TestJobStatus:
    """Tests for the JobStatus enum."""

    def test_status_values(self):
        """Test all status values are accessible."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.EXTRACTING.value == "extracting"
        assert JobStatus.CONVERTING.value == "converting"
        assert JobStatus.FINALIZING.value == "finalizing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"
