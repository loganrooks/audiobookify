"""Job management for isolated audiobook conversions.

This module provides job isolation to prevent file collisions between
concurrent or sequential conversions of different books.

Each conversion job gets a unique folder containing:
- job.json: Job metadata and state
- Extracted text file
- Audio segment files (chapter_NNN.flac)
- Final M4B (moved to output when complete)

Example:
    >>> manager = JobManager()
    >>> job = manager.create_job("/path/to/book.epub")
    >>> print(job.job_dir)  # ~/.audiobookify/jobs/book_20241203_143022/
    >>> # ... do conversion work in job.job_dir ...
    >>> manager.complete_job(job.job_id, "/path/to/output/book.m4b")
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from epub2tts_edge.config import generate_job_slug, get_config


class JobStatus(Enum):
    """Status of a conversion job."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CONVERTING = "converting"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a single audiobook conversion job.

    Attributes:
        job_id: Unique identifier for this job (slug-based, e.g., derrida_writing_a1b2c3)
        source_file: Path to the source EPUB/MOBI file
        job_dir: Directory containing all job files
        audio_dir: Directory for intermediate audio files (defaults to job_dir/audio)
        title: Book title
        author: Book author
        status: Current job status
        created_at: Timestamp when job was created
        updated_at: Timestamp when job was last updated
        total_chapters: Total number of chapters
        completed_chapters: Number of chapters completed
        speaker: Voice being used
        rate: Speech rate adjustment
        volume: Volume adjustment
        output_path: Final output path for M4B (when complete)
        error_message: Error message if job failed
    """

    job_id: str
    source_file: str
    job_dir: str
    audio_dir: str | None = None  # Defaults to job_dir/audio if not specified
    title: str | None = None
    author: str | None = None
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    total_chapters: int = 0
    completed_chapters: int = 0
    speaker: str = "en-US-AndrewNeural"
    rate: str | None = None
    volume: str | None = None
    output_path: str | None = None
    error_message: str | None = None
    source_hash: str | None = None  # SHA256 hash for source file validation

    @property
    def is_resumable(self) -> bool:
        """Check if this job can be resumed.

        A job is resumable if:
        - Status is EXTRACTING or CONVERTING (not completed/failed/cancelled)
        - Has some chapters to process (total_chapters > 0)
        - Not already fully completed
        """
        return (
            self.status in (JobStatus.EXTRACTING, JobStatus.CONVERTING)
            and self.total_chapters > 0
            and self.completed_chapters < self.total_chapters
        )

    @property
    def progress_percentage(self) -> float:
        """Get progress as a percentage."""
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters / self.total_chapters) * 100

    @property
    def text_file(self) -> Path:
        """Path to the extracted text file."""
        source_name = Path(self.source_file).stem
        return Path(self.job_dir) / f"{source_name}.txt"

    @property
    def state_file(self) -> Path:
        """Path to the job state file."""
        return Path(self.job_dir) / "job.json"

    @property
    def effective_audio_dir(self) -> Path:
        """Get the effective audio directory for intermediate files."""
        if self.audio_dir:
            return Path(self.audio_dir)
        return Path(self.job_dir) / "audio"

    def get_chapter_audio_path(self, chapter_num: int) -> Path:
        """Get the path for a chapter's audio file."""
        return self.effective_audio_dir / f"chapter_{chapter_num:03d}.flac"

    def to_dict(self) -> dict[str, Any]:
        """Serialize job to dictionary."""
        return {
            "job_id": self.job_id,
            "source_file": self.source_file,
            "job_dir": self.job_dir,
            "audio_dir": self.audio_dir,
            "title": self.title,
            "author": self.author,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_chapters": self.total_chapters,
            "completed_chapters": self.completed_chapters,
            "speaker": self.speaker,
            "rate": self.rate,
            "volume": self.volume,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "source_hash": self.source_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Create job from dictionary."""
        return cls(
            job_id=data["job_id"],
            source_file=data["source_file"],
            job_dir=data["job_dir"],
            audio_dir=data.get("audio_dir"),
            title=data.get("title"),
            author=data.get("author"),
            status=JobStatus(data.get("status", "pending")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            total_chapters=data.get("total_chapters", 0),
            completed_chapters=data.get("completed_chapters", 0),
            speaker=data.get("speaker", "en-US-AndrewNeural"),
            rate=data.get("rate"),
            volume=data.get("volume"),
            output_path=data.get("output_path"),
            error_message=data.get("error_message"),
            source_hash=data.get("source_hash"),
        )


class JobManager:
    """Manages audiobook conversion jobs.

    Jobs are stored in a central directory configured via AppConfig.
    Each job gets a unique folder named with a human-readable slug.

    Example:
        >>> manager = JobManager()
        >>> job = manager.create_job(
        ...     "/path/to/book.epub",
        ...     title="Writing and Difference",
        ...     author="Jacques Derrida",
        ... )
        >>> print(job.job_id)  # derrida_writing-and-difference_a1b2c3
        >>> manager.update_progress(job.job_id, completed_chapters=5)
        >>> manager.complete_job(job.job_id, "/output/book.m4b")
    """

    def __init__(self, jobs_dir: str | None = None):
        """Initialize the job manager.

        Args:
            jobs_dir: Directory for storing jobs. If None, uses AppConfig.jobs_dir
        """
        if jobs_dir is None:
            config = get_config()
            self.jobs_dir = config.jobs_dir
        else:
            self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in file paths."""
        # Remove or replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Collapse multiple underscores/spaces
        sanitized = re.sub(r"[_\s]+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Limit length
        return sanitized[:50] if len(sanitized) > 50 else sanitized

    def _generate_job_id(self, source_file: str) -> str:
        """Generate a unique job ID from source file."""
        source_path = Path(source_file)
        name = self._sanitize_name(source_path.stem)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Add a short hash for uniqueness (include random for Windows low time resolution)
        hash_input = f"{source_file}{time.time()}{random.randint(0, 999999)}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"{name}_{timestamp}_{short_hash}"

    def _compute_source_hash(self, source_file: str) -> str:
        """Compute hash of source file for validation.

        Uses first 1MB of file for speed while maintaining uniqueness.

        Args:
            source_file: Path to the source file

        Returns:
            First 16 characters of SHA256 hash
        """
        hasher = hashlib.sha256()
        with open(source_file, "rb") as f:
            # Read first 1MB for speed
            hasher.update(f.read(1024 * 1024))
        return hasher.hexdigest()[:16]

    def create_job(
        self,
        source_file: str,
        title: str | None = None,
        author: str | None = None,
        speaker: str = "en-US-AndrewNeural",
        rate: str | None = None,
        volume: str | None = None,
    ) -> Job:
        """Create a new conversion job.

        Args:
            source_file: Path to the source EPUB/MOBI file
            title: Book title (used for human-readable slug)
            author: Book author (used for human-readable slug)
            speaker: Voice to use for TTS
            rate: Speech rate adjustment
            volume: Volume adjustment

        Returns:
            New Job instance with a unique job directory
        """
        source_file = str(Path(source_file).resolve())

        # Generate job ID using slug if title/author available, else fallback
        if title or author:
            config = get_config()
            job_id = generate_job_slug(title, author, config.job_slug_template)
        else:
            job_id = self._generate_job_id(source_file)

        job_dir = self.jobs_dir / job_id
        audio_dir = job_dir / "audio"

        # Create job and audio directories
        job_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Compute source hash for validation during resume
        source_hash = self._compute_source_hash(source_file)

        job = Job(
            job_id=job_id,
            source_file=source_file,
            job_dir=str(job_dir),
            audio_dir=str(audio_dir),
            title=title,
            author=author,
            speaker=speaker,
            rate=rate,
            volume=volume,
            source_hash=source_hash,
        )

        self._save_job(job)
        return job

    def _save_job(self, job: Job) -> None:
        """Save job state to disk."""
        job.updated_at = time.time()
        state_file = Path(job.job_dir) / "job.json"
        with open(state_file, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def load_job(self, job_id: str) -> Job | None:
        """Load a job by ID.

        Args:
            job_id: The job ID to load

        Returns:
            Job instance or None if not found
        """
        job_dir = self.jobs_dir / job_id
        state_file = job_dir / "job.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                data = json.load(f)
            return Job.from_dict(data)
        except (OSError, json.JSONDecodeError):
            return None

    def list_jobs(self, include_completed: bool = False) -> list[Job]:
        """List all jobs.

        Args:
            include_completed: Whether to include completed/failed jobs

        Returns:
            List of Job instances
        """
        jobs = []
        for job_dir in self.jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue

            state_file = job_dir / "job.json"
            if not state_file.exists():
                continue

            try:
                with open(state_file) as f:
                    data = json.load(f)
                job = Job.from_dict(data)

                if include_completed or job.status not in (
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ):
                    jobs.append(job)
            except (OSError, json.JSONDecodeError):
                continue

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def find_job_for_source(self, source_file: str) -> Job | None:
        """Find an existing resumable job for a source file.

        Args:
            source_file: Path to the source file

        Returns:
            Resumable Job instance or None
        """
        source_file = str(Path(source_file).resolve())

        for job in self.list_jobs():
            if job.source_file == source_file and job.is_resumable:
                return job

        return None

    def validate_job_source(self, job: Job) -> bool:
        """Verify job's source file matches stored hash.

        This prevents resuming a job with a different file that has the same name,
        which would cause wrong audio to be used.

        Args:
            job: The job to validate

        Returns:
            True if source file matches (or no hash stored for old jobs)
        """
        # Old jobs without hash - allow resume with permissive behavior
        if not job.source_hash:
            return True

        # Source file no longer exists
        if not Path(job.source_file).exists():
            return False

        # Compare hashes
        current_hash = self._compute_source_hash(job.source_file)
        return current_hash == job.source_hash

    def update_status(self, job_id: str, status: JobStatus) -> None:
        """Update job status.

        Args:
            job_id: The job ID
            status: New status
        """
        job = self.load_job(job_id)
        if job:
            job.status = status
            self._save_job(job)

    def update_progress(
        self,
        job_id: str,
        completed_chapters: int | None = None,
        total_chapters: int | None = None,
    ) -> None:
        """Update job progress.

        Args:
            job_id: The job ID
            completed_chapters: Number of completed chapters
            total_chapters: Total number of chapters
        """
        job = self.load_job(job_id)
        if job:
            if completed_chapters is not None:
                job.completed_chapters = completed_chapters
            if total_chapters is not None:
                job.total_chapters = total_chapters
            self._save_job(job)

    def set_error(self, job_id: str, error_message: str) -> None:
        """Mark job as failed with error message.

        Args:
            job_id: The job ID
            error_message: Error description
        """
        job = self.load_job(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = error_message
            self._save_job(job)

    def complete_job(self, job_id: str, output_path: str, cleanup: bool = True) -> bool:
        """Mark job as complete and optionally move output.

        Args:
            job_id: The job ID
            output_path: Final output path for the M4B
            cleanup: Whether to clean up intermediate files

        Returns:
            True if successful
        """
        job = self.load_job(job_id)
        if not job:
            return False

        job.status = JobStatus.COMPLETED
        job.output_path = output_path
        self._save_job(job)

        if cleanup:
            self._cleanup_intermediates(job)

        return True

    def _cleanup_intermediates(self, job: Job) -> None:
        """Remove intermediate files, keeping only job.json."""
        job_dir = Path(job.job_dir)
        for file in job_dir.iterdir():
            if file.name != "job.json":
                try:
                    if file.is_dir():
                        shutil.rmtree(file)
                    else:
                        file.unlink()
                except OSError:
                    pass

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and all its files.

        Args:
            job_id: The job ID to delete

        Returns:
            True if deleted successfully
        """
        job_dir = self.jobs_dir / job_id
        if job_dir.exists():
            try:
                shutil.rmtree(job_dir)
                return True
            except OSError:
                return False
        return False

    def cleanup_old_jobs(self, days: int = 7) -> int:
        """Clean up completed/failed jobs older than specified days.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        cutoff = time.time() - (days * 24 * 60 * 60)
        deleted = 0

        for job in self.list_jobs(include_completed=True):
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                if job.updated_at < cutoff:
                    if self.delete_job(job.job_id):
                        deleted += 1

        return deleted

    def get_job_stats(self) -> dict[str, int]:
        """Get statistics about jobs.

        Returns:
            Dictionary with job counts by status
        """
        stats = {status.value: 0 for status in JobStatus}
        stats["total"] = 0

        for job in self.list_jobs(include_completed=True):
            stats[job.status.value] += 1
            stats["total"] += 1

        return stats
