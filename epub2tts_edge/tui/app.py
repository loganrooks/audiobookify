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
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker

# Import our modules (from parent package)
from ..batch_processor import BatchConfig, BatchProcessor, BookTask, ProcessingStatus
from ..config import get_config
from ..job_manager import Job, JobManager, JobStatus
from ..voice_preview import VoicePreview, VoicePreviewConfig

# Import from tui submodules (Phase 1 refactor)
from .models import PreviewChapter, VoicePreviewStatus
from .panels import (
    EPUBFileItem,
    FilePanel,
    JobsPanel,
    LogPanel,
    PathInput,
    PreviewPanel,
    ProgressPanel,
    QueuePanel,
    SettingsPanel,
)
from .screens import DirectoryBrowserScreen, HelpScreen

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# All panel classes have been extracted to epub2tts_edge/tui/panels/
# All model classes have been extracted to epub2tts_edge/tui/models/
# ─────────────────────────────────────────────────────────────────────────────


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

    QueuePanel.queue-hidden {
        display: none;
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
        Binding("b", "browse_dir", "Browse", show=False),
        Binding("p", "preview_voice", "Preview Voice"),
        # Navigation
        Binding("slash", "focus_path", "Path", show=False),
        Binding("backspace", "parent_dir", "Parent", show=False),
        # Tab switching (1-4 for bottom tabs)
        Binding("1", "tab_preview", "Preview", show=False),
        Binding("2", "tab_current", "Current", show=False),
        Binding("3", "tab_jobs", "Jobs", show=False),
        Binding("4", "tab_log", "Log", show=False),
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
        self.is_paused = False
        self.current_worker: Worker | None = None
        self.job_manager = JobManager()
        self.debug_mode = False
        self._pending_resume_jobs: list[Job] = []  # Jobs queued for sequential resume
        self._current_preview_job: Job | None = None  # Job being previewed/edited

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="app-container"):
            with Vertical(id="left-column"):
                yield FilePanel(self.initial_path)
                with TabbedContent(id="bottom-tabs"):
                    with TabPane("📋 Preview", id="preview-tab"):
                        yield PreviewPanel()
                    with TabPane("▶️ Current", id="current-tab"):
                        yield ProgressPanel()
                        # Hidden queue panel for internal task tracking
                        yield QueuePanel(classes="queue-hidden")
                    with TabPane("📊 Jobs", id="jobs-tab"):
                        yield JobsPanel(self.job_manager)
                    with TabPane("📜 Log", id="log-tab"):
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
            path_input = self.query_one("#path-input", PathInput)
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
                file_panel.query_one("#path-input", PathInput).value = str(parent)
                file_panel.scan_directory()
                self.log_debug(f"Navigated to parent: {parent}")
        except Exception as e:
            self.log_debug(f"Parent navigation failed: {e}")

    def action_browse_dir(self) -> None:
        """Open directory browser modal."""
        try:
            file_panel = self.query_one(FilePanel)
            self.push_screen(
                DirectoryBrowserScreen(file_panel.current_path),
                file_panel._on_directory_selected,
            )
        except Exception as e:
            self.log_debug(f"Browse failed: {e}")

    def action_tab_preview(self) -> None:
        """Switch to Preview tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "preview-tab"
        except Exception:
            pass

    def action_tab_current(self) -> None:
        """Switch to Current tab."""
        try:
            self.query_one("#bottom-tabs", TabbedContent).active = "current-tab"
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
        """Merge chapters in Preview tab (M key).

        Uses batch_merge if multiple chapters are selected,
        otherwise merges highlighted chapter with next one.
        """
        try:
            tabs = self.query_one("#bottom-tabs", TabbedContent)
            if tabs.active != "preview-tab":
                return
            preview_panel = self.query_one(PreviewPanel)
            # Use batch merge if items are selected, otherwise merge with next
            selected = preview_panel._get_selected_items()
            if len(selected) >= 2:
                preview_panel.batch_merge()
            else:
                preview_panel.merge_with_next()
            self._save_preview_edits()
        except Exception:
            pass

    def action_delete_chapter(self) -> None:
        """Delete chapters in Preview tab (X key).

        Uses batch_delete if chapters are selected,
        otherwise deletes the highlighted chapter.
        """
        try:
            tabs = self.query_one("#bottom-tabs", TabbedContent)
            if tabs.active != "preview-tab":
                return
            preview_panel = self.query_one(PreviewPanel)
            # Use batch delete if items are selected, otherwise delete highlighted
            selected = preview_panel._get_selected_items()
            if len(selected) >= 1:
                preview_panel.batch_delete()
            else:
                preview_panel.delete_chapter()
            self._save_preview_edits()
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
            self._save_preview_edits()
        except Exception:
            pass

    def _save_preview_edits(self) -> None:
        """Save current preview state (chapter edits) to the job."""
        import json

        if not self._current_preview_job:
            return

        try:
            preview_panel = self.query_one(PreviewPanel)
            if not preview_panel.preview_state:
                return

            # Serialize chapter edits
            edits = [
                {
                    "title": ch.title,
                    "included": ch.included,
                    "merged_into": ch.merged_into,
                }
                for ch in preview_panel.preview_state.chapters
            ]

            # Update job with edits
            job = self.job_manager.load_job(self._current_preview_job.job_id)
            if job:
                job.chapter_edits = json.dumps(edits)
                self.job_manager._save_job(job)
                self._current_preview_job = job  # Update reference
        except Exception:
            pass  # Don't crash on save errors

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

        # Use existing preview job if available, otherwise create one
        job = self._current_preview_job
        if job and job.status == JobStatus.PREVIEW:
            # Update job status to EXTRACTING
            self.job_manager.update_status(job.job_id, JobStatus.EXTRACTING)
            job.total_chapters = len(included)
            self.job_manager._save_job(job)
            self.log_message(f"   📋 Using preview job: {job.job_id}")
        else:
            # No preview job - create one now
            settings_panel = self.query_one(SettingsPanel)
            config = settings_panel.get_config()
            job = self.job_manager.create_job(
                source_file=str(source_file),
                speaker=config["speaker"],
                rate=config.get("tts_rate"),
                volume=config.get("tts_volume"),
            )
            job.total_chapters = len(included)
            self.job_manager.update_status(job.job_id, JobStatus.EXTRACTING)
            self.job_manager._save_job(job)
            self._current_preview_job = job
            self.log_message(f"   📋 Created job: {job.job_id}")

        # Export to job directory (always use job directory now)
        text_file = Path(job.job_dir) / f"{source_file.stem}.txt"
        self.log_message(f"   📝 Exporting preview to: {text_file}")

        try:
            preview_state.export_to_text(text_file)
        except Exception as e:
            self.notify(f"Failed to export: {e}", severity="error")
            self.log_message(f"❌ Export failed: {e}")
            return

        # Extract cover image to job directory
        cover_path = Path(job.job_dir) / f"{source_file.stem}.png"
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
        self.is_paused = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)
        self.query_one(JobsPanel).set_running(True)

        queue_panel = self.query_one(QueuePanel)
        queue_panel.clear_queue()

        # Refresh jobs panel to show updated status
        self.query_one(JobsPanel).refresh_jobs()

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
        elif event.button.id == "pause-btn":
            self.action_pause()
        elif event.button.id == "preview-voice-btn":
            self.action_preview_voice()
        elif event.button.id == "job-delete":
            self.action_delete_job()
        elif event.button.id == "job-refresh":
            self.action_refresh_jobs()
        elif event.button.id == "job-select-all":
            jobs_panel = self.query_one(JobsPanel)
            jobs_panel.select_all()
            jobs_panel.update_play_button()
        elif event.button.id == "job-deselect-all":
            jobs_panel = self.query_one(JobsPanel)
            jobs_panel.deselect_all()
            jobs_panel.update_play_button()
        # Jobs panel transport controls
        elif event.button.id == "jobs-play-btn":
            self.action_jobs_play()
        elif event.button.id == "jobs-pause-btn":
            self.action_pause()
        elif event.button.id == "jobs-stop-btn":
            self.action_stop()
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

    def action_jobs_play(self) -> None:
        """Context-aware play button for Jobs panel.

        Based on selected job status:
        - PREVIEW: Start conversion
        - PAUSED: Resume conversion
        - COMPLETED/FAILED/CANCELLED: Restart conversion
        - PENDING: Start conversion
        """
        jobs_panel = self.query_one(JobsPanel)
        selected = jobs_panel.get_selected_jobs()

        if not selected:
            self.notify("No jobs selected", severity="warning")
            return

        first_job = selected[0]

        if first_job.status == JobStatus.PREVIEW:
            # Start from PREVIEW - need to export chapters and begin processing
            self._start_preview_job(first_job)
        elif first_job.status == JobStatus.PAUSED:
            # Resume paused job
            self.action_resume_job()
        elif first_job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            # Restart - delete old job files and start fresh
            self._restart_job(first_job)
        elif first_job.status == JobStatus.PENDING:
            # Start pending job
            self._start_pending_job(first_job)
        else:
            self.notify(
                f"Cannot start job with status: {first_job.status.value}", severity="warning"
            )

    def _start_preview_job(self, job: Job) -> None:
        """Start conversion from a PREVIEW job."""
        # Load the preview panel's state and use it
        preview_panel = self.query_one(PreviewPanel)

        if (
            not preview_panel.preview_state
            or str(preview_panel.preview_state.epub_path) != job.source_file
        ):
            # Need to reload preview for this job
            self.notify("Please preview the file first before starting", severity="warning")
            return

        # Trigger the same flow as "Start All" from preview
        preview_panel.post_message(PreviewPanel.ApproveAndStart())

    def _restart_job(self, job: Job) -> None:
        """Restart a completed/failed job by creating fresh state."""
        # Clear preview job reference if it matches
        if self._current_preview_job and self._current_preview_job.job_id == job.job_id:
            self._current_preview_job = None
            try:
                preview_panel = self.query_one(PreviewPanel)
                preview_panel.clear_preview()
            except Exception:
                pass

        # Delete old job and let user start fresh
        self.job_manager.delete_job(job.job_id)
        self.query_one(JobsPanel).refresh_jobs()
        self.notify("Job deleted. Preview the file again to restart.", severity="information")

    def _start_pending_job(self, job: Job) -> None:
        """Start a pending job."""
        # For now, treat pending jobs similarly to resumable jobs
        self.action_resume_job()

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
        self.is_paused = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)
        self.query_one(JobsPanel).set_running(True)

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
        self.is_paused = False  # Clear pause state when stopping
        self.log_message("⏹️ Stopping... (will stop after current paragraph)")

        if self.current_worker:
            self.current_worker.cancel()

    def action_pause(self) -> None:
        """Toggle pause state for processing."""
        if not self.is_processing:
            return

        self.is_paused = not self.is_paused
        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_paused(self.is_paused)
        self.query_one(JobsPanel).set_paused(self.is_paused)

        # Update job status if we have a current preview job
        if self._current_preview_job:
            job = self.job_manager.load_job(self._current_preview_job.job_id)
            if job:
                if self.is_paused:
                    self.job_manager.update_status(job.job_id, JobStatus.PAUSED)
                else:
                    self.job_manager.update_status(job.job_id, JobStatus.CONVERTING)
                self.query_one(JobsPanel).refresh_jobs()

        if self.is_paused:
            self.log_message("⏸️ Paused - processing will pause after current operation")
        else:
            self.log_message("▶️ Resumed")

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
                # Get app config for output directory
                app_config = get_config()
                output_dir = str(app_config.output_dir) if app_config.output_dir else None

                config = BatchConfig(
                    input_path=str(epub_path),
                    output_dir=output_dir,
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
                    # Parallelization
                    max_concurrent=config_dict.get("max_concurrent", 5),
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

            # Refresh jobs panel to show newly created/updated jobs
            self.call_from_thread(self.query_one(JobsPanel).refresh_jobs)

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
            # Get app config for output directory
            app_config = get_config()
            output_dir = str(app_config.output_dir) if app_config.output_dir else None

            config = BatchConfig(
                input_path=str(epub_path),
                output_dir=output_dir,
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
                # Parallelization
                max_concurrent=config_dict.get("max_concurrent", 5),
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
        """Process text files in background thread using proper job isolation."""
        import os
        import shutil

        from .audio_generator import read_book
        from .epub2tts_edge import add_cover, generate_metadata, get_book, make_m4b
        from .job_manager import JobManager, JobStatus

        settings_panel = self.query_one(SettingsPanel)
        config = settings_panel.get_config()
        total = len(files)

        # Create job manager for proper isolation
        job_manager = JobManager()

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

            # Create job for this text file (provides isolated directory)
            job = job_manager.create_job(
                source_file=str(txt_path),
                speaker=config["speaker"],
                rate=config.get("tts_rate"),
                volume=config.get("tts_volume"),
            )
            task.job_id = job.job_id
            task.job_dir = job.job_dir

            self.call_from_thread(self.log_message, f"  📁 Job: {job.job_id}")

            try:
                task.status = ProcessingStatus.EXPORTING
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)
                job_manager.update_status(job.job_id, JobStatus.EXTRACTING)
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
                job_manager.update_status(job.job_id, JobStatus.CONVERTING)
                job_manager.update_progress(job.job_id, total_chapters=total_chapters)
                self.call_from_thread(self.log_message, "  🔊 Generating audio...")

                # Progress callback that also updates job progress
                # Capture job_id to avoid late binding issue
                current_job_id = job.job_id

                def progress_callback(info, job_id=current_job_id):
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
                    if info.status == "chapter_done":
                        job_manager.update_progress(job_id, completed_chapters=info.chapter_num)

                def check_cancelled():
                    return self.should_stop

                # Use job's isolated audio directory
                audio_output_dir = str(job.effective_audio_dir)

                audio_files = read_book(
                    book_contents,
                    config["speaker"],
                    config.get("paragraph_pause", 1200),
                    config.get("sentence_pause", 1200),
                    output_dir=audio_output_dir,
                    rate=config.get("tts_rate"),
                    volume=config.get("tts_volume"),
                    max_concurrent=config.get("max_concurrent", 5),
                    progress_callback=progress_callback,
                    cancellation_check=check_cancelled,
                )

                if self.should_stop:
                    self.call_from_thread(self.log_message, "⏹️ Stopped by user")
                    break

                if not audio_files:
                    task.status = ProcessingStatus.FAILED
                    task.error_message = "No audio files generated"
                    job_manager.set_error(job.job_id, "No audio files generated")
                    self.call_from_thread(self.log_message, "❌ No audio files generated")
                    continue

                self.call_from_thread(self.log_message, "  📦 Creating M4B file...")
                job_manager.update_status(job.job_id, JobStatus.FINALIZING)

                # Generate M4B in the job directory with explicit paths (no chdir!)
                generate_metadata(
                    audio_files, book_author, book_title, chapter_titles, output_dir=job.job_dir
                )
                m4b_path = make_m4b(
                    audio_files, str(txt_path), config["speaker"], output_dir=job.job_dir
                )

                # Check for cover image
                cover_path = txt_path.with_suffix(".png")
                if cover_path.exists():
                    add_cover(str(cover_path), m4b_path)
                    self.call_from_thread(self.log_message, "  🖼️ Added cover image")

                # Move M4B to original text file's directory
                m4b_filename = os.path.basename(m4b_path)
                final_output = txt_path.parent / m4b_filename
                shutil.move(m4b_path, final_output)
                self.call_from_thread(self.log_message, f"  📁 Output: {final_output}")
                self.call_from_thread(
                    self.log_message, f"  📂 Intermediate files: {job.effective_audio_dir}"
                )

                # Complete the job
                job_manager.complete_job(job.job_id, str(final_output))

                task.status = ProcessingStatus.COMPLETED
                task.m4b_path = str(final_output)
                task.chapter_count = len(book_contents)
                self.call_from_thread(self.log_message, f"✅ Completed: {txt_path.name}")

            except Exception as e:
                import traceback

                task.status = ProcessingStatus.FAILED
                task.error_message = str(e)
                if job:
                    job_manager.set_error(job.job_id, str(e))
                # Log detailed error with traceback
                self.call_from_thread(self.log_message, f"❌ Error: {txt_path.name}")
                self.call_from_thread(self.log_message, f"   Exception: {type(e).__name__}: {e}")
                # Log traceback lines for debugging
                tb_lines = traceback.format_exc().strip().split("\n")
                for line in tb_lines[-5:]:  # Last 5 lines of traceback
                    self.call_from_thread(self.log_message, f"   {line}")

            finally:
                self.call_from_thread(self.query_one(QueuePanel).update_task, task)

        # Processing complete
        self.call_from_thread(self._processing_complete, total)

    def _processing_complete(self, total: int) -> None:
        """Called when processing is complete."""
        self.is_processing = False
        self.should_stop = False
        self.is_paused = False

        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(False)
        progress_panel.set_paused(False)  # Reset pause button state
        progress_panel.set_progress(total, total, "", "Complete!")
        progress_panel.clear_chapter_progress()

        # Refresh Jobs panel and file list to show updated state
        jobs_panel = self.query_one(JobsPanel)
        jobs_panel.set_running(False)
        jobs_panel.set_paused(False)
        jobs_panel.refresh_jobs()
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
            # Get app config for output directory
            app_config = get_config()
            output_dir = str(app_config.output_dir) if app_config.output_dir else None

            config = BatchConfig(
                input_path=str(source_path),
                output_dir=output_dir,
                speaker=job.speaker,
                tts_rate=job.rate,
                tts_volume=job.volume,
                # Use defaults for other settings
                detection_method="combined",
                hierarchy_style="flat",
                skip_existing=False,
                export_only=False,
                max_concurrent=5,  # Use default for resumed jobs
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
        self.is_paused = False
        progress_panel = self.query_one(ProgressPanel)
        progress_panel.set_running(True)
        progress_panel.set_progress(0, 1, source_path.name, "Resuming...")
        self.query_one(JobsPanel).set_running(True)

        # Switch to Current tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "current-tab"

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

        # Check if current preview job is being deleted
        preview_job_deleted = False
        if self._current_preview_job:
            for job in selected_jobs:
                if job.job_id == self._current_preview_job.job_id:
                    preview_job_deleted = True
                    break

        job_names = [Path(j.source_file).name for j in selected_jobs]
        deleted_count = jobs_panel.delete_selected_jobs()

        if deleted_count > 0:
            self.log_message(f"🗑️ Deleted {deleted_count} job(s)")
            for name in job_names:
                self.log_message(f"   {name}")
            self.notify(f"Deleted {deleted_count} job(s)", title="Jobs Deleted")

            # Clear current preview job if it was deleted
            if preview_job_deleted:
                self._current_preview_job = None
                # Clear the preview panel since its job was deleted
                try:
                    preview_panel = self.query_one(PreviewPanel)
                    preview_panel.clear_preview()
                    self.log_message("   📋 Preview cleared (job was deleted)")
                except Exception:
                    pass
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
        speaker = config["speaker"]

        # Build filter config from settings
        filter_config = None
        if (
            config.get("filter_front_matter")
            or config.get("filter_back_matter")
            or config.get("remove_inline_notes")
        ):
            from .content_filter import FilterConfig

            filter_config = FilterConfig(
                remove_front_matter=config.get("filter_front_matter", False),
                remove_back_matter=config.get("filter_back_matter", False),
                include_translator_content=config.get("keep_translator", True),
                remove_inline_notes=config.get("remove_inline_notes", False),
            )

        self.log_message(f"📋 Loading preview: {epub_path.name}")
        self.log_message(f"   Detection: {detection_method}, Hierarchy: {hierarchy_style}")
        if filter_config:
            filters = []
            if config.get("filter_front_matter"):
                filters.append("front matter")
            if config.get("filter_back_matter"):
                filters.append("back matter")
            if config.get("remove_inline_notes"):
                filters.append("inline notes")
            self.log_message(f"   Filtering: {', '.join(filters)}")

        # Clear existing preview before starting new one
        preview_panel = self.query_one(PreviewPanel)
        preview_panel.clear_preview()

        # Switch to Preview tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "preview-tab"

        # Run preview in background (exclusive to cancel any previous preview)
        self.preview_chapters_async(
            epub_path, detection_method, hierarchy_style, speaker, filter_config
        )

    @work(exclusive=True, thread=True, group="preview")
    def preview_chapters_async(
        self,
        epub_path: Path,
        detection_method: str,
        hierarchy_style: str,
        speaker: str,
        filter_config=None,
    ) -> None:
        """Preview chapters in background thread and load into Preview tab.

        Uses exclusive=True in group="preview" to cancel any previous preview worker.
        Creates a job with PREVIEW status so it appears in the Jobs panel.
        """
        import json

        from .chapter_detector import ChapterDetector

        try:
            self.call_from_thread(
                self.log_message, f"   🔍 Detecting chapters with '{detection_method}'..."
            )

            detector = ChapterDetector(
                str(epub_path),
                method=detection_method,
                hierarchy_style=hierarchy_style,
                filter_config=filter_config,
            )
            chapter_tree = detector.detect()

            # Log filter results if filtering was applied
            if filter_config:
                filter_result = detector.get_filter_result()
                if filter_result and filter_result.removed_count > 0:
                    self.call_from_thread(
                        self.log_message,
                        f"   🔻 Filtered {filter_result.removed_count} chapters "
                        f"({filter_result.filtered_count} remaining)",
                    )
                    if filter_result.removed_front_matter:
                        self.call_from_thread(
                            self.log_message,
                            f"      Front matter: {len(filter_result.removed_front_matter)} removed",
                        )
                    if filter_result.removed_back_matter:
                        self.call_from_thread(
                            self.log_message,
                            f"      Back matter: {len(filter_result.removed_back_matter)} removed",
                        )
                    if filter_result.kept_translator_content:
                        self.call_from_thread(
                            self.log_message,
                            f"      Translator content: {len(filter_result.kept_translator_content)} kept",
                        )

            # Log content extraction stats for debugging
            content_stats = detector.get_content_stats()
            if content_stats:
                self.call_from_thread(
                    self.log_message,
                    f"   📊 Content extraction: {content_stats['with_content']}/{content_stats['total']} chapters have content",
                )
                if content_stats["no_paragraphs"] > 0:
                    self.call_from_thread(
                        self.log_message,
                        f"   ⚠️ {content_stats['no_paragraphs']} chapters have NO content extracted!",
                    )
                if content_stats["no_href"] > 0:
                    self.call_from_thread(
                        self.log_message,
                        f"   ⚠️ {content_stats['no_href']} chapters have no href (no link to content)",
                    )
                # Detailed breakdown for debugging
                self.call_from_thread(
                    self.log_message,
                    f"   📝 Extraction methods: anchor={content_stats['anchor_found']}, "
                    f"heading={content_stats['heading_match']}, full_file={content_stats['full_file']}",
                )

                # Show TOC debug info if there are problems
                if content_stats["no_paragraphs"] > 0:
                    toc_debug = detector.get_toc_debug()
                    self.call_from_thread(
                        self.log_message,
                        f"   📖 TOC DEBUG: nav_found={toc_debug['nav_found']}, "
                        f"ncx_found={toc_debug['ncx_found']}",
                    )
                    if toc_debug["toc_items"]:
                        for item in toc_debug["toc_items"]:
                            self.call_from_thread(
                                self.log_message,
                                f"      • {item['name']} (type={item['type']})",
                            )

                # Show what detection found BEFORE content population
                detection_debug = detector.get_detection_debug()
                if detection_debug and content_stats["no_paragraphs"] > 0:
                    self.call_from_thread(
                        self.log_message,
                        f"   🔎 DETECTION RESULTS ({len(detection_debug)} chapters):",
                    )
                    # Show all main content chapters (skip front matter)
                    shown = 0
                    for dbg in detection_debug:
                        # Skip typical front matter
                        title_lower = dbg.get("title", "").lower()
                        is_front_matter = any(
                            fm in title_lower
                            for fm in [
                                "cover",
                                "title page",
                                "copyright",
                                "contents",
                                "half-title",
                            ]
                        )
                        if not is_front_matter or shown < 3:
                            self.call_from_thread(
                                self.log_message,
                                f"      • '{dbg['title'][:35]}': href={dbg.get('href', '?')}, anchor={dbg['anchor']}",
                            )
                            shown += 1
                            if shown >= 15:  # Show up to 15 chapters
                                remaining = len(detection_debug) - shown
                                if remaining > 0:
                                    self.call_from_thread(
                                        self.log_message,
                                        f"      ... and {remaining} more chapters",
                                    )
                                break

                # Show detailed debug info for chapters that failed
                content_debug = detector.get_content_debug()
                if content_debug:
                    self.call_from_thread(
                        self.log_message,
                        f"   🔍 CONTENT EXTRACTION FAILURES ({len(content_debug)} chapters):",
                    )
                    for i, dbg in enumerate(content_debug):
                        if i >= 15:  # Show up to 15 failures
                            remaining = len(content_debug) - i
                            self.call_from_thread(
                                self.log_message,
                                f"      ... and {remaining} more failures",
                            )
                            break
                        p_count = dbg.get("p_tags_in_file", "?")
                        self.call_from_thread(
                            self.log_message,
                            f"      • '{dbg['title'][:35]}': file={dbg.get('href', '?')}, "
                            f"anchor={dbg['anchor']}, p_in_file={p_count}",
                        )
                        self.call_from_thread(
                            self.log_message,
                            f"        → elem=<{dbg['element_type']}>, scanned={dbg['elements_scanned']}, "
                            f"stop={dbg['stop_reason']}",
                        )

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

            # Check for existing PREVIEW job for this source file
            existing_job = self.job_manager.find_job_for_source(str(epub_path))
            saved_edits: dict[int, dict] | None = None

            if existing_job and existing_job.status == JobStatus.PREVIEW:
                # Load existing preview edits
                self.call_from_thread(
                    self.log_message, f"   📋 Loading existing preview job: {existing_job.job_id}"
                )
                job = existing_job
                if job.chapter_edits:
                    try:
                        # Parse saved edits and create a lookup by index
                        edits_list = json.loads(job.chapter_edits)
                        saved_edits = dict(enumerate(edits_list))
                    except json.JSONDecodeError:
                        pass
            else:
                # Create new job with PREVIEW status
                job = self.job_manager.create_job(
                    source_file=str(epub_path),
                    title=book_title,
                    author=book_author,
                    speaker=speaker,
                )
                self.job_manager.update_status(job.job_id, JobStatus.PREVIEW)
                job.total_chapters = len(chapter_list)
                self.job_manager._save_job(job)
                self.call_from_thread(self.log_message, f"   📋 Created preview job: {job.job_id}")

            # Store reference to current preview job
            self._current_preview_job = job

            # Convert to PreviewChapter objects
            preview_chapters: list[PreviewChapter] = []
            for i, chapter in enumerate(chapter_list):
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

                # Apply saved edits if available
                included = True
                merged_into = None
                title = chapter.title
                if saved_edits and i in saved_edits:
                    edit = saved_edits[i]
                    included = edit.get("included", True)
                    merged_into = edit.get("merged_into")
                    title = edit.get("title", chapter.title)

                preview_chapters.append(
                    PreviewChapter(
                        title=title,
                        level=chapter.level,
                        word_count=word_count,
                        paragraph_count=paragraph_count,
                        content_preview=content_preview,
                        original_content=original_content,
                        included=included,
                        merged_into=merged_into,
                    )
                )

            # Load into Preview panel on main thread
            def load_preview():
                preview_panel = self.query_one(PreviewPanel)
                preview_panel.load_chapters(
                    epub_path, preview_chapters, detection_method, book_title, book_author
                )
                # Refresh Jobs panel to show the new/existing preview job
                try:
                    jobs_panel = self.query_one(JobsPanel)
                    jobs_panel.refresh_jobs()
                except Exception:
                    pass

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

        # Build filter config from settings
        filter_config = None
        if (
            config.get("filter_front_matter")
            or config.get("filter_back_matter")
            or config.get("remove_inline_notes")
        ):
            from .content_filter import FilterConfig

            filter_config = FilterConfig(
                remove_front_matter=config.get("filter_front_matter", False),
                remove_back_matter=config.get("filter_back_matter", False),
                include_translator_content=config.get("keep_translator", True),
                remove_inline_notes=config.get("remove_inline_notes", False),
            )

        # Switch to Log tab
        tabs = self.query_one("#bottom-tabs", TabbedContent)
        tabs.active = "log-tab"

        self.log_message("─" * 50)
        self.log_message("📝 EXPORT & EDIT WORKFLOW")
        self.log_message("─" * 50)

        if filter_config:
            filters = []
            if config.get("filter_front_matter"):
                filters.append("front matter")
            if config.get("filter_back_matter"):
                filters.append("back matter")
            if config.get("remove_inline_notes"):
                filters.append("inline notes")
            self.log_message(f"   Filtering: {', '.join(filters)}")

        # Run export in background
        self.export_text_async(
            epub_path, config["detection_method"], config["hierarchy_style"], filter_config
        )

    @work(exclusive=False, thread=True)
    def export_text_async(
        self, epub_path: Path, detection_method: str, hierarchy_style: str, filter_config=None
    ) -> None:
        """Export EPUB to text file in background thread."""
        from .chapter_detector import ChapterDetector

        try:
            # Create output path next to EPUB
            txt_path = epub_path.with_suffix(".txt")

            self.call_from_thread(self.log_message, f"   Exporting: {epub_path.name}")

            # Detect chapters and export
            detector = ChapterDetector(
                str(epub_path),
                method=detection_method,
                hierarchy_style=hierarchy_style,
                filter_config=filter_config,
            )
            detector.detect()
            detector.export_to_text(str(txt_path), include_metadata=True, level_markers=True)

            chapters = detector.get_flat_chapters()

            # Log filter results if filtering was applied
            if filter_config:
                filter_result = detector.get_filter_result()
                if filter_result and filter_result.removed_count > 0:
                    self.call_from_thread(
                        self.log_message,
                        f"   🔻 Filtered {filter_result.removed_count} chapters",
                    )

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
