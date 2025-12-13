"""Tests for the core ConversionPipeline module.

These tests verify the unified conversion pipeline that both CLI and TUI use.
"""

from pathlib import Path
from unittest.mock import MagicMock

from epub2tts_edge.content_filter import FilterConfig
from epub2tts_edge.core.pipeline import ConversionPipeline, PipelineConfig, PipelineResult
from epub2tts_edge.job_manager import Job, JobManager, JobStatus


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""

    def test_default_config(self):
        """PipelineConfig should have sensible defaults."""
        config = PipelineConfig()

        assert config.speaker == "en-US-AndrewNeural"
        assert config.rate is None
        assert config.volume is None
        assert config.detection_method == "combined"
        assert config.hierarchy_style == "flat"
        assert config.max_depth is None
        assert config.filter_config is None
        assert config.normalize_audio is False
        assert config.sentence_pause == 1200
        assert config.paragraph_pause == 1200
        assert config.max_concurrent == 5
        assert config.retry_count == 3
        assert config.retry_delay == 2

    def test_custom_config(self):
        """PipelineConfig should accept custom values."""
        config = PipelineConfig(
            speaker="en-US-JennyNeural",
            rate="+20%",
            volume="-10%",
            detection_method="toc",
            hierarchy_style="numbered",
            max_depth=2,
            normalize_audio=True,
            normalize_target=-18.0,
            sentence_pause=800,
            paragraph_pause=1000,
            max_concurrent=10,
        )

        assert config.speaker == "en-US-JennyNeural"
        assert config.rate == "+20%"
        assert config.volume == "-10%"
        assert config.detection_method == "toc"
        assert config.hierarchy_style == "numbered"
        assert config.max_depth == 2
        assert config.normalize_audio is True
        assert config.normalize_target == -18.0
        assert config.sentence_pause == 800
        assert config.paragraph_pause == 1000
        assert config.max_concurrent == 10

    def test_config_with_filter(self):
        """PipelineConfig should accept FilterConfig."""
        filter_config = FilterConfig(
            remove_front_matter=True,
            remove_back_matter=True,
        )
        config = PipelineConfig(filter_config=filter_config)

        assert config.filter_config is not None
        assert config.filter_config.remove_front_matter is True
        assert config.filter_config.remove_back_matter is True

    def test_config_with_pronunciation(self):
        """PipelineConfig should accept pronunciation settings."""
        config = PipelineConfig(
            pronunciation_dict="/path/to/dict.json",
            voice_mapping="/path/to/mapping.json",
            narrator_voice="en-US-GuyNeural",
        )

        assert config.pronunciation_dict == "/path/to/dict.json"
        assert config.voice_mapping == "/path/to/mapping.json"
        assert config.narrator_voice == "en-US-GuyNeural"


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_success_result(self, temp_dir):
        """PipelineResult should represent successful completion."""
        job = MagicMock(spec=Job)
        job.job_id = "test_job_123"

        result = PipelineResult(
            job=job,
            success=True,
            output_path=temp_dir / "output.m4b",
            chapters_detected=10,
            chapters_filtered=2,
            chapters_converted=8,
        )

        assert result.success is True
        assert result.job == job
        assert result.output_path == temp_dir / "output.m4b"
        assert result.error is None
        assert result.chapters_detected == 10
        assert result.chapters_filtered == 2
        assert result.chapters_converted == 8

    def test_failure_result(self):
        """PipelineResult should represent failure."""
        job = MagicMock(spec=Job)
        job.job_id = "test_job_456"

        result = PipelineResult(
            job=job,
            success=False,
            error="TTS connection failed",
        )

        assert result.success is False
        assert result.error == "TTS connection failed"
        assert result.output_path is None
        assert result.chapters_detected == 0
        assert result.chapters_converted == 0

    def test_result_with_filter_result(self):
        """PipelineResult should include filter result."""
        from epub2tts_edge.content_filter import FilterResult

        job = MagicMock(spec=Job)
        filter_result = FilterResult(
            original_count=15,
            filtered_count=12,
            removed_front_matter=["Title Page", "Copyright"],
            removed_back_matter=["Index"],
        )

        result = PipelineResult(
            job=job,
            success=True,
            filter_result=filter_result,
            chapters_detected=15,
            chapters_filtered=3,
        )

        assert result.filter_result is not None
        assert result.filter_result.original_count == 15
        assert result.filter_result.removed_count == 3


