"""Tests for chapter selection functionality."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from epub2tts_edge.chapter_selector import (
    ChapterSelector,
    ChapterRange,
    parse_chapter_selection,
    InvalidSelectionError,
)


class TestChapterRange(unittest.TestCase):
    """Tests for ChapterRange dataclass."""

    def test_single_chapter(self):
        """Test single chapter range."""
        r = ChapterRange(start=3, end=3)
        self.assertTrue(r.contains(3))
        self.assertFalse(r.contains(2))
        self.assertFalse(r.contains(4))

    def test_range(self):
        """Test chapter range."""
        r = ChapterRange(start=2, end=5)
        self.assertFalse(r.contains(1))
        self.assertTrue(r.contains(2))
        self.assertTrue(r.contains(3))
        self.assertTrue(r.contains(5))
        self.assertFalse(r.contains(6))

    def test_open_end_range(self):
        """Test open-ended range (from N to end)."""
        r = ChapterRange(start=5, end=None)
        self.assertFalse(r.contains(4))
        self.assertTrue(r.contains(5))
        self.assertTrue(r.contains(100))

    def test_open_start_range(self):
        """Test open-start range (from 1 to N)."""
        r = ChapterRange(start=None, end=5)
        self.assertTrue(r.contains(1))
        self.assertTrue(r.contains(5))
        self.assertFalse(r.contains(6))


class TestParseChapterSelection(unittest.TestCase):
    """Tests for parsing chapter selection strings."""

    def test_parse_single_chapter(self):
        """Test parsing single chapter number."""
        ranges = parse_chapter_selection("3")
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].start, 3)
        self.assertEqual(ranges[0].end, 3)

    def test_parse_range(self):
        """Test parsing chapter range."""
        ranges = parse_chapter_selection("2-5")
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].start, 2)
        self.assertEqual(ranges[0].end, 5)

    def test_parse_open_end_range(self):
        """Test parsing open-ended range."""
        ranges = parse_chapter_selection("5-")
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].start, 5)
        self.assertIsNone(ranges[0].end)

    def test_parse_open_start_range(self):
        """Test parsing open-start range."""
        ranges = parse_chapter_selection("-5")
        self.assertEqual(len(ranges), 1)
        self.assertIsNone(ranges[0].start)
        self.assertEqual(ranges[0].end, 5)

    def test_parse_multiple_selections(self):
        """Test parsing multiple selections."""
        ranges = parse_chapter_selection("1,3,5-7")
        self.assertEqual(len(ranges), 3)
        # First: single chapter 1
        self.assertEqual(ranges[0].start, 1)
        self.assertEqual(ranges[0].end, 1)
        # Second: single chapter 3
        self.assertEqual(ranges[1].start, 3)
        self.assertEqual(ranges[1].end, 3)
        # Third: range 5-7
        self.assertEqual(ranges[2].start, 5)
        self.assertEqual(ranges[2].end, 7)

    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        ranges = parse_chapter_selection("1, 3, 5 - 7")
        self.assertEqual(len(ranges), 3)

    def test_parse_invalid_empty(self):
        """Test parsing empty string."""
        with self.assertRaises(InvalidSelectionError):
            parse_chapter_selection("")

    def test_parse_invalid_negative(self):
        """Test parsing negative chapter numbers."""
        with self.assertRaises(InvalidSelectionError):
            parse_chapter_selection("-3--1")

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        with self.assertRaises(InvalidSelectionError):
            parse_chapter_selection("abc")

    def test_parse_invalid_range_order(self):
        """Test parsing range with end < start."""
        with self.assertRaises(InvalidSelectionError):
            parse_chapter_selection("5-2")


class TestChapterSelector(unittest.TestCase):
    """Tests for ChapterSelector class."""

    def test_selector_with_single_range(self):
        """Test selector with single range."""
        selector = ChapterSelector("2-5")
        self.assertFalse(selector.is_selected(1))
        self.assertTrue(selector.is_selected(2))
        self.assertTrue(selector.is_selected(3))
        self.assertTrue(selector.is_selected(5))
        self.assertFalse(selector.is_selected(6))

    def test_selector_with_multiple_ranges(self):
        """Test selector with multiple ranges."""
        selector = ChapterSelector("1,3,5-7,10-")
        self.assertTrue(selector.is_selected(1))
        self.assertFalse(selector.is_selected(2))
        self.assertTrue(selector.is_selected(3))
        self.assertFalse(selector.is_selected(4))
        self.assertTrue(selector.is_selected(5))
        self.assertTrue(selector.is_selected(7))
        self.assertFalse(selector.is_selected(9))
        self.assertTrue(selector.is_selected(10))
        self.assertTrue(selector.is_selected(100))

    def test_filter_chapters(self):
        """Test filtering chapter list."""
        chapters = [
            {"title": "Ch1", "paragraphs": ["p1"]},
            {"title": "Ch2", "paragraphs": ["p2"]},
            {"title": "Ch3", "paragraphs": ["p3"]},
            {"title": "Ch4", "paragraphs": ["p4"]},
            {"title": "Ch5", "paragraphs": ["p5"]},
        ]
        selector = ChapterSelector("1,3,5")
        filtered = selector.filter_chapters(chapters)

        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0]["title"], "Ch1")
        self.assertEqual(filtered[1]["title"], "Ch3")
        self.assertEqual(filtered[2]["title"], "Ch5")

    def test_filter_chapters_preserves_order(self):
        """Test that filtering preserves chapter order."""
        chapters = [
            {"title": f"Ch{i}", "paragraphs": [f"p{i}"]}
            for i in range(1, 11)
        ]
        selector = ChapterSelector("5,2,8")
        filtered = selector.filter_chapters(chapters)

        # Should be in original order (2, 5, 8), not selection order
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0]["title"], "Ch2")
        self.assertEqual(filtered[1]["title"], "Ch5")
        self.assertEqual(filtered[2]["title"], "Ch8")

    def test_get_selected_indices(self):
        """Test getting selected indices for a total count."""
        selector = ChapterSelector("1,3,5-7")
        indices = selector.get_selected_indices(10)
        self.assertEqual(indices, [0, 2, 4, 5, 6])  # 0-indexed

    def test_no_selection_selects_all(self):
        """Test that None selection selects all chapters."""
        selector = ChapterSelector(None)
        chapters = [
            {"title": f"Ch{i}", "paragraphs": [f"p{i}"]}
            for i in range(1, 6)
        ]
        filtered = selector.filter_chapters(chapters)
        self.assertEqual(len(filtered), 5)

    def test_selector_summary(self):
        """Test summary generation."""
        selector = ChapterSelector("1,3,5-7")
        summary = selector.get_summary()
        self.assertIn("1", summary)
        self.assertIn("3", summary)
        self.assertIn("5-7", summary)


class TestChapterSelectorEdgeCases(unittest.TestCase):
    """Edge case tests for chapter selector."""

    def test_selection_beyond_total(self):
        """Test selection that includes chapters beyond total."""
        selector = ChapterSelector("1-100")
        chapters = [{"title": f"Ch{i}"} for i in range(1, 6)]
        filtered = selector.filter_chapters(chapters)
        self.assertEqual(len(filtered), 5)  # Only 5 chapters exist

    def test_selection_with_gaps(self):
        """Test selection with gaps in numbering."""
        selector = ChapterSelector("1,5,10")
        chapters = [{"title": f"Ch{i}"} for i in range(1, 8)]
        filtered = selector.filter_chapters(chapters)
        self.assertEqual(len(filtered), 2)  # Only 1 and 5 exist

    def test_empty_result(self):
        """Test selection that results in no chapters."""
        selector = ChapterSelector("100-200")
        chapters = [{"title": f"Ch{i}"} for i in range(1, 6)]
        filtered = selector.filter_chapters(chapters)
        self.assertEqual(len(filtered), 0)


if __name__ == "__main__":
    unittest.main()
