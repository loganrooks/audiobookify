"""Tests for the OutputNaming system."""

from pathlib import Path

from epub2tts_edge.core.output_naming import (
    NAMING_PRESETS,
    BookMetadata,
    OutputNaming,
    get_naming_preset,
    list_naming_presets,
    sanitize_filename,
)


class TestBookMetadata:
    """Tests for BookMetadata dataclass."""

    def test_create_with_title_only(self):
        """BookMetadata can be created with just title."""
        metadata = BookMetadata(title="My Book")
        assert metadata.title == "My Book"
        assert metadata.author == "Unknown Author"
        assert metadata.year is None
        assert metadata.series is None
        assert metadata.series_index is None
        assert metadata.language == "en"
        assert metadata.publisher is None

    def test_create_with_all_fields(self):
        """BookMetadata can be created with all fields."""
        metadata = BookMetadata(
            title="The Great Book",
            author="Jane Doe",
            year="2024",
            series="Epic Series",
            series_index=3,
            language="en-US",
            publisher="Big Publisher",
        )
        assert metadata.title == "The Great Book"
        assert metadata.author == "Jane Doe"
        assert metadata.year == "2024"
        assert metadata.series == "Epic Series"
        assert metadata.series_index == 3
        assert metadata.language == "en-US"
        assert metadata.publisher == "Big Publisher"

    def test_to_dict(self):
        """BookMetadata can be converted to dictionary."""
        metadata = BookMetadata(
            title="Test Book",
            author="Test Author",
            year="2023",
        )
        data = metadata.to_dict()

        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"
        assert data["year"] == "2023"
        assert data["series"] == ""  # None becomes empty string
        assert data["series_index"] == ""
        assert data["language"] == "en"
        assert data["publisher"] == ""

    def test_to_dict_with_none_values(self):
        """BookMetadata to_dict handles None values."""
        metadata = BookMetadata(title="Minimal")
        data = metadata.to_dict()

        assert data["year"] == "Unknown"  # None becomes "Unknown" for year
        assert data["series"] == ""
        assert data["publisher"] == ""


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_simple_string(self):
        """Simple strings pass through unchanged."""
        assert sanitize_filename("My Book") == "My Book"

    def test_removes_invalid_chars(self):
        """Invalid characters are replaced and spaces collapsed."""
        # Colon replaced with underscore, then underscore+space collapsed to space
        assert sanitize_filename("Book: Subtitle") == "Book Subtitle"
        assert sanitize_filename("Book/Other") == "Book Other"
        # Multiple invalid chars get collapsed
        assert sanitize_filename("Book<>Name") == "Book Name"
        assert sanitize_filename('Book"Name') == "Book Name"

    def test_collapses_multiple_spaces(self):
        """Multiple spaces are collapsed."""
        assert sanitize_filename("Book    Name") == "Book Name"
        assert sanitize_filename("Book___Name") == "Book Name"

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert sanitize_filename("  Book Name  ") == "Book Name"

    def test_strips_dots(self):
        """Leading/trailing dots are stripped."""
        assert sanitize_filename("...Book Name...") == "Book Name"

    def test_empty_string_fallback(self):
        """Empty result falls back to 'audiobook'."""
        assert sanitize_filename("") == "audiobook"
        assert sanitize_filename("   ") == "audiobook"
        assert sanitize_filename("...") == "audiobook"

    def test_custom_replacement(self):
        """Custom replacement character can be used."""
        assert sanitize_filename("Book:Name", replacement="-") == "Book-Name"


class TestOutputNaming:
    """Tests for OutputNaming class."""

    def test_default_template(self):
        """Default template is author - title."""
        naming = OutputNaming()
        metadata = BookMetadata(title="My Book", author="John Smith")
        result = naming.format(metadata)
        assert result == "John Smith - My Book.m4b"

    def test_custom_template(self):
        """Custom template can be specified."""
        naming = OutputNaming("{title} by {author}")
        metadata = BookMetadata(title="The Adventure", author="Jane Doe")
        result = naming.format(metadata)
        assert result == "The Adventure by Jane Doe.m4b"

    def test_title_only_template(self):
        """Title-only template works."""
        naming = OutputNaming("{title}")
        metadata = BookMetadata(title="Simple Title", author="Someone")
        result = naming.format(metadata)
        assert result == "Simple Title.m4b"

    def test_template_with_year(self):
        """Template with year works."""
        naming = OutputNaming("{title} ({year})")
        metadata = BookMetadata(title="Historic Book", author="Historian", year="1999")
        result = naming.format(metadata)
        assert result == "Historic Book (1999).m4b"

    def test_template_with_series(self):
        """Template with series works."""
        naming = OutputNaming("{series} {series_index} - {title}")
        metadata = BookMetadata(
            title="First Adventure",
            author="Writer",
            series="Fantasy Series",
            series_index=1,
        )
        result = naming.format(metadata)
        assert result == "Fantasy Series 1 - First Adventure.m4b"

    def test_custom_extension(self):
        """Custom file extension can be specified."""
        naming = OutputNaming("{title}", extension=".mp3")
        metadata = BookMetadata(title="Audio Book")
        result = naming.format(metadata)
        assert result == "Audio Book.mp3"

    def test_handles_missing_series(self):
        """Missing series is handled gracefully."""
        naming = OutputNaming("{series} - {title}")
        metadata = BookMetadata(title="No Series Book", author="Author")
        result = naming.format(metadata)
        # Should clean up the empty series and dash
        assert "No Series Book" in result
        assert result.endswith(".m4b")

    def test_handles_empty_parentheses(self):
        """Empty parentheses are removed."""
        naming = OutputNaming("{title} ({series})")
        metadata = BookMetadata(title="Book Without Series")
        result = naming.format(metadata)
        assert "()" not in result
        assert result == "Book Without Series.m4b"

    def test_sanitizes_output(self):
        """Output is sanitized for filenames."""
        naming = OutputNaming("{title}")
        metadata = BookMetadata(title="Book: With/Invalid<Chars>")
        result = naming.format(metadata)
        assert ":" not in result
        assert "/" not in result
        assert "<" not in result
        assert ">" not in result

    def test_format_path(self):
        """format_path returns complete path."""
        naming = OutputNaming("{author} - {title}")
        metadata = BookMetadata(title="My Book", author="Author")
        output_dir = Path("/output/audiobooks")
        result = naming.format_path(metadata, output_dir)
        assert result == Path("/output/audiobooks/Author - My Book.m4b")


