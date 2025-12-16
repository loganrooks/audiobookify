"""Multi-file preview state management.

Tracks preview states for multiple files, enabling browser-style
tabs in the preview panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .preview_state import ChapterPreviewState, PreviewChapter


@dataclass
class MultiPreviewState:
    """Manages preview states for multiple files with tab support."""

    # Map of file path to preview state
    _states: dict[Path, ChapterPreviewState] = field(default_factory=dict)

    # Currently active file (shown in preview)
    _active_file: Path | None = None

    # Maximum number of tabs allowed
    max_tabs: int = 8

    @property
    def active_file(self) -> Path | None:
        """Get the currently active file path."""
        return self._active_file

    @property
    def active_state(self) -> ChapterPreviewState | None:
        """Get the preview state for the active file."""
        if self._active_file is None:
            return None
        return self._states.get(self._active_file)

    @property
    def file_count(self) -> int:
        """Get the number of open file previews."""
        return len(self._states)

    @property
    def is_empty(self) -> bool:
        """Check if there are no open previews."""
        return len(self._states) == 0

    def get_open_files(self) -> list[Path]:
        """Get list of open file paths in order."""
        return list(self._states.keys())

    def get_state(self, file_path: Path) -> ChapterPreviewState | None:
        """Get preview state for a specific file."""
        return self._states.get(file_path)

    def has_file(self, file_path: Path) -> bool:
        """Check if a file is already open."""
        return file_path in self._states

    def add_preview(
        self,
        source_file: Path,
        chapters: list[PreviewChapter],
        detection_method: str,
        book_title: str = "",
        book_author: str = "",
    ) -> bool:
        """Add a new preview or update existing one.

        Args:
            source_file: Path to the source file
            chapters: List of preview chapters
            detection_method: Detection method used
            book_title: Book title
            book_author: Book author

        Returns:
            True if added successfully, False if at max tabs and file not already open
        """
        # If file already open, update it
        if source_file in self._states:
            self._states[source_file] = ChapterPreviewState(
                source_file=source_file,
                detection_method=detection_method,
                chapters=chapters,
                book_title=book_title,
                book_author=book_author,
            )
            self._active_file = source_file
            return True

        # Check max tabs
        if len(self._states) >= self.max_tabs:
            return False

        # Add new preview
        self._states[source_file] = ChapterPreviewState(
            source_file=source_file,
            detection_method=detection_method,
            chapters=chapters,
            book_title=book_title,
            book_author=book_author,
        )
        self._active_file = source_file
        return True

    def switch_to(self, file_path: Path) -> bool:
        """Switch active tab to the specified file.

        Args:
            file_path: Path to switch to

        Returns:
            True if switched successfully, False if file not open
        """
        if file_path not in self._states:
            return False
        self._active_file = file_path
        return True

    def close_tab(self, file_path: Path) -> Path | None:
        """Close a preview tab.

        Args:
            file_path: Path to close

        Returns:
            Path of the new active file, or None if no tabs remain
        """
        if file_path not in self._states:
            return self._active_file

        # Get current position
        files = list(self._states.keys())
        idx = files.index(file_path)

        # Remove the state
        del self._states[file_path]

        # If no tabs left
        if not self._states:
            self._active_file = None
            return None

        # If closed tab was active, switch to adjacent tab
        if self._active_file == file_path:
            # Prefer tab to the left, else tab to the right
            new_files = list(self._states.keys())
            new_idx = min(idx, len(new_files) - 1)
            self._active_file = new_files[new_idx]

        return self._active_file

    def close_all(self) -> None:
        """Close all preview tabs."""
        self._states.clear()
        self._active_file = None

    def close_others(self, keep_file: Path) -> None:
        """Close all tabs except the specified one.

        Args:
            keep_file: Path to keep open
        """
        if keep_file not in self._states:
            return

        state = self._states[keep_file]
        self._states.clear()
        self._states[keep_file] = state
        self._active_file = keep_file

    def get_tab_label(self, file_path: Path, max_length: int = 20) -> str:
        """Get display label for a tab.

        Args:
            file_path: File path
            max_length: Maximum label length

        Returns:
            Truncated filename for display
        """
        name = file_path.stem
        if len(name) > max_length:
            return name[: max_length - 3] + "..."
        return name

    def is_modified(self, file_path: Path) -> bool:
        """Check if a preview has been modified.

        Args:
            file_path: File to check

        Returns:
            True if the preview has modifications
        """
        state = self._states.get(file_path)
        return state.modified if state else False