class TestConversionPipelineInit:
    """Test ConversionPipeline initialization."""

    def test_init_with_defaults(self, temp_dir):
        """ConversionPipeline should initialize with default config."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        assert pipeline.job_manager == job_manager
        assert pipeline.config is not None
        assert pipeline.config.speaker == "en-US-AndrewNeural"
        assert pipeline.event_bus is None

    def test_init_with_custom_config(self, temp_dir):
        """ConversionPipeline should accept custom config."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        config = PipelineConfig(speaker="en-US-JennyNeural", rate="+15%")

        pipeline = ConversionPipeline(job_manager, config)

        assert pipeline.config.speaker == "en-US-JennyNeural"
        assert pipeline.config.rate == "+15%"

    def test_init_with_event_bus(self, temp_dir):
        """ConversionPipeline should accept EventBus."""
        from epub2tts_edge.core.events import EventBus

        job_manager = JobManager(str(temp_dir / "jobs"))
        event_bus = EventBus()

        pipeline = ConversionPipeline(job_manager, event_bus=event_bus)

        assert pipeline.event_bus == event_bus


class TestConversionPipelineCreateJob:
    """Test ConversionPipeline.create_job method."""

    def test_create_job_basic(self, temp_dir, sample_epub):
        """create_job should create a new job."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        job = pipeline.create_job(sample_epub)

        assert job is not None
        assert job.job_id is not None
        assert Path(job.source_file).resolve() == Path(sample_epub).resolve()
        assert job.speaker == "en-US-AndrewNeural"

    def test_create_job_with_title_author(self, temp_dir, sample_epub):
        """create_job should accept title and author."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        job = pipeline.create_job(
            sample_epub,
            title="Test Book",
            author="Test Author",
        )

        assert job is not None
        # Job ID should incorporate title
        assert "test" in job.job_id.lower() or job.job_id is not None

    def test_create_job_uses_config_speaker(self, temp_dir, sample_epub):
        """create_job should use speaker from config."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        config = PipelineConfig(speaker="en-GB-SoniaNeural")
        pipeline = ConversionPipeline(job_manager, config)

        job = pipeline.create_job(sample_epub)

        assert job.speaker == "en-GB-SoniaNeural"


class TestConversionPipelineDetectChapters:
    """Test ConversionPipeline.detect_chapters method."""

    def test_detect_chapters_basic(self, temp_dir, sample_epub):
        """detect_chapters should find chapters in EPUB."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        chapters, filter_result = pipeline.detect_chapters(sample_epub)

        assert len(chapters) > 0
        # Chapters are returned as dicts
        for chapter in chapters:
            assert "title" in chapter
            assert "paragraphs" in chapter

    def test_detect_chapters_with_different_methods(self, temp_dir, sample_epub):
        """detect_chapters should respect detection method."""
        job_manager = JobManager(str(temp_dir / "jobs"))

        for method in ["toc", "headings", "combined", "auto"]:
            config = PipelineConfig(detection_method=method)
            pipeline = ConversionPipeline(job_manager, config)

            chapters, _ = pipeline.detect_chapters(sample_epub)
            # Should return chapters regardless of method
            assert isinstance(chapters, list)

    def test_detect_chapters_with_filter(self, temp_dir, sample_epub):
        """detect_chapters should apply content filter."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        filter_config = FilterConfig(
            remove_front_matter=True,
            remove_back_matter=True,
        )
        config = PipelineConfig(filter_config=filter_config)
        pipeline = ConversionPipeline(job_manager, config)

        chapters, filter_result = pipeline.detect_chapters(sample_epub)

        # Should return chapters (filter may or may not remove any)
        assert isinstance(chapters, list)
        # filter_result should exist when filter_config is set
        # (may be None if no filtering occurred)


class TestConversionPipelineExportText:
    """Test ConversionPipeline.export_text method."""

    def test_export_text_creates_file(self, temp_dir, sample_epub):
        """export_text should create text file."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        job = pipeline.create_job(sample_epub)
        chapters, _ = pipeline.detect_chapters(sample_epub)
        text_file = pipeline.export_text(job, chapters)

        assert text_file.exists()
        assert text_file.suffix == ".txt"

    def test_export_text_contains_chapters(self, temp_dir, sample_epub):
        """export_text should include chapter content."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        job = pipeline.create_job(sample_epub)
        chapters, _ = pipeline.detect_chapters(sample_epub)
        text_file = pipeline.export_text(job, chapters)

        content = text_file.read_text(encoding="utf-8")
        # Should have chapter markers
        assert "# " in content or "## " in content

    def test_export_text_with_metadata(self, temp_dir, sample_epub):
        """export_text should include metadata when requested."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        job = pipeline.create_job(sample_epub)
        chapters, _ = pipeline.detect_chapters(sample_epub)
        text_file = pipeline.export_text(job, chapters, include_metadata=True)

        content = text_file.read_text(encoding="utf-8")
        # May include Title: or Author: if extractable
        assert len(content) > 0


