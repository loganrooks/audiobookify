"""Tests for audio normalization functionality."""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import will be created after tests
# from epub2tts_edge.audio_normalization import (
#     AudioNormalizer,
#     NormalizationConfig,
#     NormalizationMethod,
#     AudioStats,
# )


class TestNormalizationConfig:
    """Tests for NormalizationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        config = NormalizationConfig()
        assert config.target_dbfs == -16.0  # Standard for audiobooks
        assert config.method == "peak"
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        config = NormalizationConfig(target_dbfs=-14.0, method="rms", enabled=True)
        assert config.target_dbfs == -14.0
        assert config.method == "rms"
        assert config.enabled is True

    def test_disabled_config(self):
        """Test disabled normalization."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        config = NormalizationConfig(enabled=False)
        assert config.enabled is False


class TestAudioStats:
    """Tests for AudioStats dataclass."""

    def test_audio_stats_creation(self):
        """Test AudioStats creation."""
        from epub2tts_edge.audio_normalization import AudioStats

        stats = AudioStats(peak_dbfs=-3.5, rms_dbfs=-18.2, duration_ms=5000)
        assert stats.peak_dbfs == -3.5
        assert stats.rms_dbfs == -18.2
        assert stats.duration_ms == 5000

    def test_audio_stats_gain_calculation(self):
        """Test gain needed calculation."""
        from epub2tts_edge.audio_normalization import AudioStats

        stats = AudioStats(peak_dbfs=-6.0, rms_dbfs=-20.0, duration_ms=1000)
        # To reach -16 dBFS target with peak method: -16 - (-6) = -10 dB
        assert stats.gain_needed_for_target(-16.0, "peak") == -10.0
        # To reach -16 dBFS target with RMS method: -16 - (-20) = 4 dB
        assert stats.gain_needed_for_target(-16.0, "rms") == 4.0


