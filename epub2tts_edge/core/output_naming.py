"""Output naming templates for audiobook files.

This module provides template-based naming for output files,
allowing users to customize how their audiobooks are named.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BookMetadata:
    """Metadata about a book for use in naming templates.

    Attributes:
        title: Book title
        author: Book author
        year: Publication year (if available)
        series: Series name (if available)
        series_index: Position in series (if available)
        language: Book language code
        publisher: Publisher name (if available)
    """

    title: str
    author: str = "Unknown Author"
    year: str | None = None
    series: str | None = None
    series_index: int | None = None
    language: str = "en"
    publisher: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for template formatting."""
        return {
            "title": self.title,
            "author": self.author,
            "year": self.year or "Unknown",
            "series": self.series or "",
            "series_index": self.series_index or "",
            "language": self.language,
            "publisher": self.publisher or "",
        }


# Characters not allowed in filenames on various systems
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Multiple spaces or underscores
MULTIPLE_SPACES = re.compile(r"[\s_]+")


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Sanitize a string for use as a filename.

    Args:
        name: The string to sanitize
        replacement: Character to replace invalid chars with

    Returns:
        A sanitized string safe for filenames
    """
    # Replace invalid characters
    result = INVALID_FILENAME_CHARS.sub(replacement, name)
    # Collapse multiple spaces/underscores
    result = MULTIPLE_SPACES.sub(" ", result)
    # Strip leading/trailing whitespace and dots
    result = result.strip(" .")
    # Ensure we have something
    return result or "audiobook"


class OutputNaming:
    """Template-based output naming for audiobook files.

    Supports template variables:
        {title} - Book title
        {author} - Book author
        {year} - Publication year
        {series} - Series name
        {series_index} - Position in series
        {language} - Language code
        {publisher} - Publisher name

    Example templates:
        "{author} - {title}" -> "John Smith - My Book"
        "{title} ({year})" -> "My Book (2024)"
        "{series} {series_index} - {title}" -> "Fantasy Series 1 - First Book"

    Usage:
        >>> naming = OutputNaming("{author} - {title}")
        >>> metadata = BookMetadata(title="My Book", author="John Smith")
        >>> naming.format(metadata)
        'John Smith - My Book.m4b'
    """

    DEFAULT_TEMPLATE = "{author} - {title}"

    # Available template variables and their descriptions
    TEMPLATE_VARIABLES = {
        "title": "Book title",
        "author": "Book author",
        "year": "Publication year",
        "series": "Series name",
        "series_index": "Position in series",
        "language": "Language code",
        "publisher": "Publisher name",
    }

    def __init__(self, template: str | None = None, extension: str = ".m4b") -> None:
        """Initialize output naming with a template.

        Args:
            template: The naming template (default: "{author} - {title}")
            extension: File extension to append (default: ".m4b")
        """
        self.template = template or self.DEFAULT_TEMPLATE
        self.extension = extension

    def format(self, metadata: BookMetadata) -> str:
        """Format output filename from metadata.

        Args:
            metadata: Book metadata to use for formatting

        Returns:
            Formatted filename with extension
        """
        data = metadata.to_dict()

        # Handle missing optional fields gracefully
        try:
            result = self.template.format(**data)
        except KeyError:
            # Unknown template variable, fall back to title
            result = metadata.title

        # Clean up any empty parts (e.g., "{series} - {title}" when no series)
        result = re.sub(r"\s*-\s*-\s*", " - ", result)  # Double dashes
        result = re.sub(r"^\s*-\s*", "", result)  # Leading dash
        result = re.sub(r"\s*-\s*$", "", result)  # Trailing dash
        result = re.sub(r"\(\s*\)", "", result)  # Empty parentheses
        result = re.sub(r"\s+", " ", result)  # Multiple spaces

        # Sanitize for filesystem
        result = sanitize_filename(result)

        # Add extension
        if not result.endswith(self.extension):
            result += self.extension

        return result

    def format_path(self, metadata: BookMetadata, output_dir: Path) -> Path:
        """Format complete output path.

        Args:
            metadata: Book metadata to use for formatting
            output_dir: Directory for output file

        Returns:
            Complete path to output file
        """
        filename = self.format(metadata)
        return output_dir / filename

    def validate_template(self) -> tuple[bool, str]:
        """Validate the template string.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for at least one variable
        if "{" not in self.template or "}" not in self.template:
            return False, "Template must contain at least one variable like {title}"

        # Check for valid variables
        pattern = re.compile(r"\{(\w+)\}")
        variables = pattern.findall(self.template)

        if not variables:
            return False, "Template must contain at least one variable"

        unknown = set(variables) - set(self.TEMPLATE_VARIABLES.keys())
        if unknown:
            return False, f"Unknown template variables: {', '.join(unknown)}"

        # Test format with dummy data
        try:
            test_metadata = BookMetadata(title="Test", author="Test")
            self.format(test_metadata)
        except Exception as e:
            return False, f"Template error: {e}"

        return True, ""

    @classmethod
    def get_variable_help(cls) -> str:
        """Get help text for template variables.

        Returns:
            Formatted help text listing all variables
        """
        lines = ["Available template variables:"]
        for var, desc in cls.TEMPLATE_VARIABLES.items():
            lines.append(f"  {{{var}}} - {desc}")
        return "\n".join(lines)


# Preset naming templates
NAMING_PRESETS: dict[str, OutputNaming] = {
    "author_title": OutputNaming("{author} - {title}"),
    "title_only": OutputNaming("{title}"),
    "title_author": OutputNaming("{title} by {author}"),
    "series": OutputNaming("{series} {series_index} - {title}"),
    "year": OutputNaming("{title} ({year})"),
    "full": OutputNaming("{author} - {series} {series_index} - {title}"),
}


def get_naming_preset(name: str) -> OutputNaming | None:
    """Get a naming preset by name.

    Args:
        name: Preset name

    Returns:
        The OutputNaming instance if found, None otherwise
    """
    return NAMING_PRESETS.get(name.lower())


def list_naming_presets() -> list[str]:
    """Get all available preset names.

    Returns:
        List of preset name keys
    """
    return list(NAMING_PRESETS.keys())
