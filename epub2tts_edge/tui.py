"""
Audiobookify TUI - Terminal User Interface

A modern terminal-based interface for converting EPUB files to audiobooks.
Built with Textual for a rich, interactive experience.

Usage:
    python -m epub2tts_edge.tui
    # or
    audiobookify-tui
"""

# Type alias for chapter nodes (to avoid circular imports)
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Log,
    ProgressBar,
    Rule,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker

# Import our modules
from .batch_processor import BatchConfig, BatchProcessor, BookTask, ProcessingStatus
from .job_manager import Job, JobManager, JobStatus
from .voice_preview import AVAILABLE_VOICES, VoicePreview, VoicePreviewConfig

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Preview Tab Data Models
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PreviewChapter:
    """A chapter in the preview with editing state."""

    title: str
    level: int
    word_count: int
    paragraph_count: int
    content_preview: str  # First 500 chars
    included: bool = True
    merged_into: int | None = None  # Index of chapter this merges into
    original_content: str = ""  # Full content for processing


@dataclass
class ChapterPreviewState:
    """State for the preview workflow."""

    source_file: Path
    detection_method: str
    chapters: list[PreviewChapter] = field(default_factory=list)
    modified: bool = False
    book_title: str = ""
    book_author: str = ""

    def get_included_chapters(self) -> list[PreviewChapter]:
        """Get chapters that are included (not excluded or merged)."""
        return [c for c in self.chapters if c.included and c.merged_into is None]

    def get_total_words(self) -> int:
        """Get total word count of included chapters."""
        return sum(c.word_count for c in self.get_included_chapters())

    def get_chapter_selection_string(self) -> str | None:
        """Convert included chapters to a selection string (e.g., '1,3,5-7').

        Returns:
            Selection string for ChapterSelector, or None if all chapters included.
        """
        if not self.chapters:
            return None

        # Get indices of included chapters (1-indexed for user display)
        included_indices = [
            i + 1  # Convert to 1-indexed
            for i, ch in enumerate(self.chapters)
            if ch.included and ch.merged_into is None
        ]

        # If all chapters are included, return None (means "all")
        if len(included_indices) == len(self.chapters):
            return None

        if not included_indices:
            return ""  # Nothing selected

        # Convert to ranges for compact representation
        # e.g., [1, 2, 3, 5, 7, 8, 9] → "1-3,5,7-9"
        ranges: list[str] = []
        start = included_indices[0]
        end = start

        for idx in included_indices[1:]:
            if idx == end + 1:
                # Consecutive
                end = idx
            else:
                # Gap - emit current range
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = end = idx

        # Emit final range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return ",".join(ranges)

    def export_to_text(self, output_path: Path) -> Path:
        """Export preview state to text file format for processing.

        This exports the current preview state (with merges applied) to a text file
        that can be processed by the audio generator.

        Args:
            output_path: Path to write the text file

        Returns:
            Path to the output file
        """
        import re

        with open(output_path, "w", encoding="utf-8") as f:
            # Write metadata header
            title = self.book_title or self.source_file.stem
            author = self.book_author or "Unknown"
            f.write(f"Title: {title}\n")
            f.write(f"Author: {author}\n\n")

            # Write title chapter
            f.write("# Title\n")
            f.write(f"{title}, by {author}\n\n")

            # Write included chapters
            for chapter in self.get_included_chapters():
                # Determine header level based on chapter level
                markers = "#" * min(chapter.level, 6) if chapter.level > 0 else "#"

                f.write(f"{markers} {chapter.title}\n\n")

                # Write paragraphs from original_content
                if chapter.original_content:
                    # Split content into paragraphs and clean up
                    paragraphs = chapter.original_content.split("\n\n")
                    for paragraph in paragraphs:
                        # Clean up text (normalize whitespace, quotes)
                        clean = re.sub(r"[\s\n]+", " ", paragraph.strip())
                        clean = re.sub(r"[\u201c\u201d]", '"', clean)
                        clean = re.sub(r"[\u2018\u2019]", "'", clean)
                        if clean:
                            f.write(f"{clean}\n\n")

        return output_path


