"""Tests for multi-file preview state management."""

from pathlib import Path

import pytest

from epub2tts_edge.tui.models import MultiPreviewState, PreviewChapter


@pytest.fixture
def sample_chapters():
    """Create sample chapters for testing."""
    return [
        PreviewChapter(
            title="Chapter 1",
            level=1,
            word_count=1000,
            paragraph_count=10,
            content_preview="This is chapter 1...",
            original_content="Full content of chapter 1",
        ),
        PreviewChapter(
            title="Chapter 2",
            level=1,
            word_count=1500,
            paragraph_count=15,
            content_preview="This is chapter 2...",
            original_content="Full content of chapter 2",
        ),
    ]


class TestMultiPreviewStateBasic:
    """Basic tests for MultiPreviewState."""

    def test_init_empty(self):
        """New state starts empty."""
        state = MultiPreviewState()
        assert state.is_empty
        assert state.file_count == 0
        assert state.active_file is None
        assert state.active_state is None

    def test_default_max_tabs(self):
        """Default max tabs is 8."""
        state = MultiPreviewState()
        assert state.max_tabs == 8

    def test_custom_max_tabs(self):
        """Can set custom max tabs."""
        state = MultiPreviewState(max_tabs=5)
        assert state.max_tabs == 5


class TestMultiPreviewStateAddPreview:
    """Tests for adding previews."""

    def test_add_first_preview(self, sample_chapters):
        """Adding first preview sets it as active."""
        state = MultiPreviewState()
        file_path = Path("/books/book1.epub")

        result = state.add_preview(
            source_file=file_path,
            chapters=sample_chapters,
            detection_method="combined",
            book_title="Book One",
            book_author="Author One",
        )

        assert result is True
        assert state.file_count == 1
        assert state.active_file == file_path
        assert state.active_state is not None
        assert state.active_state.book_title == "Book One"

    def test_add_multiple_previews(self, sample_chapters):
        """Can add multiple previews."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "toc")

        assert state.file_count == 2
        # Second added becomes active
        assert state.active_file == file2

    def test_add_preview_at_max_fails(self, sample_chapters):
        """Cannot add preview when at max tabs."""
        state = MultiPreviewState(max_tabs=2)
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")
        file3 = Path("/books/book3.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")
        result = state.add_preview(file3, sample_chapters, "combined")

        assert result is False
        assert state.file_count == 2
        assert not state.has_file(file3)

    def test_add_existing_file_updates(self, sample_chapters):
        """Adding existing file updates it."""
        state = MultiPreviewState()
        file_path = Path("/books/book1.epub")

        state.add_preview(file_path, sample_chapters, "combined", book_title="Original")

        # Update with new title
        new_chapters = [
            PreviewChapter(
                title="New Chapter",
                level=1,
                word_count=500,
                paragraph_count=5,
                content_preview="New...",
                original_content="New content",
            )
        ]
        result = state.add_preview(file_path, new_chapters, "toc", book_title="Updated")

        assert result is True
        assert state.file_count == 1
        assert state.active_state.book_title == "Updated"
        assert len(state.active_state.chapters) == 1

    def test_get_open_files(self, sample_chapters):
        """get_open_files returns paths in order."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")
        file3 = Path("/books/book3.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")
        state.add_preview(file3, sample_chapters, "combined")

        files = state.get_open_files()
        assert files == [file1, file2, file3]


