"""Status bar widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class StatusBar(Horizontal):
    """Status bar showing key bindings and messages."""

    def __init__(self) -> None:
        super().__init__()
        self._message = ""

    def compose(self) -> ComposeResult:
        """Compose the status bar."""
        # Use \[ to escape brackets in Rich markup
        yield Static(
            r"\[F]etch \[I]gnore \[W]Follow \[O]pen \[P]rocess \[Q]ueue \[S]tart Queue",
            id="keybindings",
        )
        yield Static("", id="status-message")

    def set_message(self, message: str) -> None:
        """Set the status message."""
        self._message = message
        status = self.query_one("#status-message", Static)
        status.update(message)

    def clear_message(self) -> None:
        """Clear the status message."""
        self.set_message("")
