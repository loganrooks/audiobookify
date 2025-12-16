"""Settings panel for configuring conversion settings."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

from ...core.profiles import ProcessingProfile, ProfileManager, get_profile
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

    SettingsPanel .profile-actions {
        height: auto;
        margin: 0 1;
        padding: 0;
    }

    SettingsPanel .profile-actions Button {
        min-width: 10;
        margin-right: 1;
    }

    SettingsPanel #dirty-indicator {
        color: $warning;
        text-style: bold;
        margin-left: 1;
        width: auto;
    }

    SettingsPanel #dirty-indicator.hidden {
        display: none;
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

    # Output naming template presets
    OUTPUT_NAMING_OPTIONS = [
        ("{author} - {title}", "Author - Title"),
        ("{title}", "Title Only"),
        ("{title} by {author}", "Title by Author"),
        ("{series} {series_index} - {title}", "Series - Title"),
        ("{title} ({year})", "Title (Year)"),
    ]

    # Reactive state for dirty tracking
    is_dirty: reactive[bool] = reactive(False)

    def __init__(self, **kwargs) -> None:
        """Initialize the settings panel with profile state tracking."""
        super().__init__(**kwargs)
        # Profile state tracking
        self._loaded_profile_key: str | None = None  # Key of loaded profile
        self._loaded_profile_snapshot: dict | None = None  # Snapshot at load time

    def _get_profile_options(self) -> list[tuple[str, str]]:
        """Get dynamic profile options.

        Returns list of (display_name, key) tuples for Select widget.
        Custom is first, then all profiles with star for default.
        """
        mgr = ProfileManager.get_instance()
        default_key = mgr.get_default_profile()

        options: list[tuple[str, str]] = [("Custom", "custom")]

        # Add all profiles, marking the default with a star
        for key in mgr.get_profile_names():
            profile = mgr.get_profile(key)
            if profile:
                if key == default_key:
                    options.append((f"★ {profile.name}", key))
                else:
                    options.append((profile.name, key))

        return options

    def compose(self) -> ComposeResult:
        with TabbedContent(id="settings-tabs"):
            # 🎙️ Voice Tab
            with TabPane("🎙️", id="voice-tab"):
                with VerticalScroll():
                    # Profile selector at top of voice tab
                    with Horizontal(classes="setting-row"):
                        yield Label("Profile:")
                        yield Select(
                            self._get_profile_options(),
                            value="custom",
                            id="profile-select",
                        )

                    # Profile management buttons and dirty indicator
                    with Horizontal(classes="profile-actions"):
                        yield Button("Save As", id="save-profile-btn", variant="default")
                        yield Button(
                            "Overwrite",
                            id="overwrite-profile-btn",
                            variant="warning",
                            disabled=True,
                        )
                        yield Button(
                            "Delete", id="delete-profile-btn", variant="error", disabled=True
                        )
                        yield Button(
                            "Set Default",
                            id="set-default-btn",
                            variant="primary",
                            disabled=True,
                        )
                        yield Static("● Modified", id="dirty-indicator", classes="hidden")

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
                    # Output naming template
                    with Horizontal(classes="setting-row"):
                        yield Label("Output Name:")
                        yield Select(
                            [(o[1], o[0]) for o in self.OUTPUT_NAMING_OPTIONS],
                            value="{author} - {title}",
                            id="output-naming-select",
                        )

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
        self._update_dirty_indicator()
        self._update_profile_buttons()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes for progressive disclosure and dirty tracking."""
        if event.switch.id == "trim-silence-switch":
            self._update_trim_visibility()
        elif event.switch.id == "normalize-switch":
            self._update_normalize_visibility()
        elif event.switch.id == "filter-front-switch":
            self._update_filter_visibility()

        # Check dirty state for profile-related settings
        self._check_dirty()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes, including profile selection and dirty tracking."""
        if event.select.id == "profile-select":
            profile_key = event.value
            # Handle blank selection or "custom" option
            if profile_key == Select.BLANK or profile_key == "custom":
                # Reset to custom mode
                self._loaded_profile_key = None
                self._loaded_profile_snapshot = None
                self.is_dirty = False
            else:
                self._apply_profile(profile_key)
            self._update_dirty_indicator()
            self._update_profile_buttons()
        else:
            # Any other setting change triggers dirty check
            self._check_dirty()

    def _apply_profile(self, profile_key: str) -> None:
        """Apply a profile's settings to all relevant controls.

        Args:
            profile_key: Key of the profile to apply
        """
        profile = get_profile(profile_key)
        if not profile:
            return

        try:
            # Voice settings
            self.query_one("#voice-select", Select).value = profile.voice
            # Rate - find matching option or use empty
            rate_val = profile.rate or ""
            self.query_one("#rate-select", Select).value = rate_val
            # Volume - find matching option or use empty
            volume_val = profile.volume or ""
            self.query_one("#volume-select", Select).value = volume_val

            # Audio settings
            self.query_one("#sentence-pause-select", Select).value = profile.sentence_pause
            self.query_one("#paragraph-pause-select", Select).value = profile.paragraph_pause
            self.query_one("#trim-silence-switch", Switch).value = profile.trim_silence
            self.query_one("#normalize-switch", Switch).value = profile.normalize_audio

            # Chapter settings
            self.query_one("#detect-select", Select).value = profile.detection_method
            self.query_one("#hierarchy-select", Select).value = profile.hierarchy_style

            # Update progressive disclosure visibility
            self._update_trim_visibility()
            self._update_normalize_visibility()

            # Track loaded profile state for dirty detection
            self._loaded_profile_key = profile_key
            self._loaded_profile_snapshot = self._get_profile_settings()
            self.is_dirty = False

        except Exception:
            pass  # Some widgets might not be mounted yet

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
        output_naming_val = self.query_one("#output-naming-select", Select).value
        profile_val = self.query_one("#profile-select", Select).value

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
            # Phase 3: Profiles and output naming
            "profile": profile_val if profile_val != "custom" else None,
            "output_naming_template": output_naming_val,
        }

    def _get_profile_settings(self) -> dict:
        """Get current settings in profile-compatible format for dirty comparison.

        Returns only the settings that are part of a profile.
        """
        try:
            return {
                "voice": self.query_one("#voice-select", Select).value,
                "rate": self.query_one("#rate-select", Select).value or None,
                "volume": self.query_one("#volume-select", Select).value or None,
                "paragraph_pause": self.query_one("#paragraph-pause-select", Select).value,
                "sentence_pause": self.query_one("#sentence-pause-select", Select).value,
                "normalize_audio": self.query_one("#normalize-switch", Switch).value,
                "trim_silence": self.query_one("#trim-silence-switch", Switch).value,
                "detection_method": self.query_one("#detect-select", Select).value,
                "hierarchy_style": self.query_one("#hierarchy-select", Select).value,
            }
        except Exception:
            return {}

    def _check_dirty(self) -> None:
        """Check if current settings differ from loaded profile."""
        if self._loaded_profile_snapshot is None:
            self.is_dirty = False
            return

        current = self._get_profile_settings()
        self.is_dirty = current != self._loaded_profile_snapshot
        self._update_dirty_indicator()
        self._update_profile_buttons()

    def _update_dirty_indicator(self) -> None:
        """Update the dirty indicator visibility."""
        try:
            indicator = self.query_one("#dirty-indicator", Static)
            indicator.set_class(not self.is_dirty, "hidden")
        except Exception:
            pass  # Widget not mounted yet

    def _update_profile_buttons(self) -> None:
        """Update profile button states based on current profile."""
        try:
            mgr = ProfileManager.get_instance()
            overwrite_btn = self.query_one("#overwrite-profile-btn", Button)
            delete_btn = self.query_one("#delete-profile-btn", Button)
            set_default_btn = self.query_one("#set-default-btn", Button)

            if self._loaded_profile_key is None:
                # Custom/no profile loaded
                overwrite_btn.disabled = True
                delete_btn.disabled = True
                set_default_btn.disabled = True
            else:
                # Profile is loaded - all buttons available
                overwrite_btn.disabled = not self.is_dirty
                delete_btn.disabled = False
                # Disable "Set Default" if already the default
                is_default = mgr.is_default(self._loaded_profile_key)
                set_default_btn.disabled = is_default
                if is_default:
                    set_default_btn.label = "★ Default"
                else:
                    set_default_btn.label = "Set Default"
        except Exception:
            pass  # Widgets not mounted yet

    def _refresh_profile_dropdown(self) -> None:
        """Refresh the profile dropdown options."""
        try:
            select = self.query_one("#profile-select", Select)
            select.set_options(self._get_profile_options())
        except Exception:
            pass  # Widget not mounted yet

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle profile action button presses."""
        if event.button.id == "save-profile-btn":
            self._on_save_profile()
        elif event.button.id == "overwrite-profile-btn":
            self._on_overwrite_profile()
        elif event.button.id == "delete-profile-btn":
            self._on_delete_profile()
        elif event.button.id == "set-default-btn":
            self._on_set_default_profile()

    def _on_save_profile(self) -> None:
        """Handle Save As button press - opens dialog for name input."""
        # Import here to avoid circular imports
        from ..screens.profile_dialog import ProfileNameDialog

        self.app.push_screen(ProfileNameDialog(), self._do_save_profile)

    def _do_save_profile(self, name: str | None) -> None:
        """Actually save the profile after getting name from dialog."""
        if not name:
            return

        mgr = ProfileManager.get_instance()
        settings = self._get_profile_settings()

        profile = ProcessingProfile(
            name=name,
            description="",
            voice=settings.get("voice", "en-US-AndrewNeural"),
            rate=settings.get("rate"),
            volume=settings.get("volume"),
            paragraph_pause=settings.get("paragraph_pause", 1200),
            sentence_pause=settings.get("sentence_pause", 1200),
            normalize_audio=settings.get("normalize_audio", False),
            trim_silence=settings.get("trim_silence", False),
            detection_method=settings.get("detection_method", "combined"),
            hierarchy_style=settings.get("hierarchy_style", "flat"),
        )

        try:
            key = mgr.save_profile(profile)
            self._refresh_profile_dropdown()
            # Select the newly saved profile
            self.query_one("#profile-select", Select).value = key
            self._loaded_profile_key = key
            self._loaded_profile_snapshot = settings.copy()
            self.is_dirty = False
            self._update_dirty_indicator()
            self._update_profile_buttons()
            self.notify(f"Profile '{name}' saved", severity="information")
        except FileExistsError:
            self.notify(f"Profile '{name}' already exists", severity="error")
        except ValueError as e:
            self.notify(str(e), severity="error")

    def _on_overwrite_profile(self) -> None:
        """Handle Overwrite button press."""
        if not self._loaded_profile_key:
            return

        mgr = ProfileManager.get_instance()
        existing = mgr.get_profile(self._loaded_profile_key)
        if not existing:
            return

        settings = self._get_profile_settings()
        updated_profile = ProcessingProfile(
            name=existing.name,
            description=existing.description,
            voice=settings.get("voice", "en-US-AndrewNeural"),
            rate=settings.get("rate"),
            volume=settings.get("volume"),
            paragraph_pause=settings.get("paragraph_pause", 1200),
            sentence_pause=settings.get("sentence_pause", 1200),
            normalize_audio=settings.get("normalize_audio", False),
            trim_silence=settings.get("trim_silence", False),
            detection_method=settings.get("detection_method", "combined"),
            hierarchy_style=settings.get("hierarchy_style", "flat"),
        )

        try:
            mgr.save_profile(updated_profile, overwrite=True)
            self._loaded_profile_snapshot = settings.copy()
            self.is_dirty = False
            self._update_dirty_indicator()
            self._update_profile_buttons()
            self.notify(f"Profile '{existing.name}' updated", severity="information")
        except ValueError as e:
            self.notify(str(e), severity="error")

    def _on_delete_profile(self) -> None:
        """Handle Delete button press."""
        if not self._loaded_profile_key:
            return

        mgr = ProfileManager.get_instance()

        try:
            profile = mgr.get_profile(self._loaded_profile_key)
            profile_name = profile.name if profile else self._loaded_profile_key
            mgr.delete_profile(self._loaded_profile_key)
            self._refresh_profile_dropdown()
            self._loaded_profile_key = None
            self._loaded_profile_snapshot = None
            self.query_one("#profile-select", Select).value = "custom"
            self.is_dirty = False
            self._update_dirty_indicator()
            self._update_profile_buttons()
            self.notify(f"Profile '{profile_name}' deleted", severity="information")
        except ValueError as e:
            self.notify(str(e), severity="error")

    def _on_set_default_profile(self) -> None:
        """Handle Set Default button press."""
        if not self._loaded_profile_key:
            return

        mgr = ProfileManager.get_instance()

        if mgr.set_default_profile(self._loaded_profile_key):
            profile = mgr.get_profile(self._loaded_profile_key)
            profile_name = profile.name if profile else self._loaded_profile_key
            self._update_profile_buttons()
            self._refresh_profile_dropdown()
            self.notify(f"'{profile_name}' is now the default profile", severity="information")
        else:
            self.notify("Failed to set default profile", severity="error")
