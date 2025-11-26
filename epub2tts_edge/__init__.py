from .epub2tts_edge import main

# Expose enhanced chapter detection classes for programmatic use
from .chapter_detector import (
    ChapterDetector,
    ChapterNode,
    TOCParser,
    HeadingDetector,
    DetectionMethod,
    HierarchyStyle,
    detect_chapters
)

# Expose batch processing classes for programmatic use
from .batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchResult,
    BookTask,
    ProcessingStatus,
    batch_process
)

# TUI entry point
from .tui import main as tui_main, AudiobookifyApp

__all__ = [
    # Main entry point
    'main',
    # TUI
    'tui_main',
    'AudiobookifyApp',
    # Chapter detection
    'ChapterDetector',
    'ChapterNode',
    'TOCParser',
    'HeadingDetector',
    'DetectionMethod',
    'HierarchyStyle',
    'detect_chapters',
    # Batch processing
    'BatchProcessor',
    'BatchConfig',
    'BatchResult',
    'BookTask',
    'ProcessingStatus',
    'batch_process',
]