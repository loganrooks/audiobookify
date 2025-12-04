"""
Tests for the batch processing module.
"""

import importlib.util
import json
import os
import sys
import tempfile

import pytest

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import directly from the module file to avoid __init__.py dependency issues

spec = importlib.util.spec_from_file_location(
    "batch_processor", os.path.join(parent_dir, "epub2tts_edge", "batch_processor.py")
)
batch_processor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch_processor)

BatchConfig = batch_processor.BatchConfig
BatchResult = batch_processor.BatchResult
BookTask = batch_processor.BookTask
ProcessingStatus = batch_processor.ProcessingStatus
BatchProcessor = batch_processor.BatchProcessor


class TestProcessingStatus:
    """Tests for ProcessingStatus enum."""

    def test_enum_values(self):
        """Test enum value conversion."""
        assert ProcessingStatus("pending") == ProcessingStatus.PENDING
        assert ProcessingStatus("exporting") == ProcessingStatus.EXPORTING
        assert ProcessingStatus("converting") == ProcessingStatus.CONVERTING
        assert ProcessingStatus("completed") == ProcessingStatus.COMPLETED
        assert ProcessingStatus("failed") == ProcessingStatus.FAILED
        assert ProcessingStatus("skipped") == ProcessingStatus.SKIPPED


class TestBookTask:
    """Tests for BookTask class."""

    def test_create_book_task(self):
        """Test basic book task creation."""
        task = BookTask(epub_path="/path/to/book.epub")
        assert task.epub_path == "/path/to/book.epub"
        assert task.status == ProcessingStatus.PENDING
        assert task.txt_path is None
        assert task.m4b_path is None

    def test_basename(self):
        """Test basename extraction."""
        task = BookTask(epub_path="/path/to/My Book.epub")
        assert task.basename == "My Book"

    def test_duration(self):
        """Test duration calculation."""
        task = BookTask(epub_path="/path/to/book.epub")
        assert task.duration is None

        task.start_time = 100.0
        task.end_time = 150.5
        assert task.duration == 50.5

    def test_to_dict(self):
        """Test dictionary serialization."""
        task = BookTask(
            epub_path="/path/to/book.epub",
            status=ProcessingStatus.COMPLETED,
            txt_path="/path/to/book.txt",
            m4b_path="/path/to/book.m4b",
            chapter_count=10,
        )
        task.start_time = 100.0
        task.end_time = 200.0

        d = task.to_dict()
        assert d["epub_path"] == "/path/to/book.epub"
        assert d["status"] == "completed"
        assert d["txt_path"] == "/path/to/book.txt"
        assert d["m4b_path"] == "/path/to/book.m4b"
        assert d["chapter_count"] == 10
        assert d["duration"] == 100.0


