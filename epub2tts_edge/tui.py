"""
Audiobookify TUI - Terminal User Interface

A modern terminal-based interface for converting EPUB files to audiobooks.
Built with Textual for a rich, interactive experience.

Usage:
    python -m epub2tts_edge.tui
    # or
    audiobookify-tui
"""

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
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
    Switch,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker

# Import our modules
from .batch_processor import BatchConfig, BatchProcessor, BookTask, ProcessingStatus
from .voice_preview import AVAILABLE_VOICES, VoicePreview, VoicePreviewConfig


class EPUBFileItem(ListItem):
    """A list item representing an EPUB file."""

    def __init__(self, path: Path, selected: bool = True) -> None:
        super().__init__()
        self.path = path
        self.is_selected = selected

    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.is_selected else "☐"
        yield Label(f"{checkbox} {self.path.name}")

    def toggle(self) -> None:
        self.is_selected = not self.is_selected
        checkbox = "☑" if self.is_selected else "☐"
        self.query_one(Label).update(f"{checkbox} {self.path.name}")


class FilePanel(Vertical):
    """Panel for browsing and selecting EPUB/MOBI files."""

    DEFAULT_CSS = """
    FilePanel {
        width: 1fr;
        height: 100%;
        border: round $primary;
        border-title-color: $primary;
        padding: 1;
        background: $surface;
    }

    FilePanel > Label.title {
        text-style: bold;
        margin-bottom: 1;
        color: $primary-lighten-2;
    }

    FilePanel > Label.file-count {
        color: $text-muted;
        margin-bottom: 1;
    }

    FilePanel > #path-input {
        margin-bottom: 1;
        border: round $primary-darken-1;
    }

    FilePanel > #file-list {
        height: 1fr;
        border: round $primary-darken-2;
        background: $surface-darken-1;
    }

    FilePanel > #file-actions {
        height: auto;
        margin-top: 1;
    }

    FilePanel > #file-actions > Button {
        margin-right: 1;
    }
    """

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.current_path = Path(initial_path).resolve()
        self.epub_files: list[Path] = []

    def compose(self) -> ComposeResult:
        yield Label("📁 Select Books (EPUB/MOBI/AZW)", classes="title")
        yield Label("0 files found", classes="file-count", id="file-count")
        yield Input(
            placeholder="Enter folder path...",
            value=str(self.current_path),
            id="path-input"
        )
        yield ListView(id="file-list")
        with Horizontal(id="file-actions"):
            yield Button("✓ All", id="select-all", variant="default")
            yield Button("✗ None", id="deselect-all", variant="default")
            yield Button("🔄 Refresh", id="refresh", variant="primary")

    def on_mount(self) -> None:
        self.scan_directory()

    def scan_directory(self) -> None:
        """Scan current directory for EPUB, MOBI, and AZW files."""
        file_list = self.query_one("#file-list", ListView)
        file_list.clear()

        self.epub_files = []

        if self.current_path.exists() and self.current_path.is_dir():
            # Scan for all supported formats
            patterns = ["*.epub", "*.mobi", "*.azw", "*.azw3"]
            all_files = []
            for pattern in patterns:
                all_files.extend(self.current_path.glob(pattern))

            for book_path in sorted(set(all_files)):
                self.epub_files.append(book_path)
                file_list.append(EPUBFileItem(book_path))

        # Update file count
        count_label = self.query_one("#file-count", Label)
        count = len(self.epub_files)
        count_label.update(f"{count} file{'s' if count != 1 else ''} found")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path-input":
            new_path = Path(event.value).resolve()
            if new_path.exists() and new_path.is_dir():
                self.current_path = new_path
                self.scan_directory()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-all":
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
        return [
            item.path for item in self.query(EPUBFileItem)
            if item.is_selected
        ]


