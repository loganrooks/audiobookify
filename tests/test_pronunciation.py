"""Tests for custom pronunciation functionality."""

import json
import os
import tempfile

import pytest


class TestPronunciationConfig:
    """Tests for PronunciationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from epub2tts_edge.pronunciation import PronunciationConfig

        config = PronunciationConfig()
        assert config.dictionary == {}
        assert config.case_sensitive is False
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from epub2tts_edge.pronunciation import PronunciationConfig

        dictionary = {"Hermione": "Her-my-oh-nee", "Gandalf": "Gan-dalf"}
        config = PronunciationConfig(
            dictionary=dictionary,
            case_sensitive=True,
            enabled=True
        )
        assert config.dictionary == dictionary
        assert config.case_sensitive is True

    def test_disabled_config(self):
        """Test disabled pronunciation config."""
        from epub2tts_edge.pronunciation import PronunciationConfig

        config = PronunciationConfig(enabled=False)
        assert config.enabled is False


class TestPronunciationEntry:
    """Tests for PronunciationEntry dataclass."""

    def test_entry_creation(self):
        """Test basic entry creation."""
        from epub2tts_edge.pronunciation import PronunciationEntry

        entry = PronunciationEntry(
            original="Hermione",
            replacement="Her-my-oh-nee"
        )
        assert entry.original == "Hermione"
        assert entry.replacement == "Her-my-oh-nee"

    def test_entry_with_description(self):
        """Test entry with optional description."""
        from epub2tts_edge.pronunciation import PronunciationEntry

        entry = PronunciationEntry(
            original="Nguyen",
            replacement="Win",
            description="Vietnamese surname"
        )
        assert entry.description == "Vietnamese surname"


class TestPronunciationProcessor:
    """Tests for PronunciationProcessor class."""

    def test_init_default_config(self):
        """Test initializer with default config."""
        from epub2tts_edge.pronunciation import PronunciationProcessor

        processor = PronunciationProcessor()
        assert processor.config.dictionary == {}
        assert processor.config.enabled is True

    def test_init_custom_config(self):
        """Test initializer with custom config."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(
            dictionary={"test": "replacement"},
            case_sensitive=True
        )
        processor = PronunciationProcessor(config)
        assert processor.config.dictionary == {"test": "replacement"}

    def test_process_text_basic_replacement(self):
        """Test basic text replacement."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={"Hermione": "Her-my-oh-nee"})
        processor = PronunciationProcessor(config)

        result = processor.process_text("Hermione cast a spell.")
        assert result == "Her-my-oh-nee cast a spell."

    def test_process_text_multiple_replacements(self):
        """Test multiple replacements in one text."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={
            "Hermione": "Her-my-oh-nee",
            "Voldemort": "Vol-de-mor"
        })
        processor = PronunciationProcessor(config)

        result = processor.process_text("Hermione faced Voldemort.")
        assert result == "Her-my-oh-nee faced Vol-de-mor."

    def test_process_text_case_insensitive(self):
        """Test case-insensitive replacement (default)."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(
            dictionary={"hermione": "Her-my-oh-nee"},
            case_sensitive=False
        )
        processor = PronunciationProcessor(config)

        result = processor.process_text("HERMIONE cast a spell.")
        assert "Her-my-oh-nee" in result

    def test_process_text_case_sensitive(self):
        """Test case-sensitive replacement."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(
            dictionary={"Hermione": "Her-my-oh-nee"},
            case_sensitive=True
        )
        processor = PronunciationProcessor(config)

        # Should NOT replace lowercase version
        result = processor.process_text("hermione cast a spell.")
        assert result == "hermione cast a spell."

        # Should replace exact case
        result2 = processor.process_text("Hermione cast a spell.")
        assert result2 == "Her-my-oh-nee cast a spell."

    def test_process_text_disabled(self):
        """Test that processing is skipped when disabled."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(
            dictionary={"Hermione": "Her-my-oh-nee"},
            enabled=False
        )
        processor = PronunciationProcessor(config)

        result = processor.process_text("Hermione cast a spell.")
        assert result == "Hermione cast a spell."  # Unchanged

    def test_process_text_word_boundaries(self):
        """Test that replacements respect word boundaries."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={"her": "replacement"})
        processor = PronunciationProcessor(config)

        # Should not replace "her" inside "Hermione"
        result = processor.process_text("Hermione told her friend.")
        # "her" as standalone should be replaced, but not inside "Hermione"
        assert "Hermione" in result

    def test_process_text_empty_dictionary(self):
        """Test with empty dictionary."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={})
        processor = PronunciationProcessor(config)

        result = processor.process_text("Some text here.")
        assert result == "Some text here."

    def test_add_entry(self):
        """Test adding entries dynamically."""
        from epub2tts_edge.pronunciation import PronunciationProcessor

        processor = PronunciationProcessor()
        processor.add_entry("Hermione", "Her-my-oh-nee")

        result = processor.process_text("Hermione appeared.")
        assert result == "Her-my-oh-nee appeared."

    def test_remove_entry(self):
        """Test removing entries."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={"Hermione": "Her-my-oh-nee"})
        processor = PronunciationProcessor(config)

        processor.remove_entry("Hermione")
        result = processor.process_text("Hermione appeared.")
        assert result == "Hermione appeared."  # Not replaced


