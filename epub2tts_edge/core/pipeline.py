"""Conversion pipeline for audiobookify.

This module provides a unified pipeline for converting ebooks to audiobooks.
It orchestrates the workflow: detect → filter → export → generate → package.

Both CLI and TUI should use this pipeline to ensure consistent behavior.
Bug fixes in this module automatically apply to all interfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ..audio_generator import ProgressCallback, make_m4b, read_book
from ..chapter_detector import ChapterDetector, ChapterNode, DetectionMethod, HierarchyStyle
from ..content_filter import FilterConfig, FilterResult
from ..job_manager import Job, JobManager, JobStatus
from ..logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for conversion pipeline.

    This consolidates all conversion settings in one place.
    """

    # Voice settings
    speaker: str = "en-US-AndrewNeural"
    rate: str | None = None
    volume: str | None = None

    # Chapter detection
    detection_method: str = "combined"
    hierarchy_style: str = "flat"
    max_depth: int | None = None

    # Content filtering
    filter_config: FilterConfig | None = None

    # Audio processing
    normalize_audio: bool = False
    normalize_target: float = -16.0
    normalize_method: str = "peak"
    trim_silence: bool = False
    silence_threshold: int = -40
    max_silence_ms: int = 2000

    # Pause settings
    sentence_pause: int = 1200
    paragraph_pause: int = 1200

    # Performance
    max_concurrent: int = 5
    retry_count: int = 3
    retry_delay: int = 2

    # Pronunciation/multi-voice (optional)
    pronunciation_dict: str | None = None
    voice_mapping: str | None = None
    narrator_voice: str | None = None


@dataclass
class PipelineResult:
    """Result of a pipeline operation."""

    job: Job
    success: bool
    output_path: Path | None = None
    error: str | None = None
    chapters_detected: int = 0
    chapters_filtered: int = 0
    chapters_converted: int = 0
    filter_result: FilterResult | None = None