class SettingsPanel(Vertical):
    """Panel for configuring conversion settings."""

    DEFAULT_CSS = """
    SettingsPanel {
        width: 40;
        height: 100%;
        border: round $secondary;
        border-title-color: $secondary;
        padding: 1;
        overflow-y: auto;
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

    def compose(self) -> ComposeResult:
        yield Label("⚙️ Settings", classes="title")

        # Voice settings
        with Horizontal(classes="setting-row"):
            yield Label("Voice:")
            yield Select(
                [(v[1], v[0]) for v in self.VOICES],
                value="en-US-AndrewNeural",
                id="voice-select"
            )

        yield Button("🔊 Preview Voice", id="preview-voice-btn", variant="default")

        # v2.1.0: Rate and Volume controls
        yield Label("Voice Adjustments", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Rate:")
            yield Select(
                [(r[1], r[0]) for r in self.RATE_OPTIONS],
                value="",
                id="rate-select"
            )

        with Horizontal(classes="setting-row"):
            yield Label("Volume:")
            yield Select(
                [(v[1], v[0]) for v in self.VOLUME_OPTIONS],
                value="",
                id="volume-select"
            )

        yield Rule()

        # Detection settings
        with Horizontal(classes="setting-row"):
            yield Label("Detection:")
            yield Select(
                [(d[1], d[0]) for d in self.DETECTION_METHODS],
                value="combined",
                id="detect-select"
            )

        with Horizontal(classes="setting-row"):
            yield Label("Hierarchy:")
            yield Select(
                [(h[1], h[0]) for h in self.HIERARCHY_STYLES],
                value="flat",
                id="hierarchy-select"
            )

        # v2.1.0: Chapter selection
        yield Label("Chapter Selection", classes="section-title")

        with Horizontal(classes="setting-row"):
            yield Label("Chapters:")
            yield Input(
                placeholder="e.g., 1-5, 1,3,7",
                id="chapters-input"
            )

        yield Rule()

        # Processing options
        with Horizontal(classes="setting-row"):
            yield Label("Export Only:")
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
            yield Input(
                placeholder="Path to dictionary file",
                id="pronunciation-input"
            )

        with Horizontal(classes="setting-row"):
            yield Label("Voice Map:")
            yield Input(
                placeholder="Path to voice mapping",
                id="voice-mapping-input"
            )

    def get_config(self) -> dict:
        """Get current settings as a dictionary."""
        rate_val = self.query_one("#rate-select", Select).value
        volume_val = self.query_one("#volume-select", Select).value
        chapters_val = self.query_one("#chapters-input", Input).value.strip()
        pronunciation_val = self.query_one("#pronunciation-input", Input).value.strip()
        voice_mapping_val = self.query_one("#voice-mapping-input", Input).value.strip()

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
        min-height: 12;
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
        self.query_one("#status-text", Label).update(
            status or f"{current}/{total} books processed"
        )

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
            key=task.epub_path
        )

    def update_task(self, task: BookTask) -> None:
        """Update a task in the queue display."""
        table = self.query_one("#queue-table", DataTable)
        try:
            row_key = table.get_row_index(task.epub_path)
            status_icon = self._get_status_icon(task.status)
            table.update_cell_at((row_key, 0), status_icon)
            table.update_cell_at((row_key, 2), str(task.chapter_count) if task.chapter_count else "-")
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
        background: $surface-darken-1;
        border: round $primary-darken-2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📜 Log", classes="title")
        yield Log(id="log-output", auto_scroll=True)

    def write(self, message: str) -> None:
        """Write a message to the log."""
        self.query_one("#log-output", Log).write_line(message)

    def clear(self) -> None:
        """Clear the log."""
        self.query_one("#log-output", Log).clear()


class AudiobookifyApp(App):
    """Main Audiobookify TUI Application."""

    TITLE = "Audiobookify"
    SUB_TITLE = "EPUB to Audiobook Converter"

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 40;
        grid-rows: 1fr auto;
    }

    #main-area {
        column-span: 1;
        row-span: 1;
    }

    #settings-area {
        column-span: 1;
        row-span: 2;
    }

    #bottom-area {
        column-span: 1;
        row-span: 1;
        height: 100%;
    }

    #left-panels {
        height: 100%;
    }

    #right-bottom {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start", "Start"),
        Binding("escape", "stop", "Stop"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "select_all", "Select All"),
        Binding("d", "deselect_all", "Deselect All"),
        Binding("p", "preview_voice", "Preview Voice"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.initial_path = initial_path
        self.is_processing = False
        self.should_stop = False
        self.current_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-area"):
            with Vertical(id="left-panels"):
                yield FilePanel(self.initial_path)

        with Vertical(id="settings-area"):
            yield SettingsPanel()

        with Horizontal(id="bottom-area"):
            with TabbedContent():
                with TabPane("Progress", id="progress-tab"):
                    yield ProgressPanel()
                    yield QueuePanel()
                with TabPane("Log", id="log-tab"):
                    yield LogPanel()

        yield Footer()

    def on_mount(self) -> None:
        self.log_message("Audiobookify TUI started")
        self.log_message("Select EPUB files and press Start (or 's')")

    def log_message(self, message: str) -> None:
        """Log a message to the log panel."""
        try:
            log_panel = self.query_one(LogPanel)
            log_panel.write(message)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.action_start()
        elif event.button.id == "stop-btn":
            self.action_stop()
        elif event.button.id == "preview-voice-btn":
            self.action_preview_voice()

    def action_preview_voice(self) -> None:
        """Preview the currently selected voice."""
        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()

        speaker = config["speaker"]
        rate = config["tts_rate"]
        volume = config["tts_volume"]

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

        try:
            preview_config = VoicePreviewConfig(speaker=speaker)
            if rate:
                preview_config.rate = rate
            if volume:
                preview_config.volume = volume

            preview = VoicePreview(preview_config)
            output_path = preview.generate_preview_temp()

            self.call_from_thread(
                self.log_message,
                f"   Preview saved to: {output_path}"
            )

            # Try to play the audio with various players
            # Priority: PulseAudio/PipeWire tools, then common media players
            players = [
                ('paplay', []),                      # PulseAudio
                ('pw-play', []),                     # PipeWire
                ('ffplay', ['-nodisp', '-autoexit']), # FFmpeg
                ('mpv', ['--no-video']),             # MPV
                ('vlc', ['--intf', 'dummy', '--play-and-exit']),  # VLC
                ('aplay', []),                       # ALSA
                ('afplay', []),                      # macOS
            ]
            for player, args in players:
                if shutil.which(player):
                    self.call_from_thread(
                        self.log_message,
                        f"   Playing with {player}..."
                    )
                    try:
                        subprocess.run(
                            [player] + args + [output_path],
                            capture_output=True, timeout=30
                        )
                        break
                    except Exception:
                        continue
            else:
                self.call_from_thread(
                    self.log_message,
                    "   No audio player found. File saved for manual playback."
                )
                self.call_from_thread(
                    self.log_message,
                    f"   Install: paplay (PulseAudio), mpv, or ffplay"
                )

        except Exception as e:
            self.call_from_thread(
                self.log_message,
                f"   ❌ Preview failed: {e}"
            )

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

        self.log_message(f"Starting processing of {len(selected_files)} files...")

        # Start processing in background
        self.current_worker = self.process_files(selected_files)

    def action_stop(self) -> None:
        """Stop processing."""
        if not self.is_processing:
            return

        self.should_stop = True
        self.log_message("Stopping... (will finish current book)")

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
                self.call_from_thread(
                    self.log_message,
                    "Processing stopped by user"
                )
                break

            # Create task
            task = BookTask(epub_path=str(epub_path))

            # Add to queue display
            self.call_from_thread(
                self.query_one(QueuePanel).add_task,
                task
            )

            # Update progress
            self.call_from_thread(
                self.query_one(ProgressPanel).set_progress,
                i, total, epub_path.name, "Processing..."
            )

            self.call_from_thread(
                self.log_message,
                f"Processing: {epub_path.name}"
            )

            # Process the book
            try:
                task.status = ProcessingStatus.EXPORTING
                self.call_from_thread(
                    self.query_one(QueuePanel).update_task,
                    task
                )

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
                )

                processor = BatchProcessor(config)
                processor.prepare()

                if processor.result.tasks:
                    book_task = processor.result.tasks[0]
                    success = processor.process_book(book_task)

                    task.status = book_task.status
                    task.chapter_count = book_task.chapter_count
                    task.start_time = book_task.start_time
                    task.end_time = book_task.end_time

                    if success:
                        self.call_from_thread(
                            self.log_message,
                            f"✅ Completed: {epub_path.name}"
                        )
                    else:
                        self.call_from_thread(
                            self.log_message,
                            f"❌ Failed: {epub_path.name} - {book_task.error_message}"
                        )
                else:
                    task.status = ProcessingStatus.SKIPPED
                    self.call_from_thread(
                        self.log_message,
                        f"⏭️ Skipped: {epub_path.name}"
                    )

            except Exception as e:
                task.status = ProcessingStatus.FAILED
                task.error_message = str(e)
                self.call_from_thread(
                    self.log_message,
                    f"❌ Error: {epub_path.name} - {e}"
                )

            # Update queue display
            self.call_from_thread(
                self.query_one(QueuePanel).update_task,
                task
            )

        # Processing complete
        self.call_from_thread(self._processing_complete, total)

    def _processing_complete(self, total: int) -> None:
        """Called when processing is complete."""
        self.is_processing = False
        self.should_stop = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(False)
        progress_panel.set_progress(total, total, "", "Complete!")

        self.log_message("Processing complete!")

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

    def action_help(self) -> None:
        """Show help."""
        self.log_message("─" * 40)
        self.log_message("Keyboard Shortcuts:")
        self.log_message("  s     - Start processing")
        self.log_message("  Esc   - Stop processing")
        self.log_message("  r     - Refresh file list")
        self.log_message("  a     - Select all files")
        self.log_message("  d     - Deselect all files")
        self.log_message("  p     - Preview selected voice")
        self.log_message("  q     - Quit")
        self.log_message("  ?     - Show this help")
        self.log_message("─" * 40)
        self.log_message("")
        self.log_message("v2.1.0 Features:")
        self.log_message("  - Rate/Volume: Adjust TTS speed and volume")
        self.log_message("  - Chapters: Select specific chapters (e.g., 1-5)")
        self.log_message("  - Voice Preview: Listen before converting")
        self.log_message("")
        self.log_message("v2.2.0 Features:")
        self.log_message("  - Normalize: Consistent volume across chapters")
        self.log_message("  - Trim Silence: Remove excessive pauses")
        self.log_message("  - Pronunciation: Custom word pronunciations")
        self.log_message("  - Voice Mapping: Different voices for characters")
        self.log_message("─" * 40)


def main(path: str = ".") -> None:
    """Run the Audiobookify TUI."""
    app = AudiobookifyApp(initial_path=path)
    app.run()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    main(path)
