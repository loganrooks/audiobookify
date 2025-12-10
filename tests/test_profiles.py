"""Tests for the ProcessingProfile system."""

from epub2tts_edge.core.profiles import (
    BUILTIN_PROFILES,
    ProcessingProfile,
    get_profile,
    get_profile_names,
    list_profiles,
)


class TestProcessingProfile:
    """Tests for ProcessingProfile dataclass."""

    def test_create_profile_with_defaults(self):
        """Profile can be created with just a name."""
        profile = ProcessingProfile(name="Test")
        assert profile.name == "Test"
        assert profile.voice == "en-US-AndrewNeural"
        assert profile.rate is None
        assert profile.volume is None
        assert profile.paragraph_pause == 1200
        assert profile.sentence_pause == 1200
        assert profile.normalize_audio is False
        assert profile.trim_silence is False
        assert profile.detection_method == "combined"
        assert profile.hierarchy_style == "flat"

    def test_create_profile_with_all_options(self):
        """Profile can be created with all options specified."""
        profile = ProcessingProfile(
            name="Custom",
            description="A custom profile",
            voice="en-US-JennyNeural",
            rate="+15%",
            volume="-5%",
            paragraph_pause=1500,
            sentence_pause=1000,
            normalize_audio=True,
            trim_silence=True,
            detection_method="toc",
            hierarchy_style="numbered",
        )
        assert profile.name == "Custom"
        assert profile.description == "A custom profile"
        assert profile.voice == "en-US-JennyNeural"
        assert profile.rate == "+15%"
        assert profile.volume == "-5%"
        assert profile.paragraph_pause == 1500
        assert profile.sentence_pause == 1000
        assert profile.normalize_audio is True
        assert profile.trim_silence is True
        assert profile.detection_method == "toc"
        assert profile.hierarchy_style == "numbered"

    def test_to_dict(self):
        """Profile can be converted to dictionary."""
        profile = ProcessingProfile(
            name="Test",
            description="Test profile",
            voice="en-US-GuyNeural",
            rate="+10%",
        )
        data = profile.to_dict()

        assert data["name"] == "Test"
        assert data["description"] == "Test profile"
        assert data["voice"] == "en-US-GuyNeural"
        assert data["rate"] == "+10%"
        assert data["volume"] is None
        assert data["paragraph_pause"] == 1200
        assert data["sentence_pause"] == 1200

    def test_from_dict(self):
        """Profile can be created from dictionary."""
        data = {
            "name": "FromDict",
            "description": "Created from dict",
            "voice": "en-US-AriaNeural",
            "rate": "-10%",
            "volume": "+5%",
            "paragraph_pause": 1800,
            "sentence_pause": 1400,
            "normalize_audio": True,
            "trim_silence": True,
            "detection_method": "headings",
            "hierarchy_style": "arrow",
        }
        profile = ProcessingProfile.from_dict(data)

        assert profile.name == "FromDict"
        assert profile.description == "Created from dict"
        assert profile.voice == "en-US-AriaNeural"
        assert profile.rate == "-10%"
        assert profile.volume == "+5%"
        assert profile.paragraph_pause == 1800
        assert profile.sentence_pause == 1400
        assert profile.normalize_audio is True
        assert profile.trim_silence is True
        assert profile.detection_method == "headings"
        assert profile.hierarchy_style == "arrow"

    def test_from_dict_with_missing_fields(self):
        """Profile from_dict uses defaults for missing fields."""
        data = {"name": "Minimal"}
        profile = ProcessingProfile.from_dict(data)

        assert profile.name == "Minimal"
        assert profile.voice == "en-US-AndrewNeural"
        assert profile.rate is None
        assert profile.paragraph_pause == 1200

    def test_from_dict_with_empty_dict(self):
        """Profile from_dict handles empty dict."""
        profile = ProcessingProfile.from_dict({})
        assert profile.name == "Custom"
        assert profile.voice == "en-US-AndrewNeural"

    def test_roundtrip_to_dict_from_dict(self):
        """Profile survives roundtrip through dict."""
        original = ProcessingProfile(
            name="Roundtrip",
            description="Test roundtrip",
            voice="en-US-JennyNeural",
            rate="+20%",
            volume="-10%",
            paragraph_pause=2000,
            sentence_pause=1600,
            normalize_audio=True,
            trim_silence=True,
            detection_method="auto",
            hierarchy_style="breadcrumb",
        )
        data = original.to_dict()
        restored = ProcessingProfile.from_dict(data)

        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.voice == original.voice
        assert restored.rate == original.rate
        assert restored.volume == original.volume
        assert restored.paragraph_pause == original.paragraph_pause
        assert restored.sentence_pause == original.sentence_pause
        assert restored.normalize_audio == original.normalize_audio
        assert restored.trim_silence == original.trim_silence
        assert restored.detection_method == original.detection_method
        assert restored.hierarchy_style == original.hierarchy_style


