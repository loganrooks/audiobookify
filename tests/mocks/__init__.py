"""Mock implementations for testing audiobookify.

``MockTTSEngine`` now lives inside the distributed package
(:mod:`epub2tts_edge.testing`) so that ``--test-mode`` keeps working from an
installed wheel, where the ``tests`` package is not shipped. This module
re-exports it so existing imports keep working.
"""

from epub2tts_edge.testing import MockTTSEngine, TTSCall

__all__ = ["MockTTSEngine", "TTSCall"]
