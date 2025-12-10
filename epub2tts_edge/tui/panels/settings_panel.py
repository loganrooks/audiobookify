"""Settings panel for configuring conversion settings."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Switch,
    TabbedContent,
    TabPane,
)

from ...voice_preview import AVAILABLE_VOICES
from ..models import VoicePreviewStatus


class SettingsPanel(Vertical):
    """Panel for configuring conversion settings with tabbed interface."""

    DEFAULT_CSS = """
    SettingsPanel {
        width: 40;
        height: 100%;
        border: round $secondary;
        border-title-color: $secondary;
        background: $surface;
    }

    SettingsPanel > #settings-tabs {
        height: 1fr;
    }

    SettingsPanel .setting-row {
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
    }

    SettingsPanel .setting-row > Label {
        width: 12;
    }

    SettingsPanel .setting-row > Select {
        width: 1fr;
    }

    SettingsPanel .setting-row > Input {
        width: 1fr;
    }

    SettingsPanel .setting-row > Switch {
        width: auto;
    }

    SettingsPanel #preview-voice-btn {
        margin: 1;
        width: 100%;
    }

    SettingsPanel .sub-setting {
        margin-left: 2;
        color: $text-muted;
    }

    SettingsPanel .hidden {
        display: none;
    }

    SettingsPanel TabPane {
        padding: 1 0;
    }

    SettingsPanel ContentSwitcher {
        height: 1fr;
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

    NORMALIZE_METHODS = [
        ("peak", "Peak"),
        ("rms", "RMS"),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="settings-tabs"):
            # 🎙️ Voice Tab
            with TabPane("🎙️", id="voice-tab"):
                with VerticalScroll():
                    with Horizontal(classes="setting-row"):
                        yield Label("Voice:")
                        yield Select(
                            [(v[1], v[0]) for v in self.VOICES],
                            value="en-US-AndrewNeural",
                            id="voice-select",
                        )

                    yield Button("🔊 Preview Voice", id="preview-voice-btn", variant="default")
                    yield VoicePreviewStatus()

                    with Horizontal(classes="setting-row"):
                        yield Label("Rate:")
                        yield Select(
                            [(r[1], r[0]) for r in self.RATE_OPTIONS],
                            value="",
                            id="rate-select",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Volume:")
                        yield Select(
                            [(v[1], v[0]) for v in self.VOLUME_OPTIONS],
                            value="",
                            id="volume-select",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Narrator:")
                        yield Input(
                            placeholder="Voice for narration",
                            id="narrator-voice-input",
                        )

            # 🎵 Audio Tab
            with TabPane("🎵", id="audio-tab"):
                with VerticalScroll():
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

                    with Horizontal(classes="setting-row"):
                        yield Label("Trim Silence:")
                        yield Switch(id="trim-silence-switch")

                    # Sub-settings for trim silence (progressive disclosure)
                    with Horizontal(classes="setting-row sub-setting", id="trim-threshold-row"):
                        yield Label("↳ Threshold:")
                        yield Input(value="-40", placeholder="dBFS", id="trim-threshold-input")

                    with Horizontal(classes="setting-row sub-setting", id="trim-duration-row"):
                        yield Label("↳ Max (ms):")
                        yield Input(value="2000", placeholder="ms", id="trim-duration-input")

                    with Horizontal(classes="setting-row"):
                        yield Label("Normalize:")
                        yield Switch(id="normalize-switch")

                    # Sub-settings for normalize (progressive disclosure)
                    with Horizontal(classes="setting-row sub-setting", id="normalize-target-row"):
                        yield Label("↳ Target:")
                        yield Input(value="-16", placeholder="dBFS", id="normalize-target-input")

                    with Horizontal(classes="setting-row sub-setting", id="normalize-method-row"):
                        yield Label("↳ Method:")
                        yield Select(
                            [(m[1], m[0]) for m in self.NORMALIZE_METHODS],
                            value="peak",
                            id="normalize-method-select",
                        )

            # 📖 Chapters Tab
            with TabPane("📖", id="chapters-tab"):
                with VerticalScroll():
                    with Horizontal(classes="setting-row"):
                        yield Label("Detection:")
                        yield Select(
                            [(d[1], d[0]) for d in self.DETECTION_METHODS],
                            value="combined",
                            id="detect-select",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Hierarchy:")
                        yield Select(
                            [(h[1], h[0]) for h in self.HIERARCHY_STYLES],
                            value="flat",
                            id="hierarchy-select",
                        )

                    with Horizontal(classes="setting-row"):
                        yield Label("Max Depth:")
                        yield Input(placeholder="(all levels)", id="max-depth-input")

                    with Horizontal(classes="setting-row"):
                        yield Label("Chapters:")
                        yield Input(placeholder="e.g., 1-5, 1,3,7", id="chapters-input")

                    # Content filtering options
                    with Horizontal(classes="setting-row"):
                        yield Label("Filter Front:")
                        yield Switch(id="filter-front-switch")

                    with Horizontal(classes="setting-row"):
                        yield Label("Filter Back:")
                        yield Switch(id="filter-back-switch")

                    # Sub-setting for translator content (progressive disclosure)
                    with Horizontal(classes="setting-row sub-setting", id="keep-translator-row"):
                        yield Label("↳ Keep Transl.:")
                        yield Switch(value=True, id="keep-translator-switch")

                    with Horizontal(classes="setting-row"):
                        yield Label("Trim Notes:")
                        yield Switch(id="trim-notes-switch")

            # ⚙️ Advanced Tab
            with TabPane("⚙️", id="advanced-tab"):
                with VerticalScroll():
                    with Horizontal(classes="setting-row"):
                        yield Label("Pronuncia.:")
                        yield Input(placeholder="Path to dictionary", id="pronunciation-input")

                    with Horizontal(classes="setting-row"):
                        yield Label("Voice Map:")
                        yield Input(placeholder="Path to mapping JSON", id="voice-mapping-input")

                    with Horizontal(classes="setting-row"):
                        yield Label("Parallel:")
                        yield Input(value="5", placeholder="1-15", id="concurrency-input")

                    with Horizontal(classes="setting-row"):
                        yield Label("Recursive:")
                        yield Switch(id="recursive-switch")

                    with Horizontal(classes="setting-row"):
                        yield Label("Skip Done:")
                        yield Switch(value=True, id="skip-existing-switch")

                    with Horizontal(classes="setting-row"):
                        yield Label("Text Only:")
                        yield Switch(id="export-only-switch")

    def on_mount(self) -> None:
        """Initialize progressive disclosure state."""
        self._update_trim_visibility()
        self._update_normalize_visibility()
        self._update_filter_visibility()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes for progressive disclosure."""
        if event.switch.id == "trim-silence-switch":
            self._update_trim_visibility()
        elif event.switch.id == "normalize-switch":
            self._update_normalize_visibility()
        elif event.switch.id == "filter-front-switch":
            self._update_filter_visibility()

    def _update_trim_visibility(self) -> None:
        """Show/hide trim silence sub-settings."""
        try:
            enabled = self.query_one("#trim-silence-switch", Switch).value
            threshold_row = self.query_one("#trim-threshold-row")
            duration_row = self.query_one("#trim-duration-row")
            threshold_row.set_class(not enabled, "hidden")
            duration_row.set_class(not enabled, "hidden")
        except Exception:
            pass  # Widget not mounted yet

    def _update_normalize_visibility(self) -> None:
        """Show/hide normalize sub-settings."""
        try:
            enabled = self.query_one("#normalize-switch", Switch).value
            target_row = self.query_one("#normalize-target-row")
            method_row = self.query_one("#normalize-method-row")
            target_row.set_class(not enabled, "hidden")
            method_row.set_class(not enabled, "hidden")
        except Exception:
            pass  # Widget not mounted yet

    def _update_filter_visibility(self) -> None:
        """Show/hide content filter sub-settings."""
        try:
            enabled = self.query_one("#filter-front-switch", Switch).value
            translator_row = self.query_one("#keep-translator-row")
            translator_row.set_class(not enabled, "hidden")
        except Exception:
            pass  # Widget not mounted yet

    def get_config(self) -> dict:
        """Get current settings as a dictionary."""
        rate_val = self.query_one("#rate-select", Select).value
        volume_val = self.query_one("#volume-select", Select).value
        chapters_val = self.query_one("#chapters-input", Input).value.strip()
        pronunciation_val = self.query_one("#pronunciation-input", Input).value.strip()
        voice_mapping_val = self.query_one("#voice-mapping-input", Input).value.strip()
        sentence_pause_val = self.query_one("#sentence-pause-select", Select).value
        paragraph_pause_val = self.query_one("#paragraph-pause-select", Select).value
        concurrency_val = self.query_one("#concurrency-input", Input).value.strip()

        # Parse concurrency as int, default to 5, clamp to 1-15
        try:
            max_concurrent = max(1, min(15, int(concurrency_val)))
        except ValueError:
            max_concurrent = 5

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
            "max_concurrent": max_concurrent,
            # Content filtering options
            "filter_front_matter": self.query_one("#filter-front-switch", Switch).value,
            "filter_back_matter": self.query_one("#filter-back-switch", Switch).value,
            "keep_translator": self.query_one("#keep-translator-switch", Switch).value,
            "remove_inline_notes": self.query_one("#trim-notes-switch", Switch).value,
        }