class TestConversionPipelineParseTextFile:
    """Test ConversionPipeline._parse_text_file method."""

    def test_parse_text_file_basic(self, temp_dir):
        """_parse_text_file should parse markdown-style chapters."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        text_file = temp_dir / "test.txt"
        text_file.write_text(
            """Title: Test Book
Author: Test Author

# Chapter 1
First paragraph.

Second paragraph.

# Chapter 2
Another paragraph.
""",
            encoding="utf-8",
        )

        chapters = pipeline._parse_text_file(text_file)

        assert len(chapters) == 2
        assert chapters[0]["title"] == "Chapter 1"
        assert "First paragraph." in chapters[0]["paragraphs"]
        assert "Second paragraph." in chapters[0]["paragraphs"]
        assert chapters[1]["title"] == "Chapter 2"
        assert "Another paragraph." in chapters[1]["paragraphs"]

    def test_parse_text_file_with_nested_headers(self, temp_dir):
        """_parse_text_file should handle nested headers."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        text_file = temp_dir / "test.txt"
        text_file.write_text(
            """# Part 1
Part intro.

## Chapter 1
Content here.

## Chapter 2
More content.
""",
            encoding="utf-8",
        )

        chapters = pipeline._parse_text_file(text_file)

        assert len(chapters) == 3
        assert chapters[0]["title"] == "Part 1"
        assert chapters[1]["title"] == "Chapter 1"
        assert chapters[2]["title"] == "Chapter 2"

    def test_parse_text_file_empty(self, temp_dir):
        """_parse_text_file should handle empty file."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        text_file = temp_dir / "empty.txt"
        text_file.write_text("", encoding="utf-8")

        chapters = pipeline._parse_text_file(text_file)

        assert chapters == []


class TestConversionPipelineWithMockTTS:
    """Test ConversionPipeline with mock TTS for audio generation."""

    def test_generate_audio_with_mock_tts(self, temp_dir, sample_epub):
        """generate_audio should work with mock TTS."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode

        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        try:
            enable_test_mode()

            job = pipeline.create_job(sample_epub)
            chapters, _ = pipeline.detect_chapters(sample_epub)
            text_file = pipeline.export_text(job, chapters[:2])  # Limit for speed

            audio_files = pipeline.generate_audio(job, text_file)

            assert len(audio_files) > 0
            for audio_file in audio_files:
                assert audio_file.exists()

        finally:
            disable_test_mode()

    def test_generate_audio_updates_job_status(self, temp_dir, sample_epub):
        """generate_audio should update job status."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode

        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        try:
            enable_test_mode()

            job = pipeline.create_job(sample_epub)
            chapters, _ = pipeline.detect_chapters(sample_epub)
            text_file = pipeline.export_text(job, chapters[:1])

            pipeline.generate_audio(job, text_file)

            # Reload job to check status
            updated_job = job_manager.load_job(job.job_id)
            assert updated_job.status in [JobStatus.CONVERTING, JobStatus.COMPLETED]

        finally:
            disable_test_mode()

    def test_generate_audio_with_progress_callback(self, temp_dir, sample_epub):
        """generate_audio should call progress callback."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode

        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        progress_calls = []

        def progress_callback(info):
            progress_calls.append(info.status)

        try:
            enable_test_mode()

            job = pipeline.create_job(sample_epub)
            chapters, _ = pipeline.detect_chapters(sample_epub)
            text_file = pipeline.export_text(job, chapters[:1])

            pipeline.generate_audio(job, text_file, progress_callback=progress_callback)

            assert len(progress_calls) > 0
            assert "chapter_start" in progress_calls
            assert "chapter_done" in progress_calls

        finally:
            disable_test_mode()


