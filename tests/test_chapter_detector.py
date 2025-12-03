"""
Tests for the enhanced chapter detection module.
"""

import importlib.util
import os
import sys

import pytest

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import directly from the module file to avoid __init__.py dependency issues

spec = importlib.util.spec_from_file_location(
    "chapter_detector", os.path.join(parent_dir, "epub2tts_edge", "chapter_detector.py")
)
chapter_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chapter_detector)

ChapterNode = chapter_detector.ChapterNode
HeadingDetector = chapter_detector.HeadingDetector
DetectionMethod = chapter_detector.DetectionMethod
HierarchyStyle = chapter_detector.HierarchyStyle


class TestChapterNode:
    """Tests for ChapterNode class."""

    def test_create_chapter_node(self):
        """Test basic chapter node creation."""
        node = ChapterNode(title="Chapter 1", level=1)
        assert node.title == "Chapter 1"
        assert node.level == 1
        assert node.children == []
        assert node.parent is None

    def test_add_child(self):
        """Test adding children to a node."""
        root = ChapterNode(title="Root", level=0)
        child = ChapterNode(title="Chapter 1")

        root.add_child(child)

        assert len(root.children) == 1
        assert root.children[0] is child
        assert child.parent is root
        assert child.level == 1

    def test_get_path(self):
        """Test getting path from root to node."""
        root = ChapterNode(title="Root", level=0)
        part = ChapterNode(title="Part 1")
        chapter = ChapterNode(title="Chapter 1")

        root.add_child(part)
        part.add_child(chapter)

        path = chapter.get_path()
        assert len(path) == 3
        assert path[0].title == "Root"
        assert path[1].title == "Part 1"
        assert path[2].title == "Chapter 1"

    def test_get_depth(self):
        """Test getting depth of subtree."""
        root = ChapterNode(title="Root", level=0)
        assert root.get_depth() == 0

        part = ChapterNode(title="Part 1")
        root.add_child(part)
        assert root.get_depth() == 1

        chapter = ChapterNode(title="Chapter 1")
        part.add_child(chapter)
        assert root.get_depth() == 2

    def test_flatten(self):
        """Test flattening the hierarchy."""
        root = ChapterNode(title="Root", level=0)
        part1 = ChapterNode(title="Part 1")
        chapter1 = ChapterNode(title="Chapter 1")
        chapter2 = ChapterNode(title="Chapter 2")
        part2 = ChapterNode(title="Part 2")

        root.add_child(part1)
        part1.add_child(chapter1)
        part1.add_child(chapter2)
        root.add_child(part2)

        flat = root.flatten()
        assert len(flat) == 4
        titles = [n.title for n in flat]
        assert titles == ["Part 1", "Chapter 1", "Chapter 2", "Part 2"]

    def test_flatten_with_max_depth(self):
        """Test flattening with max depth limit."""
        root = ChapterNode(title="Root", level=0)
        part = ChapterNode(title="Part 1")
        chapter = ChapterNode(title="Chapter 1")
        section = ChapterNode(title="Section 1")

        root.add_child(part)
        part.add_child(chapter)
        chapter.add_child(section)

        # Max depth 2 should include Part and Chapter but not Section
        flat = root.flatten(max_depth=2)
        titles = [n.title for n in flat]
        assert "Part 1" in titles
        assert "Chapter 1" in titles
        assert "Section 1" not in titles

    def test_format_title_flat(self):
        """Test flat title formatting."""
        root = ChapterNode(title="Root", level=0)
        chapter = ChapterNode(title="Chapter 1")
        root.add_child(chapter)

        assert chapter.format_title(HierarchyStyle.FLAT) == "Chapter 1"

    def test_format_title_numbered(self):
        """Test numbered title formatting."""
        root = ChapterNode(title="Root", level=0)
        part = ChapterNode(title="Part 1")
        chapter = ChapterNode(title="Chapter 1")

        root.add_child(part)
        part.add_child(chapter)

        formatted = chapter.format_title(HierarchyStyle.NUMBERED)
        assert "1.1" in formatted
        assert "Chapter 1" in formatted

    def test_format_title_arrow(self):
        """Test arrow hierarchy formatting."""
        root = ChapterNode(title="Root", level=0)
        part = ChapterNode(title="Part 1")
        chapter = ChapterNode(title="Chapter 1")

        root.add_child(part)
        part.add_child(chapter)

        formatted = chapter.format_title(HierarchyStyle.ARROW)
        assert formatted == "Part 1 > Chapter 1"

    def test_format_title_breadcrumb(self):
        """Test breadcrumb hierarchy formatting."""
        root = ChapterNode(title="Root", level=0)
        part = ChapterNode(title="Part 1")
        chapter = ChapterNode(title="Chapter 1")

        root.add_child(part)
        part.add_child(chapter)

        formatted = chapter.format_title(HierarchyStyle.BREADCRUMB)
        assert formatted == "Part 1 / Chapter 1"

    def test_to_dict(self):
        """Test dictionary serialization."""
        node = ChapterNode(
            title="Chapter 1", level=1, href="chapter1.html", paragraphs=["Para 1", "Para 2"]
        )

        d = node.to_dict()
        assert d["title"] == "Chapter 1"
        assert d["level"] == 1
        assert d["href"] == "chapter1.html"
        assert d["paragraph_count"] == 2


