"""Tests for voice preview functionality."""
import os

# Import the module we're testing
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from epub2tts_edge.voice_preview import (
    AVAILABLE_VOICES,
    DEFAULT_PREVIEW_TEXT,
    VoicePreview,
    VoicePreviewConfig,
)


class TestVoicePreviewConfig(unittest.TestCase):
    """Tests for VoicePreviewConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VoicePreviewConfig()
        self.assertEqual(config.speaker, "en-US-AndrewNeural")
        self.assertEqual(config.text, DEFAULT_PREVIEW_TEXT)
        self.assertIsNone(config.rate)
        self.assertIsNone(config.volume)

    def test_custom_config(self):
        """Test custom configuration values."""
        config = VoicePreviewConfig(
            speaker="en-US-JennyNeural",
            text="Custom preview text",
            rate="+20%",
            volume="-10%"
        )
        self.assertEqual(config.speaker, "en-US-JennyNeural")
        self.assertEqual(config.text, "Custom preview text")
        self.assertEqual(config.rate, "+20%")
        self.assertEqual(config.volume, "-10%")


class TestAvailableVoices(unittest.TestCase):
    """Tests for available voices list."""

    def test_voices_list_not_empty(self):
        """Test that voices list is not empty."""
        self.assertGreater(len(AVAILABLE_VOICES), 0)

    def test_default_voice_in_list(self):
        """Test that default voice is in the list."""
        voice_ids = [v["id"] for v in AVAILABLE_VOICES]
        self.assertIn("en-US-AndrewNeural", voice_ids)

    def test_voice_structure(self):
        """Test that each voice has required fields."""
        required_fields = ["id", "name", "gender", "locale"]
        for voice in AVAILABLE_VOICES:
            for field in required_fields:
                self.assertIn(field, voice, f"Voice missing field: {field}")


class TestVoicePreview(unittest.TestCase):
    """Tests for VoicePreview class."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        preview = VoicePreview()
        self.assertEqual(preview.config.speaker, "en-US-AndrewNeural")

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = VoicePreviewConfig(speaker="en-US-JennyNeural")
        preview = VoicePreview(config)
        self.assertEqual(preview.config.speaker, "en-US-JennyNeural")

    def test_set_speaker(self):
        """Test setting speaker."""
        preview = VoicePreview()
        preview.set_speaker("en-US-GuyNeural")
        self.assertEqual(preview.config.speaker, "en-US-GuyNeural")

    def test_set_text(self):
        """Test setting preview text."""
        preview = VoicePreview()
        preview.set_text("Custom text")
        self.assertEqual(preview.config.text, "Custom text")

    def test_set_rate(self):
        """Test setting rate."""
        preview = VoicePreview()
        preview.set_rate("+25%")
        self.assertEqual(preview.config.rate, "+25%")

    def test_set_volume(self):
        """Test setting volume."""
        preview = VoicePreview()
        preview.set_volume("-15%")
        self.assertEqual(preview.config.volume, "-15%")

    @patch('epub2tts_edge.voice_preview.edge_tts')
    def test_generate_preview_creates_file(self, mock_edge_tts):
        """Test that generate_preview creates an audio file."""
        # Setup mock
        mock_communicate = MagicMock()
        mock_communicate.save = AsyncMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        preview = VoicePreview()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "preview.mp3")
            preview.generate_preview(output_path)

            # Verify edge_tts was called correctly
            mock_edge_tts.Communicate.assert_called_once()
            call_args = mock_edge_tts.Communicate.call_args
            self.assertEqual(call_args[0][0], DEFAULT_PREVIEW_TEXT)
            self.assertEqual(call_args[0][1], "en-US-AndrewNeural")

    @patch('epub2tts_edge.voice_preview.edge_tts')
    def test_generate_preview_with_rate_and_volume(self, mock_edge_tts):
        """Test that rate and volume are passed to edge_tts."""
        mock_communicate = MagicMock()
        mock_communicate.save = AsyncMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        config = VoicePreviewConfig(
            speaker="en-US-JennyNeural",
            rate="+20%",
            volume="-10%"
        )
        preview = VoicePreview(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "preview.mp3")
            preview.generate_preview(output_path)

            call_kwargs = mock_edge_tts.Communicate.call_args[1]
            self.assertEqual(call_kwargs.get("rate"), "+20%")
            self.assertEqual(call_kwargs.get("volume"), "-10%")

    @patch('epub2tts_edge.voice_preview.edge_tts')
    def test_generate_preview_to_temp_file(self, mock_edge_tts):
        """Test generate_preview_temp creates a temp file."""
        mock_communicate = MagicMock()
        mock_communicate.save = AsyncMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        preview = VoicePreview()
        result = preview.generate_preview_temp()

        self.assertTrue(result.endswith(".mp3"))
        # Cleanup
        if os.path.exists(result):
            os.remove(result)


class TestVoicePreviewValidation(unittest.TestCase):
    """Tests for input validation."""

    def test_validate_rate_valid(self):
        """Test validation of valid rate values."""
        preview = VoicePreview()
        valid_rates = ["+50%", "-25%", "+0%", "-100%", "+200%"]
        for rate in valid_rates:
            preview.set_rate(rate)
            self.assertEqual(preview.config.rate, rate)

    def test_validate_rate_invalid(self):
        """Test validation of invalid rate values."""
        preview = VoicePreview()
        with self.assertRaises(ValueError):
            preview.set_rate("invalid")
        with self.assertRaises(ValueError):
            preview.set_rate("50")  # Missing +/- and %
        with self.assertRaises(ValueError):
            preview.set_rate("50%")  # Missing +/-

    def test_validate_volume_valid(self):
        """Test validation of valid volume values."""
        preview = VoicePreview()
        valid_volumes = ["+50%", "-25%", "+0%", "-100%"]
        for volume in valid_volumes:
            preview.set_volume(volume)
            self.assertEqual(preview.config.volume, volume)

    def test_validate_volume_invalid(self):
        """Test validation of invalid volume values."""
        preview = VoicePreview()
        with self.assertRaises(ValueError):
            preview.set_volume("invalid")


if __name__ == "__main__":
    unittest.main()
