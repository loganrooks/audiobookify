"""Processing profiles for audiobook conversion.

This module provides predefined configuration profiles that users can select
instead of manually configuring each setting. Each profile represents a
different use case (quick draft, high quality, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def get_profile(name: str) -> ProcessingProfile | None:
    """Get a profile by name.

    Args:
        name: Profile name (case-insensitive)

    Returns:
        The profile if found, None otherwise
    """
    return BUILTIN_PROFILES.get(name.lower())


def list_profiles() -> list[ProcessingProfile]:
    """Get all available profiles.

    Returns:
        List of all built-in profiles
    """
    return list(BUILTIN_PROFILES.values())


def get_profile_names() -> list[str]:
    """Get all profile names.

    Returns:
        List of profile name keys
    """
    return list(BUILTIN_PROFILES.keys())
