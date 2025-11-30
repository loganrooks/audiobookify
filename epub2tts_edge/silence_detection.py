"""Silence detection and trimming for audiobook audio.

This module provides functionality to detect and trim excessive silence
in audio files for a better listening experience.
"""

from dataclasses import dataclass
from typing import Any

from pydub import AudioSegment
from pydub.silence import detect_silence


@dataclass
class SilenceConfig:
    """Configuration for silence detection.

    Attributes:
        min_silence_len: Minimum length of silence to detect (ms)
        silence_thresh: Silence threshold in dBFS (e.g., -40)
        max_silence_len: Maximum allowed silence length before trimming (ms)
        enabled: Whether silence detection/trimming is enabled
    """
    min_silence_len: int = 1000  # 1 second
    silence_thresh: int = -40    # dBFS
    max_silence_len: int = 2000  # 2 seconds max
    enabled: bool = True


@dataclass
class SilenceSegment:
    """Represents a detected silence segment.

    Attributes:
        start_ms: Start position in milliseconds
        end_ms: End position in milliseconds
    """
    start_ms: int
    end_ms: int

    @property
    def duration_ms(self) -> int:
        """Duration of the silence segment in milliseconds."""
        return self.end_ms - self.start_ms

    def is_excessive(self, max_silence: int) -> bool:
        """Check if this silence is longer than the maximum allowed.

        Args:
            max_silence: Maximum allowed silence in milliseconds

        Returns:
            True if silence duration exceeds max_silence
        """
        return self.duration_ms > max_silence


class SilenceDetector:
    """Detects and trims silence in audio files.

    This class provides methods to analyze audio files for silence
    and optionally trim excessive pauses.

    Attributes:
        config: SilenceConfig instance with settings
    """

    def __init__(self, config: SilenceConfig | None = None):
        """Initialize the detector.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SilenceConfig()

    def detect_silence_in_file(self, file_path: str) -> list[SilenceSegment]:
        """Detect silence segments in an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            List of SilenceSegment objects
        """
        audio = AudioSegment.from_file(file_path)

        # detect_silence returns list of [start_ms, end_ms] pairs
        silence_ranges = detect_silence(
            audio,
            min_silence_len=self.config.min_silence_len,
            silence_thresh=self.config.silence_thresh
        )

        return [
            SilenceSegment(start_ms=start, end_ms=end)
            for start, end in silence_ranges
        ]

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        """Analyze an audio file for silence statistics.

        Args:
            file_path: Path to the audio file

        Returns:
            Dictionary with silence statistics
        """
        audio = AudioSegment.from_file(file_path)
        total_duration = len(audio)

        segments = self.detect_silence_in_file(file_path)

        total_silence = sum(s.duration_ms for s in segments)
        excessive_segments = [
            s for s in segments
            if s.is_excessive(self.config.max_silence_len)
        ]
        potential_reduction = sum(
            max(0, s.duration_ms - self.config.max_silence_len)
            for s in segments
        )

        return {
            'total_duration_ms': total_duration,
            'silence_count': len(segments),
            'total_silence_ms': total_silence,
            'excessive_silence_count': len(excessive_segments),
            'potential_reduction_ms': potential_reduction,
            'silence_percentage': (total_silence / total_duration * 100) if total_duration > 0 else 0
        }

    def analyze_files(self, file_paths: list[str]) -> list[dict[str, Any]]:
        """Analyze multiple audio files for silence.

        Args:
            file_paths: List of paths to audio files

        Returns:
            List of statistics dictionaries for each file
        """
        return [self.analyze_file(path) for path in file_paths]

    def trim_silence(
        self,
        input_path: str,
        output_path: str
    ) -> str | None:
        """Trim excessive silence from an audio file.

        Reduces silence segments longer than max_silence_len to
        exactly max_silence_len.

        Args:
            input_path: Path to input audio file
            output_path: Path for trimmed output

        Returns:
            Output path if trimming was performed, None if disabled
        """
        if not self.config.enabled:
            return None

        audio = AudioSegment.from_file(input_path)

        # Detect silence segments
        silence_ranges = detect_silence(
            audio,
            min_silence_len=self.config.min_silence_len,
            silence_thresh=self.config.silence_thresh
        )

        if not silence_ranges:
            # No silence to trim, just copy
            audio.export(output_path, format=self._get_format(output_path))
            return output_path

        # Build new audio by trimming excessive silences
        result = AudioSegment.empty()
        last_end = 0

        for start, end in silence_ranges:
            silence_duration = end - start

            # Add audio before this silence
            result += audio[last_end:start]

            # Add silence (trimmed if excessive)
            if silence_duration > self.config.max_silence_len:
                # Trim to max_silence_len
                trimmed_silence = AudioSegment.silent(duration=self.config.max_silence_len)
                result += trimmed_silence
            else:
                # Keep original silence
                result += audio[start:end]

            last_end = end

        # Add remaining audio after last silence
        result += audio[last_end:]

        # Export result
        result.export(output_path, format=self._get_format(output_path))
        return output_path

    def trim_files(
        self,
        input_paths: list[str],
        output_dir: str
    ) -> list[str]:
        """Trim silence from multiple audio files.

        Args:
            input_paths: List of input file paths
            output_dir: Directory for trimmed files

        Returns:
            List of output file paths
        """
        import os

        if not self.config.enabled:
            return input_paths  # Return originals unchanged

        output_paths = []

        for input_path in input_paths:
            filename = os.path.basename(input_path)
            output_path = os.path.join(output_dir, f"trimmed_{filename}")
            self.trim_silence(input_path, output_path)
            output_paths.append(output_path)

        return output_paths

    def _get_format(self, file_path: str) -> str:
        """Get audio format from file extension.

        Args:
            file_path: Path to audio file

        Returns:
            Format string for pydub export
        """
        ext = file_path.rsplit('.', 1)[-1].lower()
        if ext in ('m4a', 'm4b'):
            return 'ipod'
        return ext
