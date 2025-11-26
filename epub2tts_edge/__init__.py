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

__all__ = [
    'main',
    'ChapterDetector',
    'ChapterNode',
    'TOCParser',
    'HeadingDetector',
    'DetectionMethod',
    'HierarchyStyle',
    'detect_chapters'
]