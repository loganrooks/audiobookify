"""
Tests for the content filtering module.
"""

from epub2tts_edge.chapter_detector import ChapterNode
from epub2tts_edge.content_filter import (
    BACK_MATTER_PATTERNS,
    FRONT_MATTER_PATTERNS,
    TRANSLATOR_PATTERNS,
    ChapterType,
    ContentFilter,
    FilterConfig,
    FilterResult,
)


class TestFilterConfig:
    """Tests for FilterConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FilterConfig()
        assert config.remove_front_matter is False
        assert config.remove_back_matter is False
        assert config.include_translator_content is True
        assert config.remove_inline_notes is False
        assert config.extra_front_matter_patterns == []
        assert config.extra_back_matter_patterns == []

    def test_is_filtering_enabled_default(self):
        """Test that filtering is disabled by default."""
        config = FilterConfig()
        assert config.is_filtering_enabled() is False

    def test_is_filtering_enabled_front_matter(self):
        """Test that filtering is enabled when front matter removal is on."""
        config = FilterConfig(remove_front_matter=True)
        assert config.is_filtering_enabled() is True

    def test_is_filtering_enabled_back_matter(self):
        """Test that filtering is enabled when back matter removal is on."""
        config = FilterConfig(remove_back_matter=True)
        assert config.is_filtering_enabled() is True

    def test_is_filtering_enabled_inline_notes(self):
        """Test that filtering is enabled when inline notes removal is on."""
        config = FilterConfig(remove_inline_notes=True)
        assert config.is_filtering_enabled() is True


class TestFilterResult:
    """Tests for FilterResult dataclass."""

    def test_removed_count(self):
        """Test removed_count property calculation."""
        result = FilterResult(original_count=10, filtered_count=7)
        assert result.removed_count == 3

    def test_get_summary_no_filtering(self):
        """Test summary when no chapters were filtered."""
        result = FilterResult(original_count=10, filtered_count=10)
        summary = result.get_summary()
        assert "Filtered 0 of 10 chapters" in summary

    def test_get_summary_with_front_matter(self):
        """Test summary includes front matter details."""
        result = FilterResult(
            original_count=10,
            filtered_count=7,
            removed_front_matter=["Cover", "Title Page", "Copyright"],
        )
        summary = result.get_summary()
        assert "Filtered 3 of 10 chapters" in summary
        assert "Front matter removed: 3" in summary
        assert "Cover" in summary

    def test_get_summary_with_back_matter(self):
        """Test summary includes back matter details."""
        result = FilterResult(
            original_count=10,
            filtered_count=8,
            removed_back_matter=["Notes", "Index"],
        )
        summary = result.get_summary()
        assert "Back matter removed: 2" in summary

    def test_get_summary_with_translator_content(self):
        """Test summary shows kept translator content."""
        result = FilterResult(
            original_count=10,
            filtered_count=9,
            kept_translator_content=["Translator's Preface"],
        )
        summary = result.get_summary()
        assert "Translator content kept: 1" in summary


class TestContentFilterClassification:
    """Tests for chapter classification."""

    def test_classify_front_matter_cover(self):
        """Test classification of cover pages."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Cover") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Cover Page") == ChapterType.FRONT_MATTER

    def test_classify_front_matter_title(self):
        """Test classification of title pages."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Title") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Title Page") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Half-Title") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Halftitle Page") == ChapterType.FRONT_MATTER

    def test_classify_front_matter_copyright(self):
        """Test classification of copyright pages."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Copyright") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Copyright Page") == ChapterType.FRONT_MATTER

    def test_classify_front_matter_contents(self):
        """Test classification of contents pages."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Contents") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Table of Contents") == ChapterType.FRONT_MATTER

    def test_classify_front_matter_misc(self):
        """Test classification of other front matter."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Dedication") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Epigraph") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Foreword") == ChapterType.FRONT_MATTER
        assert filter_obj.classify_chapter("Preface") == ChapterType.FRONT_MATTER

    def test_classify_back_matter_notes(self):
        """Test classification of notes sections."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Notes") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("Endnotes") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("Footnotes") == ChapterType.BACK_MATTER

    def test_classify_back_matter_index(self):
        """Test classification of index."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Index") == ChapterType.BACK_MATTER

    def test_classify_back_matter_bibliography(self):
        """Test classification of bibliography sections."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Bibliography") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("References") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("Sources") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("Works Cited") == ChapterType.BACK_MATTER

    def test_classify_back_matter_about(self):
        """Test classification of about sections."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("About the Author") == ChapterType.BACK_MATTER
        assert filter_obj.classify_chapter("Also by") == ChapterType.BACK_MATTER

    def test_classify_translator_content(self):
        """Test classification of translator content."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Translator's Preface") == ChapterType.TRANSLATOR_CONTENT
        assert (
            filter_obj.classify_chapter("Translator's Introduction")
            == ChapterType.TRANSLATOR_CONTENT
        )
        assert filter_obj.classify_chapter("Translators Note") == ChapterType.TRANSLATOR_CONTENT

    def test_classify_main_content(self):
        """Test classification of main content chapters."""
        filter_obj = ContentFilter()
        assert filter_obj.classify_chapter("Chapter 1") == ChapterType.MAIN_CONTENT
        assert filter_obj.classify_chapter("Part One") == ChapterType.MAIN_CONTENT
        assert filter_obj.classify_chapter("The Beginning") == ChapterType.MAIN_CONTENT
        assert filter_obj.classify_chapter("1. Introduction") == ChapterType.MAIN_CONTENT


class TestContentFilterInclusionDecisions:
    """Tests for should_include_chapter method."""

    def test_include_all_when_filtering_disabled(self):
        """Test that all chapters are included when filtering is disabled."""
        filter_obj = ContentFilter(FilterConfig())
        assert filter_obj.should_include_chapter("Cover") is True
        assert filter_obj.should_include_chapter("Notes") is True
        assert filter_obj.should_include_chapter("Chapter 1") is True

    def test_exclude_front_matter(self):
        """Test front matter exclusion when enabled."""
        config = FilterConfig(remove_front_matter=True)
        filter_obj = ContentFilter(config)
        assert filter_obj.should_include_chapter("Cover") is False
        assert filter_obj.should_include_chapter("Title Page") is False
        assert filter_obj.should_include_chapter("Chapter 1") is True

    def test_exclude_back_matter(self):
        """Test back matter exclusion when enabled."""
        config = FilterConfig(remove_back_matter=True)
        filter_obj = ContentFilter(config)
        assert filter_obj.should_include_chapter("Notes") is False
        assert filter_obj.should_include_chapter("Index") is False
        assert filter_obj.should_include_chapter("Chapter 1") is True

    def test_keep_translator_content_by_default(self):
        """Test that translator content is kept by default."""
        config = FilterConfig(remove_front_matter=True)
        filter_obj = ContentFilter(config)
        assert filter_obj.should_include_chapter("Translator's Preface") is True

    def test_exclude_translator_content_when_disabled(self):
        """Test translator content exclusion when disabled."""
        config = FilterConfig(
            remove_front_matter=True,
            include_translator_content=False,
        )
        filter_obj = ContentFilter(config)
        assert filter_obj.should_include_chapter("Translator's Preface") is False


class TestContentFilterChapters:
    """Tests for filter_chapters method."""

    def _create_chapter(self, title: str, paragraphs: list[str] | None = None) -> ChapterNode:
        """Helper to create a ChapterNode."""
        return ChapterNode(
            title=title,
            level=1,
            href="test.xhtml",
            paragraphs=paragraphs or ["Test paragraph."],
        )

    def test_no_filtering_returns_all(self):
        """Test that no chapters are removed when filtering is disabled."""
        config = FilterConfig()
        filter_obj = ContentFilter(config)
        chapters = [
            self._create_chapter("Cover"),
            self._create_chapter("Chapter 1"),
            self._create_chapter("Notes"),
        ]
        filtered, result = filter_obj.filter_chapters(chapters)
        assert len(filtered) == 3
        assert result.filtered_count == 3
        assert result.removed_count == 0

    def test_filter_front_matter(self):
        """Test front matter filtering."""
        config = FilterConfig(remove_front_matter=True)
        filter_obj = ContentFilter(config)
        chapters = [
            self._create_chapter("Cover"),
            self._create_chapter("Title Page"),
            self._create_chapter("Chapter 1"),
            self._create_chapter("Chapter 2"),
        ]
        filtered, result = filter_obj.filter_chapters(chapters)
        assert len(filtered) == 2
        assert result.removed_count == 2
        assert "Cover" in result.removed_front_matter
        assert "Title Page" in result.removed_front_matter

    def test_filter_back_matter(self):
        """Test back matter filtering."""
        config = FilterConfig(remove_back_matter=True)
        filter_obj = ContentFilter(config)
        chapters = [
            self._create_chapter("Chapter 1"),
            self._create_chapter("Chapter 2"),
            self._create_chapter("Notes"),
            self._create_chapter("Index"),
        ]
        filtered, result = filter_obj.filter_chapters(chapters)
        assert len(filtered) == 2
        assert result.removed_count == 2
        assert "Notes" in result.removed_back_matter
        assert "Index" in result.removed_back_matter

    def test_filter_both(self):
        """Test filtering both front and back matter."""
        config = FilterConfig(remove_front_matter=True, remove_back_matter=True)
        filter_obj = ContentFilter(config)
        chapters = [
            self._create_chapter("Cover"),
            self._create_chapter("Chapter 1"),
            self._create_chapter("Notes"),
        ]
        filtered, result = filter_obj.filter_chapters(chapters)
        assert len(filtered) == 1
        assert filtered[0].title == "Chapter 1"

    def test_keep_translator_content(self):
        """Test that translator content is kept."""
        config = FilterConfig(remove_front_matter=True)
        filter_obj = ContentFilter(config)
        chapters = [
            self._create_chapter("Cover"),
            self._create_chapter("Translator's Introduction"),
            self._create_chapter("Chapter 1"),
        ]
        filtered, result = filter_obj.filter_chapters(chapters)
        assert len(filtered) == 2
        assert any(c.title == "Translator's Introduction" for c in filtered)
        assert "Translator's Introduction" in result.kept_translator_content


class TestInlineNotesRemoval:
    """Tests for inline notes removal."""

    def test_find_notes_section_with_heading(self):
        """Test finding notes section by heading."""
        filter_obj = ContentFilter()
        paragraphs = [
            "This is the main content.",
            "More content here.",
            "Notes",
            "1. First note reference.",
            "2. Second note reference.",
        ]
        start = filter_obj._find_notes_section_start(paragraphs)
        assert start == 2

    def test_find_notes_section_with_numbered_lines(self):
        """Test finding notes section by numbered lines.

        Note: The algorithm only checks the last 30% of paragraphs to avoid
        false positives. With 10 paragraphs, it checks from index 7 backward.
        """
        filter_obj = ContentFilter()
        paragraphs = [
            "This is the main content.",
            "More content here.",
            "Third paragraph.",
            "Fourth paragraph.",
            "Fifth paragraph.",
            "Sixth paragraph.",
            "Seventh paragraph.",
            "1. First note.",
            "2. Second note.",
            "3. Third note.",
        ]
        start = filter_obj._find_notes_section_start(paragraphs)
        assert start == 7

    def test_no_notes_section(self):
        """Test when no notes section exists."""
        filter_obj = ContentFilter()
        paragraphs = [
            "This is the main content.",
            "More content here.",
            "Final paragraph.",
        ]
        start = filter_obj._find_notes_section_start(paragraphs)
        assert start is None

    def test_remove_inline_notes(self):
        """Test inline notes removal from chapter."""
        config = FilterConfig(remove_inline_notes=True)
        filter_obj = ContentFilter(config)

        chapter = ChapterNode(
            title="Chapter 1",
            level=1,
            href="test.xhtml",
            paragraphs=[
                "This is the main content.",
                "More content here.",
                "Notes",
                "1. First note.",
                "2. Second note.",
            ],
        )

        chapters = [chapter]
        filtered, result = filter_obj.filter_chapters(chapters)

        assert len(filtered) == 1
        assert len(filtered[0].paragraphs) == 2
        assert result.chapters_with_notes_removed == 1


class TestCustomPatterns:
    """Tests for custom pattern support."""

    def test_extra_front_matter_patterns(self):
        """Test adding custom front matter patterns."""
        config = FilterConfig(
            remove_front_matter=True,
            extra_front_matter_patterns=[r"^my\s+custom\s+page$"],
        )
        filter_obj = ContentFilter(config)
        assert filter_obj.classify_chapter("My Custom Page") == ChapterType.FRONT_MATTER

    def test_extra_back_matter_patterns(self):
        """Test adding custom back matter patterns."""
        config = FilterConfig(
            remove_back_matter=True,
            extra_back_matter_patterns=[r"^appendix\s+\d+$"],
        )
        filter_obj = ContentFilter(config)
        assert filter_obj.classify_chapter("Appendix 1") == ChapterType.BACK_MATTER


class TestPatternCoverage:
    """Tests to ensure patterns match expected content types."""

    def test_front_matter_patterns_are_valid_regex(self):
        """Test that all front matter patterns are valid regex."""
        import re

        for pattern in FRONT_MATTER_PATTERNS:
            # Should not raise
            re.compile(pattern, re.IGNORECASE)

    def test_back_matter_patterns_are_valid_regex(self):
        """Test that all back matter patterns are valid regex."""
        import re

        for pattern in BACK_MATTER_PATTERNS:
            # Should not raise
            re.compile(pattern, re.IGNORECASE)

    def test_translator_patterns_are_valid_regex(self):
        """Test that all translator patterns are valid regex."""
        import re

        for pattern in TRANSLATOR_PATTERNS:
            # Should not raise
            re.compile(pattern, re.IGNORECASE)