class VoicePreviewStatus(Static):
    """Widget to show voice preview generation and playback status."""

    DEFAULT_CSS = """
    VoicePreviewStatus {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    VoicePreviewStatus.idle {
        display: none;
    }

    VoicePreviewStatus.generating {
        color: $warning;
    }

    VoicePreviewStatus.playing {
        color: $success;
    }

    VoicePreviewStatus.done {
        color: $text-muted;
    }

    VoicePreviewStatus.error {
        color: $error;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self.add_class("idle")

    def set_generating(self) -> None:
        """Show generating status."""
        self.remove_class("idle", "playing", "done", "error")
        self.add_class("generating")
        self.update("⏳ Generating preview...")

    def set_playing(self) -> None:
        """Show playing status."""
        self.remove_class("idle", "generating", "done", "error")
        self.add_class("playing")
        self.update("🔊 Playing...")

    def set_done(self) -> None:
        """Show done status briefly, then hide."""
        self.remove_class("idle", "generating", "playing", "error")
        self.add_class("done")
        self.update("✅ Done")

    def set_error(self, msg: str = "Error") -> None:
        """Show error status."""
        self.remove_class("idle", "generating", "playing", "done")
        self.add_class("error")
        self.update(f"❌ {msg}")

    def set_idle(self) -> None:
        """Hide the status widget."""
        self.remove_class("generating", "playing", "done", "error")
        self.add_class("idle")
        self.update("")


class EPUBFileItem(ListItem):
    """A list item representing an EPUB file."""

    def __init__(
        self, path: Path, selected: bool = False, has_resumable_session: bool = False
    ) -> None:
        super().__init__()
        self.path = path
        self.is_selected = selected
        self.has_resumable_session = has_resumable_session

    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.is_selected else "☐"
        resume_indicator = " 🔄" if self.has_resumable_session else ""
        yield Label(f"{checkbox} {self.path.name}{resume_indicator}")

    def toggle(self) -> None:
        self.is_selected = not self.is_selected
        checkbox = "☑" if self.is_selected else "☐"
        resume_indicator = " 🔄" if self.has_resumable_session else ""
        self.query_one(Label).update(f"{checkbox} {self.path.name}{resume_indicator}")


class JobItem(ListItem):
    """A list item representing a saved job with checkbox selection."""

    STATUS_ICONS = {
        JobStatus.PENDING: "⏳",
        JobStatus.EXTRACTING: "📝",
        JobStatus.CONVERTING: "🔊",
        JobStatus.FINALIZING: "📦",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫",
    }

    def __init__(self, job: Job, selected: bool = False) -> None:
        super().__init__()
        self.job = job
        self.is_selected = selected

    def compose(self) -> ComposeResult:
        yield Label(self._build_label())

    def _build_label(self) -> str:
        """Build the display label for this job item."""
        checkbox = "☑" if self.is_selected else "☐"
        status_icon = self.STATUS_ICONS.get(self.job.status, "?")
        book_name = Path(self.job.source_file).stem[:25]
        progress = f"{self.job.completed_chapters}/{self.job.total_chapters}"
        created = datetime.fromtimestamp(self.job.created_at).strftime("%m/%d %H:%M")
        resumable = " 🔄" if self.job.is_resumable else ""
        return f"{checkbox} {status_icon} {book_name} [{progress}] {created}{resumable}"

    def toggle(self) -> None:
        """Toggle selection state."""
        self.is_selected = not self.is_selected
        self.query_one(Label).update(self._build_label())

    def refresh_display(self) -> None:
        """Refresh the display label (e.g., after job update)."""
        self.query_one(Label).update(self._build_label())


class FilePanel(Vertical):
    """Panel for browsing and selecting files (EPUB/MOBI or TXT)."""

    DEFAULT_CSS = """
    FilePanel {
        width: 1fr;
        height: 100%;
        border: round $primary;
        border-title-color: $primary;
        padding: 0 1;
        background: $surface;
    }

    FilePanel > #file-header {
        height: auto;
        margin-bottom: 0;
    }

    FilePanel > #file-header > Label.title {
        text-style: bold;
        color: $primary-lighten-2;
        width: auto;
    }

    FilePanel > #file-header > Label.file-count {
        color: $text-muted;
        margin-left: 1;
    }

    FilePanel > #file-header > Button {
        min-width: 6;
        height: auto;
        padding: 0;
        margin: 0 0 0 1;
    }

    FilePanel > #file-header > Button.active {
        background: $primary;
        color: $text;
    }

    FilePanel > #path-input {
        margin-bottom: 0;
        border: round $primary-darken-1;
    }

    FilePanel > #file-list {
        height: 1fr;
        min-height: 3;
        border: round $primary-darken-2;
        background: $surface-darken-1;
    }

    FilePanel > #file-list > EPUBFileItem {
        height: 1;
        padding: 0;
    }

    FilePanel > #file-list > EPUBFileItem > Label {
        width: 100%;
        padding: 0 1;
    }

    FilePanel > #file-actions {
        height: auto;
        margin-top: 0;
        width: 100%;
    }

    FilePanel > #file-actions > Button {
        min-width: 4;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }

    FilePanel > #file-actions > Button.sel-btn {
        min-width: 6;
    }
    """

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.current_path = Path(initial_path).resolve()
        self.files: list[Path] = []
        self.file_mode = "books"  # "books" or "text"

    def compose(self) -> ComposeResult:
        with Horizontal(id="file-header"):
            yield Label("📁", classes="title", id="panel-title")
            yield Label("(0)", classes="file-count", id="file-count")
            yield Button("📚", id="mode-books", classes="active")
            yield Button("📝", id="mode-text")
        yield Input(
            placeholder="Enter folder path...", value=str(self.current_path), id="path-input"
        )
        yield ListView(id="file-list")
        with Horizontal(id="file-actions"):
            yield Button("All", id="select-all", classes="sel-btn")
            yield Button("None", id="deselect-all", classes="sel-btn")
            yield Button("⟳", id="refresh")

    def on_mount(self) -> None:
        self.scan_directory()

    def set_mode(self, mode: str) -> None:
        """Set the file selection mode."""
        if mode == self.file_mode:
            return

        self.file_mode = mode

        # Update button states
        books_btn = self.query_one("#mode-books", Button)
        text_btn = self.query_one("#mode-text", Button)

        if mode == "books":
            books_btn.add_class("active")
            text_btn.remove_class("active")
        else:
            books_btn.remove_class("active")
            text_btn.add_class("active")

        # Update title
        title = self.query_one("#panel-title", Label)
        if mode == "books":
            title.update("📁 Select Books (EPUB/MOBI/AZW)")
        else:
            title.update("📁 Select Text Files")

        # Rescan directory
        self.scan_directory()

    def scan_directory(self) -> None:
        """Scan current directory for files based on current mode."""
        file_list = self.query_one("#file-list", ListView)
        file_list.clear()

        self.files = []
        resumable_count = 0

        # Get job manager from app if available
        job_manager = getattr(self.app, "job_manager", None)

        if self.current_path.exists() and self.current_path.is_dir():
            # Scan for files based on mode
            if self.file_mode == "books":
                patterns = ["*.epub", "*.mobi", "*.azw", "*.azw3"]
            else:
                patterns = ["*.txt"]

            all_files = []
            for pattern in patterns:
                all_files.extend(self.current_path.glob(pattern))

            for file_path in sorted(set(all_files)):
                self.files.append(file_path)

                # Check for resumable job via JobManager (only for books)
                has_resumable = False
                if self.file_mode == "books" and job_manager:
                    resumable_job = job_manager.find_job_for_source(str(file_path))
                    has_resumable = resumable_job is not None

                if has_resumable:
                    resumable_count += 1

                file_list.append(EPUBFileItem(file_path, has_resumable_session=has_resumable))

        # Update file count with resumable indicator
        count_label = self.query_one("#file-count", Label)
        count = len(self.files)
        resume_text = f"+🔄{resumable_count}" if resumable_count > 0 else ""
        count_label.update(f"({count}{resume_text})")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path-input":
            new_path = Path(event.value).resolve()
            if new_path.exists() and new_path.is_dir():
                self.current_path = new_path
                self.scan_directory()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mode-books":
            self.set_mode("books")
        elif event.button.id == "mode-text":
            self.set_mode("text")
        elif event.button.id == "select-all":
            for item in self.query(EPUBFileItem):
                if not item.is_selected:
                    item.toggle()
        elif event.button.id == "deselect-all":
            for item in self.query(EPUBFileItem):
                if item.is_selected:
                    item.toggle()
        elif event.button.id == "refresh":
            path_input = self.query_one("#path-input", Input)
            self.current_path = Path(path_input.value).resolve()
            self.scan_directory()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, EPUBFileItem):
            event.item.toggle()

    def get_selected_files(self) -> list[Path]:
        """Get list of selected EPUB files."""
        return [item.path for item in self.query(EPUBFileItem) if item.is_selected]


class SettingsPanel(VerticalScroll):
    """Panel for configuring conversion settings (scrollable)."""

    DEFAULT_CSS = """
    SettingsPanel {
        width: 40;
        height: 100%;
        border: round $secondary;
        border-title-color: $secondary;
        padding: 1;
        background: $surface;
    }

    SettingsPanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $secondary-lighten-2;
    }

    SettingsPanel > .setting-row {
        height: auto;
        margin-bottom: 1;
    }

    SettingsPanel > .setting-row > Label {
        width: 15;
    }

    SettingsPanel > .setting-row > Select {
        width: 1fr;
    }

    SettingsPanel > .setting-row > Input {
        width: 1fr;
    }

    SettingsPanel > #preview-voice-btn {
        margin-top: 1;
        margin-bottom: 1;
    }

    SettingsPanel > Label.section-title {
        text-style: bold;
        margin-top: 1;
        color: $secondary-lighten-1;
    }

    SettingsPanel Rule {
        margin-top: 1;
        margin-bottom: 1;
        color: $secondary-darken-2;
    }
    """

    # Common voices - use AVAILABLE_VOICES from voice_preview
    VOICES = [(v["id"], f"{v['name']} ({v['locale'][-2:]})") for v in AVAILABLE_VOICES]

    DETECTION_METHODS = [
        ("combined", "Combined (TOC + Headings)"),
        ("toc", "TOC Only"),
        ("headings", "Headings Only"),
        ("auto", "Auto Detect"),
    ]

    HIERARCHY_STYLES = [
        ("flat", "Flat"),
        ("numbered", "Numbered (1.1, 1.2)"),
        ("arrow", "Arrow (Part > Chapter)"),
        ("breadcrumb", "Breadcrumb (Part / Chapter)"),
        ("indented", "Indented"),
    ]

    RATE_OPTIONS = [
        ("", "Normal"),
        ("+10%", "+10% Faster"),
        ("+20%", "+20% Faster"),
        ("+30%", "+30% Faster"),
        ("+50%", "+50% Faster"),
        ("-10%", "-10% Slower"),
        ("-20%", "-20% Slower"),
        ("-30%", "-30% Slower"),
    ]

    VOLUME_OPTIONS = [
        ("", "Normal"),
        ("+10%", "+10% Louder"),
        ("+20%", "+20% Louder"),
        ("+50%", "+50% Louder"),
        ("-10%", "-10% Quieter"),
        ("-20%", "-20% Quieter"),
        ("-50%", "-50% Quieter"),
    ]

    PAUSE_OPTIONS = [
        (500, "0.5s - Short"),
        (800, "0.8s - Quick"),
        (1200, "1.2s - Default"),
        (1500, "1.5s - Medium"),
        (2000, "2.0s - Long"),
        (3000, "3.0s - Very Long"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("⚙️ Settings", classes="title")

        # Voice settings
        with Horizontal(classes="setting-row"):
            yield Label("Voice:")
            yield Select(
                [(v[1], v[0]) for v in self.VOICES], value="en-US-AndrewNeural", id="voice-select"
            )

        yield Button("🔊 Preview Voice", id="preview-voice-btn", variant="default")
        yield VoicePreviewStatus()

        # v2.1.0: Rate and Volume controls
        yield Label("Voice Adjustments", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Rate:")
            yield Select([(r[1], r[0]) for r in self.RATE_OPTIONS], value="", id="rate-select")

        with Horizontal(classes="setting-row"):
            yield Label("Volume:")
            yield Select([(v[1], v[0]) for v in self.VOLUME_OPTIONS], value="", id="volume-select")

        # Pause settings
        yield Label("Pause Timing", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Sentence:")
            yield Select(
                [(p[1], p[0]) for p in self.PAUSE_OPTIONS],
                value=1200,
                id="sentence-pause-select",
            )

        with Horizontal(classes="setting-row"):
            yield Label("Paragraph:")
            yield Select(
                [(p[1], p[0]) for p in self.PAUSE_OPTIONS],
                value=1200,
                id="paragraph-pause-select",
            )

        yield Rule()

        # Detection settings
        with Horizontal(classes="setting-row"):
            yield Label("Detection:")
            yield Select(
                [(d[1], d[0]) for d in self.DETECTION_METHODS], value="combined", id="detect-select"
            )

        with Horizontal(classes="setting-row"):
            yield Label("Hierarchy:")
            yield Select(
                [(h[1], h[0]) for h in self.HIERARCHY_STYLES], value="flat", id="hierarchy-select"
            )

        yield Button("📋 Preview Chapters", id="preview-chapters-btn", variant="default")
        yield Button("📝 Export & Edit", id="export-text-btn", variant="default")

        # v2.1.0: Chapter selection
        yield Label("Chapter Selection", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Chapters:")
            yield Input(placeholder="e.g., 1-5, 1,3,7", id="chapters-input")

        yield Rule()

        # Processing options
        with Horizontal(classes="setting-row"):
            yield Label("Text Only:")
            yield Switch(id="export-only-switch")

        with Horizontal(classes="setting-row"):
            yield Label("Skip Existing:")
            yield Switch(value=True, id="skip-existing-switch")

        with Horizontal(classes="setting-row"):
            yield Label("Recursive:")
            yield Switch(id="recursive-switch")

        yield Rule()

        # v2.2.0: Audio Quality options
        yield Label("Audio Quality", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Normalize:")
            yield Switch(id="normalize-switch")

        with Horizontal(classes="setting-row"):
            yield Label("Trim Silence:")
            yield Switch(id="trim-silence-switch")

        # v2.2.0: Advanced options
        yield Label("Advanced", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Pronuncia.:")
            yield Input(placeholder="Path to dictionary file", id="pronunciation-input")

        with Horizontal(classes="setting-row"):
            yield Label("Voice Map:")
            yield Input(placeholder="Path to voice mapping", id="voice-mapping-input")

    def get_config(self) -> dict:
        """Get current settings as a dictionary."""
        rate_val = self.query_one("#rate-select", Select).value
        volume_val = self.query_one("#volume-select", Select).value
        chapters_val = self.query_one("#chapters-input", Input).value.strip()
        pronunciation_val = self.query_one("#pronunciation-input", Input).value.strip()
        voice_mapping_val = self.query_one("#voice-mapping-input", Input).value.strip()
        sentence_pause_val = self.query_one("#sentence-pause-select", Select).value
        paragraph_pause_val = self.query_one("#paragraph-pause-select", Select).value

        return {
            "speaker": self.query_one("#voice-select", Select).value,
            "detection_method": self.query_one("#detect-select", Select).value,
            "hierarchy_style": self.query_one("#hierarchy-select", Select).value,
            "export_only": self.query_one("#export-only-switch", Switch).value,
            "skip_existing": self.query_one("#skip-existing-switch", Switch).value,
            "recursive": self.query_one("#recursive-switch", Switch).value,
            # v2.1.0 options
            "tts_rate": rate_val if rate_val else None,
            "tts_volume": volume_val if volume_val else None,
            "chapters": chapters_val if chapters_val else None,
            # Pause settings
            "sentence_pause": sentence_pause_val,
            "paragraph_pause": paragraph_pause_val,
            # v2.2.0 options
            "normalize": self.query_one("#normalize-switch", Switch).value,
            "trim_silence": self.query_one("#trim-silence-switch", Switch).value,
            "pronunciation": pronunciation_val if pronunciation_val else None,
            "voice_mapping": voice_mapping_val if voice_mapping_val else None,
        }


class ProgressPanel(Vertical):
    """Panel for displaying conversion progress."""

    DEFAULT_CSS = """
    ProgressPanel {
        height: auto;
        min-height: 14;
        border: round $success;
        border-title-color: $success;
        padding: 1;
        background: $surface;
    }

    ProgressPanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $success-lighten-2;
    }

    ProgressPanel > #current-book {
        margin-bottom: 1;
    }

    ProgressPanel > #chapter-progress {
        color: $primary;
        margin-bottom: 0;
    }

    ProgressPanel > #paragraph-progress {
        color: $text-muted;
        margin-bottom: 1;
    }

    ProgressPanel > #progress-bar {
        margin-bottom: 1;
    }

    ProgressPanel > #status-text {
        color: $text-muted;
    }

    ProgressPanel > #action-buttons {
        margin-top: 1;
    }

    ProgressPanel > #action-buttons > Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📊 Progress", classes="title")
        yield Label("Ready to convert", id="current-book")
        yield Label("", id="chapter-progress")
        yield Label("", id="paragraph-progress")
        yield ProgressBar(total=100, show_eta=False, id="progress-bar")
        yield Label("Select files and press Start", id="status-text")
        with Horizontal(id="action-buttons"):
            yield Button("▶ Start", id="start-btn", variant="success")
            yield Button("⏹ Stop", id="stop-btn", variant="error", disabled=True)

    def set_progress(self, current: int, total: int, book_name: str = "", status: str = "") -> None:
        """Update progress display."""
        progress = (current / total * 100) if total > 0 else 0
        self.query_one("#progress-bar", ProgressBar).update(progress=progress)
        self.query_one("#current-book", Label).update(
            f"Processing: {book_name}" if book_name else "Ready to convert"
        )
        self.query_one("#status-text", Label).update(status or f"{current}/{total} books processed")

    def set_chapter_progress(
        self,
        chapter_num: int,
        total_chapters: int,
        chapter_title: str,
        paragraph_num: int,
        total_paragraphs: int,
    ) -> None:
        """Update chapter/paragraph progress display."""
        # Calculate overall progress based on chapters and paragraphs
        chapter_progress = (chapter_num - 1) / total_chapters if total_chapters > 0 else 0
        paragraph_progress = paragraph_num / total_paragraphs if total_paragraphs > 0 else 0
        overall = (chapter_progress + (paragraph_progress / total_chapters)) * 100

        self.query_one("#progress-bar", ProgressBar).update(progress=overall)
        self.query_one("#chapter-progress", Label).update(
            f"📖 Chapter {chapter_num}/{total_chapters}: {chapter_title[:40]}"
        )
        self.query_one("#paragraph-progress", Label).update(
            f"   Paragraph {paragraph_num}/{total_paragraphs}"
        )

    def clear_chapter_progress(self) -> None:
        """Clear chapter/paragraph progress display."""
        self.query_one("#chapter-progress", Label).update("")
        self.query_one("#paragraph-progress", Label).update("")

    def set_running(self, running: bool) -> None:
        """Update button states based on running status."""
        self.query_one("#start-btn", Button).disabled = running
        self.query_one("#stop-btn", Button).disabled = not running


