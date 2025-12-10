"""Preview state models for chapter editing workflow.

These models track the state of chapters being previewed and edited
before conversion to audiobook.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PreviewChapter:
    """A chapter in the preview with editing state."""

    title: str
    level: int
    word_count: int
    paragraph_count: int
    content_preview: str  # First 500 chars
    included: bool = True
    merged_into: int | None = None  # Index of chapter this merges into
    original_content: str = ""  # Full content for processing


@dataclass
class ChapterPreviewState:
    """State for the preview workflow."""

    source_file: Path
    detection_method: str
    chapters: list[PreviewChapter] = field(default_factory=list)
    modified: bool = False
    book_title: str = ""
    book_author: str = ""

    def get_included_chapters(self) -> list[PreviewChapter]:
        """Get chapters that are included (not excluded or merged)."""
        return [c for c in self.chapters if c.included and c.merged_into is None]

    def get_total_words(self) -> int:
        """Get total word count of included chapters."""
        return sum(c.word_count for c in self.get_included_chapters())

    def get_chapter_selection_string(self) -> str | None:
        """Convert included chapters to a selection string (e.g., '1,3,5-7').

        Returns:
            Selection string for ChapterSelector, or None if all chapters included.
        """
        if not self.chapters:
            return None

        # Get indices of included chapters (1-indexed for user display)
        included_indices = [
            i + 1  # Convert to 1-indexed
            for i, ch in enumerate(self.chapters)
            if ch.included and ch.merged_into is None
        ]

        # If all chapters are included, return None (means "all")
        if len(included_indices) == len(self.chapters):
            return None

        if not included_indices:
            return ""  # Nothing selected

        # Convert to ranges for compact representation
        # e.g., [1, 2, 3, 5, 7, 8, 9] → "1-3,5,7-9"
        ranges: list[str] = []
        start = included_indices[0]
        end = start

        for idx in included_indices[1:]:
            if idx == end + 1:
                # Consecutive
                end = idx
            else:
                # Gap - emit current range
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = end = idx

        # Emit final range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return ",".join(ranges)

    def export_to_text(self, output_path: Path) -> Path:
        """Export preview state to text file format for processing.

        This exports the current preview state (with merges applied) to a text file
        that can be processed by the audio generator.

        Args:
            output_path: Path to write the text file

        Returns:
            Path to the output file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            # Write metadata header
            title = self.book_title or self.source_file.stem
            author = self.book_author or "Unknown"
            f.write(f"Title: {title}\n")
            f.write(f"Author: {author}\n\n")

            # Write title chapter
            f.write("# Title\n")
            f.write(f"{title}, by {author}\n\n")

            # Write included chapters
            for chapter in self.get_included_chapters():
                # Determine header level based on chapter level
                markers = "#" * min(chapter.level, 6) if chapter.level > 0 else "#"

                f.write(f"{markers} {chapter.title}\n\n")

                # Write paragraphs from original_content
                if chapter.original_content:
                    # Split content into paragraphs and clean up
                    paragraphs = chapter.original_content.split("\n\n")
                    for paragraph in paragraphs:
                        # Clean up text (normalize whitespace, quotes)
                        clean = re.sub(r"[\s\n]+", " ", paragraph.strip())
                        clean = re.sub(r"[\u201c\u201d]", '"', clean)
                        clean = re.sub(r"[\u2018\u2019]", "'", clean)
                        if clean:
                            f.write(f"{clean}\n\n")

        return output_path