class TestOutputNamingValidation:
    """Tests for template validation."""

    def test_valid_template(self):
        """Valid template passes validation."""
        naming = OutputNaming("{author} - {title}")
        is_valid, error = naming.validate_template()
        assert is_valid is True
        assert error == ""

    def test_invalid_no_variables(self):
        """Template without variables fails validation."""
        naming = OutputNaming("Just Plain Text")
        is_valid, error = naming.validate_template()
        assert is_valid is False
        assert "variable" in error.lower()

    def test_invalid_unknown_variable(self):
        """Template with unknown variable fails validation."""
        naming = OutputNaming("{title} - {unknown_field}")
        is_valid, error = naming.validate_template()
        assert is_valid is False
        assert "unknown" in error.lower()

    def test_valid_all_variables(self):
        """Template with all valid variables passes."""
        naming = OutputNaming("{title} - {author} ({year}) [{series} {series_index}]")
        is_valid, error = naming.validate_template()
        assert is_valid is True

    def test_get_variable_help(self):
        """get_variable_help returns help text."""
        help_text = OutputNaming.get_variable_help()
        assert "{title}" in help_text
        assert "{author}" in help_text
        assert "{year}" in help_text
        assert "{series}" in help_text


class TestNamingPresets:
    """Tests for naming presets."""

    def test_author_title_preset(self):
        """author_title preset exists and works."""
        preset = get_naming_preset("author_title")
        assert preset is not None
        metadata = BookMetadata(title="Book", author="Author")
        result = preset.format(metadata)
        assert "Author" in result
        assert "Book" in result

    def test_title_only_preset(self):
        """title_only preset exists and works."""
        preset = get_naming_preset("title_only")
        assert preset is not None
        metadata = BookMetadata(title="Just Title", author="Ignored")
        result = preset.format(metadata)
        assert "Just Title" in result
        assert "Ignored" not in result

    def test_title_author_preset(self):
        """title_author preset exists and works."""
        preset = get_naming_preset("title_author")
        assert preset is not None
        metadata = BookMetadata(title="First", author="Second")
        result = preset.format(metadata)
        # Should be "{title} by {author}"
        assert "by" in result.lower() or result.index("First") < result.index("Second")

    def test_series_preset(self):
        """series preset exists and works."""
        preset = get_naming_preset("series")
        assert preset is not None

    def test_year_preset(self):
        """year preset exists and works."""
        preset = get_naming_preset("year")
        assert preset is not None

    def test_full_preset(self):
        """full preset exists and works."""
        preset = get_naming_preset("full")
        assert preset is not None

    def test_get_nonexistent_preset(self):
        """get_naming_preset returns None for unknown preset."""
        preset = get_naming_preset("nonexistent")
        assert preset is None

    def test_list_naming_presets(self):
        """list_naming_presets returns all preset names."""
        presets = list_naming_presets()
        assert "author_title" in presets
        assert "title_only" in presets
        assert "series" in presets
        assert len(presets) == len(NAMING_PRESETS)

    def test_all_presets_produce_valid_filenames(self):
        """All presets produce valid filenames."""
        metadata = BookMetadata(
            title="Test Book: Subtitle",
            author="Test/Author",
            year="2024",
            series="Test<Series>",
            series_index=1,
        )
        for name, preset in NAMING_PRESETS.items():
            result = preset.format(metadata)
            assert result.endswith(".m4b"), f"Preset '{name}' missing extension"
            # Check no invalid characters
            for char in '<>:"/\\|?*':
                assert char not in result, f"Preset '{name}' has invalid char '{char}'"
