"""Centralized logging configuration for audiobookify.

This module provides a consistent logging setup across all modules.
"""

import logging
import sys
from typing import Optional


# Default format for log messages
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"

# Module-level logger cache
_loggers: dict = {}


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
    simple: bool = True
) -> None:
    """Configure the root logger for audiobookify.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)
        log_file: Path to log file (optional, logs to stderr by default)
        simple: Use simple format without timestamps (default: True)
    """
    if format_string is None:
        format_string = SIMPLE_FORMAT if simple else DEFAULT_FORMAT

    # Configure root logger for epub2tts_edge package
    root_logger = logging.getLogger("epub2tts_edge")
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    if name not in _loggers:
        # Create child logger under epub2tts_edge namespace
        if name.startswith("epub2tts_edge"):
            logger = logging.getLogger(name)
        else:
            logger = logging.getLogger(f"epub2tts_edge.{name}")
        _loggers[name] = logger

    return _loggers[name]


def set_level(level: int) -> None:
    """Set the logging level for all audiobookify loggers.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    root_logger = logging.getLogger("epub2tts_edge")
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def enable_debug() -> None:
    """Enable debug logging."""
    set_level(logging.DEBUG)


def enable_quiet() -> None:
    """Enable quiet mode (only warnings and errors)."""
    set_level(logging.WARNING)
