# Audio generation
from .audio_generator import (
    DEFAULT_CONCURRENT_TASKS,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    add_cover,
    append_silence,
    generate_metadata,
    get_duration,
    make_m4b,
    parallel_edgespeak,
    read_book,
    run_edgespeak,
)

# Audio normalization
from .audio_normalization import (
    AudioNormalizer,
    AudioStats,
    NormalizationConfig,
    validate_method,
)

# Expose batch processing classes for programmatic use
from .batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchResult,
    BookTask,
    ProcessingStatus,
    batch_process,
)

# Expose enhanced chapter detection classes for programmatic use
from .chapter_detector import (
    ChapterDetector,
    ChapterNode,
    DetectionMethod,
    HeadingDetector,
    HierarchyStyle,
    TOCParser,
    detect_chapters,
)

# Chapter selection
from .chapter_selector import (
    ChapterRange,
    ChapterSelector,
    InvalidSelectionError,
    parse_chapter_selection,
)
from .epub2tts_edge import main

# Custom errors
from .errors import (
    AudiobookifyError,
    ChapterDetectionError,
    ConfigurationError,
    DependencyError,
    FFmpegError,
    InvalidFileFormatError,
    ResumeError,
    TTSError,
    format_error_for_user,
)

# Logging utilities
from .logger import (
    enable_debug,
    enable_quiet,
    get_logger,
    set_level,
    setup_logging,
)

# MOBI/AZW parser
from .mobi_parser import (
    MobiBook,
    MobiChapter,
    MobiParseError,
    MobiParser,
    is_azw_file,
    is_kindle_file,
    is_mobi_file,
)

# Multi-voice support
from .multi_voice import (
    DialogueSegment,
    MultiVoiceProcessor,
    VoiceMapping,
)

# Pause/resume
from .pause_resume import (
    STATE_FILE_NAME,
    ConversionState,
    StateManager,
)

# Pronunciation
from .pronunciation import (
    PronunciationConfig,
    PronunciationEntry,
    PronunciationProcessor,
)

# Silence detection
from .silence_detection import (
    SilenceConfig,
    SilenceDetector,
    SilenceSegment,
)
from .tui import AudiobookifyApp

# TUI entry point
from .tui import main as tui_main

# Voice preview
from .voice_preview import (
    AVAILABLE_VOICES,
    DEFAULT_PREVIEW_TEXT,
    VoicePreview,
    VoicePreviewConfig,
    get_voice_by_id,
    get_voices_by_gender,
    get_voices_by_locale,
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
    # MOBI/AZW parser
    'MobiParser',
    'MobiBook',
    'MobiChapter',
    'MobiParseError',
    'is_mobi_file',
    'is_azw_file',
    'is_kindle_file',
    # Logging
    'get_logger',
    'setup_logging',
    'set_level',
    'enable_debug',
    'enable_quiet',
    # Audio generation
    'read_book',
    'make_m4b',
    'add_cover',
    'generate_metadata',
    'run_edgespeak',
    'parallel_edgespeak',
    'get_duration',
    'append_silence',
    'DEFAULT_RETRY_COUNT',
    'DEFAULT_RETRY_DELAY',
    'DEFAULT_CONCURRENT_TASKS',
    # Custom errors
    'AudiobookifyError',
    'TTSError',
    'FFmpegError',
    'ChapterDetectionError',
    'ConfigurationError',
    'DependencyError',
    'ResumeError',
    'InvalidFileFormatError',
    'format_error_for_user',
]
