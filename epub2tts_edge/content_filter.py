"""Content filtering for front matter, back matter, and inline notes.

This module provides functionality to filter out unwanted content from EPUBs:
- Front matter (cover, title page, copyright, contents, etc.)
- Back matter (notes, index, bibliography, etc.)
- Translator's preface (optionally kept)
- In-chapter endnotes (notes appearing after chapter content)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chapter_detector import ChapterNode

logger = logging.getLogger(__name__)


class ChapterType(Enum):
    """Classification of chapter types."""

    FRONT_MATTER = "front_matter"
    BACK_MATTER = "back_matter"
    TRANSLATOR_CONTENT = "translator_content"
    MAIN_CONTENT = "main_content"


# Front matter title patterns (case-insensitive)
FRONT_MATTER_PATTERNS: list[str] = [
    r"^cover\s*(page)?$",
    r"^half[\s-]?title(\s+page)?$",
    r"^title(\s+page)?$",
    r"^front\s*(page)?$",
    r"^copyright(\s+page)?$",
    r"^contents$",
    r"^table\s+of\s+contents$",
    r"^series(\s+page)?$",
    r"^series\s+editor",
    r"^epigraph$",
    r"^dedication$",
    r"^foreword$",
    r"^preface$",  # General preface (not translator's)
    r"^introduction$",  # General introduction (not translator's)
    r"^editor'?s?\s+(introduction|preface|note)",
    r"^note\s+on\s+(the\s+)?text",
    r"^acknowledgment?s?$",  # At beginning
    r"^about\s+this\s+(e?book|edition)",
    r"^front\s*matter$",
    r"^exordium$",  # Opening section/preamble
]

# Back matter title patterns (case-insensitive)
BACK_MATTER_PATTERNS: list[str] = [
    r"^notes?$",
    r"^end\s*notes?$",
    r"^foot\s*notes?$",
    r"^index$",
    r"^bibliography$",
    r"^references?$",
    r"^sources?$",
    r"^works?\s+cited$",
    r"^further\s+reading$",
    r"^suggested\s+reading$",
    r"^about\s+the\s+author",
    r"^also\s+by",
    r"^other\s+(books|works)\s+by",
    r"^colophon$",
    r"^back\s*matter$",
    r"^appendix",
    r"^glossary$",
]

# Translator content patterns (case-insensitive)
TRANSLATOR_PATTERNS: list[str] = [
    r"^translator'?s?\s+(introduction|preface|note)",
    r"^introduction\s+by\s+.*translator",
    r"^preface\s+by\s+.*translator",
    r"^note\s+by\s+.*translator",
]

# In-chapter endnotes patterns
INLINE_NOTES_PATTERNS: list[str] = [
    r"^\s*\d+\.\s+",  # Lines starting with "1. ", "2. ", etc.
    r"^\s*\[\d+\]\s*",  # Lines starting with "[1]", "[2]", etc.
    r"^\s*\*+\s*",  # Lines starting with asterisks
]


@dataclass
class FilterConfig:
    """Configuration for content filtering."""

    remove_front_matter: bool = False
    remove_back_matter: bool = False
    include_translator_content: bool = True  # Keep translator preface by default
    remove_inline_notes: bool = False

    # Custom patterns (extend defaults)
    extra_front_matter_patterns: list[str] = field(default_factory=list)
    extra_back_matter_patterns: list[str] = field(default_factory=list)

    def is_filtering_enabled(self) -> bool:
        """Check if any filtering is enabled."""
        return self.remove_front_matter or self.remove_back_matter or self.remove_inline_notes


@dataclass
class FilterResult:
    """Result of content filtering operation."""

    original_count: int
    filtered_count: int
    removed_front_matter: list[str] = field(default_factory=list)
    removed_back_matter: list[str] = field(default_factory=list)
    kept_translator_content: list[str] = field(default_factory=list)
    chapters_with_notes_removed: int = 0

    @property
    def removed_count(self) -> int:
        """Total number of chapters removed."""
        return self.original_count - self.filtered_count

    def get_summary(self) -> str:
        """Get a summary of filtering results."""
        lines = [f"Filtered {self.removed_count} of {self.original_count} chapters"]

        if self.removed_front_matter:
            lines.append(f"  Front matter removed: {len(self.removed_front_matter)}")
            for title in self.removed_front_matter[:5]:
                lines.append(f"    - {title}")
            if len(self.removed_front_matter) > 5:
                lines.append(f"    ... and {len(self.removed_front_matter) - 5} more")

        if self.removed_back_matter:
            lines.append(f"  Back matter removed: {len(self.removed_back_matter)}")
            for title in self.removed_back_matter[:5]:
                lines.append(f"    - {title}")
            if len(self.removed_back_matter) > 5:
                lines.append(f"    ... and {len(self.removed_back_matter) - 5} more")

        if self.kept_translator_content:
            lines.append(f"  Translator content kept: {len(self.kept_translator_content)}")
            for title in self.kept_translator_content:
                lines.append(f"    - {title}")

        if self.chapters_with_notes_removed > 0:
            lines.append(
                f"  Chapters with inline notes removed: {self.chapters_with_notes_removed}"
            )

        return "\n".join(lines)


class ContentFilter:
    """Filter content from EPUB chapters."""

    def __init__(self, config: FilterConfig | None = None):
        """Initialize content filter.

        Args:
            config: Filter configuration. Uses defaults if None.
        """
        self.config = config or FilterConfig()
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        # Combine default and custom patterns
        front_patterns = FRONT_MATTER_PATTERNS + self.config.extra_front_matter_patterns
        back_patterns = BACK_MATTER_PATTERNS + self.config.extra_back_matter_patterns

        self._front_matter_re = [re.compile(p, re.IGNORECASE) for p in front_patterns]
        self._back_matter_re = [re.compile(p, re.IGNORECASE) for p in back_patterns]
        self._translator_re = [re.compile(p, re.IGNORECASE) for p in TRANSLATOR_PATTERNS]
        self._inline_notes_re = [re.compile(p) for p in INLINE_NOTES_PATTERNS]

    def classify_chapter(self, title: str) -> ChapterType:
        """Classify a chapter based on its title.

        Args:
            title: Chapter title to classify.

        Returns:
            ChapterType indicating the classification.
        """
        title_clean = title.strip()

        # Check translator content first (takes precedence)
        for pattern in self._translator_re:
            if pattern.search(title_clean):
                return ChapterType.TRANSLATOR_CONTENT

        # Check front matter
        for pattern in self._front_matter_re:
            if pattern.search(title_clean):
                return ChapterType.FRONT_MATTER

        # Check back matter
        for pattern in self._back_matter_re:
            if pattern.search(title_clean):
                return ChapterType.BACK_MATTER

        return ChapterType.MAIN_CONTENT

    def should_include_chapter(self, title: str) -> bool:
        """Determine if a chapter should be included based on config.

        Args:
            title: Chapter title.

        Returns:
            True if chapter should be included, False otherwise.
        """
        chapter_type = self.classify_chapter(title)

        if chapter_type == ChapterType.TRANSLATOR_CONTENT:
            # Include translator content based on config
            return self.config.include_translator_content

        if chapter_type == ChapterType.FRONT_MATTER:
            return not self.config.remove_front_matter

        if chapter_type == ChapterType.BACK_MATTER:
            return not self.config.remove_back_matter

        # Main content is always included
        return True

    def filter_chapters(
        self, chapters: list[ChapterNode]
    ) -> tuple[list[ChapterNode], FilterResult]:
        """Filter a list of chapters based on configuration.

        Args:
            chapters: List of ChapterNode objects to filter.

        Returns:
            Tuple of (filtered chapters, filter result).
        """
        result = FilterResult(
            original_count=len(chapters),
            filtered_count=0,
        )

        if not self.config.is_filtering_enabled():
            result.filtered_count = len(chapters)
            return chapters, result

        filtered: list[ChapterNode] = []

        for chapter in chapters:
            chapter_type = self.classify_chapter(chapter.title)

            if chapter_type == ChapterType.TRANSLATOR_CONTENT:
                if self.config.include_translator_content:
                    result.kept_translator_content.append(chapter.title)
                    filtered.append(chapter)
                else:
                    result.removed_front_matter.append(chapter.title)

            elif chapter_type == ChapterType.FRONT_MATTER:
                if self.config.remove_front_matter:
                    result.removed_front_matter.append(chapter.title)
                    logger.debug("Filtering front matter: %s", chapter.title)
                else:
                    filtered.append(chapter)

            elif chapter_type == ChapterType.BACK_MATTER:
                if self.config.remove_back_matter:
                    result.removed_back_matter.append(chapter.title)
                    logger.debug("Filtering back matter: %s", chapter.title)
                else:
                    filtered.append(chapter)

            else:
                # Main content - always include
                filtered.append(chapter)

        result.filtered_count = len(filtered)

        # Process inline notes if enabled
        if self.config.remove_inline_notes:
            for chapter in filtered:
                if self._remove_inline_notes_from_chapter(chapter):
                    result.chapters_with_notes_removed += 1

        logger.info(
            "Content filter: %d -> %d chapters",
            result.original_count,
            result.filtered_count,
        )

        return filtered, result

    def _remove_inline_notes_from_chapter(self, chapter: ChapterNode) -> bool:
        """Remove inline endnotes from chapter paragraphs.

        This detects and removes note sections that typically appear at the
        end of chapters, identified by:
        - Consecutive numbered lines (1., 2., 3., etc.)
        - Lines starting with [1], [2], etc.
        - A "Notes" heading followed by numbered content

        Args:
            chapter: ChapterNode to process.

        Returns:
            True if notes were removed, False otherwise.
        """
        if not chapter.paragraphs:
            return False

        # Look for notes section at end of chapter
        notes_start_idx = self._find_notes_section_start(chapter.paragraphs)

        if notes_start_idx is not None and notes_start_idx < len(chapter.paragraphs):
            removed_count = len(chapter.paragraphs) - notes_start_idx
            chapter.paragraphs = chapter.paragraphs[:notes_start_idx]
            logger.debug(
                "Removed %d inline note paragraphs from '%s'",
                removed_count,
                chapter.title[:30],
            )
            return True

        return False

    def _find_notes_section_start(self, paragraphs: list[str]) -> int | None:
        """Find where inline notes section starts in paragraphs.

        Args:
            paragraphs: List of paragraph texts.

        Returns:
            Index where notes section starts, or None if not found.
        """
        # Strategy 1: Look for "Notes" heading
        for i, para in enumerate(paragraphs):
            para_clean = para.strip().lower()
            if para_clean in ("notes", "notes:", "endnotes", "endnotes:"):
                return i

        # Strategy 2: Look for consecutive numbered lines at end
        # Start from end and look backward for numbered sequence
        if len(paragraphs) < 3:
            return None

        # Check last 30% of paragraphs for note patterns
        check_start = max(0, int(len(paragraphs) * 0.7))
        consecutive_notes = 0
        notes_start = None

        for i in range(len(paragraphs) - 1, check_start - 1, -1):
            para = paragraphs[i].strip()

            # Check if this looks like a note
            is_note = False
            for pattern in self._inline_notes_re:
                if pattern.match(para):
                    is_note = True
                    break

            if is_note:
                consecutive_notes += 1
                notes_start = i
            else:
                # If we found at least 3 consecutive notes, we found a section
                if consecutive_notes >= 3:
                    return notes_start
                consecutive_notes = 0
                notes_start = None

        # Check if we ended with enough consecutive notes
        if consecutive_notes >= 3:
            return notes_start

        return None

    def filter_tree(self, root: ChapterNode) -> tuple[ChapterNode, FilterResult]:
        """Filter a chapter tree, removing filtered chapters and their children.

        Args:
            root: Root ChapterNode of the tree.

        Returns:
            Tuple of (filtered root, filter result).
        """
        from .chapter_detector import ChapterNode

        result = FilterResult(original_count=0, filtered_count=0)

        def count_chapters(node: ChapterNode) -> int:
            count = 1 if node.level > 0 else 0
            for child in node.children:
                count += count_chapters(child)
            return count

        result.original_count = count_chapters(root)

        if not self.config.is_filtering_enabled():
            result.filtered_count = result.original_count
            return root, result

        def filter_node(node: ChapterNode) -> ChapterNode | None:
            """Recursively filter node and its children."""
            # Check if this node should be included
            if node.level > 0 and not self.should_include_chapter(node.title):
                chapter_type = self.classify_chapter(node.title)
                if chapter_type == ChapterType.FRONT_MATTER:
                    result.removed_front_matter.append(node.title)
                elif chapter_type == ChapterType.BACK_MATTER:
                    result.removed_back_matter.append(node.title)
                elif chapter_type == ChapterType.TRANSLATOR_CONTENT:
                    if not self.config.include_translator_content:
                        result.removed_front_matter.append(node.title)
                return None

            # Process inline notes if enabled
            if self.config.remove_inline_notes and node.paragraphs:
                if self._remove_inline_notes_from_chapter(node):
                    result.chapters_with_notes_removed += 1

            # Filter children
            filtered_children = []
            for child in node.children:
                filtered_child = filter_node(child)
                if filtered_child is not None:
                    filtered_children.append(filtered_child)

            # Create new node with filtered children
            new_node = ChapterNode(
                title=node.title,
                level=node.level,
                href=node.href,
                anchor=node.anchor,
                content=node.content,
                paragraphs=node.paragraphs.copy() if node.paragraphs else [],
                play_order=node.play_order,
            )
            for child in filtered_children:
                new_node.add_child(child)

            # Track translator content
            if node.level > 0:
                chapter_type = self.classify_chapter(node.title)
                if chapter_type == ChapterType.TRANSLATOR_CONTENT:
                    result.kept_translator_content.append(node.title)

            return new_node

        filtered_root = filter_node(root)
        if filtered_root is None:
            # Shouldn't happen for root, but handle gracefully
            filtered_root = ChapterNode(title="Root", level=0)

        result.filtered_count = count_chapters(filtered_root)

        logger.info(
            "Content filter (tree): %d -> %d chapters",
            result.original_count,
            result.filtered_count,
        )

        return filtered_root, result
