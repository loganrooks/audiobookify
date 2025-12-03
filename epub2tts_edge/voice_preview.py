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

# Available voices with metadata - organized by language
AVAILABLE_VOICES: List[Dict[str, str]] = [
    # === MULTILINGUAL VOICES (can speak multiple languages) ===
    {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew (Multilingual)", "gender": "Male", "locale": "en-US", "description": "Multilingual - Confident, Casual, Warm"},
    {"id": "en-US-AvaMultilingualNeural", "name": "Ava (Multilingual)", "gender": "Female", "locale": "en-US", "description": "Multilingual - Pleasant, Friendly, Caring"},
    {"id": "en-US-BrianMultilingualNeural", "name": "Brian (Multilingual)", "gender": "Male", "locale": "en-US", "description": "Multilingual - Sincere, Calm, Approachable"},
    {"id": "en-US-EmmaMultilingualNeural", "name": "Emma (Multilingual)", "gender": "Female", "locale": "en-US", "description": "Multilingual - Cheerful, Light-Hearted"},
    {"id": "en-US-JennyMultilingualNeural", "name": "Jenny (Multilingual)", "gender": "Female", "locale": "en-US", "description": "Multilingual - Sincere, Pleasant"},
    {"id": "en-GB-AdaMultilingualNeural", "name": "Ada (Multilingual)", "gender": "Female", "locale": "en-GB", "description": "Multilingual - Cheerful, Warm, Gentle"},
    {"id": "de-DE-FlorianMultilingualNeural", "name": "Florian (Multilingual)", "gender": "Male", "locale": "de-DE", "description": "Multilingual German - Cheerful, Warm"},
    {"id": "de-DE-SeraphinaMultilingualNeural", "name": "Seraphina (Multilingual)", "gender": "Female", "locale": "de-DE", "description": "Multilingual German - Casual"},
    {"id": "fr-FR-RemyMultilingualNeural", "name": "Remy (Multilingual)", "gender": "Male", "locale": "fr-FR", "description": "Multilingual French - Bright, Cheerful"},
    {"id": "fr-FR-VivienneMultilingualNeural", "name": "Vivienne (Multilingual)", "gender": "Female", "locale": "fr-FR", "description": "Multilingual French - Warm, Casual"},
    {"id": "es-ES-ArabellaMultilingualNeural", "name": "Arabella (Multilingual)", "gender": "Female", "locale": "es-ES", "description": "Multilingual Spanish - Cheerful, Friendly"},
    {"id": "it-IT-IsabellaMultilingualNeural", "name": "Isabella (Multilingual)", "gender": "Female", "locale": "it-IT", "description": "Multilingual Italian - Warm, Cheerful"},
    {"id": "it-IT-GiuseppeMultilingualNeural", "name": "Giuseppe (Multilingual)", "gender": "Male", "locale": "it-IT", "description": "Multilingual Italian - Expressive, Upbeat"},
    {"id": "pt-BR-ThalitaMultilingualNeural", "name": "Thalita (Multilingual)", "gender": "Female", "locale": "pt-BR", "description": "Multilingual Portuguese - Confident, Warm"},
    {"id": "ja-JP-MasaruMultilingualNeural", "name": "Masaru (Multilingual)", "gender": "Male", "locale": "ja-JP", "description": "Multilingual Japanese - Bright, Warm"},
    {"id": "ko-KR-HyunsuMultilingualNeural", "name": "Hyunsu (Multilingual)", "gender": "Male", "locale": "ko-KR", "description": "Multilingual Korean - Formal, Clear"},
    {"id": "zh-CN-XiaoxiaoMultilingualNeural", "name": "Xiaoxiao (Multilingual)", "gender": "Female", "locale": "zh-CN", "description": "Multilingual Chinese - Warm, Animated"},

    # === ENGLISH - US ===
    {"id": "en-US-AndrewNeural", "name": "Andrew", "gender": "Male", "locale": "en-US", "description": "American - Confident, Authentic, Warm"},
    {"id": "en-US-AvaNeural", "name": "Ava", "gender": "Female", "locale": "en-US", "description": "American - Pleasant, Caring, Friendly"},
    {"id": "en-US-BrianNeural", "name": "Brian", "gender": "Male", "locale": "en-US", "description": "American - Sincere, Calm, Approachable"},
    {"id": "en-US-EmmaNeural", "name": "Emma", "gender": "Female", "locale": "en-US", "description": "American - Cheerful, Light-Hearted"},
    {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "Female", "locale": "en-US", "description": "American - Sincere, Pleasant, Approachable"},
    {"id": "en-US-GuyNeural", "name": "Guy", "gender": "Male", "locale": "en-US", "description": "American - Light-Hearted, Friendly"},
    {"id": "en-US-AriaNeural", "name": "Aria", "gender": "Female", "locale": "en-US", "description": "American - Crisp, Bright, Clear"},
    {"id": "en-US-DavisNeural", "name": "Davis", "gender": "Male", "locale": "en-US", "description": "American - Soothing, Calm, Smooth"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "Male", "locale": "en-US", "description": "American - Deep, Warm"},
    {"id": "en-US-MichelleNeural", "name": "Michelle", "gender": "Female", "locale": "en-US", "description": "American - Confident, Authentic, Warm"},
    {"id": "en-US-SteffanNeural", "name": "Steffan", "gender": "Male", "locale": "en-US", "description": "American - Mature, Authentic, Warm"},
    {"id": "en-US-EricNeural", "name": "Eric", "gender": "Male", "locale": "en-US", "description": "American - Confident, Sincere, Warm"},
    {"id": "en-US-RogerNeural", "name": "Roger", "gender": "Male", "locale": "en-US", "description": "American - Serious, Formal, Confident"},

    # === ENGLISH - UK ===
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "gender": "Female", "locale": "en-GB", "description": "British - Gentle, Soft"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "Male", "locale": "en-GB", "description": "British - Bright, Engaging"},
    {"id": "en-GB-LibbyNeural", "name": "Libby", "gender": "Female", "locale": "en-GB", "description": "British - Crisp, Bright, Clear"},
    {"id": "en-GB-ThomasNeural", "name": "Thomas", "gender": "Male", "locale": "en-GB", "description": "British - Classic British Male"},
    {"id": "en-GB-MaisieNeural", "name": "Maisie", "gender": "Female", "locale": "en-GB", "description": "British - Crisp, Cheerful, Bright"},

    # === ENGLISH - Australia ===
    {"id": "en-AU-NatashaNeural", "name": "Natasha", "gender": "Female", "locale": "en-AU", "description": "Australian - Crisp, Bright, Clear"},
    {"id": "en-AU-WilliamNeural", "name": "William", "gender": "Male", "locale": "en-AU", "description": "Australian - Engaging, Strong"},

    # === GERMAN ===
    {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "Male", "locale": "de-DE", "description": "German - Engaging, Friendly"},
    {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "Female", "locale": "de-DE", "description": "German - Calm, Pleasant"},
    {"id": "de-DE-AmalaNeural", "name": "Amala", "gender": "Female", "locale": "de-DE", "description": "German - Well-Rounded, Animated"},
    {"id": "de-DE-KillianNeural", "name": "Killian", "gender": "Male", "locale": "de-DE", "description": "German - Male Voice"},

    # === FRENCH ===
    {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "Male", "locale": "fr-FR", "description": "French - Strong, Calm"},
    {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "Female", "locale": "fr-FR", "description": "French - Bright, Engaging"},
    {"id": "fr-FR-YvetteNeural", "name": "Yvette", "gender": "Female", "locale": "fr-FR", "description": "French - Animated, Bright"},

    # === SPANISH ===
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "Male", "locale": "es-ES", "description": "Spanish - Confident, Animated"},
    {"id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "Female", "locale": "es-ES", "description": "Spanish - Bright, Clear"},
    {"id": "es-MX-JorgeMultilingualNeural", "name": "Jorge (Multilingual)", "gender": "Male", "locale": "es-MX", "description": "Mexican Spanish - Warm, Friendly"},
    {"id": "es-MX-DaliaMultilingualNeural", "name": "Dalia (Multilingual)", "gender": "Female", "locale": "es-MX", "description": "Mexican Spanish - Warm, Cheerful"},

    # === ITALIAN ===
    {"id": "it-IT-DiegoNeural", "name": "Diego", "gender": "Male", "locale": "it-IT", "description": "Italian - Animated, Upbeat"},
    {"id": "it-IT-ElsaNeural", "name": "Elsa", "gender": "Female", "locale": "it-IT", "description": "Italian - Confident, Crisp"},
    {"id": "it-IT-IsabellaNeural", "name": "Isabella", "gender": "Female", "locale": "it-IT", "description": "Italian - Upbeat, Bright"},

    # === PORTUGUESE ===
    {"id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "Male", "locale": "pt-BR", "description": "Brazilian - Bright, Upbeat"},
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "Female", "locale": "pt-BR", "description": "Brazilian - Cheerful, Crisp"},
    {"id": "pt-BR-ThalitaNeural", "name": "Thalita", "gender": "Female", "locale": "pt-BR", "description": "Brazilian - Confident, Formal"},

    # === JAPANESE ===
    {"id": "ja-JP-NanamiNeural", "name": "Nanami", "gender": "Female", "locale": "ja-JP", "description": "Japanese - Bright, Cheerful"},
    {"id": "ja-JP-KeitaNeural", "name": "Keita", "gender": "Male", "locale": "ja-JP", "description": "Japanese - Casual, Engaging"},

    # === KOREAN ===
    {"id": "ko-KR-SunHiNeural", "name": "SunHi", "gender": "Female", "locale": "ko-KR", "description": "Korean - Confident, Formal"},
    {"id": "ko-KR-InJoonNeural", "name": "InJoon", "gender": "Male", "locale": "ko-KR", "description": "Korean - Casual, Friendly"},

    # === CHINESE ===
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "gender": "Female", "locale": "zh-CN", "description": "Chinese - Warm, Well-Rounded"},
    {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "gender": "Male", "locale": "zh-CN", "description": "Chinese - Bright, Animated"},
    {"id": "zh-CN-YunyangNeural", "name": "Yunyang", "gender": "Male", "locale": "zh-CN", "description": "Chinese - Formal, Deep, Calm"},
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
