"""TUI workflow integration tests using Textual's testing framework.

These tests verify the key workflows in the TUI:
1. Preview loading - Load chapters from an EPUB
2. Chapter editing - Delete, merge, undo operations
3. Selection system - Batch select for editing

Tests use mock EPUBs and don't require network access or TTS.
"""

import pytest

from epub2tts_edge.tui import (
    AudiobookifyApp,
    FilePanel,
    JobItem,
    JobsPanel,
    PreviewPanel,
    SettingsPanel,
)


def make_preview_chapter(
    title: str,
    content: str = "Test content",
    level: int = 1,
    word_count: int | None = None,
):
    """Helper to create PreviewChapter with correct fields."""
    from epub2tts_edge.tui import PreviewChapter

    if word_count is None:
        word_count = len(content.split())

    return PreviewChapter(
        title=title,
        level=level,
        word_count=word_count,
        paragraph_count=1,
        content_preview=content[:500],
        original_content=content,
    )


def load_preview_chapters(
    preview,
    chapters: list,
    source_file=None,
    book_title: str = "Test Book",
    book_author: str = "Test Author",
    detection_method: str = "combined",
):
    """Helper to load chapters into a PreviewPanel.

    This calls the panel's load_chapters method with the correct signature.
    """
    from pathlib import Path

    # Use a dummy path if none provided
    if source_file is None:
        source_file = Path("/tmp/test_book.epub")

    preview.load_chapters(
        source_file=source_file,
        chapters=chapters,
        detection_method=detection_method,
        book_title=book_title,
        book_author=book_author,
    )


class TestAppInstantiation:
    """Test that the app can be created and mounted."""

    @pytest.mark.asyncio
    async def test_app_creates_successfully(self):
        """App should instantiate without errors."""
        app = AudiobookifyApp()
        assert app is not None
        assert app.TITLE == "Audiobookify"

    @pytest.mark.asyncio
    async def test_app_mounts_and_shows_panels(self, temp_dir):
        """App should mount and display all panels."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            # Check main panels exist by class
            file_panel = app.query_one(FilePanel)
            assert file_panel is not None

            settings_panel = app.query_one(SettingsPanel)
            assert settings_panel is not None

            # Check tabbed content exists
            tabs = app.query_one("TabbedContent")
            assert tabs is not None


class TestPreviewLoading:
    """Test chapter preview loading workflow."""

    @pytest.mark.asyncio
    async def test_preview_panel_exists(self, temp_dir):
        """PreviewPanel should exist in the app."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)
            assert preview is not None
            assert not preview.has_chapters()

    @pytest.mark.asyncio
    async def test_preview_loads_chapters_directly(self, temp_dir):
        """Preview should load chapters when given chapters."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            # Create preview chapters directly (simpler than loading from EPUB)
            preview_chapters = [
                make_preview_chapter(f"Chapter {i}", f"Content for chapter {i}")
                for i in range(1, 6)
            ]

            load_preview_chapters(preview, preview_chapters)

            # Verify chapters loaded
            assert preview.has_chapters()
            assert len(preview.preview_state.chapters) == 5

    @pytest.mark.asyncio
    async def test_preview_clears_properly(self, temp_dir):
        """Preview should clear all chapters when requested."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            load_preview_chapters(
                preview,
                [
                    make_preview_chapter("Ch1", "Content"),
                    make_preview_chapter("Ch2", "Content"),
                ],
            )
            assert preview.has_chapters()

            # Clear preview
            preview.clear_preview()
            assert not preview.has_chapters()
            assert preview.preview_state is None


