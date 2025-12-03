"""Pause and resume functionality for audiobookify.

This module provides state management for pausing and resuming
audiobook conversions at the chapter level.

Features:
- Save conversion state after each chapter
- Resume from last completed chapter
- Track intermediate files for cleanup
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any

STATE_FILE_NAME = ".audiobookify_state.json"


@dataclass
class ConversionState:
    """Represents the state of an in-progress conversion.

    Attributes:
        source_file: Path to the source file being converted
        total_chapters: Total number of chapters to convert
        completed_chapters: Number of chapters already converted
        speaker: Voice being used
        rate: Speech rate adjustment
        volume: Volume adjustment
        chapters_selection: Chapter selection string if used
        intermediate_files: List of intermediate files created
        timestamp: When state was last updated
    """
    source_file: str
    total_chapters: int = 0
    completed_chapters: int = 0
    speaker: str = "en-US-AndrewNeural"
    rate: str | None = None
    volume: str | None = None
    chapters_selection: str | None = None
    intermediate_files: list[str] = field(default_factory=list)
    timestamp: float | None = None

    @property
    def is_resumable(self) -> bool:
        """Check if this state can be resumed.

        Returns:
            True if there is progress but not complete
        """
        return 0 < self.completed_chapters < self.total_chapters

    @property
    def progress_percentage(self) -> float:
        """Get progress as a percentage.

        Returns:
            Percentage of chapters completed (0-100)
        """
        if self.total_chapters == 0:
            return 0.0
        return (self.completed_chapters / self.total_chapters) * 100

    @property
    def remaining_chapters(self) -> int:
        """Get number of remaining chapters."""
        return max(0, self.total_chapters - self.completed_chapters)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary.

        Returns:
            Dictionary representation of the state
        """
        return {
            "source_file": self.source_file,
            "total_chapters": self.total_chapters,
            "completed_chapters": self.completed_chapters,
            "speaker": self.speaker,
            "rate": self.rate,
            "volume": self.volume,
            "chapters_selection": self.chapters_selection,
            "intermediate_files": self.intermediate_files,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ConversionState':
        """Create state from dictionary.

        Args:
            data: Dictionary with state data

        Returns:
            ConversionState instance
        """
        return cls(
            source_file=data.get("source_file", ""),
            total_chapters=data.get("total_chapters", 0),
            completed_chapters=data.get("completed_chapters", 0),
            speaker=data.get("speaker", "en-US-AndrewNeural"),
            rate=data.get("rate"),
            volume=data.get("volume"),
            chapters_selection=data.get("chapters_selection"),
            intermediate_files=data.get("intermediate_files", []),
            timestamp=data.get("timestamp"),
        )


class StateManager:
    """Manage conversion state for pause/resume functionality.

    This class handles saving and loading conversion state to enable
    resuming interrupted conversions.

    Example:
        >>> manager = StateManager("/path/to/output")
        >>> state = ConversionState(source_file="/path/to/book.txt", total_chapters=10)
        >>> manager.save_state(state)
        >>> # Later...
        >>> loaded = manager.load_state()
        >>> if loaded and loaded.is_resumable:
        ...     print(f"Resume from chapter {loaded.completed_chapters + 1}")
    """

    def __init__(self, directory: str):
        """Initialize the state manager.

        Args:
            directory: Directory where state file will be stored
        """
        self.directory = directory
        self.state_path = os.path.join(directory, STATE_FILE_NAME)

    def save_state(self, state: ConversionState) -> None:
        """Save conversion state to file.

        Args:
            state: ConversionState to save
        """
        import time
        state.timestamp = time.time()

        os.makedirs(self.directory, exist_ok=True)
        with open(self.state_path, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)

    def load_state(self) -> ConversionState | None:
        """Load conversion state from file.

        Returns:
            ConversionState if found, None otherwise
        """
        if not self.has_state():
            return None

        try:
            with open(self.state_path) as f:
                data = json.load(f)
            return ConversionState.from_dict(data)
        except (OSError, json.JSONDecodeError):
            return None

    def clear_state(self) -> None:
        """Clear saved state file."""
        if os.path.exists(self.state_path):
            os.remove(self.state_path)

    def has_state(self) -> bool:
        """Check if a state file exists.

        Returns:
            True if state file exists
        """
        return os.path.exists(self.state_path)

    def state_matches(self, source_file: str) -> bool:
        """Check if saved state matches a source file.

        Args:
            source_file: Path to check against

        Returns:
            True if state exists and matches the source file
        """
        state = self.load_state()
        if not state:
            return False
        # Normalize paths for comparison
        return os.path.normpath(state.source_file) == os.path.normpath(source_file)

    def update_progress(self, completed_chapters: int,
                       intermediate_files: list[str] | None = None) -> None:
        """Update progress in the saved state.

        Args:
            completed_chapters: Number of chapters completed
            intermediate_files: List of intermediate files created
        """
        state = self.load_state()
        if state:
            state.completed_chapters = completed_chapters
            if intermediate_files is not None:
                state.intermediate_files = intermediate_files
            self.save_state(state)

    def get_resume_info(self, source_file: str) -> dict[str, Any] | None:
        """Get resume information if available.

        Args:
            source_file: Path to the source file

        Returns:
            Dict with resume info, or None if no resumable state
        """
        if not self.state_matches(source_file):
            return None

        state = self.load_state()
        if not state or not state.is_resumable:
            return None

        return {
            "start_chapter": state.completed_chapters + 1,
            "total_chapters": state.total_chapters,
            "progress": state.progress_percentage,
            "intermediate_files": state.intermediate_files,
            "speaker": state.speaker,
            "rate": state.rate,
            "volume": state.volume,
        }


def prompt_resume(source_file: str, state_dir: str) -> bool:
    """Check for resumable state and prompt user.

    Args:
        source_file: Source file being converted
        state_dir: Directory containing state file

    Returns:
        True if user wants to resume, False to start fresh
    """
    manager = StateManager(state_dir)
    info = manager.get_resume_info(source_file)

    if not info:
        return False

    print("\nFound incomplete conversion:")
    print(f"  Progress: {info['progress']:.1f}% ({info['start_chapter']-1}/{info['total_chapters']} chapters)")
    print(f"  Voice: {info['speaker']}")

    # In non-interactive mode, default to resume
    # In interactive mode, we'd prompt the user
    return True
