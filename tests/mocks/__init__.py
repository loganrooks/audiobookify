"""Mock implementations for testing audiobookify.

This module provides mock versions of external dependencies like TTS engines
to enable fast, offline, reproducible testing.
"""

from .tts_mock import MockTTSEngine

__all__ = ["MockTTSEngine"]
