"""Tests for preview export functionality."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from epub2tts_edge.tui import ChapterPreviewState, PreviewChapter


class TestChapterPreviewStateExport(unittest.TestCase):
    """Tests for ChapterPreviewState.export_to_text method."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_path = Path(self.temp_dir) / "test_output.txt"

    def tearDown(self):
        """Clean up temp files."""
        if self.output_path.exists():
            self.output_path.unlink()
        os.rmdir(self.temp_dir)

    def test_export_basic_chapters(self):
        """Test exporting basic chapters to text file."""
        chapters = [
            PreviewChapter(
                title="Chapter 1",
                level=1,
                word_count=10,
                paragraph_count=2,
                content_preview="Test content...",
                original_content="Paragraph one.\n\nParagraph two.",
            ),
            PreviewChapter(
                title="Chapter 2",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="More content...",
                original_content="Another paragraph.",
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="Test Book",
            book_author="Test Author",
        )

        state.export_to_text(self.output_path)

        self.assertTrue(self.output_path.exists())
        content = self.output_path.read_text()

        # Check metadata header
        self.assertIn("Title: Test Book", content)
        self.assertIn("Author: Test Author", content)

        # Check title chapter
        self.assertIn("# Title", content)
        self.assertIn("Test Book, by Test Author", content)

        # Check chapters
        self.assertIn("# Chapter 1", content)
        self.assertIn("Paragraph one.", content)
        self.assertIn("Paragraph two.", content)
        self.assertIn("# Chapter 2", content)
        self.assertIn("Another paragraph.", content)

    def test_export_excludes_non_included_chapters(self):
        """Test that excluded chapters are not exported."""
        chapters = [
            PreviewChapter(
                title="Chapter 1",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="Included",
                original_content="This is included.",
            ),
            PreviewChapter(
                title="Chapter 2",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="Excluded",
                original_content="This is excluded.",
                included=False,  # Excluded!
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="Test",
            book_author="Author",
        )

        state.export_to_text(self.output_path)
        content = self.output_path.read_text()

        self.assertIn("Chapter 1", content)
        self.assertIn("This is included.", content)
        self.assertNotIn("Chapter 2", content)
        self.assertNotIn("This is excluded.", content)

    def test_export_excludes_merged_chapters(self):
        """Test that merged chapters are not exported separately."""
        chapters = [
            PreviewChapter(
                title="Chapter 1 (+ 1 merged)",
                level=1,
                word_count=15,
                paragraph_count=2,
                content_preview="Combined",
                original_content="Content from chapter 1.\n\nContent from chapter 2.",
            ),
            PreviewChapter(
                title="Chapter 2",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="Merged away",
                original_content="Content from chapter 2.",
                included=False,
                merged_into=0,  # Merged into chapter 0
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="Test",
            book_author="Author",
        )

        state.export_to_text(self.output_path)
        content = self.output_path.read_text()

        # Only merged chapter title appears
        self.assertIn("Chapter 1 (+ 1 merged)", content)
        # Combined content appears
        self.assertIn("Content from chapter 1.", content)
        self.assertIn("Content from chapter 2.", content)
        # But not as a separate chapter
        lines = content.split("\n")
        chapter_2_as_header = [line for line in lines if line.strip() == "# Chapter 2"]
        self.assertEqual(len(chapter_2_as_header), 0)

    def test_export_with_multi_level_chapters(self):
        """Test exporting chapters with different hierarchy levels."""
        chapters = [
            PreviewChapter(
                title="Part 1",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="Part intro",
                original_content="Introduction to part 1.",
            ),
            PreviewChapter(
                title="Chapter 1",
                level=2,
                word_count=10,
                paragraph_count=1,
                content_preview="Chapter content",
                original_content="Chapter 1 content.",
            ),
            PreviewChapter(
                title="Section 1.1",
                level=3,
                word_count=8,
                paragraph_count=1,
                content_preview="Section content",
                original_content="Section content here.",
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="Test",
            book_author="Author",
        )

        state.export_to_text(self.output_path)
        content = self.output_path.read_text()

        # Check different header levels
        self.assertIn("# Part 1", content)
        self.assertIn("## Chapter 1", content)
        self.assertIn("### Section 1.1", content)

    def test_export_uses_filename_when_no_title(self):
        """Test that filename is used when book_title is empty."""
        chapters = [
            PreviewChapter(
                title="Chapter 1",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="Test",
                original_content="Test content.",
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/my_book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="",  # Empty title
            book_author="",  # Empty author
        )

        state.export_to_text(self.output_path)
        content = self.output_path.read_text()

        # Should use filename stem
        self.assertIn("Title: my_book", content)
        self.assertIn("Author: Unknown", content)

    def test_export_normalizes_whitespace(self):
        """Test that exported content has normalized whitespace."""
        chapters = [
            PreviewChapter(
                title="Chapter 1",
                level=1,
                word_count=5,
                paragraph_count=1,
                content_preview="Test",
                original_content="Text  with   multiple\n\nspaces  and\nnewlines.",
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
            book_title="Test",
            book_author="Author",
        )

        state.export_to_text(self.output_path)
        content = self.output_path.read_text()

        # Multiple spaces should be normalized
        self.assertIn("Text with multiple", content)
        self.assertIn("spaces and newlines.", content)


class TestGetIncludedChapters(unittest.TestCase):
    """Tests for ChapterPreviewState.get_included_chapters method."""

    def test_all_included(self):
        """Test when all chapters are included."""
        chapters = [
            PreviewChapter(
                title="Ch1",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
            ),
            PreviewChapter(
                title="Ch2",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
        )

        included = state.get_included_chapters()
        self.assertEqual(len(included), 2)

    def test_some_excluded(self):
        """Test when some chapters are excluded."""
        chapters = [
            PreviewChapter(
                title="Ch1",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
            ),
            PreviewChapter(
                title="Ch2",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
                included=False,
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
        )

        included = state.get_included_chapters()
        self.assertEqual(len(included), 1)
        self.assertEqual(included[0].title, "Ch1")

    def test_merged_chapters_excluded(self):
        """Test that merged chapters are not included."""
        chapters = [
            PreviewChapter(
                title="Ch1",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
            ),
            PreviewChapter(
                title="Ch2",
                level=1,
                word_count=10,
                paragraph_count=1,
                content_preview="",
                original_content="",
                included=False,
                merged_into=0,
            ),
        ]
        state = ChapterPreviewState(
            source_file=Path("/fake/book.epub"),
            detection_method="combined",
            chapters=chapters,
        )

        included = state.get_included_chapters()
        self.assertEqual(len(included), 1)
        self.assertEqual(included[0].title, "Ch1")


if __name__ == "__main__":
    unittest.main()