class TestHeadingDetector:
    """Tests for HeadingDetector class."""

    def test_extract_headings(self):
        """Test extracting headings from HTML."""
        detector = HeadingDetector()
        html = """
        <html>
        <body>
            <h1 id="title">Book Title</h1>
            <h2>Chapter 1</h2>
            <p>Some text</p>
            <h2>Chapter 2</h2>
            <h3>Section 2.1</h3>
        </body>
        </html>
        """

        headings = detector.extract_headings(html)

        assert len(headings) == 4
        assert headings[0] == (1, "Book Title", "title")
        assert headings[1] == (2, "Chapter 1", None)
        assert headings[2] == (2, "Chapter 2", None)
        assert headings[3] == (3, "Section 2.1", None)

    def test_extract_sections(self):
        """Test extracting sections with paragraphs."""
        detector = HeadingDetector()
        html = """
        <html>
        <body>
            <h1>Chapter 1</h1>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
            <h2>Section 1.1</h2>
            <p>Section paragraph.</p>
        </body>
        </html>
        """

        sections = detector.extract_sections(html)

        assert len(sections) == 2
        assert sections[0]["title"] == "Chapter 1"
        assert sections[0]["level"] == 1
        assert len(sections[0]["paragraphs"]) == 2
        assert sections[1]["title"] == "Section 1.1"
        assert sections[1]["level"] == 2

    def test_is_chapter_title(self):
        """Test chapter title pattern matching."""
        detector = HeadingDetector()

        # Should match
        assert detector.is_chapter_title("Chapter 1")
        assert detector.is_chapter_title("CHAPTER 10")
        assert detector.is_chapter_title("Chapter IV")
        assert detector.is_chapter_title("Part 1")
        assert detector.is_chapter_title("Part II")
        assert detector.is_chapter_title("Book 1")
        assert detector.is_chapter_title("Prologue")
        assert detector.is_chapter_title("Epilogue")
        assert detector.is_chapter_title("1. Introduction")

        # Should not match
        assert not detector.is_chapter_title("A random title")
        assert not detector.is_chapter_title("The Great Adventure")

    def test_detect_heading_in_text(self):
        """Test detecting heading level in plain text."""
        detector = HeadingDetector()

        # Part/Book level (1)
        assert detector.detect_heading_in_text("Part 1") == 1
        assert detector.detect_heading_in_text("Book III") == 1

        # Chapter level (2)
        assert detector.detect_heading_in_text("Chapter 5") == 2
        assert detector.detect_heading_in_text("1. Introduction") == 2

        # Section level (3)
        assert detector.detect_heading_in_text("Section 2.1") == 3

        # Not a heading
        assert (
            detector.detect_heading_in_text(
                "This is a normal paragraph that is quite long and should not be detected as a heading."
            )
            is None
        )


class TestDetectionMethodEnum:
    """Tests for DetectionMethod enum."""

    def test_enum_values(self):
        """Test enum value conversion."""
        assert DetectionMethod("toc") == DetectionMethod.TOC_ONLY
        assert DetectionMethod("headings") == DetectionMethod.HEADINGS_ONLY
        assert DetectionMethod("combined") == DetectionMethod.COMBINED
        assert DetectionMethod("auto") == DetectionMethod.AUTO


class TestHierarchyStyleEnum:
    """Tests for HierarchyStyle enum."""

    def test_enum_values(self):
        """Test enum value conversion."""
        assert HierarchyStyle("flat") == HierarchyStyle.FLAT
        assert HierarchyStyle("numbered") == HierarchyStyle.NUMBERED
        assert HierarchyStyle("indented") == HierarchyStyle.INDENTED
        assert HierarchyStyle("arrow") == HierarchyStyle.ARROW
        assert HierarchyStyle("breadcrumb") == HierarchyStyle.BREADCRUMB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
