"""Tests for multiple voice support functionality."""

import json
import os
import tempfile


class TestVoiceMapping:
    """Tests for VoiceMapping dataclass."""

    def test_default_mapping(self):
        """Test default voice mapping."""
        from epub2tts_edge.multi_voice import VoiceMapping

        mapping = VoiceMapping()
        assert mapping.default_voice == "en-US-AndrewNeural"
        assert mapping.narrator_voice is None
        assert mapping.character_voices == {}

    def test_custom_mapping(self):
        """Test custom voice mapping."""
        from epub2tts_edge.multi_voice import VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-JennyNeural",
            narrator_voice="en-US-GuyNeural",
            character_voices={"Harry": "en-GB-RyanNeural"}
        )
        assert mapping.default_voice == "en-US-JennyNeural"
        assert mapping.narrator_voice == "en-US-GuyNeural"
        assert mapping.character_voices["Harry"] == "en-GB-RyanNeural"


class TestDialogueSegment:
    """Tests for DialogueSegment dataclass."""

    def test_segment_creation(self):
        """Test dialogue segment creation."""
        from epub2tts_edge.multi_voice import DialogueSegment

        segment = DialogueSegment(
            text="Hello there!",
            speaker="Gandalf",
            is_dialogue=True
        )
        assert segment.text == "Hello there!"
        assert segment.speaker == "Gandalf"
        assert segment.is_dialogue is True

    def test_narration_segment(self):
        """Test narration segment."""
        from epub2tts_edge.multi_voice import DialogueSegment

        segment = DialogueSegment(
            text="He walked slowly.",
            speaker=None,
            is_dialogue=False
        )
        assert segment.is_dialogue is False
        assert segment.speaker is None


class TestMultiVoiceProcessor:
    """Tests for MultiVoiceProcessor class."""

    def test_init_default(self):
        """Test initializer with defaults."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        assert processor.mapping.default_voice == "en-US-AndrewNeural"

    def test_init_custom_mapping(self):
        """Test initializer with custom mapping."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-JennyNeural",
            character_voices={"Alice": "en-GB-SoniaNeural"}
        )
        processor = MultiVoiceProcessor(mapping)
        assert processor.mapping.default_voice == "en-US-JennyNeural"

    def test_detect_dialogue_basic(self):
        """Test basic dialogue detection with quotes."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"Hello," said Harry.'

        segments = processor.parse_text(text)
        assert len(segments) >= 1
        # Should detect "Hello," as dialogue
        dialogue_segments = [s for s in segments if s.is_dialogue]
        assert len(dialogue_segments) >= 1

    def test_detect_dialogue_with_speaker(self):
        """Test dialogue detection with speaker attribution."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"I must go," Harry said quietly.'

        segments = processor.parse_text(text)
        dialogue_segments = [s for s in segments if s.is_dialogue]
        assert len(dialogue_segments) >= 1
        # Check if speaker was detected
        assert any(s.speaker == "Harry" for s in dialogue_segments)

    def test_detect_narration(self):
        """Test narration detection."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = "The sun set behind the mountains."

        segments = processor.parse_text(text)
        assert len(segments) == 1
        assert segments[0].is_dialogue is False

    def test_get_voice_for_segment_dialogue(self):
        """Test getting voice for dialogue segment."""
        from epub2tts_edge.multi_voice import DialogueSegment, MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-AndrewNeural",
            character_voices={"Harry": "en-GB-RyanNeural"}
        )
        processor = MultiVoiceProcessor(mapping)

        segment = DialogueSegment(text="Hello", speaker="Harry", is_dialogue=True)
        voice = processor.get_voice_for_segment(segment)
        assert voice == "en-GB-RyanNeural"

    def test_get_voice_for_segment_unknown_character(self):
        """Test getting voice for unknown character uses default."""
        from epub2tts_edge.multi_voice import DialogueSegment, MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-AndrewNeural",
            character_voices={"Harry": "en-GB-RyanNeural"}
        )
        processor = MultiVoiceProcessor(mapping)

        segment = DialogueSegment(text="Hello", speaker="Hermione", is_dialogue=True)
        voice = processor.get_voice_for_segment(segment)
        assert voice == "en-US-AndrewNeural"  # Falls back to default

    def test_get_voice_for_narration(self):
        """Test getting voice for narration."""
        from epub2tts_edge.multi_voice import DialogueSegment, MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-AndrewNeural",
            narrator_voice="en-US-GuyNeural"
        )
        processor = MultiVoiceProcessor(mapping)

        segment = DialogueSegment(text="He walked.", speaker=None, is_dialogue=False)
        voice = processor.get_voice_for_segment(segment)
        assert voice == "en-US-GuyNeural"

    def test_get_voice_narration_no_narrator_voice(self):
        """Test narration uses default when no narrator voice set."""
        from epub2tts_edge.multi_voice import DialogueSegment, MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(default_voice="en-US-AndrewNeural")
        processor = MultiVoiceProcessor(mapping)

        segment = DialogueSegment(text="He walked.", speaker=None, is_dialogue=False)
        voice = processor.get_voice_for_segment(segment)
        assert voice == "en-US-AndrewNeural"

    def test_add_character_voice(self):
        """Test adding character voice dynamically."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        processor.add_character_voice("Gandalf", "en-GB-RyanNeural")

        assert processor.mapping.character_voices["Gandalf"] == "en-GB-RyanNeural"

    def test_remove_character_voice(self):
        """Test removing character voice."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(character_voices={"Harry": "en-GB-RyanNeural"})
        processor = MultiVoiceProcessor(mapping)

        processor.remove_character_voice("Harry")
        assert "Harry" not in processor.mapping.character_voices


class TestVoiceMappingFile:
    """Tests for loading/saving voice mappings."""

    def test_load_mapping_from_json(self):
        """Test loading voice mapping from JSON file."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        mapping_data = {
            "default_voice": "en-US-JennyNeural",
            "narrator_voice": "en-US-GuyNeural",
            "character_voices": {
                "Harry": "en-GB-RyanNeural",
                "Hermione": "en-GB-SoniaNeural"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mapping_data, f)
            temp_path = f.name

        try:
            processor = MultiVoiceProcessor()
            processor.load_mapping(temp_path)

            assert processor.mapping.default_voice == "en-US-JennyNeural"
            assert processor.mapping.narrator_voice == "en-US-GuyNeural"
            assert processor.mapping.character_voices["Harry"] == "en-GB-RyanNeural"
        finally:
            os.unlink(temp_path)

    def test_save_mapping_to_json(self):
        """Test saving voice mapping to JSON file."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-JennyNeural",
            character_voices={"Harry": "en-GB-RyanNeural"}
        )
        processor = MultiVoiceProcessor(mapping)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            processor.save_mapping(temp_path)

            with open(temp_path) as f:
                loaded = json.load(f)

            assert loaded["default_voice"] == "en-US-JennyNeural"
            assert loaded["character_voices"]["Harry"] == "en-GB-RyanNeural"
        finally:
            os.unlink(temp_path)


class TestDialoguePatterns:
    """Tests for various dialogue patterns."""

    def test_double_quotes(self):
        """Test dialogue in double quotes."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"This is dialogue," she said.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert len(dialogue) >= 1

    def test_single_quotes(self):
        """Test dialogue in single quotes."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = "'This is dialogue,' he replied."
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert len(dialogue) >= 1

    def test_curly_quotes(self):
        """Test dialogue in curly quotes."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"This is dialogue," she said.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert len(dialogue) >= 1

    def test_multiple_dialogues(self):
        """Test paragraph with multiple dialogues."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"Hello," said Harry. "How are you?" asked Hermione.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert len(dialogue) >= 2

    def test_mixed_content(self):
        """Test paragraph with mixed narration and dialogue."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = 'The door opened. "Who goes there?" the guard demanded. Silence followed.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        narration = [s for s in segments if not s.is_dialogue]

        assert len(dialogue) >= 1
        assert len(narration) >= 1


