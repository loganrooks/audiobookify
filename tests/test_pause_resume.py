"""Tests for pause/resume functionality."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from epub2tts_edge.pause_resume import (
    STATE_FILE_NAME,
    ConversionState,
    StateManager,
)


class TestConversionState(unittest.TestCase):
    """Tests for ConversionState dataclass."""

    def test_create_state(self):
        """Test creating a conversion state."""
        state = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=3
        )
        self.assertEqual(state.source_file, "/path/to/book.txt")
        self.assertEqual(state.total_chapters, 10)
        self.assertEqual(state.completed_chapters, 3)

    def test_state_defaults(self):
        """Test default values."""
        state = ConversionState(source_file="/path/to/book.txt")
        self.assertEqual(state.total_chapters, 0)
        self.assertEqual(state.completed_chapters, 0)
        self.assertEqual(state.speaker, "en-US-AndrewNeural")
        self.assertIsNone(state.rate)
        self.assertIsNone(state.volume)
        self.assertEqual(state.intermediate_files, [])

    def test_is_resumable(self):
        """Test is_resumable property."""
        state = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=5
        )
        self.assertTrue(state.is_resumable)

        state2 = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=0
        )
        self.assertFalse(state2.is_resumable)

        state3 = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=10
        )
        self.assertFalse(state3.is_resumable)  # Already complete

    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        state = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=5
        )
        self.assertEqual(state.progress_percentage, 50.0)

        state2 = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=0,
            completed_chapters=0
        )
        self.assertEqual(state2.progress_percentage, 0.0)

    def test_to_dict(self):
        """Test serialization to dict."""
        state = ConversionState(
            source_file="/path/to/book.txt",
            total_chapters=10,
            completed_chapters=3,
            speaker="en-US-JennyNeural",
            rate="+20%",
            intermediate_files=["part1.flac", "part2.flac"]
        )
        d = state.to_dict()
        self.assertEqual(d["source_file"], "/path/to/book.txt")
        self.assertEqual(d["total_chapters"], 10)
        self.assertEqual(d["completed_chapters"], 3)
        self.assertEqual(d["speaker"], "en-US-JennyNeural")
        self.assertEqual(d["rate"], "+20%")
        self.assertEqual(d["intermediate_files"], ["part1.flac", "part2.flac"])

    def test_from_dict(self):
        """Test deserialization from dict."""
        d = {
            "source_file": "/path/to/book.txt",
            "total_chapters": 10,
            "completed_chapters": 5,
            "speaker": "en-US-GuyNeural",
            "rate": "-10%",
            "volume": "+20%",
            "intermediate_files": ["part1.flac"]
        }
        state = ConversionState.from_dict(d)
        self.assertEqual(state.source_file, "/path/to/book.txt")
        self.assertEqual(state.completed_chapters, 5)
        self.assertEqual(state.speaker, "en-US-GuyNeural")
        self.assertEqual(state.rate, "-10%")


class TestStateManager(unittest.TestCase):
    """Tests for StateManager class."""

    def test_save_and_load_state(self):
        """Test saving and loading state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            state = ConversionState(
                source_file="/path/to/book.txt",
                total_chapters=10,
                completed_chapters=3
            )
            manager.save_state(state)

            loaded = manager.load_state()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.source_file, "/path/to/book.txt")
            self.assertEqual(loaded.completed_chapters, 3)

    def test_load_nonexistent_state(self):
        """Test loading state when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            state = manager.load_state()
            self.assertIsNone(state)

    def test_clear_state(self):
        """Test clearing saved state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            state = ConversionState(
                source_file="/path/to/book.txt",
                total_chapters=10,
                completed_chapters=3
            )
            manager.save_state(state)

            # Verify state exists
            self.assertTrue(manager.has_state())

            # Clear it
            manager.clear_state()

            # Verify it's gone
            self.assertFalse(manager.has_state())
            self.assertIsNone(manager.load_state())

    def test_has_state(self):
        """Test checking if state exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            self.assertFalse(manager.has_state())

            state = ConversionState(source_file="/path/to/book.txt")
            manager.save_state(state)
            self.assertTrue(manager.has_state())

    def test_update_progress(self):
        """Test updating progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            state = ConversionState(
                source_file="/path/to/book.txt",
                total_chapters=10,
                completed_chapters=0
            )
            manager.save_state(state)

            # Update progress
            manager.update_progress(5, ["part1.flac", "part2.flac"])

            loaded = manager.load_state()
            self.assertEqual(loaded.completed_chapters, 5)
            self.assertEqual(loaded.intermediate_files, ["part1.flac", "part2.flac"])

    def test_state_matches_source(self):
        """Test checking if state matches source file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)
            state = ConversionState(
                source_file="/path/to/book.txt",
                total_chapters=10,
                completed_chapters=3
            )
            manager.save_state(state)

            self.assertTrue(manager.state_matches("/path/to/book.txt"))
            self.assertFalse(manager.state_matches("/path/to/other.txt"))


class TestStateManagerEdgeCases(unittest.TestCase):
    """Edge case tests for StateManager."""

    def test_corrupted_state_file(self):
        """Test handling corrupted state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)

            # Write corrupted JSON
            state_path = os.path.join(tmpdir, STATE_FILE_NAME)
            with open(state_path, 'w') as f:
                f.write("not valid json{")

            # Should return None and not crash
            state = manager.load_state()
            self.assertIsNone(state)

    def test_partial_state_file(self):
        """Test handling state file with missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StateManager(tmpdir)

            # Write partial state
            state_path = os.path.join(tmpdir, STATE_FILE_NAME)
            with open(state_path, 'w') as f:
                json.dump({"source_file": "/path/to/book.txt"}, f)

            # Should load with defaults for missing fields
            state = manager.load_state()
            self.assertIsNotNone(state)
            self.assertEqual(state.source_file, "/path/to/book.txt")
            self.assertEqual(state.completed_chapters, 0)


if __name__ == "__main__":
    unittest.main()