class QueuePanel(Vertical):
    """Panel showing the processing queue and results."""

    DEFAULT_CSS = """
    QueuePanel {
        height: 1fr;
        border: round $warning;
        border-title-color: $warning;
        padding: 1;
        background: $surface;
    }

    QueuePanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $warning-lighten-2;
    }

    QueuePanel > #queue-table {
        height: 1fr;
        background: $surface-darken-1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📋 Queue", classes="title")
        yield DataTable(id="queue-table")

    def on_mount(self) -> None:
        table = self.query_one("#queue-table", DataTable)
        table.add_columns("Status", "Book", "Chapters", "Time")

    def add_task(self, task: BookTask) -> None:
        """Add a task to the queue display."""
        table = self.query_one("#queue-table", DataTable)
        status_icon = self._get_status_icon(task.status)
        table.add_row(
            status_icon,
            task.basename[:30],
            str(task.chapter_count) if task.chapter_count else "-",
            self._format_duration(task.duration),
            key=task.epub_path,
        )

    def update_task(self, task: BookTask) -> None:
        """Update a task in the queue display."""
        table = self.query_one("#queue-table", DataTable)
        try:
            row_key = table.get_row_index(task.epub_path)
            status_icon = self._get_status_icon(task.status)
            table.update_cell_at((row_key, 0), status_icon)
            table.update_cell_at(
                (row_key, 2), str(task.chapter_count) if task.chapter_count else "-"
            )
            table.update_cell_at((row_key, 3), self._format_duration(task.duration))
        except Exception:
            pass

    def clear_queue(self) -> None:
        """Clear the queue display."""
        table = self.query_one("#queue-table", DataTable)
        table.clear()

    def _get_status_icon(self, status: ProcessingStatus) -> str:
        icons = {
            ProcessingStatus.PENDING: "⏳",
            ProcessingStatus.EXPORTING: "📝",
            ProcessingStatus.CONVERTING: "🔊",
            ProcessingStatus.COMPLETED: "✅",
            ProcessingStatus.FAILED: "❌",
            ProcessingStatus.SKIPPED: "⏭️",
        }
        return icons.get(status, "?")

    def _format_duration(self, duration: float | None) -> str:
        if duration is None:
            return "-"
        mins = int(duration // 60)
        secs = int(duration % 60)
        return f"{mins}m {secs}s"


class LogPanel(Vertical):
    """Panel for displaying log output."""

    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        min-height: 10;
        border: round $primary-darken-1;
        border-title-color: $primary-darken-1;
        padding: 1;
        background: $surface;
    }

    LogPanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary-lighten-1;
    }

    LogPanel > #log-output {
        height: 1fr;
        min-height: 8;
        background: $surface-darken-1;
        border: round $primary-darken-2;
        scrollbar-gutter: stable;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📜 Log", classes="title")
        yield Log(id="log-output", auto_scroll=True, max_lines=1000)

    def write(self, message: str) -> None:
        """Write a message to the log."""
        self.query_one("#log-output", Log).write_line(message)

    def clear(self) -> None:
        """Clear the log."""
        self.query_one("#log-output", Log).clear()


class JobsPanel(Vertical):
    """Panel showing saved jobs with checkbox selection for multi-select operations."""

    DEFAULT_CSS = """
    JobsPanel {
        height: 1fr;
        border: round $secondary;
        border-title-color: $secondary;
        padding: 0 1;
        background: $surface;
    }

    JobsPanel > #jobs-header {
        height: auto;
        margin-bottom: 0;
    }

    JobsPanel > #jobs-header > Label.title {
        text-style: bold;
        color: $secondary-lighten-2;
        width: auto;
    }

    JobsPanel > #jobs-header > Label.count {
        color: $text-muted;
        margin-left: 1;
    }

    JobsPanel > #jobs-list {
        height: 1fr;
        background: $surface-darken-1;
    }

    JobsPanel > #jobs-buttons {
        height: auto;
        margin-top: 0;
    }

    JobsPanel Button {
        min-width: 4;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }

    JobsPanel Button.resume {
        background: $success-darken-1;
    }

    JobsPanel Button.delete {
        background: $error-darken-1;
    }

    JobsPanel Button.move {
        background: $primary-darken-1;
    }

    JobsPanel Button.sel-btn {
        min-width: 6;
    }
    """

    def __init__(self, job_manager: JobManager | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.job_manager = job_manager or JobManager()

    def compose(self) -> ComposeResult:
        with Horizontal(id="jobs-header"):
            yield Label("💼 Jobs", classes="title")
            yield Label("(0)", id="job-count", classes="count")
        yield ListView(id="jobs-list")
        with Horizontal(id="jobs-buttons"):
            yield Button("All", id="job-select-all", classes="sel-btn")
            yield Button("None", id="job-deselect-all", classes="sel-btn")
            yield Button("↑", id="job-move-up", classes="move")
            yield Button("↓", id="job-move-down", classes="move")
            yield Button("▶", id="job-resume", classes="resume")
            yield Button("🗑", id="job-delete", classes="delete")
            yield Button("⟳", id="job-refresh")

    def on_mount(self) -> None:
        self.refresh_jobs()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle item selection (toggle checkbox)."""
        if isinstance(event.item, JobItem):
            event.item.toggle()

    def refresh_jobs(self) -> None:
        """Refresh the job list from disk."""
        jobs_list = self.query_one("#jobs-list", ListView)
        jobs_list.clear()

        jobs = self.job_manager.list_jobs(include_completed=True)
        for job in jobs:
            jobs_list.append(JobItem(job))

        # Update count label
        count_label = self.query_one("#job-count", Label)
        job_count = len(jobs)
        count_label.update(f"({job_count})")

    def get_selected_jobs(self) -> list[Job]:
        """Get all selected jobs."""
        return [item.job for item in self.query(JobItem) if item.is_selected]

    def get_selected_job(self) -> Job | None:
        """Get the first selected job (for backward compatibility)."""
        selected = self.get_selected_jobs()
        return selected[0] if selected else None

    def get_resumable_selected_jobs(self) -> list[Job]:
        """Get selected jobs that can be resumed."""
        return [job for job in self.get_selected_jobs() if job.is_resumable]

    def delete_selected_jobs(self) -> int:
        """Delete all selected jobs. Returns count of deleted jobs."""
        deleted = 0
        for job in self.get_selected_jobs():
            if self.job_manager.delete_job(job.job_id):
                deleted += 1
        self.refresh_jobs()
        return deleted

    def select_all(self) -> None:
        """Select all jobs."""
        for item in self.query(JobItem):
            if not item.is_selected:
                item.toggle()

    def deselect_all(self) -> None:
        """Deselect all jobs."""
        for item in self.query(JobItem):
            if item.is_selected:
                item.toggle()

    def move_selected_up(self) -> None:
        """Move selected jobs up in the list (for queue priority)."""
        jobs_list = self.query_one("#jobs-list", ListView)
        items = list(self.query(JobItem))

        # Find indices of selected items
        selected_indices = [i for i, item in enumerate(items) if item.is_selected]

        if not selected_indices or selected_indices[0] == 0:
            return  # Can't move up if already at top or nothing selected

        # Move each selected item up by one position
        for idx in selected_indices:
            if idx > 0:
                # Swap with previous item
                items[idx], items[idx - 1] = items[idx - 1], items[idx]

        # Rebuild the list
        jobs_list.clear()
        for item in items:
            jobs_list.append(JobItem(item.job, selected=item.is_selected))

    def move_selected_down(self) -> None:
        """Move selected jobs down in the list (for queue priority)."""
        jobs_list = self.query_one("#jobs-list", ListView)
        items = list(self.query(JobItem))

        # Find indices of selected items (in reverse order for proper movement)
        selected_indices = [i for i, item in enumerate(items) if item.is_selected]

        if not selected_indices or selected_indices[-1] == len(items) - 1:
            return  # Can't move down if already at bottom or nothing selected

        # Move each selected item down by one position (process in reverse)
        for idx in reversed(selected_indices):
            if idx < len(items) - 1:
                # Swap with next item
                items[idx], items[idx + 1] = items[idx + 1], items[idx]

        # Rebuild the list
        jobs_list.clear()
        for item in items:
            jobs_list.append(JobItem(item.job, selected=item.is_selected))


# ─────────────────────────────────────────────────────────────────────────────
# Preview Tab Components
# ─────────────────────────────────────────────────────────────────────────────


class ChapterPreviewItem(ListItem):
    """Interactive chapter item with selection for batch operations."""

    class Clicked(Message):
        """Message sent when chapter item is clicked with modifier info."""

        def __init__(self, item: "ChapterPreviewItem", shift: bool) -> None:
            super().__init__()
            self.item = item
            self.shift = shift

    def __init__(self, chapter: PreviewChapter, index: int) -> None:
        super().__init__()
        self.chapter = chapter
        self.index = index
        self.is_selected = False  # For batch operations (merge/delete)

    def compose(self) -> ComposeResult:
        yield Label(self._build_label())

    def _build_label(self) -> str:
        """Build the display label for this chapter."""
        # Checkbox for batch selection (editing only, not export)
        checkbox = "☑" if self.is_selected else "☐"

        indent = "  " * max(0, self.chapter.level - 1)

        # Truncate title if needed
        title = self.chapter.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Stats
        stats = f"({self.chapter.word_count:,}w)"

        return f"{checkbox} {indent}{title} {stats}"

    def on_click(self, event: Click) -> None:
        """Handle click with shift detection for range selection."""
        # Find parent PreviewPanel and call handler directly
        # This avoids message bubbling issues
        for ancestor in self.ancestors:
            if isinstance(ancestor, PreviewPanel):
                ancestor._handle_item_click(self, event.shift)
                break
        event.stop()

    def toggle_selection(self) -> None:
        """Toggle selection for batch operations."""
        self.is_selected = not self.is_selected
        self.refresh_display()
        # Update CSS class for visual feedback
        if self.is_selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    def set_selected(self, selected: bool) -> None:
        """Set selection state directly (for range selection)."""
        if self.is_selected != selected:
            self.is_selected = selected
            self.refresh_display()
            if self.is_selected:
                self.add_class("selected")
            else:
                self.remove_class("selected")

    def refresh_display(self) -> None:
        """Refresh the display."""
        self.query_one(Label).update(self._build_label())


