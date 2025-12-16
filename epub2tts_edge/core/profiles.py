"""Processing profiles for audiobook conversion.

This module provides predefined configuration profiles that users can select
instead of manually configuring each setting. Each profile represents a
different use case (quick draft, high quality, etc.).

User profiles are stored as JSON files in the profiles directory:
- Linux: ~/.audiobookify/profiles/
- macOS: ~/Library/Application Support/Audiobookify/profiles/
- Windows: %APPDATA%/Audiobookify/profiles/
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class ProcessingProfile:
    """A named configuration profile for audiobook conversion.

    Profiles bundle related settings together for common use cases,
    making it easier for users to get started without understanding
    every option.

    Attributes:
        name: Display name for the profile
        description: Brief description of when to use this profile
        voice: Edge TTS voice identifier
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+10%", "-5%")
        paragraph_pause: Pause between paragraphs in milliseconds
        sentence_pause: Pause between sentences in milliseconds
        normalize_audio: Whether to normalize audio levels
        trim_silence: Whether to trim excessive silence
        detection_method: Chapter detection method
        hierarchy_style: Chapter title hierarchy style
    """

    name: str
    description: str = ""
    voice: str = "en-US-AndrewNeural"
    rate: str | None = None
    volume: str | None = None
    paragraph_pause: int = 1200
    sentence_pause: int = 1200
    normalize_audio: bool = False
    trim_silence: bool = False
    detection_method: str = "combined"
    hierarchy_style: str = "flat"

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "paragraph_pause": self.paragraph_pause,
            "sentence_pause": self.sentence_pause,
            "normalize_audio": self.normalize_audio,
            "trim_silence": self.trim_silence,
            "detection_method": self.detection_method,
            "hierarchy_style": self.hierarchy_style,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessingProfile:
        """Create profile from dictionary."""
        return cls(
            name=data.get("name", "Custom"),
            description=data.get("description", ""),
            voice=data.get("voice", "en-US-AndrewNeural"),
            rate=data.get("rate"),
            volume=data.get("volume"),
            paragraph_pause=data.get("paragraph_pause", 1200),
            sentence_pause=data.get("sentence_pause", 1200),
            normalize_audio=data.get("normalize_audio", False),
            trim_silence=data.get("trim_silence", False),
            detection_method=data.get("detection_method", "combined"),
            hierarchy_style=data.get("hierarchy_style", "flat"),
        )


# Built-in profiles for common use cases
BUILTIN_PROFILES: dict[str, ProcessingProfile] = {
    "default": ProcessingProfile(
        name="Default",
        description="Balanced settings for everyday listening",
        voice="en-US-AndrewNeural",
        rate=None,
        volume=None,
        paragraph_pause=1200,
        sentence_pause=1200,
        normalize_audio=False,
        trim_silence=False,
        detection_method="combined",
        hierarchy_style="flat",
    ),
    "quick_draft": ProcessingProfile(
        name="Quick Draft",
        description="Fast preview with faster speech rate",
        voice="en-US-GuyNeural",
        rate="+20%",
        volume=None,
        paragraph_pause=800,
        sentence_pause=600,
        normalize_audio=False,
        trim_silence=True,
        detection_method="toc",
        hierarchy_style="flat",
    ),
    "high_quality": ProcessingProfile(
        name="High Quality",
        description="Best quality with normalization and slower pace",
        voice="en-US-AndrewNeural",
        rate="-10%",
        volume=None,
        paragraph_pause=1500,
        sentence_pause=1400,
        normalize_audio=True,
        trim_silence=True,
        detection_method="combined",
        hierarchy_style="numbered",
    ),
    "audiobook": ProcessingProfile(
        name="Audiobook",
        description="Optimized for long-form listening",
        voice="en-US-AndrewNeural",
        rate="-5%",
        volume=None,
        paragraph_pause=1400,
        sentence_pause=1200,
        normalize_audio=True,
        trim_silence=False,
        detection_method="combined",
        hierarchy_style="flat",
    ),
    "accessibility": ProcessingProfile(
        name="Accessibility",
        description="Slower pace with clear articulation",
        voice="en-US-JennyNeural",
        rate="-20%",
        volume="+10%",
        paragraph_pause=2000,
        sentence_pause=1800,
        normalize_audio=True,
        trim_silence=False,
        detection_method="combined",
        hierarchy_style="numbered",
    ),
}


class ProfileManager:
    """Manages built-in and user-defined processing profiles.

    User profiles are stored as JSON files in the profiles directory.
    Profile files use the naming convention: {profile_key}.json
    where profile_key is the normalized name (lowercase, underscores).
    """

    _instance: ClassVar[ProfileManager | None] = None
    _user_profiles: dict[str, ProcessingProfile]
    _profiles_dir: Path | None

    def __init__(self, profiles_dir: Path | None = None) -> None:
        """Initialize the profile manager.

        Args:
            profiles_dir: Custom profiles directory. If None, uses AppConfig.
        """
        self._profiles_dir = profiles_dir
        self._user_profiles = {}
        self._load_user_profiles()

    @classmethod
    def get_instance(cls, profiles_dir: Path | None = None) -> ProfileManager:
        """Get the singleton ProfileManager instance.

        Args:
            profiles_dir: Optional custom profiles directory (only used on first call)

        Returns:
            The singleton ProfileManager instance
        """
        if cls._instance is None:
            cls._instance = cls(profiles_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def _get_profiles_dir(self) -> Path:
        """Get the profiles directory path."""
        if self._profiles_dir is not None:
            return self._profiles_dir

        # Lazy import to avoid circular dependency
        from epub2tts_edge.config import get_config

        return get_config().profiles_dir

    def _ensure_profiles_dir(self) -> None:
        """Ensure the profiles directory exists."""
        profiles_dir = self._get_profiles_dir()
        profiles_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _name_to_key(name: str) -> str:
        """Convert profile display name to storage key.

        Example: "My Custom Profile" -> "my_custom_profile"
        """
        # Lowercase, replace spaces with underscores
        key = name.lower().strip()
        key = re.sub(r"\s+", "_", key)
        # Remove non-alphanumeric except underscores
        key = re.sub(r"[^a-z0-9_]", "", key)
        # Collapse multiple underscores
        key = re.sub(r"_+", "_", key)
        return key.strip("_") or "custom"

    def _key_to_filename(self, key: str) -> str:
        """Convert profile key to filename."""
        return f"{key}.json"

    def _load_user_profiles(self) -> None:
        """Load all user profiles from disk."""
        self._user_profiles = {}
        profiles_dir = self._get_profiles_dir()

        if not profiles_dir.exists():
            return

        for profile_file in profiles_dir.glob("*.json"):
            try:
                with open(profile_file) as f:
                    data = json.load(f)
                profile = ProcessingProfile.from_dict(data)
                key = profile_file.stem  # Use filename without extension as key
                self._user_profiles[key] = profile
            except (json.JSONDecodeError, OSError, KeyError):
                # Skip malformed profile files
                continue

    def refresh(self) -> None:
        """Reload user profiles from disk (cache invalidation)."""
        self._load_user_profiles()

    def get_profile(self, name: str) -> ProcessingProfile | None:
        """Get a profile by name (builtin or user).

        Builtin profiles are checked first, then user profiles.

        Args:
            name: Profile name or key (case-insensitive)

        Returns:
            The profile if found, None otherwise
        """
        key = name.lower()

        # Check builtins first
        if key in BUILTIN_PROFILES:
            return BUILTIN_PROFILES[key]

        # Check user profiles
        return self._user_profiles.get(key)

    def list_profiles(self) -> list[ProcessingProfile]:
        """Get all available profiles (builtin + user).

        Returns:
            List of all profiles, builtins first
        """
        profiles = list(BUILTIN_PROFILES.values())
        profiles.extend(self._user_profiles.values())
        return profiles

    def get_profile_names(self) -> list[str]:
        """Get names of all profiles (builtin keys + user keys).

        Returns:
            List of profile keys
        """
        names = list(BUILTIN_PROFILES.keys())
        names.extend(self._user_profiles.keys())
        return names

    def get_builtin_names(self) -> list[str]:
        """Get names of builtin profiles only.

        Returns:
            List of builtin profile keys
        """
        return list(BUILTIN_PROFILES.keys())

    def get_user_profile_names(self) -> list[str]:
        """Get names of user profiles only.

        Returns:
            List of user profile keys
        """
        return list(self._user_profiles.keys())

    def is_builtin(self, name: str) -> bool:
        """Check if a profile is a built-in profile.

        Args:
            name: Profile name or key

        Returns:
            True if builtin, False otherwise
        """
        return name.lower() in BUILTIN_PROFILES

    def is_user_profile(self, name: str) -> bool:
        """Check if a profile is a user-defined profile.

        Args:
            name: Profile name or key

        Returns:
            True if user profile, False otherwise
        """
        return name.lower() in self._user_profiles

    def save_profile(
        self,
        profile: ProcessingProfile,
        overwrite: bool = False,
    ) -> str:
        """Save a user profile to disk.

        Args:
            profile: The profile to save
            overwrite: If True, allow overwriting existing user profiles.
                       Never overwrites built-in profiles.

        Returns:
            The profile key used for storage

        Raises:
            ValueError: If attempting to overwrite a built-in profile
            FileExistsError: If profile exists and overwrite=False
        """
        key = self._name_to_key(profile.name)

        # Never overwrite builtins
        if self.is_builtin(key):
            raise ValueError(f"Cannot overwrite built-in profile: {key}")

        # Check for existing user profile
        if not overwrite and key in self._user_profiles:
            raise FileExistsError(f"Profile already exists: {profile.name}")

        self._ensure_profiles_dir()

        # Add metadata for user profiles
        data = profile.to_dict()
        now = datetime.now(UTC).isoformat()
        if key not in self._user_profiles:
            data["created_at"] = now
        data["updated_at"] = now
        data["version"] = 1

        profile_file = self._get_profiles_dir() / self._key_to_filename(key)
        with open(profile_file, "w") as f:
            json.dump(data, f, indent=2)

        # Update cache
        self._user_profiles[key] = profile

        return key

    def delete_profile(self, name: str) -> bool:
        """Delete a user profile.

        Args:
            name: Profile name or key to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If attempting to delete a built-in profile
        """
        key = name.lower()

        if self.is_builtin(key):
            raise ValueError(f"Cannot delete built-in profile: {key}")

        if key not in self._user_profiles:
            return False

        profile_file = self._get_profiles_dir() / self._key_to_filename(key)
        try:
            profile_file.unlink()
        except OSError:
            pass

        del self._user_profiles[key]
        return True

    def rename_profile(self, old_name: str, new_name: str) -> str:
        """Rename a user profile.

        Args:
            old_name: Current profile name or key
            new_name: New display name for the profile

        Returns:
            The new profile key

        Raises:
            ValueError: If old_name is builtin or doesn't exist
            FileExistsError: If new_name conflicts with existing profile
        """
        old_key = old_name.lower()
        new_key = self._name_to_key(new_name)

        if self.is_builtin(old_key):
            raise ValueError(f"Cannot rename built-in profile: {old_key}")

        if old_key not in self._user_profiles:
            raise ValueError(f"Profile not found: {old_key}")

        if self.is_builtin(new_key) or (new_key in self._user_profiles and new_key != old_key):
            raise FileExistsError(f"Profile name already exists: {new_name}")

        # Get existing profile and update name
        profile = self._user_profiles[old_key]
        updated_profile = ProcessingProfile(
            name=new_name,
            description=profile.description,
            voice=profile.voice,
            rate=profile.rate,
            volume=profile.volume,
            paragraph_pause=profile.paragraph_pause,
            sentence_pause=profile.sentence_pause,
            normalize_audio=profile.normalize_audio,
            trim_silence=profile.trim_silence,
            detection_method=profile.detection_method,
            hierarchy_style=profile.hierarchy_style,
        )

        # Delete old file
        old_file = self._get_profiles_dir() / self._key_to_filename(old_key)
        try:
            old_file.unlink()
        except OSError:
            pass
        del self._user_profiles[old_key]

        # Save with new name
        return self.save_profile(updated_profile)

    def export_profile(self, name: str, path: Path) -> bool:
        """Export a profile to a specific path.

        Args:
            name: Profile name or key
            path: Destination path for the JSON file

        Returns:
            True if exported successfully
        """
        profile = self.get_profile(name)
        if not profile:
            return False

        data = profile.to_dict()
        data["exported_at"] = datetime.now(UTC).isoformat()

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return True

    def import_profile(self, path: Path, new_name: str | None = None) -> ProcessingProfile:
        """Import a profile from a JSON file.

        Args:
            path: Path to the profile JSON file
            new_name: Optional new name for the imported profile

        Returns:
            The imported profile

        Raises:
            FileNotFoundError: If path doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(path) as f:
            data = json.load(f)

        profile = ProcessingProfile.from_dict(data)
        if new_name:
            profile = ProcessingProfile(
                name=new_name,
                description=profile.description,
                voice=profile.voice,
                rate=profile.rate,
                volume=profile.volume,
                paragraph_pause=profile.paragraph_pause,
                sentence_pause=profile.sentence_pause,
                normalize_audio=profile.normalize_audio,
                trim_silence=profile.trim_silence,
                detection_method=profile.detection_method,
                hierarchy_style=profile.hierarchy_style,
            )

        self.save_profile(profile)
        return profile


def get_profile(name: str) -> ProcessingProfile | None:
    """Get a profile by name (builtin or user).

    This function provides backward compatibility.
    For full profile management, use ProfileManager.get_instance().

    Args:
        name: Profile name (case-insensitive)

    Returns:
        The profile if found, None otherwise
    """
    return ProfileManager.get_instance().get_profile(name)


def list_profiles() -> list[ProcessingProfile]:
    """Get all available profiles (builtin + user).

    Returns:
        List of all profiles
    """
    return ProfileManager.get_instance().list_profiles()


def get_profile_names() -> list[str]:
    """Get all profile names (builtin + user).

    Returns:
        List of profile keys
    """
    return ProfileManager.get_instance().get_profile_names()


def get_builtin_profile_names() -> list[str]:
    """Get names of builtin profiles only.

    Returns:
        List of builtin profile keys
    """
    return ProfileManager.get_instance().get_builtin_names()
