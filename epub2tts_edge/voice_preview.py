"""Voice preview functionality for audiobookify.

This module provides voice preview capabilities, allowing users to
listen to a sample of a voice before committing to a full conversion.
"""
import asyncio
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, Dict

import edge_tts


# Default sample text for voice preview
DEFAULT_PREVIEW_TEXT = (
    "Hello! This is a preview of the selected voice. "
    "You can use this to hear how your audiobook will sound."
)

# Available voices with metadata
AVAILABLE_VOICES: List[Dict[str, str]] = [
    {
        "id": "en-US-AndrewNeural",
        "name": "Andrew",
        "gender": "Male",
        "locale": "en-US",
        "description": "American English, Male"
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny",
        "gender": "Female",
        "locale": "en-US",
        "description": "American English, Female"
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy",
        "gender": "Male",
        "locale": "en-US",
        "description": "American English, Male"
    },
    {
        "id": "en-GB-SoniaNeural",
        "name": "Sonia",
        "gender": "Female",
        "locale": "en-GB",
        "description": "British English, Female"
    },
    {
        "id": "en-GB-RyanNeural",
        "name": "Ryan",
        "gender": "Male",
        "locale": "en-GB",
        "description": "British English, Male"
    },
    {
        "id": "en-AU-NatashaNeural",
        "name": "Natasha",
        "gender": "Female",
        "locale": "en-AU",
        "description": "Australian English, Female"
    },
    {
        "id": "en-AU-WilliamNeural",
        "name": "William",
        "gender": "Male",
        "locale": "en-AU",
        "description": "Australian English, Male"
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Aria",
        "gender": "Female",
        "locale": "en-US",
        "description": "American English, Female"
    },
    {
        "id": "en-US-DavisNeural",
        "name": "Davis",
        "gender": "Male",
        "locale": "en-US",
        "description": "American English, Male"
    },
    {
        "id": "en-US-JaneNeural",
        "name": "Jane",
        "gender": "Female",
        "locale": "en-US",
        "description": "American English, Female"
    },
]


@dataclass
class VoicePreviewConfig:
    """Configuration for voice preview.

    Attributes:
        speaker: The voice ID to use (e.g., "en-US-AndrewNeural")
        text: The sample text to speak
        rate: Speech rate adjustment (e.g., "+20%", "-10%")
        volume: Volume adjustment (e.g., "+50%", "-25%")
    """
    speaker: str = "en-US-AndrewNeural"
    text: str = field(default_factory=lambda: DEFAULT_PREVIEW_TEXT)
    rate: Optional[str] = None
    volume: Optional[str] = None


class VoicePreview:
    """Generate voice previews using edge-tts.

    This class allows users to preview how a voice sounds before
    committing to a full audiobook conversion.

    Example:
        >>> preview = VoicePreview()
        >>> preview.set_speaker("en-US-JennyNeural")
        >>> preview.set_rate("+10%")
        >>> audio_path = preview.generate_preview_temp()
        >>> # Play audio_path with your preferred player
    """

    # Regex patterns for validation
    RATE_PATTERN = re.compile(r'^[+-]\d+%$')
    VOLUME_PATTERN = re.compile(r'^[+-]\d+%$')

    def __init__(self, config: Optional[VoicePreviewConfig] = None):
        """Initialize VoicePreview with optional configuration.

        Args:
            config: VoicePreviewConfig instance, or None to use defaults
        """
        self.config = config or VoicePreviewConfig()

    def set_speaker(self, speaker: str) -> 'VoicePreview':
        """Set the voice speaker.

        Args:
            speaker: Voice ID (e.g., "en-US-AndrewNeural")

        Returns:
            self for method chaining
        """
        self.config.speaker = speaker
        return self

    def set_text(self, text: str) -> 'VoicePreview':
        """Set the preview text.

        Args:
            text: Text to speak in the preview

        Returns:
            self for method chaining
        """
        self.config.text = text
        return self

    def set_rate(self, rate: str) -> 'VoicePreview':
        """Set the speech rate.

        Args:
            rate: Rate adjustment (e.g., "+20%", "-10%")

        Returns:
            self for method chaining

        Raises:
            ValueError: If rate format is invalid
        """
        if not self.RATE_PATTERN.match(rate):
            raise ValueError(
                f"Invalid rate format: {rate}. "
                "Expected format: '+N%' or '-N%' (e.g., '+20%', '-10%')"
            )
        self.config.rate = rate
        return self

    def set_volume(self, volume: str) -> 'VoicePreview':
        """Set the volume adjustment.

        Args:
            volume: Volume adjustment (e.g., "+50%", "-25%")

        Returns:
            self for method chaining

        Raises:
            ValueError: If volume format is invalid
        """
        if not self.VOLUME_PATTERN.match(volume):
            raise ValueError(
                f"Invalid volume format: {volume}. "
                "Expected format: '+N%' or '-N%' (e.g., '+50%', '-25%')"
            )
        self.config.volume = volume
        return self

    def generate_preview(self, output_path: str) -> str:
        """Generate a voice preview and save to the specified path.

        Args:
            output_path: Path where the MP3 file will be saved

        Returns:
            The output path
        """
        asyncio.run(self._generate_async(output_path))
        return output_path

    def generate_preview_temp(self) -> str:
        """Generate a voice preview in a temporary file.

        Returns:
            Path to the temporary MP3 file. Caller is responsible
            for cleanup.
        """
        fd, temp_path = tempfile.mkstemp(suffix=".mp3", prefix="voice_preview_")
        os.close(fd)
        return self.generate_preview(temp_path)

    async def _generate_async(self, output_path: str) -> None:
        """Async implementation of preview generation.

        Args:
            output_path: Path where the MP3 file will be saved
        """
        # Build kwargs for edge_tts.Communicate
        kwargs = {}
        if self.config.rate:
            kwargs["rate"] = self.config.rate
        if self.config.volume:
            kwargs["volume"] = self.config.volume

        communicate = edge_tts.Communicate(
            self.config.text,
            self.config.speaker,
            **kwargs
        )
        await communicate.save(output_path)


def get_voice_by_id(voice_id: str) -> Optional[Dict[str, str]]:
    """Get voice metadata by ID.

    Args:
        voice_id: The voice ID to look up

    Returns:
        Voice metadata dict, or None if not found
    """
    for voice in AVAILABLE_VOICES:
        if voice["id"] == voice_id:
            return voice
    return None


def get_voices_by_locale(locale: str) -> List[Dict[str, str]]:
    """Get all voices for a specific locale.

    Args:
        locale: Locale code (e.g., "en-US", "en-GB")

    Returns:
        List of voice metadata dicts
    """
    return [v for v in AVAILABLE_VOICES if v["locale"] == locale]


def get_voices_by_gender(gender: str) -> List[Dict[str, str]]:
    """Get all voices of a specific gender.

    Args:
        gender: Gender ("Male" or "Female")

    Returns:
        List of voice metadata dicts
    """
    return [v for v in AVAILABLE_VOICES if v["gender"] == gender]
