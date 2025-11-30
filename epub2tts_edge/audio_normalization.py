"""Audio normalization for consistent volume across chapters.

This module provides functionality to normalize audio levels across
audiobook chapters for a consistent listening experience.
"""

from dataclasses import dataclass

from pydub import AudioSegment

# Valid normalization methods
VALID_METHODS = ("peak", "rms")


def validate_method(method: str) -> str:
    """Validate normalization method.

    Args:
        method: The method to validate ('peak' or 'rms')

    Returns:
        The validated method string

    Raises:
        ValueError: If method is not valid
    """
    if method not in VALID_METHODS:
        raise ValueError(f"Invalid normalization method '{method}'. Must be one of: {VALID_METHODS}")
    return method


@dataclass
class NormalizationConfig:
    """Configuration for audio normalization.

    Attributes:
        target_dbfs: Target loudness level in dBFS (default -16.0 for audiobooks)
        method: Normalization method ('peak' or 'rms')
        enabled: Whether normalization is enabled
    """
    target_dbfs: float = -16.0
    method: str = "peak"
    enabled: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.method not in VALID_METHODS:
            raise ValueError(f"Invalid method '{self.method}'. Must be one of: {VALID_METHODS}")


@dataclass
class AudioStats:
    """Statistics for an audio file.

    Attributes:
        peak_dbfs: Peak level in dBFS
        rms_dbfs: RMS (average) level in dBFS
        duration_ms: Duration in milliseconds
    """
    peak_dbfs: float
    rms_dbfs: float
    duration_ms: int

    def gain_needed_for_target(self, target_dbfs: float, method: str) -> float:
        """Calculate gain needed to reach target level.

        Args:
            target_dbfs: Target loudness level in dBFS
            method: Normalization method ('peak' or 'rms')

        Returns:
            Gain in dB needed to reach target
        """
        if method == "peak":
            return target_dbfs - self.peak_dbfs
        elif method == "rms":
            return target_dbfs - self.rms_dbfs
        else:
            raise ValueError(f"Invalid method: {method}")


class AudioNormalizer:
    """Normalizes audio files for consistent volume.

    This class provides methods to analyze and normalize audio files
    to achieve consistent volume levels across audiobook chapters.

    Attributes:
        config: NormalizationConfig instance with settings
    """

    def __init__(self, config: NormalizationConfig | None = None):
        """Initialize the normalizer.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or NormalizationConfig()

    def analyze_file(self, file_path: str) -> AudioStats:
        """Analyze an audio file and return its statistics.

        Args:
            file_path: Path to the audio file

        Returns:
            AudioStats with peak, RMS, and duration info
        """
        audio = AudioSegment.from_file(file_path)
        return AudioStats(
            peak_dbfs=audio.max_dBFS,
            rms_dbfs=audio.dBFS,
            duration_ms=len(audio)
        )

    def analyze_files(self, file_paths: list[str]) -> list[AudioStats]:
        """Analyze multiple audio files.

        Args:
            file_paths: List of paths to audio files

        Returns:
            List of AudioStats for each file
        """
        return [self.analyze_file(path) for path in file_paths]

    def calculate_unified_gain(self, stats_list: list[AudioStats]) -> float:
        """Calculate unified gain for consistent volume across all files.

        Uses the loudest file as reference to prevent clipping in any file.

        Args:
            stats_list: List of AudioStats from multiple files

        Returns:
            Gain in dB to apply uniformly to all files
        """
        if not stats_list:
            return 0.0

        if self.config.method == "peak":
            # Find the loudest peak
            max_peak = max(stats.peak_dbfs for stats in stats_list)
            return self.config.target_dbfs - max_peak
        else:  # rms
            # Find the loudest RMS, but also check peaks to prevent clipping
            max_rms = max(stats.rms_dbfs for stats in stats_list)
            max_peak = max(stats.peak_dbfs for stats in stats_list)

            ideal_gain = self.config.target_dbfs - max_rms
            # Ensure we don't clip (peak + gain should not exceed 0 dBFS)
            max_safe_gain = -max_peak  # Headroom available

            return min(ideal_gain, max_safe_gain)

    def normalize_file(
        self,
        input_path: str,
        output_path: str,
        gain_override: float | None = None
    ) -> str | None:
        """Normalize an audio file to target level.

        Args:
            input_path: Path to input audio file
            output_path: Path for normalized output
            gain_override: Optional specific gain to apply (for unified normalization)

        Returns:
            Output path if normalization was performed, None if disabled
        """
        if not self.config.enabled:
            return None

        audio = AudioSegment.from_file(input_path)

        if gain_override is not None:
            gain = gain_override
        else:
            # Calculate gain based on method
            if self.config.method == "peak":
                current_level = audio.max_dBFS
            else:  # rms
                current_level = audio.dBFS

            gain = self.config.target_dbfs - current_level

            # Prevent clipping: ensure peak + gain <= 0 dBFS
            headroom = -audio.max_dBFS
            if gain > headroom:
                gain = headroom

        # Apply gain
        normalized_audio = audio + gain

        # Determine output format from extension
        output_format = output_path.rsplit('.', 1)[-1].lower()
        if output_format == 'flac':
            normalized_audio.export(output_path, format='flac')
        elif output_format == 'm4a' or output_format == 'm4b':
            normalized_audio.export(output_path, format='ipod')
        elif output_format == 'mp3':
            normalized_audio.export(output_path, format='mp3')
        else:
            normalized_audio.export(output_path, format=output_format)

        return output_path

    def normalize_files(
        self,
        input_paths: list[str],
        output_dir: str,
        unified: bool = True
    ) -> list[str]:
        """Normalize multiple audio files.

        Args:
            input_paths: List of input file paths
            output_dir: Directory for normalized files
            unified: If True, use same gain for all files for consistency

        Returns:
            List of output file paths
        """
        import os

        if not self.config.enabled:
            return input_paths  # Return originals unchanged

        output_paths = []

        if unified:
            # Analyze all files first to calculate unified gain
            stats_list = self.analyze_files(input_paths)
            unified_gain = self.calculate_unified_gain(stats_list)

            for input_path in input_paths:
                filename = os.path.basename(input_path)
                output_path = os.path.join(output_dir, f"norm_{filename}")
                self.normalize_file(input_path, output_path, gain_override=unified_gain)
                output_paths.append(output_path)
        else:
            # Normalize each file independently
            for input_path in input_paths:
                filename = os.path.basename(input_path)
                output_path = os.path.join(output_dir, f"norm_{filename}")
                self.normalize_file(input_path, output_path)
                output_paths.append(output_path)

        return output_paths