class ConversionPipeline:
    """Single source of truth for the conversion workflow.

    Used by both CLI and TUI for consistent behavior.
    Orchestrates: detect → filter → export → generate → package.

    Example usage::

        config = PipelineConfig(speaker="en-US-JennyNeural", rate="+10%")
        pipeline = ConversionPipeline(job_manager, config)

        # Full conversion
        result = pipeline.run(Path("book.epub"), progress_callback=my_callback)

        # Or step by step
        job = pipeline.create_job(Path("book.epub"), title="My Book")
        chapters, filter_result = pipeline.detect_chapters(Path("book.epub"))
        text_file = pipeline.export_text(job, chapters)
        audio_files = pipeline.generate_audio(job, text_file)
        output = pipeline.package_audiobook(job, audio_files)
    """

    def __init__(self, job_manager: JobManager, config: PipelineConfig | None = None):
        """Initialize the pipeline.

        Args:
            job_manager: JobManager instance for job persistence
            config: Pipeline configuration (uses defaults if None)
        """
        self.job_manager = job_manager
        self.config = config or PipelineConfig()

    def create_job(
        self,
        source_file: Path,
        title: str | None = None,
        author: str | None = None,
    ) -> Job:
        """Create a new conversion job.

        Args:
            source_file: Path to source EPUB/MOBI file
            title: Book title (for job naming)
            author: Book author (for job naming)

        Returns:
            New Job instance with persistent storage
        """
        job = self.job_manager.create_job(
            source_file=str(source_file),
            title=title,
            author=author,
            speaker=self.config.speaker,
            rate=self.config.rate,
            volume=self.config.volume,
        )
        logger.info("Created job: %s", job.job_id)
        return job

    def detect_chapters(
        self,
        source_file: Path,
    ) -> tuple[list[ChapterNode], FilterResult | None]:
        """Detect and optionally filter chapters from source file.

        Args:
            source_file: Path to source EPUB/MOBI file

        Returns:
            Tuple of (chapters, filter_result)
            filter_result is None if no filtering was applied
        """
        try:
            method = DetectionMethod(self.config.detection_method)
        except ValueError:
            method = DetectionMethod.COMBINED

        try:
            style = HierarchyStyle(self.config.hierarchy_style)
        except ValueError:
            style = HierarchyStyle.FLAT

        detector = ChapterDetector(
            str(source_file),
            method=method,
            max_depth=self.config.max_depth,
            hierarchy_style=style,
            filter_config=self.config.filter_config,
        )

        detector.detect()  # Populates internal state
        chapters = detector.get_flat_chapters()
        filter_result = detector.get_filter_result()

        logger.info(
            "Detected %d chapters (filtered: %s)",
            len(chapters),
            filter_result.removed_count if filter_result else 0,
        )

        return chapters, filter_result

    def export_text(
        self,
        job: Job,
        chapters: list[ChapterNode],
        include_metadata: bool = True,
    ) -> Path:
        """Export chapters to text file in job directory.

        Args:
            job: Job instance (provides output directory)
            chapters: List of chapters to export
            include_metadata: Whether to include title/author header

        Returns:
            Path to exported text file
        """
        # Determine output path in job directory
        source_name = Path(job.source_file).stem
        text_file = Path(job.job_dir) / f"{source_name}.txt"

        # Build text content
        lines = []

        if include_metadata:
            # Try to extract metadata from source
            try:
                from ebooklib import epub

                book = epub.read_epub(job.source_file)
                title = book.get_metadata("DC", "title")
                author = book.get_metadata("DC", "creator")
                if title:
                    lines.append(f"Title: {title[0][0]}")
                if author:
                    lines.append(f"Author: {author[0][0]}")
                lines.append("")
            except Exception:
                pass  # Skip metadata if can't extract

        # Export chapters with level markers
        for chapter in chapters:
            level_marker = "#" * (chapter.level + 1)
            lines.append(f"{level_marker} {chapter.title}")
            if chapter.paragraphs:
                for para in chapter.paragraphs:
                    lines.append(para)
                    lines.append("")
            lines.append("")

        # Write to file
        text_file.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Exported %d chapters to %s", len(chapters), text_file)

        return text_file

    def generate_audio(
        self,
        job: Job,
        text_file: Path,
        progress_callback: ProgressCallback | None = None,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> list[Path]:
        """Generate audio from text file.

        Args:
            job: Job instance (provides audio directory)
            text_file: Path to exported text file
            progress_callback: Optional callback for progress updates
            cancellation_check: Optional callable returning True to cancel

        Returns:
            List of generated audio segment paths
        """
        # Parse text file into chapters
        book_contents = self._parse_text_file(text_file)

        # Update job status
        self.job_manager.update_status(job.job_id, JobStatus.CONVERTING)
        self.job_manager.update_progress(job.job_id, total_chapters=len(book_contents))

        # Load pronunciation processor if configured
        pronunciation_processor = None
        if self.config.pronunciation_dict:
            from ..pronunciation import PronunciationProcessor

            pronunciation_processor = PronunciationProcessor(self.config.pronunciation_dict)

        # Load multi-voice processor if configured
        multi_voice_processor = None
        if self.config.voice_mapping:
            from ..multi_voice import MultiVoiceProcessor, VoiceMapping

            mapping = VoiceMapping.from_json(self.config.voice_mapping)
            if self.config.narrator_voice:
                mapping.default_voice = self.config.narrator_voice
            multi_voice_processor = MultiVoiceProcessor(mapping)

        # Generate audio
        audio_dir = job.effective_audio_dir
        audio_dir.mkdir(parents=True, exist_ok=True)

        segments = read_book(
            book_contents,
            speaker=self.config.speaker,
            paragraphpause=self.config.paragraph_pause,
            sentencepause=self.config.sentence_pause,
            output_dir=str(audio_dir),
            rate=self.config.rate,
            volume=self.config.volume,
            pronunciation_processor=pronunciation_processor,
            multi_voice_processor=multi_voice_processor,
            retry_count=self.config.retry_count,
            retry_delay=self.config.retry_delay,
            max_concurrent=self.config.max_concurrent,
            progress_callback=progress_callback,
            cancellation_check=cancellation_check,
            skip_completed=job.completed_chapters,
        )

        return [Path(s) for s in segments]

    def package_audiobook(
        self,
        job: Job,
        audio_files: list[Path],
        cover_image: Path | None = None,
    ) -> Path:
        """Create final M4B audiobook from audio segments.

        Args:
            job: Job instance
            audio_files: List of audio segment paths
            cover_image: Optional cover image path

        Returns:
            Path to final M4B file
        """
        self.job_manager.update_status(job.job_id, JobStatus.FINALIZING)

        # Determine output path
        source_name = Path(job.source_file).stem
        output_path = Path(job.job_dir) / f"{source_name}.m4b"

        # Get chapter info from text file
        text_file = Path(job.job_dir) / f"{source_name}.txt"
        book_contents = self._parse_text_file(text_file) if text_file.exists() else []

        # Create M4B
        make_m4b(
            files=[str(f) for f in audio_files],
            chapternames=[c.get("title", f"Chapter {i + 1}") for i, c in enumerate(book_contents)],
            cover=str(cover_image) if cover_image else None,
            output=str(output_path),
        )

        # Update job status
        self.job_manager.complete_job(job.job_id, str(output_path))
        logger.info("Created audiobook: %s", output_path)

        return output_path

    def run(
        self,
        source_file: Path,
        title: str | None = None,
        author: str | None = None,
        progress_callback: ProgressCallback | None = None,
        cancellation_check: Callable[[], bool] | None = None,
    ) -> PipelineResult:
        """Run the full conversion pipeline.

        This is the main entry point for converting an ebook to audiobook.
        Orchestrates: detect → filter → export → generate → package.

        Args:
            source_file: Path to source EPUB/MOBI file
            title: Book title (for job naming)
            author: Book author (for job naming)
            progress_callback: Optional callback for progress updates
            cancellation_check: Optional callable returning True to cancel

        Returns:
            PipelineResult with job, success status, and output path
        """
        job = None
        try:
            # Create job
            job = self.create_job(source_file, title, author)

            # Detect chapters
            self.job_manager.update_status(job.job_id, JobStatus.EXTRACTING)
            chapters, filter_result = self.detect_chapters(source_file)

            if not chapters:
                raise ValueError("No chapters detected in source file")

            # Export to text
            text_file = self.export_text(job, chapters)

            # Extract cover image
            cover_image = self._extract_cover(source_file, job)

            # Generate audio
            audio_files = self.generate_audio(job, text_file, progress_callback, cancellation_check)

            if cancellation_check and cancellation_check():
                self.job_manager.update_status(job.job_id, JobStatus.CANCELLED)
                return PipelineResult(
                    job=job,
                    success=False,
                    error="Cancelled by user",
                    chapters_detected=len(chapters),
                    filter_result=filter_result,
                )

            # Package audiobook
            output_path = self.package_audiobook(job, audio_files, cover_image)

            return PipelineResult(
                job=job,
                success=True,
                output_path=output_path,
                chapters_detected=len(chapters),
                chapters_filtered=filter_result.removed_count if filter_result else 0,
                chapters_converted=len(audio_files),
                filter_result=filter_result,
            )

        except Exception as e:
            logger.error("Pipeline error: %s", e)
            if job:
                self.job_manager.set_error(job.job_id, str(e))
            return PipelineResult(
                job=job,
                success=False,
                error=str(e),
            )

    def _parse_text_file(self, text_file: Path) -> list[dict]:
        """Parse text file into chapter dictionaries.

        Args:
            text_file: Path to text file

        Returns:
            List of dicts with 'title' and 'paragraphs' keys
        """
        content = text_file.read_text(encoding="utf-8")
        chapters = []
        current_chapter = None

        for line in content.split("\n"):
            line = line.rstrip()

            # Check for chapter header (# Title)
            if line.startswith("#"):
                # Save previous chapter
                if current_chapter:
                    chapters.append(current_chapter)

                # Start new chapter (strip # markers)
                title = line.lstrip("#").strip()
                current_chapter = {"title": title, "paragraphs": []}

            elif current_chapter is not None and line:
                # Add paragraph to current chapter
                current_chapter["paragraphs"].append(line)

        # Don't forget last chapter
        if current_chapter:
            chapters.append(current_chapter)

        return chapters

    def _extract_cover(self, source_file: Path, job: Job) -> Path | None:
        """Extract cover image from source file.

        Args:
            source_file: Path to source EPUB/MOBI
            job: Job instance (for output directory)

        Returns:
            Path to extracted cover image, or None
        """
        try:
            from PIL import Image

            # Try EPUB cover extraction
            if source_file.suffix.lower() == ".epub":
                from ..epub2tts_edge import get_epub_cover

                cover_data = get_epub_cover(str(source_file))
                if cover_data:
                    image = Image.open(cover_data)
                    cover_path = Path(job.job_dir) / f"{source_file.stem}.png"
                    image.save(str(cover_path))
                    logger.info("Extracted cover: %s", cover_path)
                    return cover_path

            # Try MOBI cover extraction
            elif source_file.suffix.lower() in (".mobi", ".azw", ".azw3"):
                from ..mobi_parser import MobiParser

                parser = MobiParser(str(source_file))
                book = parser.parse()
                if book.cover_image:
                    cover_path = Path(job.job_dir) / f"{source_file.stem}.png"
                    cover_path.write_bytes(book.cover_image)
                    logger.info("Extracted cover: %s", cover_path)
                    return cover_path

        except Exception as e:
            logger.warning("Could not extract cover: %s", e)

        return None