class PreviewPanel(Vertical):
    """Panel for interactive chapter preview and editing."""

    DEFAULT_CSS = """
    PreviewPanel {
        height: 100%;
    }

    PreviewPanel > #preview-header {
        height: auto;
        padding: 0 1;
        background: $surface-darken-1;
    }

    PreviewPanel > #preview-header > Label {
        margin-right: 1;
    }

    PreviewPanel > #preview-header > #book-title {
        width: 1fr;
    }

    PreviewPanel > #preview-header > #chapter-stats {
        color: $text-muted;
    }

    PreviewPanel > #chapter-tree {
        height: 1fr;
        border: solid $primary-darken-2;
        margin: 0;
    }

    PreviewPanel > #content-preview {
        height: auto;
        max-height: 8;
        background: $surface-darken-2;
        padding: 0 1;
        margin: 0;
        display: none;
    }

    PreviewPanel > #content-preview.visible {
        display: block;
    }

    PreviewPanel > #preview-actions {
        height: auto;
        padding: 0;
        margin-top: 0;
    }

    PreviewPanel > #preview-actions > Button {
        min-width: 6;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }

    PreviewPanel > #preview-actions > Button.approve {
        background: $success-darken-1;
    }

    PreviewPanel > #no-preview {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    PreviewPanel > #preview-instructions {
        height: auto;
        padding: 0 1;
        color: $text-muted;
        text-style: italic;
        display: none;
    }

    PreviewPanel > #preview-instructions.visible {
        display: block;
    }

    ChapterPreviewItem {
        height: auto;
        padding: 0 1;
    }

    ChapterPreviewItem.selected {
        background: $primary-darken-2;
    }

    ChapterPreviewItem.selected Label {
        color: $text;
        text-style: bold;
    }
    """

    MAX_UNDO_STACK = 20  # Limit undo history to prevent memory issues

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.preview_state: ChapterPreviewState | None = None
        self._undo_stack: list[list[PreviewChapter]] = []  # Stack of chapter snapshots
        self._last_selected_index: int | None = (
            None  # Anchor for shift-click range select  # Track if shift key is held  # Stack of chapter snapshots
        )

    def compose(self) -> ComposeResult:
        # Header with book info
        with Horizontal(id="preview-header"):
            yield Label("📖", id="book-icon")
            yield Label("Select a file and click 'Preview Chapters'", id="book-title")
            yield Label("", id="chapter-stats")

        # Placeholder when no preview
        yield Static(
            "Select a file and press 'Preview Chapters' to see chapter breakdown",
            id="no-preview",
        )

        # Instruction label for editing - CLEAR that Start processes ALL
        yield Label(
            "📝 Edit: Click=select, Shift+Click=range | Merge/Delete selected | Start=ALL",
            id="preview-instructions",
        )

        # Chapter tree (hidden initially)
        yield ListView(id="chapter-tree")

        # Content preview pane (expandable)
        yield Static("", id="content-preview")

        # Action buttons
        with Horizontal(id="preview-actions"):
            yield Button("Select All", id="preview-select-all")
            yield Button("Select None", id="preview-select-none")
            yield Button("✏️ Edit", id="preview-edit", disabled=True)
            yield Button("🔗 Merge", id="preview-merge", disabled=True)
            yield Button("🗑️ Delete", id="preview-delete", disabled=True)
            yield Button("↩️ Undo", id="preview-undo", disabled=True)
            yield Button("▶️ Start All", id="preview-approve", classes="approve", disabled=True)

    def on_mount(self) -> None:
        """Hide the chapter tree initially."""
        self.query_one("#chapter-tree").display = False

    def load_chapters(
        self,
        source_file: Path,
        chapters: list[PreviewChapter],
        detection_method: str,
        book_title: str = "",
        book_author: str = "",
    ) -> None:
        """Load chapters into the preview panel."""
        self.preview_state = ChapterPreviewState(
            source_file=source_file,
            detection_method=detection_method,
            chapters=chapters,
            book_title=book_title,
            book_author=book_author,
        )

        # Clear undo stack for new book
        self._undo_stack.clear()

        # Update header
        book_name = source_file.stem
        if len(book_name) > 40:
            book_name = book_name[:37] + "..."
        self.query_one("#book-title", Label).update(book_name)

        # Update stats
        total_chapters = len(chapters)
        total_words = sum(c.word_count for c in chapters)
        self.query_one("#chapter-stats", Label).update(f"{total_chapters} ch, {total_words:,}w")

        # Hide placeholder, show tree and instructions
        self.query_one("#no-preview").display = False
        self.query_one("#preview-instructions").add_class("visible")
        chapter_tree = self.query_one("#chapter-tree", ListView)
        chapter_tree.display = True

        # Populate chapter list
        chapter_tree.clear()
        for i, chapter in enumerate(chapters):
            chapter_tree.append(ChapterPreviewItem(chapter, i))

        # Enable approve button, update other buttons
        self.query_one("#preview-approve", Button).disabled = False
        self._update_action_buttons()

    def clear_preview(self) -> None:
        """Clear the current preview."""
        self.preview_state = None
        self._undo_stack.clear()
        self.query_one("#book-title", Label).update("Select a file and click 'Preview Chapters'")
        self.query_one("#chapter-stats", Label).update("")
        self.query_one("#no-preview").display = True
        self.query_one("#preview-instructions").remove_class("visible")
        self.query_one("#chapter-tree").display = False
        self.query_one("#chapter-tree", ListView).clear()
        self.query_one("#content-preview").display = False
        self.query_one("#preview-approve", Button).disabled = True
        self.query_one("#preview-undo", Button).disabled = True
        self.query_one("#preview-merge", Button).disabled = True
        self.query_one("#preview-delete", Button).disabled = True
        self.query_one("#preview-edit", Button).disabled = True

    def has_chapters(self) -> bool:
        """Check if there are chapters loaded."""
        return self.preview_state is not None and len(self.preview_state.chapters) > 0

    def get_included_chapters(self) -> list[PreviewChapter]:
        """Get chapters that are included."""
        if not self.preview_state:
            return []
        return self.preview_state.get_included_chapters()

    def select_all(self) -> None:
        """Select all chapters for batch operations."""
        if not self.preview_state:
            return
        for item in self.query(ChapterPreviewItem):
            if not item.is_selected:
                item.is_selected = True
                item.add_class("selected")
                item.refresh_display()
        self._update_stats()
        self._update_action_buttons()

    def select_none(self) -> None:
        """Deselect all chapters."""
        if not self.preview_state:
            return
        self._clear_all_selections()
        self._update_stats()
        self._update_action_buttons()

    def toggle_content_preview(self) -> None:
        """Toggle the content preview pane."""
        content_preview = self.query_one("#content-preview", Static)
        chapter_tree = self.query_one("#chapter-tree", ListView)

        if content_preview.display:
            content_preview.display = False
            content_preview.remove_class("visible")
        else:
            # Get selected chapter
            if chapter_tree.highlighted_child:
                item = chapter_tree.highlighted_child
                if isinstance(item, ChapterPreviewItem):
                    preview_text = item.chapter.content_preview or "(No content preview available)"
                    content_preview.update(f"Preview: {preview_text}")
                    content_preview.display = True
                    content_preview.add_class("visible")

    def _update_stats(self) -> None:
        """Update the stats display."""
        if not self.preview_state:
            return
        total_chapters = len(self.preview_state.chapters)
        total_words = sum(c.word_count for c in self.preview_state.chapters)
        selected_count = len(self._get_selected_items())

        # Show total chapters (what will be processed) and edit selection
        if selected_count > 0:
            self.query_one("#chapter-stats", Label).update(
                f"{total_chapters} chapters, {total_words:,}w | {selected_count} selected for edit"
            )
        else:
            self.query_one("#chapter-stats", Label).update(
                f"{total_chapters} chapters, {total_words:,}w"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "preview-select-all":
            self.select_all()
        elif event.button.id == "preview-select-none":
            self.select_none()
        elif event.button.id == "preview-edit":
            self.edit_highlighted_title()
        elif event.button.id == "preview-merge":
            self.batch_merge()
        elif event.button.id == "preview-delete":
            self.batch_delete()
        elif event.button.id == "preview-undo":
            self.undo()
        elif event.button.id == "preview-approve":
            # Bubble up to app
            self.post_message(self.ApproveAndStart())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle ListView selection - only for keyboard navigation (Enter key).

        Note: Click-based selection is handled by on_chapter_preview_item_clicked
        to properly detect shift modifier for range selection.
        """
        # ListView.Selected is triggered by Enter key on highlighted item
        # We still want Enter to toggle selection
        if isinstance(event.item, ChapterPreviewItem):
            event.item.toggle_selection()
            self._last_selected_index = event.item.index
            self._update_stats()
            self._update_action_buttons()

    def _handle_item_click(self, item: ChapterPreviewItem, shift: bool) -> None:
        """Handle chapter item click with shift detection for range selection.

        Called directly from ChapterPreviewItem.on_click to avoid message bubbling issues.

        Args:
            item: The clicked chapter item
            shift: True if shift key was held during click
        """
        clicked_index = item.index

        if shift and self._last_selected_index is not None:
            # Range selection: select all items from anchor to clicked
            self._select_range(self._last_selected_index, clicked_index)
        else:
            # Regular click: toggle selection, update anchor point
            item.toggle_selection()
            self._last_selected_index = clicked_index

        self._update_stats()
        self._update_action_buttons()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update buttons when highlight changes."""
        self._update_action_buttons()

    def _get_highlighted_item(self) -> ChapterPreviewItem | None:
        """Get the currently highlighted chapter item."""
        chapter_tree = self.query_one("#chapter-tree", ListView)
        if chapter_tree.highlighted_child:
            item = chapter_tree.highlighted_child
            if isinstance(item, ChapterPreviewItem):
                return item
        return None

    def _get_next_item(self, current: ChapterPreviewItem) -> ChapterPreviewItem | None:
        """Get the chapter item after the current one."""
        items = list(self.query(ChapterPreviewItem))
        try:
            idx = items.index(current)
            if idx + 1 < len(items):
                return items[idx + 1]
        except ValueError:
            pass
        return None

    def _update_action_buttons(self) -> None:
        """Update merge/delete/undo/edit button states based on selection."""
        selected_count = len(self._get_selected_items())
        selected_indices = self._get_selected_indices()
        highlighted = self._get_highlighted_item()

        merge_btn = self.query_one("#preview-merge", Button)
        delete_btn = self.query_one("#preview-delete", Button)
        undo_btn = self.query_one("#preview-undo", Button)
        edit_btn = self.query_one("#preview-edit", Button)

        # Update button labels with selection count
        if selected_count > 0:
            delete_btn.label = f"🗑️ Delete ({selected_count})"
        else:
            delete_btn.label = "🗑️ Delete"

        if selected_count >= 2:
            merge_btn.label = f"🔗 Merge ({selected_count})"
        else:
            merge_btn.label = "🔗 Merge"

        # Enable delete if at least one selected
        delete_btn.disabled = selected_count < 1

        # Enable merge if 2+ adjacent chapters selected
        if selected_count >= 2:
            # Check if adjacent
            selected_indices.sort()
            is_adjacent = all(
                selected_indices[i + 1] - selected_indices[i] == 1
                for i in range(len(selected_indices) - 1)
            )
            merge_btn.disabled = not is_adjacent
        else:
            merge_btn.disabled = True

        # Undo is enabled if there's something in the stack
        undo_btn.disabled = len(self._undo_stack) == 0

        # Edit is enabled if there's a highlighted item
        edit_btn.disabled = highlighted is None

    def _save_undo_state(self) -> None:
        """Save current chapters to undo stack (deep copy)."""
        if not self.preview_state:
            return
        from copy import deepcopy

        snapshot = deepcopy(self.preview_state.chapters)
        self._undo_stack.append(snapshot)

        # Enforce stack size limit to prevent memory issues
        while len(self._undo_stack) > self.MAX_UNDO_STACK:
            self._undo_stack.pop(0)

    def _rebuild_chapter_list(self) -> None:
        """Rebuild the ListView from current chapters."""
        if not self.preview_state:
            return

        chapter_tree = self.query_one("#chapter-tree", ListView)
        chapter_tree.clear()

        for i, chapter in enumerate(self.preview_state.chapters):
            chapter_tree.append(ChapterPreviewItem(chapter, i))

    def merge_with_next(self) -> None:
        """Merge highlighted chapter with the one below it - visually combines them."""
        if not self.preview_state:
            return

        target_item = self._get_highlighted_item()
        if not target_item:
            self.app.notify("Highlight a chapter first", severity="warning")
            return

        next_item = self._get_next_item(target_item)
        if not next_item:
            self.app.notify("No chapter below to merge with", severity="warning")
            return

        # Save state for undo BEFORE making changes
        self._save_undo_state()

        target = target_item.chapter
        source = next_item.chapter

        # Combine titles
        target.title = f"{target.title} + {source.title}"

        # Merge content
        merged_content = []
        if target.original_content:
            merged_content.append(target.original_content)
        if source.original_content:
            merged_content.append(source.original_content)
        target.original_content = "\n\n".join(merged_content)

        # Combine stats
        target.word_count += source.word_count
        target.paragraph_count += source.paragraph_count

        # Remove the source chapter from the list
        self.preview_state.chapters.remove(source)

        # Rebuild the list view
        self._rebuild_chapter_list()

        # Mark state as modified
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Merged: {target.title}", severity="information")

    def delete_chapter(self) -> None:
        """Delete the highlighted chapter from the list."""
        if not self.preview_state:
            return

        item = self._get_highlighted_item()
        if not item:
            self.app.notify("Highlight a chapter first", severity="warning")
            return

        # Prevent deleting the last chapter
        if len(self.preview_state.chapters) <= 1:
            self.app.notify("Cannot delete the last chapter", severity="error")
            return

        # Save state for undo BEFORE making changes
        self._save_undo_state()

        chapter = item.chapter

        # Remove from chapters list
        self.preview_state.chapters.remove(chapter)

        # Rebuild the list view
        self._rebuild_chapter_list()

        # Mark state as modified
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Deleted: {chapter.title}", severity="information")

    def undo(self) -> None:
        """Undo the last merge or delete operation."""
        if not self.preview_state or not self._undo_stack:
            return

        # Restore chapters from undo stack
        self.preview_state.chapters = self._undo_stack.pop()

        # Rebuild the list view
        self._rebuild_chapter_list()

        self._update_stats()
        self._update_action_buttons()
        self.app.notify("Undo successful", severity="information")

    def _get_selected_items(self) -> list["ChapterPreviewItem"]:
        """Get all selected chapter items in order."""
        list_view = self.query_one("#chapter-tree", ListView)
        selected = []
        for item in list_view.children:
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                selected.append(item)
        return selected

    def _get_selected_indices(self) -> list[int]:
        """Get indices of all selected items."""
        list_view = self.query_one("#chapter-tree", ListView)
        indices = []
        for i, item in enumerate(list_view.children):
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                indices.append(i)
        return indices

    def _clear_all_selections(self) -> None:
        """Clear all selections."""
        list_view = self.query_one("#chapter-tree", ListView)
        for item in list_view.children:
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                item.is_selected = False
                item.remove_class("selected")
                item.refresh_display()

    def _select_range(self, start_index: int, end_index: int) -> None:
        """Select all chapters between start and end indices (inclusive).

        Args:
            start_index: Starting index (anchor point)
            end_index: Ending index (clicked item)
        """
        # Ensure start <= end
        if start_index > end_index:
            start_index, end_index = end_index, start_index

        items = list(self.query(ChapterPreviewItem))
        for item in items:
            if start_index <= item.index <= end_index:
                item.set_selected(True)

    def batch_delete(self) -> None:
        """Delete all selected chapters at once."""
        if not self.preview_state:
            return

        selected = self._get_selected_items()
        if not selected:
            self.app.notify("Select chapters first (click to select)", severity="warning")
            return

        # Prevent deleting all chapters
        remaining = len(self.preview_state.chapters) - len(selected)
        if remaining < 1:
            self.app.notify("Cannot delete all chapters. Keep at least one.", severity="error")
            return

        # Save state for undo
        self._save_undo_state()

        # Get chapters to delete
        chapters_to_delete = [item.chapter for item in selected]
        deleted_count = len(chapters_to_delete)

        # Remove chapters
        for chapter in chapters_to_delete:
            self.preview_state.chapters.remove(chapter)

        # Rebuild UI
        self._rebuild_chapter_list()
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Deleted {deleted_count} chapter(s)", severity="information")

    def batch_merge(self) -> None:
        """Merge all selected chapters if they are adjacent."""
        if not self.preview_state:
            return

        indices = self._get_selected_indices()
        if len(indices) < 2:
            self.app.notify("Select at least 2 adjacent chapters to merge", severity="warning")
            return

        # Check if indices are consecutive (adjacent)
        indices.sort()
        is_adjacent = all(indices[i + 1] - indices[i] == 1 for i in range(len(indices) - 1))

        if not is_adjacent:
            self.app.notify("Selected chapters must be adjacent to merge", severity="error")
            return

        # Save state for undo
        self._save_undo_state()

        # Get chapters to merge (in order)
        chapters = [self.preview_state.chapters[i] for i in indices]
        target = chapters[0]

        # Combine titles
        titles = [c.title for c in chapters]
        target.title = " + ".join(titles)

        # Merge content
        contents = []
        for c in chapters:
            if c.original_content:
                contents.append(c.original_content)
        target.original_content = "\n\n".join(contents)

        # Sum stats
        target.word_count = sum(c.word_count for c in chapters)
        target.paragraph_count = sum(c.paragraph_count for c in chapters)

        # Remove merged chapters (all except first)
        for chapter in chapters[1:]:
            self.preview_state.chapters.remove(chapter)

        # Rebuild UI
        self._rebuild_chapter_list()
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(
            f"Merged {len(chapters)} chapters into '{target.title[:30]}...'",
            severity="information",
        )

    def edit_highlighted_title(self) -> None:
        """Edit the title of the highlighted chapter using an inline Input."""
        if not self.preview_state:
            return

        highlighted = self._get_highlighted_item()
        if not highlighted:
            self.app.notify("Highlight a chapter to edit its title", severity="warning")
            return

        # Create an input with current title
        from textual.widgets import Input

        # Create an Input widget
        input_widget = Input(
            value=highlighted.chapter.title,
            id="title-edit-input",
            placeholder="Enter new title...",
        )
        input_widget.chapter_item = highlighted  # Store reference to item

        # Replace the label temporarily with input
        label = highlighted.query_one(Label)
        label.display = False
        highlighted.mount(input_widget)
        input_widget.focus()

    def _finish_title_edit(self, input_widget, new_title: str) -> None:
        """Complete the title edit operation."""
        chapter_item = input_widget.chapter_item

        if new_title.strip():
            # Save undo state
            self._save_undo_state()

            # Update the chapter title
            chapter_item.chapter.title = new_title.strip()
            self.preview_state.modified = True

            self.app.notify(f"Renamed to: {new_title[:30]}...", severity="information")

        # Remove input and restore label
        input_widget.remove()
        label = chapter_item.query_one(Label)
        label.display = True
        chapter_item.refresh_display()

    def on_input_submitted(self, event) -> None:
        """Handle Enter key in title edit input."""
        if event.input.id == "title-edit-input":
            self._finish_title_edit(event.input, event.value)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for chapter editing."""
        if event.key == "e" or event.key == "E":
            # Edit highlighted chapter title
            self.edit_highlighted_title()
            event.stop()
        elif event.key == "escape":
            # Cancel title edit if active
            try:
                input_widget = self.query_one("#title-edit-input", Input)
                chapter_item = input_widget.chapter_item
                input_widget.remove()
                label = chapter_item.query_one(Label)
                label.display = True
                event.stop()
            except Exception:
                pass  # No edit in progress
        elif event.key == "space":
            # Space toggles selection on highlighted - track anchor
            highlighted = self._get_highlighted_item()
            if highlighted:
                self._last_selected_index = highlighted.index  # No edit in progress

    class ApproveAndStart(Message):
        """Message sent when user clicks Approve & Start."""

        pass


class HelpScreen(ModalScreen):
    """Modal screen showing all keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
        Binding("f1", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 65;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }

    #help-container > Label.title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #help-container > Label.section {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }

    #help-container > Static {
        height: 1;
    }

    #help-container > Static.hint {
        color: $text-muted;
        text-align: center;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("⌨️  Keyboard Shortcuts", classes="title")

            yield Label("── Global ──", classes="section")
            yield Static("  q              Quit application")
            yield Static("  s              Start conversion")
            yield Static("  Escape         Stop conversion")
            yield Static("  r              Refresh file list")
            yield Static("  Tab            Focus next panel")
            yield Static("  Shift+Tab      Focus previous panel")
            yield Static("  1-5            Switch tabs (Prog/Prev/Queue/Jobs/Log)")
            yield Static("  ?/F1           Show this help")
            yield Static("  Ctrl+D         Toggle debug mode")

            yield Label("── File Selection ──", classes="section")
            yield Static("  a              Select all files")
            yield Static("  d              Deselect all")
            yield Static("  /              Focus path input")
            yield Static("  Backspace      Go to parent directory")

            yield Label("── Preview Tab ──", classes="section")
            yield Static("  Click          Select/deselect chapter")
            yield Static("  Shift+Click    Range select (anchor to click)")
            yield Static("  Space          Toggle chapter selection")
            yield Static("  m              Merge with next chapter")
            yield Static("  x              Delete highlighted chapter")
            yield Static("  u              Undo last merge/delete")
            yield Static("  e              Edit chapter title")

            yield Label("── Jobs ──", classes="section")
            yield Static("  R              Resume selected jobs")
            yield Static("  X              Delete selected jobs")
            yield Static("  ↑/↓            Reorder in queue")

            yield Label("── Voice ──", classes="section")
            yield Static("  p              Preview selected voice")

            yield Label("── Tips ──", classes="section")
            yield Static("  Preview: M=merge↓, X=delete, U=undo")
            yield Static("  Font Size: Ctrl/Cmd + Plus/Minus")

            yield Static("Press Escape, ? or F1 to close", classes="hint")

    def action_dismiss(self) -> None:
        """Close the help screen."""
        self.dismiss()