class TestBatchConfig:
    """Tests for BatchConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BatchConfig(input_path="/path/to/books")
        assert config.input_path == "/path/to/books"
        assert config.output_dir is None
        assert config.recursive is False
        assert config.speaker == "en-US-AndrewNeural"
        assert config.detection_method == "combined"
        assert config.skip_existing is True
        assert config.export_only is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = BatchConfig(
            input_path="/books",
            output_dir="/output",
            recursive=True,
            speaker="en-GB-SoniaNeural",
            detection_method="toc",
            hierarchy_style="numbered",
            max_depth=2,
            skip_existing=False,
            export_only=True,
        )
        assert config.recursive is True
        assert config.speaker == "en-GB-SoniaNeural"
        assert config.max_depth == 2
        assert config.export_only is True

    def test_to_dict(self):
        """Test dictionary serialization."""
        config = BatchConfig(input_path="/books")
        d = config.to_dict()
        assert d["input_path"] == "/books"
        assert "speaker" in d
        assert "recursive" in d


class TestBatchResult:
    """Tests for BatchResult class."""

    def test_empty_result(self):
        """Test empty batch result."""
        config = BatchConfig(input_path="/books")
        result = BatchResult(config=config)

        assert result.total_count == 0
        assert result.completed_count == 0
        assert result.failed_count == 0
        assert result.skipped_count == 0

    def test_result_counts(self):
        """Test result counting."""
        config = BatchConfig(input_path="/books")
        result = BatchResult(config=config)

        result.tasks = [
            BookTask(epub_path="/book1.epub", status=ProcessingStatus.COMPLETED),
            BookTask(epub_path="/book2.epub", status=ProcessingStatus.COMPLETED),
            BookTask(epub_path="/book3.epub", status=ProcessingStatus.FAILED),
            BookTask(epub_path="/book4.epub", status=ProcessingStatus.SKIPPED),
            BookTask(epub_path="/book5.epub", status=ProcessingStatus.PENDING),
        ]

        assert result.total_count == 5
        assert result.completed_count == 2
        assert result.failed_count == 1
        assert result.skipped_count == 1
        assert result.pending_count == 1

    def test_duration(self):
        """Test duration calculation."""
        config = BatchConfig(input_path="/books")
        result = BatchResult(config=config)

        assert result.duration is None

        result.start_time = 1000.0
        result.end_time = 1500.0
        assert result.duration == 500.0

    def test_get_summary(self):
        """Test summary generation."""
        config = BatchConfig(input_path="/books")
        result = BatchResult(config=config)
        result.start_time = 1000.0
        result.end_time = 1060.0

        result.tasks = [
            BookTask(epub_path="/book1.epub", status=ProcessingStatus.COMPLETED),
            BookTask(epub_path="/book2.epub", status=ProcessingStatus.FAILED),
        ]
        result.tasks[0].start_time = 1000.0
        result.tasks[0].end_time = 1030.0
        result.tasks[1].error_message = "Test error"

        summary = result.get_summary()

        assert "BATCH PROCESSING SUMMARY" in summary
        assert "Total books:     2" in summary
        assert "Completed:       1" in summary
        assert "Failed:          1" in summary
        assert "book1" in summary
        assert "book2" in summary
        assert "Test error" in summary

    def test_to_dict(self):
        """Test dictionary serialization."""
        config = BatchConfig(input_path="/books")
        result = BatchResult(config=config)
        result.tasks = [
            BookTask(epub_path="/book1.epub", status=ProcessingStatus.COMPLETED),
        ]

        d = result.to_dict()
        assert "config" in d
        assert "tasks" in d
        assert "summary" in d
        assert d["summary"]["total"] == 1
        assert d["summary"]["completed"] == 1

    def test_save_report(self):
        """Test saving report to file."""
        config = BatchConfig(input_path="/tmp")
        result = BatchResult(config=config)
        result.tasks = [
            BookTask(epub_path="/book1.epub", status=ProcessingStatus.COMPLETED),
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            report_path = f.name

        try:
            result.save_report(report_path)
            assert os.path.exists(report_path)

            with open(report_path) as f:
                data = json.load(f)

            assert "config" in data
            assert "tasks" in data
            assert "summary" in data
        finally:
            if os.path.exists(report_path):
                os.remove(report_path)


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_discover_books_single_file(self):
        """Test discovering a single EPUB file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = os.path.join(tmpdir, "test.epub")
            open(epub_path, "w").close()

            config = BatchConfig(input_path=epub_path, use_job_isolation=False)
            processor = BatchProcessor(config)
            books = processor.discover_books()

            assert len(books) == 1
            assert books[0] == epub_path

    def test_discover_books_directory(self):
        """Test discovering EPUBs in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            epub1 = os.path.join(tmpdir, "book1.epub")
            epub2 = os.path.join(tmpdir, "book2.epub")
            txt_file = os.path.join(tmpdir, "notes.txt")

            open(epub1, "w").close()
            open(epub2, "w").close()
            open(txt_file, "w").close()

            config = BatchConfig(input_path=tmpdir, use_job_isolation=False)
            processor = BatchProcessor(config)
            books = processor.discover_books()

            assert len(books) == 2
            assert epub1 in books
            assert epub2 in books

    def test_discover_books_recursive(self):
        """Test recursive EPUB discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            epub1 = os.path.join(tmpdir, "book1.epub")
            epub2 = os.path.join(subdir, "book2.epub")

            open(epub1, "w").close()
            open(epub2, "w").close()

            # Non-recursive should only find 1
            config = BatchConfig(input_path=tmpdir, recursive=False, use_job_isolation=False)
            processor = BatchProcessor(config)
            books = processor.discover_books()
            assert len(books) == 1

            # Recursive should find 2
            config = BatchConfig(input_path=tmpdir, recursive=True, use_job_isolation=False)
            processor = BatchProcessor(config)
            books = processor.discover_books()
            assert len(books) == 2

    def test_should_skip_existing(self):
        """Test skip existing file detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = os.path.join(tmpdir, "book.epub")
            m4b_path = os.path.join(tmpdir, "book (en-US-AndrewNeural).m4b")

            open(epub_path, "w").close()

            # Without M4B, should not skip
            config = BatchConfig(input_path=tmpdir, skip_existing=True, use_job_isolation=False)
            processor = BatchProcessor(config)
            assert not processor.should_skip(epub_path)

            # With M4B, should skip
            open(m4b_path, "w").close()
            assert processor.should_skip(epub_path)

            # With skip_existing=False, should not skip
            config = BatchConfig(input_path=tmpdir, skip_existing=False, use_job_isolation=False)
            processor = BatchProcessor(config)
            assert not processor.should_skip(epub_path)

    def test_prepare_queue(self):
        """Test preparing the processing queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            epub1 = os.path.join(tmpdir, "book1.epub")
            epub2 = os.path.join(tmpdir, "book2.epub")
            m4b = os.path.join(tmpdir, "book2 (en-US-AndrewNeural).m4b")

            open(epub1, "w").close()
            open(epub2, "w").close()
            open(m4b, "w").close()

            config = BatchConfig(input_path=tmpdir, skip_existing=True, use_job_isolation=False)
            processor = BatchProcessor(config)
            pending = processor.prepare()

            # book1 should be pending, book2 should be skipped
            assert len(pending) == 1
            assert pending[0].epub_path == epub1

            all_tasks = processor.result.tasks
            assert len(all_tasks) == 2
            assert any(t.status == ProcessingStatus.SKIPPED for t in all_tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
