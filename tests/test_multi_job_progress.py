"""Tests for multi-job progress panel."""

from epub2tts_edge.tui.panels.multi_job_progress import (
    JobProgressInfo,
    JobProgressItem,
    MultiJobProgress,
)


class TestJobProgressInfo:
    """Tests for JobProgressInfo dataclass."""

    def test_init_defaults(self):
        """JobProgressInfo initializes with defaults."""
        info = JobProgressInfo(job_id="test", title="Test", status="Running")
        assert info.job_id == "test"
        assert info.title == "Test"
        assert info.status == "Running"
        assert info.chapter_num == 0
        assert info.total_chapters == 0
        assert info.chapter_title == ""
        assert info.paragraph_num == 0
        assert info.total_paragraphs == 0

    def test_progress_percentage_zero_chapters(self):
        """Progress is 0% with no chapters."""
        info = JobProgressInfo(job_id="test", title="Test", status="Running", total_chapters=0)
        assert info.progress_percentage == 0.0

    def test_progress_percentage_chapter_only(self):
        """Progress calculated from chapters only."""
        info = JobProgressInfo(
            job_id="test",
            title="Test",
            status="Running",
            chapter_num=3,
            total_chapters=10,
            total_paragraphs=0,
        )
        # (3-1)/10 * 100 = 20%
        assert info.progress_percentage == 20.0

    def test_progress_percentage_with_paragraphs(self):
        """Progress includes paragraph progress."""
        info = JobProgressInfo(
            job_id="test",
            title="Test",
            status="Running",
            chapter_num=2,
            total_chapters=4,
            paragraph_num=5,
            total_paragraphs=10,
        )
        # chapter_progress = (2-1)/4 = 0.25
        # para_progress = 5/10 = 0.5
        # overall = (0.25 + 0.5/4) * 100 = (0.25 + 0.125) * 100 = 37.5%
        assert info.progress_percentage == 37.5

    def test_status_text_no_chapters(self):
        """Status text shows status when no chapters."""
        info = JobProgressInfo(job_id="test", title="Test", status="Initializing", total_chapters=0)
        assert info.status_text == "Initializing"

    def test_status_text_with_chapter_title(self):
        """Status text shows chapter info."""
        info = JobProgressInfo(
            job_id="test",
            title="Test",
            status="Running",
            chapter_num=3,
            total_chapters=10,
            chapter_title="The Beginning",
        )
        assert info.status_text == "Ch 3/10: The Beginning"

    def test_status_text_long_chapter_title_truncated(self):
        """Long chapter titles are truncated."""
        info = JobProgressInfo(
            job_id="test",
            title="Test",
            status="Running",
            chapter_num=1,
            total_chapters=5,
            chapter_title="This Is A Very Long Chapter Title That Should Be Truncated",
        )
        assert len(info.status_text) <= 40  # "Ch 1/5: " + 25 chars max

    def test_status_text_no_chapter_title(self):
        """Status text without chapter title."""
        info = JobProgressInfo(
            job_id="test",
            title="Test",
            status="Running",
            chapter_num=2,
            total_chapters=8,
            chapter_title="",
        )
        assert info.status_text == "Chapter 2/8"


class TestJobProgressItem:
    """Tests for JobProgressItem widget."""

    def test_init(self):
        """JobProgressItem initializes correctly."""
        item = JobProgressItem("job1", "Test Book")
        assert item.job_id == "job1"
        assert item._title == "Test Book"
        assert item._status == "Queued"
        assert item._progress == 0.0


class TestMultiJobProgress:
    """Tests for MultiJobProgress panel."""

    def test_init(self):
        """MultiJobProgress initializes correctly."""
        panel = MultiJobProgress()
        assert panel._job_widgets == {}
        assert panel.border_title == "Queue Progress"

    def test_job_widgets_empty(self):
        """Job widgets dict starts empty."""
        panel = MultiJobProgress()
        assert len(panel._job_widgets) == 0

    def test_get_job_ids_empty(self):
        """get_job_ids returns empty list when no jobs."""
        panel = MultiJobProgress()
        assert panel.get_job_ids() == []