class TestPronunciationDictionary:
    """Tests for dictionary loading and saving."""

    def test_load_from_json_file(self):
        """Test loading dictionary from JSON file."""
        from epub2tts_edge.pronunciation import PronunciationProcessor

        dictionary = {
            "Hermione": "Her-my-oh-nee",
            "Gandalf": "Gan-dalf"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(dictionary, f)
            temp_path = f.name

        try:
            processor = PronunciationProcessor()
            processor.load_dictionary(temp_path)

            assert processor.config.dictionary["Hermione"] == "Her-my-oh-nee"
            assert processor.config.dictionary["Gandalf"] == "Gan-dalf"
        finally:
            os.unlink(temp_path)

    def test_load_from_text_file(self):
        """Test loading dictionary from simple text file."""
        from epub2tts_edge.pronunciation import PronunciationProcessor

        content = """# Comment line
Hermione = Her-my-oh-nee
Gandalf = Gan-dalf
# Another comment
Voldemort = Vol-de-mor
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            processor = PronunciationProcessor()
            processor.load_dictionary(temp_path)

            assert processor.config.dictionary["Hermione"] == "Her-my-oh-nee"
            assert processor.config.dictionary["Gandalf"] == "Gan-dalf"
            assert processor.config.dictionary["Voldemort"] == "Vol-de-mor"
        finally:
            os.unlink(temp_path)

    def test_save_dictionary(self):
        """Test saving dictionary to file."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={
            "Hermione": "Her-my-oh-nee",
            "Gandalf": "Gan-dalf"
        })
        processor = PronunciationProcessor(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            processor.save_dictionary(temp_path)

            with open(temp_path) as f:
                loaded = json.load(f)

            assert loaded["Hermione"] == "Her-my-oh-nee"
            assert loaded["Gandalf"] == "Gan-dalf"
        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        from epub2tts_edge.pronunciation import PronunciationProcessor

        processor = PronunciationProcessor()

        with pytest.raises(FileNotFoundError):
            processor.load_dictionary("/nonexistent/path/dict.json")


class TestPronunciationIntegration:
    """Integration tests for pronunciation processing."""

    def test_process_paragraph(self):
        """Test processing a full paragraph."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={
            "Hermione": "Her-my-oh-nee",
            "Voldemort": "Vol-de-mor",
            "Hogwarts": "Hog-warts"
        })
        processor = PronunciationProcessor(config)

        text = "Hermione studied at Hogwarts while Voldemort plotted his return."
        result = processor.process_text(text)

        assert "Her-my-oh-nee" in result
        assert "Hog-warts" in result
        assert "Vol-de-mor" in result

    def test_get_entry_count(self):
        """Test getting dictionary entry count."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={
            "word1": "replacement1",
            "word2": "replacement2"
        })
        processor = PronunciationProcessor(config)

        assert processor.entry_count == 2

    def test_list_entries(self):
        """Test listing all dictionary entries."""
        from epub2tts_edge.pronunciation import PronunciationConfig, PronunciationProcessor

        config = PronunciationConfig(dictionary={
            "Hermione": "Her-my-oh-nee",
            "Gandalf": "Gan-dalf"
        })
        processor = PronunciationProcessor(config)

        entries = processor.list_entries()
        assert len(entries) == 2
        assert ("Hermione", "Her-my-oh-nee") in entries
