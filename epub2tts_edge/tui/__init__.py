"""Audiobookify TUI - Terminal User Interface.

This package contains the TUI components organized into submodules:
- models/: Data models and status widgets (PreviewChapter, ChapterPreviewState, VoicePreviewStatus)
- screens/: Modal screens (HelpScreen, DirectoryBrowserScreen)
- panels/: Panel widgets (FilePanel, SettingsPanel, PreviewPanel, etc.)
- app.py: Main AudiobookifyApp class
"""

# Re-export main app and entry point
# Re-export batch processor types for backward compatibility
from ..batch_processor import BookTask, ProcessingStatus
from .app import AudiobookifyApp, main

# Re-export models
from .models import ChapterPreviewState, PreviewChapter, VoicePreviewStatus

# Re-export panels
from .panels import (
    ChapterPreviewItem,
    EPUBFileItem,
    FilePanel,
    JobItem,
    JobsPanel,
    LogPanel,
    PathInput,
    PreviewPanel,
    ProgressPanel,
    QueuePanel,
    SettingsPanel,
)

# Re-export screens
from .screens import DirectoryBrowserScreen, FilteredDirectoryTree, HelpScreen

__all__ = [
    # Main app
    "AudiobookifyApp",
    "main",
    # Models
    "PreviewChapter",
    "ChapterPreviewState",
    "VoicePreviewStatus",
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
    "ProcessingStatus",
    "BookTask",
]
