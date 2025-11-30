"""Custom exceptions and error handling for audiobookify.

This module provides custom exception classes with contextual error messages
and suggestions for resolution.
"""



class AudiobookifyError(Exception):
    """Base exception for audiobookify errors.

    Attributes:
        message: Human-readable error message
        suggestion: Optional suggestion for resolving the error
        context: Optional additional context about the error
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        context: str | None = None
    ):
        self.message = message
        self.suggestion = suggestion
        self.context = context
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the complete error message."""
        parts = [f"Error: {self.message}"]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)


class FileNotFoundError(AudiobookifyError):
    """Raised when a required file is not found."""

    def __init__(self, file_path: str, file_type: str = "file"):
        super().__init__(
            message=f"{file_type.capitalize()} not found: {file_path}",
            suggestion=f"Check that the {file_type} exists and the path is correct.",
            context=f"Looking for {file_type} at: {file_path}"
        )
        self.file_path = file_path


class InvalidFileFormatError(AudiobookifyError):
    """Raised when a file has an invalid or unsupported format."""

    def __init__(
        self,
        file_path: str,
        expected_formats: list[str],
        actual_format: str | None = None
    ):
        format_list = ", ".join(expected_formats)
        message = f"Invalid file format for: {file_path}"
        if actual_format:
            message = f"Invalid file format '{actual_format}' for: {file_path}"

        super().__init__(
            message=message,
            suggestion=f"Supported formats are: {format_list}",
            context=f"File: {file_path}"
        )
        self.file_path = file_path
        self.expected_formats = expected_formats


class TTSError(AudiobookifyError):
    """Raised when text-to-speech generation fails."""

    def __init__(
        self,
        message: str,
        text_sample: str | None = None,
        voice: str | None = None,
        retry_count: int = 0
    ):
        context_parts = []
        if text_sample:
            # Truncate long text
            sample = text_sample[:100] + "..." if len(text_sample) > 100 else text_sample
            context_parts.append(f"Text: '{sample}'")
        if voice:
            context_parts.append(f"Voice: {voice}")
        if retry_count > 0:
            context_parts.append(f"Attempted {retry_count} times")

        super().__init__(
            message=message,
            suggestion="Check your internet connection. If the problem persists, "
                      "try using --retry-count with a higher value or --retry-delay "
                      "with a longer delay.",
            context="; ".join(context_parts) if context_parts else None
        )
        self.text_sample = text_sample
        self.voice = voice
        self.retry_count = retry_count


class FFmpegError(AudiobookifyError):
    """Raised when FFmpeg processing fails."""

    def __init__(self, operation: str, details: str | None = None):
        super().__init__(
            message=f"FFmpeg {operation} failed",
            suggestion="Ensure FFmpeg is installed and accessible in your PATH. "
                      "On Ubuntu: sudo apt install ffmpeg. "
                      "On macOS: brew install ffmpeg. "
                      "On Windows: choco install ffmpeg",
            context=details
        )
        self.operation = operation


class ChapterDetectionError(AudiobookifyError):
    """Raised when chapter detection fails or produces no results."""

    def __init__(
        self,
        file_path: str,
        detection_method: str,
        details: str | None = None
    ):
        super().__init__(
            message=f"No chapters detected in {file_path}",
            suggestion=f"Try a different detection method. Current method: {detection_method}. "
                      "Options are: toc, headings, combined, auto",
            context=details
        )
        self.file_path = file_path
        self.detection_method = detection_method


class ConfigurationError(AudiobookifyError):
    """Raised when there's a configuration or argument error."""

    def __init__(self, message: str, parameter: str | None = None):
        suggestion = "Check your command line arguments or configuration file."
        if parameter:
            suggestion = f"Check the value of '{parameter}' parameter."

        super().__init__(
            message=message,
            suggestion=suggestion,
            context=f"Parameter: {parameter}" if parameter else None
        )
        self.parameter = parameter


class DependencyError(AudiobookifyError):
    """Raised when a required dependency is missing."""

    INSTALL_INSTRUCTIONS = {
        "ffmpeg": "Ubuntu: sudo apt install ffmpeg | macOS: brew install ffmpeg | Windows: choco install ffmpeg",
        "espeak-ng": "Ubuntu: sudo apt install espeak-ng | macOS: brew install espeak | Windows: See espeak website",
        "mobi": "pip install mobi",
        "nltk": "pip install nltk && python -c \"import nltk; nltk.download('punkt')\"",
    }

    def __init__(self, dependency: str, purpose: str | None = None):
        install_hint = self.INSTALL_INSTRUCTIONS.get(
            dependency.lower(),
            f"pip install {dependency}"
        )

        context = None
        if purpose:
            context = f"{dependency} is required for {purpose}"

        super().__init__(
            message=f"Missing dependency: {dependency}",
            suggestion=f"Install with: {install_hint}",
            context=context
        )
        self.dependency = dependency


class ResumeError(AudiobookifyError):
    """Raised when resume operation fails."""

    def __init__(self, message: str, state_file: str | None = None):
        super().__init__(
            message=message,
            suggestion="Use --no-resume to start fresh, or delete the state file manually.",
            context=f"State file: {state_file}" if state_file else None
        )
        self.state_file = state_file


def format_error_for_user(error: Exception) -> str:
    """Format any exception for user-friendly display.

    Args:
        error: The exception to format

    Returns:
        User-friendly error message string
    """
    if isinstance(error, AudiobookifyError):
        return str(error)

    # Handle common exceptions with better messages
    error_type = type(error).__name__
    error_msg = str(error)

    if isinstance(error, FileNotFoundError):
        return f"Error: File not found - {error_msg}\nSuggestion: Check that the file path is correct."

    if isinstance(error, PermissionError):
        return f"Error: Permission denied - {error_msg}\nSuggestion: Check file permissions or run with appropriate privileges."

    if isinstance(error, ConnectionError):
        return f"Error: Network connection failed - {error_msg}\nSuggestion: Check your internet connection and try again."

    if isinstance(error, TimeoutError):
        return f"Error: Operation timed out - {error_msg}\nSuggestion: Check your network connection or try again later."

    # Generic fallback
    return f"Error ({error_type}): {error_msg}"
