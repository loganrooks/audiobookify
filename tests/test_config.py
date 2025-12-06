"""Tests for centralized configuration module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from epub2tts_edge.config import (
    AppConfig,
    extract_author_lastname,
    generate_job_slug,
    generate_short_id,
    get_config,
    init_config,
    reset_config,
    slugify_title,
)


class TestExtractAuthorLastname:
    """Tests for extract_author_lastname function."""

    def test_simple_name(self):
        assert extract_author_lastname("Jacques Derrida") == "derrida"

    def test_middle_name(self):
        assert extract_author_lastname("Fyodor Mikhailovich Dostoevsky") == "dostoevsky"

    def test_initials(self):
        assert extract_author_lastname("J.R.R. Tolkien") == "tolkien"

    def test_multiple_authors_comma(self):
        assert extract_author_lastname("John Smith, Jane Doe") == "smith"

    def test_multiple_authors_and(self):
        assert extract_author_lastname("John Smith and Jane Doe") == "smith"

    def test_none(self):
        assert extract_author_lastname(None) == "unknown"

    def test_empty_string(self):
        assert extract_author_lastname("") == "unknown"

    def test_single_name(self):
        assert extract_author_lastname("Plato") == "plato"

    def test_special_characters(self):
        # Test that special chars are stripped
        assert extract_author_lastname("Mary O'Brien") == "obrien"


class TestSlugifyTitle:
    """Tests for slugify_title function."""

    def test_simple_title(self):
        assert slugify_title("Writing and Difference") == "writing-and-difference"

    def test_title_with_special_chars(self):
        assert slugify_title("The Brothers Karamazov!") == "the-brothers-karamazov"

    def test_title_with_underscores(self):
        assert slugify_title("Some_Book_Title") == "some-book-title"

    def test_long_title_truncation(self):
        long_title = "A Very Long Title That Goes On And On Forever"
        slug = slugify_title(long_title, max_length=30)
        assert len(slug) <= 30
        # Should truncate at word boundary
        assert not slug.endswith("-")

    def test_none(self):
        assert slugify_title(None) == "untitled"

    def test_empty_string(self):
        assert slugify_title("") == "untitled"

    def test_multiple_spaces(self):
        assert slugify_title("Title   With    Spaces") == "title-with-spaces"

    def test_numeric_title(self):
        assert slugify_title("2001: A Space Odyssey") == "2001-a-space-odyssey"


class TestGenerateShortId:
    """Tests for generate_short_id function."""

    def test_length(self):
        short_id = generate_short_id()
        assert len(short_id) == 6

    def test_alphanumeric(self):
        short_id = generate_short_id()
        assert short_id.isalnum()

    def test_uniqueness(self):
        # Generate multiple IDs and check they're unique
        ids = {generate_short_id() for _ in range(100)}
        # Most should be unique (time-based)
        assert len(ids) > 90


class TestGenerateJobSlug:
    """Tests for generate_job_slug function."""

    def test_default_template(self):
        slug = generate_job_slug("Writing and Difference", "Jacques Derrida")
        # Should match pattern: lastname_title_shortid
        parts = slug.split("_")
        assert len(parts) == 3
        assert parts[0] == "derrida"
        assert parts[1] == "writing-and-difference"
        assert len(parts[2]) == 6

    def test_custom_template(self):
        slug = generate_job_slug(
            "Test Book",
            "John Smith",
            template="{title_slug}_{short_id}",
        )
        parts = slug.split("_")
        assert len(parts) == 2
        assert parts[0] == "test-book"

    def test_missing_author(self):
        slug = generate_job_slug("Test Book", None)
        assert slug.startswith("unknown_")

    def test_missing_title(self):
        slug = generate_job_slug(None, "John Smith")
        assert "_untitled_" in slug


class TestAppConfig:
    """Tests for AppConfig class."""

    def test_platform_default_linux(self):
        with patch("platform.system", return_value="Linux"):
            base = AppConfig.get_platform_default_base()
            assert str(base).endswith(".audiobookify")

    def test_platform_default_macos(self):
        with patch("platform.system", return_value="Darwin"):
            base = AppConfig.get_platform_default_base()
            assert "Application Support" in str(base)
            assert "Audiobookify" in str(base)

    def test_platform_default_windows(self):
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
                base = AppConfig.get_platform_default_base()
                assert "Audiobookify" in str(base)

    def test_load_with_explicit_base_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            assert config.base_dir == Path(tmpdir)

    def test_load_with_env_variable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"AUDIOBOOKIFY_HOME": tmpdir}):
                config = AppConfig.load()
                assert config.base_dir == Path(tmpdir)

    def test_load_from_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_data = {
                "job_slug_template": "{title_slug}_{short_id}",
                "default_voice": "en-GB-RyanNeural",
                "cleanup_audio_on_success": False,
            }
            config_file = Path(tmpdir) / "config.json"
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            config = AppConfig.load(base_dir=tmpdir)
            assert config.job_slug_template == "{title_slug}_{short_id}"
            assert config.default_voice == "en-GB-RyanNeural"
            assert config.cleanup_audio_on_success is False

    def test_save_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            config.default_voice = "custom-voice"
            config.save()

            # Load again and verify
            config2 = AppConfig.load(base_dir=tmpdir)
            assert config2.default_voice == "custom-voice"

    def test_ensure_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            config.ensure_dirs()

            assert config.jobs_dir.exists()
            assert config.cache_dir.exists()

    def test_get_job_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            job_dir = config.get_job_dir("test-slug")
            assert job_dir == config.jobs_dir / "test-slug"

    def test_get_job_audio_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            audio_dir = config.get_job_audio_dir("test-slug")
            assert audio_dir == config.jobs_dir / "test-slug" / "audio"

    def test_get_output_path_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig.load(base_dir=tmpdir)
            output = config.get_output_path("test-slug", "book.m4b")
            assert output == config.jobs_dir / "test-slug" / "book.m4b"

    def test_get_output_path_custom_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "audiobooks"
            config = AppConfig.load(base_dir=tmpdir)
            config.output_dir = output_dir
            output = config.get_output_path("test-slug", "book.m4b")
            assert output == output_dir / "book.m4b"


class TestConfigSingleton:
    """Tests for global config singleton functions."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset config after each test."""
        reset_config()

    def test_get_config_creates_singleton(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"AUDIOBOOKIFY_HOME": tmpdir}):
                config1 = get_config()
                config2 = get_config()
                assert config1 is config2

    def test_init_config_resets_singleton(self):
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                with patch.dict(os.environ, {"AUDIOBOOKIFY_HOME": tmpdir1}):
                    config1 = get_config()
                    assert config1.base_dir == Path(tmpdir1)

                    config2 = init_config(base_dir=tmpdir2)
                    assert config2.base_dir == Path(tmpdir2)

                    # get_config should now return the new config
                    config3 = get_config()
                    assert config3.base_dir == Path(tmpdir2)

    def test_reset_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"AUDIOBOOKIFY_HOME": tmpdir}):
                config1 = get_config()
                reset_config()
                config2 = get_config()
                # Should be new instance (but same values due to same env)
                assert config1 is not config2
