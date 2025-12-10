"""Voice preview status widget."""

from textual.widgets import Static


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