class TestBuiltinProfiles:
    """Tests for built-in profiles."""

    def test_default_profile_exists(self):
        """Default profile is available."""
        assert "default" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["default"]
        assert profile.name == "Default"
        assert profile.voice == "en-US-AndrewNeural"
        assert profile.normalize_audio is False

    def test_quick_draft_profile_exists(self):
        """Quick draft profile is available."""
        assert "quick_draft" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["quick_draft"]
        assert profile.name == "Quick Draft"
        assert profile.rate == "+20%"
        assert profile.trim_silence is True

    def test_high_quality_profile_exists(self):
        """High quality profile is available."""
        assert "high_quality" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["high_quality"]
        assert profile.name == "High Quality"
        assert profile.rate == "-10%"
        assert profile.normalize_audio is True
        assert profile.trim_silence is True

    def test_audiobook_profile_exists(self):
        """Audiobook profile is available."""
        assert "audiobook" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["audiobook"]
        assert profile.name == "Audiobook"
        assert profile.normalize_audio is True

    def test_accessibility_profile_exists(self):
        """Accessibility profile is available."""
        assert "accessibility" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["accessibility"]
        assert profile.name == "Accessibility"
        assert profile.rate == "-20%"
        assert profile.volume == "+10%"
        assert profile.normalize_audio is True

    def test_all_profiles_have_descriptions(self):
        """All built-in profiles have descriptions."""
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.description, f"Profile '{name}' missing description"

    def test_all_profiles_have_valid_voices(self):
        """All built-in profiles have valid voice identifiers."""
        for name, profile in BUILTIN_PROFILES.items():
            assert profile.voice.startswith("en-"), f"Profile '{name}' has non-English voice"
            assert "Neural" in profile.voice, f"Profile '{name}' should use Neural voice"


class TestProfileHelpers:
    """Tests for profile helper functions."""

    def test_get_profile_by_name(self):
        """get_profile returns profile by name."""
        profile = get_profile("default")
        assert profile is not None
        assert profile.name == "Default"

    def test_get_profile_case_insensitive(self):
        """get_profile is case-insensitive."""
        # All case variations should return the same profile
        profile1 = get_profile("DEFAULT")
        profile2 = get_profile("Default")
        profile3 = get_profile("default")

        assert profile1 is not None
        assert profile2 is not None
        assert profile3 is not None
        assert profile1.name == "Default"
        assert profile2.name == "Default"
        assert profile3.name == "Default"

    def test_get_profile_nonexistent(self):
        """get_profile returns None for unknown profiles."""
        profile = get_profile("nonexistent")
        assert profile is None

    def test_list_profiles_returns_all(self):
        """list_profiles returns all built-in profiles."""
        profiles = list_profiles()
        assert len(profiles) == len(BUILTIN_PROFILES)
        assert all(isinstance(p, ProcessingProfile) for p in profiles)

    def test_get_profile_names(self):
        """get_profile_names returns all profile keys."""
        names = get_profile_names()
        assert "default" in names
        assert "quick_draft" in names
        assert "high_quality" in names
        assert "audiobook" in names
        assert "accessibility" in names
        assert len(names) == len(BUILTIN_PROFILES)
