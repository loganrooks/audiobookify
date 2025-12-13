"""Tests for test mode functionality.

Tests that --test-mode flag enables mock TTS for fast, offline testing.
"""

from pathlib import Path

from epub2tts_edge.audio_generator import (
    disable_test_mode,
    enable_test_mode,
    get_mock_engine,
    is_test_mode,
    run_edgespeak,
)


class TestTestModeToggle:
    """Tests for enabling/disabling test mode."""

    def setup_method(self):
        """Ensure test mode is disabled before each test."""
        disable_test_mode()

    def teardown_method(self):
        """Ensure test mode is disabled after each test."""
        disable_test_mode()

    def test_test_mode_initially_disabled(self):
        """Test mode should be disabled by default."""
        assert is_test_mode() is False
        assert get_mock_engine() is None

    def test_enable_test_mode(self):
        """enable_test_mode should activate mock TTS."""
        enable_test_mode()
        assert is_test_mode() is True
        assert get_mock_engine() is not None

    def test_disable_test_mode(self):
        """disable_test_mode should deactivate mock TTS."""
        enable_test_mode()
        assert is_test_mode() is True

        disable_test_mode()
        assert is_test_mode() is False
        assert get_mock_engine() is None

    def test_enable_test_mode_idempotent(self):
        """Calling enable_test_mode multiple times should be safe."""
        enable_test_mode()
        engine1 = get_mock_engine()

        enable_test_mode()
        engine2 = get_mock_engine()

        # Both should be valid mock engines
        assert engine1 is not None
        assert engine2 is not None


class TestTestModeIntegration:
    """Tests for test mode integration with TTS generation."""

    def setup_method(self):
        """Enable test mode before each test."""
        enable_test_mode()

    def teardown_method(self):
        """Disable test mode after each test."""
        disable_test_mode()

    def test_run_edgespeak_uses_mock_engine(self, tmp_path: Path):
        """run_edgespeak should use mock engine when test mode is enabled."""
        output_file = tmp_path / "test_output.mp3"

        run_edgespeak(
            sentence="Hello, this is a test.",
            speaker="en-US-AndrewNeural",
            filename=str(output_file),
        )

        # File should be created
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Mock engine should record the call
        mock = get_mock_engine()
        assert mock is not None
        assert mock.call_count == 1
        assert mock.calls[0].text == "Hello, this is a test."
        assert mock.calls[0].voice == "en-US-AndrewNeural"

    def test_run_edgespeak_with_rate_and_volume(self, tmp_path: Path):
        """run_edgespeak should pass rate and volume to mock engine."""
        output_file = tmp_path / "test_output.mp3"

        run_edgespeak(
            sentence="Testing rate and volume.",
            speaker="en-US-JennyNeural",
            filename=str(output_file),
            rate="+20%",
            volume="-10%",
        )

        mock = get_mock_engine()
        assert mock.calls[0].rate == "+20%"
        assert mock.calls[0].volume == "-10%"

    def test_multiple_tts_calls_tracked(self, tmp_path: Path):
        """Multiple TTS calls should all be tracked."""
        for i in range(3):
            output_file = tmp_path / f"test_{i}.mp3"
            run_edgespeak(
                sentence=f"Sentence number {i}",
                speaker="en-US-AriaNeural",
                filename=str(output_file),
            )

        mock = get_mock_engine()
        assert mock.call_count == 3
        assert "Sentence number 0" in mock.calls[0].text
        assert "Sentence number 1" in mock.calls[1].text
        assert "Sentence number 2" in mock.calls[2].text

    def test_mock_generates_valid_audio(self, tmp_path: Path):
        """Mock engine should generate valid WAV audio data."""
        output_file = tmp_path / "test_audio.mp3"

        run_edgespeak(
            sentence="Generate valid audio for testing.",
            speaker="en-US-GuyNeural",
            filename=str(output_file),
        )

        # Read the file and check it has WAV header
        with open(output_file, "rb") as f:
            header = f.read(4)
            # WAV files start with "RIFF"
            assert header == b"RIFF", f"Expected WAV header, got: {header}"


class TestTestModeDisabled:
    """Tests to verify behavior when test mode is disabled."""

    def setup_method(self):
        """Ensure test mode is disabled."""
        disable_test_mode()

    def test_is_test_mode_returns_false(self):
        """is_test_mode should return False when disabled."""
        assert is_test_mode() is False

    def test_get_mock_engine_returns_none(self):
        """get_mock_engine should return None when disabled."""
        assert get_mock_engine() is None


class TestMockEngineFeatures:
    """Tests for mock engine specific features."""

    def setup_method(self):
        """Enable test mode."""
        enable_test_mode()

    def teardown_method(self):
        """Disable test mode."""
        disable_test_mode()

    def test_mock_engine_reset(self, tmp_path: Path):
        """Mock engine reset should clear call history."""
        output_file = tmp_path / "test.mp3"

        run_edgespeak("First call", "en-US-AriaNeural", str(output_file))

        mock = get_mock_engine()
        assert mock.call_count == 1

        mock.reset()
        assert mock.call_count == 0
        assert len(mock.calls) == 0

    def test_mock_engine_total_text_length(self, tmp_path: Path):
        """Mock engine should track total text length."""
        for i, text in enumerate(["Short", "A longer sentence here"]):
            output_file = tmp_path / f"test_{i}.mp3"
            run_edgespeak(text, "en-US-AriaNeural", str(output_file))

        mock = get_mock_engine()
        expected_length = len("Short") + len("A longer sentence here")
        assert mock.total_text_length == expected_length

    def test_mock_engine_get_calls_for_voice(self, tmp_path: Path):
        """Mock engine should filter calls by voice."""
        voices = ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-AriaNeural"]

        for i, voice in enumerate(voices):
            output_file = tmp_path / f"test_{i}.mp3"
            run_edgespeak(f"Text {i}", voice, str(output_file))

        mock = get_mock_engine()
        aria_calls = mock.get_calls_for_voice("en-US-AriaNeural")
        guy_calls = mock.get_calls_for_voice("en-US-GuyNeural")

        assert len(aria_calls) == 2
        assert len(guy_calls) == 1
