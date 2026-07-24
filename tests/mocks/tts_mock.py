"""Backwards-compatible shim for the mock TTS engine.

The implementation moved to :mod:`epub2tts_edge.testing.mock_tts` so it ships
with the wheel and ``--test-mode`` works for installed users. Import from there
in new code.
"""

from epub2tts_edge.testing.mock_tts import MockTTSEngine, TTSCall

__all__ = ["MockTTSEngine", "TTSCall"]
