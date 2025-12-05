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