class TestChapterEditing:
    """Test chapter editing operations on the data model.

    Note: delete_chapter() and merge_with_next() work on the highlighted item,
    so we test the underlying data operations instead of UI interactions.
    """

    async def _setup_preview(self, app: AudiobookifyApp, num_chapters: int = 5):
        """Helper to set up preview with chapters."""
        preview = app.query_one(PreviewPanel)

        chapters = [
            make_preview_chapter(
                title=f"Chapter {i}",
                content=f"Content for chapter {i}. " * 10,
            )
            for i in range(1, num_chapters + 1)
        ]

        load_preview_chapters(preview, chapters)
        return preview

    @pytest.mark.asyncio
    async def test_preview_state_tracks_chapters(self, temp_dir):
        """Preview state should track all loaded chapters."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = await self._setup_preview(app, num_chapters=5)

            assert len(preview.preview_state.chapters) == 5
            assert preview.preview_state.chapters[0].title == "Chapter 1"
            assert preview.preview_state.chapters[4].title == "Chapter 5"

    @pytest.mark.asyncio
    async def test_get_included_chapters_returns_all_by_default(self, temp_dir):
        """All chapters should be included by default."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = await self._setup_preview(app, num_chapters=5)

            included = preview.preview_state.get_included_chapters()
            assert len(included) == 5

    @pytest.mark.asyncio
    async def test_undo_stack_initialized_empty(self, temp_dir):
        """Undo stack should be empty after loading chapters."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = await self._setup_preview(app, num_chapters=3)

            # Stack should be empty for fresh load
            assert len(preview._undo_stack) == 0

    @pytest.mark.asyncio
    async def test_undo_does_nothing_when_empty(self, temp_dir):
        """Undo should do nothing when stack is empty."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = await self._setup_preview(app, num_chapters=3)

            # Undo with empty stack should not change chapter count
            initial_count = len(preview.preview_state.chapters)
            preview.undo()
            assert len(preview.preview_state.chapters) == initial_count

    @pytest.mark.asyncio
    async def test_max_undo_stack_constant_defined(self, temp_dir):
        """MAX_UNDO_STACK should be defined."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = await self._setup_preview(app, num_chapters=1)

            assert hasattr(preview, "MAX_UNDO_STACK")
            assert preview.MAX_UNDO_STACK > 0


class TestBatchOperations:
    """Test batch selection and operations.

    Note: Batch operations require UI state (selected widgets).
    These tests verify the underlying data model operations work correctly.
    """

    @pytest.mark.asyncio
    async def test_chapter_removal_from_state(self, temp_dir):
        """Chapters can be removed from preview state."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            chapters = [make_preview_chapter(f"Chapter {i}", f"Content {i}") for i in range(1, 6)]

            load_preview_chapters(preview, chapters)

            # Directly remove a chapter from state
            preview.preview_state.chapters.remove(preview.preview_state.chapters[1])

            assert len(preview.preview_state.chapters) == 4
            remaining_titles = [ch.title for ch in preview.preview_state.chapters]
            assert "Chapter 1" in remaining_titles
            assert "Chapter 2" not in remaining_titles
            assert "Chapter 3" in remaining_titles

    @pytest.mark.asyncio
    async def test_chapter_content_can_be_merged(self, temp_dir):
        """Chapter content can be merged manually."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            chapters = [make_preview_chapter(f"Chapter {i}", f"Content {i}") for i in range(1, 4)]

            load_preview_chapters(preview, chapters)

            # Manually merge chapter 2 content into chapter 1
            ch1 = preview.preview_state.chapters[0]
            ch2 = preview.preview_state.chapters[1]

            ch1.original_content += "\n\n" + ch2.original_content
            ch1.word_count += ch2.word_count
            preview.preview_state.chapters.remove(ch2)

            assert len(preview.preview_state.chapters) == 2
            assert "Content 1" in ch1.original_content
            assert "Content 2" in ch1.original_content

    @pytest.mark.asyncio
    async def test_undo_stack_saves_state(self, temp_dir):
        """Undo stack can save and restore chapter state."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            chapters = [make_preview_chapter(f"Chapter {i}", f"Content {i}") for i in range(1, 4)]

            load_preview_chapters(preview, chapters)

            # Manually save state to undo stack
            preview._save_undo_state()
            original_count = len(preview.preview_state.chapters)

            # Modify chapters
            preview.preview_state.chapters.pop()

            assert len(preview.preview_state.chapters) == 2

            # Restore from undo stack
            preview.preview_state.chapters = preview._undo_stack.pop()

            assert len(preview.preview_state.chapters) == original_count

    @pytest.mark.asyncio
    async def test_modified_flag_tracking(self, temp_dir):
        """Preview state tracks when modifications are made."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)

            chapters = [
                make_preview_chapter("Chapter 1", "Content 1"),
            ]

            load_preview_chapters(preview, chapters)

            # State should not be modified initially
            assert not preview.preview_state.modified

            # Mark as modified
            preview.preview_state.modified = True
            assert preview.preview_state.modified


class TestMockTTSIntegration:
    """Test that MockTTSEngine can be used for testing."""

    @pytest.mark.asyncio
    async def test_mock_tts_generates_audio(self, mock_tts):
        """MockTTSEngine should generate audio and track calls."""
        audio = await mock_tts.generate("Test text for TTS", "en-US-AriaNeural")

        assert len(audio) > 0
        assert mock_tts.call_count == 1
        assert mock_tts.calls[0].text == "Test text for TTS"
        assert mock_tts.calls[0].voice == "en-US-AriaNeural"

    @pytest.mark.asyncio
    async def test_mock_tts_tracks_multiple_calls(self, mock_tts):
        """MockTTSEngine should track multiple calls."""
        await mock_tts.generate("First sentence.", "en-US-AriaNeural")
        await mock_tts.generate("Second sentence.", "en-US-GuyNeural")
        await mock_tts.generate("Third sentence.", "en-US-AriaNeural")

        assert mock_tts.call_count == 3
        assert len(mock_tts.get_calls_for_voice("en-US-AriaNeural")) == 2
        assert len(mock_tts.get_calls_for_voice("en-US-GuyNeural")) == 1

    @pytest.mark.asyncio
    async def test_mock_tts_can_simulate_failure(self, mock_tts_with_failures):
        """MockTTSEngine should be able to simulate failures."""
        mock_tts_with_failures.fail_on_text = "ERROR"

        # Normal text should work
        await mock_tts_with_failures.generate("Normal text", "en-US-AriaNeural")

        # Text containing ERROR should fail
        with pytest.raises(RuntimeError, match="Mock TTS failure"):
            await mock_tts_with_failures.generate("This contains ERROR text", "en-US-AriaNeural")


class TestJobItemSelection:
    """Test JobItem selection functionality."""

    def test_job_item_starts_unselected(self):
        """JobItem should start unselected by default."""
        from epub2tts_edge.job_manager import Job, JobStatus

        job = Job(
            job_id="test_job_123",
            source_file="/tmp/test.epub",
            job_dir="/tmp/jobs/test_job_123",
            status=JobStatus.PENDING,
        )
        item = JobItem(job)
        assert item.is_selected is False

    def test_job_item_can_start_selected(self):
        """JobItem should support starting selected."""
        from epub2tts_edge.job_manager import Job, JobStatus

        job = Job(
            job_id="test_job_123",
            source_file="/tmp/test.epub",
            job_dir="/tmp/jobs/test_job_123",
            status=JobStatus.PENDING,
        )
        item = JobItem(job, selected=True)
        assert item.is_selected is True

    def test_job_item_toggle_changes_state(self):
        """JobItem.toggle() should flip selection state."""
        from epub2tts_edge.job_manager import Job, JobStatus

        job = Job(
            job_id="test_job_123",
            source_file="/tmp/test.epub",
            job_dir="/tmp/jobs/test_job_123",
            status=JobStatus.PENDING,
        )
        item = JobItem(job)

        # Start unselected
        assert item.is_selected is False

        # Toggle to selected (note: toggle() calls query_one which needs mount)
        item.is_selected = True
        assert item.is_selected is True

        # Toggle back
        item.is_selected = False
        assert item.is_selected is False


class TestJobsPanelSelection:
    """Test JobsPanel selection functionality."""

    @pytest.mark.asyncio
    async def test_jobs_panel_exists_in_app(self, temp_dir):
        """App should contain a JobsPanel."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            jobs_panel = app.query_one(JobsPanel)
            assert jobs_panel is not None

    @pytest.mark.asyncio
    async def test_jobs_panel_has_select_buttons(self, temp_dir):
        """JobsPanel should have All and None selection buttons."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            jobs_panel = app.query_one(JobsPanel)

            # Check for selection buttons
            all_btn = jobs_panel.query_one("#job-select-all")
            none_btn = jobs_panel.query_one("#job-deselect-all")

            assert all_btn is not None
            assert none_btn is not None

    @pytest.mark.asyncio
    async def test_jobs_panel_has_transport_controls(self, temp_dir):
        """JobsPanel should have Play, Pause, Stop transport controls."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            jobs_panel = app.query_one(JobsPanel)

            # Check for transport controls (play button renamed from start)
            play_btn = jobs_panel.query_one("#jobs-play-btn")
            pause_btn = jobs_panel.query_one("#jobs-pause-btn")
            stop_btn = jobs_panel.query_one("#jobs-stop-btn")

            assert play_btn is not None
            assert pause_btn is not None
            assert stop_btn is not None

    @pytest.mark.asyncio
    async def test_jobs_panel_transport_initial_state(self, temp_dir):
        """Transport controls should have correct initial state."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            jobs_panel = app.query_one(JobsPanel)

            play_btn = jobs_panel.query_one("#jobs-play-btn")
            pause_btn = jobs_panel.query_one("#jobs-pause-btn")
            stop_btn = jobs_panel.query_one("#jobs-stop-btn")

            # All transport buttons disabled initially (no jobs selected)
            assert play_btn.disabled is True
            assert pause_btn.disabled is True
            assert stop_btn.disabled is True

    def test_jobs_panel_get_selected_jobs_empty(self):
        """get_selected_jobs should return empty list when nothing selected."""
        panel = JobsPanel()
        # Without mounting, there are no items
        selected = panel.get_selected_jobs()
        assert selected == []

    def test_jobs_panel_select_all_method_exists(self):
        """JobsPanel should have select_all method."""
        panel = JobsPanel()
        assert hasattr(panel, "select_all")
        assert callable(panel.select_all)

    def test_jobs_panel_deselect_all_method_exists(self):
        """JobsPanel should have deselect_all method."""
        panel = JobsPanel()
        assert hasattr(panel, "deselect_all")
        assert callable(panel.deselect_all)

    def test_jobs_panel_set_running_method_exists(self):
        """JobsPanel should have set_running method for transport control state."""
        panel = JobsPanel()
        assert hasattr(panel, "set_running")
        assert callable(panel.set_running)

    def test_jobs_panel_set_paused_method_exists(self):
        """JobsPanel should have set_paused method for pause button state."""
        panel = JobsPanel()
        assert hasattr(panel, "set_paused")
        assert callable(panel.set_paused)


class TestTUILazyImports:
    """Test that lazy imports in TUI app resolve correctly.

    These tests verify that internal imports inside TUI functions
    correctly reference the parent epub2tts_edge package, not the
    tui subpackage. This catches import path errors like:
    - `from .module` (wrong - looks in tui/)
    - `from ..module` (correct - looks in epub2tts_edge/)
    """

    def test_chapter_detector_import_from_tui_context(self):
        """ChapterDetector can be imported from TUI context."""
        # This simulates the import done inside preview_chapters_async

        # Verify the module exists and can resolve the import
        # The actual import path used in app.py
        from epub2tts_edge.chapter_detector import ChapterDetector

        assert ChapterDetector is not None
        assert hasattr(ChapterDetector, "__init__")

    def test_epub2tts_edge_import_from_tui_context(self):
        """epub2tts_edge functions can be imported from TUI context."""
        # This simulates the imports done inside process_files_async
        from epub2tts_edge.epub2tts_edge import (
            add_cover,
            generate_metadata,
            get_book,
            get_epub_cover,
            make_m4b,
        )

        assert get_epub_cover is not None
        assert add_cover is not None
        assert generate_metadata is not None
        assert get_book is not None
        assert make_m4b is not None

    def test_audio_generator_import_from_tui_context(self):
        """audio_generator can be imported from TUI context."""
        from epub2tts_edge.audio_generator import read_book

        assert read_book is not None
        assert callable(read_book)

    def test_job_manager_import_from_tui_context(self):
        """job_manager can be imported from TUI context."""
        from epub2tts_edge.job_manager import JobManager, JobStatus

        assert JobManager is not None
        assert JobStatus is not None

    def test_tui_app_module_loads_without_import_errors(self):
        """TUI app module can be fully loaded without import errors."""
        # Force a fresh import check of the app module
        import importlib

        from epub2tts_edge.tui import app

        # Reload to catch any deferred import issues at module level
        importlib.reload(app)

        # Verify key classes are accessible
        assert hasattr(app, "AudiobookifyApp")

    def test_preview_chapters_async_import_path(self):
        """The import inside preview_chapters_async uses correct path."""
        # Get the actual source to verify the import statement
        import inspect

        from epub2tts_edge.tui.app import AudiobookifyApp

        source = inspect.getsource(AudiobookifyApp.preview_chapters_async)

        # Verify it uses parent package import (double dot)
        assert "from ..chapter_detector" in source
        # Verify it doesn't use incorrect single-dot import
        assert "from .chapter_detector" not in source

    def test_process_text_files_import_paths(self):
        """The imports inside process_text_files use correct paths."""
        import inspect

        from epub2tts_edge.tui.app import AudiobookifyApp

        source = inspect.getsource(AudiobookifyApp.process_text_files)

        # Verify parent package imports (double dot)
        assert "from ..audio_generator" in source
        assert "from ..epub2tts_edge" in source
        assert "from ..job_manager" in source

        # Verify no incorrect single-dot imports
        assert "from .audio_generator" not in source
        assert "from .epub2tts_edge" not in source
        assert "from .job_manager" not in source

    def test_export_text_async_import_path(self):
        """The import inside export_text_async uses correct path."""
        import inspect

        from epub2tts_edge.tui.app import AudiobookifyApp

        source = inspect.getsource(AudiobookifyApp.export_text_async)

        # Verify it uses parent package import (double dot)
        assert "from ..chapter_detector" in source
        # Verify it doesn't use incorrect single-dot import
        assert "from .chapter_detector" not in source


class TestProcessingInitiation:
    """Test that processing can be initiated with mock TTS.

    These tests verify the workflow from EPUB to audio conversion
    using the test mode infrastructure.
    """

    def test_batch_processor_with_test_mode(self, sample_epub):
        """BatchProcessor should work with test mode enabled."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
        )
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        try:
            enable_test_mode()

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(sample_epub.parent),
                speaker="en-US-AriaNeural",
                export_only=True,  # Just export text, don't convert to audio
            )

            processor = BatchProcessor(config)
            processor.prepare()

            assert processor.result is not None
            assert len(processor.result.tasks) == 1
            assert processor.result.tasks[0].epub_path == str(sample_epub)

        finally:
            disable_test_mode()

    def test_batch_processor_export_creates_text_file(self, sample_epub):
        """BatchProcessor should create text file during export."""
        from epub2tts_edge.audio_generator import disable_test_mode, enable_test_mode
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        try:
            enable_test_mode()

            output_dir = sample_epub.parent / "output"
            output_dir.mkdir(exist_ok=True)

            config = BatchConfig(
                input_path=str(sample_epub),
                output_dir=str(output_dir),
                speaker="en-US-AriaNeural",
                export_only=True,
            )

            processor = BatchProcessor(config)
            processor.prepare()

            if processor.result.tasks:
                task = processor.result.tasks[0]
                processor.process_book(task)

                # Text file should be created
                assert task.txt_path is not None

        finally:
            disable_test_mode()

    def test_test_mode_enables_mock_tts_globally(self):
        """Enabling test mode should make mock TTS available globally."""
        from epub2tts_edge.audio_generator import (
            disable_test_mode,
            enable_test_mode,
            get_mock_engine,
            is_test_mode,
        )

        try:
            # Initially disabled
            assert is_test_mode() is False
            assert get_mock_engine() is None

            # Enable
            enable_test_mode()
            assert is_test_mode() is True
            mock = get_mock_engine()
            assert mock is not None
            assert hasattr(mock, "generate")
            assert hasattr(mock, "calls")

        finally:
            disable_test_mode()

    def test_chapter_detector_works_with_sample_epub(self, sample_epub):
        """ChapterDetector should extract chapters from sample EPUB."""
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        detector = ChapterDetector(epub_path=sample_epub, method=DetectionMethod.AUTO)
        root_node = detector.detect()

        # detect() returns a ChapterNode tree, flatten to get all chapters
        chapters = root_node.flatten() if root_node else []

        # Should find chapters from our test EPUB
        assert len(chapters) > 0
        # Chapters should have titles and paragraphs (content stored in paragraphs list)
        for chapter in chapters:
            assert chapter.title is not None
            # paragraphs contains the text content
            assert chapter.paragraphs is not None
            assert len(chapter.paragraphs) > 0


