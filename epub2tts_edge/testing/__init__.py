"""Testing utilities shipped with audiobookify.

These helpers back the ``--test-mode`` flag and are part of the distributed
package (not the test suite), so they remain importable from an installed
wheel. Downstream projects can use them to exercise audiobookify without
hitting Microsoft's TTS service.
"""

from .mock_tts import MockTTSEngine, TTSCall

__all__ = ["MockTTSEngine", "TTSCall"]