class TestAudioNormalizer:
    """Tests for AudioNormalizer class."""

    def test_init_default_config(self):
        """Test initializer with default config."""
        from epub2tts_edge.audio_normalization import AudioNormalizer

        normalizer = AudioNormalizer()
        assert normalizer.config.target_dbfs == -16.0
        assert normalizer.config.method == "peak"

    def test_init_custom_config(self):
        """Test initializer with custom config."""
        from epub2tts_edge.audio_normalization import AudioNormalizer, NormalizationConfig

        config = NormalizationConfig(target_dbfs=-14.0, method="rms")
        normalizer = AudioNormalizer(config)
        assert normalizer.config.target_dbfs == -14.0
        assert normalizer.config.method == "rms"

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_analyze_audio_file(self, mock_audio_segment):
        """Test analyzing an audio file for stats."""
        from epub2tts_edge.audio_normalization import AudioNormalizer

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.max_dBFS = -6.0
        mock_audio.dBFS = -18.0
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio_segment.from_file.return_value = mock_audio

        normalizer = AudioNormalizer()
        stats = normalizer.analyze_file("/path/to/audio.flac")

        assert stats.peak_dbfs == -6.0
        assert stats.rms_dbfs == -18.0
        assert stats.duration_ms == 5000

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_normalize_file_peak_method(self, mock_audio_segment):
        """Test normalizing a file using peak method."""
        from epub2tts_edge.audio_normalization import AudioNormalizer, NormalizationConfig

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.max_dBFS = -6.0
        mock_audio.dBFS = -18.0
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio_segment.from_file.return_value = mock_audio

        config = NormalizationConfig(target_dbfs=-16.0, method="peak")
        normalizer = AudioNormalizer(config)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            output_path = f.name

        try:
            normalizer.normalize_file("/path/to/input.flac", output_path)
            # Should apply -10 dB gain (target -16, current peak -6)
            mock_audio.__add__.assert_called_once_with(-10.0)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_normalize_file_rms_method(self, mock_audio_segment):
        """Test normalizing a file using RMS method."""
        from epub2tts_edge.audio_normalization import AudioNormalizer, NormalizationConfig

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.max_dBFS = -6.0
        mock_audio.dBFS = -20.0  # RMS level
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio_segment.from_file.return_value = mock_audio

        config = NormalizationConfig(target_dbfs=-16.0, method="rms")
        normalizer = AudioNormalizer(config)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            output_path = f.name

        try:
            normalizer.normalize_file("/path/to/input.flac", output_path)
            # Should apply +4 dB gain (target -16, current RMS -20)
            mock_audio.__add__.assert_called_once_with(4.0)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_normalize_file_disabled(self, mock_audio_segment):
        """Test that normalization is skipped when disabled."""

        from epub2tts_edge.audio_normalization import AudioNormalizer, NormalizationConfig

        config = NormalizationConfig(enabled=False)
        normalizer = AudioNormalizer(config)

        # When disabled, should just copy the file (or return input path)
        result = normalizer.normalize_file("/path/to/input.flac", "/path/to/output.flac")
        assert result is None  # Indicates no normalization performed
        mock_audio_segment.from_file.assert_not_called()

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_normalize_file_clipping_prevention(self, mock_audio_segment):
        """Test that normalization prevents clipping."""
        from epub2tts_edge.audio_normalization import AudioNormalizer, NormalizationConfig

        # Mock audio that would clip if normalized to target
        mock_audio = MagicMock()
        mock_audio.max_dBFS = -2.0  # Very loud
        mock_audio.dBFS = -10.0
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio_segment.from_file.return_value = mock_audio

        # With RMS method targeting -16, would need +6 dB gain
        # But that would push peak to +4 dBFS (clipping!)
        config = NormalizationConfig(target_dbfs=-16.0, method="rms")
        normalizer = AudioNormalizer(config)

        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            output_path = f.name

        try:
            normalizer.normalize_file("/path/to/input.flac", output_path)
            # Should limit gain to prevent clipping (max gain = -peak = 2 dB)
            call_args = mock_audio.__add__.call_args[0][0]
            assert call_args <= 2.0  # Should not exceed headroom
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch("epub2tts_edge.audio_normalization.AudioSegment")
    def test_analyze_multiple_files(self, mock_audio_segment):
        """Test analyzing multiple files for batch normalization."""
        from epub2tts_edge.audio_normalization import AudioNormalizer

        # Mock different audio segments
        mock_audio1 = MagicMock()
        mock_audio1.max_dBFS = -6.0
        mock_audio1.dBFS = -18.0
        mock_audio1.__len__ = Mock(return_value=5000)

        mock_audio2 = MagicMock()
        mock_audio2.max_dBFS = -3.0
        mock_audio2.dBFS = -15.0
        mock_audio2.__len__ = Mock(return_value=3000)

        mock_audio_segment.from_file.side_effect = [mock_audio1, mock_audio2]

        normalizer = AudioNormalizer()
        stats_list = normalizer.analyze_files(["/path/to/ch1.flac", "/path/to/ch2.flac"])

        assert len(stats_list) == 2
        assert stats_list[0].peak_dbfs == -6.0
        assert stats_list[1].peak_dbfs == -3.0

    def test_calculate_unified_gain(self):
        """Test calculating unified gain for consistent volume across chapters."""
        from epub2tts_edge.audio_normalization import (
            AudioNormalizer,
            AudioStats,
            NormalizationConfig,
        )

        config = NormalizationConfig(target_dbfs=-16.0, method="peak")
        normalizer = AudioNormalizer(config)

        stats_list = [
            AudioStats(peak_dbfs=-6.0, rms_dbfs=-18.0, duration_ms=5000),
            AudioStats(peak_dbfs=-3.0, rms_dbfs=-15.0, duration_ms=3000),
            AudioStats(peak_dbfs=-10.0, rms_dbfs=-22.0, duration_ms=4000),
        ]

        # Unified gain should be based on the loudest file to prevent clipping
        # Loudest peak is -3.0, so max safe gain to reach -16 is -13 dB
        unified_gain = normalizer.calculate_unified_gain(stats_list)
        assert unified_gain == -13.0  # -16 - (-3) = -13


class TestNormalizationIntegration:
    """Integration tests for normalization with the conversion pipeline."""

    def test_validate_target_dbfs_range(self):
        """Test that target dBFS is within valid range."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        # Valid ranges for audiobooks are typically -24 to -6 dBFS
        config = NormalizationConfig(target_dbfs=-16.0)
        assert -24.0 <= config.target_dbfs <= -6.0

    def test_validate_method_values(self):
        """Test that method accepts valid values."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        # Should accept peak and rms
        config_peak = NormalizationConfig(method="peak")
        config_rms = NormalizationConfig(method="rms")
        assert config_peak.method == "peak"
        assert config_rms.method == "rms"

    def test_invalid_method_raises_error(self):
        """Test that invalid method raises error."""
        from epub2tts_edge.audio_normalization import validate_method

        with pytest.raises(ValueError):
            validate_method("invalid_method")