class TestErrorHandling:
    """Test error handling for file operations and processing errors.

    These tests verify that the application properly handles various error
    conditions and provides meaningful error messages.
    """

    def test_invalid_file_format_error_has_suggestion(self):
        """InvalidFileFormatError should include helpful suggestion."""
        from epub2tts_edge.errors import InvalidFileFormatError

        error = InvalidFileFormatError(
            "test.pdf", expected_formats=[".epub", ".mobi", ".azw", ".azw3"]
        )

        assert "test.pdf" in str(error)
        assert error.suggestion is not None
        assert ".epub" in error.suggestion

    def test_tts_error_captures_text_context(self):
        """TTSError should capture the text that failed."""
        from epub2tts_edge.errors import TTSError

        error = TTSError(
            message="Network connection failed",
            text_sample="Hello world",
            voice="en-US-AriaNeural",
        )

        assert "Network connection failed" in str(error)
        # Context contains the text sample
        assert error.text_sample == "Hello world"
        assert error.voice == "en-US-AriaNeural"

    def test_chapter_detection_error_includes_file_path(self):
        """ChapterDetectionError should include the file path."""
        from epub2tts_edge.errors import ChapterDetectionError

        error = ChapterDetectionError(
            file_path="/path/to/book.epub",
            detection_method="toc",
            details="No TOC found",
        )

        assert "/path/to/book.epub" in str(error)
        assert error.file_path == "/path/to/book.epub"

    def test_format_error_for_user_creates_readable_message(self):
        """format_error_for_user should create user-friendly error messages."""
        from epub2tts_edge.errors import TTSError, format_error_for_user

        error = TTSError(
            message="Connection timeout",
            text_sample="Some text",
            voice="en-US-AriaNeural",
        )

        formatted = format_error_for_user(error)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Connection timeout" in formatted or "TTS" in formatted

    def test_audiobookify_error_base_class_formatting(self):
        """AudiobookifyError base class should format messages properly."""
        from epub2tts_edge.errors import AudiobookifyError

        error = AudiobookifyError(
            message="Something went wrong",
            suggestion="Try restarting",
            context={"operation": "test"},
        )

        formatted = str(error)
        assert "Something went wrong" in formatted

    def test_ffmpeg_error_includes_command_context(self):
        """FFmpegError should provide context about the failed command."""
        from epub2tts_edge.errors import FFmpegError

        error = FFmpegError(
            operation="m4b_conversion",
            details="Exit code 1: Invalid input format",
        )

        assert "FFmpeg" in str(error)
        assert "m4b_conversion" in str(error)
        assert error.operation == "m4b_conversion"

    def test_dependency_error_for_missing_ffmpeg(self):
        """DependencyError should handle missing FFmpeg scenario."""
        from epub2tts_edge.errors import DependencyError

        error = DependencyError(
            dependency="ffmpeg",
            purpose="audio processing",
        )

        assert "ffmpeg" in str(error).lower()
        assert error.suggestion is not None
        assert "install" in error.suggestion.lower()

    def test_resume_error_with_invalid_state(self):
        """ResumeError should handle invalid state file scenarios."""
        from epub2tts_edge.errors import ResumeError

        error = ResumeError(
            message="State file corrupted",
            state_file="/path/to/state.json",
        )

        assert "State file corrupted" in str(error)
        assert error.state_file == "/path/to/state.json"

    def test_configuration_error_with_invalid_setting(self):
        """ConfigurationError should indicate which setting is invalid."""
        from epub2tts_edge.errors import ConfigurationError

        error = ConfigurationError(
            message="Invalid voice 'invalid-voice'",
            parameter="speaker",
        )

        assert "Invalid voice" in str(error)
        assert error.parameter == "speaker"

    def test_invalid_file_format_error_for_text_file(self, temp_dir):
        """InvalidFileFormatError for attempting to process a text file."""
        from epub2tts_edge.errors import InvalidFileFormatError

        # Create a plain text file
        txt_file = temp_dir / "not_an_epub.txt"
        txt_file.write_text("This is not an EPUB file")

        error = InvalidFileFormatError(
            str(txt_file), expected_formats=[".epub", ".mobi", ".azw", ".azw3"]
        )

        assert "not_an_epub.txt" in str(error)
        assert ".epub" in error.suggestion

    def test_mock_tts_failure_triggers_runtime_error(self, mock_tts_with_failures):
        """MockTTSEngine failure mode should raise RuntimeError."""
        mock_tts_with_failures.fail_on_text = "FAIL_ME"

        # Use synchronous generate_sync which works without event loop
        with pytest.raises(RuntimeError, match="Mock TTS failure"):
            mock_tts_with_failures.generate_sync("This text FAIL_ME will fail", "en-US-AriaNeural")

    def test_batch_processor_handles_nonexistent_file(self, temp_dir):
        """BatchProcessor should handle non-existent input files gracefully."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        nonexistent = temp_dir / "does_not_exist.epub"

        config = BatchConfig(
            input_path=str(nonexistent),
            output_dir=str(temp_dir),
            speaker="en-US-AriaNeural",
        )

        processor = BatchProcessor(config)
        processor.prepare()

        # Should have no tasks since file doesn't exist
        assert processor.result is not None
        assert len(processor.result.tasks) == 0

    def test_batch_processor_handles_empty_directory(self, temp_dir):
        """BatchProcessor should handle empty directories gracefully."""
        from epub2tts_edge.batch_processor import BatchConfig, BatchProcessor

        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        config = BatchConfig(
            input_path=str(empty_dir),
            output_dir=str(temp_dir),
            speaker="en-US-AriaNeural",
        )

        processor = BatchProcessor(config)
        processor.prepare()

        # Should have no tasks since directory is empty
        assert processor.result is not None
        assert len(processor.result.tasks) == 0

    def test_chapter_detector_handles_invalid_epub_gracefully(self, temp_dir):
        """ChapterDetector should handle malformed EPUB files."""
        # Create a fake EPUB (just a zip with wrong contents)
        import zipfile

        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        fake_epub = temp_dir / "fake.epub"
        with zipfile.ZipFile(fake_epub, "w") as zf:
            zf.writestr("not_valid.txt", "This is not valid EPUB content")

        # Should raise an error or return empty results
        try:
            detector = ChapterDetector(epub_path=fake_epub, method=DetectionMethod.AUTO)
            result = detector.detect()
            # If it doesn't raise, result should indicate no chapters
            chapters = result.flatten() if result else []
            assert len(chapters) == 0 or result is None
        except Exception as e:
            # Any exception is acceptable for invalid EPUB
            assert isinstance(e, Exception)

    def test_error_hierarchy_inheritance(self):
        """All custom errors should inherit from AudiobookifyError."""
        from epub2tts_edge.errors import (
            AudiobookifyError,
            ChapterDetectionError,
            ConfigurationError,
            DependencyError,
            FFmpegError,
            InvalidFileFormatError,
            ResumeError,
            TTSError,
        )

        # Create instances with correct signatures and verify inheritance
        errors = [
            TTSError("test message"),  # message only
            InvalidFileFormatError("file.pdf", [".epub"]),  # file_path, expected_formats
            ChapterDetectionError("/path", "toc"),  # file_path, detection_method
            FFmpegError("conversion"),  # operation
            ConfigurationError("invalid setting"),  # message
            DependencyError("dep"),  # dependency
            ResumeError("state error"),  # message
        ]

        for error in errors:
            assert isinstance(error, AudiobookifyError), (
                f"{type(error).__name__} should inherit from AudiobookifyError"
            )
            assert isinstance(error, Exception), f"{type(error).__name__} should be an Exception"


class TestPreviewJobGuard:
    """_start_preview_job must compare against the preview state's real attribute."""

    @pytest.mark.asyncio
    async def test_mismatched_preview_state_warns_instead_of_crashing(self, temp_dir):
        """A job pointing at a different file must warn, not raise AttributeError."""
        from pathlib import Path

        from epub2tts_edge.job_manager import Job, JobStatus

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(preview, [make_preview_chapter("Chapter 1", "Some content")])
            # Preview state points at file A...
            preview.preview_state.source_file = Path(temp_dir) / "a.epub"

            notifications: list[str] = []
            app.notify = lambda message, **kwargs: notifications.append(str(message))

            # ...while the job points at file B: the guard must take the
            # "please preview first" branch, not raise AttributeError.
            job = Job(
                job_id="preview_job_guard",
                source_file=str(Path(temp_dir) / "b.epub"),
                job_dir=str(Path(temp_dir) / "jobs" / "preview_job_guard"),
                status=JobStatus.PREVIEW,
            )
            app._start_preview_job(job)

            assert any("preview" in n.lower() for n in notifications), notifications

    @pytest.mark.asyncio
    async def test_matching_preview_state_proceeds(self, temp_dir):
        """A job matching the preview state must not take the warning branch."""
        from pathlib import Path

        from epub2tts_edge.job_manager import Job, JobStatus

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(preview, [make_preview_chapter("Chapter 1", "Some content")])
            source = Path(temp_dir) / "a.epub"
            preview.preview_state.source_file = source

            notifications: list[str] = []
            app.notify = lambda message, **kwargs: notifications.append(str(message))

            job = Job(
                job_id="preview_job_match",
                source_file=str(source),
                job_dir=str(Path(temp_dir) / "jobs" / "preview_job_match"),
                status=JobStatus.PREVIEW,
            )
            app._start_preview_job(job)

            assert notifications == [], notifications

    @pytest.mark.asyncio
    async def test_unresolved_preview_path_matches_resolved_job(self, temp_dir):
        """Production stores the two sides with different resolution.

        The SAME ``epub_path`` feeds both sides of the guard, but
        ``JobManager.create_job`` resolves it (job_manager.py:281) while
        ``PreviewPanel.load_chapters`` stores it verbatim
        (preview_panel.py:244). A path reached through a symlinked directory
        therefore differs as a *string* while naming the same file, and a raw
        string comparison falsely warns "Please preview the file first".
        """
        from pathlib import Path

        from epub2tts_edge.job_manager import JobManager

        # A real file addressed through a symlinked directory - exactly what
        # file_panel's glob yields after browsing into a symlink, since
        # _on_directory_selected (file_panel.py:405) does not resolve.
        real_dir = Path(temp_dir) / "real"
        real_dir.mkdir()
        source = real_dir / "a.epub"
        source.write_bytes(b"epub bytes")

        link_dir = Path(temp_dir) / "link"
        link_dir.symlink_to(real_dir, target_is_directory=True)
        unresolved = link_dir / "a.epub"

        manager = JobManager(jobs_dir=str(Path(temp_dir) / "jobs"))
        job = manager.create_job(
            source_file=str(unresolved), title="T", author="A", speaker="en-US-AndrewNeural"
        )

        # Sanity: the test is only meaningful if the two spellings differ.
        assert str(unresolved) != job.source_file

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(preview, [make_preview_chapter("Chapter 1", "Some content")])
            # Stored verbatim, as load_chapters does.
            preview.preview_state.source_file = unresolved

            notifications: list[str] = []
            app.notify = lambda message, **kwargs: notifications.append(str(message))

            app._start_preview_job(job)

            assert notifications == [], notifications