class AudiobookifyApp(App):
    """Main Audiobookify TUI Application."""

    TITLE = "Audiobookify"
    SUB_TITLE = "EPUB to Audiobook Converter"

    CSS = """
    #app-container {
        width: 100%;
        height: 100%;
    }

    #left-column {
        width: 2fr;
        height: 100%;
        min-width: 30;
    }

    #right-column {
        width: 1fr;
        height: 100%;
        min-width: 35;
        max-width: 50;
    }

    FilePanel {
        height: 1fr;
        min-height: 10;
        margin-bottom: 1;
    }

    #bottom-tabs {
        height: 1fr;
        min-height: 15;
    }

    /* Fix TabbedContent internal height propagation */
    #bottom-tabs > ContentSwitcher {
        height: 1fr;
    }

    #bottom-tabs TabPane {
        height: 100%;
        padding: 0;
    }

    ProgressPanel {
        height: 100%;
    }

    QueuePanel {
        height: 100%;
    }

    LogPanel {
        height: 100%;
    }

    JobsPanel {
        height: 100%;
    }
    """

    BINDINGS = [
        # Core actions
        Binding("q", "quit", "Quit"),
        Binding("s", "start", "Start"),
        Binding("escape", "stop", "Stop"),
        Binding("r", "refresh", "Refresh"),
        # File selection
        Binding("a", "select_all", "Select All"),
        Binding("d", "deselect_all", "Deselect All"),
        Binding("p", "preview_voice", "Preview Voice"),
        # Navigation
        Binding("slash", "focus_path", "Path", show=False),
        Binding("backspace", "parent_dir", "Parent", show=False),
        # Tab switching (1-5 for bottom tabs)
        Binding("1", "tab_progress", "Progress", show=False),
        Binding("2", "tab_preview", "Preview", show=False),
        Binding("3", "tab_queue", "Queue", show=False),
        Binding("4", "tab_jobs", "Jobs", show=False),
        Binding("5", "tab_log", "Log", show=False),
        # Job operations (uppercase for safety)
        Binding("R", "resume_jobs", "Resume", show=False),
        Binding("X", "delete_jobs", "Delete", show=False),
        # Preview tab operations
        Binding("m", "merge_chapters", "Merge↓", show=False),
        Binding("x", "delete_chapter", "Delete", show=False),
        Binding("u", "undo_preview", "Undo", show=False),
        # Help
        Binding("?", "show_help", "Help"),
        Binding("f1", "show_help", "Help", show=False),
        # Debug
        Binding("ctrl+d", "toggle_debug", "Debug"),
    ]

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.initial_path = initial_path
        self.is_processing = False
        self.should_stop = False
        self.current_worker: Worker | None = None
        self.job_manager = JobManager()
        self.debug_mode = False
        self._pending_resume_jobs: list[Job] = []  # Jobs queued for sequential resume

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="app-container"):
            with Vertical(id="left-column"):
                yield FilePanel(self.initial_path)
                with TabbedContent(id="bottom-tabs"):
                    with TabPane("Progress", id="progress-tab"):
                        yield ProgressPanel()
                    with TabPane("Preview", id="preview-tab"):
                        yield PreviewPanel()
                    with TabPane("Queue", id="queue-tab"):
                        yield QueuePanel()
                    with TabPane("Jobs", id="jobs-tab"):
                        yield JobsPanel(self.job_manager)
                    with TabPane("Log", id="log-tab"):
                        yield LogPanel()

            with Vertical(id="right-column"):
                yield SettingsPanel()

        yield Footer()

    def on_mount(self) -> None:
        self.log_message("Audiobookify TUI started")
        self.log_message("Select EPUB files and press Start (or 's')")
        self.log_message("💡 Press ? for help | Ctrl+/-: font size")

    def log_message(self, message: str) -> None:
        """Log a message to the log panel."""
        try:
            log_panel = self.query_one(LogPanel)
            log_panel.write(message)
        except Exception:
            pass

    def log_debug(self, message: str) -> None:
        """Log a debug message (only shown when debug mode is enabled)."""
        if self.debug_mode:
            self.log_message(f"[DEBUG] {message}")

    def action_toggle_debug(self) -> None:
        """Toggle debug logging mode."""
        self.debug_mode = not self.debug_mode
        status = "enabled" if self.debug_mode else "disabled"
        self.notify(f"Debug logging {status}", title="Debug Mode")
        self.log_message(f"🔧 Debug logging {status} (Ctrl+D to toggle)")

    # ─────────────────────────────────────────────────────────────────────────
    # Keyboard Navigation Actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_show_help(self) -> None:
        """Show the help modal with all keyboard shortcuts."""
        self.push_screen(HelpScreen())

    def action_focus_path(self) -> None:
        """Focus the path input field."""
        try:
            path_input = self.query_one("#path-input", Input)
            path_input.focus()
        except Exception:
            pass

    def action_parent_dir(self) -> None:
        """Navigate to parent directory."""
        try:
            file_panel = self.query_one(FilePanel)
            parent = file_panel.current_path.parent
            if parent.exists() and parent != file_panel.current_path:
                file_panel.current_path = parent
                file_panel.query_one("#path-input", Input).value = str(parent)
                file_panel.scan_directory()
                self.log_debug(f"Navigated to parent: {parent}")
        except Exception as e:
            self.log_debug(f"Parent navigation failed: {e}")

    def action_tab_progress(self) -> None:
        """Switch to Progress tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "progress-tab"
        except Exception:
            pass

    def action_tab_preview(self) -> None:
        """Switch to Preview tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "preview-tab"
        except Exception:
            pass

    def action_tab_queue(self) -> None:
        """Switch to Queue tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "queue-tab"
        except Exception:
            pass

    def action_tab_jobs(self) -> None:
        """Switch to Jobs tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "jobs-tab"
        except Exception:
            pass

    def action_tab_log(self) -> None:
        """Switch to Log tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "log-tab"
        except Exception:
            pass

    def action_resume_jobs(self) -> None:
        """Resume selected jobs (keyboard shortcut)."""
        self.action_resume_job()

    def action_delete_jobs(self) -> None:
        """Delete selected jobs (keyboard shortcut)."""
        self.action_delete_job()

    def action_merge_chapters(self) -> None:
        """Merge highlighted chapter with next in Preview tab (M key)."""
        try:
            tabs = self.query_one("#bottom-tabs", TabbedContent)
            if tabs.active != "preview-tab":
                return
            preview_panel = self.query_one(PreviewPanel)
            preview_panel.merge_with_next()
        except Exception:
            pass

    def action_delete_chapter(self) -> None:
        """Delete highlighted chapter in Preview tab (X key)."""
        try:
            tabs = self.query_one("#bottom-tabs", TabbedContent)
            if tabs.active != "preview-tab":
                return
            preview_panel = self.query_one(PreviewPanel)
            preview_panel.delete_chapter()
        except Exception:
            pass

    def action_undo_preview(self) -> None:
        """Undo last merge/delete in Preview tab (U key)."""
        try:
            tabs = self.query_one("#bottom-tabs", TabbedContent)
            if tabs.active != "preview-tab":
                return
            preview_panel = self.query_one(PreviewPanel)
            preview_panel.undo()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Preview Panel Message Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def on_preview_panel_approve_and_start(self, event: PreviewPanel.ApproveAndStart) -> None:
        """Handle Approve & Start from Preview panel."""
        preview_panel = self.query_one(PreviewPanel)

        if not preview_panel.has_chapters():
            self.notify("No chapters to process", severity="warning")
            return

        if not preview_panel.preview_state:
            self.notify("No preview state", severity="error")
            return

        included = preview_panel.get_included_chapters()
        if not included:
            self.notify("No chapters selected", severity="warning")
            return

        preview_state = preview_panel.preview_state
        source_file = preview_state.source_file

        # Log what we're processing
        total_chapters = len(preview_state.chapters)
        self.log_message(f"✅ Processing {len(included)}/{total_chapters} chapters from preview")

        # Export preview state to text file (with merged content preserved)
        text_file = source_file.with_suffix(".txt")
        self.log_message(f"   📝 Exporting preview to: {text_file.name}")

        try:
            preview_state.export_to_text(text_file)
        except Exception as e:
            self.notify(f"Failed to export: {e}", severity="error")
            self.log_message(f"❌ Export failed: {e}")
            return

        # Extract cover image if not already present
        cover_path = source_file.with_suffix(".png")
        if not cover_path.exists() and source_file.suffix.lower() == ".epub":
            try:
                from PIL import Image

                from .epub2tts_edge import get_epub_cover

                cover_data = get_epub_cover(str(source_file))
                if cover_data:
                    image = Image.open(cover_data)
                    image.save(str(cover_path))
                    self.log_message(f"   🖼️ Extracted cover: {cover_path.name}")
            except Exception as e:
                self.log_message(f"   ⚠️ Could not extract cover: {e}")

        # Start processing with chapter filter
        if self.is_processing:
            self.notify("Processing already in progress", severity="warning")
            return

        self.is_processing = True
        self.should_stop = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)

        queue_panel = self.query_one(QueuePanel)
        queue_panel.clear_queue()

        # Process the exported text file using text file processor
        # (no chapter selection needed - already filtered in export)
        self.current_worker = self.process_text_files([text_file])

    # ─────────────────────────────────────────────────────────────────────────
    # Button Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.action_start()
        elif event.button.id == "stop-btn":
            self.action_stop()
        elif event.button.id == "preview-voice-btn":
            self.action_preview_voice()
        elif event.button.id == "job-resume":
            self.action_resume_job()
        elif event.button.id == "job-delete":
            self.action_delete_job()
        elif event.button.id == "job-refresh":
            self.action_refresh_jobs()
        elif event.button.id == "job-select-all":
            self.query_one(JobsPanel).select_all()
        elif event.button.id == "job-deselect-all":
            self.query_one(JobsPanel).deselect_all()
        elif event.button.id == "job-move-up":
            self.query_one(JobsPanel).move_selected_up()
        elif event.button.id == "job-move-down":
            self.query_one(JobsPanel).move_selected_down()
        elif event.button.id == "preview-chapters-btn":
            self.action_preview_chapters()
        elif event.button.id == "export-text-btn":
            self.action_export_text()

    def action_preview_voice(self) -> None:
        """Preview the currently selected voice."""
        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()

        speaker = config["speaker"]
        rate = config["tts_rate"]
        volume = config["tts_volume"]

        # Show generating status
        status_widget = self.query_one(VoicePreviewStatus)
        status_widget.set_generating()

        self.log_message(f"🔊 Previewing voice: {speaker}")
        if rate:
            self.log_message(f"   Rate: {rate}")
        if volume:
            self.log_message(f"   Volume: {volume}")

        # Generate preview in background
        self.preview_voice_async(speaker, rate, volume)

    @work(exclusive=False, thread=True)
    def preview_voice_async(self, speaker: str, rate: str | None, volume: str | None) -> None:
        """Generate voice preview in background thread."""
        import shutil
        import subprocess

        def set_status_generating() -> None:
            self.query_one(VoicePreviewStatus).set_generating()

        def set_status_playing() -> None:
            self.query_one(VoicePreviewStatus).set_playing()

        def set_status_done() -> None:
            self.query_one(VoicePreviewStatus).set_done()

        def set_status_error(msg: str) -> None:
            self.query_one(VoicePreviewStatus).set_error(msg)

        try:
            preview_config = VoicePreviewConfig(speaker=speaker)
            if rate:
                preview_config.rate = rate
            if volume:
                preview_config.volume = volume

            preview = VoicePreview(preview_config)
            output_path = preview.generate_preview_temp()

            self.call_from_thread(self.log_message, f"   Preview saved to: {output_path}")

            # Try to play the audio with various players
            # Priority: PulseAudio/PipeWire tools, then common media players
            players = [
                ("paplay", []),  # PulseAudio
                ("pw-play", []),  # PipeWire
                ("ffplay", ["-nodisp", "-autoexit"]),  # FFmpeg
                ("mpv", ["--no-video"]),  # MPV
                ("vlc", ["--intf", "dummy", "--play-and-exit"]),  # VLC
                ("aplay", []),  # ALSA
                ("afplay", []),  # macOS
            ]
            played = False
            for player, args in players:
                if shutil.which(player):
                    self.call_from_thread(set_status_playing)
                    self.call_from_thread(self.log_message, f"   Playing with {player}...")
                    try:
                        subprocess.run(
                            [player] + args + [output_path], capture_output=True, timeout=30
                        )
                        played = True
                        break
                    except Exception:
                        continue

            if played:
                self.call_from_thread(set_status_done)
            else:
                self.call_from_thread(set_status_error, "No player")
                self.call_from_thread(
                    self.log_message, "   No audio player found. File saved for manual playback."
                )
                self.call_from_thread(
                    self.log_message, "   Install: paplay (PulseAudio), mpv, or ffplay"
                )

        except Exception as e:
            self.call_from_thread(set_status_error, str(e)[:20])
            self.call_from_thread(self.log_message, f"   ❌ Preview failed: {e}")

    def action_start(self) -> None:
        """Start processing selected files."""
        if self.is_processing:
            return

        file_panel = self.query_one(FilePanel)
        selected_files = file_panel.get_selected_files()

        if not selected_files:
            self.log_message("No files selected")
            return

        self.is_processing = True
        self.should_stop = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)

        queue_panel = self.query_one(QueuePanel)
        queue_panel.clear_queue()

        # Route to appropriate processor based on file mode
        if file_panel.file_mode == "text":
            self.log_message(f"Starting text conversion of {len(selected_files)} files...")
            self.current_worker = self.process_text_files(selected_files)
        else:
            self.log_message(f"Starting processing of {len(selected_files)} files...")
            self.current_worker = self.process_files(selected_files)

    def action_stop(self) -> None:
        """Stop processing."""
        if not self.is_processing:
            return

        self.should_stop = True
        self.log_message("⏹️ Stopping... (will stop after current paragraph)")

        if self.current_worker:
            self.current_worker.cancel()

    @work(exclusive=True, thread=True)
    def process_files(self, files: list[Path]) -> None:
        """Process files in background thread."""
        settings_panel = self.query_one(SettingsPanel)
        config_dict = settings_panel.get_config()

        total = len(files)

        for i, epub_path in enumerate(files):
            if self.should_stop:
                self.call_from_thread(self.log_message, "Processing stopped by user")
                break

            # Create task
            task = BookTask(epub_path=str(epub_path))

            # Add to queue display
            self.call_from_thread(self.query_one(QueuePanel).add_task, task)

            # Update progress
            self.call_from_thread(
                self.query_one(ProgressPanel).set_progress,
                i,
                total,
                epub_path.name,
                "Processing...",
            )

            self.call_from_thread(self.log_message, f"Processing: {epub_path.name}")

            # Log export_only setting for debugging
            export_only = config_dict["export_only"]
            self.call_from_thread(
                self.log_message,
                f"  Mode: {'Text export only' if export_only else 'Full audiobook conversion'}",
            )

            # Process the book
            try:
                task.status = ProcessingStatus.EXPORTING
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)
                self.call_from_thread(self.log_message, "  📝 Exporting to text...")

                # Create config for single file
                config = BatchConfig(
                    input_path=str(epub_path),
                    speaker=config_dict["speaker"],
                    detection_method=config_dict["detection_method"],
                    hierarchy_style=config_dict["hierarchy_style"],
                    skip_existing=config_dict["skip_existing"],
                    export_only=config_dict["export_only"],
                    # v2.1.0 options
                    tts_rate=config_dict.get("tts_rate"),
                    tts_volume=config_dict.get("tts_volume"),
                    chapters=config_dict.get("chapters"),
                    # Pause settings
                    sentence_pause=config_dict.get("sentence_pause", 1200),
                    paragraph_pause=config_dict.get("paragraph_pause", 1200),
                )

                processor = BatchProcessor(config)
                processor.prepare()

                if processor.result.tasks:
                    book_task = processor.result.tasks[0]

                    # Update status in real-time during processing
                    if not export_only:
                        self.call_from_thread(self.log_message, "  🔊 Converting to audio...")
                        task.status = ProcessingStatus.CONVERTING
                        self.call_from_thread(self.query_one(QueuePanel).update_task, task)

                    # Create progress callback for chapter/paragraph updates
                    def progress_callback(info):
                        """Handle progress updates from audio generation."""
                        self.call_from_thread(
                            self.query_one(ProgressPanel).set_chapter_progress,
                            info.chapter_num,
                            info.total_chapters,
                            info.chapter_title,
                            info.paragraph_num,
                            info.total_paragraphs,
                        )
                        # Also log chapter starts
                        if info.status == "chapter_start":
                            self.call_from_thread(
                                self.log_message,
                                f"  📖 Chapter {info.chapter_num}/{info.total_chapters}: {info.chapter_title[:50]}",
                            )

                    # Create cancellation check
                    def check_cancelled():
                        return self.should_stop

                    success = processor.process_book(
                        book_task,
                        progress_callback=progress_callback,
                        cancellation_check=check_cancelled,
                    )

                    task.status = book_task.status
                    task.chapter_count = book_task.chapter_count
                    task.start_time = book_task.start_time
                    task.end_time = book_task.end_time

                    if success:
                        duration = task.duration
                        time_str = f" ({int(duration)}s)" if duration else ""
                        self.call_from_thread(
                            self.log_message, f"✅ Completed: {epub_path.name}{time_str}"
                        )
                    else:
                        self.call_from_thread(
                            self.log_message,
                            f"❌ Failed: {epub_path.name} - {book_task.error_message}",
                        )
                else:
                    task.status = ProcessingStatus.SKIPPED
                    self.call_from_thread(
                        self.log_message, f"⏭️ Skipped: {epub_path.name} (no tasks created)"
                    )

            except Exception as e:
                task.status = ProcessingStatus.FAILED
                task.error_message = str(e)
                self.call_from_thread(self.log_message, f"❌ Error: {epub_path.name} - {e}")

            # Update queue display
            self.call_from_thread(self.query_one(QueuePanel).update_task, task)

        # Processing complete
        self.call_from_thread(self._processing_complete, total)

    @work(exclusive=True, thread=True)
    def process_preview_file(self, epub_path: Path, chapter_selection: str | None) -> None:
        """Process a single file from preview with chapter selection.

        Args:
            epub_path: Path to the EPUB file
            chapter_selection: Chapter selection string (e.g., "1,3,5-7") or None for all
        """
        settings_panel = self.query_one(SettingsPanel)
        config_dict = settings_panel.get_config()

        # Create task
        task = BookTask(epub_path=str(epub_path))

        # Add to queue display
        self.call_from_thread(self.query_one(QueuePanel).add_task, task)

        # Update progress
        self.call_from_thread(
            self.query_one(ProgressPanel).set_progress,
            0,
            1,
            epub_path.name,
            "Processing with chapter filter...",
        )

        self.call_from_thread(self.log_message, f"📖 Processing: {epub_path.name}")
        if chapter_selection:
            self.call_from_thread(self.log_message, f"  📑 Selected chapters: {chapter_selection}")

        # Process the book
        try:
            task.status = ProcessingStatus.EXPORTING
            self.call_from_thread(self.query_one(QueuePanel).update_task, task)
            self.call_from_thread(self.log_message, "  📝 Exporting to text...")

            # Create config with chapter selection override
            config = BatchConfig(
                input_path=str(epub_path),
                speaker=config_dict["speaker"],
                detection_method=config_dict["detection_method"],
                hierarchy_style=config_dict["hierarchy_style"],
                skip_existing=config_dict["skip_existing"],
                export_only=config_dict["export_only"],
                # v2.1.0 options
                tts_rate=config_dict.get("tts_rate"),
                tts_volume=config_dict.get("tts_volume"),
                # Chapter selection from preview (overrides settings panel)
                chapters=chapter_selection,
                # Pause settings
                sentence_pause=config_dict.get("sentence_pause", 1200),
                paragraph_pause=config_dict.get("paragraph_pause", 1200),
            )

            processor = BatchProcessor(config)
            processor.prepare()

            if processor.result.tasks:
                book_task = processor.result.tasks[0]

                # Update status in real-time during processing
                export_only = config_dict["export_only"]
                if not export_only:
                    self.call_from_thread(self.log_message, "  🔊 Converting to audio...")
                    task.status = ProcessingStatus.CONVERTING
                    self.call_from_thread(self.query_one(QueuePanel).update_task, task)

                # Create progress callback for chapter/paragraph updates
                def progress_callback(info):
                    """Handle progress updates from audio generation."""
                    self.call_from_thread(
                        self.query_one(ProgressPanel).set_chapter_progress,
                        info.chapter_num,
                        info.total_chapters,
                        info.chapter_title,
                        info.paragraph_num,
                        info.total_paragraphs,
                    )
                    # Also log chapter starts
                    if info.status == "chapter_start":
                        self.call_from_thread(
                            self.log_message,
                            f"  📖 Chapter {info.chapter_num}/{info.total_chapters}: {info.chapter_title[:50]}",
                        )

                # Create cancellation check
                def check_cancelled():
                    return self.should_stop

                success = processor.process_book(
                    book_task,
                    progress_callback=progress_callback,
                    cancellation_check=check_cancelled,
                )

                task.status = book_task.status
                task.chapter_count = book_task.chapter_count
                task.start_time = book_task.start_time
                task.end_time = book_task.end_time

                if success:
                    duration = task.duration
                    time_str = f" ({int(duration)}s)" if duration else ""
                    self.call_from_thread(
                        self.log_message, f"✅ Completed: {epub_path.name}{time_str}"
                    )
                else:
                    self.call_from_thread(
                        self.log_message,
                        f"❌ Failed: {epub_path.name} - {book_task.error_message}",
                    )
            else:
                task.status = ProcessingStatus.SKIPPED
                self.call_from_thread(
                    self.log_message, f"⏭️ Skipped: {epub_path.name} (no tasks created)"
                )

        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            self.call_from_thread(self.log_message, f"❌ Error: {epub_path.name} - {e}")

        # Update queue display
        self.call_from_thread(self.query_one(QueuePanel).update_task, task)

        # Processing complete
        self.call_from_thread(self._processing_complete, 1)

    @work(exclusive=True, thread=True)
    def process_text_files(self, files: list[Path]) -> None:
        """Process text files in background thread."""
        import os

        from .audio_generator import read_book
        from .epub2tts_edge import add_cover, generate_metadata, get_book, make_m4b

        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()
        total = len(files)

        for i, txt_path in enumerate(files):
            if self.should_stop:
                self.call_from_thread(self.log_message, "Processing stopped by user")
                break

            # Create task for queue display
            task = BookTask(epub_path=str(txt_path))
            self.call_from_thread(self.query_one(QueuePanel).add_task, task)

            # Update progress
            self.call_from_thread(
                self.query_one(ProgressPanel).set_progress,
                i,
                total,
                txt_path.name,
                "Processing...",
            )

            self.call_from_thread(self.log_message, f"Processing: {txt_path.name}")

            original_dir = os.getcwd()
            working_dir = txt_path.parent

            try:
                os.chdir(working_dir)
                task.status = ProcessingStatus.EXPORTING
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)
                self.call_from_thread(self.log_message, "  📖 Reading text file...")

                book_contents, book_title, book_author, chapter_titles = get_book(str(txt_path))

                total_chapters = len(book_contents)
                self.call_from_thread(self.log_message, f"  Found {total_chapters} chapters")

                if self.should_stop:
                    self.call_from_thread(self.log_message, "⏹️ Stopped by user")
                    break

                # Apply chapter selection if specified
                chapters_selection = config.get("chapters")
                if chapters_selection:
                    from .chapter_selector import ChapterSelector

                    selector = ChapterSelector(chapters_selection)
                    selected_indices = selector.get_selected_indices(len(book_contents))
                    book_contents = [book_contents[j] for j in selected_indices]
                    chapter_titles = [chapter_titles[j] for j in selected_indices]
                    self.call_from_thread(
                        self.log_message,
                        f"  {selector.get_summary()} ({len(book_contents)} chapters)",
                    )

                task.status = ProcessingStatus.CONVERTING
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)
                self.call_from_thread(self.log_message, "  🔊 Generating audio...")

                # Progress callback
                def progress_callback(info):
                    self.call_from_thread(
                        self.query_one(ProgressPanel).set_chapter_progress,
                        info.chapter_num,
                        info.total_chapters,
                        info.chapter_title,
                        info.paragraph_num,
                        info.total_paragraphs,
                    )
                    if info.status == "chapter_start":
                        self.call_from_thread(
                            self.log_message,
                            f"  📖 Chapter {info.chapter_num}/{info.total_chapters}: {info.chapter_title[:50]}",
                        )

                def check_cancelled():
                    return self.should_stop

                audio_files = read_book(
                    book_contents,
                    config["speaker"],
                    config.get("paragraph_pause", 1200),
                    config.get("sentence_pause", 1200),
                    rate=config.get("tts_rate"),
                    volume=config.get("tts_volume"),
                    progress_callback=progress_callback,
                    cancellation_check=check_cancelled,
                )

                if self.should_stop:
                    self.call_from_thread(self.log_message, "⏹️ Stopped by user")
                    break

                if not audio_files:
                    task.status = ProcessingStatus.FAILED
                    task.error_message = "No audio files generated"
                    self.call_from_thread(self.log_message, "❌ No audio files generated")
                    continue

                self.call_from_thread(self.log_message, "  📦 Creating M4B file...")

                generate_metadata(audio_files, book_author, book_title, chapter_titles)
                m4b_filename = make_m4b(audio_files, str(txt_path), config["speaker"])

                # Check for cover image
                cover_path = txt_path.with_suffix(".png")
                if cover_path.exists():
                    add_cover(str(cover_path), m4b_filename)
                    self.call_from_thread(self.log_message, "  🖼️ Added cover image")

                task.status = ProcessingStatus.COMPLETED
                task.chapter_count = len(book_contents)
                self.call_from_thread(self.log_message, f"✅ Completed: {txt_path.name}")

            except Exception as e:
                import traceback

                task.status = ProcessingStatus.FAILED
                task.error_message = str(e)
                # Log detailed error with traceback
                self.call_from_thread(self.log_message, f"❌ Error: {txt_path.name}")
                self.call_from_thread(self.log_message, f"   Exception: {type(e).__name__}: {e}")
                # Log traceback lines for debugging
                tb_lines = traceback.format_exc().strip().split("\n")
                for line in tb_lines[-5:]:  # Last 5 lines of traceback
                    self.call_from_thread(self.log_message, f"   {line}")

            finally:
                os.chdir(original_dir)
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)

        # Processing complete
        self.call_from_thread(self._processing_complete, total)

    def _processing_complete(self, total: int) -> None:
        """Called when processing is complete."""
        self.is_processing = False
        self.should_stop = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(False)
        progress_panel.set_progress(total, total, "", "Complete!")
        progress_panel.clear_chapter_progress()

        # Refresh Jobs panel and file list to show updated state
        self.query_one(JobsPanel).refresh_jobs()
        self.query_one(FilePanel).scan_directory()

        self.log_message("Processing complete!")

    @work(exclusive=True, thread=True)
    def resume_job_async(self, job: Job) -> None:
        """Resume a job in background thread.

        Uses the job's saved settings (speaker, rate, volume) for consistency.
        The BatchProcessor will find the existing job and resume from where it left off.
        """
        source_path = Path(job.source_file)
        book_name = source_path.name

        # Log detailed job info for debugging (only in debug mode)
        self.call_from_thread(self.log_debug, f"Job ID: {job.job_id}")
        self.call_from_thread(self.log_debug, f"Job dir: {job.job_dir}")
        self.call_from_thread(self.log_debug, f"Status: {job.status.value}")
        self.call_from_thread(
            self.log_debug,
            f"Progress: {job.completed_chapters}/{job.total_chapters} chapters",
        )
        self.call_from_thread(self.log_debug, f"Voice: {job.speaker}")

        # Create task for the job
        task = BookTask(epub_path=str(source_path))
        task.job_id = job.job_id
        task.job_dir = job.job_dir

        self.call_from_thread(self.log_debug, f"Task created with job_id={task.job_id}")

        # Add to queue display
        self.call_from_thread(self.query_one(QueuePanel).add_task, task)

        try:
            task.status = ProcessingStatus.CONVERTING
            self.call_from_thread(self.query_one(QueuePanel).update_task, task)
            if job.completed_chapters > 0:
                self.call_from_thread(
                    self.log_message,
                    f"   Skipping {job.completed_chapters} completed chapters...",
                )

            # Create config using job's saved settings for consistency
            config = BatchConfig(
                input_path=str(source_path),
                speaker=job.speaker,
                tts_rate=job.rate,
                tts_volume=job.volume,
                # Use defaults for other settings
                detection_method="combined",
                hierarchy_style="flat",
                skip_existing=False,
                export_only=False,
            )

            processor = BatchProcessor(config)
            # Don't call prepare() - we already have our task with job info
            # prepare() would create a fresh task without job_id/job_dir

            # Create progress callback for chapter/paragraph updates
            def progress_callback(info):
                """Handle progress updates from audio generation."""
                self.call_from_thread(
                    self.query_one(ProgressPanel).set_chapter_progress,
                    info.chapter_num,
                    info.total_chapters,
                    info.chapter_title,
                    info.paragraph_num,
                    info.total_paragraphs,
                )
                if info.status == "chapter_start":
                    self.call_from_thread(
                        self.log_message,
                        f"  📖 Chapter {info.chapter_num}/{info.total_chapters}: {info.chapter_title[:50]}",
                    )

            # Use our pre-configured task with job info directly
            success = processor.process_book(task, progress_callback=progress_callback)

            if success:
                duration = task.duration
                time_str = f" ({int(duration)}s)" if duration else ""
                self.call_from_thread(
                    self.log_message, f"✅ Resumed and completed: {book_name}{time_str}"
                )
            else:
                self.call_from_thread(
                    self.log_message,
                    f"❌ Resume failed: {book_name} - {task.error_message}",
                )

        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            self.call_from_thread(self.log_message, f"❌ Resume error: {book_name} - {e}")

        # Update queue display
        self.call_from_thread(self.query_one(QueuePanel).update_task, task)

        # Refresh jobs list to show updated status
        self.call_from_thread(self.query_one(JobsPanel).refresh_jobs)

        # Processing complete
        self.call_from_thread(self._processing_complete, 1)

    def action_refresh(self) -> None:
        """Refresh file list."""
        self.query_one(FilePanel).scan_directory()

    def action_select_all(self) -> None:
        """Select all files."""
        for item in self.query(EPUBFileItem):
            if not item.is_selected:
                item.toggle()

    def action_deselect_all(self) -> None:
        """Deselect all files."""
        for item in self.query(EPUBFileItem):
            if item.is_selected:
                item.toggle()

    def action_refresh_jobs(self) -> None:
        """Refresh the jobs list."""
        jobs_panel = self.query_one(JobsPanel)
        jobs_panel.refresh_jobs()
        self.log_message("Jobs list refreshed")

    def action_resume_job(self) -> None:
        """Resume selected jobs. First resumable job starts immediately, others queue."""
        self.log_debug("action_resume_job called")

        if self.is_processing:
            self.notify("Already processing", severity="warning")
            self.log_message("⚠️ Cannot resume: already processing")
            return

        jobs_panel = self.query_one(JobsPanel)
        selected_jobs = jobs_panel.get_selected_jobs()

        self.log_debug(f"Selected jobs count: {len(selected_jobs)}")

        if not selected_jobs:
            self.notify("No jobs selected", severity="warning")
            self.log_message("⚠️ Cannot resume: no jobs selected (use checkbox to select)")
            return

        # Filter to resumable jobs only
        resumable_jobs = [j for j in selected_jobs if j.is_resumable]
        self.log_debug(f"Resumable jobs count: {len(resumable_jobs)}")

        if not resumable_jobs:
            self.notify("No resumable jobs selected", severity="warning")
            self.log_message("⚠️ Cannot resume: none of the selected jobs are resumable")
            for job in selected_jobs:
                self.log_debug(
                    f"  {Path(job.source_file).name}: status={job.status.value}, "
                    f"progress={job.completed_chapters}/{job.total_chapters}, "
                    f"is_resumable={job.is_resumable}"
                )
            return

        # Verify source files exist
        valid_jobs = []
        for job in resumable_jobs:
            source_path = Path(job.source_file)
            if source_path.exists():
                valid_jobs.append(job)
            else:
                self.log_message(f"⚠️ Source file missing: {source_path.name}")

        if not valid_jobs:
            self.notify("No valid source files found", severity="error")
            return

        # First job starts immediately
        first_job = valid_jobs[0]
        source_path = Path(first_job.source_file)

        self.log_message(f"🔄 Resuming {len(valid_jobs)} job(s)")
        self.log_message(
            f"   Starting: {source_path.name} "
            f"({first_job.completed_chapters}/{first_job.total_chapters} chapters done)"
        )

        # Note: Multi-job resume queues remaining jobs for sequential processing
        if len(valid_jobs) > 1:
            self.log_message(
                f"   Note: {len(valid_jobs) - 1} more job(s) will resume after this one"
            )
            # Store remaining jobs for sequential processing
            self._pending_resume_jobs = valid_jobs[1:]

        self.notify(
            f"Resuming {len(valid_jobs)} job(s)",
            title="Job Resume",
            severity="information",
        )

        # Start processing
        self.is_processing = True
        self.should_stop = False
        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)
        progress_panel.set_progress(0, 1, source_path.name, "Resuming...")

        # Switch to Progress tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "progress-tab"

        # Start the resume worker with job context
        self.resume_job_async(first_job)

    def action_delete_job(self) -> None:
        """Delete all selected jobs."""
        jobs_panel = self.query_one(JobsPanel)
        selected_jobs = jobs_panel.get_selected_jobs()

        if not selected_jobs:
            self.notify("No jobs selected", severity="warning")
            self.log_message("⚠️ Cannot delete: no jobs selected (use checkbox to select)")
            return

        job_names = [Path(j.source_file).name for j in selected_jobs]
        deleted_count = jobs_panel.delete_selected_jobs()

        if deleted_count > 0:
            self.log_message(f"🗑️ Deleted {deleted_count} job(s)")
            for name in job_names:
                self.log_message(f"   {name}")
            self.notify(f"Deleted {deleted_count} job(s)", title="Jobs Deleted")
        else:
            self.log_message("❌ Failed to delete jobs")
            self.notify("Failed to delete jobs", severity="error")

    def action_preview_chapters(self) -> None:
        """Preview chapters for the first selected file in the Preview tab."""
        # Get selected files
        selected = [item.path for item in self.query(EPUBFileItem) if item.is_selected]

        if not selected:
            self.notify("Select a file first", severity="warning")
            return

        # Only preview first file
        epub_path = selected[0]
        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()

        detection_method = config["detection_method"]
        hierarchy_style = config["hierarchy_style"]

        self.log_message(f"📋 Loading preview: {epub_path.name}")
        self.log_message(f"   Detection: {detection_method}, Hierarchy: {hierarchy_style}")

        # Clear existing preview before starting new one
        preview_panel = self.query_one(PreviewPanel)
        preview_panel.clear_preview()

        # Switch to Preview tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "preview-tab"

        # Run preview in background (exclusive to cancel any previous preview)
        self.preview_chapters_async(epub_path, detection_method, hierarchy_style)

    @work(exclusive=True, thread=True, group="preview")
    def preview_chapters_async(
        self, epub_path: Path, detection_method: str, hierarchy_style: str
    ) -> None:
        """Preview chapters in background thread and load into Preview tab.

        Uses exclusive=True in group="preview" to cancel any previous preview worker.
        """
        from .chapter_detector import ChapterDetector

        try:
            self.call_from_thread(
                self.log_message, f"   🔍 Detecting chapters with '{detection_method}'..."
            )

            detector = ChapterDetector(
                str(epub_path),
                method=detection_method,
                hierarchy_style=hierarchy_style,
            )
            chapter_tree = detector.detect()

            # Extract book metadata from detector's book object
            book_title = "Unknown"
            book_author = "Unknown"
            try:
                title_meta = detector.book.get_metadata("DC", "title")
                if title_meta:
                    book_title = title_meta[0][0]
            except (IndexError, KeyError, TypeError):
                pass
            try:
                author_meta = detector.book.get_metadata("DC", "creator")
                if author_meta:
                    book_author = author_meta[0][0]
            except (IndexError, KeyError, TypeError):
                pass

            # Flatten the chapter tree to get a list
            chapter_list = chapter_tree.flatten() if chapter_tree else []

            if not chapter_list:
                self.call_from_thread(self.notify, "No chapters detected!", severity="warning")
                self.call_from_thread(
                    self.log_message, "⚠️ No chapters detected. Try a different detection method."
                )
                return

            # Convert to PreviewChapter objects
            preview_chapters: list[PreviewChapter] = []
            for chapter in chapter_list:
                # Calculate stats from paragraphs (populated by _populate_content)
                paragraphs = chapter.paragraphs if chapter.paragraphs else []
                paragraph_count = len(paragraphs)

                # Word count from all paragraphs
                word_count = sum(len(p.split()) for p in paragraphs)

                # Build content from paragraphs
                original_content = "\n\n".join(paragraphs) if paragraphs else ""

                # Create content preview (first 200 chars)
                if original_content:
                    content_preview = original_content[:200].strip()
                    if len(original_content) > 200:
                        content_preview += "..."
                else:
                    content_preview = "(No content extracted)"

                # Ensure at least 1 paragraph (the title itself) if no content found
                if paragraph_count == 0:
                    paragraph_count = 1  # Title counts as a paragraph
                if word_count == 0:
                    word_count = len(chapter.title.split())  # Count words in title

                preview_chapters.append(
                    PreviewChapter(
                        title=chapter.title,
                        level=chapter.level,
                        word_count=word_count,
                        paragraph_count=paragraph_count,
                        content_preview=content_preview,
                        original_content=original_content,
                    )
                )

            # Load into Preview panel on main thread
            def load_preview():
                preview_panel = self.query_one(PreviewPanel)
                preview_panel.load_chapters(
                    epub_path, preview_chapters, detection_method, book_title, book_author
                )

            self.call_from_thread(load_preview)
            self.call_from_thread(
                self.log_message,
                f"✅ Loaded {len(preview_chapters)} chapters (method: {detection_method})",
            )

        except Exception as e:
            self.call_from_thread(self.log_message, f"❌ Preview error: {e}")
            self.call_from_thread(self.notify, f"Preview error: {e}", severity="error")

    def action_export_text(self) -> None:
        """Export selected EPUB to text file for editing."""
        selected = [item.path for item in self.query(EPUBFileItem) if item.is_selected]

        if not selected:
            self.notify("Select a file first", severity="warning")
            return

        epub_path = selected[0]
        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()

        # Switch to Log tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "log-tab"

        self.log_message("─" * 50)
        self.log_message("📝 EXPORT & EDIT WORKFLOW")
        self.log_message("─" * 50)

        # Run export in background
        self.export_text_async(epub_path, config["detection_method"], config["hierarchy_style"])

    @work(exclusive=False, thread=True)
    def export_text_async(
        self, epub_path: Path, detection_method: str, hierarchy_style: str
    ) -> None:
        """Export EPUB to text file in background thread."""
        from .chapter_detector import ChapterDetector

        try:
            # Create output path next to EPUB
            txt_path = epub_path.with_suffix(".txt")

            self.call_from_thread(self.log_message, f"   Exporting: {epub_path.name}")

            # Detect chapters and export
            detector = ChapterDetector(
                str(epub_path), method=detection_method, hierarchy_style=hierarchy_style
            )
            detector.detect()
            detector.export_to_text(str(txt_path), include_metadata=True, level_markers=True)

            chapters = detector.get_flat_chapters()

            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, f"✅ Exported {len(chapters)} chapters to:")
            self.call_from_thread(self.log_message, f"   {txt_path}")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "─" * 50)
            self.call_from_thread(self.log_message, "📋 EDITING INSTRUCTIONS:")
            self.call_from_thread(self.log_message, "─" * 50)
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "1. Open the .txt file in your text editor")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "2. Chapter markers use # symbols:")
            self.call_from_thread(self.log_message, "   # Chapter 1    → Main chapter")
            self.call_from_thread(self.log_message, "   ## Section 1.1 → Sub-section")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "3. To fix split chapter titles:")
            self.call_from_thread(self.log_message, "   BEFORE:")
            self.call_from_thread(self.log_message, "     # 1")
            self.call_from_thread(self.log_message, "     # The Beginning")
            self.call_from_thread(self.log_message, "   AFTER:")
            self.call_from_thread(self.log_message, "     # 1 - The Beginning")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "4. To merge chapters, delete the # line")
            self.call_from_thread(self.log_message, "   and the content will join the previous")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "5. Delete any unwanted sections entirely")
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, "─" * 50)
            self.call_from_thread(self.log_message, "📌 NEXT STEPS:")
            self.call_from_thread(self.log_message, "─" * 50)
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(
                self.log_message,
                "After editing, click '📝 Text' in the file panel to switch",
            )
            self.call_from_thread(
                self.log_message, "to text mode, select your .txt file, and press Start."
            )
            self.call_from_thread(self.log_message, "")
            self.call_from_thread(self.log_message, f"File location: {txt_path}")
            self.call_from_thread(self.log_message, "─" * 50)

        except Exception as e:
            self.call_from_thread(self.log_message, f"❌ Export failed: {e}")


def main(path: str = ".") -> None:
    """Run the Audiobookify TUI."""
    app = AudiobookifyApp(initial_path=path)
    app.run()


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    main(path)
