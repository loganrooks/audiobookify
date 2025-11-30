"""Multiple voice support for audiobook narration.

This module provides functionality to use different voices for
different characters and narration in audiobooks.
"""

import json
import re
from dataclasses import dataclass, field


@dataclass
class VoiceMapping:
    """Voice mapping configuration.

    Attributes:
        default_voice: Default voice for unassigned speakers
        narrator_voice: Voice for narration (non-dialogue)
        character_voices: Dict mapping character names to voices
    """
    default_voice: str = "en-US-AndrewNeural"
    narrator_voice: str | None = None
    character_voices: dict[str, str] = field(default_factory=dict)


@dataclass
class DialogueSegment:
    """A segment of text with speaker information.

    Attributes:
        text: The text content
        speaker: Speaker name (None for narration)
        is_dialogue: Whether this is dialogue (quoted speech)
    """
    text: str
    speaker: str | None = None
    is_dialogue: bool = False


class MultiVoiceProcessor:
    """Processes text to apply multiple voices.

    This class parses text to detect dialogue and narration,
    and assigns appropriate voices to each segment.

    Attributes:
        mapping: VoiceMapping instance with voice assignments
    """

    # Speech verbs for speaker attribution
    SPEECH_VERBS = [
        'said', 'asked', 'replied', 'answered', 'whispered', 'shouted',
        'yelled', 'screamed', 'murmured', 'muttered', 'exclaimed',
        'declared', 'announced', 'stated', 'added', 'continued',
        'explained', 'suggested', 'demanded', 'insisted', 'admitted',
        'agreed', 'argued', 'begged', 'called', 'commented', 'complained',
        'cried', 'gasped', 'groaned', 'grumbled', 'hissed', 'interrupted',
        'laughed', 'mentioned', 'moaned', 'noted', 'observed', 'offered',
        'ordered', 'pleaded', 'promised', 'questioned', 'remarked',
        'repeated', 'responded', 'sighed', 'snapped', 'sobbed', 'spoke',
        'stammered', 'stuttered', 'told', 'urged', 'warned', 'wondered'
    ]

    # Quote patterns
    QUOTE_PATTERNS = [
        r'"([^"]+)"',           # Double quotes
        r"'([^']+)'",           # Single quotes
        r'\u201c([^\u201d]+)\u201d',  # Curly double quotes
        r'\u2018([^\u2019]+)\u2019',  # Curly single quotes
    ]

    def __init__(self, mapping: VoiceMapping | None = None):
        """Initialize the processor.

        Args:
            mapping: Optional voice mapping. Uses defaults if not provided.
        """
        self.mapping = mapping or VoiceMapping()
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for dialogue detection."""
        # Pattern to match quoted text
        self._quote_pattern = re.compile(
            r'["\'""]([^"\'""]+)["\'""]',
            re.UNICODE
        )

        # Pattern to match speaker attribution after dialogue
        # e.g., "Hello," said Harry. or "Hello," Harry said.
        verbs = '|'.join(self.SPEECH_VERBS)
        self._speaker_after_pattern = re.compile(
            rf'["\'""]([^"\'""]+)["\'""][,.]?\s*(?:({verbs})\s+)?([A-Z][a-z]+)(?:\s+({verbs}))?',
            re.UNICODE
        )

    def parse_text(self, text: str) -> list[DialogueSegment]:
        """Parse text into dialogue and narration segments.

        Args:
            text: Input text to parse

        Returns:
            List of DialogueSegment objects
        """
        segments = []
        remaining = text
        last_end = 0

        # Find all quoted sections with potential speaker attribution
        for match in self._speaker_after_pattern.finditer(text):
            dialogue_text = match.group(1)
            verb_before = match.group(2)
            potential_speaker = match.group(3)
            verb_after = match.group(4)

            # Get narration before this dialogue
            narration_before = text[last_end:match.start()].strip()
            if narration_before:
                segments.append(DialogueSegment(
                    text=narration_before,
                    speaker=None,
                    is_dialogue=False
                ))

            # Determine speaker
            speaker = None
            if potential_speaker and (verb_before or verb_after):
                # Verify it's a speech verb context
                speaker = potential_speaker

            segments.append(DialogueSegment(
                text=dialogue_text,
                speaker=speaker,
                is_dialogue=True
            ))

            last_end = match.end()

        # Handle remaining text
        remaining = text[last_end:].strip()
        if remaining:
            # Check if remaining has any unmatched quotes
            simple_quotes = self._quote_pattern.findall(remaining)
            if simple_quotes:
                # Has dialogue but no clear speaker
                for quote in simple_quotes:
                    segments.append(DialogueSegment(
                        text=quote,
                        speaker=None,
                        is_dialogue=True
                    ))
                # Remove quotes from remaining for narration
                remaining_narration = self._quote_pattern.sub('', remaining).strip()
                if remaining_narration:
                    segments.append(DialogueSegment(
                        text=remaining_narration,
                        speaker=None,
                        is_dialogue=False
                    ))
            else:
                segments.append(DialogueSegment(
                    text=remaining,
                    speaker=None,
                    is_dialogue=False
                ))

        # If no segments found, treat entire text as narration
        if not segments:
            segments.append(DialogueSegment(
                text=text,
                speaker=None,
                is_dialogue=False
            ))

        return segments

    def get_voice_for_segment(self, segment: DialogueSegment) -> str:
        """Get the appropriate voice for a segment.

        Args:
            segment: DialogueSegment to get voice for

        Returns:
            Voice ID string
        """
        if segment.is_dialogue and segment.speaker:
            # Try to get character-specific voice
            if segment.speaker in self.mapping.character_voices:
                return self.mapping.character_voices[segment.speaker]

        if not segment.is_dialogue:
            # Narration
            if self.mapping.narrator_voice:
                return self.mapping.narrator_voice

        # Fall back to default
        return self.mapping.default_voice

    def process_paragraph(self, text: str) -> list[tuple[str, str]]:
        """Process a paragraph and return voice-text pairs.

        Args:
            text: Paragraph text to process

        Returns:
            List of (voice_id, text) tuples
        """
        segments = self.parse_text(text)
        pairs = []

        for segment in segments:
            voice = self.get_voice_for_segment(segment)
            pairs.append((voice, segment.text))

        return pairs

    def add_character_voice(self, character: str, voice: str) -> None:
        """Add a character voice mapping.

        Args:
            character: Character name
            voice: Voice ID to use
        """
        self.mapping.character_voices[character] = voice

    def remove_character_voice(self, character: str) -> None:
        """Remove a character voice mapping.

        Args:
            character: Character name to remove
        """
        if character in self.mapping.character_voices:
            del self.mapping.character_voices[character]

    def load_mapping(self, file_path: str) -> None:
        """Load voice mapping from a JSON file.

        Args:
            file_path: Path to the JSON file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Mapping file not found: {file_path}")

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)

        if 'default_voice' in data:
            self.mapping.default_voice = data['default_voice']
        if 'narrator_voice' in data:
            self.mapping.narrator_voice = data['narrator_voice']
        if 'character_voices' in data:
            self.mapping.character_voices.update(data['character_voices'])

    def save_mapping(self, file_path: str) -> None:
        """Save voice mapping to a JSON file.

        Args:
            file_path: Path for the output file
        """
        data = {
            'default_voice': self.mapping.default_voice,
            'narrator_voice': self.mapping.narrator_voice,
            'character_voices': self.mapping.character_voices
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_character_voices(self) -> list[tuple[str, str]]:
        """List all character voice mappings.

        Returns:
            List of (character, voice) tuples
        """
        return list(self.mapping.character_voices.items())

    @property
    def character_count(self) -> int:
        """Get the number of character voice mappings."""
        return len(self.mapping.character_voices)

    def clear_character_voices(self) -> None:
        """Clear all character voice mappings."""
        self.mapping.character_voices.clear()