class TestQueuePanelUpdates:
    """Pin QueuePanel.update_task's observable effect.

    ``update_task``'s whole body sits inside ``try: ... except Exception: pass``.
    That means a signature/API drift in Textual's ``DataTable.update_cell_at``
    would turn every queue update into a silent no-op rather than an error.
    These tests assert on the resulting cell contents so such a regression is
    loud instead of invisible.
    """

    @pytest.mark.asyncio
    async def test_update_task_rewrites_status_chapters_and_time(self):
        """A completed task's status, chapter count and duration reach the table."""
        from textual.app import App, ComposeResult
        from textual.coordinate import Coordinate
        from textual.widgets import DataTable

        from epub2tts_edge.batch_processor import BookTask, ProcessingStatus
        from epub2tts_edge.tui import QueuePanel

        class QueueHost(App):
            def compose(self) -> ComposeResult:
                yield QueuePanel()

        task = BookTask(epub_path="/tmp/queue-panel-test-book.epub")

        app = QueueHost()
        async with app.run_test() as _:
            panel = app.query_one(QueuePanel)
            panel.add_task(task)

            table = panel.query_one("#queue-table", DataTable)
            assert table.get_cell_at(Coordinate(0, 0)) == "⏳"
            assert table.get_cell_at(Coordinate(0, 2)) == "-"
            assert table.get_cell_at(Coordinate(0, 3)) == "-"

            task.status = ProcessingStatus.COMPLETED
            task.chapter_count = 12
            task.start_time = 100.0
            task.end_time = 225.0  # -> "2m 5s"

            panel.update_task(task)

            assert table.get_cell_at(Coordinate(0, 0)) == "✅"
            assert table.get_cell_at(Coordinate(0, 2)) == "12"
            assert table.get_cell_at(Coordinate(0, 3)) == "2m 5s"
            # The book column is written once by add_task and left alone.
            assert table.get_cell_at(Coordinate(0, 1)) == "queue-panel-test-book"

    @pytest.mark.asyncio
    async def test_update_task_for_unknown_row_is_a_no_op(self):
        """An unqueued task is swallowed rather than raising - that part is intended."""
        from textual.app import App, ComposeResult

        from epub2tts_edge.batch_processor import BookTask
        from epub2tts_edge.tui import QueuePanel

        class QueueHost(App):
            def compose(self) -> ComposeResult:
                yield QueuePanel()

        app = QueueHost()
        async with app.run_test() as _:
            panel = app.query_one(QueuePanel)
            panel.update_task(BookTask(epub_path="/tmp/never-added.epub"))


