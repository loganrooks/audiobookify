"""
Batch Processing Module for audiobookify

This module provides batch processing capabilities for converting
multiple EPUB files to audiobooks.

Features:
- Folder scanning for EPUB files
- Progress tracking across multiple books
- Skip already-processed files
- Summary reports
- Configurable processing options
"""

import glob
import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProcessingStatus(Enum):
    """Status of a book in the processing queue."""

    PENDING = "pending"
    EXPORTING = "exporting"
    CONVERTING = "converting"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BookTask:
    """Represents a single book to be processed."""

    epub_path: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    txt_path: str | None = None
    m4b_path: str | None = None
    cover_path: str | None = None
    error_message: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    chapter_count: int = 0
    file_size: int = 0

    def __post_init__(self):
        if os.path.exists(self.epub_path):
            self.file_size = os.path.getsize(self.epub_path)

    @property
    def duration(self) -> float | None:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def basename(self) -> str:
        """Get the base filename without extension."""
        return os.path.splitext(os.path.basename(self.epub_path))[0]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "epub_path": self.epub_path,
            "status": self.status.value,
            "txt_path": self.txt_path,
            "m4b_path": self.m4b_path,
            "cover_path": self.cover_path,
            "error_message": self.error_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "chapter_count": self.chapter_count,
            "file_size": self.file_size,
        }


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    # Input/Output
    input_path: str  # File or directory
    output_dir: str | None = None  # Output directory (default: same as input)
    recursive: bool = False  # Scan subdirectories

    # Processing options
    speaker: str = "en-US-AndrewNeural"
    detection_method: str = "combined"
    hierarchy_style: str = "flat"
    max_depth: int | None = None
    sentence_pause: int = 1200
    paragraph_pause: int = 1200

    # TTS parameters
    tts_rate: str | None = None  # Speech rate (e.g., "+20%", "-10%")
    tts_volume: str | None = None  # Volume adjustment (e.g., "+50%", "-25%")

    # Chapter selection
    chapters: str | None = None  # Chapter selection (e.g., "1-5", "1,3,7")

    # Batch options
    skip_existing: bool = True  # Skip if M4B already exists
    export_only: bool = False  # Only export to TXT, don't convert to audio
    continue_on_error: bool = True  # Continue processing if one book fails
    save_state: bool = True  # Save processing state for resume

    # Filters
    include_pattern: str | None = None  # Glob pattern to include
    exclude_pattern: str | None = None  # Glob pattern to exclude

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BatchResult:
    """Results of a batch processing run."""

    config: BatchConfig
    tasks: list[BookTask] = field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None

    @property
    def total_count(self) -> int:
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == ProcessingStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == ProcessingStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == ProcessingStatus.SKIPPED)

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == ProcessingStatus.PENDING)

    @property
    def duration(self) -> float | None:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def get_summary(self) -> str:
        """Generate a summary report."""
        lines = [
            "=" * 60,
            "BATCH PROCESSING SUMMARY",
            "=" * 60,
            "",
            f"Total books:     {self.total_count}",
            f"Completed:       {self.completed_count}",
            f"Failed:          {self.failed_count}",
            f"Skipped:         {self.skipped_count}",
            f"Pending:         {self.pending_count}",
            "",
        ]

        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            lines.append(f"Total time:      {minutes}m {seconds}s")
            lines.append("")

        # List completed books
        completed = [t for t in self.tasks if t.status == ProcessingStatus.COMPLETED]
        if completed:
            lines.append("Completed books:")
            for task in completed:
                duration_str = ""
                if task.duration:
                    mins = int(task.duration // 60)
                    secs = int(task.duration % 60)
                    duration_str = f" ({mins}m {secs}s)"
                lines.append(f"  ✓ {task.basename}{duration_str}")
            lines.append("")

        # List failed books
        failed = [t for t in self.tasks if t.status == ProcessingStatus.FAILED]
        if failed:
            lines.append("Failed books:")
            for task in failed:
                error = task.error_message or "Unknown error"
                lines.append(f"  ✗ {task.basename}: {error}")
            lines.append("")

        # List skipped books
        skipped = [t for t in self.tasks if t.status == ProcessingStatus.SKIPPED]
        if skipped:
            lines.append("Skipped books (already processed):")
            for task in skipped:
                lines.append(f"  - {task.basename}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "config": self.config.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "summary": {
                "total": self.total_count,
                "completed": self.completed_count,
                "failed": self.failed_count,
                "skipped": self.skipped_count,
                "pending": self.pending_count,
            },
        }

    def save_report(self, output_path: str | None = None) -> str:
        """Save the batch report to a JSON file."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = self.config.output_dir or os.path.dirname(self.config.input_path)
            output_path = os.path.join(output_dir, f"batch_report_{timestamp}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        return output_path


class BatchProcessor:
    """
    Batch processor for converting multiple EPUB files to audiobooks.

    Usage:
        processor = BatchProcessor(config)
        result = processor.run()
        print(result.get_summary())
    """

    STATE_FILE = ".audiobookify_state.json"

    def __init__(
        self,
        config: BatchConfig,
        progress_callback: Callable[[BookTask, int, int], None] | None = None,
    ):
        self.config = config
        self.progress_callback = progress_callback
        self.result = BatchResult(config=config)
        self._state_file: str | None = None

    def discover_books(self) -> list[str]:
        """
        Discover ebook files (EPUB, MOBI, AZW) to process based on configuration.

        Returns:
            List of ebook file paths
        """
        # Supported formats
        supported_extensions = (".epub", ".mobi", ".azw", ".azw3")

        book_files = []
        input_path = self.config.input_path

        if os.path.isfile(input_path):
            # Single file
            if input_path.lower().endswith(supported_extensions):
                book_files.append(input_path)
        elif os.path.isdir(input_path):
            # Directory - scan for all supported formats
            for ext in supported_extensions:
                if self.config.recursive:
                    pattern = os.path.join(input_path, "**", f"*{ext}")
                    book_files.extend(glob.glob(pattern, recursive=True))
                else:
                    pattern = os.path.join(input_path, f"*{ext}")
                    book_files.extend(glob.glob(pattern))

            # Remove duplicates (in case of overlapping patterns)
            book_files = list(set(book_files))

            # Apply include pattern
            if self.config.include_pattern:
                include_pattern = os.path.join(input_path, self.config.include_pattern)
                included = set(glob.glob(include_pattern, recursive=self.config.recursive))
                book_files = [f for f in book_files if f in included]

            # Apply exclude pattern
            if self.config.exclude_pattern:
                exclude_pattern = os.path.join(input_path, self.config.exclude_pattern)
                excluded = set(glob.glob(exclude_pattern, recursive=self.config.recursive))
                book_files = [f for f in book_files if f not in excluded]

        # Sort for consistent ordering
        book_files.sort()

        return book_files

    def should_skip(self, epub_path: str) -> bool:
        """Check if a book should be skipped (already processed)."""
        if not self.config.skip_existing:
            return False

        # Determine output paths
        output_dir = self.config.output_dir or os.path.dirname(epub_path)
        basename = os.path.splitext(os.path.basename(epub_path))[0]

        if self.config.export_only:
            # Check for TXT file
            txt_path = os.path.join(output_dir, f"{basename}.txt")
            return os.path.exists(txt_path)
        else:
            # Check for M4B file
            m4b_pattern = os.path.join(output_dir, f"{basename}*.m4b")
            return len(glob.glob(m4b_pattern)) > 0

    def _get_state_file_path(self) -> str:
        """Get the path to the state file."""
        output_dir = self.config.output_dir or os.path.dirname(self.config.input_path)
        if os.path.isfile(self.config.input_path):
            output_dir = os.path.dirname(self.config.input_path)
        return os.path.join(output_dir, self.STATE_FILE)

    def _save_state(self):
        """Save current processing state for resume."""
        if not self.config.save_state:
            return

        state_file = self._get_state_file_path()
        state = {
            "config": self.config.to_dict(),
            "tasks": [t.to_dict() for t in self.result.tasks],
            "timestamp": datetime.now().isoformat(),
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> bool:
        """Load previous processing state if available."""
        state_file = self._get_state_file_path()

        if not os.path.exists(state_file):
            return False

        try:
            with open(state_file, encoding="utf-8") as f:
                state = json.load(f)

            # Restore tasks
            for task_dict in state.get("tasks", []):
                task = BookTask(
                    epub_path=task_dict["epub_path"],
                    status=ProcessingStatus(task_dict["status"]),
                    txt_path=task_dict.get("txt_path"),
                    m4b_path=task_dict.get("m4b_path"),
                    cover_path=task_dict.get("cover_path"),
                    error_message=task_dict.get("error_message"),
                    chapter_count=task_dict.get("chapter_count", 0),
                )
                self.result.tasks.append(task)

            return True

        except Exception as e:
            print(f"Warning: Could not load state file: {e}")
            return False

    def _clear_state(self):
        """Clear the state file after successful completion."""
        state_file = self._get_state_file_path()
        if os.path.exists(state_file):
            os.remove(state_file)

    def prepare(self) -> list[BookTask]:
        """
        Prepare the processing queue.

        Returns:
            List of BookTask objects to process
        """
        # Try to load previous state
        if self.config.save_state and self._load_state():
            # Filter out completed tasks, keep pending/failed
            pending = [
                t
                for t in self.result.tasks
                if t.status in (ProcessingStatus.PENDING, ProcessingStatus.FAILED)
            ]
            if pending:
                print(f"Resuming previous batch: {len(pending)} books remaining")
                return pending

        # Fresh start - discover books
        epub_files = self.discover_books()

        if not epub_files:
            print("No EPUB files found to process")
            return []

        # Create tasks
        self.result.tasks = []
        for epub_path in epub_files:
            task = BookTask(epub_path=epub_path)

            if self.should_skip(epub_path):
                task.status = ProcessingStatus.SKIPPED
            else:
                task.status = ProcessingStatus.PENDING

            self.result.tasks.append(task)

        return [t for t in self.result.tasks if t.status == ProcessingStatus.PENDING]

    def process_book(self, task: BookTask, progress_callback: Callable | None = None) -> bool:
        """
        Process a single book.

        Args:
            task: The BookTask to process
            progress_callback: Optional callback for progress updates (receives ProgressInfo)

        Returns:
            True if successful, False otherwise
        """
        # Import here to avoid circular imports
        from ebooklib import epub

        from .chapter_detector import ChapterDetector, DetectionMethod, HierarchyStyle
        from .epub2tts_edge import (
            add_cover,
            ensure_punkt,
            generate_metadata,
            get_book,
            make_m4b,
            read_book,
        )

        task.start_time = time.time()
        task.status = ProcessingStatus.EXPORTING

        try:
            ensure_punkt()

            # Determine output paths
            output_dir = self.config.output_dir or os.path.dirname(task.epub_path)
            os.makedirs(output_dir, exist_ok=True)

            basename = task.basename

            # Set up output paths
            txt_path = os.path.join(output_dir, f"{basename}.txt")
            cover_path = os.path.join(output_dir, f"{basename}.png")

            # Export EPUB to TXT
            print(f"\nExporting: {basename}")
            epub.read_epub(task.epub_path)

            # Use chapter detector
            try:
                method_enum = DetectionMethod(self.config.detection_method)
                style_enum = HierarchyStyle(self.config.hierarchy_style)
            except ValueError:
                method_enum = DetectionMethod.COMBINED
                style_enum = HierarchyStyle.FLAT

            detector = ChapterDetector(
                task.epub_path,
                method=method_enum,
                max_depth=self.config.max_depth,
                hierarchy_style=style_enum,
            )
            detector.detect()
            detector.export_to_text(txt_path, include_metadata=True, level_markers=True)

            task.txt_path = txt_path
            task.chapter_count = len(detector.get_flat_chapters())

            # Check for cover
            if os.path.exists(cover_path):
                task.cover_path = cover_path

            if self.config.export_only:
                task.status = ProcessingStatus.COMPLETED
                task.end_time = time.time()
                return True

            # Convert to audiobook
            task.status = ProcessingStatus.CONVERTING
            print(f"Converting to audiobook: {basename}")

            # Change to output directory for intermediate files
            original_dir = os.getcwd()
            os.chdir(output_dir)

            try:
                book_contents, book_title, book_author, chapter_titles = get_book(txt_path)

                # Apply chapter selection if specified
                if self.config.chapters:
                    from .chapter_selector import ChapterSelector

                    selector = ChapterSelector(self.config.chapters)
                    selected_indices = selector.get_selected_indices(len(book_contents))
                    book_contents = [book_contents[i] for i in selected_indices]
                    chapter_titles = [chapter_titles[i] for i in selected_indices]
                    print(f"  {selector.get_summary()} ({len(book_contents)} chapters)")

                files = read_book(
                    book_contents,
                    self.config.speaker,
                    self.config.paragraph_pause,
                    self.config.sentence_pause,
                    rate=self.config.tts_rate,
                    volume=self.config.tts_volume,
                    progress_callback=progress_callback,
                )
                generate_metadata(files, book_author, book_title, chapter_titles)
                m4b_filename = make_m4b(files, txt_path, self.config.speaker)

                if task.cover_path:
                    add_cover(task.cover_path, m4b_filename)

                task.m4b_path = os.path.join(output_dir, m4b_filename)

            finally:
                os.chdir(original_dir)

            task.status = ProcessingStatus.COMPLETED
            task.end_time = time.time()
            return True

        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            task.end_time = time.time()
            print(f"Error processing {task.basename}: {e}")
            return False

    def run(self, resume: bool = True) -> BatchResult:
        """
        Run the batch processing.

        Args:
            resume: Whether to resume from previous state

        Returns:
            BatchResult with processing results
        """
        self.result.start_time = time.time()

        # Prepare queue
        pending_tasks = self.prepare()

        if not pending_tasks and not any(
            t.status == ProcessingStatus.SKIPPED for t in self.result.tasks
        ):
            print("No books to process")
            self.result.end_time = time.time()
            return self.result

        # Show summary
        total = len(self.result.tasks)
        pending = len(pending_tasks)
        skipped = sum(1 for t in self.result.tasks if t.status == ProcessingStatus.SKIPPED)

        print(f"\nBatch processing: {total} books found")
        print(f"  - {pending} to process")
        print(f"  - {skipped} already processed (skipped)")
        print()

        # Process each book
        for i, task in enumerate(pending_tasks):
            print(f"\n[{i + 1}/{pending}] Processing: {task.basename}")
            print("-" * 50)

            success = self.process_book(task)

            # Save state after each book
            self._save_state()

            # Call progress callback
            if self.progress_callback:
                self.progress_callback(task, i + 1, pending)

            # Check if we should continue
            if not success and not self.config.continue_on_error:
                print("Stopping due to error (continue_on_error=False)")
                break

        self.result.end_time = time.time()

        # Clear state file if all completed
        if self.result.pending_count == 0:
            self._clear_state()

        # Print summary
        print("\n" + self.result.get_summary())

        return self.result


def batch_process(
    input_path: str,
    output_dir: str | None = None,
    recursive: bool = False,
    speaker: str = "en-US-AndrewNeural",
    detection_method: str = "combined",
    hierarchy_style: str = "flat",
    max_depth: int | None = None,
    skip_existing: bool = True,
    export_only: bool = False,
    continue_on_error: bool = True,
    save_report: bool = True,
) -> BatchResult:
    """
    Convenience function for batch processing.

    Args:
        input_path: Path to EPUB file or directory containing EPUBs
        output_dir: Output directory (default: same as input)
        recursive: Scan subdirectories for EPUBs
        speaker: TTS voice to use
        detection_method: Chapter detection method
        hierarchy_style: Chapter hierarchy display style
        max_depth: Maximum chapter depth
        skip_existing: Skip already processed books
        export_only: Only export to TXT, don't convert to audio
        continue_on_error: Continue if one book fails
        save_report: Save JSON report after completion

    Returns:
        BatchResult with processing results
    """
    config = BatchConfig(
        input_path=input_path,
        output_dir=output_dir,
        recursive=recursive,
        speaker=speaker,
        detection_method=detection_method,
        hierarchy_style=hierarchy_style,
        max_depth=max_depth,
        skip_existing=skip_existing,
        export_only=export_only,
        continue_on_error=continue_on_error,
    )

    processor = BatchProcessor(config)
    result = processor.run()

    if save_report:
        report_path = result.save_report()
        print(f"\nReport saved to: {report_path}")

    return result
