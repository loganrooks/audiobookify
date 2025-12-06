"""Test fixtures for audiobookify.

This module provides predefined EPUB content fixtures for testing various
scenarios like front matter, back matter, nested chapters, etc.
"""

from .epub_factory import FIXTURES, create_test_epub

__all__ = ["create_test_epub", "FIXTURES"]
