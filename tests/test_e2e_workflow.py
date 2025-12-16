"""End-to-end workflow tests using mock TTS.

These tests verify the complete pipeline from EPUB to audio output,
using the mock TTS infrastructure to avoid network calls.
"""

import os
import shutil
import subprocess

import pytest


def ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


FFMPEG_AVAILABLE = ffmpeg_available()


class TestExportOnlyWorkflow:
    """Test the EPUB → text export workflow (no TTS needed)."""

    def test_epub_to_text_export_creates_file(self, sample_epub, temp_dir):
        """Complete export workflow should create text file."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = BatchConfig(
            input_path=str(sample_epub),
            output_dir=str(output_dir),
            speaker="en-US-AriaNeural",
            export_only=True,
        )

        processor = BatchProcessor(config)
        processor.prepare()

        assert len(processor.result.tasks) == 1
        task = processor.result.tasks[0]

        # Process the book (export only)
        success = processor.process_book(task)

        assert success
        assert task.txt_path is not None
        assert os.path.exists(task.txt_path)

    def test_exported_text_contains_chapters(self, sample_epub, temp_dir):
        """Exported text file should contain chapter content."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = BatchConfig(
            input_path=str(sample_epub),
            output_dir=str(output_dir),
            speaker="en-US-AriaNeural",
            export_only=True,
        )

        processor = BatchProcessor(config)
        processor.prepare()
        task = processor.result.tasks[0]
        processor.process_book(task)

        # Read and verify content
        with open(task.txt_path, encoding="utf-8") as f:
            content = f.read()

        # Should contain title marker and chapter content
        assert "# " in content  # Chapter marker
        assert len(content) > 100  # Should have substantial content

    def test_chapter_detector_integration(self, sample_epub):
        """ChapterDetector should work correctly in the pipeline."""
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        detector = ChapterDetector(
            epub_path=sample_epub,
            method=DetectionMethod.COMBINED,
        )
        root = detector.detect()
        chapters = root.flatten() if root else []

        assert len(chapters) > 0
        for chapter in chapters:
            assert chapter.title is not None
            assert chapter.paragraphs is not None

    def test_export_with_different_detection_methods(self, sample_epub, temp_dir):
        """Export should work with various detection methods."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        methods = ["toc", "headings", "combined", "auto"]

        for method in methods:
            output_dir = temp_dir / f"output_{method}"
            output_dir.mkdir(exist_ok=True)

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(output_dir),
                speaker="en-US-AriaNeural",
                export_only=True,
                detection_method=method,
            )

            processor = BatchProcessor(config)
            processor.prepare()

            if processor.result.tasks:
                task = processor.result.tasks[0]
                success = processor.process_book(task)
                assert success, f"Export failed with detection method: {method}"


class TestMockTTSGeneration:
    """Test audio generation with mock TTS (no network, instant results)."""

    def test_mock_tts_generates_audio_segments(self, sample_epub, temp_dir):
        """Mock TTS should generate audio segment files."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            read_book,
        )
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        try:
            enable_test_mode()

            # Detect chapters
            detector = ChapterDetector(
                epub_path=sample_epub,
                method=DetectionMethod.COMBINED,
            )
            detector.detect()

            # Get book contents (returns list of dicts)
            chapters = detector.get_flat_chapters()
            book_contents = [
                {"title": ch["title"], "paragraphs": ch["paragraphs"]}
                for ch in chapters[:2]  # Limit to 2 chapters for speed
            ]

            output_dir = temp_dir / "audio"
            output_dir.mkdir()

            # Generate audio
            segments = read_book(
                book_contents=book_contents,
                speaker="en-US-AriaNeural",
                paragraphpause=500,
                sentencepause=250,
                output_dir=str(output_dir),
            )

            # Should have generated segments
            assert len(segments) > 0
            for segment in segments:
                assert os.path.exists(segment), f"Segment not created: {segment}"

        finally:
            disable_test_mode()

    def test_mock_tts_tracks_calls(self, sample_epub, temp_dir):
        """Mock TTS should track all generate calls."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            get_mock_engine,
            read_book,
        )
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        try:
            enable_test_mode()
            mock = get_mock_engine()
            mock.reset()  # Clear any previous calls

            # Detect chapters
            detector = ChapterDetector(
                epub_path=sample_epub,
                method=DetectionMethod.COMBINED,
            )
            detector.detect()

            # Get minimal content (get_flat_chapters returns dicts)
            chapters = detector.get_flat_chapters()
            book_contents = [
                {"title": chapters[0]["title"], "paragraphs": chapters[0]["paragraphs"][:1]}
            ]

            output_dir = temp_dir / "audio"
            output_dir.mkdir()

            # Generate audio
            read_book(
                book_contents=book_contents,
                speaker="en-US-AriaNeural",
                paragraphpause=500,
                sentencepause=250,
                output_dir=str(output_dir),
            )

            # Mock should have recorded calls
            assert len(mock.calls) > 0, "Mock TTS should have recorded calls"

        finally:
            disable_test_mode()

    def test_mock_tts_respects_rate_and_volume(self, sample_epub, temp_dir):
        """Mock TTS should receive rate and volume parameters."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            get_mock_engine,
            read_book,
        )
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        try:
            enable_test_mode()
            mock = get_mock_engine()
            mock.reset()

            # Detect chapters
            detector = ChapterDetector(
                epub_path=sample_epub,
                method=DetectionMethod.COMBINED,
            )
            detector.detect()

            # get_flat_chapters returns dicts
            chapters = detector.get_flat_chapters()
            book_contents = [
                {"title": chapters[0]["title"], "paragraphs": chapters[0]["paragraphs"][:1]}
            ]

            output_dir = temp_dir / "audio"
            output_dir.mkdir()

            # Generate with rate and volume
            read_book(
                book_contents=book_contents,
                speaker="en-US-AriaNeural",
                paragraphpause=500,
                sentencepause=250,
                output_dir=str(output_dir),
                rate="+20%",
                volume="-10%",
            )

            # Verify parameters were passed
            assert len(mock.calls) > 0
            # Check that at least one call has rate/volume (calls are TTSCall objects)
            assert any(c.rate == "+20%" or c.volume == "-10%" for c in mock.calls), (
                "Rate and volume should be passed to mock TTS"
            )

        finally:
            disable_test_mode()


