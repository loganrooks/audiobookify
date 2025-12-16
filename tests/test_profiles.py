"""Tests for the ProcessingProfile system."""

import json

import pytest

from epub2tts_edge.core.profiles import (
    BUILTIN_PROFILES,
    ProcessingProfile,
    ProfileManager,
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


class TestProfileManager:
    """Tests for ProfileManager class."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_singleton_pattern(self, profiles_dir):
        """ProfileManager follows singleton pattern."""
        ProfileManager.reset_instance()
        mgr1 = ProfileManager.get_instance(profiles_dir=profiles_dir)
        mgr2 = ProfileManager.get_instance()
        assert mgr1 is mgr2
        ProfileManager.reset_instance()

    def test_reset_instance(self, profiles_dir):
        """reset_instance clears the singleton."""
        ProfileManager.reset_instance()
        mgr1 = ProfileManager.get_instance(profiles_dir=profiles_dir)
        ProfileManager.reset_instance()
        mgr2 = ProfileManager.get_instance(profiles_dir=profiles_dir)
        assert mgr1 is not mgr2
        ProfileManager.reset_instance()

    def test_name_to_key(self, manager):
        """_name_to_key converts names correctly."""
        assert manager._name_to_key("My Profile") == "my_profile"
        assert manager._name_to_key("Quick Draft") == "quick_draft"
        assert manager._name_to_key("   Spaces   ") == "spaces"
        assert manager._name_to_key("MixedCase") == "mixedcase"

    def test_get_builtin_profile(self, manager):
        """get_profile returns builtin profiles."""
        profile = manager.get_profile("default")
        assert profile is not None
        assert profile.name == "Default"

    def test_get_builtin_names(self, manager):
        """get_builtin_names returns only builtin profile keys."""
        names = manager.get_builtin_names()
        assert "default" in names
        assert "quick_draft" in names
        assert "high_quality" in names

    def test_get_user_profile_names_includes_starter(self, manager):
        """get_user_profile_names returns all profiles including starter profiles."""
        names = manager.get_user_profile_names()
        # Starter profiles are copied on init, so they should all be present
        assert "default" in names
        assert "quick_draft" in names
        assert "high_quality" in names

    def test_is_builtin(self, manager):
        """is_builtin correctly identifies builtin profiles."""
        assert manager.is_builtin("default") is True
        assert manager.is_builtin("Default") is True
        assert manager.is_builtin("nonexistent") is False

    def test_is_user_profile_empty(self, manager):
        """is_user_profile returns False when no user profiles exist."""
        assert manager.is_user_profile("my_custom") is False


class TestProfileManagerSave:
    """Tests for ProfileManager save operations."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_save_profile_creates_file(self, manager, profiles_dir):
        """save_profile creates a JSON file."""
        profile = ProcessingProfile(name="My Custom", description="Test profile")
        key = manager.save_profile(profile)

        assert key == "my_custom"
        assert (profiles_dir / "my_custom.json").exists()

    def test_save_profile_content(self, manager, profiles_dir):
        """save_profile writes correct content."""
        profile = ProcessingProfile(
            name="Test Profile",
            voice="en-US-JennyNeural",
            rate="+10%",
        )
        manager.save_profile(profile)

        with open(profiles_dir / "test_profile.json") as f:
            data = json.load(f)

        assert data["name"] == "Test Profile"
        assert data["voice"] == "en-US-JennyNeural"
        assert data["rate"] == "+10%"
        assert "created_at" in data
        assert "updated_at" in data
        assert "version" in data

    def test_save_profile_prevents_overwrite_by_default(self, manager):
        """save_profile raises FileExistsError without overwrite flag."""
        profile = ProcessingProfile(name="Duplicate")
        manager.save_profile(profile)

        with pytest.raises(FileExistsError):
            manager.save_profile(profile)

    def test_save_profile_with_overwrite(self, manager, profiles_dir):
        """save_profile allows overwrite when flag is True."""
        profile = ProcessingProfile(name="Overwrite Me", rate="+10%")
        manager.save_profile(profile)

        profile2 = ProcessingProfile(name="Overwrite Me", rate="+20%")
        manager.save_profile(profile2, overwrite=True)

        # Verify the new rate
        with open(profiles_dir / "overwrite_me.json") as f:
            data = json.load(f)
        assert data["rate"] == "+20%"

    def test_save_profile_can_overwrite_starter(self, manager, profiles_dir):
        """save_profile can overwrite starter profiles with overwrite=True."""
        # All profiles including starters can be overwritten
        profile = ProcessingProfile(name="Default", rate="+5%")
        manager.save_profile(profile, overwrite=True)

        # Verify the update
        with open(profiles_dir / "default.json") as f:
            data = json.load(f)
        assert data["rate"] == "+5%"

    def test_is_user_profile_after_save(self, manager):
        """is_user_profile returns True after saving."""
        profile = ProcessingProfile(name="Saved Profile")
        manager.save_profile(profile)

        # is_user_profile uses lowercase comparison against stored keys
        assert manager.is_user_profile("saved_profile") is True
        # Keys use underscores, not spaces
        assert manager.is_user_profile("SAVED_PROFILE") is True

    def test_get_user_profile_names_after_save(self, manager):
        """get_user_profile_names includes saved profiles."""
        profile = ProcessingProfile(name="User Created")
        manager.save_profile(profile)

        # Returns keys (lowercase), not display names
        names = manager.get_user_profile_names()
        assert "user_created" in names


class TestProfileManagerDelete:
    """Tests for ProfileManager delete operations."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_delete_profile_removes_file(self, manager, profiles_dir):
        """delete_profile removes the JSON file."""
        profile = ProcessingProfile(name="To Delete")
        manager.save_profile(profile)

        assert (profiles_dir / "to_delete.json").exists()
        manager.delete_profile("to_delete")
        assert not (profiles_dir / "to_delete.json").exists()

    def test_delete_profile_removes_from_cache(self, manager):
        """delete_profile removes from internal cache."""
        profile = ProcessingProfile(name="Cached")
        manager.save_profile(profile)

        assert manager.get_profile("cached") is not None
        manager.delete_profile("cached")
        assert manager.get_profile("cached") is None

    def test_delete_profile_allows_starter(self, manager, profiles_dir):
        """delete_profile can delete starter profiles."""
        # Verify starter profile exists
        assert manager.get_profile("default") is not None
        assert (profiles_dir / "default.json").exists()

        # Delete it
        result = manager.delete_profile("default")
        assert result is True
        assert manager.get_profile("default") is None
        assert not (profiles_dir / "default.json").exists()

    def test_delete_profile_nonexistent(self, manager):
        """delete_profile returns False for unknown profiles."""
        result = manager.delete_profile("nonexistent")
        assert result is False


class TestProfileManagerRename:
    """Tests for ProfileManager rename operations."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_rename_profile_updates_file(self, manager, profiles_dir):
        """rename_profile renames the file."""
        profile = ProcessingProfile(name="Old Name")
        manager.save_profile(profile)

        manager.rename_profile("old_name", "New Name")

        assert not (profiles_dir / "old_name.json").exists()
        assert (profiles_dir / "new_name.json").exists()

    def test_rename_profile_updates_content(self, manager, profiles_dir):
        """rename_profile updates the name inside the file."""
        profile = ProcessingProfile(name="Original")
        manager.save_profile(profile)

        manager.rename_profile("original", "Renamed")

        with open(profiles_dir / "renamed.json") as f:
            data = json.load(f)
        assert data["name"] == "Renamed"

    def test_rename_profile_updates_cache(self, manager):
        """rename_profile updates internal cache."""
        profile = ProcessingProfile(name="Cache Test")
        manager.save_profile(profile)

        manager.rename_profile("cache_test", "Updated Cache")

        assert manager.get_profile("cache_test") is None
        assert manager.get_profile("updated_cache") is not None
        assert manager.get_profile("updated_cache").name == "Updated Cache"

    def test_rename_profile_allows_starter(self, manager, profiles_dir):
        """rename_profile can rename starter profiles."""
        # Verify starter profile exists
        assert manager.get_profile("default") is not None

        # Rename it
        new_key = manager.rename_profile("default", "My Default")
        assert new_key == "my_default"

        # Old name gone, new name exists
        assert manager.get_profile("default") is None
        assert manager.get_profile("my_default") is not None
        assert not (profiles_dir / "default.json").exists()
        assert (profiles_dir / "my_default.json").exists()

    def test_rename_profile_rejects_conflict(self, manager):
        """rename_profile refuses when target exists."""
        profile1 = ProcessingProfile(name="Profile One")
        profile2 = ProcessingProfile(name="Profile Two")
        manager.save_profile(profile1)
        manager.save_profile(profile2)

        with pytest.raises(FileExistsError):
            manager.rename_profile("profile_one", "Profile Two")


class TestProfileManagerExportImport:
    """Tests for ProfileManager export/import operations."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_export_profile_creates_file(self, manager, tmp_path):
        """export_profile creates a JSON file at destination."""
        profile = ProcessingProfile(name="Exportable", rate="+15%")
        manager.save_profile(profile)

        export_path = tmp_path / "exported.json"
        manager.export_profile("exportable", export_path)

        assert export_path.exists()
        with open(export_path) as f:
            data = json.load(f)
        assert data["name"] == "Exportable"
        assert data["rate"] == "+15%"

    def test_export_profile_rejects_nonexistent(self, manager, tmp_path):
        """export_profile returns False for unknown profiles."""
        result = manager.export_profile("nonexistent", tmp_path / "out.json")
        assert result is False

    def test_import_profile_loads_file(self, manager, tmp_path):
        """import_profile loads from external JSON file."""
        # Create an external profile file
        import_path = tmp_path / "external.json"
        data = {
            "name": "Imported Profile",
            "voice": "en-US-GuyNeural",
            "rate": "-5%",
        }
        with open(import_path, "w") as f:
            json.dump(data, f)

        # import_profile returns the ProcessingProfile
        profile = manager.import_profile(import_path)

        assert profile.name == "Imported Profile"
        assert profile.voice == "en-US-GuyNeural"
        assert profile.rate == "-5%"

        # Verify it's now in the manager
        retrieved = manager.get_profile("imported_profile")
        assert retrieved is not None
        assert retrieved.name == "Imported Profile"

    def test_import_profile_rejects_duplicate(self, manager, tmp_path):
        """import_profile raises FileExistsError if profile exists."""
        profile = ProcessingProfile(name="Existing")
        manager.save_profile(profile)

        import_path = tmp_path / "conflict.json"
        with open(import_path, "w") as f:
            json.dump({"name": "Existing"}, f)

        with pytest.raises(FileExistsError):
            manager.import_profile(import_path)


class TestProfileManagerRefresh:
    """Tests for ProfileManager refresh operations."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_refresh_loads_new_files(self, manager, profiles_dir):
        """refresh() picks up externally added files."""
        # Save a profile normally
        profile = ProcessingProfile(name="Normal")
        manager.save_profile(profile)

        # Manually add another profile file
        profiles_dir.mkdir(parents=True, exist_ok=True)
        with open(profiles_dir / "external.json", "w") as f:
            json.dump({"name": "External"}, f)

        # Before refresh, external isn't in cache
        assert manager.get_profile("external") is None

        manager.refresh()

        # After refresh, external is available
        assert manager.get_profile("external") is not None

    def test_refresh_removes_deleted_files(self, manager, profiles_dir):
        """refresh() removes profiles for deleted files."""
        profile = ProcessingProfile(name="To Remove")
        manager.save_profile(profile)

        assert manager.get_profile("to_remove") is not None

        # Manually delete the file
        (profiles_dir / "to_remove.json").unlink()

        manager.refresh()

        assert manager.get_profile("to_remove") is None


class TestProfileManagerDefault:
    """Tests for ProfileManager default profile functionality."""

    @pytest.fixture
    def profiles_dir(self, tmp_path):
        """Create a temporary profiles directory."""
        return tmp_path / "profiles"

    @pytest.fixture
    def manager(self, profiles_dir):
        """Create a ProfileManager with temporary directory."""
        ProfileManager.reset_instance()
        mgr = ProfileManager.get_instance(profiles_dir=profiles_dir)
        yield mgr
        ProfileManager.reset_instance()

    def test_default_profile_starts_as_default(self, manager):
        """get_default_profile returns 'default' initially."""
        assert manager.get_default_profile() == "default"

    def test_is_default_initial(self, manager):
        """is_default returns True for 'default' initially."""
        assert manager.is_default("default") is True
        assert manager.is_default("quick_draft") is False

    def test_set_default_profile(self, manager, profiles_dir):
        """set_default_profile changes the default."""
        result = manager.set_default_profile("quick_draft")
        assert result is True
        assert manager.get_default_profile() == "quick_draft"
        assert manager.is_default("quick_draft") is True
        assert manager.is_default("default") is False

        # Verify saved to disk
        config_file = profiles_dir / "_config.json"
        assert config_file.exists()
        with open(config_file) as f:
            config = json.load(f)
        assert config["default_profile"] == "quick_draft"

    def test_set_default_profile_nonexistent(self, manager):
        """set_default_profile returns False for unknown profile."""
        result = manager.set_default_profile("nonexistent")
        assert result is False
        assert manager.get_default_profile() == "default"

    def test_set_default_profile_case_insensitive(self, manager):
        """set_default_profile is case-insensitive."""
        result = manager.set_default_profile("QUICK_DRAFT")
        assert result is True
        assert manager.get_default_profile() == "quick_draft"

    def test_delete_default_profile_updates_default(self, manager):
        """Deleting the default profile updates default to another profile."""
        # Delete the default profile
        manager.delete_profile("default")

        # Default should be updated to another profile
        new_default = manager.get_default_profile()
        assert new_default != "default"
        assert new_default in manager.get_profile_names()

    def test_default_persists_across_refresh(self, manager, profiles_dir):
        """Default profile setting persists across refresh."""
        manager.set_default_profile("audiobook")
        manager.refresh()
        assert manager.get_default_profile() == "audiobook"

    def test_rename_default_profile_updates_default(self, manager):
        """Renaming the default profile updates the default key."""
        # Make sure default is the default
        assert manager.get_default_profile() == "default"

        # Rename it
        manager.rename_profile("default", "My Default")

        # Default should be updated to new key
        assert manager.get_default_profile() == "my_default"
        assert manager.is_default("my_default") is True
