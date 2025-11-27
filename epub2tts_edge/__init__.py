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

# Voice preview
from .voice_preview import (
    VoicePreview,
    VoicePreviewConfig,
    AVAILABLE_VOICES,
    DEFAULT_PREVIEW_TEXT,
    get_voice_by_id,
    get_voices_by_locale,
    get_voices_by_gender,
)

# Chapter selection
from .chapter_selector import (
    ChapterSelector,
    ChapterRange,
    parse_chapter_selection,
    InvalidSelectionError,
)

# Pause/resume
from .pause_resume import (
    ConversionState,
    StateManager,
    STATE_FILE_NAME,
)

# Audio normalization
from .audio_normalization import (
    AudioNormalizer,
    NormalizationConfig,
    AudioStats,
    validate_method,
)

# Silence detection
from .silence_detection import (
    SilenceDetector,
    SilenceConfig,
    SilenceSegment,
)

# Pronunciation
from .pronunciation import (
    PronunciationProcessor,
    PronunciationConfig,
    PronunciationEntry,
)

# Multi-voice support
from .multi_voice import (
    MultiVoiceProcessor,
    VoiceMapping,
    DialogueSegment,
)

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
    # Voice preview
    'VoicePreview',
    'VoicePreviewConfig',
    'AVAILABLE_VOICES',
    'DEFAULT_PREVIEW_TEXT',
    'get_voice_by_id',
    'get_voices_by_locale',
    'get_voices_by_gender',
    # Chapter selection
    'ChapterSelector',
    'ChapterRange',
    'parse_chapter_selection',
    'InvalidSelectionError',
    # Pause/resume
    'ConversionState',
    'StateManager',
    'STATE_FILE_NAME',
    # Audio normalization
    'AudioNormalizer',
    'NormalizationConfig',
    'AudioStats',
    'validate_method',
    # Silence detection
    'SilenceDetector',
    'SilenceConfig',
    'SilenceSegment',
    # Pronunciation
    'PronunciationProcessor',
    'PronunciationConfig',
    'PronunciationEntry',
    # Multi-voice support
    'MultiVoiceProcessor',
    'VoiceMapping',
    'DialogueSegment',
]