class TestSpeakerAttribution:
    """Tests for speaker attribution patterns."""

    def test_said_pattern(self):
        """Test 'said X' pattern."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"Hello," said Harry.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert any(s.speaker == "Harry" for s in dialogue)

    def test_x_said_pattern(self):
        """Test 'X said' pattern."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        text = '"Hello," Harry said.'
        segments = processor.parse_text(text)

        dialogue = [s for s in segments if s.is_dialogue]
        assert any(s.speaker == "Harry" for s in dialogue)

    def test_various_speech_verbs(self):
        """Test various speech verbs."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor

        processor = MultiVoiceProcessor()
        verbs_texts = [
            ('"Hello," whispered Harry.', "Harry"),
            ('"Go away!" shouted Ron.', "Ron"),
            ('"Perhaps," murmured Dumbledore.', "Dumbledore"),
        ]

        for text, expected_speaker in verbs_texts:
            segments = processor.parse_text(text)
            dialogue = [s for s in segments if s.is_dialogue]
            assert any(s.speaker == expected_speaker for s in dialogue), f"Failed for: {text}"


class TestMultiVoiceIntegration:
    """Integration tests for multi-voice processing."""

    def test_process_paragraph_returns_voice_text_pairs(self):
        """Test processing paragraph returns voice-text pairs."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            default_voice="en-US-AndrewNeural",
            narrator_voice="en-US-GuyNeural",
            character_voices={"Harry": "en-GB-RyanNeural"}
        )
        processor = MultiVoiceProcessor(mapping)

        text = 'Harry smiled. "Hello there," Harry said.'
        pairs = processor.process_paragraph(text)

        assert len(pairs) >= 1
        # Each pair should be (voice, text)
        for voice, segment_text in pairs:
            assert voice is not None
            assert segment_text is not None

    def test_list_character_voices(self):
        """Test listing all character voices."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            character_voices={
                "Harry": "en-GB-RyanNeural",
                "Hermione": "en-GB-SoniaNeural"
            }
        )
        processor = MultiVoiceProcessor(mapping)

        voices = processor.list_character_voices()
        assert len(voices) == 2
        assert ("Harry", "en-GB-RyanNeural") in voices

    def test_get_character_count(self):
        """Test getting character count."""
        from epub2tts_edge.multi_voice import MultiVoiceProcessor, VoiceMapping

        mapping = VoiceMapping(
            character_voices={
                "Harry": "en-GB-RyanNeural",
                "Ron": "en-US-GuyNeural"
            }
        )
        processor = MultiVoiceProcessor(mapping)

        assert processor.character_count == 2
