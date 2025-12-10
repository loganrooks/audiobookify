"""Mock TTS engine for fast testing.

This module provides a mock TTS engine that generates silent audio instead
of calling the real Edge TTS API. This enables:
- Fast test execution (1000x+ faster than real TTS)
- Offline testing without internet
- Reproducible results
- Zero API costs
"""

import io
import struct
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TTSCall:
    """Record of a TTS call for assertions."""

    text: str
    voice: str
    rate: str | None = None
    volume: str | None = None
    output_path: Path | None = None


@dataclass
class MockTTSEngine:
    """Mock TTS engine that generates silence instead of speech.

    This mock tracks all calls made to it, allowing tests to verify
    that the correct text was sent for synthesis without actually
    generating audio.

    Attributes:
        speed_factor: How much faster than real TTS (100.0 = instant)
        calls: List of all TTS calls made
        fail_on_text: Optional text pattern that triggers failures

    Example:
        >>> mock = MockTTSEngine(speed_factor=1000)
        >>> audio = await mock.generate("Hello world", "en-US-AriaNeural")
        >>> assert len(mock.calls) == 1
        >>> assert mock.calls[0].text == "Hello world"
    """

    speed_factor: float = 1000.0
    calls: list[TTSCall] = field(default_factory=list)
    fail_on_text: str | None = None
    _sample_rate: int = 24000
    _channels: int = 1
    _sample_width: int = 2  # 16-bit audio

    def reset(self) -> None:
        """Clear all recorded calls."""
        self.calls.clear()

    def _calculate_duration(self, text: str) -> float:
        """Calculate audio duration based on text length.

        Assumes approximately 150 words per minute speaking rate.

        Args:
            text: The text to estimate duration for

        Returns:
            Duration in seconds (adjusted by speed_factor)
        """
        words = len(text.split())
        # 150 words per minute = 2.5 words per second
        real_duration = words / 2.5
        return real_duration / self.speed_factor

    def _generate_silence(self, duration_seconds: float) -> bytes:
        """Generate silent WAV audio data.

        Args:
            duration_seconds: Duration of silence to generate

        Returns:
            WAV file bytes containing silence
        """
        # Calculate number of samples
        num_samples = int(self._sample_rate * duration_seconds)

        # Minimum of 100 samples to ensure valid audio
        num_samples = max(num_samples, 100)

        # Generate silent samples (zeros)
        silence_data = struct.pack("<" + "h" * num_samples, *([0] * num_samples))

        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self._channels)
            wav_file.setsampwidth(self._sample_width)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(silence_data)

        return buffer.getvalue()

    async def generate(
        self,
        text: str,
        voice: str,
        rate: str | None = None,
        volume: str | None = None,
        output_path: Path | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate mock audio for the given text.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            rate: Speaking rate adjustment (e.g., "+20%")
            volume: Volume adjustment (e.g., "-10%")
            output_path: Optional path to write audio file
            **kwargs: Additional arguments (ignored)

        Returns:
            WAV audio bytes (silence)

        Raises:
            RuntimeError: If fail_on_text pattern matches
        """
        # Record the call
        call = TTSCall(text=text, voice=voice, rate=rate, volume=volume, output_path=output_path)
        self.calls.append(call)

        # Check for intentional failure
        if self.fail_on_text and self.fail_on_text in text:
            raise RuntimeError(f"Mock TTS failure triggered by text: {text[:50]}...")

        # Generate silent audio
        duration = self._calculate_duration(text)
        audio_data = self._generate_silence(duration)

        # Write to file if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_data)

        return audio_data

    def generate_sync(
        self,
        text: str,
        voice: str,
        rate: str | None = None,
        volume: str | None = None,
        output_path: Path | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Synchronous version of generate for non-async contexts.

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            rate: Speaking rate adjustment
            volume: Volume adjustment
            output_path: Optional path to write audio file
            **kwargs: Additional arguments (ignored)

        Returns:
            WAV audio bytes (silence)
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.generate(text, voice, rate, volume, output_path, **kwargs)
        )

    @property
    def call_count(self) -> int:
        """Return the number of TTS calls made."""
        return len(self.calls)

    @property
    def total_text_length(self) -> int:
        """Return the total character count of all text sent to TTS."""
        return sum(len(call.text) for call in self.calls)

    def get_calls_for_voice(self, voice: str) -> list[TTSCall]:
        """Return all calls made with a specific voice.

        Args:
            voice: Voice ID to filter by

        Returns:
            List of TTSCall objects for that voice
        """
        return [call for call in self.calls if call.voice == voice]

    def assert_called_with_text(self, expected_text: str) -> None:
        """Assert that TTS was called with the expected text.

        Args:
            expected_text: Text that should have been sent to TTS

        Raises:
            AssertionError: If text was not found in any call
        """
        for call in self.calls:
            if expected_text in call.text:
                return
        raise AssertionError(f"Expected text not found in TTS calls: {expected_text[:50]}...")

    def assert_call_count(self, expected: int) -> None:
        """Assert the number of TTS calls made.

        Args:
            expected: Expected number of calls

        Raises:
            AssertionError: If call count doesn't match
        """
        if self.call_count != expected:
            raise AssertionError(f"Expected {expected} TTS calls, got {self.call_count}")
