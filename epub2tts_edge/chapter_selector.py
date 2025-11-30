"""Chapter selection functionality for audiobookify.

This module provides chapter selection capabilities, allowing users to
convert only specific chapters from a book.

Supported selection formats:
- Single chapter: "3" (chapter 3 only)
- Range: "2-5" (chapters 2 through 5)
- Open-ended: "5-" (chapter 5 to end)
- Open-start: "-5" (chapters 1 through 5)
- Multiple: "1,3,5-7" (chapters 1, 3, and 5 through 7)
"""
from dataclasses import dataclass
from typing import Any


class InvalidSelectionError(ValueError):
    """Raised when a chapter selection string is invalid."""
    pass


@dataclass
class ChapterRange:
    """Represents a range of chapters.

    Attributes:
        start: Starting chapter number (1-indexed), or None for "from beginning"
        end: Ending chapter number (1-indexed), or None for "to end"
    """
    start: int | None
    end: int | None

    def contains(self, chapter_num: int) -> bool:
        """Check if a chapter number is within this range.

        Args:
            chapter_num: 1-indexed chapter number to check

        Returns:
            True if the chapter is within the range
        """
        if self.start is not None and chapter_num < self.start:
            return False
        if self.end is not None and chapter_num > self.end:
            return False
        return True


def parse_chapter_selection(selection: str) -> list[ChapterRange]:
    """Parse a chapter selection string into ranges.

    Args:
        selection: Selection string like "1,3,5-7,10-"

    Returns:
        List of ChapterRange objects

    Raises:
        InvalidSelectionError: If the selection format is invalid
    """
    if not selection or not selection.strip():
        raise InvalidSelectionError("Chapter selection cannot be empty")

    ranges = []
    parts = [p.strip() for p in selection.split(",")]

    for part in parts:
        if not part:
            continue

        # Check for range (contains -)
        if "-" in part:
            # Handle special cases: "-5" (open start) or "5-" (open end)
            if part.startswith("-"):
                # Open start: -5 means chapters 1 to 5
                try:
                    end = int(part[1:])
                    if end < 1:
                        raise InvalidSelectionError(
                            f"Invalid chapter number: {end}"
                        )
                    ranges.append(ChapterRange(start=None, end=end))
                except ValueError:
                    raise InvalidSelectionError(
                        f"Invalid chapter selection: {part}"
                    ) from None
            elif part.endswith("-"):
                # Open end: 5- means chapter 5 to end
                try:
                    start = int(part[:-1])
                    if start < 1:
                        raise InvalidSelectionError(
                            f"Invalid chapter number: {start}"
                        )
                    ranges.append(ChapterRange(start=start, end=None))
                except ValueError:
                    raise InvalidSelectionError(
                        f"Invalid chapter selection: {part}"
                    ) from None
            else:
                # Regular range: 2-5
                try:
                    start_str, end_str = part.split("-", 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start < 1 or end < 1:
                        raise InvalidSelectionError(
                            f"Chapter numbers must be positive: {part}"
                        )
                    if end < start:
                        raise InvalidSelectionError(
                            f"Invalid range (end < start): {part}"
                        )
                    ranges.append(ChapterRange(start=start, end=end))
                except ValueError:
                    raise InvalidSelectionError(
                        f"Invalid chapter selection: {part}"
                    ) from None
        else:
            # Single chapter number
            try:
                num = int(part)
                if num < 1:
                    raise InvalidSelectionError(
                        f"Chapter numbers must be positive: {num}"
                    )
                ranges.append(ChapterRange(start=num, end=num))
            except ValueError:
                raise InvalidSelectionError(
                    f"Invalid chapter number: {part}"
                ) from None

    if not ranges:
        raise InvalidSelectionError("No valid chapter selections found")

    return ranges


class ChapterSelector:
    """Select specific chapters for processing.

    Example:
        >>> selector = ChapterSelector("1,3,5-7")
        >>> selector.is_selected(1)  # True
        >>> selector.is_selected(2)  # False
        >>> selector.is_selected(5)  # True
    """

    def __init__(self, selection: str | None = None):
        """Initialize the selector.

        Args:
            selection: Chapter selection string, or None to select all
        """
        self.selection_string = selection
        if selection:
            self.ranges = parse_chapter_selection(selection)
        else:
            self.ranges = []  # Empty means select all

    def is_selected(self, chapter_num: int) -> bool:
        """Check if a chapter number is selected.

        Args:
            chapter_num: 1-indexed chapter number

        Returns:
            True if the chapter is selected
        """
        if not self.ranges:
            return True  # No selection means all chapters
        return any(r.contains(chapter_num) for r in self.ranges)

    def filter_chapters(self, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter a list of chapters based on selection.

        Args:
            chapters: List of chapter dicts (with 'title', 'paragraphs', etc.)

        Returns:
            Filtered list of chapters in original order
        """
        if not self.ranges:
            return chapters  # No selection means all chapters

        return [
            ch for i, ch in enumerate(chapters, start=1)
            if self.is_selected(i)
        ]

    def get_selected_indices(self, total_chapters: int) -> list[int]:
        """Get 0-indexed list of selected chapter indices.

        Args:
            total_chapters: Total number of chapters in the book

        Returns:
            List of 0-indexed chapter indices that are selected
        """
        return [
            i for i in range(total_chapters)
            if self.is_selected(i + 1)  # Convert to 1-indexed for check
        ]

    def get_summary(self) -> str:
        """Get a human-readable summary of the selection.

        Returns:
            Summary string like "Chapters: 1, 3, 5-7"
        """
        if not self.ranges:
            return "All chapters"

        parts = []
        for r in self.ranges:
            if r.start == r.end:
                parts.append(str(r.start))
            elif r.start is None:
                parts.append(f"1-{r.end}")
            elif r.end is None:
                parts.append(f"{r.start}-end")
            else:
                parts.append(f"{r.start}-{r.end}")

        return f"Chapters: {', '.join(parts)}"

    def __bool__(self) -> bool:
        """Return True if a selection is active."""
        return bool(self.ranges)

    def __repr__(self) -> str:
        return f"ChapterSelector({self.selection_string!r})"
