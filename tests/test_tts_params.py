"""Tests for TTS rate and volume parameters."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from epub2tts_edge.batch_processor import BatchConfig


class TestBatchConfigTTSParams(unittest.TestCase):
    """Tests for TTS parameters in BatchConfig."""

    def test_default_tts_params(self):
        """Test default TTS parameters are None."""
        config = BatchConfig(input_path="/test/path")
        self.assertIsNone(config.tts_rate)
        self.assertIsNone(config.tts_volume)

    def test_custom_tts_rate(self):
        """Test setting custom TTS rate."""
        config = BatchConfig(
            input_path="/test/path",
            tts_rate="+20%"
        )
        self.assertEqual(config.tts_rate, "+20%")

    def test_custom_tts_volume(self):
        """Test setting custom TTS volume."""
        config = BatchConfig(
            input_path="/test/path",
            tts_volume="-10%"
        )
        self.assertEqual(config.tts_volume, "-10%")

    def test_tts_params_in_to_dict(self):
        """Test TTS params are included in serialization."""
        config = BatchConfig(
            input_path="/test/path",
            tts_rate="+25%",
            tts_volume="-15%"
        )
        d = config.to_dict()
        self.assertEqual(d["tts_rate"], "+25%")
        self.assertEqual(d["tts_volume"], "-15%")


class TestTTSParamsValidation(unittest.TestCase):
    """Tests for TTS parameter validation."""

    def test_valid_rate_formats(self):
        """Test valid rate format strings."""
        valid_rates = ["+0%", "+10%", "+50%", "+100%", "+200%",
                       "-0%", "-10%", "-50%", "-100%"]
        for rate in valid_rates:
            config = BatchConfig(input_path="/test", tts_rate=rate)
            self.assertEqual(config.tts_rate, rate)

    def test_valid_volume_formats(self):
        """Test valid volume format strings."""
        valid_volumes = ["+0%", "+10%", "+50%", "+100%",
                         "-0%", "-10%", "-50%", "-100%"]
        for volume in valid_volumes:
            config = BatchConfig(input_path="/test", tts_volume=volume)
            self.assertEqual(config.tts_volume, volume)


class TestRunEdgeSpeakParams(unittest.TestCase):
    """Tests for run_edgespeak with rate/volume parameters."""

    @patch('epub2tts_edge.audio_generator.edge_tts')
    @patch('epub2tts_edge.audio_generator.run_save')
    @patch('os.path.getsize', return_value=1000)
    def test_run_edgespeak_with_rate(self, mock_getsize, mock_run_save, mock_edge_tts):
        """Test run_edgespeak passes rate to edge_tts."""
        from epub2tts_edge.audio_generator import run_edgespeak

        mock_communicate = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        run_edgespeak("Hello", "en-US-AndrewNeural", "test.mp3", rate="+20%")

        mock_edge_tts.Communicate.assert_called_once()
        call_kwargs = mock_edge_tts.Communicate.call_args[1]
        self.assertEqual(call_kwargs.get("rate"), "+20%")

    @patch('epub2tts_edge.audio_generator.edge_tts')
    @patch('epub2tts_edge.audio_generator.run_save')
    @patch('os.path.getsize', return_value=1000)
    def test_run_edgespeak_with_volume(self, mock_getsize, mock_run_save, mock_edge_tts):
        """Test run_edgespeak passes volume to edge_tts."""
        from epub2tts_edge.audio_generator import run_edgespeak

        mock_communicate = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        run_edgespeak("Hello", "en-US-AndrewNeural", "test.mp3", volume="-10%")

        mock_edge_tts.Communicate.assert_called_once()
        call_kwargs = mock_edge_tts.Communicate.call_args[1]
        self.assertEqual(call_kwargs.get("volume"), "-10%")

    @patch('epub2tts_edge.audio_generator.edge_tts')
    @patch('epub2tts_edge.audio_generator.run_save')
    @patch('os.path.getsize', return_value=1000)
    def test_run_edgespeak_with_rate_and_volume(self, mock_getsize, mock_run_save, mock_edge_tts):
        """Test run_edgespeak passes both rate and volume."""
        from epub2tts_edge.audio_generator import run_edgespeak

        mock_communicate = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        run_edgespeak("Hello", "en-US-AndrewNeural", "test.mp3",
                      rate="+30%", volume="-20%")

        call_kwargs = mock_edge_tts.Communicate.call_args[1]
        self.assertEqual(call_kwargs.get("rate"), "+30%")
        self.assertEqual(call_kwargs.get("volume"), "-20%")

    @patch('epub2tts_edge.audio_generator.edge_tts')
    @patch('epub2tts_edge.audio_generator.run_save')
    @patch('os.path.getsize', return_value=1000)
    def test_run_edgespeak_without_params(self, mock_getsize, mock_run_save, mock_edge_tts):
        """Test run_edgespeak works without rate/volume."""
        from epub2tts_edge.audio_generator import run_edgespeak

        mock_communicate = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate

        run_edgespeak("Hello", "en-US-AndrewNeural", "test.mp3")

        # Should not pass rate/volume if not provided
        call_kwargs = mock_edge_tts.Communicate.call_args[1]
        self.assertNotIn("rate", call_kwargs)
        self.assertNotIn("volume", call_kwargs)


if __name__ == "__main__":
    unittest.main()
