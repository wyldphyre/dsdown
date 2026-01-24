"""Simple confirmation dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmDialog(ModalScreen[bool]):
    """Modal dialog for confirming an action."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Vertical {
        width: 50;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDialog #title {
        text-align: center;
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }

    ConfirmDialog #message {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    ConfirmDialog #buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Vertical():
            yield Label(self._title, id="title")
            yield Label(self._message, id="message")
            with Horizontal(id="buttons"):
                yield Button("Yes", variant="primary", id="yes-btn")
                yield Button("No", variant="default", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "yes-btn":
            self.dismiss(True)
        elif event.button.id == "no-btn":
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(False)