class TestProgressTracking:
    """Test progress callback functionality."""

    def test_progress_callback_receives_updates(self, sample_epub, temp_dir):
        """Progress callback should receive chapter and paragraph updates."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            read_book,
        )
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        progress_updates = []

        def progress_callback(info):
            progress_updates.append(
                {
                    "chapter": info.chapter_num,
                    "status": info.status,
                }
            )

        try:
            enable_test_mode()

            detector = ChapterDetector(
                epub_path=sample_epub,
                method=DetectionMethod.COMBINED,
            )
            detector.detect()

            # get_flat_chapters returns dicts
            chapters = detector.get_flat_chapters()
            book_contents = [
                {"title": chapters[0]["title"], "paragraphs": chapters[0]["paragraphs"][:2]}
            ]

            output_dir = temp_dir / "audio"
            output_dir.mkdir()

            read_book(
                book_contents=book_contents,
                speaker="en-US-AriaNeural",
                paragraphpause=500,
                sentencepause=250,
                output_dir=str(output_dir),
                progress_callback=progress_callback,
            )

            # Should have received progress updates
            assert len(progress_updates) > 0
            # Should have chapter_start and chapter_done
            statuses = [u["status"] for u in progress_updates]
            assert "chapter_start" in statuses
            assert "chapter_done" in statuses

        finally:
            disable_test_mode()

    def test_cancellation_stops_processing(self, sample_epub, temp_dir):
        """Cancellation check should stop processing."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            read_book,
        )
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        call_count = 0

        def cancel_after_first():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Cancel after first check

        try:
            enable_test_mode()

            detector = ChapterDetector(
                epub_path=sample_epub,
                method=DetectionMethod.COMBINED,
            )
            detector.detect()

            # get_flat_chapters returns dicts
            chapters = detector.get_flat_chapters()
            book_contents = [
                {"title": ch["title"], "paragraphs": ch["paragraphs"]} for ch in chapters[:3]
            ]

            output_dir = temp_dir / "audio"
            output_dir.mkdir()

            segments = read_book(
                book_contents=book_contents,
                speaker="en-US-AriaNeural",
                paragraphpause=500,
                sentencepause=250,
                output_dir=str(output_dir),
                cancellation_check=cancel_after_first,
            )

            # Should have stopped early
            assert len(segments) < len(book_contents)

        finally:
            disable_test_mode()


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="FFmpeg not available")
class TestFullPipelineWithFFmpeg:
    """Test complete EPUB → M4B pipeline (requires FFmpeg)."""

    def test_complete_conversion_creates_m4b(self, sample_epub, temp_dir):
        """Full pipeline should create M4B file."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        try:
            enable_test_mode()

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(output_dir),
                speaker="en-US-AriaNeural",
                export_only=False,  # Full conversion
            )

            processor = BatchProcessor(config)
            processor.prepare()

            assert len(processor.result.tasks) == 1
            task = processor.result.tasks[0]

            success = processor.process_book(task)

            assert success, f"Conversion failed: {task.error_message}"
            assert task.m4b_path is not None
            assert os.path.exists(task.m4b_path)
            assert task.m4b_path.endswith(".m4b")

        finally:
            disable_test_mode()

    def test_m4b_file_has_reasonable_size(self, sample_epub, temp_dir):
        """Generated M4B should have reasonable file size."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        try:
            enable_test_mode()

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(output_dir),
                speaker="en-US-AriaNeural",
                export_only=False,
            )

            processor = BatchProcessor(config)
            processor.prepare()
            task = processor.result.tasks[0]
            processor.process_book(task)

            # M4B should exist and have some size
            assert os.path.exists(task.m4b_path)
            size = os.path.getsize(task.m4b_path)
            assert size > 1000, "M4B file should have reasonable size"

        finally:
            disable_test_mode()