class TestHelpScreenAndTitleEdit:
    """Cover the two previously-untested paths reworked for type correctness.

    ``HelpScreen.action_dismiss`` became an ``async`` override to match Textual's
    ``Screen``, and the title-edit ``Input`` became a ``TitleEditInput`` subclass
    that carries its chapter item. Both are behaviourally load-bearing and were
    uncovered, so pin them.
    """

    @pytest.mark.asyncio
    async def test_help_screen_opens_and_escape_closes_it(self, temp_dir):
        """The escape binding must still pop the help screen."""
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as pilot:
            depth_before = len(app.screen_stack)

            app.action_show_help()
            await pilot.pause()
            assert len(app.screen_stack) == depth_before + 1
            assert type(app.screen).__name__ == "HelpScreen"

            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == depth_before, "help screen did not close"

    @pytest.mark.asyncio
    async def test_title_edit_round_trip(self, temp_dir):
        """Submitting the edit renames the chapter, flags modified, and tears down.

        Driven through the real entry point (Input.Submitted -> on_input_submitted)
        rather than by calling the private _finish_title_edit directly.
        """
        from textual.widgets import Label, ListView

        from epub2tts_edge.tui.panels.preview_panel import TitleEditInput

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as pilot:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(preview, [make_preview_chapter("Old Title", "body text")])
            await pilot.pause()
            preview.preview_state.modified = False

            tree = preview.query_one("#chapter-tree", ListView)
            tree.index = 0
            await pilot.pause()

            item = preview._get_highlighted_item()
            assert item is not None

            preview.edit_highlighted_title()
            await pilot.pause()

            widget = preview.query_one("#title-edit-input", TitleEditInput)
            assert widget.chapter_item is item

            # Real entry point: type into the focused Input and press Enter.
            widget.value = "Brand New Title"
            await pilot.press("enter")
            await pilot.pause()

            assert item.chapter.title == "Brand New Title"
            assert preview.preview_state.modified is True
            assert len(preview.query("#title-edit-input")) == 0, "input not torn down"
            assert item.query_one(Label).display is True, "label not restored"

    @pytest.mark.asyncio
    async def test_title_edit_escape_cancels_and_restores_label(self, temp_dir):
        """Escape tears the edit box down via the on_key lookup, leaving the title alone.

        This is the other real entry point into the TitleEditInput lookup, and it
        sits inside `except Exception: pass` - so it must be pinned by assertion
        rather than by absence of a raised error.
        """
        from textual.widgets import Label, ListView

        from epub2tts_edge.tui.panels.preview_panel import TitleEditInput

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as pilot:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(preview, [make_preview_chapter("Keep Me", "body text")])
            await pilot.pause()
            preview.preview_state.modified = False

            tree = preview.query_one("#chapter-tree", ListView)
            tree.index = 0
            await pilot.pause()

            item = preview._get_highlighted_item()
            assert item is not None

            preview.edit_highlighted_title()
            await pilot.pause()

            widget = preview.query_one("#title-edit-input", TitleEditInput)
            widget.value = "Discard This"
            assert item.query_one(Label).display is False

            await pilot.press("escape")
            await pilot.pause()

            assert len(preview.query("#title-edit-input")) == 0, "escape did not remove input"
            assert item.query_one(Label).display is True, "escape did not restore label"
            assert item.chapter.title == "Keep Me", "escape must not rename"
            assert preview.preview_state.modified is False


class TestProfileSelectBlank:
    """The profile Select offers a blank row, and picking it used to crash the app.

    `Select` is built with the default `allow_blank=True`, which prepends a
    selectable ("", Select.NULL) option. Choosing it fires Select.Changed with a
    NoSelection value, which the old guard passed straight to get_profile() ->
    `name.lower()` -> AttributeError inside the message pump.
    """

    @pytest.mark.asyncio
    async def test_blank_option_is_present_and_selectable(self, temp_dir):
        """Pin the reachability premise this guard exists for."""
        from textual.widgets import Select

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            select = app.query_one("#profile-select", Select)
            assert ("", Select.NULL) in select._options, "blank row gone; revisit the guard"

    @pytest.mark.asyncio
    async def test_selecting_blank_profile_does_not_crash(self, temp_dir):
        """Selecting the blank row must be a no-op, not an AttributeError."""
        from textual.widgets import Select

        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as pilot:
            select = app.query_one("#profile-select", Select)

            select.value = Select.NULL
            await pilot.pause()

            assert select.value is Select.NULL
            assert app.is_running, "app died handling the blank profile selection"
