"""Help screen modal showing keyboard shortcuts."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


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
            yield Static("  b              Browse directories")
            yield Static("  /              Focus path input")
            yield Static("  Tab            Autocomplete path (in input)")
            yield Static("  Backspace      Go to parent directory")

            yield Label("── Preview Tab ──", classes="section")
            yield Static("  Space          Select/deselect (sets anchor)")
            yield Static("  Enter          Select range (anchor→current)")
            yield Static("  m              Merge selected chapters")
            yield Static("  x              Delete selected chapters")
            yield Static("  u              Undo last operation")
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