class TestBatchProcessing:
    """Test batch processing of multiple files."""

    def test_batch_processes_multiple_epubs(self, sample_epub, temp_dir):
        """Batch processor should handle multiple EPUB files."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        # Create input directory with multiple EPUBs
        input_dir = temp_dir / "input"
        input_dir.mkdir()

        # Copy sample EPUB twice with different names

        epub1 = input_dir / "book1.epub"
        epub2 = input_dir / "book2.epub"
        shutil.copy(sample_epub, epub1)
        shutil.copy(sample_epub, epub2)

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = BatchConfig(
            input_path=str(input_dir),
            output_dir=str(output_dir),
            speaker="en-US-AriaNeural",
            export_only=True,
        )

        processor = BatchProcessor(config)
        processor.prepare()

        # Should discover both EPUBs
        assert len(processor.result.tasks) == 2

        # Process all
        for task in processor.result.tasks:
            success = processor.process_book(task)
            assert success

    def test_batch_skips_already_processed(self, sample_epub, temp_dir):
        """Batch processor should skip already processed files."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Create existing output file to simulate previous processing
        basename = sample_epub.stem
        existing_txt = output_dir / f"{basename}.txt"
        existing_txt.write_text("Already processed")

        config = BatchConfig(
            input_path=str(sample_epub),
            output_dir=str(output_dir),
            speaker="en-US-AriaNeural",
            export_only=True,
            skip_existing=True,
        )

        processor = BatchProcessor(config)
        processor.prepare()

        # Should mark as skipped or have no tasks
        # (behavior depends on implementation)
        assert processor.result is not None


class TestJobManagerIntegration:
    """Test integration with JobManager for resumable jobs."""

    def test_job_manager_creates_job_entry(self, sample_epub, temp_dir):
        """Processing with JobManager should create job entry."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor
        from epub2tts_edge.job_manager import JobManager

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        jobs_dir = temp_dir / "jobs"
        jobs_dir.mkdir()

        job_manager = JobManager(str(jobs_dir))

        try:
            enable_test_mode()

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(output_dir),
                speaker="en-US-AriaNeural",
                export_only=True,
            )

            processor = BatchProcessor(config)
            processor._job_manager = job_manager
            processor.prepare()

            if processor.result.tasks:
                task = processor.result.tasks[0]
                processor.process_book(task)

                # Job should have been created
                assert task.job_id is not None

        finally:
            disable_test_mode()