class TestMultiPreviewStateSwitching:
    """Tests for switching between previews."""

    def test_switch_to_existing(self, sample_chapters):
        """Can switch to an existing file."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined", book_title="Book 1")
        state.add_preview(file2, sample_chapters, "combined", book_title="Book 2")

        assert state.active_file == file2

        result = state.switch_to(file1)

        assert result is True
        assert state.active_file == file1
        assert state.active_state.book_title == "Book 1"

    def test_switch_to_nonexistent(self, sample_chapters):
        """Switching to nonexistent file returns False."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")

        result = state.switch_to(file2)

        assert result is False
        assert state.active_file == file1

    def test_has_file(self, sample_chapters):
        """has_file correctly identifies open files."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")

        assert state.has_file(file1) is True
        assert state.has_file(file2) is False


class TestMultiPreviewStateCloseTab:
    """Tests for closing preview tabs."""

    def test_close_single_tab(self, sample_chapters):
        """Closing single tab makes state empty."""
        state = MultiPreviewState()
        file_path = Path("/books/book1.epub")

        state.add_preview(file_path, sample_chapters, "combined")
        result = state.close_tab(file_path)

        assert result is None
        assert state.is_empty
        assert state.active_file is None

    def test_close_active_tab_switches_adjacent(self, sample_chapters):
        """Closing active tab switches to adjacent tab (same position or left)."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")
        file3 = Path("/books/book3.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")
        state.add_preview(file3, sample_chapters, "combined")
        state.switch_to(file2)  # Make middle tab active

        result = state.close_tab(file2)

        # After closing middle, switches to same index position (now file3)
        assert result == file3
        assert state.active_file == file3
        assert state.file_count == 2

    def test_close_first_tab_switches_right(self, sample_chapters):
        """Closing first tab switches to right neighbor."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")
        state.switch_to(file1)  # Make first tab active

        result = state.close_tab(file1)

        assert result == file2
        assert state.active_file == file2

    def test_close_inactive_tab(self, sample_chapters):
        """Closing inactive tab doesn't change active."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")

        # file2 is active, close file1
        result = state.close_tab(file1)

        assert result == file2
        assert state.active_file == file2
        assert state.file_count == 1

    def test_close_nonexistent_tab(self, sample_chapters):
        """Closing nonexistent tab returns current active."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")

        result = state.close_tab(file2)

        assert result == file1
        assert state.file_count == 1


class TestMultiPreviewStateCloseAll:
    """Tests for close_all and close_others."""

    def test_close_all(self, sample_chapters):
        """close_all removes all tabs."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")

        state.close_all()

        assert state.is_empty
        assert state.active_file is None

    def test_close_others(self, sample_chapters):
        """close_others keeps only specified file."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")
        file3 = Path("/books/book3.epub")

        state.add_preview(file1, sample_chapters, "combined")
        state.add_preview(file2, sample_chapters, "combined")
        state.add_preview(file3, sample_chapters, "combined")

        state.close_others(file2)

        assert state.file_count == 1
        assert state.active_file == file2
        assert state.has_file(file2)
        assert not state.has_file(file1)
        assert not state.has_file(file3)

    def test_close_others_nonexistent(self, sample_chapters):
        """close_others with nonexistent file does nothing."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined")

        state.close_others(file2)

        # Nothing changed
        assert state.file_count == 1
        assert state.has_file(file1)


class TestMultiPreviewStateHelpers:
    """Tests for helper methods."""

    def test_get_tab_label_short(self, sample_chapters):
        """Short filenames are returned as-is."""
        state = MultiPreviewState()
        file_path = Path("/books/ShortName.epub")

        state.add_preview(file_path, sample_chapters, "combined")

        label = state.get_tab_label(file_path)
        assert label == "ShortName"

    def test_get_tab_label_long_truncated(self, sample_chapters):
        """Long filenames are truncated."""
        state = MultiPreviewState()
        file_path = Path("/books/ThisIsAVeryLongBookNameThatShouldBeTruncated.epub")

        state.add_preview(file_path, sample_chapters, "combined")

        label = state.get_tab_label(file_path, max_length=20)
        assert len(label) == 20
        assert label.endswith("...")

    def test_is_modified_false(self, sample_chapters):
        """New preview is not modified."""
        state = MultiPreviewState()
        file_path = Path("/books/book1.epub")

        state.add_preview(file_path, sample_chapters, "combined")

        assert state.is_modified(file_path) is False

    def test_is_modified_after_change(self, sample_chapters):
        """Modified flag is tracked."""
        state = MultiPreviewState()
        file_path = Path("/books/book1.epub")

        state.add_preview(file_path, sample_chapters, "combined")
        # Mark as modified
        state.active_state.modified = True

        assert state.is_modified(file_path) is True

    def test_get_state_returns_correct_state(self, sample_chapters):
        """get_state returns correct state for each file."""
        state = MultiPreviewState()
        file1 = Path("/books/book1.epub")
        file2 = Path("/books/book2.epub")

        state.add_preview(file1, sample_chapters, "combined", book_title="Book 1")
        state.add_preview(file2, sample_chapters, "toc", book_title="Book 2")

        state1 = state.get_state(file1)
        state2 = state.get_state(file2)

        assert state1 is not None
        assert state2 is not None
        assert state1.book_title == "Book 1"
        assert state2.book_title == "Book 2"
        assert state1.detection_method == "combined"
        assert state2.detection_method == "toc"

    def test_get_state_nonexistent(self):
        """get_state returns None for nonexistent file."""
        state = MultiPreviewState()
        result = state.get_state(Path("/nonexistent.epub"))
        assert result is None