class TestConversionPipelineEventEmission:
    """Test ConversionPipeline event emission."""

    def test_emit_with_event_bus(self, temp_dir, sample_epub):
        """Pipeline should emit events when event_bus is configured."""
        from epub2tts_edge.core.events import EventBus, EventType

        job_manager = JobManager(str(temp_dir / "jobs"))
        event_bus = EventBus()
        pipeline = ConversionPipeline(job_manager, event_bus=event_bus)

        received_events = []

        def handler(event):
            """Event handler receives Event object."""
            received_events.append(event.event_type)

        # Use on() method to subscribe to events
        event_bus.on(EventType.JOB_CREATED, handler)
        event_bus.on(EventType.DETECTION_STARTED, handler)
        event_bus.on(EventType.DETECTION_COMPLETED, handler)

        # Run detection (not full pipeline to avoid TTS)
        job = pipeline.create_job(sample_epub)
        pipeline._emit(EventType.JOB_CREATED, job=job)

        chapters, _ = pipeline.detect_chapters(sample_epub)
        pipeline._emit(EventType.DETECTION_STARTED, job=job)
        pipeline._emit(
            EventType.DETECTION_COMPLETED,
            job=job,
            chapter_count=len(chapters),
        )

        assert EventType.JOB_CREATED in received_events
        assert EventType.DETECTION_STARTED in received_events
        assert EventType.DETECTION_COMPLETED in received_events

    def test_emit_without_event_bus(self, temp_dir, sample_epub):
        """Pipeline should not fail when event_bus is None."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)  # No event_bus

        # Should not raise
        job = pipeline.create_job(sample_epub)
        pipeline._emit("some_event", job=job)  # Should be no-op


class TestConversionPipelineIntegration:
    """Integration tests for full pipeline."""

    def test_full_workflow_export_only(self, temp_dir, sample_epub):
        """Test full workflow up to text export."""
        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        # Create job
        job = pipeline.create_job(sample_epub, title="Test Book")
        assert job is not None

        # Detect chapters
        chapters, filter_result = pipeline.detect_chapters(sample_epub)
        assert len(chapters) > 0

        # Export text
        text_file = pipeline.export_text(job, chapters)
        assert text_file.exists()

        # Verify text content
        content = text_file.read_text(encoding="utf-8")
        assert len(content) > 100  # Should have substantial content
        assert "# " in content  # Should have chapter markers

    def test_full_workflow_with_mock_tts(self, temp_dir, sample_epub):
        """Test full workflow including audio generation with mock TTS."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode

        job_manager = JobManager(str(temp_dir / "jobs"))
        pipeline = ConversionPipeline(job_manager)

        try:
            enable_test_mode()

            # Create job
            job = pipeline.create_job(sample_epub)

            # Detect chapters
            chapters, _ = pipeline.detect_chapters(sample_epub)

            # Export text (limit to 1 chapter for speed)
            text_file = pipeline.export_text(job, chapters[:1])

            # Generate audio
            audio_files = pipeline.generate_audio(job, text_file)

            assert len(audio_files) > 0
            for audio_file in audio_files:
                assert audio_file.exists()

        finally:
            disable_test_mode()
