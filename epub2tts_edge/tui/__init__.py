"""Audiobookify TUI - Terminal User Interface.

This package contains the TUI components organized into submodules:
- models/: Pure data classes (PreviewChapter, ChapterPreviewState)
- screens/: Modal screens (HelpScreen, DirectoryBrowserScreen)
- panels/: Panel widgets (being extracted incrementally)
- app.py: Main AudiobookifyApp class
"""

# Re-export models
# Re-export main app and entry point
# Re-export other commonly used items from app.py for backward compatibility
from .app import (
    AudiobookifyApp,
    BookTask,
    ChapterPreviewItem,
    EPUBFileItem,
    FilePanel,
    JobItem,
    JobsPanel,
    LogPanel,
    PathInput,
    PreviewPanel,
    ProcessingStatus,
    ProgressPanel,
    QueuePanel,
    SettingsPanel,
    VoicePreviewStatus,
    main,
)
from .models import ChapterPreviewState, PreviewChapter

# Re-export screens
from .screens import DirectoryBrowserScreen, FilteredDirectoryTree, HelpScreen

__all__ = [
    # Main app
    "AudiobookifyApp",
    "main",
    # Models
    "PreviewChapter",
    "ChapterPreviewState",
    # Screens
    "HelpScreen",
    "DirectoryBrowserScreen",
    "FilteredDirectoryTree",
    # Panels
    "FilePanel",
    "SettingsPanel",
    "PreviewPanel",
    "ProgressPanel",
    "QueuePanel",
    "JobsPanel",
    "LogPanel",
    # Items
    "EPUBFileItem",
    "JobItem",
    "ChapterPreviewItem",
    # Other
    "PathInput",
    "VoicePreviewStatus",
    "ProcessingStatus",
    "BookTask",
]
