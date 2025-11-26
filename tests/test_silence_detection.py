"""Tests for silence detection and trimming functionality."""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass


class TestSilenceConfig:
    """Tests for SilenceConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from epub2tts_edge.silence_detection import SilenceConfig

        config = SilenceConfig()
        assert config.min_silence_len == 1000  # 1 second default
        assert config.silence_thresh == -40  # -40 dBFS default
        assert config.max_silence_len == 2000  # Max 2 seconds
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from epub2tts_edge.silence_detection import SilenceConfig

        config = SilenceConfig(
            min_silence_len=500,
            silence_thresh=-50,
            max_silence_len=1500,
            enabled=True
        )
        assert config.min_silence_len == 500
        assert config.silence_thresh == -50
        assert config.max_silence_len == 1500
        assert config.enabled is True

    def test_disabled_config(self):
        """Test disabled silence detection."""
        from epub2tts_edge.silence_detection import SilenceConfig

        config = SilenceConfig(enabled=False)
        assert config.enabled is False


class TestSilenceSegment:
    """Tests for SilenceSegment dataclass."""

    def test_silence_segment_creation(self):
        """Test SilenceSegment creation."""
        from epub2tts_edge.silence_detection import SilenceSegment

        segment = SilenceSegment(start_ms=1000, end_ms=3500)
        assert segment.start_ms == 1000
        assert segment.end_ms == 3500
        assert segment.duration_ms == 2500

    def test_silence_segment_duration(self):
        """Test duration property."""
        from epub2tts_edge.silence_detection import SilenceSegment

        segment = SilenceSegment(start_ms=0, end_ms=1000)
        assert segment.duration_ms == 1000

    def test_silence_segment_is_excessive(self):
        """Test is_excessive method."""
        from epub2tts_edge.silence_detection import SilenceSegment

        segment = SilenceSegment(start_ms=0, end_ms=3000)
        assert segment.is_excessive(max_silence=2000) is True
        assert segment.is_excessive(max_silence=4000) is False


class TestSilenceDetector:
    """Tests for SilenceDetector class."""

    def test_init_default_config(self):
        """Test initializer with default config."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        detector = SilenceDetector()
        assert detector.config.min_silence_len == 1000
        assert detector.config.silence_thresh == -40

    def test_init_custom_config(self):
        """Test initializer with custom config."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        config = SilenceConfig(min_silence_len=500, silence_thresh=-50)
        detector = SilenceDetector(config)
        assert detector.config.min_silence_len == 500
        assert detector.config.silence_thresh == -50

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_detect_silence_in_file(self, mock_audio_segment, mock_detect_silence):
        """Test detecting silence segments in a file."""
        from epub2tts_edge.silence_detection import SilenceDetector

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=10000)
        mock_audio_segment.from_file.return_value = mock_audio

        # Mock silence detection - returns list of [start, end] pairs
        mock_detect_silence.return_value = [
            [1000, 2500],  # 1.5s silence
            [5000, 8000],  # 3s silence
        ]

        detector = SilenceDetector()
        segments = detector.detect_silence_in_file("/path/to/audio.flac")

        assert len(segments) == 2
        assert segments[0].start_ms == 1000
        assert segments[0].end_ms == 2500
        assert segments[0].duration_ms == 1500

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_detect_no_silence(self, mock_audio_segment, mock_detect_silence):
        """Test when no silence is detected."""
        from epub2tts_edge.silence_detection import SilenceDetector

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=5000)
        mock_audio_segment.from_file.return_value = mock_audio
        mock_detect_silence.return_value = []

        detector = SilenceDetector()
        segments = detector.detect_silence_in_file("/path/to/audio.flac")

        assert len(segments) == 0

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_trim_silence_basic(self, mock_audio_segment, mock_detect_silence):
        """Test trimming excessive silence."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        # Create a result mock that tracks all operations
        result_audio = MagicMock()

        # Mock audio segment with slice support
        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=10000)
        mock_audio.__getitem__ = Mock(return_value=mock_audio)

        # Mock AudioSegment.empty() to return result_audio
        mock_audio_segment.empty.return_value = result_audio
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio_segment.silent.return_value = mock_audio

        # The result's __iadd__ (+=) returns result_audio
        result_audio.__iadd__ = Mock(return_value=result_audio)

        # 3s silence that should be trimmed to max_silence_len (2s)
        mock_detect_silence.return_value = [[3000, 6000]]

        config = SilenceConfig(max_silence_len=2000)
        detector = SilenceDetector(config)

        with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as f:
            output_path = f.name

        try:
            result = detector.trim_silence("/path/to/input.flac", output_path)
            assert result is not None
            # Verify export was called on the result audio
            result_audio.export.assert_called()
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_trim_silence_disabled(self, mock_audio_segment):
        """Test that silence trimming is skipped when disabled."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        config = SilenceConfig(enabled=False)
        detector = SilenceDetector(config)

        result = detector.trim_silence("/path/to/input.flac", "/path/to/output.flac")
        assert result is None
        mock_audio_segment.from_file.assert_not_called()

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_get_excessive_silence_count(self, mock_audio_segment, mock_detect_silence):
        """Test counting excessive silence segments."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=10000)
        mock_audio_segment.from_file.return_value = mock_audio

        # Mix of normal and excessive silences
        mock_detect_silence.return_value = [
            [0, 1500],    # 1.5s - not excessive
            [3000, 6500], # 3.5s - excessive
            [8000, 9000], # 1s - not excessive
        ]

        config = SilenceConfig(max_silence_len=2000)
        detector = SilenceDetector(config)
        segments = detector.detect_silence_in_file("/path/to/audio.flac")

        excessive = [s for s in segments if s.is_excessive(config.max_silence_len)]
        assert len(excessive) == 1
        assert excessive[0].duration_ms == 3500

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_calculate_total_silence_reduction(self, mock_audio_segment, mock_detect_silence):
        """Test calculating total silence reduction."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=10000)
        mock_audio_segment.from_file.return_value = mock_audio

        # Silences that would be trimmed
        mock_detect_silence.return_value = [
            [0, 3000],    # 3s -> trim 1s (keep 2s max)
            [5000, 9000], # 4s -> trim 2s (keep 2s max)
        ]

        config = SilenceConfig(max_silence_len=2000)
        detector = SilenceDetector(config)
        segments = detector.detect_silence_in_file("/path/to/audio.flac")

        reduction = sum(
            max(0, s.duration_ms - config.max_silence_len)
            for s in segments
        )
        assert reduction == 3000  # 1000 + 2000 = 3s total reduction


class TestSilenceAnalysis:
    """Tests for silence analysis features."""

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_analyze_file_returns_stats(self, mock_audio_segment, mock_detect_silence):
        """Test that analyze returns useful statistics."""
        from epub2tts_edge.silence_detection import SilenceDetector, SilenceConfig

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=60000)  # 60s audio
        mock_audio_segment.from_file.return_value = mock_audio

        mock_detect_silence.return_value = [
            [5000, 8000],   # 3s
            [20000, 22000], # 2s
            [40000, 45000], # 5s
        ]

        config = SilenceConfig(max_silence_len=2000)
        detector = SilenceDetector(config)
        stats = detector.analyze_file("/path/to/audio.flac")

        assert stats['total_duration_ms'] == 60000
        assert stats['silence_count'] == 3
        assert stats['total_silence_ms'] == 10000  # 3+2+5 = 10s
        assert stats['excessive_silence_count'] == 2  # 3s and 5s
        assert stats['potential_reduction_ms'] == 4000  # (3-2) + (5-2) = 4s

    @patch('epub2tts_edge.silence_detection.detect_silence')
    @patch('epub2tts_edge.silence_detection.AudioSegment')
    def test_analyze_multiple_files(self, mock_audio_segment, mock_detect_silence):
        """Test analyzing multiple files."""
        from epub2tts_edge.silence_detection import SilenceDetector

        mock_audio = MagicMock()
        mock_audio.__len__ = Mock(return_value=30000)
        mock_audio_segment.from_file.return_value = mock_audio

        mock_detect_silence.return_value = [[5000, 8000]]

        detector = SilenceDetector()
        stats_list = detector.analyze_files(["/path/to/ch1.flac", "/path/to/ch2.flac"])

        assert len(stats_list) == 2


class TestSilenceIntegration:
    """Integration tests for silence detection in conversion pipeline."""

    def test_config_validation(self):
        """Test configuration validation."""
        from epub2tts_edge.silence_detection import SilenceConfig

        # Valid config
        config = SilenceConfig(min_silence_len=500, silence_thresh=-50, max_silence_len=1500)
        assert config.min_silence_len == 500

        # max_silence should be >= min_silence for sensible behavior
        config2 = SilenceConfig(min_silence_len=1000, max_silence_len=500)
        # This is allowed (user's choice) but may not be useful

    def test_threshold_range(self):
        """Test silence threshold is in valid dBFS range."""
        from epub2tts_edge.silence_detection import SilenceConfig

        # Typical ranges are -60 to -20 dBFS
        config = SilenceConfig(silence_thresh=-40)
        assert -80 <= config.silence_thresh <= 0  # Valid dBFS range
