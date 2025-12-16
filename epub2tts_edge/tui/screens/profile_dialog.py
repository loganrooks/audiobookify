"""Profile name input dialog."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class ProfileNameDialog(ModalScreen[str | None]):
    """Modal dialog for entering a profile name."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ProfileNameDialog {
        align: center middle;
    }

    #dialog-container {
        width: 50;
        height: auto;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }

    #dialog-container > Label.title {
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    #dialog-container > Label.hint {
        color: $text-muted;
        margin-bottom: 1;
    }

    #dialog-container > Input {
        margin-bottom: 1;
    }

    #dialog-buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        align: center middle;
    }

    #dialog-buttons > Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog-container"):
            yield Label("Save Profile", classes="title")
            yield Label("Enter a name for this profile:", classes="hint")
            yield Input(placeholder="My Custom Profile", id="profile-name-input")
            with Vertical(id="dialog-buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one("#profile-name-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self._save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._save()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(None)

    def _save(self) -> None:
        """Validate and save the profile name."""
        name_input = self.query_one("#profile-name-input", Input)
        name = name_input.value.strip()

        if not name:
            self.notify("Profile name cannot be empty", severity="error")
            name_input.focus()
            return

        if len(name) > 50:
            self.notify("Profile name too long (max 50 characters)", severity="error")
            name_input.focus()
            return

        self.dismiss(name)
