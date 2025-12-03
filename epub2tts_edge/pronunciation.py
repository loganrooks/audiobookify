"""Custom pronunciation dictionary for TTS.

This module provides functionality to define custom pronunciations
for proper nouns, technical terms, and other words that may be
mispronounced by the TTS engine.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class PronunciationConfig:
    """Configuration for pronunciation processing.

    Attributes:
        dictionary: Dict mapping words to their pronunciations
        case_sensitive: Whether replacements are case-sensitive
        enabled: Whether pronunciation processing is enabled
    """

    dictionary: dict[str, str] = field(default_factory=dict)
    case_sensitive: bool = False
    enabled: bool = True


@dataclass
class PronunciationEntry:
    """A single pronunciation dictionary entry.

    Attributes:
        original: The original word/phrase
        replacement: The pronunciation replacement
        description: Optional description/notes
    """

    original: str
    replacement: str
    description: str | None = None


class PronunciationProcessor:
    """Processes text with custom pronunciation replacements.

    This class applies pronunciation substitutions to text before
    it is sent to the TTS engine.

    Attributes:
        config: PronunciationConfig instance with settings
    """

    def __init__(self, config: PronunciationConfig | None = None):
        """Initialize the processor.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or PronunciationConfig()
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for all dictionary entries."""
        self._compiled_patterns.clear()

        flags = 0 if self.config.case_sensitive else re.IGNORECASE

        for original in self.config.dictionary:
            # Use word boundaries to avoid partial word matches
            pattern = r"\b" + re.escape(original) + r"\b"
            self._compiled_patterns[original] = re.compile(pattern, flags)

    def process_text(self, text: str) -> str:
        """Process text with pronunciation replacements.

        Args:
            text: Input text to process

        Returns:
            Text with pronunciations applied
        """
        if not self.config.enabled:
            return text

        if not self.config.dictionary:
            return text

        result = text

        for original, pattern in self._compiled_patterns.items():
            replacement = self.config.dictionary[original]
            result = pattern.sub(replacement, result)

        return result

    def add_entry(self, original: str, replacement: str) -> None:
        """Add a pronunciation entry.

        Args:
            original: The word/phrase to match
            replacement: The pronunciation replacement
        """
        self.config.dictionary[original] = replacement
        self._compile_patterns()

    def remove_entry(self, original: str) -> None:
        """Remove a pronunciation entry.

        Args:
            original: The word/phrase to remove
        """
        if original in self.config.dictionary:
            del self.config.dictionary[original]
            self._compile_patterns()

    def load_dictionary(self, file_path: str) -> None:
        """Load a pronunciation dictionary from a file.

        Supports JSON and simple text formats.

        JSON format:
            {"word": "pronunciation", ...}

        Text format:
            # Comment
            word = pronunciation
            another_word = another_pronunciation

        Args:
            file_path: Path to the dictionary file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not file_path or not isinstance(file_path, str):
            raise ValueError("Invalid file path")

        import os

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dictionary file not found: {file_path}")

        ext = file_path.rsplit(".", 1)[-1].lower()

        if ext == "json":
            self._load_json(file_path)
        else:
            self._load_text(file_path)

        self._compile_patterns()

    def _load_json(self, file_path: str) -> None:
        """Load dictionary from JSON file."""
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            self.config.dictionary.update(data)
        else:
            raise ValueError("JSON file must contain a dictionary object")

    def _load_text(self, file_path: str) -> None:
        """Load dictionary from text file."""
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse "word = pronunciation" format
                if "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        original = parts[0].strip()
                        replacement = parts[1].strip()
                        if original and replacement:
                            self.config.dictionary[original] = replacement

    def save_dictionary(self, file_path: str) -> None:
        """Save the pronunciation dictionary to a file.

        Args:
            file_path: Path for the output file (JSON format)
        """
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.config.dictionary, f, indent=2, ensure_ascii=False)

    @property
    def entry_count(self) -> int:
        """Get the number of entries in the dictionary."""
        return len(self.config.dictionary)

    def list_entries(self) -> list[tuple[str, str]]:
        """List all dictionary entries.

        Returns:
            List of (original, replacement) tuples
        """
        return list(self.config.dictionary.items())

    def clear(self) -> None:
        """Clear all dictionary entries."""
        self.config.dictionary.clear()
        self._compiled_patterns.clear()
