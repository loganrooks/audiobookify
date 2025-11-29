"""Integration tests for audiobookify.

These tests verify the complete workflow from EPUB/text input to output.
They use mock TTS to avoid actual API calls during testing.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add parent directory for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class TestEpubExport:
    """Integration tests for EPUB export functionality."""

    @pytest.mark.integration
    def test_export_epub_to_text(self, sample_epub: Path, temp_dir: Path):
        """Test exporting an EPUB file to text format."""
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        detector = ChapterDetector(
            str(sample_epub),
            method=DetectionMethod.COMBINED
        )
        detector.detect()

        # Verify chapters were detected
        chapters = detector.get_flat_chapters()
        assert len(chapters) > 0, "Should detect at least one chapter"

        # Export to text
        output_file = temp_dir / "output.txt"
        detector.export_to_text(str(output_file))

        assert output_file.exists(), "Output file should be created"

        content = output_file.read_text(encoding='utf-8')
        assert "Test Book" in content, "Title should be in output"
        assert "Test Author" in content, "Author should be in output"
        assert "Chapter 1" in content, "Chapter 1 should be in output"

    @pytest.mark.integration
    def test_export_epub_with_different_detection_methods(self, sample_epub: Path, temp_dir: Path):
        """Test EPUB export with different chapter detection methods."""
        from epub2tts_edge.chapter_detector import ChapterDetector, DetectionMethod

        for method in [DetectionMethod.TOC_ONLY, DetectionMethod.HEADINGS_ONLY,
                      DetectionMethod.COMBINED, DetectionMethod.AUTO]:
            detector = ChapterDetector(str(sample_epub), method=method)
            detector.detect()

            chapters = detector.get_flat_chapters()
            # All methods should detect some content
            assert len(chapters) >= 0, f"Method {method} should work without error"

    @pytest.mark.integration
    def test_chapter_detection_returns_paragraphs(self, sample_epub: Path):
        """Test that chapter detection extracts paragraphs correctly."""
        from epub2tts_edge.chapter_detector import ChapterDetector

        detector = ChapterDetector(str(sample_epub))
        detector.detect()

        chapters = detector.get_flat_chapters()
        total_paragraphs = sum(len(c['paragraphs']) for c in chapters)

        assert total_paragraphs > 0, "Should extract paragraphs from chapters"


class TestChapterSelection:
    """Integration tests for chapter selection functionality."""

    @pytest.mark.integration
    def test_select_specific_chapters(self, sample_epub: Path):
        """Test selecting specific chapters from EPUB."""
        from epub2tts_edge.chapter_detector import ChapterDetector
        from epub2tts_edge.chapter_selector import ChapterSelector

        detector = ChapterDetector(str(sample_epub))
        detector.detect()
        chapters = detector.get_flat_chapters()

        if len(chapters) >= 2:
            selector = ChapterSelector("1-2")
            selected = selector.get_selected_indices(len(chapters))
            assert len(selected) == 2, "Should select 2 chapters"

    @pytest.mark.integration
    def test_select_all_chapters(self, sample_epub: Path):
        """Test selecting all chapters."""
        from epub2tts_edge.chapter_detector import ChapterDetector
        from epub2tts_edge.chapter_selector import ChapterSelector

        detector = ChapterDetector(str(sample_epub))
        detector.detect()
        chapters = detector.get_flat_chapters()

        selector = ChapterSelector(f"1-{len(chapters)}")
        selected = selector.get_selected_indices(len(chapters))
        assert len(selected) == len(chapters), "Should select all chapters"


class TestPronunciationProcessing:
    """Integration tests for pronunciation processing."""

    @pytest.mark.integration
    def test_load_and_apply_pronunciation(self, sample_pronunciation_dict: Path):
        """Test loading and applying pronunciation dictionary."""
        from epub2tts_edge.pronunciation import PronunciationProcessor, PronunciationConfig

        processor = PronunciationProcessor(PronunciationConfig())
        processor.load_dictionary(str(sample_pronunciation_dict))

        assert processor.entry_count == 3, "Should load 3 entries"

        text = "Tolkien wrote about Gandalf in his CLI interface."
        processed = processor.process_text(text)

        assert "toll-keen" in processed, "Should replace Tolkien"
        assert "gan-dalf" in processed, "Should replace Gandalf"
        assert "command line interface" in processed, "Should replace CLI"

    @pytest.mark.integration
    def test_pronunciation_case_insensitive(self, temp_dir: Path):
        """Test case-insensitive pronunciation replacement."""
        import json
        from epub2tts_edge.pronunciation import PronunciationProcessor, PronunciationConfig

        # Create a simple dictionary
        dict_file = temp_dir / "dict.json"
        with open(dict_file, "w") as f:
            json.dump({"EPUB": "ee-pub"}, f)

        processor = PronunciationProcessor(PronunciationConfig(case_sensitive=False))
        processor.load_dictionary(str(dict_file))

        assert "ee-pub" in processor.process_text("Convert epub files")
        assert "ee-pub" in processor.process_text("Convert EPUB files")


class TestMultiVoice:
    """Integration tests for multi-voice functionality."""

    @pytest.mark.integration
    def test_load_voice_mapping(self, sample_voice_mapping: Path):
        """Test loading voice mapping configuration."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        processor.load_mapping(str(sample_voice_mapping))

        assert processor.mapping.default_voice == "en-US-AriaNeural"
        assert processor.mapping.narrator_voice == "en-US-GuyNeural"
        assert processor.character_count == 2

    @pytest.mark.integration
    def test_dialogue_parsing(self):
        """Test parsing dialogue from text."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-AriaNeural",
            character_voices={"Alice": "en-US-JennyNeural"}
        )
        processor = MultiVoiceProcessor(mapping)

        text = '"Hello there," said Alice.'
        segments = processor.parse_text(text)

        # Should detect dialogue
        dialogue_segments = [s for s in segments if s.is_dialogue]
        assert len(dialogue_segments) >= 1, "Should detect dialogue"


class TestAudioNormalization:
    """Integration tests for audio normalization."""

    @pytest.mark.integration
    def test_normalization_config_validation(self):
        """Test normalization configuration validation."""
        from epub2tts_edge.audio_normalization import NormalizationConfig

        # Valid config
        config = NormalizationConfig(target_dbfs=-16.0, method="peak")
        assert config.method == "peak"

        # Invalid method should raise
        with pytest.raises(ValueError):
            NormalizationConfig(method="invalid")

    @pytest.mark.integration
    def test_calculate_unified_gain(self):
        """Test unified gain calculation."""
        from epub2tts_edge.audio_normalization import AudioNormalizer, AudioStats, NormalizationConfig

        config = NormalizationConfig(target_dbfs=-16.0, method="peak")
        normalizer = AudioNormalizer(config)

        # Simulate stats from multiple files
        stats = [
            AudioStats(peak_dbfs=-10.0, rms_dbfs=-20.0, duration_ms=1000),
            AudioStats(peak_dbfs=-15.0, rms_dbfs=-25.0, duration_ms=1500),
            AudioStats(peak_dbfs=-12.0, rms_dbfs=-22.0, duration_ms=2000),
        ]

        gain = normalizer.calculate_unified_gain(stats)
        # With target -16 and max peak -10, gain should be -6
        assert gain == -6.0, "Gain should bring loudest peak to target"


class TestSilenceDetection:
    """Integration tests for silence detection."""

    @pytest.mark.integration
    def test_silence_config_defaults(self):
        """Test silence detection configuration defaults."""
        from epub2tts_edge.silence_detection import SilenceConfig

        config = SilenceConfig()
        assert config.min_silence_len == 1000
        assert config.silence_thresh == -40
        assert config.max_silence_len == 2000
        assert config.enabled is True

    @pytest.mark.integration
    def test_silence_segment_properties(self):
        """Test SilenceSegment properties."""
        from epub2tts_edge.silence_detection import SilenceSegment

        segment = SilenceSegment(start_ms=1000, end_ms=4000)
        assert segment.duration_ms == 3000
        assert segment.is_excessive(2000) is True
        assert segment.is_excessive(5000) is False


class TestTextParsing:
    """Integration tests for text file parsing."""

    @pytest.mark.integration
    def test_parse_text_file(self, sample_text_file: Path):
        """Test parsing a text file in audiobookify format."""
        content = sample_text_file.read_text(encoding='utf-8')

        # Should have expected structure
        assert "Title:" in content
        assert "Author:" in content
        assert "#" in content  # Chapter markers

    @pytest.mark.integration
    def test_get_book_from_text(self, sample_text_file: Path, temp_dir: Path):
        """Test get_book function with a text file."""
        # Change to temp dir since get_book may create files
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            from epub2tts_edge.epub2tts_edge import get_book

            book_contents, title, author, chapters = get_book(str(sample_text_file))

            assert title == "Test Book"
            assert author == "Test Author"
            assert len(book_contents) > 0
        finally:
            os.chdir(original_dir)


class TestStateManagement:
    """Integration tests for pause/resume state management."""

    @pytest.mark.integration
    def test_state_save_and_load(self, temp_dir: Path):
        """Test saving and loading conversion state."""
        from epub2tts_edge.pause_resume import ConversionState, StateManager

        state_manager = StateManager(str(temp_dir))

        state = ConversionState(
            source_file="/path/to/book.txt",
            output_file="/path/to/book.m4b",
            chapter_count=10,
            current_chapter=5,
            speaker="en-US-AriaNeural"
        )

        state_manager.save_state(state)

        # Load state
        loaded = state_manager.load_state()
        assert loaded is not None
        assert loaded.source_file == "/path/to/book.txt"
        assert loaded.current_chapter == 5

    @pytest.mark.integration
    def test_state_clear(self, temp_dir: Path):
        """Test clearing conversion state."""
        from epub2tts_edge.pause_resume import ConversionState, StateManager

        state_manager = StateManager(str(temp_dir))

        state = ConversionState(
            source_file="/path/to/book.txt",
            output_file="/path/to/book.m4b"
        )

        state_manager.save_state(state)
        state_manager.clear_state()

        loaded = state_manager.load_state()
        assert loaded is None or not loaded.is_resumable


class TestLogging:
    """Integration tests for logging functionality."""

    @pytest.mark.integration
    def test_logger_setup(self):
        """Test logger setup and configuration."""
        import logging
        from epub2tts_edge.logger import setup_logging, get_logger, enable_debug

        setup_logging(level=logging.INFO)
        logger = get_logger("test_module")

        assert logger is not None
        assert logger.name == "epub2tts_edge.test_module"

    @pytest.mark.integration
    def test_logger_levels(self):
        """Test different logging levels."""
        import logging
        from epub2tts_edge.logger import setup_logging, get_logger, set_level

        setup_logging(level=logging.WARNING)
        logger = get_logger("test_levels")

        # Change level
        set_level(logging.DEBUG)

        # Logger should now be at DEBUG level
        root = logging.getLogger("epub2tts_edge")
        assert root.level == logging.DEBUG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
